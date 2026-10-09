"""Lazy per-application service registry for feature modules.

Feature routers build their service on first use and cache it on the
application context, so new features do not need to edit ``context.py``::

    def _service(ctx: AppContext) -> ImportService:
        return service(ctx, "imports", lambda: ImportService(ctx))
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

_lock = threading.Lock()


def service[T](ctx: AppContext, name: str, factory: Callable[[], T]) -> T:
    """Return ``ctx.extras[name]``, creating it once with ``factory``."""
    existing = ctx.extras.get(name)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    with _lock:
        existing = ctx.extras.get(name)
        if existing is None:
            existing = factory()
            ctx.extras[name] = existing
    return existing  # type: ignore[no-any-return]
