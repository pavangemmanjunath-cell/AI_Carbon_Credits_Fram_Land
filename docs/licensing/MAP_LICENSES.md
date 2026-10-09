# Map software and imagery licenses

The mapping stack is permissively licensed. This page lists each component, its license, what the license asks of us
and where the notice must appear, and then the terms of every satellite and aerial imagery provider the map can show.
Data licenses (OpenStreetMap, Sentinel, WorldCover) are in [DATA_LICENSES.md](DATA_LICENSES.md); the full dependency
inventory is in [THIRD_PARTY.md](THIRD_PARTY.md); the strings to display are in [ATTRIBUTION.md](ATTRIBUTION.md).

## Mapping software

| Component | Role | License | Obligations | Source |
| --- | --- | --- | --- | --- |
| **MapLibre GL JS** (`maplibre-gl`) | WebGL vector map renderer | BSD-3-Clause (contains portions © Mapbox under the same license as of the fork point) | Keep copyright notice and license text in distributions; no endorsement with contributors' names | <https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt> |
| **PMTiles** (`pmtiles` JavaScript library and CLI) | Single-file tile archive reader; protocol handler for MapLibre | BSD-3-Clause | Keep notice | <https://github.com/protomaps/PMTiles> |
| **PMTiles specification** | Format specification | Dedicated to the public domain under CC0 1.0 (verify in the `spec/` directory of the repository) | None | <https://github.com/protomaps/PMTiles/tree/main/spec> |
| **Protomaps basemap builds** (`protomaps/basemaps`) | Tile schema and build tooling for the archive you host. The app reads the schema's layer names with its own minimal style (`apps/web/src/components/map/mapStyle.ts`) and does not bundle the Protomaps style package | BSD-3-Clause | Keep notice, if you use the tooling | <https://github.com/protomaps/basemaps> |
| **terra-draw** and its MapLibre adapter | Drawing and editing polygons on MapLibre | MIT | Keep notice | <https://github.com/JamesLMilner/terra-draw> |
| **Natural Earth** (inside Protomaps builds at low zoom) | Country and coastline geometry | Public domain | None; courtesy credit "Made with Natural Earth" | <https://www.naturalearthdata.com/about/terms-of-use/> |
| **MapLibre demo tiles and glyphs** (`demotiles.maplibre.org`) | Development-only basemap style, and the label glyphs ("Open Sans Regular") that the app's built-in PMTiles style requests | Served by MapLibre for demos; data attribution as stated in the style JSON | Do not use as a production basemap; check the style's attribution field. TODO(verify): the license of the glyph font files | <https://demotiles.maplibre.org/style.json> |

The licenses of MapLibre GL JS, PMTiles and terra-draw were confirmed from the installed `package.json` files
(2026-10-05). The other rows are as first researched. The web app does not use deck.gl, three.js or React Three Fiber:
they are not in `apps/web/package.json` (checked 2026-10-05), so they have no row. If one is added back, add its row
here and in [THIRD_PARTY.md](THIRD_PARTY.md) in the same pull request.

## Where notices live

- The map's own attribution bar. The app switches MapLibre's built-in attribution control off and draws its own bar
  (`AttributionBar`). It shows the attribution of the basemap style's sources, then the attribution of the imagery
  provider on screen (only while the Satellite view is on), then the data attributions (ESA WorldCover and Copernicus
  Sentinel). On a phone the line is clamped to one row and expands when you tap it. Software credits are not shown
  there; they are not what the licenses above require.
- This page, [THIRD_PARTY.md](THIRD_PARTY.md) and the generated inventories list the software and its licenses. In
  version 0.1 the web build does not copy dependency license texts into its output and the app has no "About" panel
  ([notices](THIRD_PARTY.md#notices)).
- Reports and exports carry the attribution of every source they used ([ATTRIBUTION.md](ATTRIBUTION.md)).

## Why these licenses matter for the architecture

MapLibre's BSD license is the reason a self-hosted basemap is possible at all without per-load fees or usage policies;
the PMTiles format's public specification is what lets a bucket serve tiles without a server
([mapping architecture](../architecture/mapping-architecture.md)). Both are compatible with the project's Apache-2.0
license ([ADR-0005](../architecture/adr/0005-apache-2-license.md)). None of the components imposes copyleft on the
application; the only share-alike obligation in the stack comes from the **ODbL data** in OpenStreetMap-derived tiles,
and it attaches to the tile database (publish how it was made), not to the application code.

## Imagery providers

The Satellite view shows imagery from the providers in [`config/imagery/providers.yaml`](../../config/imagery/providers.yaml).
The API lists them at `GET /api/v1/imagery/providers`, with the recommended one first for the country, and the web app
lets the user choose one in Settings, "Map imagery" ([how it works](../data-sources/FREE_APIS.md#satellite-and-aerial-imagery)).
The terms below were read from each provider's own capabilities, terms or metadata on 2026-10-05 and are summarized
from [the research](../research/imagery-providers.md), which holds the quotations, the sources and what could not be
confirmed. Providers change their terms; the provider's current text always applies. This is not legal advice.

| Provider (id) | Coverage | License | Commercial use | Analysis or ML | Key |
| --- | --- | --- | --- | --- | --- |
| Esri World Imagery (`esri-world-imagery`) | Global | Esri Master License Agreement, proprietary ([terms summary](https://www.esri.com/content/dam/arcgisonline/docs/tou_summary.pdf)) | Review the terms | **Not allowed: display only** | Yes: `ESRI_API_KEY` |
| USGS Imagery Only (`usgs-imagery-only`) | United States | Public domain ([USGS policy](https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs)) | Allowed | Allowed | No |
| IGN France, BD ORTHO (`ign-france-orthophotos`) | France | Licence Ouverte 2.0, Etalab ([text](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0)) | Allowed | Allowed | No |
| IGN Spain, PNOA (`ign-spain-pnoa`) | Spain | CC BY 4.0 scne.es ([conditions](https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf)) | Allowed | Allowed | No |
| PDOK Luchtfoto (`pdok-luchtfoto`) | Netherlands | CC BY 4.0 ([Beeldmateriaal Nederland](https://www.beeldmateriaal.nl/dataroom)) | Allowed | Allowed | No |
| EOX Sentinel-2 cloudless 2016 (`eox-s2cloudless-2016`) | Global | CC BY 4.0 ([deed](https://creativecommons.org/licenses/by/4.0/)) | Allowed | Allowed | No |
| EOX Sentinel-2 cloudless 2017 (`eox-s2cloudless-2017`) | Global | CC BY 4.0 | Allowed | Allowed | No |
| EOX Sentinel-2 cloudless 2025 (`eox-s2cloudless-2025`) | Global | CC BY-NC-SA 4.0 ([deed](https://creativecommons.org/licenses/by-nc-sa/4.0/)) | **Not allowed** | Review the terms | No |

"Analysis or ML" means running segmentation, machine learning or feature extraction on the tiles, which is a licensing
question and says nothing about whether the resolution shows trees. The rule is the one in the config file: do it only
on providers marked `analysis_allowed: true`, or on the user's own imagery. `Review the terms` means "not until someone
has read the terms". The Atlas itself runs no analysis on these tiles: its vegetation indices and tree-cover detection
read Sentinel-2 through the STAC adapters. A data-quality test keeps open-data providers analysis-allowed and
display-only providers display-only.

The attribution text of each provider is in [ATTRIBUTION.md](ATTRIBUTION.md#imagery-providers-satellite-view). Notes
that matter per provider:

- **Esri World Imagery.** Optional, never the default, and only with a key the deployer supplies from the environment
  (never committed). Esri's MapLibre tutorial says an ArcGIS Location Platform account and an API key are required.
  Esri's blog (11 February 2025) says World Imagery "cannot be used as direct input to automated information
  extraction" and that derived data is "strictly for non-commercial use within ArcGIS". The terms summary (updated
  21 April 2025) lists as prohibited: systematically harvesting basemap tiles, redistributing basemap tiles,
  downloading or self-hosting Esri-hosted content, and using ArcGIS Living Atlas content commercially in your own
  application or product; it also requires attribution to Esri and its data providers. The full Master License
  Agreement was not read, and whether a free open-source deployment counts as commercial use is not confirmed, so the
  config keeps `review-terms`. A key in a web build is visible to every visitor: use a referrer-restricted,
  basemap-only key. The attribution drifts: the live service says "Esri, Vantor, Earthstar Geographics, and the GIS
  User Community" while Esri's tutorial still says Maxar; the config uses the live text.
- **USGS Imagery Only.** Public domain as USGS information and NAIP. The tile cache ends at zoom 16, so sub-meter NAIP
  detail is not visible; for bulk analysis take the NAIP source data instead of harvesting tiles. USDA's Farm Service
  Agency notice AP-26 (27 November 2017) said the agency was considering a licensed data model for future NAIP, so
  re-check before relying on this for newer imagery. Coverage in Alaska, Hawaii and the territories was not confirmed.
- **IGN France.** The license is inferred from a chain: the Géoplateforme terms say the Licence Ouverte applies by
  default, and the data.gouv.fr dataset BD ORTHO states Licence Ouverte 2.0, which allows commercial reuse and
  requires naming the source and the date of last update. No attribution text is mandated; the one in the config is
  composed from the license, so add the survey date when you know it.
- **IGN Spain.** The license document asks for a credit in the form `<product> <date> CC-BY 4.0 <producer>`, visible at
  the foot of the map, and "Obra derivada de" on derived works. The config omits the date because this layer is a
  rolling mosaic; add the product year when it is known. At small scales the layer shows Sentinel-2, not aerial photos.
- **PDOK.** Three sources agree on CC BY 4.0. The publisher asks only that publications refer to beeldmateriaal.nl, and
  CC BY asks for credit to the licensor; the config's text is composed from both. Any PDOK fair-use policy was not
  confirmed.
- **EOX Sentinel-2 cloudless.** The 2016 and 2017 layers are CC BY 4.0, and the 2025 layer is CC BY-NC-SA 4.0:
  non-commercial, share-alike, and commercial use needs a license from EOX. Layers 2018 to 2024 follow the 2025 pattern
  and are not in the config. The free endpoint is provided "as is" and rate limited, so production traffic needs a
  self-hosted copy or an agreement with EOX. Copying EOX's tiles needs EOX's written confirmation first, because a
  2017 EOX post described the downloadable original tiles as CC BY-SA 4.0. An earlier version of this page described
  all EOX mosaics as CC BY-NC-SA 4.0; that was wrong for 2016 and 2017.

Not listed on purpose. Google Maps and Bing Maps imagery can be used only through their own APIs and terms, and direct
tile URLs are not allowed. For India, NRSC Bhuvan's terms grant a non-transferable license to use the portal and bar
redistribution and bulk download, and no open tile service was found, so India uses the global default.

If a deployment sets `VITE_SATELLITE_TILES_URL`, that imagery replaces the list for every user, the provider's own terms
apply, and the deployer must set `VITE_SATELLITE_ATTRIBUTION`; the attribution bar then shows it. Other providers to
consider, none researched yet: a self-built Sentinel-2 mosaic (Copernicus terms: free, with "Contains modified
Copernicus Sentinel data [year]"), and other national orthophoto programs. Add a provider by following
[adding an integration](../developer-guide/adding-an-integration.md#which-kind-of-integration-is-it).
