"""Deterministic "what if I plant N trees here?" simulation with per-country context."""

from __future__ import annotations

from typing import Any

from app.core.errors import ProblemError
from app.services.adapters import ModeRouter
from app.services.carbon import CarbonService
from app.services.common import base_provenance, current_year
from app.services.market import MarketService
from app.services.policy import PolicyService
from app.services.regions import RegionConfig
from atlas_integrations import AdapterError
from carbon_engine import ClimateInput, InventoryInput, ModelParams, PlotInput
from geo_engine.climate import classify_climate_zone, zone_label

DEFAULT_AREA_HA = 2.13
DISCLAIMER = "Scenario estimate; not an issued carbon credit. Market-value scenarios are not guaranteed revenue."
PROGRAMME_SUMMARY = {
    "IN": "Green Credit Programme · CCTS offset mechanism (separate mechanisms)",
    "US": "COMET-Farm methodology reference · voluntary ARR methodologies · NRCS incentives",
    "EU": "CRCF certification framework (Regulation (EU) 2024/3012) · CAP eco-schemes",
}


class SimulationService:
    def __init__(
        self,
        regions: RegionConfig,
        carbon: CarbonService,
        market: MarketService,
        policy: PolicyService,
        router: ModeRouter,
    ) -> None:
        self.regions = regions
        self.carbon = carbon
        self.market = market
        self.policy = policy
        self.router = router

    def _climate(self, region_id: str, lat: float | None, lon: float | None) -> ClimateInput:
        if lat is not None and lon is not None:
            try:
                normals = self.router.climate.fetch_climate_normals(lat, lon)
                zone = classify_climate_zone(
                    normals.mean_annual_temp_c, normals.annual_precip_mm, normals.elevation_m
                )
                return ClimateInput(zone=zone.zone, zone_source="derived")
            except (AdapterError, OSError, ValueError):
                pass
        return ClimateInput(zone=self.regions.default_zone(region_id), zone_source="region-default")

    def _run(
        self, region_id: str, body: dict[str, Any], climate: ClimateInput, area_ha: float
    ) -> dict[str, Any]:
        if body["tree_count"] == 0:
            return self._zero(body)
        plot_input = PlotInput(
            area_hectares=area_ha,
            plot_id=body.get("plot_id"),
            has_polygon=bool(body.get("plot_id")),
        )
        inventory = InventoryInput(
            species_id=body["species_id"],
            tree_count=int(body["tree_count"]),
            plantation_year=int(body["planting_year"]),
            survival_rate=body.get("survival_rate"),
        )
        params = ModelParams(
            horizon_years=int(body["horizon_years"]),
            as_of_year=max(current_year(), int(body["planting_year"])),
            allow_pending_parameters=self.carbon.settings.atlas_allow_pending_parameters
            and not self.carbon.settings.is_production,
        )
        return self.carbon.run_model("tree-biomass", plot_input, inventory, climate, params)

    @staticmethod
    def _zero(body: dict[str, Any]) -> dict[str, Any]:
        years = range(
            int(body["planting_year"]), int(body["planting_year"]) + int(body["horizon_years"]) + 1
        )
        return {
            "estimate": {"low": 0.0, "central": 0.0, "high": 0.0, "unit": "tCO2e/yr"},
            "stock": {"low": 0.0, "central": 0.0, "high": 0.0, "unit": "tCO2e"},
            "annual_series": [
                {
                    "year": y,
                    "age": i,
                    "low": 0.0,
                    "central": 0.0,
                    "high": 0.0,
                    "cum_low": 0.0,
                    "cum_central": 0.0,
                    "cum_high": 0.0,
                }
                for i, y in enumerate(years)
            ],
            "confidence": "low",
            "parameters_used": [],
            "provenance": {},
        }

    def simulate(self, body: dict[str, Any]) -> dict[str, Any]:
        region_id = self.regions.resolve(body["country"])
        if region_id is None:
            raise ProblemError(
                422, f"Country {body['country']} is not supported.", type_slug="unsupported-country"
            )
        area_ha = float(body.get("area_hectares") or DEFAULT_AREA_HA)
        climate = self._climate(region_id, body.get("lat"), body.get("lon"))
        result = self._run(region_id, body, climate, area_ha)
        annual = result["estimate"]
        value = self.market.scenarios_for(region_id, annual)
        programmes = self.policy.programme_links(region_id)

        comparison = []
        for other in ("IN", "US", "EU"):
            if other not in self.regions.regions:
                continue
            other_climate = (
                climate
                if other == region_id
                else ClimateInput(
                    zone=self.regions.default_zone(other), zone_source="region-default"
                )
            )
            other_result = self._run(other, body, other_climate, area_ha)
            other_value = self.market.scenarios_for(other, other_result["estimate"])
            reference = next(s for s in other_value["scenarios"] if s["id"] == "reference")
            links = self.policy.programme_links(other)
            comparison.append(
                {
                    "country": other,
                    "name": self.regions.region(other).get("name"),
                    "climate_zone": other_climate.zone,
                    "climate_zone_label": zone_label(other_climate.zone),
                    "annual": other_result["estimate"],
                    "currency": other_value["currency"],
                    "currency_symbol": other_value["currency_symbol"],
                    "reference_price_per_tco2e": reference["price_per_tco2e"],
                    "reference_value_per_year": reference["value_per_year"]["central"],
                    "programme_summary": PROGRAMME_SUMMARY.get(other, ""),
                    "url": links[0]["url"] if links else None,
                    "programmes": links,
                }
            )

        provenance = base_provenance(self.router.mode, [])
        engine_prov = result.get("provenance", {})
        provenance.update(
            {
                "model": engine_prov.get("model"),
                "parameter_set": engine_prov.get("parameter_set"),
                "parameter_sources": engine_prov.get("sources", []),
                "notes": list(engine_prov.get("notes", [])),
            }
        )
        region = self.regions.region(region_id)
        value_scenarios = [
            {
                **scenario,
                "currency": value["currency"],
                "currency_symbol": value["currency_symbol"],
            }
            for scenario in value["scenarios"]
        ]
        return {
            "inputs": {
                "country": body["country"],
                "region": region_id,
                "species_id": body["species_id"],
                "tree_count": body["tree_count"],
                "planting_year": body["planting_year"],
                "horizon_years": body["horizon_years"],
                "survival_rate": body.get("survival_rate"),
                "area_hectares": area_ha,
                "density_per_ha": round(body["tree_count"] / area_ha, 1),
            },
            "region_name": region.get("name"),
            "currency": value["currency"],
            "currency_symbol": value["currency_symbol"],
            "area_unit": (region.get("units") or {}).get("area", "hectare"),
            "climate_zone": climate.zone,
            "climate_zone_label": zone_label(climate.zone),
            "climate_zone_source": climate.zone_source,
            "annual": annual,
            "stock_now": result["stock"],
            "series": result["annual_series"],
            "value_scenarios": value_scenarios,
            "market_disclaimer": value["disclaimer"],
            "programmes": programmes,
            "comparison": comparison,
            "parameters_used": result.get("parameters_used", []),
            "confidence": result["confidence"],
            "certified": False,
            "disclaimer": DISCLAIMER,
            "share_params": {
                "country": body["country"],
                "species": body["species_id"],
                "trees": body["tree_count"],
                "year": body["planting_year"],
                "horizon": body["horizon_years"],
            },
            "provenance": provenance,
        }
