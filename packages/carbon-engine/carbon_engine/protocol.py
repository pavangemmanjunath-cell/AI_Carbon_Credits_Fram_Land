"""The :class:`CarbonModel` protocol every model implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from carbon_engine.types import CarbonEstimate, ClimateInput, InventoryInput, ModelParams, PlotInput


@runtime_checkable
class CarbonModel(Protocol):
    """A deterministic carbon model.

    Implementations must be pure functions of their inputs and configuration:
    no network, no randomness, no LLM. ``estimate`` returns a
    :class:`CarbonEstimate` with low/central/high values, the annual series,
    every parameter used (with source and verification status), confidence,
    readiness and provenance.
    """

    id: str
    version: str

    def estimate(
        self,
        plot: PlotInput,
        inventory: InventoryInput,
        climate: ClimateInput,
        params: ModelParams | None = None,
    ) -> CarbonEstimate: ...
