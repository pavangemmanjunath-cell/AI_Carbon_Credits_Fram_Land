"""Simulation lab and privacy-preserving explanation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.context import AppContext
from app.dependencies import get_context
from app.schemas.requests import ExplainRequest, SimulateRequest

router = APIRouter()


@router.post("/simulate", tags=["simulation"], summary="What if I plant N trees here?")
def simulate(body: SimulateRequest, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    ctx.trees.species(body.species_id)
    return ctx.simulate.simulate(body.model_dump())


@router.post(
    "/explain", tags=["explanation"], summary="Plain-language explanation from indicators only"
)
def explain(body: ExplainRequest, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return ctx.explain.explain(body.indicators, body.language)
