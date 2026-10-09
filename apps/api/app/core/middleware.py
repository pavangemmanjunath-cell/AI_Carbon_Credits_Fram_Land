"""Security headers, request ids and request-size limits."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cache-Control": "no-store",
    "Cross-Origin-Resource-Policy": "cross-origin",
}
# The interactive docs need inline scripts/styles from the CDN FastAPI uses.
DOCS_CSP = (
    "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: "
    "https://fastapi.tiangolo.com; connect-src 'self'"
)
API_CSP = "default-src 'none'; frame-ancestors 'none'"
REPORT_CSP = (
    "default-src 'none'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; img-src data:; frame-ancestors *"
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID, security headers and a Content-Length guard."""

    def __init__(  # type: ignore[no-untyped-def]
        self,
        app,
        max_body_bytes: int = 1_000_000,
        max_upload_bytes: int = 50 * 1024 * 1024,
        upload_prefixes: tuple[str, ...] = ("/api/v1/imports",),
    ) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes
        self.max_upload_bytes = max_upload_bytes
        self.upload_prefixes = upload_prefixes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        length = request.headers.get("content-length")
        limit = (
            self.max_upload_bytes
            if request.url.path.startswith(self.upload_prefixes)
            else self.max_body_bytes
        )
        if length and length.isdigit() and int(length) > limit:
            return JSONResponse(
                {
                    "type": "https://agricarbon-atlas.org/problems/payload-too-large",
                    "title": "Payload Too Large",
                    "status": 413,
                    "detail": f"Request body exceeds {limit} bytes.",
                    "instance": request.url.path,
                },
                status_code=413,
                media_type="application/problem+json",
            )
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        path = request.url.path
        if path.startswith(("/docs", "/redoc")) or path.endswith("openapi.json"):
            response.headers.setdefault("Content-Security-Policy", DOCS_CSP)
        elif "/reports/" in path:
            response.headers.setdefault("Content-Security-Policy", REPORT_CSP)
            # Reports are meant to be embedded by the web app (sandboxed iframe).
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            response.headers.setdefault("Content-Security-Policy", API_CSP)
        response.headers["X-Request-ID"] = request.state.request_id
        return response
