"""Cloud masking with the Sentinel-2 L2A Scene Classification Layer (SCL).

SCL classes (Sen2Cor, ESA Sentinel-2 L2A product definition):
0 no data · 1 saturated/defective · 2 dark area (topographic shadow) ·
3 cloud shadow · 4 vegetation · 5 not vegetated · 6 water · 7 unclassified ·
8 cloud medium probability · 9 cloud high probability · 10 thin cirrus ·
11 snow/ice.

The contract keeps classes **4, 5, 6** (vegetation, not-vegetated, water);
everything else is treated as invalid.
"""

from __future__ import annotations

import numpy as np

SCL_CLEAR_CLASSES: frozenset[int] = frozenset({4, 5, 6})


def scl_clear_mask(scl: np.ndarray, keep: frozenset[int] = SCL_CLEAR_CLASSES) -> np.ndarray:
    """Return a boolean array that is True where the pixel is clear (kept)."""
    arr = np.asarray(scl)
    return np.isin(arr, list(keep))


def apply_mask(values: np.ndarray, clear: np.ndarray) -> np.ndarray:
    """Return ``values`` as float32 with NaN where ``clear`` is False."""
    out = np.asarray(values, dtype=np.float32).copy()
    out[~np.asarray(clear, dtype=bool)] = np.nan
    return out
