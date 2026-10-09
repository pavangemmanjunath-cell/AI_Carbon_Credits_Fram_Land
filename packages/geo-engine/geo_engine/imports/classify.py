"""Decide what a parsed vector file is: a boundary, tree points or tree crowns.

Rules (docs/architecture/api-contract.md §Imports; thresholds in ``config/detection.yaml``):

* ``boundary``: the largest polygon; with several large polygons (>= 0.05 ha) the largest is used
  and a warning says so.
* ``tree-crowns``: many small polygons - with every polygon below 0.05 ha, a median area below
  200 m² (three or more polygons) or ten or more polygons; with a larger polygon in the file, ten
  or more small ones that outnumber the large ones. Counted by centroid.
* ``tree-points``: points. A numeric ``score`` / ``confidence`` / ``prob`` / ``probability``
  field is used with ``min_confidence`` (default 0.5).
* points as corners: with ``purpose = boundary`` the points are the corners of a boundary; with
  ``auto`` when there are 3 to 50 points, no numeric attribute columns, and they form a valid
  polygon of at least 0.01 ha (a warning explains the interpretation).
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import shapely
from shapely.geometry import Point, Polygon

from geo_engine.construct import geodesic_area_m2, polygon_to_geojson
from geo_engine.errors import GeometryError
from geo_engine.geometry import ValidationLimits, measure_polygon, validate_polygon
from geo_engine.imports.errors import ImportDataError
from geo_engine.imports.params import VectorImportParams
from geo_engine.imports.types import (
    CONFIDENCE_FIELDS,
    HEIGHT_FIELDS,
    ID_LIKE_FIELDS,
    ParsedVector,
    RawFeature,
    TreeSet,
    VectorImport,
    field_key,
)

PURPOSES = ("auto", "boundary", "trees")
M2_PER_HA = 10_000.0


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _find_field(
    features: list[RawFeature], candidates: tuple[str, ...]
) -> tuple[str | None, np.ndarray | None]:
    """First candidate property present as a number in at least one feature."""
    original: dict[str, str] = {}
    for feature in features:
        for property_name in feature.properties:
            original.setdefault(field_key(property_name), property_name)
    for candidate in candidates:
        key = original.get(field_key(candidate))
        if key is None:
            continue
        values = np.array(
            [
                float(f.properties[key]) if _is_number(f.properties.get(key)) else np.nan
                for f in features
            ],
            dtype=float,
        )
        if np.isfinite(values).any():
            return key, values
    return None, None


def numeric_attributes(features: list[RawFeature]) -> set[str]:
    """Numeric property names other than coordinates and row identifiers."""
    names: set[str] = set()
    for feature in features:
        for key, value in feature.properties.items():
            if _is_number(value) and field_key(key) not in ID_LIKE_FIELDS:
                names.add(key)
    return names


def _clean_detail(detail: str) -> str:
    return re.sub(r"\s*\[[^\]]*\]", "", detail).strip()


# ---------------------------------------------------------------------------- boundaries
def _fit_vertices(polygon: Polygon, max_vertices: int, warnings: list[str]) -> Polygon:
    count = len(polygon.exterior.coords) - 1
    if count <= max_vertices:
        return polygon
    tolerance = 1e-6
    while tolerance <= 1e-3:
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        if isinstance(simplified, Polygon) and len(simplified.exterior.coords) - 1 <= max_vertices:
            kept = len(simplified.exterior.coords) - 1
            warnings.append(
                f"The boundary had {count} vertices and was simplified to {kept} "
                f"(tolerance about {tolerance * 111_000:.1f} m) to fit the limit of {max_vertices}."
            )
            return simplified
        tolerance *= 1.5
    raise ImportDataError(
        "too_many_vertices",
        f"the boundary has {count} vertices and cannot be simplified to {max_vertices}",
    )


def _validated_boundary(polygon: Polygon, limits: ValidationLimits, warnings: list[str]) -> Polygon:
    polygon = _fit_vertices(polygon, limits.max_vertices, warnings)
    try:
        return validate_polygon(polygon_to_geojson(polygon), limits)
    except GeometryError as exc:
        hint = ""
        if exc.code == "area_too_small":
            hint = " If the file holds tree crowns, choose purpose 'trees'."
        elif exc.code == "self_intersection":
            hint = " Fix the self-intersection in your GIS and upload again."
        raise ImportDataError(
            "invalid_boundary", f"The boundary is not usable: {_clean_detail(exc.detail)}.{hint}"
        ) from exc


def _boundary_dict(polygon: Polygon, name: str | None) -> dict[str, Any]:
    return {
        "geometry": polygon_to_geojson(polygon),
        "area_hectares": measure_polygon(polygon).area_hectares,
        "name": name,
    }


def _corner_ring(points: list[RawFeature]) -> Polygon | None:
    ring: list[tuple[float, float]] = []
    for feature in points:
        geometry = feature.geometry
        assert isinstance(geometry, Point)
        position = (geometry.x, geometry.y)
        if not ring or ring[-1] != position:
            ring.append(position)
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3:
        return None
    return Polygon([*ring, ring[0]])


# ---------------------------------------------------------------------------- trees
def _confidence_filter(
    features: list[RawFeature],
    min_confidence: float,
    warnings: list[str],
) -> tuple[list[int], np.ndarray | None, str | None, float | None]:
    """Indices to keep, confidence values (0-1), the field name and the threshold applied."""
    field, values = _find_field(features, CONFIDENCE_FIELDS)
    everything = list(range(len(features)))
    if field is None or values is None:
        return everything, None, None, None
    finite = values[np.isfinite(values)]
    low, high = float(finite.min()), float(finite.max())
    if low >= 0.0 and high <= 1.0:
        scaled = values
    elif low >= 0.0 and high <= 100.0:
        scaled = values / 100.0
        warnings.append(
            f"The '{field}' values go up to {high:g}, so they were read as percentages (0-100)."
        )
    else:
        warnings.append(
            f"The '{field}' values fall outside 0-1 and 0-100, so no confidence filter was applied."
        )
        return everything, None, field, None
    missing = int(np.isnan(scaled).sum())
    if missing:
        warnings.append(f"{missing} feature(s) have no '{field}' value and were kept.")
    keep = [i for i in everything if np.isnan(scaled[i]) or scaled[i] >= min_confidence]
    return keep, scaled, field, min_confidence


def _tree_set(
    features: list[RawFeature], kind: str, min_confidence: float, warnings: list[str], reason: str
) -> TreeSet:
    keep, scaled, field, applied = _confidence_filter(features, min_confidence, warnings)
    chosen = [features[i] for i in keep]
    _, heights = _find_field(chosen, HEIGHT_FIELDS)
    if heights is not None:
        heights = np.where(heights > 0, heights, np.nan)
        if not np.isfinite(heights).any():
            heights = None
    geometries = [f.geometry for f in chosen]
    if kind == "crowns":
        centroids = shapely.centroid(np.array(geometries, dtype=object)) if geometries else []
        xs = np.array([c.x for c in centroids], dtype=float)
        ys = np.array([c.y for c in centroids], dtype=float)
    else:
        xs = np.array([g.x for g in geometries], dtype=float)  # type: ignore[attr-defined]
        ys = np.array([g.y for g in geometries], dtype=float)  # type: ignore[attr-defined]
    noun = "crown polygons counted by centroid" if kind == "crowns" else "point features counted"
    method = f"{reason}: {noun}"
    if applied is not None and field is not None:
        method += f"; kept confidence >= {applied:g} on field '{field}'"
    return TreeSet(
        kind=kind,
        geometries=geometries,
        xs=xs,
        ys=ys,
        confidence=None if scaled is None else scaled[keep],
        height_m=heights,
        confidence_field=field,
        min_confidence=applied,
        total_in_file=len(features),
        method=method,
    )


def looks_like_crowns(areas_m2: np.ndarray, params: VectorImportParams) -> str | None:
    """Return the reason when the polygon areas look like tree crowns, else ``None``.

    * every polygon below ``crown_max_area_ha``: crowns when there are at least
      ``min_polygons_for_median`` of them with a median area below ``crown_median_area_m2``, or at
      least ``crown_count_threshold`` of them whatever their size;
    * some polygon at or above ``crown_max_area_ha`` (a field outline): crowns only when the small
      polygons number at least ``crown_count_threshold`` and outnumber the large ones - a boundary
      with a pond or two stays a boundary.
    """
    count = len(areas_m2)
    if count == 0:
        return None
    small = areas_m2 < params.crown_max_area_ha * M2_PER_HA
    n_small = int(small.sum())
    n_large = count - n_small
    if n_large == 0:
        median = float(np.median(areas_m2))
        if count >= params.min_polygons_for_median and median < params.crown_median_area_m2:
            return f"{count} polygons with a median area of {median:.0f} m²"
        if count >= params.crown_count_threshold:
            return f"{count} polygons, all smaller than {params.crown_max_area_ha:g} ha"
        return None
    if n_small >= params.crown_count_threshold and n_small > n_large:
        median = float(np.median(areas_m2[small]))
        return (
            f"{n_small} small polygons (median {median:.0f} m²) next to {n_large} larger "
            f"polygon{'s' if n_large != 1 else ''}"
        )
    return None


# ---------------------------------------------------------------------------- the decision
def build_vector_import(
    parsed: ParsedVector,
    purpose: str,
    limits: ValidationLimits,
    params: VectorImportParams,
    min_confidence: float | None = None,
) -> VectorImport:
    """Interpret ``parsed`` according to ``purpose`` (``auto`` | ``boundary`` | ``trees``)."""
    if purpose not in PURPOSES:
        raise ImportDataError("invalid_purpose", f"purpose must be one of {', '.join(PURPOSES)}")
    threshold = params.default_min_confidence if min_confidence is None else min_confidence
    polygons = [f for f in parsed.features if isinstance(f.geometry, Polygon)]
    points = [f for f in parsed.features if isinstance(f.geometry, Point)]
    if not polygons and not points:
        raise ImportDataError(
            "no_features",
            "the file holds no polygons or points (lines are not imported); nothing to import",
        )
    warnings = list(parsed.warnings)
    areas = np.array([geodesic_area_m2(f.geometry) for f in polygons], dtype=float)
    result = VectorImport(
        format=parsed.format,
        kind="unknown",
        feature_count=len(parsed.features),
        polygon_count=len(polygons),
        point_count=len(points),
        warnings=warnings,
        name=parsed.name,
    )

    def as_boundary() -> None:
        order = np.argsort(-areas, kind="stable")
        best = polygons[int(order[0])]
        large = int((areas >= params.crown_max_area_ha * M2_PER_HA).sum())
        if large > 1:
            warnings.append(
                f"The file holds {large} polygons of at least {params.crown_max_area_ha:g} ha; the "
                f"largest ({areas[order[0]] / M2_PER_HA:.2f} ha) was used as the boundary."
            )
        elif len(polygons) > 1:
            warnings.append(f"The file holds {len(polygons)} polygons; the largest was used.")
        polygon = _validated_boundary(best.geometry, limits, warnings)  # type: ignore[arg-type]
        result.kind = "boundary"
        result.boundary_polygon = polygon
        result.name = best.name or parsed.name
        result.boundary = _boundary_dict(polygon, result.name)
        if points:
            warnings.append(f"{len(points)} point feature(s) in the file were ignored.")

    def as_corners(explicit: bool) -> bool:
        candidate = _corner_ring(points)
        if candidate is None:
            if explicit:
                raise ImportDataError(
                    "no_boundary", "a boundary needs a polygon or at least three different points"
                )
            return False
        try:
            polygon = _validated_boundary(candidate, limits, warnings)
        except ImportDataError as exc:
            if explicit:
                raise ImportDataError(
                    "invalid_boundary",
                    "The points do not form a valid polygon in the order given. "
                    + exc.detail
                    + " List the corners in order around the boundary.",
                ) from exc
            return False
        area_ha = measure_polygon(polygon).area_hectares
        if not explicit and area_ha < params.corner_min_area_ha:
            return False
        result.kind = "boundary"
        result.boundary_polygon = polygon
        result.boundary = _boundary_dict(polygon, parsed.name)
        warnings.append(
            f"The {len(points)} points were read as the corners of a boundary, in file order, "
            "closed automatically."
            + ("" if explicit else " Choose purpose 'trees' to count them as trees instead.")
        )
        return True

    def as_crowns(reason: str) -> None:
        trees = _tree_set(polygons, "crowns", threshold, warnings, reason)
        result.kind = "tree-crowns"
        result.trees = trees
        if len(areas) >= 3:
            big = float(areas.max())
            if big >= params.crown_max_area_ha * M2_PER_HA and big > 10.0 * float(np.median(areas)):
                warnings.append(
                    f"One polygon is much larger than the rest ({big / M2_PER_HA:.2f} ha); check "
                    "that it is a tree crown."
                )
        if points:
            warnings.append(f"{len(points)} point feature(s) in the file were ignored.")

    def as_points(reason: str) -> None:
        result.kind = "tree-points"
        result.trees = _tree_set(points, "points", threshold, warnings, reason)
        if polygons:
            warnings.append(f"{len(polygons)} polygon feature(s) in the file were ignored.")

    if purpose == "boundary":
        if polygons:
            as_boundary()
        else:
            as_corners(explicit=True)
    elif purpose == "trees":
        if polygons and len(polygons) >= len(points):
            as_crowns("purpose 'trees'")
        else:
            as_points("purpose 'trees'")
    elif polygons:
        reason = looks_like_crowns(areas, params)
        if reason and len(polygons) >= len(points):
            as_crowns(reason)
        else:
            as_boundary()
    else:
        attributes = numeric_attributes(points)
        few = params.corner_points_min <= len(points) <= params.corner_points_max
        if few and not attributes and as_corners(explicit=False):
            pass
        else:
            as_points(f"{len(points)} point features")
    return result
