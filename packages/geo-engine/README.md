# geo-engine

Geospatial primitives for CarbonCreditBuy: polygon validation and geodesic measurement, privacy-safe centroid
generalisation, plot geometry built from a pin and a size or from a tree line, a parser for typed coordinates, ESA
WorldCover class handling, Sentinel-2 STAC search helpers, vegetation indices, an approximate IPCC climate-zone
classifier, the space-time vegetation cube, readers for GeoJSON, KML, KMZ, CSV and LAS or LAZ point clouds, tree-top
detection from a point cloud, and tree-cover detection from the vegetation cube.

It does the maths on geometry and rasters. It does not know about carbon, programmes or HTTP; the
[adapters](../../integrations/README.md) fetch data and the [API](../../apps/api/README.md) wires everything together.

## Install

```bash
python3 -m pip install -e packages/geo-engine                  # or: make install
python3 -m pip install -e "packages/geo-engine[live]"          # adds rasterio and pystac-client
python3 -m pip install -e "packages/geo-engine[imports]"       # adds laspy[lazrs] and defusedxml
python3 -m pip install -e "packages/geo-engine[imports,e57]"   # and pye57 for E57 point clouds
```

Required: Shapely, PyProj, NumPy and PyYAML. The extras are optional and imported lazily, so demo mode and most unit
tests run without them:

| Extra | Packages | Needed for |
| --- | --- | --- |
| `live` | rasterio, pystac-client | Live land cover and Sentinel-2 reads; a live-only function called without them raises `MissingDependencyError` |
| `imports` | laspy with the `lazrs` decoder, defusedxml | LAS and LAZ point clouds (`laspy`), KML and KMZ (`defusedxml`, which refuses DOCTYPEs and entity expansion) |
| `e57` | pye57 | E57 point clouds. Without it an E57 file raises `UnsupportedFormatError` with advice to convert to LAS or LAZ |

`requirements.txt` at the repository root pins `laspy` and `defusedxml`, so the API image reads those formats; E57 is
not installed by default.

## Public API

| Sub-package or module | Main names | Purpose |
| --- | --- | --- |
| `geo_engine.geometry` | `validate_polygon`, `ValidationLimits`, `measure_polygon`, `PlotMetrics`, `generalize_point`, `centroid_of`, `bbox_of`, `geodesic_area_perimeter`, `new_plot_id` | Validate a GeoJSON polygon, measure it on the WGS84 ellipsoid, generalise points for public views, create `PLT-XXXXXX` ids |
| `geo_engine.construct` | `polygon_from_point`, `strip_from_line`, `suggest_tree_count`, `polygon_to_geojson`, `geometry_to_geojson`, `geodesic_area_m2`, `ConstructionError` | Plot polygons from a pin and an area, or from a tree line |
| `geo_engine.coordinates` | `parse_coordinates`, `parse_coordinate_line`, `parse_coordinate_value`, `ParsedCoordinates`, `ParsedPoint` | Typed or pasted coordinates (decimal, hemisphere letters, DMS) into points or a polygon |
| `geo_engine.imports` | `parse_vector`, `describe_import`, `VectorImport`, `TreeSet`, `VectorImportParams`, `count_inside`, `ImportDataError`, `UnsupportedFormatError` | Read GeoJSON, KML, KMZ and CSV and say whether it is a boundary, tree points or tree crowns |
| `geo_engine.pointcloud` | `analyse_point_cloud`, `inspect_point_cloud`, `PointCloudParams`, `PointCloudResult`, `PointCloudInfo`, `E57_ADVICE`, `pye57_available` | Tree tops from a LAS or LAZ cloud: ground, canopy height model, local maxima |
| `geo_engine.detection` | `detect_tree_cover`, `TreeCoverParams`, `TreeCoverResult`, `load_detection_config`, `DetectionConfig`, `DetectionError`, `ConfigError` | Tree-cover patches from a vegetation cube; the loader of `config/detection.yaml` |
| `geo_engine.raster` | `WORLDCOVER_CLASSES`, `class_name`, `tile_name`, `tiles_for_bbox`, `class_shares`, `read_class_shares`, `ClassShare` | ESA WorldCover 2021 v200 class table, tile naming and masked reads |
| `geo_engine.satellite` | `PROVIDERS`, `StacProvider`, `Scene`, `search_scenes`, `best_scene_per_period`, `period_key`, `scene_from_item` | Sentinel-2 L2A search through STAC (Earth Search or Copernicus Data Space) |
| `geo_engine.indices` | `ndvi`, `ndmi`, `ndre`, `normalized_difference`, `scl_clear_mask`, `plot_statistics`, `IndexStats`, `classify_ndvi`, `classify_ndmi` | Index maths, cloud mask (SCL classes 4, 5, 6 kept), statistics and the contract's classes |
| `geo_engine.climate` | `classify_climate_zone`, `ClimateZoneResult`, `estimate_pet_mm`, `zone_label`, `CLIMATE_ZONE_LABELS` | Approximation of the IPCC 2006 climate-zone tree from temperature, precipitation and elevation |
| `geo_engine.cube` | `build_grid`, `CubeGrid`, `build_demo_cube`, `build_live_cube`, `Cube`, `TimeStats`, `month_sequence` | Times x rows x columns vegetation cube over a plot |

Errors: `GeoEngineError` (base), `GeometryError` (has a stable `.code`; `ConstructionError` and its subclasses extend
it), `MissingDependencyError`, `ImportDataError` and `UnsupportedFormatError` (both with a `.code`), and
`DetectionError` and `ConfigError` for the detection module.

### Example

```python
from datetime import date

from geo_engine.errors import GeometryError
from geo_engine.geometry import (
    ValidationLimits,
    generalize_point,
    measure_polygon,
    validate_polygon,
)
from geo_engine.cube import build_demo_cube

geometry = {
    "type": "Polygon",
    "coordinates": [
        [[77.50, 13.00], [77.51, 13.00], [77.51, 13.01], [77.50, 13.01], [77.50, 13.00]]
    ],
}
try:
    polygon = validate_polygon(
        geometry, ValidationLimits(max_vertices=500, min_area_ha=0.01, max_area_ha=10_000)
    )
except GeometryError as exc:
    print(exc.code, exc.detail)  # e.g. "too_many_vertices"
    raise

metrics = measure_polygon(polygon)  # area_hectares, area_acres, perimeter_m, bbox, public centroid
print(metrics.area_hectares, generalize_point(13.2923, 77.5384))  # (13.3, 77.55)

cube = build_demo_cube("PLT-DEMO01", polygon, index="ndvi", months=36, end=date(2026, 9, 1))
payload = cube.to_dict(mode="demo")  # grid, times, mask, values, stats_per_time, provenance
```

Building a plot from a pin, and finding tree cover in the cube of that plot:

```python
from datetime import date

from geo_engine.construct import polygon_from_point
from geo_engine.cube import build_demo_cube
from geo_engine.detection import detect_tree_cover
from geo_engine.geometry import validate_polygon

plot = polygon_from_point(13.0, 77.5, area_ha=2.0, shape="square")
print(plot["area_hectares"], plot["side_m"])  # within 0.1 % of 2.0 ha

cube = build_demo_cube("PLT-DEMO02", validate_polygon(plot["geometry"]), end=date(2026, 9, 1))
# the settings come from config/detection.yaml
result = detect_tree_cover(cube.to_dict(mode="demo"), plot["geometry"])
print(result.patches, result.covered_fraction)  # patches found, share of the plot they cover
```

## Behaviour worth knowing

**Polygon validation** (`validate_polygon`)

- Input is a GeoJSON `Polygon` dictionary; positions are `[lon, lat]` or `[lon, lat, z]` (the elevation is dropped). An
  unclosed ring is closed automatically; interior rings (holes) are allowed.
- Defaults: at most 500 vertices and 0.01 to 10,000 hectares (geodesic area). The API passes its own limits from
  `ATLAS_MAX_PLOT_VERTICES` and `ATLAS_MAX_PLOT_AREA_HA`.
- Failure raises `GeometryError` with one of the codes `invalid_geometry`, `invalid_coordinate`, `too_few_vertices`,
  `too_many_vertices`, `zero_area`, `self_intersection`, `area_too_small`, `area_too_large`. The API turns each into an
  RFC 7807 problem.
- The function returns a normalised Shapely polygon. Code that stores geometry should store that, not the raw client
  input (see the geometry caveat in [`data/schemas/schema.sql`](../../data/schemas/schema.sql)).

**Privacy.** `generalize_point` snaps a point to a 0.05 degree grid (about 5.5 km); `measure_polygon` returns both the
exact and the public centroid and the caller decides which one leaves the server. Plot ids come from `secrets` and are
unguessable. Nothing in `construct`, `coordinates`, `imports`, `pointcloud` or `detection` logs or stores a
coordinate, and their error messages and warnings name line numbers or counts, never positions.

**Pin and size** (`polygon_from_point`). A square or a 64-sided circle is built in a local azimuthal-equidistant
projection centred on the pin, transformed back to WGS84 and scaled until its geodesic area is within 0.1 % of the
request (the API contract promises 0.5 %). It returns `geometry`, `area_hectares`, `side_m` or `radius_m`, and `method`.
Vertices are rounded to 7 decimals (about 1 cm). Errors: `InvalidPointError` (range, pole, antimeridian),
`InvalidAreaError` (not positive, below the plot minimum, above the limit).

**Tree line** (`strip_from_line`). A line of at most 500 vertices and 50 km is buffered by half of `width_m` (1 to 50 m,
flat caps) in a local metric projection; the length is measured on the ellipsoid. `suggest_tree_count(length, spacing)`
is `floor(length / spacing) + 1`, one tree at each end. Errors: `InvalidLineError`, or the usual validation codes (for
example `area_too_small` for a strip below 0.01 ha).

**Typed coordinates** (`parse_coordinates`). One point per line, latitude first: decimal degrees (a decimal comma is
understood when the line has no dot), hemisphere letters as prefix or suffix (S and W are negative and the letters
decide which value is the latitude), degrees-minutes-seconds with `°` `'` `"` or `d m s` markers, degrees and decimal
minutes, and optional `lat:` and `lon:` labels. A pair outside range in the first position is swapped with a warning.
One point gives `kind = "point"`, three or more give `"polygon"` (closed and validated like a plot), two give
`"invalid"`. Limits: 500 data lines and 20,000 characters. Points are rounded to 7 decimals.

**Imports** (`parse_vector`, `describe_import`). GeoJSON, KML, KMZ and CSV (decimal, semicolon, tab or pipe delimited;
`lat`, `lon` and common aliases) are read into one of three kinds:

- `boundary`: the largest polygon (with several large ones, the largest is used and a warning says so), or the corner
  points when `purpose = boundary` or when 3 to 50 plain points form a valid polygon of at least 0.01 ha.
- `tree-crowns`: many small polygons (all below 0.05 ha, a median area below 200 m2, or ten or more), counted by
  centroid.
- `tree-points`: points; a numeric `score`, `confidence`, `prob` or `probability` column is used with `min_confidence`
  (0.5 by default), and a `height` column feeds the height statistics.

`describe_import` adds counts inside a plot, height statistics and a map preview (at most 5,000 features, an even
subsample above that). Structural limits are named constants: 20,000 features, 2 million vertices, archives of at most
50 MB and 100 entries (KMZ). The thresholds above live in the `vector_import` section of `config/detection.yaml`. An
`ImportDataError` carries a stable `.code` (for example `no_features`, `unsafe_xml`, `bad_archive`,
`too_many_features`); the API turns it into 422 `invalid-file`, and an `UnsupportedFormatError` into 415.

**Point clouds** (`analyse_point_cloud`). LAS and LAZ (and E57 with `pye57`) are read in chunks; noise classes are
dropped, a cloud above `max_points` (30 million) is thinned deterministically with a warning, and a header declaring
more than 300 million points is refused before decoding. Coordinates become metres; a cloud in degrees is refused and a
cloud without a CRS is analysed as metres but cannot be placed on the map. The pipeline is: ground model (the
ground-classified points, or the lowest return per 5 m cell when too few are classified) -> normalised height ->
canopy height model (maximum per cell, 0.5 m cells, raised automatically to keep the grid within 4,000 x 4,000 cells)
-> 3 x 3 mean smoothing -> local maxima above 2 m within a 1.5 m window = tree tops. The result has the count, the
heights, canopy cover and the tops in WGS84. `inspect_point_cloud` reads only the header, which the API uses when
detection is switched off. `geo_engine.pointcloud.synthetic` writes deterministic synthetic orchards as LAS or LAZ for
tests and sample data; the API never calls it.

**Tree cover** (`detect_tree_cover`). On the cube that `GET /plots/{id}/cube` returns: median NDVI of the last months
(ignoring cloud-masked values) per cell inside the plot, cells at or above the threshold, 8-connected patches, patches
smaller than `min_patch_cells` dropped, a heuristic confidence per patch (the NDVI margin, the patch size and how many
months it stays above the threshold; a ranking score, not a probability), patches below `min_confidence` dropped, and
polygons clipped to the plot. All numbers come from the `tree_cover` section of `config/detection.yaml`.
`DetectionError` carries a `.code` such as `invalid_cube` or `no_imagery`. Because the cube is a 30 m grid, a patch is a
group of trees, not a crown.

**Parameters are configuration.** `config/detection.yaml` holds every tunable number of the three sections
(`point_cloud`, `tree_cover`, `vector_import`) as `{value, unit, source, verification_status}`. A missing key is a hard
error (`ConfigError`), nothing numeric is hidden in Python, and every tunable value is flagged `assumption`: calibrate
locally before relying on a result. [`docs/architecture/imports-and-detection.md`](../../docs/architecture/imports-and-detection.md)
explains the algorithms and their limits.

**Cube.** The grid is regular in EPSG:4326 with 30 m cells by default and a ceiling of 40,000 cells (a larger plot
needs a larger `cell_size_m`). `mask` is 1 where the cell centre falls inside the polygon. Supported indices are `ndvi`,
`ndmi` and `ndre`. `build_demo_cube` is deterministic per plot id and labelled synthetic; `build_live_cube` reads
Sentinel-2 through STAC, keeps the lowest-cloud scene per month and records scene ids in `provenance`.

**Climate zones.** `classify_climate_zone` approximates IPCC 2006 Vol. 4 Ch. 3 Fig. 3A.5.1 from mean annual
temperature, precipitation and elevation, using Holland (1978) for potential evapotranspiration. Every result carries
`verification_status: assumption`, and the `subtropical_*` zones are never produced automatically.

## Tests

```bash
python3 -m pytest packages/geo-engine -q       # 409 tests, a few seconds
```

| File | Covers |
| --- | --- |
| `tests/test_geometry.py` | Area on the ellipsoid, closing rings, error codes, limits, 0.05 degree generalisation, plot ids |
| `tests/test_construct.py` | Pin and area polygons (area within tolerance, square and circle, determinism, plot limits, stable error codes) and tree-line strips (area, coverage, bent lines, tree counts, vertex limits, no echoed coordinates) |
| `tests/test_coordinates.py` | Decimal, hemisphere-letter, DMS and decimal-minute formats, mixed pastes, swapped order, one, two and three points, self-intersection, limits, no coordinates in warnings, single values for CSV cells |
| `tests/test_vector_imports.py` | GeoJSON, KML, KMZ and CSV parsing, classification into boundary, tree points and crowns, counting inside a plot, unsafe XML and archive limits |
| `tests/test_pointcloud.py` | Synthetic orchards as LAS and LAZ: ground, canopy height model, tree counts within 10 %, density, thinning, CRS handling, E57 advice, damaged files |
| `tests/test_detection.py` | Tree-cover composite (median of the last slices, nulls ignored), thresholds, 8-connected patches, confidence formula, clipping to the plot, malformed cubes, determinism, and the `config/detection.yaml` loader (citations, no pending parameter, missing keys) |
| `tests/test_indices_and_climate.py` | NDVI/NDMI/NDRE hand values, SCL mask, statistics, classes, PET, the zone decision tree |
| `tests/test_stac_and_cube.py` | Scene selection per month, STAC item mapping, grid, deterministic demo cube, aggregation |
| `tests/test_worldcover.py` | Class table, tile naming, tiles for a bounding box, class shares |

Tests never touch the network; live paths are exercised with synthetic arrays and dictionaries. The point-cloud and
KML tests need the `imports` extra, which `requirements.txt` installs.

## Design notes

- Index and class thresholds match [`docs/architecture/api-contract.md`](../../docs/architecture/api-contract.md): NDVI
  sparse below 0.3, moderate to 0.6, healthy from 0.6; NDMI dry below 0.0, moderate to 0.3, moist from 0.3.
- Numbers that are scientific assumptions (zone thresholds, PET relation, detection parameters) are named constants or
  configuration entries with a source string, so they appear in provenance rather than hiding in code.
- Network access is confined to `satellite.search_scenes`, the raster readers (`raster.read_class_shares`) and
  `cube.build_live_cube`; all three sit behind lazy imports and are called only from the adapters in `integrations/`.
  The v0.2 modules (`construct`, `coordinates`, `imports`, `pointcloud`, `detection`) work on bytes and arrays that the
  caller passes in; none of them opens a socket or a file by itself.

## Links

- [Imports and detection](../../docs/architecture/imports-and-detection.md)
- [Architecture tour](../../docs/developer-guide/architecture-tour.md)
- [Data flow](../../docs/architecture/data-flow.md)
- [Privacy design](../../docs/privacy/privacy-design.md) and [geolocation notes](../../docs/privacy/geolocation.md)
- [Data licences](../../docs/licensing/DATA_LICENSES.md)
