"""Tree-age endpoints: GET /tree-age/rules and POST /tree-age/assess (demo mode, no network)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import ProblemError
from app.main import create_app
from app.services.registry import service
from app.services.tree_age import TreeAgeService
from carbon_engine import ClimateInput
from carbon_engine.age import assess_by_age
from policy_engine.tree_age import load_rules, pending_rules

API = "/api/v1"
INDIA_MANGO = {
    "country": "IN",
    "subdivision": "IN-KA",
    "setting": "farm",
    "species_id": "mango",
    "age_years": 60,
    "tree_count": 25,
}


@contextmanager
def make_client(**settings) -> Iterator[TestClient]:
    base = {"ATLAS_MODE": "demo", "ATLAS_RATE_LIMIT_ENABLED": False, "ATLAS_API_KEYS": ""}
    app = create_app(Settings(**{**base, **settings}))  # type: ignore[arg-type]
    with TestClient(app) as test_client:
        yield test_client


def assess(client, **overrides):
    response = client.post(f"{API}/tree-age/assess", json={**INDIA_MANGO, **overrides})
    assert response.status_code == 200, response.text
    return response.json()


def by_id(rules):
    return {rule["id"]: rule for rule in rules}


# ------------------------------------------------------------------------------- rules
def test_rules_are_served_exactly_as_in_the_file(client):
    response = client.get(f"{API}/tree-age/rules")
    assert response.status_code == 200
    body = response.json()
    expected = load_rules()
    assert body["version"] == expected["version"] and body["updated"] == expected["updated"]
    assert body["disclaimer"] == expected["disclaimer"]
    assert "not legal advice" in body["disclaimer"]
    assert body["age_classes"] == expected["age_classes"]
    assert [c["id"] for c in body["age_classes"]] == ["young", "mature", "old", "veteran"]
    assert body["rules"] == expected["rules"]  # unfiltered: file content, file order
    assert body["withheld_rule_ids"] == []  # development mode serves (and flags) pending rules


def test_rules_can_be_filtered_by_country_and_subdivision(client):
    india = client.get(f"{API}/tree-age/rules", params={"country": "IN"}).json()
    assert {r["scope"] for r in india["rules"]} == {"GLOBAL", "IN"}
    assert "in-hr-pran-vayu-devta-pension" in by_id(india["rules"])
    assert india["subdivision_label"] == "State or union territory"
    assert {"IN-HR", "IN-KA", "IN-MH", "IN-DL"} <= {s["code"] for s in india["subdivisions"]}
    assert len(india["subdivisions"]) == 36

    haryana = client.get(
        f"{API}/tree-age/rules", params={"country": "in", "subdivision": "in-hr"}
    ).json()
    ids = by_id(haryana["rules"])
    assert "in-hr-pran-vayu-devta-pension" in ids and "in-ccts-offset-bm-fr05-002" in ids
    assert "in-ka-preservation-of-trees-act" not in ids  # a rule for another state
    assert all(r["subdivision"] in (None, "IN-HR") for r in haryana["rules"])

    germany = by_id(client.get(f"{API}/tree-age/rules", params={"country": "DE"}).json()["rules"])
    assert "eu-de-berlin-baumschutzverordnung" in germany
    france = by_id(client.get(f"{API}/tree-age/rules", params={"country": "FR"}).json()["rules"])
    assert "eu-de-berlin-baumschutzverordnung" not in france
    assert "eu-crcf-regulation-2024-3012" in france

    us = client.get(f"{API}/tree-age/rules", params={"country": "US"}).json()
    assert {r["scope"] for r in us["rules"]} == {"GLOBAL", "US"}
    assert {s["code"] for s in us["subdivisions"]} >= {"US-OR", "US-CA"}
    assert (
        client.get(f"{API}/tree-age/rules", params={"country": "FR"}).json()["subdivisions"] == []
    )


@pytest.mark.parametrize(
    ("params", "slug"),
    [
        ({"country": "BR"}, "unsupported-country"),
        ({"country": "IN", "subdivision": "US-OR"}, "invalid-subdivision"),
        ({"country": "IN", "subdivision": "IN-ZZ"}, "unknown-subdivision"),
    ],
)
def test_rules_errors_are_problem_json(client, params, slug):
    response = client.get(f"{API}/tree-age/rules", params=params)
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith(slug)


@pytest.mark.parametrize(
    "params", [{"country": "IND"}, {"subdivision": "Karnataka"}, {"country": "I"}]
)
def test_rules_query_validation(client, params):
    response = client.get(f"{API}/tree-age/rules", params=params)
    assert response.status_code == 422
    assert response.json()["type"].endswith("validation-error")


# ----------------------------------------------------------------------- assess: contract
def test_assess_india_mango_matches_the_contract_shape(client):
    body = assess(client)
    assert set(body) >= {
        "inputs",
        "age_class",
        "climate_zone",
        "climate_zone_source",
        "carbon",
        "credit_outlook",
        "rules",
        "certified",
        "disclaimer",
        "provenance",
    }
    assert body["inputs"] == {
        "country": "IN",
        "region": "IN",
        "subdivision": "IN-KA",
        "setting": "farm",
        "species_id": "mango",
        "age_years": 60,
        "tree_count": 25,
        "girth_cm": None,
        "height_m": None,
        "plot_id": None,
    }
    assert body["age_class"] == {"id": "old", "label": "Old (50–74 years)"}
    assert body["climate_zone"] == "tropical_dry"
    assert body["climate_zone_source"] == "region default (IN)"
    assert body["certified"] is False
    assert "not legal advice" in body["disclaimer"]
    assert body["disclaimer"].endswith(
        "Scenario estimate only. This is not an issued carbon credit."
    )

    carbon = body["carbon"]
    assert carbon["method"] == "tier1-age" and carbon["curve_method"] == "tier1-age"
    stored, annual = carbon["stored_now"], carbon["annual_now"]
    assert stored["unit"] == "tCO2e" and annual["unit"] == "tCO2e/yr"
    for rng in (stored, annual):
        assert 0 < rng["low"] < rng["central"] < rng["high"]
    # hand-computed in packages/carbon-engine/tests/test_age.py (43.28 tCO2e; 0.662 tCO2e/yr)
    assert stored["central"] == pytest.approx(43.28, abs=0.01)
    assert annual["central"] == pytest.approx(0.662, abs=0.001)
    assert carbon["per_tree"]["stored_now_kg_co2e"] * 25 == pytest.approx(
        stored["central"] * 1000, abs=30
    )
    assert carbon["confidence"] == "low"
    assert carbon["model"]["id"] == "tree-biomass" and carbon["methodology"]["id"]
    assert carbon["notes"] and carbon["parameters_used"]
    for parameter in carbon["parameters_used"]:
        assert set(parameter) == {"name", "value", "unit", "source", "verification_status"}
        assert parameter["source"]

    curve = carbon["curve"]
    assert [p["age"] for p in curve] == list(range(0, 81))  # max(age + 20, 40)
    assert set(curve[0]) == {"age", "stored", "stored_low", "stored_high", "annual"}
    assert curve[0]["stored"] == 0.0 and curve[0]["annual"] == 0.0
    stored_curve = [p["stored"] for p in curve]
    assert stored_curve == sorted(stored_curve)
    assert curve[60]["stored"] == stored["central"] and curve[60]["annual"] == annual["central"]


def test_assess_provenance_names_methods_data_and_rules_version(client):
    body = assess(client)
    provenance = body["provenance"]
    assert provenance["generated_at"] and provenance["mode"] == "demo"
    assert provenance["model"]["id"] == "tree-biomass"
    assert provenance["parameter_set"]["verification_status"] in {
        "verified",
        "assumption",
        "pending",
    }
    source_ids = {s["id"] for s in provenance["sources"]}
    assert {"ipcc-2006-vol4-ch4", "species-table", "tree-age-rules"} <= source_ids
    assert "chave-2014" not in source_ids  # only on the girth path
    rules_source = next(s for s in provenance["sources"] if s["id"] == "tree-age-rules")
    expected = load_rules()
    assert rules_source["version"] == expected["version"]
    assert rules_source["updated"] == expected["updated"]
    for source in provenance["sources"]:
        assert source["license"] and source["attribution"]
    assert provenance["climate_zone"]["zone"] == "tropical_dry"
    assert provenance["species"]["id"] == "mango"
    assert provenance["notes"] == body["carbon"]["notes"]


def test_assess_is_deterministic(client):
    first, second = assess(client), assess(client)
    for body in (first, second):
        body["provenance"].pop("generated_at")
    assert first == second


# --------------------------------------------------------------------------- girth path
def test_assess_with_girth_uses_the_measured_tree_path(client):
    tier1 = assess(client)["carbon"]
    body = assess(client, girth_cm=188, height_m=None)
    carbon = body["carbon"]
    assert carbon["method"] == "tier2-girth"
    assert carbon["curve_method"] == "tier1-age"
    assert carbon["curve"] == tier1["curve"]
    assert carbon["stored_now"]["central"] == pytest.approx(57.66, abs=0.05)  # see the engine test
    assert carbon["stored_now"]["central"] != tier1["stored_now"]["central"]
    assert carbon["annual_now"]["central"] == pytest.approx(57.66 / 60, abs=0.005)  # stock ÷ age
    assert carbon["confidence"] == "medium"
    names = {p["name"] for p in carbon["parameters_used"]}
    assert {"average_dbh_cm", "allometry_equation"} <= names
    assert any("÷ π" in n for n in carbon["notes"])
    assert body["inputs"]["girth_cm"] == 188
    assert "chave-2014" in {s["id"] for s in body["provenance"]["sources"]}


def test_assess_with_girth_and_height_is_graded_high(client):
    assert assess(client, girth_cm=150, height_m=12)["carbon"]["confidence"] == "high"


# --------------------------------------------------------------------------- new trees
def test_age_zero_plans_new_trees(client):
    body = assess(client, age_years=0, subdivision=None, setting="any")
    carbon = body["carbon"]
    assert carbon["stored_now"]["central"] == 0.0 and carbon["annual_now"]["central"] == 0.0
    assert carbon["per_tree"] == {"stored_now_kg_co2e": 0.0, "annual_now_kg_co2e": 0.0}
    assert carbon["curve"][-1]["stored"] > 0
    assert body["age_class"]["id"] == "young"
    assert body["credit_outlook"]["existing_trees"] == "conditional"
    assert "Newly planted trees" in body["credit_outlook"]["summary"]
    rules = by_id(body["rules"])
    assert rules["global-verra-vm0047-arr"]["outcome_for_you"] == "conditional"
    assert rules["in-ka-preservation-of-trees-act"]["outcome_for_you"] == "not-applicable"


# ---------------------------------------------------------------------------- outlook & rules
def test_existing_trees_in_india_are_not_eligible_for_credits(client):
    body = assess(client)
    outlook = body["credit_outlook"]
    assert outlook["existing_trees"] == "not-eligible"
    assert "do not earn removal credits" in outlook["summary"]
    assert "in-ccts-offset-bm-fr05-002" in outlook["based_on_rule_ids"]


def test_rules_carry_applies_why_and_outcome_for_you(client):
    rules = assess(client)["rules"]
    originals = by_id(load_rules()["rules"])
    for rule in rules:
        original = originals[rule["id"]]
        assert {k: rule[k] for k in original} == original  # the original fields, untouched
        assert isinstance(rule["applies"], bool) and rule["why"]
        assert rule["outcome_for_you"] == original["outcome_for_existing_trees"]
    flags = [r["applies"] for r in rules]
    assert flags == sorted(flags, reverse=True)  # applicable rules first
    index = by_id(rules)
    assert index["in-ccts-offset-bm-fr05-002"]["why"] == "Applies in India at any age"
    assert index["in-ka-preservation-of-trees-act"]["applies"] is True
    assert index["in-hr-pran-vayu-devta-pension"]["applies"] is False
    assert index["in-hr-pran-vayu-devta-pension"]["why"] == "Only in Haryana (IN-HR)"
    assert index["in-dl-preservation-of-trees-act"]["why"] == "Only in Delhi (IN-DL)"
    assert index["in-gcp-tree-plantation"]["why"] == "Only for trees in forests"
    assert not any(r["id"].startswith(("us-", "eu-")) for r in rules)


def test_haryana_pension_needs_the_state_the_age_and_flags_pending(client):
    young = by_id(assess(client, subdivision="IN-HR", age_years=60)["rules"])
    pension = young["in-hr-pran-vayu-devta-pension"]
    assert pension["applies"] is False and pension["why"] == "Needs trees aged 75 years or more"
    old = by_id(assess(client, subdivision="IN-HR", age_years=80)["rules"])
    pension = old["in-hr-pran-vayu-devta-pension"]
    assert pension["applies"] is True and pension["outcome_for_you"] == "payment"
    assert pension["verification_status"] == "pending"  # flagged, never shown as confirmed
    assert "not yet confirmed from a primary source" in pension["why"]
    assert pension["amount"]["value"] == 3000 and pension["amount"]["as_of"]


def test_setting_filters_rules(client):
    farm = by_id(assess(client, subdivision="IN-DL", setting="farm")["rules"])
    urban = by_id(assess(client, subdivision="IN-DL", setting="urban")["rules"])
    assert farm["in-dl-preservation-of-trees-act"]["why"] == "Only for urban trees"
    assert urban["in-dl-preservation-of-trees-act"]["applies"] is True


def test_us_forest_trees_have_a_conditional_route(client):
    body = assess(
        client,
        country="US",
        subdivision="US-OR",
        setting="forest",
        species_id="black_walnut",
        age_years=40,
    )
    assert body["inputs"]["region"] == "US"
    assert body["credit_outlook"]["existing_trees"] == "conditional"
    assert "specific conditions" in body["credit_outlook"]["summary"]
    rules = by_id(body["rules"])
    assert rules["us-acr-ifm-non-federal-v2-1"]["applies"] is True
    assert rules["us-or-portland-heritage-trees"]["applies"] is False  # a city example
    assert "Portland" in rules["us-or-portland-heritage-trees"]["why"]
    assert not any(r["id"].startswith("in-") for r in body["rules"])


def test_eu_member_states_use_eu_rules_and_berlin_applies_in_berlin(client):
    body = assess(
        client,
        country="DE",
        subdivision="DE-BE",
        setting="urban",
        species_id="oak",
        age_years=90,
    )
    assert body["inputs"]["region"] == "EU"
    assert body["climate_zone_source"] == "region default (EU)"
    rules = by_id(body["rules"])
    assert rules["eu-de-berlin-baumschutzverordnung"]["applies"] is True
    assert "eu-crcf-regulation-2024-3012" in rules
    assert "estimate is never a credit" in body["credit_outlook"]["summary"]
    france = by_id(assess(client, country="FR", subdivision=None, species_id="oak")["rules"])
    assert "eu-de-berlin-baumschutzverordnung" not in france


def test_species_not_listed_for_the_region_gets_a_note(client):
    body = assess(client, country="US", subdivision=None, species_id="mango", age_years=10)
    assert "not listed for US" in body["carbon"]["notes"][0]


# --------------------------------------------------------------------------- inputs
def test_country_and_subdivision_are_normalised(client):
    body = assess(client, country="in", subdivision="in-ka")
    assert body["inputs"]["country"] == "IN" and body["inputs"]["subdivision"] == "IN-KA"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"age_years": -1}, "age_years"),
        ({"age_years": 301}, "age_years"),
        ({"age_years": 60.5}, "age_years"),
        ({"tree_count": 0}, "tree_count"),
        ({"tree_count": 1_000_001}, "tree_count"),
        ({"girth_cm": 9.9}, "girth_cm"),
        ({"girth_cm": 2000.1}, "girth_cm"),
        ({"height_m": 0.4}, "height_m"),
        ({"height_m": 120.1}, "height_m"),
        ({"setting": "garden"}, "setting"),
        ({"country": "IND"}, "country"),
        ({"subdivision": "Karnataka"}, "subdivision"),
        ({"subdivision": "US-OR"}, "subdivision"),
        ({"plot_id": "../etc/passwd"}, "plot_id"),
        ({"age_years": 0, "girth_cm": 50}, "girth_cm"),
        ({"surprise": 1}, "surprise"),
    ],
)
def test_assess_validates_the_request(client, overrides, field):
    response = client.post(f"{API}/tree-age/assess", json={**INDIA_MANGO, **overrides})
    assert response.status_code == 422
    body = response.json()
    assert body["type"].endswith("validation-error")
    assert field in {e["field"] for e in body["errors"]}


def test_assess_requires_the_core_fields(client):
    response = client.post(f"{API}/tree-age/assess", json={"country": "IN"})
    assert response.status_code == 422
    fields = {e["field"] for e in response.json()["errors"]}
    assert {"species_id", "age_years", "tree_count"} <= fields


@pytest.mark.parametrize(
    ("overrides", "slug", "status"),
    [
        ({"country": "BR", "subdivision": None}, "unsupported-country", 422),
        ({"species_id": "no-such-tree"}, "unknown-species", 422),
        ({"subdivision": "IN-ZZ"}, "unknown-subdivision", 422),
        ({"plot_id": "PLT-NOPE"}, "plot-not-found", 404),
    ],
)
def test_assess_domain_errors_are_problem_json(client, overrides, slug, status):
    response = client.post(f"{API}/tree-age/assess", json={**INDIA_MANGO, **overrides})
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith(slug)


def test_extreme_sizes_still_work(client):
    one = assess(client, tree_count=1, age_years=1)
    assert one["carbon"]["per_tree"]["stored_now_kg_co2e"] > 0
    huge = assess(client, tree_count=1_000_000, age_years=300)
    points = huge["carbon"]["curve"]
    assert len(points) <= 150 and points[0]["age"] == 0  # the contract's point limit
    assert 300 in {p["age"] for p in points} and points[-1]["age"] == 320
    assert huge["age_class"]["id"] == "veteran"
    assert huge["carbon"]["stored_now"]["central"] > 1_000_000
    # one tree among a million is worth the same as a single tree
    assert huge["carbon"]["per_tree"]["stored_now_kg_co2e"] == pytest.approx(
        assess(client, tree_count=1, age_years=300)["carbon"]["per_tree"]["stored_now_kg_co2e"],
        rel=1e-3,
    )


# ------------------------------------------------------------------------ plot climate
def test_a_plot_id_supplies_the_climate_zone_of_its_analysis(client):
    analysis = client.get(f"{API}/plots/PLT-DEMOUS/analysis").json()["climate"]
    body = assess(
        client,
        country="US",
        subdivision=None,
        species_id="pecan",
        age_years=20,
        plot_id="PLT-DEMOUS",
    )
    assert body["climate_zone"] == analysis["zone"]
    assert body["climate_zone_source"] == f"plot analysis ({analysis['zone_source']})"
    assert body["inputs"]["plot_id"] == "PLT-DEMOUS"


def test_a_plot_never_leaks_its_geometry_into_the_assessment(client):
    plot = client.get(f"{API}/plots/PLT-DEMOIN").json()
    text = json.dumps(assess(client, plot_id="PLT-DEMOIN"))
    for forbidden in ('"geometry"', '"coordinates"', '"centroid"', '"bbox"', '"lat"', '"lon"'):
        assert forbidden not in text
    centroid = plot.get("centroid") or {}
    for value in (centroid.get("lat"), centroid.get("lon")):
        if value is not None:
            assert str(value) not in text


# -------------------------------------------------------------------- stores nothing, no key
def test_assess_stores_nothing_and_needs_no_api_key():
    with make_client(ATLAS_API_KEYS="a-secret-key") as protected:
        context = protected.app.state.context
        before = (len(context.repo.list_plots()), len(context.repo.list_inventories("PLT-DEMOIN")))
        # a mutating call without a key is refused elsewhere …
        denied = protected.post(f"{API}/plots/PLT-DEMOIN/trees", json={})
        assert denied.status_code in (401, 403)
        # … but the calculation is public and writes nothing
        response = protected.post(f"{API}/tree-age/assess", json=INDIA_MANGO)
        assert response.status_code == 200
        assert protected.get(f"{API}/tree-age/rules").status_code == 200
        after = (len(context.repo.list_plots()), len(context.repo.list_inventories("PLT-DEMOIN")))
        assert before == after


# ------------------------------------------------------------------------ production gate
def test_production_withholds_pending_rules_and_refuses_pending_parameters():
    with make_client(ATLAS_ENV="production") as production:
        context = production.app.state.context
        pending_ids = {r["id"] for r in pending_rules(load_rules())}

        rules = production.get(f"{API}/tree-age/rules").json()
        assert not any(r["verification_status"] == "pending" for r in rules["rules"])
        assert set(rules["withheld_rule_ids"]) == pending_ids
        india = production.get(f"{API}/tree-age/rules", params={"country": "IN"}).json()
        assert set(india["withheld_rule_ids"]) <= pending_ids
        assert all(i.startswith("in-") for i in india["withheld_rule_ids"])

        uses_pending = (
            assess_by_age(
                context.store, "mango", 60, 25, ClimateInput("tropical_dry"), as_of_year=2026
            ).provenance["parameter_set"]["verification_status"]
            == "pending"
        )
        response = production.post(f"{API}/tree-age/assess", json=INDIA_MANGO)
        if uses_pending:  # the shipped configuration: Tier 1 growth and root-to-shoot are pending
            assert response.status_code == 409
            assert response.json()["type"].endswith("pending-parameters")
        else:
            assert response.status_code == 200
            body = response.json()
            assert not any(r["verification_status"] == "pending" for r in body["rules"])
            assert set(body["withheld_rule_ids"]) <= pending_ids


def test_disallowing_pending_parameters_outside_production_does_the_same():
    with make_client(ATLAS_ALLOW_PENDING_PARAMETERS=False) as strict:
        rules = strict.get(f"{API}/tree-age/rules", params={"country": "IN"}).json()
        assert not any(r["verification_status"] == "pending" for r in rules["rules"])
        assert rules["withheld_rule_ids"]
        assert strict.post(f"{API}/tree-age/assess", json=INDIA_MANGO).status_code in (200, 409)


# --------------------------------------------------------------------- in-process callers
def test_other_modules_can_call_the_service_directly(client):
    context = client.app.state.context
    tree_age = service(context, "tree_age", lambda: TreeAgeService(context))
    assert isinstance(tree_age, TreeAgeService)
    assert service(context, "tree_age", lambda: TreeAgeService(context)) is tree_age  # cached

    body = tree_age.assess(
        {
            "country": "in",
            "species_id": "neem",
            "age_years": 15,
            "tree_count": 40,
            "ignored_extra_key": "kept out",
        }
    )
    assert body["inputs"]["setting"] == "any" and body["inputs"]["subdivision"] is None
    assert body["carbon"]["stored_now"]["central"] > 0 and body["certified"] is False

    with pytest.raises(ProblemError) as excinfo:
        tree_age.assess({"country": "IN", "species_id": "neem", "age_years": 500, "tree_count": 3})
    assert excinfo.value.status == 422
    assert "age_years" in {e["field"] for e in excinfo.value.extra["errors"]}


# --------------------------------------------------------------------------------- docs
def test_openapi_lists_the_tree_age_endpoints(client):
    spec = client.get(f"{API}/openapi.json").json()
    assert "get" in spec["paths"][f"{API}/tree-age/rules"]
    assert "post" in spec["paths"][f"{API}/tree-age/assess"]
    assert spec["paths"][f"{API}/tree-age/assess"]["post"]["tags"] == ["tree-age"]
