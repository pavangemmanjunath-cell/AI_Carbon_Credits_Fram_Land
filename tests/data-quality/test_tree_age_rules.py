"""Data-quality gates on ``config/tree-age/rules.yaml`` and ``config/tree-age/subdivisions.yaml``.

These run in every CI job. Every rule must be sourced (an https link and an access date), use the
documented vocabulary and say what is still unconfirmed. Rules whose ``verification_status`` is
``pending`` may ship in development (they are flagged), but a production deployment withholds them,
the way the carbon engine refuses pending parameters (CLAUDE.md principle 10): the ``production``
gate at the bottom runs when ``ATLAS_ENV=production`` and *reports* the withheld rules.
"""

from __future__ import annotations

import os
import re
import warnings
from datetime import date
from pathlib import Path

import pytest
import yaml

from policy_engine.tree_age import (
    CATEGORIES,
    OUTCOMES,
    REQUEST_SETTINGS,
    RULE_SETTINGS,
    RULE_STATUSES,
    SCOPES,
    TREE_STATUSES,
    VERIFICATION_STATUSES,
    evaluate,
    load_rules,
    load_subdivisions,
    pending_rules,
    rule_problems,
    select_rules,
    withheld_rule_ids,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
RULES_PATH = CONFIG / "tree-age" / "rules.yaml"
SUBDIVISIONS_PATH = CONFIG / "tree-age" / "subdivisions.yaml"
RAW = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
RAW_SUBDIVISIONS = yaml.safe_load(SUBDIVISIONS_PATH.read_text(encoding="utf-8"))
RULES = RAW["rules"]
REQUIRED_FIELDS = {
    "id",
    "scope",
    "country",
    "subdivision",
    "locality",
    "name",
    "authority",
    "category",
    "applies_to",
    "outcome_for_existing_trees",
    "summary",
    "details",
    "amount",
    "status",
    "is_example",
    "sources",
    "verification_status",
}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RULE_IDS = [rule["id"] for rule in RULES]


def as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


@pytest.fixture(scope="module")
def known_subdivisions() -> dict[str, str]:
    """``{"IN-HR": "IN", …}`` from subdivisions.yaml."""
    return {
        item["code"]: country
        for country, block in RAW_SUBDIVISIONS["countries"].items()
        for item in block["subdivisions"]
    }


@pytest.fixture(params=RULES, ids=RULE_IDS)
def rule(request):
    return request.param


# ---------------------------------------------------------------------------- whole file
def test_the_engine_accepts_the_shipped_files():
    problems = rule_problems(load_rules(CONFIG), load_subdivisions(CONFIG))
    assert problems == [], "\n".join(problems)


def test_file_header_is_complete():
    assert str(RAW["version"]).strip()
    assert as_date(RAW["updated"]) <= date.today()
    assert "not legal advice" in RAW["disclaimer"].lower()
    assert len(RULES) >= 20


def test_rule_ids_are_unique_slugs():
    assert len(RULE_IDS) == len(set(RULE_IDS))
    assert all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", rule_id) for rule_id in RULE_IDS)


def test_age_classes_are_contiguous_and_open_ended():
    classes = RAW["age_classes"]
    assert [c["id"] for c in classes] == ["young", "mature", "old", "veteran"]
    assert classes[0]["min_age"] == 0
    for before, after in zip(classes, classes[1:], strict=False):
        assert before["max_age"] is not None
        assert after["min_age"] == before["max_age"] + 1
    assert classes[-1]["max_age"] is None
    assert all(c["label"].strip() for c in classes)


def test_every_scope_and_category_the_app_shows_has_rules():
    assert {r["scope"] for r in RULES} == set(SCOPES)
    assert {r["category"] for r in RULES} == set(CATEGORIES)


def test_links_are_https_only():
    assert "http://" not in RULES_PATH.read_text(encoding="utf-8")


# ------------------------------------------------------------------------------ per rule
def test_rule_has_every_required_field(rule):
    assert REQUIRED_FIELDS <= set(rule), sorted(REQUIRED_FIELDS - set(rule))
    for field in ("name", "authority", "summary", "details"):
        assert isinstance(rule[field], str) and rule[field].strip(), field


def test_rule_uses_the_documented_vocabulary(rule):
    assert rule["scope"] in SCOPES
    assert rule["category"] in CATEGORIES
    assert rule["outcome_for_existing_trees"] in OUTCOMES
    assert rule["status"] in RULE_STATUSES
    assert rule["verification_status"] in VERIFICATION_STATUSES
    assert isinstance(rule["is_example"], bool)
    applies_to = rule["applies_to"]
    assert set(applies_to) == {"min_age_years", "max_age_years", "trees", "setting"}
    assert applies_to["trees"] in TREE_STATUSES
    assert applies_to["setting"] in RULE_SETTINGS
    low, high = applies_to["min_age_years"], applies_to["max_age_years"]
    assert all(v is None or (isinstance(v, int) and v >= 0) for v in (low, high))
    if low is not None and high is not None:
        assert low <= high


def test_rule_has_a_source_with_an_https_link_and_an_access_date(rule):
    sources = rule["sources"]
    assert isinstance(sources, list) and sources, "a rule without a source is not allowed"
    for source in sources:
        assert source["title"].strip() and source["publisher"].strip(), source
        assert source["url"].startswith("https://") and " " not in source["url"], source
        accessed = str(source["accessed"])
        assert ISO_DATE.match(accessed), source
        assert as_date(accessed) <= as_date(RAW["updated"]), "bump `updated` when adding a source"


def test_an_amount_states_its_unit_and_date(rule):
    amount = rule["amount"]
    if amount is None:
        return
    assert isinstance(amount["value"], (int, float)) and amount["value"] >= 0
    assert amount["currency"].strip() and amount["unit"].strip()
    assert re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", str(amount["as_of"])), "amount needs an as_of"


def test_a_pending_rule_says_what_is_missing(rule):
    if rule["verification_status"] == "pending":
        assert (rule.get("notes") or "").strip(), "explain in `notes` what is not yet confirmed"


def test_outcomes_match_their_category(rule):
    if rule["outcome_for_existing_trees"] == "protected":
        assert rule["category"] == "tree-protection"
    if rule["outcome_for_existing_trees"] == "payment":
        assert rule["category"] == "incentive-payment"


def test_no_rule_promises_eligibility_without_verification(rule):
    if rule["outcome_for_existing_trees"] == "eligible":
        assert rule["verification_status"] == "verified" and rule["status"] == "in-force"


def test_municipal_examples_name_their_place(rule, known_subdivisions):
    if rule["is_example"]:
        assert rule["locality"] and rule["subdivision"]
    if rule["locality"]:
        assert rule["subdivision"], "a locality needs its subdivision"


def test_geography_is_consistent_and_listed(rule, known_subdivisions):
    scope, country, subdivision = rule["scope"], rule["country"], rule["subdivision"]
    if scope == "GLOBAL":
        assert country is None and subdivision is None and rule["locality"] is None
    if scope in ("IN", "US"):
        assert country in (None, scope)
    if country is not None:
        assert re.fullmatch(r"[A-Z]{2}", country)
    if subdivision is not None:
        assert re.fullmatch(r"[A-Z]{2}-[A-Z0-9]{1,3}", subdivision)
        assert subdivision in known_subdivisions, f"{subdivision} is not in subdivisions.yaml"
        if country is not None:
            assert known_subdivisions[subdivision] == country


def test_gcp_and_ccts_stay_separate_mechanisms():
    """CLAUDE.md terminology: India's Green Credits and carbon credits are separate mechanisms."""
    for rule in RULES:
        if rule["id"].startswith("in-gcp"):
            assert rule["category"] != "carbon-credit-eligibility", rule["id"]
        if rule["id"].startswith("in-ccts"):
            assert rule["category"] == "carbon-credit-eligibility", rule["id"]


# ------------------------------------------------------------------------- subdivisions
def test_required_subdivision_codes_are_exact(known_subdivisions):
    for code, country in {
        "IN-HR": "IN",
        "IN-MH": "IN",
        "IN-KA": "IN",
        "IN-DL": "IN",
        "US-OR": "US",
        "US-CA": "US",
        "DE-BE": "DE",
    }.items():
        assert known_subdivisions[code] == country


def test_subdivision_codes_are_well_formed_and_unique():
    codes = []
    for country, block in RAW_SUBDIVISIONS["countries"].items():
        assert block["name"].strip() and block["subdivision_label"].strip()
        for item in block["subdivisions"]:
            assert item["code"].startswith(f"{country}-"), item
            assert re.fullmatch(r"[A-Z]{2}-[A-Z0-9]{1,3}", item["code"]), item
            assert item["name"].strip() and item["type"].strip()
            codes.append(item["code"])
    assert len(codes) == len(set(codes))
    assert sum(c.startswith("IN-") for c in codes) == 36  # 28 states + 8 union territories
    assert sum(c.startswith("US-") for c in codes) >= 51  # 50 states + DC


# ---------------------------------------------------------------------- engine, every place
@pytest.mark.parametrize(
    ("country", "region"), [("IN", "IN"), ("US", "US"), ("DE", "EU"), ("FR", "EU")]
)
@pytest.mark.parametrize("age", [0, 1, 20, 21, 49, 50, 74, 75, 300])
@pytest.mark.parametrize("setting", REQUEST_SETTINGS)
def test_every_rule_evaluates_to_a_sentence_and_an_outcome(country, region, age, setting):
    doc = load_rules(CONFIG)
    results = evaluate(doc, country, region, None, setting, age)
    assert results
    for result in results:
        assert isinstance(result["applies"], bool) and result["why"].strip()
        assert result["outcome_for_you"] in OUTCOMES


# ------------------------------------------------------------------------ production gate
@pytest.mark.skipif(
    os.environ.get("ATLAS_ENV", "").lower() != "production", reason="production gate"
)
def test_production_withholds_pending_rules_and_reports_them():
    doc = load_rules(CONFIG)
    pending = {r["id"] for r in pending_rules(doc)}
    for country, region in (("IN", "IN"), ("US", "US"), ("DE", "EU"), ("FR", "EU")):
        everything = {r["id"] for r in select_rules(doc, country, region)}
        served = {r["id"] for r in select_rules(doc, country, region, allow_pending=False)}
        assert not served & pending, "a pending rule would be shown in production"
        assert set(withheld_rule_ids(doc, country, region)) == pending & everything
        evaluated = {
            r["id"] for r in evaluate(doc, country, region, None, "any", 80, allow_pending=False)
        }
        assert not evaluated & pending

    # the API behaves the same way when started from the environment (ATLAS_ENV=production)
    from app.context import build_context
    from app.core.config import Settings
    from app.services.tree_age import TreeAgeService

    tree_age = TreeAgeService(build_context(Settings()))
    assert tree_age.allow_pending is False
    served_by_api = tree_age.rules()
    assert not any(r["verification_status"] == "pending" for r in served_by_api["rules"])
    assert set(served_by_api["withheld_rule_ids"]) == pending

    if pending:  # not a failure: the gate holds. Report what a release still has to confirm.
        warnings.warn(
            "tree-age rules withheld in production until confirmed from a primary source: "
            + ", ".join(sorted(pending)),
            UserWarning,
            stacklevel=1,
        )
