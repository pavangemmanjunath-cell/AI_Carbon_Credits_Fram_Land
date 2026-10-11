# Free and open data APIs

CarbonCreditBuy reads public data through adapters in [`integrations/`](../../integrations/README.md), and the map's
Satellite view loads imagery tiles from public providers. This page is the reference for each one: what it is for,
whether the API calls it in version 0.1, how to configure it, the terms it is used under, how long answers are cached,
what happens when it fails, and what location data the provider receives. The [reference tables](#reference-tables)
list every source with the same columns (endpoint variable, license, attribution, key, rate limit, adapter and demo
twin), which is the row to add for a new source ([adding an integration](../developer-guide/adding-an-integration.md)).
CLAUDE.md principle 6 asks for a README in every adapter; those do not exist yet, so this page is the interim reference
([known gaps](#known-gaps)).

The adapter facts were read from the adapter code and [`.env.example`](../../.env.example) on 2026-10-05, not from the
providers' current pages. The imagery facts come from the research of the same day
([imagery research](../research/imagery-providers.md)). Rate limits are quoted as the adapters record them, and
providers change their terms, so confirm each limit and license before a production deployment.
[`DATA_LICENSES.md`](../licensing/DATA_LICENSES.md) and [`MAP_LICENSES.md`](../licensing/MAP_LICENSES.md) are the
authority for licenses and [`ATTRIBUTION.md`](../licensing/ATTRIBUTION.md) for the strings to display. Anything we could
not confirm is marked TODO(verify).

## At a glance

| Source | Used for | Key | Cache | Called in v0.1 | What the provider receives |
| --- | --- | --- | --- | --- | --- |
| [ESA WorldCover](#esa-worldcover) | Land-cover shares | None | 24 h | Yes, plot analysis | The name of a 3° tile and the byte ranges that cover the plot |
| [Earth Search](#sentinel-2-through-earth-search) | Sentinel-2 scenes for NDVI, NDMI and the cube | None | 6 h (vegetation only) | Yes, plot analysis and the cube; the default STAC provider | The exact plot polygon in the search; byte ranges around the plot in the scene files |
| [Copernicus Data Space](#sentinel-2-through-copernicus-data-space) | The same, from another catalog | Token for asset downloads | 6 h (vegetation only) | Yes, when `ATLAS_STAC_PROVIDER=copernicus` | The same |
| [Open-Meteo](#open-meteo) | Climate normals and elevation | None for non-commercial use | 7 days | Yes, plot analysis; `/simulate` only when the request carries `lat` and `lon` | The plot centroid, in two requests |
| [SoilGrids](#soilgrids) | Soil organic carbon, 0 to 30 cm | None | 30 days | Yes, plot analysis | The plot centroid |
| [Nominatim](#nominatim) | Place search and reverse geocoding | An identifying User-Agent is mandatory | 24 h | Yes | Search text and an optional country code; the exact centroid for reverse lookups |
| [Photon](#photon) | The same, as an alternative | None | 24 h | Yes, when `ATLAS_GEOCODER=photon` | Search text; the exact centroid for reverse lookups |
| [USDA NASS Quick Stats](#usda-nass-quick-stats) | US county crop statistics | Free key | 24 h | No: built, never called | State and county codes, commodity and years; no coordinates |
| [US Census Geocoder](#us-census-geocoder) | County from coordinates | None | 30 days | No: built, never called | The exact centroid |
| [data.gov.in](#datagovin) | India district crop production | Free key | 24 h | No: built, never called | State, district and crop names |

"Called in v0.1" means a service in `apps/api` calls the adapter. In demo mode, the default, nothing is called: every
adapter is replaced by a synthetic twin ([demo and live modes](#demo-and-live-modes)). The API makes every call, so a
provider sees your server's address and not the user's; only the map tiles in the browser come straight from their
hosts ([map imagery and basemaps](#map-imagery-and-basemaps)).

## Reference tables

One row for every source. "Endpoint variable" is the environment variable that holds the URL, so you can point it at
a mirror or a self-hosted copy; the defaults are in [`.env.example`](../../.env.example). The attribution column holds
ids from [ATTRIBUTION.md](../licensing/ATTRIBUTION.md), which has the text to display. Adapter paths are relative to
[`integrations/carboncreditbuy_integrations/`](../../integrations/carboncreditbuy_integrations/).

### Data adapters

| Source | Endpoint variable | License | Attribution | Key | Rate limit or usage policy | Adapter | Demo twin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ESA WorldCover](#esa-worldcover) | `ESA_WORLDCOVER_BASE_URL`, `ESA_WORLDCOVER_VERSION` | CC BY 4.0 | `esa-worldcover` | None | None quoted in the repository. TODO(verify): the terms of the bucket | [`esa_worldcover/adapter.py`](../../integrations/carboncreditbuy_integrations/esa_worldcover/adapter.py) | `DemoWorldCoverAdapter` |
| [Earth Search](#sentinel-2-through-earth-search) (Sentinel-2 L2A STAC) | `EARTH_SEARCH_STAC_URL`; `ATLAS_STAC_PROVIDER=earth-search` selects it | Copernicus Sentinel data terms: free, full and open | `copernicus-sentinel-2` | None | None quoted. TODO(verify): the Earth Search and AWS Open Data terms | [`earth_search/adapter.py`](../../integrations/carboncreditbuy_integrations/earth_search/adapter.py), on [`stac_common.py`](../../integrations/carboncreditbuy_integrations/stac_common.py) | `DemoSatelliteAdapter`, shared with Copernicus |
| [Copernicus Data Space](#sentinel-2-through-copernicus-data-space) (STAC) | `COPERNICUS_STAC_URL`, `COPERNICUS_TOKEN`; `ATLAS_STAC_PROVIDER=copernicus` selects it | Sentinel terms, plus the CDSE terms of use | `copernicus-sentinel-2` | Search is anonymous; a token is needed to download scene files | None quoted. TODO(verify): CDSE quotas | [`copernicus/adapter.py`](../../integrations/carboncreditbuy_integrations/copernicus/adapter.py) | `DemoSatelliteAdapter` |
| [Open-Meteo](#open-meteo) (archive and elevation) | `OPEN_METEO_ARCHIVE_URL`, `OPEN_METEO_ELEVATION_URL` | Data CC BY 4.0 | `open-meteo` | None for non-commercial use; the adapter has no setting for a subscription key | Free tier for non-commercial use; the terms cite fewer than 10,000 calls a day. TODO(verify) | [`open_meteo/adapter.py`](../../integrations/carboncreditbuy_integrations/open_meteo/adapter.py) | `DemoOpenMeteoAdapter` |
| [SoilGrids](#soilgrids) | `SOILGRIDS_URL` | CC BY 4.0 | `soilgrids` | None | At most 5 requests a minute, as the adapter quotes the ISRIC policy. Nothing throttles it | [`soilgrids/adapter.py`](../../integrations/carboncreditbuy_integrations/soilgrids/adapter.py) | `DemoSoilGridsAdapter` |
| [Nominatim](#nominatim) | `NOMINATIM_URL`, `NOMINATIM_USER_AGENT`, `GEOCODER_MIN_INTERVAL_SECONDS` | Data ODbL 1.0 | `nominatim` | None, but an identifying `User-Agent` is mandatory | Public instance: 1 request a second, no bulk geocoding, cache results. The adapter spaces uncached requests | [`nominatim/adapter.py`](../../integrations/carboncreditbuy_integrations/nominatim/adapter.py) | `DemoNominatimAdapter` |
| [Photon](#photon) | `PHOTON_URL`; `ATLAS_GEOCODER=photon` selects it | Data ODbL 1.0; software Apache-2.0 | `photon` | None | Fair use on the public instance; self-host for production. Nothing throttles the adapter | [`photon/adapter.py`](../../integrations/carboncreditbuy_integrations/photon/adapter.py) | None. The Nominatim twin answers |
| [US Census Geocoder](#us-census-geocoder) | `CENSUS_GEOCODER_URL` | Public domain (US Government work) | `census-geocoder` | None | Single-point lookups; a separate batch endpoint exists for bulk work. TODO(verify) | [`census_geocoder/adapter.py`](../../integrations/carboncreditbuy_integrations/census_geocoder/adapter.py) | `DemoCensusGeocoderAdapter` |
| [USDA NASS Quick Stats](#usda-nass-quick-stats) | `USDA_NASS_API_URL`, `USDA_NASS_API_KEY` | Public domain (US Government work) | `usda-nass` | Free key. An empty key selects the demo twin | A response holds at most 50,000 records. Rate limits are not published | [`usda_nass/adapter.py`](../../integrations/carboncreditbuy_integrations/usda_nass/adapter.py) | `DemoUsdaNassAdapter` |
| [data.gov.in](#datagovin) | `DATA_GOV_IN_API_URL`, `DATA_GOV_IN_API_KEY`, `DATA_GOV_IN_CROP_RESOURCE_ID` | GODL-India | `data-gov-in` | Free key. An empty key selects the demo twin | Per-key limits per minute and per day. TODO(verify): the numbers | [`data_gov_in/adapter.py`](../../integrations/carboncreditbuy_integrations/data_gov_in/adapter.py) | `DemoDataGovInAdapter` |

### Imagery providers for the Satellite view

These are entries in [`config/imagery/providers.yaml`](../../config/imagery/providers.yaml), not adapters. For all
eight rows the endpoint is the `url` of the entry (only Esri has a variable, the key `ESRI_API_KEY`), the code is the
[imagery service](../../apps/api/app/services/imagery.py), which lists the entries and fills in the key, and there is no
demo twin: the browser loads the tiles straight from the provider, so when the provider cannot be reached the map keeps
its basemap and says that satellite tiles could not be loaded ([how it works](#satellite-and-aerial-imagery)). The
attribution column holds provider ids; the text is in
[ATTRIBUTION.md](../licensing/ATTRIBUTION.md#imagery-providers-satellite-view).

| Provider | Coverage | License | Attribution | Key | Rate limit or usage policy | Analysis |
| --- | --- | --- | --- | --- | --- | --- |
| Esri World Imagery | Global | Esri Master License Agreement (proprietary) | `esri-world-imagery` | Yes: `ESRI_API_KEY` from an ArcGIS Location Platform account | Display only. The terms bar harvesting, redistributing and self-hosting tiles, and using Living Atlas content commercially in your own product. Whether a free open-source deployment counts as commercial is not confirmed | Not allowed |
| USGS Imagery Only | United States | Public domain | `usgs-imagery-only` | None | No fair-use or rate-limit policy was found. TODO(verify). The tile cache ends at zoom 16 | Allowed |
| IGN France, BD ORTHO | France | Licence Ouverte 2.0 (Etalab) | `ign-france-orthophotos` | None | The usage-limits page of the Géoplateforme leaves the WMTS tile service out of its rate limiting, so no per-IP limit is documented | Allowed |
| IGN Spain, PNOA | Spain | CC BY 4.0 scne.es | `ign-spain-pnoa` | None | No limit documented. The credit must be visible at the foot of the map | Allowed |
| PDOK Luchtfoto | Netherlands | CC BY 4.0 | `pdok-luchtfoto` | None | No fair-use policy confirmed. TODO(verify) | Allowed |
| EOX Sentinel-2 cloudless 2016 | Global | CC BY 4.0 | `eox-s2cloudless-2016` | None | The free endpoint is "as is" and rate limited; EOX points to a dedicated service under an SLA for steady traffic. The limit is not quantified | Allowed |
| EOX Sentinel-2 cloudless 2017 | Global | CC BY 4.0 | `eox-s2cloudless-2017` | None | As for 2016 | Allowed |
| EOX Sentinel-2 cloudless 2025 | Global | CC BY-NC-SA 4.0: non-commercial; commercial use needs a license from EOX | `eox-s2cloudless-2025` | None | As for 2016, and for clearly non-commercial deployments only | Review the terms |

"Analysis" is the `analysis_allowed` flag: whether segmentation, machine learning or feature extraction on the tiles is
licensed. CarbonCreditBuy itself runs none, because its vegetation indices and tree-cover detection read Sentinel-2 through
the STAC adapters, not these tiles.

## Before you go live

1. Install the live extras with `python3 -m pip install -e "integrations[live]"`. Without `rasterio` and
   `pystac-client`, land cover, vegetation and the cube report `DependencyMissingError`.
2. Set `ATLAS_MODE=live` and a real `NOMINATIM_USER_AGENT` that names your application and a contact. The adapter
   rejects an empty value and the placeholder that `.env.example` ships with
   ([setup](../developer-guide/setup.md#demo-mode-and-live-mode)).
3. Plan the geocoder. The public Nominatim and Photon servers are for light use, and the search box sends a request
   while the user types ([Nominatim](#nominatim)). Self-host one of them for anything public.
4. Read the Open-Meteo terms. The free tier is for non-commercial use, and the adapter has no setting for a
   subscription key ([Open-Meteo](#open-meteo)).
5. Show the attribution for every source whose data you display ([attribution strings](#attribution-strings)).
6. Tell your users where location goes ([geolocation](../privacy/geolocation.md)). The exact plot polygon leaves the
   server in the satellite search, which the privacy pages do not yet say ([known gaps](#known-gaps)).

## How every adapter behaves

### Demo and live modes

`ATLAS_MODE` is `demo` (the default) or `live`. [`ModeRouter`](../../apps/api/app/services/adapters.py) is the only
code that picks a twin or a live adapter.

- **Demo.** Every adapter is its `Demo...` twin. There is no network use and no key. A twin returns deterministic
  synthetic values and reports its source as `synthetic-demo`, named "Synthetic demo data (imitating ...)", with the
  attribution "CarbonCreditBuy demo generator — not an observation". There is no Photon twin, and Earth Search and
  Copernicus share one satellite twin, so in demo mode the Nominatim twin answers place searches whichever geocoder is
  configured.
- **Live.** Each adapter is built from the settings. For NASS and data.gov.in an empty API key selects the demo twin
  even in live mode, so check `mode` and the source `id` in the provenance of what you receive.

### Requests, retries and errors

Seven adapters (Open-Meteo, SoilGrids, Nominatim, Photon, NASS, the Census geocoder and data.gov.in) share
[`HttpAdapter`](../../integrations/carboncreditbuy_integrations/base.py):

| Behavior | Detail |
| --- | --- |
| Timeout | 20 seconds per request |
| Retry | One retry after 0.5 seconds on a transport error, including a timeout, or on an HTTP 5xx status. A 4xx status is never retried |
| Headers | `User-Agent`, by default `carboncreditbuy/0.1 (+https://github.com/pavangemmanjunath-cell/Carbon_Credits_Fram_Land)` (Nominatim sends `NOMINATIM_USER_AGENT`), and `Accept: application/json` |
| 404 | `NotFoundError` |
| 429 | `RateLimitedError`, with no retry and no `Retry-After` handling |
| 401 and 403 | `ConfigurationError` ("authentication failed ... check API key"), whatever the provider's reason |
| Any other status of 400 or more, after the retry | `UpstreamError` with the host and status code |
| A body that is not JSON, or JSON of an unexpected shape | `UpstreamDataError` |
| Error text | The host and the status code or exception class only, never the query, because the query may hold coordinates |

WorldCover, Earth Search and Copernicus do not use `HttpAdapter`. They read through rasterio (GDAL) and pystac-client,
so those libraries' own timeout and retry behavior applies (TODO(verify): the defaults). Their failures are wrapped in
`UpstreamError` with the exception class name only ("WorldCover tile read failed", "STAC search failed", "Sentinel-2
asset read failed"), or in `DependencyMissingError` when a library is missing.

### Caching

- All adapters share one in-memory cache per process, holding up to 2,048 entries. When it is full, the entry that
  expires soonest is dropped. It is lost on restart and is not shared between workers, so a deployment with several API
  processes keeps several caches.
- Keys are SHA-256 hashes of the request, so coordinates never appear as readable keys.
- Only successful answers are cached. A failure is tried again on the next request.
- The TTLs in the table above are fixed in code. No setting changes them.
- `ATLAS_CACHE_DIR` is defined in the settings, but no adapter writes to disk or to a bucket in v0.1. The architecture
  and privacy pages describe cached raster windows on disk; that is not built.

### What a failure looks like

| Call | What happens |
| --- | --- |
| Land cover, vegetation or soil in `POST /plots/{plot_id}/analyze` | The analysis still succeeds. The layer is `null` and `data_quality.warnings` gains a line such as "land cover unavailable: UpstreamError" (the text names the layer and the error class). The HTML report prints the warnings as "Data quality: ..." |
| Climate in the same call | The region's default climate zone is used. The warning reads "climate normals unavailable: UpstreamError; using region default" (with the actual error class) and the Evidence chain says "region-default" |
| `GET /plots/{plot_id}/cube` | HTTP 502 `upstream-unavailable`, or 501 `dependency-missing` when rasterio or pystac-client is not installed |
| `GET /geocode` and `GET /reverse-geocode` | HTTP 502 `upstream-unavailable` |
| `POST /plots` in live mode | The reverse lookup that labels the state is optional, and a failure is ignored. If the request named no country and the region bounding boxes cannot place the point, the answer is 422 `country-unresolved` |
| `POST /simulate` with `lat` and `lon` | The region's default zone is used, without a warning |

### The API's own rate limit

`ATLAS_RATE_LIMIT` (default `60/minute`) limits calls to CarbonCreditBuy API per client, by API key prefix or by IP address,
and answers HTTP 429 with `Retry-After: 60`. It protects your server, not the providers. One uncached analysis makes
about a dozen upstream requests ([next section](#what-one-analysis-calls)), and the limits quoted below are lower than
60 a minute for SoilGrids (5 a minute) and Nominatim (1 a second). A busy public deployment can exceed a provider's
limit even when no one exceeds CarbonCreditBuy limit. Only the Nominatim adapter throttles itself.

## What one analysis calls

For the default request (`layers` land cover, vegetation, climate and soil; three years, the current year and the two
before it) in live mode:

| Step | Source | Requests |
| --- | --- | --- |
| Create the plot | Nominatim or Photon | One reverse lookup |
| Land cover | WorldCover | One windowed read per 3° tile the plot touches, normally one |
| Vegetation | STAC catalog and the scene files | One search per requested year, then windowed reads of up to six band files for that year's best scene (the near-infrared and scene-classification bands are read once per index) |
| Climate | Open-Meteo | Two: the archive and the elevation |
| Soil | SoilGrids | One |
| Vegetation cube (`GET /plots/{plot_id}/cube`) | STAC catalog and the scene files | One search for the whole window, then three windowed reads for each month that has a usable scene. Not cached |

A second analysis of the same plot inside a cache TTL repeats no cached request. The vegetation key includes today's
date, so it is refetched after midnight UTC at the latest. The web app gives up on an analysis after 60 seconds.

## The sources

### ESA WorldCover

A 10 m global land-cover map for 2021. CarbonCreditBuy reads only the pixels inside the plot and reports the share of each
class, with the tree-cover and cropland shares as headline values.

| Item | Detail |
| --- | --- |
| Status | Called by plot analysis, the land-cover layer |
| Adapter | [`esa_worldcover`](../../integrations/carboncreditbuy_integrations/esa_worldcover/adapter.py) and its demo twin; the pixel reading is in [`geo_engine.raster.worldcover`](../../packages/geo-engine/geo_engine/raster/worldcover.py) |
| Dataset | ESA WorldCover 2021, version v200. The year is fixed in code. Only the version string and the base URL are settings, and the tile file names use both, so change them together |
| Endpoint | `ESA_WORLDCOVER_BASE_URL`, default `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map`, and `ESA_WORLDCOVER_VERSION`, default `v200` |
| Files | Cloud-optimized GeoTIFF tiles of 3° by 3°, named for the south-west corner, for example `ESA_WorldCover_10m_2021_v200_N12E075_Map.tif`. A plot that crosses a tile edge reads each tile it touches and the shares are merged |
| Access | Anonymous HTTP range reads through GDAL, limited to `.tif` files. Needs `rasterio` from the `live` extra. The adapter's docstring estimates a few hundred kilobytes for a 2 ha plot |
| Credentials | None |
| Rate limits | None quoted in the repository. TODO(verify): the terms of the bucket that hosts the files |
| License | CC BY 4.0 ([terms](https://esa-worldcover.org/en/data-access)) |
| Attribution | `esa-worldcover` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md). The adapter's string matches the master copy |
| Cache | 24 hours. The key is a hash of the polygon, the version and the area |
| Failure | A read error raises `UpstreamError` ("WorldCover tile read failed" and the exception class), and the analysis shows "land cover unavailable" |
| Location sent | The tile file name, which is a 3° cell, and the byte ranges of the window around the plot. No coordinates travel as text |
| Demo twin | Synthetic class shares seeded by the plot id |
| Caveats | A 2021 snapshot, so trees planted since then do not show as tree cover. At 10 m a one-hectare plot has about 100 pixels |

### Sentinel-2 through Earth Search

Earth Search is Element 84's STAC catalog of Sentinel-2 level-2A scenes, whose cloud-optimized files sit on AWS. It is
the default provider (`ATLAS_STAC_PROVIDER=earth-search`) for the vegetation block, the NDVI and NDMI values, and the
vegetation cube (map cells, change-over-time chart and tree-cover detection).

| Item | Detail |
| --- | --- |
| Status | Called by plot analysis (vegetation) and the cube endpoint |
| Adapter | [`earth_search`](../../integrations/carboncreditbuy_integrations/earth_search/adapter.py), a thin subclass of the shared [`stac_common.py`](../../integrations/carboncreditbuy_integrations/stac_common.py) that Copernicus also uses. Search is in [`geo_engine/satellite/stac.py`](../../packages/geo-engine/geo_engine/satellite/stac.py) and cube building in `geo_engine/cube/live.py` |
| Endpoint | `EARTH_SEARCH_STAC_URL`, default `https://earth-search.aws.element84.com/v1`; collection `sentinel-2-l2a` |
| Files read | `red` (B04), `nir` (B08), `swir16` (B11), `rededge1` (B05) and `scl` (scene classification) |
| Search | Scenes that intersect the plot polygon, within 45 days either side of today's date in each requested year, with `eo:cloud_cover` at or below `MAX_CLOUD_COVER_PCT` (default 20), at most 500 items. The scene with the lowest cloud cover is that year's observation, and ties go to the latest |
| Indices | NDVI from near-infrared and red; NDMI from near-infrared and shortwave infrared; NDRE, in the cube only, from near-infrared and red edge. A pixel is kept when the scene classification says vegetation, not vegetated or water (classes 4, 5 and 6) |
| Cube | A monthly composite of the lowest-cloud scene of each month, 36 months by default (6 to 72), in 30 m cells that average 3 by 3 of the 10 m pixels |
| Credentials | None |
| Rate limits | None quoted in the repository. TODO(verify): the Earth Search and AWS Open Data terms |
| License | Copernicus Sentinel data are free, full and open under the [legal notice](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice); the archive is listed in the [AWS Open Data registry](https://registry.opendata.aws/sentinel-2-l2a-cogs/) |
| Attribution | `copernicus-sentinel-2` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md): "Contains modified Copernicus Sentinel data [year]", with the acquisition years. The adapter's string differs ([attribution strings](#attribution-strings)) |
| Cache | Vegetation only: 6 hours, keyed by the polygon, the provider, the years and today's date. The cube is not cached |
| Failure | "STAC search failed" or "Sentinel-2 asset read failed" as `UpstreamError`; a missing library as `DependencyMissingError`. A year with no scene under the cloud limit is not an error: the vegetation block has one observation fewer and a note, and the cube month stays empty |
| Location sent | The exact plot polygon in the search request, and byte-range reads of windows around the plot's bounding box in each scene file |
| Demo twin | `DemoSatelliteAdapter`, shared with Copernicus: a synthetic cube and yearly observations whose scene ids end in `_DEMO` |
| Caveats | At 10 m a small plot has few pixels, so boundary effects are large. Clouds leave gaps, and the cube reports the valid share per month instead of hiding them ([change over time](../user-guide/results-explained.md#change-over-time)) |

### Sentinel-2 through Copernicus Data Space

The Copernicus Data Space Ecosystem (CDSE) offers its own STAC catalog of the same Sentinel-2 level-2A scenes. Select
it with `ATLAS_STAC_PROVIDER=copernicus`. Everything in the Earth Search table applies unless this table says otherwise.

| Item | Detail |
| --- | --- |
| Adapter | [`copernicus`](../../integrations/carboncreditbuy_integrations/copernicus/adapter.py) |
| Endpoint | `COPERNICUS_STAC_URL`, default `https://stac.dataspace.copernicus.eu/v1`; collection `sentinel-2-l2a` |
| Files read | `B04_10m`, `B08_10m`, `B11_20m`, `B05_20m` and `SCL_20m`. The catalog is still evolving, and the adapter's docstring says to verify these keys against the live catalog. They can be overridden only in code (the constructor takes `asset_keys`), not through an environment variable |
| Credentials | Searching is anonymous. Downloading scene files needs a CDSE access token in `COPERNICUS_TOKEN`. The adapter sends it as an `Authorization: Bearer` header on the search and, for reads, through GDAL's HTTP headers, and it never refreshes it. TODO(verify): how to obtain a token, and how long it stays valid |
| Rate limits | None quoted in the repository. TODO(verify): CDSE quotas |
| License | The Sentinel terms above, and CDSE applies its own [terms of use](https://dataspace.copernicus.eu/terms-and-conditions) in addition |
| Provenance id | `sentinel-2-l2a-copernicus`, with "catalogue by ESA/CDSE" added to the attribution |

### Open-Meteo

The historical weather archive (ERA5) and an elevation service, used to classify the plot into an IPCC-style climate
zone. The zone then selects the growth defaults in the carbon model
([methodologies](../regions/IN/METHODOLOGIES.md)).

| Item | Detail |
| --- | --- |
| Status | Called by plot analysis (climate). `POST /simulate` calls it only when the request carries `lat` and `lon`, and the web Simulation Lab does not send them |
| Adapter | [`open_meteo`](../../integrations/carboncreditbuy_integrations/open_meteo/adapter.py) |
| Endpoints | `OPEN_METEO_ARCHIVE_URL`, default `https://archive-api.open-meteo.com/v1/archive`, and `OPEN_METEO_ELEVATION_URL`, default `https://api.open-meteo.com/v1/elevation` |
| Request | The archive is asked for daily mean temperature and precipitation for 2015 to 2024. Mean annual temperature is the mean of the daily values and annual precipitation is the total divided by 10 years. The window is fixed in code; the adapter's docstring says a 30-year normal would be about 11,000 rows per call. A second request returns the elevation, which the adapter's docstring attributes to the Copernicus GLO-90 model. If either request fails, the whole climate step fails |
| Credentials | None for non-commercial use. The adapter has no setting for a subscription key |
| Rate limits | The free tier is for non-commercial use, and the terms cite fewer than 10,000 calls a day ([DATA_LICENSES.md](../licensing/DATA_LICENSES.md)). Each uncached analysis makes two calls. TODO(verify): the current limits and what counts as commercial |
| License | Data CC BY 4.0 ([license](https://open-meteo.com/en/license), [terms](https://open-meteo.com/en/terms)) |
| Attribution | `open-meteo` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md). The adapter's string is longer ([attribution strings](#attribution-strings)) |
| Cache | 7 days. The key is a hash of the exact request, so two plots share an entry only when their centroids match to six decimal places |
| Failure | The climate block falls back to the region's default zone and the analysis warns, as in [what a failure looks like](#what-a-failure-looks-like) |
| Location sent | The plot centroid, rounded to six decimal places (about 0.1 m), once in each request. It is not rounded to the provider's grid |
| Demo twin | A synthetic climate for each region with a small deterministic jitter, and a latitude formula outside the regions |
| Caveats | A 10-year window is not a climate normal in the strict sense, and the zone rules are an approximation marked `assumption` ([`zones.py`](../../packages/geo-engine/geo_engine/climate/zones.py)) |

### SoilGrids

ISRIC's global 250 m model of soil properties. CarbonCreditBuy asks for soil organic carbon at three depth layers and shows
the thickness-weighted mean for 0 to 30 cm. It is a context indicator and does not enter the carbon estimate; the
report calls it a current stock indicator, not a change estimate.

| Item | Detail |
| --- | --- |
| Status | Called by plot analysis (soil) |
| Adapter | [`soilgrids`](../../integrations/carboncreditbuy_integrations/soilgrids/adapter.py) |
| Endpoint | `SOILGRIDS_URL`, default `https://rest.isric.org/soilgrids/v2.0/properties/query` |
| Request | One request for property `soc`, mean value, depths 0-5 cm, 5-15 cm and 15-30 cm. SoilGrids returns decigrams per kilogram; the adapter weights by layer thickness (5, 10 and 15 cm) and divides by 10 to give g/kg. A layer without a value is skipped and listed in `depths_used` |
| Credentials | None |
| Rate limits | At most 5 requests a minute, as the adapter's docstring quotes the ISRIC usage policy. Nothing in the adapter throttles it. TODO(verify): the current policy |
| License | CC BY 4.0 ([ISRIC data policy](https://www.isric.org/about/data-policy)) |
| Attribution | `soilgrids` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md); DATA_LICENSES.md also asks for the citation Poggio et al. (2021). The adapter's string adds the version and the citation |
| Cache | 30 days. The key is a hash of the exact request |
| Failure | The soil block is `null` and the analysis warns "soil data unavailable" |
| Location sent | The plot centroid at six decimal places |
| Demo twin | A synthetic value for each region with a small deterministic jitter |

### Nominatim

The OpenStreetMap geocoder. It powers place search, the reverse lookup that labels a new plot with its state and, when
no country is given, its country.

| Item | Detail |
| --- | --- |
| Status | Called by `GET /geocode`, `GET /reverse-geocode` and `POST /plots`, which in live mode always makes a reverse lookup. Select it with `ATLAS_GEOCODER=nominatim`, the default |
| Adapter | [`nominatim`](../../integrations/carboncreditbuy_integrations/nominatim/adapter.py) |
| Endpoint | `NOMINATIM_URL`, default `https://nominatim.openstreetmap.org` |
| Credentials | `NOMINATIM_USER_AGENT` is mandatory. The adapter raises `ConfigurationError` for an empty value or one that still contains the placeholder `you@example.org`, which is what `.env.example` ships with, so a live deployment must edit it |
| Request | Search sends the text, `format=jsonv2`, `addressdetails`, up to 5 results (the adapter allows 1 to 10) and, if known, a lowercase `countrycodes`. Reverse sends the latitude, the longitude and zoom 10. Country, state and district come from the address fields, which vary by country |
| Rate limits | The public instance allows 1 request a second, requires an identifying `User-Agent`, expects results to be cached and refuses bulk geocoding; DATA_LICENSES.md also lists "no bulk or autocomplete" ([usage policy](https://operations.osmfoundation.org/policies/nominatim/); TODO(verify): the current text). `GEOCODER_MIN_INTERVAL_SECONDS` (default 1.0) spaces uncached requests through a process-wide lock |
| License | ODbL 1.0 for the data ([license](https://opendatacommons.org/licenses/odbl/1-0/)) |
| Attribution | `nominatim` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md): "Search by Nominatim · © OpenStreetMap contributors". The adapter's string is only "© OpenStreetMap contributors" |
| Cache | 24 hours. A search key is a hash of the request. A reverse key rounds the coordinates to four decimal places (about 11 m), so neighboring plots share an entry |
| Failure | `/geocode` and `/reverse-geocode` answer 502 `upstream-unavailable`. Plot creation carries on without the label |
| Location sent | The search text and the country code; for a reverse lookup, the exact centroid (not rounded) |
| Demo twin | Four fixed places (near Bengaluru, Macon, Sevilla and Dresden) and a reverse lookup by region bounding box |
| Caveats | The web search box sends a request about 350 ms after typing pauses, from the third character, which is search-as-you-type. Check that against the usage policy, and self-host Nominatim or use Photon for a public deployment ([mapping architecture](../architecture/mapping-architecture.md)). Place names come in the language the mappers used |

### Photon

A second geocoder over the same OpenStreetMap data, run by komoot. Select it with `ATLAS_GEOCODER=photon`.

| Item | Detail |
| --- | --- |
| Status | Called wherever Nominatim would be, when selected in live mode |
| Adapter | [`photon`](../../integrations/carboncreditbuy_integrations/photon/adapter.py) |
| Endpoint | `PHOTON_URL`, default `https://photon.komoot.io`. Search is `/api` with the text, a limit and `lang=en`; reverse is `/reverse` with the coordinates |
| Credentials | None. Requests carry the default `User-Agent`; no setting changes it |
| Country | The country code is not sent. The adapter filters the results by country after they arrive and returns all of them when none match |
| Rate limits | The adapter's docstring says the public instance asks for fair use, with no heavy bulk traffic and an identifying `User-Agent`, and that production deployments should self-host. Nothing throttles the adapter. TODO(verify): the provider's current terms |
| License | ODbL 1.0 for the data, Apache-2.0 for the software ([Photon](https://github.com/komoot/photon)) |
| Attribution | `photon` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md): "Search by Photon (komoot) · © OpenStreetMap contributors". The adapter's string is only "© OpenStreetMap contributors" |
| Cache | 24 hours |
| Failure | As for Nominatim |
| Location sent | The search text; for a reverse lookup, the exact centroid |
| Demo twin | None. The Nominatim twin answers in demo mode |

### USDA NASS Quick Stats

County crop statistics for the United States, meant for the "other farm income" context. Details for United States
users are in [US data sources](../regions/US/DATA_SOURCES.md).

| Item | Detail |
| --- | --- |
| Status | Built and tested. `ModeRouter` can construct it, but no service calls it in v0.1 |
| Adapter | [`usda_nass`](../../integrations/carboncreditbuy_integrations/usda_nass/adapter.py) |
| Endpoint | `USDA_NASS_API_URL`, default `https://quickstats.nass.usda.gov/api/api_GET/` |
| Credentials | A free key in `USDA_NASS_API_KEY` ([request one](https://quickstats.nass.usda.gov/api)). The adapter refuses an empty key, and in live mode the router substitutes the demo twin. The key travels as a query parameter; error messages never include it |
| Request | Survey data, crops sector, county level, for a commodity (upper-cased), a two-digit state code, a three-digit county code and a range of years, optionally one statistic |
| Limits | A response is capped at 50,000 records, and errors come back as HTTP 400 or 413. Rate limits are not published, as the adapter's docstring says, so it caches |
| License | Public domain as a work of the US Government, and NASS asks users to acknowledge the source ([DATA_LICENSES.md](../licensing/DATA_LICENSES.md)) |
| Attribution | `usda-nass` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md): "Source: USDA National Agricultural Statistics Service, Quick Stats". The adapter's string differs |
| Cache | 24 hours |
| Location sent | No coordinates; state and county codes, a commodity and years |
| Demo twin | Synthetic values for a "DEMO COUNTY" |
| Caveats | A value of "(D)" (withheld) or "(Z)" (rounds to zero) comes back as no value, not as zero |

### US Census Geocoder

Turns a coordinate pair into state and county codes, which Quick Stats needs.

| Item | Detail |
| --- | --- |
| Status | Built and tested, and not called in v0.1. County labels come from Nominatim or Photon |
| Adapter | [`census_geocoder`](../../integrations/carboncreditbuy_integrations/census_geocoder/adapter.py) |
| Endpoint | `CENSUS_GEOCODER_URL`, default `https://geocoding.geo.census.gov/geocoder/geographies/coordinates` |
| Credentials | None |
| Request | One coordinate pair for the current benchmark and vintage, asking for the county and state layers. A point outside US counties raises `NotFoundError` |
| Limits | Single-point lookups only; the service has a separate batch endpoint for bulk work ([service](https://geocoding.geo.census.gov/geocoder/)). TODO(verify): the request limits |
| License | Public domain as a work of the US Government |
| Attribution | `census-geocoder` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md): "County lookup: U.S. Census Bureau Geocoder". The adapter's string differs |
| Cache | 30 days |
| Location sent | The exact centroid, if it were wired. Decide whether a generalized point is enough before wiring it ([geolocation](../privacy/geolocation.md)) |
| Demo twin | Answers with one fixed county for points inside the US bounding box and raises `NotFoundError` elsewhere |

### data.gov.in

India's Open Government Data platform, meant for district crop production in the "other farm income" context. Details
for India are in [India data sources](../regions/IN/DATA_SOURCES.md).

| Item | Detail |
| --- | --- |
| Status | Built and tested. `ModeRouter` can construct it, but no service calls it in v0.1 |
| Adapter | [`data_gov_in`](../../integrations/carboncreditbuy_integrations/data_gov_in/adapter.py) |
| Endpoint | `DATA_GOV_IN_API_URL`, default `https://api.data.gov.in/resource`, plus the resource id in `DATA_GOV_IN_CROP_RESOURCE_ID`. The default id is marked "verify" in `.env.example`: resource ids change when datasets are republished |
| Credentials | A free key in `DATA_GOV_IN_API_KEY` ([data.gov.in](https://data.gov.in/)). The adapter refuses an empty key, and in live mode the router substitutes the demo twin |
| Request | The key, `format=json`, a limit of 1 to 1,000, an offset and `filters[field]=value`. The field names (`state_name`, `district_name`, `crop`) are constructor arguments, which the router does not set, so check them against the resource's field list before use |
| Rate limits | The platform caps each key per minute and per day, as the adapter's docstring says; see your key's page. TODO(verify): the numbers |
| License | Government Open Data License - India ([GODL](https://data.gov.in/government-open-data-license-india)) |
| Attribution | `data-gov-in` in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md): it must name the ministry or department that publishes the resource. The adapter's fixed string does not |
| Cache | 24 hours |
| Location sent | State, district and crop names, no coordinates |
| Demo twin | Synthetic crop records for 2019 to 2023, for mango unless another crop is asked for |
| Caveats | District names must be matched by hand (spelling, renamed districts), and units differ by crop |

## Map imagery and basemaps

The map layers in the browser are not adapters. The browser requests tiles from the hosts you configure, so each tile
host sees the viewport and the user's IP address ([geolocation](../privacy/geolocation.md#residual-risks-and-mitigations)).
That includes the imagery provider the map uses by default.

### Basemap

| Variable | Purpose | Notes |
| --- | --- | --- |
| `VITE_BASEMAP_STYLE_URL` | MapLibre style for the basemap | Default `https://tiles.openfreemap.org/styles/liberty`, for development only ([MAP_LICENSES.md](../licensing/MAP_LICENSES.md)) |
| `VITE_BASEMAP_PMTILES_URL` | A Protomaps archive you host | OpenStreetMap data under the ODbL; the attribution is required |

These are read when the web app is built. In the Docker image the web server also has to allow each tile host, or the
browser blocks it ([setup](../developer-guide/setup.md#web-container-run-time),
[troubleshooting](../developer-guide/troubleshooting.md#a-basemap-or-imagery-works-with-npm-run-dev-but-not-in-docker)).

### Satellite and aerial imagery

The map's Satellite view shows imagery from one of the providers in the
[reference table](#imagery-providers-for-the-satellite-view). Research and licenses are in
[imagery-providers.md](../research/imagery-providers.md) and [MAP_LICENSES.md](../licensing/MAP_LICENSES.md).

1. [`config/imagery/providers.yaml`](../../config/imagery/providers.yaml) holds each provider's tile URL template,
   maximum zoom, coverage, license, attribution, key requirement, whether commercial use and automated analysis are
   allowed, and a `verification_status`. A provider that is not `verified` fails the production data-quality test.
2. `GET /api/v1/imagery/providers?country=XX` returns the list from the
   [imagery service](../../apps/api/app/services/imagery.py). Providers that cover the country come first, and
   `recommended` is the entry for that country in `default_by_country`, else the global default. A provider whose key
   is missing comes back with `available: false`, `url: null` and a reason ("Set ESRI_API_KEY to enable"), so the
   browser never receives an unfilled `${...}` placeholder.
3. The web app uses the user's choice from Settings, "Map imagery", else the recommended provider, else the first
   available one. The choice is stored in the browser, per country. The attribution bar shows the active provider's
   attribution while the Satellite view is on. If six or more tile requests fail, the bar says "Satellite tiles could
   not be loaded - showing the plain map", and the basemap stays underneath.
4. Setting `VITE_SATELLITE_TILES_URL` (and `VITE_SATELLITE_ATTRIBUTION`) at build time overrides the list for everyone.
   The settings page then says so, and the deployer carries the provider's terms ([`mapEnv.ts`](../../apps/web/src/config/mapEnv.ts)).

What the defaults are, and why:

- The global default is the EOX Sentinel-2 cloudless 2016 mosaic: keyless, CC BY 4.0, 10 m. The free endpoint is "as
  is" and rate limited, so production traffic needs a self-hosted copy or an agreement with EOX. A self-hosted copy
  needs EOX's written confirmation of the license first, because a 2017 EOX post described the downloadable tiles as
  CC BY-SA 4.0.
- Where open orthophotos exist, they are the default: the USGS "Imagery Only" layer in the United States, IGN in
  France, PNOA in Spain and PDOK in the Netherlands. A plot anywhere else, and a deployment set to the EU with no
  plot, gets the global default. India has no verified open high-resolution tile service, so it falls back to the
  global default as well.
- Esri World Imagery is an optional layer for display only, under the deployer's own license and key. It is never the
  default (a data-quality test enforces that), and its terms bar automated analysis.
- The EOX 2016 and 2017 layers are CC BY 4.0. Every later EOX year, including 2025, is CC BY-NC-SA 4.0, which is not open
  data and fits only a clearly non-commercial deployment.

How a key is handled. `ESRI_API_KEY` is read by the API (from the environment or `.env`) and inserted, URL-encoded, into
the Esri URL. The browser needs the full tile URL, so every user of the web app can see the key. Use a
referrer-restricted key that is good for basemap tiles only. The service never logs it, and it substitutes no other
variable that the application uses for another integration (such as `LLM_API_KEY` or `USDA_NASS_API_KEY`).
`.env.example` does not list `ESRI_API_KEY` yet; [setup](../developer-guide/setup.md#api) does.

Analysis rule. Imagery on screen is for viewing. Run segmentation, machine learning or feature extraction only on
providers with `analysis_allowed: true`, or on the user's own imagery. CarbonCreditBuy runs none of it on these tiles.

Before a new provider ships, CLAUDE.md principles 5 and 6 apply: a row in [DATA_LICENSES.md](../licensing/DATA_LICENSES.md)
and [MAP_LICENSES.md](../licensing/MAP_LICENSES.md), a string in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md), a row in
the table above and a provider entry whose license, attribution and key rule were read from the provider's own terms
([adding an integration](../developer-guide/adding-an-integration.md#which-kind-of-integration-is-it)).

## Attribution strings

[ATTRIBUTION.md](../licensing/ATTRIBUTION.md) is the master copy and says to copy strings verbatim. The string that
travels in a result's provenance comes from each adapter, and `GET /attribution` serves a third list. In version 0.1
they differ. Display the master copy in your own interface and publications until the code is reconciled.

| Source | Master id | Adapter `SOURCE.id` | What the adapter's text changes |
| --- | --- | --- | --- |
| ESA WorldCover | `esa-worldcover` | `esa-worldcover` | Nothing |
| Sentinel-2 | `copernicus-sentinel-2` | `sentinel-2-l2a-earth-search`, `sentinel-2-l2a-copernicus` | Uses the current year, not the acquisition year, and adds "processed by CarbonCreditBuy" and "catalogue by Element 84" or "catalogue by ESA/CDSE" |
| Open-Meteo | `open-meteo` | `open-meteo` | Adds "(CC BY 4.0); ERA5 © ECMWF/Copernicus; elevation © Copernicus DEM GLO-90". The master list's Copernicus DEM entry (`copernicus-dem`) names GLO-30 |
| SoilGrids | `soilgrids` | `soilgrids` | Adds "2.0" and the Poggio et al. citation |
| Nominatim | `nominatim` | `osm-nominatim` | Omits "Search by Nominatim" |
| Photon | `photon` | `osm-photon` | Omits "Search by Photon (komoot)" |
| USDA NASS | `usda-nass` | `usda-nass-quickstats` | Omits "Source:" and adds "database" |
| Census geocoder | `census-geocoder` | `census-geocoder` | "U.S. Census Bureau Geocoding Services" instead of "County lookup: U.S. Census Bureau Geocoder" |
| data.gov.in | `data-gov-in` | `data-gov-in` | Omits the ministry or department |

`GET /attribution` serves eight items: `osm`, `esa-worldcover`, `copernicus-sentinel-2`, `open-meteo`, `soilgrids`,
`maplibre`, `usda-nass` and `data-gov-in`. All except `osm` are worded differently from the master copy, and there are
no entries for Nominatim, Photon, the Census geocoder, Protomaps or the Copernicus DEM.

Imagery attribution travels differently. Each provider's text is the `attribution` field of its entry in
`GET /imagery/providers`, and the web app shows the text of the provider on screen. ATTRIBUTION.md lists the same
strings, copied from `config/imagery/providers.yaml`, so the two agree today; change both together.

## Known gaps

- **No per-adapter READMEs.** CLAUDE.md principle 6 asks for them. This page and the
  [integrations README](../../integrations/README.md) stand in.
- **Three adapters are not called.** NASS, the Census geocoder and data.gov.in are built and tested, but no service
  uses them, so the "other farm income" lines are empty for every region.
- **Memory-only cache.** `ATLAS_CACHE_DIR` is unused. The architecture and privacy pages
  ([system architecture](../architecture/system-architecture.md), [privacy design](../privacy/privacy-design.md)) say
  raster windows are cached on disk; the code does not do that. The code keys every answer on the exact request, so a
  cached answer is not shared by neighboring plots (except for reverse geocoding, which rounds to four decimal places).
- **The exact polygon goes to the STAC catalog.** The privacy pages describe bounding boxes and centroids. The
  satellite search sends the plot polygon itself. A deployer who cannot allow that can run a STAC API of their own and
  set `EARTH_SEARCH_STAC_URL` or `COPERNICUS_STAC_URL` to it, or run demo mode.
- **No rounding to a provider's grid.** [Geolocation](../privacy/geolocation.md) says the climate point may be rounded
  to the provider's grid. The code sends six decimal places. The same page says US reverse geocoding uses the Census
  geocoder; it uses Nominatim or Photon.
- **Search as you type.** The search box can send a request on every pause in typing, while the Nominatim policy as
  DATA_LICENSES.md quotes it says "no bulk or autocomplete".
- **Fixed in code.** The WorldCover year (2021), the Open-Meteo window (2015 to 2024), the cache TTLs, the 45-day
  satellite search window, the cube cell size (30 m) and the Copernicus file keys cannot be changed by a setting.
  There is no setting for an Open-Meteo subscription key and no refresh for the Copernicus token.
- **Different timeouts.** WorldCover and the STAC adapters do not use the 20 second timeout and one retry of
  `HttpAdapter`.
- **Attribution wording and ids differ** between ATTRIBUTION.md, the adapters and `GET /attribution`
  ([attribution strings](#attribution-strings)).
- **Imagery providers have not been seen in a browser.** The research checked that a tile exists near each provider's
  maximum zoom, not what the tile shows, and not the provider's CORS headers. Open each one in the running app before
  a release. Whether Esri counts a free open-source deployment as commercial use is not confirmed either.
- **The Docker web image allows no imagery host.** Its Content-Security-Policy names none (`ATLAS_EXTRA_IMG_SRC` is
  empty), so the Satellite view stays empty until a deployer lists the hosts of the providers it enables
  ([troubleshooting](../developer-guide/troubleshooting.md#a-basemap-or-imagery-works-with-npm-run-dev-but-not-in-docker)).
- **Label glyphs come from the MapLibre demo host.** With `VITE_BASEMAP_PMTILES_URL` the app's built-in style loads
  glyphs from `https://demotiles.maplibre.org/font/`, an address written in `mapStyle.ts` instead of an environment
  variable (CLAUDE.md principle 6). The demo host is for development, and it sees each viewer's address.
- **The search box shows no geocoder credit.** ATTRIBUTION.md asks for "Search by Nominatim · © OpenStreetMap
  contributors" with search results. The API returns the adapter's credit in the `attribution` field of `/geocode`,
  and the web app does not display it. The map credits OpenStreetMap only through the basemap style.
- **`.env.example` is incomplete.** It lacks several settings that the API reads (for example `ESRI_API_KEY`,
  `ATLAS_SEED_DEMO` and `ATLAS_MAX_UPLOAD_MB`; [setup](../developer-guide/setup.md#environment-variables) lists them
  all), and its `S3_*` variables are read by no code.

Some of these are [starter issues](../community/starter-issues.md): the missing adapter READMEs (issue 14), the
imagery check in a browser (issue 3) and the missing search credit (issue 9). The others are larger or need a decision
first, and are in [roadmap ideas](../community/roadmap-ideas.md).

## Related pages

[Integrations README](../../integrations/README.md) · [Data licenses](../licensing/DATA_LICENSES.md) ·
[Map licenses](../licensing/MAP_LICENSES.md) · [Attribution strings](../licensing/ATTRIBUTION.md) ·
[Adding an integration](../developer-guide/adding-an-integration.md) ·
[India data sources](../regions/IN/DATA_SOURCES.md) · [US data sources](../regions/US/DATA_SOURCES.md) ·
[EU data sources](../regions/EU/DATA_SOURCES.md) · [Geolocation](../privacy/geolocation.md) ·
[Imagery research](../research/imagery-providers.md)
