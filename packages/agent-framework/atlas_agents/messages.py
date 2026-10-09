"""What agents say: messages, tool calls and evidence.

An :class:`AgentMessage` is one line of the run transcript — the "who said
what" record. Everything here is plain data (dataclasses) that serialises to
the JSON shape in ``docs/architecture/api-contract.md`` (AgentRun → messages)::

    {"id": "M3", "step": 1, "agent": "land", "agent_title": "Land agent",
     "to": "team", "kind": "finding",
     "text": "Your plot is 2.13 ha in Karnataka, India. …",
     "facts": {"area_hectares": 2.13},
     "tool_calls": [{"tool": "measure_plot", "status": "ok", "duration_ms": 1,
                     "input": {"plot_id": "PLT-DEMOIN"}, "output": {…}}],
     "evidence": [{"label": "ESA WorldCover 2021", "source": "esa-worldcover", "url": "…"}],
     "confidence": null, "created_at": "2026-10-05T09:12:00Z"}

``text`` is for people, ``facts`` are for machines (and for the optional LLM,
after redaction), ``evidence`` says where the statement comes from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, get_args

MessageKind = Literal["plan", "finding", "warning", "handoff", "answer", "summary"]
ToolStatus = Literal["ok", "error", "skipped"]
Confidence = Literal["low", "medium", "high"]

MESSAGE_KINDS: tuple[str, ...] = get_args(MessageKind)
TOOL_STATUSES: tuple[str, ...] = get_args(ToolStatus)
CONFIDENCE_LEVELS: tuple[str, ...] = get_args(Confidence)

TEAM = "team"
"""The default address: a message for everyone (and for the person reading the run)."""


@dataclass(frozen=True)
class Evidence:
    """Where a statement comes from: a dataset, a methodology, a record or a document."""

    label: str
    source: str
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "source": self.source, "url": self.url}


@dataclass(frozen=True)
class ToolCall:
    """The transcript record of one tool use.

    ``input`` and ``output`` are short, *redacted* summaries made by
    :meth:`atlas_agents.tools.Tool.invoke` — never raw service payloads, never
    coordinates or geometry. When a tool is skipped or fails, ``output`` holds
    ``{"reason": "…"}``.
    """

    tool: str
    status: ToolStatus
    duration_ms: int
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in TOOL_STATUSES:
            raise ValueError(f"tool status must be one of {TOOL_STATUSES}, got {self.status!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "input": dict(self.input),
            "output": dict(self.output),
        }


@dataclass
class AgentMessage:
    """One message in the transcript.

    Agents do not build these by hand: they call ``ctx.say(...)``,
    ``ctx.warn(...)`` or ``ctx.handoff(...)`` on their
    :class:`~atlas_agents.agent.RunContext`, which fills in the author, the step,
    the time and the tool calls made since the agent's previous message. The
    orchestrator assigns ``id`` ("M1", "M2", …) when the message joins the
    transcript.
    """

    id: str
    step: int
    agent: str
    agent_title: str
    kind: MessageKind
    text: str
    to: str = TEAM
    facts: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    confidence: Confidence | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.kind not in MESSAGE_KINDS:
            raise ValueError(f"message kind must be one of {MESSAGE_KINDS}, got {self.kind!r}")
        if self.confidence is not None and self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"confidence must be one of {CONFIDENCE_LEVELS} or None, got {self.confidence!r}"
            )
        if not self.text or not self.text.strip():
            raise ValueError("a message needs non-empty text")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "step": self.step,
            "agent": self.agent,
            "agent_title": self.agent_title,
            "to": self.to,
            "kind": self.kind,
            "text": self.text,
            "facts": dict(self.facts),
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence,
            "created_at": self.created_at,
        }
