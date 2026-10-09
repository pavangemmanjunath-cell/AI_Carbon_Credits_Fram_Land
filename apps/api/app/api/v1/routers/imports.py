"""File import endpoints (see docs/architecture/api-contract.md §v0.2).

``POST /imports`` takes a multipart upload. The size limit (``ATLAS_MAX_UPLOAD_MB``) is enforced
three times: the middleware rejects a too-large ``Content-Length`` before reading anything, the
route below counts the bytes of the request stream so a body **without** ``Content-Length``
(chunked transfer) is cut off as soon as it exceeds the limit, and the file itself is read in
1 MiB chunks. The raw file is never stored.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.routing import APIRoute

from app.context import AppContext
from app.core.config import get_settings
from app.core.errors import ProblemError
from app.core.security import require_api_key
from app.dependencies import get_context
from app.services.imports import PURPOSES, ImportService, safe_filename
from app.services.registry import service

CHUNK_BYTES = 1024 * 1024
ENVELOPE_BYTES = 1024 * 1024  # multipart boundaries and headers around the file
mutating = [Depends(require_api_key)]


def _upload_limit(request: Request) -> int:
    settings = getattr(request.app.state, "settings", None) or get_settings()
    return int(settings.max_upload_bytes)


def _too_large(limit: int) -> HTTPException:
    return HTTPException(
        status_code=413,
        detail=f"The upload is larger than the limit of {limit // (1024 * 1024)} MB.",
    )


class _LimitedRequest(Request):
    """A request whose body stream raises 413 once it passes the upload limit."""

    async def stream(self) -> AsyncGenerator[bytes, None]:
        limit = _upload_limit(self) + ENVELOPE_BYTES
        total = 0
        async for chunk in super().stream():
            total += len(chunk)
            if total > limit:
                raise _too_large(limit - ENVELOPE_BYTES)
            yield chunk


class UploadRoute(APIRoute):
    """Route class that applies the streaming size limit while the multipart body is parsed."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            return await original(_LimitedRequest(request.scope, request.receive))

        return handler


router = APIRouter(tags=["imports"], route_class=UploadRoute)


def _service(ctx: AppContext) -> ImportService:
    return service(ctx, "imports", lambda: ImportService(ctx))


def read_limited(upload: UploadFile, limit: int) -> bytes:
    """Read an upload in 1 MiB chunks; 413 as soon as it exceeds ``limit`` bytes."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = upload.file.read(CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ProblemError(
                413,
                f"The file is larger than the upload limit of {limit // (1024 * 1024)} MB.",
                type_slug="payload-too-large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/imports",
    status_code=201,
    dependencies=mutating,
    summary="Import data: a GeoJSON, KML, KMZ, CSV, LAS or LAZ file (the file is not stored)",
)
def create_import(
    file: UploadFile = File(..., description=".geojson/.json, .kml, .kmz, .csv, .las or .laz"),
    plot_id: str | None = Form(None, description="Link the import to a plot"),
    purpose: str = Form("auto", description="auto | boundary | trees"),
    run_detection: bool = Form(True, description="Run tree detection on import (point clouds)"),
    min_confidence: float | None = Form(
        None, ge=0, le=1, description="Minimum score/confidence for trees from a file"
    ),
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    if purpose not in PURPOSES:
        raise ProblemError(
            422, f"purpose must be one of {', '.join(PURPOSES)}.", type_slug="validation-error"
        )
    data = read_limited(file, ctx.settings.max_upload_bytes)
    return _service(ctx).create(
        data,
        safe_filename(file.filename),
        plot_id=plot_id or None,
        purpose=purpose,
        run_detection=run_detection,
        min_confidence=min_confidence,
    )


@router.get("/imports", summary="Imports (newest first), optionally for one plot; no map preview")
def list_imports(
    plot_id: str | None = None, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    return {"items": _service(ctx).list(plot_id)}


@router.get("/imports/{import_id}", summary="One import, including its map preview")
def get_import(import_id: str, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    return _service(ctx).get(import_id)


@router.delete(
    "/imports/{import_id}", status_code=204, dependencies=mutating, summary="Delete an import"
)
def delete_import(import_id: str, ctx: AppContext = Depends(get_context)) -> Response:
    _service(ctx).delete(import_id)
    return Response(status_code=204)
