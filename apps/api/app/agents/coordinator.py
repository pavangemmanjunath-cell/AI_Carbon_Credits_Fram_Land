"""Coordinator: opens every run with the plan and closes it with a summary or an answer.

The coordinator is the only agent that may read the whole blackboard
(``reads = ("*",)``). It never calls a tool and never computes anything: at
the start it explains the plan; at the end it gathers what the specialists
wrote and turns it into a headline, next steps and — when you asked a
question — a direct answer built from the specialists' own sentences.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.agents import wording
from carboncreditbuy_agents import Agent, AgentMessage, Evidence, RunContext, StepRecord
from carboncreditbuy_agents.messages import MessageKind

INTENT_TOPICS = {
    "what_if": "a what-if with a different number of trees",
    "tree_age": "the age of existing trees",
    "report": "an assessment report",
    "value": "money values",
    "programmes": "carbon and environmental programmes",
    "vegetation": "satellite vegetation and tree cover",
    "land": "the plot and its land",
    "carbon": "carbon removal",
}
CLOSING_DISCLAIMER = (
    "These are estimates and screening results — not carbon credits, certifications or "
    "eligibility decisions; money values are scenarios, not guaranteed revenue."
)


def _quote(question: str) -> str:
    """“How much carbon?” — add a full stop only when the question has no end mark."""
    end = "" if question.rstrip()[-1:] in "?!.।" else "."
    return f"“{question}”{end}"


def _problem(record: StepRecord) -> str:
    """One line for the closing message, e.g. "carbon agent skipped — no tree inventory …"."""
    if record.status == "failed":
        return f"{record.agent} agent failed"
    return f"{record.agent} agent skipped — {record.summary.removeprefix('skipped: ').rstrip('.')}"


def _team(ctx: RunContext) -> str:
    """Name the specialists of the plan, e.g. "the Land, Imagery … agents"."""
    middle = [a for a in ctx.plan.agent_ids[1:-1] if a != "coordinator"]
    # Display names follow the agents' titles ("Tree agent" has the id "trees").
    display = {"trees": "Tree"}
    names = [display.get(a, a.capitalize()) for a in dict.fromkeys(middle)]
    return f"the {wording.join_words(names)} agent{'s' if len(names) != 1 else ''}"


class CoordinatorAgent(Agent):
    id = "coordinator"
    title = "Coordinator"
    role = (
        "Opens every run with the plan and closes it with a summary or the answer to your question."
    )
    says = (
        "At the start: which agents will work and in which order. At the end: the headline "
        "numbers, evidence readiness and next steps — or a direct answer to your question."
    )
    tools = ()
    reads = ("*",)
    writes = ("summary",)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        if ctx.is_first_step:
            return [self._open(ctx)]
        return [self._close(ctx)]

    # ------------------------------------------------------------------------- opening
    def _open(self, ctx: RunContext) -> AgentMessage:
        plot_id = ctx.read("plot_id")
        intent: Mapping[str, Any] = ctx.read("intent") or {}
        parts: list[str] = []
        question = ctx.read("question")
        if question:
            # The router chose the plan for /agents/ask; for /agents/run you chose it.
            chooser = "I chose" if intent.get("plan") == ctx.plan.id else "you chose"
            if intent.get("fallback"):
                parts.append(
                    f"You asked: {_quote(question)} I could not match it to a topic; "
                    f"{chooser} the {ctx.plan.title} plan."
                )
            else:
                topic = INTENT_TOPICS.get(str(intent.get("intent")), str(intent.get("intent")))
                matched = ", ".join(f"“{w}”" for w in intent.get("matched") or [])
                parts.append(
                    f"You asked: {_quote(question)} I read it as a question about {topic} "
                    f"(matched {matched}); {chooser} the {ctx.plan.title} plan."
                )
            change = (ctx.read("what_if") or {}).get("change")
            if change:
                verb = "adding" if change > 0 else "removing"
                parts.append(f"The Carbon agent will also simulate {verb} {abs(change):,} trees.")
        parts.append(
            f"Plan “{ctx.plan.title}” for plot {plot_id}: {_team(ctx)} work in that order, then "
            "I summarize."
        )
        parts.append(
            "Every number comes from the project's calculation engines; nothing here is a "
            "carbon credit."
        )
        if ctx.read("mode") == "demo":
            parts.append("Demo mode: observations are synthetic.")
        if ctx.locale.split("-")[0].lower() != "en" and ctx.reasoner.mode == "template":
            parts.append(
                "Agent messages are in English for now (translated templates are not available "
                "yet)."
            )
        facts = {
            "plot_id": plot_id,
            "plan": ctx.plan.id,
            "steps": ctx.plan.agent_ids,
            "intent": intent.get("intent"),
            "tree_change": (ctx.read("what_if") or {}).get("change"),
            "mode": ctx.read("mode"),
        }
        return ctx.say("plan", " ".join(parts), facts={k: v for k, v in facts.items() if v})

    # ------------------------------------------------------------------------- closing
    def _close(self, ctx: RunContext) -> AgentMessage:
        plot: Mapping[str, Any] = ctx.read("plot_summary") or {}
        estimate: Mapping[str, Any] = ctx.read("estimate") or {}
        headline = self._headline(ctx.read("plot_id"), plot, estimate)
        next_steps = self._next_steps(ctx, plot, estimate)
        readiness = (estimate.get("readiness") or {}).get("score")
        ctx.write(
            "summary",
            {
                "headline": headline,
                "estimate": estimate.get("estimate"),
                "readiness": readiness,
                "next_steps": next_steps,
                "certified": False,
            },
        )
        trouble = [_problem(r) for r in ctx.progress if r.status in ("skipped", "failed")]
        evidence = self._evidence(ctx)
        facts = {
            "headline": headline,
            "readiness": readiness,
            "next_steps": next_steps,
            "steps_with_problems": len(trouble),
        }
        question = ctx.read("question")
        kind: MessageKind
        if question:
            answer = self._answer(ctx)
            text = f"You asked: {_quote(question)} {' '.join(answer)} In short: {headline}"
            kind = "answer"
        else:
            text = f"Summary — {headline}"
            kind = "summary"
        if trouble:
            text += f" Not completed: {'; '.join(trouble)}."
        if next_steps:
            numbered = "; ".join(
                f"{i}) {wording.lower_first(s.rstrip('.'))}" for i, s in enumerate(next_steps, 1)
            )
            text += f" Next steps: {numbered}."
        return ctx.say(
            kind,
            text,
            facts=facts,
            evidence=evidence,
            confidence=estimate.get("confidence"),
            disclaimer=CLOSING_DISCLAIMER,
        )

    @staticmethod
    def _headline(plot_id: Any, plot: Mapping[str, Any], estimate: Mapping[str, Any]) -> str:
        where = ""
        if plot:
            place = wording.join_place(plot.get("state"), plot.get("country_label"))
            where = f" ({wording.num(plot['area_hectares'], 2)} ha" + (
                f", {place})" if place else ")"
            )
        if not estimate:
            return f"Plot {plot_id}{where}: no carbon estimate yet."
        text = (
            f"Plot {plot_id}{where}: estimated removal {wording.per_year(estimate['estimate'])}, "
            f"confidence {estimate.get('confidence')}"
        )
        score = (estimate.get("readiness") or {}).get("score")
        if score is not None:
            text += f", evidence readiness {score}/100"
        return text + "."

    @staticmethod
    def _next_steps(
        ctx: RunContext, plot: Mapping[str, Any], estimate: Mapping[str, Any]
    ) -> list[str]:
        steps: list[str] = []
        if plot and not plot.get("boundary_valid", True):
            steps.append("Redraw the plot boundary: it is not a valid polygon.")
        if not ctx.read("inventory"):
            steps.append("Add a tree inventory: species, number of trees and planting year.")
        for item in ((estimate.get("readiness") or {}).get("missing") or [])[:3]:
            steps.append(f"Collect {wording.lower_first(str(item.get('label')))}.")
        screening: Mapping[str, Any] = ctx.read("programmes") or {}
        for programme in screening.get("programmes") or []:
            if str(programme.get("status", "")).startswith("requires"):
                steps.append(
                    f"Ask {programme.get('authority')} whether {programme.get('programme')} "
                    "applies to your land (screening is not an eligibility decision)."
                )
                break
        return steps[:5]

    @staticmethod
    def _evidence(ctx: RunContext) -> list[Evidence]:
        estimate: Mapping[str, Any] = ctx.read("estimate") or {}
        methodology = estimate.get("methodology") or {}
        evidence: list[Evidence] = []
        if methodology.get("name"):
            refs = methodology.get("references") or [{}]
            evidence.append(
                Evidence(str(methodology["name"]), str(methodology.get("id")), refs[0].get("url"))
            )
        for key in ("landcover", "vegetation", "programmes", "market"):
            record: Mapping[str, Any] = ctx.read(key) or {}
            evidence.extend(wording.evidence_from_sources(record.get("sources"))[:1])
        if not evidence:
            evidence.append(Evidence(f"Plot {ctx.read('plot_id')}", "plot"))
        return evidence

    def _answer(self, ctx: RunContext) -> list[str]:
        """The focused answer, assembled from what the specialists wrote."""
        intent = str((ctx.read("intent") or {}).get("intent") or "general")
        board = {
            k: ctx.read(k)
            for k in (
                "plot_summary",
                "landcover",
                "vegetation",
                "detection",
                "inventory",
                "estimate",
                "what_if",
                "what_if_result",
                "programmes",
                "tree_age",
                "market",
                "report",
            )
        }
        estimate = board["estimate"]
        if intent == "what_if":
            if board["what_if_result"]:
                return wording.what_if_sentences(board["what_if_result"], lead=False)
            return ["I could not run the what-if: it needs a tree inventory for this plot."]
        if intent == "tree_age":
            if board["tree_age"]:
                return wording.tree_age_sentences(board["tree_age"])
            fallback = ["The tree-age rules could not be checked in this run."]
            return fallback + ([wording.carbon_sentence(estimate)] if estimate else [])
        if intent == "programmes" and board["programmes"]:
            return [wording.programmes_sentence(board["programmes"])]
        if intent == "value" and board["market"] and estimate:
            return wording.market_sentences(board["market"], estimate["estimate"])
        if intent == "vegetation" and board["vegetation"]:
            out = wording.vegetation_sentences(board["vegetation"])
            if board["detection"]:
                out.append(wording.detection_sentence(board["detection"]))
            return out
        if intent == "land" and board["plot_summary"]:
            out = [wording.plot_sentence(board["plot_summary"])]
            if board["landcover"]:
                out.append(wording.landcover_sentence(board["landcover"]))
            return out
        if intent == "report" and board["report"]:
            return [wording.report_sentence(board["report"])]
        if estimate:
            prefix = (
                ["I could not match your question to a topic, so the team ran a quick estimate."]
                if intent == "general"
                else []
            )
            return prefix + [wording.carbon_sentence(estimate)]
        return ["The team could not produce what this question needs; see the warnings above."]
