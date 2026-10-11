"""AgentService: the one class the API router talks to.

It wires the generic framework (``carboncreditbuy_agents``) to CarbonCreditBuy:

* builds the team (:mod:`app.agents.catalog`) and the orchestrator once;
* picks a reasoner per run — templates by default, an LLM only when
  ``ATLAS_AGENT_REASONER=llm`` and ``LLM_API_BASE_URL`` + ``LLM_MODEL`` are set;
* adds the six CarbonCreditBuy guardrails, including a search for this plot's own
  coordinates;
* stores every run through the generic repository record API
  (``kind="agent-run"``, linked to the plot, so deleting the plot deletes it).

Cached per application with ``service(ctx, "agents", lambda: AgentService(ctx))``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from app.agents.catalog import build_team, catalog
from app.agents.plans import DEFAULT_PLAN, PLANS
from app.agents.wording import RUN_DISCLAIMER
from app.core.config import Settings
from app.core.errors import ProblemError
from app.services.common import base_provenance
from carboncreditbuy_agents import (
    FRAMEWORK_NAME,
    Blackboard,
    Guardrail,
    GuardrailInput,
    GuardrailResult,
    LLMReasoner,
    Orchestrator,
    Reasoner,
    Route,
    RunResult,
    TemplateReasoner,
    __version__,
    check_no_coordinates,
    check_not_a_credit,
    check_pending_parameters,
    check_provenance,
    check_uncertainty,
    check_values_separated,
    default_router,
    new_run_id,
)
from carboncreditbuy_agents.llm import LLMProvider, OpenAICompatibleProvider, redact_text
from carboncreditbuy_agents.llm.redaction import sensitive_number_strings

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

log = logging.getLogger("carboncreditbuy.agents")

RUN_KIND = "agent-run"
"""Record kind used with ``Repository.save_record`` / ``list_records``."""
LIST_LIMIT = 50


def build_provider(settings: Settings) -> LLMProvider | None:
    """The optional LLM client — ``None`` unless the reasoner is ``llm`` and fully configured."""
    if not settings.llm_enabled:
        return None
    return OpenAICompatibleProvider.from_settings(
        reasoner=settings.atlas_agent_reasoner,
        base_url=settings.llm_api_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def _carbon_records(board: Blackboard) -> list[tuple[str, Mapping[str, Any] | None]]:
    """Blackboard records that carry carbon numbers (and therefore ``certified``)."""
    return [
        ("the estimate", board.get("estimate")),
        ("the what-if", board.get("what_if_result")),
        ("the tree-age result", board.get("tree_age")),
    ]


def guardrails_for(plot: Mapping[str, Any]) -> list[Guardrail]:
    """The six CarbonCreditBuy guardrails, bound to this plot's private coordinates."""
    centroid = plot.get("centroid") or {}
    private_numbers = [v for v in (centroid.get("lat"), centroid.get("lon")) if v is not None]
    private_numbers += list(plot.get("bbox") or [])
    sensitive = sensitive_number_strings(private_numbers)

    def uncertainty(run: GuardrailInput) -> GuardrailResult:
        estimate = run.board.get("estimate") or {}
        what_if = run.board.get("what_if_result") or {}
        tree_age = run.board.get("tree_age") or {}
        return check_uncertainty(
            ranges=[
                ("estimate", estimate.get("estimate")),
                ("stock", estimate.get("stock")),
                ("what-if", what_if.get("scenario")),
                ("what-if baseline", what_if.get("baseline")),
                ("tree-age stored", tree_age.get("stored_now")),
                ("tree-age annual", tree_age.get("annual_now")),
            ],
            confidences=[("estimate", estimate.get("confidence"))] if estimate else [],
        )

    def pending(run: GuardrailInput) -> GuardrailResult:
        estimate = run.board.get("estimate")
        return check_pending_parameters(estimate.get("parameters") if estimate else None)

    return [
        Guardrail(
            "not-a-credit",
            lambda run: check_not_a_credit(
                [m.text for m in run.messages],
                _carbon_records(run.board),
                run_certified=False,
                disclaimer=RUN_DISCLAIMER,
            ),
        ),
        Guardrail("uncertainty-present", uncertainty),
        Guardrail(
            "provenance-present",
            lambda run: check_provenance(run.messages, _carbon_records(run.board)),
        ),
        Guardrail(
            "no-coordinates",
            lambda run: check_no_coordinates(run.messages, sensitive_strings=sensitive),
        ),
        Guardrail("pending-parameters", pending),
        Guardrail("values-separated", lambda run: check_values_separated(run.messages)),
    ]


class AgentService:
    """Runs agent plans for plots and stores the transcripts."""

    def __init__(self, app: AppContext) -> None:
        self.app = app
        self.orchestrator = Orchestrator(build_team())
        for plan in PLANS.values():
            self.orchestrator.check_plan(plan)
        self.router = default_router()
        self._provider: LLMProvider | None = None
        self._provider_ready = False

    # ------------------------------------------------------------------------ catalog
    def catalog(self) -> dict[str, Any]:
        return catalog(self.app.settings)

    # ------------------------------------------------------------------------ runs
    def run(
        self,
        plot_id: str,
        plan: str = DEFAULT_PLAN,
        question: str | None = None,
        locale: str = "en",
        costs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run ``plan`` on a plot. A question, if given, is answered at the end."""
        plot = self.app.plots.require(plot_id)
        if plan not in PLANS:
            raise ProblemError(
                422,
                f"Unknown plan {plan!r}; use one of {', '.join(PLANS)}.",
                type_slug="unknown-plan",
            )
        route = self.router.route(question) if question else None
        return self._execute(plot, plan, question, locale, route, costs)

    def ask(
        self,
        question: str,
        plot_id: str | None,
        locale: str = "en",
        costs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Answer a free-text question: the intent router picks the plan."""
        if not plot_id:
            raise ProblemError(
                422,
                "plot_id is required: the agents answer questions about one plot.",
                type_slug="plot-required",
            )
        plot = self.app.plots.require(plot_id)
        route = self.router.route(question)
        return self._execute(plot, route.plan, question, locale, route, costs)

    def get_run(self, run_id: str) -> dict[str, Any]:
        record = self.app.repo.get_record(RUN_KIND, run_id)
        if record is None:
            raise ProblemError(
                404, f"Agent run {run_id} was not found.", type_slug="agent-run-not-found"
            )
        return record

    def list_runs(self, plot_id: str | None = None) -> dict[str, Any]:
        if plot_id is not None:
            self.app.plots.require(plot_id)
        records = self.app.repo.list_records(RUN_KIND, plot_id=plot_id, limit=LIST_LIMIT)
        return {"items": [self._row(record) for record in records]}

    # ------------------------------------------------------------------------ internals
    def _reasoner(self) -> Reasoner:
        """A fresh reasoner per run (the LLM reasoner counts accepted/rejected rephrasings)."""
        if not self._provider_ready:
            try:
                self._provider = build_provider(self.app.settings)
            except Exception as exc:  # e.g. httpx missing: stay deterministic
                log.warning("LLM provider unavailable (%s); using templates", type(exc).__name__)
                self._provider = None
            self._provider_ready = True
        if self._provider is None:
            return TemplateReasoner()
        return LLMReasoner(self._provider)

    def _execute(
        self,
        plot: Mapping[str, Any],
        plan_id: str,
        question: str | None,
        locale: str,
        route: Route | None,
        costs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        plan = PLANS[plan_id]
        safe_question = redact_text(question) if question else None
        inputs: dict[str, Any] = {
            "plot_id": plot["plot_id"],
            "locale": locale,
            "mode": self.app.settings.atlas_mode,
        }
        if safe_question:
            inputs["question"] = safe_question
        if route is not None:
            inputs["intent"] = route.to_dict()
            if route.tree_change:
                inputs["what_if"] = {"change": route.tree_change}
            if route.age_years is not None:
                inputs["age_years"] = route.age_years
        if costs and any(v is not None for v in costs.values()):
            inputs["costs"] = dict(costs)
        result = self.orchestrator.run(
            plan,
            inputs=inputs,
            deps=self.app,
            reasoner=self._reasoner(),
            guardrails=guardrails_for(plot),
            locale=locale,
            run_id=new_run_id(),
        )
        record = self._record(plot, result, safe_question, locale, route)
        self.app.repo.save_record(RUN_KIND, record["run_id"], record, plot_id=plot["plot_id"])
        self.app.repo.audit(
            "agents.run",
            plot["plot_id"],
            {"run_id": record["run_id"], "plan": plan.id, "status": record["status"]},
        )
        return record

    def _record(
        self,
        plot: Mapping[str, Any],
        result: RunResult,
        question: str | None,
        locale: str,
        route: Route | None,
    ) -> dict[str, Any]:
        run = result.to_dict()
        summary = result.board.get("summary") or {
            "headline": "The run ended without a summary.",
            "estimate": None,
            "readiness": None,
            "next_steps": [],
        }
        reasoner = dict(run["reasoner"])
        reasoner["llm_enabled"] = self.app.settings.llm_enabled
        return {
            "run_id": run["run_id"],
            "plot_id": plot["plot_id"],
            "plan": run["plan"],
            "status": run["status"],
            "reasoner": reasoner,
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
            "duration_ms": run["duration_ms"],
            "steps": run["steps"],
            "messages": run["messages"],
            "summary": {**summary, "certified": False},
            "guardrails": run["guardrails"],
            "certified": False,
            "disclaimer": RUN_DISCLAIMER,
            "provenance": self._provenance(result),
            # Additions beyond the contract, for the learning view:
            "question": question,
            "locale": locale,
            "intent": route.to_dict() if route else None,
            "blackboard": run["blackboard"],
        }

    def _provenance(self, result: RunResult) -> dict[str, Any]:
        board = result.board
        estimate = board.get("estimate") or {}
        sources: list[dict[str, Any]] = []
        seen: set[tuple[Any, Any]] = set()
        for key in (
            "estimate",
            "landcover",
            "climate",
            "vegetation",
            "detection",
            "what_if_result",
            "tree_age",
        ):
            for src in (board.get(key) or {}).get("sources") or []:
                marker = (src.get("id"), src.get("label"))
                if marker in seen:
                    continue
                seen.add(marker)
                sources.append(
                    {
                        "id": src.get("id"),
                        "name": src.get("label"),
                        "version": src.get("version"),
                        "license": src.get("license"),
                        "url": src.get("url"),
                    }
                )
        provenance = base_provenance(self.app.settings.atlas_mode, sources)
        provenance["model"] = estimate.get("model")
        provenance["parameter_set"] = estimate.get("parameter_set")
        provenance["agents"] = {
            "framework": FRAMEWORK_NAME,
            "version": __version__,
            "plan": result.plan.id,
            "reasoner": result.reasoner_mode,
        }
        provenance["notes"] = [
            "Numbers come from the carbon, policy and market engines; agent text is built from "
            "them by deterministic templates"
            + (
                " and rephrased by an LLM only where every number still matched."
                if result.reasoner_mode == "llm"
                else "."
            )
        ]
        return provenance

    @staticmethod
    def _row(record: Mapping[str, Any]) -> dict[str, Any]:
        """A run summary for listings."""
        plan = record.get("plan") or {}
        return {
            "run_id": record.get("run_id"),
            "plot_id": record.get("plot_id"),
            "plan": {"id": plan.get("id"), "title": plan.get("title")},
            "status": record.get("status"),
            "started_at": record.get("started_at"),
            "finished_at": record.get("finished_at"),
            "duration_ms": record.get("duration_ms"),
            "headline": (record.get("summary") or {}).get("headline"),
            "question": record.get("question"),
            "reasoner": (record.get("reasoner") or {}).get("mode"),
        }
