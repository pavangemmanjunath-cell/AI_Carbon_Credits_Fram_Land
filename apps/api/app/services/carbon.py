"""Carbon estimates: wraps the carbon engine and attaches API-level provenance."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.errors import ProblemError
from app.repositories.base import Repository
from app.services.analysis import AnalysisService
from app.services.common import base_provenance, current_year, now_iso, short_id
from app.services.regions import RegionConfig
from carbon_engine import (
    CarbonEngineError,
    ClimateInput,
    InventoryInput,
    ModelNotImplementedError,
    ModelParams,
    ParameterStore,
    PendingParameterError,
    PlotInput,
    UnknownClimateZoneError,
    get_model,
)
from geo_engine.climate import zone_label


class CarbonService:
    def __init__(
        self,
        repo: Repository,
        settings: Settings,
        store: ParameterStore,
        regions: RegionConfig,
        analysis: AnalysisService,
    ) -> None:
        self.repo = repo
        self.settings = settings
        self.store = store
        self.regions = regions
        self.analysis = analysis

    def climate_for(self, plot: dict[str, Any], analysis: dict[str, Any] | None) -> ClimateInput:
        climate = (analysis or {}).get("climate") or {}
        if climate.get("zone"):
            return ClimateInput(
                zone=str(climate["zone"]), zone_source=str(climate.get("zone_source", "derived"))
            )
        region_id = self.regions.resolve(plot.get("country")) or "IN"
        return ClimateInput(zone=self.regions.default_zone(region_id), zone_source="region-default")

    def run_model(
        self,
        model_id: str,
        plot_input: PlotInput,
        inventory_input: InventoryInput,
        climate: ClimateInput,
        params: ModelParams,
    ) -> dict[str, Any]:
        try:
            model = get_model(model_id, self.store)
            return model.estimate(plot_input, inventory_input, climate, params).to_dict()
        except ModelNotImplementedError as exc:
            raise ProblemError(501, str(exc), type_slug="model-not-implemented") from exc
        except PendingParameterError as exc:
            raise ProblemError(
                409,
                f"{exc} Set ATLAS_ALLOW_PENDING_PARAMETERS=true outside production.",
                type_slug="pending-parameters",
            ) from exc
        except UnknownClimateZoneError as exc:
            raise ProblemError(422, str(exc), type_slug="unknown-climate-zone") from exc
        except CarbonEngineError as exc:
            raise ProblemError(422, str(exc), type_slug="carbon-engine-error") from exc

    def estimate(
        self,
        plot: dict[str, Any],
        inventory: dict[str, Any],
        model_id: str,
        horizon_years: int | None,
        evidence: dict[str, bool],
    ) -> dict[str, Any]:
        analysis = self.repo.get_analysis(plot["plot_id"])
        has_satellite = bool(analysis and analysis.get("vegetation"))
        plot_input = PlotInput(
            area_hectares=float(plot["area_hectares"]),
            plot_id=plot["plot_id"],
            has_polygon=True,
            has_satellite_observation=has_satellite,
            country=plot.get("country"),
        )
        inventory_input = InventoryInput(
            species_id=inventory["species"]["id"],
            tree_count=int(inventory["tree_count"]),
            plantation_year=int(inventory["plantation_year"]),
            average_dbh_cm=inventory.get("average_dbh_cm"),
            average_height_m=inventory.get("average_height_m"),
            survival_rate=inventory.get("survival_rate"),
            measurement_source=inventory.get("measurement_source", "user-reported"),
            inventory_id=inventory["inventory_id"],
        )
        climate = self.climate_for(plot, analysis)
        params = ModelParams(
            horizon_years=horizon_years,
            as_of_year=current_year(),
            allow_pending_parameters=self.settings.atlas_allow_pending_parameters
            and not self.settings.is_production,
            evidence=dict(evidence),
        )
        result = self.run_model(model_id, plot_input, inventory_input, climate, params)
        engine_prov = result.pop("provenance", {})
        provenance = base_provenance(self.settings.atlas_mode, self.analysis.sources_for(analysis))
        provenance.update(
            {
                "model": engine_prov.get("model"),
                "parameter_set": engine_prov.get("parameter_set"),
                "parameter_sources": engine_prov.get("sources", []),
                "climate_zone": engine_prov.get("climate_zone")
                or {
                    "zone": climate.zone,
                    "label": zone_label(climate.zone),
                    "source": climate.zone_source,
                },
                "species": engine_prov.get("species"),
                "notes": list(engine_prov.get("notes", [])),
            }
        )
        estimate = {
            "estimate_id": short_id("EST-", 4),
            "plot_id": plot["plot_id"],
            "inventory_id": inventory["inventory_id"],
            **result,
            "provenance": provenance,
            "generated_at": now_iso(),
        }
        self.repo.save_estimate(estimate)
        self.repo.audit(
            "estimate.created", plot["plot_id"], {"estimate_id": estimate["estimate_id"]}
        )
        return estimate

    def latest(self, plot_id: str) -> dict[str, Any] | None:
        items = self.repo.list_estimates(plot_id)
        return items[-1] if items else None

    def require(self, plot_id: str, estimate_id: str | None) -> dict[str, Any]:
        estimate = (
            self.repo.get_estimate(plot_id, estimate_id) if estimate_id else self.latest(plot_id)
        )
        if estimate is None:
            raise ProblemError(
                404,
                "No carbon estimate for this plot yet — POST /plots/{plot_id}/carbon-estimate first.",
                type_slug="estimate-missing",
            )
        return estimate
