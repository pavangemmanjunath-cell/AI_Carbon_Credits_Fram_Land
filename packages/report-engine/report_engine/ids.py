"""Report identifiers: ``RPT-YYYY-MM-DD-NNNN`` (sequence restarts daily)."""

from __future__ import annotations

import re
import threading
from datetime import UTC, date, datetime

REPORT_ID_PATTERN = re.compile(r"^RPT-\d{4}-\d{2}-\d{2}-\d{4}$")


def new_report_id(day: date, sequence: int) -> str:
    if sequence < 1 or sequence > 9999:
        raise ValueError("report sequence must be within 1..9999")
    return f"RPT-{day.isoformat()}-{sequence:04d}"


class ReportIdSequencer:
    """Thread-safe daily counter. Persisted stores pass ``initial`` from their last id."""

    def __init__(self, initial: dict[str, int] | None = None) -> None:
        self._counts: dict[str, int] = dict(initial or {})
        self._lock = threading.Lock()

    def next_id(self, when: datetime | None = None) -> str:
        day = (when or datetime.now(UTC)).date()
        key = day.isoformat()
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            return new_report_id(day, self._counts[key])

    def observe(self, report_id: str) -> None:
        """Advance the counter past an existing id (used when loading persisted reports)."""
        if not REPORT_ID_PATTERN.match(report_id):
            return
        key, seq = report_id[4:14], int(report_id[15:])
        with self._lock:
            self._counts[key] = max(self._counts.get(key, 0), seq)
