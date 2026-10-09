"""Satellite tree-cover detection on a vegetation cube (geo_engine.detection)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon, shape

from geo_engine.construct import geodesic_area_m2
from geo_engine.cube.demo import build_demo_cube
from geo_engine.cube.grid import build_grid
from geo_engine.detection import (
    ConfigError,
    DetectionError,
    TreeCoverParams,
    composite_median,
    connected_patches,
    detect_tree_cover,
    find_config_file,
    heuristic_confidence,
    load_detection_config,
)
from geo_engine.detection.tree_cover import _polygonal_part

ROOT = Path(__file__).resolve().parents[3]
PLOT_RING = [(77.5000, 13.0000), (77.5030, 13.0000), (77.5030, 13.0030), (77.5000, 13.0030)]
PLOT = Polygon([*PLOT_RING, PLOT_RING[0]])
TIMES = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
LOW, HIGH = 0.35, 0.8


def geometry_of(polygon: Polygon) -> dict:
    return json.loads(json.dumps(polygon.__geo_interface__))


def make_cube(
    layers: list[np.ndarray] | None = None,
    polygon: Polygon = PLOT,
    times: list[str] | None = None,
    index: str = "ndvi",
    mode: str = "demo",
    source: str = "synthetic-demo",
    base: float = LOW,
) -> tuple[dict, int, int]:
    """A cube dict (the ``GET /plots/{id}/cube`` shape) with the given monthly layers."""
    grid, mask = build_grid(polygon, 30)
    times = times or TIMES
    if layers is None:
        layers = [np.full((grid.rows, grid.cols), base) for _ in times]
    values = []
    for layer in layers:
        layer = np.where(mask.astype(bool), layer, np.nan)
        values.append([[None if np.isnan(v) else float(v) for v in row] for row in layer])
    cube = {
        "plot_id": "PLT-TEST",
        "index": index,
        "mode": mode,
        "grid": grid.to_dict(),
        "times": times,
        "mask": mask.astype(int).tolist(),
        "values": values,
        "provenance": {"source": source},
    }
    return cube, grid.rows, grid.cols


def flat(rows: int, cols: int, value: float = LOW) -> np.ndarray:
    return np.full((rows, cols), value, dtype=float)


def with_block(layer: np.ndarray, rows: slice, cols: slice, value: float = HIGH) -> np.ndarray:
    out = layer.copy()
    out[rows, cols] = value
    return out


def stack(layer: np.ndarray, count: int = len(TIMES)) -> list[np.ndarray]:
    return [layer.copy() for _ in range(count)]


# ---------------------------------------------------------------------------- patches
def test_two_separate_blocks_make_two_patches_largest_first():
    _, rows, cols = make_cube()
    layer = with_block(flat(rows, cols), slice(1, 4), slice(1, 4))  # 3 x 3 = 9 cells
    layer = with_block(layer, slice(6, 8), slice(6, 9))  # 2 x 3 = 6 cells
    cube, _, _ = make_cube(stack(layer))
    result = detect_tree_cover(cube, geometry_of(PLOT))
    assert result.patches == 2
    first, second = (f["properties"] for f in result.features)
    assert (first["id"], second["id"]) == ("P1", "P2")
    assert (first["cells"], second["cells"]) == (9, 6)
    assert first["area_m2"] == pytest.approx(9 * 900, rel=0.03)
    assert second["area_m2"] == pytest.approx(6 * 900, rel=0.03)
    assert first["label"] == "tree cover"
    assert first["mean_ndvi"] == pytest.approx(HIGH, abs=1e-3)
    data = result.to_dict()
    assert data["index"] == "ndvi" and data["month"] == TIMES[-1]
    assert data["summary"]["patches"] == 2
    assert data["features"]["type"] == "FeatureCollection"


def test_patch_polygons_are_valid_and_inside_the_plot():
    _, rows, cols = make_cube()
    cube, _, _ = make_cube(stack(with_block(flat(rows, cols), slice(0, rows), slice(0, cols))))
    result = detect_tree_cover(cube, geometry_of(PLOT))
    assert result.patches == 1
    patch = shape(result.features[0]["geometry"])
    assert patch.is_valid and PLOT.buffer(1e-9).contains(patch)
    assert result.features[0]["geometry"]["type"] == "Polygon"
    # ring orientation follows RFC 7946: exterior counter-clockwise
    assert patch.exterior.is_ccw
    assert result.covered_fraction > 0.9
    assert result.area_hectares * 10_000 == pytest.approx(
        result.features[0]["properties"]["area_m2"], rel=0.01
    )


def test_diagonal_neighbours_belong_to_one_patch():
    _, rows, cols = make_cube()
    layer = flat(rows, cols)
    layer[2, 2] = layer[3, 3] = HIGH
    cube, _, _ = make_cube(stack(layer))
    result = detect_tree_cover(cube, geometry_of(PLOT))
    assert result.patches == 1  # 8-connected: two singletons would both be dropped
    assert result.features[0]["properties"]["cells"] == 2
    # two squares that only touch at a corner are drawn as a MultiPolygon, still one patch
    assert result.features[0]["geometry"]["type"] == "MultiPolygon"
    assert shape(result.features[0]["geometry"]).is_valid
    assert result.features[0]["properties"]["area_m2"] == pytest.approx(2 * 900, rel=0.05)


def test_a_single_cell_is_dropped_unless_min_patch_cells_allows_it():
    _, rows, cols = make_cube()
    layer = flat(rows, cols)
    layer[4, 4] = 0.95
    cube, _, _ = make_cube(stack(layer))
    default = detect_tree_cover(cube, geometry_of(PLOT))
    assert default.patches == 0
    assert default.parameters["dropped_patches"] == {"too_small": 1, "low_confidence": 0}
    kept = detect_tree_cover(cube, geometry_of(PLOT), min_patch_cells=1)
    assert kept.patches == 1 and kept.parameters["min_patch_cells"] == 1


def test_threshold_override_changes_the_cells_and_is_reported():
    _, rows, cols = make_cube()
    layer = with_block(flat(rows, cols, 0.55), slice(2, 6), slice(2, 6), 0.7)
    cube, _, _ = make_cube(stack(layer))
    default = detect_tree_cover(cube, geometry_of(PLOT))  # threshold 0.6 from config
    assert default.threshold == 0.6 and default.patches == 1
    assert default.features[0]["properties"]["cells"] == 16
    lenient = detect_tree_cover(cube, geometry_of(PLOT), threshold=0.5, min_confidence=0.0)
    assert lenient.threshold == 0.5 and lenient.features[0]["properties"]["cells"] > 16
    strict = detect_tree_cover(cube, geometry_of(PLOT), threshold=0.75)
    assert strict.patches == 0


def test_a_cell_exactly_at_the_threshold_counts():
    _, rows, cols = make_cube()
    layer = with_block(flat(rows, cols), slice(2, 5), slice(2, 5), 0.6)
    cube, _, _ = make_cube(stack(layer))
    assert detect_tree_cover(cube, geometry_of(PLOT), min_confidence=0.0).patches == 1


# ---------------------------------------------------------------------------- composite
def test_composite_is_the_median_of_the_last_three_slices_ignoring_nulls():
    values = np.full((5, 1, 4), 0.1)
    values[2:, 0, 0] = [0.9, 0.9, 0.1]  # outlier month ignored by the median
    values[2:, 0, 1] = [0.9, 0.7, np.nan]  # null ignored: median of 0.9, 0.7
    values[2:, 0, 2] = [np.nan, np.nan, np.nan]  # no data at all
    values[0:2, 0, 3] = 0.99  # old months do not matter
    values[2:, 0, 3] = 0.2
    mask = np.ones((1, 4), dtype=bool)
    composite, last = composite_median(values, mask, 3)
    assert composite[0, 0] == pytest.approx(0.9)
    assert composite[0, 1] == pytest.approx(0.8)
    assert np.isnan(composite[0, 2])
    assert composite[0, 3] == pytest.approx(0.2)
    assert last.shape[0] == 3
    outside = np.array([[True, False, True, True]])
    assert np.isnan(composite_median(values, outside, 3)[0][0, 1])


def test_only_the_last_three_months_decide():
    _, rows, cols = make_cube()
    high = with_block(flat(rows, cols), slice(1, 5), slice(1, 5))
    low = flat(rows, cols)
    old_high = detect_tree_cover(make_cube([high, high, high, low, low, low])[0], geometry_of(PLOT))
    assert old_high.patches == 0
    recent_high = detect_tree_cover(
        make_cube([low, low, low, high, high, high])[0], geometry_of(PLOT)
    )
    assert recent_high.patches == 1
    # one good month out of three is not enough, two are
    one = detect_tree_cover(make_cube([low, low, low, high, low, low])[0], geometry_of(PLOT))
    two = detect_tree_cover(make_cube([low, low, low, high, high, low])[0], geometry_of(PLOT))
    assert one.patches == 0 and two.patches == 1


def test_cloud_masked_cells_are_ignored_not_treated_as_low():
    _, rows, cols = make_cube()
    high = with_block(flat(rows, cols), slice(1, 5), slice(1, 5))
    cloudy = high.copy()
    cloudy[1:3, 1:5] = np.nan  # clouds in the last month: median of the two clear months
    cube, _, _ = make_cube([high, high, high, high, high, cloudy])
    result = detect_tree_cover(cube, geometry_of(PLOT))
    assert result.patches == 1 and result.features[0]["properties"]["cells"] == 16
    assert result.parameters["valid_cell_share"] == 1.0


def test_fewer_than_three_slices_are_used_with_a_note():
    _, rows, cols = make_cube()
    high = with_block(flat(rows, cols), slice(1, 5), slice(1, 5))
    cube, _, _ = make_cube([high, high], times=TIMES[:2])
    result = detect_tree_cover(cube, geometry_of(PLOT))
    assert result.patches == 1
    assert result.parameters["composite_slices"] == 2
    assert result.parameters["composite_months"] == TIMES[:2]
    assert any("Only 2 monthly slices" in n for n in result.limitations)
    one, _, _ = make_cube([high], times=TIMES[:1])
    assert any(
        "Only 1 monthly slice was" in n
        for n in detect_tree_cover(one, geometry_of(PLOT)).limitations
    )


def test_no_data_at_all_gives_no_patches_and_says_why():
    _, rows, cols = make_cube()
    cube, _, _ = make_cube(stack(flat(rows, cols, np.nan)))
    result = detect_tree_cover(cube, geometry_of(PLOT))
    assert result.patches == 0 and result.area_hectares == 0.0 and result.covered_fraction == 0.0
    assert result.parameters["valid_cell_share"] == 0.0
    assert any("usable satellite value" in n for n in result.limitations)


# ---------------------------------------------------------------------------- confidence
def test_confidence_formula():
    params = TreeCoverParams.from_config()
    thr, ceiling = params.threshold, params.confidence_ndvi_ceiling
    reliable = params.confidence_reliable_cells
    # NDVI at the threshold, a reliable patch, steady: only size and persistence count
    at_threshold = heuristic_confidence(thr, reliable, 1.0, params)
    assert at_threshold == pytest.approx(params.weight_size + params.weight_persistence)
    # NDVI at the ceiling: full marks
    assert heuristic_confidence(ceiling, reliable, 1.0, params) == pytest.approx(1.0)
    assert heuristic_confidence(0.99, reliable * 3, 1.0, params) == pytest.approx(1.0)
    # size part grows linearly up to the reliable size
    half = heuristic_confidence(ceiling, reliable // 2, 1.0, params)
    assert half == pytest.approx(1.0 - params.weight_size * 0.5)
    # persistence part
    assert heuristic_confidence(ceiling, reliable, 0.0, params) == pytest.approx(
        1.0 - params.weight_persistence
    )
    assert 0.0 <= heuristic_confidence(0.0, 1, 0.0, params) <= 1.0


def test_confidence_rises_with_ndvi_and_size_and_falls_with_unsteadiness():
    params = TreeCoverParams.from_config()
    base = heuristic_confidence(0.65, 4, 1.0, params)
    assert heuristic_confidence(0.80, 4, 1.0, params) > base
    assert heuristic_confidence(0.65, 8, 1.0, params) > base
    assert heuristic_confidence(0.65, 4, 2 / 3, params) < base


def test_confidences_stay_between_zero_and_one_and_the_filter_applies():
    _, rows, cols = make_cube()
    layer = with_block(flat(rows, cols), slice(0, 3), slice(0, 3), 0.95)  # strong, 9 cells
    layer = with_block(layer, slice(6, 8), slice(6, 8), 0.61)  # marginal, 4 cells
    cube, _, _ = make_cube(stack(layer))
    everything = detect_tree_cover(cube, geometry_of(PLOT), min_confidence=0.0)
    scores = [f["properties"]["confidence"] for f in everything.features]
    assert len(scores) == 2 and all(0.0 <= s <= 1.0 for s in scores)
    strong, marginal = sorted(scores, reverse=True)
    assert strong > 0.9 and marginal < strong
    cutoff = (strong + marginal) / 2
    filtered = detect_tree_cover(cube, geometry_of(PLOT), min_confidence=cutoff)
    assert filtered.patches == 1
    assert filtered.parameters["dropped_patches"]["low_confidence"] == 1
    assert filtered.features[0]["properties"]["confidence"] == pytest.approx(strong)
    assert filtered.parameters["min_confidence"] == pytest.approx(cutoff)


def test_a_patch_that_is_green_only_part_of_the_time_scores_lower():
    _, rows, cols = make_cube()
    steady = with_block(flat(rows, cols), slice(1, 5), slice(1, 5), 0.7)
    dip = with_block(flat(rows, cols), slice(1, 5), slice(1, 5), 0.5)
    even = detect_tree_cover(make_cube(stack(steady))[0], geometry_of(PLOT), min_confidence=0.0)
    uneven = detect_tree_cover(
        make_cube([steady, steady, steady, steady, dip, steady])[0],
        geometry_of(PLOT),
        min_confidence=0.0,
    )
    # the median of (0.7, 0.5, 0.7) is still 0.7, but the patch was below the threshold in one month
    assert (
        uneven.features[0]["properties"]["confidence"]
        < even.features[0]["properties"]["confidence"]
    )


# ---------------------------------------------------------------------------- clipping to the plot
def test_patches_are_clipped_to_an_irregular_plot():
    triangle = Polygon(
        [(77.5000, 13.0000), (77.5040, 13.0000), (77.5000, 13.0040), (77.5000, 13.0000)]
    )
    grid, _ = build_grid(triangle, 30)
    cube, _, _ = make_cube(stack(flat(grid.rows, grid.cols, HIGH)), polygon=triangle)
    result = detect_tree_cover(cube, geometry_of(triangle))
    assert result.patches == 1
    patch = shape(result.features[0]["geometry"])
    assert triangle.buffer(1e-9).contains(patch)
    assert result.covered_fraction <= 1.0
    assert result.area_hectares * 10_000 <= geodesic_area_m2(triangle) * 1.001
    # the patch hugs the plot edge instead of showing whole grid squares outside it
    assert (
        patch.area
        < Polygon(
            [(c[0], c[1]) for c in shape(geometry_of(triangle.envelope)).exterior.coords]
        ).area
    )


def test_a_concave_plot_keeps_every_patch_inside_it():
    # a plot with two lobes and notches: patches follow the outline instead of the grid squares
    plot = Polygon(
        [
            (77.5000, 13.0000), (77.5020, 13.0000), (77.5020, 13.0008), (77.5030, 13.0008),
            (77.5030, 13.0000), (77.5050, 13.0000), (77.5050, 13.0020), (77.5030, 13.0020),
            (77.5030, 13.0012), (77.5020, 13.0012), (77.5020, 13.0020), (77.5000, 13.0020),
        ]
    )  # fmt: skip
    grid, _ = build_grid(plot, 30)
    cube, _, _ = make_cube(stack(flat(grid.rows, grid.cols, HIGH)), polygon=plot)
    result = detect_tree_cover(cube, geometry_of(plot))
    assert result.patches >= 1
    for feature in result.features:
        patch = shape(feature["geometry"])
        assert patch.is_valid and plot.buffer(1e-9).contains(patch)
        assert feature["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert result.covered_fraction <= 1.0


def test_polygonal_part_keeps_polygons_and_drops_everything_else():
    square = Polygon([(0, 0), (0.001, 0), (0.001, 0.001), (0, 0.001)])
    other = Polygon([(0.01, 0), (0.011, 0), (0.011, 0.001), (0.01, 0.001)])
    sliver = Polygon([(0.02, 0), (0.02 + 1e-9, 0), (0.02 + 1e-9, 1e-9), (0.02, 1e-9)])
    assert _polygonal_part(square).equals(square)
    mixed = GeometryCollection([square, LineString([(0, 0), (1, 1)])])
    assert isinstance(_polygonal_part(mixed), Polygon)
    both = _polygonal_part(GeometryCollection([square, other, sliver]))
    assert isinstance(both, MultiPolygon) and len(both.geoms) == 2
    assert _polygonal_part(LineString([(0, 0), (1, 1)])) is None
    assert _polygonal_part(Polygon()) is None
    assert _polygonal_part(sliver) is None


def test_connected_patches_use_eight_connectivity_and_row_major_order():
    grid = np.zeros((6, 6), dtype=bool)
    grid[0, 0] = grid[1, 1] = grid[2, 2] = True  # one diagonal patch
    grid[4, 0] = grid[4, 1] = True  # a horizontal pair
    grid[0, 5] = True  # a lone cell
    patches = connected_patches(grid)
    assert [len(p) for p in patches] == [3, 1, 2]
    assert patches[0][0] == (0, 0)
    assert connected_patches(np.zeros((3, 3), dtype=bool)) == []


# ---------------------------------------------------------------------------- summary and honesty
def test_summary_matches_the_features():
    _, rows, cols = make_cube()
    layer = with_block(flat(rows, cols), slice(1, 4), slice(1, 4), 0.9)
    layer = with_block(layer, slice(6, 9), slice(5, 9), 0.85)
    cube, _, _ = make_cube(stack(layer))
    result = detect_tree_cover(cube, geometry_of(PLOT))
    data = result.to_dict()
    total_m2 = sum(f["properties"]["area_m2"] for f in data["features"]["features"])
    summary = data["summary"]
    assert summary["patches"] == len(data["features"]["features"]) == 2
    assert summary["area_hectares"] == pytest.approx(total_m2 / 10_000, abs=1e-3)
    assert summary["covered_fraction"] == pytest.approx(total_m2 / geodesic_area_m2(PLOT), abs=0.01)
    assert 0.0 < summary["covered_fraction"] < 1.0


def test_limitations_are_honest_and_mention_demo_data():
    _, rows, cols = make_cube()
    cube, _, _ = make_cube(stack(with_block(flat(rows, cols), slice(1, 5), slice(1, 5))))
    result = detect_tree_cover(cube, geometry_of(PLOT))
    text = " ".join(result.limitations)
    assert "not individual crowns" in text
    assert "30 m" in text
    assert "not a probability" in text
    assert "has not been calibrated" in text and "0.6" in text
    assert "dense green vegetation" in text
    assert "Demo mode" in text  # the cube says mode demo
    live, _, _ = make_cube(
        stack(with_block(flat(rows, cols), slice(1, 5), slice(1, 5))),
        mode="live",
        source="sentinel-2-l2a",
    )
    assert "Demo mode" not in " ".join(detect_tree_cover(live, geometry_of(PLOT)).limitations)
    assert result.method == "NDVI threshold + connected components on the 30 m vegetation grid"


def test_a_plot_of_a_few_cells_is_told_it_may_show_no_patch():
    ring = [(77.5000, 13.0000), (77.5004, 13.0000), (77.5004, 13.0004), (77.5000, 13.0004)]
    small = Polygon([*ring, ring[0]])  # about 44 m x 44 m: 4 cells of the 30 m grid
    cube, _, _ = make_cube(polygon=small, base=HIGH)
    result = detect_tree_cover(cube, geometry_of(small))
    assert any("covers only 4 cells" in n and "few or no patches" in n for n in result.limitations)
    large, _, _ = make_cube(base=HIGH)
    assert not any(
        "covers only" in n for n in detect_tree_cover(large, geometry_of(PLOT)).limitations
    )


def test_parameters_record_what_was_used():
    _, rows, cols = make_cube()
    cube, _, _ = make_cube(stack(with_block(flat(rows, cols), slice(1, 5), slice(1, 5))))
    parameters = detect_tree_cover(cube, geometry_of(PLOT), min_confidence=0.4).parameters
    assert parameters["threshold"] == 0.6
    assert parameters["min_patch_cells"] == 2
    assert parameters["min_confidence"] == 0.4
    assert parameters["composite_months"] == TIMES[-3:]
    assert parameters["cell_size_m"] == 30
    assert parameters["verification_status"] == "assumption"
    assert sum(parameters["weights"].values()) == pytest.approx(1.0)


def test_results_are_deterministic_and_json_serialisable():
    _, rows, cols = make_cube()
    layer = with_block(flat(rows, cols), slice(1, 4), slice(1, 4))
    layer = with_block(layer, slice(5, 8), slice(5, 8))
    cube, _, _ = make_cube(stack(layer))
    first = detect_tree_cover(cube, geometry_of(PLOT)).to_dict()
    second = detect_tree_cover(cube, geometry_of(PLOT)).to_dict()
    assert first == second
    assert json.loads(json.dumps(first)) == first


def test_the_plot_can_be_given_as_a_shapely_geometry():
    _, rows, cols = make_cube()
    cube, _, _ = make_cube(stack(with_block(flat(rows, cols), slice(1, 5), slice(1, 5))))
    assert detect_tree_cover(cube, PLOT).patches == 1


# ---------------------------------------------------------------------------- errors
@pytest.mark.parametrize(
    "mutate, code",
    [
        (lambda c: c.pop("grid"), "invalid_cube"),
        (lambda c: c.pop("values"), "invalid_cube"),
        (lambda c: c.update(times=[]), "no_imagery"),
        (lambda c: c.update(times=c["times"][:-1]), "invalid_cube"),
        (lambda c: c.update(mask=[[1]]), "invalid_cube"),
        (lambda c: c.update(index="ndmi"), "wrong_index"),
        (lambda c: c.update(values="nope"), "invalid_cube"),
        (lambda c: c["grid"].update(cell_size_m=0), "invalid_cube"),
        (lambda c: c.update(mask=[[0] * len(c["mask"][0]) for _ in c["mask"]]), "empty_plot"),
    ],
)
def test_malformed_cubes_are_rejected_with_a_code(mutate, code):
    cube, _, _ = make_cube()
    mutate(cube)
    with pytest.raises(DetectionError) as caught:
        detect_tree_cover(cube, geometry_of(PLOT))
    assert caught.value.code == code
    assert isinstance(caught.value, ValueError)


@pytest.mark.parametrize(
    "kwargs, code",
    [
        ({"threshold": 1.0}, "invalid_threshold"),
        ({"threshold": -1.5}, "invalid_threshold"),
        ({"min_patch_cells": 0}, "invalid_min_patch_cells"),
        ({"min_patch_cells": 100_000}, "invalid_min_patch_cells"),
        ({"min_confidence": 1.5}, "invalid_min_confidence"),
        ({"min_confidence": -0.1}, "invalid_min_confidence"),
    ],
)
def test_parameters_out_of_range_are_rejected(kwargs, code):
    cube, _, _ = make_cube()
    with pytest.raises(DetectionError) as caught:
        detect_tree_cover(cube, geometry_of(PLOT), **kwargs)
    assert caught.value.code == code


def test_a_bad_plot_geometry_is_rejected():
    cube, _, _ = make_cube()
    with pytest.raises(DetectionError) as caught:
        detect_tree_cover(cube, {"type": "Point", "coordinates": [77.5, 13.0]})
    assert caught.value.code == "invalid_plot"
    with pytest.raises(DetectionError):
        detect_tree_cover(cube, {"type": "Nope"})
    with pytest.raises(DetectionError):
        detect_tree_cover(cube, {})


# ---------------------------------------------------------------------------- demo cubes and speed
@pytest.mark.parametrize("name", ["india-mango-farm", "usa-agroforestry", "eu-carbon-farming"])
def test_demo_plots_give_patches_inside_the_plot(name):
    sample = json.loads((ROOT / "data" / "sample" / "plots" / f"{name}.json").read_text())
    polygon = shape(sample["geometry"])
    cube = build_demo_cube(sample["plot_id"], polygon, "ndvi", months=36).to_dict("demo")
    result = detect_tree_cover(cube, sample["geometry"])
    assert result.patches > 0
    for feature in result.features:
        assert 0.0 <= feature["properties"]["confidence"] <= 1.0
        patch = shape(feature["geometry"])
        # valid as served: snapping a pinch of touching cells to a grid once left a ring that
        # touched itself (PLT-DEMOIN), which GEOS calls invalid
        assert patch.is_valid
        assert polygon.buffer(1e-9).contains(patch)
        parts = [patch] if patch.geom_type == "Polygon" else list(patch.geoms)
        assert all(part.exterior.is_ccw for part in parts)
    assert 0.0 < result.covered_fraction <= 1.0
    assert any("Demo mode" in n for n in result.limitations)


def test_a_large_cube_is_fast_enough():
    polygon = Polygon([(77.0, 13.0), (77.15, 13.0), (77.15, 13.15), (77.0, 13.15)])  # ~16 km square
    grid, _ = build_grid(polygon, 100)
    rows, cols = grid.rows, grid.cols
    yy, xx = np.mgrid[0:rows, 0:cols]
    field = 0.6 + 0.25 * np.sin(xx / 9.0) * np.cos(yy / 7.0)
    cube, _, _ = (
        {
            "plot_id": "BIG",
            "index": "ndvi",
            "mode": "live",
            "grid": grid.to_dict(),
            "times": TIMES[-3:],
            "mask": np.ones((rows, cols), dtype=int).tolist(),
            "values": [field.round(3).tolist() for _ in range(3)],
            "provenance": {"source": "test"},
        },
        rows,
        cols,
    )
    started = time.perf_counter()
    result = detect_tree_cover(cube, geometry_of(polygon))
    assert time.perf_counter() - started < 15.0
    assert result.patches > 0 and rows * cols > 10_000


# ---------------------------------------------------------------------------- config
def test_parameters_come_from_config_detection_yaml():
    params = TreeCoverParams.from_config()
    assert params.threshold == 0.6 and params.min_patch_cells == 2
    assert params.composite_slices == 3 and params.default_min_confidence == 0.5
    assert params.verification_status == "assumption"


def test_every_parameter_cites_a_source_and_a_verification_status():
    config = load_detection_config()
    assert config.path == ROOT / "config" / "detection.yaml"
    assert set(config.sections) >= {"point_cloud", "tree_cover", "vector_import"}
    for section in config.sections:
        for parameter in config.parameters(section):
            assert parameter.source.strip(), (section, parameter.name)
            assert parameter.verification_status in {"verified", "assumption"}, parameter.name
            assert parameter.unit, (section, parameter.name)
            if parameter.verification_status == "assumption":
                assert "assumption" in parameter.source, (section, parameter.name)
    assert "calibrate locally" in config.parameter("tree_cover", "ndvi_tree_cover_threshold").source
    assert config.parameter("point_cloud", "ground_class_code").verification_status == "verified"
    assert "ASPRS" in config.parameter("point_cloud", "ground_class_code").source


def test_no_parameter_is_pending():
    config = load_detection_config()
    pending = [
        (section, p.name)
        for section in config.sections
        for p in config.parameters(section)
        if p.verification_status == "pending"
    ]
    assert pending == []


REAL_CONFIG = (ROOT / "config" / "detection.yaml").read_text(encoding="utf-8")


def write_config(folder: Path, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "detection.yaml").write_text(text, encoding="utf-8")
    return folder


def test_a_config_directory_is_used_before_the_default(tmp_path):
    folder = write_config(tmp_path / "cfg", REAL_CONFIG.replace("version: 0.1.0", "version: 9.9.9"))
    assert find_config_file(folder) == folder / "detection.yaml"
    assert load_detection_config(folder).version == "9.9.9"
    assert load_detection_config().version != "9.9.9"


def test_the_environment_variable_points_at_the_config_directory(tmp_path, monkeypatch):
    folder = write_config(tmp_path / "envcfg", REAL_CONFIG)
    monkeypatch.setenv("ATLAS_CONFIG_DIR", str(folder))
    assert find_config_file() == folder / "detection.yaml"


@pytest.mark.parametrize(
    "old, new",
    [
        (
            "    verification_status: assumption\n  min_patch_cells:",
            "    verification_status: guessed\n  min_patch_cells:",
        ),
        ('    source: "project assumption v0.1 - calibrate locally"\n', ""),
    ],
)
def test_a_malformed_parameter_stops_the_load(tmp_path, old, new):
    assert old in REAL_CONFIG
    folder = write_config(tmp_path / "bad", REAL_CONFIG.replace(old, new, 1))
    with pytest.raises(ConfigError):
        load_detection_config(folder)


def test_a_missing_file_is_a_config_error(monkeypatch):
    monkeypatch.setattr("geo_engine.detection.config.CONFIG_FILE", "no-such-file.yaml")
    with pytest.raises(ConfigError, match="could not locate"):
        find_config_file()


def test_confidence_weights_must_sum_to_one(tmp_path):
    old = "  confidence_weight_size:\n    value: 0.3"
    assert old in REAL_CONFIG
    folder = write_config(tmp_path / "w", REAL_CONFIG.replace(old, old.replace("0.3", "0.5")))
    with pytest.raises(ConfigError, match="sum to 1"):
        TreeCoverParams.from_config(config_dir=folder)


def test_a_missing_parameter_or_section_is_a_config_error(tmp_path):
    config = load_detection_config()
    with pytest.raises(ConfigError):
        config.parameter("tree_cover", "no_such_parameter")
    with pytest.raises(ConfigError):
        config.section("no_such_section")
    folder = write_config(tmp_path / "short", "version: 1\nupdated: 2026-10-05\ntree_cover: {}\n")
    with pytest.raises(ConfigError):
        TreeCoverParams.from_config(config_dir=folder)
