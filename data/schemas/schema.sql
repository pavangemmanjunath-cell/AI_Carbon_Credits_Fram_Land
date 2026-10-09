-- =============================================================================
-- AgriCarbon Atlas -- PostgreSQL + PostGIS schema, revision 0.2.0
-- =============================================================================
--
-- Target: PostgreSQL 15 or newer with PostGIS 3. Verified on PostgreSQL 16 with
-- PostGIS 3.4, the image docker-compose.yml uses (postgis/postgis:16-3.4).
-- PostgreSQL 15 is the floor because of ON DELETE SET NULL (column list) below.
--
-- Used when ATLAS_REPOSITORY=postgres (apps/api/app/repositories/postgres.py).
-- docker-compose.yml mounts this file as /docker-entrypoint-initdb.d/01-schema.sql,
-- so the image runs it ONCE, on the first start of an empty data directory. The
-- file is idempotent (IF NOT EXISTS everywhere) and can be applied by hand to any
-- database, which is also how you upgrade:
--
--     psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/schemas/schema.sql
--
-- CREATE EXTENSION postgis needs a role that may create extensions (the compose
-- superuser does). On a managed service, enable PostGIS once as an administrator.
-- The API itself never creates or alters tables.
--
-- Design rules (CLAUDE.md, docs/privacy/):
--   * PRIVACY. plots.geom and plots.record hold the EXACT boundary and belong to
--     the owner. Anything public reads the plots_public view: generalized
--     centroid (0.05-degree grid, about 5.5 km), area rounded to 0.1 ha, no name,
--     no geometry. Coordinates never go into audit_events.
--   * NOT CREDITS. A carbon estimate is a modelled range, never a credit. The
--     stored JSON may not say "certified": true (CHECK on carbon_estimates).
--   * Records are stored as JSONB exactly as the API returns them; the contract
--     in docs/architecture/api-contract.md is the source of truth. The typed
--     columns beside the JSON exist for ordering, joins, limits and indexes.
--   * Deleting a plot deletes everything derived from it (analysis, inventories,
--     estimates, reports, generic records), as docs/privacy/data-retention.md
--     promises. audit_events has NO foreign key: the deletion event itself has
--     to outlive the plot. It stores event names and ids, never coordinates.
--
-- Tables and the SQL in postgres.py that they serve
--   plots              save_plot, get_plot, list_plots, delete_plot
--   land_observations  save_analysis, get_analysis       (latest analysis per plot)
--   tree_inventory     save_inventory, list_inventories, get_inventory
--   carbon_estimates   save_estimate, list_estimates, get_estimate
--   reports            save_report, get_report, report_ids
--   records            save_record, get_record, list_records, delete_record
--   audit_events       audit
--   schema_version     (not used by the API; tells operators which revision ran)
--   plots_public       (view; the privacy-safe projection of plots)
--
-- Naming: early design notes called land_observations "plot_analyses" and
-- tree_inventory "tree_inventories". The repository uses the names above, and
-- this file follows the repository.
--
-- GEOMETRY CAVEAT. plots.geom is geometry(Polygon, 4326): two dimensions, valid,
-- rings closed. postgres.py passes the GeoJSON of the request to
-- ST_GeomFromGeoJSON as it is. geo_engine.validate_polygon (which the API runs
-- first) also accepts [lon, lat, z] positions and closes an open ring in its
-- own copy, but PlotService.create keeps the raw request geometry. The database
-- rejects that raw input in both cases: "Geometry has Z dimension but column
-- does not" for z values, and plots_geom_valid for an open ring. With
-- ATLAS_REPOSITORY=postgres the API then answers 500 where the in-memory
-- repository answers 201. Code that stores a plot must store the normalised
-- polygon the validator returns, not the raw client input. Polygons with
-- holes are fine. (Checked against PostgreSQL 16 and PostGIS 3.4.)
--
-- Tests: the "postgres" job in .github/workflows/ci.yml applies this file twice,
-- runs .github/scripts/postgres_smoke.py (every PostgresRepository method) and
-- .github/scripts/schema_constraints.sql (what the database must refuse). See
-- docs/developer-guide/testing.md, section "Testing the PostgreSQL schema".
-- =============================================================================

BEGIN;

SET LOCAL client_min_messages = warning;   -- quiet "already exists, skipping"

CREATE EXTENSION IF NOT EXISTS postgis;

-- -----------------------------------------------------------------------------
-- schema_version -- one row per applied revision
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version    text        PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE schema_version IS 'Revisions of this file that have been applied to the database. Informational.';

-- -----------------------------------------------------------------------------
-- plots -- a user-defined land parcel
-- -----------------------------------------------------------------------------
-- postgres.py: INSERT ... ON CONFLICT (plot_id) DO UPDATE SET record, name, geom,
-- area_hectares, updated_at; SELECT record ... ORDER BY created_at;
-- DELETE ... RETURNING plot_id.
--
-- PRIVACY: geom and record contain the exact boundary (record also the exact
-- centroid and bounding box). The generalized centroid lives in
-- public_centroid_lat / public_centroid_lon and is the only location a public
-- view may use.
CREATE TABLE IF NOT EXISTS plots (
    plot_id             text             PRIMARY KEY,
    country             text,
    name                text,
    geom                geometry(Polygon, 4326) NOT NULL,
    area_hectares       double precision NOT NULL,
    public_centroid_lat double precision NOT NULL,
    public_centroid_lon double precision NOT NULL,
    -- The generalized centroid as a point, for public map queries.
    public_centroid     geometry(Point, 4326)
        GENERATED ALWAYS AS (
            ST_SetSRID(ST_MakePoint(public_centroid_lon, public_centroid_lat), 4326)
        ) STORED,
    source              text,
    record              jsonb            NOT NULL,
    created_at          timestamptz      NOT NULL DEFAULT now(),
    updated_at          timestamptz,

    -- data/schemas/plot.schema.json: ^PLT-[A-Z0-9]{4,12}$
    CONSTRAINT plots_plot_id_format CHECK (plot_id ~ '^PLT-[A-Z0-9]{4,12}$'),
    -- ISO 3166-1 alpha-2. EU member states keep their own code; policy maps them to EU.
    CONSTRAINT plots_country_iso2 CHECK (country IS NULL OR country ~ '^[A-Z]{2}$'),
    CONSTRAINT plots_area_positive CHECK (area_hectares > 0),
    CONSTRAINT plots_geom_valid CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
    CONSTRAINT plots_public_centroid_range CHECK (
        public_centroid_lat BETWEEN -90 AND 90 AND public_centroid_lon BETWEEN -180 AND 180
    ),
    -- Backstop for the privacy rule: the public centroid carries no more than two
    -- decimals (about 1 km), within a tolerance of 1e-6 degrees for floating-point
    -- noise. geo_engine.generalize_point snaps to 0.05 degrees; this check only
    -- refuses an exact coordinate that was copied here by mistake. A finer public
    -- grid is a privacy decision: change this constraint on purpose, not by accident.
    CONSTRAINT plots_public_centroid_coarse CHECK (
        abs(public_centroid_lat - round(public_centroid_lat::numeric, 2)::float8) < 1e-6
        AND abs(public_centroid_lon - round(public_centroid_lon::numeric, 2)::float8) < 1e-6
    ),
    -- Where the boundary came from. A format check, not a list: a new PlotSource in
    -- apps/api/app/schemas/requests.py must not need a migration. Today:
    -- manual-drawing, upload, import, pin-and-area, tree-line, coordinates,
    -- qgis-plugin, api, and synthetic-demo (the demo seed).
    CONSTRAINT plots_source_format CHECK (source IS NULL OR source ~ '^[a-z][a-z0-9-]*$'),
    CONSTRAINT plots_record_is_object CHECK (jsonb_typeof(record) = 'object'),
    -- The stored record is the private one. The public view ("generalized-public")
    -- is built on read and is never stored.
    CONSTRAINT plots_record_private CHECK (
        record ->> 'privacy' IS NULL OR record ->> 'privacy' = 'private'
    )
);

CREATE INDEX IF NOT EXISTS plots_geom_gist            ON plots USING gist (geom);
CREATE INDEX IF NOT EXISTS plots_public_centroid_gist ON plots USING gist (public_centroid);
CREATE INDEX IF NOT EXISTS plots_country_idx          ON plots (country);
CREATE INDEX IF NOT EXISTS plots_created_at_idx       ON plots (created_at);

COMMENT ON TABLE  plots IS 'User-defined land parcels. PRIVATE: geom and record hold the exact boundary. Public views must read plots_public.';
COMMENT ON COLUMN plots.geom IS 'PRIVATE. Exact boundary, WGS 84, two dimensions. Never log it, send it to an LLM, or put it in a share link.';
COMMENT ON COLUMN plots.name IS 'Free text typed by the owner. Treat as personal data; plots_public does not expose it.';
COMMENT ON COLUMN plots.area_hectares IS 'Geodesic area in hectares, computed by geo_engine.measure_polygon. Must be greater than zero.';
COMMENT ON COLUMN plots.public_centroid_lat IS 'Generalized latitude on the 0.05-degree grid. Safe for public views.';
COMMENT ON COLUMN plots.public_centroid_lon IS 'Generalized longitude on the 0.05-degree grid. Safe for public views.';
COMMENT ON COLUMN plots.public_centroid IS 'Point built from the generalized centroid. Safe for public views.';
COMMENT ON COLUMN plots.source IS 'How the boundary was created: manual-drawing, upload, import, pin-and-area, tree-line, coordinates, qgis-plugin, api, synthetic-demo.';
COMMENT ON COLUMN plots.record IS 'PRIVATE. The full plot record as the API returns it to its owner, including exact geometry, centroid and bbox. privacy is always "private".';

-- The public projection of plots. Grant this view, never the base table, to any
-- role that serves public or shared views, for example:
--     GRANT SELECT ON plots_public TO atlas_public;
-- Area is rounded to 0.1 ha (docs/privacy/geolocation.md). Name, geometry, exact
-- centroid and the JSON record are deliberately absent.
CREATE OR REPLACE VIEW plots_public WITH (security_barrier = true) AS
SELECT plot_id,
       country,
       round(area_hectares::numeric, 1) AS area_hectares,
       public_centroid_lat,
       public_centroid_lon,
       public_centroid,
       source,
       created_at
  FROM plots;

COMMENT ON VIEW plots_public IS 'Privacy-safe projection of plots: generalized centroid, area rounded to 0.1 ha. No name, geometry, exact centroid or record.';

-- -----------------------------------------------------------------------------
-- land_observations -- the latest analysis of a plot
-- -----------------------------------------------------------------------------
-- postgres.py: INSERT (plot_id, record) ON CONFLICT (plot_id) DO UPDATE SET
-- record, observed_at; SELECT record WHERE plot_id = %s. A new analysis replaces
-- the old one; the history is in each record's provenance.
--
-- PRIVACY: the record can carry the plot bounding box (raster windows) and the
-- vegetation cube grid. Treat it as location data.
CREATE TABLE IF NOT EXISTS land_observations (
    plot_id     text        PRIMARY KEY REFERENCES plots (plot_id) ON DELETE CASCADE,
    record      jsonb       NOT NULL,
    observed_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT land_observations_record_is_object CHECK (jsonb_typeof(record) = 'object')
);

COMMENT ON TABLE land_observations IS 'Latest land analysis per plot: land cover, vegetation indices, climate, soil, data quality, provenance. PRIVATE (may include the bounding box). Deleted with the plot.';

-- -----------------------------------------------------------------------------
-- tree_inventory -- trees reported for a plot
-- -----------------------------------------------------------------------------
-- postgres.py: INSERT (inventory_id, plot_id, record); SELECT record WHERE
-- plot_id = %s ORDER BY created_at; ... AND inventory_id = %s.
-- Ids look like INV-AB12 and are only unique within a plot, hence the composite key.
CREATE TABLE IF NOT EXISTS tree_inventory (
    inventory_id text        NOT NULL,
    plot_id      text        NOT NULL REFERENCES plots (plot_id) ON DELETE CASCADE,
    record       jsonb       NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (plot_id, inventory_id),
    CONSTRAINT tree_inventory_record_is_object CHECK (jsonb_typeof(record) = 'object')
);

CREATE INDEX IF NOT EXISTS tree_inventory_plot_created_idx ON tree_inventory (plot_id, created_at);

COMMENT ON TABLE tree_inventory IS 'Tree inventories as API records (data/schemas/tree-inventory.schema.json). Species, counts and ages are not coordinates, but with a district they narrow identity: PRIVATE to the owner.';

-- -----------------------------------------------------------------------------
-- carbon_estimates -- modelled removal scenarios
-- -----------------------------------------------------------------------------
-- postgres.py: INSERT (estimate_id, plot_id, inventory_id, central, low, high,
-- unit, confidence, record); SELECT record WHERE plot_id = %s ORDER BY created_at
-- [AND estimate_id = %s]. Ids look like EST-AB12 and are only unique within a plot.
--
-- NOT A CREDIT (CLAUDE.md principle 1): the carbon engine always writes
-- "certified": false. The CHECK keeps a hand-written or buggy record from
-- claiming otherwise. If a registry integration ever exists, a certified credit
-- is a different object and belongs in its own table.
CREATE TABLE IF NOT EXISTS carbon_estimates (
    estimate_id  text             NOT NULL,
    plot_id      text             NOT NULL REFERENCES plots (plot_id) ON DELETE CASCADE,
    inventory_id text,
    central      double precision NOT NULL,
    low          double precision NOT NULL,
    high         double precision NOT NULL,
    unit         text             NOT NULL,
    confidence   text             NOT NULL,
    record       jsonb            NOT NULL,
    created_at   timestamptz      NOT NULL DEFAULT now(),

    PRIMARY KEY (plot_id, estimate_id),
    -- Deleting an inventory keeps the estimate and clears only the link.
    FOREIGN KEY (plot_id, inventory_id) REFERENCES tree_inventory (plot_id, inventory_id)
        ON DELETE SET NULL (inventory_id),
    CONSTRAINT carbon_estimates_range_ordered CHECK (low <= central AND central <= high),
    -- carbon_engine.CONFIDENCE_LEVELS
    CONSTRAINT carbon_estimates_confidence_known CHECK (confidence IN ('low', 'medium', 'high')),
    CONSTRAINT carbon_estimates_record_is_object CHECK (jsonb_typeof(record) = 'object'),
    -- A record without the key passes; one that says anything but false does not.
    CONSTRAINT carbon_estimates_record_not_certified CHECK (
        COALESCE(record -> 'certified', 'false'::jsonb) = 'false'::jsonb
    )
);

CREATE INDEX IF NOT EXISTS carbon_estimates_plot_created_idx ON carbon_estimates (plot_id, created_at);

COMMENT ON TABLE  carbon_estimates IS 'Scenario estimates with a low/central/high range, confidence and provenance. Estimates are NOT carbon credits.';
COMMENT ON COLUMN carbon_estimates.central IS 'Central estimate of annual removal. The unit column says which unit (tCO2e/yr for the current models).';
COMMENT ON COLUMN carbon_estimates.record IS 'Full API record: model, methodology, parameters_used with verification_status, readiness, provenance, disclaimer. "certified" is always false.';

-- -----------------------------------------------------------------------------
-- reports -- rendered report files
-- -----------------------------------------------------------------------------
-- postgres.py: INSERT (report_id, plot_id, format, meta, content); SELECT meta,
-- content WHERE report_id = %s; SELECT report_id.
-- Ids come from report_engine.ReportIdSequencer: RPT-YYYY-MM-DD-NNNN.
--
-- PRIVACY: a report may contain the exact boundary when the owner included it.
-- Default retention is 30 days (docs/privacy/data-retention.md); clean-up is the
-- deployer's job.
CREATE TABLE IF NOT EXISTS reports (
    report_id  text        PRIMARY KEY,
    plot_id    text        REFERENCES plots (plot_id) ON DELETE CASCADE,
    format     text,
    meta       jsonb       NOT NULL,
    content    bytea       NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT reports_report_id_format CHECK (report_id ~ '^RPT-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4,}$'),
    -- html, json, markdown or pdf today (ReportFormat in apps/api/app/schemas/requests.py)
    CONSTRAINT reports_format_token CHECK (format IS NULL OR format ~ '^[a-z0-9]{2,16}$'),
    CONSTRAINT reports_meta_is_object CHECK (jsonb_typeof(meta) = 'object')
);

CREATE INDEX IF NOT EXISTS reports_plot_idx    ON reports (plot_id);
CREATE INDEX IF NOT EXISTS reports_created_idx ON reports (created_at);

COMMENT ON TABLE reports IS 'Rendered HTML, Markdown, JSON or PDF reports (bytes) with metadata. PRIVATE: may include the exact boundary. Deleted with the plot.';

-- -----------------------------------------------------------------------------
-- records -- generic, kind-tagged JSON records
-- -----------------------------------------------------------------------------
-- postgres.py: INSERT (kind, record_id, plot_id, record) ON CONFLICT (kind,
-- record_id) DO UPDATE SET record, plot_id, updated_at;
-- SELECT record WHERE kind = %s AND record_id = %s;
-- SELECT record WHERE kind = %s [AND plot_id = %s] ORDER BY created_at DESC LIMIT %s;
-- DELETE ... WHERE kind = %s AND record_id = %s RETURNING record_id.
--
-- Feature modules that do not need their own table keep their data here:
-- imports, detection results and agent runs. The module that writes a kind owns
-- the shape of its records.
--
-- PRIVACY: an import or a detection result contains coordinates by nature, so
-- the table is PRIVATE like plots. Agent-run records hold derived indicators only
-- (CLAUDE.md principle 11): no coordinates, no geometry, no addresses.
CREATE TABLE IF NOT EXISTS records (
    kind       text        NOT NULL,
    record_id  text        NOT NULL,
    plot_id    text        REFERENCES plots (plot_id) ON DELETE CASCADE,
    record     jsonb       NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,

    PRIMARY KEY (kind, record_id),
    CONSTRAINT records_kind_not_blank CHECK (length(btrim(kind)) > 0),
    CONSTRAINT records_record_id_not_blank CHECK (length(btrim(record_id)) > 0),
    CONSTRAINT records_record_is_object CHECK (jsonb_typeof(record) = 'object')
);

CREATE INDEX IF NOT EXISTS records_kind_plot_created_idx ON records (kind, plot_id, created_at DESC);
-- list_records without a plot filter
CREATE INDEX IF NOT EXISTS records_kind_created_idx      ON records (kind, created_at DESC);
-- delete_plot and the ON DELETE CASCADE look rows up by plot only
CREATE INDEX IF NOT EXISTS records_plot_idx              ON records (plot_id);

COMMENT ON TABLE  records IS 'Generic JSON records tagged by kind (imports, detection results, agent runs). PRIVATE: may contain coordinates. A record with a plot_id is deleted with that plot.';
COMMENT ON COLUMN records.kind IS 'Record type, chosen by the service that writes it. Together with record_id it is the primary key.';
COMMENT ON COLUMN records.plot_id IS 'Owning plot, or NULL for records that belong to no plot (for example an import that has not been turned into plots yet).';
COMMENT ON COLUMN records.record IS 'The record as a JSON object. Agent-run records contain derived indicators only, never coordinates or geometry.';

-- -----------------------------------------------------------------------------
-- audit_events -- operational audit trail
-- -----------------------------------------------------------------------------
-- postgres.py: INSERT (event, plot_id, detail). Events the services write today:
-- plot.created, plot.deleted, plot.analyzed, plot.cube, inventory.created,
-- estimate.created, report.created.
--
-- PRIVACY: plot_id is NOT a foreign key on purpose, so that "plot.deleted"
-- survives the plot. detail must never carry coordinates. The CHECK rejects a
-- location key at any depth of the JSON as a last line of defense; the real
-- control is that the services never pass one. Detail is a small object such as
-- {"area_hectares": 4.2} or {"report_id": "...", "format": "html"}.
CREATE TABLE IF NOT EXISTS audit_events (
    id      bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event   text        NOT NULL,
    plot_id text,
    detail  jsonb       NOT NULL DEFAULT '{}'::jsonb,
    at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT audit_events_detail_is_object CHECK (jsonb_typeof(detail) = 'object'),
    CONSTRAINT audit_events_detail_no_location CHECK (
        detail::text !~* '"(lat|lon|lng|latitude|longitude|coordinates|geometry|centroid|bbox|polygon)"\s*:'
    )
);

CREATE INDEX IF NOT EXISTS audit_events_plot_at_idx  ON audit_events (plot_id, at);
CREATE INDEX IF NOT EXISTS audit_events_event_at_idx ON audit_events (event, at);

COMMENT ON TABLE audit_events IS 'Operational audit trail: event name, plot id, small detail object. NEVER coordinates. No foreign key, so deletion events outlive the plot.';

-- -----------------------------------------------------------------------------
-- Upgrading a database created from revision 0.1
-- -----------------------------------------------------------------------------
-- CREATE TABLE IF NOT EXISTS leaves existing tables alone, so the statements
-- below bring the constraints that changed in 0.2.0 into line. They are
-- idempotent and change nothing on a database created from this file. Delete
-- this block once no 0.1 database is left.
--   * plots_source_known allowed four plot sources and rejected import,
--     pin-and-area, tree-line, coordinates and qgis-plugin. It is replaced by
--     plots_source_format.
--   * reports_format_known is replaced by reports_format_token the same way.
--   * plots_record_private, plots_public_centroid_coarse and
--     carbon_estimates_record_not_certified are new. The last one refuses
--     "certified" with any value but false, a JSON string included. The 0.1
--     constraint only refused the boolean true, and let it through when a
--     registry_serial was present. Nothing in this repository ever writes a
--     registry serial, so a row that trips the new constraint is a data problem
--     to look at; the upgrade then stops and rolls back as a whole.
--   * audit_events_detail_no_location now looks at every depth of the JSON.
-- Not touched, because nothing reads or writes them: the 0.1 tables
-- plot_analyses, tree_inventories, agent_runs and audit_log, the 0.1 columns
-- carbon_estimates.certified and registry_serial with their constraints, and the
-- 0.1 pattern for report ids. Drop them if you want the exact 0.2.0 shape.
ALTER TABLE plots DROP CONSTRAINT IF EXISTS plots_source_known;
ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_format_known;

DO $upgrade$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'plots'::regclass AND conname = 'plots_source_format') THEN
        ALTER TABLE plots ADD CONSTRAINT plots_source_format
            CHECK (source IS NULL OR source ~ '^[a-z][a-z0-9-]*$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'reports'::regclass AND conname = 'reports_format_token') THEN
        ALTER TABLE reports ADD CONSTRAINT reports_format_token
            CHECK (format IS NULL OR format ~ '^[a-z0-9]{2,16}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'plots'::regclass AND conname = 'plots_record_private') THEN
        ALTER TABLE plots ADD CONSTRAINT plots_record_private
            CHECK (record ->> 'privacy' IS NULL OR record ->> 'privacy' = 'private');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'plots'::regclass AND conname = 'plots_public_centroid_coarse') THEN
        ALTER TABLE plots ADD CONSTRAINT plots_public_centroid_coarse
            CHECK (abs(public_centroid_lat - round(public_centroid_lat::numeric, 2)::float8) < 1e-6
                   AND abs(public_centroid_lon - round(public_centroid_lon::numeric, 2)::float8) < 1e-6);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'carbon_estimates'::regclass
                      AND conname = 'carbon_estimates_record_not_certified') THEN
        ALTER TABLE carbon_estimates ADD CONSTRAINT carbon_estimates_record_not_certified
            CHECK (COALESCE(record -> 'certified', 'false'::jsonb) = 'false'::jsonb);
    END IF;
    -- The 0.1 constraint tested top-level keys only (it used the ?| operator).
    IF EXISTS (SELECT 1 FROM pg_constraint
                WHERE conrelid = 'audit_events'::regclass
                  AND conname = 'audit_events_detail_no_location'
                  AND pg_get_constraintdef(oid) LIKE '%?|%') THEN
        ALTER TABLE audit_events DROP CONSTRAINT audit_events_detail_no_location;
        ALTER TABLE audit_events ADD CONSTRAINT audit_events_detail_no_location CHECK (
            detail::text !~* '"(lat|lon|lng|latitude|longitude|coordinates|geometry|centroid|bbox|polygon)"\s*:'
        );
    END IF;
END
$upgrade$;

INSERT INTO schema_version (version) VALUES ('0.2.0') ON CONFLICT (version) DO NOTHING;

COMMIT;
