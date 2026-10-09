"""Plots larger than the vegetation grid get a clear 422, not an upstream 502."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client() -> TestClient:
    settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False, ATLAS_SEED_DEMO=False)  # type: ignore[call-arg]
    return TestClient(create_app(settings))


def _square(lon: float, lat: float, half_deg: float) -> dict:
    ring = [
        [lon - half_deg, lat - half_deg],
        [lon + half_deg, lat - half_deg],
        [lon + half_deg, lat + half_deg],
        [lon - half_deg, lat + half_deg],
        [lon - half_deg, lat - half_deg],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def test_large_plot_cube_and_detection_return_422() -> None:
    with _client() as client:
        # ~6.6 km × 6.6 km ≈ 4,400 ha: allowed as a plot (limit 10,000 ha) but more than
        # 40,000 cells of 30 m for the vegetation grid.
        created = client.post(
            "/api/v1/plots",
            json={"name": "Big estate", "country": "IN", "geometry": _square(77.5, 13.3, 0.03)},
        )
        assert created.status_code == 201, created.text
        plot_id = created.json()["plot_id"]

        cube = client.get(f"/api/v1/plots/{plot_id}/cube")
        assert cube.status_code == 422
        problem = cube.json()
        assert problem["type"].endswith("plot-too-large-for-grid")
        assert "Split the land" in problem["detail"]

        detect = client.post(f"/api/v1/plots/{plot_id}/detect", json={"target": "tree-cover"})
        assert detect.status_code == 422


def test_normal_plot_cube_still_works() -> None:
    with _client() as client:
        created = client.post(
            "/api/v1/plots",
            json={"name": "Small", "country": "IN", "geometry": _square(77.5, 13.3, 0.001)},
        )
        plot_id = created.json()["plot_id"]
        assert client.get(f"/api/v1/plots/{plot_id}/cube").status_code == 200
