"""RFC 7807 ``application/problem+json`` error handling."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("atlas.api")

PROBLEM_TYPE_BASE = "https://agricarbon-atlas.org/problems/"
_TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    413: "Payload Too Large",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


class ProblemError(Exception):
    """Raise anywhere in the service layer to produce a problem+json response."""

    def __init__(
        self,
        status: int,
        detail: str,
        *,
        title: str | None = None,
        type_slug: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.title = title or _TITLES.get(status, "Error")
        self.type_slug = type_slug or self.title.lower().replace(" ", "-")
        self.extra = extra or {}


def problem_response(
    request: Request,
    status: int,
    detail: str,
    *,
    title: str | None = None,
    type_slug: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    title = title or _TITLES.get(status, "Error")
    body: dict[str, Any] = {
        "type": PROBLEM_TYPE_BASE + (type_slug or title.lower().replace(" ", "-")),
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
    }
    if extra:
        body.update(extra)
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    return JSONResponse(
        body, status_code=status, media_type="application/problem+json", headers=headers
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(request: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(
            request,
            exc.status,
            exc.detail,
            title=exc.title,
            type_slug=exc.type_slug,
            extra=exc.extra,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return problem_response(request, exc.status_code, detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            errors.append({"field": loc, "message": err.get("msg", "invalid")})
        return problem_response(
            request,
            422,
            "Request validation failed.",
            type_slug="validation-error",
            extra={"errors": errors},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s", request.url.path)
        return problem_response(request, 500, "An unexpected error occurred.")
