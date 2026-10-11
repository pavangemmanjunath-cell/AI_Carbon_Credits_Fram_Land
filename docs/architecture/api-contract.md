# API contract — `/api/v1`

This document is the single source of truth shared by the FastAPI back end
(`apps/api`) and the React front end (`apps/web`). Field names are
`snake_case` on the wire. Coordinates are GeoJSON order `[lon, lat]`,
CRS EPSG:4326. Areas are hectares unless a field says otherwise. Every
carbon-bearing response carries `certified: false`, `confidence`,
`provenance` and a `disclaimer`.

Errors use RFC 7807 `application/problem+json`:
`{"type": "...", "title": "...", "status": 422, "detail": "...", "instance": "/api/v1/plots"}`.

Mutating endpoints accept an optional `X-API-Key` header; when the server has
`ATLAS_API_KEYS` configured the header is required. Default rate limit:
60 requests/minute per client.

The server runs in one of two modes, reported by `/health`:

- `demo` — no network needed; adapters return deterministic synthetic data
  that is clearly labelled `"source": "synthetic-demo"` in provenance.
- `live` — adapters call the configured public APIs (ESA WorldCover on AWS,
  STAC Sentinel-2, Open-Meteo, SoilGrids, geocoders, USDA NASS, data.gov.in).

---

## Shared objects

### Provenance

```json
{
  "generated_at": "2026-10-04T09:12:00Z",
  "api_version": "1",
  "mode": "demo",
  "sources": [
    {"id": "esa-worldcover", "name": "ESA WorldCover 2021 v200", "version": "v200",
     "license": "CC BY 4.0", "attribution": "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium",
     "url": "https://esa-worldcover.org/", "accessed_at": "2026-10-04T09:11:40Z"}
  ],
  "model": {"id": "tree-biomass", "version": "0.1.0"},
  "parameter_set": {"id": "species-table", "version": "0.1.0", "verification_status": "pending"},
  "notes": []
}
```

### Range

`{"low": 29.4, "central": 38.5, "high": 46.8, "unit": "tCO2e/yr"}`

### Confidence

One of `"low" | "medium" | "high"`.

---

## Endpoints

### `GET /health`
→ `{"status":"ok","version":"0.1.0","mode":"demo","time":"…"}`

### `GET /regions`
→ array of
```json
{"id":"IN","name":"India","calling_code":"+91","currency":"INR","currency_symbol":"₹",
 "units":{"area":"hectare","area_secondary":"acre"},"languages":["en","hi","kn"],
 "default_center":{"lat":20.59,"lon":78.96},"default_zoom":4.5,
 "bbox":[68.1,6.5,97.4,35.7],
 "programmes":[{"id":"in-gcp","name":"Green Credit Programme","authority":"MoEFCC","kind":"government_programme","url":"…"}]}
```

### `GET /geocode?q=<text>&country=<ISO>`
→ `{"results":[{"label":"Doddaballapura, Bengaluru Rural, Karnataka, India","lat":13.29,"lon":77.54,"bbox":[…],"admin":{"country":"IN","state":"Karnataka","district":"Bengaluru Rural"}}],"provider":"nominatim","attribution":"© OpenStreetMap contributors"}`

### `GET /reverse-geocode?lat=&lon=`
→ `{"country":"IN","state":"Karnataka","district":"Bengaluru Rural","label":"…","provider":"nominatim","attribution":"© OpenStreetMap contributors"}`

### `GET /species?country=<ISO>`
→ array of
```json
{"id":"mango","scientific_name":"Mangifera indica","common_name":"Mango","group":"broadleaf_tropical_fruit",
 "regions":["IN"],"suitable_climate_zones":["tropical_dry","tropical_moist","subtropical_humid"],
 "reference_density_per_ha":150,"max_density_per_ha":600,"maturity_years":8,
 "wood_density_g_cm3":{"value":0.55,"source":"…","verification_status":"pending"},"notes":"…"}
```

### `GET /methodologies`
→ registry entries `{"id":"ipcc-2006-vol4-ch4","name":"…","kind":"guideline|voluntary_standard|government_methodology|certification_framework","regions":["*"],"url":"…","status":"active","notes":"…"}`

### `GET /attribution`
→ `{"items":[{"id":"osm","text":"© OpenStreetMap contributors","url":"https://www.openstreetmap.org/copyright","license":"ODbL"}, …]}`

---

### `POST /plots`
Body
```json
{"name":"Plot A","country":"IN","source":"manual-drawing",
 "geometry":{"type":"Polygon","coordinates":[[[77.53,13.29],[77.54,13.29],[77.54,13.30],[77.53,13.30],[77.53,13.29]]]}}
```
Validation: valid simple polygon, 4–500 vertices, area 0.01–10 000 ha,
coordinates within [-180,180]/[-90,90]. `country` may be omitted and is then
derived from reverse geocoding (live) or the centroid bbox (demo).

→ **Plot**
```json
{"plot_id":"PLT-7F3K2Q","name":"Plot A","country":"IN","region":"Karnataka",
 "geometry":{…},"area_hectares":2.13,"area_acres":5.26,"perimeter_m":612.4,
 "centroid":{"lat":13.2923,"lon":77.5384},
 "public_centroid":{"lat":13.30,"lon":77.55},
 "source":"manual-drawing","privacy":"private","created_at":"…"}
```
`public_centroid` is generalized (rounded to 0.05°); `geometry` and
`centroid` are returned only to the owner.

### `GET /plots` → `{"items":[Plot…]}` · `GET /plots/{plot_id}` → Plot · `DELETE /plots/{plot_id}` → 204

### `POST /plots/{plot_id}/analyze`
Body (all optional): `{"layers":["landcover","vegetation","climate","soil","terrain"],"years":[2023,2024,2025,2026]}`

→ **Analysis**
```json
{"plot_id":"PLT-7F3K2Q","mode":"demo",
 "landcover":{"dataset":"ESA WorldCover","version":"2021 v200","resolution_m":10,
   "classes":[{"code":40,"name":"Cropland","share":0.62,"area_ha":1.32},{"code":10,"name":"Tree cover","share":0.24,"area_ha":0.51}],
   "tree_cover_share":0.24,"cropland_share":0.62,"provenance":{…}},
 "vegetation":{
   "indices":{"ndvi":{"value":0.76,"class":"healthy","date":"2026-09-21","scene_id":"S2B_MSIL2A_20260921T050659_N0511_R019_T43PGQ_20260921T081213"},
              "ndmi":{"value":0.21,"class":"moderate","date":"2026-09-21","scene_id":"…"}},
   "time_series":[{"date":"2024-09-22","ndvi":0.62,"ndmi":0.14,"cloud_cover":2.1,"scene_id":"…"},{"date":"2025-09-17","ndvi":0.69,"ndmi":0.18,"cloud_cover":3.4,"scene_id":"…"},{"date":"2026-09-21","ndvi":0.76,"ndmi":0.21,"cloud_cover":3.0,"scene_id":"…"}],
   "trend":{"start":"2024-09","end":"2026-09","change_pct":22.6,"statement":"Vegetation index increased approximately 23% during the evaluated period."},
   "provenance":{…}},
 "climate":{"zone":"tropical_dry","zone_label":"Tropical dry","mean_annual_temp_c":24.1,"annual_precip_mm":820,"elevation_m":880,"provenance":{…}},
 "soil":{"soc_0_30cm_g_per_kg":9.8,"provenance":{…}},
 "data_quality":{"warnings":["demo mode: synthetic observations"]},
 "generated_at":"…"}
```
NDVI classes: `sparse` < 0.3, `moderate` 0.3–0.6, `healthy` ≥ 0.6.
NDMI classes: `dry` < 0.0, `moderate` 0.0–0.3, `moist` ≥ 0.3.

### `GET /plots/{plot_id}/vegetation` → the `vegetation` block of the latest analysis.

### `GET /plots/{plot_id}/cube?index=ndvi&months=36`
Space-time cube: a time series of index grids over the plot. The web app draws one month of it as the NDVI layer, and
the tree-cover detection reads it. `values` is `times × rows × cols`, `null` outside the polygon or where cloud-masked.
```json
{"plot_id":"PLT-7F3K2Q","index":"ndvi","mode":"demo",
 "grid":{"rows":12,"cols":12,"cell_size_m":30,"bbox":[77.5366,13.2905,77.5402,13.2941],"crs":"EPSG:4326"},
 "times":["2023-10","2023-11","…","2026-09"],
 "mask":[[1,1,0,…],…],
 "values":[[[0.61,0.58,null,…],…],…],
 "stats_per_time":[{"time":"2023-10","mean":0.58,"min":0.31,"max":0.71,"valid_share":0.93}],
 "provenance":{"source":"synthetic-demo","composite":"monthly-min-cloud","cloud_mask":"SCL classes 4,5,6 kept","aggregation":"3×3 mean of 10 m pixels","scene_ids":[]}}
```

### `POST /plots/{plot_id}/trees`
Body `{"species_id":"mango","tree_count":420,"plantation_year":2023,"average_dbh_cm":null,"average_height_m":null,"survival_rate":0.85,"measurement_source":"user-reported"}`
`measurement_source` ∈ `user-reported | satellite-derived | government-data | field-measured | model-estimated`.

→ **TreeInventory**
```json
{"inventory_id":"INV-01","plot_id":"PLT-7F3K2Q",
 "species":{"id":"mango","scientific_name":"Mangifera indica","common_name":"Mango"},
 "tree_count":420,"density_per_ha":197.2,"plantation_year":2023,"age_years":3,
 "average_dbh_cm":null,"average_height_m":null,"survival_rate":0.85,"measurement_source":"user-reported",
 "data_quality":{"fields":[{"name":"tree_count","status":"supplied"},{"name":"species","status":"supplied"},{"name":"age","status":"supplied"},{"name":"dbh","status":"missing"},{"name":"height","status":"missing"},{"name":"mortality","status":"missing"}],"confidence":"medium"},
 "created_at":"…"}
```
Confidence rule: `high` when count, species, age, DBH and height are supplied;
`medium` when count, species and age are supplied; otherwise `low`.

### `GET /plots/{plot_id}/trees` → `{"items":[TreeInventory…]}`

### `POST /plots/{plot_id}/carbon-estimate`
Body `{"inventory_id":"INV-01","model":"tree-biomass"}` (both optional → latest inventory, default model)

→ **CarbonEstimate**
```json
{"estimate_id":"EST-01","plot_id":"PLT-7F3K2Q","inventory_id":"INV-01",
 "model":{"id":"tree-biomass","version":"0.1.0","tier":"1"},
 "methodology":{"id":"ipcc-2006-vol4-ch4","name":"IPCC 2006 Guidelines, Vol. 4, Ch. 4 (Forest Land), Tier 1 gain-loss","references":[{"title":"…","url":"…"}]},
 "estimate":{"low":13.2,"central":18.8,"high":24.4,"unit":"tCO2e/yr"},
 "stock":{"low":18.0,"central":25.7,"high":33.4,"unit":"tCO2e"},
 "components":{"above_ground_tco2e_yr":14.7,"below_ground_tco2e_yr":4.1},
 "annual_series":[{"year":2023,"age":0,"low":0,"central":0,"high":0,"cum_low":0,"cum_central":0,"cum_high":0}, …],
 "parameters_used":[{"name":"above_ground_biomass_growth","value":4.0,"unit":"t d.m./ha/yr","source":"IPCC 2006 Vol.4 Ch.4 Table 4.12 (tropical dry, Asia, ≤20 yr)","verification_status":"pending"},
                    {"name":"carbon_fraction","value":0.47,"unit":"t C/t d.m.","source":"IPCC 2006 Vol.4 Ch.4 Table 4.3","verification_status":"verified"}],
 "confidence":"medium","certified":false,
 "disclaimer":"Scenario estimate; not an issued carbon credit.",
 "readiness":{"score":64,"grade":"medium",
   "present_evidence":[{"id":"polygon","label":"Land polygon"},{"id":"tree_count","label":"Tree count"},{"id":"age","label":"Plantation age"},{"id":"satellite","label":"Satellite observation"}],
   "missing_evidence":[{"id":"dbh","label":"Tree diameter measurements","weight":15},{"id":"baseline","label":"Baseline land-use records","weight":12},{"id":"management","label":"Farm management history","weight":9}]},
 "provenance":{…},"generated_at":"…"}
```

### `GET /plots/{plot_id}/policy-eligibility?activity=tree_plantation`
→
```json
{"country":"IN","activity":"tree_plantation","disclaimer":"Initial screening only — not an eligibility determination.",
 "programmes":[
  {"id":"in-gcp","name":"Green Credit Programme","authority":"Ministry of Environment, Forest and Climate Change","kind":"government_programme",
   "status":"requires_assessment","requirements":["…"],"notes":["Green Credits are distinct from carbon credits under the CCTS."],
   "references":[{"title":"…","url":"…"}],"distinct_from":["in-ccts"]},
  {"id":"in-ccts","name":"Carbon Credit Trading Scheme (offset mechanism)","authority":"Bureau of Energy Efficiency","kind":"compliance_market","status":"requires_methodology_assessment","requirements":["…"],"references":[…]}
 ]}
```
`status` ∈ `potentially_applicable | requires_assessment | requires_methodology_assessment | requires_certification | not_applicable | unknown`.

### `GET /plots/{plot_id}/market-scenario?estimate_id=EST-01`
→
```json
{"currency":"INR","currency_symbol":"₹",
 "scenarios":[{"id":"low","price_per_tco2e":480,"value_per_year":{"low":6336,"central":9024,"high":11712}},
              {"id":"reference","price_per_tco2e":1100,"value_per_year":{…}},
              {"id":"high","price_per_tco2e":2100,"value_per_year":{…}}],
 "basis":{"source":"config/market/carbon-price-scenarios.yaml","as_of":"2025","note":"Illustrative scenario prices; not a quote."},
 "other_income":[{"id":"fruit_yield","label":"Mango fruit yield","value":null,"unit":"INR/yr","source":"district statistics (data.gov.in) + your records"}],
 "disclaimer":"Market-value scenario — not guaranteed revenue."}
```

### `POST /plots/{plot_id}/report`
Body `{"format":"html","language":"en","estimate_id":"EST-01"}` · formats `html | json | markdown | pdf` (pdf only when WeasyPrint is installed; otherwise 501).
→ `{"report_id":"RPT-2026-10-04-0001","format":"html","url":"/api/v1/reports/RPT-2026-10-04-0001","generated_at":"…"}`

### `GET /reports/{report_id}` → the rendered document.

### `POST /simulate`
Deterministic "what if" used by the Simulation Lab and by shareable links
(`/simulate?country=IN&species=mango&trees=420&year=2023&horizon=30`).
Body
```json
{"country":"IN","species_id":"mango","tree_count":420,"planting_year":2023,"horizon_years":30,
 "survival_rate":0.85,"area_hectares":2.13,"lat":13.29,"lon":77.54}
```
`lat`/`lon` are optional; when given (live mode) the climate zone is derived
from Open-Meteo normals, otherwise from the region default.

→ **Simulation**
```json
{"inputs":{…echo…},"climate_zone":"tropical_dry","climate_zone_label":"Tropical dry",
 "annual":{"low":13.2,"central":18.8,"high":24.4,"unit":"tCO2e/yr"},
 "series":[{"year":2023,"age":0,"low":0,"central":0,"high":0,"cum_low":0,"cum_central":0,"cum_high":0},…],
 "value_scenarios":[{"id":"low","currency":"INR","currency_symbol":"₹","price_per_tco2e":480,"value_per_year":{"low":…,"central":…,"high":…}},…],
 "programmes":[{"id":"in-gcp","name":"Green Credit Programme","url":"…","status":"requires_assessment"},{"id":"in-ccts","name":"Carbon Credit Trading Scheme","url":"…","status":"requires_methodology_assessment"}],
 "comparison":[{"country":"IN","climate_zone":"tropical_dry","annual":{…},"currency":"INR","currency_symbol":"₹","reference_value_per_year":…,"programme_summary":"Green Credit Programme · CCTS (separate mechanisms)","url":"…"},
               {"country":"US",…},{"country":"EU",…}],
 "confidence":"medium","certified":false,
 "disclaimer":"Scenario estimate; not an issued carbon credit. Market-value scenarios are not guaranteed revenue.",
 "share_params":{"country":"IN","species":"mango","trees":420,"year":2023,"horizon":30},
 "provenance":{…}}
```

Optional `"costs"` in the body — the user's own costs in the region currency; the platform has no built-in cost
values and a missing field counts as zero (listed in `not_entered`):
`{"sapling_per_tree":60,"planting_per_tree":null,"maintenance_per_ha_per_year":5000,"monitoring_per_year":null}`.
The response then carries `cost_scenario` (otherwise `null`), computed by `carbon_engine.economics`:
```json
{"currency":"INR","horizon_years":30,"total_cost":344700,"establishment":25200,
 "maintenance_over_horizon":319500,"monitoring_over_horizon":0,
 "removal_over_horizon_tco2e":{"low":231,"central":330,"high":430},
 "break_even_price_per_tco2e":{"low":802,"central":1043,"high":1490},
 "price_scenarios":[{"id":"reference","price_per_tco2e":1100,"indicative_value_over_horizon":…,"share_of_costs_covered_pct":105.4},…],
 "not_entered":["planting_per_tree","monitoring_per_year"],"discounted":false,"certified":false,"disclaimer":"…"}
```
The same `costs` object is accepted by `POST /plots/{id}/agents/run` and `POST /agents/ask`; the Market agent then
adds a cost-scenario finding.

### `POST /simulate/drivers`
Explainable AI without an AI model. Same body as `/simulate`. The carbon engine is re-run with each input the user
controls (`tree_count`, `survival_rate`, `area_hectares`) moved by ±10 %, everything else fixed.
```json
{"method":"One-at-a-time sensitivity: …","step_pct":10,"baseline":{"low":…,"central":11.02,"high":…,"unit":"tCO2e/yr"},
 "drivers":[{"input":"tree_count","value":420,"value_low":378,"value_high":462,
             "central_low":10.04,"central_high":12.12,"change_pct_low":-8.9,"change_pct_high":10.0},…],
 "factors":[{"name":"carbon_fraction","value":0.47,"unit":"t C / t d.m.","source":"IPCC 2006 Vol.4 Ch.4 Table 4.3 …","verification_status":"verified"},…],
 "weakest_evidence":["above_ground_biomass_growth","root_to_shoot_ratio"],"certified":false,"disclaimer":"…"}
```

### `POST /explain`
Privacy-preserving explanation. The body schema **rejects** any key named
`lat`, `lon`, `latitude`, `longitude`, `geometry`, `coordinates`, `polygon`.
Body `{"language":"en","indicators":{"area_hectares":2.13,"tree_count":420,"species":"Mango","ndvi":0.76,"ndvi_trend_pct":22.6,"estimate_central":18.8,"estimate_low":13.2,"estimate_high":24.4,"confidence":"medium","missing_evidence":["dbh","baseline"]}}`
→ `{"text":"…","provider":"template","privacy_note":"Only derived indicators were used; no coordinates were processed."}`
Default provider is the deterministic `template`; an `llm` provider is opt-in
via `ATLAS_EXPLAIN_PROVIDER` and still receives this payload only.

---

## Front-end contract notes

- `apps/web/src/services/api.ts` is the only module that knows URLs; it reads
  `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).
- TypeScript types for every object above live in `apps/web/src/types/api.ts`
  and mirror this document field by field.
- The web app must function in `demo` mode with no external network beyond the
  basemap style URL configured in `VITE_BASEMAP_STYLE_URL`.

---

## v0.2 additions — simpler land input, imports, detection, tree age, imagery, agents

All rules above still apply (snake_case, `[lon, lat]`, RFC 7807 errors, optional
`X-API-Key` on mutating calls, `provenance` on results, `certified: false` on
anything carbon-related, coordinates never logged and never sent to an LLM).
Feature records (imports, detections, agent runs) are stored through the generic
repository record API (`save_record(kind, id, record, plot_id)`), so deleting a
plot deletes them.

### Plot changes
`POST /plots` accepts two new optional fields:

- `source` ∈ `manual-drawing | upload | import | pin-and-area | tree-line | coordinates | qgis-plugin | api`
- `boundary_quality` ∈ `exact | approximate` (default `exact`). Use `approximate`
  for boundaries built from a pin + size or a tree line. The Plot echoes both.

### Geometry helpers (tag `geometry`) — pure calculations, nothing stored

`POST /geometry/from-point` — "drop a pin and type the size"
```json
{"lat": 13.2923, "lon": 77.5384, "area": {"value": 5, "unit": "ac"}, "shape": "square"}
```
`unit` ∈ `ha | ac | m2`; `shape` ∈ `square` (default) `| circle`. Area must be
`> 0` and `≤ ATLAS_MAX_PLOT_AREA_HA`.
→ `{"geometry": Polygon, "area_hectares": 2.0234, "area_acres": 5.0, "boundary_quality": "approximate", "method": "geodesic square centred on the pin (side 142.2 m)", "provenance": {…}}`.
The polygon's geodesic area matches the requested area within 0.5 %.

`POST /geometry/from-line` — "draw a tree line" (bund, boundary or roadside planting)
```json
{"line": {"type": "LineString", "coordinates": [[77.5370, 13.2910], [77.5395, 13.2912]]},
 "width_m": 4, "spacing_m": 5}
```
`width_m` 1–50 (default 4, strip width used as the plot), `spacing_m` 0.5–50
(default 5, distance between trees), 2–500 vertices, total length ≤ 50 km.
→ `{"geometry": Polygon, "length_m": 270.6, "area_hectares": 0.108, "suggested_tree_count": 55, "boundary_quality": "approximate", "method": "line buffered by width/2 in a local metric projection; trees = floor(length / spacing) + 1", "provenance": {…}}`

`POST /geometry/parse-coordinates` — "type latitude/longitude or corner points"
```json
{"text": "13.2923, 77.5384\n13°17'40\"N 77°32'25\"E\n13.2935 77.5400"}
```
Accepts one point per line: decimal degrees (`lat, lon` / `lat lon` / `lat;lon`),
hemisphere letters (`13.29N 77.53E`) and degrees-minutes-seconds. Latitude comes
first; if the first value is outside ±90 and the second inside, the pair is swapped
with a warning. Max 500 lines, 20 000 characters.
→ `{"points": [{"lat": 13.2923, "lon": 77.5384}, …], "kind": "point" | "polygon" | "invalid", "geometry": Point | Polygon | null, "area_hectares": 1.2 | null, "warnings": ["…"]}` — 1 point → `point`; ≥ 3 → `polygon` (ring closed automatically, validated like `POST /plots`); 2 → `invalid` with a warning.

### Imports (tag `imports`) — Trimble-style "Import data"

`POST /imports` — `multipart/form-data`
- `file` (required): `.geojson`/`.json`, `.kml`, `.kmz`, `.csv`, `.las`, `.laz` (`.e57` only when the optional `pye57` package is installed, otherwise **415** with advice to convert to LAS/LAZ with CloudCompare or PDAL).
- `plot_id` (optional): link to a plot; tree counts inside that plot are computed.
- `purpose` (optional): `auto` (default) | `boundary` | `trees`.
- `run_detection` (optional, default `true`): "Run tree detection on import".

Limits: `ATLAS_MAX_UPLOAD_MB` (default 50; **413** above), GeoJSON/KML/CSV ≤ 20 000 features, XML parsed with `defusedxml`. The raw file is **not stored** — only the derived record below.

→ **ImportRecord** (201)
```json
{"import_id": "IMP-4K2Q9X", "filename": "orchard.laz", "format": "laz", "size_bytes": 1840221,
 "created_at": "…", "plot_id": "PLT-DEMOIN",
 "kind": "boundary" | "tree-points" | "tree-crowns" | "point-cloud" | "unknown",
 "status": "ready" | "failed",
 "summary": {"feature_count": 1, "polygon_count": 0, "point_count": 412883, "georeferenced": true, "crs": "EPSG:32643"},
 "boundary": null | {"geometry": Polygon, "area_hectares": 2.13, "name": "Field 7"},
 "trees": null | {"count": 128, "count_in_plot": 120 | null, "mean_height_m": 6.4 | null, "median_height_m": 6.1 | null,
                  "p90_height_m": 8.9 | null, "canopy_cover_fraction": 0.42 | null,
                  "confidence_field": "score" | null, "min_confidence": 0.5 | null, "method": "…"},
 "detection": null | {"ran": true, "method": "canopy height model + local maxima", "parameters": {"cell_size_m": 0.5, "min_height_m": 2.0, "window_radius_m": 1.5}, "notes": ["…"]},
 "preview": null | FeatureCollection,
 "warnings": ["…"], "privacy": "private", "provenance": {…}}
```
- `boundary`: the largest polygon of a boundary file (GeoJSON/KML/CSV corner list); `kind: "boundary"`.
- `tree-points` / `tree-crowns`: many points / many small polygons (e.g. QGIS *AI Segmentation* output). A numeric field named `score`, `confidence`, `prob` or `probability` is used with `min_confidence` (default 0.5). Crowns are counted by centroid.
- `point-cloud`: LAS/LAZ → ground (class 2 when present, otherwise lowest return per 5 m cell) → canopy height model → local maxima above `min_height_m` = tree tops. Without a CRS the cloud is still analysed (`georeferenced: false`) but `count_in_plot` is `null`.
- `preview` holds up to 5 000 tree tops / crowns / the boundary for the map — private like the plot polygon; omitted from list responses.

`GET /imports?plot_id=` → `{"items": [ImportRecord without preview]}` · `GET /imports/{import_id}` → ImportRecord · `DELETE /imports/{import_id}` → 204.
The web app then calls the existing endpoints: `POST /plots` (`source: "import"`) to use a boundary and `POST /plots/{id}/trees` (`measurement_source: "model-estimated"`, plus `average_height_m` from a point cloud) to use a tree count.

### Detection (tag `detection`) — "AI detected tree cover" from satellite data

`POST /plots/{plot_id}/detect` body `{"target": "tree-cover", "min_confidence": 0.5}`
→ **Detection** (stored, latest per plot)
```json
{"detection_id": "DET-…", "plot_id": "PLT-DEMOIN", "target": "tree-cover",
 "method": "NDVI threshold + connected components on the 10 m vegetation grid",
 "index": "ndvi", "threshold": 0.6, "month": "2026-09",
 "features": {"type": "FeatureCollection", "features": [
   {"type": "Feature", "geometry": Polygon,
    "properties": {"id": "P1", "label": "tree cover", "confidence": 0.82, "area_m2": 4100.0, "mean_ndvi": 0.71}}]},
 "summary": {"patches": 6, "covered_fraction": 0.61, "area_hectares": 1.3},
 "limitations": ["10 m pixels show groups of trees, not individual crowns", "…"],
 "created_at": "…", "provenance": {…}}
```
Thresholds live in `config/detection.yaml` (with `verification_status`). `GET /plots/{plot_id}/detections` → latest Detection or 404.

### Tree age (tag `tree-age`)

`GET /tree-age/rules?country=IN&subdivision=IN-HR` → `{"version", "updated", "disclaimer", "age_classes": […], "rules": [Rule…]}` (rules exactly as in `config/tree-age/rules.yaml`).

`POST /tree-age/assess`
```json
{"country": "IN", "subdivision": "IN-KA", "setting": "farm", "species_id": "mango",
 "age_years": 60, "tree_count": 25, "girth_cm": null, "height_m": null, "plot_id": null}
```
`setting` ∈ `farm | urban | forest | any`; `age_years` 0–300; `tree_count` 1–1 000 000; optional `girth_cm` (trunk circumference at 1.3 m, 10–2 000) switches to the measured-tree path (DBH = girth / π, Chave et al. 2014 eq. 4).
→ **TreeAgeAssessment**
```json
{"inputs": {…}, "age_class": {"id": "old", "label": "Old (50–74 years)"},
 "climate_zone": "tropical_dry", "climate_zone_source": "region default (IN)",
 "carbon": {"method": "tier1-age" | "tier2-girth",
   "stored_now": Range(tCO2e), "annual_now": Range(tCO2e/yr),
   "per_tree": {"stored_now_kg_co2e": 1520.0, "annual_now_kg_co2e": 24.0},
   "curve": [{"age": 0, "stored": 0.0, "stored_low": 0.0, "stored_high": 0.0, "annual": 0.0}, …],
   "parameters_used": [ParameterUsed…], "notes": ["…"]},
 "credit_outlook": {"existing_trees": "not-eligible" | "conditional" | "eligible",
                    "summary": "Existing trees usually do not earn removal credits; new planting or avoided loss can."},
 "rules": [Rule + {"applies": true, "why": "Applies in India at any age"}],
 "certified": false, "disclaimer": "…", "provenance": {…}}
```
`curve` covers ages 0…max(age + 20, 40) (≤ 150 points). Rules are returned for
GLOBAL, the country's region (EU members → EU) and the country; a rule with a
different `subdivision`, an age outside `[min_age_years, max_age_years]` or an
incompatible `setting` is returned with `"applies": false` and a plain `why`.
Rules with `verification_status: pending` are flagged, never presented as confirmed.

### Imagery (tag `imagery`)

`GET /imagery/providers?country=IN` →
```json
{"recommended": "eox-s2cloudless-2016",
 "providers": [{"id", "name", "kind", "url", "tile_size", "max_zoom", "coverage", "resolution",
   "license", "license_url", "attribution", "requires_key", "available": true,
   "unavailable_reason": null, "commercial_use", "analysis_allowed", "open_data", "verification_status"}],
 "notes": "…"}
```
Built from `config/imagery/providers.yaml`; `${ESRI_API_KEY}` is substituted from
the environment, and a provider whose key is missing is returned with
`available: false`. Providers whose `coverage` excludes the country are listed
after the ones that cover it. `recommended` = `default_by_country[country]`,
else `default`.

### Agents (tag `agents`) — agentic AI framework

`GET /agents` →
```json
{"framework": {"name": "carboncreditbuy-agents", "version": "0.1.0", "reasoner": "template", "llm_enabled": false},
 "agents": [{"id": "carbon", "title": "Carbon agent", "role": "…", "says": "what this agent reports",
             "tools": [{"name": "estimate_carbon", "description": "…"}], "reads": ["plot", "inventory"], "writes": ["estimate"]}],
 "plans": [{"id": "full-assessment", "title": "Full assessment", "steps": ["coordinator", "land", "imagery", "trees", "carbon", "policy", "market", "review", "report", "coordinator"]}]}
```
Agents: `coordinator`, `land`, `imagery`, `trees`, `carbon`, `policy`, `market`, `review`, `report`.
Plans: `full-assessment`, `quick-estimate` (coordinator → land → trees → carbon → review → coordinator), `tree-age-check` (coordinator → trees → carbon → policy → review → coordinator).

`POST /plots/{plot_id}/agents/run` body `{"plan": "full-assessment", "question": null, "locale": "en"}`
`POST /agents/ask` body `{"question": "How much carbon if I add 200 trees?", "plot_id": "PLT-DEMOIN", "locale": "en"}` (a deterministic intent router picks the plan/agents; ≤ 500 characters; coordinates in the question are redacted before any optional LLM call).
→ **AgentRun** (stored; `GET /agents/runs/{run_id}`; `GET /agents/runs?plot_id=` lists summaries)
```json
{"run_id": "RUN-…", "plot_id": "PLT-DEMOIN",
 "plan": {"id": "full-assessment", "title": "Full assessment", "steps": ["coordinator", "land", "…"]},
 "status": "completed" | "completed-with-warnings" | "failed",
 "reasoner": {"mode": "template" | "llm", "llm_enabled": false, "provider": null},
 "started_at": "…", "finished_at": "…", "duration_ms": 42,
 "steps": [{"step": 1, "agent": "land", "status": "done" | "warning" | "skipped" | "failed", "duration_ms": 3, "summary": "…"}],
 "messages": [{"id": "M1", "step": 0, "agent": "coordinator", "agent_title": "Coordinator", "to": "team",
               "kind": "plan" | "finding" | "warning" | "handoff" | "answer" | "summary",
               "text": "plain-language sentence(s)", "facts": {"area_hectares": 2.13},
               "tool_calls": [{"tool": "measure_plot", "status": "ok" | "error" | "skipped", "duration_ms": 1, "input": {…}, "output": {…}}],
               "evidence": [{"label": "ESA WorldCover 2021", "source": "esa-worldcover", "url": "https://…"}],
               "confidence": "low" | "medium" | "high" | null, "created_at": "…"}],
 "summary": {"headline": "…", "estimate": Range | null, "readiness": 55 | null, "next_steps": ["…"], "certified": false},
 "guardrails": [{"id": "not-a-credit" | "uncertainty-present" | "provenance-present" | "no-coordinates" | "pending-parameters" | "values-separated", "status": "pass" | "warn" | "fail", "detail": "…"}],
 "certified": false, "disclaimer": "…", "provenance": {…}}
```
Tool `input`/`output` are summaries: never coordinates or geometry. Numbers always
come from the engines; an optional LLM (`ATLAS_AGENT_REASONER=llm` with an
OpenAI-compatible `LLM_API_BASE_URL` + `LLM_MODEL`) may only rephrase `text` from
redacted `facts`, and the template text is kept when it fails.

---

## v0.2 implementation notes

The "v0.2 additions" above describe the shapes that the web app and the QGIS plugin were built against. This section
records where the code says more than those examples, or something different. Each statement was checked against
`apps/api` and the engines it calls on 2026-10-05. When an example above and a note below disagree, the note describes
what the API does today. The longer explanations are in [imports-and-detection.md](imports-and-detection.md) and
[tree-age-model.md](tree-age-model.md); the agent team is explained in [../agents/README.md](../agents/README.md).

### Status codes

| Call | Success | Note |
| --- | --- | --- |
| `POST /plots/{plot_id}/detect` | 200 | It returns the detection it just stored. It does not create something at a new URL, so it is not 201 |
| `POST /geometry/from-point`, `from-line`, `parse-coordinates` and `POST /tree-age/assess` | 200 | Pure calculations; nothing is stored |
| `POST /imports`, `POST /plots/{plot_id}/agents/run`, `POST /agents/ask` | 201 | An import record or an agent run is stored |
| `DELETE /imports/{import_id}` | 204 | |

`GET /health` also returns `repository` (`memory` or `postgres`) next to `status`, `version`, `mode` and `time`. The
endpoints `GET /plots/{plot_id}/public`, `GET /plots/{plot_id}/analysis` and `GET /plots/{plot_id}/carbon-estimate`
exist although the sections above do not list them: the first is the privacy-preserving view of a plot (no `geometry`,
`centroid` or `perimeter_m`, and `privacy: "generalized-public"`), the other two return the latest stored analysis and
estimate.

### Problem types added in v0.2

Every problem body is RFC 7807, with `type` set to `https://carboncreditbuy.org/problems/<slug>`. A `code` member
carries a stable, machine-readable reason where the table says so.

| Slug | Status | When |
| --- | --- | --- |
| `invalid-geometry` | 422 | A pin, a line or typed corners are not usable. `code` names the rule, for example `area_too_small`, `invalid_width` or `coordinate_out_of_range` |
| `unsupported-file-type` | 415 | The extension is not one the server reads (`code: unsupported_extension`), the first bytes do not fit the extension (`signature_mismatch`), or the server lacks an optional reader: `pye57` for E57 (`e57_unsupported`), `defusedxml` for KML and KMZ (`xml_backend_missing`), a LAZ decoder for LAZ (`laz_backend_missing`) |
| `invalid-file` | 422 | The file was read but cannot be used. `code` is for example `no_features`, `empty_file`, `invalid_content`, `bad_archive`, `unsafe_xml`, `too_many_features`, `geographic_crs` or `empty_cloud` |
| `payload-too-large` | 413 | A JSON body above `ATLAS_MAX_BODY_BYTES` (1 MB), or an upload to `/imports` above `ATLAS_MAX_UPLOAD_MB` (50 MB) |
| `import-not-found`, `detection-not-found`, `agent-run-not-found` | 404 | `GET` or `DELETE /imports/{import_id}`; `GET /plots/{plot_id}/detections` before a detection ran; `GET /agents/runs/{run_id}` |
| `import-failed` | 500 | The file passed every check but processing failed. The message never repeats file content |
| `detection-failed` | 422 | The vegetation cube cannot be analysed (`code`: `invalid_cube` or `no_imagery`) |
| `config-error` | 500 | `config/detection.yaml` is missing or invalid |
| `plot-required` | 422 | `POST /agents/ask` without a `plot_id` |
| `invalid-subdivision` | 422 | The value is not an ISO 3166-2 code, or it belongs to another country than `country` |
| `unknown-subdivision` | 422 | A well-formed code that is not listed for the country in `config/tree-age/subdivisions.yaml` |
| `unknown-species`, `unknown-climate-zone`, `carbon-engine-error` | 422 | Tree-age inputs that the carbon engine refuses |
| `pending-parameters` | 409 | In production, a calculation would use a `pending` parameter ([below](#tree-age)) |
| `tree-age-rules-unavailable`, `imagery-providers-unavailable` | 500 | The rules file or the provider file is missing or invalid; the server log says why |

Validation errors keep the existing shape: `type` ending in `validation-error`, status 422 and an `errors` list of
`{"field", "message"}`. An unknown agent `plan` is such an error, because the plan ids are an enumeration in the
request model.

### Geometry helpers

- `POST /geometry/from-point` also returns `side_m` for a square or `radius_m` for a circle. The polygon's geodesic
  area is within 0.1 % of the request; the contract promises 0.5 %.
- `parse-coordinates` rounds points to 7 decimals (about 1 cm). Its warnings name line numbers, never the coordinates.

### Imports

- **`status` is always `"ready"`.** A file that cannot be used is rejected with a problem response and nothing is
  stored: 422 `invalid-file` (for example `no_features`), 415 `unsupported-file-type` (an unsupported extension, or
  `signature_mismatch` when the content does not fit the extension) or 413 `payload-too-large`. The value `"failed"`
  never appears in a record.
- **`kind` is one of** `boundary`, `tree-points`, `tree-crowns` or `point-cloud`. `"unknown"` is never returned: a file
  with nothing to import is the 422 `no_features` above.
- **`min_confidence`** is also accepted as a form field of `POST /imports` (a number from 0 to 1). It filters the
  `score`, `confidence`, `prob` or `probability` field of a tree file and is ignored for the other kinds.
- **`detection.parameters`** lists six values for a point cloud: `cell_size_m`, `min_height_m`, `window_radius_m`,
  `ground_cell_size_m`, `smoothing_window_cells` and `max_tree_height_m`. With `run_detection=false` the record has
  `detection.ran: false` and `trees: null`.
- **`provenance`** names the parameter set (`config/detection.yaml#point_cloud` or `#vector_import`, with its version
  and weakest `verification_status`) and, for a point cloud, the model `chm-local-maxima`.
- **`preview`** features carry `in_plot` and `confidence` (crowns), `in_plot` and `height_m` (tree tops) or `role` and
  `name` (a boundary). `GET /imports` returns the 100 newest records without `preview`.
- **The upload limit is enforced three times**: from the `Content-Length` header before anything is read, while the
  request streams (so a chunked upload without that header is cut off too), and while the file is read in 1 MiB chunks.

### Detection

- **`method` states the real grid.** The detection runs on the cube that `GET /plots/{plot_id}/cube` returns, so the
  text reads "NDVI threshold + connected components on the 30 m vegetation grid" for the default 30 m cell. The example
  above says 10 m, which is the resolution of the Sentinel-2 bands, not of the cube. `limitations` repeats the point:
  grid cells show groups of trees, not individual crowns.
- **Added fields.** The record has `parameters` (the threshold, `min_patch_cells`, `min_confidence`, the composite
  months, `cell_size_m`, the confidence weights, `verification_status`, `valid_cell_share` and `dropped_patches` with
  the counts `too_small` and `low_confidence`) and `privacy: "private"`. Each patch has `properties.cells`, the number
  of grid cells it covers.
- **Stored records.** The five newest detections of a plot are kept; `GET /plots/{plot_id}/detections` returns the
  newest.

### Tree age

- **Fields the example above leaves out.** `inputs.region`, `climate_zone_label`, `carbon.curve_method` (always
  `tier1-age`, because the curve comes from the age-only run even on the girth path), `carbon.confidence`,
  `carbon.model` (`id`, `version`, `tier`), `carbon.methodology`, `credit_outlook.based_on_rule_ids` (the applicable
  carbon-credit rules the outlook rests on) and a top-level `withheld_rule_ids`.
- **`credit_outlook.existing_trees` is never `eligible`.** The type allows it, but only a programme's own verification
  can decide that, so the engine answers `not-eligible` or `conditional`.
- **`GET /tree-age/rules`** also returns `withheld_rule_ids`, `subdivision_label` (for example "State or union
  territory") and `subdivisions`, a list of `{"code", "name", "type"}` for the country or, without `country`, for all
  countries. The web form uses it to fill the subdivision selector.
- **Production.** When `ATLAS_ENV=production`, or `ATLAS_ALLOW_PENDING_PARAMETERS=false`, `POST /tree-age/assess`
  answers 409 `pending-parameters` while a carbon parameter it needs is still `pending`, the same rule as
  `POST /plots/{plot_id}/carbon-estimate`. Rules whose `verification_status` is `pending` are withheld from both tree-age
  endpoints, and `withheld_rule_ids` names them, so a client can say that something was left out.
- `plot_id` is optional. When given, only the climate zone of that plot's latest analysis is read (404 `plot-not-found`
  for an unknown plot); no coordinate is read.

### Imagery

- The response also has `country` (the code that was asked for, or `null`), `version` and `updated` of
  `config/imagery/providers.yaml`.
- Every provider has `covers_country`: `true` or `false` for the requested country, and `null` when none was asked for.
  Providers that cover the country are listed first. A provider also carries `notes` and `sources`.
- **`url` is `null` when a key is missing**, together with `available: false` and an `unavailable_reason` such as "Set
  ESRI_API_KEY to enable". An unfilled `${...}` placeholder is never sent to a client. When a key is set, it is part of
  the tile URL that the browser needs, so use a referrer-restricted, basemap-only key.

### Agents

- **`AgentRun` also has** `question` (the question as asked, with coordinate-like text replaced by "[location
  removed]"; `null` for a plan run without a question), `locale`, `intent` (the router's decision, an object for
  `POST /agents/ask` and `null` for a plan run) and `blackboard`. The blackboard is the write log: a list of
  `{"key", "agent", "step"}` that says which agent wrote which key at which step (`agent: "request"` for the inputs).
- **Seven guardrails when an LLM is on.** The six ids in the example are always present. A seventh, `llm-rephrase`,
  is added only when the optional language-model reasoner is on. It reports how many rephrasings were kept and how many
  were rejected for a new or dropped number, coordinate-like text or a credit claim (the template text stays for those).
- **Why a tool did not return a result.** A tool call with `status: "skipped"` or `"error"` has
  `output: {"reason": "..."}` (redacted and at most 240 characters) in place of the usual summary of its output.
- **`plot_id` is required for `POST /agents/ask`.** The request model accepts a missing `plot_id`, so the answer is a
  clear 422 `plot-required` and not a generic validation error.
