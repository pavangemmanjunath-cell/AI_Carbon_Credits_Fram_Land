"""GeoJSON reader (RFC 7946): FeatureCollection, Feature or a bare geometry.

Polygon, MultiPolygon, Point and MultiPoint are imported; a GeometryCollection is unpacked; lines
are skipped with a warning. Multi-part geometries become one feature per part, so the 20 000
feature limit also bounds a single huge MultiPoint.
"""

from __future__ import annotations

import json
import re
from typing import Any

from geo_engine.imports.errors import ImportDataError
from geo_engine.imports.shapes import Collector, clean_properties, feature_name
from geo_engine.imports.types import MAX_FEATURES, ParsedVector

_GEOMETRY_TYPES = {
    "Point",
    "MultiPoint",
    "Polygon",
    "MultiPolygon",
    "LineString",
    "MultiLineString",
    "GeometryCollection",
}
_WGS84_NAMES = re.compile(r"(CRS84|EPSG:{1,2}4326)$", re.IGNORECASE)


def _walk_geometry(
    geometry: Any, properties: dict[str, Any], name: str | None, out: Collector, depth: int = 0
) -> None:
    if not isinstance(geometry, dict):
        out.skip("no_geometry")
        return
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Polygon":
        if not isinstance(coordinates, list):
            raise ImportDataError("invalid_content", "Polygon coordinates must be an array")
        out.add_polygon(coordinates, properties, name)
    elif kind == "MultiPolygon":
        if not isinstance(coordinates, list):
            raise ImportDataError("invalid_content", "MultiPolygon coordinates must be an array")
        for part in coordinates:
            if not isinstance(part, list):
                raise ImportDataError("invalid_content", "MultiPolygon parts must be arrays")
            out.add_polygon(part, properties, name)
    elif kind == "Point":
        out.add_point(coordinates, properties, name)
    elif kind == "MultiPoint":
        if not isinstance(coordinates, list):
            raise ImportDataError("invalid_content", "MultiPoint coordinates must be an array")
        for position in coordinates:
            out.add_point(position, properties, name)
    elif kind in ("LineString", "MultiLineString"):
        out.skip("line")
    elif kind == "GeometryCollection":
        members = geometry.get("geometries")
        if depth >= 3 or not isinstance(members, list):
            out.skip("unsupported")
            return
        for member in members:
            _walk_geometry(member, properties, name, out, depth + 1)
    else:
        out.skip("unsupported")


def _check_crs(document: dict[str, Any]) -> None:
    crs = document.get("crs")
    if not isinstance(crs, dict):
        return
    properties = crs.get("properties")
    declared = properties.get("name") if isinstance(properties, dict) else None
    if isinstance(declared, str) and declared and not _WGS84_NAMES.search(declared.strip()):
        raise ImportDataError(
            "unsupported_crs",
            f"the file declares the coordinate system {declared[:60]!r}; only WGS84 longitude, "
            "latitude (EPSG:4326) is supported: reproject it first",
        )


def parse_geojson(data: bytes) -> ParsedVector:
    """Read a GeoJSON document from bytes."""
    try:
        document = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ImportDataError("invalid_content", "the file is not valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise ImportDataError("invalid_content", "GeoJSON must be a JSON object")
    _check_crs(document)

    kind = document.get("type")
    if kind == "FeatureCollection":
        members = document.get("features")
        if not isinstance(members, list):
            raise ImportDataError("invalid_content", "FeatureCollection.features must be an array")
        if len(members) > MAX_FEATURES * 2:
            raise ImportDataError(
                "too_many_features", f"the file holds more than {MAX_FEATURES} features"
            )
    elif kind == "Feature":
        members = [document]
    elif kind in _GEOMETRY_TYPES:
        members = [{"type": "Feature", "geometry": document, "properties": {}}]
    else:
        raise ImportDataError(
            "invalid_content", "expected a GeoJSON FeatureCollection, Feature or geometry"
        )

    out = Collector()
    for member in members:
        if not isinstance(member, dict) or member.get("type") != "Feature":
            out.skip("unsupported")
            continue
        properties = clean_properties(member.get("properties"))
        _walk_geometry(member.get("geometry"), properties, feature_name(properties), out)
    document_name = document.get("name") if isinstance(document.get("name"), str) else None
    return ParsedVector(
        format="geojson",
        features=out.features,
        warnings=out.warnings(),
        name=document_name,
    )
