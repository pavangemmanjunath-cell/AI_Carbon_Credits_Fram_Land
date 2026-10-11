# integrations

Adapters for every external API and dataset CarbonCreditBuy uses, each with an
offline **demo twin**. This is where the project's data-source rules are
enforced (CLAUDE.md principles 5 and 6): the API never calls a public service
directly; it goes through an adapter that states its source, licence,
attribution, rate limits, caching and failure behaviour, and that takes its
endpoint from an environment variable.

This folder holds three kinds of integration:

| Part | What it is | Where it runs |
| --- | --- | --- |
| `carboncreditbuy_integrations/` | The Python adapters in the table below | In the API |
| [`imagery/`](imagery/README.md) | Display imagery providers (Esri, USGS, EOX, national orthophotos): configuration and documentation, not a Python adapter. The browser loads the tiles | In the web app's map |
| [`qgis-plugin/`](qgis-plugin/README.md) | A QGIS 3 plugin that sends a field polygon and a tree count to the API ([user guide](../docs/user-guide/qgis-plugin.md)) | In QGIS, talking to the API over HTTP |

The Python package is `carboncreditbuy_integrations` (install name `carboncreditbuy-integrations`).

## Install

```bash
python3 -m pip install -e integrations                 # or: make install
python3 -m pip install -e "integrations[live]"         # rasterio and pystac-client for live imagery
```

Runtime dependencies: httpx, NumPy, Shapely (plus the `geo_engine` package for
raster and STAC helpers). `rasterio` and `pystac-client` are imported lazily; a
live satellite or land-cover call without them raises `DependencyMissingError`.

## Adapters

| Package | Source | Endpoint variable | Credentials | Licence | Cache |
| --- | --- | --- | --- | --- | --- |
| `esa_worldcover` | ESA WorldCover 2021 v200, 10 m land cover (COG range reads) | `ESA_WORLDCOVER_BASE_URL`, `ESA_WORLDCOVER_VERSION` | none | CC BY 4.0 | 24 h |
| `earth_search` | Sentinel-2 L2A through the Earth Search STAC catalogue (AWS) | `EARTH_SEARCH_STAC_URL` | none | Copernicus Sentinel data terms | 6 h |
| `copernicus` | Sentinel-2 L2A through the Copernicus Data Space STAC catalogue | `COPERNICUS_STAC_URL` | `COPERNICUS_TOKEN` for asset downloads; search is anonymous | Copernicus Sentinel data terms | 6 h |
| `open_meteo` | Open-Meteo archive (ERA5 normals) and elevation | `OPEN_METEO_ARCHIVE_URL`, `OPEN_METEO_ELEVATION_URL` | none for non-commercial use | CC BY 4.0 | 7 days |
| `soilgrids` | ISRIC SoilGrids 2.0, soil organic carbon 0-30 cm | `SOILGRIDS_URL` | none | CC BY 4.0 | 30 days |
| `nominatim` | Nominatim geocoding (OpenStreetMap) | `NOMINATIM_URL`, `NOMINATIM_USER_AGENT`, `GEOCODER_MIN_INTERVAL_SECONDS` | identifying User-Agent is mandatory | ODbL 1.0 | 24 h |
| `photon` | Photon geocoding (komoot, OpenStreetMap) | `PHOTON_URL` | none | ODbL 1.0 (data), Apache-2.0 (software) | 24 h |
| `usda_nass` | USDA NASS Quick Stats county crop statistics | `USDA_NASS_API_URL`, `USDA_NASS_API_KEY` | free key | US public domain | 24 h |
| `census_geocoder` | US Census Bureau geographies by coordinates | `CENSUS_GEOCODER_URL` | none | US public domain | 30 days |
| `data_gov_in` | data.gov.in district crop production | `DATA_GOV_IN_API_URL`, `DATA_GOV_IN_API_KEY`, `DATA_GOV_IN_CROP_RESOURCE_ID` | free key | Government Open Data License - India | 24 h |

Full terms, attribution strings and rate-limit notes per source:
[`docs/data-sources/FREE_APIS.md`](../docs/data-sources/FREE_APIS.md) and
[`docs/licensing/DATA_LICENSES.md`](../docs/licensing/DATA_LICENSES.md).

## Display imagery is configuration, not an adapter

The "Satellite" view of the web map shows tiles from imagery providers. These are
**not** fetched by the API: the API only serves the provider list from
[`config/imagery/providers.yaml`](../config/imagery/providers.yaml)
(`GET /imagery/providers`, with licence, attribution, coverage and the tile URL
with any key filled in from the environment), and the visitor's browser loads the
tiles. Nothing is stored or analysed, and the tiles are never read by a
calculation. The licence of each provider says whether feature extraction is
allowed; the `analysis_allowed` field carries that answer to the user.

Because the browser does the fetching, a Python adapter would add nothing: the
source, licence, attribution, key handling, rate limits and failure behaviour that
principle 6 asks for are documented in [`imagery/README.md`](imagery/README.md),
and the endpoints still come from configuration and environment variables, never
from literals in application code.

## The QGIS plugin

`integrations/qgis-plugin/` is a QGIS 3 plugin (experimental, 0.1.0). It selects a
field polygon, counts the tree crowns found inside it by a segmentation tool, and
asks the API for a scenario estimate and for the AI agent team's assessment. It
talks only to the API address in its settings, uses nothing but QGIS and the
Python standard library, and shows `certified: false` on every result. Build the
installable ZIP with `make qgis-plugin` from the repository root. Its code is
licensed GPL-2.0-or-later because it runs inside QGIS; the rest of the repository is
Apache-2.0, and the two exchange only HTTP and JSON. Details, privacy table and
limitations: [plugin README](qgis-plugin/README.md).

## The adapter pattern

Every adapter package has the same shape:

```text
carboncreditbuy_integrations/<name>/
    __init__.py     exports SOURCE, the live adapter, the Demo twin and result types
    adapter.py      SOURCE (SourceProvenance), live class, Demo twin
```

- **`SOURCE`** is a `SourceProvenance` (`id`, `name`, `version`, `license`,
  `attribution`, `url`). The adapter's static `provenance()` returns it, and the
  API copies it into every result's provenance and into `GET /attribution`.
- **Live adapter** extends `HttpAdapter` (httpx with a 20 second timeout, one
  retry on a 5xx or a transport error, an optional cache and typed errors) or
  wraps rasterio/pystac-client for imagery. Constructors receive URLs and keys as
  arguments; live adapters do not read the environment (only the demo helper
  `demo_support` looks up `ATLAS_CONFIG_DIR` to find the region files).
- **Demo twin** (`Demo<Name>Adapter`) has the same method names, returns
  deterministic synthetic data and reports `synthetic-demo` as its source through
  `demo_source(SOURCE)`. Demo data is never presented as an observation.
- **Typed errors** (`AdapterError` and its subclasses `ConfigurationError`,
  `DependencyMissingError`, `UpstreamError`, `NotFoundError`, `RateLimitedError`,
  `UpstreamDataError`) let the API turn a failure into a clear problem response
  or a "layer unavailable" note instead of an invented value.
- **Caching**: `MemoryTTLCache` and `cache_key` (a SHA-256 of the request
  identity), so coordinates are not kept as readable keys.
- **Privacy**: error messages carry the host and status code only, never the
  query, because the query may hold coordinates.

`stac_common.StacSatelliteAdapter` is the shared implementation behind
`earth_search` and `copernicus`; `demo_support` holds the helpers the twins use
(region hints, deterministic noise).

## Demo and live modes

`apps/api/app/services/adapters.py` (`ModeRouter`) is the only place that picks
a twin or a live adapter, from `ATLAS_MODE`:

- `demo`: every adapter is its `Demo*` twin. No network, no keys.
- `live`: the live adapter is built from the settings. For `usda_nass` and
  `data_gov_in`, an empty API key silently selects the demo twin, so check the
  `mode` and the provenance of what you receive.

## Tests

```bash
python3 -m pytest integrations -q
```

`integrations/tests/` uses `httpx.MockTransport` helpers (`httpmock.py`) so no
test reaches the network. It covers the shared base (retry, status-code
mapping, cache, provenance), Open-Meteo, SoilGrids, USDA NASS, the Census
geocoder and data.gov.in. See [testing](../docs/developer-guide/testing.md).

The QGIS plugin has its own suite in `qgis-plugin/tests/`, which runs without
QGIS against stand-ins for the parts of PyQGIS that the plugin uses; the one
dialog smoke test needs PyQt5 and is skipped without it. The imagery providers
file is checked by `tests/data-quality/test_imagery_providers.py` and by
`apps/api/tests/test_imagery_api.py`.

Not yet covered by adapter tests: Nominatim, Photon, WorldCover, Earth Search
and Copernicus (the underlying `geo_engine` helpers are tested). These are good
first contributions; see [starter issues](../docs/community/starter-issues.md).

## Known gaps

- The per-adapter READMEs that CLAUDE.md principle 6 asks for do not exist yet
  for the Python adapters; this file and `docs/data-sources/FREE_APIS.md` are the
  interim reference. The imagery integration has its own README.
- `usda_nass`, `census_geocoder` and `data_gov_in` are built by the router but no
  service calls them yet, so "other farm income" stays empty.
- The Copernicus asset key names are configurable because the catalogue
  evolves; the adapter docstring asks you to verify them against the live
  catalogue before relying on them.
- Rate limits for SoilGrids and the Open-Meteo free tier are quoted from the
  provider's published terms at the time of writing; re-check before a
  production deployment.

## Adding an adapter

Follow [adding a data adapter](../docs/developer-guide/adding-a-data-adapter.md):
licence row first, then `SOURCE`, the live adapter, the demo twin, the
environment variable, the router wiring, tests and the attribution entry.
