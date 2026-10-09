-- Self-checking constraint tests for data/schemas/schema.sql.
--
-- Why: the schema is the last line of defense for three promises the API makes
-- (CLAUDE.md principles 1 and 11): an estimate is never certified, a public centroid is
-- never exact, and an audit event never carries coordinates. This script proves that the
-- database refuses what it must refuse and accepts what it must accept.
--
-- Usage, after applying the schema (see docs/developer-guide/testing.md):
--
--     psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f .github/scripts/schema_constraints.sql
--
-- Every check prints "ok" as a NOTICE. A wrong outcome raises an exception, so psql stops
-- with a non-zero exit code. Everything runs in one transaction that is rolled back at the
-- end, so no row is left behind, but do not point it at a database that holds real data.

\set ON_ERROR_STOP on
\pset pager off
-- The checks are SELECTs that return nothing useful; the NOTICEs are the report.
\o /dev/null

BEGIN;

-- ---------------------------------------------------------------------------------------
-- Helpers (in pg_temp: they vanish with the session)
-- ---------------------------------------------------------------------------------------

-- The statement must fail with one of the SQLSTATEs (23514 check_violation by default).
CREATE FUNCTION pg_temp.expect_rejected(
    label text, stmt text, expected text[] DEFAULT ARRAY['23514']
) RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
    BEGIN
        EXECUTE stmt;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE = ANY (expected) THEN
            RAISE NOTICE 'ok    rejected: % [%]', label, SQLSTATE;
            RETURN;
        END IF;
        RAISE EXCEPTION 'FAIL  %: rejected with SQLSTATE % (%), expected one of %',
            label, SQLSTATE, SQLERRM, expected;
    END;
    RAISE EXCEPTION 'FAIL  %: the statement was accepted but must be rejected', label;
END
$fn$;

-- The statement must succeed.
CREATE FUNCTION pg_temp.expect_ok(label text, stmt text) RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
    BEGIN
        EXECUTE stmt;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'FAIL  %: rejected with SQLSTATE % (%) but must be accepted',
            label, SQLSTATE, SQLERRM;
    END;
    RAISE NOTICE 'ok    accepted: %', label;
END
$fn$;

CREATE FUNCTION pg_temp.expect_true(label text, condition boolean) RETURNS void
LANGUAGE plpgsql AS $fn$
BEGIN
    IF condition IS TRUE THEN
        RAISE NOTICE 'ok    holds:    %', label;
    ELSE
        RAISE EXCEPTION 'FAIL  %: the condition is not true', label;
    END IF;
END
$fn$;

-- An INSERT into plots with sensible defaults; every argument can be overridden.
CREATE FUNCTION pg_temp.plot_sql(
    p_id      text   DEFAULT 'PLT-T00001',
    p_country text   DEFAULT 'IN',
    p_area    float8 DEFAULT 1.5,
    p_lat     float8 DEFAULT 12.05,
    p_lon     float8 DEFAULT 77.0,
    p_source  text   DEFAULT 'api',
    p_record  text   DEFAULT '{}',
    p_geojson text   DEFAULT $g${"type":"Polygon","coordinates":[[[77,12],[77.01,12],[77.01,12.01],[77,12.01],[77,12]]]}$g$
) RETURNS text LANGUAGE sql AS $fn$
    SELECT format(
        $q$INSERT INTO plots (plot_id, country, name, geom, area_hectares,
                              public_centroid_lat, public_centroid_lon, source, record)
           VALUES (%L, %L, 'constraint test', ST_SetSRID(ST_GeomFromGeoJSON(%L), 4326),
                   %s, %s, %s, %L, %L::jsonb)$q$,
        p_id, p_country, p_geojson, p_area, p_lat, p_lon, p_source, p_record)
$fn$;

-- ---------------------------------------------------------------------------------------
-- The revision
-- ---------------------------------------------------------------------------------------
SELECT pg_temp.expect_true('schema_version records revision 0.2.0',
    EXISTS (SELECT 1 FROM schema_version WHERE version = '0.2.0'));

-- ---------------------------------------------------------------------------------------
-- plots
-- ---------------------------------------------------------------------------------------
SELECT pg_temp.expect_ok('a valid private plot',
    pg_temp.plot_sql(p_area => 1.26, p_source => 'qgis-plugin', p_record => '{"privacy":"private"}'));
SELECT pg_temp.expect_ok('every PlotSource the API knows is a valid source',
    pg_temp.plot_sql(p_id => 'PLT-T00002', p_source => 'pin-and-area'));
SELECT pg_temp.expect_ok('public centroid with floating-point noise (12.350000000000001)',
    pg_temp.plot_sql(p_id => 'PLT-T00003', p_lat => 12.350000000000001, p_lon => 77.10000000000001));

SELECT pg_temp.expect_rejected('area of zero',
    pg_temp.plot_sql(p_id => 'PLT-T00010', p_area => 0));
SELECT pg_temp.expect_rejected('the public view stored as the private record',
    pg_temp.plot_sql(p_id => 'PLT-T00011', p_record => '{"privacy":"generalized-public"}'));
SELECT pg_temp.expect_rejected('an exact coordinate as the public centroid',
    pg_temp.plot_sql(p_id => 'PLT-T00012', p_lat => 12.971634, p_lon => 77.594612));
SELECT pg_temp.expect_rejected('a plot id without the PLT- prefix',
    pg_temp.plot_sql(p_id => 'plt-1'));
SELECT pg_temp.expect_rejected('a country that is not ISO 3166-1 alpha-2',
    pg_temp.plot_sql(p_id => 'PLT-T00013', p_country => 'IND'));
SELECT pg_temp.expect_rejected('a source with spaces and capitals',
    pg_temp.plot_sql(p_id => 'PLT-T00014', p_source => 'Manual Drawing'));
SELECT pg_temp.expect_rejected('a self-intersecting (bow-tie) polygon',
    pg_temp.plot_sql(p_id => 'PLT-T00015',
        p_geojson => '{"type":"Polygon","coordinates":[[[0,0],[1,1],[1,0],[0,1],[0,0]]]}'));
SELECT pg_temp.expect_rejected('a polygon whose ring is not closed',
    pg_temp.plot_sql(p_id => 'PLT-T00016',
        p_geojson => '{"type":"Polygon","coordinates":[[[77,12],[77.01,12],[77.01,12.01],[77,12.01]]]}'),
    ARRAY['23514', '22023', 'XX000']);
SELECT pg_temp.expect_rejected('a polygon with z values (the column has two dimensions)',
    pg_temp.plot_sql(p_id => 'PLT-T00017',
        p_geojson => '{"type":"Polygon","coordinates":[[[77,12,5],[77.01,12,5],[77.01,12.01,5],[77,12.01,5],[77,12,5]]]}'),
    ARRAY['22023', '23514', 'XX000']);
SELECT pg_temp.expect_rejected('a duplicate plot id',
    pg_temp.plot_sql(), ARRAY['23505']);

-- The public projection
SELECT pg_temp.expect_true('plots_public has no name, geometry or record column',
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'plots_public' AND column_name IN ('geom', 'name', 'record')));
SELECT pg_temp.expect_true('plots_public rounds the area to 0.1 ha (1.26 becomes 1.3)',
    (SELECT area_hectares FROM plots_public WHERE plot_id = 'PLT-T00001') = 1.3);

-- ---------------------------------------------------------------------------------------
-- land_observations, tree_inventory
-- ---------------------------------------------------------------------------------------
SELECT pg_temp.expect_ok('a land observation',
    $s$INSERT INTO land_observations (plot_id, record) VALUES ('PLT-T00001', '{"mode":"demo"}')$s$);
SELECT pg_temp.expect_rejected('a land observation for a plot that does not exist',
    $s$INSERT INTO land_observations (plot_id, record) VALUES ('PLT-NOPE00', '{}')$s$, ARRAY['23503']);
SELECT pg_temp.expect_rejected('a land observation whose record is not an object',
    $s$INSERT INTO land_observations (plot_id, record) VALUES ('PLT-T00002', '[]')$s$);

SELECT pg_temp.expect_ok('a tree inventory',
    $s$INSERT INTO tree_inventory (inventory_id, plot_id, record)
       VALUES ('INV-AB12', 'PLT-T00001', '{"tree_count":10}')$s$);
SELECT pg_temp.expect_ok('the same inventory id on another plot (ids are unique per plot only)',
    $s$INSERT INTO tree_inventory (inventory_id, plot_id, record)
       VALUES ('INV-AB12', 'PLT-T00002', '{"tree_count":4}')$s$);
SELECT pg_temp.expect_rejected('the same inventory id twice on one plot',
    $s$INSERT INTO tree_inventory (inventory_id, plot_id, record)
       VALUES ('INV-AB12', 'PLT-T00001', '{}')$s$, ARRAY['23505']);

-- ---------------------------------------------------------------------------------------
-- carbon_estimates: never certified, ordered range, known confidence
-- ---------------------------------------------------------------------------------------
SELECT pg_temp.expect_ok('an estimate that says certified: false',
    $s$INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high,
                                     unit, confidence, record)
       VALUES ('EST-AB12', 'PLT-T00001', 'INV-AB12', 2, 1, 3, 'tCO2e/yr', 'medium',
               '{"certified": false}')$s$);
SELECT pg_temp.expect_ok('an estimate without a certified key',
    $s$INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high,
                                     unit, confidence, record)
       VALUES ('EST-CD34', 'PLT-T00001', NULL, 2, 1, 3, 'tCO2e/yr', 'low', '{}')$s$);
SELECT pg_temp.expect_rejected('an estimate that says certified: true',
    $s$INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high,
                                     unit, confidence, record)
       VALUES ('EST-EF56', 'PLT-T00001', NULL, 2, 1, 3, 'tCO2e/yr', 'low', '{"certified": true}')$s$);
SELECT pg_temp.expect_rejected('an estimate that says certified: "true" (a string)',
    $s$INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high,
                                     unit, confidence, record)
       VALUES ('EST-EF57', 'PLT-T00001', NULL, 2, 1, 3, 'tCO2e/yr', 'low', '{"certified": "true"}')$s$);
SELECT pg_temp.expect_rejected('a range with low above central',
    $s$INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high,
                                     unit, confidence, record)
       VALUES ('EST-GH78', 'PLT-T00001', NULL, 2, 5, 3, 'tCO2e/yr', 'low', '{}')$s$);
SELECT pg_temp.expect_rejected('a confidence grade outside low, medium and high',
    $s$INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high,
                                     unit, confidence, record)
       VALUES ('EST-IJ90', 'PLT-T00001', NULL, 2, 1, 3, 'tCO2e/yr', 'certain', '{}')$s$);
SELECT pg_temp.expect_rejected('an estimate that points at an inventory that does not exist',
    $s$INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high,
                                     unit, confidence, record)
       VALUES ('EST-KL12', 'PLT-T00001', 'INV-NOPE', 2, 1, 3, 'tCO2e/yr', 'low', '{}')$s$,
    ARRAY['23503']);

-- Deleting an inventory keeps the estimate and clears only the link.
DELETE FROM tree_inventory WHERE plot_id = 'PLT-T00001' AND inventory_id = 'INV-AB12';
SELECT pg_temp.expect_true('deleting an inventory keeps its estimate and clears the link',
    (SELECT inventory_id IS NULL FROM carbon_estimates
      WHERE plot_id = 'PLT-T00001' AND estimate_id = 'EST-AB12'));

-- ---------------------------------------------------------------------------------------
-- reports, records
-- ---------------------------------------------------------------------------------------
SELECT pg_temp.expect_ok('a report',
    $s$INSERT INTO reports (report_id, plot_id, format, meta, content)
       VALUES ('RPT-2026-10-05-0001', 'PLT-T00001', 'html', '{}', 'x')$s$);
SELECT pg_temp.expect_rejected('a report id in the wrong shape',
    $s$INSERT INTO reports (report_id, plot_id, format, meta, content)
       VALUES ('RPT-1', 'PLT-T00001', 'html', '{}', 'x')$s$);
SELECT pg_temp.expect_rejected('a report format in capitals',
    $s$INSERT INTO reports (report_id, plot_id, format, meta, content)
       VALUES ('RPT-2026-10-05-0002', 'PLT-T00001', 'HTML', '{}', 'x')$s$);

SELECT pg_temp.expect_ok('a generic record with a plot',
    $s$INSERT INTO records (kind, record_id, plot_id, record)
       VALUES ('import', 'IMP-1', 'PLT-T00001', '{"features":1}')$s$);
SELECT pg_temp.expect_ok('a generic record without a plot',
    $s$INSERT INTO records (kind, record_id, record) VALUES ('detection', 'DET-1', '{"trees":3}')$s$);
SELECT pg_temp.expect_ok('the same record id under another kind',
    $s$INSERT INTO records (kind, record_id, record) VALUES ('agent-run', 'IMP-1', '{}')$s$);
SELECT pg_temp.expect_rejected('a record that is not an object',
    $s$INSERT INTO records (kind, record_id, record) VALUES ('import', 'IMP-2', '[]')$s$);
SELECT pg_temp.expect_rejected('a record for a plot that does not exist',
    $s$INSERT INTO records (kind, record_id, plot_id, record)
       VALUES ('import', 'IMP-3', 'PLT-NOPE00', '{}')$s$, ARRAY['23503']);
SELECT pg_temp.expect_rejected('a blank record kind',
    $s$INSERT INTO records (kind, record_id, record) VALUES ('  ', 'IMP-4', '{}')$s$);

-- ---------------------------------------------------------------------------------------
-- audit_events: no coordinates at any depth
-- ---------------------------------------------------------------------------------------
SELECT pg_temp.expect_ok('an audit event with harmless keys (latest and layers contain "lat")',
    $s$INSERT INTO audit_events (event, plot_id, detail)
       VALUES ('plot.analyzed', 'PLT-T00001',
               '{"latest": 1, "layers": ["landcover"], "area_hectares": 4.2}')$s$);
SELECT pg_temp.expect_rejected('an audit event with lat and lon',
    $s$INSERT INTO audit_events (event, plot_id, detail)
       VALUES ('x', 'PLT-T00001', '{"lat": 12.9, "lon": 77.5}')$s$);
SELECT pg_temp.expect_rejected('an audit event with coordinates nested two levels down, in capitals',
    $s$INSERT INTO audit_events (event, plot_id, detail)
       VALUES ('x', 'PLT-T00001', '{"where": {"Centroid": [1, 2]}}')$s$);
SELECT pg_temp.expect_rejected('an audit event whose detail is not an object',
    $s$INSERT INTO audit_events (event, plot_id, detail) VALUES ('x', 'PLT-T00001', '[]')$s$);

-- ---------------------------------------------------------------------------------------
-- Deleting a plot deletes everything derived from it, except the audit trail
-- ---------------------------------------------------------------------------------------
INSERT INTO audit_events (event, plot_id, detail) VALUES ('plot.deleted', 'PLT-T00001', '{}');
DELETE FROM plots WHERE plot_id = 'PLT-T00001';
SELECT pg_temp.expect_true('delete cascades to land_observations',
    NOT EXISTS (SELECT 1 FROM land_observations WHERE plot_id = 'PLT-T00001'));
SELECT pg_temp.expect_true('delete cascades to tree_inventory',
    NOT EXISTS (SELECT 1 FROM tree_inventory WHERE plot_id = 'PLT-T00001'));
SELECT pg_temp.expect_true('delete cascades to carbon_estimates',
    NOT EXISTS (SELECT 1 FROM carbon_estimates WHERE plot_id = 'PLT-T00001'));
SELECT pg_temp.expect_true('delete cascades to reports',
    NOT EXISTS (SELECT 1 FROM reports WHERE plot_id = 'PLT-T00001'));
SELECT pg_temp.expect_true('delete cascades to generic records of that plot',
    NOT EXISTS (SELECT 1 FROM records WHERE plot_id = 'PLT-T00001'));
SELECT pg_temp.expect_true('delete keeps records that belong to no plot',
    EXISTS (SELECT 1 FROM records WHERE kind = 'detection' AND record_id = 'DET-1'));
SELECT pg_temp.expect_true('delete keeps the audit events, including plot.deleted',
    EXISTS (SELECT 1 FROM audit_events WHERE event = 'plot.deleted' AND plot_id = 'PLT-T00001'));

ROLLBACK;

\o
\echo 'schema_constraints.sql: every check passed; nothing was written.'
