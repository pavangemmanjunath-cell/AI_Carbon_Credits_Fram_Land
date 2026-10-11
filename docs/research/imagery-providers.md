# Imagery providers for the Satellite view

Research of 2026-10-05 behind `config/imagery/providers.yaml`. The web map (MapLibre GL JS, raster tiles in Web
Mercator) needs a "Satellite" view. For each candidate this page records the tile URL, maximum zoom, coverage, licence,
attribution, key requirement, and whether commercial use and automated analysis (segmentation, ML) are allowed.
Everything was read from the provider's own capabilities, terms or metadata with a page-summarising fetch tool, so
quotations are as that tool returned them; open the cited page before relying on a quoted sentence. Nothing here is
legal advice, and the provider's current terms always apply.

## Recommendation for production

1. **Keep an open, keyless global default: EOX Sentinel-2 cloudless 2016** (`eox-s2cloudless-2016`). It is the only
   provider verified to be global, keyless, licensed for commercial use (CC BY 4.0) and free of any ban on automated
   analysis. Its costs are real: 10 m pixels (a village or a large field is visible, individual trees are not), imagery
   from 2016, and a free endpoint that EOX describes as "as is" and under heavy load with rate limiting. For
   production traffic either arrange a service-level agreement with EOX or replace the free endpoint with your own
   Sentinel-2 mosaic (item 3). Copying EOX's tiles needs EOX's written confirmation of the licence first, because a
   2017 EOX post described the downloadable original tiles as CC BY-SA 4.0 while the live capabilities say CC BY 4.0.
2. **Use the national open orthophotos where they exist**: United States (`usgs-imagery-only`, public domain), France
   (`ign-france-orthophotos`, Licence Ouverte 2.0), Spain (`ign-spain-pnoa`, CC BY 4.0 scne.es) and the Netherlands
   (`pdok-luchtfoto`, CC BY 4.0). They are sharper (8 cm to about 1 m), keyless and openly licensed. Only these four
   countries are mapped in `default_by_country`, because only they pass the test "coverage fits and the licence is
   open, keyless and allows analysis".
3. **India has no verified open high-resolution tile service**, so it falls back to the global default. For a production
   India deployment the options, best first, are a self-built cloud-free Sentinel-2 mosaic published as PMTiles from the
   project's own bucket (the repo's STAC adapters already read Sentinel-2; `docs/licensing/MAP_LICENSES.md` records the
   Copernicus attribution wording, which this research did not re-open), then Esri World Imagery as an optional,
   display-only layer under the deployer's own Esri licence, and for analysis the user's own imagery.
4. **Esri World Imagery is optional, never the default, and never an input to analysis.** It needs an ArcGIS key, its
   terms restrict commercial use of Living Atlas content in your own product, and Esri says World Imagery "cannot be
   used as direct input to automated information extraction". A deployer who holds an Esri licence may set
   `default: esri-world-imagery` for display only.
5. **Analysis rule.** Run segmentation or ML only on providers with `analysis_allowed: true` or on the user's own
   imagery. `review-terms` means "not until someone has read the terms".
6. **Always show the attribution string** from the config in the map's attribution control, and label the imagery
   source and year in the UI. A 2016 mosaic does not show a plantation made in 2020; CarbonCreditBuy never claims it does.

Before a provider ships, `CLAUDE.md` rules 5 and 6 still apply: add it to `docs/licensing/DATA_LICENSES.md` and give it
an adapter with a README, licence, attribution, rate limits, caching and failure handling, taking the endpoint from an
environment variable. This research supplies the verified metadata only.

### Why the default is not Esri

The obvious first choice, and the example this file was started from, was `default: esri-world-imagery`; this research
changed it. Esri's documented third-party path needs an ArcGIS Location Platform account and an API key, the key would
sit in a public browser bundle, the terms prohibit redistributing or self-hosting tiles and Living Atlas content in a
commercial product, and automated analysis is not permitted. An open-source default has to work for any deployer with
no account and no restrictions. The price of that choice is lower detail (10 m instead of 30 cm in many places), which
is stated openly above.

## Comparison

| Provider (id) | Coverage | Resolution | Max zoom | Key | Licence | Commercial use | Analysis / ML | Open data |
|---|---|---|---|---|---|---|---|---|
| EOX Sentinel-2 cloudless 2016 (`eox-s2cloudless-2016`) | Global | 10 m, 2016 | 14 | No | CC BY 4.0 | Allowed | Allowed | Yes |
| EOX Sentinel-2 cloudless 2017 (`eox-s2cloudless-2017`) | Global | 10 m, 2017 | 14 | No | CC BY 4.0 | Allowed | Allowed | Yes |
| EOX Sentinel-2 cloudless 2025 (`eox-s2cloudless-2025`) | Global | 10 m, 2025 | 14 | No | CC BY-NC-SA 4.0 | Not allowed | Review terms | No |
| USGS Imagery Only (`usgs-imagery-only`) | US | NAIP 0.6 to 1 m (cache ends at z16) | 16 | No | Public domain | Allowed | Allowed | Yes |
| IGN France orthophotos (`ign-france-orthophotos`) | FR | 20 cm | 19 | No | Licence Ouverte 2.0 | Allowed | Allowed | Yes |
| IGN Spain PNOA (`ign-spain-pnoa`) | ES | 25 to 50 cm (Sentinel-2 10 m at small scales) | 19 | No | CC BY 4.0 scne.es | Allowed | Allowed | Yes |
| PDOK Luchtfoto (`pdok-luchtfoto`) | NL | 8 cm (5 cm in places) | 21 | No | CC BY 4.0 | Allowed | Allowed | Yes |
| Esri World Imagery (`esri-world-imagery`) | Global | 15 m worldwide, 1.2 m to 30 cm in many places, 15 cm to 3 cm in some | 19 (conservative) | Yes | Esri Master License Agreement | Review terms | Not allowed | No |
| NRSC Bhuvan (India) | IN | not verified | not verified | not verified | Access licence only (see below) | Not listed | Not listed | No entry |
| Google, Bing | Global | not researched | not researched | their own API | their own terms | Not listed | Not listed | No entry |

"Max zoom" is the highest zoom the app should request. MapLibre then over-zooms the last tile level instead of
asking for tiles that do not exist. "Analysis / ML" is a licensing statement only: it says nothing about whether the
resolution is good enough to see trees.

### Attribution strings as configured

| Provider | Attribution text (display this) |
|---|---|
| EOX 2016 | EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016) released under Creative Commons Attribution 4.0 International License. |
| EOX 2017 | The same text with 2017 in place of 2016. |
| EOX 2025 | The same text with 2025, released under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License, followed by "For commercial usage please see https://cloudless.eox.at". |
| USGS | USDA, USGS The National Map: Orthoimagery (the service appends a refresh marker, "Data refreshed June, 2024.v1.2"; USGS also asks for a credit such as "courtesy of the U.S. Geological Survey"). |
| IGN France | Source : IGN - Institut national de l'information géographique et forestière - Licence Ouverte 2.0 (composed from the licence requirement; add the survey date when known). |
| IGN Spain | PNOA CC-BY 4.0 scne.es (composed from the SCNE pattern "product, date, CC-BY 4.0, producers"; add the product year when known). |
| PDOK | Beeldmateriaal Nederland (beeldmateriaal.nl), CC BY 4.0, via PDOK (composed from beeldmateriaal.nl's request to refer to it). |
| Esri | Esri, Vantor, Earthstar Geographics, and the GIS User Community (from the live service; Esri's tutorial still says Maxar). |

Only the EOX, USGS and Esri strings are verbatim from the provider. The French, Spanish and Dutch texts are composed
because those providers mandate no verbatim string, and the config says so in each entry's notes.

## Licence notes by provider

### EOX Sentinel-2 cloudless

- The live WMTS capabilities (`tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml`) give each year its own licence
  statement. The 2016 and 2017 layers say "released under Creative Commons Attribution 4.0 International License".
  Every layer from 2018 to 2025 says "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License",
  and the 2025 text adds "For commercial usage please see https://cloudless.eox.at".
- The CC BY 4.0 deed (opened) allows sharing and adapting "for any purpose, even commercially". The CC BY-NC-SA 4.0
  deed (opened) says "You may not use the material for commercial purposes" and requires derivatives to be shared under
  the same licence. That is why `eox-s2cloudless-2025` is `commercial_use: not-allowed`, `analysis_allowed:
  review-terms` and `open_data: false`.
- **Existing repo text to reconcile.** `docs/licensing/MAP_LICENSES.md` lists "EOX Sentinel-2 cloudless" as "CC BY-NC-SA
  4.0; non-commercial unless licensed". That holds for 2018 to 2025 but not for the 2016 and 2017 layers, whose live
  capabilities say CC BY 4.0. This research did not edit that file.
- Tile paths. The capabilities advertise the 2016 layer as `s2cloudless-2016_3857`, but its ResourceURL, and the only
  path that returned a tile, uses `s2cloudless_3857`. A request with `s2cloudless-2016_3857` in the path returned 404.
  The 2017 and 2025 layers use `s2cloudless-2017_3857` and `s2cloudless-2025_3857`. The matrix set in the path is `g`
  (GoogleMapsCompatible), and the capabilities give no tile-matrix limits.
- Resolution. The mosaic is 10 m. At z14 a pixel is about 9.5 m on the equator, so z14 is the native level. The
  service returned images from z15 to z18 as well, but they are expected to be up-sampled and their content could not
  be inspected. An EOX post of March 2017 puts the best match to 10 m at zoom 13 of its original tile grid, which is a
  different grid from Web Mercator.
- Service terms. `maps.eox.at` says the free service is provided "as is without any guarantee", that "Content and
  availability may change without notice", that "Ever increasing interest in our free service results in heavy loads",
  that rate limiting can cause HTTP errors and redirects, and that users who need consistent access should ask about "a
  dedicated service under SLA". The same page grants an explicit permission to use the 2016 to 2025 layers as
  background for manual, non-commercial OpenStreetMap editing; that permission is limited to that purpose.

### USGS The National Map, USGS Imagery Only

- The service (`basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer`) is a 256 px tile cache with
  levels 0 to 23 in the scheme but a cache "visible to the 1:9,028 zoom scale", which is level 16. A z16 request
  returned an image and a z17 request returned 404 at the one location tried.
- Sources by scale (USGS FAQ): NASA Blue Marble Next Generation for the world view to 1:2,300,000, a subset of Landsat
  Global Land Survey 2000 from 1:1,150,000 to 1:289,000, and primarily NAIP at larger scales. NAIP was flown at 1 m
  from 2003 to 2017 and at 0.6 m since 2018, with a 0.3 m option in some coastal states (USGS EROS).
- Licence. The USGS credit policy says "Most U.S. Geological Survey (USGS) information resides in the Public Domain and
  may be used without restriction" and asks that proper credit be given. The EROS page for NAIP states "Sources/Usage:
  Public Domain". The policy also warns that some non-USGS images are used with the copyright holder's permission.
- Risk to re-check. FSA notice AP-26 of 27 November 2017 says all NAIP imagery since 2003 "has been placed in public
  domain" and that the agency was considering a licensed data model for the future. USGS currently states public domain,
  so the entry is `verified`, but a licence change for new NAIP flights would need a fresh look.

### IGN France, Géoplateforme orthophotos

- Layer `ORTHOIMAGERY.ORTHOPHOTOS` ("Photographies aériennes"), style `normal`, JPEG, matrix set `PM_0_19`. A z19 request
  returned an image and z20 returned 404. The capabilities say `Fees: none` and point to the terms at
  `https://cartes.gouv.fr/cgu`.
- The licence is established by a chain rather than by one sentence in the layer: the terms (version of 15 October
  2024) say the Licence Ouverte applies by default; the layer's metadata id is `IGNF_BD-ORTHO`; and the data.gouv.fr
  dataset "BD ORTHO" is published under Licence Ouverte / Open Licence 2.0 at 20 cm resolution. The licence allows
  reuse including commercial use ("l'exploiter à titre commercial") and requires naming the source, at minimum the
  licensor, and the date of the last update.
- The Géoplateforme usage-limits page says the rate-limiting mechanism covers most APIs "à l'exception notable de
  l'API « Diffusion d'images tuilées WMTS »", so no per-IP limit is documented for tiles.
- The survey dates are in a PDF linked from the layer abstract; the licence's date requirement is best met by showing
  the date for the visible area.

### IGN Spain, PNOA

- Service `www.ign.es/wmts/pnoa-ma`, layer `OI.OrthoimageCoverage`, matrix set `GoogleMapsCompatible`. The capabilities
  give `AccessConstraints: CC BY 4.0 scne.es` and `Fees: No se aplican condiciones`. The abstract says Sentinel-2 (10 m)
  is shown at scales below 1:70,000 and PNOA orthophotos at larger scales, with tiles pre-generated in JPEG to level 19.
  Both z19 and z20 returned an image; z19 is the documented level.
- The licence document (based on Orden FOM/2807/2015) says use is "libre y gratuito" and requires a credit of the form
  `product identifier, date, CC-BY 4.0, producer attribution`, shown legibly at the foot of the map. Derived works
  must carry the prefix "Obra derivada de". The IDEE record for PNOA 2025 uses "PNOA 2025 CC-BY 4.0 scne.es".
- IDEE also documents a TMS endpoint, `https://tms-pnoa-ma.idee.es/1.0.0/pnoa-ma/{z}/{x}/{-y}.jpeg`, with `maxZoom: 19`.
  Because it is TMS, a MapLibre source must set `scheme: "tms"` (or use the WMTS URL in the config instead).

### PDOK, Luchtfoto RGB (Netherlands)

- Layer `Actueel_orthoHR` (current 8 cm orthophoto) in the service `luchtfotorgb/wmts/v1_0`, matrix set `EPSG:3857`.
  The REST template is `{TileMatrixSet}/{TileMatrix}/{TileCol}/{TileRow}.jpeg`, which equals `{z}/{x}/{y}` in XYZ
  terms. The tile matrix reaches level 21 and z19, z20 and z21 each returned an image. A 25 cm layer
  (`Actueel_ortho25`) and yearly layers exist.
- Three sources agree on CC BY 4.0: PDOK ("onder hantering van het CC BY 4.0 gebruiksrecht"; the services are "voor
  iedereen kosteloos en vrij beschikbaar voor alle toepassingen"), beeldmateriaal.nl ("De beelden worden beschikbaar
  gesteld met een CC BY 4.0 licentie"; used or adapted "zonder verplichtingen"; "Wel vragen wij voor publicaties te
  refereren aan beeldmateriaal.nl"), and data.overheid.nl ("CC-BY (4.0)", owner Dienst voor het kadaster en de openbare
  registers).

### Esri World Imagery

- Documented third-party path: `https://ibasemaps-api.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}?token=...`.
  Esri's MapLibre tutorial says this needs an ArcGIS Location Platform account and an API key credential, and the
  Esri Leaflet FAQ says "you need to provide an API key or implement another type of authentication". The keyless
  `server.arcgisonline.com` host returned tiles at z10 and z19 but is not the documented third-party path, so the
  config does not use it.
- Esri's blog of 11 February 2025 says "World Imagery layers/services cannot be used as direct input to automated
  information extraction" and that data derived from World Imagery is "strictly for non-commercial use within ArcGIS".
  The ArcGIS Online terms summary (updated 21 April 2025) prohibits systematically harvesting basemap tiles,
  redistributing basemap tiles, downloading or self-hosting Esri-hosted content, and using Living Atlas content
  commercially in your own application or product, and requires attribution to Esri and its data providers.
- The item description says "This work is licensed under the Esri Master License Agreement". The service text is
  "Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community". Esri's tutorial still shows the older
  "Maxar" wording; the live text is used.
- Coverage detail from the item: 15 m TerraColor worldwide; Vantor Vivid Standard 1.2 m to 30 cm, Vivid Advanced 30 cm
  in more than 1,000 metros, Vivid Premium 15 cm in select metros; community imagery 30 cm to 3 cm; "typically within
  3-5 years of currency" for the high-resolution areas.
- Not confirmed: the full Master License Agreement, whether a free open-source deployment counts as commercial use,
  how a key used in browser code can be restricted to a domain, and tile availability above z19.

### India and the providers that are not listed

- **NRSC Bhuvan.** The Bhuvan terms page (`bhuvan.nrsc.gov.in/terms.php`, titled Disclaimer) says "DOS/ISRO/NRSC grants
  a non-exclusive, non-transferable license to access the Bhuvan geo portal and service" and prohibits users from
  redistributing or otherwise making the content "available to third parties" and from access to "mass downloads or
  bulk feeds of any content". No tile URL and no open licence for the imagery were found; the page for the NRSC Open
  EO Data Archive returned no licensing text. Bhuvan is therefore not listed. If NRSC publishes an openly licensed tile
  service, add it with its own verified entry.
- **Google and Bing.** Their imagery is usable only through their own APIs and terms, and direct tile URLs are not
  allowed. They were not researched further and have no entry.

## Using the config in MapLibre

A provider entry maps to a raster source like this (EOX 2016 shown):

```json
{
  "version": 8,
  "sources": {
    "satellite": {
      "type": "raster",
      "tiles": ["https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg"],
      "tileSize": 256,
      "maxzoom": 14,
      "attribution": "EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016) released under Creative Commons Attribution 4.0 International License."
    }
  },
  "layers": [{ "id": "satellite", "type": "raster", "source": "satellite" }]
}
```

- `tileSize` is 256 for every provider here, `maxzoom` is the config's `max_zoom`, and `attribution` is the config's
  `attribution`. Above `maxzoom` MapLibre scales the last tile level up rather than requesting more tiles.
- Look the provider up by ISO 3166-1 alpha-2 country code (`default_by_country[country]`, else `default`) in a service
  or hook, not in a component. Quote codes that YAML 1.1 reads as booleans (for example `NO`) when adding countries.
- WMTS key-value URLs (IGN France and Spain) work as XYZ templates because the three tile coordinates are named
  placeholders (`TILEMATRIX={z}&TILEROW={y}&TILECOL={x}`). The PDOK path contains a colon (`EPSG:3857`), which is fine
  in a tile URL.
- `${ESRI_API_KEY}` is an environment-variable placeholder, not a tile placeholder; substitute it before the URL reaches
  MapLibre and never commit a key. A key placed in a browser bundle is visible to every visitor.
- For country-limited providers, set the source `bounds` to the country's bounding box so MapLibre does not request
  tiles outside the coverage. The bounding boxes were not part of this research.
- The existing environment variables `VITE_SATELLITE_TILES_URL` and `VITE_SATELLITE_ATTRIBUTION` take the `url` and
  `attribution` of the chosen provider.

## What was tested

Single tiles were requested near each stated maximum zoom. The fetch tool reports "Image content is not supported" when
the server answers with an image, which proves a tile exists but not what it shows, so placeholder or "no data" tiles
cannot be told apart from real ones.

| Provider | Tile requests |
|---|---|
| EOX 2016 (`s2cloudless_3857`) | Images at z10, z14, z15, z16, z17 and z18; `s2cloudless-2016_3857` in the path returned 404 |
| EOX 2017, EOX 2025 | Image at z10 |
| USGS Imagery Only | Images at z10 and z16; 404 at z17 |
| IGN France | Images at z10 and z19; 404 at z20 |
| IGN Spain | Images at z10, z19 and z20 |
| PDOK | Images at z10, z19, z20 and z21 |
| Esri (keyless `server.arcgisonline.com` host only) | Images at z10 and z19; the keyed `ibasemaps-api` host was not called |

## Not confirmed

- Tile content and cross-origin behaviour. No provider was loaded in a browser, so CORS headers (MapLibre requests
  tiles cross-origin), placeholder tiles and rendering were not checked. Test each provider in the running app.
- EOX. The CC BY versus CC BY-SA statements differ between a 2017 post and the live capabilities; the free endpoint's
  limits are unquantified; native zoom 14 is derived from the 10 m resolution, not read from a document.
- USGS. Coverage in Alaska, Hawaii and the territories; non-NAIP sources; any service-level fair-use policy (none was
  found; for bulk analysis take NAIP source data instead of harvesting tiles).
- IGN France. The layer's own dataset page could not be read (it needs JavaScript), so the licence rests on the chain
  above; overseas coverage; tile size 256 is the standard for the `PM` set but was not re-read.
- IGN Spain. Coverage of the Canary Islands, Ceuta and Melilla; the product year for the attribution; tile size 256 is
  the standard for `GoogleMapsCompatible` but was not re-read.
- PDOK. Coverage of the Caribbean Netherlands and any fair-use policy.
- Esri. The full Master License Agreement and the points listed under Esri above.
- India. Any openly licensed NRSC tile service; the NRSC Open EO Data Archive terms.
- Copernicus. The Sentinel data terms were not opened; the attribution wording in `MAP_LICENSES.md` is used as it
  stands.

## Sources

All accessed on 2026-10-05.

### EOX

- <https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml>
- <https://maps.eox.at/>
- <https://eox.at/2017/03/sentinel-2-cloudless-original-tiles-available/>
- <https://creativecommons.org/licenses/by/4.0/>
- <https://creativecommons.org/licenses/by-nc-sa/4.0/>

### USGS and NAIP

- <https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer?f=pjson>
- <https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs>
- <https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip>
- <https://www.usgs.gov/faqs/what-sources-were-used-imagery-national-map-services>
- <https://www.usgs.gov/index.php/faqs/what-are-base-map-services-or-urls-used-national-map>
- <https://www.fsa.usda.gov/Internet/FSA_Notice/ap_26.pdf>

### IGN France

- <https://data.geopf.fr/annexes/ressources/wmts/ortho.xml>
- <https://data.geopf.fr/annexes/ressources/wms-r/ortho.xml>
- <https://cartes.gouv.fr/cgu>
- <https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/limites-d-usage/>
- <https://www.data.gouv.fr/datasets/bd-ortho-r>
- <https://www.data.gouv.fr/pages/legal/licences/etalab-2.0>

### IGN Spain

- <https://www.ign.es/wmts/pnoa-ma?request=GetCapabilities&service=WMTS>
- <https://www.ign.es/wms-inspire/pnoa-ma?request=GetCapabilities&service=WMS>
- <https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf>
- <https://www.scne.es/productos_info.html>
- <https://www.idee.es/csw-codsi-idee/srv/api/records/spaignwmts_pnoa-ma>
- <https://www.idee.es/csw-codsi-idee/srv/api/records/spaignPNOA2025?language=eng>
- <https://blog-idee.blogspot.com/2022/12/como-cargar-el-tms-del-pnoa-ma-en_7.html>

### PDOK and Beeldmateriaal Nederland

- <https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0?request=GetCapabilities&service=wmts>
- <https://www.pdok.nl/-/nu-hoge-resolutie-luchtfoto-2024-bij-pdok>
- <https://www.beeldmateriaal.nl/dataroom>
- <https://data.overheid.nl/dataset/83048-luchtfoto-beeldmateriaal-2026-5cm---8cm-rgb-open-data>

### Esri

- <https://developers.arcgis.com/maplibre-gl-js/maps/raster-tile-basemaps/display-multiple-basemap-layers/>
- <https://developers.arcgis.com/esri-leaflet/faq/>
- <https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer?f=pjson>
- <https://www.arcgis.com/sharing/rest/content/items/10df2279f9684e4a9f6a7f08febac2a9?f=json>
- <https://www.esri.com/content/dam/arcgisonline/docs/tou_summary.pdf>
- <https://www.esri.com/arcgis-blog/products/arcgis-living-atlas/imagery/learn-to-use-ai-to-extract-information-from-world-imagery>

### India

- <https://bhuvan.nrsc.gov.in/terms.php>
- <https://bhuvan-app3.nrsc.gov.in/data/download/index.php>
