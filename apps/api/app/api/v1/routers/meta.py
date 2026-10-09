"""Health, regions, species, methodologies, attribution and geocoding."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app import __version__
from app.context import AppContext
from app.core.errors import ProblemError
from app.dependencies import get_context
from app.services.common import now_iso
from app.services.regions import ATTRIBUTION_ITEMS
from atlas_integrations import AdapterError

router = APIRouter()


@router.get("/health", tags=["meta"], summary="Liveness and mode")
def health(ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "mode": ctx.settings.atlas_mode,
        "repository": ctx.settings.atlas_repository,
        "time": now_iso(),
    }


@router.get("/regions", tags=["meta"], summary="Supported regions and their programmes")
def regions(ctx: AppContext = Depends(get_context)) -> list[dict[str, Any]]:
    return ctx.regions.public_regions()


@router.get("/species", tags=["meta"], summary="Species table (parameters with provenance)")
def species(
    country: str | None = Query(None, min_length=2, max_length=2),
    ctx: AppContext = Depends(get_context),
) -> list[dict[str, Any]]:
    region = ctx.regions.resolve(country) if country else None
    return ctx.trees.species_list(region)


@router.get(
    "/methodologies", tags=["meta"], summary="Methodology registry (referenced, never applied)"
)
def methodologies(ctx: AppContext = Depends(get_context)) -> list[dict[str, Any]]:
    return ctx.regions.methodologies()


@router.get("/attribution", tags=["meta"], summary="Attribution strings for UI and reports")
def attribution() -> dict[str, Any]:
    return {"items": ATTRIBUTION_ITEMS}


@router.get(
    "/geocode", tags=["location"], summary="Forward geocoding (server-side, policy-compliant)"
)
def geocode(
    q: str = Query(..., min_length=2, max_length=200),
    country: str | None = Query(None, min_length=2, max_length=2),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    try:
        results = ctx.router.geocoder.search(q, country=country, limit=5)
    except AdapterError as exc:
        raise ProblemError(
            502, f"Geocoder unavailable: {type(exc).__name__}", type_slug="upstream-unavailable"
        ) from exc
    provenance = ctx.router.geocoder.provenance()
    return {
        "results": [r.to_dict() for r in results],
        "provider": ctx.settings.atlas_geocoder if not ctx.settings.is_demo else "demo",
        "attribution": provenance.get("attribution"),
    }


@router.get(
    "/reverse-geocode", tags=["location"], summary="Reverse geocoding to country/state/district"
)
def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    try:
        result = ctx.router.geocoder.reverse(lat, lon)
    except AdapterError as exc:
        raise ProblemError(
            502, f"Geocoder unavailable: {type(exc).__name__}", type_slug="upstream-unavailable"
        ) from exc
    payload = result.to_dict()
    payload["provider"] = ctx.settings.atlas_geocoder if not ctx.settings.is_demo else "demo"
    payload["attribution"] = ctx.router.geocoder.provenance().get("attribution")
    return payload
