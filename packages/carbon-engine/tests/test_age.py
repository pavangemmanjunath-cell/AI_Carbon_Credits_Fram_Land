"""Carbon by tree age (``carbon_engine.age``).

Hand-computed reference (girth path), 25 mango, age 60, tropical_dry, no height reported:

    DBH             = 188 cm / π                      = 59.84 cm
    height          = typical 10 m (age 60 ≥ maturity 8 → factor 1)
    AGB per tree    = 0.0673 · (0.55 · 59.84² · 10)^0.976 = 1045.6 kg d.m.   (Chave 2014 eq. 4)
    stand area      = 25 / 150 trees per ha            = 0.1667 ha  → AGB 156.8 t/ha ≥ 20 → R = 0.28
    stock           = 25 · 1.0456 t · 0.47 · 44/12 · (1 + 0.28)        = 57.66 tCO2e
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

import pytest

from carbon_engine import (
    ClimateInput,
    InventoryInput,
    ModelParams,
    ParameterStore,
    PendingParameterError,
    PlotInput,
    TreeBiomassModel,
    UnknownClimateZoneError,
    UnknownSpeciesError,
)
from carbon_engine.age import (
    MAX_CURVE_POINTS,
    METHOD_TIER1,
    METHOD_TIER2,
    AgeAssessment,
    assess_by_age,
)
from carbon_engine.equations.allometric import chave_2014_agb_kg
from carbon_engine.errors import ModelInputError

DRY = ClimateInput("tropical_dry", "region default (IN)")
YEAR = 2026


def assess(store: ParameterStore, **overrides) -> AgeAssessment:
    args = {
        "species_id": "mango",
        "age_years": 60,
        "tree_count": 25,
        "climate": DRY,
        "as_of_year": YEAR,
    }
    args.update(overrides)
    return assess_by_age(store, **args)


def param(assessment: AgeAssessment, name: str):
    return next(p for p in assessment.parameters_used if p.name == name)


# ----------------------------------------------------------------------- hand-computed Tier 1
def test_tier1_reference_case_hand_computed(store):
    """25 mango, age 60, tropical_dry, stand at the reference density (150 trees/ha).

    G_w 4.0 × multiplier 0.9 = 3.6 t d.m./ha/yr (density factor 1, survival 1). Ramp 6 years and
    maturity at 8 years (then 50 %) give a cumulative factor of
    (1+2+3+4+5)/6 + 3 + 52 × 0.5 = 31.5 → 113.4 t d.m./ha above ground. The above-ground stock
    stays under 20 t/ha for ages 1-8 (R = 0.56, factor 5.5) and R = 0.28 after (factor 26):

        Δbiomass = 3.6 × (5.5 × 1.56 + 26 × 1.28) = 150.7 t/ha → × 0.47 × 44/12 = 259.7 tCO2e/ha
        stored   = 259.7 × (25 / 150 ha)                     = 43.28 tCO2e   (± 30 %)
        annual   = 3.6 × 0.5 × 1.28 × 0.47 × 44/12 × (25/150) =  0.662 tCO2e/yr (age 60)
    """
    result = assess(store)
    assert result.stored_now.central == pytest.approx(43.28, abs=0.01)
    assert result.stored_now.low == pytest.approx(43.28 * 0.7, abs=0.01)
    assert result.stored_now.high == pytest.approx(43.28 * 1.3, abs=0.01)
    assert result.annual_now.central == pytest.approx(0.662, abs=0.001)
    assert result.annual_now.low == pytest.approx(0.662 * 0.7, abs=0.001)
    assert result.per_tree_stored_now_kg_co2e == pytest.approx(1731.3, abs=0.2)
    assert result.per_tree_annual_now_kg_co2e == pytest.approx(26.5, abs=0.1)


# ----------------------------------------------------------------------- the age curve
def test_stored_curve_is_monotonic_ordered_and_covers_the_horizon(store):
    result = assess(store)
    assert result.method == METHOD_TIER1 and result.curve_method == METHOD_TIER1
    ages = [p.age for p in result.curve]
    assert ages == list(range(0, 81))  # max(60 + 20, 40)
    stored = [p.stored for p in result.curve]
    assert stored == sorted(stored)
    assert all(p.stored_low <= p.stored <= p.stored_high for p in result.curve)
    assert all(p.annual >= 0 for p in result.curve)
    assert result.curve[0].stored == 0.0 and result.curve[0].annual == 0.0


@pytest.mark.parametrize(("age", "last_age"), [(0, 40), (5, 40), (19, 40), (20, 40), (21, 41)])
def test_curve_has_at_least_forty_years(store, age, last_age):
    result = assess(store, age_years=age)
    assert result.curve[-1].age == last_age
    assert len(result.curve) == last_age + 1


def test_stored_now_is_the_curve_at_todays_age_on_the_tier1_path(store):
    result = assess(store, age_years=33)
    today = next(p for p in result.curve if p.age == 33)
    assert result.stored_now.central == pytest.approx(today.stored, abs=1e-9)
    assert result.stored_now.low == pytest.approx(today.stored_low, abs=1e-9)
    assert result.stored_now.high == pytest.approx(today.stored_high, abs=1e-9)
    assert result.annual_now.central == pytest.approx(today.annual, abs=1e-9)
    assert result.stored_now.unit == "tCO2e" and result.annual_now.unit == "tCO2e/yr"


def test_very_old_trees_keep_a_thinned_curve_that_still_reaches_today(store):
    result = assess(store, age_years=300)
    ages = [p.age for p in result.curve]
    assert len(ages) <= MAX_CURVE_POINTS
    assert ages == sorted(set(ages))
    assert ages[0] == 0 and 300 in ages and ages[-1] == 320
    today = next(p for p in result.curve if p.age == 300)
    assert result.stored_now.central == pytest.approx(today.stored, abs=1e-9)
    # a stock cannot be read past the end of the model run: it must be the age-300 value
    assert result.stored_now.central > next(p for p in result.curve if p.age == 150).stored


def test_curve_is_not_thinned_while_it_fits_in_the_point_limit(store):
    result = assess(store, age_years=129)  # horizon 149 -> ages 0..149 = 150 points
    assert [p.age for p in result.curve] == list(range(0, MAX_CURVE_POINTS))


def test_curve_one_year_past_the_point_limit_is_thinned_but_complete(store):
    result = assess(store, age_years=130)  # horizon 150 would need 151 points
    ages = [p.age for p in result.curve]
    assert len(ages) <= MAX_CURVE_POINTS
    assert ages == sorted(set(ages))
    assert ages[0] == 0 and 130 in ages and ages[-1] == 150


# ----------------------------------------------------------------------- age 0 = planning
def test_age_zero_is_planning_new_trees(store):
    result = assess(store, age_years=0)
    assert result.stored_now.central == 0.0 and result.annual_now.central == 0.0
    assert result.stored_now.high == 0.0 and result.annual_now.high == 0.0
    assert result.per_tree_stored_now_kg_co2e == 0.0
    assert result.per_tree_annual_now_kg_co2e == 0.0
    assert result.curve[-1].stored > 0  # the scenario ahead still accumulates carbon
    assert any("planning to plant" in note for note in result.notes)
    # planned trees keep the model's configured default survival (some will die)
    survival = param(result, "survival_rate")
    default = store.assumption_param("survival_rate_default", "fraction")
    assert survival.value == default.value and survival.value < 1.0


def test_existing_trees_are_counted_alive_and_the_basis_is_documented(store):
    result = assess(store, age_years=12)
    survival = param(result, "survival_rate")
    assert survival.value == 1.0
    assert "counted alive" in survival.source and "reported" not in survival.source
    assert survival.verification_status == "assumption"
    assert any("counted as alive" in note for note in result.notes)


def test_existing_trees_store_more_than_the_same_trees_planted_with_default_survival(store):
    planned = assess(store, age_years=0)
    existing = assess(store, age_years=10)
    # same growth up to age 10, but the planned stand loses part of its trees; the ratio is at
    # most 1 / survival (the root-to-shoot class changes with the per-hectare stock)
    survival = float(param(planned, "survival_rate").value)
    ratio = existing.curve[10].stored / planned.curve[10].stored
    assert 1.0 < ratio <= 1.0 / survival + 1e-9


# ----------------------------------------------------------------------- reuse of the model
def test_tier1_matches_the_tree_biomass_model_exactly(store):
    """Nothing is re-implemented: 1000 trees (one copy) must equal a direct model run."""
    result = assess(store, age_years=12, tree_count=1000)
    direct = TreeBiomassModel(store).estimate(
        PlotInput(area_hectares=1000 / 150),
        InventoryInput("mango", 1000, YEAR - 12, survival_rate=1.0),
        DRY,
        ModelParams(horizon_years=40, as_of_year=YEAR),
    )
    assert result.stored_now.central == pytest.approx(direct.stock.central, abs=0.01)
    assert result.stored_now.low == pytest.approx(direct.stock.low, abs=0.01)
    assert result.stored_now.high == pytest.approx(direct.stock.high, abs=0.01)
    point = direct.annual_series[12]
    assert result.annual_now.central == pytest.approx(point.central, abs=0.001)
    assert [p.stored for p in result.curve] == [
        pytest.approx(s.cum_central, abs=0.001) for s in direct.annual_series
    ]


def test_every_parameter_is_cited_and_the_methodology_is_ipcc(store):
    result = assess(store)
    assert result.parameters_used
    for p in result.parameters_used:
        assert p.source and p.verification_status in {"verified", "assumption", "pending"}
    names = {p.name for p in result.parameters_used}
    assert {"above_ground_biomass_growth", "carbon_fraction", "root_to_shoot_ratio"} <= names
    assert {"survival_rate", "stand_area_hectares"} <= names
    assert result.methodology.id == "ipcc-2006-vol4-ch4"
    assert result.model_id == store.model_id
    assert result.certified is False and "not an issued carbon credit" in result.disclaimer
    assert result.provenance["sources"] and result.provenance["parameter_set"]["id"]


# ----------------------------------------------------------------------- per-tree figures
@pytest.mark.parametrize("age", [0, 1, 7, 25, 60, 150])
@pytest.mark.parametrize("trees", [1, 7, 25, 999, 1000, 5000])
def test_per_tree_times_count_equals_the_totals(store, age, trees):
    result = assess(store, age_years=age, tree_count=trees)
    stored_kg = result.per_tree_stored_now_kg_co2e * trees
    annual_kg = result.per_tree_annual_now_kg_co2e * trees
    # totals are rounded to 3 decimals of tCO2e (1 kg), per-tree figures to 0.1 kg
    tolerance = 1.0 + trees * 0.1
    assert stored_kg == pytest.approx(result.stored_now.central * 1000, rel=2e-3, abs=tolerance)
    assert annual_kg == pytest.approx(result.annual_now.central * 1000, rel=2e-3, abs=tolerance)


def test_a_tree_is_worth_the_same_whether_you_have_one_or_many(store):
    """Tier 1 is linear in stand size at constant density, so the per-tree figure is stable."""
    reference = assess(store, tree_count=5000)
    for trees in (1, 2, 3, 25, 400, 999):
        other = assess(store, tree_count=trees)
        assert other.per_tree_stored_now_kg_co2e == pytest.approx(
            reference.per_tree_stored_now_kg_co2e, rel=2e-3
        )
        assert other.per_tree_annual_now_kg_co2e == pytest.approx(
            reference.per_tree_annual_now_kg_co2e, rel=2e-3
        )


def test_totals_scale_with_tree_count(store):
    one = assess(store, tree_count=10)
    ten = assess(store, tree_count=100)
    assert ten.stored_now.central == pytest.approx(10 * one.stored_now.central, rel=2e-3)
    assert ten.annual_now.central == pytest.approx(10 * one.annual_now.central, rel=2e-3)


# ----------------------------------------------------------------------- girth path
def test_girth_path_uses_chave_and_differs_from_tier1(store):
    tier1 = assess(store)
    girth = assess(store, girth_cm=188.0)
    assert girth.method == METHOD_TIER2
    assert girth.curve_method == METHOD_TIER1  # the curve is still the age-only scenario
    assert girth.stored_now.central != tier1.stored_now.central
    assert girth.annual_now.central != tier1.annual_now.central
    assert girth.curve == tier1.curve

    dbh = 188.0 / math.pi
    agb_kg = chave_2014_agb_kg(0.55, dbh, 10.0)
    expected = 25 * agb_kg / 1000 * 0.47 * (44 / 12) * (1 + 0.28)
    assert girth.stored_now.central == pytest.approx(expected, rel=2e-3)
    assert girth.stored_now.low == pytest.approx(
        expected * 0.8, rel=2e-3
    )  # Tier 2 uncertainty ±20 %
    assert girth.stored_now.high == pytest.approx(expected * 1.2, rel=2e-3)
    assert girth.annual_now.central == pytest.approx(expected / 60, rel=2e-3)  # stock ÷ age
    assert param(girth, "average_dbh_cm").value == pytest.approx(dbh, abs=0.01)
    assert any("÷ age" in note or "divided by age" in note for note in girth.notes)
    assert any("tier1-age" in note for note in girth.notes)
    assert girth.confidence in {"medium", "high"} and tier1.confidence == "low"


def test_girth_path_uses_the_reported_height(store):
    short = assess(store, girth_cm=188.0, height_m=5.0)
    tall = assess(store, girth_cm=188.0, height_m=20.0)
    assert short.stored_now.central < tall.stored_now.central
    assert param(tall, "average_height_m").value == 20.0
    assert tall.confidence == "high"  # count, species, age, DBH and height supplied


def test_girth_path_per_tree_times_count_equals_totals(store):
    result = assess(store, girth_cm=120.0, tree_count=3)
    assert result.per_tree_stored_now_kg_co2e * 3 == pytest.approx(
        result.stored_now.central * 1000, rel=2e-3
    )
    # a single tree: one tenth of ten trees
    one = assess(store, girth_cm=120.0, tree_count=1)
    ten = assess(store, girth_cm=120.0, tree_count=10)
    assert one.per_tree_stored_now_kg_co2e == pytest.approx(
        ten.per_tree_stored_now_kg_co2e, rel=2e-3
    )


@pytest.mark.parametrize("girth", [10.0, 15.0, 1500.0])
def test_girth_outside_the_chave_calibration_range_is_flagged(store, girth):
    assert any("outside" in note for note in assess(store, girth_cm=girth).notes)


def test_girth_inside_the_calibration_range_has_no_range_warning(store):
    assert not any("outside" in note for note in assess(store, girth_cm=188.0).notes)


def test_height_without_girth_is_ignored_with_a_note(store):
    with_height = assess(store, height_m=12.0)
    assert with_height.stored_now == assess(store).stored_now
    assert any("ignored" in note for note in with_height.notes)


# ----------------------------------------------------------------------- area and notes
def test_area_supplied_applies_the_models_density_factor(store):
    """With an area the model's own density factor (clamped) applies; without one it is 1.0."""
    default = assess(store, age_years=20)
    assert param(default, "stand_area_hectares").value == pytest.approx(25 / 150, abs=1e-4)
    assert "reference density" in param(default, "stand_area_hectares").source
    assert param(default, "density_factor_applied").value == pytest.approx(1.0, abs=1e-3)
    assert any("reference density" in note for note in default.notes)

    # half the reference density: ratio 0.5 is inside the model's clamp
    inside = assess(store, age_years=20, area_hectares=25 / 150 * 2)
    assert param(inside, "stand_area_hectares").source == "supplied by the caller"
    assert param(inside, "density_factor_applied").value == pytest.approx(0.5, abs=1e-3)
    assert not any("No area was given" in note for note in inside.notes)
    assert not any("clamped" in note for note in inside.notes)
    assert inside.stored_now.central > 0

    # twice the reference density: ratio 2.0 is capped at 1.5 on half the area
    dense = assess(store, age_years=20, area_hectares=25 / 150 / 2)
    assert param(dense, "density_factor_applied").value == pytest.approx(1.5)
    assert dense.per_tree_stored_now_kg_co2e < default.per_tree_stored_now_kg_co2e
    assert any("clamped" in note for note in dense.notes)

    # one tenth of the reference density: ratio 0.1 is floored to 0.2 (the model's own rule)
    sparse = assess(store, age_years=20, area_hectares=25 / 150 * 10)
    assert param(sparse, "density_factor_applied").value == pytest.approx(0.2)
    assert any("clamped" in note for note in sparse.notes)


def test_old_tree_note_appears_after_maturity_only(store):
    old = assess(store, age_years=60)
    young = assess(store, age_years=3)
    assert any("measure trunk girth" in note for note in old.notes)
    assert not any("measure trunk girth" in note for note in young.notes)
    assert any("post-maturity" in note for note in old.notes)


def test_pending_parameters_are_flagged_in_notes_and_provenance(store):
    result = assess(store)
    pending = {p.name for p in result.parameters_used if p.verification_status == "pending"}
    assert pending  # the Tier 1 growth table is still pending in the shipped configuration
    assert any("pending verification" in note for note in result.notes)
    assert result.provenance["parameter_set"]["verification_status"] == "pending"


def test_notes_do_not_repeat_the_plot_headline(store):
    for result in (assess(store), assess(store, girth_cm=150.0)):
        assert not any(n.startswith(("Headline estimate", "Climate zone")) for n in result.notes)


# ----------------------------------------------------------------------- production gate
def test_pending_parameters_are_refused_when_not_allowed(store):
    with pytest.raises(PendingParameterError) as excinfo:
        assess(store, allow_pending=False)
    assert "above_ground_biomass_growth" in excinfo.value.names
    with pytest.raises(PendingParameterError):
        assess(store, allow_pending=False, girth_cm=188.0)
    with pytest.raises(PendingParameterError):
        assess(store, allow_pending=False, age_years=0)


def test_pending_parameters_are_allowed_by_default(store):
    assert assess(store).stored_now.central > 0


# ----------------------------------------------------------------------- inputs
def test_as_of_year_defaults_to_the_current_year(store):
    result = assess_by_age(store, "mango", 10, 20, DRY)
    assert result.as_of_year == datetime.now(UTC).year
    assert result.plantation_year == result.as_of_year - 10


def test_result_depends_on_age_not_on_the_calendar(store):
    assert (
        assess(store, age_years=30, as_of_year=2020).stored_now
        == assess(store, age_years=30, as_of_year=2031).stored_now
    )
    assert assess(store, age_years=30, as_of_year=2020).plantation_year == 1990


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"age_years": -1}, "age_years"),
        ({"tree_count": 0}, "tree_count"),
        ({"girth_cm": 0.0}, "girth_cm"),
        ({"girth_cm": -5.0}, "girth_cm"),
        ({"girth_cm": 100.0, "age_years": 0}, "girth_cm needs age_years"),
        ({"height_m": 0.0}, "height_m"),
        ({"area_hectares": 0.0}, "area_hectares"),
    ],
)
def test_out_of_domain_inputs_raise_model_input_error(store, overrides, message):
    with pytest.raises(ModelInputError, match=message):
        assess(store, **overrides)


def test_unknown_species_and_zone_raise_engine_errors(store):
    with pytest.raises(UnknownSpeciesError):
        assess(store, species_id="no-such-tree")
    with pytest.raises(UnknownClimateZoneError):
        assess(store, climate=ClimateInput("no-such-zone"))


# ----------------------------------------------------------------------- every species
def _species_cases(store: ParameterStore):
    for species in store.species_list():
        yield species["id"], species["suitable_climate_zones"][0]


def test_every_species_in_the_table_can_be_assessed(store):
    for species_id, zone in _species_cases(store):
        result = assess(store, species_id=species_id, climate=ClimateInput(zone), age_years=30)
        stored = [p.stored for p in result.curve]
        assert stored == sorted(stored), species_id
        assert result.per_tree_stored_now_kg_co2e > 0, species_id
        girth = assess(
            store, species_id=species_id, climate=ClimateInput(zone), age_years=30, girth_cm=120.0
        )
        assert girth.method == METHOD_TIER2 and girth.stored_now.central > 0, species_id


# ----------------------------------------------------------------------- serialisation
def test_to_dict_is_json_ready_and_has_the_contract_shape(store):
    for result in (assess(store), assess(store, girth_cm=188.0), assess(store, age_years=0)):
        data = json.loads(json.dumps(result.to_dict()))
        assert set(data) >= {
            "method",
            "curve_method",
            "stored_now",
            "annual_now",
            "per_tree",
            "curve",
            "parameters_used",
            "notes",
            "confidence",
            "model",
            "methodology",
        }
        assert set(data["stored_now"]) == {"low", "central", "high", "unit"}
        assert set(data["per_tree"]) == {"stored_now_kg_co2e", "annual_now_kg_co2e"}
        assert set(data["curve"][0]) == {"age", "stored", "stored_low", "stored_high", "annual"}
        assert data["confidence"] in {"low", "medium", "high"}
        for item in data["parameters_used"]:
            assert set(item) == {"name", "value", "unit", "source", "verification_status"}
        assert result.certified is False
