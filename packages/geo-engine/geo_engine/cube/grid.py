"""Regular lon/lat grid over a plot's bounding box.

The cube grid is defined in EPSG:4326 with a cell size expressed in metres
(default 30 m = 3 × 3 Sentinel-2 10 m pixels). Cell dimensions in degrees are
derived at the plot's centre latitude (1° latitude ≈ 111 320 m; 1° longitude
≈ 111 320 m × cos φ), which is exact enough for field-scale plots.

``mask`` is 1 where the **cell centre** falls inside the polygon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import shapely
from shapely.geometry import Polygon

METRES_PER_DEGREE_LAT = 111_320.0
DEFAULT_CELL_SIZE_M = 30
MAX_CELLS = 40_000  # 200 × 200 — keeps responses well under a few MB


@dataclass(frozen=True)
class CubeGrid:
    rows: int
    cols: int
    cell_size_m: int
    bbox: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    crs: str = "EPSG:4326"

    @property
    def d_lon(self) -> float:
        return (self.bbox[2] - self.bbox[0]) / self.cols

    @property
    def d_lat(self) -> float:
        return (self.bbox[3] - self.bbox[1]) / self.rows

    def cell_centres(self) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(lons, lats)`` arrays of shape (rows, cols); row 0 is the north edge."""
        lons = self.bbox[0] + (np.arange(self.cols) + 0.5) * self.d_lon
        lats = self.bbox[3] - (np.arange(self.rows) + 0.5) * self.d_lat
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        return lon_grid, lat_grid

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "cell_size_m": self.cell_size_m,
            "bbox": [round(v, 6) for v in self.bbox],
            "crs": self.crs,
        }


class GridTooLargeError(ValueError):
    """The plot's bounding box needs more than ``MAX_CELLS`` cells at this cell size."""

    def __init__(self, rows: int, cols: int, cell_size_m: int) -> None:
        self.rows = rows
        self.cols = cols
        self.cell_size_m = cell_size_m
        self.max_area_ha = MAX_CELLS * cell_size_m * cell_size_m / 10_000
        super().__init__(
            f"grid of {rows}×{cols} cells exceeds the maximum of {MAX_CELLS}; increase cell_size_m"
        )


def build_grid(
    polygon: Polygon, cell_size_m: int = DEFAULT_CELL_SIZE_M
) -> tuple[CubeGrid, np.ndarray]:
    """Create the grid covering ``polygon`` and the inside mask (rows × cols, uint8)."""
    if cell_size_m <= 0:
        raise ValueError("cell_size_m must be positive")
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    centre_lat = (min_lat + max_lat) / 2.0
    metres_per_degree_lon = METRES_PER_DEGREE_LAT * max(math.cos(math.radians(centre_lat)), 1e-6)
    height_m = (max_lat - min_lat) * METRES_PER_DEGREE_LAT
    width_m = (max_lon - min_lon) * metres_per_degree_lon
    rows = max(1, math.ceil(height_m / cell_size_m))
    cols = max(1, math.ceil(width_m / cell_size_m))
    if rows * cols > MAX_CELLS:
        raise GridTooLargeError(rows, cols, cell_size_m)
    # Expand the bbox so cells are exactly cell_size_m, centred on the plot.
    d_lat = cell_size_m / METRES_PER_DEGREE_LAT
    d_lon = cell_size_m / metres_per_degree_lon
    centre_lon = (min_lon + max_lon) / 2.0
    bbox = (
        centre_lon - cols * d_lon / 2.0,
        centre_lat - rows * d_lat / 2.0,
        centre_lon + cols * d_lon / 2.0,
        centre_lat + rows * d_lat / 2.0,
    )
    grid = CubeGrid(rows=rows, cols=cols, cell_size_m=cell_size_m, bbox=bbox)
    lon_grid, lat_grid = grid.cell_centres()
    inside = shapely.contains_xy(polygon, lon_grid.ravel(), lat_grid.ravel()).reshape(rows, cols)
    if not inside.any():
        # Tiny polygon smaller than a cell: keep the cell containing the centroid.
        inside = np.zeros((rows, cols), dtype=bool)
        inside[rows // 2, cols // 2] = True
    return grid, inside.astype(np.uint8)


def month_sequence(end: date, months: int) -> list[str]:
    """Return ``months`` consecutive ``YYYY-MM`` labels ending with ``end``'s month."""
    labels: list[str] = []
    year, month = end.year, end.month
    for _ in range(months):
        labels.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(labels))
