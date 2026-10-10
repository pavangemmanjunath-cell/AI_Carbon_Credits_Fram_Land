"""Agentic AI framework endpoints (see docs/architecture/api-contract.md §v0.2, "Agents").

Thin by design: validate the body, call :class:`~app.agents.service.AgentService`.
The service is built once per application and cached on the context.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.agents.schemas import AgentAskRequest, AgentRunRequest
from app.agents.service import AgentService
from app.context import AppContext
from app.core.security import require_api_key
from app.dependencies import get_context
from app.services.registry import service

router = APIRouter(tags=["agents"])
mutating = [Depends(require_api_key)]


def _agents(ctx: AppContext) -> AgentService:
    return service(ctx, "agents", lambda: AgentService(ctx))


@router.get("/agents", summary="The agent team: roles, tools, blackboard keys and plans")
def list_agents(ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return _agents(ctx).catalog()


@router.post(
    "/plots/{plot_id}/agents/run",
    status_code=201,
    dependencies=mutating,
    summary="Run an agent plan on a plot and store the transcript",
)
def run_agents(
    plot_id: str,
    body: AgentRunRequest | None = None,
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    body = body or AgentRunRequest()
    costs = body.costs.model_dump() if body.costs else None
    return _agents(ctx).run(plot_id, body.plan, body.question, body.locale, costs)


@router.post(
    "/agents/ask",
    status_code=201,
    dependencies=mutating,
    summary="Ask the agent team a question about a plot (deterministic intent routing)",
)
def ask_agents(body: AgentAskRequest, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    costs = body.costs.model_dump() if body.costs else None
    return _agents(ctx).ask(body.question, body.plot_id, body.locale, costs)


@router.get("/agents/runs", summary="Stored agent runs, newest first (summaries)")
def list_runs(
    plot_id: str | None = Query(None, min_length=1, max_length=64),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    return _agents(ctx).list_runs(plot_id)


@router.get("/agents/runs/{run_id}", summary="One stored agent run (full transcript)")
def get_run(run_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return _agents(ctx).get_run(run_id)
