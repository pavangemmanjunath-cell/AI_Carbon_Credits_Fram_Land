"""Run trace: timing, one record per plan step, an event timeline — and a text renderer.

The orchestrator fills a :class:`RunTrace` while it works. Its ``steps`` become
the ``steps`` array of the stored run (contract: ``{"step", "agent", "status",
"duration_ms", "summary"}``); its ``events`` are a finer timeline (step start,
tool used, message posted …) that is handy when you debug or teach.

:func:`render_transcript` turns a stored run (the JSON dict) into readable
text — the same view ``examples/agents/run_team.py`` prints.
"""

from __future__ import annotations

import textwrap
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, get_args

StepStatus = Literal["done", "warning", "skipped", "failed"]
STEP_STATUSES: tuple[str, ...] = get_args(StepStatus)

Clock = Callable[[], str]


def utc_now_iso() -> str:
    """Current UTC time as ``2026-10-05T09:12:00Z``."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class StepRecord:
    """What happened in one plan step."""

    step: int
    agent: str
    status: StepStatus
    duration_ms: int
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "agent": self.agent,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class TraceEvent:
    """One point on the timeline (``at_ms`` = milliseconds since the run started)."""

    at_ms: int
    kind: str
    step: int | None = None
    agent: str | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "at_ms": self.at_ms,
            "kind": self.kind,
            "step": self.step,
            "agent": self.agent,
            "detail": self.detail,
        }


@dataclass
class RunTrace:
    """Timing and step records for one run."""

    run_id: str
    plan_id: str
    clock: Clock = utc_now_iso
    started_at: str = ""
    finished_at: str | None = None
    duration_ms: int | None = None
    steps: list[StepRecord] = field(default_factory=list)
    events: list[TraceEvent] = field(default_factory=list)
    _t0: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._t0 = time.perf_counter()
        self.started_at = self.started_at or self.clock()
        self.event("run-start", f"plan {self.plan_id}")

    def elapsed_ms(self) -> int:
        return round((time.perf_counter() - self._t0) * 1000)

    def event(
        self, kind: str, detail: str = "", *, step: int | None = None, agent: str | None = None
    ) -> None:
        self.events.append(
            TraceEvent(at_ms=self.elapsed_ms(), kind=kind, step=step, agent=agent, detail=detail)
        )

    def add_step(self, record: StepRecord) -> None:
        self.steps.append(record)
        self.event(
            "step-end",
            f"{record.status} in {record.duration_ms} ms",
            step=record.step,
            agent=record.agent,
        )

    def finish(self) -> None:
        self.duration_ms = self.elapsed_ms()
        self.finished_at = self.clock()
        self.event("run-end", f"{self.duration_ms} ms")


# ----------------------------------------------------------------------------- rendering
def _wrap(text: str, indent: str, width: int) -> str:
    # Keep "68 %" together: wrap with a no-break space, then restore the plain space.
    protected = text.replace(" %", "\u00a0%")
    wrapped = textwrap.fill(
        protected,
        width=width,
        initial_indent=indent,
        subsequent_indent=indent,
        break_on_hyphens=False,
    )
    return wrapped.replace("\u00a0", " ")


def render_transcript(
    run: Mapping[str, Any], *, width: int = 92, show_blackboard: bool = True
) -> str:
    """Readable text for a stored run (the AgentRun JSON dict)."""
    plan = run.get("plan") or {}
    reasoner = run.get("reasoner") or {}
    lines = [
        f"Run {run.get('run_id')}  plan: {plan.get('title')} ({plan.get('id')})  "
        f"plot: {run.get('plot_id')}",
        f"status: {run.get('status')}  duration: {run.get('duration_ms')} ms  "
        f"reasoner: {reasoner.get('mode')}"
        + (f" ({reasoner.get('provider')})" if reasoner.get("provider") else ""),
    ]
    if run.get("question"):
        lines.append(f"question: {run['question']}")
    lines.append("")
    indent = " " * 6
    for message in run.get("messages") or []:
        header = (
            f"[{message.get('id')}] step {message.get('step')} · {message.get('agent_title')} "
            f"→ {message.get('to')} · {message.get('kind')}"
        )
        lines.append(header)
        lines.append(_wrap(str(message.get("text", "")), indent, width))
        calls = message.get("tool_calls") or []
        if calls:
            used = ", ".join(
                f"{c.get('tool')} ({c.get('status')}, {c.get('duration_ms')} ms)" for c in calls
            )
            lines.append(_wrap(f"tools: {used}", indent, width))
        evidence = message.get("evidence") or []
        if evidence:
            lines.append(
                _wrap(
                    "evidence: " + "; ".join(str(e.get("label")) for e in evidence), indent, width
                )
            )
        if message.get("confidence"):
            lines.append(f"{indent}confidence: {message['confidence']}")
    lines.append("")
    lines.append("Steps")
    for step in run.get("steps") or []:
        lines.append(
            f"  {step.get('step'):>2} {step.get('agent'):<12} {step.get('status'):<8} "
            f"{step.get('duration_ms'):>4} ms  {step.get('summary')}"
        )
    lines.append("")
    lines.append("Guardrails")
    for check in run.get("guardrails") or []:
        lines.append(
            _wrap(f"[{check.get('status')}] {check.get('id')}: {check.get('detail')}", "  ", width)
        )
    summary = run.get("summary") or {}
    if summary:
        lines.append("")
        lines.append("Summary")
        lines.append(_wrap(str(summary.get("headline", "")), "  ", width))
        for index, item in enumerate(summary.get("next_steps") or [], start=1):
            lines.append(_wrap(f"{index}. {item}", "  ", width))
    if show_blackboard and run.get("blackboard"):
        lines.append("")
        lines.append("Blackboard — who wrote what")
        writes = [
            f"{w.get('key')} ← {w.get('agent')}"
            + (f" (step {w.get('step')})" if w.get("step") is not None else "")
            for w in run["blackboard"]
        ]
        lines.append(_wrap(" · ".join(writes), "  ", width))
    if run.get("disclaimer"):
        lines.append("")
        lines.append(_wrap(str(run["disclaimer"]), "", width))
    return "\n".join(lines)
