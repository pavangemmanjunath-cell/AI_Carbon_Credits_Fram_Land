"""Normalised-difference spectral indices on Sentinel-2 L2A reflectance.

* NDVI = (NIR − Red) / (NIR + Red) — Rouse et al. (1974); Sentinel-2 B08/B04.
* NDMI = (NIR − SWIR1) / (NIR + SWIR1) — Gao (1996); Sentinel-2 B08/B11.
* NDRE = (NIR − RedEdge) / (NIR + RedEdge) — Barnes et al. (2000); B08/B05.

Inputs may be digital numbers or surface reflectance; the ratio is scale
free. Sentinel-2 L2A DN use ``reflectance = (DN − 1000) / 10000`` from
processing baseline 04.00 — callers should apply that offset first when mixing
bands from different baselines. Division by zero yields NaN.
"""

from __future__ import annotations

import numpy as np


def normalized_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Return ``(a − b) / (a + b)`` as float32 with NaN where ``a + b == 0``."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denominator = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(denominator == 0, np.nan, (a - b) / denominator)
    return result.astype(np.float32)


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalised Difference Vegetation Index (B08, B04)."""
    return normalized_difference(nir, red)


def ndmi(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Normalised Difference Moisture Index (B08, B11)."""
    return normalized_difference(nir, swir1)


def ndre(nir: np.ndarray, red_edge: np.ndarray) -> np.ndarray:
    """Normalised Difference Red-Edge index (B08, B05)."""
    return normalized_difference(nir, red_edge)
