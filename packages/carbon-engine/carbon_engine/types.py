"""Typed inputs and outputs shared by every carbon model.

All numbers are plain floats in SI-derived units stated in the field names
(``_ha``, ``_t``, ``_tco2e``). Outputs are dataclasses with ``to_dict`` so the
API layer can serialise them without knowing model internals.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

CONFIDENCE_LEVELS = ("low", "medium", "high")
DISCLAIMER = "Scenario estimate; not an issued carbon credit."


@dataclass(frozen=True)
class PlotInput:
    """What the model needs to know about the land parcel."""

    area_hectares: float
    plot_id: str | None = None
    has_polygon: bool = True
    has_satellite_observation: bool = False
    country: str | None = None


@dataclass(frozen=True)
class InventoryInput:
    """Trees reported for the plot (see tree-inventory.schema.json)."""

    species_id: str
    tree_count: int
    plantation_year: int
    average_dbh_cm: float | None = None
    average_height_m: float | None = None
    survival_rate: float | None = None
    measurement_source: str = "user-reported"
    inventory_id: str | None = None


@dataclass(frozen=True)
class ClimateInput:
    """Climate zone id as used by the parameter tables (e.g. ``tropical_dry``)."""

    zone: str
    zone_source: str = "region-default"  # region-default | derived | user


@dataclass(frozen=True)
class ModelParams:
    """Run-time knobs; ``None`` means "use the configured default"."""

    horizon_years: int | None = None
    as_of_year: int | None = None
    years_to_full_increment: float | None = None
    allow_pending_parameters: bool = True
    #: evidence the caller can vouch for beyond the inventory (baseline, management, ownership)
    evidence: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Range:
    low: float
    central: float
    high: float
    unit: str

    def to_dict(self) -> dict[str, Any]:
        return {"low": self.low, "central": self.central, "high": self.high, "unit": self.unit}


@dataclass(frozen=True)
class ParameterUsed:
    name: str
    value: Any
    unit: str
    source: str
    verification_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "verification_status": self.verification_status,
        }


@dataclass(frozen=True)
class SeriesPoint:
    year: int
    age: int
    low: float
    central: float
    high: float
    cum_low: float
    cum_central: float
    cum_high: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "age": self.age,
            "low": self.low,
            "central": self.central,
            "high": self.high,
            "cum_low": self.cum_low,
            "cum_central": self.cum_central,
            "cum_high": self.cum_high,
        }


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    label: str
    weight: int

    def to_dict(self, with_weight: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {"id": self.id, "label": self.label}
        if with_weight:
            data["weight"] = self.weight
        return data


@dataclass(frozen=True)
class Readiness:
    score: int
    grade: str
    present_evidence: list[EvidenceItem]
    missing_evidence: list[EvidenceItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "grade": self.grade,
            "present_evidence": [e.to_dict(with_weight=False) for e in self.present_evidence],
            "missing_evidence": [e.to_dict() for e in self.missing_evidence],
        }


@dataclass(frozen=True)
class Methodology:
    id: str
    name: str
    references: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "references": list(self.references)}


@dataclass
class CarbonEstimate:
    """Model output — never certified, always a range with provenance."""

    model_id: str
    model_version: str
    tier: str
    methodology: Methodology
    estimate: Range
    stock: Range
    components: dict[str, float]
    annual_series: list[SeriesPoint]
    parameters_used: list[ParameterUsed]
    confidence: str
    readiness: Readiness
    provenance: dict[str, Any]
    notes: list[str] = field(default_factory=list)
    certified: bool = False
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": {"id": self.model_id, "version": self.model_version, "tier": self.tier},
            "methodology": self.methodology.to_dict(),
            "estimate": self.estimate.to_dict(),
            "stock": self.stock.to_dict(),
            "components": dict(self.components),
            "annual_series": [p.to_dict() for p in self.annual_series],
            "parameters_used": [p.to_dict() for p in self.parameters_used],
            "confidence": self.confidence,
            "certified": False,
            "disclaimer": self.disclaimer,
            "readiness": self.readiness.to_dict(),
            "provenance": dict(self.provenance),
            "notes": list(self.notes),
        }
