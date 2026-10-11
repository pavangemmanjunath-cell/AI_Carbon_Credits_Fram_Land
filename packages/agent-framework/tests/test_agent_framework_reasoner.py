"""Reasoners: templates by default; an LLM may only rephrase, and is checked when it does."""

from __future__ import annotations

import json
from collections.abc import Sequence

import httpx
import pytest

from carboncreditbuy_agents import (
    Agent,
    AgentMessage,
    Evidence,
    LLMReasoner,
    NarrationRequest,
    Orchestrator,
    Plan,
    PlanStep,
    RunContext,
    TemplateReasoner,
    review_rephrase,
)
from carboncreditbuy_agents.llm import ChatMessage, LLMError, OpenAICompatibleProvider
from carboncreditbuy_agents.reasoner import numbers_in, numbers_in_facts

TEMPLATE = "Estimated removal is 7.7–14.3 tCO₂e per year (central 11.0) using IPCC Tier 1."
FACTS = {"low": 7.71, "central": 11.02, "high": 14.32, "unit": "tCO2e/yr"}


class FakeProvider:
    """Records prompts and replies with a fixed answer (or raises)."""

    name = "fake/test-model"

    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.calls: list[Sequence[ChatMessage]] = []

    def complete(
        self, messages: Sequence[ChatMessage], *, max_tokens: int = 300, temperature: float = 0.0
    ) -> str:
        self.calls.append(messages)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def request(
    text: str = TEMPLATE, kind: str = "finding", facts: dict | None = None
) -> NarrationRequest:
    return NarrationRequest(
        agent="carbon",
        agent_title="Carbon agent",
        kind=kind,
        text=text,
        facts=FACTS if facts is None else facts,
        locale="en",
    )


def test_template_reasoner_keeps_the_text():
    reasoner = TemplateReasoner()
    narration = reasoner.narrate(request())
    assert narration.text == TEMPLATE and narration.source == "template"
    assert reasoner.mode == "template" and reasoner.provider is None and reasoner.report() is None


def test_numbers_are_compared_in_canonical_form():
    assert numbers_in("7.7–14.3 (central 11.0), ₹12,122, 0.630") == {
        "7.7",
        "14.3",
        "11",
        "12122",
        "0.63",
    }
    assert numbers_in_facts({"a": [1.50, {"b": "2026-10-05"}], "flag": True}) == {
        "1.5",
        "2026",
        "10",
        "5",
    }


def test_llm_rephrasing_with_the_same_numbers_is_used():
    provider = FakeProvider(
        "Your trees remove about 7.7–14.3 tCO₂e each year (central 11.0), by IPCC Tier 1."
    )
    reasoner = LLMReasoner(provider)
    narration = reasoner.narrate(request())
    assert narration.source == "llm" and narration.text.startswith("Your trees")
    assert reasoner.report().status == "pass"
    assert reasoner.provider == "fake/test-model"


@pytest.mark.parametrize(
    "answer,problem",
    [
        ("Your trees remove about 12 tCO₂e a year (7.7–14.3, IPCC Tier 1).", "new numbers"),
        ("Your trees remove about 11.0 tCO₂e a year with IPCC Tier 1.", "dropped numbers"),
        ("At 13.2923, 77.5384 trees remove 7.7–14.3 tCO₂e (central 11.0), Tier 1.", "new numbers"),
        (
            "These are certified carbon credits: 7.7–14.3 tCO₂e (central 11.0), Tier 1.",
            "credit claim",
        ),
        ("", "empty answer"),
    ],
)
def test_llm_text_with_other_numbers_or_claims_is_rejected(answer: str, problem: str):
    reasoner = LLMReasoner(FakeProvider(answer))
    narration = reasoner.narrate(request())
    assert narration.source == "template" and narration.text == TEMPLATE
    assert problem in str(narration.rejected_reason)
    report = reasoner.report()
    assert report.id == "llm-rephrase" and report.status == "warn" and problem in report.detail


def test_provider_failure_keeps_the_template_and_stops_calling():
    provider = FakeProvider(LLMError("timeout after 20 s"))
    reasoner = LLMReasoner(provider)
    first, second = reasoner.narrate(request()), reasoner.narrate(request())
    assert first.text == second.text == TEMPLATE
    assert len(provider.calls) == 1  # a dead endpoint costs one call per run, not one per message
    assert "provider error (LLMError)" in reasoner.report().detail


def test_only_findings_answers_and_summaries_are_sent():
    provider = FakeProvider("unused")
    reasoner = LLMReasoner(provider)
    for kind in ("plan", "warning", "handoff"):
        assert reasoner.narrate(request(kind=kind)).text == TEMPLATE
    assert provider.calls == []


def test_prompt_never_contains_coordinates_or_names():
    provider = FakeProvider(TEMPLATE)
    reasoner = LLMReasoner(provider)
    facts = {
        "area_hectares": 2.13,
        "lat": 13.292298,
        "centroid": {"lon": 77.538399},
        "name": "Ramesh",
    }
    reasoner.narrate(request(text="Plot near 13.2923, 77.5384 is 2.13 ha.", facts=facts))
    prompt = json.dumps([m.to_dict() for m in provider.calls[0]], ensure_ascii=False)
    for secret in ("13.29", "77.53", "Ramesh", '"lat"', "centroid"):
        assert secret not in prompt
    assert "2.13" in prompt and "Keep every number exactly" in prompt


def test_review_rephrase_lists_every_problem():
    assert review_rephrase(TEMPLATE, FACTS, TEMPLATE) == []
    # numbers that come from the facts (the engines) are allowed
    assert (
        review_rephrase(TEMPLATE, FACTS, "7.7–14.3 tCO₂e (central 11.0; 11.02 exactly), Tier 1.")
        == []
    )


# ----------------------------------------------------------------------------- end to end
class CarbonLike(Agent):
    id = "carbon"
    title = "Carbon agent"
    role = "Says a number."
    says = "A range."

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        return [
            ctx.say(
                "finding",
                TEMPLATE,
                facts=FACTS,
                evidence=[Evidence("IPCC", "ipcc")],
                disclaimer="This is an estimate, not a carbon credit.",
            ),
            ctx.warn("Two parameters are pending."),
        ]


def test_disclaimer_is_pinned_after_narration_and_never_sent_to_the_llm():
    provider = FakeProvider("About 7.7–14.3 tCO₂e per year (central 11.0) with IPCC Tier 1.")
    result = Orchestrator([CarbonLike()]).run(
        Plan("p", "P", (PlanStep("carbon"),)), inputs={}, reasoner=LLMReasoner(provider)
    )
    finding, warning = result.messages
    assert finding.text.endswith("This is an estimate, not a carbon credit.")
    assert finding.text.startswith("About 7.7–14.3")
    assert "not a carbon credit" not in json.dumps([m.to_dict() for m in provider.calls[0]])
    assert warning.text == "Two parameters are pending."  # warnings are never reworded
    assert result.guardrails[-1].id == "llm-rephrase" and result.guardrails[-1].status == "pass"
    assert result.to_dict()["reasoner"] == {
        "mode": "llm",
        "llm_enabled": True,
        "provider": "fake/test-model",
    }


def test_rejected_llm_text_makes_the_run_warn():
    provider = FakeProvider("About 99 tCO₂e per year.")
    result = Orchestrator([CarbonLike()]).run(
        Plan("p", "P", (PlanStep("carbon"),)), inputs={}, reasoner=LLMReasoner(provider)
    )
    assert result.messages[0].text.startswith(TEMPLATE)
    assert result.guardrails[-1].status == "warn" and result.status == "completed-with-warnings"


# ----------------------------------------------------------------------------- HTTP client
def _provider(handler, api_key: str = "") -> OpenAICompatibleProvider:  # type: ignore[no-untyped-def]
    return OpenAICompatibleProvider(
        "http://llm.test/v1",
        "tiny-model",
        api_key=api_key,
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )


def test_openai_compatible_client_posts_chat_completions():
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["auth"] = req.headers.get("authorization")
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": " Hello farmer. "}}]})

    provider = _provider(handler, api_key="secret")
    assert provider.complete([ChatMessage("user", "hi")]) == "Hello farmer."
    assert seen["url"] == "http://llm.test/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "tiny-model" and seen["body"]["temperature"] == 0.0
    assert seen["body"]["messages"] == [{"role": "user", "content": "hi"}]
    assert provider.name == "openai-compatible/tiny-model"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="oops"),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": "  "}}]}),
    ],
)
def test_openai_compatible_client_raises_llm_error_on_bad_responses(response: httpx.Response):
    with pytest.raises(LLMError):
        _provider(lambda req: response).complete([ChatMessage("user", "hi")])


def test_openai_compatible_client_turns_timeouts_into_llm_errors():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(LLMError, match="timeout"):
        _provider(handler).complete([ChatMessage("user", "hi")])


def test_client_is_off_unless_fully_configured():
    build = OpenAICompatibleProvider.from_settings
    assert build(reasoner="template", base_url="http://x/v1", model="m") is None
    assert build(reasoner="llm", base_url="", model="m") is None
    assert build(reasoner="llm", base_url="http://x/v1", model="") is None
    assert isinstance(
        build(reasoner="LLM", base_url="http://x/v1", model="m"), OpenAICompatibleProvider
    )
