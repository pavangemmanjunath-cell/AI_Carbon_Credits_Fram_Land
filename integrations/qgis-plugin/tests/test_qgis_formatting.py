# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Tests of the HTML/text formatting: disclaimers, three separate values, escaping, robustness."""

from __future__ import annotations

import json
import math
import random
import re
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from carboncreditbuy_qgis import formatting
from carboncreditbuy_qgis.api_client import (
    ApiConfigError,
    ApiConnectionError,
    ApiProblem,
    ApiResponseError,
)
from carboncreditbuy_qgis.crowns import CrownCount
from carboncreditbuy_qgis.formatting import (
    describe_confidence_range,
    describe_crown_count,
    describe_error,
    describe_health,
    esc,
    fmt_num,
    fmt_percent,
    format_agent_run,
    format_analysis,
    format_carbon_results,
    format_inventory_page,
    format_plot_page,
    link,
    pretty_unit,
    safe_url,
)
from carboncreditbuy_qgis.geometry import GeometryError
from carboncreditbuy_qgis.version import DISCLAIMER

SAMPLES = Path(__file__).resolve().parents[3] / "data" / "sample" / "responses"
XSS = '<script>alert("x")</script><img src=x onerror=alert(1)>'


def sample(name: str) -> Any:
    path = SAMPLES / f"{name}.json"
    if not path.is_file():
        pytest.skip(f"sample response {path} is not available")
    return json.loads(path.read_text(encoding="utf-8"))


ALLOWED_TAGS = {
    "html", "head", "meta", "title", "body", "h2", "h3", "p", "b", "i", "code", "span",
    "table", "tr", "td", "ul", "li", "br", "hr", "a",
}  # fmt: skip
ALLOWED_ATTRIBUTES = {
    "charset", "width", "cellspacing", "cellpadding", "border", "bgcolor", "style", "href",
}  # fmt: skip


class _MarkupAudit(HTMLParser):
    """Collects every tag and attribute of a page so the tests can allow-list them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.problems: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_TAGS:
            self.problems.append(f"tag <{tag}>")
        for name, value in attrs:
            if name not in ALLOWED_ATTRIBUTES:
                self.problems.append(f"attribute {name} on <{tag}>")
            if name == "href" and not str(value).lower().startswith(("http://", "https://")):
                self.problems.append(f"href {value!r}")
            if name == "style" and re.search(r"url\(|expression\(|javascript", str(value), re.I):
                self.problems.append(f"style {value!r}")


def assert_no_active_markup(html_text: str) -> None:
    """Only the tags and attributes the formatters use may appear; escaped text is fine."""
    audit = _MarkupAudit()
    audit.feed(html_text)
    audit.close()
    assert audit.problems == []


# --------------------------------------------------------------------------- inline fixtures
ESTIMATE: dict[str, Any] = {
    "estimate_id": "EST-AB12",
    "plot_id": "PLT-1",
    "inventory_id": "INV-1",
    "estimate": {"low": 4.02, "central": 5.74, "high": 7.46, "unit": "tCO2e/yr"},
    "confidence": "medium",
    "certified": False,
    "disclaimer": "Scenario estimate; not an issued carbon credit.",
    "stock": {"low": 32.8, "central": 46.9, "high": 61.0, "unit": "tCO2e"},
    "components": {"above_ground_tco2e_yr": 3.68, "below_ground_tco2e_yr": 2.06},
    "model": {"id": "tree-biomass", "version": "0.1.0", "tier": 1},
    "methodology": {
        "name": "IPCC 2006 Vol 4 Ch 4",
        "references": [{"title": "IPCC", "url": "https://www.ipcc.ch"}],
    },
    "parameters_used": [
        {"verification_status": "verified"},
        {"verification_status": "pending"},
        {"verification_status": "assumption"},
    ],
    "readiness": {
        "score": 55,
        "grade": "medium",
        "present_evidence": [{"id": "polygon", "label": "Land polygon"}],
        "missing_evidence": [{"id": "dbh", "label": "Tree diameter measurements", "weight": 15}],
    },
    "provenance": {
        "mode": "live",
        "sources": [{"id": "x", "name": "ESA WorldCover", "license": "CC BY 4.0"}],
    },
    "generated_at": "2026-10-05T10:00:00Z",
    "notes": ["Model note one."],
}
MARKET: dict[str, Any] = {
    "currency": "INR",
    "currency_symbol": "₹",
    "scenarios": [
        {
            "id": "low",
            "label": "Low",
            "price_per_tco2e": 480,
            "value_per_year": {"low": 1930, "central": 2755, "high": 3581},
        }
    ],
    "other_income": [
        {
            "id": "fruit",
            "label": "Fruit sales",
            "value": None,
            "unit": "INR/yr",
            "source": "not provided",
        }
    ],
    "basis": {"note": "Scenario prices.", "as_of": "2026-01", "verification_status": "pending"},
    "disclaimer": "Market-value scenario, not guaranteed revenue.",
}
POLICY: dict[str, Any] = {
    "programmes": [
        {
            "id": "ccts",
            "name": "Carbon Credit Trading Scheme",
            "authority": "BEE",
            "kind": "compliance_market",
            "status": "requires_assessment",
            "requirements": ["Registered methodology"],
            "notes": ["India: GCP and CCTS are separate mechanisms."],
            "references": [{"title": "BEE", "url": "https://beeindia.gov.in"}],
        }
    ],
    "disclaimer": "Initial screening only.",
}
PLOT: dict[str, Any] = {
    "plot_id": "PLT-1",
    "name": "North field",
    "country": "IN",
    "region": "Karnataka",
    "area_hectares": 3.8037,
    "area_acres": 9.4,
    "source": "api",
    "privacy": "private",
    "geometry": {"type": "Polygon", "coordinates": [[[77.1234567, 13.7654321]]]},
}
INVENTORY: dict[str, Any] = {
    "inventory_id": "INV-1",
    "plot_id": "PLT-1",
    "species": {"id": "mango", "scientific_name": "Mangifera indica", "common_name": "Mango"},
    "tree_count": 120,
    "density_per_ha": 31.5,
    "plantation_year": 2019,
    "age_years": 7,
    "measurement_source": "model-estimated",
    "data_quality": {
        "confidence": "medium",
        "fields": [
            {"name": "tree_count", "status": "supplied"},
            {"name": "dbh", "status": "missing"},
        ],
    },
}
AGENT_RUN: dict[str, Any] = {
    "run_id": "RUN-1",
    "plot_id": "PLT-1",
    "plan": {"id": "full-assessment", "title": "Full assessment", "steps": ["analyse", "estimate"]},
    "status": "completed",
    "reasoner": {"mode": "deterministic", "llm_enabled": False, "provider": None},
    "started_at": "2026-10-05T10:00:00Z",
    "finished_at": "2026-10-05T10:00:02Z",
    "duration_ms": 2034,
    "steps": [{"step": 1, "agent": "land-analyst", "status": "done", "duration_ms": 120}],
    "messages": [
        {
            "id": "m1",
            "step": 1,
            "agent": "land-analyst",
            "agent_title": "Land analyst",
            "to": "carbon-estimator",
            "kind": "finding",
            "text": "Tree cover is 12 percent.\nCropland dominates.",
            "tool_calls": [
                {"tool": "get_landcover", "status": "ok", "duration_ms": 12},
                {"tool": "get_ndvi", "status": "error"},
                {"tool": "get_soil", "status": "skipped"},
            ],
            "evidence": [
                {"label": "ESA WorldCover", "source": "ESA", "url": "https://esa-worldcover.org"},
                {"label": "Bad link", "url": "javascript:alert(1)"},
            ],
            "confidence": "medium",
            "created_at": "2026-10-05T10:00:01Z",
        },
        {"agent_title": "Reviewer", "kind": "warning", "text": "Check the count."},
    ],
    "summary": {"headline": "Estimated 5.7 tCO2e/yr (scenario).", "certified": False},
    "guardrails": [
        {"id": "no-credit-claim", "status": "pass", "detail": "No credit language."},
        {"id": "coordinates", "status": "warn", "detail": "Coordinates withheld."},
        {"id": "numbers", "status": "fail", "detail": "Mismatch."},
    ],
    "certified": False,
    "disclaimer": "Scenario estimate only. This is not an issued carbon credit.",
}
FORMATTERS: dict[str, Callable[[Any], str]] = {
    "plot": lambda data: format_plot_page(data, data, "analysis failed: <b>", ["note <i>"]),
    "analysis": format_analysis,
    "inventory": lambda data: format_inventory_page(data, None, None, None),
    "carbon": lambda data: format_carbon_results(data, data, data, "m", "p"),
    "agents": format_agent_run,
}


# --------------------------------------------------------------------------- carbon results
def test_carbon_results_show_the_disclaimer_certified_false_and_three_separate_values() -> None:
    page = format_carbon_results(ESTIMATE, MARKET, POLICY)
    assert DISCLAIMER in page
    assert "certified: false" in page
    assert "never added together" in page
    headings = re.findall(r"<h3>(\d) · ([^<]+)</h3>", page)
    assert [number for number, _ in headings] == ["1", "2", "3"]
    assert "Environmental benefit" in headings[0][1]
    assert "Indicative carbon value" in headings[1][1]
    assert "Other farm income" in headings[2][1]
    assert "estimated annual carbon removal" in page
    assert "tCO₂e/yr" in page
    assert "ESG amount" not in page


def test_the_removal_range_is_low_central_high_and_values_are_never_summed() -> None:
    page = format_carbon_results(ESTIMATE, MARKET, POLICY)
    for shown in ("4.02", "5.74", "7.46", "₹1,930", "₹2,755", "₹3,581"):
        assert shown in page
    for summed in ("5.74 + ", "total", "combined", "8,495"):  # 5.74 + 2755 would be 2,760.74
        assert summed not in page.lower()
    assert "2,760" not in page


def test_programme_screening_and_readiness_are_shown() -> None:
    page = format_carbon_results(ESTIMATE, MARKET, POLICY)
    assert "Programme screening" in page and "not an eligibility determination" in page
    assert "Carbon Credit Trading Scheme" in page
    assert "requires assessment" in page
    assert "Readiness score" in page and "not a probability of certification" in page
    assert "Tree diameter measurements" in page
    assert "1 verified, 1 pending verification, 1 assumptions" in page


def test_a_server_that_claims_certification_is_ignored_and_flagged() -> None:
    page = format_carbon_results({**ESTIMATE, "certified": True})
    assert "certified: false" in page
    assert "certified: true" not in page
    assert "treat every figure as an estimate" in page


def test_missing_market_and_policy_parts_say_why() -> None:
    page = format_carbon_results(ESTIMATE, None, None, "market failed", "policy failed")
    assert "not available (market failed)" in page
    assert "not available (policy failed)" in page
    assert DISCLAIMER in page


def test_the_demo_mode_banner_appears_only_in_demo_mode() -> None:
    demo = {**ESTIMATE, "provenance": {"mode": "demo"}}
    assert "demo mode" in format_carbon_results(demo)
    assert "demo mode" not in format_carbon_results(ESTIMATE)


def test_repository_samples_render_with_all_sections() -> None:
    page = format_carbon_results(
        sample("carbon-estimate"), sample("market-scenario"), sample("policy-eligibility")
    )
    assert DISCLAIMER in page and "certified: false" in page
    assert page.count("<h3>1 · ") == page.count("<h3>2 · ") == page.count("<h3>3 · ") == 1
    assert "not available" not in page.split("Other farm income")[0]  # estimate and prices present
    assert_no_active_markup(page)


def test_repository_samples_for_the_other_pages() -> None:
    plot_page = format_plot_page(sample("plot"), sample("analysis"))
    assert DISCLAIMER in plot_page and "PLT-" in plot_page
    inventory = sample("trees")["items"][0]
    inventory_page = format_inventory_page(inventory)
    assert DISCLAIMER in inventory_page and "Mango" in inventory_page


# --------------------------------------------------------------------------- other pages
def test_plot_page_has_the_banner_facts_and_next_step() -> None:
    page = format_plot_page(PLOT, notes=["The plot was created with source 'api'."])
    assert DISCLAIMER in page and "certified: false" in page
    for shown in ("PLT-1", "North field", "Karnataka", "3.80 ha", "9.40 acres", "private"):
        assert shown in page
    assert "source &#x27;api&#x27;" in page
    assert "Count trees from segmentation layer" in page


def test_plot_page_never_prints_coordinates() -> None:
    page = format_plot_page(PLOT)
    assert "77.1234567" not in page and "13.7654321" not in page


def test_plot_page_reports_a_failed_analysis_without_losing_the_plot() -> None:
    page = format_plot_page(PLOT, analysis_error="The server is busy.")
    assert "The plot was created, but the analysis failed" in page
    assert "The server is busy." in page and "PLT-1" in page


def test_inventory_page_explains_how_the_count_was_made() -> None:
    count = CrownCount(
        examined=120,
        invalid=1,
        outside=19,
        inside=100,
        counted=83,
        below_threshold=15,
        missing_confidence=2,
        threshold=0.5,
    )
    page = format_inventory_page(INVENTORY, count, "score", "Detected crowns")
    assert DISCLAIMER in page
    assert "model-estimated" in page and "Mango (Mangifera indica)" in page
    assert "How the count was made" in page and "Detected crowns" in page
    assert "score &gt;= 0.5" in page
    assert "check the count against the imagery" in page


def test_analysis_block_is_tolerant_and_has_no_carbon_values() -> None:
    page = format_analysis(sample("analysis"))
    assert "tCO" not in page
    assert "Land cover" in page


# --------------------------------------------------------------------------- agent transcript
def test_agent_transcript_shows_titles_kinds_text_and_tool_calls() -> None:
    page = format_agent_run(AGENT_RUN)
    assert "<b>Land analyst</b>" in page and "<b>Reviewer</b>" in page
    assert "finding" in page and "warning" in page
    assert "Tree cover is 12 percent.<br>Cropland dominates." in page
    for tool in ("get_landcover", "get_ndvi", "get_soil"):
        assert f"<code>{tool}</code>" in page
    for status in ("ok", "error", "skipped"):
        assert f"&nbsp;{status}&nbsp;" in page
    assert DISCLAIMER in page and "certified: false" in page
    assert "Full assessment" in page and "completed" in page
    assert "Estimated 5.7 tCO2e/yr (scenario)." in page
    assert "PASS" in page and "WARN" in page and "FAIL" in page
    assert "deterministic" in page
    assert "written by a language model" not in page


def test_agent_evidence_links_only_for_http_urls() -> None:
    page = format_agent_run(AGENT_RUN)
    assert '<a href="https://esa-worldcover.org">ESA WorldCover</a>' in page
    assert "javascript:" not in page
    assert "Bad link" in page  # shown as plain text


def test_agent_transcript_notes_when_a_language_model_wrote_part_of_it() -> None:
    run = {**AGENT_RUN, "reasoner": {"mode": "llm", "llm_enabled": True, "provider": "example"}}
    page = format_agent_run(run)
    assert "written by a language model" in page and "provider example" in page


def test_agent_transcript_escapes_model_written_text() -> None:
    run = {
        "messages": [{"agent_title": XSS, "kind": XSS, "text": XSS, "tool_calls": [{"tool": XSS}]}],
        "summary": {"headline": XSS},
        "guardrails": [{"id": XSS, "status": "pass", "detail": XSS}],
        "plan": {"title": XSS, "steps": [XSS]},
    }
    page = format_agent_run(run)
    assert_no_active_markup(page)
    assert "&lt;script&gt;" in page


def test_agent_run_with_no_messages_or_unknown_fields_still_renders() -> None:
    page = format_agent_run({"status": "failed", "mystery": {"a": 1}})
    assert "The server returned no messages." in page and DISCLAIMER in page
    assert "failed" in page


# --------------------------------------------------------------------------- escaping
def test_every_formatter_escapes_html_in_server_text() -> None:
    nasty = {key: XSS for key in ("name", "plot_id", "region", "country", "source", "privacy")}
    pages = [
        format_plot_page(nasty, {"landcover": {"classes": [{"name": XSS}]}}, XSS, [XSS]),
        format_inventory_page(
            {"species": {"common_name": XSS, "scientific_name": XSS}, "inventory_id": XSS},
            None,
            XSS,
            XSS,
        ),
        format_carbon_results(
            {**ESTIMATE, "estimate_id": XSS, "confidence": XSS, "notes": [XSS]},
            {**MARKET, "scenarios": [{"label": XSS, "price_per_tco2e": 1}], "currency_symbol": XSS},
            {"programmes": [{"name": XSS, "status": XSS, "notes": [XSS], "requirements": [XSS]}]},
            XSS,
            XSS,
        ),
    ]
    for page in pages:
        assert_no_active_markup(page)
        assert "&lt;script&gt;" in page


def test_links_are_escaped_and_restricted_to_http_and_https() -> None:
    assert safe_url("https://example.org/x") == "https://example.org/x"
    assert safe_url("HTTP://example.org") == "HTTP://example.org"
    for bad in ("javascript:alert(1)", "file:///etc/passwd", "ftp://x", "//x", "", None, 5):
        assert safe_url(bad) is None
    assert safe_url("https://a b") is None and safe_url("https://a<b") is None
    tricky = link("x", 'https://e.com/"onmouseover="alert(1)')
    assert 'href="https://e.com/&quot;onmouseover=&quot;alert(1)"' in tricky
    assert link("label", "javascript:alert(1)") == "label"


def test_esc_handles_none_and_non_strings() -> None:
    assert esc(None) == ""
    assert esc(5) == "5"
    assert esc("<&>\"'") == "&lt;&amp;&gt;&quot;&#x27;"


# --------------------------------------------------------------------------- robustness
JUNK_VALUES: list[Any] = [
    None,
    True,
    0,
    -1,
    3.5,
    math.nan,
    math.inf,
    "",
    "text",
    XSS,
    [],
    [1, "a", None],
    {},
    {"a": {"b": [1, 2]}},
    [[], {}, None],
]


@pytest.mark.parametrize("name", sorted(FORMATTERS))
@pytest.mark.parametrize("junk", JUNK_VALUES, ids=repr)
def test_formatters_never_raise_on_junk_input(name: str, junk: Any) -> None:
    result = FORMATTERS[name](junk)
    assert isinstance(result, str)
    if name != "analysis":  # the analysis is an HTML fragment, the others are full documents
        assert result.startswith("<html>")
    assert_no_active_markup(result)


def _random_json(rng: random.Random, depth: int = 0) -> Any:
    kind = rng.randrange(8 if depth < 3 else 5)
    if kind == 0:
        return None
    if kind == 1:
        return rng.choice([True, False])
    if kind == 2:
        return rng.choice([0, 1, -5, 12345678901, 0.5, -3.25, 1e300, math.nan, math.inf])
    if kind == 3:
        return rng.choice(["", "x", "<b>", XSS, "a" * 300, "line\nbreak", "ünï"])
    if kind == 4:
        return rng.choice(JUNK_VALUES)
    if kind == 5:
        return [_random_json(rng, depth + 1) for _ in range(rng.randrange(4))]
    keys = [
        "estimate",
        "low",
        "central",
        "high",
        "unit",
        "name",
        "label",
        "status",
        "scenarios",
        "programmes",
        "messages",
        "tool_calls",
        "evidence",
        "classes",
        "share",
        "readiness",
        "score",
        "present_evidence",
        "missing_evidence",
        "value_per_year",
        "species",
        "steps",
        "guardrails",
        "summary",
        "plan",
        "reasoner",
        "provenance",
        "sources",
        "url",
    ]
    return {rng.choice(keys): _random_json(rng, depth + 1) for _ in range(rng.randrange(6))}


@pytest.mark.parametrize("name", sorted(FORMATTERS))
def test_formatters_survive_random_nested_garbage(name: str) -> None:
    rng = random.Random(20261005)
    for _ in range(300):
        payload = _random_json(rng)
        result = FORMATTERS[name](payload)
        assert isinstance(result, str)
        assert_no_active_markup(result)


def test_every_results_page_is_a_complete_document_with_an_escaped_title() -> None:
    document = formatting.page("A <b> title", "<p>body</p>")
    assert document.startswith("<html><head><meta charset=")
    assert "<title>A &lt;b&gt; title</title>" in document


def test_colours_come_in_background_and_text_pairs_for_dark_themes() -> None:
    page = format_carbon_results(ESTIMATE, MARKET, POLICY) + format_agent_run(AGENT_RUN)
    for match in re.finditer(r'bgcolor="[^"]+"', page):
        assert "color:" in page[match.end() : match.end() + 80]
    for match in re.finditer(r'style="([^"]*background-color[^"]*)"', page):
        assert re.search(r"(?<!background-)color:", match.group(1))


# --------------------------------------------------------------------------- numbers
def test_number_formatting() -> None:
    assert fmt_num(1234567.891) == "1,234,567.89"
    assert fmt_num(2, 0) == "2"
    assert fmt_num(2.50, 2, trim=True) == "2.5"
    assert fmt_num(3.0, 2, trim=True) == "3"
    for missing in (None, "abc", True, math.nan, math.inf, [], {}):
        assert fmt_num(missing) == "not available"
    assert fmt_num("7.5") == "7.50"
    assert fmt_percent(0.123) == "12%"
    assert fmt_percent(None) == "not available"
    assert pretty_unit("tCO2e/yr") == "tCO₂e/yr"
    assert pretty_unit(None) == ""


# --------------------------------------------------------------------------- error text
def problem(status: int, slug: str = "", detail: str = "", **kwargs: Any) -> ApiProblem:
    type_ = f"https://x/problems/{slug}" if slug else None
    return ApiProblem(status, title=f"T{status}", detail=detail, type_=type_, **kwargs)


@pytest.mark.parametrize(
    ("exc", "context", "expected"),
    [
        (problem(401), None, "requires an API key"),
        (problem(403), None, "rejected the API key"),
        (problem(404, "plot-not-found"), None, "does not exist on the server"),
        (problem(404, "inventory-missing"), None, "no tree inventory yet"),
        (problem(404, "estimate-missing"), None, "no carbon estimate yet"),
        (problem(404), "agents", "does not offer the AI agent team"),
        (problem(405), "agents", "does not offer the AI agent team"),
        (problem(501), "agents", "does not offer the AI agent team"),
        (problem(404), None, "could not find what was requested"),
        (problem(404, "plot-not-found"), "agents", "does not exist on the server"),
        (problem(409, "pending-parameters"), None, "pending verification"),
        (problem(413), None, "too large"),
        (
            problem(422, "invalid-geometry", "Self-intersection."),
            None,
            "rejected the field polygon",
        ),
        (problem(422, "country-unresolved"), None, "which country"),
        (problem(422, "unsupported-country", "Country XX."), None, "does not support this country"),
        (problem(422, "unknown-species", "Unknown 'x'."), None, "does not know this species"),
        (problem(422, "", "Bad input."), None, "could not accept the data: Bad input."),
        (problem(429, retry_after=7), None, "about 7 seconds"),
        (problem(429), None, "rate limit"),
        (problem(501, "model-not-implemented", "No model."), None, "does not implement this yet"),
        (problem(500), None, "Try again later"),
        (problem(502, "upstream-unavailable"), None, "Try again later"),
        (problem(418, detail="teapot"), None, "teapot"),
        (ApiConfigError("The API base URL is empty."), None, "Settings"),
        (ApiConnectionError("No answer from x."), None, "No answer from x."),
        (ApiResponseError("odd answer"), None, "odd answer"),
        (GeometryError("multipart", "The selected feature has 2 parts."), None, "2 parts"),
        (ValueError("tree_count must be positive."), None, "tree_count must be positive."),
    ],
)
def test_error_descriptions_are_specific_and_actionable(
    exc: BaseException, context: str | None, expected: str
) -> None:
    assert expected in describe_error(exc, context)


def test_the_request_id_is_appended_when_the_server_gave_one() -> None:
    assert describe_error(problem(401, request_id="abc123")).endswith("(request id abc123)")


def test_the_message_of_an_unexpected_exception_is_not_shown() -> None:
    text = describe_error(RuntimeError("secret field 77.123456"))
    assert "Unexpected error (RuntimeError)" in text
    assert "secret" not in text and "77.123456" not in text


def test_describe_error_never_raises() -> None:
    class Weird(Exception):
        def __str__(self) -> str:
            raise RuntimeError("str() fails")

    assert "Unexpected error" in describe_error(Weird())


# --------------------------------------------------------------------------- small texts
def test_crown_count_summary_with_and_without_a_filter() -> None:
    plain = CrownCount(10, 0, 3, 7, 7, 0, 0, None)
    text = describe_crown_count(plain)
    assert "7 crown centroids inside the field (10 features examined)" in text
    assert "no confidence filter" in text
    filtered = CrownCount(120, 2, 18, 100, 80, 15, 5, 0.5)
    text = describe_crown_count(filtered, "score")
    assert "Counted: 80 with score >= 0.5" in text
    assert "Below the threshold: 15" in text and "(not counted): 5" in text
    assert "Skipped 2 features without a usable location" in text


def test_confidence_range_hint() -> None:
    assert describe_confidence_range(None, None, 0.5) == ""
    assert (
        describe_confidence_range(0.1, 0.99, 0.5) == "Values in this field range from 0.1 to 0.99."
    )
    percent = describe_confidence_range(12, 97.3, 0.5)
    assert "percentages" in percent and "50" in percent
    unreachable = describe_confidence_range(0.1, 0.8, 0.9)
    assert "nothing would be counted" in unreachable
    assert (
        describe_confidence_range(0.1, 0.8, None) == "Values in this field range from 0.1 to 0.8."
    )


def test_health_text() -> None:
    assert describe_health({"status": "ok", "version": "0.1.0", "mode": "live"}) == (
        "Connected: CarbonCreditBuy API 0.1.0, mode live."
    )
    assert "synthetic data" in describe_health({"version": "0.1.0", "mode": "demo"})
    assert "not with the usual health information" in describe_health(None)
    assert "not with the usual health information" in describe_health([])
