"""Canopy height model and local-maximum tree tops — numpy only (no scipy).

Pipeline (all grids are row-major, row 0 = south, cells are squares in metres):

1. **Ground**: mean height of the ground-classified points per ground cell, or the lowest point
   per ground cell when too few points are classified; gaps are filled from the nearest valid
   cells (iterative frontier mean) and the surface is sampled by bilinear interpolation.
2. **Normalised height** of every point = z minus the interpolated ground; points above
   ``max_tree_height_m`` are noise and ignored, heights below ground are clamped to zero.
3. **CHM** = maximum normalised height per CHM cell.
4. **Smoothing** with a square mean filter (NaN-aware, so holes between sparse returns close).
5. **Tree tops** = cells that equal the maximum of the circular window of radius
   ``window_radius_m`` and exceed ``min_height_m``; touching maxima (plateaus) merge into one top.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

CHUNK = 2_000_000


@dataclass(frozen=True)
class GridSpec:
    """Square-cell grid anchored at the south-west corner ``(x0, y0)`` (metres)."""

    x0: float
    y0: float
    cell: float
    ncols: int
    nrows: int

    @property
    def size(self) -> int:
        return self.ncols * self.nrows


def make_grid(x0: float, y0: float, width: float, height: float, cell: float) -> GridSpec:
    return GridSpec(
        x0=x0,
        y0=y0,
        cell=cell,
        ncols=int(math.floor(width / cell)) + 1,
        nrows=int(math.floor(height / cell)) + 1,
    )


def choose_cell_size(width: float, height: float, cell: float, max_side: int) -> float:
    """Smallest cell >= ``cell`` (rounded up to 1 cm) that keeps both sides <= ``max_side``."""
    while max(math.floor(width / cell), math.floor(height / cell)) + 1 > max_side:
        needed = max(width, height) / (max_side - 1)
        cell = max(cell * 1.01, math.ceil(needed * 100.0) / 100.0)
    return cell


def cell_index(x: np.ndarray, y: np.ndarray, spec: GridSpec) -> np.ndarray:
    """Flat cell index (``row * ncols + col``) of float32 positions, clipped into the grid."""
    col = np.clip(
        ((x - np.float32(spec.x0)) / np.float32(spec.cell)).astype(np.int64), 0, spec.ncols - 1
    )
    row = np.clip(
        ((y - np.float32(spec.y0)) / np.float32(spec.cell)).astype(np.int64), 0, spec.nrows - 1
    )
    return row * spec.ncols + col


# ---------------------------------------------------------------------------- ground
def fill_nearest(grid: np.ndarray, needed: np.ndarray, max_iterations: int) -> np.ndarray:
    """Fill NaN cells that are ``needed`` from the mean of their valid 8-neighbours, outward.

    Each pass extends the valid area by one cell (nearest-valid-cell fill). Cells still empty after
    ``max_iterations`` passes — or outside ``needed`` — take the median of the valid cells.
    """
    filled = grid.astype(np.float32, copy=True)
    rows, cols = filled.shape
    for _ in range(max_iterations):
        missing = np.isnan(filled)
        if not (missing & needed).any():
            break
        padded = np.pad(filled, 1, constant_values=np.nan)
        sums = np.zeros_like(filled)
        counts = np.zeros(filled.shape, dtype=np.uint8)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                if dy == 1 and dx == 1:
                    continue
                neighbour = padded[dy : dy + rows, dx : dx + cols]
                valid = ~np.isnan(neighbour)
                sums += np.where(valid, neighbour, 0.0)
                counts += valid
        take = missing & (counts > 0)
        filled[take] = sums[take] / counts[take]
    leftovers = np.isnan(filled)
    if leftovers.any():
        valid_values = filled[~leftovers]
        filled[leftovers] = float(np.median(valid_values)) if valid_values.size else 0.0
    return filled


def dilate(mask: np.ndarray) -> np.ndarray:
    """Boolean 3x3 dilation."""
    rows, cols = mask.shape
    padded = np.pad(mask, 1, constant_values=False)
    out = np.zeros_like(mask)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            out |= padded[dy : dy + rows, dx : dx + cols]
    return out


def ground_surface(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    classification: np.ndarray | None,
    spec: GridSpec,
    ground_code: int,
    min_share: float,
    max_gap_cells: int,
) -> tuple[np.ndarray, str, float, np.ndarray]:
    """Ground height grid ``(nrows, ncols)``, the method, the classified share and occupancy."""
    share = 0.0
    use_class = False
    if classification is not None and classification.size:
        share = float((classification == ground_code).mean())
        use_class = share >= min_share
    size = spec.size
    occupied = np.zeros(size, dtype=bool)
    if use_class:
        sums = np.zeros(size, dtype=np.float64)
        counts = np.zeros(size, dtype=np.int64)
    else:
        lowest = np.full(size, np.inf, dtype=np.float32)
    for start in range(0, x.size, CHUNK):
        stop = start + CHUNK
        index = cell_index(x[start:stop], y[start:stop], spec)
        occupied[index] = True
        if use_class:
            chosen = classification[start:stop] == ground_code  # type: ignore[index]
            picked = index[chosen]
            counts += np.bincount(picked, minlength=size)
            sums += np.bincount(picked, weights=z[start:stop][chosen], minlength=size)
        else:
            np.minimum.at(lowest, index, z[start:stop])
    if use_class:
        grid = np.full(size, np.nan, dtype=np.float32)
        have = counts > 0
        grid[have] = (sums[have] / counts[have]).astype(np.float32)
    else:
        grid = lowest
        grid[~np.isfinite(grid)] = np.nan
    occupied_grid = occupied.reshape(spec.nrows, spec.ncols)
    filled = fill_nearest(
        grid.reshape(spec.nrows, spec.ncols), dilate(occupied_grid), max_gap_cells
    )
    method = "classification" if use_class else "lowest-return"
    return filled, method, share, occupied_grid


def sample_bilinear(grid: np.ndarray, x: np.ndarray, y: np.ndarray, spec: GridSpec) -> np.ndarray:
    """Bilinear interpolation of ``grid`` (cell-centre values) at float32 positions."""
    nrows, ncols = grid.shape
    fx = (x - np.float32(spec.x0)) / np.float32(spec.cell) - np.float32(0.5)
    fy = (y - np.float32(spec.y0)) / np.float32(spec.cell) - np.float32(0.5)
    floor_x = np.floor(fx)
    floor_y = np.floor(fy)
    j0 = floor_x.astype(np.int32)
    i0 = floor_y.astype(np.int32)
    wx = fx - floor_x
    wy = fy - floor_y
    j0c = np.clip(j0, 0, ncols - 1)
    j1c = np.clip(j0 + 1, 0, ncols - 1)
    i0c = np.clip(i0, 0, nrows - 1)
    i1c = np.clip(i0 + 1, 0, nrows - 1)
    top = grid[i0c, j0c] * (1 - wx) + grid[i0c, j1c] * wx
    bottom = grid[i1c, j0c] * (1 - wx) + grid[i1c, j1c] * wx
    return (top * (1 - wy) + bottom * wy).astype(np.float32)


# ---------------------------------------------------------------------------- canopy height model
def canopy_height_model(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    ground: np.ndarray,
    ground_spec: GridSpec,
    spec: GridSpec,
    max_height_m: float,
) -> tuple[np.ndarray, int]:
    """Maximum normalised height per CHM cell (NaN where no point) and the count of noise points."""
    chm = np.full(spec.size, -np.inf, dtype=np.float32)
    dropped = 0
    for start in range(0, x.size, CHUNK):
        stop = start + CHUNK
        xs, ys = x[start:stop], y[start:stop]
        height = z[start:stop] - sample_bilinear(ground, xs, ys, ground_spec)
        keep = height <= max_height_m
        dropped += int((~keep).sum())
        index = cell_index(xs, ys, spec)
        np.maximum.at(chm, index[keep], np.maximum(height[keep], 0.0))
    chm[~np.isfinite(chm)] = np.nan
    return chm.reshape(spec.nrows, spec.ncols), dropped


def smooth_mean(chm: np.ndarray, window: int) -> np.ndarray:
    """Square mean filter that ignores NaN cells.

    A cell with no data keeps NaN unless at least three of its neighbours have data, so sparse
    holes inside a canopy close while the edge of the data is not pushed outward.
    """
    if window <= 1:
        return chm.copy()
    radius = window // 2
    rows, cols = chm.shape
    padded = np.pad(chm, radius, constant_values=np.nan)
    sums = np.zeros(chm.shape, dtype=np.float32)
    counts = np.zeros(chm.shape, dtype=np.uint8)
    for dy in range(window):
        for dx in range(window):
            neighbour = padded[dy : dy + rows, dx : dx + cols]
            valid = ~np.isnan(neighbour)
            sums += np.where(valid, neighbour, 0.0)
            counts += valid
    mean = sums / np.maximum(counts, 1)
    had_data = ~np.isnan(chm)
    out = np.where(had_data | (counts >= 3), mean, np.nan)
    return out.astype(np.float32)


def window_maximum(values: np.ndarray, radius_cells: int, circular: bool = True) -> np.ndarray:
    """Maximum over a window of ``radius_cells`` (shifted maxima, no scipy).

    ``circular`` keeps offsets with ``dy² + dx² <= r²``; otherwise the full square is used.
    """
    rows, cols = values.shape
    padded = np.pad(values, radius_cells, constant_values=0.0)
    result = values.copy()
    for dy in range(-radius_cells, radius_cells + 1):
        for dx in range(-radius_cells, radius_cells + 1):
            if not (dy or dx):
                continue
            if circular and dy * dy + dx * dx > radius_cells * radius_cells:
                continue
            shifted = padded[
                radius_cells + dy : radius_cells + dy + rows,
                radius_cells + dx : radius_cells + dx + cols,
            ]
            np.maximum(result, shifted, out=result)
    return result


def _merge_touching(cells: np.ndarray, shape: tuple[int, int]) -> list[tuple[float, float]]:
    """Centroids (row, col) of 8-connected groups of candidate cells (plateaus -> one top)."""
    mask = np.zeros(shape, dtype=bool)
    mask[cells[:, 0], cells[:, 1]] = True
    rows, cols = shape
    padded = np.pad(mask, 1, constant_values=False)
    neighbours = np.zeros(shape, dtype=np.uint8)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if not (dy == 1 and dx == 1):
                neighbours += padded[dy : dy + rows, dx : dx + cols]
    isolated = mask & (neighbours == 0)
    tops = [(float(r), float(c)) for r, c in np.argwhere(isolated)]
    crowded = {(int(r), int(c)) for r, c in np.argwhere(mask & ~isolated)}
    seen: set[tuple[int, int]] = set()
    for start in sorted(crowded):
        if start in seen:
            continue
        seen.add(start)
        queue = deque([start])
        members: list[tuple[int, int]] = []
        while queue:
            r, c = queue.popleft()
            members.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nxt = (r + dr, c + dc)
                    if nxt in crowded and nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
        tops.append(
            (sum(m[0] for m in members) / len(members), sum(m[1] for m in members) / len(members))
        )
    tops.sort()
    return tops


def find_tree_tops(
    chm: np.ndarray, smoothed: np.ndarray, radius_cells: int, min_height_m: float
) -> tuple[np.ndarray, np.ndarray]:
    """Tree tops as ``(rows_cols (N, 2) float centroids, heights (N,))``.

    Positions are the local maxima of the *smoothed* CHM inside a circular window; a maximum is a
    tree top when the *unsmoothed* CHM in the 3 x 3 cells around it exceeds ``min_height_m`` (so
    smoothing does not lower a short tree below the threshold). Reported heights are that same
    unsmoothed maximum.
    """
    filled = np.nan_to_num(smoothed, nan=0.0)
    raw = np.nan_to_num(chm, nan=0.0)
    around = window_maximum(raw, 1, circular=False)
    peak = window_maximum(filled, radius_cells)
    candidates = np.argwhere((filled >= peak) & (filled > 0.0) & (around > min_height_m))
    if candidates.shape[0] == 0:
        return np.zeros((0, 2)), np.zeros(0)
    centroids = np.array(_merge_touching(candidates, filled.shape), dtype=float)
    rows = np.clip(np.rint(centroids[:, 0]).astype(int), 0, filled.shape[0] - 1)
    cols = np.clip(np.rint(centroids[:, 1]).astype(int), 0, filled.shape[1] - 1)
    return centroids, around[rows, cols].astype(float)
