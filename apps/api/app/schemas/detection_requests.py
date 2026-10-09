"""Request body of ``POST /plots/{plot_id}/detect`` (docs/architecture/api-contract.md §v0.2).

Lives in its own module so the shared ``schemas/requests.py`` stays untouched.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DetectionTarget = Literal["tree-cover"]


class DetectRequest(BaseModel):
    """What to detect and how sure a patch must look to be kept."""

    model_config = ConfigDict(extra="forbid")

    target: DetectionTarget = Field(
        default="tree-cover", description="Only tree-cover is available"
    )
    min_confidence: float = Field(
        default=0.5,
        ge=0,
        le=1,
        allow_inf_nan=False,
        description="Patches whose heuristic confidence is below this are dropped",
    )
