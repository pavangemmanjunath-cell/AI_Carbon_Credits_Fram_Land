"""Typed / pasted coordinates (geo_engine.coordinates)."""

from __future__ import annotations

import pytest

from geo_engine.coordinates import (
    MAX_CHARS,
    MAX_LINES,
    parse_coordinate_line,
    parse_coordinate_value,
    parse_coordinates,
)
from geo_engine.errors import GeometryError


def _single(text: str) -> tuple[float, float]:
    parsed = parse_coordinates(text)
    assert parsed.kind == "point", parsed.warnings
    assert len(parsed.points) == 1
    return parsed.points[0].lat, parsed.points[0].lon


# ---------------------------------------------------------------------------- one point per format
@pytest.mark.parametrize(
    "text",
    [
        "13.2923, 77.5384",
        "13.2923 77.5384",
        "13.2923;77.5384",
        "13.2923,77.5384",
        "  13.2923 ,   77.5384  ",
        "13,2923;77,5384",  # decimal comma
        "lat: 13.2923, lon: 77.5384",
        "lat=13.2923 lng=77.5384",
        "Latitude 13.2923 Longitude 77.5384",
        "13.29230 77.53840\r",
        "13.2923\t77.5384",
    ],
)
def test_decimal_degrees_in_common_layouts(text):
    assert _single(text) == pytest.approx((13.2923, 77.5384), abs=1e-6)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("13.2923N 77.5384E", (13.2923, 77.5384)),
        ("13.2923 N, 77.5384 E", (13.2923, 77.5384)),
        ("N13.2923 E77.5384", (13.2923, 77.5384)),
        ("33.9249S 18.4241E", (-33.9249, 18.4241)),
        ("40.7128N 74.0060W", (40.7128, -74.006)),
        ("S33.9249 W70.6693", (-33.9249, -70.6693)),
        ("77.5384E 13.2923N", (13.2923, 77.5384)),  # the letters decide the order
        ("E77.5384 N13.2923", (13.2923, 77.5384)),
        ("n13.2923 e77.5384", (13.2923, 77.5384)),
    ],
)
def test_hemisphere_letters_set_sign_and_order(text, expected):
    assert _single(text) == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize(
    "text",
    [
        "13°17'32.3\"N 77°32'18.2\"E",
        "13° 17' 32.3\" N, 77° 32' 18.2\" E",
        "N13°17'32.3\" E77°32'18.2\"",
        "13d17m32.3sN 77d32m18.2sE",
        "13 17 32.3 N 77 32 18.2 E",
        "13º17′32.3″N 77º32′18.2″E",  # typographic marks pasted from documents
    ],
)
def test_degrees_minutes_seconds(text):
    lat, lon = _single(text)
    assert lat == pytest.approx(13 + 17 / 60 + 32.3 / 3600, abs=1e-6)
    assert lon == pytest.approx(77 + 32 / 60 + 18.2 / 3600, abs=1e-6)


def test_degrees_and_decimal_minutes():
    lat, lon = _single("13°17.538'N 77°32.303'E")
    assert lat == pytest.approx(13 + 17.538 / 60, abs=1e-6)
    assert lon == pytest.approx(77 + 32.303 / 60, abs=1e-6)


def test_dms_in_the_southern_and_western_hemispheres_are_negative():
    lat, lon = _single("33°55'30\"S 18°25'27\"W")
    assert lat < 0 and lon < 0
    assert lat == pytest.approx(-(33 + 55 / 60 + 30 / 3600), abs=1e-6)


def test_signed_decimals_are_kept():
    assert _single("-33.9249, 18.4241") == pytest.approx((-33.9249, 18.4241), abs=1e-6)
    assert _single("40.7128, -74.0060") == pytest.approx((40.7128, -74.006), abs=1e-6)


# ---------------------------------------------------------------------------- swapped order
def test_longitude_first_is_swapped_with_a_warning():
    swapped = parse_coordinates("100.5, 13.75")  # 100.5 cannot be a latitude
    assert swapped.kind == "point"
    assert swapped.points[0].lat == pytest.approx(13.75)
    assert swapped.points[0].lon == pytest.approx(100.5)
    assert any("swapped" in w for w in swapped.warnings)
    assert "line" in swapped.warnings[0].lower()


def test_values_that_fit_either_way_are_not_swapped():
    parsed = parse_coordinates("13.2923, 77.5384")
    assert parsed.warnings == []
    assert parsed.points[0].lat == pytest.approx(13.2923)


# ---------------------------------------------------------------------------- points -> geometry
def test_one_point_gives_a_point_geometry():
    parsed = parse_coordinates("13.2923, 77.5384")
    assert parsed.kind == "point"
    assert parsed.geometry == {"type": "Point", "coordinates": [77.5384, 13.2923]}
    assert parsed.area_hectares is None
    assert parsed.to_dict()["points"] == [{"lat": 13.2923, "lon": 77.5384}]


def test_two_points_are_invalid_with_a_warning():
    parsed = parse_coordinates("13.2923, 77.5384\n13.2935, 77.5400")
    assert parsed.kind == "invalid"
    assert parsed.geometry is None and parsed.area_hectares is None
    assert len(parsed.points) == 2
    assert any("third" in w for w in parsed.warnings)


def test_three_or_more_points_make_a_closed_polygon_with_an_area():
    text = "13.2910, 77.5370\n13.2910, 77.5390\n13.2930, 77.5390\n13.2930, 77.5370"
    parsed = parse_coordinates(text)
    assert parsed.kind == "polygon"
    ring = parsed.geometry["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 5
    assert ring[0] == [77.537, 13.291]  # [lon, lat]
    # 0.002 deg x 0.002 deg at 13.3 N is about 4.8 ha
    assert parsed.area_hectares == pytest.approx(4.8, rel=0.03)
    assert parsed.warnings == []


def test_a_ring_the_user_closed_is_not_duplicated():
    text = "13.2910, 77.5370\n13.2910, 77.5390\n13.2930, 77.5390\n13.2910, 77.5370"
    parsed = parse_coordinates(text)
    assert parsed.kind == "polygon"
    assert len(parsed.geometry["coordinates"][0]) == 4
    assert any("merged" in w for w in parsed.warnings)


def test_mixed_formats_in_one_paste():
    text = "13.2923, 77.5384\n13°17'40\"N 77°32'25\"E\n13.2935 77.5400"
    parsed = parse_coordinates(text)
    assert parsed.kind == "polygon"
    assert parsed.points[1].lat == pytest.approx(13 + 17 / 60 + 40 / 3600, abs=1e-6)
    assert parsed.points[1].lon == pytest.approx(77 + 32 / 60 + 25 / 3600, abs=1e-6)


def test_header_and_blank_lines_are_ignored_and_bad_lines_are_reported_by_number():
    text = (
        "latitude,longitude\n\n13.2910, 77.5370\nnot a point 1 2 3\n"
        "13.2910, 77.5390\n13.2930, 77.5390\n"
    )
    parsed = parse_coordinates(text)
    assert parsed.kind == "polygon"
    assert len(parsed.points) == 3
    assert any("Line(s) 4" in w for w in parsed.warnings)


def test_a_self_intersecting_polygon_is_invalid_and_asks_for_order():
    text = "13.2910, 77.5370\n13.2930, 77.5390\n13.2930, 77.5370\n13.2910, 77.5390"
    parsed = parse_coordinates(text)
    assert parsed.kind == "invalid"
    assert parsed.geometry is None
    assert any("in order" in w for w in parsed.warnings)


def test_a_polygon_below_the_minimum_area_is_invalid():
    text = "13.29100, 77.53700\n13.29100, 77.53705\n13.29105, 77.53705"
    parsed = parse_coordinates(text)
    assert parsed.kind == "invalid"
    assert parsed.warnings


@pytest.mark.parametrize("text", ["", "   \n  ", "hello world", "latitude,longitude"])
def test_nothing_to_read_is_invalid_with_a_hint(text):
    parsed = parse_coordinates(text)
    assert parsed.kind == "invalid"
    assert parsed.points == []
    assert any("No coordinates" in w for w in parsed.warnings)


@pytest.mark.parametrize(
    "text", ["95.0, 200.0", "13.2923", "13.2923, 77.5384, 5.0, 1", "N13.29 N14.29"]
)
def test_unreadable_lines_are_skipped_not_guessed(text):
    parsed = parse_coordinates(text)
    assert parsed.kind == "invalid"
    assert parsed.points == []


# ---------------------------------------------------------------------------- limits and privacy
def test_line_and_character_limits():
    many = "\n".join("13.29, 77.53" for _ in range(MAX_LINES + 1))
    with pytest.raises(GeometryError) as lines:
        parse_coordinates(many)
    assert lines.value.code == "too_many_lines"
    with pytest.raises(GeometryError) as chars:
        parse_coordinates("x" * (MAX_CHARS + 1))
    assert chars.value.code == "text_too_long"
    # exactly 500 data lines are fine
    ok = "\n".join(f"13.{29 + i % 5}, 77.53" for i in range(MAX_LINES))
    assert parse_coordinates(ok).points


def test_non_string_input_is_rejected():
    with pytest.raises(GeometryError) as caught:
        parse_coordinates(12345)  # type: ignore[arg-type]
    assert caught.value.code == "invalid_input"


def test_warnings_never_contain_the_coordinates():
    text = "13.2910, 77.5370\n13.2930, 77.5390\n13.2930, 77.5370\n13.2910, 77.5390\nfoo 9 8 7"
    parsed = parse_coordinates(text)
    joined = " ".join(parsed.warnings)
    for fragment in ("13.2910", "77.5370", "13.2930", "77.5390", "9 8 7"):
        assert fragment not in joined


# ---------------------------------------------------------------------------- helpers
@pytest.mark.parametrize(
    "text, axis, value",
    [
        ("13.2923", None, 13.2923),
        ("13,2923", None, 13.2923),
        ("-33.9", "lat", -33.9),
        ("77.5E", "lon", 77.5),
        ("12S", "lat", -12.0),
        ("13°30'N", "lat", 13.5),
    ],
)
def test_single_values_for_csv_cells(text, axis, value):
    assert parse_coordinate_value(text, axis) == pytest.approx(value)


@pytest.mark.parametrize(
    "text, axis", [("abc", None), ("", None), ("95", "lat"), ("200", "lon"), ("12N", "lon")]
)
def test_single_values_out_of_range_or_unreadable_raise_value_error(text, axis):
    with pytest.raises(ValueError):
        parse_coordinate_value(text, axis)


def test_line_parser_reports_the_swap_flag():
    assert parse_coordinate_line("13.2, 77.5") == (13.2, 77.5, False)
    assert parse_coordinate_line("100.5, 13.75") == (13.75, 100.5, True)
    assert parse_coordinate_line("garbage") is None
