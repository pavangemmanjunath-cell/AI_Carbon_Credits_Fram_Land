"""Entry point: read a GeoJSON / KML / KMZ / CSV upload and interpret it."""

from __future__ import annotations

from pathlib import PurePosixPath

from geo_engine.geometry import ValidationLimits
from geo_engine.imports.classify import build_vector_import
from geo_engine.imports.csv_points import parse_csv
from geo_engine.imports.errors import ImportDataError, UnsupportedFormatError
from geo_engine.imports.geojson import parse_geojson
from geo_engine.imports.kml import parse_kml, parse_kmz
from geo_engine.imports.params import VectorImportParams
from geo_engine.imports.types import VECTOR_FORMATS, ParsedVector, VectorImport

POINT_CLOUD_EXTENSIONS = {"las", "laz", "e57"}


def file_extension(filename: str) -> str:
    """Lower-case extension of the last path component, without the dot."""
    name = PurePosixPath(filename.replace("\\", "/")).name
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def vector_format(filename: str) -> str:
    """``geojson`` | ``kml`` | ``kmz`` | ``csv`` for a supported vector file name."""
    extension = file_extension(filename)
    if extension in VECTOR_FORMATS:
        return VECTOR_FORMATS[extension]
    if extension in POINT_CLOUD_EXTENSIONS:
        raise UnsupportedFormatError("point clouds are analysed with analyse_point_cloud")
    raise UnsupportedFormatError(
        "unsupported file type: use .geojson, .json, .kml, .kmz, .csv, .las or .laz"
    )


def read_vector(filename: str, data: bytes) -> ParsedVector:
    """Parse the bytes of a vector file without interpreting them."""
    fmt = vector_format(filename)
    if not data.strip():
        raise ImportDataError("empty_file", "the file is empty")
    if fmt == "geojson":
        return parse_geojson(data)
    if fmt == "kml":
        return parse_kml(data)
    if fmt == "kmz":
        return parse_kmz(data)
    return parse_csv(data)


def parse_vector(
    filename: str,
    data: bytes,
    purpose: str = "auto",
    *,
    limits: ValidationLimits | None = None,
    min_confidence: float | None = None,
    params: VectorImportParams | None = None,
) -> VectorImport:
    """Read and interpret a vector upload.

    ``purpose`` is ``auto`` (default), ``boundary`` or ``trees``. ``limits`` are the plot
    validation limits (vertices, area); ``min_confidence`` overrides the default 0.5 used with a
    ``score`` / ``confidence`` / ``prob`` / ``probability`` field. Raises :class:`ImportDataError`
    (or :class:`UnsupportedFormatError`) with a stable ``code`` and a plain-language ``detail``.
    """
    if min_confidence is not None and not 0.0 <= min_confidence <= 1.0:
        raise ImportDataError("invalid_min_confidence", "min_confidence must be between 0 and 1")
    parsed = read_vector(filename, data)
    return build_vector_import(
        parsed,
        purpose,
        limits or ValidationLimits(),
        params or VectorImportParams.from_config(),
        min_confidence,
    )
