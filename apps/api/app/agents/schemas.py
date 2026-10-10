"""Request bodies for the agent endpoints (Pydantic v2, unknown fields rejected)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.requests import CostInputsBody

PlanId = Literal["full-assessment", "quick-estimate", "tree-age-check"]
"""Must match ``app.agents.plans.PLANS`` (a test checks it)."""

LOCALE_PATTERN = r"^[A-Za-z]{2}(?:[-_][A-Za-z]{2})?$"


def _clean_question(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    return value or None


class AgentRunRequest(BaseModel):
    """``POST /plots/{plot_id}/agents/run``"""

    model_config = ConfigDict(extra="forbid")
    plan: PlanId = "full-assessment"
    question: str | None = Field(default=None, max_length=500)
    locale: str = Field(default="en", min_length=2, max_length=5, pattern=LOCALE_PATTERN)
    costs: CostInputsBody | None = None
    """Your own costs; the Market agent then adds a cost scenario (break-even carbon price)."""

    @field_validator("question")
    @classmethod
    def _question(cls, value: str | None) -> str | None:
        return _clean_question(value)


class AgentAskRequest(BaseModel):
    """``POST /agents/ask`` — a deterministic intent router picks the plan."""

    model_config = ConfigDict(extra="forbid")
    question: str = Field(..., min_length=1, max_length=500)
    plot_id: str | None = Field(default=None, min_length=1, max_length=64)
    locale: str = Field(default="en", min_length=2, max_length=5, pattern=LOCALE_PATTERN)
    costs: CostInputsBody | None = None

    @field_validator("question")
    @classmethod
    def _question(cls, value: str) -> str:
        cleaned = _clean_question(value)
        if not cleaned:
            raise ValueError("question must not be blank")
        return cleaned
