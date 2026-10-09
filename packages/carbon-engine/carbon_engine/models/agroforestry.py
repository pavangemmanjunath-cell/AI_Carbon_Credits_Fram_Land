"""``agroforestry`` model — typed interface only (not implemented in v0.1).

Authoritative sources required before any number ships:

* **USDA COMET-Farm / COMET-Planner agroforestry module** — tree biomass
  growth by species group from Forest Inventory and Analysis (FIA) based
  growth equations, with practice-specific defaults (windbreaks, alley
  cropping, silvopasture, riparian buffers). https://comet-farm.com/
* **IPCC 2019 Refinement, Vol. 4, Ch. 5 Cropland, Table 5.3** — Tier 1
  biomass carbon stocks and accumulation rates for agroforestry systems by
  climate region (the only global Tier 1 agroforestry defaults).
* **Verra VM0047 (ARR) census-based approach** for mixed plantings.

Until those tables are transcribed into ``config/`` with ``source`` and
``verification_status``, :meth:`AgroforestryModel.estimate` raises
:class:`ModelNotImplementedError`. Mixed tree plantings can be approximated
today by running ``tree-biomass`` per species and summing the series.
"""

from __future__ import annotations

from carbon_engine.errors import ModelNotImplementedError
from carbon_engine.types import CarbonEstimate, ClimateInput, InventoryInput, ModelParams, PlotInput


class AgroforestryModel:
    id = "agroforestry"
    version = "0.0.0"
    required_sources = (
        "USDA COMET-Farm agroforestry module (FIA growth equations)",
        "IPCC 2019 Refinement Vol.4 Ch.5 Table 5.3 (agroforestry biomass stocks)",
        "Verra VM0047 census-based approach",
    )

    def estimate(
        self,
        plot: PlotInput,
        inventory: InventoryInput,
        climate: ClimateInput,
        params: ModelParams | None = None,
    ) -> CarbonEstimate:
        raise ModelNotImplementedError(
            "agroforestry model not implemented: requires verified parameters from "
            + "; ".join(self.required_sources)
        )
