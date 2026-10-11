"""Agents, and the context they work in.

An **agent** here is a small, named piece of code with one job. It declares:

* ``id`` / ``title`` — who it is ("carbon" / "Carbon agent");
* ``role`` — its job in one sentence;
* ``says`` — what it reports, in one sentence (shown in the catalog);
* ``tools`` — the tools it may use (nothing else);
* ``reads`` / ``writes`` — the blackboard keys it may read and write.

and implements one method, ``run(ctx) -> list[AgentMessage]``.

There is no hidden prompt and no model deciding what to do: the agent's
``run`` method *is* its policy, written in Python and covered by tests. An
LLM, when switched on, only rewords the messages afterwards (see
:mod:`carboncreditbuy_agents.reasoner`).

A minimal agent::

    class GreeterAgent(Agent):
        id = "greeter"
        title = "Greeter"
        role = "Says hello."
        says = "A greeting with the plot id."
        tools = ()
        reads = ("plot_id",)
        writes = ("greeted",)

        def run(self, ctx: RunContext) -> list[AgentMessage]:
            plot_id = ctx.read("plot_id")
            ctx.write("greeted", True)
            return [ctx.say("finding", f"Hello, plot {plot_id}!",
                            evidence=[Evidence("Request", "request")])]
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from carboncreditbuy_agents.blackboard import Blackboard, BlackboardAccessError, allowed
from carboncreditbuy_agents.llm.redaction import redact, redact_text
from carboncreditbuy_agents.messages import (
    TEAM,
    AgentMessage,
    Confidence,
    Evidence,
    MessageKind,
    ToolCall,
)
from carboncreditbuy_agents.plan import Plan
from carboncreditbuy_agents.reasoner import NarrationRequest, Reasoner
from carboncreditbuy_agents.tools import Tool, ToolResult
from carboncreditbuy_agents.trace import RunTrace, StepRecord, utc_now_iso


class ToolNotAllowed(PermissionError):
    """An agent tried to use a tool it did not declare in ``tools``."""


class Agent:
    """Base class for one member of the team (subclass it; see the module docstring)."""

    id: ClassVar[str] = ""
    title: ClassVar[str] = ""
    role: ClassVar[str] = ""
    says: ClassVar[str] = ""
    tools: ClassVar[tuple[Tool, ...]] = ()
    reads: ClassVar[tuple[str, ...]] = ()
    writes: ClassVar[tuple[str, ...]] = ()

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        raise NotImplementedError(f"{type(self).__name__}.run() is not implemented")

    def tool(self, name: str) -> Tool | None:
        """The declared tool called ``name`` (``None`` when not declared)."""
        return next((t for t in self.tools if t.name == name), None)

    def card(self) -> dict[str, Any]:
        """Catalog entry (contract shape used by ``GET /agents``)."""
        return {
            "id": self.id,
            "title": self.title,
            "role": self.role,
            "says": self.says,
            "tools": [t.card() for t in self.tools],
            "reads": list(self.reads),
            "writes": list(self.writes),
        }


@dataclass
class RunContext:
    """Everything one agent may touch during its step — and nothing more.

    The orchestrator creates a fresh context for every step. It enforces the
    agent's declared ``reads``, ``writes`` and ``tools``, records tool calls,
    and turns text into :class:`AgentMessage` objects through the reasoner.
    """

    run_id: str
    plan: Plan
    step: int
    agent: Agent
    board: Blackboard
    reasoner: Reasoner
    deps: Any = None
    locale: str = "en"
    trace: RunTrace | None = None
    clock: Callable[[], str] = utc_now_iso
    progress: tuple[StepRecord, ...] = ()
    """Records of the steps that ran before this one (status and summary), read-only."""
    summary: str | None = None
    """Optional one-line step summary for the trace (defaults to the first sentence said)."""
    _pending_calls: list[ToolCall] = field(default_factory=list, repr=False)

    # -- the plan ------------------------------------------------------------------
    @property
    def is_first_step(self) -> bool:
        return self.step == 0

    @property
    def is_last_step(self) -> bool:
        return self.step == len(self.plan.steps) - 1

    @property
    def later_agents(self) -> list[str]:
        """Agent ids still to run after this step (in plan order)."""
        return [s.agent for s in self.plan.steps[self.step + 1 :]]

    # -- the blackboard ----------------------------------------------------------------
    def _check_read(self, key: str) -> None:
        if not allowed(key, self.agent.reads):
            raise BlackboardAccessError(
                f"{self.agent.id} may not read {key!r}; add it to {type(self.agent).__name__}.reads"
            )

    def read(self, key: str, default: Any = None) -> Any:
        """Read a declared key (``default`` when nobody wrote it)."""
        self._check_read(key)
        return self.board.get(key, default)

    def has(self, key: str) -> bool:
        """True when a declared key holds a value."""
        self._check_read(key)
        return self.board.has(key)

    def write(self, key: str, value: Any) -> None:
        """Write a declared key; the board logs that this agent wrote it in this step."""
        if not allowed(key, self.agent.writes):
            raise BlackboardAccessError(
                f"{self.agent.id} may not write {key!r}; add it to "
                f"{type(self.agent).__name__}.writes"
            )
        self.board.write(key, value, agent=self.agent.id, step=self.step)

    # -- tools ---------------------------------------------------------------------------
    def use(self, tool: Tool | str, /, **kwargs: Any) -> ToolResult:
        """Call one of the agent's declared tools and record the call.

        Never raises for tool failures: check ``result.ok`` / ``result.status``.
        Raises :class:`ToolNotAllowed` when the tool was not declared (a bug).
        """
        name = tool if isinstance(tool, str) else tool.name
        declared = self.agent.tool(name)
        if declared is None:
            raise ToolNotAllowed(
                f"{self.agent.id} may not use {name!r}; add it to {type(self.agent).__name__}.tools"
            )
        result, call = declared.invoke(self.deps, **kwargs)
        self._pending_calls.append(call)
        if self.trace is not None:
            self.trace.event(
                "tool",
                f"{name}: {call.status} ({call.duration_ms} ms)",
                step=self.step,
                agent=self.agent.id,
            )
        return result

    def take_tool_calls(self) -> list[ToolCall]:
        """Tool calls made since the last message (and forget them)."""
        calls, self._pending_calls = self._pending_calls, []
        return calls

    # -- messages ------------------------------------------------------------------------
    def say(
        self,
        kind: MessageKind,
        text: str,
        *,
        facts: Mapping[str, Any] | None = None,
        evidence: Iterable[Evidence] = (),
        confidence: Confidence | None = None,
        to: str = TEAM,
        disclaimer: str | None = None,
    ) -> AgentMessage:
        """Turn template text into a message.

        * ``text`` is the deterministic template; the reasoner may reword it.
        * ``disclaimer`` is appended verbatim *after* narration — use it for
          sentences that must never be reworded ("not a carbon credit").
        * ``facts`` are redacted (no location or identity keys) before they are
          stored or shown to any reasoner.
        * Tool calls made since the previous message are attached to this one.
        """
        clean_facts = redact(dict(facts or {}))
        narration = self.reasoner.narrate(
            NarrationRequest(
                agent=self.agent.id,
                agent_title=self.agent.title,
                kind=kind,
                text=text,
                facts=clean_facts,
                locale=self.locale,
            )
        )
        final = narration.text.strip()
        if disclaimer:
            final = f"{final} {disclaimer.strip()}"
        message = AgentMessage(
            id="",
            step=self.step,
            agent=self.agent.id,
            agent_title=self.agent.title,
            kind=kind,
            text=redact_text(final),
            to=to,
            facts=clean_facts,
            tool_calls=self.take_tool_calls(),
            evidence=_unique(evidence),
            confidence=confidence,
            created_at=self.clock(),
        )
        if self.trace is not None:
            self.trace.event(
                "message",
                f"{kind} → {to} ({narration.source})",
                step=self.step,
                agent=self.agent.id,
            )
        return message

    def warn(
        self,
        text: str,
        *,
        facts: Mapping[str, Any] | None = None,
        evidence: Iterable[Evidence] = (),
        to: str = TEAM,
    ) -> AgentMessage:
        """A ``warning`` message: something is missing or went wrong (never reworded)."""
        return self.say("warning", text, facts=facts, evidence=evidence, to=to)

    def handoff(
        self, to: str, text: str, *, facts: Mapping[str, Any] | None = None
    ) -> AgentMessage:
        """A ``handoff`` message addressed to another agent (by id)."""
        return self.say("handoff", text, facts=facts, to=to)


def _unique(evidence: Iterable[Evidence]) -> list[Evidence]:
    """Drop repeated evidence items while keeping their order."""
    seen: set[tuple[str, str, str | None]] = set()
    out: list[Evidence] = []
    for item in evidence:
        key = (item.label, item.source, item.url)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out
