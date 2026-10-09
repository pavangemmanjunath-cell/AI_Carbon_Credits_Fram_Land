"""Seed the repository with the synthetic demo plots from ``data/sample/plots``.

Runs on startup in demo mode (``ATLAS_SEED_DEMO=true``) so the web app always
has data. Plots are synthetic polygons — never real farm boundaries.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.context import AppContext

log = logging.getLogger("atlas.seed")


def seed_demo_plots(ctx: AppContext, sample_dir: Path | None = None) -> list[str]:
    sample_dir = sample_dir or ctx.settings.sample_dir / "plots"
    seeded: list[str] = []
    if not sample_dir.is_dir():
        log.warning("sample directory missing: %s", sample_dir)
        return seeded
    for path in sorted(sample_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            sample = json.load(handle)
        plot_id = sample["plot_id"]
        if ctx.repo.get_plot(plot_id):
            continue
        plot = ctx.plots.create(
            geometry=sample["geometry"],
            name=sample.get("name", plot_id),
            country=sample.get("country"),
            source="synthetic-demo",
            plot_id=plot_id,
        )
        inventory = sample.get("inventory")
        if inventory:
            ctx.trees.create(plot, inventory)
        try:
            ctx.analysis.analyze(plot, ["landcover", "vegetation", "climate", "soil"], None)
            if inventory:
                ctx.carbon.estimate(plot, ctx.trees.latest(plot_id) or {}, "tree-biomass", None, {})
        except Exception:  # analysis failures must never block startup
            log.exception("demo seeding partially failed", extra={"plot_id": plot_id})
        seeded.append(plot_id)
    log.info("seeded %d demo plots", len(seeded))
    return seeded
