"""The blackboard: shared state that remembers who wrote what.

Agents in this framework never call each other. Each one reads what it needs
from one shared board and writes what it found; the orchestrator decides who
runs next. This is the classic *blackboard* architecture (Hearsay-II, 1970s)
and the same idea as LangGraph's shared graph state.

Two properties make it useful for learning and for audits:

* **Provenance of state** — every write is logged as (key, agent, step), so a
  run can show "the ``estimate`` on the board was written by the carbon agent
  in step 4".
* **Declared access** — agents declare the keys they ``reads`` and ``writes``;
  :class:`~atlas_agents.agent.RunContext` refuses anything else with
  :class:`BlackboardAccessError`. The catalog therefore tells the truth about
  data flow.

Values are deep-copied on write, so an agent cannot change another agent's
finding behind its back.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

REQUEST = "request"
"""Writer name for the run's inputs (plot id, question, locale …)."""

WILDCARD = "*"


class BlackboardAccessError(PermissionError):
    """An agent read or wrote a key it did not declare in ``reads`` / ``writes``."""


@dataclass(frozen=True)
class BoardWrite:
    """One entry of the write log: ``key`` was written by ``agent`` in ``step``."""

    key: str
    agent: str
    step: int | None

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "agent": self.agent, "step": self.step}


def allowed(key: str, patterns: Iterable[str]) -> bool:
    """True when ``key`` is listed in ``patterns`` (``"*"`` allows every key)."""
    return any(pattern == WILDCARD or pattern == key for pattern in patterns)


class Blackboard:
    """A small dict-like store with a write log."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._writes: list[BoardWrite] = []

    # -- writing -------------------------------------------------------------------
    def write(self, key: str, value: Any, *, agent: str, step: int | None = None) -> None:
        """Store ``value`` under ``key`` and log who wrote it."""
        if not key:
            raise ValueError("blackboard keys must be non-empty strings")
        self._values[key] = copy.deepcopy(value)
        self._writes.append(BoardWrite(key=key, agent=agent, step=step))

    # -- reading -------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def has(self, key: str) -> bool:
        """True when ``key`` holds a value other than ``None``."""
        return self._values.get(key) is not None

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __contains__(self, key: object) -> bool:
        return key in self._values

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def keys(self) -> list[str]:
        return list(self._values)

    # -- provenance ------------------------------------------------------------------
    def writer(self, key: str) -> str | None:
        """The agent that last wrote ``key`` (``None`` if nobody did)."""
        for entry in reversed(self._writes):
            if entry.key == key:
                return entry.agent
        return None

    def history(self) -> list[BoardWrite]:
        """Every write in order — the "who wrote what" view."""
        return list(self._writes)

    def snapshot(self) -> dict[str, Any]:
        """A deep copy of the current values (for debugging and tests)."""
        return copy.deepcopy(self._values)
