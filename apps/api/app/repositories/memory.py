"""Thread-safe in-memory repository (default; ideal for demo mode and tests)."""

from __future__ import annotations

import copy
import threading
from datetime import UTC, datetime
from typing import Any

from app.repositories.base import Repository


class MemoryRepository(Repository):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._plots: dict[str, dict[str, Any]] = {}
        self._analyses: dict[str, dict[str, Any]] = {}
        self._inventories: dict[str, list[dict[str, Any]]] = {}
        self._estimates: dict[str, list[dict[str, Any]]] = {}
        self._reports: dict[str, tuple[dict[str, Any], bytes]] = {}
        self._audit: list[dict[str, Any]] = []
        # kind -> record_id -> (plot_id, sequence, record)
        self._records: dict[str, dict[str, tuple[str | None, int, dict[str, Any]]]] = {}
        self._sequence = 0

    # plots
    def save_plot(self, plot: dict[str, Any]) -> None:
        with self._lock:
            self._plots[plot["plot_id"]] = copy.deepcopy(plot)

    def get_plot(self, plot_id: str) -> dict[str, Any] | None:
        with self._lock:
            plot = self._plots.get(plot_id)
            return copy.deepcopy(plot) if plot else None

    def list_plots(self) -> list[dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(p) for p in self._plots.values()]

    def delete_plot(self, plot_id: str) -> bool:
        with self._lock:
            existed = self._plots.pop(plot_id, None) is not None
            self._analyses.pop(plot_id, None)
            self._inventories.pop(plot_id, None)
            self._estimates.pop(plot_id, None)
            for records in self._records.values():
                for record_id in [k for k, v in records.items() if v[0] == plot_id]:
                    records.pop(record_id, None)
            return existed

    # analyses
    def save_analysis(self, plot_id: str, analysis: dict[str, Any]) -> None:
        with self._lock:
            self._analyses[plot_id] = copy.deepcopy(analysis)

    def get_analysis(self, plot_id: str) -> dict[str, Any] | None:
        with self._lock:
            analysis = self._analyses.get(plot_id)
            return copy.deepcopy(analysis) if analysis else None

    # inventories
    def save_inventory(self, inventory: dict[str, Any]) -> None:
        with self._lock:
            self._inventories.setdefault(inventory["plot_id"], []).append(copy.deepcopy(inventory))

    def list_inventories(self, plot_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(i) for i in self._inventories.get(plot_id, [])]

    def get_inventory(self, plot_id: str, inventory_id: str) -> dict[str, Any] | None:
        with self._lock:
            for inv in self._inventories.get(plot_id, []):
                if inv["inventory_id"] == inventory_id:
                    return copy.deepcopy(inv)
            return None

    # estimates
    def save_estimate(self, estimate: dict[str, Any]) -> None:
        with self._lock:
            self._estimates.setdefault(estimate["plot_id"], []).append(copy.deepcopy(estimate))

    def list_estimates(self, plot_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(e) for e in self._estimates.get(plot_id, [])]

    def get_estimate(self, plot_id: str, estimate_id: str) -> dict[str, Any] | None:
        with self._lock:
            for est in self._estimates.get(plot_id, []):
                if est["estimate_id"] == estimate_id:
                    return copy.deepcopy(est)
            return None

    # reports
    def save_report(self, report_id: str, meta: dict[str, Any], content: bytes) -> None:
        with self._lock:
            self._reports[report_id] = (copy.deepcopy(meta), bytes(content))

    def get_report(self, report_id: str) -> tuple[dict[str, Any], bytes] | None:
        with self._lock:
            item = self._reports.get(report_id)
            return (copy.deepcopy(item[0]), item[1]) if item else None

    def report_ids(self) -> list[str]:
        with self._lock:
            return list(self._reports)

    # generic records
    def save_record(
        self, kind: str, record_id: str, record: dict[str, Any], plot_id: str | None = None
    ) -> None:
        with self._lock:
            self._sequence += 1
            self._records.setdefault(kind, {})[record_id] = (
                plot_id,
                self._sequence,
                copy.deepcopy(record),
            )

    def get_record(self, kind: str, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._records.get(kind, {}).get(record_id)
            return copy.deepcopy(item[2]) if item else None

    def list_records(
        self, kind: str, plot_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = [
                v
                for v in self._records.get(kind, {}).values()
                if plot_id is None or v[0] == plot_id
            ]
            items.sort(key=lambda v: v[1], reverse=True)
            return [copy.deepcopy(v[2]) for v in items[: max(0, limit)]]

    def delete_record(self, kind: str, record_id: str) -> bool:
        with self._lock:
            return self._records.get(kind, {}).pop(record_id, None) is not None

    # audit
    def audit(self, event: str, plot_id: str | None, detail: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._audit.append(
                {
                    "at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "event": event,
                    "plot_id": plot_id,
                    "detail": detail or {},
                }
            )
            if len(self._audit) > 10_000:
                del self._audit[: len(self._audit) - 10_000]

    def audit_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._audit)
