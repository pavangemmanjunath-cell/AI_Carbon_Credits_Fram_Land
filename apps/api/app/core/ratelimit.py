"""Per-client rate limiting with slowapi (disable with ATLAS_RATE_LIMIT_ENABLED=false)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import Settings


def _client_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key[:8]}"
    return get_remote_address(request)


def install_rate_limiting(app: FastAPI, settings: Settings) -> Limiter:
    limiter = Limiter(
        key_func=_client_key,
        default_limits=[settings.atlas_rate_limit],
        enabled=settings.atlas_rate_limit_enabled,
        headers_enabled=True,
    )
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            {
                "type": "https://agricarbon-atlas.org/problems/rate-limited",
                "title": "Too Many Requests",
                "status": 429,
                "detail": f"Rate limit exceeded: {exc.detail}",
                "instance": request.url.path,
            },
            status_code=429,
            media_type="application/problem+json",
            headers={"Retry-After": "60"},
        )

    app.add_middleware(SlowAPIMiddleware)
    return limiter
