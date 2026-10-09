"""``crop-practice`` model — typed interface only (not implemented in v0.1).

Emission reductions from cropland practices (reduced tillage, cover crops,
fertiliser and residue management, rotations) require:

* **Verra VM0042 v2.2** (Improved Agricultural Land Management) — the
  quantification approaches, baseline rules and uncertainty deductions.
* **IPCC 2006 Vol. 4, Ch. 11 (N₂O from managed soils) and Ch. 5 (Cropland)**
  with the 2019 Refinement emission factors (EF₁, FracGASF …).
* **USDA COMET-Farm** (DayCent-based) as the United States reference tool;
  for India, ICAR/NABARD practice-level datasets; for the EU, the CRCF
  mineral-soils methodology.

No practice-level factor is bundled; the model raises until the parameter
file exists with ``source`` and ``verification_status`` for every value.
"""

from __future__ import annotations

from carbon_engine.errors import ModelNotImplementedError
from carbon_engine.types import CarbonEstimate, ClimateInput, InventoryInput, ModelParams, PlotInput


class CropPracticeModel:
    id = "crop-practice"
    version = "0.0.0"
    required_sources = (
        "Verra VM0042 v2.2 Improved Agricultural Land Management",
        "IPCC 2006/2019 Vol.4 Ch.11 N2O emission factors and Ch.5 Cropland",
        "USDA COMET-Farm (DayCent) practice defaults",
    )

    def estimate(
        self,
        plot: PlotInput,
        inventory: InventoryInput,
        climate: ClimateInput,
        params: ModelParams | None = None,
    ) -> CarbonEstimate:
        raise ModelNotImplementedError(
            "crop-practice model not implemented: requires verified parameters from "
            + "; ".join(self.required_sources)
        )
