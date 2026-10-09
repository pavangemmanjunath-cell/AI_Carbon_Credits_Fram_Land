"""Plot creation, validation, measurement and privacy-aware views."""

from __future__ import annotations

from typing import Any

from shapely.geometry import shape

from app.core.config import Settings
from app.core.errors import ProblemError
from app.repositories.base import Repository
from app.services.adapters import ModeRouter
from app.services.common import now_iso
from app.services.regions import RegionConfig
from geo_engine.errors import GeometryError
from geo_engine.geometry import ValidationLimits, measure_polygon, new_plot_id, validate_polygon

PRIVATE_FIELDS = ("geometry", "centroid", "perimeter_m")


class PlotService:
    def __init__(
        self, repo: Repository, settings: Settings, router: ModeRouter, regions: RegionConfig
    ) -> None:
        self.repo = repo
        self.settings = settings
        self.router = router
        self.regions = regions
        self.limits = ValidationLimits(
            max_vertices=settings.atlas_max_plot_vertices,
            max_area_ha=settings.atlas_max_plot_area_ha,
        )

    # -- helpers -----------------------------------------------------------------
    def polygon(self, plot: dict[str, Any]):  # type: ignore[no-untyped-def]
        return shape(plot["geometry"])

    def require(self, plot_id: str) -> dict[str, Any]:
        plot = self.repo.get_plot(plot_id)
        if plot is None:
            raise ProblemError(404, f"Plot {plot_id} was not found.", type_slug="plot-not-found")
        return plot

    def region_id(self, plot: dict[str, Any]) -> str:
        resolved = self.regions.resolve(plot.get("country"))
        if resolved:
            return resolved
        by_point = self.regions.region_for_point(plot["centroid"]["lat"], plot["centroid"]["lon"])
        return by_point or "IN"

    @staticmethod
    def public_view(plot: dict[str, Any]) -> dict[str, Any]:
        """What a non-owner may see: no exact geometry."""
        view = {k: v for k, v in plot.items() if k not in PRIVATE_FIELDS}
        view["privacy"] = "generalized-public"
        return view

    # -- commands ------------------------------------------------------------------
    def create(
        self,
        geometry: dict[str, Any],
        name: str,
        country: str | None,
        source: str,
        plot_id: str | None = None,
        boundary_quality: str = "exact",
    ) -> dict[str, Any]:
        try:
            polygon = validate_polygon(geometry, self.limits)
        except GeometryError as exc:
            raise ProblemError(422, str(exc), type_slug="invalid-geometry") from exc
        metrics = measure_polygon(polygon)
        region_name: str | None = None
        resolved_country = country
        if not resolved_country or self.settings.atlas_mode == "live":
            try:
                reverse = self.router.geocoder.reverse(metrics.centroid_lat, metrics.centroid_lon)
                resolved_country = resolved_country or (reverse.country or None)
                region_name = reverse.state
            except Exception:  # adapter failures must not block plot creation
                region_name = None
        if not resolved_country:
            resolved_country = self.regions.region_for_point(
                metrics.centroid_lat, metrics.centroid_lon
            )
        if not resolved_country:
            raise ProblemError(
                422,
                "Could not determine the country for this plot; pass `country` explicitly.",
                type_slug="country-unresolved",
            )
        if self.regions.resolve(resolved_country) is None:
            raise ProblemError(
                422,
                f"Country {resolved_country} is not supported in this release (IN, US, EU members).",
                type_slug="unsupported-country",
            )
        if region_name is None and self.settings.is_demo:
            try:
                region_name = self.router.geocoder.reverse(
                    metrics.centroid_lat, metrics.centroid_lon
                ).state
            except Exception:
                region_name = None
        new_id = plot_id or new_plot_id()
        plot: dict[str, Any] = {
            "plot_id": new_id,
            "name": name,
            "country": resolved_country.upper(),
            "region": region_name,
            "geometry": geometry,
            "area_hectares": round(metrics.area_hectares, 4),
            "area_acres": round(metrics.area_acres, 4),
            "perimeter_m": round(metrics.perimeter_m, 1),
            "centroid": {
                "lat": round(metrics.centroid_lat, 6),
                "lon": round(metrics.centroid_lon, 6),
            },
            "public_centroid": {
                "lat": round(metrics.public_centroid_lat, 2),
                "lon": round(metrics.public_centroid_lon, 2),
            },
            "bbox": [round(v, 6) for v in metrics.bbox],
            "source": source,
            "boundary_quality": boundary_quality,
            "privacy": "private",
            "created_by": "user",
            "created_at": now_iso(),
            "updated_at": None,
        }
        self.repo.save_plot(plot)
        self.repo.audit("plot.created", new_id, {"area_hectares": plot["area_hectares"]})
        return plot

    def delete(self, plot_id: str) -> None:
        if not self.repo.delete_plot(plot_id):
            raise ProblemError(404, f"Plot {plot_id} was not found.", type_slug="plot-not-found")
        self.repo.audit("plot.deleted", plot_id)
