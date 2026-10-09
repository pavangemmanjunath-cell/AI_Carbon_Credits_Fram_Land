# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Count detected tree crowns inside a field polygon (pure Python, no QGIS imports).

The QGIS side reads the segmentation layer (for example the output of an AI segmentation
plugin), takes one centroid per feature and an optional confidence value, and hands plain
numbers to :func:`count_crowns`. Everything here works on any planar coordinates as long as
the field polygon and the crown centroids share the same CRS.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, NamedTuple

Point = tuple[float, float]
Ring = Sequence[Point]

#: Field names recognised as a detection confidence, in order of preference.
CONFIDENCE_FIELD_NAMES = ("score", "confidence", "prob", "probability")
#: Extra spellings accepted after the preferred names (exact, case-insensitive).
CONFIDENCE_FIELD_ALIASES = ("conf", "scores", "confidences", "probs", "probabilities")
#: Substrings that suggest a confidence field when no exact name matches.
CONFIDENCE_FIELD_HINTS = ("confidence", "score", "probab")

DEFAULT_CONFIDENCE_THRESHOLD = 0.5


class Crown(NamedTuple):
    """One detected crown reduced to its centroid and an optional confidence value."""

    x: float
    y: float
    confidence: float | None = None


@dataclass(frozen=True)
class CrownCount:
    """Result of :func:`count_crowns`. ``counted`` is the tree count to send to the API."""

    examined: int
    invalid: int
    outside: int
    inside: int
    counted: int
    below_threshold: int
    missing_confidence: int
    threshold: float | None

    @property
    def excluded_by_confidence(self) -> int:
        return self.below_threshold + self.missing_confidence


def detect_confidence_field(field_names: Iterable[str]) -> str | None:
    """Pick the most likely confidence field, or ``None``.

    Exact (case-insensitive) matches win, in the order ``score, confidence, prob,
    probability``, then common aliases (``conf``...), then any name that contains
    ``confidence``, ``score`` or ``probab`` (for example ``det_score``). The caller should only
    pass numeric field names and must let the user override the choice.
    """
    names = [str(n) for n in field_names]
    lowered = {n.lower(): n for n in names}
    for wanted in CONFIDENCE_FIELD_NAMES + CONFIDENCE_FIELD_ALIASES:
        if wanted in lowered:
            return lowered[wanted]
    for hint in CONFIDENCE_FIELD_HINTS:
        for name in names:
            if hint in name.lower():
                return name
    return None


def to_float(value: Any) -> float | None:
    """Coerce an attribute value to a finite float; ``None``/NULL/NaN/text become ``None``."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _locate(px: float, py: float, ring: Ring) -> int:
    """Locate a point against one ring: ``1`` inside, ``0`` on the boundary, ``-1`` outside.

    Even-odd ray casting (a horizontal ray towards +x) in a single pass. Exact hits on a vertex,
    on a horizontal edge or on the crossing point of a slanted edge are reported as boundary.
    Works for open and closed rings.
    """
    inside = False
    xj, yj = ring[-1]
    for xi, yi in ring:
        if yi == py and xi == px:
            return 0
        if (yi > py) != (yj > py):
            x_cross = (xj - xi) * (py - yi) / (yj - yi) + xi
            if px == x_cross:
                return 0
            if px < x_cross:
                inside = not inside
        elif yi == py and yj == py and (xi <= px <= xj or xj <= px <= xi):
            return 0
        xj, yj = xi, yi
    return 1 if inside else -1


def point_in_ring(px: float, py: float, ring: Ring) -> bool:
    """True when the point is inside the ring or exactly on its boundary."""
    return bool(ring) and _locate(px, py, ring) >= 0


def point_in_polygon(px: float, py: float, rings: Sequence[Ring]) -> bool:
    """Point-in-polygon with holes: ``rings[0]`` is the outer ring, the rest are holes.

    Points on the outer boundary or on a hole boundary count as inside the polygon.
    """
    if not rings:
        return False
    where = _locate(px, py, rings[0])
    if where <= 0:
        return where == 0
    for hole in rings[1:]:
        where = _locate(px, py, hole)
        if where == 0:
            return True
        if where == 1:
            return False
    return True


class PreparedPolygon:
    """A polygon with a cached bounding box so most outside points are rejected cheaply."""

    __slots__ = ("max_x", "max_y", "min_x", "min_y", "rings")

    def __init__(self, rings: Sequence[Ring]) -> None:
        self.rings = [list(ring) for ring in rings if len(ring) >= 3]
        if not self.rings:
            raise ValueError("A polygon needs at least one ring with three or more positions.")
        xs = [p[0] for p in self.rings[0]]
        ys = [p[1] for p in self.rings[0]]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)

    def contains(self, px: float, py: float) -> bool:
        if px < self.min_x or px > self.max_x or py < self.min_y or py > self.max_y:
            return False
        return point_in_polygon(px, py, self.rings)


def _unpack(item: Any) -> tuple[Any, Any, Any]:
    if isinstance(item, Crown):
        return item.x, item.y, item.confidence
    if isinstance(item, (tuple, list)) and len(item) in (2, 3):
        return item[0], item[1], item[2] if len(item) == 3 else None
    return None, None, None


def count_crowns(
    crowns: Iterable[Any],
    polygons: Iterable[Sequence[Ring]],
    min_confidence: float | None = None,
) -> CrownCount:
    """Count crowns whose centroid lies inside the field.

    ``crowns`` yields :class:`Crown` objects or ``(x, y)`` / ``(x, y, confidence)`` tuples.
    ``polygons`` is an iterable of polygons, each a list of rings (outer ring first, then holes);
    pass one polygon for a plain field or several for a multi-part field.

    With ``min_confidence`` set, a crown counts only when its confidence is a number that is
    greater than or equal to the threshold. Crowns without a usable confidence are *excluded*
    and reported in ``missing_confidence`` rather than silently counted.
    """
    prepared = [PreparedPolygon(p) for p in polygons]
    if not prepared:
        raise ValueError("At least one field polygon is required.")
    threshold: float | None = None
    if min_confidence is not None:
        threshold = to_float(min_confidence)
        if threshold is None:
            raise ValueError("The confidence threshold must be a finite number.")

    examined = invalid = outside = inside = counted = below = missing = 0
    for item in crowns:
        examined += 1
        raw_x, raw_y, raw_conf = _unpack(item)
        x, y = to_float(raw_x), to_float(raw_y)
        if x is None or y is None:
            invalid += 1
            continue
        if not any(poly.contains(x, y) for poly in prepared):
            outside += 1
            continue
        inside += 1
        if threshold is None:
            counted += 1
            continue
        confidence = to_float(raw_conf)
        if confidence is None:
            missing += 1
        elif confidence >= threshold:
            counted += 1
        else:
            below += 1
    return CrownCount(
        examined=examined,
        invalid=invalid,
        outside=outside,
        inside=inside,
        counted=counted,
        below_threshold=below,
        missing_confidence=missing,
        threshold=threshold,
    )
