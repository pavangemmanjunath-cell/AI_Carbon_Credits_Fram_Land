from __future__ import annotations

import numpy as np
import pytest

from geo_engine.climate import classify_climate_zone, estimate_pet_mm, zone_label
from geo_engine.indices import (
    classify_ndmi,
    classify_ndvi,
    ndmi,
    ndre,
    ndvi,
    plot_statistics,
    scl_clear_mask,
)
from geo_engine.indices.classify import trend_statement
from geo_engine.indices.masks import apply_mask


def test_ndvi_hand_computed():
    nir = np.array([[0.5, 0.3, 0.0]], dtype=np.float32)
    red = np.array([[0.1, 0.3, 0.0]], dtype=np.float32)
    out = ndvi(nir, red)
    assert out[0, 0] == pytest.approx((0.5 - 0.1) / 0.6)
    assert out[0, 1] == pytest.approx(0.0)
    assert np.isnan(out[0, 2])


def test_ndmi_and_ndre_follow_the_same_form():
    nir = np.array([0.4], dtype=np.float32)
    assert ndmi(nir, np.array([0.2], dtype=np.float32))[0] == pytest.approx(0.2 / 0.6)
    assert ndre(nir, np.array([0.3], dtype=np.float32))[0] == pytest.approx(0.1 / 0.7)


def test_scl_mask_keeps_only_4_5_6():
    scl = np.array([[0, 3, 4], [5, 6, 9]])
    clear = scl_clear_mask(scl)
    assert clear.tolist() == [[False, False, True], [True, True, False]]
    masked = apply_mask(np.ones_like(scl, dtype=np.float32), clear)
    assert np.isnan(masked[0, 0]) and masked[1, 1] == 1.0


@pytest.mark.parametrize(
    "value, cls",
    [
        (0.1, "sparse"),
        (0.299, "sparse"),
        (0.3, "moderate"),
        (0.59, "moderate"),
        (0.6, "healthy"),
        (0.9, "healthy"),
        (None, None),
        (float("nan"), None),
    ],
)
def test_ndvi_classes(value, cls):
    assert classify_ndvi(value) == cls


@pytest.mark.parametrize(
    "value, cls",
    [(-0.1, "dry"), (0.0, "moderate"), (0.29, "moderate"), (0.3, "moist"), (0.5, "moist")],
)
def test_ndmi_classes(value, cls):
    assert classify_ndmi(value) == cls


def test_plot_statistics_ignore_nan_and_report_valid_share():
    values = np.array([[0.2, np.nan], [0.6, 0.4]], dtype=np.float32)
    inside = np.array([[True, True], [True, False]])
    stats = plot_statistics(values, inside)
    assert stats.mean == pytest.approx(0.4)
    assert stats.min == pytest.approx(0.2)
    assert stats.max == pytest.approx(0.6)
    assert stats.valid_share == pytest.approx(2 / 3, abs=1e-4)
    empty = plot_statistics(np.full((2, 2), np.nan, dtype=np.float32))
    assert empty.mean is None and empty.valid_share == 0.0


def test_trend_statement_wording():
    assert "increased approximately 23%" in trend_statement(22.6)
    assert "decreased approximately 10%" in trend_statement(-10.2)
    assert "stable" in trend_statement(2.0)
    assert "could not be evaluated" in trend_statement(None)


def test_pet_approximation_values():
    assert estimate_pet_mm(10.0) == pytest.approx(600.0)
    assert estimate_pet_mm(0.0) == pytest.approx(300.0)
    assert estimate_pet_mm(-30.0) == 0.0


@pytest.mark.parametrize(
    "mat, precip, elev, zone",
    [
        (24.1, 820, 880, "tropical_dry"),
        (26.0, 1500, 100, "tropical_moist"),
        (26.0, 2500, 100, "tropical_wet"),
        (19.0, 900, 1500, "tropical_mountain"),
        (17.5, 1250, 150, "warm_temperate_moist"),  # Georgia, USA
        (17.8, 550, 120, "warm_temperate_dry"),  # Andalusia
        (9.0, 620, 110, "cool_temperate_moist"),  # Dresden
        (8.0, 300, 500, "cool_temperate_dry"),
        (-2.0, 500, 200, "boreal"),
    ],
)
def test_climate_zone_decision_tree(mat, precip, elev, zone):
    result = classify_climate_zone(mat, precip, elev)
    assert result.zone == zone
    assert result.verification_status == "assumption"
    assert result.label == zone_label(zone)
    assert "IPCC" in result.source
