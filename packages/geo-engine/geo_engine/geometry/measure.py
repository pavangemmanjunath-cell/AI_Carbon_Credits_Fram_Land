"""Geodesic measurement and privacy-preserving generalisation.

* Area and perimeter use :class:`pyproj.Geod` on the WGS84 ellipsoid
  (Karney's algorithms), so hectares are correct at any latitude without
  choosing a projection.
* The centroid is the planar centroid of the lon/lat polygon, adequate for
  field-scale plots (≤ 10 000 ha) where the distortion is far below the
  generalisation step used for public views.
* ``generalize_point`` rounds to a 0.05° grid (≈ 5.5 km) — the contract's
  privacy rule for ``public_centroid``.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyproj import Geod
from shapely.geometry import Polygon

_GEOD = Geod(ellps="WGS84")
M2_PER_HA = 10_000.0
ACRES_PER_HA = 2.4710538147  # international acre
PUBLIC_GRID_DEGREES = 0.05


@dataclass(frozen=True)
class PlotMetrics:
    """Everything the API needs to describe a plot's geometry."""

    area_hectares: float
    area_acres: float
    perimeter_m: float
    centroid_lat: float
    centroid_lon: float
    public_centroid_lat: float
    public_centroid_lon: float
    bbox: tuple[float, float, float, float]


def geodesic_area_perimeter(polygon: Polygon) -> tuple[float, float]:
    """Return ``(area_m2, perimeter_m)`` on the WGS84 ellipsoid (holes subtracted)."""
    area, perimeter = _GEOD.geometry_area_perimeter(polygon)
    return abs(float(area)), float(perimeter)


def centroid_of(polygon: Polygon) -> tuple[float, float]:
    """Return ``(lat, lon)`` of the polygon centroid."""
    c = polygon.centroid
    return float(c.y), float(c.x)


def generalize_point(
    lat: float, lon: float, grid: float = PUBLIC_GRID_DEGREES
) -> tuple[float, float]:
    """Snap a point to a coarse grid for public display (default 0.05°).

    >>> generalize_point(13.2923, 77.5384)
    (13.3, 77.55)
    """
    steps = round(1.0 / grid)
    lat_g = round(round(lat * steps) / steps, 6)
    lon_g = round(round(lon * steps) / steps, 6)
    lon_g = max(-180.0, min(180.0, lon_g))
    lat_g = max(-90.0, min(90.0, lat_g))
    return lat_g, lon_g


def bbox_of(polygon: Polygon) -> tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)``."""
    min_x, min_y, max_x, max_y = polygon.bounds
    return float(min_x), float(min_y), float(max_x), float(max_y)


def measure_polygon(polygon: Polygon) -> PlotMetrics:
    """Compute area (ha, acres), perimeter, centroid, public centroid and bbox."""
    area_m2, perimeter = geodesic_area_perimeter(polygon)
    lat, lon = centroid_of(polygon)
    plat, plon = generalize_point(lat, lon)
    area_ha = area_m2 / M2_PER_HA
    return PlotMetrics(
        area_hectares=round(area_ha, 4),
        area_acres=round(area_ha * ACRES_PER_HA, 4),
        perimeter_m=round(perimeter, 1),
        centroid_lat=round(lat, 6),
        centroid_lon=round(lon, 6),
        public_centroid_lat=plat,
        public_centroid_lon=plon,
        bbox=bbox_of(polygon),
    )
