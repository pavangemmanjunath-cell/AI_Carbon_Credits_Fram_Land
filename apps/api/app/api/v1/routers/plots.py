"""Plots, analysis, cube, trees, carbon, policy, market and reports — all per plot."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import Response as RawResponse

from app.context import AppContext
from app.core.security import require_api_key
from app.dependencies import get_context
from app.schemas.requests import (
    Activity,
    AnalyzeRequest,
    CarbonEstimateRequest,
    PlotCreate,
    ReportRequest,
    TreeInventoryCreate,
)

router = APIRouter(tags=["plots"])
mutating = [Depends(require_api_key)]


@router.post(
    "/plots", status_code=201, dependencies=mutating, summary="Create a plot from a polygon"
)
def create_plot(body: PlotCreate, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return ctx.plots.create(
        body.geometry.model_dump(),
        body.name,
        body.country,
        body.source,
        boundary_quality=body.boundary_quality,
    )


@router.get("/plots", summary="List plots (owner view in this single-tenant release)")
def list_plots(ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return {"items": ctx.repo.list_plots()}


@router.get("/plots/{plot_id}", summary="Fetch one plot")
def get_plot(plot_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return ctx.plots.require(plot_id)


@router.get(
    "/plots/{plot_id}/public", summary="Privacy-preserving public view (generalized centroid only)"
)
def get_plot_public(plot_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return ctx.plots.public_view(ctx.plots.require(plot_id))


@router.delete("/plots/{plot_id}", status_code=204, dependencies=mutating, summary="Delete a plot")
def delete_plot(plot_id: str, ctx: AppContext = Depends(get_context)) -> Response:
    ctx.plots.delete(plot_id)
    return Response(status_code=204)


@router.post(
    "/plots/{plot_id}/analyze",
    dependencies=mutating,
    summary="Land cover, vegetation, climate, soil",
)
def analyze(
    plot_id: str, body: AnalyzeRequest | None = None, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    body = body or AnalyzeRequest()
    plot = ctx.plots.require(plot_id)
    return ctx.analysis.analyze(plot, list(body.layers), body.years)


@router.get("/plots/{plot_id}/analysis", summary="Latest analysis")
def get_analysis(plot_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    plot = ctx.plots.require(plot_id)
    analysis = ctx.repo.get_analysis(plot["plot_id"])
    if analysis is None:
        analysis = ctx.analysis.analyze(plot, ["landcover", "vegetation", "climate", "soil"], None)
    return analysis


@router.get("/plots/{plot_id}/vegetation", summary="Vegetation block of the latest analysis")
def get_vegetation(plot_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    plot = ctx.plots.require(plot_id)
    analysis = ctx.repo.get_analysis(plot["plot_id"]) or ctx.analysis.analyze(
        plot, ["vegetation"], None
    )
    return analysis.get("vegetation") or {
        "indices": {},
        "time_series": [],
        "trend": {},
        "notes": ["no observations"],
    }


@router.get("/plots/{plot_id}/cube", summary="Space-time cube (lon × lat × time × index) as JSON")
def get_cube(
    plot_id: str,
    index: str = Query("ndvi"),
    months: int = Query(36, ge=6, le=72),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    plot = ctx.plots.require(plot_id)
    return ctx.cube.build(plot, index, months)


@router.post(
    "/plots/{plot_id}/trees",
    status_code=201,
    dependencies=mutating,
    summary="Record a tree inventory",
)
def create_trees(
    plot_id: str, body: TreeInventoryCreate, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    plot = ctx.plots.require(plot_id)
    return ctx.trees.create(plot, body.model_dump())


@router.get("/plots/{plot_id}/trees", summary="Tree inventories for a plot")
def list_trees(plot_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    ctx.plots.require(plot_id)
    return {"items": ctx.repo.list_inventories(plot_id)}


@router.post(
    "/plots/{plot_id}/carbon-estimate",
    status_code=201,
    dependencies=mutating,
    summary="Carbon removal scenario",
)
def carbon_estimate(
    plot_id: str, body: CarbonEstimateRequest | None = None, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    body = body or CarbonEstimateRequest()
    plot = ctx.plots.require(plot_id)
    inventory = ctx.trees.require(plot_id, body.inventory_id)
    return ctx.carbon.estimate(plot, inventory, body.model, body.horizon_years, body.evidence)


@router.get("/plots/{plot_id}/carbon-estimate", summary="Latest carbon estimate")
def latest_estimate(plot_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    ctx.plots.require(plot_id)
    return ctx.carbon.require(plot_id, None)


@router.get("/plots/{plot_id}/policy-eligibility", summary="Programme screening (not eligibility)")
def policy_eligibility(
    plot_id: str,
    activity: Activity = Query("tree_plantation"),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    plot = ctx.plots.require(plot_id)
    return ctx.policy.screen(plot["country"], activity, area_ha=plot["area_hectares"])


@router.get(
    "/plots/{plot_id}/market-scenario", summary="Indicative value scenarios for an estimate"
)
def market_scenario(
    plot_id: str, estimate_id: str | None = Query(None), ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    plot = ctx.plots.require(plot_id)
    estimate = ctx.carbon.require(plot_id, estimate_id)
    region_id = ctx.regions.resolve(plot["country"]) or "IN"
    payload = ctx.market.scenarios_for(region_id, estimate["estimate"])
    payload["estimate_id"] = estimate["estimate_id"]
    payload["plot_id"] = plot_id
    return payload


@router.post(
    "/plots/{plot_id}/report",
    status_code=201,
    dependencies=mutating,
    summary="Generate an assessment report",
)
def create_report(
    plot_id: str, body: ReportRequest | None = None, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    body = body or ReportRequest()
    plot = ctx.plots.require(plot_id)
    meta = ctx.reports.create(plot, body.format, body.language, body.estimate_id)
    meta["url"] = f"/api/v1/reports/{meta['report_id']}"
    return meta


@router.get("/reports/{report_id}", tags=["reports"], summary="Fetch a rendered report")
def get_report(report_id: str, ctx: AppContext = Depends(get_context)) -> RawResponse:
    meta, content = ctx.reports.fetch(report_id)
    filename = f"{report_id}.{'md' if meta['format'] == 'markdown' else meta['format']}"
    return RawResponse(
        content=content,
        media_type=meta["media_type"],
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
