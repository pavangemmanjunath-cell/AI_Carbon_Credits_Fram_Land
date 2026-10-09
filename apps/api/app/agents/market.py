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
from app.agents.tools import market_scenarios
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
    tools = (market_scenarios,)
    reads = ("plot_id", "estimate")
    writes = ("market",)

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
        return [
            ctx.say(
                "finding",
                " ".join(wording.market_sentences(market, estimate["estimate"])),
                facts=facts,
                evidence=evidence,
                disclaimer=market.get("disclaimer"),
            )
        ]
