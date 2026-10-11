# Setup

How to get CarbonCreditBuy running on your machine, in demo mode first and then in live mode, with
PostgreSQL, or in Docker. When something does not work, go to [troubleshooting](troubleshooting.md).

## Prerequisites

| Tool | Version | Needed for |
| --- | --- | --- |
| Python | 3.12 or newer (CI tests 3.12 and 3.13) | API, engines, adapters, agent framework |
| Node.js and npm | Node 22 or newer | Web app |
| make | any | The shortcuts in the `Makefile` |
| git | any | Cloning and contributing |
| Docker with Compose v2 | optional | `make docker-up`, PostGIS and MinIO, the schema tests |
| `psql` | optional | Applying the database schema yourself |
| Pango and Cairo system libraries | optional | PDF reports through WeasyPrint |
| QGIS 3.28 or newer | optional | Trying the QGIS plugin. Its tests do not need QGIS, and it supports Python 3.9 |

## 1. Install

```bash
git clone https://github.com/<org>/carboncreditbuy.git    # replace <org> with the organization
cd carboncreditbuy
python3 -m venv .venv && . .venv/bin/activate              # recommended
make install
```

`make install` runs two things:

- `install-api`: `python3 -m pip install -r requirements.txt` (pinned versions), then editable installs
  of `packages/carbon-engine`, `packages/geo-engine`, `packages/policy-engine`,
  `packages/report-engine`, `integrations` and `apps/api`.
- `install-web`: `cd apps/web && npm install`. For a reproducible install that matches CI, use
  `cd apps/web && npm ci` instead.

The API imports the agent framework, which is a seventh editable package. If the `install-api` target
in your `Makefile` does not list it yet, install it yourself, or the API and its tests fail with
`ModuleNotFoundError: carboncreditbuy_agents`:

```bash
python3 -m pip install -e packages/agent-framework
```

Heavy geospatial dependencies (`rasterio`, `pystac-client`) are in `requirements.txt`, but the code
imports them lazily, so demo mode does not exercise them. The same goes for `psycopg`, which is used
only when `ATLAS_REPOSITORY=postgres`. Imports use `laspy` (with `lazrs`, to read LAZ files) and
`defusedxml` (to parse KML safely). The web app needs no network at run time other than the API and the
map basemap: its fonts come from `@fontsource` packages and are served with the app.

## 2. Configure

```bash
cp .env.example .env
```

Every setting has a default, so demo mode works without a `.env`. The file matters when you switch to
live mode, change ports or add API keys. Notes:

- **Where `.env` is read.** Vite and Docker Compose read the `.env` in the repository root. The API
  reads `.env` from its **current working directory**, and `make api` starts it from `apps/api`, so the
  root file is *not* loaded by that target. Use one of:

  ```bash
  set -a; . ./.env; set +a; make api                               # export, then run
  python3 -m uvicorn app.main:app --app-dir apps/api --reload      # run from the repository root
  ```

- `VITE_*` variables are compiled into the web bundle at build or dev-server start, and are public.
  Never put a secret in one.
- `.env` is ignored by git. Never commit it.
- The full list of variables is in [Environment variables](#environment-variables) below.
  `.env.example` does not list all of them yet; every variable has a default in code.

## 3. Run

```bash
make dev        # API on :8000 and web on :5173 together (Ctrl+C stops both)
# or, in two terminals:
make api
make web
```

Check it:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","version":"0.1.0","mode":"demo","repository":"memory", ...}
```

Open <http://localhost:5173> for the web app and <http://localhost:8000/docs> for the interactive API
reference. In demo mode three synthetic plots (`PLT-DEMOIN`, `PLT-DEMOUS`, `PLT-DEMOEU`) are created at
start-up, so the workspace and "My plots" are never empty. If the API is not running, the web app falls
back to static fixtures and shows "API offline — showing demo data."

## Demo mode and live mode

`ATLAS_MODE` selects the adapters. Both modes run the same engines on the same configuration.

| | `demo` (default) | `live` |
| --- | --- | --- |
| Network | Not needed by the API | Calls public APIs through the adapters |
| Data | Deterministic synthetic data labeled `synthetic-demo` | Real data with dataset versions and access times in provenance |
| Climate zone | Region default from `config/regions/<ISO>.yaml` | Derived from Open-Meteo normals |
| Keys | None | Optional: `USDA_NASS_API_KEY`, `DATA_GOV_IN_API_KEY`, `COPERNICUS_TOKEN`, `ESRI_API_KEY` |
| Use it for | Development, tests, CI, workshops | Real analysis |

For live mode set at least:

```bash
ATLAS_MODE=live
NOMINATIM_USER_AGENT="carboncreditbuy/0.1 (contact: your-real-address@your-domain)"
```

The Nominatim usage policy requires an identifying User-Agent, and the adapter rejects the
`you@example.org` placeholder from `.env.example`. A source that needs a key (USDA NASS, data.gov.in)
falls back to its demo twin when the key is empty, so a missing key does not produce an error: check the
`provenance` of a result to see which kind of data you got. See [FREE_APIS.md](../data-sources/FREE_APIS.md)
for each source's terms and [adding an integration](adding-an-integration.md) for how adapters are built.

`ATLAS_ENV=production` changes behavior, not just a label: estimates that use a `pending` parameter
are refused (HTTP 409), whatever `ATLAS_ALLOW_PENDING_PARAMETERS` says, and `pending` tree-age rules
are withheld. With the v0.1 configuration that means a production deployment cannot produce estimates
until the pending parameters are verified
([species and parameters](adding-a-species-or-parameter.md)).

## Environment variables

Defaults are the ones in `apps/api/app/core/config.py` and `apps/web/src/config/mapEnv.ts`. The last
column says whether `.env.example` lists the variable.

### API

| Variable | Default | What it does | Listed |
| --- | --- | --- | --- |
| `ATLAS_ENV` | `development` | `production` refuses `pending` parameters and withholds `pending` tree-age rules | yes |
| `ATLAS_MODE` | `demo` | `demo` (synthetic twins) or `live` (public APIs) | yes |
| `ATLAS_LOG_LEVEL` | `info` | Log level. Logs never contain coordinates | yes |
| `ATLAS_API_HOST`, `ATLAS_API_PORT` | `0.0.0.0`, `8000` | Used by `make api` | yes |
| `ATLAS_CORS_ORIGINS` | `localhost` and `127.0.0.1` on 5173 and 4173, `localhost:8080` | Comma-separated browser origins allowed to call the API. See [troubleshooting](troubleshooting.md#the-browser-reports-a-cors-error) | yes |
| `ATLAS_API_KEYS` | empty | Comma-separated keys. When set, mutating endpoints require `X-API-Key`. Read endpoints stay open | yes |
| `ATLAS_RATE_LIMIT`, `ATLAS_RATE_LIMIT_ENABLED` | `60/minute`, `true` | Per-client request limit | first only |
| `ATLAS_MAX_PLOT_VERTICES`, `ATLAS_MAX_PLOT_AREA_HA` | `500`, `10000` | Limits on a plot polygon | yes |
| `ATLAS_MAX_BODY_BYTES` | `1000000` | Largest JSON request body | no |
| `ATLAS_MAX_UPLOAD_MB` | `50` | Largest file for `POST /imports` (HTTP 413 above it) | no |
| `ATLAS_ALLOW_PENDING_PARAMETERS` | `true` | `false` makes the API refuse `pending` parameters, as production does | yes |
| `ATLAS_CONFIG_DIR` | repository `config/` | Directory every configuration reader uses (set in the Docker image) | no |
| `ATLAS_SEED_DEMO` | `true` | Create the three demo plots at start-up in demo mode | no |
| `ATLAS_CACHE_DIR`, `ATLAS_REPORTS_DIR` | `.cache`, `.reports` | Defined in `Settings`; no code reads them yet | yes |
| `ATLAS_REPOSITORY` | `memory` | `memory` or `postgres` | yes |
| `DATABASE_URL` | `postgresql://atlas:atlas@localhost:5432/atlas` | Used when the repository is `postgres` | yes |
| `ATLAS_STAC_PROVIDER` | `earth-search` | `earth-search` or `copernicus` | yes |
| `EARTH_SEARCH_STAC_URL`, `COPERNICUS_STAC_URL`, `COPERNICUS_TOKEN` | see `.env.example` | Sentinel-2 catalogs. The token is needed only to download Copernicus assets | yes |
| `ESA_WORLDCOVER_BASE_URL`, `ESA_WORLDCOVER_VERSION` | WorldCover 2021 v200 on AWS | Land-cover tiles | yes |
| `OPEN_METEO_ARCHIVE_URL`, `OPEN_METEO_ELEVATION_URL` | Open-Meteo endpoints | Climate normals and elevation | yes |
| `SOILGRIDS_URL` | ISRIC REST endpoint | Soil organic carbon | yes |
| `MAX_CLOUD_COVER_PCT` | `20` | Cloud filter for Sentinel-2 scenes | yes |
| `ATLAS_GEOCODER` | `nominatim` | `nominatim` or `photon` | yes |
| `NOMINATIM_URL`, `NOMINATIM_USER_AGENT` | OSM endpoint, empty | The adapter refuses an empty User-Agent or the `you@example.org` placeholder in live mode | yes |
| `PHOTON_URL`, `GEOCODER_MIN_INTERVAL_SECONDS` | Komoot endpoint, `1.0` | Photon endpoint and the pause between geocoder calls | yes |
| `USDA_NASS_API_URL`, `USDA_NASS_API_KEY` | QuickStats endpoint, empty | US crop statistics. An empty key selects the demo twin | yes |
| `CENSUS_GEOCODER_URL` | Census endpoint | US county lookup | yes |
| `DATA_GOV_IN_API_URL`, `DATA_GOV_IN_API_KEY`, `DATA_GOV_IN_CROP_RESOURCE_ID` | data.gov.in endpoint, empty, resource id | Indian crop statistics. An empty key selects the demo twin | yes |
| `ESRI_API_KEY` | empty | Substituted into the Esri provider URL of `GET /imagery/providers`. Without it that provider is `available: false` | no |
| `ATLAS_EXPLAIN_PROVIDER` | `template` | `template` or `llm` for the explanation endpoint. The `llm` option receives derived indicators only | yes |
| `ATLAS_AGENT_REASONER` | `template` | `template` or `llm`. A language model only rephrases agent sentences from redacted facts | no |
| `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | empty | An OpenAI-compatible endpoint. The model is used only when the reasoner is `llm` and the base URL and model are set | yes |
| `LLM_TIMEOUT_SECONDS` | `20` | Timeout for the optional language model | no |

`.env.example` also lists `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY`.
No code reads them yet; they belong to the object-storage plan for tiles.

### Web app (build time)

Vite reads these from the root `.env` (`envDir` is the repository root) when the dev server starts or
the app is built. They end up in the public bundle.

| Variable | Default | What it does |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Where the app finds the API |
| `VITE_API_KEY` | none | Sent as `X-API-Key`. Public, because it is compiled in. Use it only for a low-value key |
| `VITE_BASEMAP_STYLE_URL` | `https://tiles.openfreemap.org/styles/liberty` | A MapLibre style. The default is for demos only |
| `VITE_BASEMAP_PMTILES_URL` | none | Your own PMTiles basemap (OpenStreetMap-based builds need ODbL attribution) |
| `VITE_SATELLITE_TILES_URL`, `VITE_SATELLITE_ATTRIBUTION` | none | Forces one imagery tile template and its attribution. Respect its license; see [MAP_LICENSES.md](../licensing/MAP_LICENSES.md) |
| `VITE_DEFAULT_COUNTRY`, `VITE_DEFAULT_LANGUAGE` | `IN`, `en` | First-run country and language |

### Web container (run time)

The nginx image builds its Content-Security-Policy from these when the container starts. Keep them
consistent with the build-time values above.

| Variable | Default | What it allows |
| --- | --- | --- |
| `NGINX_PORT` | `8080` | Listen port |
| `ATLAS_API_ORIGIN` | `http://localhost:8000` | The API origin (`connect-src`) |
| `ATLAS_BASEMAP_ORIGINS` | `https://demotiles.maplibre.org` | Space-separated origins for the style, glyphs, sprites and tiles (`img-src`, `connect-src`) |
| `ATLAS_EXTRA_CONNECT_SRC` | the imagery hosts of `config/imagery/providers.yaml` | More `connect-src` origins. MapLibre fetches raster tiles with `fetch()`, so every imagery tile host must be here too |
| `ATLAS_EXTRA_IMG_SRC` | the imagery hosts of `config/imagery/providers.yaml` | More `img-src` origins. Every imagery provider the satellite view can load needs its tile host here |

## PostgreSQL and PostGIS

The default repository keeps everything in memory and loses it on restart. To persist, use PostgreSQL
15 or newer with PostGIS 3 (the compose file uses PostgreSQL 16 with PostGIS 3.4).

```bash
docker compose up -d db                                  # postgis/postgis:16-3.4, schema applied on first start
ATLAS_REPOSITORY=postgres DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas make api
```

The compose file mounts [`data/schemas/schema.sql`](../../data/schemas/schema.sql) into the image's init
directory, which runs **only when the data volume is empty**. For an existing database apply it
yourself; it is idempotent, and it brings a database created from an earlier revision up to date:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/schemas/schema.sql
```

The API does not create tables. In PostgreSQL, deleting a plot cascades to its inventories, analysis,
estimates, reports and generic records (imports, detections, agent runs); the in-memory repository
does not yet delete a plot's reports. The header of `schema.sql` explains the table map and one known
geometry caveat: a polygon with `z` coordinates or an unclosed ring passes the validator but is rejected
by the database. The schema is tested against a real database in CI, and you can run the same checks
yourself: see [testing the PostgreSQL schema](testing.md#testing-the-postgresql-schema).

## Docker

```bash
cp .env.example .env          # the compose file requires the file to exist
make docker-up                # docker compose up --build
make docker-down              # stops and removes containers and volumes (-v)
```

| Service | Port | Notes |
| --- | --- | --- |
| `api` | 8000 | `infra/docker/Dockerfile.api`, non-root user 10001, health check on `/api/v1/health` |
| `web` | 8080 | `infra/docker/Dockerfile.web`, nginx with a strict Content-Security-Policy, `/healthz` |
| `db` | 5432 | `postgis/postgis:16-3.4`, user, password and database all `atlas` (development only) |
| `minio` | 9000, 9001 | S3-compatible storage for tiles; the development password is a placeholder, change it |

Compose starts the API with `ATLAS_REPOSITORY=memory` unless you override it. The web image bakes
`VITE_*` values in at build time; rebuild it after changing them. The container's Content-Security-Policy
only allows the origins named in the variables above, so a basemap or satellite host that you add must
also be added there ([troubleshooting](troubleshooting.md#a-basemap-or-imagery-works-with-npm-run-dev-but-not-in-docker)).

## PDF reports

PDF output needs the optional WeasyPrint package and the Pango and Cairo system libraries:

```bash
python3 -m pip install weasyprint
```

Without it, `POST /plots/{id}/report` with `format: pdf` returns HTTP 501 (`pdf-unavailable`). The HTML
report can always be printed to PDF from the browser.

## The QGIS plugin

The plugin in `integrations/qgis-plugin` is a client of the API, so start the API first. Its tests need
only `pytest` and no QGIS. To try it in QGIS, run `make package` or `make link` inside
`integrations/qgis-plugin/`, as its README explains. It is licensed GPL-2.0-or-later, unlike the rest of
the repository ([why](../licensing/THIRD_PARTY.md#the-qgis-plugin-and-the-gpl)).

## Everyday commands

| Command | What it does |
| --- | --- |
| `make test` | pytest (all Python) plus web typecheck and Vitest |
| `make lint` | ruff, mypy and ESLint |
| `make format` | ruff format and Prettier |
| `make build` | Production web build into `apps/web/dist` |
| `make clean` | Remove caches and build output |

Details: [testing](testing.md). Documentation images are made as described in
[images/README.md](../images/README.md).

## Next

- [Architecture overview](architecture-overview.md): how a request travels through the code
- [Testing](testing.md)
- [Troubleshooting](troubleshooting.md)
- [Contributing](../../CONTRIBUTING.md)
