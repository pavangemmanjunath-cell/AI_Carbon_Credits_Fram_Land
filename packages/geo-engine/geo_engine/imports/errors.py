"""Errors raised while reading an uploaded file.

``code`` is a stable machine-readable identifier; the API maps ``unsupported_format`` onto
HTTP 415 and everything else onto 422.
"""

from __future__ import annotations

from geo_engine.errors import GeoEngineError


class ImportDataError(GeoEngineError, ValueError):
    """The upload could not be read or interpreted (unreadable, unsafe, too large, empty …)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class UnsupportedFormatError(ImportDataError):
    """The file format is not supported (HTTP 415)."""

    def __init__(self, detail: str, code: str = "unsupported_format") -> None:
        super().__init__(code, detail)
