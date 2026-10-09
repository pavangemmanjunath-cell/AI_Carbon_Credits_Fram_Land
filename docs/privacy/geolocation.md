# Geolocation

This page covers how the platform obtains, uses and generalizes location:
browser geolocation, geocoding, the exact centroid used for lookups, and
the 0.05° public centroid.

## Sources of location

| Source | When | Precision | Handling |
|---|---|---|---|
| Browser Geolocation API ("locate me") | Only when the user presses the button; `Permissions-Policy: geolocation=(self)` allows it for the app's own origin only | Device-dependent (GPS to tens of metres) | Used once to center the map; never sent to the API or stored |
| Place-name search (`GET /geocode`) | User types a name | Place level | Query text goes to the geocoder with the required `User-Agent`; the result's coordinates center the map |
| Drawn polygon (`POST /plots`) | User draws or uploads | Vertex precision as drawn (five decimals ≈ 1 m) | Stored as private geometry; centroid derived server-side |
| Reverse geocoding | Live mode, when `country` is omitted, or to label the state/district | Admin level | Centroid sent to Nominatim (or the Census geocoder in the US); only admin names are kept |
| Demo mode | Always | — | Country derived from the centroid against the region bounding boxes; no external call |

## Exact centroid: what it is used for

The centroid is a point lookup key for climate normals (Open-Meteo),
elevation, and soil properties (SoilGrids). It is sent from the API to
those services without user identity. For climate the API may round the
point to the provider's native grid (Open-Meteo's archive is ~9–11 km;
SoilGrids is 250 m) before the request, which both improves cache hits and
reduces precision disclosed. Bounding boxes, not centroids, drive raster
reads for WorldCover and Sentinel-2.

## The 0.05° generalization

```text
public_lat = round(lat / 0.05) * 0.05
public_lon = round(lon / 0.05) * 0.05
```

Properties:

- **Deterministic.** The same plot always maps to the same public point,
  so there is nothing to average out across requests.
- **Grid-aligned, not jittered.** The point is a grid node, visibly not a
  farm location; a jittered point would look like a real place and invite
  false precision.
- **Coarse enough.** One cell is 0.05° × 0.05°: about 5.5 km × 5.4 km in
  Karnataka, 5.5 km × 4.7 km in Georgia, 5.5 km × 4.4 km in Andalusia. A
  cell typically contains hundreds of parcels and several villages.
- **Fine enough.** District-level statistics, regional climate and
  programme screening work at this scale.

Edge cases the implementation and tests cover: plots straddling a grid
boundary (the centroid decides); plots larger than a cell (public centroid
still a single node; area is reported separately); plots near country
borders (country comes from the exact centroid, public point may fall
across the border — the country field is authoritative); antimeridian and
polar coordinates (rejected by the ±180/±90 validation and by the regional
bounding boxes).

## Residual risks and mitigations

| Risk | Mitigation |
|---|---|
| Area + district + species + planting year narrows a plot to a few candidates in sparsely planted areas | Shared views show area rounded to 0.1 ha; the owner chooses whether to share inventory details; aggregated public maps require a minimum of 5 plots per cell before a cell is shown |
| Satellite thumbnails in reports reveal field shape | Reports include a district-scale static map by default; the exact-boundary map is an explicit owner choice |
| Repeated `/simulate` calls with `lat`/`lon` from a public kiosk | `/simulate` stores nothing and is rate-limited; share links contain no coordinates |
| Browser history and referrers | Plot ids are opaque; URLs never contain coordinates; `Referrer-Policy: strict-origin-when-cross-origin` |
| Third-party tile provider sees the viewport | Self-hosted PMTiles avoid a third party; if an external basemap or imagery provider is configured, its privacy policy applies and should be named in the deployment's notice |

## For developers

- Never log a coordinate, including in debug mode; use the plot id.
- Never put coordinates in a URL path or query string except for the
  documented lookups (`/reverse-geocode`, which is owner-initiated, and
  `/simulate`, which is stateless).
- Compute `public_centroid` in one place (`geo-engine`), test it, and
  reuse it; do not reimplement rounding in the UI.
- Keep the `/explain` schema rejection list in sync with
  [privacy-design.md](privacy-design.md).
