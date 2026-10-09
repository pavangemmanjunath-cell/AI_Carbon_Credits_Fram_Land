"""PostgreSQL + PostGIS repository (``ATLAS_REPOSITORY=postgres``).

Uses psycopg 3 (imported lazily so the default install stays light). Tables
are created by ``data/schemas/schema.sql``; records are stored as JSONB with
the plot geometry additionally kept as a PostGIS ``geometry(Polygon, 4326)``
column so spatial queries are possible later.
"""

from __future__ import annotations

import json
from typing import Any

from app.repositories.base import Repository


class PostgresRepository(Repository):
    def __init__(self, dsn: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("psycopg is required for ATLAS_REPOSITORY=postgres") from exc
        self._psycopg = psycopg
        self._conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)

    def _exec(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return list(cur.fetchall())
            return []

    # plots
    def save_plot(self, plot: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO plots (plot_id, country, name, geom, area_hectares, public_centroid_lat,
                               public_centroid_lon, source, record)
            VALUES (%s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (plot_id) DO UPDATE SET record = EXCLUDED.record, name = EXCLUDED.name,
                geom = EXCLUDED.geom, area_hectares = EXCLUDED.area_hectares, updated_at = now()
            """,
            (
                plot["plot_id"],
                plot.get("country"),
                plot.get("name"),
                json.dumps(plot["geometry"]),
                plot["area_hectares"],
                plot["public_centroid"]["lat"],
                plot["public_centroid"]["lon"],
                plot.get("source"),
                json.dumps(plot),
            ),
        )

    def get_plot(self, plot_id: str) -> dict[str, Any] | None:
        rows = self._exec("SELECT record FROM plots WHERE plot_id = %s", (plot_id,))
        return rows[0]["record"] if rows else None

    def list_plots(self) -> list[dict[str, Any]]:
        return [r["record"] for r in self._exec("SELECT record FROM plots ORDER BY created_at")]

    def delete_plot(self, plot_id: str) -> bool:
        self._exec("DELETE FROM records WHERE plot_id = %s", (plot_id,))
        rows = self._exec("DELETE FROM plots WHERE plot_id = %s RETURNING plot_id", (plot_id,))
        return bool(rows)

    # analyses
    def save_analysis(self, plot_id: str, analysis: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO land_observations (plot_id, record) VALUES (%s, %s::jsonb)
            ON CONFLICT (plot_id) DO UPDATE SET record = EXCLUDED.record, observed_at = now()
            """,
            (plot_id, json.dumps(analysis)),
        )

    def get_analysis(self, plot_id: str) -> dict[str, Any] | None:
        rows = self._exec("SELECT record FROM land_observations WHERE plot_id = %s", (plot_id,))
        return rows[0]["record"] if rows else None

    # inventories
    def save_inventory(self, inventory: dict[str, Any]) -> None:
        self._exec(
            "INSERT INTO tree_inventory (inventory_id, plot_id, record) VALUES (%s, %s, %s::jsonb)",
            (inventory["inventory_id"], inventory["plot_id"], json.dumps(inventory)),
        )

    def list_inventories(self, plot_id: str) -> list[dict[str, Any]]:
        rows = self._exec(
            "SELECT record FROM tree_inventory WHERE plot_id = %s ORDER BY created_at", (plot_id,)
        )
        return [r["record"] for r in rows]

    def get_inventory(self, plot_id: str, inventory_id: str) -> dict[str, Any] | None:
        rows = self._exec(
            "SELECT record FROM tree_inventory WHERE plot_id = %s AND inventory_id = %s",
            (plot_id, inventory_id),
        )
        return rows[0]["record"] if rows else None

    # estimates
    def save_estimate(self, estimate: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO carbon_estimates (estimate_id, plot_id, inventory_id, central, low, high, unit,
                                          confidence, record)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                estimate["estimate_id"],
                estimate["plot_id"],
                estimate.get("inventory_id"),
                estimate["estimate"]["central"],
                estimate["estimate"]["low"],
                estimate["estimate"]["high"],
                estimate["estimate"]["unit"],
                estimate["confidence"],
                json.dumps(estimate),
            ),
        )

    def list_estimates(self, plot_id: str) -> list[dict[str, Any]]:
        rows = self._exec(
            "SELECT record FROM carbon_estimates WHERE plot_id = %s ORDER BY created_at", (plot_id,)
        )
        return [r["record"] for r in rows]

    def get_estimate(self, plot_id: str, estimate_id: str) -> dict[str, Any] | None:
        rows = self._exec(
            "SELECT record FROM carbon_estimates WHERE plot_id = %s AND estimate_id = %s",
            (plot_id, estimate_id),
        )
        return rows[0]["record"] if rows else None

    # reports
    def save_report(self, report_id: str, meta: dict[str, Any], content: bytes) -> None:
        self._exec(
            "INSERT INTO reports (report_id, plot_id, format, meta, content) VALUES (%s, %s, %s, %s::jsonb, %s)",
            (report_id, meta.get("plot_id"), meta.get("format"), json.dumps(meta), content),
        )

    def get_report(self, report_id: str) -> tuple[dict[str, Any], bytes] | None:
        rows = self._exec("SELECT meta, content FROM reports WHERE report_id = %s", (report_id,))
        if not rows:
            return None
        return rows[0]["meta"], bytes(rows[0]["content"])

    def report_ids(self) -> list[str]:
        return [r["report_id"] for r in self._exec("SELECT report_id FROM reports")]

    # generic records (table `records`, see data/schemas/schema.sql)
    def save_record(
        self, kind: str, record_id: str, record: dict[str, Any], plot_id: str | None = None
    ) -> None:
        self._exec(
            """
            INSERT INTO records (kind, record_id, plot_id, record)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (kind, record_id) DO UPDATE SET record = EXCLUDED.record,
                plot_id = EXCLUDED.plot_id, updated_at = now()
            """,
            (kind, record_id, plot_id, json.dumps(record)),
        )

    def get_record(self, kind: str, record_id: str) -> dict[str, Any] | None:
        rows = self._exec(
            "SELECT record FROM records WHERE kind = %s AND record_id = %s", (kind, record_id)
        )
        return rows[0]["record"] if rows else None

    def list_records(
        self, kind: str, plot_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        if plot_id is None:
            rows = self._exec(
                "SELECT record FROM records WHERE kind = %s ORDER BY created_at DESC LIMIT %s",
                (kind, limit),
            )
        else:
            rows = self._exec(
                "SELECT record FROM records WHERE kind = %s AND plot_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (kind, plot_id, limit),
            )
        return [r["record"] for r in rows]

    def delete_record(self, kind: str, record_id: str) -> bool:
        rows = self._exec(
            "DELETE FROM records WHERE kind = %s AND record_id = %s RETURNING record_id",
            (kind, record_id),
        )
        return bool(rows)

    # audit
    def audit(self, event: str, plot_id: str | None, detail: dict[str, Any] | None = None) -> None:
        self._exec(
            "INSERT INTO audit_events (event, plot_id, detail) VALUES (%s, %s, %s::jsonb)",
            (event, plot_id, json.dumps(detail or {})),
        )

    def close(self) -> None:
        self._conn.close()
