"""Tree-cover patches from a vegetation cube: NDVI threshold + 8-connected components.

Steps (all numbers come from ``config/detection.yaml`` and are project assumptions):

1. **Composite** - per cell, the median of the last ``composite_slices`` monthly NDVI slices,
   ignoring null (cloud-masked) values, for cells whose centre is inside the plot.
2. **Candidates** - cells with a composite value at or above the threshold.
3. **Patches** - 8-connected candidate cells (breadth-first search); patches smaller than
   ``min_patch_cells`` are dropped.
4. **Heuristic confidence** (a ranking score, not a probability) = weighted sum of
   the NDVI margin above the threshold, the patch size and the share of composite months in which
   the patch stays above the threshold; patches below ``min_confidence`` are dropped.
5. **Polygons** - the union of a patch's cell rectangles, clipped to the plot boundary.

The cube is the ``GET /plots/{id}/cube`` payload: ``grid`` (rows, cols, cell_size_m, bbox),
``times`` (``YYYY-MM``), ``mask`` and ``values[t][row][col]`` with row 0 on the north edge.
"""

from __future__ import annotations

import warnings
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
import shapely
from shapely.errors import ShapelyError
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box, shape
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

from geo_engine.construct import geodesic_area_m2, geometry_to_geojson
from geo_engine.detection.config import ConfigError, DetectionConfig, load_detection_config
from geo_engine.errors import GeoEngineError

SECTION = "tree_cover"
COORD_DIGITS = 7  # ~1 cm
HIGH_PRECISION_DIGITS = 9  # used when snapping to 7 digits would make a patch invalid
EXACT_DIGITS = 15  # last resort: the patch as computed (float64 holds about 15 digits)
# Patches are clipped to the plot shrunk by this much (1e-7 degrees, ~1 cm): rounding the vertices
# to COORD_DIGITS moves them by at most 0.71e-7 degrees, so the rounded patch stays inside the plot.
CLIP_INSET_DEGREES = 1.0e-7
MIN_PART_AREA_M2 = 1.0  # clipping slivers smaller than this are not worth drawing
MAX_COMPOSITE_SLICES = 12
LABEL = "tree cover"
SMALL_PLOT_FACTOR = 4  # a plot under 4 x min_patch_cells grid cells gets a "small plot" note
TARGET = "tree-cover"


class DetectionError(GeoEngineError, ValueError):
    """The cube or the parameters cannot be analysed. ``code`` is a stable identifier."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class TreeCoverParams:
    """Tree-cover parameters, read from ``config/detection.yaml`` (section ``tree_cover``)."""

    threshold: float
    min_patch_cells: int
    composite_slices: int
    confidence_ndvi_ceiling: float
    confidence_reliable_cells: int
    default_min_confidence: float
    weight_spectral: float
    weight_size: float
    weight_persistence: float
    verification_status: str

    @classmethod
    def from_config(
        cls, config: DetectionConfig | None = None, config_dir: Path | str | None = None
    ) -> TreeCoverParams:
        config = config or load_detection_config(config_dir)
        get = config.value
        params = cls(
            threshold=float(get(SECTION, "ndvi_tree_cover_threshold")),
            min_patch_cells=int(get(SECTION, "min_patch_cells")),
            composite_slices=int(get(SECTION, "composite_slices")),
            confidence_ndvi_ceiling=float(get(SECTION, "confidence_ndvi_ceiling")),
            confidence_reliable_cells=int(get(SECTION, "confidence_reliable_cells")),
            default_min_confidence=float(get(SECTION, "default_min_confidence")),
            weight_spectral=float(get(SECTION, "confidence_weight_spectral")),
            weight_size=float(get(SECTION, "confidence_weight_size")),
            weight_persistence=float(get(SECTION, "confidence_weight_persistence")),
            verification_status=config.weakest_status(SECTION),
        )
        weights = params.weight_spectral + params.weight_size + params.weight_persistence
        if abs(weights - 1.0) > 1e-6:
            raise ConfigError(f"{config.path}: the tree_cover confidence weights must sum to 1")
        if not 1 <= params.composite_slices <= MAX_COMPOSITE_SLICES:
            raise ConfigError(
                f"{config.path}: composite_slices must be between 1 and {MAX_COMPOSITE_SLICES}"
            )
        if params.confidence_reliable_cells < 1 or params.min_patch_cells < 1:
            raise ConfigError(f"{config.path}: cell counts must be at least 1")
        return params

    def with_overrides(
        self,
        threshold: float | None = None,
        min_patch_cells: int | None = None,
    ) -> TreeCoverParams:
        values: dict[str, Any] = {}
        if threshold is not None:
            if isinstance(threshold, bool) or not -1.0 < float(threshold) < 1.0:
                raise DetectionError(
                    "invalid_threshold", "the NDVI threshold must be between -1 and 1"
                )
            values["threshold"] = float(threshold)
        if min_patch_cells is not None:
            if isinstance(min_patch_cells, bool) or not 1 <= int(min_patch_cells) <= 10_000:
                raise DetectionError(
                    "invalid_min_patch_cells", "min_patch_cells must be between 1 and 10 000"
                )
            values["min_patch_cells"] = int(min_patch_cells)
        return replace(self, **values) if values else self


@dataclass
class TreeCoverResult:
    """Outcome of :func:`detect_tree_cover` (``to_dict`` gives the API payload fields)."""

    method: str
    index: str
    threshold: float
    month: str
    features: list[dict[str, Any]]
    patches: int
    covered_fraction: float
    area_hectares: float
    limitations: list[str]
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": TARGET,
            "method": self.method,
            "index": self.index,
            "threshold": self.threshold,
            "month": self.month,
            "features": {"type": "FeatureCollection", "features": self.features},
            "summary": {
                "patches": self.patches,
                "covered_fraction": self.covered_fraction,
                "area_hectares": self.area_hectares,
            },
            "limitations": list(self.limitations),
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class _Cube:
    values: np.ndarray  # (times, rows, cols) float, NaN = no data
    mask: np.ndarray  # (rows, cols) bool, True = cell centre inside the plot
    times: list[str]
    rows: int
    cols: int
    cell_size_m: float
    bbox: tuple[float, float, float, float]
    index: str
    synthetic: bool


def _read_cube(cube: Mapping[str, Any]) -> _Cube:
    try:
        grid = cube["grid"]
        rows, cols = int(grid["rows"]), int(grid["cols"])
        cell_size = float(grid["cell_size_m"])
        bbox_values = [float(v) for v in grid["bbox"]]
        times = [str(t) for t in cube["times"]]
        raw_values = cube["values"]
        raw_mask = cube["mask"]
    except (KeyError, TypeError, ValueError) as exc:
        raise DetectionError(
            "invalid_cube", "the vegetation cube is incomplete or malformed"
        ) from exc
    if len(bbox_values) != 4 or rows < 1 or cols < 1 or cell_size <= 0:
        raise DetectionError("invalid_cube", "the vegetation cube grid is malformed")
    if not times:
        raise DetectionError(
            "no_imagery",
            "the vegetation cube has no monthly slices, so there is nothing to analyse",
        )
    try:
        values = np.array(raw_values, dtype=float)
        mask = np.array(raw_mask, dtype=float) > 0
    except (TypeError, ValueError) as exc:
        raise DetectionError(
            "invalid_cube", "the vegetation cube holds non-numeric values"
        ) from exc
    if values.shape != (len(times), rows, cols) or mask.shape != (rows, cols):
        raise DetectionError("invalid_cube", "the vegetation cube dimensions do not match its grid")
    index = str(cube.get("index", "ndvi")).lower()
    provenance = cube.get("provenance")
    source = str(provenance.get("source", "")) if isinstance(provenance, Mapping) else ""
    return _Cube(
        values=values,
        mask=mask,
        times=times,
        rows=rows,
        cols=cols,
        cell_size_m=cell_size,
        bbox=(bbox_values[0], bbox_values[1], bbox_values[2], bbox_values[3]),
        index=index,
        synthetic="synthetic" in source.lower() or str(cube.get("mode", "")).lower() == "demo",
    )


def composite_median(
    values: np.ndarray, mask: np.ndarray, slices: int
) -> tuple[np.ndarray, np.ndarray]:
    """Per-cell median of the last ``slices`` monthly slices (nulls ignored) and those slices.

    Cells outside ``mask`` and cells with no value in any of the slices are NaN.
    """
    last = values[-slices:]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # "All-NaN slice encountered"
        composite = np.nanmedian(last, axis=0)
    composite = np.where(mask, composite, np.nan)
    return composite, last


def connected_patches(candidate: np.ndarray) -> list[list[tuple[int, int]]]:
    """8-connected groups of ``True`` cells, in row-major order of their first cell."""
    rows, cols = candidate.shape
    seen = np.zeros(candidate.shape, dtype=bool)
    patches: list[list[tuple[int, int]]] = []
    for start_row, start_col in np.argwhere(candidate):
        start = (int(start_row), int(start_col))
        if seen[start]:
            continue
        seen[start] = True
        queue = deque([start])
        cells: list[tuple[int, int]] = []
        while queue:
            row, col = queue.popleft()
            cells.append((row, col))
            for d_row in (-1, 0, 1):
                for d_col in (-1, 0, 1):
                    n_row, n_col = row + d_row, col + d_col
                    if (
                        0 <= n_row < rows
                        and 0 <= n_col < cols
                        and candidate[n_row, n_col]
                        and not seen[n_row, n_col]
                    ):
                        seen[n_row, n_col] = True
                        queue.append((n_row, n_col))
        patches.append(cells)
    return patches


def heuristic_confidence(
    mean_ndvi: float,
    cells: int,
    persistence: float,
    params: TreeCoverParams,
) -> float:
    """Weighted score in [0, 1] from the NDVI margin, the patch size and the persistence.

    It ranks patches; it is **not** the probability that the patch is trees.
    """
    span = params.confidence_ndvi_ceiling - params.threshold
    spectral = 1.0 if span <= 0 else min(1.0, max(0.0, (mean_ndvi - params.threshold) / span))
    size = min(1.0, cells / params.confidence_reliable_cells)
    score = (
        params.weight_spectral * spectral
        + params.weight_size * size
        + params.weight_persistence * min(1.0, max(0.0, persistence))
    )
    return min(1.0, max(0.0, score))


def _persistence(last: np.ndarray, rows: np.ndarray, cols: np.ndarray, threshold: float) -> float:
    """Share of the composite months (with data on the patch) whose patch mean is >= threshold."""
    months = 0
    hits = 0
    for layer in last:
        patch_values = layer[rows, cols]
        finite = patch_values[np.isfinite(patch_values)]
        if finite.size == 0:
            continue
        months += 1
        hits += int(float(finite.mean()) >= threshold)
    return hits / months if months else 0.0


def _runs_as_boxes(cells: Sequence[tuple[int, int]], cube: _Cube) -> list[Polygon]:
    """Cell rectangles with horizontal neighbours merged into one box per run."""
    west, south, east, north = cube.bbox
    d_lon = (east - west) / cube.cols
    d_lat = (north - south) / cube.rows
    by_row: dict[int, list[int]] = {}
    for row, col in cells:
        by_row.setdefault(row, []).append(col)
    boxes: list[Polygon] = []
    for row in sorted(by_row):
        columns = sorted(by_row[row])
        start = previous = columns[0]
        runs: list[tuple[int, int]] = []
        for col in columns[1:]:
            if col == previous + 1:
                previous = col
                continue
            runs.append((start, previous))
            start = previous = col
        runs.append((start, previous))
        top = north - row * d_lat
        for first, last in runs:
            boxes.append(box(west + first * d_lon, top - d_lat, west + (last + 1) * d_lon, top))
    return boxes


def _polygonal_part(geometry: BaseGeometry) -> Polygon | MultiPolygon | None:
    """Keep the polygon parts of a clipping result (drops lines, points and slivers)."""
    if geometry.is_empty:
        return None
    if isinstance(geometry, Polygon):
        parts: list[Polygon] = [geometry]
    elif isinstance(geometry, MultiPolygon):
        parts = list(geometry.geoms)
    elif isinstance(geometry, GeometryCollection):
        parts = []
        for member in geometry.geoms:
            if isinstance(member, Polygon):
                parts.append(member)
            elif isinstance(member, MultiPolygon):
                parts.extend(member.geoms)
    else:
        return None
    parts = [p for p in parts if not p.is_empty and geodesic_area_m2(p) >= MIN_PART_AREA_M2]
    if not parts:
        return None
    oriented = [orient(p.simplify(1e-9, preserve_topology=True), 1.0) for p in parts]
    return oriented[0] if len(oriented) == 1 else MultiPolygon(oriented)


def _plot_polygon(plot_geometry: Mapping[str, Any] | BaseGeometry) -> BaseGeometry:
    try:
        geometry = (
            plot_geometry if isinstance(plot_geometry, BaseGeometry) else shape(dict(plot_geometry))
        )
    except (TypeError, ValueError, AttributeError, KeyError, ShapelyError) as exc:
        raise DetectionError("invalid_plot", "the plot geometry could not be read") from exc
    if not isinstance(geometry, Polygon | MultiPolygon) or geometry.is_empty:
        raise DetectionError("invalid_plot", "the plot geometry must be a Polygon")
    if not geometry.is_valid:
        geometry = shapely.make_valid(geometry)
    return geometry


def _clip_region(plot: BaseGeometry) -> BaseGeometry:
    """The plot shrunk by ``CLIP_INSET_DEGREES`` (the plot itself when that leaves nothing)."""
    inner = plot.buffer(-CLIP_INSET_DEGREES, join_style="mitre")
    if inner.is_empty or not inner.is_valid:
        return plot
    return inner


def _oriented(geometry: BaseGeometry) -> BaseGeometry:
    """Exterior rings counter-clockwise (RFC 7946), which snapping to a grid does not keep."""
    if isinstance(geometry, Polygon) and not geometry.is_empty:
        return orient(geometry, 1.0)
    if isinstance(geometry, MultiPolygon):
        return MultiPolygon([orient(part, 1.0) for part in geometry.geoms if not part.is_empty])
    return geometry


def _geojson(geometry: Polygon | MultiPolygon, plot: BaseGeometry) -> dict[str, Any]:
    """GeoJSON on a ~1 cm grid; a finer grid, then the exact coordinates, when snapping a patch
    to the grid would make it invalid (two corners of touching cells merge) or push it outside
    the plot."""
    for digits in (COORD_DIGITS, HIGH_PRECISION_DIGITS):
        snapped = _oriented(shapely.set_precision(geometry, 10.0**-digits))
        if (
            isinstance(snapped, Polygon | MultiPolygon)
            and not snapped.is_empty
            and snapped.is_valid
            and plot.contains(snapped)
        ):
            return geometry_to_geojson(snapped, digits)
    return geometry_to_geojson(geometry, EXACT_DIGITS)


def _limitations(
    cube: _Cube, params: TreeCoverParams, slices_used: int, valid_share: float, plot_cells: int
) -> list[str]:
    notes = [
        f"{cube.cell_size_m:g} m grid cells show groups of trees, not individual crowns, and "
        "patch edges follow the grid.",
        "NDVI is high for any dense green vegetation (crops, grass, shrubs), so a patch is "
        "vegetation that looks like tree cover, not a confirmed tree.",
        f"The NDVI threshold ({params.threshold:g}) is a project assumption that has not been "
        "calibrated against field data for this crop, season or region.",
        "The confidence is a heuristic score from the NDVI margin, the patch size and how steadily "
        "the patch stays green over the composite months; it is not a probability.",
    ]
    if slices_used < params.composite_slices:
        notes.append(
            f"Only {slices_used} monthly slice{'s' if slices_used != 1 else ''} "
            f"{'were' if slices_used != 1 else 'was'} available (the composite normally uses "
            f"{params.composite_slices}), so cloud or a single date can weigh more."
        )
    if plot_cells < SMALL_PLOT_FACTOR * params.min_patch_cells:
        notes.append(
            f"The plot covers only {plot_cells} cell{'s' if plot_cells != 1 else ''} of the "
            f"{cube.cell_size_m:g} m grid and a patch needs at least {params.min_patch_cells} "
            "touching cells, so a plot this small can show few or no patches."
        )
    if valid_share < 0.5:
        notes.append(
            f"Only {valid_share:.0%} of the plot has a usable satellite value in the composite "
            "months (cloud or no data); the result may miss tree cover."
        )
    if cube.synthetic:
        notes.append(
            "Demo mode: the vegetation cube is synthetic, so this result illustrates the workflow "
            "and does not describe real land."
        )
    return notes


def detect_tree_cover(
    cube: Mapping[str, Any],
    plot_geometry: Mapping[str, Any] | BaseGeometry,
    threshold: float | None = None,
    min_patch_cells: int | None = None,
    min_confidence: float | None = None,
    *,
    params: TreeCoverParams | None = None,
) -> TreeCoverResult:
    """Find tree-cover patches in a vegetation cube (see the module docstring).

    ``threshold``, ``min_patch_cells`` and ``min_confidence`` default to ``config/detection.yaml``.
    Raises :class:`DetectionError` when the cube is malformed, has no monthly slice or is not an
    NDVI cube, or when a parameter is out of range.
    """
    params = (params or TreeCoverParams.from_config()).with_overrides(threshold, min_patch_cells)
    minimum = params.default_min_confidence if min_confidence is None else min_confidence
    if isinstance(minimum, bool) or not 0.0 <= float(minimum) <= 1.0:
        raise DetectionError("invalid_min_confidence", "min_confidence must be between 0 and 1")
    minimum = float(minimum)

    data = _read_cube(cube)
    if data.index != "ndvi":
        raise DetectionError(
            "wrong_index", f"tree-cover detection needs an NDVI cube, not {data.index!r}"
        )
    plot = _plot_polygon(plot_geometry)
    region = _clip_region(plot)
    plot_area_m2 = geodesic_area_m2(plot)
    if plot_area_m2 <= 0.0 or not data.mask.any():
        raise DetectionError("empty_plot", "the plot covers no cell of the vegetation grid")

    slices = min(params.composite_slices, len(data.times))
    composite, last = composite_median(data.values, data.mask, slices)
    inside = int(data.mask.sum())
    has_value = np.isfinite(composite)
    valid_share = float(has_value.sum()) / inside if inside else 0.0
    candidate = has_value & (np.nan_to_num(composite, nan=-1.0) >= params.threshold)

    dropped_small = 0
    dropped_low = 0
    kept: list[dict[str, Any]] = []
    for cells in connected_patches(candidate):
        if len(cells) < params.min_patch_cells:
            dropped_small += 1
            continue
        rows = np.fromiter((c[0] for c in cells), dtype=int, count=len(cells))
        cols = np.fromiter((c[1] for c in cells), dtype=int, count=len(cells))
        mean_ndvi = float(composite[rows, cols].mean())
        persistence = _persistence(last, rows, cols, params.threshold)
        confidence = heuristic_confidence(mean_ndvi, len(cells), persistence, params)
        if confidence < minimum:
            dropped_low += 1
            continue
        union = shapely.union_all(_runs_as_boxes(cells, data))
        clipped = _polygonal_part(union.intersection(region))
        if clipped is None:
            continue
        kept.append(
            {
                "geometry": clipped,
                "area_m2": geodesic_area_m2(clipped),
                "mean_ndvi": mean_ndvi,
                "confidence": confidence,
                "cells": len(cells),
                "first": (int(rows[0]), int(cols[0])),
            }
        )

    kept.sort(key=lambda p: (-p["area_m2"], p["first"]))
    features: list[dict[str, Any]] = []
    for number, patch in enumerate(kept, start=1):
        features.append(
            {
                "type": "Feature",
                "geometry": _geojson(patch["geometry"], plot),
                "properties": {
                    "id": f"P{number}",
                    "label": LABEL,
                    "confidence": round(patch["confidence"], 3),
                    "area_m2": round(patch["area_m2"], 1),
                    "mean_ndvi": round(patch["mean_ndvi"], 3),
                    "cells": patch["cells"],
                },
            }
        )
    covered_m2 = float(sum(p["area_m2"] for p in kept))
    return TreeCoverResult(
        method=(
            f"NDVI threshold + connected components on the {data.cell_size_m:g} m vegetation grid"
        ),
        index=data.index,
        threshold=params.threshold,
        month=data.times[-1],
        features=features,
        patches=len(features),
        covered_fraction=round(min(1.0, covered_m2 / plot_area_m2), 4),
        area_hectares=round(covered_m2 / 10_000.0, 4),
        limitations=_limitations(data, params, slices, valid_share, inside),
        parameters={
            "threshold": params.threshold,
            "min_patch_cells": params.min_patch_cells,
            "min_confidence": minimum,
            "composite_slices": slices,
            "composite_months": data.times[-slices:],
            "cell_size_m": data.cell_size_m,
            "ndvi_ceiling": params.confidence_ndvi_ceiling,
            "reliable_cells": params.confidence_reliable_cells,
            "weights": {
                "spectral": params.weight_spectral,
                "size": params.weight_size,
                "persistence": params.weight_persistence,
            },
            "verification_status": params.verification_status,
            "valid_cell_share": round(valid_share, 3),
            "dropped_patches": {"too_small": dropped_small, "low_confidence": dropped_low},
        },
    )
