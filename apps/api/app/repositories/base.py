"""Repository interface. Records are plain JSON-serialisable dicts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Repository(ABC):
    """Persistence boundary used by the services (memory or PostGIS)."""

    # plots -----------------------------------------------------------------
    @abstractmethod
    def save_plot(self, plot: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_plot(self, plot_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def list_plots(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def delete_plot(self, plot_id: str) -> bool: ...

    # analyses ----------------------------------------------------------------
    @abstractmethod
    def save_analysis(self, plot_id: str, analysis: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_analysis(self, plot_id: str) -> dict[str, Any] | None: ...

    # inventories -------------------------------------------------------------
    @abstractmethod
    def save_inventory(self, inventory: dict[str, Any]) -> None: ...

    @abstractmethod
    def list_inventories(self, plot_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_inventory(self, plot_id: str, inventory_id: str) -> dict[str, Any] | None: ...

    # estimates ---------------------------------------------------------------
    @abstractmethod
    def save_estimate(self, estimate: dict[str, Any]) -> None: ...

    @abstractmethod
    def list_estimates(self, plot_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_estimate(self, plot_id: str, estimate_id: str) -> dict[str, Any] | None: ...

    # reports -----------------------------------------------------------------
    @abstractmethod
    def save_report(self, report_id: str, meta: dict[str, Any], content: bytes) -> None: ...

    @abstractmethod
    def get_report(self, report_id: str) -> tuple[dict[str, Any], bytes] | None: ...

    @abstractmethod
    def report_ids(self) -> list[str]: ...

    # generic records (imports, agent runs, detections, …) -----------------------
    # Feature modules store their JSON documents here instead of adding new tables.
    # ``plot_id`` links a record to a plot so deleting the plot deletes its records.
    @abstractmethod
    def save_record(
        self, kind: str, record_id: str, record: dict[str, Any], plot_id: str | None = None
    ) -> None: ...

    @abstractmethod
    def get_record(self, kind: str, record_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def list_records(
        self, kind: str, plot_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Newest first."""

    @abstractmethod
    def delete_record(self, kind: str, record_id: str) -> bool: ...

    # audit -------------------------------------------------------------------
    @abstractmethod
    def audit(
        self, event: str, plot_id: str | None, detail: dict[str, Any] | None = None
    ) -> None: ...

    def close(self) -> None:  # pragma: no cover - optional
        return None
