"""Geometry helper endpoints (see docs/architecture/api-contract.md §v0.2).

All three calls are pure calculations: nothing is stored, so no API key is needed. Coordinates
are used for the calculation only and are never logged.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.context import AppContext
from app.dependencies import get_context
from app.schemas.geometry_requests import (
    FromLineRequest,
    FromPointRequest,
    ParseCoordinatesRequest,
)
from app.services.geometry import GeometryService
from app.services.registry import service

router = APIRouter(tags=["geometry"])


def _service(ctx: AppContext) -> GeometryService:
    return service(ctx, "geometry", lambda: GeometryService(ctx))


@router.post(
    "/geometry/from-point",
    summary="Drop a pin and type the size: a plot polygon from a point and an area",
)
def from_point(body: FromPointRequest, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return _service(ctx).from_point(body.lat, body.lon, body.area.value, body.area.unit, body.shape)


@router.post(
    "/geometry/from-line",
    summary="Draw a tree line (bund, boundary, roadside): a strip polygon and a tree count",
)
def from_line(body: FromLineRequest, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return _service(ctx).from_line(body.line.coordinates, body.width_m, body.spacing_m)


@router.post(
    "/geometry/parse-coordinates",
    summary="Type latitude/longitude or corner points (decimal, N/S/E/W letters or DMS)",
)
def parse_typed_coordinates(
    body: ParseCoordinatesRequest, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    return _service(ctx).parse_coordinates(body.text)
