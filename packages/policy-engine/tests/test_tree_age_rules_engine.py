"""Tree-age rules engine: schema validation, matching by place / age / setting, outcomes.

(File name note: ``tests/data-quality/test_tree_age_rules.py`` checks the shipped data; this
module checks the *engine* with small hand-made rule sets and with the shipped file.)
"""

from __future__ import annotations

import copy
import json

import pytest

from policy_engine.tree_age import (
    CATEGORIES,
    CREDIT_OUTLOOKS,
    OUTCOMES,
    TreeAgeRulesError,
    age_class_for,
    credit_outlook,
    evaluate,
    load_rules,
    load_subdivisions,
    pending_rules,
    rule_problems,
    select_rules,
    validate_rules,
    withheld_rule_ids,
)

SOURCE = {
    "title": "Example Act",
    "publisher": "Example Ministry",
    "url": "https://example.org/act",
    "accessed": "2026-10-05",
}


def make_rule(rule_id: str = "in-ka-example", **overrides):
    rule = {
        "id": rule_id,
        "scope": "IN",
        "country": "IN",
        "subdivision": None,
        "locality": None,
        "name": "Example rule: for tests",
        "authority": "Example authority",
        "category": "tree-protection",
        "applies_to": {
            "min_age_years": None,
            "max_age_years": None,
            "trees": "existing",
            "setting": "any",
        },
        "outcome_for_existing_trees": "protected",
        "summary": "A short plain-language summary.",
        "details": "Longer details.",
        "amount": None,
        "status": "in-force",
        "is_example": False,
        "sources": [dict(SOURCE)],
        "verification_status": "verified",
        "notes": None,
    }
    for key, value in overrides.items():
        if key in rule["applies_to"]:
            rule["applies_to"][key] = value
        else:
            rule[key] = value
    return rule


def make_doc(*rules):
    return {
        "version": "0.0.1",
        "updated": "2026-10-05",
        "disclaimer": "Screening information only.",
        "age_classes": [
            {"id": "young", "label": "Young (0–20 years)", "min_age": 0, "max_age": 20},
            {"id": "old", "label": "Old (21+ years)", "min_age": 21, "max_age": None},
        ],
        "rules": list(rules) or [make_rule()],
    }


@pytest.fixture(scope="module")
def doc():
    return load_rules()


@pytest.fixture(scope="module")
def subdivisions():
    return load_subdivisions()


def by_id(results):
    return {r["id"]: r for r in results}


# ------------------------------------------------------------------------------- loading
def test_shipped_rules_load_validate_and_are_json_ready(doc, subdivisions):
    validate_rules(doc, subdivisions)
    assert doc["version"] and doc["disclaimer"]
    assert isinstance(doc["updated"], str) and len(doc["updated"]) == 10  # a date, not a datetime
    assert len(doc["rules"]) >= 20
    json.dumps(doc)  # no date objects left


def test_load_returns_private_copies(doc):
    again = load_rules()
    again["rules"].clear()
    assert load_rules()["rules"]


def test_subdivisions_file_has_the_required_codes(subdivisions):
    codes = {
        item["code"]: item["name"]
        for block in subdivisions["countries"].values()
        for item in block["subdivisions"]
    }
    expected = {
        "IN-HR": "Haryana",
        "IN-MH": "Maharashtra",
        "IN-KA": "Karnataka",
        "IN-DL": "Delhi",
        "US-OR": "Oregon",
        "US-CA": "California",
        "DE-BE": "Berlin",
    }
    for code, name in expected.items():
        assert codes[code] == name
    assert len([c for c in codes if c.startswith("IN-")]) == 36  # 28 states + 8 union territories
    assert len([c for c in codes if c.startswith("US-")]) >= 51  # 50 states + DC


# ----------------------------------------------------------------------------- validation
def test_a_minimal_valid_document_has_no_problems():
    assert rule_problems(make_doc()) == []


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda r: r.pop("summary"), "missing field(s): summary"),
        (lambda r: r.update(scope="MARS"), "'scope' must be one of"),
        (lambda r: r.update(category="gift"), "'category' must be one of"),
        (lambda r: r.update(outcome_for_existing_trees="maybe"), "'outcome_for_existing_trees'"),
        (lambda r: r.update(status="draft"), "'status' must be one of"),
        (lambda r: r.update(verification_status="assumption"), "'verification_status'"),
        (lambda r: r.update(is_example="no"), "'is_example' must be true or false"),
        (lambda r: r.update(id="Not A Slug"), "'id' must be a slug"),
        (lambda r: r.update(typo_field=1), "unknown field(s): typo_field"),
        (lambda r: r.update(country="india"), "'country' must be null or an upper-case"),
        (
            lambda r: r.update(subdivision="Karnataka"),
            "'subdivision' must be null or an ISO 3166-2",
        ),
        (lambda r: r.update(subdivision="US-OR"), "is not inside country 'IN'"),
        (lambda r: r.update(locality="Bengaluru"), "must also name its 'subdivision'"),
        (lambda r: r.update(scope="GLOBAL"), "a GLOBAL rule must not name a country"),
        (lambda r: r["applies_to"].update(trees="all"), "'applies_to.trees' must be one of"),
        (lambda r: r["applies_to"].update(setting="farm"), "'applies_to.setting' must be one of"),
        (lambda r: r["applies_to"].update(min_age_years="75"), "'applies_to.min_age_years'"),
        (lambda r: r["applies_to"].update(min_age_years=80, max_age_years=70), "larger than"),
        (lambda r: r["applies_to"].pop("setting"), "'applies_to' must have exactly the keys"),
        (lambda r: r.update(sources=[]), "'sources' must list at least one source"),
        (lambda r: r["sources"][0].update(url="http://example.org"), "must be an https:// link"),
        (lambda r: r["sources"][0].pop("accessed"), "'accessed' must be a date"),
        (lambda r: r["sources"][0].update(title=""), "'title' must be a non-empty string"),
        (
            lambda r: r.update(amount={"value": 5, "currency": "INR", "unit": "per tree"}),
            "'amount.as_of' must be a date",
        ),
        (
            lambda r: r.update(
                amount={"value": -1, "currency": "INR", "unit": "x", "as_of": "2026-07"}
            ),
            "'amount.value' must be a number",
        ),
    ],
)
def test_rule_schema_problems_are_clear(mutate, expected):
    rule = make_rule()
    mutate(rule)
    problems = rule_problems(make_doc(rule))
    assert any(expected in problem for problem in problems), problems
    assert any("'in-ka-example'" in problem or "Not A Slug" in problem for problem in problems)
    with pytest.raises(TreeAgeRulesError, match="rules.yaml is invalid"):
        validate_rules(make_doc(rule))


def test_a_valid_amount_is_accepted():
    amount = {"value": 3000, "currency": "INR", "unit": "per tree per year", "as_of": "2026-07"}
    assert rule_problems(make_doc(make_rule(amount=amount))) == []


def test_duplicate_ids_are_reported():
    problems = rule_problems(make_doc(make_rule("same-id"), make_rule("same-id")))
    assert any("'same-id' is used more than once" in p for p in problems)


def test_subdivisions_must_be_listed_when_a_list_is_given(subdivisions):
    rule = make_rule(subdivision="IN-ZZ")
    assert rule_problems(make_doc(rule)) == []  # no list given → only the format is checked
    problems = rule_problems(make_doc(rule), subdivisions)
    assert any("not listed in config/tree-age/subdivisions.yaml" in p for p in problems)
    assert rule_problems(make_doc(make_rule(subdivision="IN-HR")), subdivisions) == []


def test_all_problems_are_listed_at_once():
    broken = make_rule(scope="MARS", category="gift", status="draft")
    message = None
    try:
        validate_rules(make_doc(broken))
    except TreeAgeRulesError as error:
        message = str(error)
    assert message and message.count("\n - ") >= 3


@pytest.mark.parametrize(
    ("classes", "expected"),
    [
        (
            [
                {"id": "a", "label": "A", "min_age": 0, "max_age": 20},
                {"id": "b", "label": "B", "min_age": 22, "max_age": None},
            ],
            "must be contiguous",
        ),
        (
            [
                {"id": "a", "label": "A", "min_age": 0, "max_age": 20},
                {"id": "b", "label": "B", "min_age": 20, "max_age": None},
            ],
            "must be contiguous",
        ),
        ([{"id": "a", "label": "A", "min_age": 1, "max_age": None}], "must be contiguous"),
        ([{"id": "a", "label": "A", "min_age": 0, "max_age": 20}], "must be open-ended"),
        (
            [
                {"id": "a", "label": "A", "min_age": 0, "max_age": None},
                {"id": "b", "label": "B", "min_age": 5, "max_age": None},
            ],
            "only the last age class",
        ),
        (
            [
                {"id": "a", "label": "A", "min_age": 0, "max_age": 5},
                {"id": "a", "label": "B", "min_age": 6, "max_age": None},
            ],
            "used more than once",
        ),
        ([], "non-empty list"),
    ],
)
def test_age_classes_must_be_contiguous_and_open_ended(classes, expected):
    document = make_doc()
    document["age_classes"] = classes
    assert any(expected in p for p in rule_problems(document))


def test_top_level_fields_are_required():
    document = make_doc()
    for key in ("version", "updated", "disclaimer", "age_classes", "rules"):
        broken = copy.deepcopy(document)
        broken.pop(key)
        assert any(f"missing top-level field {key!r}" in p for p in rule_problems(broken))


def test_pending_rules_are_listed_and_explained(doc):
    pending = pending_rules(doc)
    assert pending  # the shipped file still has rules awaiting a primary source
    for rule in pending:
        assert rule["notes"] and rule["notes"].strip(), rule["id"]


# ------------------------------------------------------------------------------ age classes
@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, "young"),
        (20, "young"),
        (21, "mature"),
        (49, "mature"),
        (50, "old"),
        (74, "old"),
        (75, "veteran"),
        (300, "veteran"),
    ],
)
def test_age_class_for(doc, age, expected):
    result = age_class_for(age, doc)
    assert result["id"] == expected
    assert result["label"].lower().startswith(expected)
    assert age_class_for(age)["id"] == expected  # default document


def test_age_class_for_label_matches_the_contract_example(doc):
    assert age_class_for(60, doc) == {"id": "old", "label": "Old (50–74 years)"}


# ----------------------------------------------------------------------------- geography
def test_geography_selects_global_region_and_country(doc, subdivisions):
    india = by_id(evaluate(doc, "IN", "IN", None, "any", 60, subdivisions=subdivisions))
    assert {r["scope"] for r in india.values()} == {"GLOBAL", "IN"}
    assert "global-verra-vm0047-arr" in india and "in-ccts-offset-bm-fr05-002" in india
    assert not any(rid.startswith(("us-", "eu-")) for rid in india)

    us = by_id(evaluate(doc, "US", "US", None, "any", 60, subdivisions=subdivisions))
    assert {r["scope"] for r in us.values()} == {"GLOBAL", "US"}

    germany = by_id(evaluate(doc, "DE", "EU", None, "any", 60, subdivisions=subdivisions))
    assert "eu-de-berlin-baumschutzverordnung" in germany
    assert "eu-crcf-regulation-2024-3012" in germany
    france = by_id(evaluate(doc, "FR", "EU", None, "any", 60, subdivisions=subdivisions))
    assert "eu-de-berlin-baumschutzverordnung" not in france  # a German rule
    assert "eu-crcf-regulation-2024-3012" in france


def test_every_result_keeps_the_original_fields_and_adds_three(doc, subdivisions):
    results = evaluate(doc, "IN", "IN", "IN-KA", "farm", 60, subdivisions=subdivisions)
    originals = {r["id"]: r for r in doc["rules"]}
    for rule in results:
        original = originals[rule["id"]]
        assert {k: rule[k] for k in original} == original
        assert set(rule) - set(original) == {"applies", "why", "outcome_for_you"}
        assert isinstance(rule["applies"], bool) and rule["why"].strip()
        assert rule["outcome_for_you"] in OUTCOMES
    assert not any("applies" in r for r in doc["rules"])  # the shared document is untouched
    json.dumps(results)


# ---------------------------------------------------------------------- subdivision / age / setting
def test_a_rule_for_another_subdivision_does_not_apply(doc, subdivisions):
    for chosen in (None, "IN-KA"):
        rules = by_id(evaluate(doc, "IN", "IN", chosen, "farm", 80, subdivisions=subdivisions))
        haryana = rules["in-hr-pran-vayu-devta-pension"]
        assert haryana["applies"] is False
        assert haryana["why"] == "Only in Haryana (IN-HR)"
    karnataka = by_id(evaluate(doc, "IN", "IN", "IN-KA", "farm", 80, subdivisions=subdivisions))
    assert karnataka["in-ka-preservation-of-trees-act"]["applies"] is True
    assert karnataka["in-dl-preservation-of-trees-act"]["why"] == "Only in Delhi (IN-DL)"


def test_age_threshold_is_a_hard_filter(doc, subdivisions):
    young = by_id(evaluate(doc, "IN", "IN", "IN-HR", "farm", 74, subdivisions=subdivisions))
    pension = young["in-hr-pran-vayu-devta-pension"]
    assert pension["applies"] is False
    assert pension["why"] == "Needs trees aged 75 years or more"
    old = by_id(evaluate(doc, "IN", "IN", "IN-HR", "farm", 75, subdivisions=subdivisions))
    pension = old["in-hr-pran-vayu-devta-pension"]
    assert pension["applies"] is True
    assert pension["why"].startswith(
        "Applies in Haryana (IN-HR) to trees outside forests aged 75 years or more"
    )
    assert "not yet confirmed from a primary source" in pension["why"]  # pending rule is flagged
    assert pension["outcome_for_you"] == "payment"


def test_setting_is_a_filter_and_any_never_excludes(doc, subdivisions):
    farm = by_id(evaluate(doc, "IN", "IN", "IN-DL", "farm", 30, subdivisions=subdivisions))
    assert farm["in-dl-preservation-of-trees-act"]["applies"] is False
    assert farm["in-dl-preservation-of-trees-act"]["why"] == "Only for urban trees"
    urban = by_id(evaluate(doc, "IN", "IN", "IN-DL", "urban", 30, subdivisions=subdivisions))
    assert urban["in-dl-preservation-of-trees-act"]["applies"] is True
    assert (
        urban["in-dl-preservation-of-trees-act"]["why"]
        == "Applies in Delhi (IN-DL) to urban trees at any age"
    )
    unknown = by_id(evaluate(doc, "IN", "IN", "IN-DL", "any", 30, subdivisions=subdivisions))
    assert unknown["in-dl-preservation-of-trees-act"]["applies"] is True
    assert unknown["in-gcp-tree-plantation"]["applies"] is True  # forest-only, setting unknown

    forest = by_id(evaluate(doc, "IN", "IN", "IN-HR", "forest", 90, subdivisions=subdivisions))
    assert forest["in-hr-pran-vayu-devta-pension"]["why"] == "Only for trees outside forests"
    assert forest["in-gcp-tree-plantation"]["applies"] is True
    # a farm tree and an urban tree are both outside forests
    for setting in ("farm", "urban"):
        rules = by_id(evaluate(doc, "IN", "IN", "IN-HR", setting, 90, subdivisions=subdivisions))
        assert rules["in-hr-pran-vayu-devta-pension"]["applies"] is True


def test_maharashtra_heritage_needs_age_and_urban_setting(doc, subdivisions):
    def heritage(age, setting):
        rules = by_id(evaluate(doc, "IN", "IN", "IN-MH", setting, age, subdivisions=subdivisions))
        return rules["in-mh-heritage-tree"]

    assert heritage(49, "urban")["why"] == "Needs trees aged 50 years or more"
    assert heritage(50, "farm")["why"] == "Only for urban trees"
    assert heritage(50, "urban")["applies"] is True
    # the Maharashtra replacement-planting rule has no age bound
    compensatory = by_id(evaluate(doc, "IN", "IN", "IN-MH", "urban", 3, subdivisions=subdivisions))
    assert compensatory["in-mh-compensatory-planting-estimated-age"]["applies"] is True


def test_a_rule_with_a_max_age_reports_it(subdivisions):
    document = make_doc(make_rule(min_age_years=5, max_age_years=20))
    low = evaluate(document, "IN", "IN", None, "any", 3, subdivisions=subdivisions)[0]
    high = evaluate(document, "IN", "IN", None, "any", 30, subdivisions=subdivisions)[0]
    inside = evaluate(document, "IN", "IN", None, "any", 10, subdivisions=subdivisions)[0]
    assert low["why"] == high["why"] == "Needs trees aged 5 to 20 years"
    assert inside["applies"] is True and "aged 5 to 20 years" in inside["why"]
    only_max = make_doc(make_rule(max_age_years=20))
    over = evaluate(only_max, "IN", "IN", None, "any", 21, subdivisions=subdivisions)[0]
    assert over["why"] == "Needs trees aged 20 years or less"


def test_the_applies_sentence_for_a_plain_country_rule_matches_the_contract(doc, subdivisions):
    rules = by_id(evaluate(doc, "IN", "IN", None, "any", 60, subdivisions=subdivisions))
    assert rules["in-ccts-offset-bm-fr05-002"]["why"] == "Applies in India at any age"
    assert rules["global-verra-vm0047-arr"]["why"] == "Applies worldwide at any age"
    us = by_id(evaluate(doc, "US", "US", None, "forest", 60, subdivisions=subdivisions))
    assert (
        us["us-acr-ifm-non-federal-v2-1"]["why"]
        == "Applies in the United States to trees in forests at any age"
    )
    eu = by_id(evaluate(doc, "FR", "EU", None, "any", 60, subdivisions=subdivisions))
    assert eu["eu-crcf-regulation-2024-3012"]["why"] == "Applies in the EU at any age"
    assert "proposed, not yet in force" in eu["eu-crcf-carbon-farming-delegated-act-2026"]["why"]


# ------------------------------------------------------------------------------- locality
def test_municipal_examples_apply_only_for_their_city(doc, subdivisions):
    oregon = by_id(evaluate(doc, "US", "US", "US-OR", "urban", 80, subdivisions=subdivisions))
    portland = oregon["us-or-portland-heritage-trees"]
    assert portland["applies"] is False
    assert portland["why"] == "Municipal example for Portland (US-OR); check your own city's rules"
    assert oregon["us-ca-los-angeles-protected-trees"]["why"] == "Only in California (US-CA)"

    named = by_id(
        evaluate(
            doc, "US", "US", "US-OR", "urban", 80, locality="  portland ", subdivisions=subdivisions
        )
    )
    assert named["us-or-portland-heritage-trees"]["applies"] is True
    assert named["us-or-portland-heritage-trees"]["why"].endswith("check your own city's rules")
    wrong_city = by_id(
        evaluate(doc, "US", "US", "US-OR", "urban", 80, locality="Salem", subdivisions=subdivisions)
    )
    assert wrong_city["us-or-portland-heritage-trees"]["applies"] is False


def test_berlin_applies_because_the_subdivision_is_the_city(doc, subdivisions):
    berlin = by_id(evaluate(doc, "DE", "EU", "DE-BE", "urban", 40, subdivisions=subdivisions))
    rule = berlin["eu-de-berlin-baumschutzverordnung"]
    assert rule["applies"] is True
    assert rule["why"].startswith("Applies in Berlin (DE-BE) to urban trees at any age")
    assert "municipal example" in rule["why"]
    bavaria = by_id(evaluate(doc, "DE", "EU", "DE-BY", "urban", 40, subdivisions=subdivisions))
    assert bavaria["eu-de-berlin-baumschutzverordnung"]["why"] == "Only in Berlin (DE-BE)"


# ------------------------------------------------------------------------ outcome_for_you
def test_outcome_for_existing_trees_is_the_rules_own_outcome(doc, subdivisions):
    rules = evaluate(doc, "IN", "IN", "IN-HR", "farm", 80, subdivisions=subdivisions)
    originals = {r["id"]: r["outcome_for_existing_trees"] for r in doc["rules"]}
    for rule in rules:
        assert rule["outcome_for_you"] == originals[rule["id"]]
    ages = {
        age: by_id(evaluate(doc, "IN", "IN", "IN-HR", "farm", age, subdivisions=subdivisions))
        for age in (1, 5, 60, 300)
    }
    for rule_id, outcome in originals.items():
        if rule_id in ages[1]:
            assert {ages[a][rule_id]["outcome_for_you"] for a in ages} == {outcome}


def test_age_zero_turns_new_planting_rules_conditional_and_existing_rules_not_applicable(
    doc, subdivisions
):
    rules = evaluate(doc, "IN", "IN", "IN-KA", "any", 0, subdivisions=subdivisions)
    for rule in rules:
        trees = rule["applies_to"]["trees"]
        expected = "not-applicable" if trees == "existing" else "conditional"
        assert rule["outcome_for_you"] == expected, rule["id"]
    index = by_id(rules)
    assert index["global-verra-vm0047-arr"]["outcome_for_you"] == "conditional"  # new planting
    assert index["in-ka-preservation-of-trees-act"]["outcome_for_you"] == "not-applicable"
    assert index["in-hr-pran-vayu-devta-pension"]["outcome_for_you"] == "not-applicable"
    assert index["global-icvcm-ccp-additionality"]["outcome_for_you"] == "conditional"  # 'any'


# ------------------------------------------------------------------------------- ordering
def test_applicable_rules_come_first_then_category_then_id(doc, subdivisions):
    for args in (
        ("IN", "IN", "IN-KA", "farm", 60),
        ("US", "US", "US-OR", "forest", 40),
        ("DE", "EU", "DE-BE", "urban", 90),
    ):
        results = evaluate(doc, *args, subdivisions=subdivisions)
        keys = [(not r["applies"], CATEGORIES.index(r["category"]), r["id"]) for r in results]
        assert keys == sorted(keys)
        flags = [r["applies"] for r in results]
        assert flags == sorted(flags, reverse=True)  # all True first
        assert True in flags and False in flags


# ----------------------------------------------------------------------------- bad inputs
def test_invalid_arguments_are_rejected(doc, subdivisions):
    with pytest.raises(ValueError, match="setting"):
        evaluate(doc, "IN", "IN", None, "garden", 5, subdivisions=subdivisions)
    with pytest.raises(ValueError, match="age_years"):
        evaluate(doc, "IN", "IN", None, "any", -1, subdivisions=subdivisions)


# ----------------------------------------------------------------------- select_rules
def test_select_rules_filters_by_geography_and_subdivision(doc):
    assert len(select_rules(doc)) == len(doc["rules"])
    india = select_rules(doc, country="IN", region="IN")
    assert {r["scope"] for r in india} == {"GLOBAL", "IN"}
    karnataka = select_rules(doc, country="IN", region="IN", subdivision="in-ka")
    assert any(r["subdivision"] == "IN-KA" for r in karnataka)
    assert all(r["subdivision"] in (None, "IN-KA") for r in karnataka)
    assert any(r["id"] == "in-ccts-offset-bm-fr05-002" for r in karnataka)
    assert len(karnataka) < len(india)
    # copies: editing a result never changes the document
    karnataka[0]["name"] = "changed"
    assert all(r["name"] != "changed" for r in doc["rules"])


# ------------------------------------------------------------------------- credit outlook
def outlook(doc, subdivisions, *args):
    rules = evaluate(doc, *args, subdivisions=subdivisions)
    return credit_outlook(rules, args[-1]), rules


def test_existing_trees_in_india_are_not_eligible(doc, subdivisions):
    result, _ = outlook(doc, subdivisions, "IN", "IN", "IN-KA", "farm", 60)
    assert result["existing_trees"] == "not-eligible"
    assert "do not earn removal credits" in result["summary"]
    assert {"global-verra-vm0047-arr", "in-ccts-offset-bm-fr05-002"} <= set(
        result["based_on_rule_ids"]
    )
    assert result["summary"].count(".") == 1  # one sentence


def test_forest_trees_in_the_us_have_a_conditional_route(doc, subdivisions):
    result, _ = outlook(doc, subdivisions, "US", "US", "US-OR", "forest", 40)
    assert result["existing_trees"] == "conditional"
    assert (
        "specific conditions" in result["summary"]
        and "3 of the applicable rules" in result["summary"]
    )
    assert "an estimate is never a credit" in result["summary"]


def test_a_farm_tree_in_the_us_is_not_eligible(doc, subdivisions):
    result, _ = outlook(doc, subdivisions, "US", "US", "US-OR", "farm", 40)
    assert result["existing_trees"] == "not-eligible"  # the urban and forest routes do not apply


def test_eu_trees_are_conditional_on_crcf(doc, subdivisions):
    result, _ = outlook(doc, subdivisions, "FR", "EU", None, "farm", 25)
    assert result["existing_trees"] == "conditional"
    assert "Regulation (EU) 2024/3012 (CRCF)" in result["summary"]
    assert "not yet confirmed" not in result["summary"]


def test_new_trees_are_conditional(doc, subdivisions):
    result, _ = outlook(doc, subdivisions, "IN", "IN", None, "farm", 0)
    assert result["existing_trees"] == "conditional"
    assert "Newly planted trees" in result["summary"]
    assert "an estimate is never a credit" in result["summary"]


def test_eligible_is_never_claimed():
    rule = make_rule(category="carbon-credit-eligibility", outcome_for_existing_trees="eligible")
    document = make_doc(rule)
    rules = evaluate(document, "IN", "IN", None, "any", 40, subdivisions={"countries": {}})
    assert rules[0]["outcome_for_you"] == "eligible"
    result = credit_outlook(rules, 40)
    assert result["existing_trees"] == "conditional"
    assert result["existing_trees"] in CREDIT_OUTLOOKS


def test_only_rules_in_force_can_lift_the_outlook():
    proposed = make_rule(
        "in-proposed",
        category="carbon-credit-eligibility",
        outcome_for_existing_trees="conditional",
        status="proposed",
    )
    in_force = make_rule(
        "in-in-force",
        category="carbon-credit-eligibility",
        outcome_for_existing_trees="not-eligible",
    )
    rules = evaluate(
        make_doc(proposed, in_force), "IN", "IN", None, "any", 40, subdivisions={"countries": {}}
    )
    result = credit_outlook(rules, 40)
    assert result["existing_trees"] == "not-eligible"
    assert result["based_on_rule_ids"] == ["in-in-force"]


def test_a_lift_that_rests_only_on_a_pending_rule_says_so():
    pending = make_rule(
        "in-pending",
        category="carbon-credit-eligibility",
        outcome_for_existing_trees="conditional",
        verification_status="pending",
    )
    rules = evaluate(make_doc(pending), "IN", "IN", None, "any", 40, subdivisions={"countries": {}})
    result = credit_outlook(rules, 40)
    assert result["existing_trees"] == "conditional"
    assert "not yet confirmed from a primary source" in result["summary"]


def test_rules_that_do_not_apply_never_change_the_outlook():
    elsewhere = make_rule(
        "in-hr-credit",
        category="carbon-credit-eligibility",
        outcome_for_existing_trees="conditional",
        subdivision="IN-HR",
    )
    rules = evaluate(
        make_doc(elsewhere), "IN", "IN", "IN-KA", "any", 40, subdivisions={"countries": {}}
    )
    assert rules[0]["applies"] is False
    assert credit_outlook(rules, 40)["existing_trees"] == "not-eligible"


# ----------------------------------------------------------------------- pending rules
def test_pending_rules_are_withheld_when_not_allowed(doc, subdivisions):
    pending = {r["id"] for r in pending_rules(doc)}
    assert pending
    served = evaluate(doc, "IN", "IN", "IN-HR", "farm", 80, subdivisions=subdivisions)
    assert pending & {r["id"] for r in served}  # shown (flagged) by default
    assert any(r["verification_status"] == "pending" for r in served)

    safe = evaluate(
        doc, "IN", "IN", "IN-HR", "farm", 80, subdivisions=subdivisions, allow_pending=False
    )
    assert not any(r["verification_status"] == "pending" for r in safe)
    assert {r["id"] for r in served} - {r["id"] for r in safe} == pending & {
        r["id"] for r in served
    }
    assert not any(
        r["verification_status"] == "pending" for r in select_rules(doc, allow_pending=False)
    )
    assert len(select_rules(doc, allow_pending=False)) == len(doc["rules"]) - len(pending)


def test_withheld_rule_ids_are_those_the_place_would_have_shown(doc):
    india = withheld_rule_ids(doc, "IN", "IN")
    assert set(india) <= {r["id"] for r in pending_rules(doc)}
    assert all(i.startswith("in-") for i in india)  # only Indian rules matter to an Indian user
    everywhere = withheld_rule_ids(doc)
    assert set(everywhere) == {r["id"] for r in pending_rules(doc)}
    assert withheld_rule_ids(doc, "US", "US") == []  # nothing pending in the US set


def test_withholding_changes_the_credit_outlook_only_through_the_rules_it_hides():
    pending = make_rule(
        "in-pending",
        category="carbon-credit-eligibility",
        outcome_for_existing_trees="conditional",
        verification_status="pending",
    )
    document = make_doc(pending)
    empty = {"countries": {}}
    shown = evaluate(document, "IN", "IN", None, "any", 40, subdivisions=empty)
    hidden = evaluate(
        document, "IN", "IN", None, "any", 40, subdivisions=empty, allow_pending=False
    )
    assert credit_outlook(shown, 40)["existing_trees"] == "conditional"
    assert hidden == []
    assert credit_outlook(hidden, 40)["existing_trees"] == "not-eligible"
