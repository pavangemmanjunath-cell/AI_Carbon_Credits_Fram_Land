# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""GeoJSON polygon validation for ``POST /api/v1/plots`` (pure Python, no QGIS imports).

The API contract (docs/architecture/api-contract.md) accepts a GeoJSON ``Polygon`` in
EPSG:4326 with 4-500 vertices and longitude/latitude inside [-180, 180] / [-90, 90]. This
module applies the same checks on the client so users get a precise message before any data
leaves their machine. The server remains the authority (self-intersection, area limits).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

#: Maximum number of vertices of one ring (the closing position is not counted).
MAX_VERTICES = 500
#: Coordinates are rounded to 7 decimal places (about 1 cm); removes CRS-transform noise.
COORD_DECIMALS = 7


class GeometryError(ValueError):
    """The geometry cannot be sent to the API. ``code`` is stable; the message is for users."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _coordinate(value: Any, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GeometryError("invalid_coordinate", f"The {what} must be a number, got {value!r}.")
    number = float(value)
    if not math.isfinite(number):
        raise GeometryError("invalid_coordinate", f"The {what} must be a finite number.")
    return number


def _position(position: Any, label: str, index: int) -> list[float]:
    if not isinstance(position, (list, tuple)) or len(position) not in (2, 3):
        raise GeometryError(
            "invalid_coordinate",
            f"{label}: position {index} must be [longitude, latitude] (an optional height is "
            "ignored).",
        )
    lon = _coordinate(position[0], "longitude")
    lat = _coordinate(position[1], "latitude")
    if not -180.0 <= lon <= 180.0:
        raise GeometryError(
            "coordinate_out_of_range",
            f"{label}: longitude {lon} is outside [-180, 180]. Is the layer CRS set correctly?",
        )
    if not -90.0 <= lat <= 90.0:
        raise GeometryError(
            "coordinate_out_of_range",
            f"{label}: latitude {lat} is outside [-90, 90]. Is the layer CRS set correctly?",
        )
    # ``+ 0.0`` turns -0.0 into 0.0 so equal positions always serialise identically.
    return [round(lon, COORD_DECIMALS) + 0.0, round(lat, COORD_DECIMALS) + 0.0]


def validate_ring(ring: Any, label: str = "ring") -> list[list[float]]:
    """Validate one linear ring and return it as ``[[lon, lat], ...]``.

    Rules: a list of positions, each ``[lon, lat]`` (a third value is dropped), within range,
    at least 4 positions, closed (first == last), at most ``MAX_VERTICES`` vertices and at least
    three distinct vertices.
    """
    if not isinstance(ring, (list, tuple)):
        raise GeometryError("invalid_geometry", f"{label} must be a list of positions.")
    positions = [_position(p, label, i) for i, p in enumerate(ring)]
    if len(positions) < 4:
        raise GeometryError(
            "too_few_vertices",
            f"{label} has {len(positions)} positions; a polygon ring needs at least 4 "
            "(three distinct vertices plus the closing position).",
        )
    if positions[0] != positions[-1]:
        raise GeometryError(
            "ring_not_closed", f"{label} is not closed: the first and last position differ."
        )
    vertices = len(positions) - 1
    if vertices > MAX_VERTICES:
        raise GeometryError(
            "too_many_vertices",
            f"{label} has {vertices} vertices; the API accepts at most {MAX_VERTICES}. "
            "Simplify the polygon first (Vector > Geometry Tools > Simplify) and check that the "
            "shape still matches the field.",
        )
    if len({tuple(p) for p in positions[:-1]}) < 3:
        raise GeometryError(
            "degenerate_ring", f"{label} has fewer than three distinct vertices (no area)."
        )
    return positions


def normalize_polygon(geometry: Any) -> dict[str, Any]:
    """Return a validated GeoJSON ``Polygon`` (a new dict) from a Polygon or 1-part MultiPolygon.

    Raises :class:`GeometryError` for anything else, including multi-part geometries, empty
    geometries, other geometry types and invalid rings.
    """
    if not isinstance(geometry, Mapping):
        raise GeometryError("invalid_geometry", "The geometry must be a GeoJSON object.")
    gtype = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if gtype == "MultiPolygon":
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) == 0:
            raise GeometryError("empty_geometry", "The MultiPolygon has no parts.")
        if len(coordinates) > 1:
            raise GeometryError(
                "multipart",
                f"The selected feature has {len(coordinates)} separate parts, but the API "
                "accepts one polygon per plot. Split it (Vector > Geometry Tools > Multipart to "
                "Singleparts) and select the part you want to send.",
            )
        coordinates = coordinates[0]
    elif gtype != "Polygon":
        shown = gtype if isinstance(gtype, str) else type(gtype).__name__
        raise GeometryError(
            "unsupported_type",
            f"Geometry type {shown!r} is not supported; select a Polygon (or a MultiPolygon "
            "with a single part).",
        )
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) == 0:
        raise GeometryError("empty_geometry", "The polygon has no rings.")
    rings = [
        validate_ring(ring, "The outer ring" if i == 0 else f"Interior ring {i}")
        for i, ring in enumerate(coordinates)
    ]
    return {"type": "Polygon", "coordinates": rings}


def vertex_count(polygon: Mapping[str, Any]) -> int:
    """Number of vertices of the outer ring of a normalised polygon (closing position excluded)."""
    rings = polygon.get("coordinates") or []
    return max(len(rings[0]) - 1, 0) if rings else 0


def polygon_rings(polygon: Mapping[str, Any]) -> list[list[tuple[float, float]]]:
    """Rings of a normalised polygon as ``(x, y)`` tuples, ready for ``crowns.count_crowns``."""
    return [[(p[0], p[1]) for p in ring] for ring in polygon.get("coordinates") or []]


def feature_collection(
    polygon: Mapping[str, Any], properties: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Wrap one polygon in a GeoJSON ``FeatureCollection`` (RFC 7946: always WGS 84)."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": dict(properties or {}),
                "geometry": dict(polygon),
            }
        ],
    }


def fingerprint(polygon: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical coordinates of a normalised polygon.

    The QGIS project stores this digest (never the coordinates) so the plugin can tell whether
    the selected field is the one that was already sent as the current plot.
    """
    canonical = json.dumps(polygon.get("coordinates"), separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()
