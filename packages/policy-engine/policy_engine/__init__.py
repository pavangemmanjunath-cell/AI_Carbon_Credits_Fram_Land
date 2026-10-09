"""policy_engine — screens a plot/activity against ``config/policies/<country>.yaml``.

The output is always a **screening** ("which programmes might be relevant and
what would they require?"), never an eligibility determination. Rules live in
YAML; this package only evaluates them.
"""

from policy_engine.engine import (
    ACTIVITIES,
    STATUSES,
    PolicyEngine,
    ProgrammeScreening,
    Screening,
    get_engine,
)
from policy_engine.loader import (
    PolicyConfig,
    RegionIndex,
    find_config_dir,
    load_policy,
    load_regions,
)

__version__ = "0.1.0"
__all__ = [
    "ACTIVITIES",
    "STATUSES",
    "PolicyConfig",
    "PolicyEngine",
    "ProgrammeScreening",
    "RegionIndex",
    "Screening",
    "find_config_dir",
    "get_engine",
    "load_policy",
    "load_regions",
]
