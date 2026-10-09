"""Small shared helpers for the services."""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime
from typing import Any

from app import __version__

API_VERSION = "1"
_ALPHABET = string.ascii_uppercase + string.digits


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def current_year() -> int:
    return datetime.now(UTC).year


def short_id(prefix: str, length: int = 6) -> str:
    return prefix + "".join(secrets.choice(_ALPHABET) for _ in range(length))


def base_provenance(mode: str, sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "api_version": API_VERSION,
        "app_version": __version__,
        "mode": mode,
        "sources": list(sources or []),
        "notes": [],
    }
