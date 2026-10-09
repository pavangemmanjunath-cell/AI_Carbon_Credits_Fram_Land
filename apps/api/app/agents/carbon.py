"""Carbon agent: estimated annual removal from the carbon engine, plus what-if scenarios.

This agent states numbers, so it is the strictest about how it says them:
every figure is a low–central–high range with a method and a confidence, and
every message ends with a pinned disclaimer that no reasoner may reword.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.agents import wording
from app.agents.tools import estimate_carbon, simulate_what_if
from atlas_agents import Agent, AgentMessage, Evidence, RunContext


def estimate_evidence(estimate: Mapping[str, Any]) -> list[Evidence]:
    """Methodology, model, parameter set and parameter sources of an estimate."""
    evidence: list[Evidence] = []
    methodology = estimate.get("methodology") or {}
    references = methodology.get("references") or []
    if methodology.get("name"):
        evidence.append(
            Evidence(
                str(methodology["name"]),
                str(methodology.get("id")),
                references[0].get("url") if references else None,
            )
        )
    model = estimate.get("model") or {}
    if model.get("id"):
        evidence.append(
            Evidence(
                f"Model {model['id']} v{model.get('version')} (Tier {model.get('tier')})",
                str(model["id"]),
            )
        )
    parameter_set = estimate.get("parameter_set") or {}
    if parameter_set.get("id"):
        evidence.append(
            Evidence(
                f"Parameter set {parameter_set['id']} v{parameter_set.get('version')} "
                f"({parameter_set.get('verification_status')})",
                str(parameter_set["id"]),
            )
        )
    sources = [s for s in estimate.get("sources") or [] if s.get("id") != "synthetic-demo"]
    evidence += wording.evidence_from_sources(sources)
    return evidence


class CarbonAgent(Agent):
    id = "carbon"
    title = "Carbon agent"
    role = (
        "Runs the carbon engine on the tree inventory and answers what-if questions with the "
        "Simulation Lab."
    )
    says = (
        "Estimated carbon removal per year as a low–central–high range with the method and "
        "confidence, and what-if scenarios — always 'an estimate, not a carbon credit'."
    )
    tools = (estimate_carbon, simulate_what_if)
    reads = ("plot_id", "inventory", "what_if")
    writes = ("estimate", "what_if_result")

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        plot_id = ctx.read("plot_id")
        messages: list[AgentMessage] = []

        result = ctx.use(estimate_carbon, plot_id=plot_id)
        estimate: Mapping[str, Any] | None = result.value if result.ok else None
        if estimate is not None:
            ctx.write("estimate", estimate)
            rng = estimate["estimate"]
            facts = {
                "estimate_id": estimate["estimate_id"],
                "low": rng["low"],
                "central": rng["central"],
                "high": rng["high"],
                "unit": rng["unit"],
                "confidence": estimate["confidence"],
                "model": (estimate.get("model") or {}).get("id"),
                "tier": (estimate.get("model") or {}).get("tier"),
                "methodology": (estimate.get("methodology") or {}).get("id"),
                "certified": estimate["certified"],
                "reused_stored_estimate": estimate["reused"],
            }
            messages.append(
                ctx.say(
                    "finding",
                    wording.carbon_sentence(estimate),
                    facts=facts,
                    evidence=estimate_evidence(estimate),
                    confidence=estimate["confidence"],
                    disclaimer=wording.NOT_A_CREDIT,
                )
            )
        elif result.status == "skipped":
            messages.append(ctx.warn(f"No carbon estimate: {result.reason}."))
        else:
            messages.append(
                ctx.warn(f"The carbon engine could not produce an estimate ({result.reason}).")
            )

        change = (ctx.read("what_if") or {}).get("change")
        if change:
            messages.extend(self._what_if(ctx, plot_id, int(change)))

        if estimate is not None:
            target = next((a for a in ("market", "review") if a in ctx.later_agents), None)
            if target:
                messages.append(
                    ctx.handoff(
                        target,
                        f"{target.capitalize()} agent: estimate {estimate['estimate_id']} is "
                        f"{wording.per_year(estimate['estimate'])}, confidence "
                        f"{estimate['confidence']}.",
                        facts={"estimate_id": estimate["estimate_id"]},
                    )
                )
        return messages

    def _what_if(self, ctx: RunContext, plot_id: str, change: int) -> list[AgentMessage]:
        result = ctx.use(simulate_what_if, plot_id=plot_id, change=change)
        if not result.ok:
            return [
                ctx.warn(f"I could not run the what-if for {change:+,} trees ({result.reason}).")
            ]
        sim = result.value
        ctx.write("what_if_result", sim)
        facts = {
            "tree_change": sim["change"],
            "tree_count_now": sim["tree_count_now"],
            "tree_count_new": sim["tree_count_new"],
            "baseline": sim["baseline"],
            "scenario": sim["scenario"],
            "difference_central": sim["difference_central"],
            "horizon_years": sim["horizon_years"],
            "climate_zone": sim["climate_zone"],
        }
        if sim.get("density_cap"):
            facts["density_cap"] = sim["density_cap"]
        evidence = [
            Evidence("Simulation Lab (POST /simulate, carbon engine tree-biomass)", "simulate"),
            *wording.evidence_from_sources(
                [s for s in sim.get("sources") or [] if s.get("id") != "synthetic-demo"]
            ),
        ]
        return [
            ctx.say(
                "finding",
                " ".join(wording.what_if_sentences(sim)),
                facts=facts,
                evidence=evidence,
                confidence=sim.get("confidence"),
                disclaimer=wording.SCENARIO_NOT_A_CREDIT,
            )
        ]
