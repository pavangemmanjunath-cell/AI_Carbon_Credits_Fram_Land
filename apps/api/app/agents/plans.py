"""The three plans from the API contract (docs/architecture/api-contract.md, "Agents").

Plans are data. Each one is an ordered list of agent ids with a few rules:

* a specialist whose input is missing **skips itself** (``skip_if=missing(...)``) —
  no inventory → no carbon estimate → no market value and no report;
* the closing coordinator step **always runs** (``run_always=True``), so every
  run ends with a summary even when something failed earlier.

=====================  ==================================================================
``full-assessment``    coordinator → land → imagery → trees → carbon → policy → market →
                       review → report → coordinator
``quick-estimate``     coordinator → land → trees → carbon → review → coordinator
``tree-age-check``     coordinator → trees → carbon → policy → review → coordinator
=====================  ==================================================================
"""

from __future__ import annotations

from carboncreditbuy_agents import Plan, PlanStep, missing

NO_INVENTORY = missing(
    "inventory", reason="skipped: no tree inventory, so there is nothing to estimate"
)
NO_ESTIMATE_TO_PRICE = missing("estimate", reason="skipped: no carbon estimate to put a value on")
NO_ESTIMATE_TO_REVIEW = missing("estimate", reason="skipped: no carbon estimate to review")
NO_ESTIMATE_TO_REPORT = missing("estimate", reason="skipped: a report needs a carbon estimate")

FULL_ASSESSMENT = Plan(
    id="full-assessment",
    title="Full assessment",
    description=(
        "Everything the team can say about one plot: land, satellite vegetation, trees, "
        "carbon, programmes, value scenarios, a review and a report."
    ),
    steps=(
        PlanStep("coordinator", note="announce the plan"),
        PlanStep("land"),
        PlanStep("imagery"),
        PlanStep("trees"),
        PlanStep("carbon", skip_if=NO_INVENTORY),
        PlanStep("policy"),
        PlanStep("market", skip_if=NO_ESTIMATE_TO_PRICE),
        PlanStep("review", skip_if=NO_ESTIMATE_TO_REVIEW),
        PlanStep("report", skip_if=NO_ESTIMATE_TO_REPORT),
        PlanStep("coordinator", run_always=True, note="summarize"),
    ),
)

QUICK_ESTIMATE = Plan(
    id="quick-estimate",
    title="Quick estimate",
    description="The plot, its trees and the carbon estimate with a review — no report.",
    steps=(
        PlanStep("coordinator", note="announce the plan"),
        PlanStep("land"),
        PlanStep("trees"),
        PlanStep("carbon", skip_if=NO_INVENTORY),
        PlanStep("review", skip_if=NO_ESTIMATE_TO_REVIEW),
        PlanStep("coordinator", run_always=True, note="summarize"),
    ),
)

TREE_AGE_CHECK = Plan(
    id="tree-age-check",
    title="Tree-age check",
    description=(
        "For existing (often old) trees: their carbon by age and the rules that treat trees "
        "differently by age, next to the programme screening."
    ),
    steps=(
        PlanStep("coordinator", note="announce the plan"),
        PlanStep("trees"),
        PlanStep("carbon", skip_if=NO_INVENTORY),
        PlanStep("policy", note="programme screening + tree-age rules"),
        PlanStep("review", skip_if=NO_ESTIMATE_TO_REVIEW),
        PlanStep("coordinator", run_always=True, note="summarize"),
    ),
)

PLANS: dict[str, Plan] = {
    plan.id: plan for plan in (FULL_ASSESSMENT, QUICK_ESTIMATE, TREE_AGE_CHECK)
}
DEFAULT_PLAN = FULL_ASSESSMENT.id
