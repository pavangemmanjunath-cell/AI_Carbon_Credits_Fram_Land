"""Tools, blackboard, agents, plans and the orchestrator — with a tiny toy team."""

from __future__ import annotations

import json

import pytest

from atlas_agents import (
    Agent,
    AgentMessage,
    Blackboard,
    Evidence,
    Guardrail,
    GuardrailResult,
    Orchestrator,
    Plan,
    PlanStep,
    RunContext,
    ToolRegistry,
    ToolSkipped,
    missing,
    render_transcript,
    summarize,
)

TOOLS = ToolRegistry()


@TOOLS.tool()
def add(deps: object, a: int, b: int) -> dict:
    """Add two numbers."""
    return {
        "sum": a + b,
        "lat": 13.2923,
        "geometry": {"type": "Point", "coordinates": [77.5, 13.2]},
    }


@TOOLS.tool(description="Always raises.")
def broken(deps: object) -> None:
    raise RuntimeError("upstream timeout near 13.2923, 77.5384")


@TOOLS.tool()
def not_installed(deps: object) -> None:
    """An optional feature that is missing."""
    raise ToolSkipped("module not installed")


# ----------------------------------------------------------------------------- toy team
class Opener(Agent):
    id = "lead"
    title = "Lead"
    role = "Opens and closes."
    says = "The plan, then a summary."
    reads = ("*",)
    writes = ("summary",)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        if ctx.is_first_step:
            return [ctx.say("plan", f"Plan {ctx.plan.id}: {', '.join(ctx.plan.agent_ids)}.")]
        problems = [r.agent for r in ctx.progress if r.status != "done"]
        ctx.write("summary", {"sum": ctx.read("sum"), "problems": problems})
        return [
            ctx.say(
                "summary",
                f"Sum is {ctx.read('sum')}; problems: {len(problems)}.",
                evidence=[Evidence("toy", "toy")],
            )
        ]


class Adder(Agent):
    id = "adder"
    title = "Adder agent"
    role = "Adds."
    says = "A sum."
    tools = (add,)
    reads = ("x",)
    writes = ("sum",)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        result = ctx.use(add, a=ctx.read("x"), b=2)
        ctx.write("sum", result.value["sum"])
        return [
            ctx.say(
                "finding", f"The sum is {result.value['sum']}.", evidence=[Evidence("calc", "calc")]
            ),
            ctx.handoff("lead", "Lead: the sum is ready."),
        ]


class Flaky(Agent):
    id = "flaky"
    title = "Flaky agent"
    role = "Uses a tool that fails."
    says = "A warning."
    tools = (broken, not_installed)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        result = ctx.use(broken)
        skipped = ctx.use(not_installed)
        assert skipped.status == "skipped"
        return [ctx.warn(f"My tool failed ({result.reason}).")]


class Crasher(Agent):
    id = "crasher"
    title = "Crasher agent"
    role = "Raises."
    says = "Nothing."

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        raise ZeroDivisionError("boom")


class Rogue(Agent):
    id = "rogue"
    title = "Rogue agent"
    role = "Touches things it did not declare."
    says = "Nothing."
    reads = ("x",)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        ctx.write("sum", 0)  # not declared in writes
        return []


class Silent(Agent):
    id = "silent"
    title = "Silent agent"
    role = "Says nothing."
    says = "Nothing."
    tools = (add,)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        ctx.use(add, a=1, b=1)
        return []


TEAM = [Opener(), Adder(), Flaky(), Crasher(), Rogue(), Silent()]


def plan(*steps: PlanStep, plan_id: str = "toy") -> Plan:
    return Plan(plan_id, "Toy plan", (PlanStep("lead"), *steps, PlanStep("lead", run_always=True)))


def run(*steps: PlanStep, **kwargs: object) -> dict:
    result = Orchestrator(TEAM).run(plan(*steps), inputs={"x": 40}, **kwargs)  # type: ignore[arg-type]
    return result.to_dict()


# ----------------------------------------------------------------------------- tools
def test_tool_records_ok_call_with_redacted_summaries():
    result, call = add.invoke(None, a=1, b=2)
    assert result.ok and result.value["sum"] == 3
    assert call.status == "ok" and call.tool == "add" and call.duration_ms >= 0
    assert call.input == {"a": 1, "b": 2}
    assert call.output == {"sum": 3}  # lat and geometry never reach the transcript


def test_tool_error_and_skip_are_results_not_exceptions():
    result, call = broken.invoke(None)
    assert result.status == "error" and not result.ok
    assert "RuntimeError" in result.reason and "13.2923" not in result.reason
    assert call.output == {"reason": result.reason}
    skipped, call = not_installed.invoke(None)
    assert skipped.status == "skipped" and skipped.reason == "module not installed"
    assert call.status == "skipped"


def test_tool_metadata_and_registry():
    assert add.description == "Add two numbers."
    assert broken.description == "Always raises."
    assert [c["name"] for c in TOOLS.cards()] == ["add", "broken", "not_installed"]
    assert "add" in TOOLS and len(TOOLS) == 3
    with pytest.raises(ValueError):
        TOOLS.add(add)
    with pytest.raises(KeyError):
        TOOLS.get("nope")


def test_summarize_keeps_previews_short():
    preview = summarize(
        {"items": list(range(100)), "text": "x" * 500, "deep": {"a": {"b": {"c": 1}}}}
    )
    assert len(preview["items"]) == 7 and preview["items"][-1] == "… 94 more"
    assert len(preview["text"]) == 160
    assert preview["deep"] == {"a": "{1 fields}"}


# ----------------------------------------------------------------------------- blackboard
def test_blackboard_logs_writers_and_copies_values():
    board = Blackboard()
    value = {"n": 1}
    board.write("k", value, agent="a", step=1)
    value["n"] = 2  # changing the original must not change the board
    assert board.get("k") == {"n": 1} and board.has("k") and "k" in board
    board.write("k", {"n": 3}, agent="b", step=2)
    assert board.writer("k") == "b"
    assert [w.to_dict() for w in board.history()] == [
        {"key": "k", "agent": "a", "step": 1},
        {"key": "k", "agent": "b", "step": 2},
    ]
    board.write("empty", None, agent="c")
    assert not board.has("empty") and missing("empty")(board)


# ----------------------------------------------------------------------------- orchestrator
def test_plan_runs_in_order_numbers_messages_and_records_writers():
    out = run(PlanStep("adder"))
    assert out["status"] == "completed"
    assert [s["agent"] for s in out["steps"]] == ["lead", "adder", "lead"]
    assert [s["status"] for s in out["steps"]] == ["done", "done", "done"]
    assert [m["id"] for m in out["messages"]] == ["M1", "M2", "M3", "M4"]
    assert [(m["agent"], m["kind"], m["to"]) for m in out["messages"]] == [
        ("lead", "plan", "team"),
        ("adder", "finding", "team"),
        ("adder", "handoff", "lead"),
        ("lead", "summary", "team"),
    ]
    assert out["messages"][1]["tool_calls"][0]["tool"] == "add"
    assert out["messages"][2]["tool_calls"] == []  # calls attach to the first message after them
    assert out["messages"][-1]["text"] == "Sum is 42; problems: 0."
    assert out["blackboard"] == [
        {"key": "x", "agent": "request", "step": None},
        {"key": "sum", "agent": "adder", "step": 1},
        {"key": "summary", "agent": "lead", "step": 2},
    ]
    assert out["plan"] == {"id": "toy", "title": "Toy plan", "steps": ["lead", "adder", "lead"]}
    assert out["reasoner"] == {"mode": "template", "llm_enabled": False, "provider": None}
    assert out["started_at"].endswith("Z") and isinstance(out["duration_ms"], int)


def test_failing_tool_makes_a_warning_step_and_the_run_completes():
    out = run(PlanStep("flaky"), PlanStep("adder"))
    assert out["status"] == "completed-with-warnings"
    statuses = {s["agent"]: s["status"] for s in out["steps"]}
    assert statuses["flaky"] == "warning" and statuses["adder"] == "done"
    warning = next(m for m in out["messages"] if m["agent"] == "flaky")
    assert warning["kind"] == "warning"
    assert [c["status"] for c in warning["tool_calls"]] == ["error", "skipped"]
    assert out["messages"][-1]["kind"] == "summary"


def test_crashing_agent_is_isolated_and_reported():
    out = run(PlanStep("crasher"), PlanStep("adder"))
    assert out["status"] == "completed-with-warnings"
    crash = next(s for s in out["steps"] if s["agent"] == "crasher")
    assert crash["status"] == "failed" and "ZeroDivisionError" in crash["summary"]
    message = next(m for m in out["messages"] if m["agent"] == "crasher")
    assert message["kind"] == "warning" and "ZeroDivisionError" in message["text"]
    assert next(s for s in out["steps"] if s["agent"] == "adder")["status"] == "done"
    assert out["messages"][-1]["text"].endswith("problems: 1.")


def test_critical_failure_skips_the_rest_but_still_closes_the_run():
    out = run(PlanStep("crasher", critical=True), PlanStep("adder"))
    assert out["status"] == "failed"
    statuses = [(s["agent"], s["status"]) for s in out["steps"]]
    assert statuses == [
        ("lead", "done"),
        ("crasher", "failed"),
        ("adder", "skipped"),
        ("lead", "done"),
    ]
    assert "step 1 (crasher) failed" in out["steps"][2]["summary"]


def test_skip_rules_and_broken_skip_rules():
    def broken_rule(board: Blackboard) -> str | None:
        raise TypeError("bad rule")

    out = run(
        PlanStep("adder", skip_if=missing("nothing-here", reason="skipped: no input")),
        PlanStep("adder", skip_if=broken_rule),
        PlanStep("adder"),
    )
    assert out["status"] == "completed-with-warnings"
    assert out["steps"][1] == {
        "step": 1,
        "agent": "adder",
        "status": "skipped",
        "duration_ms": 0,
        "summary": "skipped: no input",
    }
    assert out["steps"][2]["status"] == "skipped" and "TypeError" in out["steps"][2]["summary"]
    assert out["steps"][3]["status"] == "done"


def test_a_run_where_no_specialist_works_has_failed():
    out = run(PlanStep("adder", skip_if=missing("nothing-here")))
    assert out["status"] == "failed"
    assert out["messages"][-1]["kind"] == "summary"  # the closing step still ran


def test_undeclared_board_access_fails_the_step():
    out = run(PlanStep("rogue"))
    step = next(s for s in out["steps"] if s["agent"] == "rogue")
    assert step["status"] == "failed"
    assert (
        "BlackboardAccessError" in next(m for m in out["messages"] if m["agent"] == "rogue")["text"]
    )


def test_undeclared_tool_is_refused():
    class Sneaky(Agent):
        id = "sneaky"
        title = "Sneaky agent"
        role = "Uses a tool it did not declare."
        says = "Nothing."

        def run(self, ctx: RunContext) -> list[AgentMessage]:
            ctx.use("add", a=1, b=2)
            return []

    result = Orchestrator([Opener(), Sneaky()]).run(
        Plan("p", "P", (PlanStep("lead"), PlanStep("sneaky"), PlanStep("lead"))), inputs={}
    )
    message = next(m for m in result.messages if m.agent == "sneaky")
    assert "ToolNotAllowed" in message.text
    assert result.steps[1].status == "failed"


def test_agent_that_says_nothing_gets_a_warning_with_its_tool_calls():
    out = run(PlanStep("silent"))
    message = next(m for m in out["messages"] if m["agent"] == "silent")
    assert message["kind"] == "warning" and message["tool_calls"][0]["tool"] == "add"


def test_unknown_agents_and_empty_plans_are_rejected():
    with pytest.raises(ValueError, match="unknown agents"):
        Orchestrator(TEAM).run(Plan("p", "P", (PlanStep("ghost"),)), inputs={})
    with pytest.raises(ValueError):
        Plan("p", "P", ())
    with pytest.raises(ValueError):
        Orchestrator([Adder(), Adder()])


def test_guardrails_decide_the_status_and_cannot_crash_the_run():
    always_warn = Guardrail("warn-me", lambda run: GuardrailResult("warn-me", "warn", "careful"))

    def explode(run: object) -> GuardrailResult:
        raise RuntimeError("bug")

    out = run(PlanStep("adder"), guardrails=[always_warn])
    assert out["status"] == "completed-with-warnings"
    assert out["guardrails"] == [{"id": "warn-me", "status": "warn", "detail": "careful"}]
    out = run(PlanStep("adder"), guardrails=[Guardrail("explode", explode)])
    assert out["status"] == "failed"
    assert (
        out["guardrails"][0]["status"] == "fail"
        and "RuntimeError" in out["guardrails"][0]["detail"]
    )


def test_messages_validate_their_fields():
    with pytest.raises(ValueError):
        AgentMessage(id="M1", step=0, agent="a", agent_title="A", kind="chat", text="hi")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        AgentMessage(id="M1", step=0, agent="a", agent_title="A", kind="finding", text=" ")
    with pytest.raises(ValueError):
        AgentMessage(
            id="M1",
            step=0,
            agent="a",
            agent_title="A",
            kind="finding",
            text="x",
            confidence="sure",  # type: ignore[arg-type]
        )


def test_run_dict_is_json_and_renders_as_a_transcript():
    out = run(PlanStep("adder"), PlanStep("flaky"))
    json.dumps(out)  # stored as JSON by the host application
    text = render_transcript({**out, "plot_id": "PLT-TOY"})
    assert "[M2] step 1 · Adder agent → team · finding" in text
    assert "tools: add (ok" in text and "Guardrails" in text
    assert "x ← request" in text and "sum ← adder (step 1)" in text
