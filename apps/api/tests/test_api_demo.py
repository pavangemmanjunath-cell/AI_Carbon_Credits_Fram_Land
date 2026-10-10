"""End-to-end API tests in demo mode (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "data" / "schemas"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / name).read_text())
    store = {
        json.loads(p.read_text())["$id"]: json.loads(p.read_text()) for p in SCHEMAS.glob("*.json")
    }
    store.update({p.name: json.loads(p.read_text()) for p in SCHEMAS.glob("*.json")})
    resolver = RefResolver(base_uri=schema.get("$id", ""), referrer=schema, store=store)
    return Draft202012Validator(schema, resolver=resolver)


# --------------------------------------------------------------------------- meta
def test_health_reports_demo_mode(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok" and body["mode"] == "demo"


def test_regions_species_methodologies_attribution(client):
    regions = client.get("/api/v1/regions").json()
    assert {r["id"] for r in regions} == {"IN", "US", "EU"}
    india = next(r for r in regions if r["id"] == "IN")
    assert india["currency"] == "INR" and india["units"]["area"] == "hectare"
    assert any(p["id"] == "in-gcp" for p in india["programmes"])
    species = client.get("/api/v1/species?country=IN").json()
    assert "mango" in {s["id"] for s in species}
    assert (
        "wood_density_g_cm3" in species[0]
        and "verification_status" in species[0]["wood_density_g_cm3"]
    )
    assert client.get("/api/v1/species?country=DE").json()  # EU member resolves to EU species
    methods = client.get("/api/v1/methodologies").json()
    assert any(m["id"] == "verra-vm0042" for m in methods)
    attribution = client.get("/api/v1/attribution").json()["items"]
    assert any("OpenStreetMap" in a["text"] for a in attribution)


def test_geocode_demo(client):
    body = client.get("/api/v1/geocode", params={"q": "Dodda", "country": "IN"}).json()
    assert body["results"] and body["results"][0]["admin"]["country"] == "IN"
    rev = client.get("/api/v1/reverse-geocode", params={"lat": 13.29, "lon": 77.54}).json()
    assert rev["country"] == "IN"


# --------------------------------------------------------------------------- demo plots
def test_demo_plots_are_seeded_and_private_fields_hidden_in_public_view(client):
    items = client.get("/api/v1/plots").json()["items"]
    ids = {p["plot_id"] for p in items}
    assert {"PLT-DEMOIN", "PLT-DEMOUS", "PLT-DEMOEU"} <= ids
    plot = client.get("/api/v1/plots/PLT-DEMOIN").json()
    assert abs(plot["area_hectares"] - 2.13) < 0.02
    assert plot["privacy"] == "private" and "geometry" in plot
    _validator("plot.schema.json").validate({k: v for k, v in plot.items() if k != "bbox"})
    public = client.get("/api/v1/plots/PLT-DEMOIN/public").json()
    assert "geometry" not in public and "centroid" not in public
    assert public["public_centroid"]["lat"] == round(public["public_centroid"]["lat"], 2)


def test_demo_plot_has_analysis_estimate_policy_market(client):
    analysis = client.get("/api/v1/plots/PLT-DEMOIN/analysis").json()
    assert (
        analysis["landcover"]["classes"]
        and abs(sum(c["share"] for c in analysis["landcover"]["classes"]) - 1) < 0.02
    )
    assert analysis["vegetation"]["indices"]["ndvi"]["class"] in {"sparse", "moderate", "healthy"}
    assert analysis["climate"]["zone"] == "tropical_dry"
    assert "synthetic" in analysis["data_quality"]["warnings"][0]
    estimate = client.get("/api/v1/plots/PLT-DEMOIN/carbon-estimate").json()
    _validator("carbon-estimate.schema.json").validate(estimate)
    assert estimate["certified"] is False
    assert (
        estimate["estimate"]["low"]
        <= estimate["estimate"]["central"]
        <= estimate["estimate"]["high"]
    )
    assert estimate["confidence"] == "medium"
    assert any(p["verification_status"] == "verified" for p in estimate["parameters_used"])
    assert estimate["provenance"]["mode"] == "demo" and estimate["provenance"]["sources"]
    policy = client.get("/api/v1/plots/PLT-DEMOIN/policy-eligibility").json()
    statuses = {p["id"]: p["status"] for p in policy["programmes"]}
    assert statuses["in-gcp"] == "requires_assessment"
    assert statuses["in-ccts"] == "requires_methodology_assessment"
    assert "separate" in policy["disclaimer"].lower()
    market = client.get("/api/v1/plots/PLT-DEMOIN/market-scenario").json()
    assert market["currency"] == "INR" and [s["id"] for s in market["scenarios"]] == [
        "low",
        "reference",
        "high",
    ]
    ref = market["scenarios"][1]
    assert ref["value_per_year"]["central"] == round(
        estimate["estimate"]["central"] * ref["price_per_tco2e"], 0
    )
    assert "not guaranteed" in market["disclaimer"]


def test_cube_shape_and_json_only(client):
    cube = client.get(
        "/api/v1/plots/PLT-DEMOIN/cube", params={"index": "ndvi", "months": 24}
    ).json()
    rows, cols = cube["grid"]["rows"], cube["grid"]["cols"]
    assert len(cube["times"]) == 24 and len(cube["values"]) == 24
    assert len(cube["values"][0]) == rows and len(cube["values"][0][0]) == cols
    assert len(cube["mask"]) == rows
    assert cube["provenance"]["source"] == "synthetic-demo"
    inside = [
        v
        for row, m in zip(cube["values"][-1], cube["mask"], strict=True)
        for v, inside_flag in zip(row, m, strict=True)
        if inside_flag
    ]
    assert inside and all(v is None or -1 <= v <= 1 for v in inside)
    assert client.get("/api/v1/plots/PLT-DEMOIN/cube", params={"index": "evi"}).status_code == 422


# --------------------------------------------------------------------------- full flow
def test_full_flow_create_analyze_trees_estimate_report(client, square):
    created = client.post("/api/v1/plots", json={"name": "Flow plot", "geometry": square})
    assert created.status_code == 201, created.text
    plot = created.json()
    plot_id = plot["plot_id"]
    assert plot["country"] == "IN" and plot["area_hectares"] > 100

    analysis = client.post(f"/api/v1/plots/{plot_id}/analyze", json={"years": [2024, 2025, 2026]})
    assert analysis.status_code == 200 and len(analysis.json()["vegetation"]["time_series"]) == 3

    trees = client.post(
        f"/api/v1/plots/{plot_id}/trees",
        json={"species_id": "teak", "tree_count": 5000, "plantation_year": 2022},
    )
    assert trees.status_code == 201
    inventory = trees.json()
    _validator("tree-inventory.schema.json").validate(inventory)
    assert inventory["data_quality"]["confidence"] == "medium"
    assert {f["name"]: f["status"] for f in inventory["data_quality"]["fields"]}["dbh"] == "missing"

    est = client.post(f"/api/v1/plots/{plot_id}/carbon-estimate", json={"horizon_years": 20})
    assert est.status_code == 201, est.text
    estimate = est.json()
    assert estimate["model"]["tier"] == "1" and estimate["annual_series"][-1]["year"] == 2042
    assert estimate["readiness"]["score"] > 0 and estimate["readiness"]["missing_evidence"]

    measured = client.post(
        f"/api/v1/plots/{plot_id}/trees",
        json={
            "species_id": "teak",
            "tree_count": 5000,
            "plantation_year": 2022,
            "average_dbh_cm": 12.5,
            "average_height_m": 9.0,
        },
    ).json()
    assert measured["data_quality"]["confidence"] == "high"
    tier2 = client.post(
        f"/api/v1/plots/{plot_id}/carbon-estimate", json={"inventory_id": measured["inventory_id"]}
    ).json()
    assert tier2["model"]["tier"] == "2" and tier2["confidence"] == "high"

    for fmt, ctype in (
        ("html", "text/html"),
        ("json", "application/json"),
        ("markdown", "text/markdown"),
    ):
        report = client.post(f"/api/v1/plots/{plot_id}/report", json={"format": fmt})
        assert report.status_code == 201, report.text
        fetched = client.get(report.json()["url"])
        assert fetched.status_code == 200 and fetched.headers["content-type"].startswith(ctype)
        if fmt == "html":
            assert "not an issued carbon credit" in fetched.text
            assert fetched.headers["x-frame-options"] == "SAMEORIGIN"
    pdf = client.post(f"/api/v1/plots/{plot_id}/report", json={"format": "pdf"})
    assert pdf.status_code in (201, 501)

    assert client.delete(f"/api/v1/plots/{plot_id}").status_code == 204
    assert client.get(f"/api/v1/plots/{plot_id}").status_code == 404


def test_validation_errors_are_problem_json(client):
    tiny = {"type": "Polygon", "coordinates": [[[0, 0], [0, 0.0001], [0.0001, 0.0001], [0, 0]]]}
    resp = client.post("/api/v1/plots", json={"name": "tiny", "geometry": tiny})
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["type"].endswith("invalid-geometry")
    missing = client.post("/api/v1/plots", json={"name": "x"})
    assert missing.status_code == 422 and missing.json()["errors"]
    assert client.get("/api/v1/plots/NOPE").json()["status"] == 404
    bad_country = {
        "type": "Polygon",
        "coordinates": [
            [[151.2, -33.9], [151.21, -33.9], [151.21, -33.89], [151.2, -33.89], [151.2, -33.9]]
        ],
    }
    resp = client.post("/api/v1/plots", json={"name": "au", "geometry": bad_country})
    assert resp.status_code == 422
    assert resp.json()["type"].split("/")[-1] in {"unsupported-country", "country-unresolved"}


# --------------------------------------------------------------------------- simulate / explain
@pytest.mark.parametrize(
    "country,species,zone",
    [
        ("IN", "mango", "tropical_dry"),
        ("US", "pecan", "warm_temperate_moist"),
        ("DE", "oak", "cool_temperate_moist"),
    ],
)
def test_simulate_per_country(client, country, species, zone):
    body = {
        "country": country,
        "species_id": species,
        "tree_count": 420,
        "planting_year": 2023,
        "horizon_years": 30,
    }
    sim = client.post("/api/v1/simulate", json=body)
    assert sim.status_code == 200, sim.text
    data = sim.json()
    assert data["climate_zone"] == zone and data["certified"] is False
    assert data["annual"]["low"] <= data["annual"]["central"] <= data["annual"]["high"]
    assert (
        len(data["series"]) == 31
        and data["series"][-1]["cum_central"] >= data["series"][1]["cum_central"]
    )
    assert [v["id"] for v in data["value_scenarios"]] == ["low", "reference", "high"]
    assert {c["country"] for c in data["comparison"]} == {"IN", "US", "EU"}
    assert all(p["url"] for p in data["programmes"])
    assert data["share_params"] == {
        "country": country,
        "species": species,
        "trees": 420,
        "year": 2023,
        "horizon": 30,
    }


def test_simulate_scales_with_tree_count_and_zero_trees(client):
    base = {"country": "IN", "species_id": "mango", "planting_year": 2023, "horizon_years": 20}
    small = client.post("/api/v1/simulate", json={**base, "tree_count": 100}).json()["annual"][
        "central"
    ]
    large = client.post("/api/v1/simulate", json={**base, "tree_count": 300}).json()["annual"][
        "central"
    ]
    assert large > small
    zero = client.post("/api/v1/simulate", json={**base, "tree_count": 0}).json()
    assert zero["annual"]["central"] == 0 and zero["series"][-1]["cum_central"] == 0


def test_simulate_drivers_explain_the_estimate_with_engine_reruns(client):
    body = {
        "country": "IN",
        "species_id": "mango",
        "planting_year": 2023,
        "horizon_years": 30,
        "tree_count": 420,
        "area_hectares": 2.13,
    }
    out = client.post("/api/v1/simulate/drivers", json=body).json()
    plain = client.post("/api/v1/simulate", json=body).json()
    assert out["baseline"]["central"] == plain["annual"]["central"]
    by_input = {d["input"]: d for d in out["drivers"]}
    assert set(by_input) == {"tree_count", "survival_rate", "area_hectares"}
    trees = by_input["tree_count"]
    assert (trees["value_low"], trees["value_high"]) == (378, 462)
    more = client.post("/api/v1/simulate", json={**body, "tree_count": 462}).json()
    assert trees["central_high"] == round(more["annual"]["central"], 3)  # a plain engine rerun
    assert trees["change_pct_high"] > 0 > trees["change_pct_low"]
    assert by_input["survival_rate"]["value"] == 0.85  # the engine's own default, reported back
    # every factor carries its source and status; pending ones are flagged as weakest evidence
    assert all(f["source"] and f["verification_status"] for f in out["factors"])
    assert "above_ground_biomass_growth" in out["weakest_evidence"]
    assert len(out["weakest_evidence"]) == len(set(out["weakest_evidence"]))
    survival = next(f for f in out["factors"] if f["name"] == "survival_rate")
    assert survival["verification_status"] == "assumption"  # not sent → the config default
    assert out["certified"] is False and "No AI model" in out["method"]
    zero = client.post("/api/v1/simulate/drivers", json={**body, "tree_count": 0}).json()
    assert zero["drivers"] == []


def test_simulate_cost_scenario_uses_only_the_users_costs(client):
    base = {
        "country": "IN",
        "species_id": "mango",
        "planting_year": 2023,
        "horizon_years": 20,
        "tree_count": 400,
        "area_hectares": 2.0,
    }
    plain = client.post("/api/v1/simulate", json=base).json()
    assert plain["cost_scenario"] is None  # no built-in costs
    costs = {"sapling_per_tree": 60, "maintenance_per_ha_per_year": 5000}
    sim = client.post("/api/v1/simulate", json={**base, "costs": costs}).json()
    cost = sim["cost_scenario"]
    assert cost["total_cost"] == 400 * 60 + 2.0 * 5000 * 20
    assert cost["currency"] == sim["currency"]
    assert cost["removal_over_horizon_tco2e"]["central"] == sim["series"][-1]["cum_central"]
    assert cost["break_even_price_per_tco2e"]["central"] == round(
        cost["total_cost"] / sim["series"][-1]["cum_central"], 2
    )
    assert {s["id"] for s in cost["price_scenarios"]} == {s["id"] for s in sim["value_scenarios"]}
    assert cost["certified"] is False and set(cost["not_entered"]) == {
        "planting_per_tree",
        "monitoring_per_year",
    }
    bad = client.post("/api/v1/simulate", json={**base, "costs": {"sapling_per_tree": -1}})
    assert bad.status_code == 422


def test_explain_accepts_indicators_and_rejects_coordinates(client):
    ok = client.post(
        "/api/v1/explain",
        json={
            "language": "en",
            "indicators": {
                "area_hectares": 2.13,
                "tree_count": 420,
                "species": "Mango",
                "ndvi": 0.76,
                "estimate_central": 11.0,
                "estimate_low": 7.7,
                "estimate_high": 14.3,
                "confidence": "medium",
                "missing_evidence": ["dbh"],
            },
        },
    )
    assert ok.status_code == 200 and "scenario estimate" in ok.json()["text"]
    assert ok.json()["provider"] == "template"
    for bad in ({"lat": 1, "lon": 2}, {"nested": {"coordinates": [1, 2]}}, {"geometry": {}}):
        resp = client.post("/api/v1/explain", json={"indicators": bad})
        assert resp.status_code == 422


def test_security_headers_and_request_id(client):
    resp = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["x-request-id"] == "abc123"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in resp.headers["content-security-policy"]


def test_api_key_enforced_when_configured(square):
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    settings = Settings(
        ATLAS_MODE="demo",
        ATLAS_RATE_LIMIT_ENABLED=False,
        ATLAS_API_KEYS="secret-1",
        ATLAS_SEED_DEMO=False,
    )  # type: ignore[call-arg]
    with TestClient(create_app(settings)) as c:
        assert c.post("/api/v1/plots", json={"geometry": square}).status_code == 401
        assert (
            c.post(
                "/api/v1/plots", json={"geometry": square}, headers={"X-API-Key": "nope"}
            ).status_code
            == 403
        )
        assert (
            c.post(
                "/api/v1/plots", json={"geometry": square}, headers={"X-API-Key": "secret-1"}
            ).status_code
            == 201
        )
        assert c.get("/api/v1/regions").status_code == 200  # reads stay open


def test_body_size_limit():
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    settings = Settings(
        ATLAS_MODE="demo",
        ATLAS_RATE_LIMIT_ENABLED=False,
        ATLAS_MAX_BODY_BYTES=200,
        ATLAS_SEED_DEMO=False,
    )  # type: ignore[call-arg]
    with TestClient(create_app(settings)) as c:
        big = {
            "name": "x" * 500,
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        }
        assert c.post("/api/v1/plots", json=big).status_code == 413
