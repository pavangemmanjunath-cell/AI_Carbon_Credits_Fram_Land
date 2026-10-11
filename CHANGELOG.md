# Changelog

All notable changes to CarbonCreditBuy are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Until 1.0.0 the public API (`/api/v1`) may change between minor versions;
every change is recorded under **Changed** with a migration note.

Entries that alter a carbon parameter, an allometric equation or a policy
rule name the configuration file, the source document and the reviewer who
set `verification_status: verified`.

## [Unreleased]

Nothing yet.

## [0.2.0] — 2026-10-05

A development release, not a production release. Version 0.2.0 adds an AI agent team, simpler ways to mark land,
imports with tree detection, tree age, imagery providers for the Satellite view and a QGIS plugin, and it removes every
3D view. Every carbon figure is still a scenario estimate with `certified: false`, and production mode still refuses an
estimate that uses a `pending` parameter. Pending in this release:

- [`config/methodologies/ipcc-2006-tier1.yaml`](config/methodologies/ipcc-2006-tier1.yaml): the root-to-shoot ratios
  (IPCC 2006 Table 4.4), the above-ground growth values (Tables 4.10 and 4.12) and the temperate-generic allometry.
- [`config/species/species.yaml`](config/species/species.yaml): 11 wood densities and 3 increment multipliers (teak,
  eucalyptus and poplar).
- [`config/market/carbon-price-scenarios.yaml`](config/market/carbon-price-scenarios.yaml): the three regional price
  scenarios.
- [`config/tree-age/rules.yaml`](config/tree-age/rules.yaml): three rules, which production mode withholds:
  `in-hr-pran-vayu-devta-pension`, `in-mh-heritage-tree` and `eu-crcf-carbon-farming-delegated-act-2026`.

### Added

- **AI agent team.** A small in-house framework, `packages/agent-framework` (`carboncreditbuy_agents`), and nine agents in
  `apps/api/app/agents`: `coordinator`, `land`, `imagery`, `trees`, `carbon`, `policy`, `market`, `review` and
  `report`. Three plans (`full-assessment`, `quick-estimate`, `tree-age-check`) and the endpoints `GET /agents`,
  `POST /plots/{plot_id}/agents/run`, `POST /agents/ask`, `GET /agents/runs` and `GET /agents/runs/{run_id}`. Agents call
  the engines, so every number comes from an engine, and guardrails check each run. They are deterministic by default;
  a language model is optional (`ATLAS_AGENT_REASONER=llm`) and may only reword sentences.
  See the [agents guide](docs/agents/README.md), the [catalog](docs/agents/catalog.md) and
  [ADR-0006](docs/architecture/adr/0006-agentic-framework.md).
- **Simpler ways to mark land.** `POST /geometry/from-point` (a pin and a size), `POST /geometry/from-line` (a tree line
  with a width and a spacing) and `POST /geometry/parse-coordinates` (typed coordinates, degrees-minutes-seconds
  included) are pure calculations that store nothing. `POST /plots` accepts `source` and `boundary_quality`; a boundary
  built from a pin or a tree line is `approximate`, and the map draws it with a dashed outline.
- **Import data.** `POST /imports`, `GET /imports`, `GET /imports/{import_id}` and `DELETE /imports/{import_id}` read
  GeoJSON, KML, KMZ, CSV, LAS and LAZ files (E57 only where the optional `pye57` package is installed). The raw file is
  read in memory and dropped; only a derived record is stored: a boundary, tree counts and heights, and a map preview.
  The limit is `ATLAS_MAX_UPLOAD_MB` (50 by default). The web app has an Import data dialog in the header and a Data page.
  Synthetic sample files are in [`data/sample/imports/`](data/sample/imports/README.md).
- **AI detected tree cover.** `POST /plots/{plot_id}/detect` and `GET /plots/{plot_id}/detections` find patches of dense
  green vegetation in the vegetation cube, each with a heuristic confidence, and every result lists its limitations.
  Tree tops come from LAS and LAZ point clouds through a canopy height model. All parameters are in
  [`config/detection.yaml`](config/detection.yaml) (version 0.1.0), and every tunable number is an `assumption`. See
  [imports and detection](docs/architecture/imports-and-detection.md).
- **Tree age.** `GET /tree-age/rules` and `POST /tree-age/assess`. `carbon_engine.age` estimates carbon by tree age
  (Tier 1) or by trunk girth (Tier 2, Chave et al. 2014 equation 4) with a curve by age, and `policy_engine.tree_age`
  applies the rules. [`config/tree-age/rules.yaml`](config/tree-age/rules.yaml) holds 22 rules (19 `verified`, which
  means the source was opened and states the condition, and 3 `pending`), and `config/tree-age/subdivisions.yaml` lists
  the ISO 3166-2 states, union territories and Länder (India, the United States and Germany) that a rule can name. The
  sources are in [tree age, carbon credits and the law](docs/research/tree-age-carbon-rules.md); the model is in
  [tree-age-model.md](docs/architecture/tree-age-model.md). The web app has a Tree age page.
- **Imagery providers.** [`config/imagery/providers.yaml`](config/imagery/providers.yaml) (version 0.1.0) lists eight
  providers: Esri World Imagery, USGS Imagery Only, IGN France, IGN Spain (PNOA), PDOK Luchtfoto and the EOX Sentinel-2
  cloudless mosaics of 2016, 2017 and 2025. Each has its licence, attribution, key requirement, coverage, `max_zoom` and
  whether automated analysis is allowed. `GET /imagery/providers?country=XX` serves them, names the recommended one in
  `recommended`, and returns a provider whose key is missing with `available: false`. Esri needs `ESRI_API_KEY`.
  The web image allows the provider hosts by default (`ATLAS_EXTRA_IMG_SRC` and `ATLAS_EXTRA_CONNECT_SRC`). See
  [`integrations/imagery`](integrations/imagery/README.md) and [imagery providers](docs/research/imagery-providers.md).
- **QGIS plugin.** [`integrations/qgis-plugin`](integrations/qgis-plugin/README.md) (version 0.1.0, experimental,
  GPL-2.0-or-later, QGIS 3.28 or newer). It sends a selected field polygon, counts the tree crowns of a segmentation
  layer inside it, and shows a scenario estimate and the agent team's assessment. `make qgis-plugin` builds the ZIP,
  and the `QGIS plugin` workflow tests it on Python 3.9 and 3.12.
- **Database.** `data/schemas/schema.sql` revision 0.2.0 adds a generic `records` table for imports, detections and
  agent runs, which is deleted with its plot.
- **Samples and tests.** `scripts/make_sample_tree_age.py` and `scripts/make_sample_imports.py` (both with `--check`)
  join `make_sample_responses.py`, and `make samples` runs them all and refreshes the web demo fixtures.
  `make agents-demo` runs the agent team from the command line. The suites hold 2,184 Python tests, 459 web unit tests
  and 4 Playwright smoke tests.
- **Documentation.** A new user guide, the agents guide and catalog, the architecture pages for imports and detection
  and for tree age, the research notes under [`docs/research/`](docs/research/imagery-providers.md), the
  [free APIs](docs/data-sources/FREE_APIS.md) page, ADR-0006, new developer-guide pages, READMEs for the apps, packages,
  integrations and tests, and a rewritten [documentation index](docs/README.md).

### Changed

- **The web app is flat 2D and simpler.** The left navigation is My land, Data, AI agents, Tree age, Simulation, Reports
  and Settings. The plot list moved to the Data page. The Satellite view is a Map | Satellite switch that uses the
  imagery provider recommended for the country, or the one chosen in Settings; `VITE_SATELLITE_TILES_URL` still
  overrides it. The vegetation cube is drawn as a flat NDVI layer. The map has two new layers, "Tree cover (AI
  detected)" and "Imported trees".
  *Migration:* saved settings (`carboncreditbuy-ui` in the browser, store version 2) are migrated on first load: the old
  `cube3d` and `drawMode` fields are dropped and the old satellite layer flag becomes the Map | Satellite switch.
  `/app/cube` and `/app/plots/:id/cube` redirect to the results page.
- **`POST /plots` takes two new optional fields**, `source` (`manual-drawing`, `upload`, `import`, `pin-and-area`,
  `tree-line`, `coordinates`, `qgis-plugin` or `api`) and `boundary_quality` (`exact`, the default, or `approximate`),
  and the plot echoes both. *Migration:* none for clients; every other endpoint of 0.1 is unchanged.
- **The PostgreSQL schema is revision 0.2.0.** *Migration:* apply the file again before you start the new API:
  `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/schemas/schema.sql`. It is idempotent and upgrades a revision 0.1
  database inside one transaction. `plots_source_known` is replaced by `plots_source_format` so that the new plot
  sources are accepted, `reports_format_known` by `reports_format_token`, and three constraints are new (see
  **Security**). If an existing row breaks a new constraint, the whole upgrade rolls back and the error names it. The 0.1
  tables `plot_analyses`, `tree_inventories`, `agent_runs` and `audit_log` are no longer used and are not touched.
- **New settings:** `ATLAS_MAX_UPLOAD_MB`, `ATLAS_AGENT_REASONER`, `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`,
  `LLM_TIMEOUT_SECONDS` and `ESRI_API_KEY`, all in [`.env.example`](.env.example). `VITE_TERRAIN_TILES_URL` is no longer
  read.

### Removed

- All 3D views: three.js, `@react-three/fiber`, `@react-three/drei` and `@deck.gl/*` are gone from `apps/web`, together
  with the 4D cube view, the 3D columns toggle, and the map tilt and terrain control. The map is flat and north-up.
- In-browser SQL. An early design proposed DuckDB-WASM, and it was never added: the cube stays plain JSON
  ([ADR-0002](docs/architecture/adr/0002-json-cube-no-duckdb.md)).

### Security

- **Uploads.** The size limit is enforced three times: before the body is read, while the multipart stream is counted,
  and while the file is read in chunks. Only listed extensions are accepted, and the first bytes must fit the
  extension. KML and KMZ are parsed with `defusedxml`, a document with a DOCTYPE or an entity declaration is refused,
  and a KMZ may hold at most 100 entries and expand to at most 50 MB. A point cloud that declares more than 300 million
  points is refused before it is decoded. Error messages are written by the code and never repeat file content or
  coordinates.
- **Agents and language models.** Coordinates never reach a model: questions are redacted, tool inputs and outputs are
  summaries, and a model's answer is dropped if it changes a number. Guardrails check every run, among them
  `not-a-credit` and `no-coordinates`.
- **Database.** `carbon_estimates_record_not_certified` refuses `certified` with any value but false; the 0.1 constraint
  refused only the boolean `true` and let it through when a registry serial was present. `plots_record_private` and
  `plots_public_centroid_coarse` are new, and `audit_events_detail_no_location` now looks at every depth of the JSON.
- **Imagery keys.** A key is read from the environment and never committed, and a provider without its key is listed as
  unavailable and returned without a URL. The application's other secrets, such as `LLM_API_KEY`, cannot be filled into
  a tile URL. The Esri key reaches the browser inside the tile URL, so use a referrer-restricted, basemap-only key.

## 0.1.0 — not released on its own

The first scaffold of the repository, the base that 0.2.0 builds on. It was not published as a release of its own.

### Added

- Repository scaffold: `apps/api` (FastAPI), `apps/web` (Vite + React 19 +
  TypeScript), `packages/{carbon-engine,geo-engine,policy-engine,report-engine}`,
  `integrations/`, `config/` and `data/schemas/`.
- API contract `/api/v1` ([docs/architecture/api-contract.md](docs/architecture/api-contract.md)).
- Region configuration for `IN`, `US`, `EU`; species table v0.1; IPCC 2006
  Tier 1 parameter set v0.1 (all growth parameters `pending` or
  `assumption`); methodology registry; illustrative carbon-price scenarios.
- Policy screening rules for the Green Credit Programme, CCTS, state
  agroforestry incentives (IN); COMET-Farm, voluntary ARR/ALM
  methodologies, NRCS EQIP/CSP (US); CRCF, CAP eco-schemes, voluntary
  standards (EU).
- Documentation set under `docs/` (architecture, concepts, privacy,
  licensing, regions, user guide, developer guide), community files,
  GitHub workflows and issue templates, Docker images, example requests for
  three synthetic farms, research and validation plans.

### Security

- Content Security Policy and security headers in the web image
  ([infra/docker/nginx.conf](infra/docker/nginx.conf)); non-root API
  container; CodeQL, `pip-audit`, `npm audit` and gitleaks in CI.

[Unreleased]: https://github.com/<org>/carboncreditbuy/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/<org>/carboncreditbuy/releases/tag/v0.2.0
