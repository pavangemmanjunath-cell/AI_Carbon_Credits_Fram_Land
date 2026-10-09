"""LAS / LAZ point clouds: ground -> canopy height model -> local maxima (geo_engine.pointcloud).

The clouds are synthetic orchards (``geo_engine.pointcloud.synthetic``): flat or sloping noisy
ground and N cone-shaped trees 4-12 m tall at known positions, written with laspy. The detection
must find N within 10 % (in practice it finds all of them).
"""

from __future__ import annotations

import dataclasses
import io
import math

import laspy
import numpy as np
import pytest
from pyproj import CRS, Transformer
from shapely.geometry import box

from geo_engine.imports.errors import ImportDataError, UnsupportedFormatError
from geo_engine.pointcloud import (
    E57_ADVICE,
    MAX_GRID_CELLS_PER_SIDE,
    METHOD,
    PointCloudParams,
    analyse_point_cloud,
    inspect_point_cloud,
)
from geo_engine.pointcloud import chm as chm_ops
from geo_engine.pointcloud import reader as reader_module
from geo_engine.pointcloud.synthetic import (
    CLASS_GROUND,
    make_orchard,
    match_trees,
    to_las_bytes,
)

TOLERANCE = 0.10  # the detection must find N planted trees +/- 10 %
EPSG = 32643  # WGS 84 / UTM zone 43N


def planted_xy(orchard) -> np.ndarray:
    return np.column_stack([orchard.tree_x, orchard.tree_y])


def assert_within_ten_percent(found: int, planted: int) -> None:
    assert abs(found - planted) <= TOLERANCE * planted, f"found {found} for {planted} planted"


# ---------------------------------------------------------------------------- accuracy
@pytest.mark.parametrize(
    "label, kwargs, compressed",
    [
        ("class 2 ground, LAS", {"classified": True, "n_trees": 60, "seed": 1}, False),
        ("class 2 ground, LAZ", {"classified": True, "n_trees": 80, "seed": 3}, True),
        ("unclassified ground", {"classified": False, "n_trees": 60, "seed": 5}, False),
        ("unclassified, LAZ", {"classified": False, "n_trees": 100, "seed": 6}, True),
        (
            "sloping ground, unclassified",
            {"classified": False, "n_trees": 60, "seed": 9, "ground_slope": 0.05},
            False,
        ),
        (
            "sloping ground, class 2",
            {"classified": True, "n_trees": 60, "seed": 10, "ground_slope": 0.08},
            False,
        ),
        (
            "dense orchard",
            {"classified": True, "n_trees": 200, "size_m": (150.0, 150.0), "seed": 11},
            True,
        ),
    ],
)
def test_detection_finds_the_planted_trees_within_ten_percent(label, kwargs, compressed):
    orchard = make_orchard(**kwargs)
    result = analyse_point_cloud(to_las_bytes(orchard, compressed=compressed), "orchard.laz")
    assert_within_ten_percent(result.count, orchard.n_trees)
    matched, missed, extra = match_trees(result.tops_xy, planted_xy(orchard), tolerance_m=2.0)
    assert matched >= (1 - TOLERANCE) * orchard.n_trees, (label, matched, missed, extra)
    assert result.georeferenced and result.crs == f"EPSG:{EPSG}"


def test_ground_method_follows_the_classification():
    classified = analyse_point_cloud(to_las_bytes(make_orchard(classified=True)), "a.las")
    assert classified.ground_method == "classification"
    assert classified.ground_classified_share > 0.5
    unclassified = analyse_point_cloud(to_las_bytes(make_orchard(classified=False)), "a.las")
    assert unclassified.ground_method == "lowest-return"
    assert unclassified.ground_classified_share == 0.0


def test_a_few_ground_points_are_not_enough_to_trust_the_classification():
    orchard = make_orchard(classified=True, n_trees=40, seed=2)
    classes = np.where(np.arange(orchard.n_points) % 400 == 0, CLASS_GROUND, 5).astype(np.uint8)
    thin = dataclasses.replace(orchard, classification=classes)  # ~0.25 % ground < 1 %
    result = analyse_point_cloud(to_las_bytes(thin), "a.las")
    assert result.ground_method == "lowest-return"
    assert_within_ten_percent(result.count, 40)


def test_las_and_laz_give_identical_results():
    orchard = make_orchard(n_trees=50, seed=4)
    las = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    laz = analyse_point_cloud(to_las_bytes(orchard, compressed=True), "a.laz")
    assert (las.format, laz.format) == ("las", "laz")
    assert las.count == laz.count
    np.testing.assert_allclose(las.tops_xy, laz.tops_xy)
    np.testing.assert_allclose(las.heights_m, laz.heights_m)


def test_results_are_deterministic():
    data = to_las_bytes(make_orchard(n_trees=50, seed=4))
    first = analyse_point_cloud(data, "a.las")
    second = analyse_point_cloud(data, "a.las")
    np.testing.assert_array_equal(first.tops_xy, second.tops_xy)
    np.testing.assert_array_equal(first.heights_m, second.heights_m)


def test_legacy_point_format_with_geotiff_crs_keys():
    orchard = make_orchard(n_trees=40, seed=12)
    result = analyse_point_cloud(to_las_bytes(orchard, point_format=3), "legacy.las")
    assert result.crs == f"EPSG:{EPSG}"
    assert_within_ten_percent(result.count, 40)


# ---------------------------------------------------------------------------- positions and stats
def test_tree_tops_are_placed_at_the_planted_positions_in_wgs84():
    orchard = make_orchard(n_trees=60, seed=1)
    result = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    assert result.tops_lonlat is not None and result.tops_lonlat.shape == (result.count, 2)
    to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{EPSG}", always_xy=True)
    x, y = to_utm.transform(result.tops_lonlat[:, 0], result.tops_lonlat[:, 1])
    matched, _, extra = match_trees(np.column_stack([x, y]), planted_xy(orchard), tolerance_m=1.5)
    assert matched >= 0.95 * orchard.n_trees and extra <= 3
    # the cloud sits in India (UTM 43N): longitudes between 72 and 78 degrees east
    assert result.tops_lonlat[:, 0].min() > 71.9 and result.tops_lonlat[:, 0].max() < 78.1


def test_heights_are_above_the_ground_not_above_sea_level():
    orchard = make_orchard(n_trees=60, seed=1, ground_elevation_m=915.0)
    result = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    assert result.mean_height_m == pytest.approx(float(orchard.tree_height_m.mean()), abs=0.6)
    assert result.heights_m.max() < 13.0 and result.heights_m.min() > 2.0
    assert result.median_height_m is not None and result.p90_height_m is not None
    assert result.p90_height_m >= result.median_height_m
    sloped = make_orchard(n_trees=60, seed=1, ground_slope=0.05, classified=False)
    on_slope = analyse_point_cloud(to_las_bytes(sloped), "a.las")
    assert on_slope.mean_height_m == pytest.approx(float(sloped.tree_height_m.mean()), abs=0.8)


def test_individual_heights_match_the_planted_heights():
    orchard = make_orchard(n_trees=40, seed=8)
    result = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    errors = []
    for index, (tx, ty) in enumerate(planted_xy(orchard)):
        distances = np.hypot(result.tops_xy[:, 0] - tx, result.tops_xy[:, 1] - ty)
        nearest = int(np.argmin(distances))
        if distances[nearest] <= 1.5:
            errors.append(result.heights_m[nearest] - orchard.tree_height_m[index])
    assert len(errors) >= 38
    assert abs(float(np.mean(errors))) < 0.35
    assert float(np.percentile(np.abs(errors), 95)) < 1.2


def test_point_density_footprint_and_canopy_cover():
    orchard = make_orchard(n_trees=60, seed=1, size_m=(100.0, 100.0))
    result = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    assert result.point_count == orchard.n_points == result.points_used
    assert result.point_density_per_m2 == pytest.approx(orchard.n_points / 10_000.0, rel=0.2)
    assert result.bbox_wgs84 is not None
    west, south, east, north = result.bbox_wgs84
    width_m = (east - west) * 111_320 * math.cos(math.radians(north))
    assert width_m == pytest.approx(100.0, abs=2.0)
    assert 0.0 < (result.canopy_cover_fraction or 0.0) < 0.5
    assert result.bbox[2] - result.bbox[0] == pytest.approx(100.0, abs=1.0)


def test_count_in_plot_uses_the_tree_tops_inside_the_polygon():
    orchard = make_orchard(n_trees=80, seed=2)
    result = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    to_lonlat = Transformer.from_crs(f"EPSG:{EPSG}", "EPSG:4326", always_xy=True)
    mid_x = orchard.origin[0] + 50.0
    west, south = to_lonlat.transform(orchard.origin[0] - 10, orchard.origin[1] - 10)
    east, north = to_lonlat.transform(mid_x, orchard.origin[1] + 110)
    plot = box(west, south, east, north)
    expected = int((orchard.tree_x < mid_x).sum())
    in_plot = result.count_in_plot(plot)
    assert in_plot is not None and abs(in_plot - expected) <= 2
    block = result.trees_block(plot)
    assert block["count"] == result.count and block["count_in_plot"] == in_plot
    assert block["confidence_field"] is None and block["min_confidence"] is None
    preview, note = result.preview(plot)
    assert preview is not None and len(preview["features"]) == result.count and note is None
    flags = [f["properties"]["in_plot"] for f in preview["features"]]
    assert sum(flags) == in_plot
    assert preview["features"][0]["geometry"]["type"] == "Point"
    assert result.count_in_plot(None) is None


def test_preview_is_capped():
    orchard = make_orchard(n_trees=60, seed=1)
    result = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    preview, note = result.preview(None, limit=10)
    assert preview is not None and len(preview["features"]) <= 10
    assert note is not None and "10 of" in note


# ---------------------------------------------------------------------------- CRS handling
def test_a_cloud_without_a_crs_is_analysed_but_not_georeferenced():
    orchard = make_orchard(n_trees=60, seed=5, classified=False)
    result = analyse_point_cloud(to_las_bytes(orchard, with_crs=False), "nocrs.las")
    assert_within_ten_percent(result.count, 60)
    assert result.georeferenced is False and result.crs is None
    assert result.tops_lonlat is None and result.bbox_wgs84 is None
    assert result.count_in_plot(box(0, 0, 1, 1)) is None
    assert result.preview(None) == (None, None)
    assert result.trees_block(box(0, 0, 1, 1))["count_in_plot"] is None
    assert any("no coordinate system" in w for w in result.warnings)
    assert result.summary_block() == {
        "feature_count": 1,
        "polygon_count": 0,
        "point_count": orchard.n_points,
        "georeferenced": False,
        "crs": None,
    }


def test_coordinates_in_us_survey_feet_are_converted_to_metres():
    orchard = make_orchard(n_trees=60, seed=4)
    foot = 1200.0 / 3937.0  # US survey foot in metres
    feet = dataclasses.replace(
        orchard,
        x=(orchard.x - orchard.origin[0] + 300_000.0) / foot,
        y=(orchard.y - orchard.origin[1] + 100_000.0) / foot,
        z=orchard.z / foot,
        tree_x=(orchard.tree_x - orchard.origin[0] + 300_000.0) / foot,
        tree_y=(orchard.tree_y - orchard.origin[1] + 100_000.0) / foot,
    )
    result = analyse_point_cloud(
        to_las_bytes(feet, epsg=2263), "feet.las"
    )  # NAD83 / NY Long Island (ftUS)
    assert result.crs == "EPSG:2263"
    assert_within_ten_percent(result.count, 60)
    assert result.mean_height_m == pytest.approx(float(orchard.tree_height_m.mean()), abs=0.6)
    assert result.bbox[2] - result.bbox[0] == pytest.approx(100.0 / foot, abs=2.0)
    assert result.tops_lonlat is not None and -80 < result.tops_lonlat[0, 0] < -70


def test_geographic_coordinates_are_refused_with_advice():
    orchard = make_orchard(n_trees=5, seed=1)
    with pytest.raises(ImportDataError) as caught:
        analyse_point_cloud(to_las_bytes(orchard, epsg=4326), "degrees.las")
    assert caught.value.code == "geographic_crs"
    assert "projected" in caught.value.detail
    with pytest.raises(ImportDataError):
        inspect_point_cloud(to_las_bytes(orchard, epsg=4326), "degrees.las")


def test_compound_crs_with_a_vertical_datum():
    orchard = make_orchard(n_trees=40, seed=3)
    crs = CRS.from_user_input("EPSG:32643+5773")  # UTM 43N + EGM96 height
    header = laspy.LasHeader(point_format=6, version="1.4")
    header.scales = np.array([0.01, 0.01, 0.01])
    header.offsets = np.array([math.floor(orchard.x.min()), math.floor(orchard.y.min()), 0.0])
    header.add_crs(crs)
    las = laspy.LasData(header)
    las.x, las.y, las.z = orchard.x, orchard.y, orchard.z
    las.classification = orchard.classification
    buffer = io.BytesIO()
    las.write(buffer)
    result = analyse_point_cloud(buffer.getvalue(), "compound.las")
    assert result.georeferenced
    assert_within_ten_percent(result.count, 40)


# ---------------------------------------------------------------------------- parameters
def test_detection_block_exposes_the_config_parameters():
    result = analyse_point_cloud(to_las_bytes(make_orchard(n_trees=30, seed=1)), "a.las")
    block = result.detection_block()
    assert (
        block["ran"] is True and block["method"] == METHOD == "canopy height model + local maxima"
    )
    parameters = block["parameters"]
    assert parameters["cell_size_m"] == 0.5
    assert parameters["min_height_m"] == 2.0
    assert parameters["window_radius_m"] == 1.5
    assert parameters["ground_cell_size_m"] == 5.0
    assert block["notes"] and all(isinstance(n, str) for n in block["notes"])
    assert any("Ground:" in n for n in block["notes"])


def test_parameters_are_read_from_the_config_file():
    params = PointCloudParams.from_config()
    assert (params.cell_size_m, params.min_height_m, params.window_radius_m) == (0.5, 2.0, 1.5)
    assert params.ground_class_code == 2 and params.ground_class_min_share == 0.01
    assert params.smoothing_window_cells == 3 and params.max_points == 30_000_000
    assert params.noise_class_codes == (7, 18)


def test_a_higher_minimum_height_finds_only_taller_trees():
    orchard = make_orchard(n_trees=60, seed=1, height_range_m=(4.0, 12.0))
    data = to_las_bytes(orchard)
    default = analyse_point_cloud(data, "a.las")
    params = dataclasses.replace(PointCloudParams.from_config(), min_height_m=8.0)
    tall = analyse_point_cloud(data, "a.las", params)
    expected = int((orchard.tree_height_m > 8.0).sum())
    assert tall.count < default.count
    assert abs(tall.count - expected) <= max(3, 0.1 * expected)
    assert tall.heights_m.min() > 8.0
    assert tall.detection_block()["parameters"]["min_height_m"] == 8.0


def test_a_wider_window_merges_neighbouring_trees():
    orchard = make_orchard(n_trees=60, seed=1)
    data = to_las_bytes(orchard)
    default = analyse_point_cloud(data, "a.las")
    wide = analyse_point_cloud(
        data, "a.las", dataclasses.replace(PointCloudParams.from_config(), window_radius_m=9.0)
    )
    assert wide.count < default.count


def test_the_cell_size_is_raised_to_keep_the_grid_within_4000_cells():
    orchard = make_orchard(n_trees=30, seed=1)
    far_x = np.append(orchard.x, orchard.origin[0] + 25_000.0)
    far_y = np.append(orchard.y, orchard.origin[1] + 100.0)
    far_z = np.append(orchard.z, 300.0)
    classes = np.append(orchard.classification, CLASS_GROUND).astype(np.uint8)
    wide = dataclasses.replace(orchard, x=far_x, y=far_y, z=far_z, classification=classes)
    result = analyse_point_cloud(to_las_bytes(wide), "wide.las")
    assert result.cell_size_m > 0.5
    assert 25_000.0 / result.cell_size_m <= MAX_GRID_CELLS_PER_SIDE
    assert any("raised" in w and "4,000" in w for w in result.warnings)
    assert result.detection_block()["parameters"]["cell_size_m"] == result.cell_size_m


def test_choose_cell_size_keeps_the_grid_within_the_limit():
    assert chm_ops.choose_cell_size(100.0, 100.0, 0.5, 4000) == 0.5
    for width, height in [(2_000.0, 10.0), (2_001.0, 10.0), (50_000.0, 50_000.0), (3_999.5, 1.0)]:
        cell = chm_ops.choose_cell_size(width, height, 0.5, 4000)
        grid = chm_ops.make_grid(0.0, 0.0, width, height, cell)
        assert cell >= 0.5 and max(grid.ncols, grid.nrows) <= 4000


def test_decimation_above_the_point_cap_is_reported():
    orchard = make_orchard(n_trees=60, seed=1, ground_points_per_m2=8.0, crown_points_per_m2=24.0)
    params = dataclasses.replace(PointCloudParams.from_config(), max_points=50_000)
    result = analyse_point_cloud(to_las_bytes(orchard), "dense.las", params)
    assert result.decimation_stride > 1
    assert result.points_used < result.point_count == orchard.n_points
    assert any("every" in w and "point was used" in w for w in result.warnings)
    assert_within_ten_percent(result.count, 60)


def test_clouds_declaring_too_many_points_are_refused_before_decoding():
    data = to_las_bytes(make_orchard(n_trees=10, seed=1))
    params = dataclasses.replace(PointCloudParams.from_config(), max_points_hard_limit=1_000)
    with pytest.raises(ImportDataError) as caught:
        analyse_point_cloud(data, "huge.las", params)
    assert caught.value.code == "too_many_points"


def test_low_point_density_is_flagged():
    sparse = make_orchard(n_trees=60, seed=1, ground_points_per_m2=0.3, crown_points_per_m2=1.0)
    result = analyse_point_cloud(to_las_bytes(sparse), "sparse.las")
    assert any("point density" in w for w in result.warnings)
    dense = analyse_point_cloud(to_las_bytes(make_orchard(n_trees=60, seed=1)), "dense.las")
    assert not any("point density" in w for w in dense.warnings)


# ---------------------------------------------------------------------------- noise
def test_noise_classes_and_points_far_above_the_trees_are_ignored():
    orchard = make_orchard(n_trees=40, seed=2)
    n_noise = 50
    rng = np.random.default_rng(0)
    noise_x = orchard.origin[0] + rng.uniform(0, 100, n_noise)
    noise_y = orchard.origin[1] + rng.uniform(0, 100, n_noise)
    # 30 m spikes classified as noise (7 = low/high noise per ASPRS code 18), plus unclassified
    # spikes at 500 m above the ground (above max_tree_height_m)
    spikes = dataclasses.replace(
        orchard,
        x=np.concatenate([orchard.x, noise_x, noise_x]),
        y=np.concatenate([orchard.y, noise_y, noise_y]),
        z=np.concatenate([orchard.z, np.full(n_noise, 330.0), np.full(n_noise, 800.0)]),
        classification=np.concatenate(
            [orchard.classification, np.full(n_noise, 18), np.full(n_noise, 5)]
        ).astype(np.uint8),
    )
    clean = analyse_point_cloud(to_las_bytes(orchard), "a.las")
    noisy = analyse_point_cloud(to_las_bytes(spikes), "a.las")
    assert noisy.count == clean.count
    assert any("classified as noise" in w for w in noisy.warnings)
    assert any("higher than 80" in n for n in noisy.notes)


# ---------------------------------------------------------------------------- errors
def test_e57_without_pye57_is_unsupported_with_advice(monkeypatch):
    monkeypatch.setattr("geo_engine.pointcloud.analyse.pye57_available", lambda: False)
    with pytest.raises(UnsupportedFormatError) as caught:
        analyse_point_cloud(b"ASTM-E57" + bytes(100), "scan.e57")
    assert caught.value.code == "e57_unsupported"
    assert "CloudCompare" in caught.value.detail and "PDAL" in caught.value.detail
    assert caught.value.detail == E57_ADVICE
    with pytest.raises(UnsupportedFormatError):
        inspect_point_cloud(b"ASTM-E57", "scan.e57")


def test_unknown_extensions_are_unsupported():
    with pytest.raises(UnsupportedFormatError):
        analyse_point_cloud(b"x", "cloud.xyz")
    with pytest.raises(UnsupportedFormatError):
        inspect_point_cloud(b"x", "cloud.ply")


@pytest.mark.parametrize("payload", [b"", b"not a point cloud", b"LASF" + bytes(10), bytes(2000)])
def test_garbage_is_rejected_cleanly(payload):
    for name in ("a.las", "a.laz"):
        with pytest.raises(ImportDataError) as caught:
            analyse_point_cloud(payload, name)
        assert caught.value.code in {"invalid_content", "truncated", "empty_cloud"}


def test_truncated_files_are_rejected():
    orchard = make_orchard(n_trees=20, seed=1)
    las = to_las_bytes(orchard)
    with pytest.raises(ImportDataError) as caught:
        analyse_point_cloud(las[: len(las) // 2], "cut.las")
    assert caught.value.code == "truncated"
    laz = to_las_bytes(orchard, compressed=True)
    with pytest.raises(ImportDataError) as caught_laz:
        analyse_point_cloud(laz[: len(laz) // 2], "cut.laz")
    assert caught_laz.value.code in {"invalid_content", "truncated"}


def test_an_empty_cloud_is_rejected():
    header = laspy.LasHeader(point_format=6, version="1.4")
    header.scales = np.array([0.01, 0.01, 0.01])
    header.add_crs(CRS.from_epsg(EPSG))
    buffer = io.BytesIO()
    laspy.LasData(header).write(buffer)
    with pytest.raises(ImportDataError) as caught:
        analyse_point_cloud(buffer.getvalue(), "empty.las")
    assert caught.value.code == "empty_cloud"


def test_laz_without_a_backend_gives_a_clear_unsupported_error(monkeypatch):
    def refuse(_stream):
        raise RuntimeError("No LazBackend selected, cannot decompress data")

    monkeypatch.setattr(laspy, "open", refuse)
    with pytest.raises(UnsupportedFormatError) as caught:
        reader_module.read_header(b"LASF")
    assert caught.value.code == "laz_backend_missing"


# ---------------------------------------------------------------------------- header only
def test_inspect_reads_the_header_without_decoding_points():
    orchard = make_orchard(n_trees=30, seed=1)
    info = inspect_point_cloud(to_las_bytes(orchard, compressed=True), "a.laz")
    assert info.format == "laz" and info.point_count == orchard.n_points
    assert info.georeferenced and info.crs == f"EPSG:{EPSG}"
    assert info.bbox_wgs84 is not None
    west, south, east, north = info.bbox_wgs84
    assert 72 < west < east < 78 and 0 < south < north < 90
    no_crs = inspect_point_cloud(to_las_bytes(orchard, with_crs=False), "a.las")
    assert not no_crs.georeferenced and no_crs.bbox_wgs84 is None
    assert any("coordinate system" in w for w in no_crs.warnings)


# ---------------------------------------------------------------------------- the building blocks
def test_flat_plateau_gives_one_tree_top():
    chm = np.zeros((20, 20), dtype=np.float32)
    chm[8:10, 8:10] = 6.0  # a 2 x 2 plateau
    centroids, heights = chm_ops.find_tree_tops(chm, chm_ops.smooth_mean(chm, 1), 3, 2.0)
    assert len(centroids) == 1
    assert centroids[0] == pytest.approx((8.5, 8.5))
    assert heights[0] == pytest.approx(6.0)


def test_two_separate_crowns_and_one_that_is_too_short():
    chm = np.zeros((40, 40), dtype=np.float32)
    chm[10, 10] = 7.0
    chm[10, 30] = 5.0
    chm[30, 20] = 1.5  # below min_height
    centroids, heights = chm_ops.find_tree_tops(chm, chm.copy(), 3, 2.0)
    assert sorted(heights.tolist()) == [5.0, 7.0]
    assert len(centroids) == 2


def test_a_lower_peak_inside_the_window_of_a_taller_one_is_not_a_tree():
    chm = np.zeros((30, 30), dtype=np.float32)
    chm[15, 15] = 8.0
    chm[15, 17] = 6.0  # 2 cells away, inside a 3-cell window
    centroids, _ = chm_ops.find_tree_tops(chm, chm.copy(), 3, 2.0)
    assert len(centroids) == 1
    far, _ = chm_ops.find_tree_tops(chm, chm.copy(), 1, 2.0)  # a 1-cell window sees both
    assert len(far) == 2


def test_smoothing_ignores_missing_cells_and_closes_small_holes():
    chm = np.full((9, 9), 5.0, dtype=np.float32)
    chm[4, 4] = np.nan
    smoothed = chm_ops.smooth_mean(chm, 3)
    assert smoothed[4, 4] == pytest.approx(5.0)  # eight valid neighbours fill the hole
    edge = np.full((9, 9), np.nan, dtype=np.float32)
    edge[3:6, 3:6] = 4.0
    out = chm_ops.smooth_mean(edge, 3)
    assert np.isnan(out[0, 0]) and np.isnan(out[1, 1])  # the data edge is not pushed outward
    assert out[4, 4] == pytest.approx(4.0)


def test_fill_nearest_extends_ground_from_valid_cells():
    grid = np.full((5, 5), np.nan, dtype=np.float32)
    grid[2, 2] = 10.0
    filled = chm_ops.fill_nearest(grid, np.ones_like(grid, dtype=bool), max_iterations=10)
    assert np.allclose(filled, 10.0)
    empty = chm_ops.fill_nearest(
        np.full((3, 3), np.nan, dtype=np.float32), np.ones((3, 3), bool), 5
    )
    assert np.allclose(empty, 0.0)


def test_bilinear_sampling_of_a_ramp():
    spec = chm_ops.GridSpec(x0=0.0, y0=0.0, cell=1.0, ncols=10, nrows=10)
    ramp = np.tile(np.arange(10, dtype=np.float32), (10, 1))  # value = column index
    xs = np.array([2.5, 3.0, 4.25], dtype=np.float32)
    ys = np.array([5.0, 5.0, 5.0], dtype=np.float32)
    np.testing.assert_allclose(
        chm_ops.sample_bilinear(ramp, xs, ys, spec), [2.0, 2.5, 3.75], atol=1e-5
    )


def test_analysis_result_notes_carry_the_honest_limitations():
    result = analyse_point_cloud(to_las_bytes(make_orchard(n_trees=30, seed=1)), "a.las")
    assert any("compare with a field count" in n for n in result.notes)
    assert "heights are above the estimated ground" in result.trees_block()["method"]
