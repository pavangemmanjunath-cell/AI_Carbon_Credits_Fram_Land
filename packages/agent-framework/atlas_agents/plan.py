"""Plans: which agents run, in which order, and when a step is skipped.

A plan is an ordered list of steps; each step names one agent. Plans are
*data*, written by people — the orchestrator follows them, it does not invent
them. That is what "deterministic by default" means for control flow.

A step can carry three rules:

* ``skip_if`` — a function of the blackboard that returns a reason to skip
  ("no carbon estimate yet") or ``None`` to run. Steps whose inputs are
  missing skip themselves, which is how the team "continues when sensible"
  after a failure.
* ``critical`` — if this step *fails*, later steps are skipped.
* ``run_always`` — run even after a critical failure (used for the closing
  coordinator step, so every run ends with a summary).

Example::

    QUICK = Plan(
        id="quick-estimate",
        title="Quick estimate",
        steps=(
            PlanStep("coordinator"),
            PlanStep("land"),
            PlanStep("trees"),
            PlanStep("carbon", skip_if=missing("inventory")),
            PlanStep("review"),
            PlanStep("coordinator", run_always=True),
        ),
    )
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from atlas_agents.blackboard import Blackboard

SkipRule = Callable[[Blackboard], str | None]


def missing(*keys: str, reason: str | None = None) -> SkipRule:
    """Skip rule: skip when any of ``keys`` is absent (or ``None``) on the blackboard."""

    def rule(board: Blackboard) -> str | None:
        absent = [key for key in keys if not board.has(key)]
        if not absent:
            return None
        return reason or f"skipped: nothing on the blackboard for {', '.join(absent)}"

    rule.__name__ = f"missing({', '.join(keys)})"
    return rule


@dataclass(frozen=True)
class PlanStep:
    """One step: run ``agent`` (an agent id) unless a rule says otherwise."""

    agent: str
    skip_if: SkipRule | None = None
    critical: bool = False
    run_always: bool = False
    note: str = ""


@dataclass(frozen=True)
class Plan:
    """An ordered list of steps with an id and a human title."""

    id: str
    title: str
    steps: tuple[PlanStep, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError(f"plan {self.id!r} has no steps")

    @property
    def agent_ids(self) -> list[str]:
        """Agent ids in step order (an agent may appear more than once)."""
        return [step.agent for step in self.steps]

    def to_dict(self) -> dict[str, Any]:
        """Contract shape: ``{"id", "title", "steps": [agent ids]}``."""
        return {"id": self.id, "title": self.title, "steps": self.agent_ids}

    def describe(self) -> dict[str, Any]:
        """A longer form for docs and catalogs (includes skip rules and flags)."""
        return {
            **self.to_dict(),
            "description": self.description,
            "rules": [
                {
                    "step": index,
                    "agent": step.agent,
                    "skip_if": getattr(step.skip_if, "__name__", None) if step.skip_if else None,
                    "critical": step.critical,
                    "run_always": step.run_always,
                    "note": step.note,
                }
                for index, step in enumerate(self.steps)
            ],
        }
