# Geometry helpers, imports and detection (v0.2)

This page explains **how** the v0.2 endpoints for simpler land input, "Import data" and "AI
detected tree cover" calculate their results: the algorithms, the parameters and where they live,
the limits, what is private, and what the results cannot tell you. The request and response shapes
are in [`api-contract.md`](api-contract.md) (section "v0.2 additions"); this page does not repeat
them.

| Part | Endpoints | Engine | API layer |
| --- | --- | --- | --- |
| Geometry helpers | `POST /geometry/from-point`, `/from-line`, `/parse-coordinates` | `geo_engine.construct`, `geo_engine.coordinates` | `services/geometry.py` |
| Imports | `POST/GET /imports`, `GET/DELETE /imports/{id}` | `geo_engine.imports`, `geo_engine.pointcloud` | `services/imports.py` |
| Detection | `POST /plots/{id}/detect`, `GET /plots/{id}/detections` | `geo_engine.detection` | `services/detection.py` |

All of it is deterministic: the same input and the same `config/detection.yaml` give the same
output. No LLM is involved and no coordinate is ever sent to one. Nothing here produces a carbon
number; a tree count or a tree-cover patch is an input to later steps, not a result to quote.

## 1. Geometry helpers (nothing is stored)

### Pin and area (`from-point`)

The shape (a square, or a 64-sided circle) is built in a local azimuthal-equidistant projection
centred on the pin, transformed back to WGS 84, and then **scaled iteratively until its geodesic
area is within 0.1 % of the request** (the contract promises 0.5 %). The geodesic area is the
ellipsoidal area computed by PROJ's geodesic routines, which implement Karney's algorithms
(C. F. F. Karney, "Algorithms for geodesics", *Journal of Geodesy* 87, 43-55, 2013). The polygon
is then passed through the same validation as `POST /plots` (vertex limit, minimum and maximum
area, simple ring), so the result can be posted unchanged. Units are hectares, acres
(1 ac = 0.40468564224 ha) or square metres. Pins within the polygon's reach of a pole, or a shape
that would cross the antimeridian, are refused with a plain message.

The `method` string states exactly what was done ("geodesic square centred on the pin (side 142.2 m)")
and the response says `boundary_quality: "approximate"`: a pin and a size is not a surveyed
boundary, and the carbon estimate for such a plot carries lower confidence.

### Tree line (`from-line`)

The line is buffered by `width / 2` with flat caps in a local metric projection centred on the
line, then transformed back. The length is measured on the ellipsoid (`Geod.line_length`), the
area is geodesic, and the suggested tree count is `floor(length / spacing) + 1` (a tree at each
end). A strip that needs more than the plot vertex limit is simplified with a tolerance of at most
a quarter of the width, or refused. Limits: 2-500 vertices, a length of at most 50 km, a width of
1-50 m, and the usual plot minimum area (0.01 ha), so a very short thin line is refused with
`area_too_small`.

### Typed coordinates (`parse-coordinates`)

One point per line; decimal degrees, hemisphere letters, degrees-minutes-seconds (with `°'"`,
typographic marks, `d m s`, or spaces) and degrees with decimal minutes are read, with `,` or `.`
as the decimal mark. Latitude comes first unless hemisphere letters say otherwise; if the first
value cannot be a latitude and the second can, the pair is swapped **with a warning**. Lines that
cannot be read are skipped and reported by line number only; they are never guessed. One point
gives a `Point`; three or more give a polygon (the ring is closed automatically and validated like
a plot); two points are `invalid` with a hint. Warnings never contain the coordinates. Limits: 500
lines, 20 000 characters.

## 2. Imports ("Import data")

`POST /imports` turns an uploaded file into a **derived record**. The raw file is read from memory,
interpreted and discarded; only the record (summary, boundary or counts, an optional map preview,
warnings, provenance) is kept, through the generic record API (`kind: "import"`), marked
`privacy: "private"` and deleted with its plot.

### Checks before anything is parsed

1. **Size.** The limit is `ATLAS_MAX_UPLOAD_MB` (default 50). It is enforced three times: a
   `Content-Length` above the limit is refused before any body is read; the request stream is
   counted while the multipart body is parsed, so a chunked upload without `Content-Length` is cut
   off as soon as it passes the limit; and the file is read in 1 MiB chunks. The limit applies to
   the request body, so a file very close to the limit may be refused by a few hundred bytes of
   multipart framing. Over the limit: **413**.
2. **Extension.** `.geojson`, `.json`, `.kml`, `.kmz`, `.csv`, `.las`, `.laz`, and `.e57` only
   where the optional `pye57` package is installed (otherwise **415** with advice to convert to
   LAS/LAZ with CloudCompare or PDAL). Anything else: **415**.
3. **Signature.** The first bytes must fit the extension (`LASF` for LAS/LAZ, a ZIP header for
   KMZ, `<` for KML, `{` for GeoJSON, no NUL bytes for CSV, `ASTM-E57` for E57); a renamed file is
   **415** with `code: "signature_mismatch"`. The file name stored in the record is the base name
   only, without control characters and at most 200 characters.
4. **Empty file**: 422.

Problems are RFC 7807 documents. Engine problems carry a stable `code` (`invalid_content`,
`unsafe_xml`, `archive_too_large`, `too_many_features`, `invalid_boundary`, `geographic_crs`,
`truncated`, ...). Their messages are written by the code, never copied from a parser, so they do
not contain coordinates.

### Vector files (GeoJSON, KML, KMZ, CSV)

* **GeoJSON** must be WGS 84 longitude/latitude (a coordinate outside the WGS 84 range is refused
  with the advice to reproject). Lines are not imported. At most 20 000 features.
* **KML / KMZ** are parsed with `defusedxml`; a document with a DOCTYPE or entity declaration
  (external entities, "billion laughs") is refused outright (`unsafe_xml`). A KMZ must hold at
  most 100 entries and expand to at most 50 MB, checked from the archive's directory *and* while
  decompressing; the first `.kml` is used (`doc.kml` preferred). Without the `defusedxml` package
  KML and KMZ answer 415 `xml_backend_missing` rather than fall back to an unsafe parser.
* **CSV** columns are found by header name (`lat`, `latitude`, `y` and `lon`, `lng`, `long`,
  `longitude`, `x`; a `name`, `label` or `title` column names the point; other numeric columns such
  as `score` and `height` are kept). Without a recognised header the first two columns are read as
  latitude, longitude (and a first row without digits is skipped as a header). The delimiter
  (`,` `;` tab `|`) and decimal commas are detected, values may be decimal degrees or
  degrees-minutes-seconds, and a file that is not UTF-8 is read as Windows-1252 with a warning.
  At most 20 000 rows.

What the file **is** depends on `purpose` (`auto`, `boundary`, `trees`):

| Content | `auto` reads it as |
| --- | --- |
| One polygon, or polygons of which at least one is 0.05 ha or larger and the small ones do not dominate | **boundary**: the largest polygon (a warning says when several were present) |
| Many small polygons | **tree-crowns** (see rule below) |
| Many points | **tree-points** |
| 3-50 points enclosing at least 0.01 ha | **boundary**: corners in file order, ring closed automatically, with a warning (`purpose=trees` counts them as trees instead) |

The crown rule, with the numbers from `config/detection.yaml` (`vector_import`): when every
polygon is below `crown_max_area_ha` (0.05 ha), the file is crowns if there are at least
`min_polygons_for_median` (3) of them with a median area below `crown_median_area_m2` (200 m²), or
at least `crown_count_threshold` (10) of them. When a larger polygon is present (a field outline)
the small polygons must number at least 10 *and* outnumber the large ones, so a field boundary
with a pond or two stays a boundary. These are heuristics: when they guess wrong the answer is the
`purpose` field, which overrides them (`boundary` on a file that is crowns is refused with an
explanation, typically that the polygon is below the minimum plot area; it is never silently
reinterpreted).

A boundary is validated exactly like `POST /plots` (simple ring, minimum area, maximum area,
vertex limit; a boundary over the vertex limit is simplified with the smallest tolerance that
fits, and the warning says so). Rounding to 7 decimal places (about 1 cm) happens **before**
validation, so what is returned is what was validated.

**Trees.** A numeric field named `score`, `confidence`, `prob` or `probability` is used as a
confidence: values in 0-1 as they are, values up to 100 as percentages (with a warning), anything
else disables the filter (with a warning). Features below `min_confidence` (request value, default
0.5 from the config) are dropped; features with no value are kept and counted in a warning. A
numeric field named `height`, `height_m`, `h`, `tree_height` or `tree_height_m` supplies heights
(non-positive values are ignored). **Crowns are counted by their centroid**, points as they are, and "inside the plot"
means intersecting the plot polygon (the edge counts). `canopy_cover_fraction` for crowns is the
area of the union of the kept crowns (overlaps counted once) inside the plot, divided by the plot
area. Counting is a count of *features* in the file: if a segmentation tool outputs two polygons
for one tree, that tree is counted twice.

The map `preview` holds the boundary and up to 5 000 trees (an even, deterministic subsample when
there are more, with a warning); it is as private as the plot polygon and is left out of list
responses.

### Point clouds (LAS, LAZ)

The pipeline is the standard canopy-height-model (CHM) approach: normalise heights against the
ground, take the highest return per cell, and look for local maxima. It uses only NumPy (no SciPy,
no PDAL). Parameters are in `config/detection.yaml` (`point_cloud`).

1. **Read.** `laspy` decodes LAS 1.0-1.4 and LAZ (LAZ needs `laspy[lazrs]`; without a backend the
   answer is 415 "upload LAS instead"). A header that declares more than 300 million points is
   refused before decoding; above 30 million points the cloud is thinned deterministically (every
   k-th point) with a warning. Points classified 7 (low noise) or 18 (high noise) are dropped.
2. **CRS and units.** The CRS comes from the header. A **geographic** CRS (degrees) is refused
   with advice to export in a projected CRS such as the UTM zone. Foot-based CRSs are converted
   to metres from the CRS definition. A cloud with **no CRS** is still analysed, with coordinates
   and heights taken as metres, but it cannot be placed on the map: `georeferenced: false`,
   `count_in_plot: null`, no preview, and a warning.
3. **Ground.** If at least `ground_class_min_share` (1 %) of the points carry ASPRS class 2, the
   ground model is the mean height of class-2 points per `ground_cell_size_m` (5 m) cell;
   otherwise it is the **lowest return per 5 m cell** (a warning says this can sit above the true
   ground under dense canopy, so heights are then underestimated). Gaps are filled from the
   nearest cells and the surface is sampled by bilinear interpolation.
4. **Normalised height** = z minus the interpolated ground; below ground is set to zero, and
   points higher than `max_tree_height_m` (80 m) are treated as noise.
5. **CHM** = the maximum normalised height per `cell_size_m` (0.5 m) cell; the cell size is raised
   automatically so that the grid never exceeds 4 000 x 4 000 cells.
6. **Smoothing** with a NaN-aware 3 x 3 mean filter, so single missing returns do not create holes.
7. **Tree tops** are cells that equal the maximum of a circular window of radius
   `window_radius_m` (1.5 m) on the smoothed CHM, whose unsmoothed 3 x 3 maximum is above
   `min_height_m` (2 m). Touching maxima (plateaus) merge into one top. The tree height is that
   unsmoothed maximum, so smoothing finds the tops without lowering the heights.
8. **Statistics.** `mean_height_m`, `median_height_m` and `p90_height_m` of the tops;
   `canopy_cover_fraction` = share of CHM cells (that have data) above `min_height_m`. **Counts
   and heights describe the whole cloud**, not only the plot (the method string says so);
   `count_in_plot` is the number of tops intersecting the plot polygon.

A warning is added when the point density is below `low_density_warning_per_m2` (2 points/m²).
With `run_detection=false` only the header is read: the point count, CRS and footprint are
returned, no trees. A footprint that does not overlap the linked plot gives a warning that the
file may be the wrong one.

**Resources.** Decoding and analysis are done in memory, in chunks of one million points. On the
development machine a synthetic 12.3 million point LAZ (63 MB) took about 7 s and a peak of about
0.8 GB of memory, and the 4.5 points/m² sample (184 000 points) well under a second; budget about
2 GB for the 30 million point cap. On a small server lower `ATLAS_MAX_UPLOAD_MB`, or `max_points`
in the config (the cloud is then thinned and a warning says so).

`.e57` is read only when `pye57` is installed; E57 support is therefore optional and untested in
the default deployment.

## 3. Detection ("AI detected tree cover" from satellite data)

The input is the vegetation cube that also feeds the map's NDVI cells and the change-over-time chart
(`GET /plots/{id}/cube`, NDVI, the last 36
months); in demo mode that cube is **synthetic**, and the result says so in its `limitations`.

1. **Composite.** Per cell, the median of the last `composite_slices` (3) monthly NDVI slices,
   ignoring cloud-masked (null) values.
2. **Candidates.** Cells with a composite NDVI at or above `ndvi_tree_cover_threshold` (0.6).
3. **Patches.** 8-connected groups of candidate cells (breadth-first search); groups smaller than
   `min_patch_cells` (2) are dropped.
4. **Heuristic confidence**, a ranking score between 0 and 1 (**not a probability**):

   `confidence = w_s * spectral + w_z * size + w_p * persistence`, with
   `spectral = clamp((mean NDVI - threshold) / (ceiling - threshold))`,
   `size = min(1, cells / reliable_cells)` and `persistence` = the share of the composite months
   in which the patch's mean NDVI is at or above the threshold. The weights are 0.5, 0.3 and 0.2
   (they must sum to 1), the ceiling is 0.9 and `reliable_cells` is 6. Patches below
   `min_confidence` (request value, default 0.5) are dropped and counted in
   `parameters.dropped_patches`.
5. **Polygons.** Each patch is the union of its cell rectangles, clipped to the plot (shrunk by
   about 1 cm so that rounding cannot push a vertex outside), snapped to a 1 cm grid, and checked:
   if snapping would make the polygon invalid or leave the plot, a finer grid or the exact
   coordinates are used instead. Patch edges follow the grid.

`summary.covered_fraction` is the geodesic area of the kept patches over the plot's area. The
latest five detections of a plot are stored (`kind: "detection"`, private); older ones are pruned,
and deleting the plot deletes them all.

Honest reading of a result: it shows **where the satellite sees dense green vegetation that
looks like tree cover**, at the cube's resolution (30 m cells in the demo cube, so groups of
trees, never single crowns). NDVI is also high for dense crops, grass and shrubs; the threshold is
a project assumption that has not been calibrated for any crop, season or region; and a plot of
only a few cells can show no patch at all (the result then says so). Every result lists these
limitations and the parameters used.

## 4. Parameters

Every tunable number is in [`config/detection.yaml`](../../config/detection.yaml) as
`{value, unit, source, verification_status}`, loaded by `geo_engine.detection.config` (which
rejects a missing parameter, a wrong type or weights that do not sum to 1). Records name the
parameter set they used (`provenance.parameter_set`: file section, version and the weakest
`verification_status` in that section), and the detection and point-cloud results list the values
actually applied. Sections:

| Section | Used by | Parameters |
| --- | --- | --- |
| `point_cloud` | LAS/LAZ | `cell_size_m`, `min_height_m`, `window_radius_m`, `max_tree_height_m`, `ground_cell_size_m`, `ground_class_code`, `noise_class_codes`, `ground_class_min_share`, `smoothing_window_cells`, `max_points`, `max_points_hard_limit`, `max_ground_gap_cells`, `low_density_warning_per_m2` |
| `tree_cover` | satellite detection | `ndvi_tree_cover_threshold`, `min_patch_cells`, `composite_slices`, `confidence_ndvi_ceiling`, `confidence_reliable_cells`, `confidence_weight_spectral`, `confidence_weight_size`, `confidence_weight_persistence`, `default_min_confidence` |
| `vector_import` | GeoJSON/KML/KMZ/CSV | `crown_median_area_m2`, `min_polygons_for_median`, `crown_count_threshold`, `crown_max_area_ha`, `default_min_confidence`, `corner_points_min`, `corner_points_max`, `corner_min_area_ha` |

**None of the tunable numbers is verified.** They are `assumption` values ("project assumption
v0.1"): sensible starting points, not calibrated against field data for any species, crop, sensor
or region. Only the ASPRS class codes (ground = 2, low noise = 7, high noise = 18) are `verified`,
against the ASPRS LAS 1.4 specification. Calibrate locally before relying on a result: compare
tree counts with a field count and the satellite patches with a ground-truth map, then change the
number *and its `source`* together. A data-quality test (`tests/data-quality/
test_detection_parameters.py`) checks that every parameter has a unit, a source and a
`verification_status`, and fails if any is still `pending`.

Limits that are part of the API contract are named constants in the code, not parameters: 20 000
features per vector file, 5 000 preview features, 50 MB and 100 entries per KMZ, a CHM of at most
4 000 x 4 000 cells, and the upload size from `ATLAS_MAX_UPLOAD_MB`.

## 5. Privacy and security

* **The raw upload is never stored**, and a rejected upload is discarded as well. Records are
  `privacy: "private"`, like the plot polygon; the preview and the boundary are returned only to
  the caller who asks for the record, and everything linked to a plot is deleted with the plot.
* **No coordinate is logged.** Services convert engine and parser errors into problems that carry
  a code and a plain message (never the parser's text, which can quote the offending value), do
  not chain the original exception, and audit events hold counts and format names only
  (`import.created`: format, kind, size; `plot.detected`: target, patches). File names are not
  logged. The log formatter additionally scrubs coordinate-like numbers.
* **No coordinate goes to an LLM.** These endpoints do not call one; the agents see only derived
  indicators.
* **Hostile files.** XML is parsed with `defusedxml` and a DOCTYPE is refused; KMZ archives are
  bounded in size and entry count before and while they are decompressed and are never extracted
  to disk; the declared point count of a LAS/LAZ file is checked before decoding; bodies are cut off
  at the upload limit even when `Content-Length` is missing; file names are reduced to a base name.
* **Writes need the API key** when `ATLAS_API_KEYS` is set (`POST /imports`, `DELETE
  /imports/{id}`, `POST /plots/{id}/detect`); reads and the geometry helpers (pure calculations)
  do not.

## 6. What the results can and cannot say

Accuracy of the point-cloud method on **synthetic** orchards (cone-shaped crowns standing on
slightly jittered grids, 100 m x 100 m, 1.5 m matching tolerance), produced by the generator in
`geo_engine.pointcloud.synthetic`; the tests in `packages/geo-engine/tests/test_pointcloud.py`
guard the same behaviour:

| Scenario | Planted | Found | Matched | Missed | Extra | Mean height error |
| --- | --- | --- | --- | --- | --- | --- |
| 60 trees, ground classified | 60 | 60 | 60 | 0 | 0 | 0.00 m |
| 150 trees, ground classified | 150 | 150 | 150 | 0 | 0 | 0.00 m |
| 300 trees (4-8 m), ground classified | 300 | 300 | 300 | 0 | 0 | 0.00 m |
| 500 small trees (3-6 m), dense | 500 | 498 | 498 | 2 | 0 | 0.00 m |
| 150 trees, ground unclassified | 150 | 150 | 150 | 0 | 0 | 0.13 m (heights low) |
| 60 trees on a 10 % slope | 60 | 60 | 60 | 0 | 0 | 0.01 m |
| 60 trees, 15 cm ground noise | 60 | 60 | 60 | 0 | 0 | 0.01 m |
| 60 trees, 1 point/m² ground + 4 points/m² crowns | 60 | 60 | 60 | 0 | 0 | 0.02 m |
| 60 trees, 0.5 point/m² ground + 2 points/m² crowns | 60 | 63 | 60 | 0 | 3 | 0.03 m |
| the sample file `demo-orchard.laz` (472 trees) | 472 | 472 | 472 | 0 | 0 | 0.02 m |

These are best cases: the trees are well separated, the crowns are clean cones, there is no
understorey and no wind. **Do not quote them as the accuracy on real land.** On real canopies
expect merged crowns (under-counting), double tops on broad or multi-stemmed crowns
(over-counting), and misses of trees below `min_height_m`; a fixed window radius cannot suit
crowns of very different sizes (Popescu and Wynne 2004 use a window that varies with height; this
version uses a fixed one). Below about 2 points/m² false tops appear (the last rows), which is why
that density raises a warning. Compare any count with a field count of a sample of the plot.

Other limits worth knowing:

* Vector counts are counts of **features in the file**. The import does not judge whether the
  polygons are really trees, whether they overlap, or whether a tree appears twice.
* `purpose: auto` is a heuristic; check the `kind` in the record and set `purpose` when it guessed
  wrong.
* A point cloud's `count` and heights are for the **whole cloud**; only `count_in_plot` is limited
  to the plot. Heights are above the estimated ground, not above a vertical datum.
* A cloud without CRS is analysed with coordinates assumed to be metres and cannot be tied to a
  plot; a cloud in degrees is refused.
* Satellite tree cover cannot separate trees from other dense green vegetation, works at the
  cube's cell size (30 m in the demo cube), and its `confidence` ranks patches; it is not a
  probability. In demo mode the cube is synthetic.
* Nothing here is a carbon value, a measurement of tree age or an eligibility statement. Imported
  counts feed the tree inventory as `measurement_source: "model-estimated"`; the estimates built on
  them stay estimates (`certified: false`).

## 7. Differences from the contract text

The implementation follows [`api-contract.md`](api-contract.md) section "v0.2 additions"; where it
adds to or differs from the written examples:

* **`POST /plots/{id}/detect` returns 200** with the stored Detection. Its `method` names the real
  grid ("... on the 30 m vegetation grid"; the contract's example says 10 m, which is the
  resolution of Sentinel-2 bands, not of the demo cube). The record adds `parameters` (what was
  applied, including the dropped patch counts) and `privacy`; each patch has an extra `cells`
  property.
* **Import records add** `privacy` and, in `preview` features, `in_plot`, `height_m` or
  `confidence` properties. `status` is always `"ready"`: a file that cannot be read is an HTTP
  error (and nothing is stored), not a `"failed"` record, and `kind: "unknown"` is never returned
  (`422 no_features`).
* **`min_confidence`** is also accepted as a form field of `POST /imports` (0-1), as the contract
  text for tree points and crowns implies.
* **Error codes.** Import problems add a stable `code` (see section 2); a renamed file is 415 with
  `signature_mismatch`; an upload over the limit is 413 whether or not `Content-Length` was sent.
* **Point clouds**: `trees.canopy_cover_fraction` is the share of CHM cells above `min_height_m`
  for the whole cloud; the `method` string says counts and heights are not limited to the plot.

## 8. Code map and tests

| What | Where |
| --- | --- |
| Pin + area, tree line, GeoJSON helpers | `packages/geo-engine/geo_engine/construct.py` |
| Typed coordinates | `packages/geo-engine/geo_engine/coordinates.py` |
| Vector imports (GeoJSON, KML/KMZ, CSV, classification, counting) | `packages/geo-engine/geo_engine/imports/` |
| Point clouds (reader, CHM, analysis, synthetic generator) | `packages/geo-engine/geo_engine/pointcloud/` |
| Satellite tree cover and the parameter loader | `packages/geo-engine/geo_engine/detection/` |
| Parameters | `config/detection.yaml` |
| Services, routers, request models | `apps/api/app/services/{geometry,imports,detection}.py`, `apps/api/app/api/v1/routers/{geometry,imports,detection}.py`, `apps/api/app/schemas/{geometry,detection}_requests.py` |
| Sample files and their generator | `data/sample/imports/`, `scripts/make_sample_imports.py` |
| Tests | `packages/geo-engine/tests/test_{construct,coordinates,vector_imports,pointcloud,detection}.py`, `apps/api/tests/test_{geometry,imports,detection}_api.py`, `tests/data-quality/test_detection_parameters.py` |

Run them with `python3 -m pytest -q packages/geo-engine apps/api/tests/test_geometry_api.py
apps/api/tests/test_imports_api.py apps/api/tests/test_detection_api.py`. LAZ needs
`laspy[lazrs]` and KML needs `defusedxml` (both in `requirements.txt`; add them to the geo-engine
package's optional dependencies if it is installed on its own). E57 needs the optional `pye57`.

## 9. References

* Popescu, S. C., and Wynne, R. H. (2004). Seeing the trees in the forest: using lidar and
  multispectral data fusion with local filtering and variable window size for estimating tree
  height. *Photogrammetric Engineering and Remote Sensing* 70(5), 589-604. (Local-maximum filtering
  of a canopy height model to find treetops; this implementation uses a fixed window and no
  multispectral data.)
* ASPRS (2019). *LAS Specification 1.4 - R15*. (Classification codes: 2 ground, 7 low point
  (noise), 18 high noise.)
* Rouse, J. W., Haas, R. H., Schell, J. A., and Deering, D. W. (1974). Monitoring vegetation
  systems in the Great Plains with ERTS. *Third ERTS Symposium*, NASA SP-351, 309-317. (The
  normalised difference vegetation index.)
* Karney, C. F. F. (2013). Algorithms for geodesics. *Journal of Geodesy* 87, 43-55. (Geodesic
  area and length on the ellipsoid, as implemented in PROJ/GeographicLib.)
* Median compositing of cloud-masked time series, 8-connected component labelling, mean-filter
  smoothing and bilinear interpolation are standard techniques and are not attributed to a single
  source. The heuristic confidence formula and every threshold are this project's assumptions, not
  published values.
