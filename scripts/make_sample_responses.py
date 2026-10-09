#!/usr/bin/env python3
"""Regenerate ``data/sample/responses/*.json`` from the API in demo mode.

Usage: ``python3 scripts/make_sample_responses.py`` (from the repository root).
All exchange formats are JSON; these files double as web-app demo fixtures.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.environ.setdefault("ATLAS_MODE", "demo")
os.environ.setdefault("ATLAS_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("ATLAS_LOG_LEVEL", "warning")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

OUT = ROOT / "data" / "sample" / "responses"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False, ATLAS_API_KEYS="")  # type: ignore[call-arg]
    with TestClient(create_app(settings)) as client:
        gets = {
            "health": "/api/v1/health",
            "regions": "/api/v1/regions",
            "species": "/api/v1/species?country=IN",
            "methodologies": "/api/v1/methodologies",
            "attribution": "/api/v1/attribution",
            "geocode": "/api/v1/geocode?q=Doddaballapura&country=IN",
            "plots": "/api/v1/plots",
            "plot": "/api/v1/plots/PLT-DEMOIN",
            "plot-public": "/api/v1/plots/PLT-DEMOIN/public",
            "analysis": "/api/v1/plots/PLT-DEMOIN/analysis",
            "vegetation": "/api/v1/plots/PLT-DEMOIN/vegetation",
            "cube": "/api/v1/plots/PLT-DEMOIN/cube?index=ndvi&months=36",
            "trees": "/api/v1/plots/PLT-DEMOIN/trees",
            "carbon-estimate": "/api/v1/plots/PLT-DEMOIN/carbon-estimate",
            "policy-eligibility": "/api/v1/plots/PLT-DEMOIN/policy-eligibility",
            "market-scenario": "/api/v1/plots/PLT-DEMOIN/market-scenario",
        }
        for name, path in gets.items():
            resp = client.get(path)
            resp.raise_for_status()
            (OUT / f"{name}.json").write_text(
                json.dumps(resp.json(), indent=2, ensure_ascii=False) + "\n"
            )
        for country, species in (("IN", "mango"), ("US", "pecan"), ("EU", "olive")):
            body = {
                "country": country,
                "species_id": species,
                "tree_count": 420,
                "planting_year": 2023,
                "horizon_years": 30,
                "area_hectares": 2.13,
            }
            resp = client.post("/api/v1/simulate", json=body)
            resp.raise_for_status()
            (OUT / f"simulate-{country}.json").write_text(
                json.dumps(resp.json(), indent=2, ensure_ascii=False) + "\n"
            )
        report = client.post("/api/v1/plots/PLT-DEMOIN/report", json={"format": "json"})
        report.raise_for_status()
        (OUT / "report-meta.json").write_text(json.dumps(report.json(), indent=2) + "\n")
        (OUT / "report.json").write_text(client.get(report.json()["url"]).text)
        html = client.post("/api/v1/plots/PLT-DEMOIN/report", json={"format": "html"})
        (OUT / "report.html").write_text(client.get(html.json()["url"]).text)
        explain = client.post(
            "/api/v1/explain",
            json={
                "language": "en",
                "indicators": {
                    "area_hectares": 2.13,
                    "tree_count": 420,
                    "species": "Mango",
                    "ndvi": 0.62,
                    "ndvi_trend_pct": 12.0,
                    "estimate_central": 10.6,
                    "estimate_low": 7.4,
                    "estimate_high": 13.8,
                    "confidence": "medium",
                    "missing_evidence": ["dbh", "baseline"],
                },
            },
        )
        (OUT / "explain.json").write_text(
            json.dumps(explain.json(), indent=2, ensure_ascii=False) + "\n"
        )
    print(f"wrote {len(list(OUT.glob('*')))} files to {OUT}")


if __name__ == "__main__":
    main()
