"""Cost scenario: what a planting costs against the carbon it may remove.

Bookkeeping only — no new science and no built-in prices or costs:

* **Costs are the user's own inputs** (in the region's currency). The platform
  ships no default sapling, labour or monitoring cost, because no sourced,
  current figure exists in ``config/`` for every region (CLAUDE.md: never
  invent). A cost left out counts as zero and is listed in ``not_entered``.
* **Removal** is the engine's own cumulative series over the horizon
  (low / central / high).
* **Prices** are the configured market scenarios (``config/market/``).

Outputs:

* ``break_even_price_per_tco2e`` — the carbon price at which an indicative
  value would equal the entered costs: ``total_cost / cumulative_removal``.
  Its range uses the removal range (more removal → lower break-even price).
* per price scenario, the indicative value over the horizon and the share of
  the entered costs it would cover.

Everything is undiscounted and ``certified: False``: an estimate is not a
credit, and a price scenario is not revenue.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

COST_DISCLAIMER = (
    "Costs are your own inputs; carbon prices are scenarios, not offers. Values are undiscounted "
    "and indicative. Removal must be validated, monitored and verified under a recognised "
    "programme before any credit can be issued — this is not a credit or revenue."
)

COST_FIELDS = (
    "sapling_per_tree",
    "planting_per_tree",
    "maintenance_per_ha_per_year",
    "monitoring_per_year",
)


@dataclass(frozen=True)
class CostInputs:
    """User-entered costs in the region's currency. ``None`` means not entered."""

    sapling_per_tree: float | None = None
    planting_per_tree: float | None = None
    maintenance_per_ha_per_year: float | None = None
    monitoring_per_year: float | None = None

    def __post_init__(self) -> None:
        for name in COST_FIELDS:
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must not be negative")

    @property
    def entered(self) -> bool:
        return any(getattr(self, name) is not None for name in COST_FIELDS)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> CostInputs:
        data = data or {}
        return cls(**{name: _opt_float(data.get(name)) for name in COST_FIELDS})


def _opt_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _round(value: float) -> float:
    return round(value, 2)


def cost_scenario(
    costs: CostInputs,
    *,
    tree_count: int,
    area_hectares: float,
    horizon_years: int,
    removal_over_horizon: Mapping[str, float],
    price_scenarios: Sequence[Mapping[str, Any]],
    currency: str,
) -> dict[str, Any]:
    """Totals, break-even carbon price and coverage per price scenario."""
    if tree_count < 0 or area_hectares <= 0 or horizon_years <= 0:
        raise ValueError("tree_count ≥ 0, area_hectares > 0 and horizon_years > 0 are required")
    zero = 0.0
    establishment = tree_count * (
        (costs.sapling_per_tree or zero) + (costs.planting_per_tree or zero)
    )
    maintenance = area_hectares * (costs.maintenance_per_ha_per_year or zero) * horizon_years
    monitoring = (costs.monitoring_per_year or zero) * horizon_years
    total = establishment + maintenance + monitoring

    low = float(removal_over_horizon.get("low", 0.0))
    central = float(removal_over_horizon.get("central", 0.0))
    high = float(removal_over_horizon.get("high", 0.0))

    def per_tonne(tonnes: float) -> float | None:
        return _round(total / tonnes) if tonnes > 0 and total > 0 else None

    scenarios = []
    for scenario in price_scenarios:
        price = float(scenario["price_per_tco2e"])
        value = price * central
        scenarios.append(
            {
                "id": scenario.get("id"),
                "price_per_tco2e": price,
                "indicative_value_over_horizon": _round(value),
                "share_of_costs_covered_pct": _round(100 * value / total) if total > 0 else None,
            }
        )

    return {
        "currency": currency,
        "horizon_years": horizon_years,
        "inputs": {name: getattr(costs, name) for name in COST_FIELDS},
        "not_entered": [name for name in COST_FIELDS if getattr(costs, name) is None],
        "establishment": _round(establishment),
        "maintenance_over_horizon": _round(maintenance),
        "monitoring_over_horizon": _round(monitoring),
        "total_cost": _round(total),
        "removal_over_horizon_tco2e": {"low": low, "central": central, "high": high},
        "break_even_price_per_tco2e": {
            # more removal → lower price needed, so the low price pairs with high removal
            "low": per_tonne(high),
            "central": per_tonne(central),
            "high": per_tonne(low),
        },
        "price_scenarios": scenarios,
        "discounted": False,
        "certified": False,
        "disclaimer": COST_DISCLAIMER,
    }
