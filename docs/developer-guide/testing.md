# Testing

This software produces numbers that people may act on, so tests are a requirement, not a courtesy
([CLAUDE.md](../../CLAUDE.md) principle 10): every calculation has a test, and the production gate
refuses `pending` parameters. All tests run offline, in demo mode, against synthetic data. This page
says what runs where, how to run it, how to write a good test for each layer, how the database schema
is tested, and what CI does.

## Quick reference

| I want to... | Command (from the repository root) |
| --- | --- |
| Run everything | `make test` (pytest, then web typecheck and Vitest) |
| Run all Python tests | `python3 -m pytest -q` |
| Run one package or file | `python3 -m pytest packages/carbon-engine -q`, `python3 -m pytest apps/api/tests/test_api_demo.py -q` |
| Run tests matching a name | `python3 -m pytest -q -k "estimate and not report"` |
| Stop at the first failure, rerun failures | `python3 -m pytest -x`, `python3 -m pytest --lf` |
| Run the agent framework tests | `python3 -m pytest packages/agent-framework -q` |
| Run the QGIS plugin tests (no QGIS needed) | `python3 -m pytest integrations/qgis-plugin/tests -q` |
| Run the configuration checks only | `python3 -m pytest tests/data-quality -q` |
| Run the production gate | `ATLAS_ENV=production ATLAS_ALLOW_PENDING_PARAMETERS=false python3 -m pytest tests/data-quality -q` |
| Test the database schema | [Testing the PostgreSQL schema](#testing-the-postgresql-schema) |
| Run web unit tests once | `cd apps/web && npm run test -- --run` (without `--run` Vitest watches) |
| Run web tests with coverage | `cd apps/web && npm run test:coverage` |
| Run browser smoke tests | `cd apps/web && npm run build && npx playwright install chromium && npm run test:e2e` |
| Lint and type-check | `make lint` (ruff, mypy, ESLint) and `make typecheck` (web) |
| Format | `make format` (ruff format, Prettier) |

The root `pyproject.toml` sets `pythonpath` for the engines, `integrations` and `apps/api`, so pytest
finds them from a clean checkout. The API imports `carboncreditbuy_agents`, so install the agent framework as
well: `make install-api` does it, and so does `python3 -m pip install -e packages/agent-framework` if
your `Makefile` predates the framework. `testpaths` are `packages`, `apps/api/tests`, `integrations`
and `tests`. `--strict-markers` is on: a marker must be registered in `pyproject.toml` before you use
it. `asyncio_mode` is `auto`.

## Where tests live

| Location | What it covers |
| --- | --- |
| `packages/carbon-engine/tests/` | Allometric equations against hand-computed values, the parameter store, readiness and confidence, the Tier 1 and Tier 2 model, uncertainty, carbon by tree age, the production-safety check |
| `packages/geo-engine/tests/` | Polygon validation and measurement, indices and classes, climate zones, WorldCover class shares, STAC helpers and the cube |
| `packages/policy-engine/tests/` | Member-state resolution, every activity for every region, rule-matching semantics, status values, the tree-age rules engine |
| `packages/report-engine/tests/` | HTML, Markdown and JSON rendering, escaping, placeholders for missing blocks, report ids, and the clean refusal of PDF when WeasyPrint is missing |
| `packages/agent-framework/tests/` | The generic framework: agents, tools, blackboard, plans, guardrails, intent routing, the reasoner and redaction |
| `integrations/tests/` | Adapter base (retry, status mapping, cache, provenance) and the point and statistics adapters, over `httpx.MockTransport` |
| `integrations/qgis-plugin/tests/` | The QGIS plugin, against fakes of the QGIS API and a fake CarbonCreditBuy server |
| `apps/api/tests/` | The whole API in demo mode through `TestClient`: privacy, errors, API keys, body limits, tree age, imagery and agents |
| `tests/integration/` | Contract drift: the committed sample responses in `data/sample/responses/` against the field names the API produces now |
| `tests/data-quality/` | Configuration invariants (below), including the tree-age rules |
| `apps/web/src/**/*.test.ts(x)` | Vitest: pure logic, the API client and fallback, the UI store, and key components |
| `apps/web/e2e/` | Playwright smoke tests against the production preview build |
| `.github/scripts/` | The PostgreSQL schema tests (`postgres_smoke.py`, `schema_constraints.sql`) that CI runs against a real database |

Unit tests sit next to the code they test. The cross-package suites are `tests/integration` and
`tests/data-quality`.

## Principles

- **Offline and deterministic.** A test never calls the Internet. Adapters are tested with
  `httpx.MockTransport`; the API runs with the `Demo*` twins; any randomness is derived from the
  inputs. A test that needs a live endpoint does not belong in CI.
- **Synthetic data only.** Use the farms in [`examples/`](../../examples/README.md) or small hand-made
  polygons. Never commit a real farm boundary.
- **Test the invariants that protect users**, not only the arithmetic. For a carbon result:
  `low <= central <= high`, `unit == "tCO2e/yr"`, `certified is False`, a non-empty disclaimer, and
  every parameter that influenced the number listed in `parameters_used`.
- **Reference values come with their source.** Write the source and tolerance in the test, for example
  Chave et al. 2014 equation 4 with a wood density of 0.55 g/cm3, D = 20 cm and H = 10 m giving
  123.1 kg. Compute it by hand or from the paper, not by running your own code and pasting the output.
- **Privacy is tested.** No log record, error message or non-owner response may contain a coordinate
  pair; adapter errors must carry the host and status only (`test_errors_never_contain_coordinates`
  in [adding an integration](adding-an-integration.md#6-tests) is the pattern). An agent transcript
  must not contain the plot's coordinates either.
- **Policy output is checked as data.** Every program in a screening has references with URLs, and
  `status` is one of the six values. Every tree-age rule has a source link and an access date.
- **A bug fix starts with a failing test.**

## Python tests by layer

### Engines

Pure functions and classes, so tests are short and exact. The carbon-engine `conftest.py` provides
session-scoped `store` and `model` fixtures:

```python
def test_estimate_is_a_labeled_range(model):
    result = model.estimate(
        PlotInput(area_hectares=2.0),
        InventoryInput(species_id="mango", tree_count=300, plantation_year=2021),
        ClimateInput(zone="tropical_dry"),
        ModelParams(as_of_year=2026, allow_pending_parameters=True),
    )
    assert 0 < result.estimate.low <= result.estimate.central <= result.estimate.high
    assert result.estimate.unit == "tCO2e/yr" and result.certified is False
```

Remember that the engine allows pending parameters by default; pass `allow_pending_parameters=False`
when the test is about the gate.

### API

`apps/api/tests/conftest.py` builds the app with demo mode, rate limiting off and no API keys, and
exposes a **session-scoped** `client` (a `TestClient`) and a `square` polygon. The in-memory repository
is shared by the whole session, so a new test should create its own plot and must not assert on global
counts. The seeded demo plots (`PLT-DEMOIN`, `PLT-DEMOUS`, `PLT-DEMOEU`) are available. To test
API-key behavior, build a second app with `Settings(ATLAS_API_KEYS="k")` as the existing tests do.

```python
def test_unknown_plot_is_a_problem_document(client):
    response = client.get("/api/v1/plots/PLT-NOPE00")
    assert response.status_code == 404
    assert response.json()["type"].endswith("/plot-not-found")
```

Several tests validate responses against the JSON Schemas in `data/schemas/`. After an intended change
to a response shape, update the schema and the contract doc, then regenerate the sample responses with
`python3 scripts/make_sample_responses.py`; `tests/integration/test_contract_fixtures.py` fails on
accidental drift.

### Adapters

Use `integrations/tests/httpmock.py` (`make_client`, `json_response`, `Recorder`). The full pattern,
with the five tests every adapter needs, is in [adding an integration](adding-an-integration.md#6-tests).

### Agents

Agents are tested at two levels. The generic framework in `packages/agent-framework/tests/` needs no
CarbonCreditBuy code: its `conftest.py` puts the package on `sys.path`. CarbonCreditBuy agents are tested through the
API in `apps/api/tests/test_agents_api.py`, which runs the three plans on the demo plot
([adding a new agent](../agents/README.md#10-adding-a-new-agent) shows the steps). The invariants
to keep when you add or change an agent:

- the run is deterministic with the default template reasoner (two runs give the same transcript);
- every number in a message comes from an engine call, and ranges and the disclaimer are present;
- the three values (environmental benefit, indicative carbon value, other farm income) stay apart;
- the guardrails pass on the demo plot, and no message contains the plot's coordinates;
- a failing service becomes a warning step, and a specialist whose input is missing skips itself;
- an optional language model may only rephrase text, and the template text is kept when it fails.

### Data-quality tests and the production gate

`tests/data-quality/test_parameters.py` guards the configuration:

| Test | Guards |
| --- | --- |
| `test_every_species_parameter_is_cited` | Each cited species field has `value`, `source` and a valid status; each species has climate zones |
| `test_tier1_parameters_have_sources_and_valid_status` | Tier 1 constants cited; growth ranges bracket their value; carbon fraction 0.47 and 44/12 |
| `test_regions_and_policies_align` | Every region has a policy file and a price scenario in the same currency, ascending and positive |
| `test_policy_rules_reference_documents` | Every policy says "screening" in its disclaimer; every program has references with URLs; the last default is not `potentially_applicable` |
| `test_default_model_runs_for_every_species_and_zone` | The model produces a valid range for every species in every listed zone |
| `test_production_refuses_pending_parameters` | With `ATLAS_ENV=production`, a pending parameter raises `PendingParameterError`. Read [the notes on this test](adding-a-species-or-parameter.md#tests-and-the-production-gate) before you verify the last pending parameter |

`tests/data-quality/test_tree_age_rules.py` guards `config/tree-age/`: the schema and vocabulary of
every rule, an https source with an access date, a note on every `pending` rule, consistent geography,
and that the engine evaluates every rule at every age and setting. Its production gate withholds
`pending` rules instead of failing: see [adding a tree-age rule](adding-a-tree-age-rule.md).

## Testing the PostgreSQL schema

[`data/schemas/schema.sql`](../../data/schemas/schema.sql) and
[`apps/api/app/repositories/postgres.py`](../../apps/api/app/repositories/postgres.py) must agree:
the repository holds the SQL, the schema holds the tables, and nothing else ties them together. The
unit tests use the in-memory repository, so a mismatch would only show in production. Two scripts in
[`.github/scripts/`](../../.github/scripts/) close the gap, and CI runs both on every push in the job
`PostgreSQL schema (PostGIS 3.4)`.

| Script | What it proves |
| --- | --- |
| `postgres_smoke.py` | Every `PostgresRepository` method runs against the real tables: save and update a plot, the latest analysis wins, inventories, estimates, reports, generic records, the audit trail, and that deleting a plot cascades to everything derived from it |
| `schema_constraints.sql` | The database refuses what must never be stored: an estimate that says `certified: true`, an exact `public_centroid`, a stored public view, coordinates in an audit event (at any depth), a plot with an invalid or open polygon, an unknown estimate confidence, an orphan record. It also checks that harmless input is accepted, that deleting a plot keeps the audit trail, and what `plots_public` exposes. It runs in a transaction that is rolled back, so it leaves nothing behind |

To run them on your machine you need a PostgreSQL 15 or newer server with PostGIS 3 and a role that
may create extensions. The image `docker-compose.yml` uses works:

```bash
docker run -d --rm --name atlas-pg -p 5432:5432 \
  -e POSTGRES_USER=atlas -e POSTGRES_PASSWORD=atlas -e POSTGRES_DB=atlas postgis/postgis:16-3.4
export DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas

# apply the schema twice: the second run proves it is idempotent, which is how operators upgrade
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f data/schemas/schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f data/schemas/schema.sql

python3 .github/scripts/postgres_smoke.py
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f .github/scripts/schema_constraints.sql
docker stop atlas-pg
```

Both scripts write test rows, so use a scratch database. `postgres_smoke.py` needs `psycopg`, which
`requirements.txt` pins. A passing `schema_constraints.sql` prints one `ok` line per check and ends
with `every check passed`; a failure stops with a line that starts `FAIL` and exits non-zero.

When you change the schema or the repository:

1. Edit `schema.sql` so that it still works on an empty database **and** on a database created from an
   earlier revision. `CREATE TABLE IF NOT EXISTS` leaves an existing table alone, so a changed or new
   constraint also needs a guarded `ALTER TABLE` in the upgrade block at the end of the file. Bump the
   revision in the header and in the `schema_version` insert.
2. Add a check to `schema_constraints.sql` for every new constraint: one statement that must be
   rejected, and one near miss that must be accepted. A constraint with no test is a wish.
3. Add the new repository method to `postgres_smoke.py`.
4. Run both scripts on a fresh database **and** on one created from the previous revision (`git show
   <old commit>:data/schemas/schema.sql | psql ...`, then apply the new file twice). The results must
   be the same.
5. Update the [API contract](../architecture/api-contract.md) if a record changed, and tell operators
   in the release notes ([release process](release-process.md)).

The API does not create tables, and the in-memory repository does not enforce these constraints. A
mismatch that only a database can find is therefore the main reason these scripts exist. One known
gap is described in the "GEOMETRY CAVEAT" at the top of `schema.sql`: with `ATLAS_REPOSITORY=postgres`
a polygon with `z` values or an unclosed ring passes the API's validator but is rejected by the
database.

## Web tests

**Vitest** (config in `apps/web/vitest.config.ts`): jsdom, globals, the `@` alias, and a setup file
(`src/test/setup.ts`) that loads i18n, Testing Library matchers and polyfills for dialogs,
`matchMedia` and `ResizeObserver`. Tests match `src/**/*.test.{ts,tsx}`. Coverage is collected for
`features/**/logic`, `lib`, `services` and `store`. The suites cover:

- pure logic: units and formatting, the workspace model, the results logic that builds the explain
  payload, simulation parameters and the agents page logic;
- the API client and its offline fallback (`services/api.test.ts`) and the UI store;
- key components: the plot details panel, the result cards and the agent transcript components.

Write logic as a pure function in a `logic/` folder and test it without React, as the existing
features do. Components that only render need at most a render test. Prefer role and label queries
over copied text, and share fixtures from `src/test/fixtures.ts`.

**Playwright** (`apps/web/playwright.config.ts`): runs `e2e/smoke.spec.ts` in Chromium against
`npm run preview` on port 4173 (`PLAYWRIGHT_BASE_URL` overrides the base URL). It has two scenarios:
the landing page opens the workspace, and the workspace falls back to demo data and shows the offline
banner when every API call is aborted. Build first (`npm run build`) and install the browser once
(`npx playwright install chromium`). The suite is not part of CI. `tests/e2e/README.md` describes a
larger planned suite with a different layout; it does not match what exists, so follow this page and
the config file.

## QGIS plugin tests

The plugin tests need only `pytest`. They use fakes of the QGIS classes (`qgis_fakes.py`) and a fake
CarbonCreditBuy server (`qgis_plugin_fake_server.py`), so no QGIS installation is involved, and one smoke test
that needs PyQt5 is skipped when it is missing. Run them from the repository root so that
`pyproject.toml` supplies the pytest settings:
`python3 -m pytest integrations/qgis-plugin/tests -q`, or `make test` inside
`integrations/qgis-plugin/`. The plugin must keep working on Python 3.9 (QGIS 3.28 on Windows embeds
it), so its workflow tests 3.9 and 3.12 and its code avoids newer syntax (see its `ruff.toml`).

## What CI runs

| Workflow | Job | What it does |
| --- | --- | --- |
| `ci.yml` | `Python 3.12`, `Python 3.13` (ruff · mypy · pytest) | Installs as `make install-api` plus the agent framework, then `ruff check`, `ruff format --check`, `mypy`, one pytest run over every test path (QGIS plugin and agent framework included), the production data-quality gate, and a parameter-status summary on the run page |
| `ci.yml` | `PostgreSQL schema (PostGIS 3.4)` | Applies `schema.sql` twice, runs `postgres_smoke.py` and `schema_constraints.sql` |
| `ci.yml` | `Web (Node 22 · lint · typecheck · vitest · build)` | `npm ci`, typecheck, ESLint, Vitest once, production build |
| `ci.yml` | `Docker build (api · web)` | Builds both images (never pushed), starts them, checks `/api/v1/health`, `/healthz` and the CSP header |
| `qgis-plugin.yml` | `Plugin tests (Python 3.9, 3.12)`, `Package the plugin ZIP` | When the plugin changes: its tests, then a reproducible ZIP (built twice and compared byte for byte), a layout check and an artifact |
| `lint.yml` | Prettier and ESLint, ruff format, yamllint | Style gates |
| `security.yml` | CodeQL, pip-audit, npm audit, gitleaks, dependency review | Static analysis and dependency and secret scanning (also weekly); dependency review runs on pull requests |
| `docs.yml` | markdownlint, lychee | Markdown style and internal links (when Markdown changes); external links are advisory |

To reproduce the Python job locally:

```bash
python3 -m ruff check . && python3 -m ruff format --check .
python3 -m mypy packages apps/api/app integrations --ignore-missing-imports
python3 -m pytest -q
```

To check the documentation the way the Docs workflow does, run
`npx markdownlint-cli2 "**/*.md" "#node_modules"` from the repository root, and a link checker such as
`lychee --offline --config .lychee.toml './**/*.md'` if you have it installed. The offline check
verifies every relative link and every `#anchor`, so a renamed heading breaks the links that point at
it.

Note that `ruff format` in this repository also formats **Python code blocks inside Markdown files**.
If `ruff format --check` flags a `.md` file, run `python3 -m ruff format <file>`.

The branch-protection check names are listed in
[`infra/github/README.md`](../../infra/github/README.md); do not rename a job without updating that
list, and add a new required job there when you add one.

## Known gaps

- There are no adapter tests for Nominatim, Photon, WorldCover, Earth Search and Copernicus; the
  `geo_engine` helpers underneath them are tested. The geocoders are a good first contribution
  ([starter issue 13](../community/starter-issues.md#13-test-the-geocoder-adapters)); the other three
  need test inputs that nothing downloads and are in [roadmap ideas](../community/roadmap-ideas.md#data-and-adapters).
- Coverage is reported, not enforced.
- The browser smoke tests are not part of CI. Running them there, and building the larger suite, is in
  [roadmap ideas](../community/roadmap-ideas.md#tooling-infrastructure-and-documentation).
- `tests/README.md` mentions `respx`; the tests use `httpx.MockTransport`. It also says the production
  command above is expected to fail on the v0.1 configuration. It does not: the test asserts the
  refusal, and it passes while parameters are pending.

Next: [release process](release-process.md).
