"""The orchestrator: runs a plan, step by step, and never lets one agent sink the run.

For every step of a :class:`~atlas_agents.plan.Plan` the orchestrator

1. checks whether the step must be skipped (an earlier *critical* step failed,
   or the step's ``skip_if`` rule returns a reason);
2. gives the agent a fresh :class:`~atlas_agents.agent.RunContext` and times
   its ``run``;
3. catches any exception — the step becomes ``failed``, the team gets a
   warning message, and the run continues;
4. numbers the agent's messages (M1, M2, …) and appends them to the transcript;
5. records a :class:`~atlas_agents.trace.StepRecord` with status ``done``,
   ``warning``, ``skipped`` or ``failed``.

After the last step it runs the guardrails and decides the run status:

* ``failed`` — a critical step failed, no specialist step produced anything,
  or a guardrail failed;
* ``completed-with-warnings`` — a step warned, failed or was skipped, or a
  guardrail warned;
* ``completed`` — everything passed.

The orchestrator is deliberately boring: a ``for`` loop over a list you can
read. There is no LLM choosing the next agent (compare LangGraph's
conditional edges or CrewAI's hierarchical process, see docs/agents).
"""

from __future__ import annotations

import logging
import secrets
import string
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from atlas_agents.agent import Agent, RunContext
from atlas_agents.blackboard import REQUEST, Blackboard
from atlas_agents.guardrails import Guardrail, GuardrailInput, GuardrailResult, sentences
from atlas_agents.messages import AgentMessage
from atlas_agents.plan import Plan
from atlas_agents.reasoner import Reasoner, TemplateReasoner
from atlas_agents.trace import Clock, RunTrace, StepRecord, StepStatus, utc_now_iso

log = logging.getLogger("atlas.agents")

RunStatus = Literal["completed", "completed-with-warnings", "failed"]

_ID_ALPHABET = string.ascii_uppercase + string.digits


def new_run_id(prefix: str = "RUN-", length: int = 8) -> str:
    return prefix + "".join(secrets.choice(_ID_ALPHABET) for _ in range(length))


def _first_sentence(text: str, limit: int = 160) -> str:
    parts = sentences(text)
    first = parts[0] if parts else text
    return first if len(first) <= limit else first[: limit - 1] + "…"


@dataclass
class RunResult:
    """Everything a run produced. :meth:`to_dict` gives the transcript part of an AgentRun."""

    run_id: str
    plan: Plan
    status: RunStatus
    messages: list[AgentMessage]
    guardrails: list[GuardrailResult]
    trace: RunTrace
    board: Blackboard
    reasoner_mode: str
    reasoner_provider: str | None
    inputs: dict[str, Any] = field(default_factory=dict)

    @property
    def steps(self) -> list[StepRecord]:
        return self.trace.steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "plan": self.plan.to_dict(),
            "status": self.status,
            "reasoner": {
                "mode": self.reasoner_mode,
                "llm_enabled": self.reasoner_mode == "llm",
                "provider": self.reasoner_provider,
            },
            "started_at": self.trace.started_at,
            "finished_at": self.trace.finished_at,
            "duration_ms": self.trace.duration_ms,
            "steps": [s.to_dict() for s in self.trace.steps],
            "messages": [m.to_dict() for m in self.messages],
            "guardrails": [g.to_dict() for g in self.guardrails],
            "blackboard": [w.to_dict() for w in self.board.history()],
        }


class Orchestrator:
    """Runs plans over a fixed team of agents."""

    def __init__(
        self,
        agents: Iterable[Agent],
        *,
        guardrails: Sequence[Guardrail] = (),
        clock: Clock = utc_now_iso,
    ) -> None:
        self.agents: dict[str, Agent] = {}
        for agent in agents:
            if not agent.id:
                raise ValueError(f"{type(agent).__name__} has no id")
            if agent.id in self.agents:
                raise ValueError(f"two agents share the id {agent.id!r}")
            self.agents[agent.id] = agent
        self.guardrails = tuple(guardrails)
        self.clock = clock

    def check_plan(self, plan: Plan) -> None:
        """Raise ``ValueError`` when a plan names an agent this team does not have."""
        unknown = sorted({s.agent for s in plan.steps if s.agent not in self.agents})
        if unknown:
            raise ValueError(f"plan {plan.id!r} uses unknown agents: {', '.join(unknown)}")

    # ------------------------------------------------------------------------------ run
    def run(
        self,
        plan: Plan,
        *,
        inputs: Mapping[str, Any],
        deps: Any = None,
        reasoner: Reasoner | None = None,
        guardrails: Sequence[Guardrail] = (),
        locale: str = "en",
        run_id: str | None = None,
    ) -> RunResult:
        """Execute ``plan``. Never raises because of an agent; see the module docstring."""
        self.check_plan(plan)
        run_id = run_id or new_run_id()
        reasoner = reasoner or TemplateReasoner()
        board = Blackboard()
        for key, value in inputs.items():
            board.write(key, value, agent=REQUEST)
        trace = RunTrace(run_id=run_id, plan_id=plan.id, clock=self.clock)
        transcript: list[AgentMessage] = []
        halted_by: int | None = None

        for index, step in enumerate(plan.steps):
            agent = self.agents[step.agent]
            skip_reason: str | None = None
            if halted_by is not None and not step.run_always:
                skip_reason = f"skipped: step {halted_by} ({plan.steps[halted_by].agent}) failed"
            elif step.skip_if is not None:
                try:
                    skip_reason = step.skip_if(board)
                except Exception as exc:  # a broken rule skips its step; it never ends the run
                    skip_reason = f"skipped: the skip rule failed ({type(exc).__name__})"
            if skip_reason:
                record = StepRecord(index, agent.id, "skipped", 0, skip_reason)
            else:
                trace.event("step-start", agent.title, step=index, agent=agent.id)
                record, produced = self._run_step(
                    index, agent, plan, board, trace, reasoner, deps, locale, run_id
                )
                if record.status == "failed" and step.critical:
                    halted_by = index
                for message in produced:
                    message.id = f"M{len(transcript) + 1}"
                    transcript.append(message)
            trace.add_step(record)

        results = [
            g.run(GuardrailInput(transcript, board)) for g in (*self.guardrails, *guardrails)
        ]
        reasoner_report = reasoner.report()
        if reasoner_report is not None:
            results.append(reasoner_report)
        for result in results:
            trace.event("guardrail", f"{result.id}: {result.status}")
        trace.finish()
        status = self._status(plan, trace.steps, results, halted_by)
        log.info(
            "agent run %s (%s) finished: %s",
            run_id,
            plan.id,
            status,
            extra={"duration_ms": trace.duration_ms},
        )
        return RunResult(
            run_id=run_id,
            plan=plan,
            status=status,
            messages=transcript,
            guardrails=results,
            trace=trace,
            board=board,
            reasoner_mode=reasoner.mode,
            reasoner_provider=reasoner.provider,
            inputs=dict(inputs),
        )

    # ------------------------------------------------------------------------- one step
    def _run_step(
        self,
        index: int,
        agent: Agent,
        plan: Plan,
        board: Blackboard,
        trace: RunTrace,
        reasoner: Reasoner,
        deps: Any,
        locale: str,
        run_id: str,
    ) -> tuple[StepRecord, list[AgentMessage]]:
        ctx = RunContext(
            run_id=run_id,
            plan=plan,
            step=index,
            agent=agent,
            board=board,
            reasoner=reasoner,
            deps=deps,
            locale=locale,
            trace=trace,
            clock=self.clock,
            progress=tuple(trace.steps),
        )
        started = time.perf_counter()
        failure: Exception | None = None
        try:
            produced = list(agent.run(ctx) or [])
        except Exception as exc:  # the whole point: one agent must not sink the run
            failure = exc
            produced = []
            # Log ids and the exception type only — messages may contain user data.
            log.warning("agent step %d (%s) failed: %s", index, agent.id, type(exc).__name__)
        duration_ms = round((time.perf_counter() - started) * 1000)

        leftover = ctx.take_tool_calls()
        if failure is not None:
            produced.append(
                ctx.warn(
                    f"The {agent.title} ran into a problem ({type(failure).__name__}) and "
                    "stopped. The rest of the team carried on without its results.",
                    facts={"error": type(failure).__name__},
                )
            )
        elif not produced:
            produced.append(ctx.warn(f"The {agent.title} finished without reporting anything."))
        if leftover:  # tool calls made after the agent's last message: keep them visible
            produced[-1].tool_calls.extend(leftover)

        status: StepStatus
        if failure is not None:
            status = "failed"
        elif any(m.kind == "warning" for m in produced) or any(
            call.status == "error" for m in produced for call in m.tool_calls
        ):
            status = "warning"
        else:
            status = "done"

        if ctx.summary:
            summary = ctx.summary
        elif failure is not None:
            summary = f"failed ({type(failure).__name__}); the team continued"
        else:
            main = next((m for m in produced if m.kind != "handoff"), produced[0])
            summary = _first_sentence(main.text)
        return StepRecord(index, agent.id, status, duration_ms, summary), produced

    # --------------------------------------------------------------------------- status
    @staticmethod
    def _status(
        plan: Plan,
        steps: Sequence[StepRecord],
        guardrails: Sequence[GuardrailResult],
        halted_by: int | None,
    ) -> RunStatus:
        bookends = {plan.steps[0].agent, plan.steps[-1].agent}
        specialists = [s for s in steps if s.agent not in bookends] or list(steps)
        produced_something = any(s.status in ("done", "warning") for s in specialists)
        if halted_by is not None or not produced_something:
            return "failed"
        if any(g.status == "fail" for g in guardrails):
            return "failed"
        if any(s.status != "done" for s in steps) or any(g.status == "warn" for g in guardrails):
            return "completed-with-warnings"
        return "completed"
