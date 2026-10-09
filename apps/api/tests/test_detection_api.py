"""Tree-cover detection endpoints: POST /plots/{id}/detect and GET /plots/{id}/detections."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from shapely.geometry import shape
from shapely.ops import unary_union

from app.core.config import Settings
from app.main import create_app
from geo_engine.construct import geodesic_area_m2

ROOT = Path(__file__).resolve().parents[3]
DEMO_PLOTS = ["PLT-DEMOIN", "PLT-DEMOUS", "PLT-DEMOEU"]
PROBLEM = "application/problem+json"
SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [[77.53, 13.29], [77.54, 13.29], [77.54, 13.30], [77.53, 13.30], [77.53, 13.29]]
    ],
}


def settings_for(**env: Any) -> Settings:
    base: dict[str, Any] = {
        "ATLAS_MODE": "demo",
        "ATLAS_RATE_LIMIT_ENABLED": False,
        "ATLAS_API_KEYS": "",
        "ATLAS_LOG_LEVEL": "warning",
    }
    base.update(env)
    return Settings(**base)


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    with TestClient(create_app(settings_for())) as client:
        yield client


@pytest.fixture(scope="module")
def keyed_api() -> Iterator[TestClient]:
    with TestClient(create_app(settings_for(ATLAS_API_KEYS="s3cret"))) as client:
        yield client


def detect_url(plot_id: str) -> str:
    return f"/api/v1/plots/{plot_id}/detect"


def latest_url(plot_id: str) -> str:
    return f"/api/v1/plots/{plot_id}/detections"


def assert_problem(response, status: int, slug: str | None = None) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(PROBLEM)
    body = response.json()
    assert body["status"] == status and body["title"] and body["detail"]
    if slug:
        assert body["type"].endswith("/" + slug), body["type"]
    return body


def new_plot(client: TestClient, geometry: dict | None = None, **extra: Any) -> str:
    body = {"name": "Detection test plot", "country": "IN", "geometry": geometry or SQUARE, **extra}
    response = client.post("/api/v1/plots", json=body)
    assert response.status_code == 201, response.text
    return response.json()["plot_id"]


def plot_shape(client: TestClient, plot_id: str):
    return shape(client.get(f"/api/v1/plots/{plot_id}").json()["geometry"])


def threshold_from_config() -> float:
    config = yaml.safe_load((ROOT / "config" / "detection.yaml").read_text(encoding="utf-8"))
    return float(config["tree_cover"]["ndvi_tree_cover_threshold"]["value"])


# ---------------------------------------------------------------------------- contract
@pytest.mark.parametrize("plot_id", DEMO_PLOTS)
def test_detect_returns_the_contract_shape(api, plot_id):
    response = api.post(detect_url(plot_id), json={"target": "tree-cover", "min_confidence": 0.5})
    assert response.status_code == 200, response.text
    body = response.json()
    assert re.fullmatch(r"DET-[A-Z0-9]{6}", body["detection_id"])
    assert body["plot_id"] == plot_id and body["target"] == "tree-cover"
    assert body["method"].startswith("NDVI threshold + connected components on the ")
    assert body["method"].endswith(" m vegetation grid")
    assert body["index"] == "ndvi"
    assert body["threshold"] == threshold_from_config()  # read from config/detection.yaml
    assert re.fullmatch(r"\d{4}-\d{2}", body["month"])
    assert body["created_at"].endswith("Z") and body["privacy"] == "private"

    collection = body["features"]
    assert collection["type"] == "FeatureCollection"
    summary = body["summary"]
    assert set(summary) == {"patches", "covered_fraction", "area_hectares"}
    assert summary["patches"] == len(collection["features"]) > 0
    assert 0.0 < summary["covered_fraction"] <= 1.0 and summary["area_hectares"] > 0.0
    total_m2 = 0.0
    for number, feature in enumerate(collection["features"], start=1):
        assert feature["type"] == "Feature"
        assert shape(feature["geometry"]).geom_type in {"Polygon", "MultiPolygon"}
        properties = feature["properties"]
        assert properties["id"] == f"P{number}" and properties["label"] == "tree cover"
        assert 0.0 <= properties["confidence"] <= 1.0
        assert properties["area_m2"] > 0.0
        assert body["threshold"] <= properties["mean_ndvi"] <= 1.0
        total_m2 += properties["area_m2"]
    assert summary["area_hectares"] == pytest.approx(total_m2 / 10_000.0, abs=1e-3)


@pytest.mark.parametrize("plot_id", DEMO_PLOTS)
def test_patches_stay_inside_the_plot_and_cover_what_the_summary_says(api, plot_id):
    body = api.post(detect_url(plot_id)).json()
    plot = plot_shape(api, plot_id)
    patches = [shape(f["geometry"]) for f in body["features"]["features"]]
    for patch in patches:
        assert patch.is_valid and plot.buffer(1e-9).contains(patch)
    plot_ha = geodesic_area_m2(plot) / 10_000.0
    covered = unary_union(patches)
    assert geodesic_area_m2(covered) / 10_000.0 == pytest.approx(
        body["summary"]["area_hectares"], rel=0.01
    )
    assert body["summary"]["covered_fraction"] == pytest.approx(
        body["summary"]["area_hectares"] / plot_ha, abs=0.01
    )


def test_the_month_is_the_latest_one_of_the_vegetation_cube(api):
    cube = api.get("/api/v1/plots/PLT-DEMOIN/cube").json()
    assert api.post(detect_url("PLT-DEMOIN")).json()["month"] == cube["times"][-1]


def test_the_limitations_are_honest(api):
    limitations = api.post(detect_url("PLT-DEMOIN")).json()["limitations"]
    text = " ".join(limitations)
    assert "not individual crowns" in text
    assert "not a probability" in text
    assert "has not been calibrated" in text
    assert "Demo mode" in text  # the vegetation cube is synthetic in demo mode


def test_the_parameters_that_were_used_are_listed(api):
    parameters = api.post(detect_url("PLT-DEMOIN"), json={"min_confidence": 0.4}).json()[
        "parameters"
    ]
    assert parameters["threshold"] == threshold_from_config()
    assert parameters["min_confidence"] == 0.4
    assert parameters["cell_size_m"] > 0 and parameters["composite_months"]
    assert parameters["verification_status"] == "assumption"
    assert sum(parameters["weights"].values()) == pytest.approx(1.0)
    assert set(parameters["dropped_patches"]) == {"too_small", "low_confidence"}


def test_the_provenance_names_the_data_the_model_and_the_parameters(api):
    provenance = api.post(detect_url("PLT-DEMOIN")).json()["provenance"]
    assert provenance["mode"] == "demo" and provenance["api_version"] and provenance["generated_at"]
    assert provenance["sources"][0]["id"] == "synthetic-demo"
    assert provenance["sources"][0]["license"]
    assert provenance["model"] == {"id": "ndvi-threshold-connected-components", "version": "0.1.0"}
    parameter_set = provenance["parameter_set"]
    assert parameter_set["id"] == "config/detection.yaml#tree_cover" and parameter_set["version"]
    assert parameter_set["verification_status"] == "assumption"  # not calibrated: says so
    assert any("not a probability" in note for note in provenance["notes"])


def test_detection_is_deterministic(api):
    first = api.post(detect_url("PLT-DEMOUS")).json()
    second = api.post(detect_url("PLT-DEMOUS")).json()
    assert first["detection_id"] != second["detection_id"]
    for key in ("features", "summary", "month", "threshold", "limitations", "parameters", "method"):
        assert first[key] == second[key]


def test_each_plot_gets_its_own_result(api):
    results = {pid: api.post(detect_url(pid)).json()["summary"] for pid in DEMO_PLOTS}
    assert len({s["covered_fraction"] for s in results.values()}) == len(DEMO_PLOTS)


# ---------------------------------------------------------------------------- the request body
def test_the_body_is_optional_and_defaults_to_tree_cover_at_half_confidence(api):
    with_nothing = api.post(detect_url("PLT-DEMOIN"))
    with_empty = api.post(detect_url("PLT-DEMOIN"), json={})
    explicit = api.post(
        detect_url("PLT-DEMOIN"), json={"target": "tree-cover", "min_confidence": 0.5}
    )
    assert with_nothing.status_code == with_empty.status_code == explicit.status_code == 200
    assert with_nothing.json()["parameters"]["min_confidence"] == 0.5
    assert (
        with_nothing.json()["features"]
        == with_empty.json()["features"]
        == explicit.json()["features"]
    )


def test_min_confidence_drops_the_patches_that_look_less_certain(api):
    kept = api.post(detect_url("PLT-DEMOIN"), json={"min_confidence": 0}).json()
    none = api.post(detect_url("PLT-DEMOIN"), json={"min_confidence": 1}).json()
    assert kept["summary"]["patches"] >= 1
    assert none["summary"] == {"patches": 0, "covered_fraction": 0.0, "area_hectares": 0.0}
    assert none["features"] == {"type": "FeatureCollection", "features": []}
    assert none["parameters"]["dropped_patches"]["low_confidence"] == kept["summary"]["patches"]
    assert none["threshold"] == kept["threshold"]  # the rest of the record is the same


@pytest.mark.parametrize(
    "body",
    [
        {"target": "tree-species"},
        {"target": "crops"},
        {"min_confidence": 1.5},
        {"min_confidence": -0.1},
        {"min_confidence": "high"},
        {"min_confidence": None},
        {"threshold": 0.3},  # the threshold lives in config/detection.yaml, not in the request
        {"unknown": True},
    ],
)
def test_bad_bodies_are_422(api, body):
    problem = assert_problem(api.post(detect_url("PLT-DEMOIN"), json=body), 422, "validation-error")
    assert problem["errors"]


def test_a_body_that_is_not_json_is_422(api):
    response = api.post(
        detect_url("PLT-DEMOIN"), content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert_problem(response, 422, "validation-error")


# ---------------------------------------------------------------------------- stored result
def test_the_latest_detection_is_stored_with_the_plot(api):
    plot_id = new_plot(api)
    assert_problem(api.get(latest_url(plot_id)), 404, "detection-not-found")
    posted = api.post(detect_url(plot_id)).json()
    fetched = api.get(latest_url(plot_id))
    assert fetched.status_code == 200
    assert fetched.json() == posted

    newer = api.post(detect_url(plot_id), json={"min_confidence": 0.3}).json()
    assert newer["detection_id"] != posted["detection_id"]
    assert api.get(latest_url(plot_id)).json()["detection_id"] == newer["detection_id"]


def test_the_not_found_message_says_what_to_do(api):
    plot_id = new_plot(api)
    problem = assert_problem(api.get(latest_url(plot_id)), 404, "detection-not-found")
    assert f"POST /plots/{plot_id}/detect" in problem["detail"]


def test_only_the_five_latest_detections_of_a_plot_are_kept(api):
    plot_id = new_plot(api)
    ids = [api.post(detect_url(plot_id)).json()["detection_id"] for _ in range(7)]
    stored = api.app.state.context.repo.list_records("detection", plot_id, limit=100)
    assert [record["detection_id"] for record in stored] == ids[::-1][:5]
    assert api.get(latest_url(plot_id)).json()["detection_id"] == ids[-1]


def test_unknown_plots_are_404(api):
    problem = assert_problem(api.post(detect_url("PLT-NOPE")), 404, "plot-not-found")
    assert "PLT-NOPE" in problem["detail"]
    assert_problem(api.get(latest_url("PLT-NOPE")), 404, "plot-not-found")


def test_deleting_a_plot_deletes_its_detections(api):
    plot_id = new_plot(api)
    detection_id = api.post(detect_url(plot_id)).json()["detection_id"]
    repo = api.app.state.context.repo
    assert repo.get_record("detection", detection_id) is not None
    assert api.delete(f"/api/v1/plots/{plot_id}").status_code == 204
    assert repo.get_record("detection", detection_id) is None
    assert repo.list_records("detection", plot_id, limit=10) == []
    assert_problem(api.get(latest_url(plot_id)), 404, "plot-not-found")
    other = api.post(detect_url("PLT-DEMOIN")).json()["detection_id"]
    assert repo.get_record("detection", other) is not None  # other plots are untouched


def test_the_detection_is_audited_without_geometry(api):
    plot_id = new_plot(api)
    api.post(detect_url(plot_id))
    events = [e for e in api.app.state.context.repo.audit_events() if e["event"] == "plot.detected"]
    assert events and events[-1]["plot_id"] == plot_id
    assert set(events[-1]["detail"]) == {"target", "patches"}


# ---------------------------------------------------------------------------- other plots
def test_a_plot_made_from_a_pin_and_an_area_can_be_detected(api):
    geometry = api.post(
        "/api/v1/geometry/from-point",
        json={"lat": 13.2923, "lon": 77.5384, "area": {"value": 3, "unit": "ha"}},
    ).json()["geometry"]
    plot_id = new_plot(api, geometry, source="pin-and-area", boundary_quality="approximate")
    body = api.post(detect_url(plot_id)).json()
    assert body["plot_id"] == plot_id and body["summary"]["patches"] >= 1
    assert body["summary"]["area_hectares"] <= 3.05


@pytest.mark.parametrize("hectares", [0.02, 0.1])
def test_a_plot_smaller_than_a_few_grid_cells_has_no_patch_and_says_why(api, hectares):
    geometry = api.post(
        "/api/v1/geometry/from-point",
        json={"lat": 13.2923, "lon": 77.5384, "area": {"value": hectares, "unit": "ha"}},
    ).json()["geometry"]
    plot_id = new_plot(api, geometry, source="pin-and-area", boundary_quality="approximate")
    response = api.post(detect_url(plot_id))
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {"patches": 0, "covered_fraction": 0.0, "area_hectares": 0.0}
    assert any("few or no patches" in note for note in body["limitations"])


# ---------------------------------------------------------------------------- API key
def test_running_a_detection_needs_the_api_key_when_keys_are_configured(keyed_api):
    no_key = keyed_api.post(detect_url("PLT-DEMOIN"))
    assert no_key.status_code == 401 and no_key.headers["content-type"].startswith(PROBLEM)
    assert (
        keyed_api.post(detect_url("PLT-DEMOIN"), headers={"X-API-Key": "nope"}).status_code == 403
    )
    ok = keyed_api.post(detect_url("PLT-DEMOIN"), headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 200
    # reading the stored result stays open
    assert (
        keyed_api.get(latest_url("PLT-DEMOIN")).json()["detection_id"] == ok.json()["detection_id"]
    )


# ---------------------------------------------------------------------------- privacy
def test_coordinates_are_never_logged_by_the_detection(api, caplog):
    plot_id = new_plot(
        api,
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.123456, 13.654321],
                    [77.133456, 13.654321],
                    [77.133456, 13.664321],
                    [77.123456, 13.664321],
                    [77.123456, 13.654321],
                ]
            ],
        },
    )
    with caplog.at_level(logging.DEBUG):
        posted = api.post(detect_url(plot_id))
        api.get(latest_url(plot_id))
        api.post(detect_url(plot_id), json={"min_confidence": 7})  # a validation problem
    assert posted.status_code == 200
    logged = " ".join(
        f"{r.getMessage()} {r.__dict__.get('path', '')} {r.exc_text or ''}" for r in caplog.records
    )
    assert logged  # the requests themselves were logged
    for fragment in ("77.123456", "13.654321", "77.133456", "13.664321"):
        assert fragment not in logged
