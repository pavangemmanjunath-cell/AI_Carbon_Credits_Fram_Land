"""Reasoners: how an agent's template text becomes the message people read.

Every agent writes its message as a **deterministic template** filled from
facts that came out of the engines ("Estimated removal is 7.7–14.3 tCO₂e per
year (central 11.0) …"). A reasoner then decides the final wording:

* :class:`TemplateReasoner` (the default) keeps the template exactly. No
  network, no model, same input → same text.
* :class:`LLMReasoner` (opt-in) asks a language model to *rephrase* the
  template — friendlier wording, another language — and then **checks** the
  answer before using it. The template is kept, and a guardrail warning is
  recorded, when the model fails, times out, or its text

  - contains a number that is not in the template or the facts,
  - drops a number that the template had (ranges must survive),
  - contains coordinate-like text, or
  - presents an estimate as a credit, a certification or guaranteed income.

Numbers therefore always come from the engines, never from the LLM
(CLAUDE.md principle 12). The LLM only ever sees the template text and the
facts after :func:`~carboncreditbuy_agents.llm.redaction.redact` — no coordinates,
geometry or names (principle 11).

Safety sentences such as "This is an estimate, not a carbon credit." are not
part of the template at all: agents pass them as ``disclaimer=`` and the
context appends them *after* narration, verbatim.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol, runtime_checkable

from carboncreditbuy_agents.guardrails import GuardrailResult, credit_claims
from carboncreditbuy_agents.llm.base import ChatMessage, LLMProvider
from carboncreditbuy_agents.llm.redaction import find_coordinates, redact, redact_text

REPHRASED_KINDS: tuple[str, ...] = ("finding", "answer", "summary")
"""Message kinds an LLM may rephrase. Plans, hand-offs and warnings stay verbatim."""


@dataclass(frozen=True)
class NarrationRequest:
    """Everything a reasoner may use to word one message."""

    agent: str
    agent_title: str
    kind: str
    text: str
    facts: Mapping[str, Any]
    locale: str = "en"


@dataclass(frozen=True)
class Narration:
    """The final wording and where it came from."""

    text: str
    source: Literal["template", "llm"]
    rejected_reason: str | None = None


@runtime_checkable
class Reasoner(Protocol):
    """Anything that can word a message: ``narrate`` it, then ``report`` on the run."""

    @property
    def mode(self) -> str:
        """``"template"`` or ``"llm"``."""
        ...

    @property
    def provider(self) -> str | None:
        """Which model answered (``None`` for templates)."""
        ...

    def narrate(self, request: NarrationRequest) -> Narration: ...

    def report(self) -> GuardrailResult | None:
        """A guardrail result describing this reasoner's run, or ``None``."""
        ...


class TemplateReasoner:
    """Keep the agent's deterministic template text, unchanged."""

    mode = "template"
    provider: str | None = None

    def narrate(self, request: NarrationRequest) -> Narration:
        return Narration(text=request.text, source="template")

    def report(self) -> GuardrailResult | None:
        return None


# ----------------------------------------------------------------------------- number checks
_NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def _canonical(token: str) -> str | None:
    """``"11.0"`` → ``"11"``, ``"12,122"`` → ``"12122"``, ``"0.630"`` → ``"0.63"``."""
    try:
        value = Decimal(token.replace(",", ""))
    except InvalidOperation:
        return None
    return format(value.normalize(), "f")


def numbers_in(text: str) -> set[str]:
    """Canonical forms of every number written in ``text`` (signs are ignored)."""
    found = (_canonical(token) for token in _NUMBER.findall(text))
    return {n for n in found if n is not None}


def numbers_in_facts(facts: Any) -> set[str]:
    """Canonical forms of every number inside a JSON-like ``facts`` structure."""
    found: set[str] = set()
    if isinstance(facts, bool) or facts is None:
        return found
    if isinstance(facts, (int, float)):
        canonical = _canonical(repr(abs(facts)))
        return {canonical} if canonical else found
    if isinstance(facts, str):
        return numbers_in(facts)
    if isinstance(facts, Mapping):
        values: Iterable[Any] = facts.values()
    elif isinstance(facts, (list, tuple, set)):
        values = facts
    else:
        return found
    for value in values:
        found |= numbers_in_facts(value)
    return found


def review_rephrase(template: str, facts: Mapping[str, Any], output: str) -> list[str]:
    """Problems that make an LLM rephrasing unusable (empty list = acceptable).

    Problems are described by category only; offending values are never echoed
    (they could be coordinates).
    """
    problems: list[str] = []
    if not output.strip():
        return ["empty answer"]
    template_numbers = numbers_in(template)
    output_numbers = numbers_in(output)
    if output_numbers - (template_numbers | numbers_in_facts(facts)):
        problems.append("new numbers")
    if template_numbers - output_numbers:
        problems.append("dropped numbers")
    if find_coordinates(output):
        problems.append("coordinate-like text")
    if credit_claims(output):
        problems.append("credit claim")
    if len(output) > max(400, 3 * len(template)):
        problems.append("too long")
    return problems


SYSTEM_PROMPT = (
    "You rewrite short status messages written by a team of software agents for a farmer.\n"
    "Rules:\n"
    "1. Keep every number exactly as written in the message: same digits, same decimals, "
    "same units. Do not round, convert or recompute anything.\n"
    "2. Do not add any number, place, date, name, fact, advice or promise that is not in "
    "the message.\n"
    "3. Never say or imply that an estimate is a carbon credit, is certified, or guarantees "
    "income.\n"
    "4. Use plain, friendly words and short sentences. Answer in the language with code "
    "'{locale}'.\n"
    "5. Reply with the rewritten message only."
)


class LLMReasoner:
    """Rephrase templates with an LLM, but only keep answers that pass the checks.

    One instance serves one run: it counts accepted and rejected rephrasings
    for :meth:`report`, and after ``max_failures`` provider errors it stops
    calling the model for the rest of the run (a dead endpoint costs one
    timeout, not one per message).
    """

    mode = "llm"

    def __init__(
        self,
        provider: LLMProvider,
        *,
        kinds: tuple[str, ...] = REPHRASED_KINDS,
        max_failures: int = 1,
        max_tokens: int = 300,
    ) -> None:
        self._provider = provider
        self.kinds = kinds
        self.max_failures = max_failures
        self.max_tokens = max_tokens
        self.accepted = 0
        self._rejections: Counter[str] = Counter()
        self._failures = 0

    @property
    def provider(self) -> str | None:
        return getattr(self._provider, "name", type(self._provider).__name__)

    def build_messages(self, request: NarrationRequest) -> list[ChatMessage]:
        """The exact prompt sent to the model — template text and facts, redacted."""
        payload = {
            "agent": request.agent_title,
            "kind": request.kind,
            "message": redact_text(request.text),
            "facts": redact(dict(request.facts)),
        }
        return [
            ChatMessage("system", SYSTEM_PROMPT.format(locale=request.locale)),
            ChatMessage("user", json.dumps(payload, ensure_ascii=False, default=str)),
        ]

    def _keep_template(self, request: NarrationRequest, reason: str) -> Narration:
        self._rejections[reason] += 1
        return Narration(text=request.text, source="template", rejected_reason=reason)

    def narrate(self, request: NarrationRequest) -> Narration:
        if request.kind not in self.kinds:
            return Narration(text=request.text, source="template")
        if self._failures >= self.max_failures:
            return self._keep_template(request, "LLM unavailable earlier in this run")
        try:
            answer = self._provider.complete(
                self.build_messages(request), max_tokens=self.max_tokens, temperature=0.0
            )
        except Exception as exc:  # timeouts, HTTP errors, anything: keep the template
            self._failures += 1
            return self._keep_template(request, f"provider error ({type(exc).__name__})")
        answer = (answer or "").strip()
        # Check against what the model was allowed to see (redacted facts).
        problems = review_rephrase(request.text, redact(dict(request.facts)), answer)
        if problems:
            return self._keep_template(request, ", ".join(problems))
        self.accepted += 1
        return Narration(text=answer, source="llm")

    def report(self) -> GuardrailResult:
        rejected = sum(self._rejections.values())
        attempts = self.accepted + rejected
        if attempts == 0:
            return GuardrailResult(
                "llm-rephrase", "pass", "The LLM reasoner was on; no message needed rephrasing."
            )
        if rejected == 0:
            return GuardrailResult(
                "llm-rephrase",
                "pass",
                f"{self.accepted} message(s) rephrased by {self.provider}; every number matched "
                "the template and the engines' facts.",
            )
        reasons = "; ".join(f"{reason} ×{count}" for reason, count in self._rejections.items())
        return GuardrailResult(
            "llm-rephrase",
            "warn",
            f"{rejected} of {attempts} rephrasing(s) were rejected ({reasons}); the "
            "deterministic template text was kept for those messages.",
        )
