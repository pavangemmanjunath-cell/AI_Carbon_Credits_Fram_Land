"""Guardrails: each check passes on clean data and catches the problem it exists for."""

from __future__ import annotations

from atlas_agents import (
    AgentMessage,
    Blackboard,
    Evidence,
    Guardrail,
    GuardrailInput,
    GuardrailResult,
    ToolCall,
    check_no_coordinates,
    check_not_a_credit,
    check_pending_parameters,
    check_provenance,
    check_uncertainty,
    check_values_separated,
    credit_claims,
)
from atlas_agents.llm.redaction import sensitive_number_strings


def msg(text: str, kind: str = "finding", **kwargs: object) -> AgentMessage:
    defaults: dict = {"evidence": [Evidence("IPCC 2006", "ipcc")]}
    defaults.update(kwargs)
    return AgentMessage(
        id="M1",
        step=1,
        agent="carbon",
        agent_title="Carbon agent",
        kind=kind,
        text=text,
        **defaults,
    )  # type: ignore[arg-type]


ESTIMATE = {"low": 7.7, "central": 11.0, "high": 14.3, "unit": "tCO2e/yr"}


# ----------------------------------------------------------------------------- not-a-credit
def test_not_a_credit_passes_on_honest_text_and_records():
    result = check_not_a_credit(
        [
            "Estimated removal is 7.7–14.3 tCO₂e per year. "
            "This is an estimate, not a carbon credit.",
            "Scenario estimate; not an issued carbon credit. "
            "Market-value scenario — not guaranteed revenue.",
        ],
        [("the estimate", {"certified": False})],
        run_certified=False,
        disclaimer="Not a credit.",
    )
    assert result.status == "pass" and result.id == "not-a-credit"


def test_not_a_credit_fails_on_claims_flags_and_missing_disclaimer():
    assert "certified carbon credits" in credit_claims("These are certified carbon credits.")
    assert credit_claims("You will earn credits from this.")
    assert credit_claims("This brings guaranteed revenue.")
    assert credit_claims("This is not an issued carbon credit and not guaranteed revenue.") == []
    claim = check_not_a_credit(
        ["Your trees are now certified."], [], run_certified=False, disclaimer="x"
    )
    flag = check_not_a_credit(
        [], [("the estimate", {"certified": True})], run_certified=False, disclaimer="x"
    )
    bare = check_not_a_credit([], [], run_certified=False, disclaimer="")
    assert {claim.status, flag.status, bare.status} == {"fail"}
    assert "estimate" in flag.detail and "disclaimer" in bare.detail


# ----------------------------------------------------------------------------- uncertainty
def test_uncertainty_requires_ordered_ranges_units_and_confidence():
    assert check_uncertainty([("estimate", ESTIMATE)], [("estimate", "medium")]).status == "pass"
    assert check_uncertainty([("estimate", None)]).detail.startswith("No carbon numbers")
    unordered = check_uncertainty([("estimate", {**ESTIMATE, "low": 20.0})])
    no_unit = check_uncertainty([("estimate", {**ESTIMATE, "unit": ""})])
    single = check_uncertainty([("estimate", {"central": 11.0, "unit": "t"})])
    no_confidence = check_uncertainty([("estimate", ESTIMATE)], [("estimate", None)])
    assert {r.status for r in (unordered, no_unit, single, no_confidence)} == {"fail"}


# ----------------------------------------------------------------------------- provenance
def test_provenance_requires_evidence_on_findings_and_sources_on_records():
    ok = check_provenance(
        [msg("A finding."), msg("Plan.", kind="plan", evidence=[])],
        [("the estimate", {"sources": [{"id": "ipcc"}]})],
    )
    assert ok.status == "pass"
    bare = check_provenance([msg("A finding.", evidence=[])])
    unsourced = check_provenance([msg("x")], [("the estimate", {"sources": []})])
    assert bare.status == "fail" and "M1" in bare.detail
    assert unsourced.status == "fail" and "the estimate" in unsourced.detail


# ----------------------------------------------------------------------------- no-coordinates
def test_no_coordinates_passes_on_clean_messages():
    clean = msg(
        "Your plot is 2.13 ha in Karnataka, India. NDVI 0.63, 24.0 °C.",
        facts={"area_hectares": 2.13, "clamp": [0.2, 1.5]},
    )
    assert check_no_coordinates([clean], sensitive_strings={"13.292", "77.538"}).status == "pass"


def test_no_coordinates_fails_on_crafted_messages_without_echoing_them():
    in_text = msg("The farm is at 13.2923, 77.5384 near the road.")
    in_facts = msg("Clean text.", facts={"centroid": {"lat": 13.29, "lon": 77.53}})
    in_tool = msg(
        "Clean text.",
        tool_calls=[
            ToolCall("measure_plot", "ok", 1, input={}, output={"center": [77.538399, 13.292298]})
        ],
    )
    exact = msg("The middle of the field is 13.2923 north.")
    for message in (in_text, in_facts, in_tool, exact):
        result = check_no_coordinates(
            [message], sensitive_strings=sensitive_number_strings([13.292298])
        )
        assert result.status == "fail", message.text
        assert "13.29" not in result.detail and "77.5" not in result.detail


def test_sensitive_number_strings_cover_common_roundings():
    forms = sensitive_number_strings([13.292298])
    assert {"13.292", "13.2923", "13.29230", "13.292298"} <= forms
    assert "13.29" not in forms  # two decimals is too coarse to be an exact location


# ----------------------------------------------------------------------------- pending parameters
def test_pending_parameters_warns_with_names():
    params = [
        {"parameter": "carbon_fraction", "verification_status": "verified"},
        {"parameter": "above_ground_biomass_growth", "verification_status": "pending"},
        {"name": "root_to_shoot_ratio", "verification_status": "pending"},
    ]
    result = check_pending_parameters(params)
    assert result.status == "warn"
    assert "above_ground_biomass_growth, root_to_shoot_ratio" in result.detail
    assert check_pending_parameters(params[:1]).status == "pass"
    assert check_pending_parameters(None).status == "pass"


# ----------------------------------------------------------------------------- values separated
def test_values_separated_catches_summed_money():
    honest = msg(
        "Environmental benefit: an estimated 7.7–14.3 tCO₂e per year (central 11.0). "
        "Indicative carbon value (scenario): about ₹12,122 per year at the reference price of "
        "₹1,100 per tCO₂e. Other farm income is not estimated here; add your own records. "
        "These three values answer different questions and are never added together."
    )
    assert check_values_separated([honest]).status == "pass"
    summed = msg("In total you could get ₹12,122 plus your fruit income.")
    combined_fact = msg("Clean.", facts={"total_value": 20000})
    assert check_values_separated([summed]).status == "fail"
    assert check_values_separated([combined_fact]).status == "fail"


def test_guardrail_wrapper_never_raises_and_keeps_its_id():
    board = Blackboard()

    def boom(run: GuardrailInput) -> GuardrailResult:
        raise KeyError("x")

    assert Guardrail("boom", boom).run(GuardrailInput([], board)).status == "fail"
    renamed = Guardrail("mine", lambda run: GuardrailResult("other", "pass", "ok"))
    assert renamed.run(GuardrailInput([], board)).id == "mine"
