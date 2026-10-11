"""Tools: named, described functions that agents call to get work done.

A tool wraps one capability of the host application — "measure this plot",
"run the carbon engine". Agents never reach into services directly; they use
tools, and every use is recorded. Calling a tool through :meth:`Tool.invoke`
gives you what a plain function call does not:

* a **status**: ``ok``, ``error`` (the function raised) or ``skipped`` (it raised
  :class:`ToolSkipped`, e.g. an optional module is not installed yet);
* a **duration** in milliseconds;
* **redacted summaries** of input and output for the transcript — never raw
  payloads, never coordinates or geometry.

A tool never raises into the agent. Errors come back as a :class:`ToolResult`
with ``status="error"``; the agent decides what to tell the team.

Writing a tool::

    toolbox = ToolRegistry()

    @toolbox.tool()
    def measure_plot(deps, plot_id: str) -> dict:
        \"\"\"Measure the plot and check that its boundary is valid.\"\"\"
        plot = deps.plots.require(plot_id)
        return {"area_hectares": plot["area_hectares"], ...}

The first argument (``deps``) is the host application's dependency container —
the same idea as PydanticAI's ``RunContext.deps``. The description shown to
people (and, in other frameworks, to an LLM choosing tools) is the first line
of the docstring unless you pass ``description=``.
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from carboncreditbuy_agents.llm.redaction import redact, redact_text
from carboncreditbuy_agents.messages import ToolCall, ToolStatus

Summarizer = Callable[[Any], Any]


class ToolSkipped(Exception):
    """Raise inside a tool to say "I did not run, and here is why".

    The call is recorded with ``status="skipped"`` and the message as reason —
    for example when an optional feature module is not installed yet.
    """


@dataclass(frozen=True)
class ToolResult:
    """What the agent gets back from ``ctx.use(tool, ...)``."""

    tool: str
    status: ToolStatus
    value: Any = None
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


# ----------------------------------------------------------------------------- summaries
def summarize(
    value: Any,
    *,
    depth: int = 2,
    max_items: int = 12,
    max_list: int = 6,
    max_text: int = 160,
) -> Any:
    """A short, JSON-friendly preview of ``value`` for the transcript.

    Dicts keep their first ``max_items`` keys, lists their first ``max_list``
    items, strings are cut at ``max_text`` characters and nesting stops after
    ``depth`` levels (deeper parts become ``"…"`` or a count).
    """
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= max_text else value[: max_text - 1] + "…"
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Mapping):
        if depth <= 0:
            return f"{{{len(value)} fields}}"
        out: dict[str, Any] = {}
        for index, (key, inner) in enumerate(value.items()):
            if index >= max_items:
                out["…"] = f"{len(value) - max_items} more fields"
                break
            out[str(key)] = summarize(
                inner, depth=depth - 1, max_items=max_items, max_list=max_list, max_text=max_text
            )
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        if depth <= 0:
            return f"[{len(items)} items]"
        shown = [
            summarize(v, depth=depth - 1, max_items=max_items, max_list=max_list, max_text=max_text)
            for v in items[:max_list]
        ]
        if len(items) > max_list:
            shown.append(f"… {len(items) - max_list} more")
        return shown
    return summarize(repr(value), max_text=max_text)


def summary_dict(value: Any, summarizer: Summarizer | None = None) -> dict[str, Any]:
    """Redact first, then summarise; always returns a dict (``{"value": …}`` for scalars)."""
    shaped = summarizer(value) if summarizer is not None else value
    preview = summarize(redact(shaped))
    return preview if isinstance(preview, dict) else {"value": preview}


def _first_line(text: str | None) -> str:
    for line in inspect.cleandoc(text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


# ----------------------------------------------------------------------------- tools
@dataclass(frozen=True)
class Tool:
    """A named function with a description, called as ``fn(deps, **kwargs)``."""

    name: str
    description: str
    fn: Callable[..., Any]
    summarize_output: Summarizer | None = None

    def __call__(self, deps: Any, /, **kwargs: Any) -> Any:
        """Call the function directly (no recording) — handy in unit tests."""
        return self.fn(deps, **kwargs)

    def invoke(self, deps: Any, /, **kwargs: Any) -> tuple[ToolResult, ToolCall]:
        """Run the tool and return (what the agent sees, what the transcript records)."""
        started = time.perf_counter()
        value: Any = None
        reason: str | None = None
        status: ToolStatus
        try:
            value = self.fn(deps, **kwargs)
            status = "ok"
        except ToolSkipped as exc:
            status, reason = "skipped", redact_text(str(exc))[:240] or "skipped"
        except Exception as exc:  # a tool must never crash the agent that called it
            status, reason = "error", redact_text(f"{type(exc).__name__}: {exc}")[:240]
        duration_ms = round((time.perf_counter() - started) * 1000)
        output = (
            summary_dict(value, self.summarize_output) if status == "ok" else {"reason": reason}
        )
        call = ToolCall(
            tool=self.name,
            status=status,
            duration_ms=duration_ms,
            input=summary_dict(kwargs),
            output=output,
        )
        return ToolResult(tool=self.name, status=status, value=value, reason=reason), call

    def card(self) -> dict[str, str]:
        """Catalog entry: ``{"name", "description"}``."""
        return {"name": self.name, "description": self.description}


def tool(
    name: str | None = None,
    *,
    description: str | None = None,
    summarize_output: Summarizer | None = None,
    registry: ToolRegistry | None = None,
) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator: turn ``fn(deps, **kwargs)`` into a :class:`Tool`.

    ``description`` defaults to the first line of the function's docstring.
    Pass ``registry=`` (or use :meth:`ToolRegistry.tool`) to register it.
    """

    def wrap(fn: Callable[..., Any]) -> Tool:
        made = Tool(
            name=name or fn.__name__,
            description=description or _first_line(fn.__doc__) or fn.__name__,
            fn=fn,
            summarize_output=summarize_output,
        )
        if registry is not None:
            registry.add(made)
        return made

    return wrap


class ToolRegistry:
    """The toolbox: every tool the application offers, by unique name."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def add(self, item: Tool) -> Tool:
        if item.name in self._tools:
            raise ValueError(f"a tool named {item.name!r} is already registered")
        self._tools[item.name] = item
        return item

    def tool(
        self,
        name: str | None = None,
        *,
        description: str | None = None,
        summarize_output: Summarizer | None = None,
    ) -> Callable[[Callable[..., Any]], Tool]:
        """Decorator form of :func:`tool` that registers the tool here."""
        return tool(name, description=description, summarize_output=summarize_output, registry=self)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"no tool named {name!r}; known: {sorted(self._tools)}") from None

    def cards(self) -> list[dict[str, str]]:
        return [item.card() for item in self._tools.values()]

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)
