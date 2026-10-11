# agent-framework (`carboncreditbuy_agents`)

A small, readable framework for **teams of deterministic agents**: agents with declared tools and data access,
a shared blackboard that remembers who wrote what, plans with skip rules, an orchestrator that never lets one
agent sink a run, guardrails over the finished transcript — and an *optional* language model that may only
rephrase what the agents already said.

It was written for [CarbonCreditBuy](../../docs/README.md) and for people who want to learn how agentic systems
are put together. It knows nothing about carbon: the CarbonCreditBuy team is in
[`apps/api/app/agents/`](../../apps/api/app/agents/), and the learning guide is
[docs/agents/README.md](../../docs/agents/README.md).

## What it does and does not do

| It does | It does not |
|---|---|
| Run a plan of named agents in order, with skip rules and failure isolation | Let a model choose the next agent or tool |
| Record every tool call with status, duration and redacted input/output summaries | Store raw payloads, coordinates or geometry in transcripts |
| Enforce each agent's declared tools and blackboard keys | Allow hidden data flow between agents |
| Keep template text by default; optionally let an LLM rephrase it, then check the numbers | Accept any number that did not come from the template or the facts |
| Run deterministic guardrails and report `completed`, `completed-with-warnings` or `failed` | Raise because one agent failed |

## Install

```bash
python3 -m pip install -e packages/agent-framework            # core: no third-party dependencies
python3 -m pip install -e "packages/agent-framework[llm]"     # + httpx for the OpenAI-compatible client
```

Python 3.12 or newer.

## A team in forty lines

```python
from carboncreditbuy_agents import (
    Agent,
    Evidence,
    Orchestrator,
    Plan,
    PlanStep,
    ToolRegistry,
    missing,
)
from carboncreditbuy_agents import render_transcript

tools = ToolRegistry()


@tools.tool()
def count_trees(deps, field: str) -> dict:
    """Count the trees recorded for a field."""
    return {"field": field, "trees": deps["inventory"].get(field, 0)}


class Counter(Agent):
    id, title = "counter", "Counter agent"
    role, says = "Counts trees.", "How many trees a field has."
    tools = (count_trees,)
    reads, writes = ("field",), ("trees",)

    def run(self, ctx):
        result = ctx.use(count_trees, field=ctx.read("field"))
        if not result.ok:
            return [ctx.warn(f"I could not count the trees ({result.reason}).")]
        ctx.write("trees", result.value["trees"])
        return [
            ctx.say(
                "finding",
                f"Field {result.value['field']} has {result.value['trees']} trees.",
                evidence=[Evidence("Farm inventory", "inventory")],
            )
        ]


class Narrator(Agent):
    id, title = "narrator", "Narrator"
    role, says = "Closes the run.", "A one-line summary."
    reads, writes = ("trees",), ()

    def run(self, ctx):
        return [ctx.say("summary", f"Done: {ctx.read('trees')} trees counted.")]


plan = Plan(
    "count", "Count trees", (PlanStep("counter"), PlanStep("narrator", skip_if=missing("trees")))
)
result = Orchestrator([Counter(), Narrator()]).run(
    plan, inputs={"field": "north"}, deps={"inventory": {"north": 420}}
)
print(render_transcript({**result.to_dict(), "plot_id": "demo"}))
```

`result.to_dict()` is plain JSON: `run_id`, `plan`, `status`, `reasoner`, timing, `steps`, `messages`,
`guardrails` and `blackboard` (the write log).

## Concepts and modules

| Module | Main names | Idea |
|---|---|---|
| `messages` | `AgentMessage`, `ToolCall`, `Evidence` | one line of the transcript: who said what, with which tools and evidence |
| `tools` | `Tool`, `@tool`, `ToolRegistry`, `ToolSkipped`, `ToolResult` | described functions; calls are timed and recorded, never raise into the agent |
| `blackboard` | `Blackboard`, `BlackboardAccessError` | shared state with a write log; values are copied on write |
| `agent` | `Agent`, `RunContext` | declared tools, reads and writes; `say` / `warn` / `handoff` |
| `plan` | `Plan`, `PlanStep`, `missing` | ordered steps; `skip_if`, `critical`, `run_always` |
| `orchestrator` | `Orchestrator`, `RunResult` | the loop; step and run statuses; guardrails |
| `reasoner` | `TemplateReasoner`, `LLMReasoner`, `review_rephrase` | template text by default; checked LLM rephrasing |
| `guardrails` | `Guardrail`, `check_*` | pure checks: not-a-credit, uncertainty, provenance, no-coordinates, pending parameters, values separated |
| `trace` | `RunTrace`, `StepRecord`, `render_transcript` | timing, step records and a text view |
| `intents` | `IntentRouter`, `DEFAULT_INTENTS`, `parse_tree_change` | keyword routing from a question to a plan |
| `llm` | `OpenAICompatibleProvider`, `redact`, `redact_text` | the optional client and the privacy filter |

## Optional LLM

```python
from carboncreditbuy_agents import LLMReasoner
from carboncreditbuy_agents.llm import OpenAICompatibleProvider

provider = OpenAICompatibleProvider("http://localhost:11434/v1", "llama3.1:8b", timeout_seconds=20)
result = orchestrator.run(plan, inputs=..., reasoner=LLMReasoner(provider))
```

The model sees only redacted template text and facts. Its answer is kept only when every number matches the
template or the facts, no number is dropped, nothing looks like a coordinate and nothing claims a credit;
otherwise the template is kept and the run's `llm-rephrase` guardrail warns. After a provider error the
reasoner stops calling the model for the rest of the run. Pass safety sentences as `ctx.say(...,
disclaimer="...")`: they are appended after narration and never sent to the model.

## Tests

```bash
python3 -m pytest -q packages/agent-framework
```

The tests need no network: the LLM client is exercised with `httpx.MockTransport` and fake providers.

## License

Apache-2.0, like the rest of CarbonCreditBuy.
