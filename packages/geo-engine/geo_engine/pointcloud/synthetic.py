"""Deterministic synthetic orchards as LAS / LAZ bytes (tests and sample data; not used by the API).

Cone-shaped trees stand on noisy ground. Points are random returns on the crown surface and on
the ground, so a point-cloud analysis can be checked against the known number and position of the
trees. Everything is generated from a seed: the same arguments give the same bytes.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import date

import numpy as np
from pyproj import CRS

# A fixed file creation date keeps the bytes of a generated file reproducible.
FIXED_CREATION_DATE = date(2026, 10, 5)
CLASS_UNCLASSIFIED = 1
CLASS_GROUND = 2
CLASS_HIGH_VEGETATION = 5


@dataclass(frozen=True)
class SyntheticOrchard:
    """Points (CRS metres) plus the trees that were planted."""

    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    classification: np.ndarray
    tree_x: np.ndarray
    tree_y: np.ndarray
    tree_height_m: np.ndarray
    epsg: int
    origin: tuple[float, float]
    size_m: tuple[float, float]

    @property
    def n_trees(self) -> int:
        return int(self.tree_x.size)

    @property
    def n_points(self) -> int:
        return int(self.x.size)


def _tree_positions(
    n_trees: int, size_m: tuple[float, float], rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Trees on a jittered grid, so neighbours stay at least ~60% of the grid pitch apart."""
    width, height = size_m
    cols = max(1, math.ceil(math.sqrt(n_trees * width / height)))
    rows = max(1, math.ceil(n_trees / cols))
    pitch_x, pitch_y = width / cols, height / rows
    slots = rng.permutation(cols * rows)[:n_trees]
    col, row = slots % cols, slots // cols
    jitter = rng.uniform(-0.2, 0.2, size=(n_trees, 2))
    xs = (col + 0.5 + jitter[:, 0]) * pitch_x
    ys = (row + 0.5 + jitter[:, 1]) * pitch_y
    return xs, ys


def make_orchard(
    n_trees: int = 60,
    *,
    tree_xy: np.ndarray | None = None,
    origin: tuple[float, float] = (500_000.0, 1_500_000.0),
    size_m: tuple[float, float] = (100.0, 100.0),
    height_range_m: tuple[float, float] = (4.0, 12.0),
    crown_radius_per_height: float = 0.25,
    crown_radius_base_m: float = 1.0,
    ground_points_per_m2: float = 4.0,
    crown_points_per_m2: float = 12.0,
    ground_noise_m: float = 0.05,
    ground_elevation_m: float = 300.0,
    ground_slope: float = 0.0,
    classified: bool = True,
    seed: int = 7,
    epsg: int = 32643,
) -> SyntheticOrchard:
    """A rectangle of ground (``size_m``) with ``n_trees`` cones (height 4-12 m by default).

    ``tree_xy`` (metres from ``origin``) places the trees explicitly; otherwise they stand on a
    jittered grid. ``classified`` labels ground returns 2 and crown returns 5 (ASPRS); otherwise
    every point is 1 (unclassified) and the analysis has to estimate the ground itself.
    """
    rng = np.random.default_rng(seed)
    width, height = size_m
    if tree_xy is not None:
        tree_x = np.asarray(tree_xy, dtype=float)[:, 0]
        tree_y = np.asarray(tree_xy, dtype=float)[:, 1]
        n_trees = int(tree_x.size)
    else:
        tree_x, tree_y = _tree_positions(n_trees, size_m, rng)
    tree_h = rng.uniform(height_range_m[0], height_range_m[1], size=n_trees)

    def ground_z(px: np.ndarray, py: np.ndarray) -> np.ndarray:
        return ground_elevation_m + ground_slope * px + 0.0 * py

    n_ground = int(round(width * height * ground_points_per_m2))
    gx = rng.uniform(0.0, width, n_ground)
    gy = rng.uniform(0.0, height, n_ground)
    gz = ground_z(gx, gy) + rng.normal(0.0, ground_noise_m, n_ground)

    cx_parts: list[np.ndarray] = []
    cy_parts: list[np.ndarray] = []
    cz_parts: list[np.ndarray] = []
    for tx, ty, th in zip(tree_x, tree_y, tree_h, strict=True):
        radius = crown_radius_base_m + crown_radius_per_height * th
        count = max(8, int(round(crown_points_per_m2 * math.pi * radius * radius)))
        distance = radius * np.sqrt(rng.uniform(0.0, 1.0, count))
        angle = rng.uniform(0.0, 2.0 * math.pi, count)
        px = tx + distance * np.cos(angle)
        py = ty + distance * np.sin(angle)
        pz = ground_z(px, py) + th * (1.0 - distance / radius) + rng.normal(0.0, 0.03, count)
        # one return on the apex so the crown's top is always sampled
        cx_parts.append(np.append(px, tx))
        cy_parts.append(np.append(py, ty))
        cz_parts.append(np.append(pz, ground_z(np.array([tx]), np.array([ty]))[0] + th))
    cx = np.concatenate(cx_parts) if cx_parts else np.zeros(0)
    cy = np.concatenate(cy_parts) if cy_parts else np.zeros(0)
    cz = np.concatenate(cz_parts) if cz_parts else np.zeros(0)
    keep = (cx >= 0.0) & (cx <= width) & (cy >= 0.0) & (cy <= height)
    cx, cy, cz = cx[keep], cy[keep], cz[keep]

    x = np.concatenate([gx, cx])
    y = np.concatenate([gy, cy])
    z = np.concatenate([gz, cz])
    if classified:
        classes = np.concatenate(
            [
                np.full(gx.size, CLASS_GROUND, dtype=np.uint8),
                np.full(cx.size, CLASS_HIGH_VEGETATION, dtype=np.uint8),
            ]
        )
    else:
        classes = np.full(x.size, CLASS_UNCLASSIFIED, dtype=np.uint8)
    order = rng.permutation(x.size)
    return SyntheticOrchard(
        x=x[order] + origin[0],
        y=y[order] + origin[1],
        z=z[order],
        classification=classes[order],
        tree_x=tree_x + origin[0],
        tree_y=tree_y + origin[1],
        tree_height_m=tree_h,
        epsg=epsg,
        origin=origin,
        size_m=size_m,
    )


def to_las_bytes(
    orchard: SyntheticOrchard,
    *,
    compressed: bool = False,
    with_crs: bool = True,
    epsg: int | None = None,
    point_format: int = 6,
) -> bytes:
    """Serialise the points as LAS 1.4 (or LAZ when ``compressed``), optionally with a CRS."""
    import laspy

    header = laspy.LasHeader(point_format=point_format, version="1.4")
    header.scales = np.array([0.01, 0.01, 0.01])
    header.offsets = np.array([math.floor(orchard.x.min()), math.floor(orchard.y.min()), 0.0])
    header.creation_date = FIXED_CREATION_DATE
    if with_crs:
        header.add_crs(CRS.from_epsg(epsg or orchard.epsg))
    las = laspy.LasData(header)
    las.x = orchard.x
    las.y = orchard.y
    las.z = orchard.z
    las.classification = orchard.classification
    buffer = io.BytesIO()
    las.write(buffer, do_compress=compressed)
    return buffer.getvalue()


def match_trees(
    found_xy: np.ndarray, planted_xy: np.ndarray, tolerance_m: float
) -> tuple[int, int, int]:
    """Greedy nearest matching of detections to planted trees: ``(matched, missed, extra)``."""
    if found_xy.size == 0:
        return 0, int(len(planted_xy)), 0
    remaining = list(range(len(found_xy)))
    matched = 0
    for tx, ty in planted_xy:
        if not remaining:
            break
        distances = [math.hypot(found_xy[i, 0] - tx, found_xy[i, 1] - ty) for i in remaining]
        best = int(np.argmin(distances))
        if distances[best] <= tolerance_m:
            matched += 1
            remaining.pop(best)
    return matched, int(len(planted_xy)) - matched, int(len(found_xy)) - matched
