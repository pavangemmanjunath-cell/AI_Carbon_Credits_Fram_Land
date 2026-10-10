"""Agent endpoints in demo mode: catalog, plans, ask, storage, errors, privacy and API keys."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from app.agents.plans import PLANS
from app.agents.schemas import PlanId
from app.core.config import Settings
from app.main import create_app

AGENTS = [
    "coordinator",
    "land",
    "imagery",
    "trees",
    "carbon",
    "policy",
    "market",
    "review",
    "report",
]
FULL = [
    "coordinator",
    "land",
    "imagery",
    "trees",
    "carbon",
    "policy",
    "market",
    "review",
    "report",
    "coordinator",
]
QUICK = ["coordinator", "land", "trees", "carbon", "review", "coordinator"]
TREE_AGE = ["coordinator", "trees", "carbon", "policy", "review", "coordinator"]
CONTRACT_GUARDRAILS = {
    "not-a-credit",
    "uncertainty-present",
    "provenance-present",
    "no-coordinates",
    "pending-parameters",
    "values-separated",
}
KINDS = {"plan", "finding", "warning", "handoff", "answer", "summary"}
STEP_STATUSES = {"done", "warning", "skipped", "failed"}


def run_plan(client: TestClient, plan: str, plot_id: str = "PLT-DEMOIN", **extra: object) -> dict:
    resp = client.post(f"/api/v1/plots/{plot_id}/agents/run", json={"plan": plan, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def ask(client: TestClient, question: str, **extra: object) -> dict:
    body = {"question": question, "plot_id": "PLT-DEMOIN", **extra}
    resp = client.post("/api/v1/agents/ask", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def by_agent(run: dict, agent: str, kind: str | None = None) -> list[dict]:
    return [
        m for m in run["messages"] if m["agent"] == agent and (kind is None or m["kind"] == kind)
    ]


def guardrails(run: dict) -> dict[str, str]:
    return {g["id"]: g["status"] for g in run["guardrails"]}


@pytest.fixture(scope="module")
def full_run(client: TestClient) -> dict:
    return run_plan(client, "full-assessment")


# ----------------------------------------------------------------------------- catalog
def test_catalog_describes_team_tools_and_plans(client):
    body = client.get("/api/v1/agents").json()
    assert body["framework"] == {
        "name": "atlas-agents",
        "version": "0.1.0",
        "reasoner": "template",
        "llm_enabled": False,
    }
    assert [a["id"] for a in body["agents"]] == AGENTS
    for agent in body["agents"]:
        assert {"id", "title", "role", "says", "tools", "reads", "writes"} <= agent.keys()
        assert agent["title"] and agent["role"] and agent["says"]
        assert all(t["name"] and t["description"] for t in agent["tools"])
    carbon = next(a for a in body["agents"] if a["id"] == "carbon")
    assert [t["name"] for t in carbon["tools"]] == ["estimate_carbon", "simulate_what_if"]
    assert carbon["reads"] == ["plot_id", "inventory", "what_if"] and "estimate" in carbon["writes"]
    plans = {p["id"]: p["steps"] for p in body["plans"]}
    assert plans == {"full-assessment": FULL, "quick-estimate": QUICK, "tree-age-check": TREE_AGE}


def test_plan_literal_matches_the_plans():
    assert set(PlanId.__args__) == set(PLANS)  # type: ignore[attr-defined]


# ----------------------------------------------------------------------------- full assessment
def test_full_assessment_on_the_demo_plot(full_run):
    run = full_run
    assert run["run_id"].startswith("RUN-") and run["plot_id"] == "PLT-DEMOIN"
    assert run["status"] in {"completed", "completed-with-warnings"}
    assert run["plan"] == {"id": "full-assessment", "title": "Full assessment", "steps": FULL}
    assert [s["agent"] for s in run["steps"]] == FULL
    assert [s["step"] for s in run["steps"]] == list(range(len(FULL)))
    assert {s["status"] for s in run["steps"]} <= STEP_STATUSES
    assert run["reasoner"] == {"mode": "template", "llm_enabled": False, "provider": None}
    assert run["certified"] is False and run["summary"]["certified"] is False
    assert (
        "not issued carbon" in run["disclaimer"] and "not guaranteed revenue" in run["disclaimer"]
    )
    assert run["provenance"]["mode"] == "demo" and run["provenance"]["sources"]
    assert run["provenance"]["model"]["id"] == "tree-biomass"
    assert {"started_at", "finished_at", "duration_ms"} <= run.keys()


def test_every_message_says_who_and_what(full_run):
    messages = full_run["messages"]
    assert [m["id"] for m in messages] == [f"M{i}" for i in range(1, len(messages) + 1)]
    for message in messages:
        assert message["agent"] in AGENTS and message["agent_title"] and message["text"].strip()
        assert message["kind"] in KINDS and message["to"] in {"team", *AGENTS}
        assert message["confidence"] in {None, "low", "medium", "high"}
        if message["kind"] in {"finding", "answer"}:
            assert message["evidence"], message["text"]
    assert messages[0]["kind"] == "plan" and messages[-1]["kind"] == "summary"
    assert {m["agent"] for m in messages} == set(AGENTS)


def test_agents_say_plain_numbers_with_ranges_and_disclaimers(full_run):
    land = by_agent(full_run, "land", "finding")[0]["text"]
    assert land.startswith("Your plot is 2.13 ha") and "Karnataka, India" in land
    assert (
        "is cropland" in land and "ESA WorldCover 2021" in land and "The boundary is valid" in land
    )
    carbon = by_agent(full_run, "carbon", "finding")[0]
    assert carbon["text"].startswith("Estimated removal is ")
    assert "tCO₂e per year (central " in carbon["text"] and "IPCC Tier 1" in carbon["text"]
    assert carbon["text"].endswith("This is an estimate, not a carbon credit.")
    assert carbon["confidence"] == "medium"
    facts = carbon["facts"]
    assert facts["low"] <= facts["central"] <= facts["high"] and facts["certified"] is False
    summary = full_run["summary"]
    assert summary["estimate"]["central"] == facts["central"] and summary["readiness"] == 55
    assert summary["next_steps"] and summary["headline"].startswith("Plot PLT-DEMOIN")
    trees = by_agent(full_run, "trees")
    assert any(m["kind"] == "handoff" and m["to"] == "carbon" for m in trees)


def test_market_keeps_three_values_separate(full_run):
    text = by_agent(full_run, "market", "finding")[0]["text"]
    assert "Environmental benefit" in text and "Indicative carbon value" in text
    assert "Other farm income" in text and "never added together" in text
    assert "not guaranteed revenue" in text and "total" not in text.lower()


def test_market_adds_a_cost_scenario_only_from_the_users_costs(client):
    costs = {"sapling_per_tree": 60, "maintenance_per_ha_per_year": 4000}
    run = run_plan(client, "full-assessment", costs=costs)
    findings = by_agent(run, "market", "finding")
    assert len(findings) == 2  # the three values, then the cost scenario in its own message
    cost = findings[1]
    assert "break" not in findings[0]["text"].lower()
    assert "Your entered costs" in cost["text"] and "per tCO₂e" in cost["text"]
    assert "not revenue" in cost["text"]
    assert "planting per tree" in cost["text"] and "monitoring per year" in cost["text"]
    facts = cost["facts"]
    assert facts["not_entered"] == ["planting_per_tree", "monitoring_per_year"]
    assert facts["break_even_price_per_tco2e"]["central"] > 0
    assert guardrails(run)["values-separated"] == "pass"
    assert guardrails(run)["not-a-credit"] == "pass"
    # without costs, no cost message and no cost tool call
    plain = run_plan(client, "full-assessment")
    assert len(by_agent(plain, "market", "finding")) == 1
    asked = ask(client, "What does it cost and when does it break even?", costs=costs)
    assert asked["intent"]["intent"] == "value"
    assert len(by_agent(asked, "market", "finding")) == 2


def test_guardrails_run_and_pass_on_the_demo_plot(full_run):
    checks = guardrails(full_run)
    assert CONTRACT_GUARDRAILS == set(checks)
    for check in (
        "not-a-credit",
        "uncertainty-present",
        "provenance-present",
        "no-coordinates",
        "values-separated",
    ):
        assert checks[check] == "pass", full_run["guardrails"]
    assert checks["pending-parameters"] in {"pass", "warn"}  # demo parameters are still pending


def test_no_message_contains_the_plot_coordinates(client, full_run):
    plot = client.get("/api/v1/plots/PLT-DEMOIN").json()
    blob = json.dumps(full_run["messages"], ensure_ascii=False)
    for value in (plot["centroid"]["lat"], plot["centroid"]["lon"]):
        assert str(value) not in blob
        for decimals in (3, 4, 5, 6):
            assert f"{value:.{decimals}f}" not in blob
    for message in full_run["messages"]:
        structured = json.dumps([message["facts"], message["tool_calls"]])
        for key in ("lat", "lon", "geometry", "coordinates", "centroid", "bbox"):
            assert f'"{key}"' not in structured


# ----------------------------------------------------------------------------- storage
def test_runs_are_stored_and_listed(client, full_run):
    fetched = client.get(f"/api/v1/agents/runs/{full_run['run_id']}")
    assert fetched.status_code == 200 and fetched.json() == full_run
    items = client.get("/api/v1/agents/runs", params={"plot_id": "PLT-DEMOIN"}).json()["items"]
    row = next(r for r in items if r["run_id"] == full_run["run_id"])
    assert row["plan"] == {"id": "full-assessment", "title": "Full assessment"}
    assert (
        row["status"] == full_run["status"] and row["headline"] == full_run["summary"]["headline"]
    )
    assert "messages" not in row
    everything = client.get("/api/v1/agents/runs").json()["items"]
    assert full_run["run_id"] in {r["run_id"] for r in everything}


# ----------------------------------------------------------------------------- other plans
def test_quick_estimate(client):
    run = run_plan(client, "quick-estimate")
    assert run["status"] in {"completed", "completed-with-warnings"}
    assert [s["agent"] for s in run["steps"]] == QUICK
    assert not by_agent(run, "market") and not by_agent(run, "report")
    assert by_agent(run, "carbon", "finding")
    assert by_agent(run, "carbon", "handoff")[0]["to"] == "review"


def test_tree_age_check(client):
    run = run_plan(client, "tree-age-check", question="My mango trees are 60 years old")
    assert run["status"] in {"completed", "completed-with-warnings"}
    assert [s["agent"] for s in run["steps"]] == TREE_AGE
    policy = by_agent(run, "policy")
    assert policy[0]["text"].startswith("Initial screening for India")
    # the tree-age module may be absent in some installations: then a clear warning, never a crash
    assert len(policy) == 2 and policy[1]["kind"] in {"finding", "warning"}
    if policy[1]["kind"] == "finding":
        assert "60 years" in policy[1]["text"] and "credit" in policy[1]["text"].lower()
    assert run["messages"][-1]["kind"] == "answer"


def test_runs_are_deterministic(client):
    first, second = run_plan(client, "quick-estimate"), run_plan(client, "quick-estimate")
    assert [m["text"] for m in first["messages"]] == [m["text"] for m in second["messages"]]
    assert first["run_id"] != second["run_id"]


# ----------------------------------------------------------------------------- ask
def test_ask_routes_a_what_if_question(client):
    run = ask(client, "How much carbon if I add 200 trees?")
    assert run["plan"]["id"] == "quick-estimate"
    assert run["intent"]["intent"] == "what_if" and run["intent"]["tree_change"] == 200
    assert run["question"] == "How much carbon if I add 200 trees?"
    what_if = by_agent(run, "carbon", "finding")[1]
    assert what_if["text"].startswith(
        "What if you add 200 trees? With 620 mango trees instead of 420"
    )
    assert what_if["text"].endswith("This is a scenario, not a carbon credit.")
    answer = run["messages"][-1]
    assert answer["kind"] == "answer" and answer["agent"] == "coordinator"
    assert "With 620 mango trees" in answer["text"] and "not carbon credits" in answer["text"]
    assert guardrails(run)["uncertainty-present"] == "pass"
    assert guardrails(run)["not-a-credit"] == "pass"


def test_ask_in_hindi_and_german(client):
    hindi = ask(client, "मेरे खेत में कितना कार्बन है?", locale="hi")
    assert hindi["intent"]["intent"] == "carbon" and hindi["plan"]["id"] == "quick-estimate"
    assert hindi["locale"] == "hi" and "English for now" in hindi["messages"][0]["text"]
    german = ask(client, "Wie viel Kohlenstoff, wenn ich 200 Bäume pflanze?", locale="de")
    assert german["intent"]["intent"] == "what_if" and german["intent"]["tree_change"] == 200


def test_ask_redacts_coordinates_in_the_question(client):
    run = ask(client, "How much carbon does my farm at 13.2923, 77.5384 store?")
    assert "[location removed]" in run["question"]
    blob = json.dumps(run, ensure_ascii=False)
    assert "13.2923" not in blob and "77.5384" not in blob
    assert guardrails(run)["no-coordinates"] == "pass"


# ----------------------------------------------------------------------------- degraded runs
def test_plot_without_inventory_skips_what_needs_trees(client, square):
    plot = client.post("/api/v1/plots", json={"name": "Empty field", "geometry": square}).json()
    run = run_plan(client, "full-assessment", plot_id=plot["plot_id"])
    statuses = {s["agent"]: s["status"] for s in run["steps"][1:-1]}
    assert statuses["trees"] == "warning"
    assert {statuses[a] for a in ("carbon", "market", "review", "report")} == {"skipped"}
    assert statuses["land"] == "done" and statuses["policy"] == "done"
    assert run["status"] == "completed-with-warnings"
    assert (
        run["summary"]["estimate"] is None
        and "no carbon estimate yet" in run["summary"]["headline"]
    )
    assert run["summary"]["next_steps"][0].startswith("Add a tree inventory")
    assert "carbon agent skipped" in run["messages"][-1]["text"]
    # deleting the plot deletes its runs
    assert client.delete(f"/api/v1/plots/{plot['plot_id']}").status_code == 204
    assert client.get(f"/api/v1/agents/runs/{run['run_id']}").status_code == 404


def test_a_failing_service_becomes_a_warning_step(client, monkeypatch):
    ctx = client.app.state.context

    def broken_screen(*args: object, **kwargs: object) -> dict:
        raise RuntimeError("policy engine unavailable")

    monkeypatch.setattr(ctx.policy, "screen", broken_screen)
    run = run_plan(client, "full-assessment")
    step = next(s for s in run["steps"] if s["agent"] == "policy")
    assert step["status"] == "warning"
    warning = by_agent(run, "policy")[0]
    assert warning["kind"] == "warning" and "RuntimeError" in warning["text"]
    assert warning["tool_calls"][0]["status"] == "error"
    assert run["status"] == "completed-with-warnings" and run["messages"][-1]["kind"] == "summary"
    assert next(s for s in run["steps"] if s["agent"] == "market")["status"] == "done"


# ----------------------------------------------------------------------------- errors
def test_unknown_plot_and_run_are_404(client):
    resp = client.post("/api/v1/plots/PLT-NOPE/agents/run", json={})
    assert resp.status_code == 404 and resp.headers["content-type"].startswith(
        "application/problem+json"
    )
    assert resp.json()["type"].endswith("plot-not-found")
    resp = client.get("/api/v1/agents/runs/RUN-NOPE")
    assert resp.status_code == 404 and resp.json()["type"].endswith("agent-run-not-found")
    assert client.get("/api/v1/agents/runs", params={"plot_id": "PLT-NOPE"}).status_code == 404
    assert (
        client.post(
            "/api/v1/agents/ask", json={"question": "carbon?", "plot_id": "PLT-NOPE"}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "body",
    [
        {"plan": "everything"},
        {"plan": "quick-estimate", "question": "x" * 501},
        {"plan": "quick-estimate", "locale": "english"},
        {"plan": "quick-estimate", "unexpected": True},
    ],
)
def test_bad_run_bodies_are_422(client, body):
    resp = client.post("/api/v1/plots/PLT-DEMOIN/agents/run", json=body)
    assert resp.status_code == 422 and resp.json()["type"].endswith("validation-error")


def test_bad_questions_are_422(client):
    assert (
        client.post(
            "/api/v1/agents/ask", json={"question": "   ", "plot_id": "PLT-DEMOIN"}
        ).status_code
        == 422
    )
    assert client.post("/api/v1/agents/ask", json={"plot_id": "PLT-DEMOIN"}).status_code == 422
    missing_plot = client.post("/api/v1/agents/ask", json={"question": "How much carbon?"})
    assert missing_plot.status_code == 422 and missing_plot.json()["type"].endswith("plot-required")


# ----------------------------------------------------------------------------- settings
@pytest.fixture
def make_client() -> Iterator:
    clients: list[TestClient] = []

    def factory(**env: object) -> TestClient:
        settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False, **env)  # type: ignore[call-arg]
        client = TestClient(create_app(settings))
        client.__enter__()
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


def test_api_key_is_required_for_agent_runs_when_configured(make_client):
    client = make_client(ATLAS_API_KEYS="secret-1")
    url = "/api/v1/plots/PLT-DEMOIN/agents/run"
    assert client.post(url, json={"plan": "quick-estimate"}).status_code == 401
    assert client.post(url, json={}, headers={"X-API-Key": "nope"}).status_code == 403
    assert (
        client.post(
            url, json={"plan": "quick-estimate"}, headers={"X-API-Key": "secret-1"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/agents/ask", json={"question": "carbon?", "plot_id": "PLT-DEMOIN"}
        ).status_code
        == 401
    )
    assert client.get("/api/v1/agents").status_code == 200  # reads stay open
    assert client.get("/api/v1/agents/runs").status_code == 200


class FakeLLM:
    """Stands in for an OpenAI-compatible server (no network in tests)."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.name = f"fake/{mode}"
        self.prompts: list[str] = []

    def complete(
        self, messages: Sequence, *, max_tokens: int = 300, temperature: float = 0.0
    ) -> str:
        self.prompts.append(json.dumps([m.to_dict() for m in messages], ensure_ascii=False))
        message = json.loads(messages[-1].content)["message"]
        if self.mode == "echo":
            return f"In plain words: {message}"
        return "About 99 tCO₂e per year, trust me."


@pytest.mark.parametrize("mode", ["echo", "liar"])
def test_optional_llm_only_rephrases_and_is_checked(make_client, monkeypatch, mode):
    fake = FakeLLM(mode)
    monkeypatch.setattr("app.agents.service.build_provider", lambda settings: fake)
    client = make_client(
        ATLAS_AGENT_REASONER="llm", LLM_API_BASE_URL="http://llm.invalid/v1", LLM_MODEL="tiny"
    )
    framework = client.get("/api/v1/agents").json()["framework"]
    assert framework["reasoner"] == "llm" and framework["llm_enabled"] is True
    run = run_plan(client, "quick-estimate")
    assert run["reasoner"] == {"mode": "llm", "llm_enabled": True, "provider": f"fake/{mode}"}
    carbon = by_agent(run, "carbon", "finding")[0]["text"]
    assert carbon.endswith("This is an estimate, not a carbon credit.")  # pinned, never rephrased
    llm_check = next(g for g in run["guardrails"] if g["id"] == "llm-rephrase")
    if mode == "echo":
        assert carbon.startswith("In plain words: Estimated removal is ")
        assert llm_check["status"] == "pass"
    else:
        assert carbon.startswith("Estimated removal is ") and "99" not in carbon
        assert llm_check["status"] == "warn" and run["status"] == "completed-with-warnings"
    prompts = " ".join(fake.prompts)
    assert fake.prompts and "13.29" not in prompts and "77.53" not in prompts
    assert "not a carbon credit" not in prompts
    assert by_agent(run, "coordinator", "plan")[0]["text"].startswith("Plan “Quick estimate”")
