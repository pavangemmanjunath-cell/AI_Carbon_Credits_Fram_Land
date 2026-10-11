# Mapping architecture

The map is the first thing a user sees and the surface on which land is marked, so it has to be fast, self-hostable,
correctly attributed and free of third-party usage-policy surprises. This page explains the stack: MapLibre GL JS with
PMTiles on S3-compatible storage for the basemap, optional raster imagery for the Satellite view, plain GeoJSON layers
for the data, and the JSON vegetation cube behind the NDVI cells.

The map is **flat and 2D**: north is up, and there is no tilt or rotation. There is no WebGL scene other than the
MapLibre map itself ([changelog](../../CHANGELOG.md)).

## The layer stack

MapLibre draws the layers in a fixed order, from the bottom: imagery below the data, the data below the plots, and the
drawing tools on top. Every layer except the basemap is created by `apps/web/src/components/map/layers.ts` and receives
data the API has already computed.

| Layer | MapLibre id | Drawn from |
| --- | --- | --- |
| Basemap | the style's own layers | A PMTiles archive of OpenStreetMap data, or a style URL |
| Satellite imagery (optional) | `atlas-imagery-layer` | Raster tiles of the chosen provider (XYZ) |
| NDVI cells | `atlas-ndvi-fill` | GeoJSON polygons, one per cube cell of the selected month, from `GET /plots/{id}/cube` |
| Detected tree cover | `atlas-detect-fill`, `atlas-detect-line` | GeoJSON patches from `POST /plots/{id}/detect`; the opacity follows the confidence |
| Plots | `atlas-plot-fill`, `atlas-plot-line`, `atlas-plot-line-approx` | The plots' polygons; the outline is dashed when `boundary_quality` is `approximate` |
| Imported trees | `atlas-import-crowns`, `atlas-import-points` | Crown outlines and tree tops of an import |
| Preview | `atlas-preview-fill`, `atlas-preview-line`, `atlas-preview-point` | The file or boundary that was just read, before it becomes a plot |
| Drawing | `td-*` | terra-draw while the user draws or edits |

No threshold or classification is decided in layer code. The only choice the browser makes about a value is its colour:
a discrete eight-class NDVI palette, defined once in `apps/web/src/lib/ndvi.ts`.

## Basemap: MapLibre GL JS + PMTiles

MapLibre GL JS (BSD-3-Clause) renders vector tiles in WebGL. Tiles come from a single
[PMTiles](https://github.com/protomaps/PMTiles) archive, a cloud-optimized format in which the browser fetches only the
byte ranges it needs with HTTP Range requests. The archive is built with the Protomaps basemap pipeline from
OpenStreetMap data and placed in an S3-compatible bucket behind a CDN (`VITE_BASEMAP_PMTILES_URL`); no tile server runs
anywhere. The `pmtiles` JavaScript library registers a protocol handler, and the app's own minimal style
(`components/map/mapStyle.ts`, following the Protomaps basemap layer names: earth, landuse, natural, water, roads,
boundaries, places) points its source at `pmtiles://https://<bucket>/basemap.pmtiles`. The source carries the
attribution "© OpenStreetMap contributors".

Without `VITE_BASEMAP_PMTILES_URL`, the map loads the style at `VITE_BASEMAP_STYLE_URL`, which defaults to the MapLibre
demo tiles (`https://tiles.openfreemap.org/styles/liberty`). They are low-detail and meant for demos, so use your own
archive in production. If the style cannot be loaded (an error, or no answer within seven seconds), the map falls back
to a plain ground colour and says so, and the plots, drawing tools and data layers keep working.

### Label fonts

The built-in PMTiles style takes its label glyphs from the MapLibre demo host
(`https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf`). The address is written in `mapStyle.ts`, not set in the
environment, so a deployment with its own PMTiles archive still contacts that host unless the labels are removed, and
the web image's `ATLAS_BASEMAP_ORIGINS` must keep `https://demotiles.maplibre.org` or the labels stay blank. Making the
glyph address configurable is listed in [roadmap ideas](../community/roadmap-ideas.md).

### Why not `tile.openstreetmap.org` in production

The OpenStreetMap Foundation runs its raster tile servers for the OSM community on donated capacity, and its Tile Usage
Policy (<https://operations.osmfoundation.org/policies/tiles/>) states that heavy use, use in distributed applications
without a valid HTTP referer and `User-Agent`, bulk downloading, and use as a basemap for apps with significant traffic
are not acceptable, and that access may be blocked without notice. A public agricultural tool with unknown traffic falls
outside that policy. Hosting our own PMTiles archive costs little, keeps latency predictable, and makes the ODbL
attribution ("© OpenStreetMap contributors") our responsibility rather than someone else's bandwidth. The same reasoning
applies to Nominatim: the public instance has a strict usage policy (one request per second, a mandatory identifying
`User-Agent`), which the geocoder adapter honors; heavier deployments should self-host Nominatim or Photon
([DATA_LICENSES.md](../licensing/DATA_LICENSES.md)).

### Building the archive

```bash
# Protomaps basemap for one country extract (example: India)
pmtiles extract https://build.protomaps.com/<date>.pmtiles india.pmtiles --bbox=68.1,6.5,97.4,35.7
aws s3 cp india.pmtiles s3://carboncreditbuy-tiles/basemap.pmtiles --content-type application/octet-stream
```

Protomaps publishes daily planet builds; extracting a country or region keeps the archive at a few hundred megabytes. The
bucket needs CORS that exposes `ETag` and `Content-Range` ([infra/terraform](../../infra/terraform/README.md)), and the
web image must list the bucket's origin in `ATLAS_BASEMAP_ORIGINS`. A scripted build is a
[roadmap idea](../community/roadmap-ideas.md); today the two commands above are run by hand.

## Satellite and aerial imagery

The **Satellite** view is raster imagery for looking at the land. It is configuration, not an adapter: the API never
fetches, proxies or stores a tile, and no calculation reads one. The tree-cover detection works on Sentinel-2 vegetation
data fetched by the STAC adapters, not on these pictures.

1. `config/imagery/providers.yaml` lists the providers with their licence, attribution, coverage, `max_zoom`, key
   requirement and whether automated analysis is allowed (`analysis_allowed`). It also maps a country to a recommended
   provider: the national orthophotos for the United States, France, Spain and the Netherlands, and the global EOX
   Sentinel-2 mosaic of 2016 for every other country, India included.
2. `GET /imagery/providers?country=XX` serves that list with any key filled in from the environment. A provider whose key
   is missing comes back with `available: false` and no URL.
3. The browser adds one raster source below the NDVI layer. Its `maxzoom` is the provider's `max_zoom`, so MapLibre
   over-zooms the last level instead of asking for tiles that do not exist.
4. The attribution of the provider is shown in the map's attribution bar while the view is on. The choice is the
   recommended provider unless the user picks another in Settings (stored per country in the browser), or the deployment
   sets `VITE_SATELLITE_TILES_URL` and `VITE_SATELLITE_ATTRIBUTION`.

Two consequences follow from the browser loading the tiles itself. The provider sees the visitor's IP address and which
tiles they look at (an approximate area, never a plot boundary), and each provider's own rate limits apply to your
visitors. The tile hosts must be allowed in `ATLAS_EXTRA_IMG_SRC` and `ATLAS_EXTRA_CONNECT_SRC` of the web image or the
Content-Security-Policy blocks the tiles. If a provider's tiles keep failing (six failed requests), the attribution bar
says so and the basemap shows underneath. The providers, licences, keys and failure handling are in
[`integrations/imagery`](../../integrations/imagery/README.md); the research behind them is in
[imagery providers](../research/imagery-providers.md) and the licence rows in
[map licences](../licensing/MAP_LICENSES.md).

## The vegetation cube and the NDVI cells

The cube is a time series of index grids over the plot, served by `GET /plots/{id}/cube?index=ndvi&months=36` as plain
JSON. `index` may also be `ndmi` or `ndre`, and `months` runs from 6 to 72. It holds `times`, a `values` array of
`times × rows × cols` floats (`null` for a cell outside the polygon or masked as cloud), a `rows × cols` `mask`,
`stats_per_time` and the grid's `bbox` and `crs`. Cells are 30 m (3 × 3 of the 10 m Sentinel-2 pixels) over a monthly
minimum-cloud composite.

The grid follows the plot: its rows and columns are the plot's bounding box divided into 30 m cells, so a larger plot
has more cells, up to 40,000 (a bounding box of about 3,600 ha). Measured with the demo API for 36 months:

| Plot | Grid | JSON | Gzipped |
| --- | --- | --- | --- |
| 2 ha | 5 × 5 | 9 KB | 3 KB |
| 20 ha | 15 × 15 | 53 KB | 14 KB |
| 200 ha | 48 × 48 | 498 KB | 111 KB |
| 2,000 ha | 150 × 150 | 4.8 MB | 982 KB |

At these sizes plain JSON is the simplest thing that works, and it is why no in-browser SQL engine was added
([ADR-0002](adr/0002-json-cube-no-duckdb.md)). The browser does two things with the cube, both single passes over the
array: it turns the month the user picks into the polygons of the NDVI layer, and it plots the API's monthly means
(`stats_per_time`) in the "Change over time" card. The tree-cover detection runs on the API from the same cube
([imports and detection](imports-and-detection.md)). The web app always asks for 36 months; a very large plot makes a
heavy answer, and `months` shortens it in proportion.

## Detected tree cover, imports and drawing

Detected patches are the GeoJSON `features` of a detection record: polygons whose opacity follows their confidence,
which the record's `limitations` call a heuristic score and not a probability. An import's crowns and tree tops come
back from `GET /imports/{id}` as a map preview. The browser holds none of this beyond the current view; the records stay
on the API and are deleted with the plot.

Boundaries and tree lines are drawn with terra-draw (MIT) on top of MapLibre: a polygon mode (Boundary), a line mode
(Tree line) and a select mode for vertex editing. The browser checks a polygon for quick feedback (a simple ring of up to
500 vertices, 0.01 to 10,000 ha) and the API is the authority ([API contract](api-contract.md)). The other ways to mark
land do not use the map: a pin and a size, a tree line's width and spacing and typed coordinates go to the
`POST /geometry/*` endpoints, and a file goes to `POST /imports`, which reads it on the server.

## Performance

Nothing here is enforced by a budget test; these are the design choices that keep the map light.

- The pages are lazy-loaded routes, and MapLibre and terra-draw ship in their own chunks, so the landing page does not
  pay for the map.
- The basemap is one PMTiles archive read with range requests behind a CDN, so first paint depends on a few small
  fetches and no tile server.
- The data layers are GeoJSON sources updated with `setData`, one source per kind of data, in a fixed layer order.
- Fonts are self-hosted, and no rendering library other than MapLibre is loaded (the charts are SVG).

## Attribution

The attribution bar is always visible and is the map's own (MapLibre's default control is turned off). It lists, in this
order, the attribution of the basemap's style sources (OpenStreetMap contributors for a PMTiles basemap), the active
imagery provider's attribution, and the two data attributions the workspace always shows: ESA WorldCover and Copernicus
Sentinel, with the year ([`lib/attribution.ts`](../../apps/web/src/lib/attribution.ts)). Attribution strings are licence
obligations and are never translated. The bar also carries a metric scale. The API offers the same strings at
`GET /attribution` and [ATTRIBUTION.md](../licensing/ATTRIBUTION.md) lists them, but the web app does not call that
endpoint yet. Hiding the bar is a licence violation, not a styling choice.
