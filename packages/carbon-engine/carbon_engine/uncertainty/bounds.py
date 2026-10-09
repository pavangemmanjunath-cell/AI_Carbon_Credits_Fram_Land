"""Symmetric/asymmetric fractional bounds around a central value.

v0.1 propagates uncertainty as a fixed fraction of the central estimate
(``low = central × (1 − f_low)``, ``high = central × (1 + f_high)``), the
fractions being project assumptions in ``ipcc-2006-tier1.yaml``. This is a
placeholder for IPCC Tier 1 default uncertainties (Vol. 4 Ch. 4 §4.2.1.4) or
Monte-Carlo propagation; see the carbon-engine README.
"""

from __future__ import annotations

from collections.abc import Iterable


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into ``[low, high]``."""
    return max(low, min(high, value))


def bounds_from_fraction(central: float, f_low: float, f_high: float) -> tuple[float, float, float]:
    """Return ``(low, central, high)`` with ``low ≤ central ≤ high`` guaranteed."""
    if f_low < 0 or f_high < 0:
        raise ValueError("uncertainty fractions must be non-negative")
    low = central * (1.0 - min(f_low, 1.0))
    high = central * (1.0 + f_high)
    if central < 0:  # negative central values (not expected) keep ordering
        low, high = high, low
    return low, central, high


def cumulative(values: Iterable[float]) -> list[float]:
    """Running sum."""
    total = 0.0
    out: list[float] = []
    for v in values:
        total += v
        out.append(total)
    return out


def round_range(
    low: float, central: float, high: float, digits: int = 2
) -> tuple[float, float, float]:
    """Round the three values consistently (ordering is preserved by monotonic rounding)."""
    return round(low, digits), round(central, digits), round(high, digits)
