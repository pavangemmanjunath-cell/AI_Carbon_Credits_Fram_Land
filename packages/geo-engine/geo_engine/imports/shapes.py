"""Shared feature collector: validates positions, enforces the contract limits, builds shapely."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import Any

from shapely.geometry import Point, Polygon

from geo_engine.imports.errors import ImportDataError
from geo_engine.imports.types import MAX_FEATURES, MAX_TOTAL_VERTICES, RawFeature

MAX_PROPERTIES = 50
MAX_NAME_CHARS = 200
_SKIP_TEXT = {
    "line": "line feature(s) (lines are not imported; use the tree-line tool)",
    "no_geometry": "feature(s) without geometry",
    "degenerate": "polygon(s) with fewer than three distinct corners",
    "unsupported": "feature(s) with an unsupported geometry type",
}


def clean_properties(properties: Any) -> dict[str, Any]:
    """Keep scalar values only (strings are truncated), at most :data:`MAX_PROPERTIES`."""
    if not isinstance(properties, dict):
        return {}
    kept: dict[str, Any] = {}
    for key, value in properties.items():
        if len(kept) >= MAX_PROPERTIES:
            break
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, int | float):
            if math.isfinite(float(value)):
                kept[str(key)[:100]] = value
        elif isinstance(value, str):
            kept[str(key)[:100]] = value[:MAX_NAME_CHARS]
    return kept


def feature_name(properties: dict[str, Any]) -> str | None:
    for key, value in properties.items():
        if key.lower() == "name" and isinstance(value, str) and value.strip():
            return value.strip()[:MAX_NAME_CHARS]
    return None


def check_position(position: Any) -> tuple[float, float]:
    """``[lon, lat(, z)]`` -> ``(lon, lat)``; raises on non-numbers and out-of-range values."""
    if not isinstance(position, Sequence) or isinstance(position, str | bytes) or len(position) < 2:
        raise ImportDataError("invalid_content", "a position must be [longitude, latitude]")
    lon, lat = position[0], position[1]
    if (
        isinstance(lon, bool)
        or isinstance(lat, bool)
        or not isinstance(lon, int | float)
        or not isinstance(lat, int | float)
    ):
        raise ImportDataError("invalid_content", "positions must contain numbers")
    lon, lat = float(lon), float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ImportDataError("invalid_content", "positions must be finite numbers")
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise ImportDataError(
            "coordinate_out_of_range",
            "coordinates are outside the WGS84 range (longitude ±180, latitude ±90): reproject "
            "the file to EPSG:4326 and use longitude, latitude order",
        )
    return lon, lat


class Collector:
    """Accumulates polygons and points while a parser walks a file."""

    def __init__(self) -> None:
        self.features: list[RawFeature] = []
        self.skipped: Counter[str] = Counter()
        self.vertices = 0

    def _room(self) -> None:
        if len(self.features) >= MAX_FEATURES:
            raise ImportDataError(
                "too_many_features",
                f"the file holds more than {MAX_FEATURES} features; split it or thin it out first",
            )

    def add_point(self, position: Any, properties: dict[str, Any], name: str | None) -> None:
        self._room()
        lon, lat = check_position(position)
        self.vertices += 1
        self.features.append(RawFeature(Point(lon, lat), properties, name))

    def add_polygon(
        self, rings: Sequence[Sequence[Any]], properties: dict[str, Any], name: str | None
    ) -> None:
        self._room()
        if not rings:
            self.skipped["degenerate"] += 1
            return
        parsed: list[list[tuple[float, float]]] = []
        for ring in rings:
            if not isinstance(ring, Sequence) or isinstance(ring, str | bytes):
                raise ImportDataError("invalid_content", "a ring must be an array of positions")
            self.vertices += len(ring)
            if self.vertices > MAX_TOTAL_VERTICES:
                raise ImportDataError(
                    "too_many_vertices",
                    f"the file holds more than {MAX_TOTAL_VERTICES} vertices; simplify it first",
                )
            positions = [check_position(p) for p in ring]
            if len(positions) >= 2 and positions[0] != positions[-1]:
                positions.append(positions[0])
            if len(set(positions)) < 3:
                if not parsed:
                    self.skipped["degenerate"] += 1
                    return
                continue  # a degenerate hole is dropped
            parsed.append(positions)
        self.features.append(RawFeature(Polygon(parsed[0], parsed[1:]), properties, name))

    def skip(self, reason: str, count: int = 1) -> None:
        self.skipped[reason] += count

    def warnings(self) -> list[str]:
        return [
            f"Skipped {count} {_SKIP_TEXT.get(reason, reason)}."
            for reason, count in self.skipped.items()
            if count
        ]
