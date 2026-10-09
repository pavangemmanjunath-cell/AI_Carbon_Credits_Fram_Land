"""carbon_engine — deterministic, parameter-cited carbon removal scenarios.

Public surface::

    from carbon_engine import (
        TreeBiomassModel, get_model, ParameterStore, get_store,
        PlotInput, InventoryInput, ClimateInput, ModelParams, CarbonEstimate,
    )

Every output is a *scenario estimate* (``certified: False``). The engine never
touches the network and never invents a parameter: all numbers come from
``config/`` with ``source`` and ``verification_status``.
"""

from carbon_engine.confidence import confidence_for_inventory, confidence_from_fields
from carbon_engine.errors import (
    CarbonEngineError,
    ModelInputError,
    ModelNotImplementedError,
    PendingParameterError,
    UnknownClimateZoneError,
    UnknownSpeciesError,
)
from carbon_engine.models import (
    ALL_MODEL_IDS,
    DEFAULT_MODEL_ID,
    IMPLEMENTED_MODEL_IDS,
    TreeBiomassModel,
    get_model,
)
from carbon_engine.parameters import (
    ParameterStore,
    assert_production_safe,
    find_config_dir,
    get_store,
    worst_verification_status,
)
from carbon_engine.protocol import CarbonModel
from carbon_engine.readiness import score_readiness
from carbon_engine.types import (
    DISCLAIMER,
    CarbonEstimate,
    ClimateInput,
    EvidenceItem,
    InventoryInput,
    Methodology,
    ModelParams,
    ParameterUsed,
    PlotInput,
    Range,
    Readiness,
    SeriesPoint,
)

__version__ = "0.1.0"
__all__ = [
    "ALL_MODEL_IDS",
    "DEFAULT_MODEL_ID",
    "DISCLAIMER",
    "IMPLEMENTED_MODEL_IDS",
    "CarbonEngineError",
    "CarbonEstimate",
    "CarbonModel",
    "ClimateInput",
    "EvidenceItem",
    "InventoryInput",
    "Methodology",
    "ModelInputError",
    "ModelNotImplementedError",
    "ModelParams",
    "ParameterStore",
    "ParameterUsed",
    "PendingParameterError",
    "PlotInput",
    "Range",
    "Readiness",
    "SeriesPoint",
    "TreeBiomassModel",
    "UnknownClimateZoneError",
    "UnknownSpeciesError",
    "assert_production_safe",
    "confidence_for_inventory",
    "confidence_from_fields",
    "find_config_dir",
    "get_model",
    "get_store",
    "score_readiness",
    "worst_verification_status",
]
