# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Tests of ``qgis_helpers`` and ``tasks`` against the fake ``qgis.core`` (no Qt needed).

The fakes implement the documented behaviour of the PyQGIS calls the plugin makes, so these
tests check the plugin's own logic: reprojection direction, centroid-in-field counting, the
attribute subset that is requested, what is stored in the project and what reaches the log.
"""

from __future__ import annotations

import importlib
import logging
import math
import random
from types import ModuleType
from typing import Any

import pytest
from qgis_fakes import LayerBuilder

from agricarbon_atlas_qgis import config, crowns
from agricarbon_atlas_qgis.diagnostics import exception_summary
from agricarbon_atlas_qgis.geometry import GeometryError

SQUARE = [(77.50, 13.20), (77.52, 13.20), (77.52, 13.22), (77.50, 13.22)]
HOLE = [(77.505, 13.205), (77.515, 13.205), (77.515, 13.215), (77.505, 13.215)]


# --------------------------------------------------------------------------- helpers
def mercator(lon: float, lat: float) -> tuple[float, float]:
    """EPSG:4326 -> EPSG:3857, written out independently of the fake."""
    radius = 6378137.0
    return (
        math.radians(lon) * radius,
        math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * radius,
    )


@pytest.fixture
def helpers(fake_qgis: ModuleType) -> ModuleType:
    return importlib.import_module("agricarbon_atlas_qgis.qgis_helpers")


@pytest.fixture
def tasks(fake_qgis: ModuleType) -> ModuleType:
    return importlib.import_module("agricarbon_atlas_qgis.tasks")


@pytest.fixture
def build(fake_qgis: ModuleType) -> LayerBuilder:
    return LayerBuilder()


select = LayerBuilder.select


# --------------------------------------------------------------------------- settings
def test_settings_default_when_nothing_is_stored(helpers: ModuleType) -> None:
    assert helpers.load_config() == config.PluginConfig()


def test_settings_round_trip(helpers: ModuleType) -> None:
    cfg = config.PluginConfig("https://atlas.example.org/api/v1", "key-1", "DE", 45.0)
    helpers.save_config(cfg)
    assert helpers.load_config() == cfg


def test_settings_live_under_the_plugin_prefix(helpers: ModuleType, fake_qgis: ModuleType) -> None:
    helpers.save_config(config.PluginConfig(api_key="k"))
    keys = set(fake_qgis.QgsSettings._store)
    assert keys == {
        "AgriCarbonAtlas/api_base_url",
        "AgriCarbonAtlas/api_key",
        "AgriCarbonAtlas/default_country",
        "AgriCarbonAtlas/timeout_s",
    }


def test_damaged_stored_settings_fall_back_to_defaults(
    helpers: ModuleType, fake_qgis: ModuleType
) -> None:
    store = fake_qgis.QgsSettings()
    store.setValue("AgriCarbonAtlas/api_base_url", "ftp://nope")
    store.setValue("AgriCarbonAtlas/api_key", "bad\nkey")
    store.setValue("AgriCarbonAtlas/default_country", "ZZ")
    store.setValue("AgriCarbonAtlas/timeout_s", "not a number")
    assert helpers.load_config() == config.PluginConfig()


def test_one_damaged_setting_does_not_discard_the_others(
    helpers: ModuleType, fake_qgis: ModuleType
) -> None:
    """A hand-edited timeout makes PyQt raise TypeError; the other values must survive."""
    store = fake_qgis.QgsSettings()
    store.setValue("AgriCarbonAtlas/api_base_url", "https://atlas.example.org/api/v1")
    store.setValue("AgriCarbonAtlas/api_key", "key-1")
    store.setValue("AgriCarbonAtlas/default_country", "DE")
    store.setValue("AgriCarbonAtlas/timeout_s", "thirty")
    with pytest.raises(TypeError):  # the fake converts like PyQt: this is what load_config meets
        store.value("AgriCarbonAtlas/timeout_s", 30.0, type=float)
    assert helpers.load_config() == config.PluginConfig(
        "https://atlas.example.org/api/v1", "key-1", "DE", config.DEFAULT_TIMEOUT_S
    )


# --------------------------------------------------------------------------- project state
PLOT = {
    "plot_id": "plot_abc123",
    "name": "North field",
    "country": "IN",
    "area_hectares": 4.2,
    "geometry_sha256": "ab" * 32,
    "geometry": {"type": "Polygon", "coordinates": [[[77.5, 13.2], [77.6, 13.2], [77.5, 13.3]]]},
    "centroid": {"lon": 77.55, "lat": 13.23},
    "analysis": {"anything": 1},
}


def test_no_plot_is_linked_by_default(helpers: ModuleType) -> None:
    assert helpers.read_current_plot() is None


def test_the_project_stores_only_non_spatial_fields(
    helpers: ModuleType, fake_qgis: ModuleType
) -> None:
    helpers.write_current_plot(PLOT)
    text, found = fake_qgis.QgsProject.instance().readEntry("AgriCarbonAtlas", "current_plot", "")
    assert found
    for forbidden in ("coordinates", 'geometry"', "centroid", "77.5", "13.2", "analysis"):
        assert forbidden not in text, forbidden
    assert helpers.read_current_plot() == {
        "plot_id": "plot_abc123",
        "name": "North field",
        "country": "IN",
        "area_hectares": 4.2,
        "geometry_sha256": "ab" * 32,
    }


def test_missing_values_are_not_stored(helpers: ModuleType) -> None:
    helpers.write_current_plot({"plot_id": "p1", "name": None, "area_hectares": None})
    assert helpers.read_current_plot() == {"plot_id": "p1"}


def test_unlinking_removes_the_entry(helpers: ModuleType) -> None:
    helpers.write_current_plot(PLOT)
    helpers.write_current_plot(None)
    assert helpers.read_current_plot() is None


@pytest.mark.parametrize(
    "stored",
    ["", "not json", "[]", '"text"', "{}", '{"plot_id": ""}', '{"plot_id": 5}', '{"name": "x"}'],
)
def test_damaged_project_entries_mean_no_plot(
    helpers: ModuleType, fake_qgis: ModuleType, stored: str
) -> None:
    fake_qgis.QgsProject.instance().writeEntry("AgriCarbonAtlas", "current_plot", stored)
    assert helpers.read_current_plot() is None


# --------------------------------------------------------------------------- finding the field
def test_polygon_layers_are_recognised(helpers: ModuleType, build: LayerBuilder) -> None:
    assert helpers.is_polygon_layer(build.layer("fields"))
    assert not helpers.is_polygon_layer(build.layer("trees", kind="Point"))
    assert not helpers.is_polygon_layer(build.layer("roads", kind="LineString"))
    assert not helpers.is_polygon_layer(None)
    assert not helpers.is_polygon_layer("a string")


def test_the_active_layer_wins_when_it_has_a_selection(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    first, second = build.layer("first"), build.layer("second")
    select(first, build.polygon(first, SQUARE))
    select(second, build.polygon(second, SQUARE))
    assert helpers.find_field_layer(second) is second
    assert helpers.find_field_layer(first) is first


def test_the_only_layer_with_a_selection_is_used(helpers: ModuleType, build: LayerBuilder) -> None:
    fields, other = build.layer("fields"), build.layer("other")
    points = build.layer("points", kind="Point")
    select(fields, build.polygon(fields, SQUARE))
    build.polygon(other, SQUARE)  # nothing selected
    select(points, build.point(points, 77.51, 13.21))  # selected, but not a polygon layer
    assert helpers.find_field_layer(None) is fields
    assert helpers.find_field_layer(other) is fields  # active layer has no selection
    assert helpers.find_field_layer(points) is fields


def test_no_selection_gives_advice(helpers: ModuleType, build: LayerBuilder) -> None:
    build.polygon(build.layer("fields"), SQUARE)
    with pytest.raises(helpers.HelperError, match="Select one field polygon"):
        helpers.find_field_layer(None)


def test_selections_in_several_layers_are_ambiguous(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    first, second = build.layer("first"), build.layer("second")
    select(first, build.polygon(first, SQUARE))
    select(second, build.polygon(second, SQUARE))
    with pytest.raises(helpers.HelperError, match="several polygon layers") as caught:
        helpers.find_field_layer(None)
    assert "'first'" in str(caught.value) and "'second'" in str(caught.value)


def test_exactly_one_selected_feature_is_required(helpers: ModuleType, build: LayerBuilder) -> None:
    layer = build.layer("fields")
    one = build.polygon(layer, SQUARE)
    two = build.polygon(layer, HOLE)
    with pytest.raises(helpers.HelperError, match="Select one field polygon in layer 'fields'"):
        helpers.selected_field_feature(layer)
    select(layer, one, two)
    with pytest.raises(helpers.HelperError, match="2 features are selected"):
        helpers.selected_field_feature(layer)
    select(layer, two)
    assert helpers.selected_field_feature(layer).id() == two.id()


def test_selected_feature_needs_a_polygon_layer(helpers: ModuleType, build: LayerBuilder) -> None:
    with pytest.raises(helpers.HelperError, match="polygon layer"):
        helpers.selected_field_feature(None)
    points = build.layer("points", kind="Point")
    select(points, build.point(points, 1, 1))
    with pytest.raises(helpers.HelperError, match="does not contain polygons"):
        helpers.selected_field_feature(points)


# --------------------------------------------------------------------------- field -> GeoJSON
def field_geojson(helpers: ModuleType, layer: Any) -> dict[str, Any]:
    return helpers.feature_to_wgs84_polygon(layer.selectedFeatures()[0], layer.crs())


def test_a_wgs84_field_becomes_a_geojson_polygon(helpers: ModuleType, build: LayerBuilder) -> None:
    layer = build.layer("fields")
    select(layer, build.polygon(layer, [*SQUARE, SQUARE[0]]))
    result = field_geojson(helpers, layer)
    assert result["type"] == "Polygon"
    assert result["coordinates"][0][0] == [77.5, 13.2]
    assert result["coordinates"][0][0] == result["coordinates"][0][-1]  # closed


def test_an_unclosed_qgis_ring_is_closed_for_geojson(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    layer = build.layer("fields")
    select(layer, build.polygon(layer, SQUARE))  # no closing vertex
    ring = field_geojson(helpers, layer)["coordinates"][0]
    assert len(ring) == 5 and ring[0] == ring[-1]


def test_a_web_mercator_field_is_reprojected_to_wgs84(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    layer = build.layer("fields", crs="EPSG:3857")
    ring = [mercator(lon, lat) for lon, lat in SQUARE]
    select(layer, build.polygon(layer, ring))
    result = field_geojson(helpers, layer)
    for (lon, lat), (got_lon, got_lat) in zip(SQUARE, result["coordinates"][0]):
        assert got_lon == pytest.approx(lon, abs=1e-6)
        assert got_lat == pytest.approx(lat, abs=1e-6)


def test_holes_survive_the_conversion(helpers: ModuleType, build: LayerBuilder) -> None:
    layer = build.layer("fields")
    select(layer, build.polygon(layer, SQUARE, HOLE))
    assert len(field_geojson(helpers, layer)["coordinates"]) == 2


def test_a_single_part_multipolygon_is_accepted(helpers: ModuleType, build: LayerBuilder) -> None:
    layer = build.layer("fields")
    select(layer, build.multipolygon(layer, [SQUARE]))
    assert field_geojson(helpers, layer)["type"] == "Polygon"


def test_a_multi_part_field_is_refused_with_advice(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    layer = build.layer("fields")
    other = [(77.6, 13.3), (77.62, 13.3), (77.62, 13.32), (77.6, 13.32)]
    select(layer, build.multipolygon(layer, [SQUARE], [other]))
    with pytest.raises(GeometryError, match="Multipart to Singleparts"):
        field_geojson(helpers, layer)


def test_a_layer_without_a_crs_is_refused(
    helpers: ModuleType, build: LayerBuilder, fake_qgis: ModuleType
) -> None:
    layer = build.layer("fields")
    select(layer, build.polygon(layer, SQUARE))
    with pytest.raises(helpers.HelperError, match="no valid coordinate reference system"):
        helpers.feature_to_wgs84_polygon(
            layer.selectedFeatures()[0], fake_qgis.QgsCoordinateReferenceSystem("")
        )


def test_a_failed_transformation_is_reported_in_plain_words(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    layer = build.layer("fields", crs="EPSG:32643")  # the fake has no such transform
    select(
        layer, build.polygon(layer, [(500000.0, 1450000.0), (500100.0, 1450000.0), (500, 1.4e6)])
    )
    with pytest.raises(helpers.HelperError, match="could not be transformed"):
        field_geojson(helpers, layer)


def test_features_without_usable_geometry_are_refused(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    layer = build.layer("fields")
    select(layer, build.empty(layer))
    with pytest.raises(helpers.HelperError, match="no geometry"):
        field_geojson(helpers, layer)
    points = build.layer("points", kind="Point")
    feature = build.point(points, 77.5, 13.2)
    with pytest.raises(helpers.HelperError, match="not a polygon"):
        helpers.feature_to_wgs84_polygon(feature, points.crs())


def test_coordinates_outside_the_valid_range_suggest_checking_the_crs(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    layer = build.layer("fields")  # declared as EPSG:4326 but the numbers are metres
    ring = [(500000.0, 1450000.0), (500100.0, 1450000.0), (500100.0, 1450100.0)]
    select(layer, build.polygon(layer, ring))
    with pytest.raises(GeometryError, match="CRS"):
        field_geojson(helpers, layer)


# --------------------------------------------------------------------------- confidence helpers
def test_numeric_fields_and_the_suggested_confidence_field(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    layer = build.layer(
        "crowns", fields=("id:integer", "label:string", "Score:double", "area:double")
    )
    assert helpers.numeric_field_names(layer) == ["id", "Score", "area"]
    assert helpers.suggest_confidence_field(layer) == "Score"
    assert helpers.suggest_confidence_field(build.layer("plain", fields=("label:string",))) is None


def test_value_range_of_a_field(helpers: ModuleType, build: LayerBuilder) -> None:
    layer = build.layer("crowns", kind="Point", fields=("score:double", "empty:double"))
    for value in (0.2, 0.9, 0.55):
        build.point(layer, 77.5, 13.2, [value, None])
    assert helpers.field_value_range(layer, "score") == (0.2, 0.9)
    assert helpers.field_value_range(layer, "empty") is None  # only NULL values
    assert helpers.field_value_range(layer, "missing") is None
    assert helpers.field_value_range(layer, None) is None
    assert helpers.field_value_range(layer, "") is None


def test_value_range_survives_a_provider_without_statistics(
    helpers: ModuleType, build: LayerBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    layer = build.layer("crowns", kind="Point", fields=("score:double",))

    def broken(_index: int) -> Any:
        raise RuntimeError("no statistics")

    monkeypatch.setattr(layer, "minimumValue", broken)
    assert helpers.field_value_range(layer, "score") is None


# --------------------------------------------------------------------------- counting crowns
def crown_scene(
    build: LayerBuilder,
    field_crs: str,
    crown_crs: str,
    crown_kind: str,
    seed: int = 7,
    with_hole: bool = True,
) -> tuple[Any, Any, list[tuple[float, float]], list[list[tuple[float, float]]]]:
    """A field (with a hole) and 600 random crowns; returns the layers, the crown centroids in
    the crown CRS and the field rings in the crown CRS (the independent oracle)."""
    rng = random.Random(seed)
    to_crs = {"EPSG:4326": lambda lon, lat: (lon, lat), "EPSG:3857": mercator}
    rings_lonlat = [SQUARE] + ([HOLE] if with_hole else [])

    field_layer = build.layer("fields", crs=field_crs)
    field_rings = [[to_crs[field_crs](*p) for p in ring] for ring in rings_lonlat]
    select(field_layer, build.polygon(field_layer, *field_rings))

    crown_layer = build.layer("crowns", kind=crown_kind, crs=crown_crs, fields=("score:double",))
    centroids: list[tuple[float, float]] = []
    for _ in range(600):
        lon = rng.uniform(77.495, 77.525)
        lat = rng.uniform(13.195, 13.225)
        x, y = to_crs[crown_crs](lon, lat)
        centroids.append((x, y))
        score = rng.random()
        if crown_kind == "Point":
            build.point(crown_layer, x, y, [score])
        else:
            half = 1.0 if crown_crs == "EPSG:3857" else 0.00001  # a few metres wide
            square = [(x - half, y - half), (x + half, y - half), (x + half, y + half)]
            square.append((x - half, y + half))
            build.polygon(crown_layer, square, attributes=[score])
    oracle = [[to_crs[crown_crs](*p) for p in ring] for ring in rings_lonlat]
    return field_layer, crown_layer, centroids, oracle


@pytest.mark.parametrize("crown_kind", ["Polygon", "Point"])
@pytest.mark.parametrize(
    ("field_crs", "crown_crs"),
    [
        ("EPSG:4326", "EPSG:4326"),
        ("EPSG:3857", "EPSG:4326"),
        ("EPSG:4326", "EPSG:3857"),
        ("EPSG:3857", "EPSG:3857"),
    ],
)
def test_the_count_matches_a_brute_force_check(
    helpers: ModuleType, build: LayerBuilder, field_crs: str, crown_crs: str, crown_kind: str
) -> None:
    field_layer, crown_layer, centroids, oracle = crown_scene(
        build, field_crs, crown_crs, crown_kind
    )
    expected = sum(1 for x, y in centroids if crowns.point_in_polygon(x, y, oracle))
    assert 0 < expected < len(centroids)  # the scene is not trivial
    result = helpers.count_crowns_in_field(field_layer, crown_layer, None, None)
    assert result.counted == expected
    assert result.inside == expected
    assert result.threshold is None


def test_a_hole_is_not_counted(helpers: ModuleType, build: LayerBuilder) -> None:
    with_hole = crown_scene(build, "EPSG:4326", "EPSG:4326", "Point", with_hole=True)
    solid = crown_scene(build, "EPSG:4326", "EPSG:4326", "Point", with_hole=False)
    holed_count = helpers.count_crowns_in_field(with_hole[0], with_hole[1], None, None).counted
    solid_count = helpers.count_crowns_in_field(solid[0], solid[1], None, None).counted
    assert holed_count < solid_count


def test_the_confidence_threshold_filters_crowns(helpers: ModuleType, build: LayerBuilder) -> None:
    field_layer, crown_layer, centroids, oracle = crown_scene(
        build, "EPSG:3857", "EPSG:4326", "Polygon"
    )
    scores = [feature["score"] for feature in crown_layer.getFeatures()]
    inside = [
        score for (x, y), score in zip(centroids, scores) if crowns.point_in_polygon(x, y, oracle)
    ]
    result = helpers.count_crowns_in_field(field_layer, crown_layer, "score", 0.5)
    assert result.counted == sum(1 for score in inside if score >= 0.5)
    assert result.below_threshold == sum(1 for score in inside if score < 0.5)
    assert result.counted + result.below_threshold == len(inside)
    assert result.missing_confidence == 0
    assert result.threshold == 0.5


def test_the_threshold_is_ignored_without_a_confidence_field(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    field_layer, crown_layer, _centroids, _oracle = crown_scene(
        build, "EPSG:4326", "EPSG:4326", "Point"
    )
    unfiltered = helpers.count_crowns_in_field(field_layer, crown_layer, None, None)
    ignored = helpers.count_crowns_in_field(field_layer, crown_layer, None, 0.9)
    assert ignored == unfiltered
    assert ignored.threshold is None


def test_crowns_without_a_confidence_value_are_excluded_and_reported(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    field_layer = build.layer("fields")
    select(field_layer, build.polygon(field_layer, SQUARE))
    crown_layer = build.layer("crowns", kind="Point", fields=("score:double",))
    build.point(crown_layer, 77.51, 13.21, [0.9])  # counted
    build.point(crown_layer, 77.51, 13.211, [0.1])  # below the threshold
    build.point(crown_layer, 77.511, 13.21, [None])  # empty value
    build.point(crown_layer, 77.512, 13.21)  # QGIS NULL: float(NULL) raises TypeError
    build.point(crown_layer, 78.0, 14.0, [0.99])  # outside the field
    result = helpers.count_crowns_in_field(field_layer, crown_layer, "score", 0.5)
    assert (result.counted, result.below_threshold, result.missing_confidence) == (1, 1, 2)
    assert (result.examined, result.inside, result.outside) == (4, 4, 0)  # outside is filtered out


def test_features_without_geometry_are_reported_as_invalid(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    field_layer = build.layer("fields")
    select(field_layer, build.polygon(field_layer, SQUARE))
    crown_layer = build.layer("crowns", kind="Point")
    build.point(crown_layer, 77.51, 13.21)
    build.empty(crown_layer)
    result = helpers.count_crowns_in_field(field_layer, crown_layer, None, None)
    assert (result.counted, result.invalid) == (1, 1)


def test_only_the_confidence_attribute_and_nearby_features_are_requested(
    helpers: ModuleType, build: LayerBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    field_layer, crown_layer, _centroids, _oracle = crown_scene(
        build, "EPSG:4326", "EPSG:4326", "Point"
    )
    requests: list[Any] = []
    original = crown_layer.getFeatures

    def spy(request: Any = None) -> Any:
        requests.append(request)
        return original(request)

    monkeypatch.setattr(crown_layer, "getFeatures", spy)

    helpers.count_crowns_in_field(field_layer, crown_layer, "score", 0.5)
    helpers.count_crowns_in_field(field_layer, crown_layer, None, None)

    with_score, without = requests
    assert with_score.attributes == ["score"]
    assert without.attributes == []  # no attribute is read when no confidence is used
    rect = with_score.rect
    assert (rect.xmin, rect.ymin, rect.xmax, rect.ymax) == (77.5, 13.2, 77.52, 13.22)


def test_far_away_crowns_are_not_even_examined(helpers: ModuleType, build: LayerBuilder) -> None:
    field_layer = build.layer("fields")
    select(field_layer, build.polygon(field_layer, SQUARE))
    crown_layer = build.layer("crowns", kind="Point")
    for i in range(50):
        build.point(crown_layer, 10.0 + i * 0.01, 50.0)
    build.point(crown_layer, 77.51, 13.21)
    result = helpers.count_crowns_in_field(field_layer, crown_layer, None, None)
    assert result.examined == 1 and result.counted == 1


def test_counting_needs_a_valid_crown_layer(helpers: ModuleType, build: LayerBuilder) -> None:
    field_layer = build.layer("fields")
    select(field_layer, build.polygon(field_layer, SQUARE))
    with pytest.raises(helpers.HelperError, match="layer that holds the detected tree crowns"):
        helpers.count_crowns_in_field(field_layer, None, None, None)
    lines = build.layer("roads", kind="LineString")
    with pytest.raises(helpers.HelperError, match="polygons or points"):
        helpers.count_crowns_in_field(field_layer, lines, None, None)
    crown_layer = build.layer("crowns", kind="Point", fields=("score:double",))
    with pytest.raises(helpers.HelperError, match="no field called 'confidence'"):
        helpers.count_crowns_in_field(field_layer, crown_layer, "confidence", 0.5)


def test_counting_needs_one_selected_field(helpers: ModuleType, build: LayerBuilder) -> None:
    field_layer = build.layer("fields")
    build.polygon(field_layer, SQUARE)  # nothing selected
    crown_layer = build.layer("crowns", kind="Point")
    with pytest.raises(helpers.HelperError, match="Select one field polygon"):
        helpers.count_crowns_in_field(field_layer, crown_layer, None, None)


def test_counting_a_multi_part_field_counts_every_part(
    helpers: ModuleType, build: LayerBuilder
) -> None:
    field_layer = build.layer("fields")
    other = [(77.6, 13.3), (77.62, 13.3), (77.62, 13.32), (77.6, 13.32)]
    select(field_layer, build.multipolygon(field_layer, [SQUARE], [other]))
    crown_layer = build.layer("crowns", kind="Point")
    build.point(crown_layer, 77.51, 13.21)
    build.point(crown_layer, 77.61, 13.31)
    build.point(crown_layer, 77.56, 13.26)  # between the parts
    assert helpers.count_crowns_in_field(field_layer, crown_layer, None, None).counted == 2


# --------------------------------------------------------------------------- plot layer
API_PLOT = {
    "plot_id": "plot_xyz",
    "name": "South field",
    "country": "DE",
    "area_hectares": 3.5,
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[8.0, 50.0], [8.01, 50.0], [8.01, 50.01], [8.0, 50.0]]],
    },
}


def test_the_plot_is_added_as_a_memory_layer(helpers: ModuleType, fake_qgis: ModuleType) -> None:
    layer = helpers.add_plot_layer(API_PLOT)
    assert layer.name() == "AgriCarbon plot plot_xyz"
    assert layer.crs().authid() == "EPSG:4326"
    assert layer.id() in fake_qgis.QgsProject.instance().mapLayers()
    (feature,) = list(layer.getFeatures())
    assert [feature[name] for name in ("plot_id", "name", "country", "area_ha")] == [
        "plot_xyz",
        "South field",
        "DE",
        3.5,
    ]
    assert feature.geometry().asPolygon()[0][1].x() == 8.01


def test_the_plot_layer_tolerates_missing_attributes(helpers: ModuleType) -> None:
    plot = {"geometry": API_PLOT["geometry"]}
    layer = helpers.add_plot_layer(plot)
    assert layer.name() == "AgriCarbon plot plot"
    (feature,) = list(layer.getFeatures())
    assert feature["name"] == "" and feature["area_ha"] is None


def test_a_plot_without_a_usable_geometry_is_refused(helpers: ModuleType) -> None:
    with pytest.raises(GeometryError):
        helpers.add_plot_layer({"plot_id": "p", "name": "public view"})  # no geometry


# --------------------------------------------------------------------------- QGIS log panel
@pytest.fixture
def plugin_logger() -> Any:
    logger = logging.getLogger("agricarbon_atlas_qgis")
    level, handlers = logger.level, list(logger.handlers)
    yield logger
    logger.setLevel(level)
    logger.handlers[:] = handlers


def test_log_records_reach_the_qgis_log_panel(
    helpers: ModuleType, fake_qgis: ModuleType, plugin_logger: Any
) -> None:
    handler = helpers.install_log_handler()
    child = logging.getLogger("agricarbon_atlas_qgis.api_client")
    child.info("GET /plots/p1 -> 200 (12 ms)")
    child.warning("slow")
    child.error("broken")
    child.debug("hidden")
    helpers.remove_log_handler(handler)
    child.info("after removal")
    assert fake_qgis.QgsMessageLog.messages == [
        ("GET /plots/p1 -> 200 (12 ms)", "AgriCarbon Atlas", helpers.LEVEL_INFO),
        ("slow", "AgriCarbon Atlas", helpers.LEVEL_WARNING),
        ("broken", "AgriCarbon Atlas", helpers.LEVEL_CRITICAL),
    ]


def test_the_log_handler_never_raises(
    helpers: ModuleType, fake_qgis: ModuleType, plugin_logger: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    helpers.install_log_handler()

    def explode(*_args: Any) -> None:
        raise RuntimeError("log panel unavailable")

    monkeypatch.setattr(fake_qgis.QgsMessageLog, "logMessage", staticmethod(explode))
    logging.getLogger("agricarbon_atlas_qgis.x").error("still fine")


def test_the_log_handler_supports_a_log_function_without_the_notify_argument(
    helpers: ModuleType, fake_qgis: ModuleType, plugin_logger: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[Any, ...]] = []

    def three_arguments(message: str, tag: str, level: int) -> None:
        seen.append((message, tag, level))

    monkeypatch.setattr(fake_qgis.QgsMessageLog, "logMessage", staticmethod(three_arguments))
    helpers.install_log_handler()
    logging.getLogger("agricarbon_atlas_qgis.x").warning("old QGIS")
    assert seen == [("old QGIS", "AgriCarbon Atlas", helpers.LEVEL_WARNING)]


# --------------------------------------------------------------------------- background tasks
def test_a_task_delivers_its_result_on_finish(tasks: ModuleType, fake_qgis: ModuleType) -> None:
    got: list[Any] = []
    task = tasks.submit("work", lambda: {"ok": 1}, got.append, lambda exc: got.append(exc))
    assert tasks.active_count() == 1 and got == []
    assert task.description() == "work"
    assert fake_qgis.QgsApplication.taskManager().run_all() == 1
    assert got == [{"ok": 1}]
    assert tasks.active_count() == 0


def test_a_failing_task_reports_the_error(tasks: ModuleType, fake_qgis: ModuleType) -> None:
    problem = ValueError("boom")
    successes: list[Any] = []
    errors: list[BaseException] = []

    def work() -> None:
        raise problem

    tasks.submit("failing", work, successes.append, errors.append)
    fake_qgis.QgsApplication.taskManager().run_all()
    assert errors == [problem] and successes == []
    assert tasks.active_count() == 0


def test_a_task_that_was_stopped_reports_an_error(tasks: ModuleType) -> None:
    errors: list[BaseException] = []
    task = tasks.ApiTask("stopped", lambda: 1, lambda _r: None, errors.append)
    task.finished(False)
    assert len(errors) == 1 and "stopped before it finished" in str(errors[0])


def test_a_task_works_when_qgis_has_no_flags_argument(
    tasks: ModuleType, fake_qgis: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr(fake_qgis.QgsTask, "Flags")
    task = tasks.ApiTask("older build", lambda: 1, lambda _r: None, lambda _e: None)
    assert task.description() == "older build"


def test_a_failing_callback_is_logged_without_its_message(
    tasks: ModuleType, fake_qgis: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    def show(_result: Any) -> None:
        raise RuntimeError("secret field data 77.5123,13.2456")

    with caplog.at_level(logging.INFO, logger="agricarbon_atlas_qgis"):
        tasks.submit("show result", lambda: 1, show, lambda _e: None)
        fake_qgis.QgsApplication.taskManager().run_all()
    text = caplog.text
    assert "RuntimeError" in text and "show result" in text
    assert "secret" not in text and "77.5123" not in text
    assert "Traceback" not in text
    assert tasks.active_count() == 0


def test_the_task_log_line_has_only_the_description(
    tasks: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="agricarbon_atlas_qgis"):
        tasks.submit("AgriCarbon Atlas: estimating carbon", lambda: 1, print, print)
    assert "started task: AgriCarbon Atlas: estimating carbon" in caplog.text


def test_tasks_stay_referenced_until_they_finish(tasks: ModuleType, fake_qgis: ModuleType) -> None:
    for i in range(3):
        tasks.submit(f"task {i}", lambda: 1, lambda _r: None, lambda _e: None)
    assert tasks.active_count() == 3
    fake_qgis.QgsApplication.taskManager().run_all()
    assert tasks.active_count() == 0


# --------------------------------------------------------------------------- diagnostics
def _inner() -> None:
    raise ValueError("secret 77.5123,13.2456")


def _outer() -> None:
    _inner()


def test_exception_summary_names_the_type_and_the_place_but_not_the_message() -> None:
    with pytest.raises(ValueError) as caught:
        _outer()
    text = exception_summary(caught.value)
    assert text.startswith("ValueError (")
    assert "test_qgis_helpers_logic.py" in text and "_inner" in text and "_outer" in text
    assert "secret" not in text and "77.5123" not in text


def test_exception_summary_of_an_exception_that_was_never_raised() -> None:
    assert exception_summary(KeyError("x")) == "KeyError (no frame)"
