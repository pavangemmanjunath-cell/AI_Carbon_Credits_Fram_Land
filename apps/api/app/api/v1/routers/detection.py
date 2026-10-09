"""Tree-cover detection endpoints (see docs/architecture/api-contract.md §v0.2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.context import AppContext
from app.core.errors import ProblemError
from app.core.security import require_api_key
from app.dependencies import get_context
from app.schemas.detection_requests import DetectRequest
from app.services.detection import DetectionService
from app.services.registry import service

router = APIRouter(tags=["detection"])
mutating = [Depends(require_api_key)]


def _service(ctx: AppContext) -> DetectionService:
    return service(ctx, "detection", lambda: DetectionService(ctx))


@router.post(
    "/plots/{plot_id}/detect",
    dependencies=mutating,
    summary="AI detected tree cover from satellite NDVI (heuristic; stored as the plot's latest)",
)
def detect(
    plot_id: str, body: DetectRequest | None = None, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    body = body or DetectRequest()
    return _service(ctx).detect(plot_id, body.target, body.min_confidence)


@router.get(
    "/plots/{plot_id}/detections",
    summary="Latest tree-cover detection of a plot (404 when none has been run)",
)
def latest_detection(plot_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    plot = ctx.plots.require(plot_id)
    found = _service(ctx).latest(plot["plot_id"])
    if found is None:
        raise ProblemError(
            404,
            f"No detection has been run for plot {plot['plot_id']} yet; "
            f"POST /plots/{plot['plot_id']}/detect first.",
            type_slug="detection-not-found",
        )
    return found
