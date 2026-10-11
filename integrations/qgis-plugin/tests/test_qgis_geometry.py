# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Tests of the GeoJSON polygon checks that run before anything is sent to the API."""

from __future__ import annotations

import copy
import json
import math
from typing import Any

import pytest

from carboncreditbuy_qgis import geometry
from carboncreditbuy_qgis.geometry import GeometryError, normalize_polygon

SQUARE_RING = [[77.5, 13.2], [77.6, 13.2], [77.6, 13.3], [77.5, 13.3], [77.5, 13.2]]
HOLE_RING = [[77.52, 13.22], [77.54, 13.22], [77.54, 13.24], [77.52, 13.22]]


def polygon(*rings: list[list[float]]) -> dict[str, Any]:
    return {"type": "Polygon", "coordinates": [list(r) for r in rings]}


def circle_ring(vertices: int) -> list[list[float]]:
    """A closed ring with ``vertices`` distinct vertices."""
    points = [
        [
            round(77.5 + 0.1 * math.cos(2 * math.pi * i / vertices), 6),
            round(13.2 + 0.1 * math.sin(2 * math.pi * i / vertices), 6),
        ]
        for i in range(vertices)
    ]
    return [*points, points[0]]


def error_code(geom: Any) -> str:
    with pytest.raises(GeometryError) as caught:
        normalize_polygon(geom)
    return caught.value.code


# --------------------------------------------------------------------------- accepted input
def test_a_plain_polygon_is_accepted_unchanged() -> None:
    assert normalize_polygon(polygon(SQUARE_RING)) == polygon(SQUARE_RING)


def test_the_result_is_a_new_object() -> None:
    original = polygon(SQUARE_RING)
    result = normalize_polygon(original)
    result["coordinates"][0][0][0] = 0.0
    assert original == polygon(SQUARE_RING)


def test_a_single_part_multipolygon_becomes_a_polygon() -> None:
    multi = {"type": "MultiPolygon", "coordinates": [[SQUARE_RING]]}
    assert normalize_polygon(multi) == polygon(SQUARE_RING)


def test_holes_are_kept_and_validated() -> None:
    result = normalize_polygon(polygon(SQUARE_RING, HOLE_RING))
    assert len(result["coordinates"]) == 2


def test_heights_are_dropped_and_coordinates_are_rounded() -> None:
    ring = [[77.123456789, 13.1, 250.0], [77.2, 13.1, 1], [77.2, 13.2], [77.123456789, 13.1]]
    result = normalize_polygon(polygon(ring))
    assert result["coordinates"][0][0] == [77.1234568, 13.1]
    assert all(len(position) == 2 for position in result["coordinates"][0])


def test_negative_zero_is_normalised() -> None:
    ring = [[-0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, -0.0]]
    text = json.dumps(normalize_polygon(polygon(ring)))
    assert "-0.0" not in text


def test_tuples_work_like_lists() -> None:
    ring = tuple(tuple(p) for p in SQUARE_RING)
    assert normalize_polygon({"type": "Polygon", "coordinates": (ring,)}) == polygon(SQUARE_RING)


# --------------------------------------------------------------------------- vertex limits
def test_the_vertex_limit_is_inclusive() -> None:
    assert geometry.MAX_VERTICES == 500
    result = normalize_polygon(polygon(circle_ring(500)))
    assert geometry.vertex_count(result) == 500


def test_one_vertex_too_many_is_refused_with_advice() -> None:
    with pytest.raises(GeometryError) as caught:
        normalize_polygon(polygon(circle_ring(501)))
    assert caught.value.code == "too_many_vertices"
    assert "Simplify" in str(caught.value) and "500" in str(caught.value)


def test_a_ring_needs_four_positions() -> None:
    assert error_code(polygon([[0, 0], [1, 0], [0, 0]])) == "too_few_vertices"
    assert error_code(polygon([])) == "too_few_vertices"


def test_the_ring_must_be_closed() -> None:
    open_ring = [[77.5, 13.2], [77.6, 13.2], [77.6, 13.3], [77.5, 13.3]]
    assert error_code(polygon(open_ring)) == "ring_not_closed"


def test_a_ring_with_fewer_than_three_distinct_vertices_is_degenerate() -> None:
    assert error_code(polygon([[1, 1], [2, 2], [1, 1], [1, 1]])) == "degenerate_ring"


# --------------------------------------------------------------------------- coordinates
@pytest.mark.parametrize(
    ("lon", "lat"), [(181, 0), (-180.5, 0), (0, 90.1), (0, -91), (1e9, 0), (6378137.0, 1345708.4)]
)
def test_out_of_range_coordinates_suggest_checking_the_crs(lon: float, lat: float) -> None:
    ring = [[lon, lat], [0, 0], [1, 0], [lon, lat]]
    with pytest.raises(GeometryError) as caught:
        normalize_polygon(polygon(ring))
    assert caught.value.code == "coordinate_out_of_range"
    assert "CRS" in str(caught.value)


def test_the_limits_themselves_are_valid() -> None:
    ring = [[-180, -90], [180, -90], [180, 90], [-180, -90]]
    normalize_polygon(polygon(ring))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), "77.5", None, True])
def test_non_numeric_coordinates_are_refused(bad: Any) -> None:
    ring = [[bad, 13.2], [77.6, 13.2], [77.6, 13.3], [bad, 13.2]]
    assert error_code(polygon(ring)) == "invalid_coordinate"


@pytest.mark.parametrize("position", [[1], [1, 2, 3, 4], "ab", 5, None, {}])
def test_malformed_positions_are_refused(position: Any) -> None:
    ring = [position, [1, 1], [2, 2], position]
    assert error_code(polygon(ring)) == "invalid_coordinate"


# --------------------------------------------------------------------------- unsupported shapes
def test_a_multi_part_multipolygon_is_refused_with_advice() -> None:
    multi = {"type": "MultiPolygon", "coordinates": [[SQUARE_RING], [SQUARE_RING]]}
    with pytest.raises(GeometryError) as caught:
        normalize_polygon(multi)
    assert caught.value.code == "multipart"
    assert "2 separate parts" in str(caught.value)
    assert "Multipart to Singleparts" in str(caught.value)


@pytest.mark.parametrize(
    "geom",
    [
        {"type": "Point", "coordinates": [1, 2]},
        {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
        {"type": "GeometryCollection", "geometries": []},
        {"type": 5, "coordinates": []},
        {"coordinates": [SQUARE_RING]},
    ],
)
def test_other_geometry_types_are_refused(geom: Any) -> None:
    assert error_code(geom) == "unsupported_type"


@pytest.mark.parametrize("geom", [None, [], "Polygon", 5])
def test_non_objects_are_refused(geom: Any) -> None:
    assert error_code(geom) == "invalid_geometry"


def test_empty_geometries_are_refused() -> None:
    assert error_code({"type": "Polygon", "coordinates": []}) == "empty_geometry"
    assert error_code({"type": "Polygon"}) == "empty_geometry"
    assert error_code({"type": "MultiPolygon", "coordinates": []}) == "empty_geometry"


def test_a_ring_that_is_not_a_list_is_refused() -> None:
    assert error_code({"type": "Polygon", "coordinates": ["abc"]}) == "invalid_geometry"


def test_the_label_names_the_faulty_ring() -> None:
    bad_hole = [[77.52, 13.22], [77.54, 13.22], [77.54, 13.24]]
    with pytest.raises(GeometryError) as caught:
        normalize_polygon(polygon(SQUARE_RING, bad_hole))
    assert "Interior ring 1" in str(caught.value)
    with pytest.raises(GeometryError) as caught:
        normalize_polygon(polygon(bad_hole))
    assert "The outer ring" in str(caught.value)


# --------------------------------------------------------------------------- helpers
def test_vertex_count_excludes_the_closing_position() -> None:
    assert geometry.vertex_count(polygon(SQUARE_RING)) == 4
    assert geometry.vertex_count({"type": "Polygon", "coordinates": []}) == 0


def test_polygon_rings_are_tuples_for_the_crown_counter() -> None:
    rings = geometry.polygon_rings(polygon(SQUARE_RING, HOLE_RING))
    assert rings[0][0] == (77.5, 13.2)
    assert len(rings) == 2


def test_feature_collection_wraps_one_polygon() -> None:
    poly = polygon(SQUARE_RING)
    collection = geometry.feature_collection(poly, {"name": "x"})
    assert collection["type"] == "FeatureCollection"
    (feature,) = collection["features"]
    assert feature["type"] == "Feature"
    assert feature["geometry"] == poly
    assert feature["properties"] == {"name": "x"}
    assert geometry.feature_collection(poly)["features"][0]["properties"] == {}
    json.dumps(collection)  # serialisable


def test_fingerprint_is_stable_and_sensitive() -> None:
    first = geometry.fingerprint(polygon(SQUARE_RING))
    assert first == geometry.fingerprint(copy.deepcopy(polygon(SQUARE_RING)))
    assert len(first) == 64 and set(first) <= set("0123456789abcdef")
    moved = [[x + 0.0000001, y] for x, y in SQUARE_RING]
    assert geometry.fingerprint(polygon(moved)) != first
    assert geometry.fingerprint(polygon(SQUARE_RING, HOLE_RING)) != first


def test_fingerprint_ignores_everything_but_the_coordinates() -> None:
    plain = polygon(SQUARE_RING)
    decorated = {**plain, "bbox": [0, 0, 1, 1], "extra": "ignored"}
    assert geometry.fingerprint(plain) == geometry.fingerprint(decorated)
