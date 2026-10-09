"""Land, vegetation, climate and soil analysis for a plot (demo or live)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from shapely.geometry import shape

from app.repositories.base import Repository
from app.services.adapters import ModeRouter
from app.services.common import base_provenance, current_year, now_iso
from app.services.regions import RegionConfig
from atlas_integrations import AdapterError
from geo_engine.climate import classify_climate_zone

log = logging.getLogger("atlas.analysis")


class AnalysisService:
    def __init__(self, repo: Repository, router: ModeRouter, regions: RegionConfig) -> None:
        self.repo = repo
        self.router = router
        self.regions = regions

    # -- helpers -------------------------------------------------------------------
    def latest_planting_year(self, plot_id: str) -> int | None:
        inventories = self.repo.list_inventories(plot_id)
        return inventories[-1]["plantation_year"] if inventories else None

    def _landcover(self, plot: dict[str, Any], warnings: list[str]) -> dict[str, Any] | None:
        try:
            result = (
                self.router.landcover.fetch_land_cover(
                    plot["geometry"],
                    tuple(plot["bbox"]),
                    plot["area_hectares"],
                    plot_id=plot["plot_id"],
                )
                if self.router.settings.is_demo
                else self.router.landcover.fetch_land_cover(
                    plot["geometry"], tuple(plot["bbox"]), plot["area_hectares"]
                )
            )
        except (AdapterError, OSError, ValueError) as exc:
            log.warning("landcover unavailable", extra={"plot_id": plot["plot_id"]})
            warnings.append(f"land cover unavailable: {type(exc).__name__}")
            return None
        classes = [c.to_dict() for c in result.classes]
        tree = next((c["share"] for c in classes if c["code"] == 10), 0.0)
        crop = next((c["share"] for c in classes if c["code"] == 40), 0.0)
        source = dict(result.source)
        return {
            "dataset": "ESA WorldCover",
            "version": "2021 v200",
            "resolution_m": 10,
            "classes": classes,
            "tree_cover_share": round(tree, 4),
            "cropland_share": round(crop, 4),
            "tiles": list(result.tiles),
            "notes": list(result.notes),
            "provenance": base_provenance(self.router.mode, [source]),
        }

    def _vegetation(
        self, plot: dict[str, Any], years: list[int], warnings: list[str]
    ) -> dict[str, Any] | None:
        polygon = shape(plot["geometry"])
        try:
            result = self.router.satellite.fetch_vegetation(
                polygon,
                years,
                plot_id=plot["plot_id"],
                planting_year=self.latest_planting_year(plot["plot_id"]),
            )
        except (AdapterError, OSError, ValueError) as exc:
            log.warning("vegetation unavailable", extra={"plot_id": plot["plot_id"]})
            warnings.append(f"satellite vegetation unavailable: {type(exc).__name__}")
            return None
        payload = result.to_dict()
        payload["notes"] = list(result.notes)
        payload["provenance"] = base_provenance(self.router.mode, [dict(result.source)])
        return payload

    def _climate(self, plot: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
        lat, lon = plot["centroid"]["lat"], plot["centroid"]["lon"]
        region_id = self.regions.resolve(plot["country"]) or "IN"
        try:
            normals = self.router.climate.fetch_climate_normals(lat, lon)
            zone = classify_climate_zone(
                normals.mean_annual_temp_c, normals.annual_precip_mm, normals.elevation_m
            )
            return {
                "zone": zone.zone,
                "zone_label": zone.label,
                "zone_source": "derived",
                "mean_annual_temp_c": round(normals.mean_annual_temp_c, 1),
                "annual_precip_mm": round(normals.annual_precip_mm, 0),
                "elevation_m": None
                if normals.elevation_m is None
                else round(normals.elevation_m, 0),
                "pet_mm": zone.pet_mm,
                "method": zone.method,
                "verification_status": zone.verification_status,
                "provenance": base_provenance(self.router.mode, [dict(normals.source)]),
            }
        except (AdapterError, OSError, ValueError) as exc:
            warnings.append(
                f"climate normals unavailable: {type(exc).__name__}; using region default"
            )
            zone_id = self.regions.default_zone(region_id)
            from geo_engine.climate import zone_label

            return {
                "zone": zone_id,
                "zone_label": zone_label(zone_id),
                "zone_source": "region-default",
                "mean_annual_temp_c": None,
                "annual_precip_mm": None,
                "elevation_m": None,
                "provenance": base_provenance(self.router.mode, []),
            }

    def _soil(self, plot: dict[str, Any], warnings: list[str]) -> dict[str, Any] | None:
        try:
            result = self.router.soil.fetch_soc_0_30(
                plot["centroid"]["lat"], plot["centroid"]["lon"]
            )
        except (AdapterError, OSError, ValueError) as exc:
            warnings.append(f"soil data unavailable: {type(exc).__name__}")
            return None
        payload = result.to_dict()
        payload["depths_used"] = list(result.depths_used)
        payload["provenance"] = base_provenance(self.router.mode, [dict(result.source)])
        return payload

    # -- command -----------------------------------------------------------------
    def analyze(
        self, plot: dict[str, Any], layers: list[str], years: list[int] | None
    ) -> dict[str, Any]:
        warnings: list[str] = []
        if self.router.settings.is_demo:
            warnings.append("demo mode: synthetic observations")
        this_year = current_year()
        years = years or [this_year - 2, this_year - 1, this_year]
        analysis: dict[str, Any] = {
            "plot_id": plot["plot_id"],
            "mode": self.router.mode,
            "years": years,
            "landcover": self._landcover(plot, warnings) if "landcover" in layers else None,
            "vegetation": self._vegetation(plot, years, warnings)
            if "vegetation" in layers
            else None,
            "climate": self._climate(plot, warnings) if "climate" in layers else None,
            "soil": self._soil(plot, warnings) if "soil" in layers else None,
            "terrain": None,
            "data_quality": {"warnings": warnings},
            "generated_at": now_iso(),
        }
        if "terrain" in layers:
            analysis["terrain"] = {
                "status": "not_implemented",
                "note": "Terrain/slope statistics (Copernicus DEM GLO-30) are planned for v0.2.",
            }
        self.repo.save_analysis(plot["plot_id"], analysis)
        self.repo.audit("plot.analyzed", plot["plot_id"], {"layers": layers})
        return analysis

    def sources_for(self, analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not analysis:
            return []
        sources: list[dict[str, Any]] = []
        for key in ("landcover", "vegetation", "climate", "soil"):
            block = analysis.get(key)
            if block and block.get("provenance"):
                sources.extend(block["provenance"].get("sources", []))
        return sources

    @staticmethod
    def anchor_date() -> datetime:
        return datetime.now(UTC)
