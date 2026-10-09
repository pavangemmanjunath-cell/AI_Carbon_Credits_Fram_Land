"""Plot-level statistics of an index raster."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class IndexStats:
    mean: float | None
    min: float | None
    max: float | None
    valid_share: float
    valid_pixels: int
    total_pixels: int

    def to_dict(self) -> dict[str, float | None]:
        return {
            "mean": self.mean,
            "min": self.min,
            "max": self.max,
            "valid_share": self.valid_share,
        }


def plot_statistics(
    values: np.ndarray, inside: np.ndarray | None = None, decimals: int = 4
) -> IndexStats:
    """Mean/min/max of ``values`` over ``inside`` pixels, ignoring NaN.

    ``valid_share`` is the fraction of inside pixels that were not NaN
    (i.e. not cloud-masked).
    """
    arr = np.asarray(values, dtype=np.float32)
    mask = np.ones(arr.shape, dtype=bool) if inside is None else np.asarray(inside, dtype=bool)
    region = arr[mask]
    total = int(region.size)
    valid = region[~np.isnan(region)]
    count = int(valid.size)
    if count == 0:
        return IndexStats(None, None, None, 0.0, 0, total)
    return IndexStats(
        mean=round(float(valid.mean()), decimals),
        min=round(float(valid.min()), decimals),
        max=round(float(valid.max()), decimals),
        valid_share=round(count / total, 4) if total else 0.0,
        valid_pixels=count,
        total_pixels=total,
    )
