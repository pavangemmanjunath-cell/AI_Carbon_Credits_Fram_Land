# Attribution strings

The exact strings to display in the user interface, in reports and in
exports. They are served by `GET /attribution` and embedded in every
`provenance.sources[].attribution`; this page is the human-readable
master copy. Copy them verbatim; do not shorten, translate the proper
names, or drop the year. Where a string contains `[year]`, substitute the
acquisition year(s) of the data actually used (for example
"2024–2026").

In version 0.1 the wording that the API serves and that the adapters embed
differs from this page for most sources
([the differences](../data-sources/FREE_APIS.md#attribution-strings)); until
the code is reconciled, display the strings on this page. The imagery
strings below are served by `GET /imagery/providers`, from the same text in
`config/imagery/providers.yaml`.

## Always shown on the map

| id | Text | Link | When |
| --- | --- | --- | --- |
| `osm` | © OpenStreetMap contributors | <https://www.openstreetmap.org/copyright> | Whenever the basemap or geocoding results are shown |
| `protomaps` | Protomaps | <https://protomaps.com> | When tiles come from a Protomaps build. The app's built-in PMTiles style (`apps/web/src/components/map/mapStyle.ts`) credits only OpenStreetMap, so add this to the style if your builds ask for it |
| `maplibre` | MapLibre | <https://maplibre.org/> | Served by `GET /attribution`. The app switches MapLibre's own attribution control off, so its bar does not add this; the MapLibre license asks for its notice in distributions, not an on-map credit |

## Shown when the corresponding layer or value is displayed

| id | Text | Link | Trigger |
| --- | --- | --- | --- |
| `esa-worldcover` | © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium | <https://esa-worldcover.org/> | Land-cover block, tree-cover mask layer |
| `copernicus-sentinel-2` | Contains modified Copernicus Sentinel data [year] | <https://sentinels.copernicus.eu/> | NDVI/NDMI values, time series, cube, any imagery derived from Sentinel-2 |
| `open-meteo` | Weather data by Open-Meteo.com | <https://open-meteo.com/> | Climate block (zone, temperature, precipitation, elevation) |
| `soilgrids` | SoilGrids — ISRIC World Soil Information | <https://www.isric.org/explore/soilgrids> | Soil block |
| `copernicus-dem` | Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved | <https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model> | Terrain layer or elevation from the DEM |
| `nominatim` | Search by Nominatim · © OpenStreetMap contributors | <https://nominatim.org/> | Search box and reverse-geocoded labels |
| `photon` | Search by Photon (komoot) · © OpenStreetMap contributors | <https://photon.komoot.io/> | When `ATLAS_GEOCODER=photon` |
| `usda-nass` | Source: USDA National Agricultural Statistics Service, Quick Stats | <https://quickstats.nass.usda.gov/> | US crop statistics in the other-income line |
| `census-geocoder` | County lookup: U.S. Census Bureau Geocoder | <https://geocoding.geo.census.gov/> | US county label |
| `data-gov-in` | Source: data.gov.in — [Ministry/Department], Government of India (Government Open Data License – India) | <https://data.gov.in/> | India district crop statistics |
| `satellite-imagery` | *value of `VITE_SATELLITE_ATTRIBUTION`* | provider page | Only when `VITE_SATELLITE_TILES_URL` replaces the provider list. Otherwise show the string of the provider on screen ([imagery providers](#imagery-providers-satellite-view)) |

## Imagery providers (Satellite view)

Shown in the map's attribution bar while the Satellite view is on, for the provider on screen only, and repeated in any
screenshot or publication that shows that imagery. The id is the provider id in `config/imagery/providers.yaml`.
Where the license does not dictate an exact text (IGN France, IGN Spain, PDOK), the string was composed from the
license's requirement; add the survey date or product year when you know it ([MAP_LICENSES.md](MAP_LICENSES.md)).

| id | Text | License | Link |
| --- | --- | --- | --- |
| `esri-world-imagery` | Esri, Vantor, Earthstar Geographics, and the GIS User Community | Esri Master License Agreement; display only | <https://www.esri.com/content/dam/arcgisonline/docs/tou_summary.pdf> |
| `usgs-imagery-only` | USDA, USGS The National Map: Orthoimagery | Public domain | <https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs> |
| `ign-france-orthophotos` | Source : IGN - Institut national de l'information géographique et forestière - Licence Ouverte 2.0 | Licence Ouverte 2.0 | <https://www.data.gouv.fr/pages/legal/licences/etalab-2.0> |
| `ign-spain-pnoa` | PNOA CC-BY 4.0 scne.es | CC BY 4.0 | <https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf> |
| `pdok-luchtfoto` | Beeldmateriaal Nederland (beeldmateriaal.nl), CC BY 4.0, via PDOK | CC BY 4.0 | <https://www.beeldmateriaal.nl/dataroom> |
| `eox-s2cloudless-2016` | EOxCloudless <https://cloudless.eox.at> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016) released under Creative Commons Attribution 4.0 International License. | CC BY 4.0 | <https://creativecommons.org/licenses/by/4.0/> |
| `eox-s2cloudless-2017` | EOxCloudless <https://cloudless.eox.at> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2017) released under Creative Commons Attribution 4.0 International License. | CC BY 4.0 | <https://creativecommons.org/licenses/by/4.0/> |
| `eox-s2cloudless-2025` | EOxCloudless <https://cloudless.eox.at> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2025) released under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. For commercial usage please see <https://cloudless.eox.at> | CC BY-NC-SA 4.0 | <https://creativecommons.org/licenses/by-nc-sa/4.0/> |

Esri's tutorial still names Maxar where the live service says Vantor; use the live text. The strings above are copied
from the config, so a change to one needs the same change in the other.

## Methodology and parameter credits

Use these where a result or a report names its methodology or parameters. The web app has no "About" panel in
version 0.1.

| id | Text |
| --- | --- |
| `ipcc-2006` | Default factors from the 2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 4 (AFOLU), Chapter 4, and the 2019 Refinement. Use of IPCC default values does not imply IPCC endorsement of this estimate. |
| `chave-2014` | Allometric model: Chave J. et al. (2014) Improved allometric models to estimate the aboveground biomass of tropical trees. Global Change Biology 20(10), 3177–3190. doi:10.1111/gcb.12629 |
| `gwdd-2009` | Wood density: Zanne A.E. et al. (2009) Global Wood Density Database. Dryad. doi:10.5061/dryad.234 |
| `price-scenarios` | Price scenarios are illustrative, reviewed against the World Bank *State and Trends of Carbon Pricing* and Ecosystem Marketplace reports; they are not quotes. |

## Mandatory disclaimers (verbatim)

These are not attributions but appear in the same places and are equally
non-negotiable:

| id | Text |
| --- | --- |
| `estimate` | Scenario estimate; not an issued carbon credit. |
| `market` | Market-value scenario — not guaranteed revenue. |
| `screening` | Initial screening only — not an eligibility determination. |
| `india-mechanisms` | Green Credits (GCP) and carbon credits (CCTS) are separate mechanisms. |
| `eu-crcf` | Under the CRCF a calculated estimate is never automatically certifiable; certification by a recognised scheme is required. |
| `demo` | Demo mode: synthetic observations; numbers are illustrative only. |

## Placement rules

1. **Map**: the attribution control is always visible, never collapsed by
   default on desktop, and lists every active layer's string.
2. **Results view**: each block (land cover, vegetation, climate, soil)
   shows its source line beneath the values; the estimate card shows the
   methodology credit and the `estimate` disclaimer.
3. **Reports**: an "Attribution and sources" section lists every id used,
   with links, plus the disclaimers; PDF exports include it on the last
   page.
4. **Exports (JSON)**: the `provenance` object carries the strings; no
   separate action is needed.
5. **Screenshots and publications**: reproduce the map and data
   attributions in the caption.

## Localization

Attribution strings are **not translated**; they are legal notices tied to
their sources. The UI labels around them ("Sources", "Data") are
translated. Disclaimers are translated by the i18n team with the English
text as the reference, and the English text is included in reports in
every language.
