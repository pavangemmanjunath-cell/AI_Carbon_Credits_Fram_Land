"""Geometry helper endpoints: pin + area, tree line, typed coordinates (nothing is stored)."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import shape

from app.core.config import Settings
from app.main import create_app
from geo_engine.construct import geodesic_area_m2

ACRE_IN_HA = 0.40468564224
JSON = "application/problem+json"


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False, ATLAS_API_KEYS="")  # type: ignore[call-arg]
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def area_ha(geometry: dict) -> float:
    return geodesic_area_m2(shape(geometry)) / 10_000.0


def assert_problem(response, status: int, slug: str | None = None) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(JSON)
    body = response.json()
    assert body["status"] == status and body["title"]
    if slug:
        assert body["type"].endswith("/" + slug)
    return body


# ---------------------------------------------------------------------------- from-point
def test_pin_and_area_in_acres(api):
    response = api.post(
        "/api/v1/geometry/from-point",
        json={
            "lat": 13.2923,
            "lon": 77.5384,
            "area": {"value": 5, "unit": "ac"},
            "shape": "square",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["type"] == "Polygon"
    assert area_ha(body["geometry"]) == pytest.approx(5 * ACRE_IN_HA, rel=0.005)  # contract: 0.5 %
    assert body["area_hectares"] == pytest.approx(2.0234, abs=0.003)
    assert body["area_acres"] == pytest.approx(5.0, rel=0.005)
    assert body["boundary_quality"] == "approximate"
    assert body["method"].startswith("geodesic square centred on the pin (side 142.")
    assert body["provenance"]["mode"] == "demo" and body["provenance"]["api_version"]
    assert body["provenance"]["notes"]


@pytest.mark.parametrize(
    "area, expected_ha",
    [
        ({"value": 2, "unit": "ha"}, 2.0),
        ({"value": 2}, 2.0),  # hectares by default
        ({"value": 20_000, "unit": "m2"}, 2.0),
        ({"value": 1, "unit": "ac"}, ACRE_IN_HA),
    ],
)
@pytest.mark.parametrize("shape_name", ["square", "circle"])
def test_units_and_shapes(api, area, expected_ha, shape_name):
    response = api.post(
        "/api/v1/geometry/from-point",
        json={"lat": 40.7128, "lon": -74.006, "area": area, "shape": shape_name},
    )
    assert response.status_code == 200
    body = response.json()
    assert area_ha(body["geometry"]) == pytest.approx(expected_ha, rel=0.005)
    if shape_name == "circle":
        assert "circle" in body["method"] and body["radius_m"] > 0
    else:
        assert body["side_m"] > 0


def test_shape_defaults_to_square(api):
    body = api.post(
        "/api/v1/geometry/from-point",
        json={"lat": 13.0, "lon": 77.0, "area": {"value": 1, "unit": "ha"}},
    ).json()
    assert len(body["geometry"]["coordinates"][0]) == 5


def test_a_pin_polygon_is_accepted_as_a_plot(api):
    built = api.post(
        "/api/v1/geometry/from-point",
        json={"lat": 13.2923, "lon": 77.5384, "area": {"value": 3, "unit": "ha"}},
    ).json()
    created = api.post(
        "/api/v1/plots",
        json={
            "name": "Pin plot",
            "country": "IN",
            "source": "pin-and-area",
            "boundary_quality": built["boundary_quality"],
            "geometry": built["geometry"],
        },
    )
    assert created.status_code == 201
    plot = created.json()
    assert plot["source"] == "pin-and-area" and plot["boundary_quality"] == "approximate"
    assert plot["area_hectares"] == pytest.approx(3.0, rel=0.005)
    api.delete(f"/api/v1/plots/{plot['plot_id']}")


@pytest.mark.parametrize(
    "body, slug, code",
    [
        (
            {"lat": 13.0, "lon": 77.0, "area": {"value": 100_000, "unit": "ha"}},
            "invalid-geometry",
            "area_too_large",
        ),
        (
            {"lat": 13.0, "lon": 77.0, "area": {"value": 0.001, "unit": "ha"}},
            "invalid-geometry",
            "area_too_small",
        ),
        (
            {"lat": 89.9999, "lon": 77.0, "area": {"value": 100, "unit": "ha"}},
            "invalid-geometry",
            "pole",
        ),
    ],
)
def test_area_problems_are_422_problem_json_with_a_code(api, body, slug, code):
    problem = assert_problem(api.post("/api/v1/geometry/from-point", json=body), 422, slug)
    assert problem["code"] == code and problem["detail"]


@pytest.mark.parametrize(
    "body",
    [
        {"lat": 91, "lon": 77.0, "area": {"value": 1}},
        {"lat": 13.0, "lon": 181, "area": {"value": 1}},
        {"lat": 13.0, "lon": 77.0, "area": {"value": 0}},
        {"lat": 13.0, "lon": 77.0, "area": {"value": -2, "unit": "ha"}},
        {"lat": 13.0, "lon": 77.0, "area": {"value": 1, "unit": "km2"}},
        {"lat": 13.0, "lon": 77.0, "area": {"value": 1}, "shape": "hexagon"},
        {"lat": 13.0, "lon": 77.0},
        {"lat": "north", "lon": 77.0, "area": {"value": 1}},
        {"lat": 13.0, "lon": 77.0, "area": {"value": 1}, "extra": True},
        {"lat": 13.0, "lon": 77.0, "area": {"value": 1, "colour": "red"}},
    ],
)
def test_invalid_pin_requests_fail_validation(api, body):
    problem = assert_problem(
        api.post("/api/v1/geometry/from-point", json=body), 422, "validation-error"
    )
    assert problem["errors"]


def test_no_api_key_is_needed():
    settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False, ATLAS_API_KEYS="s3cret")  # type: ignore[call-arg]
    with TestClient(create_app(settings)) as keyed:
        for path, body in (
            ("/api/v1/geometry/from-point", {"lat": 13.0, "lon": 77.0, "area": {"value": 1}}),
            (
                "/api/v1/geometry/from-line",
                {"line": {"type": "LineString", "coordinates": [[77.0, 13.0], [77.003, 13.0]]}},
            ),
            ("/api/v1/geometry/parse-coordinates", {"text": "13.2, 77.5"}),
        ):
            assert keyed.post(path, json=body).status_code == 200, path


# ---------------------------------------------------------------------------- from-line
LINE = {"type": "LineString", "coordinates": [[77.5370, 13.2910], [77.5395, 13.2912]]}


def test_tree_line_example_from_the_contract(api):
    response = api.post(
        "/api/v1/geometry/from-line", json={"line": LINE, "width_m": 4, "spacing_m": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["type"] == "Polygon" and shape(body["geometry"]).is_valid
    assert body["length_m"] == pytest.approx(271.8, abs=1.5)
    assert body["area_hectares"] * 10_000 == pytest.approx(body["length_m"] * 4, rel=0.01)
    assert body["suggested_tree_count"] == 55  # floor(271.8 / 5) + 1
    assert body["boundary_quality"] == "approximate"
    assert body["method"] == (
        "line buffered by width/2 in a local metric projection; trees = floor(length / spacing) + 1"
    )
    assert body["provenance"]["sources"] == []


def test_tree_line_defaults_and_spacing(api):
    default = api.post("/api/v1/geometry/from-line", json={"line": LINE}).json()
    assert default["area_hectares"] * 10_000 == pytest.approx(default["length_m"] * 4, rel=0.01)
    wider = api.post("/api/v1/geometry/from-line", json={"line": LINE, "spacing_m": 10}).json()
    assert wider["suggested_tree_count"] == 28  # floor(271.8 / 10) + 1
    tight = api.post("/api/v1/geometry/from-line", json={"line": LINE, "spacing_m": 0.5}).json()
    assert tight["suggested_tree_count"] == 544


def test_a_tree_line_polygon_is_accepted_as_a_plot(api):
    built = api.post("/api/v1/geometry/from-line", json={"line": LINE, "width_m": 10}).json()
    created = api.post(
        "/api/v1/plots",
        json={
            "name": "Tree line",
            "country": "IN",
            "source": "tree-line",
            "boundary_quality": "approximate",
            "geometry": built["geometry"],
        },
    )
    assert created.status_code == 201
    assert created.json()["area_hectares"] == pytest.approx(built["area_hectares"], rel=0.01)
    api.delete(f"/api/v1/plots/{created.json()['plot_id']}")


@pytest.mark.parametrize(
    "body, slug",
    [
        ({"line": {"type": "LineString", "coordinates": [[77.0, 13.0]]}}, "validation-error"),
        ({"line": {"type": "Point", "coordinates": [77.0, 13.0]}}, "validation-error"),
        ({"line": {"type": "LineString", "coordinates": [[77.0, 13.0]] * 501}}, "validation-error"),
        ({"line": LINE, "width_m": 0.5}, "validation-error"),
        ({"line": LINE, "width_m": 51}, "validation-error"),
        ({"line": LINE, "spacing_m": 0.4}, "validation-error"),
        ({"line": LINE, "spacing_m": 51}, "validation-error"),
        ({"line": LINE, "colour": "red"}, "validation-error"),
        ({}, "validation-error"),
    ],
)
def test_invalid_line_requests_fail_validation(api, body, slug):
    assert_problem(api.post("/api/v1/geometry/from-line", json=body), 422, slug)


@pytest.mark.parametrize(
    "coordinates, code",
    [
        ([[77.0, 13.0], [77.0, 13.0]], "zero_length"),
        ([[77.0, 13.0], [77.0001, 13.0]], "area_too_small"),
        ([[77.0, 13.0], [78.0, 13.0], [79.0, 13.0], [80.0, 13.0]], "line_too_long"),
        ([[179.9, 10.0], [-179.9, 10.0]], "antimeridian"),
        ([[77.0, 13.0], [200.0, 13.0]], "coordinate_out_of_range"),
    ],
)
def test_line_problems_are_422_with_a_code(api, coordinates, code):
    body = {"line": {"type": "LineString", "coordinates": coordinates}}
    problem = assert_problem(
        api.post("/api/v1/geometry/from-line", json=body), 422, "invalid-geometry"
    )
    assert problem["code"] == code
    assert "200.0" not in problem["detail"]


# ---------------------------------------------------------------------------- parse-coordinates
def test_mixed_formats_make_a_polygon(api):
    text = "13.2923, 77.5384\n13°17'40\"N 77°32'25\"E\n13.2935 77.5400"
    response = api.post("/api/v1/geometry/parse-coordinates", json={"text": text})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "polygon" and body["geometry"]["type"] == "Polygon"
    assert len(body["points"]) == 3 and body["points"][0] == {"lat": 13.2923, "lon": 77.5384}
    assert body["points"][1]["lat"] == pytest.approx(13.2944, abs=1e-4)
    assert body["area_hectares"] == pytest.approx(0.706, rel=0.02)
    assert body["warnings"] == []
    ring = body["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]  # closed automatically


def test_one_point_two_points_and_nothing(api):
    one = api.post("/api/v1/geometry/parse-coordinates", json={"text": "13.2923, 77.5384"}).json()
    assert one["kind"] == "point" and one["geometry"]["type"] == "Point"
    assert one["area_hectares"] is None
    two = api.post(
        "/api/v1/geometry/parse-coordinates", json={"text": "13.2923, 77.5384\n13.29 77.54"}
    ).json()
    assert two["kind"] == "invalid" and two["geometry"] is None and two["warnings"]
    none = api.post("/api/v1/geometry/parse-coordinates", json={"text": "hello there"}).json()
    assert none["kind"] == "invalid" and none["points"] == []
    blank = api.post("/api/v1/geometry/parse-coordinates", json={"text": "   \n  "}).json()
    assert blank["kind"] == "invalid"


def test_swapped_order_is_fixed_with_a_warning(api):
    body = api.post("/api/v1/geometry/parse-coordinates", json={"text": "100.5, 13.75"}).json()
    assert body["kind"] == "point"
    assert body["points"][0] == {"lat": 13.75, "lon": 100.5}
    assert any("swapped" in w for w in body["warnings"])


def test_hemisphere_letters_and_decimal_commas(api):
    body = api.post(
        "/api/v1/geometry/parse-coordinates",
        json={"text": "33.9249S 18.4241E\n33,9300S;18,4300E\nS33.9400 E18.4200"},
    ).json()
    assert body["kind"] == "polygon"
    assert body["points"][0]["lat"] == pytest.approx(-33.9249)
    assert body["points"][1]["lat"] == pytest.approx(-33.93)


def test_self_intersecting_points_are_invalid_with_advice(api):
    text = "13.2910, 77.5370\n13.2930, 77.5390\n13.2930, 77.5370\n13.2910, 77.5390"
    body = api.post("/api/v1/geometry/parse-coordinates", json={"text": text}).json()
    assert body["kind"] == "invalid" and any("in order" in w for w in body["warnings"])


def test_coordinate_limits(api):
    too_many = "\n".join("13.29, 77.53" for _ in range(501))
    problem = assert_problem(
        api.post("/api/v1/geometry/parse-coordinates", json={"text": too_many}),
        422,
        "invalid-geometry",
    )
    assert problem["code"] == "too_many_lines"
    too_long = "1" * 20_001
    assert_problem(
        api.post("/api/v1/geometry/parse-coordinates", json={"text": too_long}),
        422,
        "validation-error",
    )
    assert_problem(
        api.post("/api/v1/geometry/parse-coordinates", json={"text": ""}), 422, "validation-error"
    )
    assert_problem(api.post("/api/v1/geometry/parse-coordinates", json={}), 422, "validation-error")
    exactly = "\n".join(f"13.{29 + i % 7}, 77.53" for i in range(500))
    assert api.post("/api/v1/geometry/parse-coordinates", json={"text": exactly}).status_code == 200


# ---------------------------------------------------------------------------- privacy
def test_coordinates_are_never_logged_or_echoed_in_problems(api, caplog):
    secret_lat, secret_lon = "13.123456", "77.654321"
    with caplog.at_level(logging.DEBUG):
        api.post(
            "/api/v1/geometry/from-point",
            json={"lat": 13.123456, "lon": 77.654321, "area": {"value": 2, "unit": "ha"}},
        )
        api.post(
            "/api/v1/geometry/from-point",
            json={"lat": 13.123456, "lon": 77.654321, "area": {"value": 99999999, "unit": "ha"}},
        )
        api.post(
            "/api/v1/geometry/from-line",
            json={
                "line": {
                    "type": "LineString",
                    "coordinates": [[77.654321, 13.123456], [77.6543, 13.1237]],
                }
            },
        )
        api.post(
            "/api/v1/geometry/parse-coordinates",
            json={"text": "13.123456, 77.654321\nfoo 13.123456 bar\n13.1237 77.6545"},
        )
        problem = api.post(
            "/api/v1/geometry/from-line",
            json={
                "line": {
                    "type": "LineString",
                    "coordinates": [[777.654321, 13.123456], [77.6543, 13.1237]],
                }
            },
        )
    logged = " ".join(f"{r.getMessage()} {r.__dict__.get('path', '')}" for r in caplog.records)
    assert secret_lat not in logged and secret_lon not in logged
    assert "777.654321" not in problem.text
