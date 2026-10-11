# API (apps/api)

The FastAPI service behind CarbonCreditBuy. It validates and stores plots, asks the adapters for land cover,
vegetation, climate and soil, runs the deterministic engines, screens programmes, renders reports, turns files and
typed input into boundaries and trees, detects tree cover from satellite data, answers tree-age questions, lists
imagery providers and runs the agent team. It contains no carbon arithmetic and no policy rules of its own: those live
in [`packages/`](../../packages/) and [`config/`](../../config/).

Every carbon figure it returns is a scenario estimate with a low, central and high value, `certified: false`, a
confidence grade and a provenance chain. The interactive reference is served at `/docs` (Swagger UI), `/redoc` and
`/api/v1/openapi.json`; the written contract is [`docs/architecture/api-contract.md`](../../docs/architecture/api-contract.md),
including its "v0.2 implementation notes" where the code says more than the examples.

## Run it

```bash
make install                 # once: requirements, editable packages, web dependencies
make api                     # http://localhost:8000, auto-reload, demo mode by default
```

`make api` runs `uvicorn` from inside `apps/api`. The settings class reads a file called `.env` from the **current
directory**, so the repository-root `.env` is not picked up by that target. Either export the variables
(`set -a; . ./.env; set +a`) or run from the repository root, where the file is found:

```bash
python3 -m uvicorn app.main:app --app-dir apps/api --reload --port 8000
```

Docker: `make docker-up` builds and starts the API, the web app, PostGIS and MinIO
([setup guide](../../docs/developer-guide/setup.md)). The compose file passes the repository-root `.env` to the API
container.

In demo mode (`ATLAS_MODE=demo`, the default) nothing leaves the machine: every adapter has a deterministic twin, the
data is labelled `synthetic-demo`, and the three demo plots from [`data/sample/plots/`](../../data/sample/) are created
at start-up (`ATLAS_SEED_DEMO`). Set `ATLAS_MODE=live` to use the public APIs through the adapters in
[`integrations/`](../../integrations/README.md); the optional dependencies are the extras `live` (rasterio,
pystac-client), `postgres` (psycopg) and `pdf` (WeasyPrint) of `apps/api/pyproject.toml`, and `requirements.txt` pins
the first two.

## Layout

```text
apps/api/app/
  main.py              application factory: middleware, CORS, error handlers, the nine routers
  context.py           builds repository, adapters, engines and the core services once (AppContext)
  dependencies.py      FastAPI dependency that hands the AppContext to a route
  demo_seed.py         creates the three synthetic demo plots in demo mode
  core/                config.py (Settings), errors.py (RFC 7807), security.py (API keys),
                       middleware.py (headers, request ids, size limits), ratelimit.py, logging.py
  api/v1/routers/      meta, plots, simulate, geometry, imports, detection, tree_age, imagery, agents
                       (thin: validate, call a service, return a dictionary)
  schemas/             requests.py (core request models), geometry_requests.py, detection_requests.py,
                       tree_age.py (request models of the v0.2 endpoints); agents/schemas.py has its own
  services/            plots, analysis, cube, trees, carbon, policy, market, simulate, reports, explain,
                       regions, common, adapters (ModeRouter)
                       v0.2: geometry, imports, detection, tree_age, imagery, registry (lazy service cache)
  agents/              the domain layer over packages/agent-framework: catalog, plans, tools, the nine
                       agents, wording, schemas and service.py (what the router calls)
  repositories/        base.py (interface), memory.py, postgres.py
apps/api/tests/        conftest.py and eight test modules (285 tests)
```

Routers call services; services call engines, adapters and the repository. Three things are worth knowing before you
read the code:

- **`ModeRouter`** (`services/adapters.py`) is the only place that builds the adapters: it chooses a demo twin or a live
  adapter and passes the endpoints and keys from the settings.
- **`AppContext`** holds the core services. A feature module (imports, detection, tree age, imagery, agents) builds its
  own service on first use with `services.registry.service(ctx, name, factory)` and keeps it in `ctx.extras`, so
  adding a feature does not change `context.py`.
- **The agent team** wraps the services above as tools (`agents/tools.py`); it adds no calculation. How the framework
  works is explained in the [agents guide](../../docs/agents/README.md) and
  [ADR-0006](../../docs/architecture/adr/0006-agentic-framework.md).

## Endpoints (`/api/v1`)

43 operations. The *Key* column marks the mutating calls that need an `X-API-Key` header when `ATLAS_API_KEYS` is set;
everything else never asks for one (see [Security](#security)). *Status* is the success code.

### Configuration and place search

| Method and path | Purpose | Status | Key |
| --- | --- | --- | --- |
| `GET /health` | Liveness, version, mode, repository (`memory` or `postgres`) | 200 | |
| `GET /regions` | Supported regions and their programmes | 200 | |
| `GET /species` | Species table with parameter provenance; `?country=` filters | 200 | |
| `GET /methodologies` | Methodology registry (referenced, never applied) | 200 | |
| `GET /attribution` | Attribution strings for the web app and reports | 200 | |
| `GET /geocode` | Forward geocoding, server side; `?q=` required, `?country=` | 200 | |
| `GET /reverse-geocode` | Country, state and district for `?lat=&lon=` | 200 | |

### Plots and the assessment chain

| Method and path | Purpose | Status | Key |
| --- | --- | --- | --- |
| `POST /plots` | Create a plot from a GeoJSON polygon (`source` says how it was made) | 201 | yes |
| `GET /plots`, `GET /plots/{plot_id}` | List and fetch plots (exact geometry: the owner view) | 200 | |
| `GET /plots/{plot_id}/public` | Public view: generalised centroid, no geometry, no perimeter | 200 | |
| `DELETE /plots/{plot_id}` | Delete a plot and its linked records | 204 | yes |
| `POST /plots/{plot_id}/analyze` | Land cover, vegetation, climate, soil | 200 | yes |
| `GET /plots/{plot_id}/analysis`, `/vegetation` | Latest analysis, or its vegetation block | 200 | |
| `GET /plots/{plot_id}/cube` | Vegetation grid over time as JSON; `?index=` (`ndvi`, `ndmi` or `ndre`), `?months=` 6 to 72 (36) | 200 | |
| `POST /plots/{plot_id}/trees` | Record a tree inventory (a new version each time) | 201 | yes |
| `GET /plots/{plot_id}/trees` | Tree inventory versions | 200 | |
| `POST /plots/{plot_id}/carbon-estimate` | Carbon removal scenario (low, central, high) | 201 | yes |
| `GET /plots/{plot_id}/carbon-estimate` | Latest estimate | 200 | |
| `GET /plots/{plot_id}/policy-eligibility` | Programme screening, `?activity=` (never an eligibility decision) | 200 | |
| `GET /plots/{plot_id}/market-scenario` | Indicative value scenarios, `?estimate_id=` (never a quote) | 200 | |
| `POST /plots/{plot_id}/report` | Render a report: `html`, `markdown`, `json` or `pdf` | 201 | yes |
| `GET /reports/{report_id}` | Fetch a rendered report | 200 | |
| `POST /simulate` | What-if simulation for a country, species and tree count | 200 | |
| `POST /explain` | Plain-language explanation from derived indicators only | 200 | |

### Boundaries and files (v0.2)

| Method and path | Purpose | Status | Key |
| --- | --- | --- | --- |
| `POST /geometry/from-point` | Pin plus size (ha, ac or m2) becomes a square or circle polygon | 200 | |
| `POST /geometry/from-line` | A drawn tree line (bund, boundary, roadside) becomes a strip polygon and a tree count | 200 | |
| `POST /geometry/parse-coordinates` | Typed or pasted points (decimal, N/S/E/W letters, DMS) become a polygon | 200 | |
| `POST /imports` | Multipart upload of GeoJSON, KML, KMZ, CSV, LAS or LAZ; the file is read and dropped | 201 | yes |
| `GET /imports` | Imports, newest first, without the map preview; `?plot_id=` | 200 | |
| `GET /imports/{import_id}` | One import with its map preview | 200 | |
| `DELETE /imports/{import_id}` | Delete an import record | 204 | yes |
| `POST /plots/{plot_id}/detect` | Detect tree cover from the NDVI cube; body `{target, min_confidence}` is optional | 200 | yes |
| `GET /plots/{plot_id}/detections` | Latest detection of the plot (404 until one has run) | 200 | |

The three geometry calls and `POST /tree-age/assess` compute and store nothing, which is why they are not 201. An
import can create an import record linked to a plot; the web app turns a boundary into a plot with `POST /plots`.

### Tree age and imagery (v0.2)

| Method and path | Purpose | Status | Key |
| --- | --- | --- | --- |
| `GET /tree-age/rules` | Rules that treat trees differently by age; `?country=`, `?subdivision=` | 200 | |
| `POST /tree-age/assess` | Carbon held by trees of an age, the age curve and the rules that apply there | 200 | |
| `GET /imagery/providers` | Imagery providers with licence and attribution; `?country=` puts covering ones first | 200 | |

### Agents (v0.2)

| Method and path | Purpose | Status | Key |
| --- | --- | --- | --- |
| `GET /agents` | The team: roles, tools, blackboard keys and plans | 200 | |
| `POST /plots/{plot_id}/agents/run` | Run a plan (`full-assessment`, `quick-estimate`, `tree-age-check`) and store the transcript | 201 | yes |
| `POST /agents/ask` | A question about a plot (`plot_id` required); a keyword router picks the plan | 201 | yes |
| `GET /agents/runs` | Stored runs, newest first, as summaries (up to 50); `?plot_id=` | 200 | |
| `GET /agents/runs/{run_id}` | One stored run with the whole transcript | 200 | |

Typical flows, with ready-made requests in [`examples/`](../../examples/README.md):

1. **Assess a plot:** create a plot, analyze it, record trees, request a carbon estimate, read the policy screening
   and the market scenario, generate a report.
2. **Start from what you have:** `POST /geometry/from-point` (a pin and a size), `POST /geometry/from-line` (a row of
   trees) or `POST /imports` (a boundary or tree file), then `POST /plots` with the polygon that came back.
3. **Count trees from space or from a scan:** `POST /plots/{plot_id}/detect` for satellite tree cover, or
   `POST /imports` with a LAS or LAZ file for individual tree tops.
4. **Ask the team:** `POST /plots/{plot_id}/agents/run`, or `POST /agents/ask` with a question such as "How much
   carbon if I add 200 trees?".

## Services

| Service | What it does | Calls |
| --- | --- | --- |
| `PlotService` | Validates and measures polygons, resolves the country, builds the owner and public views | geo-engine |
| `AnalysisService`, `CubeService` | Land cover, vegetation indices, climate zone, soil and the vegetation cube | adapters, geo-engine |
| `TreeService` | Inventory versions; every measurement has a source | species table |
| `CarbonService` | Wraps the carbon engine and adds API-level provenance; refuses `pending` parameters in production | carbon-engine |
| `PolicyService`, `MarketService` | Programme screening and indicative value scenarios | policy-engine, `config/market` |
| `SimulationService` | The what-if for `POST /simulate` | carbon, market and policy services |
| `ReportService` | Assembles and renders the report | report-engine |
| `ExplainService` | Template text from derived indicators (see the settings table for `llm`) | none |
| `GeometryService` | Pin and size, tree line and typed coordinates | geo-engine `construct`, `coordinates` |
| `ImportService` | Reads an upload, derives boundary, trees or crowns, optionally runs point-cloud detection | geo-engine `imports`, `pointcloud` |
| `DetectionService` | Tree cover from the cube, using `config/detection.yaml` | geo-engine `detection` |
| `TreeAgeService` | Carbon by age and the tree-age rules; reads only the climate zone of a plot | carbon-engine `age`, policy-engine `tree_age` |
| `ImageryService` | Serves `config/imagery/providers.yaml` with keys filled in from the environment | none |
| `AgentService` | Runs plans, applies the guardrails, stores transcripts | the services above, through tools |

## Repositories

`repositories/base.py` is the persistence boundary. Records are plain JSON-serialisable dictionaries that match the
schemas in [`data/schemas/`](../../data/schemas/).

- **Typed methods** for plots, the latest analysis, tree inventories, carbon estimates and reports, plus an `audit`
  log (event, plot id and counts, never coordinates).
- **Generic records** for feature modules: `save_record(kind, record_id, record, plot_id)`, `get_record`,
  `list_records(kind, plot_id, limit)` (newest first) and `delete_record`. A feature stores its JSON document without a
  new table. Kinds in use: `import` (imports), `detection` (the five newest per plot are kept) and `agent-run` (agent
  transcripts). `plot_id` links a record to a plot, and deleting the plot deletes the record.
- **`MemoryRepository`** (`ATLAS_REPOSITORY=memory`, the default) is thread safe and loses its data on restart. It is
  the right choice for demo mode, tests and a first look.
- **`PostgresRepository`** (`ATLAS_REPOSITORY=postgres`) stores the same records as JSONB in PostgreSQL with PostGIS;
  apply [`data/schemas/schema.sql`](../../data/schemas/schema.sql) first (the compose file does). Generic records live in
  one `records` table.

## Configuration

All settings are environment variables read by `app/core/config.py`; [`.env.example`](../../.env.example) lists them
with comments. Names and defaults:

### Runtime and limits

| Variable | Default | Effect |
| --- | --- | --- |
| `ATLAS_MODE` | `demo` | `demo`: offline, synthetic data labelled `synthetic-demo`. `live`: public APIs through the adapters |
| `ATLAS_ENV` | `development` | `production` refuses `pending` parameters whatever the next setting says |
| `ATLAS_ALLOW_PENDING_PARAMETERS` | `true` | Honoured outside production only; when false, an estimate that needs a `pending` parameter fails with 409 |
| `ATLAS_API_KEYS` | empty | Comma-separated keys; when set, mutating endpoints need `X-API-Key` |
| `ATLAS_RATE_LIMIT`, `ATLAS_RATE_LIMIT_ENABLED` | `60/minute`, `true` | Per client: API-key prefix, else remote address |
| `ATLAS_MAX_PLOT_VERTICES`, `ATLAS_MAX_PLOT_AREA_HA` | 500, 10000 | Plot limits, enforced by the geometry validation |
| `ATLAS_MAX_BODY_BYTES` | 1000000 | JSON body limit (the `Content-Length` header) |
| `ATLAS_MAX_UPLOAD_MB` | 50 | Limit for `POST /imports` |
| `ATLAS_CORS_ORIGINS` | local dev origins | Allowed browser origins, comma-separated |
| `ATLAS_SEED_DEMO` | `true` | In demo mode, create the three demo plots at start-up |
| `ATLAS_CONFIG_DIR` | repository `config/` | Another configuration directory (the Docker image sets `/app/config`); not in `.env.example` |
| `ATLAS_LOG_LEVEL`, `ATLAS_API_HOST`, `ATLAS_API_PORT` | `info`, `0.0.0.0`, `8000` | Logging; host and port are used by `make api` and the Docker image |
| `ATLAS_CACHE_DIR`, `ATLAS_REPORTS_DIR` | `.cache`, `.reports` | Read by the settings class but not used yet: reports are kept by the repository and the adapter cache is in memory |

### Storage, adapters and imagery

| Variable | Default | Effect |
| --- | --- | --- |
| `ATLAS_REPOSITORY` | `memory` | `memory` or `postgres` |
| `DATABASE_URL` | `postgresql://atlas:atlas@localhost:5432/atlas` | Used with the postgres repository |
| `ATLAS_STAC_PROVIDER`, `EARTH_SEARCH_STAC_URL`, `COPERNICUS_STAC_URL`, `COPERNICUS_TOKEN` | `earth-search`, URLs, empty | Sentinel-2 catalogue |
| `ESA_WORLDCOVER_BASE_URL`, `ESA_WORLDCOVER_VERSION` | URL, `v200` | Land cover |
| `OPEN_METEO_ARCHIVE_URL`, `OPEN_METEO_ELEVATION_URL`, `SOILGRIDS_URL`, `MAX_CLOUD_COVER_PCT` | URLs, 20 | Climate, elevation, soil, scene filter |
| `ATLAS_GEOCODER`, `NOMINATIM_URL`, `NOMINATIM_USER_AGENT`, `PHOTON_URL`, `GEOCODER_MIN_INTERVAL_SECONDS` | `nominatim`, URLs, empty, 1.0 | Geocoding; in live mode set a real contact in `NOMINATIM_USER_AGENT`, the adapter refuses the placeholder |
| `USDA_NASS_*`, `CENSUS_GEOCODER_URL`, `DATA_GOV_IN_*` | URLs, empty keys | Regional statistics adapters (built by `ModeRouter`; no endpoint calls them yet) |
| `ESRI_API_KEY` | empty | Fills `${ESRI_API_KEY}` in the Esri tile URL of `GET /imagery/providers`; the key reaches the browser, so use a referrer-restricted, basemap-only key. Other `${..._KEY}` or `${..._TOKEN}` placeholders in the providers file are read from the process environment, except names the application uses for something else |

### Agents and explanations

| Variable | Default | Effect |
| --- | --- | --- |
| `ATLAS_AGENT_REASONER` | `template` | `llm` lets an OpenAI-compatible model rephrase agent sentences; it needs `LLM_API_BASE_URL` and `LLM_MODEL`, otherwise the templates stay in use |
| `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS` | empty, empty, empty, 20 | The optional model endpoint. It receives redacted facts, never coordinates and never numbers to compute with |
| `ATLAS_EXPLAIN_PROVIDER` | `template` | `llm` is reserved: no model client is attached to `POST /explain`, so the answer is always the template and says `provider: "template"` |

Endpoint URLs and keys for the adapters are described in
[`docs/data-sources/FREE_APIS.md`](../../docs/data-sources/FREE_APIS.md); the imagery providers, their licences and
their key handling in [`integrations/imagery/`](../../integrations/imagery/README.md).

## Errors

Errors are RFC 7807 `application/problem+json` with `type` (`https://carboncreditbuy.org/problems/<slug>`), `title`,
`status`, `detail` and `instance`. Validation failures add an `errors` list of `{field, message}`; some problems add a
machine-readable `code`. Every response carries an `X-Request-ID` (the caller's, or a generated one). The slugs:

| Status | Slugs |
| --- | --- |
| 401, 403 | `api-key-required`, `api-key-invalid` |
| 404 | `plot-not-found`, `report-not-found`, `import-not-found`, `detection-not-found`, `agent-run-not-found`, `inventory-missing`, `estimate-missing` |
| 409 | `pending-parameters` (production, or pending values not allowed) |
| 413 | `payload-too-large` |
| 415 | `unsupported-file-type` (`code`: `unsupported_extension`, `signature_mismatch`, or a missing optional reader: `e57_unsupported`, `xml_backend_missing`, `laz_backend_missing`) |
| 422 | `validation-error`, `invalid-geometry`, `invalid-file`, `detection-failed`, `plot-required`, `unsupported-country`, `country-unresolved`, `unsupported-activity`, `unknown-species`, `unknown-climate-zone`, `invalid-subdivision`, `unknown-subdivision`, `carbon-engine-error` |
| 429 | `rate-limited` (with `Retry-After`) |
| 500 | `import-failed`, `config-error`, `tree-age-rules-unavailable`, `imagery-providers-unavailable`, and a generic `internal-server-error` that never shows a stack trace |
| 501 | `model-not-implemented`, `pdf-unavailable`, `dependency-missing` |
| 502 | `upstream-unavailable` |

[`api-contract.md`](../../docs/architecture/api-contract.md#v02-implementation-notes) explains the `code` values and
when each slug appears.

## Security

- **API keys.** With `ATLAS_API_KEYS` unset, nothing asks for a key: that is the demo and single-user setting. With
  keys set, the mutating endpoints (the *Key* column) answer 401 without an `X-API-Key` header and 403 with a wrong one;
  keys are compared in constant time. Reads and the stateless endpoints (`/simulate`, `/explain`, `/geometry/*`,
  `/tree-age/assess`) never need a key.
- **Rate limiting.** `slowapi`, 60 requests a minute by default for every route. The client is `key:` plus the first 8
  characters of the API key, or the remote address when there is no key; a 429 problem response carries
  `Retry-After: 60`. `ATLAS_RATE_LIMIT_ENABLED=false` switches it off (the tests do).
- **Body and upload limits.** A JSON body above `ATLAS_MAX_BODY_BYTES` is refused with 413 when its `Content-Length`
  says so; a chunked body without that header is not cut off by this check. `POST /imports` has its own limit,
  `ATLAS_MAX_UPLOAD_MB`, checked three times: the `Content-Length`, the request stream while the form is parsed, and
  the file read in 1 MiB chunks. Uploads are also checked for extension and signature, KML and KMZ are parsed with
  `defusedxml`, and the raw file is never stored.
- **CORS.** Only the origins in `ATLAS_CORS_ORIGINS`; methods `GET`, `POST`, `DELETE`, `OPTIONS`; headers
  `Content-Type`, `X-API-Key`, `X-Request-ID`; no credentials.
- **Headers.** Every response has `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, a `Permissions-Policy` that turns geolocation, camera and microphone off, and
  `Cache-Control: no-store`. The Content-Security-Policy is `default-src 'none'; frame-ancestors 'none'` for the API,
  one that allows the Swagger and ReDoc assets for `/docs`, `/redoc` and the OpenAPI file, and a third for
  `/reports/…` (inline styles, Google Fonts, embeddable by the web app's sandboxed frame, `X-Frame-Options:
  SAMEORIGIN`).
- **Privacy.** The access log records the method, the path (never the query string), the status and the duration. A
  logging filter replaces anything that looks like a coordinate pair or a GeoJSON geometry as a second line of
  defence. `GET /plots/{id}/public` returns the generalised centroid (0.05 degree grid) only; reports carry the public
  centroid and the perimeter, not the boundary. `POST /explain` rejects location-like keys (`lat`, `lon`, `geometry`,
  `coordinates`, `polygon`, `bbox`, `centroid`, `address`, `owner`, `name`, `email`, `phone`). The agent team never
  receives coordinates, a guardrail searches every message for the plot's own numbers, and the questions stored with a
  run have coordinate-like text removed. A detection or import record holds derived shapes and counts, not the file.

Limits you should know about: the service is single-tenant, and `ATLAS_API_KEYS` protects only the mutating endpoints.
`GET /plots`, `/plots/{id}`, `/plots/{id}/cube`, `/imports/{id}` and `/reports/{id}` return data without a key, so do
not expose a deployment that holds real farm boundaries to the public Internet without a gateway in front. See the
[threat model](../../docs/privacy/threat-model.md).

## Known limits

- **Reports and plot deletion.** With the PostgreSQL repository, deleting a plot deletes its reports (a foreign key
  cascades). With the memory repository the plot's reports stay retrievable by id until the process restarts.
- **PostgreSQL and client geometry.** `PlotService.create` keeps the polygon as the client sent it. The validation
  accepts z-values and an open ring (it repairs its own copy), the memory repository answers 201, but the PostGIS
  column refuses the raw input and the call ends in a 500 (see the geometry caveat at the top of `schema.sql`). Send
  closed, two-dimensional rings.
- **Detection is a heuristic.** The cube is a 30 m grid, so detected patches are groups of trees; `limitations` in the
  response says so. Individual trees come only from point clouds.
- **Adapters without a caller.** `usda_nass`, `census_geocoder` and `data_gov_in` are built by `ModeRouter`, but no
  service uses them yet.

## Tests

```bash
python3 -m pytest apps/api -q        # 285 tests, no network
```

Every module runs the application in demo mode through `TestClient`; `tests/conftest.py` switches rate limiting off.

| Module | Covers |
| --- | --- |
| `test_api_demo.py` | Health, configuration endpoints, geocoding, the seeded plots and the private-field rules, the cube, the plot-to-report flow, problem+json errors, simulation, the explain boundary, headers, API keys, the body limit |
| `test_geometry_api.py` | Pin and size, tree line and typed coordinates: units and shapes, widths and spacing, mixed formats, hemisphere letters, swapped order, limits, nothing logged or echoed |
| `test_imports_api.py` | GeoJSON, KML, KMZ, CSV, LAS and LAZ: boundaries, tree points, crowns, `min_confidence`, point-cloud detection, signatures, unsafe XML and KMZ, upload limits (also chunked), deletion with the plot, no file stored |
| `test_detection_api.py` | Tree-cover detection: shape, parameters, provenance, honest limitations, `min_confidence`, the five newest kept, deletion with the plot, nothing logged |
| `test_tree_age_api.py` | Rules and assessment: contract shape, determinism, the girth path, age 0, per-country rules, subdivisions, a plot supplying only its climate zone, withheld rules and the production 409 |
| `test_imagery_api.py` | Providers: contract fields, recommended provider, coverage ordering, key substitution and encoding, `available` without a key, reserved variable names, the key never logged |
| `test_agents_api.py` | Catalog, the three plans, `ask` (also in Hindi and German), stored runs, determinism, guardrails, no coordinates in any message, failing steps, API keys, the optional LLM rephrasing |
| `test_agents_docs.py` | The agent docs: every agent, tool and blackboard key is documented and the links resolve |

The engines have their own suites under `packages/*/tests`; contract checks across packages are in
[`tests/integration/`](../../tests/integration/).

## Design notes

- Demo mode is a first-class mode, not a mock: the same code path runs with deterministic twins, so the web app and
  the tests work without network access.
- Services return plain dictionaries that match the JSON schemas in [`data/schemas/`](../../data/schemas/); the
  repositories store them as JSON records.
- Add behaviour in an engine or in configuration first, then expose it here. An endpoint that needs a number asks an
  engine; it never computes one.

## Links

- [Developer guide](../../docs/developer-guide/README.md) and [architecture tour](../../docs/developer-guide/architecture-tour.md)
- [System architecture](../../docs/architecture/system-architecture.md) and [data flow](../../docs/architecture/data-flow.md)
- [Imports and detection](../../docs/architecture/imports-and-detection.md) and [tree-age model](../../docs/architecture/tree-age-model.md)
- [Privacy design](../../docs/privacy/privacy-design.md)
- [Web app README](../web/README.md)
