"""Tree-age endpoints (see docs/architecture/api-contract.md §v0.2).

Both calls are pure reads of configuration and calculations: nothing is stored, so no API key is
needed and nothing about a plot except its optional climate zone is read.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.context import AppContext
from app.dependencies import get_context
from app.schemas.tree_age import SUBDIVISION_PATTERN, TreeAgeRequest
from app.services.registry import service
from app.services.tree_age import TreeAgeService

router = APIRouter(tags=["tree-age"])


def _service(ctx: AppContext) -> TreeAgeService:
    return service(ctx, "tree_age", lambda: TreeAgeService(ctx))


@router.get(
    "/tree-age/rules",
    summary="Rules that treat trees differently by age (screening information, not legal advice)",
)
def tree_age_rules(
    country: str | None = Query(
        None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2, e.g. IN, US, DE"
    ),
    subdivision: str | None = Query(
        None,
        pattern=SUBDIVISION_PATTERN,
        description="ISO 3166-2 code, e.g. IN-HR; hides rules tied to other subdivisions",
    ),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    return _service(ctx).rules(country, subdivision)


@router.post(
    "/tree-age/assess",
    summary="How much carbon do trees of this age hold, and which rules apply at this age?",
)
def tree_age_assess(body: TreeAgeRequest, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return _service(ctx).assess(body.model_dump())
