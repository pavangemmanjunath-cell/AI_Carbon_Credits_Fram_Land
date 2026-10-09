"""GeoJSON polygon validation for plots.

Rules (docs/architecture/api-contract.md, ``POST /plots``):

* geometry ``type`` must be ``"Polygon"`` with at least one linear ring;
* every position is ``[lon, lat]`` (optionally ``[lon, lat, z]``) with
  ``-180 ≤ lon ≤ 180`` and ``-90 ≤ lat ≤ 90``;
* the exterior ring has 4–``max_vertices + 1`` positions (a closed triangle is
  4 positions); an unclosed ring is closed automatically;
* the polygon is valid and simple (no self-intersection, no zero area);
* geodesic area is within ``[min_area_ha, max_area_ha]`` (defaults 0.01–10 000 ha).

The function returns a Shapely ``Polygon`` with the exterior ring closed and
the ``z`` coordinate dropped, ready for measurement and storage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.geometry import Polygon
from shapely.validation import explain_validity, make_valid

from geo_engine.errors import GeometryError
from geo_engine.geometry.measure import geodesic_area_perimeter

M2_PER_HA = 10_000.0


@dataclass(frozen=True)
class ValidationLimits:
    """Tunable validation limits (API reads them from settings/env)."""

    max_vertices: int = 500
    min_area_ha: float = 0.01
    max_area_ha: float = 10_000.0


def _as_number(value: Any, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GeometryError("invalid_coordinate", f"{what} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise GeometryError("invalid_coordinate", f"{what} must be finite")
    return number


def _parse_ring(ring: Any, index: int) -> list[tuple[float, float]]:
    if not isinstance(ring, list | tuple):
        raise GeometryError("invalid_geometry", f"ring {index} must be an array of positions")
    positions: list[tuple[float, float]] = []
    for pos_index, position in enumerate(ring):
        if not isinstance(position, list | tuple) or len(position) not in (2, 3):
            raise GeometryError(
                "invalid_coordinate",
                f"ring {index} position {pos_index} must be [lon, lat] or [lon, lat, z]",
            )
        lon = _as_number(position[0], "longitude")
        lat = _as_number(position[1], "latitude")
        if not -180.0 <= lon <= 180.0:
            raise GeometryError("coordinate_out_of_range", f"longitude {lon} outside [-180, 180]")
        if not -90.0 <= lat <= 90.0:
            raise GeometryError("coordinate_out_of_range", f"latitude {lat} outside [-90, 90]")
        positions.append((lon, lat))
    return positions


def validate_polygon(
    geometry: dict[str, Any] | None,
    limits: ValidationLimits | None = None,
) -> Polygon:
    """Validate a GeoJSON Polygon dict and return the equivalent Shapely polygon.

    Raises :class:`GeometryError` with a stable ``code`` on failure.
    """
    limits = limits or ValidationLimits()
    if not isinstance(geometry, dict):
        raise GeometryError("invalid_geometry", "geometry must be a GeoJSON object")
    if geometry.get("type") != "Polygon":
        raise GeometryError("invalid_geometry", "geometry.type must be 'Polygon'")
    rings = geometry.get("coordinates")
    if not isinstance(rings, list | tuple) or len(rings) == 0:
        raise GeometryError("invalid_geometry", "geometry.coordinates must contain a linear ring")

    parsed_rings = [_parse_ring(ring, i) for i, ring in enumerate(rings)]
    exterior = parsed_rings[0]
    if len(exterior) >= 2 and exterior[0] != exterior[-1]:
        exterior = [*exterior, exterior[0]]
    if len(exterior) < 4:
        raise GeometryError("too_few_vertices", "a polygon needs at least 3 distinct vertices")
    if len(exterior) > limits.max_vertices + 1:
        raise GeometryError(
            "too_many_vertices",
            f"polygon has {len(exterior) - 1} vertices; the maximum is {limits.max_vertices}",
        )
    holes = []
    for hole in parsed_rings[1:]:
        if len(hole) >= 2 and hole[0] != hole[-1]:
            hole = [*hole, hole[0]]
        if len(hole) < 4:
            raise GeometryError("too_few_vertices", "an interior ring needs at least 3 vertices")
        holes.append(hole)

    polygon = Polygon(exterior, holes)
    if not polygon.is_valid:
        reason = explain_validity(polygon)
        if make_valid(polygon).area == 0.0:
            raise GeometryError("zero_area", f"polygon has no area: {reason}")
        if "Self-intersection" in reason:
            raise GeometryError("self_intersection", f"polygon must be simple: {reason}")
        raise GeometryError("invalid_geometry", f"polygon is not valid: {reason}")
    if polygon.is_empty or polygon.area == 0.0:
        raise GeometryError("zero_area", "polygon has no area")
    if not polygon.is_simple:
        raise GeometryError("self_intersection", "polygon must be simple (no self-intersection)")

    area_m2, _ = geodesic_area_perimeter(polygon)
    area_ha = area_m2 / M2_PER_HA
    if area_ha < limits.min_area_ha:
        raise GeometryError(
            "area_too_small", f"area {area_ha:.4f} ha is below the minimum {limits.min_area_ha} ha"
        )
    if area_ha > limits.max_area_ha:
        raise GeometryError(
            "area_too_large", f"area {area_ha:.1f} ha exceeds the maximum {limits.max_area_ha} ha"
        )
    return polygon
