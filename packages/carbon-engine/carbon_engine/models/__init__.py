"""Model registry.

``get_model("tree-biomass")`` returns the only implemented model in v0.1;
the other ids resolve to typed stubs that raise
:class:`~carbon_engine.errors.ModelNotImplementedError` naming the
authoritative sources required.
"""

from __future__ import annotations

from carbon_engine.models.agroforestry import AgroforestryModel
from carbon_engine.models.crop_practice import CropPracticeModel
from carbon_engine.models.soil_carbon import SoilCarbonModel
from carbon_engine.models.tree_biomass import TreeBiomassModel
from carbon_engine.parameters import ParameterStore
from carbon_engine.protocol import CarbonModel

DEFAULT_MODEL_ID = "tree-biomass"
IMPLEMENTED_MODEL_IDS = ("tree-biomass",)
ALL_MODEL_IDS = ("tree-biomass", "agroforestry", "soil-carbon", "crop-practice")


def get_model(model_id: str = DEFAULT_MODEL_ID, store: ParameterStore | None = None) -> CarbonModel:
    """Return a model instance for ``model_id`` (KeyError when unknown)."""
    if model_id == "tree-biomass":
        return TreeBiomassModel(store)
    if model_id == "agroforestry":
        return AgroforestryModel()
    if model_id == "soil-carbon":
        return SoilCarbonModel()
    if model_id == "crop-practice":
        return CropPracticeModel()
    raise KeyError(model_id)


__all__ = [
    "ALL_MODEL_IDS",
    "DEFAULT_MODEL_ID",
    "IMPLEMENTED_MODEL_IDS",
    "AgroforestryModel",
    "CropPracticeModel",
    "SoilCarbonModel",
    "TreeBiomassModel",
    "get_model",
]
