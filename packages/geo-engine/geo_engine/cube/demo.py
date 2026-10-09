"""Deterministic synthetic cube for demo mode.

Nothing here is an observation. The generator produces a plausible-looking
field so the map's NDVI cells, charts, detection and tests have data without network access.
Everything is seeded from ``(plot_id, index)`` so the same plot always yields
the same cube, and the provenance says ``"source": "synthetic-demo"``.

Ingredients (all documented, none calibrated):

* a smooth spatial base field (bilinear upsampling of coarse noise);
* a seasonal cycle with its peak in ``peak_month`` (September north of the
  equator — post-monsoon greenness — March south of it);
* a slow growth trend representing a maturing plantation;
* one "stressed patch" (Gaussian dip) that deepens over time;
* a dry-season dip in the three months before the peak-minus-six month;
* a few cloud-masked months with a NaN blob (``valid_share < 1``);
* NDMI/NDRE are affine transforms of the NDVI-like field.
"""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, date, datetime
from typing import Any

import numpy as np
from shapely.geometry import Polygon

from geo_engine.cube.grid import DEFAULT_CELL_SIZE_M, build_grid, month_sequence
from geo_engine.cube.types import Cube

SUPPORTED_INDICES = ("ndvi", "ndmi", "ndre")


def _seed(plot_id: str, index: str) -> int:
    digest = hashlib.sha256(f"{plot_id}:{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _smooth_field(rng: np.random.Generator, rows: int, cols: int, coarse: int = 4) -> np.ndarray:
    """Bilinear upsampling of a coarse random field → values in roughly [-1, 1]."""
    cr, cc = max(2, math.ceil(rows / coarse) + 1), max(2, math.ceil(cols / coarse) + 1)
    coarse_field = rng.normal(0.0, 1.0, size=(cr, cc))
    ys = np.linspace(0, cr - 1, rows)
    xs = np.linspace(0, cc - 1, cols)
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, cr - 1)
    x1 = np.minimum(x0 + 1, cc - 1)
    wy = (ys - y0)[:, None]
    wx = (xs - x0)[None, :]
    top = coarse_field[y0][:, x0] * (1 - wx) + coarse_field[y0][:, x1] * wx
    bottom = coarse_field[y1][:, x0] * (1 - wx) + coarse_field[y1][:, x1] * wx
    field = top * (1 - wy) + bottom * wy
    return field / max(1e-6, np.abs(field).max())


def _month_index(label: str) -> int:
    return int(label.split("-")[1])


def build_demo_cube(
    plot_id: str,
    polygon: Polygon,
    index: str = "ndvi",
    months: int = 36,
    end: date | None = None,
    cell_size_m: int = DEFAULT_CELL_SIZE_M,
    planting_year: int | None = None,
) -> Cube:
    """Build a synthetic :class:`Cube` for ``polygon``."""
    index = index.lower()
    if index not in SUPPORTED_INDICES:
        raise ValueError(f"unsupported index {index!r}; choose one of {SUPPORTED_INDICES}")
    end = end or datetime.now(UTC).date()
    grid, mask = build_grid(polygon, cell_size_m)
    times = month_sequence(end, months)
    rows, cols = grid.rows, grid.cols
    rng = np.random.default_rng(_seed(plot_id, "base"))

    centre_lat = (grid.bbox[1] + grid.bbox[3]) / 2.0
    peak_month = 9 if centre_lat >= 0 else 3
    base = 0.48 + 0.10 * _smooth_field(rng, rows, cols)

    # Stressed patch: Gaussian dip centred on a random inside cell.
    inside_cells = np.argwhere(mask.astype(bool))
    pr, pc = inside_cells[rng.integers(len(inside_cells))]
    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    sigma = max(1.0, min(rows, cols) / 5.0)
    patch = np.exp(-(((rr - pr) ** 2 + (cc - pc) ** 2) / (2 * sigma**2)))

    # Cloud-masked months: a handful of time steps lose a blob of cells.
    cloudy_steps = set(rng.choice(months, size=max(1, months // 9), replace=False).tolist())

    start_year = int(times[0].split("-")[0])
    values = np.full((months, rows, cols), np.nan, dtype=np.float32)
    inside = mask.astype(bool)
    for t, label in enumerate(times):
        month = _month_index(label)
        phase = 2.0 * math.pi * (month - peak_month) / 12.0
        seasonal = 0.12 * math.cos(phase)
        dry_dip = -0.06 if ((peak_month - month) % 12) in (4, 5, 6) else 0.0
        years_since_start = t / 12.0
        if planting_year is not None:
            age = start_year - planting_year + years_since_start
            trend = 0.05 * max(0.0, min(age, 6.0)) / 6.0 + 0.03 * years_since_start
        else:
            trend = 0.035 * years_since_start
        stress = -0.16 * patch * (0.4 + 0.6 * t / max(1, months - 1))
        noise = rng.normal(0.0, 0.015, size=(rows, cols))
        layer = base + seasonal + dry_dip + trend + stress + noise
        if index == "ndmi":
            layer = layer * 0.55 - 0.12
        elif index == "ndre":
            layer = layer * 0.6
        layer = np.clip(layer, -0.2, 0.95)
        layer[~inside] = np.nan
        if t in cloudy_steps:
            cr, ccol = inside_cells[rng.integers(len(inside_cells))]
            blob = ((rr - cr) ** 2 + (ccol - cc) ** 2) <= max(1.0, (min(rows, cols) / 3.0) ** 2)
            layer[blob] = np.nan
        values[t] = layer.astype(np.float32)

    provenance: dict[str, Any] = {
        "source": "synthetic-demo",
        "composite": "monthly-min-cloud",
        "cloud_mask": "SCL classes 4,5,6 kept",
        "aggregation": f"{cell_size_m // 10}×{cell_size_m // 10} mean of 10 m pixels"
        if cell_size_m % 10 == 0
        else f"{cell_size_m} m cells",
        "scene_ids": [],
        "note": "Deterministic synthetic field seeded by plot id; not an observation.",
    }
    return Cube(
        plot_id=plot_id,
        index=index,
        grid=grid,
        times=times,
        mask=mask,
        values=values,
        provenance=provenance,
    )
