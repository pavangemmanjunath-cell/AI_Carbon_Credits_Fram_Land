"""API-key protection for mutating endpoints (optional; enabled when keys exist)."""

from __future__ import annotations

import hmac

from fastapi import Header, Request

from app.core.config import Settings, get_settings
from app.core.errors import ProblemError


def _settings_for(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Reject mutating calls without a valid key when ``ATLAS_API_KEYS`` is configured."""
    keys = _settings_for(request).api_keys
    if not keys:
        return
    if not x_api_key:
        raise ProblemError(401, "X-API-Key header is required.", type_slug="api-key-required")
    if not any(hmac.compare_digest(x_api_key, key) for key in keys):
        raise ProblemError(403, "Invalid API key.", type_slug="api-key-invalid")
