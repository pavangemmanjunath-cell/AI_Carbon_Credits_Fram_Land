"""Guardrails: deterministic checks over a finished run.

A guardrail looks at the transcript and the blackboard after the last step and
answers one question with ``pass``, ``warn`` or ``fail`` plus a plain-language
``detail``. Guardrails never change numbers; they make problems visible (and a
``fail`` marks the whole run as ``failed``).

The checks below are *pure functions over plain data*, so they are easy to
unit-test and reuse. The host application wires them to its own blackboard
keys with :class:`Guardrail`::

    Guardrail("pending-parameters",
              lambda run: check_pending_parameters(run.board.get("estimate", {}).get("parameters")))

Ids used by CarbonCreditBuy (docs/architecture/api-contract.md, AgentRun):
``not-a-credit``, ``uncertainty-present``, ``provenance-present``,
``no-coordinates``, ``pending-parameters``, ``values-separated`` — plus
``llm-rephrase`` when the optional LLM reasoner is on.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, get_args

from carboncreditbuy_agents.blackboard import Blackboard
from carboncreditbuy_agents.llm.redaction import (
    find_coordinates,
    is_sensitive_key,
    looks_like_position,
)
from carboncreditbuy_agents.messages import CONFIDENCE_LEVELS, AgentMessage

GuardrailStatus = Literal["pass", "warn", "fail"]
GUARDRAIL_STATUSES: tuple[str, ...] = get_args(GuardrailStatus)


@dataclass(frozen=True)
class GuardrailResult:
    id: str
    status: GuardrailStatus
    detail: str

    def __post_init__(self) -> None:
        if self.status not in GUARDRAIL_STATUSES:
            raise ValueError(f"guardrail status must be one of {GUARDRAIL_STATUSES}")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class GuardrailInput:
    """What a guardrail may look at: the finished transcript and the blackboard."""

    messages: Sequence[AgentMessage]
    board: Blackboard


@dataclass(frozen=True)
class Guardrail:
    """A named check. :meth:`run` never raises — a crashing check counts as ``fail``."""

    id: str
    check: Callable[[GuardrailInput], GuardrailResult]

    def run(self, data: GuardrailInput) -> GuardrailResult:
        try:
            result = self.check(data)
        except Exception as exc:  # a broken check must not hide a problem
            return GuardrailResult(
                self.id, "fail", f"The check itself failed ({type(exc).__name__})."
            )
        if result.id != self.id:
            return GuardrailResult(self.id, result.status, result.detail)
        return result


# ----------------------------------------------------------------------------- helpers
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_NEGATION_BEFORE = re.compile(
    r"\b(not|no|never|nor|without|isn't|aren't|cannot)\b[^.]{0,40}$", re.I
)
_CREDIT_CLAIMS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:issued|certified|verified)\s+(?:carbon\s+|green\s+)?credits?\b", re.I),
    re.compile(r"\b(?:is|are)\s+(?:now\s+)?certified\b", re.I),
    re.compile(r"\bguaranteed\s+(?:revenue|income|payment|payout|price)s?\b", re.I),
    re.compile(
        r"\byou\s+(?:will|are\s+going\s+to)\s+(?:earn|receive|get)\b[^.]*\bcredits?\b", re.I
    ),
)
_CURRENCY_AMOUNT = re.compile(
    r"(?:[₹$€£]\s?\d|\b(?:INR|USD|EUR|GBP)\s?\d|\d[\d,.]*\s?(?:INR|USD|EUR|GBP|rupees?|dollars?|euros?)\b)",
    re.I,
)
_SUM_WORDS = re.compile(
    r"\b(?:total|totals|combined|altogether|in\s+all|sum|summed|plus|adds?\s+up\s+to)\b", re.I
)
_SUM_FACT_KEY = re.compile(r"(?:total|combined|sum).*(?:value|income|revenue|benefit)", re.I)


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT.split(text.strip()) if s]


def _as_sentence(parts: list[str]) -> str:
    """Join problem fragments into one sentence with a capital first letter."""
    text = "; ".join(parts)
    return (text[:1].upper() + text[1:] + ".") if text else ""


def credit_claims(text: str) -> list[str]:
    """Affirmative claims that an estimate is a credit / certified / guaranteed.

    A claim preceded by a negation in the same sentence ("not an issued carbon
    credit", "not guaranteed revenue") is fine and is not returned.
    """
    found: list[str] = []
    for pattern in _CREDIT_CLAIMS:
        for match in pattern.finditer(text):
            before = text[: match.start()]
            sentence_start = max(before.rfind("."), before.rfind("!"), before.rfind("?"))
            if not _NEGATION_BEFORE.search(before[sentence_start + 1 :]):
                found.append(match.group(0))
    return found


def _walk(value: Any, path: str) -> Iterable[tuple[str, Any, Any]]:
    """Yield (path, key, value) for every node of a JSON-like structure."""
    if isinstance(value, Mapping):
        for key, inner in value.items():
            child = f"{path}.{key}" if path else str(key)
            yield child, key, inner
            yield from _walk(inner, child)
    elif isinstance(value, (list, tuple)):
        for index, inner in enumerate(value):
            child = f"{path}[{index}]"
            yield child, None, inner
            yield from _walk(inner, child)


def location_leaks(value: Any, path: str) -> list[str]:
    """Paths inside ``value`` that hold a sensitive key, a position or coordinate text."""
    leaks: list[str] = []
    for child, key, inner in _walk(value, path):
        if key is not None and is_sensitive_key(key):
            leaks.append(child)
        elif looks_like_position(inner):
            leaks.append(child)
        elif isinstance(inner, str) and find_coordinates(inner):
            leaks.append(child)
    return leaks


# ----------------------------------------------------------------------------- checks
def check_not_a_credit(
    texts: Iterable[str],
    records: Iterable[tuple[str, Mapping[str, Any] | None]],
    *,
    run_certified: bool,
    disclaimer: str | None,
) -> GuardrailResult:
    """Nothing is presented as a credit: ``certified`` is false everywhere, a
    disclaimer exists and no sentence claims issuance, certification or guaranteed money."""
    problems: list[str] = []
    checked: list[str] = []
    if run_certified:
        problems.append("the run is marked certified")
    if not (disclaimer or "").strip():
        problems.append("the run has no disclaimer")
    for label, record in records:
        if record is None:
            continue
        checked.append(label)
        if record.get("certified") is not False:
            problems.append(f"{label} is not marked certified: false")
    claims = [claim for text in texts for claim in credit_claims(text)]
    if claims:
        problems.append(f"{len(claims)} sentence(s) present an estimate as a credit or a guarantee")
    if problems:
        return GuardrailResult("not-a-credit", "fail", _as_sentence(problems))
    scope = f" and on {', '.join(checked)}" if checked else ""
    return GuardrailResult(
        "not-a-credit",
        "pass",
        f"certified: false on the run{scope}; a disclaimer is attached and no message presents "
        "an estimate as a credit, a certification or guaranteed income.",
    )


def check_uncertainty(
    ranges: Iterable[tuple[str, Mapping[str, Any] | None]],
    confidences: Iterable[tuple[str, str | None]] = (),
) -> GuardrailResult:
    """Every carbon number is a low/central/high range with a unit, and carries a confidence."""
    problems: list[str] = []
    seen: list[str] = []
    for label, rng in ranges:
        if rng is None:
            continue
        seen.append(label)
        values: list[Any] = [rng.get(k) for k in ("low", "central", "high")]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            problems.append(f"{label} lacks a numeric low/central/high")
            continue
        low, central, high = (float(v) for v in values)
        if not low <= central <= high:
            problems.append(f"{label} is not ordered low ≤ central ≤ high")
        if not rng.get("unit"):
            problems.append(f"{label} has no unit")
    for label, confidence in confidences:
        if confidence not in CONFIDENCE_LEVELS:
            problems.append(f"{label} has no confidence grade")
    if problems:
        return GuardrailResult("uncertainty-present", "fail", _as_sentence(problems))
    if not seen:
        return GuardrailResult(
            "uncertainty-present", "pass", "No carbon numbers were produced in this run."
        )
    return GuardrailResult(
        "uncertainty-present",
        "pass",
        f"{len(seen)} carbon range(s) ({', '.join(seen)}) have low ≤ central ≤ high, a unit and "
        "a confidence grade.",
    )


def check_provenance(
    messages: Sequence[AgentMessage],
    records: Iterable[tuple[str, Mapping[str, Any] | None]] = (),
    *,
    kinds: tuple[str, ...] = ("finding", "answer"),
) -> GuardrailResult:
    """Findings and answers cite evidence; result records carry their sources."""
    bare = [m.id or f"step {m.step}" for m in messages if m.kind in kinds and not m.evidence]
    unsourced: list[str] = []
    checked = 0
    for label, record in records:
        if record is None:
            continue
        checked += 1
        if not (record.get("sources") or record.get("provenance")):
            unsourced.append(label)
    problems = []
    if bare:
        problems.append(f"message(s) without evidence: {', '.join(bare)}")
    if unsourced:
        problems.append(f"record(s) without sources: {', '.join(unsourced)}")
    if problems:
        return GuardrailResult("provenance-present", "fail", _as_sentence(problems))
    cited = sum(1 for m in messages if m.kind in kinds)
    return GuardrailResult(
        "provenance-present",
        "pass",
        f"All {cited} findings and answers cite evidence; {checked} result record(s) carry "
        "their sources.",
    )


def check_no_coordinates(
    messages: Sequence[AgentMessage], *, sensitive_strings: Iterable[str] = ()
) -> GuardrailResult:
    """No coordinates, geometry or exact plot location in texts, facts or tool summaries.

    ``sensitive_strings`` are exact forms of this plot's own coordinates (see
    :func:`carboncreditbuy_agents.llm.redaction.sensitive_number_strings`). The detail
    names *where* something was found, never the value.
    """
    exact = [s for s in sensitive_strings if s]
    leaks: list[str] = []
    for message in messages:
        ref = message.id or f"step {message.step}"
        if find_coordinates(message.text):
            leaks.append(f"{ref} text")
        leaks.extend(f"{ref} {p}" for p in location_leaks(message.facts, "facts"))
        for index, call in enumerate(message.tool_calls):
            leaks.extend(f"{ref} {p}" for p in location_leaks(call.input, f"tool[{index}].input"))
            leaks.extend(f"{ref} {p}" for p in location_leaks(call.output, f"tool[{index}].output"))
        if exact:
            blob = json.dumps(message.to_dict(), ensure_ascii=False)
            if any(s in blob for s in exact):
                leaks.append(f"{ref} (exact plot coordinates)")
    if leaks:
        return GuardrailResult(
            "no-coordinates",
            "fail",
            f"Location data found in {len(leaks)} place(s): {', '.join(sorted(set(leaks))[:8])}.",
        )
    return GuardrailResult(
        "no-coordinates",
        "pass",
        f"No coordinates, geometry or exact plot location in {len(messages)} messages, their "
        "facts or tool summaries.",
    )


def _parameter_label(parameter: Mapping[str, Any]) -> str:
    return str(parameter.get("parameter") or parameter.get("name") or "?")


def check_pending_parameters(parameters: Iterable[Mapping[str, Any]] | None) -> GuardrailResult:
    """Flag parameters whose ``verification_status`` is still ``pending``.

    ``warn``, not ``fail``: pending values are allowed outside production, but
    a reader must know (CLAUDE.md principle 10).
    """
    if parameters is None:
        return GuardrailResult(
            "pending-parameters", "pass", "No carbon parameters were used in this run."
        )
    items = list(parameters)
    pending = sorted(
        {_parameter_label(p) for p in items if p.get("verification_status") == "pending"}
    )
    if pending:
        return GuardrailResult(
            "pending-parameters",
            "warn",
            f"{len(pending)} parameter(s) still pending verification: {', '.join(pending)}. "
            "Production mode refuses estimates that use them.",
        )
    return GuardrailResult(
        "pending-parameters",
        "pass",
        f"All {len(items)} parameters are verified or documented assumptions.",
    )


def check_values_separated(messages: Sequence[AgentMessage]) -> GuardrailResult:
    """Environmental benefit, indicative value and other income are never added up.

    Fails when a sentence pairs a money amount with a summing word ("total",
    "combined", "plus" …) or when a fact key looks like a combined value.
    """
    offenders: list[str] = []
    for message in messages:
        ref = message.id or f"step {message.step}"
        for sentence in sentences(message.text):
            if _CURRENCY_AMOUNT.search(sentence) and _SUM_WORDS.search(sentence):
                offenders.append(f"{ref} text")
                break
        for path, key, _ in _walk(message.facts, "facts"):
            if key is not None and _SUM_FACT_KEY.search(str(key)):
                offenders.append(f"{ref} {path}")
    if offenders:
        return GuardrailResult(
            "values-separated",
            "fail",
            f"Values look summed in: {', '.join(offenders)}. Environmental benefit, indicative "
            "value and other farm income must stay separate.",
        )
    return GuardrailResult(
        "values-separated",
        "pass",
        "Environmental benefit, indicative carbon value and other farm income are reported "
        "separately; no message adds them up.",
    )
