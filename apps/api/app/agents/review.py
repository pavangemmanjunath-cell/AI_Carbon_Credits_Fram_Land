"""Review agent: a second pair of eyes on the carbon estimate before anyone relies on it."""

from __future__ import annotations

from typing import Any

from app.agents import wording
from app.agents.carbon import estimate_evidence
from app.agents.tools import review_estimate
from carboncreditbuy_agents import Agent, AgentMessage, RunContext


class ReviewAgent(Agent):
    id = "review"
    title = "Review agent"
    role = (
        "Double-checks the carbon estimate: range, unit, confidence, certified flag, sources, "
        "parameter verification status and missing evidence."
    )
    says = (
        "Whether the estimate carries a range, a confidence grade, its sources and "
        "certified: false; which parameters are still pending verification; and which evidence "
        "is still missing."
    )
    tools = (review_estimate,)
    reads = ("plot_id", "estimate")
    writes = ("review",)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        estimate = ctx.read("estimate")
        result = ctx.use(
            review_estimate, plot_id=ctx.read("plot_id"), estimate_id=estimate["estimate_id"]
        )
        if not result.ok:
            return [ctx.warn(f"I could not review the estimate ({result.reason}).")]
        review = result.value
        ctx.write("review", review)
        facts: dict[str, Any] = {
            "estimate_id": review["estimate_id"],
            "checks_failed": review["checks_failed"],
            "parameter_statuses": review["parameter_statuses"],
            "pending_parameters": review["pending_parameters"],
            "readiness_score": review["readiness_score"],
            "missing_evidence": review["missing_evidence"],
        }
        text = " ".join(wording.review_sentences(review))
        if review["checks_failed"]:
            return [ctx.warn(text, facts=facts, evidence=estimate_evidence(estimate))]
        return [
            ctx.say(
                "finding",
                text,
                facts=facts,
                evidence=estimate_evidence(estimate),
                confidence=estimate.get("confidence"),
            )
        ]
