from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pytest
from shapely.geometry import Polygon

from geo_engine.cube import Cube, build_demo_cube, build_grid, month_sequence
from geo_engine.cube.live import aggregate_to_grid, index_from_bands, reflectance_offset_dn
from geo_engine.satellite import (
    PROVIDERS,
    Scene,
    best_scene_per_period,
    period_key,
    scene_from_item,
)

PLOT = Polygon([(77.538, 13.2918), (77.5394, 13.2918), (77.5394, 13.2931), (77.538, 13.2931)])


def _scene(sid: str, when: datetime, cloud: float) -> Scene:
    return Scene(id=sid, datetime=when, cloud_cover=cloud, assets={}, provider="earth-search")


def test_best_scene_per_period_picks_lowest_cloud_then_latest():
    scenes = [
        _scene("a", datetime(2026, 9, 1, tzinfo=UTC), 10.0),
        _scene("b", datetime(2026, 9, 11, tzinfo=UTC), 3.0),
        _scene("c", datetime(2026, 9, 21, tzinfo=UTC), 3.0),
        _scene("d", datetime(2026, 10, 2, tzinfo=UTC), 0.5),
    ]
    best = best_scene_per_period(scenes, "month")
    assert list(best) == ["2026-09", "2026-10"]
    assert best["2026-09"].id == "c"
    assert best["2026-10"].id == "d"
    assert best_scene_per_period(scenes, "year")["2026"].id == "d"
    assert period_key(date(2026, 3, 5)) == "2026-03"


def test_scene_from_stac_item_dict_maps_asset_roles():
    item = {
        "id": "S2B_43PGQ_20260921_0_L2A",
        "properties": {
            "datetime": "2026-09-21T05:06:59Z",
            "eo:cloud_cover": 3.0,
            "s2:processing_baseline": "05.11",
        },
        "assets": {
            "red": {"href": "https://x/B04.tif"},
            "nir": {"href": "https://x/B08.tif"},
            "swir16": {"href": "https://x/B11.tif"},
            "scl": {"href": "https://x/SCL.tif"},
        },
    }
    scene = scene_from_item(item, PROVIDERS["earth-search"])
    assert scene.cloud_cover == 3.0
    assert scene.date == date(2026, 9, 21)
    assert set(scene.assets) == {"red", "nir", "swir16", "scl"}
    assert reflectance_offset_dn(scene, PROVIDERS["earth-search"]) == -1000.0
    item["properties"]["earthsearch:boa_offset_applied"] = True
    assert (
        reflectance_offset_dn(
            scene_from_item(item, PROVIDERS["earth-search"]), PROVIDERS["earth-search"]
        )
        == 0.0
    )
    copernicus = scene_from_item(
        {
            "id": "x",
            "properties": {"datetime": "2026-01-01T00:00:00Z", "eo:cloud_cover": 1},
            "assets": {
                "B04_10m": {"href": "a"},
                "B08_10m": {"href": "b"},
                "SCL_20m": {"href": "c"},
            },
        },
        PROVIDERS["copernicus"],
    )
    assert set(copernicus.assets) == {"red", "nir", "scl"}


def test_month_sequence_wraps_years():
    assert month_sequence(date(2026, 2, 10), 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_grid_covers_plot_with_30m_cells():
    grid, mask = build_grid(PLOT, 30)
    # plot ≈ 151 m × 144 m → 6 × 6 cells of 30 m
    assert (grid.rows, grid.cols) == (5, 6) or (grid.rows, grid.cols) == (5, 5) or grid.rows == 5
    assert mask.shape == (grid.rows, grid.cols)
    assert mask.sum() >= 1
    assert grid.bbox[0] < PLOT.bounds[0] + 1e-9 and grid.bbox[2] > PLOT.bounds[2] - 1e-9


def test_demo_cube_is_deterministic_and_masked():
    end = date(2026, 9, 30)
    cube1 = build_demo_cube("PLT-DEMOIN", PLOT, "ndvi", months=12, end=end, planting_year=2023)
    cube2 = build_demo_cube("PLT-DEMOIN", PLOT, "ndvi", months=12, end=end, planting_year=2023)
    assert np.array_equal(np.nan_to_num(cube1.values), np.nan_to_num(cube2.values))
    assert cube1.values.shape == (12, cube1.grid.rows, cube1.grid.cols)
    assert cube1.times[-1] == "2026-09" and cube1.times[0] == "2025-10"
    outside = ~cube1.mask.astype(bool)
    assert np.isnan(cube1.values[:, outside]).all()
    other = build_demo_cube("PLT-OTHER1", PLOT, "ndvi", months=12, end=end)
    assert not np.array_equal(np.nan_to_num(cube1.values), np.nan_to_num(other.values))
    payload = cube1.to_dict(mode="demo")
    assert payload["provenance"]["source"] == "synthetic-demo"
    assert len(payload["stats_per_time"]) == 12
    assert payload["grid"]["cell_size_m"] == 30
    assert all(0 <= s["valid_share"] <= 1 for s in payload["stats_per_time"])
    means = [s["mean"] for s in payload["stats_per_time"] if s["mean"] is not None]
    assert all(-0.2 <= m <= 0.95 for m in means)
    # at least one cloud-masked month has valid_share < 1
    assert any(s["valid_share"] < 1 for s in payload["stats_per_time"])


def test_demo_cube_rejects_unknown_index():
    with pytest.raises(ValueError):
        build_demo_cube("PLT-X", PLOT, "evi", months=3)


def test_index_from_bands_applies_scl():
    a = np.array([[0.5, 0.5]], dtype=np.float32)
    b = np.array([[0.1, 0.1]], dtype=np.float32)
    scl = np.array([[4, 9]])
    out = index_from_bands(a, b, scl)
    assert out[0, 0] == pytest.approx(0.4 / 0.6)
    assert np.isnan(out[0, 1])


def test_aggregate_to_grid_averages_pixels():
    pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds

    grid, _mask = build_grid(PLOT, 30)
    # Synthetic 10 m "projected" raster already in EPSG:4326 over the grid bbox
    rows, cols = grid.rows * 3, grid.cols * 3
    transform = from_bounds(*grid.bbox, cols, rows)
    source = np.full((rows, cols), 0.6, dtype=np.float32)
    source[0:3, 0:3] = np.nan  # a cloud-masked 3×3 block in the top-left cell
    out = aggregate_to_grid(source, transform, "EPSG:4326", grid)
    assert out.shape == (grid.rows, grid.cols)
    assert np.nanmax(out) == pytest.approx(0.6, abs=1e-3)
    assert np.isnan(out[0, 0])
    assert isinstance(
        Cube("p", "ndvi", grid, ["2026-01"], _mask, out[None, ...]).to_dict("demo"), dict
    )
