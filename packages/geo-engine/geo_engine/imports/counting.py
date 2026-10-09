"""Describe an interpreted import for the API record: counts inside a plot, heights, preview."""

from __future__ import annotations

from typing import Any

import numpy as np
import shapely
from shapely.geometry import Polygon

from geo_engine.construct import geodesic_area_m2, geometry_to_geojson
from geo_engine.imports.types import MAX_PREVIEW_FEATURES, TreeSet, VectorImport

PREVIEW_DIGITS = 6


def count_inside(plot: Polygon, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Boolean array: which positions fall inside (or on the edge of) ``plot``.

    Shapely prepares the polygon once for the whole array, so this stays fast for 20 000 points.
    """
    if len(xs) == 0:
        return np.zeros(0, dtype=bool)
    return np.asarray(shapely.intersects_xy(plot, xs, ys), dtype=bool)


def height_stats(heights: np.ndarray | None) -> dict[str, float | None]:
    """Mean, median and 90th percentile of the finite heights (``None`` when there are none)."""
    empty: dict[str, float | None] = {
        "mean_height_m": None,
        "median_height_m": None,
        "p90_height_m": None,
    }
    if heights is None:
        return empty
    finite = heights[np.isfinite(heights)]
    if finite.size == 0:
        return empty
    return {
        "mean_height_m": round(float(finite.mean()), 2),
        "median_height_m": round(float(np.median(finite)), 2),
        "p90_height_m": round(float(np.percentile(finite, 90)), 2),
    }


def _crown_cover(trees: TreeSet, plot: Polygon) -> float | None:
    """Share of the plot covered by the union of the crowns (overlaps counted once)."""
    if trees.kind != "crowns" or not trees.geometries:
        return None
    plot_area = geodesic_area_m2(plot)
    if plot_area <= 0.0:
        return None
    crowns = shapely.make_valid(np.array(trees.geometries, dtype=object))
    covered = shapely.union_all(crowns).intersection(plot)
    return round(min(1.0, geodesic_area_m2(covered) / plot_area), 4)


def describe_trees(trees: TreeSet, plot: Polygon | None) -> dict[str, Any]:
    """The contract's ``trees`` block (``count_in_plot`` is ``None`` without a plot)."""
    block: dict[str, Any] = {
        "count": len(trees),
        "count_in_plot": None,
        **height_stats(trees.height_m),
        "canopy_cover_fraction": None,
        "confidence_field": trees.confidence_field,
        "min_confidence": trees.min_confidence,
        "method": trees.method,
    }
    if plot is not None:
        block["count_in_plot"] = int(count_inside(plot, trees.xs, trees.ys).sum())
        block["canopy_cover_fraction"] = _crown_cover(trees, plot)
    return block


def _tree_features(trees: TreeSet, plot: Polygon | None, limit: int) -> tuple[list[dict], int]:
    total = len(trees)
    if total == 0:
        return [], 0
    if total > limit:
        chosen = np.unique(np.linspace(0, total - 1, limit).astype(int))
    else:
        chosen = np.arange(total)
    inside = count_inside(plot, trees.xs[chosen], trees.ys[chosen]) if plot is not None else None
    features: list[dict[str, Any]] = []
    for slot, index in enumerate(chosen):
        properties: dict[str, Any] = {"id": int(index) + 1}
        if inside is not None:
            properties["in_plot"] = bool(inside[slot])
        if trees.confidence is not None and np.isfinite(trees.confidence[index]):
            properties["confidence"] = round(float(trees.confidence[index]), 3)
        if trees.height_m is not None and np.isfinite(trees.height_m[index]):
            properties["height_m"] = round(float(trees.height_m[index]), 2)
        features.append(
            {
                "type": "Feature",
                "geometry": geometry_to_geojson(trees.geometries[int(index)], PREVIEW_DIGITS),
                "properties": properties,
            }
        )
    return features, total


def describe_import(
    vector: VectorImport, plot: Polygon | None = None, preview_limit: int = MAX_PREVIEW_FEATURES
) -> dict[str, Any]:
    """Everything the API record needs from an interpreted vector file.

    Returns ``summary``, ``boundary``, ``trees``, ``preview`` (up to ``preview_limit`` features,
    a deterministic even subsample when there are more) and any extra ``warnings``.
    """
    extra_warnings: list[str] = []
    preview: list[dict[str, Any]] = []
    if vector.boundary_polygon is not None:
        preview.append(
            {
                "type": "Feature",
                "geometry": geometry_to_geojson(vector.boundary_polygon, PREVIEW_DIGITS),
                "properties": {"role": "boundary", "name": vector.name},
            }
        )
    trees_block = None
    if vector.trees is not None:
        trees_block = describe_trees(vector.trees, plot)
        features, total = _tree_features(vector.trees, plot, preview_limit)
        preview.extend(features)
        if total > len(features):
            extra_warnings.append(f"The map preview shows {len(features)} of {total} trees.")
    return {
        "summary": {
            "feature_count": vector.feature_count,
            "polygon_count": vector.polygon_count,
            "point_count": vector.point_count,
            "georeferenced": True,
            "crs": "EPSG:4326",
        },
        "boundary": vector.boundary,
        "trees": trees_block,
        "preview": {"type": "FeatureCollection", "features": preview},
        "warnings": extra_warnings,
    }
