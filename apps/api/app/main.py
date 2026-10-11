"""CarbonCreditBuy API — FastAPI application factory.

Run locally::

    cd apps/api && ATLAS_MODE=demo python3 -m uvicorn app.main:app --reload --port 8000

Interactive docs at http://localhost:8000/docs · contract in
``docs/architecture/api-contract.md``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.routers import (
    agents,
    detection,
    geometry,
    imagery,
    imports,
    meta,
    plots,
    simulate,
    tree_age,
)
from app.context import build_context
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.ratelimit import install_rate_limiting
from app.demo_seed import seed_demo_plots

DESCRIPTION = """
Open geospatial intelligence for tree planting, agricultural carbon potential and
sustainable land analysis.

**Every carbon figure is a scenario estimate with a low/central/high range,
`certified: false`, a confidence grade and a provenance chain. Nothing here is an
issued carbon credit.** Exact plot geometry is private by default; public views use a
generalized centroid. The optional explanation endpoint accepts derived indicators only.
"""

TAGS = [
    {"name": "meta", "description": "Health, regions, species, methodology registry, attribution."},
    {"name": "location", "description": "Server-side geocoding (provider policies respected)."},
    {
        "name": "plots",
        "description": "Plots → analysis → cube → trees → carbon estimate → policy → market → report.",
    },
    {
        "name": "reports",
        "description": "Rendered assessment reports (HTML, Markdown, JSON, PDF when available).",
    },
    {
        "name": "simulation",
        "description": "Deterministic what-if simulations with per-country programme context.",
    },
    {
        "name": "explanation",
        "description": "Plain-language explanation from indicators — never coordinates.",
    },
    {"name": "geometry", "description": "Pin + size, tree lines and typed coordinates → plots."},
    {
        "name": "imports",
        "description": "GeoJSON / KML / CSV / LAS / LAZ imports with optional tree detection.",
    },
    {"name": "detection", "description": "Tree-cover detection from satellite vegetation data."},
    {"name": "tree-age", "description": "Carbon by tree age and the rules that apply by age."},
    {"name": "imagery", "description": "Satellite / aerial imagery providers with licences."},
    {
        "name": "agents",
        "description": "Agentic AI framework: named agents, tools, transcripts, guardrails.",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.atlas_log_level)
    log = logging.getLogger("carboncreditbuy.api")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ctx = build_context(settings)
        app.state.context = ctx
        if settings.is_demo and settings.atlas_seed_demo:
            seed_demo_plots(ctx)
        log.info("api started", extra={"status": settings.atlas_mode})
        yield
        ctx.repo.close()

    app = FastAPI(
        title="CarbonCreditBuy API",
        version=__version__,
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
    )
    app.state.settings = settings

    install_error_handlers(app)
    install_rate_limiting(app, settings)
    app.add_middleware(
        RequestContextMiddleware,
        max_body_bytes=settings.atlas_max_body_bytes,
        max_upload_bytes=settings.max_upload_bytes,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
        max_age=600,
    )

    @app.middleware("http")
    async def _access_log(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        response = await call_next(request)
        log.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,  # query strings (which may hold coordinates) are not logged
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return response

    app.include_router(meta.router, prefix="/api/v1")
    app.include_router(plots.router, prefix="/api/v1")
    app.include_router(simulate.router, prefix="/api/v1")
    app.include_router(geometry.router, prefix="/api/v1")
    app.include_router(imports.router, prefix="/api/v1")
    app.include_router(detection.router, prefix="/api/v1")
    app.include_router(tree_age.router, prefix="/api/v1")
    app.include_router(imagery.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    return app


app = create_app()
