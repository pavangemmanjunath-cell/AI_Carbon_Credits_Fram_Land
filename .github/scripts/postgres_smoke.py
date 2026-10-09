"""Run every PostgresRepository method against a real PostgreSQL database.

Why: ``apps/api/app/repositories/postgres.py`` holds the SQL and ``data/schemas/schema.sql``
holds the tables. Nothing else ties them together, so a change to one that the other does not
follow would only surface in production. This script calls each repository method once, so
the CI job fails first.

Usage, from the repository root, after applying the schema:

    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f data/schemas/schema.sql
    DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas \\
        python3 .github/scripts/postgres_smoke.py

It needs ``psycopg`` (the version pinned in requirements.txt). It writes one plot,
``PLT-CISMOKE``, and deletes it again, which cascades to everything derived from it. One row
stays in ``audit_events`` on purpose: the audit trail has no foreign key. Do not point it at a
database that holds real data.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.repositories.postgres import PostgresRepository  # noqa: E402

PLOT_ID = "PLT-CISMOKE"
INVENTORY_ID = "INV-0001"
ESTIMATE_ID = "EST-0001"
REPORT_ID = "RPT-2026-01-01-0001"

SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [
            [77.5946, 12.9716],
            [77.5986, 12.9716],
            [77.5986, 12.9756],
            [77.5946, 12.9756],
            [77.5946, 12.9716],
        ]
    ],
}


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Set DATABASE_URL, for example postgresql://atlas:atlas@localhost:5432/atlas")
        return 2

    plot = {
        "plot_id": PLOT_ID,
        "name": "ci smoke",
        "country": "IN",
        "geometry": SQUARE,
        "area_hectares": 19.2,
        "public_centroid": {"lat": 12.95, "lon": 77.6},
        "source": "api",
        "privacy": "private",
    }
    inventory = {"inventory_id": INVENTORY_ID, "plot_id": PLOT_ID, "tree_count": 10}
    estimate = {
        "estimate_id": ESTIMATE_ID,
        "plot_id": PLOT_ID,
        "inventory_id": INVENTORY_ID,
        "estimate": {"central": 2.0, "low": 1.0, "high": 3.0, "unit": "tCO2e/yr"},
        "confidence": "medium",
        "certified": False,
    }

    repo = PostgresRepository(url)
    try:
        # plots
        repo.save_plot(plot)
        repo.save_plot({**plot, "name": "renamed"})  # ON CONFLICT ... DO UPDATE
        assert repo.get_plot(PLOT_ID)["name"] == "renamed"
        assert [p["plot_id"] for p in repo.list_plots()] == [PLOT_ID]

        # analyses: the latest one wins
        repo.save_analysis(PLOT_ID, {"mode": "demo", "run": 1})
        repo.save_analysis(PLOT_ID, {"mode": "demo", "run": 2})
        assert repo.get_analysis(PLOT_ID)["run"] == 2

        # inventories and estimates
        repo.save_inventory(inventory)
        assert repo.list_inventories(PLOT_ID) == [inventory]
        assert repo.get_inventory(PLOT_ID, INVENTORY_ID) == inventory
        repo.save_estimate(estimate)
        assert repo.list_estimates(PLOT_ID) == [estimate]
        assert repo.get_estimate(PLOT_ID, ESTIMATE_ID) == estimate

        # reports
        repo.save_report(REPORT_ID, {"plot_id": PLOT_ID, "format": "html"}, b"<html></html>")
        meta, content = repo.get_report(REPORT_ID)
        assert meta["format"] == "html" and content == b"<html></html>"
        assert REPORT_ID in repo.report_ids()

        # generic records (imports, detections, agent runs)
        repo.save_record("import", "IMP-1", {"features": 1}, plot_id=PLOT_ID)
        repo.save_record("import", "IMP-1", {"features": 2}, plot_id=PLOT_ID)  # upsert
        repo.save_record("detection", "DET-1", {"trees": 3})  # a record without a plot
        assert repo.get_record("import", "IMP-1") == {"features": 2}
        assert repo.list_records("import", plot_id=PLOT_ID) == [{"features": 2}]
        assert repo.list_records("detection") == [{"trees": 3}]
        assert repo.delete_record("detection", "DET-1")
        assert not repo.delete_record("detection", "DET-1")

        # audit trail
        repo.audit("plot.created", PLOT_ID, {"area_hectares": 19.2})

        # deleting the plot cascades to everything derived from it
        assert repo.delete_plot(PLOT_ID)
        assert repo.get_plot(PLOT_ID) is None
        assert repo.get_analysis(PLOT_ID) is None
        assert repo.list_inventories(PLOT_ID) == []
        assert repo.list_estimates(PLOT_ID) == []
        assert repo.list_records("import", plot_id=PLOT_ID) == []
        assert REPORT_ID not in repo.report_ids()
    finally:
        repo.close()

    print("PostgresRepository and data/schemas/schema.sql agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
