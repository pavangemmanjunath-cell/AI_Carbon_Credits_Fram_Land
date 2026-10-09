"""``soil-carbon`` model — typed interface only (not implemented in v0.1).

Soil organic carbon (SOC) change cannot be estimated from a tree count. The
authoritative methods that must be implemented (with their own parameter
files and verification) are:

* **IPCC 2006 Guidelines Vol. 4, Ch. 2 §2.3.3 and Ch. 5 §5.2.3** — Tier 1
  stock-change method ``ΔSOC = (SOC_ref · F_LU · F_MG · F_I)_t − (…)_{t−20} / D``
  with reference stocks (Table 2.3) and the land-use, management and input
  factors (Tables 5.5/5.10), plus the 2019 Refinement updates.
* **Verra VM0042 v2.2 — Improved Agricultural Land Management** —
  measurement, modelling and hybrid quantification approaches for SOC with
  baseline, additionality, leakage and permanence rules.
* **EU CRCF carbon-farming methodology for mineral soils** (delegated act,
  2025–2026) for EU plots.

SoilGrids ``soc_0_30cm`` (ISRIC) is reported by the analysis endpoint as a
*current stock indicator*, never as a change or a removal.
"""

from __future__ import annotations

from carbon_engine.errors import ModelNotImplementedError
from carbon_engine.types import CarbonEstimate, ClimateInput, InventoryInput, ModelParams, PlotInput


class SoilCarbonModel:
    id = "soil-carbon"
    version = "0.0.0"
    required_sources = (
        "IPCC 2006 Vol.4 Ch.2 §2.3.3 / Ch.5 §5.2.3 stock-change factors (Tables 2.3, 5.5, 5.10)",
        "Verra VM0042 v2.2 Improved Agricultural Land Management",
        "EU CRCF carbon-farming (mineral soils) certification methodology",
    )

    def estimate(
        self,
        plot: PlotInput,
        inventory: InventoryInput,
        climate: ClimateInput,
        params: ModelParams | None = None,
    ) -> CarbonEstimate:
        raise ModelNotImplementedError(
            "soil-carbon model not implemented: requires verified parameters from "
            + "; ".join(self.required_sources)
        )
