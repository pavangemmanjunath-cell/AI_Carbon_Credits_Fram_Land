"""Cube data structures and JSON serialisation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from geo_engine.cube.grid import CubeGrid


@dataclass(frozen=True)
class TimeStats:
    time: str
    mean: float | None
    min: float | None
    max: float | None
    valid_share: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "mean": self.mean,
            "min": self.min,
            "max": self.max,
            "valid_share": self.valid_share,
        }


@dataclass
class Cube:
    """``values`` is a float32 array ``(times, rows, cols)`` with NaN outside the
    polygon or where cloud-masked; ``mask`` is ``(rows, cols)`` with 1 inside."""

    plot_id: str
    index: str
    grid: CubeGrid
    times: list[str]
    mask: np.ndarray
    values: np.ndarray
    provenance: dict[str, Any] = field(default_factory=dict)

    def stats_per_time(self, decimals: int = 3) -> list[TimeStats]:
        inside = self.mask.astype(bool)
        total = int(inside.sum())
        out: list[TimeStats] = []
        for t, label in enumerate(self.times):
            layer = self.values[t][inside]
            valid = layer[~np.isnan(layer)]
            if valid.size == 0 or total == 0:
                out.append(TimeStats(label, None, None, None, 0.0))
                continue
            out.append(
                TimeStats(
                    time=label,
                    mean=round(float(valid.mean()), decimals),
                    min=round(float(valid.min()), decimals),
                    max=round(float(valid.max()), decimals),
                    valid_share=round(valid.size / total, 3),
                )
            )
        return out

    def to_dict(self, mode: str, decimals: int = 3) -> dict[str, Any]:
        """Serialise to the ``GET /plots/{id}/cube`` contract shape."""
        values: list[list[list[float | None]]] = []
        for t in range(self.values.shape[0]):
            layer = []
            for r in range(self.values.shape[1]):
                row = []
                for c in range(self.values.shape[2]):
                    v = float(self.values[t, r, c])
                    row.append(None if math.isnan(v) else round(v, decimals))
                layer.append(row)
            values.append(layer)
        return {
            "plot_id": self.plot_id,
            "index": self.index,
            "mode": mode,
            "grid": self.grid.to_dict(),
            "times": list(self.times),
            "mask": self.mask.astype(int).tolist(),
            "values": values,
            "stats_per_time": [s.to_dict() for s in self.stats_per_time(decimals)],
            "provenance": dict(self.provenance),
        }
