import pytest

from carbon_engine.economics import CostInputs, cost_scenario

REMOVAL = {"low": 200.0, "central": 300.0, "high": 400.0}
PRICES = [{"id": "low", "price_per_tco2e": 10.0}, {"id": "reference", "price_per_tco2e": 20.0}]


def run(costs: CostInputs) -> dict:
    return cost_scenario(
        costs,
        tree_count=100,
        area_hectares=2.0,
        horizon_years=10,
        removal_over_horizon=REMOVAL,
        price_scenarios=PRICES,
        currency="INR",
    )


def test_totals_are_plain_arithmetic_on_the_users_inputs() -> None:
    out = run(
        CostInputs(
            sapling_per_tree=50,
            planting_per_tree=30,
            maintenance_per_ha_per_year=100,
            monitoring_per_year=200,
        )
    )
    assert out["establishment"] == 8_000  # 100 trees × (50 + 30)
    assert out["maintenance_over_horizon"] == 2_000  # 2 ha × 100 × 10 years
    assert out["monitoring_over_horizon"] == 2_000  # 200 × 10 years
    assert out["total_cost"] == 12_000
    assert out["not_entered"] == []


def test_break_even_price_pairs_the_low_price_with_the_high_removal() -> None:
    out = run(CostInputs(sapling_per_tree=120))  # total 12,000
    assert out["break_even_price_per_tco2e"] == {"low": 30.0, "central": 40.0, "high": 60.0}


def test_scenarios_show_value_and_share_of_costs_covered() -> None:
    out = run(CostInputs(sapling_per_tree=120))
    reference = next(s for s in out["price_scenarios"] if s["id"] == "reference")
    assert reference["indicative_value_over_horizon"] == 6_000  # 20 × 300 t
    assert reference["share_of_costs_covered_pct"] == 50.0


def test_nothing_entered_gives_zero_cost_and_no_break_even() -> None:
    out = run(CostInputs())
    assert out["total_cost"] == 0
    assert out["break_even_price_per_tco2e"] == {"low": None, "central": None, "high": None}
    assert set(out["not_entered"]) == {
        "sapling_per_tree",
        "planting_per_tree",
        "maintenance_per_ha_per_year",
        "monitoring_per_year",
    }
    assert out["price_scenarios"][0]["share_of_costs_covered_pct"] is None


def test_never_a_credit_and_never_discounted_silently() -> None:
    out = run(CostInputs(monitoring_per_year=1))
    assert out["certified"] is False
    assert out["discounted"] is False
    assert "not a credit" in out["disclaimer"]


def test_negative_costs_are_rejected() -> None:
    with pytest.raises(ValueError):
        CostInputs(sapling_per_tree=-1)


def test_from_mapping_keeps_missing_values_as_not_entered() -> None:
    costs = CostInputs.from_mapping({"sapling_per_tree": "25"})
    assert costs.sapling_per_tree == 25.0
    assert costs.planting_per_tree is None
    assert costs.entered
