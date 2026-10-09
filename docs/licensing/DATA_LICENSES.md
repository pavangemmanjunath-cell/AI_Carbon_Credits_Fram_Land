# Data licenses

Every external dataset or API the platform uses is listed here with its
license or terms, the attribution we show, and whether we store a local
copy. CLAUDE.md principle 5 makes this table mandatory: an adapter whose
source is missing from it does not ship. The same information is embedded
in each adapter's `provenance()` and surfaced through `GET /attribution`
and in reports ([ATTRIBUTION.md](ATTRIBUTION.md)); the wording of those
copies differs in places, and the master text is ATTRIBUTION.md
([the differences](../data-sources/FREE_APIS.md#attribution-strings)). Terms
change; the *Checked* column records when a maintainer last read the source
page. Endpoints, keys, rate limits and failure behavior for each source are
in [FREE_APIS.md](../data-sources/FREE_APIS.md); the terms of the map
software and of the imagery providers are summarized in
[MAP_LICENSES.md](MAP_LICENSES.md).

## Core datasets

| Source | Purpose | Coverage | License / terms | Attribution text | Store locally? | Checked |
| --- | --- | --- | --- | --- | --- | --- |
| **ESA WorldCover 2021 v200** (10 m land cover) — <https://esa-worldcover.org/> | Land-cover class shares per plot; tree-cover and cropland shares; baseline evidence | Global | CC BY 4.0 (<https://esa-worldcover.org/en/data-access>) | © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium | The license allows copies and mirrors of the tiles. v0.1 reads only the pixels inside the plot over HTTP and keeps the computed class shares in a 24-hour in-memory cache; nothing is written to disk | 2026-10 |
| **Copernicus Sentinel-2 L2A** via Earth Search STAC (<https://earth-search.aws.element84.com/v1>, data on AWS Open Data <https://registry.opendata.aws/sentinel-2-l2a-cogs/>) or Copernicus Data Space Ecosystem STAC (<https://dataspace.copernicus.eu/>) | NDVI, NDMI, time series, 36-month cube | Global, 5-day revisit | Copernicus Sentinel data: free, full and open under the Legal notice on the use of Copernicus Sentinel Data and Service Information (<https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice>); CDSE additionally applies its terms of use (<https://dataspace.copernicus.eu/terms-and-conditions>) | Contains modified Copernicus Sentinel data [year] | The terms allow copies. v0.1 reads band windows (B04, B08, B11, B05, SCL) over HTTP and keeps the computed vegetation indices in a 6-hour in-memory cache (the 4D cube is not cached); scene ids are recorded in provenance | 2026-10 |
| **OpenStreetMap** (basemap data, geocoding data) — <https://www.openstreetmap.org/copyright> | Basemap via Protomaps PMTiles; geocoding via Nominatim/Photon | Global | Open Database License (ODbL) 1.0 (<https://opendatacommons.org/licenses/odbl/1-0/>); produced works (rendered maps) need attribution; derivative databases must be shared alike | © OpenStreetMap contributors | If you host a PMTiles extract it is a derivative database: publish the extraction recipe. The repository stores no OpenStreetMap data | 2026-10 |
| **Nominatim** (OSMF public instance) — <https://nominatim.openstreetmap.org> | Place search and reverse geocoding | Global | Nominatim Usage Policy (<https://operations.osmfoundation.org/policies/nominatim/>): max 1 request/s, identifying `User-Agent` or `Referer`, no bulk or autocomplete, display attribution; data ODbL | © OpenStreetMap contributors (results); "Search by Nominatim" in the search box (the web app does not show it yet; [known gaps](../data-sources/FREE_APIS.md#known-gaps)) | Results are cached in memory for 24 hours (reduces load; results stay ODbL) | 2026-10 |
| **Photon** (komoot) — <https://photon.komoot.io/> | Alternative geocoder (`ATLAS_GEOCODER=photon`) | Global | Fair-use public API; data ODbL; software Apache-2.0 (<https://github.com/komoot/photon>) | © OpenStreetMap contributors | Results are cached in memory for 24 hours | 2026-10 |
| **Protomaps basemap builds** — <https://docs.protomaps.com/basemaps/downloads> | Vector basemap tiles (PMTiles) | Global | Tiles contain OSM (ODbL) and Natural Earth (public domain) data; Protomaps asks for attribution of its builds; software BSD-3-Clause ([MAP_LICENSES.md](MAP_LICENSES.md)) | Protomaps © OpenStreetMap | Yes — the whole point: extract and host your own | 2026-10 |
| **Open-Meteo** archive and elevation APIs — <https://open-meteo.com/> | Climate normals → IPCC climate zone; elevation | Global | Data CC BY 4.0 (<https://open-meteo.com/en/license>); API free for non-commercial use with fair-use limits (the terms cite fewer than 10,000 calls/day), commercial use requires an API subscription (<https://open-meteo.com/en/terms>) — verify the current limits | Weather data by Open-Meteo.com | Responses are cached in memory for 7 days (normals change slowly), keyed by the exact request, not a rounded point | 2026-10 |
| **ISRIC SoilGrids 2.0** — <https://www.isric.org/explore/soilgrids> | Soil organic carbon 0–30 cm as context | Global, 250 m | CC BY 4.0 (<https://www.isric.org/about/data-policy>); REST API fair use | SoilGrids — ISRIC World Soil Information (Poggio et al. 2021, <https://doi.org/10.5194/soil-7-217-2021>) | Responses are cached in memory for 30 days | 2026-10 |
| **Copernicus DEM GLO-30** — <https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model> | Optional terrain tiles; elevation cross-check | Global, 30 m | License for the use of the Copernicus WorldDEM-30 / GLO-30 (free access, attribution required); verify the current license text on the collection page | Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved | Yes — as self-built terrain PMTiles, if the deployer enables terrain | 2026-10 |

## Imagery providers (map tiles)

The Satellite view loads these from the browser, so the Atlas stores no tiles. The entries are in
[`config/imagery/providers.yaml`](../../config/imagery/providers.yaml) and each was verified from the provider's own
terms on 2026-10-05 ([research](../research/imagery-providers.md), which also lists what could not be confirmed).
"Analysis" means segmentation, machine learning or feature extraction on the tiles. The Atlas runs none; its vegetation
indices come from Sentinel-2 through the STAC adapters. Only the providers marked analysis-allowed may be used that
way, and only the user's own imagery otherwise.

| Source | Purpose | Coverage | License / terms | Attribution text | Store locally? | Checked |
| --- | --- | --- | --- | --- | --- | --- |
| **Esri World Imagery** (`esri-world-imagery`) — <https://www.esri.com/content/dam/arcgisonline/docs/tou_summary.pdf> | Optional, display-only Satellite view with sharper imagery, for a deployer who holds an Esri license | Global; 15 m worldwide, 1.2 m to 30 cm in many places, 15 cm to 3 cm in some | Esri Master License Agreement (proprietary). Key required: ArcGIS Location Platform account, `ESRI_API_KEY`. **Display only:** automated analysis is not allowed; harvesting, redistributing and self-hosting tiles are prohibited; Living Atlas content may not be used commercially in your own product. Whether a free open-source deployment counts as commercial is not confirmed (`review-terms`) | Esri, Vantor, Earthstar Geographics, and the GIS User Community | No | 2026-10-05 |
| **USGS The National Map, USGS Imagery Only** (`usgs-imagery-only`) — <https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer> | Default Satellite view in the United States | United States; NAIP 0.6 to 1 m, tile cache ends at zoom 16 | Public domain ([USGS](https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs)). No key. Commercial use and analysis allowed; no rate-limit policy was found. For bulk analysis use the NAIP source data. FSA notice AP-26 (2017) mentions a possible licensed NAIP model, so re-check for newer imagery | USDA, USGS The National Map: Orthoimagery | No | 2026-10-05 |
| **IGN Géoplateforme, BD ORTHO** (`ign-france-orthophotos`) — <https://data.geopf.fr/annexes/ressources/wmts/ortho.xml> | Default Satellite view in France | France; 20 cm | Licence Ouverte 2.0 (Etalab), reached through the Géoplateforme terms and the data.gouv.fr dataset ([text](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0)). No key. Commercial use and analysis allowed; name the source and the date of last update. The tile service is outside the documented rate limits | Source : IGN - Institut national de l'information géographique et forestière - Licence Ouverte 2.0 | No | 2026-10-05 |
| **IGN España, PNOA máxima actualidad** (`ign-spain-pnoa`) — <https://www.ign.es/wmts/pnoa-ma> | Default Satellite view in Spain | Spain; 25 to 50 cm (Sentinel-2 10 m at small scales) | CC BY 4.0 scne.es ([conditions](https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf)). No key. Commercial use and analysis allowed; the credit must be visible at the foot of the map, and derived works say "Obra derivada de" | PNOA CC-BY 4.0 scne.es | No | 2026-10-05 |
| **PDOK Luchtfoto RGB** (`pdok-luchtfoto`) — <https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0> | Default Satellite view in the Netherlands | Netherlands; 8 cm (5 cm in places) | CC BY 4.0 ([Beeldmateriaal Nederland](https://www.beeldmateriaal.nl/dataroom)). No key. Commercial use and analysis allowed; no fair-use policy was confirmed | Beeldmateriaal Nederland (beeldmateriaal.nl), CC BY 4.0, via PDOK | No | 2026-10-05 |
| **EOX Sentinel-2 cloudless 2016** (`eox-s2cloudless-2016`) — <https://maps.eox.at/> | Global default Satellite view | Global; 10 m, 2016 | CC BY 4.0. No key. Commercial use and analysis allowed. The free endpoint is "as is" and rate limited; copying the tiles needs EOX's written confirmation of the license first | EOxCloudless <https://cloudless.eox.at> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016) released under Creative Commons Attribution 4.0 International License. | No | 2026-10-05 |
| **EOX Sentinel-2 cloudless 2017** (`eox-s2cloudless-2017`) | Optional alternative | Global; 10 m, 2017 | As for 2016 | EOxCloudless <https://cloudless.eox.at> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2017) released under Creative Commons Attribution 4.0 International License. | No | 2026-10-05 |
| **EOX Sentinel-2 cloudless 2025** (`eox-s2cloudless-2025`) | Optional, for clearly non-commercial deployments only | Global; 10 m, 2025 | CC BY-NC-SA 4.0: **not open data**; commercial use needs a license from EOX; share-alike attaches to derived data, so analysis is `review-terms`. No key. Later years than 2017 follow this pattern | EOxCloudless <https://cloudless.eox.at> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2025) released under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. For commercial usage please see <https://cloudless.eox.at> | No | 2026-10-05 |

EOX states the license of each layer in its WMTS capabilities document
(<https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml>), which is what the config was verified against.

Not listed on purpose: Google Maps and Bing Maps imagery (their own APIs and terms only) and NRSC Bhuvan for India (no
open tile service; its terms bar redistribution and bulk download).

## Regional statistics and lookups

| Source | Purpose | Coverage | License / terms | Attribution text | Store locally? | Checked |
| --- | --- | --- | --- | --- | --- | --- |
| **USDA NASS Quick Stats API** — <https://quickstats.nass.usda.gov/api> | County crop statistics for the "other farm income" line | United States | Work of the US federal government, public domain in the US (17 U.S.C. § 105); free API key; NASS asks users to acknowledge the source | USDA National Agricultural Statistics Service, Quick Stats | Cache responses; bulk downloads permitted | 2026-10 |
| **US Census Bureau Geocoder** — <https://geocoding.geo.census.gov/geocoder/> | County lookup from coordinates | United States | Public domain; no key; respect the service's request limits | U.S. Census Bureau Geocoder | Cache county results | 2026-10 |
| **data.gov.in** (district-wise crop production and other resources) — <https://data.gov.in/> | District crop statistics for the "other farm income" line | India | Government Open Data License – India (GODL) (<https://data.gov.in/government-open-data-license-india>): free use with attribution, no endorsement implied; API key required | Source: data.gov.in — [publishing Ministry/Department], Government of India | Cache responses; bulk use permitted under GODL | 2026-10 |
| **Bhuvan / NRSC services** (optional, India) — <https://bhuvan.nrsc.gov.in/> | Optional thematic layers | India | Service-specific terms; many layers require registration; verify per layer before enabling | As stated by NRSC for the layer | Only if the layer's terms permit | not yet integrated |
| **Eurostat** (optional, EU) — <https://ec.europa.eu/eurostat> | Regional agricultural statistics | EU | Eurostat reuse policy, generally CC BY 4.0 (<https://ec.europa.eu/eurostat/about-us/policies/copyright>) | Source: Eurostat | Cache responses | not yet integrated |

## Reference parameters (not fetched at runtime)

| Source | Purpose | License / terms | Attribution text | Checked |
| --- | --- | --- | --- | --- |
| **IPCC 2006 Guidelines, Vol. 4 and 2019 Refinement** — <https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html> | Default factors (carbon fraction, root-to-shoot, growth increments) in `config/methodologies/` | © IPCC; default values cited with table numbers | IPCC (2006; 2019 Refinement), Volume 4, Chapter 4, Table [n] | 2026-10 |
| **Chave et al. 2014** — <https://doi.org/10.1111/gcb.12629> | Allometric equations | Journal article; equations cited | Chave et al. (2014), Global Change Biology 20(10) | 2026-10 |
| **Global Wood Density Database** (Zanne et al. 2009) — <https://doi.org/10.5061/dryad.234> | Wood densities in `config/species/` | CC0 (Dryad) | Zanne et al. (2009), Global Wood Density Database, Dryad | 2026-10 |
| **World Bank State and Trends of Carbon Pricing** — <https://www.worldbank.org/en/programs/pricing-carbon>; **Ecosystem Marketplace** reports — <https://www.ecosystemmarketplace.com/> | Review of price scenarios in `config/market/` | Reports cited, not redistributed | As cited in the scenario file | 2026-10 |

## Rules

1. Add a row **before** merging an adapter; the data-quality tests compare
   adapter ids with this table (planned).
2. Copy attribution strings verbatim into the adapter's `provenance()`
   and into [ATTRIBUTION.md](ATTRIBUTION.md).
3. "Store locally" means what the license permits *and* what the privacy
   design allows: per-plot clips are location data with a retention limit
   ([../privacy/data-retention.md](../privacy/data-retention.md)).
4. Non-commercial clauses (Open-Meteo's free tier, some imagery mosaics)
   are deployment decisions; the deployer confirms their use qualifies or
   subscribes.
5. When a term is uncertain, the row says *verify* and the adapter README
   repeats it.
6. An imagery provider needs a row in the imagery table above and in
   [MAP_LICENSES.md](MAP_LICENSES.md), its attribution in
   [ATTRIBUTION.md](ATTRIBUTION.md), and an entry in
   `config/imagery/providers.yaml` whose license, attribution and key rule
   were read from the provider's own terms. Production refuses a provider
   that is not `verified`. A provider that needs a key, or whose terms bar
   automated analysis, stays `analysis_allowed: false`.
