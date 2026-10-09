"""Build plot geometry from simple inputs: a pin plus a size, or a tree line.

* :func:`polygon_from_point` — "drop a pin and type the size". The shape is built in a local
  azimuthal-equidistant projection centred on the pin, transformed back to WGS84 and then scaled
  iteratively until its **geodesic** area (Karney, via :func:`measure_polygon`) is within
  :data:`AREA_TOLERANCE` of the request (the API contract promises 0.5 %).
* :func:`strip_from_line` — "draw a tree line". The line is buffered by ``width / 2`` (flat caps)
  in a local metric projection centred on the line; the length is measured on the ellipsoid.

Both return a dict ready for the API and validate the polygon with :func:`validate_polygon`, so the
result can be posted to ``POST /plots`` unchanged. Nothing here logs or stores coordinates.

Also exported: small GeoJSON helpers (:func:`polygon_to_geojson`, :func:`geometry_to_geojson`) and
:func:`geodesic_area_m2`, shared by the import and detection modules.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from geo_engine.errors import GeometryError
from geo_engine.geometry import ValidationLimits, geodesic_area_perimeter, validate_polygon
from geo_engine.geometry.measure import M2_PER_HA

COORD_DIGITS = 7  # ~1 cm; plenty for a field boundary
AREA_TOLERANCE = 0.001  # internal target: 0.1 % (the contract promises 0.5 %)
CONTRACT_AREA_TOLERANCE = 0.005
MAX_ITERATIONS = 12
CIRCLE_QUAD_SEGMENTS = 16  # 4 x 16 = 64-sided polygon
MAX_LINE_VERTICES = 500
MAX_LINE_LENGTH_M = 50_000.0
MIN_WIDTH_M = 1.0
MAX_WIDTH_M = 50.0
SHAPES = ("square", "circle")
_GEOD = Geod(ellps="WGS84")


class ConstructionError(GeometryError):
    """Base class for errors raised while constructing geometry from simple inputs."""


class InvalidPointError(ConstructionError):
    """The pin is not a usable position (range, finiteness, antimeridian, pole)."""


class InvalidAreaError(ConstructionError):
    """The requested area is not positive, below the plot minimum or above the limit."""


class InvalidLineError(ConstructionError):
    """The tree line is not usable (vertices, width, length)."""


# ---------------------------------------------------------------------------- GeoJSON helpers
def polygon_to_geojson(polygon: Polygon, ndigits: int = COORD_DIGITS) -> dict[str, Any]:
    """GeoJSON ``Polygon`` dict (``[lon, lat]`` lists, rounded to ``ndigits``)."""
    rings = [polygon.exterior, *polygon.interiors]
    return {
        "type": "Polygon",
        "coordinates": [
            [[round(c[0], ndigits), round(c[1], ndigits)] for c in ring.coords] for ring in rings
        ],
    }


def geometry_to_geojson(geometry: BaseGeometry, ndigits: int = COORD_DIGITS) -> dict[str, Any]:
    """GeoJSON dict for a Polygon, MultiPolygon or Point."""
    if isinstance(geometry, Polygon):
        return polygon_to_geojson(geometry, ndigits)
    if isinstance(geometry, MultiPolygon):
        return {
            "type": "MultiPolygon",
            "coordinates": [polygon_to_geojson(p, ndigits)["coordinates"] for p in geometry.geoms],
        }
    if isinstance(geometry, Point):
        return {
            "type": "Point",
            "coordinates": [round(geometry.x, ndigits), round(geometry.y, ndigits)],
        }
    raise ValueError(f"cannot serialise {geometry.geom_type}")


def geodesic_area_m2(geometry: BaseGeometry) -> float:
    """Geodesic area (m², WGS84) of a Polygon or MultiPolygon (holes subtracted)."""
    if isinstance(geometry, Polygon):
        return geodesic_area_perimeter(geometry)[0]
    if isinstance(geometry, MultiPolygon):
        return sum(geodesic_area_perimeter(part)[0] for part in geometry.geoms)
    return 0.0


# ---------------------------------------------------------------------------- local projection
def _local_transformers(lat: float, lon: float) -> tuple[Transformer, Transformer]:
    """(to_local, to_wgs84) transformers for an azimuthal-equidistant CRS centred on a point."""
    local = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat:.9f} +lon_0={lon:.9f} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    to_local = Transformer.from_crs("EPSG:4326", local, always_xy=True)
    to_wgs84 = Transformer.from_crs(local, "EPSG:4326", always_xy=True)
    return to_local, to_wgs84


def _check_finite(value: Any, what: str, error: type[ConstructionError]) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise error("invalid_coordinate", f"{what} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise error("invalid_coordinate", f"{what} must be finite")
    return number


def _local_ring_to_lonlat(
    local_ring: Sequence[tuple[float, ...]], to_wgs84: Transformer
) -> list[tuple[float, float]]:
    xs = [p[0] for p in local_ring]
    ys = [p[1] for p in local_ring]
    lons, lats = to_wgs84.transform(xs, ys)
    return [
        (round(float(a), COORD_DIGITS), round(float(b), COORD_DIGITS))
        for a, b in zip(lons, lats, strict=True)
    ]


# ---------------------------------------------------------------------------- pin + area
def _local_shape(shape: str, size: float) -> Polygon:
    """Square of side ``size`` or circle polygon of vertex radius ``size``, centred on (0, 0)."""
    if shape == "square":
        half = size / 2.0
        return Polygon([(-half, -half), (half, -half), (half, half), (-half, half)])
    return Point(0.0, 0.0).buffer(size, quad_segs=CIRCLE_QUAD_SEGMENTS)


def _initial_size(shape: str, target_m2: float) -> float:
    if shape == "square":
        return math.sqrt(target_m2)
    n = 4 * CIRCLE_QUAD_SEGMENTS
    return math.sqrt(target_m2 / (0.5 * n * math.sin(2.0 * math.pi / n)))


def polygon_from_point(
    lat: float,
    lon: float,
    area_ha: float,
    shape: str = "square",
    limits: ValidationLimits | None = None,
) -> dict[str, Any]:
    """Polygon of ``area_ha`` hectares centred on a pin.

    Returns ``{"geometry", "area_hectares", "side_m" | "radius_m", "method"}``. The geodesic area
    of ``geometry`` is within 0.1 % of the request (the contract promises 0.5 %).
    Raises :class:`ConstructionError` subclasses for a bad pin or area and the usual
    :class:`GeometryError` codes from :func:`validate_polygon`.
    """
    limits = limits or ValidationLimits()
    lat = _check_finite(lat, "latitude", InvalidPointError)
    lon = _check_finite(lon, "longitude", InvalidPointError)
    area_ha = _check_finite(area_ha, "area", InvalidAreaError)
    if not -90.0 <= lat <= 90.0:
        raise InvalidPointError("coordinate_out_of_range", "latitude must be between -90 and 90")
    if not -180.0 <= lon <= 180.0:
        raise InvalidPointError("coordinate_out_of_range", "longitude must be between -180 and 180")
    if shape not in SHAPES:
        raise InvalidAreaError("invalid_shape", f"shape must be one of {', '.join(SHAPES)}")
    if area_ha <= 0.0:
        raise InvalidAreaError("invalid_area", "area must be greater than zero")
    if area_ha < limits.min_area_ha:
        raise InvalidAreaError(
            "area_too_small", f"area {area_ha} ha is below the minimum {limits.min_area_ha} ha"
        )
    if area_ha > limits.max_area_ha:
        raise InvalidAreaError(
            "area_too_large", f"area {area_ha} ha exceeds the maximum {limits.max_area_ha} ha"
        )

    target_m2 = area_ha * M2_PER_HA
    # A request sitting exactly on a plot limit must still land inside it after rounding, so aim a
    # hair inside the permitted range (the error against the request stays below 0.3 %).
    margin = 2.0 * AREA_TOLERANCE
    aim_m2 = min(
        max(target_m2, limits.min_area_ha * M2_PER_HA * (1.0 + margin)),
        limits.max_area_ha * M2_PER_HA * (1.0 - margin),
    )
    to_local, to_wgs84 = _local_transformers(lat, lon)
    size = _initial_size(shape, aim_m2)
    ring: list[tuple[float, float]] = []
    for _ in range(MAX_ITERATIONS):
        local = _local_shape(shape, size)
        if abs(lat) + (size / 111_000.0) >= 89.99:
            raise InvalidPointError("pole", "the area reaches a pole; choose a pin further away")
        ring = _local_ring_to_lonlat(list(local.exterior.coords), to_wgs84)
        if any(abs(v[0] - lon) > 180.0 for v in ring):
            raise InvalidPointError(
                "antimeridian", "the area crosses the antimeridian; move the pin away from ±180°"
            )
        actual_m2 = geodesic_area_perimeter(Polygon(ring))[0]
        if actual_m2 <= 0.0:
            raise InvalidAreaError("invalid_area", "could not build a polygon of that area")
        if abs(actual_m2 / aim_m2 - 1.0) <= AREA_TOLERANCE:
            break
        size *= math.sqrt(aim_m2 / actual_m2)

    geometry = {"type": "Polygon", "coordinates": [[list(v) for v in ring]]}
    polygon = validate_polygon(geometry, limits)
    area_m2 = geodesic_area_perimeter(polygon)[0]
    if abs(area_m2 / target_m2 - 1.0) > CONTRACT_AREA_TOLERANCE:  # pragma: no cover - safety net
        raise InvalidAreaError("area_mismatch", "could not match the requested area closely enough")
    result: dict[str, Any] = {
        "geometry": polygon_to_geojson(polygon),
        "area_hectares": round(area_m2 / M2_PER_HA, 4),
    }
    if shape == "square":
        result["side_m"] = round(size, 2)
        result["method"] = f"geodesic square centred on the pin (side {size:.1f} m)"
    else:
        result["radius_m"] = round(size, 2)
        result["method"] = (
            f"geodesic circle centred on the pin (radius {size:.1f} m, "
            f"{4 * CIRCLE_QUAD_SEGMENTS}-sided polygon)"
        )
    return result


# ---------------------------------------------------------------------------- tree line
def suggest_tree_count(length_m: float, spacing_m: float) -> int:
    """Trees along a line: ``floor(length / spacing) + 1`` (one at each end)."""
    if length_m < 0 or spacing_m <= 0:
        raise ValueError("length must be >= 0 and spacing > 0")
    return int(math.floor(length_m / spacing_m)) + 1


def _line_positions(coords: Sequence[Sequence[float]]) -> list[tuple[float, float]]:
    if not isinstance(coords, Sequence) or isinstance(coords, str | bytes):
        raise InvalidLineError("invalid_geometry", "line coordinates must be an array of positions")
    if len(coords) < 2:
        raise InvalidLineError("too_few_vertices", "a line needs at least 2 vertices")
    if len(coords) > MAX_LINE_VERTICES:
        raise InvalidLineError(
            "too_many_vertices",
            f"line has {len(coords)} vertices; the maximum is {MAX_LINE_VERTICES}",
        )
    points: list[tuple[float, float]] = []
    for index, position in enumerate(coords):
        if not isinstance(position, Sequence) or len(position) not in (2, 3):
            raise InvalidLineError(
                "invalid_coordinate", f"position {index} must be [lon, lat] or [lon, lat, z]"
            )
        lon = _check_finite(position[0], "longitude", InvalidLineError)
        lat = _check_finite(position[1], "latitude", InvalidLineError)
        if not -180.0 <= lon <= 180.0:
            raise InvalidLineError(
                "coordinate_out_of_range",
                f"position {index}: longitude must be between -180 and 180",
            )
        if not -90.0 <= lat <= 90.0:
            raise InvalidLineError(
                "coordinate_out_of_range", f"position {index}: latitude must be between -90 and 90"
            )
        if not points or points[-1] != (lon, lat):
            points.append((lon, lat))
    if len(points) < 2:
        raise InvalidLineError("zero_length", "all vertices of the line are identical")
    return points


def _fit_vertex_limit(polygon: Polygon, max_vertices: int, width_m: float) -> tuple[Polygon, float]:
    """Simplify ``polygon`` until its exterior has at most ``max_vertices`` vertices."""
    if len(polygon.exterior.coords) - 1 <= max_vertices:
        return polygon, 0.0
    tolerance = max(width_m / 100.0, 0.01)
    limit = width_m / 4.0
    while tolerance <= limit:
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        if isinstance(simplified, Polygon) and len(simplified.exterior.coords) - 1 <= max_vertices:
            return simplified, tolerance
        tolerance *= 1.6
    raise InvalidLineError(
        "too_many_vertices",
        f"the strip needs more than {max_vertices} vertices; draw the line with fewer points",
    )


def strip_from_line(
    coords: Sequence[Sequence[float]],
    width_m: float,
    limits: ValidationLimits | None = None,
) -> dict[str, Any]:
    """Buffer a ``[lon, lat]`` line by ``width_m / 2`` (flat caps) into a plot polygon.

    Returns ``{"geometry", "length_m", "area_hectares", "method"}``. Raises
    :class:`InvalidLineError` (fewer than 2 or more than 500 vertices, length above 50 km, bad
    width or coordinates) or the usual :class:`GeometryError` codes from :func:`validate_polygon`
    (for example ``area_too_small`` when the strip is below the 0.01 ha plot minimum).
    """
    limits = limits or ValidationLimits()
    width_m = _check_finite(width_m, "width", InvalidLineError)
    if not MIN_WIDTH_M <= width_m <= MAX_WIDTH_M:
        raise InvalidLineError(
            "invalid_width", f"width must be between {MIN_WIDTH_M:g} and {MAX_WIDTH_M:g} m"
        )
    points = _line_positions(coords)
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    length_m = float(_GEOD.line_length(lons, lats))
    if length_m > MAX_LINE_LENGTH_M:
        raise InvalidLineError(
            "line_too_long",
            f"line is {length_m / 1000:.1f} km long; "
            f"the maximum is {MAX_LINE_LENGTH_M / 1000:.0f} km",
        )
    if length_m <= 0.0:
        raise InvalidLineError("zero_length", "the line has no length")
    centre_lon = (min(lons) + max(lons)) / 2.0
    centre_lat = (min(lats) + max(lats)) / 2.0
    if max(lons) - min(lons) > 180.0:
        raise InvalidLineError("antimeridian", "the line crosses the antimeridian")
    to_local, to_wgs84 = _local_transformers(centre_lat, centre_lon)
    xs, ys = to_local.transform(lons, lats)
    line = LineString(list(zip(xs, ys, strict=True)))
    strip = line.buffer(width_m / 2.0, cap_style="flat", join_style="round", quad_segs=4)
    if not isinstance(strip, Polygon) or strip.is_empty:
        raise InvalidLineError("invalid_geometry", "the line could not be buffered into a polygon")
    strip, tolerance = _fit_vertex_limit(strip, limits.max_vertices, width_m)
    ring = _local_ring_to_lonlat(list(strip.exterior.coords), to_wgs84)
    holes = [_local_ring_to_lonlat(list(r.coords), to_wgs84) for r in strip.interiors]
    geometry = {
        "type": "Polygon",
        "coordinates": [[list(v) for v in ring], *[[list(v) for v in h] for h in holes]],
    }
    polygon = validate_polygon(geometry, limits)
    area_m2 = geodesic_area_perimeter(polygon)[0]
    method = "line buffered by width/2 in a local metric projection"
    if tolerance > 0.0:
        method += (
            f"; simplified to fit {limits.max_vertices} vertices (tolerance {tolerance:.2f} m)"
        )
    return {
        "geometry": polygon_to_geojson(polygon),
        "length_m": round(length_m, 1),
        "area_hectares": round(area_m2 / M2_PER_HA, 4),
        "method": method,
    }
