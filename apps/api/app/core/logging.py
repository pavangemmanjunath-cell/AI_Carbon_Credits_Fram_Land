"""Structured logging that never records coordinates or geometry.

Services log plot ids, counts and durations only. A filter scrubs anything
that looks like a coordinate pair or a GeoJSON geometry from log records as a
defence in depth.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from typing import Any

_COORD_RE = re.compile(r"-?\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}")
_GEOM_RE = re.compile(r'"coordinates"\s*:\s*\[.*?\]\]\]?', re.DOTALL)


class CoordinateScrubber(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        scrubbed = _GEOM_RE.sub('"coordinates": "[redacted]"', message)
        scrubbed = _COORD_RE.sub("[coords redacted]", scrubbed)
        if scrubbed != message:
            record.msg = scrubbed
            record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("request_id", "plot_id", "duration_ms", "status", "path", "method"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "info") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CoordinateScrubber())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").disabled = True
