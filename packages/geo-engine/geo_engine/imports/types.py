"""Data structures and contract limits for vector imports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

# Contract limits (docs/architecture/api-contract.md, §Imports) — structural, not tunable.
MAX_FEATURES = 20_000
MAX_PREVIEW_FEATURES = 5_000
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 100
MAX_TOTAL_VERTICES = 2_000_000

CONFIDENCE_FIELDS = ("score", "confidence", "prob", "probability")
HEIGHT_FIELDS = ("height", "height_m", "h", "tree_height", "tree_height_m")
# Numeric columns that identify a row rather than describe a tree (ignored when deciding whether
# a handful of points are boundary corners).
ID_LIKE_FIELDS = frozenset(
    {
        "id",
        "fid",
        "objectid",
        "oid",
        "no",
        "number",
        "index",
        "idx",
        "seq",
        "n",
        "nr",
        "pt",
        "point",
    }
    | {"vertex", "order", "sr", "sno", "sl", "serial", "corner", "num", "pointid", "cornerid"}
)
VECTOR_FORMATS = {"geojson": "geojson", "json": "geojson", "kml": "kml", "kmz": "kmz", "csv": "csv"}


def field_key(name: str) -> str:
    """Lower-case alphanumeric form of a property name (``Tree_Height`` -> ``treeheight``)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


@dataclass
class RawFeature:
    """One polygon or point read from a file (WGS84 lon/lat)."""

    geometry: BaseGeometry
    properties: dict[str, Any] = field(default_factory=dict)
    name: str | None = None


@dataclass
class ParsedVector:
    """Features read from a file, before they are interpreted."""

    format: str
    features: list[RawFeature]
    warnings: list[str] = field(default_factory=list)
    name: str | None = None


@dataclass
class TreeSet:
    """Trees found in a file: points, or crowns (positions are crown centroids)."""

    kind: str  # "points" | "crowns"
    geometries: list[BaseGeometry]
    xs: np.ndarray
    ys: np.ndarray
    confidence: np.ndarray | None
    height_m: np.ndarray | None
    confidence_field: str | None
    min_confidence: float | None
    total_in_file: int
    method: str

    def __len__(self) -> int:
        return len(self.geometries)


@dataclass
class VectorImport:
    """Interpreted vector file (contract: kind ``boundary`` / ``tree-points`` / ``tree-crowns``)."""

    format: str
    kind: str
    feature_count: int
    polygon_count: int
    point_count: int
    warnings: list[str]
    boundary: dict[str, Any] | None = None
    boundary_polygon: Polygon | None = None
    trees: TreeSet | None = None
    name: str | None = None
    notes: list[str] = field(default_factory=list)
