"""Pin + area polygons and tree-line strips (geo_engine.construct)."""

from __future__ import annotations

import math

import pytest
from pyproj import Geod
from shapely.geometry import Point, shape

from geo_engine.construct import (
    ConstructionError,
    InvalidAreaError,
    InvalidLineError,
    InvalidPointError,
    geodesic_area_m2,
    polygon_from_point,
    strip_from_line,
    suggest_tree_count,
)
from geo_engine.errors import GeometryError
from geo_engine.geometry import ValidationLimits, validate_polygon

GEOD = Geod(ellps="WGS84")
ACRE_IN_HA = 0.40468564224  # international acre: 4046.8564224 m2


def _area_ha(result: dict) -> float:
    return geodesic_area_m2(shape(result["geometry"])) / 10_000.0


# ---------------------------------------------------------------------------- pin + area
@pytest.mark.parametrize("lat", [0.0, 13.2923, 45.0, -33.9, 60.0, 78.0])
@pytest.mark.parametrize("area_ha", [0.05, 1.0, 5 * ACRE_IN_HA, 25.0, 500.0])
@pytest.mark.parametrize("shape_name", ["square", "circle"])
def test_pin_area_matches_request_within_half_a_percent(lat, area_ha, shape_name):
    result = polygon_from_point(lat, 77.5384, area_ha, shape_name)
    assert _area_ha(result) == pytest.approx(area_ha, rel=0.005)
    # in practice the construction is far tighter than the contract's 0.5 %
    assert _area_ha(result) == pytest.approx(area_ha, rel=0.002)
    assert result["area_hectares"] == pytest.approx(area_ha, rel=0.002)


def test_five_acres_square_is_about_142_m_a_side():
    result = polygon_from_point(13.2923, 77.5384, 5 * ACRE_IN_HA, "square")
    assert result["side_m"] == pytest.approx(142.2, abs=0.3)
    assert result["method"].startswith("geodesic square centred on the pin")
    assert "142.2" in result["method"]


def test_square_sides_are_equal_and_polygon_is_centred_on_the_pin():
    lat, lon = -33.9, 18.42
    polygon = shape(polygon_from_point(lat, lon, 2.0, "square")["geometry"])
    ring = list(polygon.exterior.coords)
    assert len(ring) == 5 and ring[0] == ring[-1]
    sides = [GEOD.inv(a[0], a[1], b[0], b[1])[2] for a, b in zip(ring, ring[1:], strict=False)]
    assert max(sides) - min(sides) < 0.05  # metres
    assert polygon.centroid.distance(Point(lon, lat)) < 2e-6  # ~0.2 m
    assert polygon.is_valid


def test_circle_is_a_64_sided_polygon_around_the_pin():
    result = polygon_from_point(13.2923, 77.5384, 3.0, "circle")
    polygon = shape(result["geometry"])
    assert len(polygon.exterior.coords) == 65
    assert result["radius_m"] > 0
    assert "circle" in result["method"]
    assert polygon.centroid.distance(Point(77.5384, 13.2923)) < 2e-6


def test_result_is_a_valid_plot_polygon():
    result = polygon_from_point(13.2923, 77.5384, 1.5)
    polygon = validate_polygon(result["geometry"])
    assert polygon.is_valid


def test_construction_is_deterministic():
    first = polygon_from_point(13.2923, 77.5384, 2.2)
    second = polygon_from_point(13.2923, 77.5384, 2.2)
    assert first == second


def test_limits_of_the_plot_rules_are_reachable():
    limits = ValidationLimits(max_area_ha=10_000.0)
    smallest = polygon_from_point(13.0, 77.0, 0.01, "square", limits)
    largest = polygon_from_point(13.0, 77.0, 10_000.0, "square", limits)
    assert _area_ha(smallest) >= 0.01
    assert _area_ha(largest) <= 10_000.0
    assert _area_ha(largest) == pytest.approx(10_000.0, rel=0.005)


@pytest.mark.parametrize(
    "kwargs, code",
    [
        ({"lat": 91.0, "lon": 10.0, "area_ha": 1.0}, "coordinate_out_of_range"),
        ({"lat": 10.0, "lon": 181.0, "area_ha": 1.0}, "coordinate_out_of_range"),
        ({"lat": float("nan"), "lon": 10.0, "area_ha": 1.0}, "invalid_coordinate"),
        ({"lat": 10.0, "lon": 10.0, "area_ha": 0.0}, "invalid_area"),
        ({"lat": 10.0, "lon": 10.0, "area_ha": -3.0}, "invalid_area"),
        ({"lat": 10.0, "lon": 10.0, "area_ha": float("inf")}, "invalid_coordinate"),
        ({"lat": 10.0, "lon": 10.0, "area_ha": 0.001}, "area_too_small"),
        ({"lat": 10.0, "lon": 10.0, "area_ha": 20_000.0}, "area_too_large"),
        ({"lat": 10.0, "lon": 10.0, "area_ha": 1.0, "shape": "hexagon"}, "invalid_shape"),
        ({"lat": 89.9999, "lon": 10.0, "area_ha": 100.0}, "pole"),
        ({"lat": 10.0, "lon": 179.9999, "area_ha": 100.0}, "antimeridian"),
    ],
)
def test_bad_pin_or_area_is_rejected_with_a_stable_code(kwargs, code):
    with pytest.raises(ConstructionError) as caught:
        polygon_from_point(**kwargs)
    assert caught.value.code == code
    assert isinstance(caught.value, GeometryError)


def test_bad_pin_messages_do_not_echo_coordinates():
    with pytest.raises(InvalidPointError) as caught:
        polygon_from_point(123.456789, 10.0, 1.0)
    assert "123.456789" not in caught.value.detail
    with pytest.raises(InvalidAreaError):
        polygon_from_point(10.0, 10.0, -1.0)


def test_non_numbers_are_rejected():
    with pytest.raises(InvalidPointError):
        polygon_from_point("13.2", 77.5, 1.0)  # type: ignore[arg-type]
    with pytest.raises(InvalidPointError):
        polygon_from_point(True, 77.5, 1.0)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------- tree line
LINE = [[77.5370, 13.2910], [77.5395, 13.2912]]


def test_strip_area_is_length_times_width_for_a_straight_line():
    result = strip_from_line(LINE, 4.0)
    length = GEOD.line_length([p[0] for p in LINE], [p[1] for p in LINE])
    assert result["length_m"] == pytest.approx(length, abs=0.1)
    # flat caps: the strip is a rectangle of width 4 m
    assert result["area_hectares"] * 10_000 == pytest.approx(length * 4.0, rel=0.005)
    assert _area_ha(result) == pytest.approx(result["area_hectares"], rel=1e-3)
    assert result["method"].startswith("line buffered by width/2")


def test_strip_covers_the_line_and_stays_within_half_the_width():
    result = strip_from_line(LINE, 10.0)
    polygon = shape(result["geometry"])
    mid = Point((LINE[0][0] + LINE[1][0]) / 2, (LINE[0][1] + LINE[1][1]) / 2)
    assert polygon.contains(mid)
    assert polygon.is_valid
    # no point of the strip is more than 5 m (+ tolerance) from the line
    from shapely.geometry import LineString

    line = LineString(LINE)
    metres_per_degree = 111_320.0 * math.cos(math.radians(13.29))
    farthest = max(line.distance(Point(c)) for c in polygon.exterior.coords) * metres_per_degree
    assert farthest <= 5.0 + 0.3


def test_strip_follows_a_bent_line():
    bent = [[77.5370, 13.2910], [77.5380, 13.2910], [77.5380, 13.2920]]
    result = strip_from_line(bent, 6.0)
    polygon = shape(result["geometry"])
    assert polygon.is_valid
    assert polygon.contains(Point(77.5380, 13.2910))  # the corner
    assert not polygon.contains(Point(77.5370, 13.2920))  # the empty corner of the bounding box
    assert result["length_m"] > GEOD.inv(77.5370, 13.2910, 77.5380, 13.2920)[2]


def test_three_dimensional_positions_and_repeated_vertices_are_accepted():
    line = [[77.5370, 13.2910, 0], [77.5370, 13.2910, 5], [77.5395, 13.2912, 0]]
    result = strip_from_line(line, 4.0)
    assert result["length_m"] > 200


@pytest.mark.parametrize(
    "length_m, spacing_m, trees",
    [(270.6, 5.0, 55), (100.0, 5.0, 21), (100.0, 7.0, 15), (4.9, 5.0, 1), (0.0, 5.0, 1)],
)
def test_tree_count_is_floor_of_length_over_spacing_plus_one(length_m, spacing_m, trees):
    assert suggest_tree_count(length_m, spacing_m) == trees


def test_tree_count_rejects_nonsense():
    with pytest.raises(ValueError):
        suggest_tree_count(10.0, 0.0)
    with pytest.raises(ValueError):
        suggest_tree_count(-1.0, 5.0)


def test_long_lines_are_simplified_to_the_vertex_limit():
    coords = [[77.0 + i * 0.00005, 13.0 + 0.0003 * math.sin(i / 60.0)] for i in range(400)]
    limits = ValidationLimits(max_vertices=500)
    result = strip_from_line(coords, 4.0, limits)
    assert len(result["geometry"]["coordinates"][0]) - 1 <= 500
    assert "simplified" in result["method"]
    assert shape(result["geometry"]).is_valid


@pytest.mark.parametrize(
    "coords, width, code",
    [
        ([[77.0, 13.0]], 4.0, "too_few_vertices"),
        ([[77.0, 13.0], [77.0, 13.0]], 4.0, "zero_length"),
        ([[77.0, 13.0], [77.001, 13.0]], 0.5, "invalid_width"),
        ([[77.0, 13.0], [77.001, 13.0]], 51.0, "invalid_width"),
        ([[77.0, 13.0], [77.001, 13.0]], float("nan"), "invalid_coordinate"),
        ([[77.0, 13.0], [200.0, 13.0]], 4.0, "coordinate_out_of_range"),
        ([[77.0, 13.0], [77.0, 95.0]], 4.0, "coordinate_out_of_range"),
        ([[77.0, 13.0], [77.0]], 4.0, "invalid_coordinate"),
        ([[77.0, 13.0], ["a", "b"]], 4.0, "invalid_coordinate"),
        ([[77.0, 13.0], [77.0001, 13.0]], 1.0, "area_too_small"),  # ~11 m x 1 m < 0.01 ha
        ([[77.0, 13.0], [78.0, 13.0], [79.0, 13.0], [80.0, 13.0]], 4.0, "line_too_long"),
        ([[179.9, 10.0], [-179.9, 10.0]], 4.0, "antimeridian"),
        ("not a line", 4.0, "invalid_geometry"),
    ],
)
def test_bad_lines_are_rejected_with_a_stable_code(coords, width, code):
    with pytest.raises(GeometryError) as caught:
        strip_from_line(coords, width)
    assert caught.value.code == code


def test_a_zigzag_that_cannot_be_simplified_is_rejected():
    coords = [[77.0 + i * 0.00005, 13.0 + 0.0001 * (i % 2)] for i in range(400)]
    with pytest.raises(InvalidLineError) as caught:
        strip_from_line(coords, 4.0, ValidationLimits(max_vertices=500))
    assert caught.value.code == "too_many_vertices"


def test_too_many_vertices_is_rejected():
    coords = [[77.0 + i * 1e-5, 13.0] for i in range(501)]
    with pytest.raises(InvalidLineError) as caught:
        strip_from_line(coords, 4.0)
    assert caught.value.code == "too_many_vertices"


def test_line_errors_do_not_echo_coordinates():
    with pytest.raises(InvalidLineError) as caught:
        strip_from_line([[77.0, 13.0], [200.123456, 13.0]], 4.0)
    assert "200.123456" not in caught.value.detail
