"""Imagery provider endpoints (see docs/architecture/api-contract.md §v0.2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.context import AppContext
from app.dependencies import get_context
from app.services.imagery import ImageryService
from app.services.registry import service

router = APIRouter(tags=["imagery"])


def _service(ctx: AppContext) -> ImageryService:
    return service(ctx, "imagery", lambda: ImageryService(ctx))


@router.get(
    "/imagery/providers",
    summary="Satellite / aerial imagery providers with licences, recommended first for a country",
)
def imagery_providers(
    country: str | None = Query(
        None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2, e.g. IN, US, FR"
    ),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    return _service(ctx).providers(country)
