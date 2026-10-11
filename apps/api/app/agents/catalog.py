"""The team: which agents exist, in which order, and how they describe themselves.

``GET /agents`` returns :func:`catalog`; ``docs/agents/catalog.md`` documents
the same metadata (a test keeps the two in step). To add an agent, write its
module, then add its class to :data:`AGENT_TYPES` (see docs/agents/README.md,
"How to add a new agent").
"""

from __future__ import annotations

from typing import Any

from app.agents.carbon import CarbonAgent
from app.agents.coordinator import CoordinatorAgent
from app.agents.imagery import ImageryAgent
from app.agents.land import LandAgent
from app.agents.market import MarketAgent
from app.agents.plans import PLANS
from app.agents.policy import PolicyAgent
from app.agents.report import ReportAgent
from app.agents.review import ReviewAgent
from app.agents.trees import TreesAgent
from app.core.config import Settings
from carboncreditbuy_agents import FRAMEWORK_NAME, Agent, __version__

AGENT_TYPES: tuple[type[Agent], ...] = (
    CoordinatorAgent,
    LandAgent,
    ImageryAgent,
    TreesAgent,
    CarbonAgent,
    PolicyAgent,
    MarketAgent,
    ReviewAgent,
    ReportAgent,
)


def build_team() -> list[Agent]:
    """One instance of every agent. Agents keep no state between runs."""
    return [agent_type() for agent_type in AGENT_TYPES]


def reasoner_mode(settings: Settings) -> str:
    """``"llm"`` only when the LLM reasoner is requested *and* configured; else ``"template"``."""
    return "llm" if settings.llm_enabled else "template"


def catalog(settings: Settings) -> dict[str, Any]:
    """The ``GET /agents`` payload (contract shape)."""
    return {
        "framework": {
            "name": FRAMEWORK_NAME,
            "version": __version__,
            "reasoner": reasoner_mode(settings),
            "llm_enabled": settings.llm_enabled,
        },
        "agents": [agent.card() for agent in build_team()],
        "plans": [plan.to_dict() for plan in PLANS.values()],
    }


def who_says_what() -> str:
    """The "Who says what" table as Markdown (used to keep the docs honest)."""
    rows = [
        "| Agent | Role | Tools | What it says | Reads | Writes |",
        "|---|---|---|---|---|---|",
    ]
    for agent in build_team():
        tools = ", ".join(f"`{t.name}`" for t in agent.tools) or "—"
        reads = ", ".join(f"`{r}`" for r in agent.reads) or "—"
        writes = ", ".join(f"`{w}`" for w in agent.writes) or "—"
        rows.append(
            f"| **{agent.title}** (`{agent.id}`) | {agent.role} | {tools} | {agent.says} | "
            f"{reads} | {writes} |"
        )
    return "\n".join(rows)
