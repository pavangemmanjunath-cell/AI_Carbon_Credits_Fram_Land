# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Tests of the crown counter: point-in-polygon, confidence filter and field-name detection."""

from __future__ import annotations

import math
import random
from typing import Any

import pytest

from carboncreditbuy_qgis import crowns
from carboncreditbuy_qgis.crowns import (
    Crown,
    CrownCount,
    PreparedPolygon,
    count_crowns,
    detect_confidence_field,
    point_in_polygon,
    point_in_ring,
    to_float,
)

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
HOLE = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0), (4.0, 4.0)]
# A "U" shape: the notch (3..7, 4..10) is outside although it lies inside the bounding box.
U_SHAPE = [
    (0.0, 0.0),
    (10.0, 0.0),
    (10.0, 10.0),
    (7.0, 10.0),
    (7.0, 4.0),
    (3.0, 4.0),
    (3.0, 10.0),
    (0.0, 10.0),
    (0.0, 0.0),
]


# --------------------------------------------------------------------------- point in ring
@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ((5, 5), True),
        ((0.1, 0.1), True),
        ((9.99, 9.99), True),
        ((-0.1, 5), False),
        ((10.1, 5), False),
        ((5, -0.1), False),
        ((5, 10.1), False),
        ((100, 100), False),
    ],
)
def test_point_in_a_square(point: tuple[float, float], expected: bool) -> None:
    assert point_in_ring(*point, SQUARE) is expected


@pytest.mark.parametrize("point", [(0, 0), (10, 10), (0, 5), (10, 5), (5, 0), (5, 10), (10, 0)])
def test_points_on_the_boundary_count_as_inside(point: tuple[float, float]) -> None:
    assert point_in_ring(*point, SQUARE)


@pytest.mark.parametrize(
    ("point", "expected"),
    [((1, 5), True), ((5, 2), True), ((5, 8), False), ((5, 5), False), ((8.5, 8), True)],
)
def test_concave_shapes(point: tuple[float, float], expected: bool) -> None:
    assert point_in_ring(*point, U_SHAPE) is expected


def test_rings_work_open_or_closed() -> None:
    open_ring = SQUARE[:-1]
    for point in [(5, 5), (11, 5), (0, 0), (10, 5)]:
        assert point_in_ring(*point, open_ring) == point_in_ring(*point, SQUARE)


def test_an_empty_ring_contains_nothing() -> None:
    assert point_in_ring(1, 1, []) is False
    assert point_in_polygon(1, 1, []) is False


def test_the_ray_passing_exactly_through_a_vertex_is_handled() -> None:
    diamond = [(5.0, 0.0), (10.0, 5.0), (5.0, 10.0), (0.0, 5.0), (5.0, 0.0)]
    # y == 5 hits two vertices of the diamond; 2 and 8 are inside, -1 and 12 are outside.
    assert point_in_ring(2, 5, diamond)
    assert point_in_ring(8, 5, diamond)
    assert not point_in_ring(-1, 5, diamond)
    assert not point_in_ring(12, 5, diamond)


def test_holes_are_excluded() -> None:
    rings = [SQUARE, HOLE]
    assert point_in_polygon(2, 2, rings)
    assert not point_in_polygon(5, 5, rings)
    assert point_in_polygon(4, 5, rings)  # on the hole boundary: still inside the polygon
    assert not point_in_polygon(11, 5, rings)


def test_large_map_coordinates_keep_their_precision() -> None:
    """Web Mercator values in the millions must not lose the boundary decision."""
    x0, y0 = 8571600.791082066, 1345708.4084091093
    ring = [(x0, y0), (x0 + 100, y0), (x0 + 100, y0 + 100), (x0, y0 + 100), (x0, y0)]
    assert point_in_ring(x0 + 50, y0 + 50, ring)
    assert point_in_ring(x0 + 99.999, y0 + 0.001, ring)
    assert not point_in_ring(x0 + 100.001, y0 + 50, ring)
    assert not point_in_ring(x0 + 50, y0 - 0.001, ring)


def test_shapely_agrees_on_random_points() -> None:
    shapely_geometry = pytest.importorskip("shapely.geometry")
    shape = shapely_geometry.Polygon(SQUARE, [HOLE[:-1]])
    rng = random.Random(7)
    for _ in range(3000):
        x, y = rng.uniform(-2, 12), rng.uniform(-2, 12)
        assert point_in_polygon(x, y, [SQUARE, HOLE]) == shape.covers(shapely_geometry.Point(x, y))
    u_shape = shapely_geometry.Polygon(U_SHAPE)
    for _ in range(3000):
        x, y = rng.uniform(-2, 12), rng.uniform(-2, 12)
        assert point_in_ring(x, y, U_SHAPE) == u_shape.covers(shapely_geometry.Point(x, y))


def test_prepared_polygon_rejects_by_bounding_box_and_needs_a_real_ring() -> None:
    prepared = PreparedPolygon([SQUARE, HOLE])
    assert prepared.contains(2, 2)
    assert not prepared.contains(5, 5)
    assert not prepared.contains(50, 5)
    with pytest.raises(ValueError):
        PreparedPolygon([])
    with pytest.raises(ValueError):
        PreparedPolygon([[(0, 0), (1, 1)]])


# --------------------------------------------------------------------------- counting
def test_counting_without_a_filter_counts_every_crown_inside() -> None:
    points = [(1, 1), (5, 5), (9, 9), (11, 5), (-1, -1)]
    result = count_crowns(points, [[SQUARE]])
    assert result == CrownCount(
        examined=5,
        invalid=0,
        outside=2,
        inside=3,
        counted=3,
        below_threshold=0,
        missing_confidence=0,
        threshold=None,
    )


def test_a_confidence_threshold_keeps_values_at_or_above_it() -> None:
    items = [(1, 1, 0.9), (2, 2, 0.5), (3, 3, 0.49), (4, 4, 0.1), (20, 20, 0.99)]
    result = count_crowns(items, [[SQUARE]], min_confidence=0.5)
    assert result.counted == 2  # 0.9 and exactly 0.5
    assert result.below_threshold == 2
    assert result.outside == 1  # the confident crown outside the field does not count
    assert result.missing_confidence == 0
    assert result.threshold == 0.5
    assert result.excluded_by_confidence == 2


def test_crowns_without_a_confidence_are_excluded_and_reported() -> None:
    items = [(1, 1, None), (2, 2, float("nan")), (3, 3, "n/a"), (4, 4, 0.8), (5, 5, "0.7")]
    result = count_crowns(items, [[SQUARE]], min_confidence=0.5)
    assert result.counted == 2  # 0.8 and the numeric string "0.7"
    assert result.missing_confidence == 3


def test_without_a_threshold_the_confidence_column_is_ignored() -> None:
    items = [(1, 1, None), (2, 2, 0.0), (3, 3, "junk")]
    assert count_crowns(items, [[SQUARE]]).counted == 3


def test_crown_tuples_lists_and_named_tuples_are_all_accepted() -> None:
    items = [Crown(1, 1, 0.9), (2, 2), [3, 3, 0.1], (4, 4, 0.7)]
    result = count_crowns(items, [[SQUARE]], 0.5)
    assert result.counted == 2
    assert result.below_threshold == 1
    assert result.missing_confidence == 1  # the (2, 2) tuple has no confidence


@pytest.mark.parametrize(
    "item",
    [None, (1,), (1, 2, 3, 4), "xy", (None, 1), ("a", "b"), (float("nan"), 1), (1, float("inf"))],
)
def test_unusable_crowns_are_counted_as_invalid(item: Any) -> None:
    result = count_crowns([item, (5, 5)], [[SQUARE]])
    assert result.invalid == 1
    assert result.counted == 1
    assert result.examined == 2


def test_multi_part_fields_count_each_crown_once() -> None:
    second = [(20.0, 0.0), (30.0, 0.0), (30.0, 10.0), (20.0, 10.0), (20.0, 0.0)]
    points = [(5, 5), (25, 5), (15, 5), (100, 100)]
    result = count_crowns(points, [[SQUARE], [second]])
    assert (result.inside, result.outside) == (2, 2)


def test_a_field_with_a_hole_does_not_count_crowns_in_the_hole() -> None:
    result = count_crowns([(5, 5), (1, 1), (5.5, 5.5)], [[SQUARE, HOLE]])
    assert result.counted == 1


def test_a_generator_of_crowns_is_consumed_lazily_once() -> None:
    consumed: list[int] = []

    def stream() -> Any:
        for i in range(50):
            consumed.append(i)
            yield (i % 12, 5.0)

    result = count_crowns(stream(), [[SQUARE]])
    assert result.examined == 50 and len(consumed) == 50


def test_no_crowns_gives_zero_counts() -> None:
    result = count_crowns([], [[SQUARE]])
    assert result.counted == result.examined == 0


def test_a_field_is_required_and_the_threshold_must_be_a_number() -> None:
    with pytest.raises(ValueError):
        count_crowns([(1, 1)], [])
    with pytest.raises(ValueError):
        count_crowns([(1, 1)], [[SQUARE]], min_confidence=float("nan"))
    with pytest.raises(ValueError):
        count_crowns([(1, 1)], [[SQUARE]], min_confidence="high")  # type: ignore[arg-type]


def test_a_numeric_string_threshold_is_accepted() -> None:
    result = count_crowns([(1, 1, 0.6)], [[SQUARE]], min_confidence="0.5")  # type: ignore[arg-type]
    assert result.counted == 1 and result.threshold == 0.5


def test_a_dense_orchard_is_counted_correctly() -> None:
    """A 20 x 20 grid of crown centres inside a 10 x 10 field, plus a ring of strays outside."""
    inside = [(0.25 + 0.5 * i, 0.25 + 0.5 * j) for i in range(20) for j in range(20)]
    outside = [(-1 + 0.1 * k, 12) for k in range(30)]
    result = count_crowns(inside + outside, [[SQUARE]])
    assert result.counted == 400
    assert result.outside == 30


# --------------------------------------------------------------------------- field names
@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["id", "score", "area"], "score"),
        (["Score"], "Score"),
        (["id", "CONFIDENCE"], "CONFIDENCE"),
        (["prob"], "prob"),
        (["probability", "id"], "probability"),
        (["id", "conf"], "conf"),
        (["det_score", "id"], "det_score"),
        (["mask_confidence_pct"], "mask_confidence_pct"),
        (["class_probab"], "class_probab"),
        (["fid", "area", "perimeter"], None),
        ([], None),
    ],
)
def test_confidence_field_detection(names: list[str], expected: str | None) -> None:
    assert detect_confidence_field(names) == expected


def test_preferred_names_beat_aliases_and_hints() -> None:
    assert detect_confidence_field(["det_score", "conf", "probability", "score"]) == "score"
    assert detect_confidence_field(["det_score", "conf", "probability"]) == "probability"
    assert detect_confidence_field(["det_score", "conf"]) == "conf"
    assert detect_confidence_field(iter(["a", "Confidence"])) == "Confidence"


def test_the_default_threshold_is_one_half() -> None:
    assert crowns.DEFAULT_CONFIDENCE_THRESHOLD == 0.5
    assert crowns.CONFIDENCE_FIELD_NAMES == ("score", "confidence", "prob", "probability")


# --------------------------------------------------------------------------- to_float
class _Null:
    """Stands in for QGIS's NULL: float() raises TypeError."""

    def __float__(self) -> float:
        raise TypeError("NULL")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, 1.0), (0.25, 0.25), ("0.75", 0.75), (" 3 ", 3.0), (-2, -2.0)],
)
def test_to_float_accepts_numbers(value: Any, expected: float) -> None:
    assert to_float(value) == expected


@pytest.mark.parametrize(
    "value", [None, True, False, "", "abc", float("nan"), float("inf"), _Null(), [], {}]
)
def test_to_float_rejects_everything_else(value: Any) -> None:
    assert to_float(value) is None


def test_to_float_never_returns_non_finite_numbers() -> None:
    for value in (math.inf, -math.inf, math.nan, "inf", "nan"):
        assert to_float(value) is None
