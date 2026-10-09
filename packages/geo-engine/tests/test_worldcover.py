from __future__ import annotations

import numpy as np

from geo_engine.raster import (
    WORLDCOVER_CLASSES,
    class_name,
    class_shares,
    tile_name,
    tiles_for_bbox,
)
from geo_engine.raster.worldcover import share_of


def test_class_table_matches_product_manual():
    assert WORLDCOVER_CLASSES[10] == "Tree cover"
    assert WORLDCOVER_CLASSES[40] == "Cropland"
    assert WORLDCOVER_CLASSES[95] == "Mangroves"
    assert WORLDCOVER_CLASSES[100] == "Moss and lichen"
    assert len(WORLDCOVER_CLASSES) == 11
    assert class_name(42).startswith("Unknown")


def test_tile_names_use_lower_left_corner_floored_to_3_degrees():
    assert tile_name(77.54, 13.29) == "ESA_WorldCover_10m_2021_v200_N12E075_Map.tif"
    assert tile_name(-83.62, 32.62) == "ESA_WorldCover_10m_2021_v200_N30W084_Map.tif"
    assert tile_name(-5.1, 37.6) == "ESA_WorldCover_10m_2021_v200_N36W006_Map.tif"
    assert tile_name(-84.4, -0.5) == "ESA_WorldCover_10m_2021_v200_S03W087_Map.tif"
    assert tile_name(0.0, 0.0) == "ESA_WorldCover_10m_2021_v200_N00E000_Map.tif"
    assert tile_name(3.0, 3.0) == "ESA_WorldCover_10m_2021_v200_N03E003_Map.tif"
    assert tile_name(-3.0, -3.0) == "ESA_WorldCover_10m_2021_v200_S03W003_Map.tif"


def test_tiles_for_bbox_crossing_a_tile_boundary():
    names = tiles_for_bbox((74.9, 11.9, 75.1, 12.1))
    assert set(names) == {
        "ESA_WorldCover_10m_2021_v200_N09E072_Map.tif",
        "ESA_WorldCover_10m_2021_v200_N09E075_Map.tif",
        "ESA_WorldCover_10m_2021_v200_N12E072_Map.tif",
        "ESA_WorldCover_10m_2021_v200_N12E075_Map.tif",
    }
    assert tiles_for_bbox((77.5, 13.2, 77.6, 13.3)) == [
        "ESA_WorldCover_10m_2021_v200_N12E075_Map.tif"
    ]


def test_class_shares_from_synthetic_raster():
    arr = np.zeros((10, 10), dtype=np.uint8)
    arr[:, :6] = 40  # 60 cropland
    arr[:, 6:9] = 10  # 30 tree cover
    arr[:, 9] = 0  # nodata column (excluded)
    inside = np.ones_like(arr, dtype=bool)
    inside[0, :] = False  # first row outside the polygon
    shares = class_shares(arr, plot_area_ha=2.0, valid_mask=inside)
    # inside & not nodata: 9 rows × 9 cols = 81 px: 54 cropland, 27 tree cover
    assert [s.code for s in shares] == [40, 10]
    assert shares[0].share == round(54 / 81, 4)
    assert shares[1].share == round(27 / 81, 4)
    assert shares[0].area_ha + shares[1].area_ha == 2.0
    assert share_of(shares, 10) == round(27 / 81, 4)
    assert share_of(shares, 50) == 0.0
    assert class_shares(np.zeros((3, 3), dtype=np.uint8), 1.0) == []
