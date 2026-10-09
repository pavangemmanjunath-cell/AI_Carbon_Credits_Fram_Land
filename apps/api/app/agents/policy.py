"""Policy agent: programme screening, and — in the tree-age check — the rules for old trees.

Everything this agent reports comes from configuration (``config/policies/``,
``config/tree-age/rules.yaml``) through the policy and tree-age services. It
never decides eligibility: statuses are "may apply", "needs an assessment" …
and the screening disclaimer is pinned to every message.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from app.agents import wording
from app.agents.tools import assess_tree_age, screen_programmes
from atlas_agents import Agent, AgentMessage, Evidence, RunContext

TREE_AGE_PLAN = "tree-age-check"


def programme_evidence(screening: Mapping[str, Any]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for programme in screening.get("programmes") or []:
        refs = programme.get("references") or []
        if refs:
            evidence.append(
                Evidence(str(refs[0].get("title")), str(programme.get("id")), refs[0].get("url"))
            )
        elif programme.get("url"):
            evidence.append(
                Evidence(
                    str(programme.get("programme")), str(programme.get("id")), programme["url"]
                )
            )
    return evidence


class PolicyAgent(Agent):
    id = "policy"
    title = "Policy agent"
    role = (
        "Screens the country's carbon and environmental programmes and, in the tree-age "
        "check, the rules that treat trees differently by age."
    )
    says = (
        "Which programmes might apply and what each still needs — an initial screening, never "
        "an eligibility decision; in the tree-age check also the age class, carbon by age and "
        "the age rules that apply."
    )
    tools = (screen_programmes, assess_tree_age)
    reads = ("plot_id", "inventory", "age_years")
    writes = ("programmes", "tree_age")

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        plot_id = ctx.read("plot_id")
        messages: list[AgentMessage] = []
        screening = ctx.use(screen_programmes, plot_id=plot_id)
        if screening.ok:
            ctx.write("programmes", screening.value)
            facts = {
                "country": screening.value["country"],
                "activity": screening.value["activity"],
                "programmes": [
                    {"id": p["id"], "status": p["status"], "kind": p["kind"]}
                    for p in screening.value["programmes"]
                ],
            }
            messages.append(
                ctx.say(
                    "finding",
                    wording.programmes_sentence(screening.value),
                    facts=facts,
                    evidence=programme_evidence(screening.value),
                    disclaimer=screening.value.get("disclaimer"),
                )
            )
        else:
            messages.append(ctx.warn(f"Programme screening is not available ({screening.reason})."))

        if ctx.plan.id == TREE_AGE_PLAN:
            messages.extend(self._tree_age(ctx, plot_id))
        return messages

    def _tree_age(self, ctx: RunContext, plot_id: str) -> list[AgentMessage]:
        inventory: Mapping[str, Any] = ctx.read("inventory") or {}
        age = ctx.read("age_years")
        age_source = "question"
        if age is None:
            age, age_source = inventory.get("age_years"), "inventory"
        if not inventory or age is None:
            return [
                ctx.warn(
                    "For the tree-age check I need the species, the number of trees and their "
                    "age — add a tree inventory for this plot."
                )
            ]
        dbh = inventory.get("average_dbh_cm")
        result = ctx.use(
            assess_tree_age,
            plot_id=plot_id,
            species_id=inventory["species_id"],
            age_years=int(age),
            tree_count=int(inventory["tree_count"]),
            # Girth (circumference) = π × diameter; the tree-age service takes girth.
            girth_cm=round(math.pi * float(dbh), 1) if dbh else None,
            height_m=inventory.get("average_height_m"),
        )
        if result.status == "skipped":
            return [
                ctx.warn(
                    f"Tree-age rules could not be checked: {result.reason}. The programme "
                    "screening above still applies."
                )
            ]
        if not result.ok:
            return [ctx.warn(f"The tree-age assessment failed ({result.reason}).")]
        assessment = {
            **result.value,
            "age_source": age_source,
            "inventory_age_years": inventory.get("age_years"),
        }
        ctx.write("tree_age", assessment)
        facts = {
            "age_years": assessment["age_years"],
            "age_source": age_source,
            "age_class": (assessment.get("age_class") or {}).get("id"),
            "stored_now": assessment.get("stored_now"),
            "annual_now": assessment.get("annual_now"),
            "credit_outlook": (assessment.get("credit_outlook") or {}).get("existing_trees"),
            "rules_applying": sum(1 for r in assessment["rules"] if r.get("applies")),
            "rules_pending": sum(
                1
                for r in assessment["rules"]
                if r.get("applies") and r.get("verification_status") == "pending"
            ),
        }
        evidence = wording.evidence_from_sources(assessment.get("sources")) or [
            Evidence("Tree-age rules (config/tree-age/rules.yaml)", "tree-age-rules")
        ]
        # The service's own disclaimer is pinned; add "not a credit" only if it lacks one.
        disclaimer = str(assessment.get("disclaimer") or wording.NOT_A_CREDIT)
        if "credit" not in disclaimer.lower():
            disclaimer = f"{wording.NOT_A_CREDIT} {disclaimer}"
        return [
            ctx.say(
                "finding",
                " ".join(wording.tree_age_sentences(assessment)),
                facts=facts,
                evidence=evidence,
                disclaimer=disclaimer,
            )
        ]
