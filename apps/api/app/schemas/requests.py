"""Request bodies (Pydantic v2). Field names follow docs/architecture/api-contract.md."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MeasurementSource = Literal[
    "user-reported", "satellite-derived", "government-data", "field-measured", "model-estimated"
]
ReportFormat = Literal["html", "json", "markdown", "pdf"]
Activity = Literal["tree_plantation", "agroforestry", "soil_carbon", "cropland_practice", "grazing"]


class PolygonGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]] = Field(..., min_length=1)


PlotSource = Literal[
    "manual-drawing",
    "upload",
    "import",
    "pin-and-area",
    "tree-line",
    "coordinates",
    "qgis-plugin",
    "api",
]
BoundaryQuality = Literal["exact", "approximate"]


class PlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field("Plot", max_length=120)
    country: str | None = Field(None, min_length=2, max_length=2)
    source: PlotSource = "manual-drawing"
    # "approximate" for boundaries built from a pin + size or a tree line: the
    # carbon estimate stays the same but confidence and readiness say so.
    boundary_quality: BoundaryQuality = "exact"
    geometry: PolygonGeometry

    @field_validator("country")
    @classmethod
    def _upper(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layers: list[Literal["landcover", "vegetation", "climate", "soil", "terrain"]] = Field(
        default_factory=lambda: ["landcover", "vegetation", "climate", "soil"]
    )
    years: list[int] | None = Field(None, min_length=1, max_length=10)

    @field_validator("years")
    @classmethod
    def _years(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        for year in value:
            if year < 2016 or year > 2100:
                raise ValueError("years must be between 2016 (Sentinel-2 L2A) and 2100")
        return sorted(set(value))


class TreeInventoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    species_id: str = Field(..., min_length=1, max_length=64)
    tree_count: int = Field(..., ge=1, le=10_000_000)
    plantation_year: int = Field(..., ge=1900, le=2100)
    average_dbh_cm: float | None = Field(None, gt=0, le=500)
    average_height_m: float | None = Field(None, gt=0, le=120)
    survival_rate: float | None = Field(None, gt=0, le=1)
    measurement_source: MeasurementSource = "user-reported"


class CarbonEstimateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inventory_id: str | None = None
    model: str = Field("tree-biomass", max_length=64)
    horizon_years: int | None = Field(None, ge=1, le=100)
    evidence: dict[str, bool] = Field(default_factory=dict)


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: ReportFormat = "html"
    language: str = Field("en", min_length=2, max_length=5)
    estimate_id: str | None = None


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country: str = Field(..., min_length=2, max_length=2)
    species_id: str = Field(..., min_length=1, max_length=64)
    tree_count: int = Field(..., ge=0, le=10_000_000)
    planting_year: int = Field(..., ge=1900, le=2100)
    horizon_years: int = Field(30, ge=1, le=100)
    survival_rate: float | None = Field(None, gt=0, le=1)
    area_hectares: float | None = Field(None, gt=0, le=10_000)
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    plot_id: str | None = None

    @field_validator("country")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


FORBIDDEN_EXPLAIN_KEYS = {
    "lat",
    "lon",
    "lng",
    "latitude",
    "longitude",
    "geometry",
    "coordinates",
    "polygon",
    "bbox",
    "centroid",
    "address",
    "owner",
    "name",
    "email",
    "phone",
}


def _scan_keys(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            if str(key).lower() in FORBIDDEN_EXPLAIN_KEYS:
                hits.append(f"{path}{key}")
            hits.extend(_scan_keys(inner, f"{path}{key}."))
    elif isinstance(value, list):
        for i, inner in enumerate(value):
            hits.extend(_scan_keys(inner, f"{path}{i}."))
    return hits


class ExplainRequest(BaseModel):
    """Only derived indicators are accepted — never coordinates or identities."""

    model_config = ConfigDict(extra="forbid")
    language: str = Field("en", min_length=2, max_length=5)
    indicators: dict[str, Any]

    @model_validator(mode="after")
    def _no_private_keys(self) -> ExplainRequest:
        hits = _scan_keys(self.indicators)
        if hits:
            raise ValueError(
                "indicators must not contain location or identity fields: " + ", ".join(hits)
            )
        return self
