"""Request bodies of the geometry helper endpoints (docs/architecture/api-contract.md §v0.2).

They live in their own module so the shared ``schemas/requests.py`` stays untouched. Validation
messages never echo the submitted coordinates.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_LINE_VERTICES = 500
MAX_TEXT_CHARS = 20_000

AreaUnit = Literal["ha", "ac", "m2"]
PointShape = Literal["square", "circle"]


class AreaInput(BaseModel):
    """A land area with its unit; ``ha`` when the unit is left out."""

    model_config = ConfigDict(extra="forbid")

    value: float = Field(..., gt=0, allow_inf_nan=False, description="Area, greater than 0")
    unit: AreaUnit = Field(default="ha", description="ha (hectares), ac (acres) or m2")


class FromPointRequest(BaseModel):
    """``POST /geometry/from-point``: drop a pin and type the size."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    area: AreaInput
    shape: PointShape = "square"


class LineStringInput(BaseModel):
    """A GeoJSON ``LineString`` (``[lon, lat]`` positions)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["LineString"]
    coordinates: list[list[float]] = Field(..., min_length=2, max_length=MAX_LINE_VERTICES)


class FromLineRequest(BaseModel):
    """``POST /geometry/from-line``: draw a tree line (bund, boundary or roadside planting)."""

    model_config = ConfigDict(extra="forbid")

    line: LineStringInput
    width_m: float = Field(
        default=4.0, ge=1, le=50, allow_inf_nan=False, description="Strip width in m"
    )
    spacing_m: float = Field(
        default=5.0, ge=0.5, le=50, allow_inf_nan=False, description="Distance between trees in m"
    )


class ParseCoordinatesRequest(BaseModel):
    """``POST /geometry/parse-coordinates``: one point per line, typed or pasted."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)
