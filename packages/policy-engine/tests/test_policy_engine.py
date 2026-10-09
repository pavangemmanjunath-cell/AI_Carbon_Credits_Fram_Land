from __future__ import annotations

import pytest

from policy_engine import ACTIVITIES, STATUSES, PolicyEngine
from policy_engine.engine import evaluate_rules, rule_matches


@pytest.fixture(scope="module")
def engine() -> PolicyEngine:
    return PolicyEngine()


def test_member_states_resolve_to_eu(engine):
    for code in ("DE", "FR", "ES", "IT", "NL", "PL", "PT", "AT", "ie"):
        assert engine.resolve_region(code) == "EU"
    assert engine.resolve_region("IN") == "IN"
    assert engine.resolve_region("US") == "US"
    assert engine.resolve_region("EU") == "EU"
    with pytest.raises(KeyError):
        engine.resolve_region("BR")


def test_india_tree_plantation_matches_contract_example(engine):
    screening = engine.screen("IN", "tree_plantation")
    data = screening.to_dict()
    assert data["country"] == "IN" and data["activity"] == "tree_plantation"
    assert "not an eligibility determination" in data["disclaimer"]
    by_id = {p["id"]: p for p in data["programmes"]}
    assert by_id["in-gcp"]["status"] == "requires_assessment"
    assert by_id["in-gcp"]["distinct_from"] == ["in-ccts"]
    assert any("separate mechanism" in n for n in by_id["in-gcp"]["notes"])
    assert by_id["in-gcp"]["requirements"] and by_id["in-gcp"]["references"][0]["url"]
    assert by_id["in-ccts"]["status"] == "requires_methodology_assessment"
    assert by_id["in-state-agroforestry"]["status"] == "potentially_applicable"
    assert screening.summary().startswith("Green Credit Programme · CCTS")
    assert "(separate mechanisms)" in screening.summary()
    assert screening.programmes[0].url == "https://moef.gov.in/"


@pytest.mark.parametrize(
    "activity, gcp, ccts, state",
    [
        (
            "tree_plantation",
            "requires_assessment",
            "requires_methodology_assessment",
            "potentially_applicable",
        ),
        (
            "agroforestry",
            "requires_assessment",
            "requires_methodology_assessment",
            "potentially_applicable",
        ),
        ("soil_carbon", "not_applicable", "requires_methodology_assessment", "not_applicable"),
        ("cropland_practice", "not_applicable", "unknown", "not_applicable"),
        ("grazing", "not_applicable", "unknown", "not_applicable"),
    ],
)
def test_india_every_activity(engine, activity, gcp, ccts, state):
    by_id = {p.id: p for p in engine.screen("IN", activity).programmes}
    assert by_id["in-gcp"].status == gcp
    assert by_id["in-ccts"].status == ccts
    assert by_id["in-state-agroforestry"].status == state


@pytest.mark.parametrize(
    "activity, comet, arr, nrcs",
    [
        (
            "tree_plantation",
            "potentially_applicable",
            "requires_methodology_assessment",
            "potentially_applicable",
        ),
        (
            "agroforestry",
            "potentially_applicable",
            "requires_methodology_assessment",
            "potentially_applicable",
        ),
        (
            "cropland_practice",
            "potentially_applicable",
            "requires_methodology_assessment",
            "potentially_applicable",
        ),
        ("grazing", "potentially_applicable", "unknown", "not_applicable"),
        ("soil_carbon", "not_applicable", "unknown", "not_applicable"),
    ],
)
def test_us_every_activity(engine, activity, comet, arr, nrcs):
    by_id = {p.id: p for p in engine.screen("US", activity).programmes}
    assert by_id["us-comet-farm"].status == comet
    assert by_id["us-voluntary-arr"].status == arr
    assert by_id["us-nrcs-conservation"].status == nrcs


@pytest.mark.parametrize(
    "activity, crcf, cap, voluntary",
    [
        (
            "tree_plantation",
            "requires_certification",
            "potentially_applicable",
            "requires_methodology_assessment",
        ),
        (
            "agroforestry",
            "requires_certification",
            "potentially_applicable",
            "requires_methodology_assessment",
        ),
        (
            "soil_carbon",
            "requires_certification",
            "not_applicable",
            "requires_methodology_assessment",
        ),
        (
            "cropland_practice",
            "requires_certification",
            "potentially_applicable",
            "requires_methodology_assessment",
        ),
        ("grazing", "unknown", "not_applicable", "unknown"),
    ],
)
def test_eu_every_activity_via_member_state(engine, activity, crcf, cap, voluntary):
    screening = engine.screen("ES", activity)
    assert screening.country == "ES" and screening.region == "EU"
    by_id = {p.id: p for p in screening.programmes}
    assert by_id["eu-crcf"].status == crcf
    assert by_id["eu-cap-eco-schemes"].status == cap
    assert by_id["eu-voluntary"].status == voluntary
    assert "never automatically certifiable" in screening.disclaimer


def test_statuses_are_within_contract_enum(engine):
    for region in ("IN", "US", "EU"):
        for activity in ACTIVITIES:
            for programme in engine.screen(region, activity).programmes:
                assert programme.status in STATUSES


def test_unknown_activity_rejected(engine):
    with pytest.raises(ValueError):
        engine.screen("IN", "mining")


def test_rule_matching_semantics():
    rules = [
        {
            "when": {"activity": ["agroforestry"], "land_type": "cropland", "min_area": 1.0},
            "status": "potentially_applicable",
            "reason": "r1",
        },
        {"when": {"activity": "agroforestry"}, "status": "requires_assessment", "reason": "r2"},
        {"default": "not_applicable"},
    ]
    assert evaluate_rules(rules, "agroforestry", "cropland", 2.0) == (
        "potentially_applicable",
        "r1",
    )
    assert evaluate_rules(rules, "agroforestry", "cropland", 0.5) == ("requires_assessment", "r2")
    assert evaluate_rules(rules, "agroforestry", None, None) == ("requires_assessment", "r2")
    assert evaluate_rules(rules, "grazing", None, None) == ("not_applicable", None)
    assert evaluate_rules(rules[:2], "grazing", None, None) == ("unknown", None)
    assert rule_matches({"activity": "x", "max_area": 10}, "x", None, 5)
    assert not rule_matches({"activity": "x", "max_area": 10}, "x", None, 50)
