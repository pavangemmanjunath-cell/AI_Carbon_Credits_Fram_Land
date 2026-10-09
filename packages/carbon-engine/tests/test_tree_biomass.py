"""Hand-computed expectations for the tree-biomass model (v0.1).

Reference case: 420 mango on 2.13 ha planted 2023, tropical_dry, survival 0.85.

    planted density   = 420 / 2.13 = 197.18 trees/ha
    density_factor    = clamp(197.18 / 150, 0.2, 1.5) = 1.3146
    full increment    = G_w 4.0 × multiplier 0.9 × 1.3146 × survival 0.85 = 4.0225 t d.m./ha/yr
    age 3 (2026)      : ramp = 3/6 → ΔAGB = 2.0113 t/ha ; AGB stock = 4.0225 t/ha (< 20 → R = 0.56)
                        ΔCO₂e = 2.0113 × 1.56 × 0.47 × 3.6667 × 2.13 ha = 11.517 tCO₂e
"""

from __future__ import annotations

import pytest

from carbon_engine import (
    ClimateInput,
    InventoryInput,
    ModelParams,
    PendingParameterError,
    PlotInput,
    UnknownClimateZoneError,
    UnknownSpeciesError,
)
from carbon_engine.errors import ModelInputError, ModelNotImplementedError
from carbon_engine.models import get_model

PLOT = PlotInput(area_hectares=2.13, plot_id="PLT-TEST01", has_satellite_observation=True)
MANGO = InventoryInput("mango", 420, 2023, survival_rate=0.85)
TROPICAL_DRY = ClimateInput("tropical_dry")
PARAMS = ModelParams(as_of_year=2026)


def test_tier1_reference_case_hand_computed(model):
    est = model.estimate(PLOT, MANGO, TROPICAL_DRY, PARAMS)
    assert est.tier == "1"
    series = {p.age: p for p in est.annual_series}
    assert series[0].central == 0.0
    assert series[3].central == pytest.approx(11.517, abs=0.002)
    assert series[3].low == pytest.approx(11.517 * 0.7, abs=0.002)
    assert series[3].high == pytest.approx(11.517 * 1.3, abs=0.002)
    # full increment reached at age 6 and held until maturity (8)
    assert series[6].central == pytest.approx(series[7].central)
    # cumulative sums are monotone and stock equals cumulative at as_of_year
    cums = [p.cum_central for p in est.annual_series]
    assert cums == sorted(cums)
    assert est.stock.central == pytest.approx(series[3].cum_central, abs=0.01)
    assert est.stock.unit == "tCO2e" and est.estimate.unit == "tCO2e/yr"
    # headline = mean over the horizon (30 years)
    assert est.estimate.central == pytest.approx(cums[-1] / 30, abs=0.01)
    assert est.components["above_ground_tco2e_yr"] > est.components["below_ground_tco2e_yr"] > 0
    assert est.certified is False
    assert est.confidence == "medium"
    assert est.methodology.id == "ipcc-2006-vol4-ch4"


def test_ramp_and_maturity_shape_with_constant_root_to_shoot(model):
    # tropical_wet has a single root-to-shoot class (0.37), so the shape is pure ramp/maturity
    est = model.estimate(PLOT, MANGO, ClimateInput("tropical_wet"), PARAMS)
    series = {p.age: p for p in est.annual_series}
    full = series[6].central
    assert series[1].central == pytest.approx(full / 6, abs=2e-3)
    assert series[3].central == pytest.approx(full / 2, abs=2e-3)
    assert series[8].central == pytest.approx(full)
    assert series[9].central == pytest.approx(full * 0.5)  # post_maturity_increment_factor
    assert series[30].central == pytest.approx(full * 0.5)
    r = [p for p in est.parameters_used if p.name == "root_to_shoot_ratio"]
    assert len(r) == 1 and r[0].value == 0.37


def test_bounds_ordered_and_series_length(model):
    est = model.estimate(PLOT, MANGO, TROPICAL_DRY, ModelParams(as_of_year=2026, horizon_years=20))
    assert len(est.annual_series) == 21
    assert est.estimate.low <= est.estimate.central <= est.estimate.high
    assert est.stock.low <= est.stock.central <= est.stock.high
    for point in est.annual_series:
        assert point.low <= point.central <= point.high
        assert point.cum_low <= point.cum_central <= point.cum_high


def test_monotonic_in_tree_count_until_density_clamp(model):
    previous = 0.0
    for count in (50, 100, 200, 300):
        est = model.estimate(
            PLOT, InventoryInput("mango", count, 2023, survival_rate=0.85), TROPICAL_DRY, PARAMS
        )
        assert est.estimate.central > previous
        previous = est.estimate.central
    # beyond the clamp (1.5 × 150 × 2.13 ≈ 479 trees) the estimate stops growing
    clamped_a = model.estimate(
        PLOT, InventoryInput("mango", 600, 2023, survival_rate=0.85), TROPICAL_DRY, PARAMS
    )
    clamped_b = model.estimate(
        PLOT, InventoryInput("mango", 1200, 2023, survival_rate=0.85), TROPICAL_DRY, PARAMS
    )
    assert clamped_a.estimate.central == pytest.approx(clamped_b.estimate.central)
    assert any("clamped" in n for n in clamped_b.notes)
    applied = next(p for p in clamped_b.parameters_used if p.name == "density_factor_applied")
    assert applied.value == 1.5
    sparse = model.estimate(
        PLOT, InventoryInput("mango", 5, 2023, survival_rate=0.85), TROPICAL_DRY, PARAMS
    )
    assert (
        next(p for p in sparse.parameters_used if p.name == "density_factor_applied").value == 0.2
    )


def test_zero_trees_gives_zero(model):
    est = model.estimate(
        PLOT, InventoryInput("mango", 0, 2023, survival_rate=0.85), TROPICAL_DRY, PARAMS
    )
    assert est.estimate.central == 0.0 and est.stock.central == 0.0
    assert all(p.central == 0.0 for p in est.annual_series)


def test_survival_scales_linearly(model):
    wet = ClimateInput("tropical_wet")  # constant root-to-shoot ratio
    full = model.estimate(PLOT, InventoryInput("mango", 420, 2023, survival_rate=1.0), wet, PARAMS)
    half = model.estimate(PLOT, InventoryInput("mango", 420, 2023, survival_rate=0.5), wet, PARAMS)
    assert half.estimate.central == pytest.approx(full.estimate.central * 0.5, rel=1e-3)
    # in tropical_dry the above-ground part is still linear; the below-ground part follows the
    # IPCC Table 4.4 stock class (lower surviving stock → higher R), so the total is not
    dry_full = model.estimate(
        PLOT, InventoryInput("mango", 420, 2023, survival_rate=1.0), TROPICAL_DRY, PARAMS
    )
    dry_half = model.estimate(
        PLOT, InventoryInput("mango", 420, 2023, survival_rate=0.5), TROPICAL_DRY, PARAMS
    )
    assert dry_half.components["above_ground_tco2e_yr"] == pytest.approx(
        dry_full.components["above_ground_tco2e_yr"] * 0.5, rel=1e-2
    )


def test_default_survival_comes_from_config(model, store):
    est = model.estimate(PLOT, InventoryInput("mango", 420, 2023), TROPICAL_DRY, PARAMS)
    survival = next(p for p in est.parameters_used if p.name == "survival_rate")
    assert survival.value == store.assumption("survival_rate_default")["value"]
    assert survival.verification_status == "assumption"


def test_parameters_used_carry_source_and_status(model):
    est = model.estimate(PLOT, MANGO, TROPICAL_DRY, PARAMS)
    names = {p.name for p in est.parameters_used}
    assert {
        "above_ground_biomass_growth",
        "carbon_fraction",
        "co2_per_c",
        "root_to_shoot_ratio",
        "increment_multiplier",
        "reference_density_per_ha",
        "survival_rate",
        "years_to_full_increment_default",
        "post_maturity_increment_factor",
    } <= names
    for p in est.parameters_used:
        assert p.source and p.verification_status in {"verified", "pending", "assumption"}
    cf = next(p for p in est.parameters_used if p.name == "carbon_fraction")
    assert cf.value == 0.47 and cf.verification_status == "verified"
    assert est.provenance["parameter_set"]["verification_status"] == "pending"
    assert est.provenance["model"] == {"id": "tree-biomass", "version": "0.1.0"}
    assert est.provenance["sources"][0]["id"] == "ipcc-2006-vol4-ch4"


def test_production_mode_refuses_pending_parameters(model):
    with pytest.raises(PendingParameterError) as excinfo:
        model.estimate(
            PLOT, MANGO, TROPICAL_DRY, ModelParams(as_of_year=2026, allow_pending_parameters=False)
        )
    assert "above_ground_biomass_growth" in excinfo.value.names


def test_other_climate_zones_and_root_to_shoot_classes(model):
    temperate = model.estimate(
        PlotInput(area_hectares=8.0),
        InventoryInput("pecan", 1200, 2021, survival_rate=0.9),
        ClimateInput("warm_temperate_moist"),
        PARAMS,
    )
    r = [p for p in temperate.parameters_used if p.name == "root_to_shoot_ratio"]
    assert r and r[0].value == 0.46  # agb < 75 t/ha class
    with pytest.raises(UnknownClimateZoneError):
        model.estimate(PLOT, MANGO, ClimateInput("martian"), PARAMS)
    with pytest.raises(UnknownSpeciesError):
        model.estimate(PLOT, InventoryInput("baobab", 10, 2020), TROPICAL_DRY, PARAMS)


def test_unsuitable_zone_is_noted(model):
    est = model.estimate(PLOT, MANGO, ClimateInput("boreal"), PARAMS)
    assert any("not listed as suitable" in n for n in est.notes)


def test_future_planting_has_zero_stock_but_positive_mean(model):
    est = model.estimate(
        PLOT, InventoryInput("mango", 420, 2030, survival_rate=0.85), TROPICAL_DRY, PARAMS
    )
    assert est.stock.central == 0.0
    assert est.estimate.central > 0


def test_tier2_path_hand_computed(model):
    inv = InventoryInput(
        "mango", 420, 2016, average_dbh_cm=20.0, average_height_m=8.0, survival_rate=0.9
    )
    est = model.estimate(PLOT, inv, TROPICAL_DRY, PARAMS)
    assert est.tier == "2"
    agb_kg = 0.0673 * (0.55 * 20.0**2 * 8.0) ** 0.976  # 99.09 kg
    surviving = 420 * 0.9
    agb_t_ha = surviving * agb_kg / 1000 / 2.13  # 17.6 t/ha → R = 0.56
    stock = surviving * agb_kg / 1000 * (1 + 0.56) * 0.47 * 3.6667
    assert est.stock.central == pytest.approx(stock, rel=1e-3)
    assert est.estimate.central == pytest.approx(stock / 10, rel=1e-3)  # age 10 in 2026
    assert est.estimate.low == pytest.approx(stock / 10 * 0.8, rel=1e-3)
    assert est.confidence == "high"
    assert agb_t_ha < 20
    series = {p.age: p for p in est.annual_series}
    assert series[0].central == 0.0
    assert series[1].central == pytest.approx(series[10].central)
    assert series[10].cum_central == pytest.approx(stock, rel=1e-3)
    names = {p.name for p in est.parameters_used}
    assert {"wood_density_g_cm3", "allometry_equation", "agb_per_tree_kg"} <= names


def test_tier2_estimates_height_when_missing_and_flags_temperate_allometry(model):
    inv = InventoryInput("pecan", 500, 2018, average_dbh_cm=15.0, survival_rate=0.9)
    est = model.estimate(
        PlotInput(area_hectares=8.0), inv, ClimateInput("warm_temperate_moist"), PARAMS
    )
    assert est.confidence == "medium"  # height missing
    names = {p.name for p in est.parameters_used}
    assert "height_estimated_m" in names and "species_allometry" in names
    pending = {p.name for p in est.parameters_used if p.verification_status == "pending"}
    assert "species_allometry" in pending
    assert any("Chave" in n for n in est.notes)
    h = next(p for p in est.parameters_used if p.name == "height_estimated_m")
    assert h.value == pytest.approx(18 * 8 / 12, abs=0.01)  # age 8 of 12 maturity years


def test_input_validation(model):
    with pytest.raises(ModelInputError):
        model.estimate(PlotInput(area_hectares=0.0), MANGO, TROPICAL_DRY, PARAMS)
    with pytest.raises(ModelInputError):
        model.estimate(
            PLOT, InventoryInput("mango", 10, 2023, survival_rate=1.5), TROPICAL_DRY, PARAMS
        )


def test_stub_models_name_their_sources():
    for model_id, needle in (
        ("agroforestry", "COMET"),
        ("soil-carbon", "VM0042"),
        ("crop-practice", "VM0042"),
    ):
        stub = get_model(model_id)
        with pytest.raises(ModelNotImplementedError) as excinfo:
            stub.estimate(PLOT, MANGO, TROPICAL_DRY)
        assert needle in str(excinfo.value)
    with pytest.raises(KeyError):
        get_model("unknown-model")


def test_to_dict_shape(model):
    data = model.estimate(PLOT, MANGO, TROPICAL_DRY, PARAMS).to_dict()
    assert data["certified"] is False
    assert data["model"]["tier"] == "1"
    assert set(data["estimate"]) == {"low", "central", "high", "unit"}
    assert data["readiness"]["score"] == 55  # 64 of 116 weight points
    assert data["readiness"]["grade"] == "medium"
    assert {e["id"] for e in data["readiness"]["missing_evidence"]} == {
        "dbh",
        "height",
        "baseline",
        "management",
        "ownership",
    }
