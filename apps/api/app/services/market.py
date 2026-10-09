"""Indicative value scenarios: estimate × configured price scenarios. Never a quote."""

from __future__ import annotations

from typing import Any

from app.services.regions import RegionConfig

DISCLAIMER = (
    "Market-value scenario — not guaranteed revenue. Issuance depends on methodology, "
    "additionality, verification, permanence and market conditions."
)


class MarketService:
    def __init__(self, regions: RegionConfig) -> None:
        self.regions = regions

    def scenarios_for(self, region_id: str, estimate: dict[str, Any]) -> dict[str, Any]:
        config = self.regions.market_scenarios(region_id)
        currency = str(config.get("currency"))
        symbol = str(config.get("currency_symbol", ""))
        rows = []
        for key, label in (("low", "low"), ("reference", "reference"), ("high", "high")):
            entry = config.get(key) or {}
            price = float(entry.get("price_per_tco2e", 0))
            rows.append(
                {
                    "id": label,
                    "label": entry.get("label", label.title()),
                    "price_per_tco2e": price,
                    "value_per_year": {
                        "low": round(estimate["low"] * price, 0),
                        "central": round(estimate["central"] * price, 0),
                        "high": round(estimate["high"] * price, 0),
                    },
                }
            )
        basis = self.regions.market_basis()
        basis["region_note"] = config.get("note")
        basis["verification_status"] = config.get("verification_status", "pending")
        return {
            "currency": currency,
            "currency_symbol": symbol,
            "scenarios": rows,
            "basis": basis,
            "other_income": self.regions.other_income(region_id, currency),
            "disclaimer": DISCLAIMER,
        }
