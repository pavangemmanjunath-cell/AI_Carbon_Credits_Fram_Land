"""KML and KMZ readers.

KML is parsed with ``defusedxml`` and DTDs are refused outright (no XXE, no entity expansion,
no external references). Namespaces are ignored (KML 2.0 to 2.3 and ``gx`` extensions). Polygons
(outer and inner boundaries), points and ``MultiGeometry`` are imported; lines are skipped.

KMZ is a ZIP archive: the reader refuses archives declaring more than 100 entries or more than
50 MB uncompressed, never extracts to disk, and reads the chosen ``.kml`` with a hard byte cap, so
a zip bomb cannot expand beyond the limit even when the headers lie.
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Any
from xml.etree.ElementTree import Element

from geo_engine.imports.errors import ImportDataError, UnsupportedFormatError
from geo_engine.imports.shapes import Collector, clean_properties, feature_name
from geo_engine.imports.types import MAX_ARCHIVE_BYTES, MAX_ARCHIVE_ENTRIES, ParsedVector

_GEOMETRY_TAGS = {
    "Polygon",
    "Point",
    "MultiGeometry",
    "LineString",
    "LinearRing",
    "Track",
    "MultiTrack",
}
_LINE_TAGS = {"LineString", "LinearRing", "Track", "MultiTrack"}
_SPACES_AROUND_COMMA = re.compile(r"\s*,\s*")


def _local(tag: Any) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _children(element: Element, name: str) -> list[Element]:
    return [child for child in element if _local(child.tag) == name]


def _first(element: Element, name: str) -> Element | None:
    for child in element:
        if _local(child.tag) == name:
            return child
    return None


def _coordinates(element: Element | None) -> list[list[float]]:
    """``<coordinates>`` text -> list of ``[lon, lat(, alt)]`` positions."""
    if element is None or not element.text:
        return []
    text = _SPACES_AROUND_COMMA.sub(",", element.text.strip())
    positions: list[list[float]] = []
    for chunk in text.split():
        try:
            positions.append([float(part) for part in chunk.split(",") if part != ""])
        except ValueError as exc:
            raise ImportDataError("invalid_content", "the KML holds invalid coordinates") from exc
    return positions


def _ring(boundary: Element | None) -> list[list[float]]:
    if boundary is None:
        return []
    ring = _first(boundary, "LinearRing")
    return _coordinates(_first(ring, "coordinates")) if ring is not None else []


def _add_geometry(
    element: Element, props: dict[str, Any], name: str | None, out: Collector, depth: int = 0
) -> None:
    tag = _local(element.tag)
    if tag == "Polygon":
        rings = [_ring(_first(element, "outerBoundaryIs"))]
        rings += [_ring(inner) for inner in _children(element, "innerBoundaryIs")]
        out.add_polygon([ring for ring in rings if ring] if rings[0] else [], props, name)
    elif tag == "Point":
        positions = _coordinates(_first(element, "coordinates"))
        if positions:
            out.add_point(positions[0], props, name)
        else:
            out.skip("no_geometry")
    elif tag == "MultiGeometry":
        if depth >= 4:
            out.skip("unsupported")
            return
        for child in element:
            if _local(child.tag) in _GEOMETRY_TAGS:
                _add_geometry(child, props, name, out, depth + 1)
    elif tag in _LINE_TAGS:
        out.skip("line")


def _extended_data(placemark: Element) -> dict[str, Any]:
    """``ExtendedData`` ``Data/value`` and ``SchemaData/SimpleData`` pairs (numbers converted)."""
    raw: dict[str, Any] = {}
    for extended in _children(placemark, "ExtendedData"):
        for child in extended:
            tag = _local(child.tag)
            if tag == "Data" and child.get("name"):
                value = _first(child, "value")
                raw[str(child.get("name"))] = (
                    (value.text or "").strip() if value is not None else ""
                )
            elif tag == "SchemaData":
                for simple in _children(child, "SimpleData"):
                    if simple.get("name"):
                        raw[str(simple.get("name"))] = (simple.text or "").strip()
    props: dict[str, Any] = {}
    for key, value in raw.items():
        try:
            props[key] = float(value)
        except ValueError:
            props[key] = value
    return clean_properties(props)


def _safe_root(data: bytes) -> Element:
    """Parse XML with ``defusedxml`` (no DOCTYPE, so no external entities or entity expansion)."""
    try:
        from defusedxml import DefusedXmlException
        from defusedxml import ElementTree as SafeET
    except ImportError as exc:  # the optional dependency is missing: say so, do not guess
        raise UnsupportedFormatError(
            "this server cannot read KML or KMZ (the 'defusedxml' package is not installed); "
            "upload GeoJSON or CSV instead",
            code="xml_backend_missing",
        ) from exc
    try:
        return SafeET.fromstring(data, forbid_dtd=True)
    except DefusedXmlException as exc:
        raise ImportDataError(
            "unsafe_xml",
            "the XML contains a DOCTYPE or entity declarations, which are not accepted",
        ) from exc
    except (SafeET.ParseError, ValueError, RecursionError) as exc:
        raise ImportDataError("invalid_content", "the file is not well-formed KML") from exc


def parse_kml(data: bytes, fmt: str = "kml") -> ParsedVector:
    """Read a KML document from bytes."""
    root = _safe_root(data)
    if _local(root.tag) not in ("kml", "Document", "Folder", "Placemark"):
        raise ImportDataError("invalid_content", "the XML is not a KML document")

    out = Collector()
    document_name: str | None = None
    for element in root.iter():
        tag = _local(element.tag)
        if tag == "Document" and document_name is None:
            title = _first(element, "name")
            if title is not None and title.text and title.text.strip():
                document_name = title.text.strip()[:200]
        if tag != "Placemark":
            continue
        props = _extended_data(element)
        label = _first(element, "name")
        name = label.text.strip()[:200] if label is not None and label.text else None
        name = name or feature_name(props)
        if name:
            props.setdefault("name", name)
        for child in element:
            if _local(child.tag) in _GEOMETRY_TAGS:
                _add_geometry(child, props, name, out)
    return ParsedVector(
        format=fmt, features=out.features, warnings=out.warnings(), name=document_name
    )


def parse_kmz(data: bytes) -> ParsedVector:
    """Read a KMZ archive (``doc.kml`` or the first ``.kml`` inside) from bytes."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ImportDataError("bad_archive", "the file is not a valid KMZ (ZIP) archive") from exc
    with archive:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_ENTRIES:
            raise ImportDataError(
                "archive_too_many_entries",
                f"the archive has {len(entries)} entries; the maximum is {MAX_ARCHIVE_ENTRIES}",
            )
        if sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES:
            raise ImportDataError(
                "archive_too_large",
                f"the archive expands to more than {MAX_ARCHIVE_BYTES // (1024 * 1024)} MB",
            )
        kml_entries = [e for e in entries if not e.is_dir() and e.filename.lower().endswith(".kml")]
        if not kml_entries:
            raise ImportDataError("invalid_content", "the KMZ archive holds no .kml file")
        chosen = next(
            (e for e in kml_entries if e.filename.lower() == "doc.kml"),
            next(
                (e for e in kml_entries if e.filename.lower().endswith("/doc.kml")), kml_entries[0]
            ),
        )
        if chosen.flag_bits & 0x1:
            raise ImportDataError("bad_archive", "encrypted KMZ archives are not supported")
        try:
            with archive.open(chosen) as handle:
                payload = handle.read(MAX_ARCHIVE_BYTES + 1)
        except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError, EOFError) as exc:
            raise ImportDataError(
                "bad_archive", "the KMZ archive could not be decompressed"
            ) from exc
        except Exception as exc:  # zlib.error, lzma/bz2 errors and other decoder failures
            raise ImportDataError(
                "bad_archive", "the KMZ archive could not be decompressed"
            ) from exc
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ImportDataError(
            "archive_too_large",
            f"the KML inside the archive exceeds {MAX_ARCHIVE_BYTES // (1024 * 1024)} MB",
        )
    return parse_kml(payload, fmt="kmz")
