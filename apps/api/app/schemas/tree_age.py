"""Request body of ``POST /tree-age/assess`` (see docs/architecture/api-contract.md §v0.2).

Lives in its own module so the shared ``schemas/requests.py`` stays untouched.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

#: where the trees stand; ``any`` = unknown (never excludes a rule)
TreeSetting = Literal["farm", "urban", "forest", "any"]
#: ISO 3166-2 code such as ``IN-KA`` (upper-cased before matching)
SUBDIVISION_PATTERN = r"^[A-Za-z]{2}-[A-Za-z0-9]{1,3}$"
_SUBDIVISION = re.compile(SUBDIVISION_PATTERN)


def normalise_subdivision(subdivision: str | None, country: str | None) -> str | None:
    """Upper-case an ISO 3166-2 code and check that it belongs to ``country``."""
    if subdivision is None or subdivision == "":
        return None
    code = subdivision.strip().upper()
    if not _SUBDIVISION.match(code):
        raise ValueError("subdivision must be an ISO 3166-2 code such as IN-KA")
    if country and code.split("-")[0] != country:
        raise ValueError(f"subdivision {code} is not inside country {country}")
    return code


class TreeAgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    subdivision: str | None = Field(None, max_length=6)
    setting: TreeSetting = "any"
    species_id: str = Field(..., min_length=1, max_length=64)
    age_years: int = Field(..., ge=0, le=300)
    tree_count: int = Field(..., ge=1, le=1_000_000)
    #: trunk circumference at 1.3 m; switches to the measured-tree path (DBH = girth / π)
    girth_cm: float | None = Field(None, ge=10, le=2000)
    height_m: float | None = Field(None, ge=0.5, le=120)
    #: optional: use the climate zone of this plot's latest analysis (nothing is read otherwise)
    plot_id: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{1,64}$")

    @field_validator("country")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    @field_validator("subdivision")
    @classmethod
    def _subdivision(cls, value: str | None, info: ValidationInfo) -> str | None:
        return normalise_subdivision(value, info.data.get("country"))

    @field_validator("girth_cm")
    @classmethod
    def _girth_needs_age(cls, value: float | None, info: ValidationInfo) -> float | None:
        if value is not None and info.data.get("age_years") == 0:
            raise ValueError(
                "girth_cm needs age_years of at least 1: a tree with a measured trunk is not "
                "newly planted"
            )
        return value
