"""Typed errors raised by geo_engine."""

from __future__ import annotations


class GeoEngineError(Exception):
    """Base class for all geo_engine errors."""


class GeometryError(GeoEngineError, ValueError):
    """A polygon failed validation.

    ``code`` is a stable machine-readable identifier (e.g. ``"too_many_vertices"``)
    that the API maps onto an RFC 7807 problem ``type``.
    """

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class MissingDependencyError(GeoEngineError, ImportError):
    """A live-mode function was called without its optional dependency installed."""
