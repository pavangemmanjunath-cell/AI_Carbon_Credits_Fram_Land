"""Vegetation cube (lon × lat × time × index) as JSON: map NDVI cells, change-over-time chart, detection."""

from __future__ import annotations

from typing import Any

from shapely.geometry import shape

from app.core.errors import ProblemError
from app.repositories.base import Repository
from app.services.adapters import ModeRouter
from carboncreditbuy_integrations import AdapterError, DependencyMissingError
from geo_engine.cube import GridTooLargeError

SUPPORTED_INDICES = ("ndvi", "ndmi", "ndre")


class CubeService:
    def __init__(self, repo: Repository, router: ModeRouter) -> None:
        self.repo = repo
        self.router = router

    def build(self, plot: dict[str, Any], index: str, months: int) -> dict[str, Any]:
        index = index.lower()
        if index not in SUPPORTED_INDICES:
            raise ProblemError(422, f"index must be one of {', '.join(SUPPORTED_INDICES)}.")
        if not 6 <= months <= 72:
            raise ProblemError(422, "months must be between 6 and 72.")
        inventories = self.repo.list_inventories(plot["plot_id"])
        planting_year = inventories[-1]["plantation_year"] if inventories else None
        polygon = shape(plot["geometry"])
        try:
            cube = self.router.satellite.build_cube(
                plot["plot_id"], polygon, index, months, planting_year=planting_year
            )
        except DependencyMissingError as exc:
            raise ProblemError(501, str(exc), type_slug="dependency-missing") from exc
        except GridTooLargeError as exc:
            raise ProblemError(
                422,
                f"This plot is too large for the vegetation grid: its bounding box needs "
                f"{exc.rows}×{exc.cols} cells of {exc.cell_size_m} m (about {exc.max_area_ha:,.0f} ha "
                "of bounding box is the limit). Split the land into smaller plots.",
                type_slug="plot-too-large-for-grid",
            ) from exc
        except (AdapterError, OSError, ValueError) as exc:
            raise ProblemError(
                502,
                f"Satellite cube unavailable: {type(exc).__name__}",
                type_slug="upstream-unavailable",
            ) from exc
        payload = cube.to_dict(self.router.mode)
        payload["provenance"].setdefault(
            "source", "synthetic-demo" if self.router.settings.is_demo else "sentinel-2-l2a"
        )
        payload["provenance"].setdefault("cell_size_m", payload["grid"]["cell_size_m"])
        self.repo.audit("plot.cube", plot["plot_id"], {"index": index, "months": months})
        return payload
