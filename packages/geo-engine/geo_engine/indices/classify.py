"""Index classes exactly as defined in docs/architecture/api-contract.md.

NDVI: ``sparse`` < 0.3 · ``moderate`` 0.3–0.6 · ``healthy`` ≥ 0.6
NDMI: ``dry`` < 0.0 · ``moderate`` 0.0–0.3 · ``moist`` ≥ 0.3
"""

from __future__ import annotations

import math

NDVI_MODERATE = 0.3
NDVI_HEALTHY = 0.6
NDMI_MODERATE = 0.0
NDMI_MOIST = 0.3


def classify_ndvi(value: float | None) -> str | None:
    """Return ``sparse | moderate | healthy`` (None for missing/NaN)."""
    if value is None or math.isnan(value):
        return None
    if value < NDVI_MODERATE:
        return "sparse"
    if value < NDVI_HEALTHY:
        return "moderate"
    return "healthy"


def classify_ndmi(value: float | None) -> str | None:
    """Return ``dry | moderate | moist`` (None for missing/NaN)."""
    if value is None or math.isnan(value):
        return None
    if value < NDMI_MODERATE:
        return "dry"
    if value < NDMI_MOIST:
        return "moderate"
    return "moist"


def trend_statement(change_pct: float | None, label: str = "Vegetation index") -> str:
    """Plain-language sentence for a percentage change between two dates."""
    if change_pct is None:
        return f"{label} trend could not be evaluated (insufficient clear observations)."
    if abs(change_pct) < 5.0:
        return f"{label} remained broadly stable (change within ±5%) during the evaluated period."
    direction = "increased" if change_pct > 0 else "decreased"
    return f"{label} {direction} approximately {abs(change_pct):.0f}% during the evaluated period."
