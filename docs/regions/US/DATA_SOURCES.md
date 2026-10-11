# Data sources — United States

Global datasets (ESA WorldCover, Sentinel-2, Open-Meteo, SoilGrids, OpenStreetMap) serve US plots exactly as they serve
plots elsewhere. This page covers the US-specific sources: how to get access, what CarbonCreditBuy does with them today,
and
what it does not use. Licenses are consolidated in
[`docs/licensing/DATA_LICENSES.md`](../../licensing/DATA_LICENSES.md), and every source's endpoint, key, cache and
failure behavior is in [FREE_APIS.md](../../data-sources/FREE_APIS.md).

**Status in version 0.1.** The two US adapters below are built and tested, and the API's mode router can construct them,
but no service calls them yet. The "other farm income" context therefore stays empty for US plots, and the county shown
for a plot comes from reverse geocoding, not from the Census Geocoder
([integrations README](../../../integrations/README.md#known-gaps)).

## USDA NASS Quick Stats: county crop statistics

The National Agricultural Statistics Service publishes crop statistics through its Quick Stats API. CarbonCreditBuy
would use
them for the "other farm income" context: area, production and yield for a county and a crop such as pecan, walnut or
apple ([`config/regions/US.yaml`](../../../config/regions/US.yaml)).

| Item | Detail |
| --- | --- |
| Adapter | [`usda_nass`](../../../integrations/carboncreditbuy_integrations/usda_nass/adapter.py), with an offline demo twin that returns synthetic values labeled `synthetic-demo` |
| Endpoint | `USDA_NASS_API_URL`, default `https://quickstats.nass.usda.gov/api/api_GET/` |
| Key | Free. Request one on the [Quick Stats API page](https://quickstats.nass.usda.gov/api) and set `USDA_NASS_API_KEY`. In live mode an empty key silently selects the demo twin, so check the `mode` and the source in what you receive |
| Query | Survey data, crops sector, county level; a commodity name (the adapter upper-cases it), a two-digit state code, a three-digit county code and a range of years |
| Fields returned | Year, commodity, statistic (for example production, yield or area harvested), value, unit, state and county |
| Limits | A response is capped at 50,000 records, and errors come back as HTTP 400 or 413. Rate limits are not published, so the adapter caches for 24 hours |
| License | Public domain as a work of the US Government ([DATA_LICENSES.md](../../licensing/DATA_LICENSES.md)) |
| Attribution | "Source: USDA National Agricultural Statistics Service, Quick Stats" ([ATTRIBUTION.md](../../licensing/ATTRIBUTION.md)) |
| Caveats | A value of "(D)" (withheld) or "(Z)" (rounds to zero) comes back as no value, not as zero. Units differ by crop. Coverage varies by crop and year (verify for your crop). County figures are county averages, not your farm |

## US Census Bureau Geocoder: county lookup

| Item | Detail |
| --- | --- |
| Purpose | Turn a coordinate pair into state and county codes, which Quick Stats needs |
| Adapter | [`census_geocoder`](../../../integrations/carboncreditbuy_integrations/census_geocoder/adapter.py), with a demo twin that answers for points inside the US bounding box only |
| Endpoint | `CENSUS_GEOCODER_URL`, default `https://geocoding.geo.census.gov/geocoder/geographies/coordinates` |
| Key | None |
| Query | One coordinate pair per request, for the current benchmark and vintage, asking for the county and state layers. The adapter raises "not found" for a point outside US counties |
| Cache | 30 days |
| License | Public domain as a work of the US Government |
| Attribution | "County lookup: U.S. Census Bureau Geocoder" ([ATTRIBUTION.md](../../licensing/ATTRIBUTION.md)) |
| Fair use | Single-point lookups only; the service has a separate batch endpoint for bulk work |

**Privacy when this is wired.** The lookup sends a coordinate pair to a US government server. A county is coarse, so use
a generalized point unless the exact point is needed, and record the decision in the privacy documents before merging
([geolocation](../../privacy/geolocation.md)). The geolocation page already says the US lookup goes to the Census
Geocoder; in version 0.1 it goes to Nominatim like every other country.

## Place search and counties from Nominatim

When the selected country is the United States, the search box asks Nominatim for results in the US only. The result
carries state and county names when OpenStreetMap has them. The public Nominatim instance allows one request per second
and requires an identifying `User-Agent`; a deployment with heavy use should self-host Nominatim or Photon
([mapping architecture](../../architecture/mapping-architecture.md)).

## Earth observation specifics

- Sentinel-2 scenes over the US come from Earth Search on AWS by default, or from the Copernicus Data Space Ecosystem.
  Cloud cover varies with season and region, and the 36-month vegetation cube shows how many pixels were valid in each
  month instead of hiding gaps ([change over time](../../user-guide/results-explained.md#change-over-time)).
- WorldCover 2021 is the land-cover baseline. It is a 2021 snapshot, so trees planted since then do not show as tree
  cover.
- Open-Meteo normals set the climate zone in live mode: the server classifies mean annual temperature, annual
  precipitation and elevation into an IPCC-style zone ([METHODOLOGIES.md](METHODOLOGIES.md)). Without them the region
  default, `warm_temperate_moist`, applies to every US plot, and it will not suit every part of the country.
- SoilGrids is a global 250 m model of soil organic carbon. More detailed US soil survey data exist and are not used
  (see below).

## Imagery for the map

The map's **Satellite** view loads raster tiles from a provider that the API recommends for the plot's country
(`GET /api/v1/imagery/providers?country=US`, from
[`config/imagery/providers.yaml`](../../../config/imagery/providers.yaml)).
For the United States the recommended provider is USGS Imagery Only. A person can choose another one under **Settings**,
**Map imagery**. Imagery is for viewing: CarbonCreditBuy does not analyze these tiles. The license, attribution and
analysis
rule of every provider are in [MAP_LICENSES.md](../../licensing/MAP_LICENSES.md), and the research is in
[imagery-providers.md](../../research/imagery-providers.md).

| Provider (id) | Role for US plots | License | Attribution to show | Key | Max zoom |
| --- | --- | --- | --- | --- | --- |
| USGS The National Map, Imagery Only (`usgs-imagery-only`) | Default | Public domain (USGS information policy; NAIP) | USDA, USGS The National Map: Orthoimagery | None | 16 |
| EOX Sentinel-2 cloudless 2016 (`eox-s2cloudless-2016`) | Global fallback at 10 m | CC BY 4.0 | The EOxCloudless text in the config, which mentions Copernicus Sentinel data | None | 14 |
| Esri World Imagery (`esri-world-imagery`) | Optional, display only | Esri Master License Agreement (proprietary) | Esri, Vantor, Earthstar Geographics, and the GIS User Community | `ESRI_API_KEY` | 19 |

The EOX 2017 layer has the same terms as 2016. The EOX 2025 layer is CC BY-NC-SA 4.0 and only for clearly
non-commercial deployments. Esri's terms prohibit using its tiles as input to automated extraction, and whether a free
open-source deployment counts as commercial use is not confirmed, so the config keeps `review-terms`.

Notes on the USGS layer, from the research of 2026-10-05:

- NAIP photographs are 0.6 to 1 m per pixel, but the tile cache stops at zoom 16 (about 1.6 to 2.2 m per pixel across
  the contiguous states), so the map over-zooms beyond it and individual trees are not visible. For analysis, get NAIP
  source data and do not harvest tiles.
- The config marks the layer `analysis_allowed: true`, because USGS information is public domain. A 2017 Farm Service
  Agency notice said the agency was considering a licensed data model for future NAIP, so re-check the terms before you
  rely on newly acquired imagery.
- Not confirmed: coverage in Alaska, Hawaii and the territories, and any rate limit or fair-use policy (none was found).
- A web container behind the Docker image only loads tiles from hosts listed in `ATLAS_EXTRA_IMG_SRC`; the development
  server has no such list
  ([troubleshooting](../../developer-guide/troubleshooting.md#a-basemap-or-imagery-works-with-npm-run-dev-but-not-in-docker)).

## Candidates not integrated

These are datasets contributors could evaluate. None has been researched for CarbonCreditBuy: the license, endpoint,
coverage and privacy impact of each are TODO(verify). Use the "Data source" issue form
([`data_source.yml`](../../../.github/ISSUE_TEMPLATE/data_source.yml)) and
[adding an integration](../../developer-guide/adding-an-integration.md).

| Candidate | What it could add |
| --- | --- |
| USDA NASS Cropland Data Layer | Crop type at field scale, to complement county statistics |
| USGS National Land Cover Database | A US-specific land-cover baseline to compare with WorldCover |
| NRCS soil survey data | Detailed soil properties to replace the global SoilGrids estimate |
| PRISM climate normals | Finer climate normals for the climate-zone step |
| USDA Forest Service Forest Inventory and Analysis tables | Growth and biomass references for US tree species, which COMET-Planner uses ([PROGRAMS.md](PROGRAMS.md)) |

## What we do not use

Producer or farm identifiers, and any record tied to a person, are out of scope: the platform needs no identity and must
not become a reason to collect it ([farmer data](../../privacy/farmer-data.md)).

## Related pages

[README.md](README.md) · [PROGRAMS.md](PROGRAMS.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[FREE_APIS.md](../../data-sources/FREE_APIS.md)
