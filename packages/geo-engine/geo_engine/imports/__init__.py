"""Imports: read GeoJSON / KML / KMZ / CSV uploads and say what they are.

``parse_vector(filename, data, purpose)`` returns a :class:`VectorImport` whose ``kind`` is
``boundary``, ``tree-points`` or ``tree-crowns``; :func:`describe_import` turns it into the pieces
of the API record (counts inside a plot, height statistics, map preview). Point clouds live in
:mod:`geo_engine.pointcloud`.
"""

from geo_engine.imports.classify import PURPOSES, looks_like_crowns
from geo_engine.imports.counting import count_inside, describe_import, describe_trees, height_stats
from geo_engine.imports.errors import ImportDataError, UnsupportedFormatError
from geo_engine.imports.params import VectorImportParams
from geo_engine.imports.types import (
    MAX_ARCHIVE_BYTES,
    MAX_ARCHIVE_ENTRIES,
    MAX_FEATURES,
    MAX_PREVIEW_FEATURES,
    TreeSet,
    VectorImport,
)
from geo_engine.imports.vector import file_extension, parse_vector, vector_format

__all__ = [
    "MAX_ARCHIVE_BYTES",
    "MAX_ARCHIVE_ENTRIES",
    "MAX_FEATURES",
    "MAX_PREVIEW_FEATURES",
    "PURPOSES",
    "ImportDataError",
    "TreeSet",
    "UnsupportedFormatError",
    "VectorImport",
    "VectorImportParams",
    "count_inside",
    "describe_import",
    "describe_trees",
    "file_extension",
    "height_stats",
    "looks_like_crowns",
    "parse_vector",
    "vector_format",
]
