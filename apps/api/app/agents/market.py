"""Market agent: three separate values — never added together.

CLAUDE.md asks for three values side by side: the environmental benefit
(tCO₂e per year), the indicative carbon value (a price *scenario*, not a
credit) and other farm income. This agent writes each in its own sentence,
keeps them in separate facts, and the ``values-separated`` guardrail checks
that nobody — including an optional LLM — adds them up.
"""

from __future__ import annotations

from typing import Any

from app.agents import wording
from app.agents.tools import cost_scenario, market_scenarios
from atlas_agents import Agent, AgentMessage, Evidence, RunContext


class MarketAgent(Agent):
    id = "market"
    title = "Market agent"
    role = (
        "Puts configured scenario prices on the carbon estimate and lists the other farm "
        "income sources for the region."
    )
    says = (
        "Three separate values — environmental benefit (tCO₂e per year), indicative carbon "
        "value (a price scenario, not a credit) and other farm income — never added together."
    )
    tools = (market_scenarios, cost_scenario)
    reads = ("plot_id", "estimate", "costs")
    writes = ("market", "cost")

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        estimate = ctx.read("estimate")
        result = ctx.use(
            market_scenarios, plot_id=ctx.read("plot_id"), estimate_id=estimate["estimate_id"]
        )
        if not result.ok:
            return [ctx.warn(f"Value scenarios are not available ({result.reason}).")]
        market = result.value
        ctx.write("market", market)
        scenarios = {s["id"]: s for s in market["scenarios"]}
        facts: dict[str, Any] = {
            "environmental_benefit_tco2e_per_year": {
                k: estimate["estimate"][k] for k in ("low", "central", "high")
            },
            "indicative_value_per_year": {
                "currency": market["currency"],
                **{key: s["value_per_year"]["central"] for key, s in scenarios.items()},
            },
            "price_per_tco2e": {key: s["price_per_tco2e"] for key, s in scenarios.items()},
            "other_farm_income": [i["label"] for i in market["other_income"]],
            "price_basis_status": market["basis"]["verification_status"],
        }
        basis = market["basis"]
        evidence = [
            Evidence(
                f"Carbon price scenarios ({basis.get('source')}, as of {basis.get('as_of')}, "
                f"{basis.get('verification_status')})",
                "market-scenarios",
            ),
            *wording.evidence_from_references(basis.get("references"), "market-reference"),
        ]
        messages = [
            ctx.say(
                "finding",
                " ".join(wording.market_sentences(market, estimate["estimate"])),
                facts=facts,
                evidence=evidence,
                disclaimer=market.get("disclaimer"),
            )
        ]
        costs = ctx.read("costs")
        if costs:
            messages.extend(self._cost(ctx, costs))
        return messages

    def _cost(self, ctx: RunContext, costs: dict[str, Any]) -> list[AgentMessage]:
        result = ctx.use(cost_scenario, plot_id=ctx.read("plot_id"), costs=costs)
        if not result.ok:
            return [ctx.warn(f"The cost scenario is not available ({result.reason}).")]
        cost = result.value
        ctx.write("cost", cost)
        facts = {
            "total_cost": cost["total_cost"],
            "currency": cost["currency"],
            "horizon_years": cost["horizon_years"],
            "break_even_price_per_tco2e": cost["break_even_price_per_tco2e"],
            "not_entered": cost["not_entered"],
        }
        evidence = [
            Evidence("Costs entered by you (no built-in cost values)", "user-costs"),
            Evidence("Cumulative removal from the carbon engine's simulation", "simulation"),
        ]
        return [
            ctx.say(
                "finding",
                " ".join(wording.cost_sentences(cost)),
                facts=facts,
                evidence=evidence,
                disclaimer=cost.get("disclaimer"),
            )
        ]
