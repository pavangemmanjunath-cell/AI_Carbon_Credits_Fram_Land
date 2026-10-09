from __future__ import annotations

import re

import pytest

from geo_engine.errors import GeometryError
from geo_engine.geometry import (
    ValidationLimits,
    generalize_point,
    measure_polygon,
    new_plot_id,
    validate_polygon,
)

SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [[77.53, 13.29], [77.54, 13.29], [77.54, 13.30], [77.53, 13.30], [77.53, 13.29]]
    ],
}


def test_square_near_equator_area_is_about_120_ha():
    polygon = validate_polygon(SQUARE)
    metrics = measure_polygon(polygon)
    # 0.01° × 0.01° at 13.3°N ≈ 1.08 km × 1.11 km ≈ 119.9 ha
    assert 118 < metrics.area_hectares < 122
    assert metrics.area_acres == pytest.approx(metrics.area_hectares * 2.4710538, rel=1e-6)
    assert 4300 < metrics.perimeter_m < 4450
    assert metrics.centroid_lat == pytest.approx(13.295, abs=1e-4)
    assert metrics.centroid_lon == pytest.approx(77.535, abs=1e-4)


def test_unclosed_ring_is_closed_automatically():
    geom = {"type": "Polygon", "coordinates": [[[77.53, 13.29], [77.54, 13.29], [77.54, 13.30]]]}
    polygon = validate_polygon(geom)
    assert polygon.exterior.coords[0] == polygon.exterior.coords[-1]


@pytest.mark.parametrize(
    "geometry, code",
    [
        (None, "invalid_geometry"),
        ({"type": "Point", "coordinates": [1, 2]}, "invalid_geometry"),
        ({"type": "Polygon", "coordinates": []}, "invalid_geometry"),
        ({"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}, "too_few_vertices"),
        (
            {"type": "Polygon", "coordinates": [[[200, 0], [201, 0], [201, 1], [200, 0]]]},
            "coordinate_out_of_range",
        ),
        (
            {"type": "Polygon", "coordinates": [[[0, 95], [1, 95], [1, 96], [0, 95]]]},
            "coordinate_out_of_range",
        ),
        (
            {"type": "Polygon", "coordinates": [[["a", 0], [1, 0], [1, 1], ["a", 0]]]},
            "invalid_coordinate",
        ),
        # bow-tie (self-intersecting)
        (
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.01, 0.01], [0.01, 0], [0, 0.01], [0, 0]]],
            },
            "self_intersection",
        ),
        # degenerate: all points on a line
        ({"type": "Polygon", "coordinates": [[[0, 0], [0.01, 0], [0.02, 0], [0, 0]]]}, "zero_area"),
    ],
)
def test_invalid_geometries_raise_with_code(geometry, code):
    with pytest.raises(GeometryError) as excinfo:
        validate_polygon(geometry)
    assert excinfo.value.code == code


def test_area_limits():
    tiny = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0.00005, 0], [0.00005, 0.00005], [0, 0.00005], [0, 0]]],
    }
    with pytest.raises(GeometryError) as excinfo:
        validate_polygon(tiny)
    assert excinfo.value.code == "area_too_small"

    huge = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}
    with pytest.raises(GeometryError) as excinfo:
        validate_polygon(huge)
    assert excinfo.value.code == "area_too_large"


def test_vertex_limit_is_configurable():
    ring = [[77.53 + i * 1e-5, 13.29 + (i % 2) * 1e-5] for i in range(12)]
    ring += [[77.53 + 12e-5, 13.31], [77.53, 13.31], ring[0]]
    geom = {"type": "Polygon", "coordinates": [ring]}
    validate_polygon(geom)  # 14 vertices is fine by default
    with pytest.raises(GeometryError) as excinfo:
        validate_polygon(geom, ValidationLimits(max_vertices=10))
    assert excinfo.value.code == "too_many_vertices"


def test_generalize_point_rounds_to_0_05_degree():
    assert generalize_point(13.2923, 77.5384) == (13.3, 77.55)
    assert generalize_point(32.6251, -83.6249) == (32.65, -83.6)
    assert generalize_point(-0.01, 179.99) == (0.0, 180.0)


def test_plot_id_format_and_uniqueness():
    ids = {new_plot_id() for _ in range(200)}
    assert len(ids) == 200
    for plot_id in ids:
        assert re.fullmatch(r"PLT-[A-Z2-7]{6}", plot_id), plot_id
