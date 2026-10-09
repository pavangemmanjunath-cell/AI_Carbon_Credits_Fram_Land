"""atlas_agents — a small, readable agent framework that is deterministic by default.

Built for AgriCarbon Atlas and for people who want to *learn* how agentic
systems are put together. Every concept is one short module:

=================  ===========================================================
``messages``       :class:`AgentMessage`, :class:`ToolCall`, :class:`Evidence`
``tools``          :class:`Tool`, :func:`tool`, :class:`ToolRegistry`
``blackboard``     :class:`Blackboard` — shared state that logs who wrote what
``agent``          :class:`Agent` and the per-step :class:`RunContext`
``plan``           :class:`Plan`, :class:`PlanStep`, :func:`missing`
``orchestrator``   :class:`Orchestrator` — runs a plan, never crashes on an agent
``reasoner``       :class:`TemplateReasoner` (default), :class:`LLMReasoner` (opt-in)
``guardrails``     deterministic checks over a finished run
``trace``          step records, timeline and :func:`render_transcript`
``intents``        a keyword intent router (question → plan)
``llm``            provider interface, OpenAI-compatible client, redaction
=================  ===========================================================

The framework has no third-party dependencies (``httpx`` only for the optional
LLM client) and knows nothing about carbon: the AgriCarbon agents live in
``apps/api/app/agents``. Start with ``docs/agents/README.md``.
"""

from atlas_agents.agent import Agent, RunContext, ToolNotAllowed
from atlas_agents.blackboard import (
    REQUEST,
    Blackboard,
    BlackboardAccessError,
    BoardWrite,
)
from atlas_agents.guardrails import (
    Guardrail,
    GuardrailInput,
    GuardrailResult,
    check_no_coordinates,
    check_not_a_credit,
    check_pending_parameters,
    check_provenance,
    check_uncertainty,
    check_values_separated,
    credit_claims,
)
from atlas_agents.intents import (
    DEFAULT_INTENTS,
    FALLBACK_INTENT,
    IntentRouter,
    IntentSpec,
    Route,
    default_router,
    parse_age_years,
    parse_tree_change,
)
from atlas_agents.messages import TEAM, AgentMessage, Evidence, ToolCall
from atlas_agents.orchestrator import Orchestrator, RunResult, new_run_id
from atlas_agents.plan import Plan, PlanStep, missing
from atlas_agents.reasoner import (
    LLMReasoner,
    Narration,
    NarrationRequest,
    Reasoner,
    TemplateReasoner,
    review_rephrase,
)
from atlas_agents.tools import Tool, ToolRegistry, ToolResult, ToolSkipped, summarize, tool
from atlas_agents.trace import RunTrace, StepRecord, render_transcript, utc_now_iso

__version__ = "0.1.0"
FRAMEWORK_NAME = "atlas-agents"

__all__ = [
    "DEFAULT_INTENTS",
    "FALLBACK_INTENT",
    "FRAMEWORK_NAME",
    "REQUEST",
    "TEAM",
    "Agent",
    "AgentMessage",
    "Blackboard",
    "BlackboardAccessError",
    "BoardWrite",
    "Evidence",
    "Guardrail",
    "GuardrailInput",
    "GuardrailResult",
    "IntentRouter",
    "IntentSpec",
    "LLMReasoner",
    "Narration",
    "NarrationRequest",
    "Orchestrator",
    "Plan",
    "PlanStep",
    "Reasoner",
    "Route",
    "RunContext",
    "RunResult",
    "RunTrace",
    "StepRecord",
    "TemplateReasoner",
    "Tool",
    "ToolCall",
    "ToolNotAllowed",
    "ToolRegistry",
    "ToolResult",
    "ToolSkipped",
    "__version__",
    "check_no_coordinates",
    "check_not_a_credit",
    "check_pending_parameters",
    "check_provenance",
    "check_uncertainty",
    "check_values_separated",
    "credit_claims",
    "default_router",
    "missing",
    "new_run_id",
    "parse_age_years",
    "parse_tree_change",
    "render_transcript",
    "review_rephrase",
    "summarize",
    "tool",
    "utc_now_iso",
]
