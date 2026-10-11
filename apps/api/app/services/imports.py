"""File imports ("Import data"): GeoJSON, KML, KMZ, CSV, LAS and LAZ -> a derived record.

The raw file is **never stored**: it is read from memory, interpreted by the geo-engine and only
the derived record (summary, boundary or trees, an optional map preview, warnings, provenance)
is kept through the generic repository record API (kind ``import``). A record linked to a plot
is deleted with the plot. Records are private, like the plot polygon. No coordinate is logged.
"""

from __future__ import annotations

import logging
import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

import shapely
from shapely.geometry import Polygon, shape

from app.core.errors import ProblemError
from app.services.common import base_provenance, now_iso, short_id
from geo_engine.detection import ConfigError, load_detection_config
from geo_engine.geometry import ValidationLimits
from geo_engine.imports import (
    ImportDataError,
    UnsupportedFormatError,
    VectorImportParams,
    describe_import,
    parse_vector,
)
from geo_engine.pointcloud import (
    E57_ADVICE,
    PointCloudParams,
    analyse_point_cloud,
    inspect_point_cloud,
    pye57_available,
)

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

log = logging.getLogger("carboncreditbuy.imports")

KIND = "import"
VECTOR_EXTENSIONS = ("geojson", "json", "kml", "kmz", "csv")
POINT_CLOUD_EXTENSIONS = ("las", "laz", "e57")
ALLOWED_EXTENSIONS = (*VECTOR_EXTENSIONS, *POINT_CLOUD_EXTENSIONS)
PURPOSES = ("auto", "boundary", "trees")
MAX_FILENAME_CHARS = 200
LIST_LIMIT = 100
HEAD_BYTES = 8192
MODEL_ID = "chm-local-maxima"
MODEL_VERSION = "0.1.0"
_BOMS = (b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")
_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


# ---------------------------------------------------------------------------- file checks
def extension_of(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def safe_filename(filename: str | None) -> str:
    """Base name only, without control characters, at most ``MAX_FILENAME_CHARS`` long."""
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    name = _CONTROL.sub("", name).strip()
    if len(name) > MAX_FILENAME_CHARS:
        stem, dot, extension = name.rpartition(".")
        if dot and 0 < len(extension) <= 10:
            name = stem[: MAX_FILENAME_CHARS - len(extension) - 1] + "." + extension
        else:
            name = name[:MAX_FILENAME_CHARS]
    return name or "upload"


def _text_head(head: bytes) -> str:
    """The start of a text file, decoded leniently, without BOM and leading whitespace."""
    if head.startswith(_UTF16_BOMS):
        return head.decode("utf-16", errors="ignore").lstrip()
    if head.startswith(_BOMS[0]):
        head = head[len(_BOMS[0]) :]
    return head.decode("utf-8", errors="ignore").lstrip()


def signature_problem(extension: str, data: bytes) -> str | None:
    """Plain-language reason when the first bytes do not fit the extension (``None`` = fine)."""
    head = data[:HEAD_BYTES]
    if extension in ("las", "laz"):
        ok = head[:4] == b"LASF"
        kind = "a LAS/LAZ point cloud"
    elif extension == "e57":
        ok = head[:8] == b"ASTM-E57"
        kind = "an E57 point cloud"
    elif extension == "kmz":
        ok = head[:4] == b"PK\x03\x04"
        kind = "a KMZ (ZIP) archive"
    elif extension == "kml":
        ok = _text_head(head).startswith("<")
        kind = "a KML (XML) document"
    elif extension in ("geojson", "json"):
        ok = _text_head(head).startswith("{")
        kind = "a GeoJSON object"
    else:  # csv: any text; binary data is not
        ok = b"\x00" not in head or head.startswith(_UTF16_BOMS)
        kind = "CSV text"
    if ok:
        return None
    return (
        f"The file does not look like {kind}: its content does not match the "
        f".{extension} extension."
    )


def _unsupported(detail: str, code: str) -> ProblemError:
    """415 problem: the file type (or its content) is not one this server reads."""
    return ProblemError(
        415,
        detail,
        title="Unsupported Media Type",
        type_slug="unsupported-file-type",
        extra={"code": code},
    )


def _file_problem(exc: ImportDataError) -> ProblemError:
    """RFC 7807 problem for an engine error (messages never hold coordinates)."""
    if isinstance(exc, UnsupportedFormatError):
        return _unsupported(exc.detail, exc.code)
    return ProblemError(422, exc.detail, type_slug="invalid-file", extra={"code": exc.code})


# ---------------------------------------------------------------------------- service
class ImportService:
    """Back end of ``POST /imports``, ``GET /imports``, ``GET/DELETE /imports/{import_id}``."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        settings = ctx.settings
        self.limits = ValidationLimits(
            max_vertices=settings.atlas_max_plot_vertices,
            max_area_ha=settings.atlas_max_plot_area_ha,
        )

    # -- helpers -------------------------------------------------------------------------
    def _config_version(self) -> tuple[str, Any]:
        try:
            config = load_detection_config(self.ctx.settings.config_dir)
        except ConfigError as exc:
            raise ProblemError(
                500, "The detection parameters are missing or invalid.", type_slug="config-error"
            ) from exc
        return config.version, config

    def _provenance(self, fmt: str, kind: str) -> dict[str, Any]:
        version, config = self._config_version()
        provenance = base_provenance(
            self.ctx.settings.atlas_mode,
            [
                {
                    "id": "user-upload",
                    "name": f"User-supplied {fmt} file",
                    "version": None,
                    "license": "Supplied by the user; not stored and not redistributed",
                    "attribution": "The data owner (the person who uploaded the file)",
                    "url": None,
                }
            ],
        )
        notes = ["The raw file was not stored; only this derived record was kept."]
        if kind == "point-cloud":
            section = "point_cloud"
            provenance["model"] = {"id": MODEL_ID, "version": MODEL_VERSION}
            notes.append(
                "Tree tops come from a canopy height model and local maxima; compare with a field "
                "count before relying on the number."
            )
        else:
            section = "vector_import"
        provenance["parameter_set"] = {
            "id": f"config/detection.yaml#{section}",
            "version": version,
            "verification_status": config.weakest_status(section),
        }
        provenance["notes"] = notes
        return provenance

    def _plot_polygon(self, plot_id: str | None) -> tuple[str | None, Polygon | None]:
        if not plot_id:
            return None, None
        plot = self.ctx.plots.require(plot_id)  # 404 when the plot does not exist
        return plot["plot_id"], shape(plot["geometry"])

    @staticmethod
    def _footprint_warnings(
        plot: Polygon | None, bbox_wgs84: list[float] | None, trees: dict[str, Any] | None
    ) -> list[str]:
        warnings: list[str] = []
        if plot is None:
            return warnings
        if bbox_wgs84 is not None and not shapely.box(*bbox_wgs84).intersects(plot):
            warnings.append(
                "The point cloud does not overlap the plot, so no tree can fall inside it; check "
                "that the file is the right one."
            )
        elif trees and trees.get("count") and trees.get("count_in_plot") == 0:
            warnings.append(
                f"None of the {trees['count']} trees falls inside the plot; check that the file "
                "and the plot are the same place and that the file's coordinate system is right."
            )
        return warnings

    # -- vector files --------------------------------------------------------------------
    def _vector(
        self,
        data: bytes,
        filename: str,
        plot: Polygon | None,
        purpose: str,
        min_confidence: float | None,
    ) -> dict[str, Any]:
        try:
            params = VectorImportParams.from_config(config_dir=self.ctx.settings.config_dir)
            vector = parse_vector(
                filename,
                data,
                purpose,
                limits=self.limits,
                min_confidence=min_confidence,
                params=params,
            )
        except ConfigError as exc:
            raise ProblemError(
                500, "The import parameters are missing or invalid.", type_slug="config-error"
            ) from exc
        described = describe_import(vector, plot)
        warnings = [*vector.warnings, *described["warnings"]]
        warnings.extend(self._footprint_warnings(plot, None, described["trees"]))
        return {
            "format": vector.format,
            "kind": vector.kind,
            "summary": described["summary"],
            "boundary": described["boundary"],
            "trees": described["trees"],
            "detection": None,
            "preview": described["preview"],
            "warnings": warnings,
        }

    # -- point clouds --------------------------------------------------------------------
    def _point_cloud(
        self, data: bytes, filename: str, plot: Polygon | None, run_detection: bool
    ) -> dict[str, Any]:
        if extension_of(filename) == "e57" and not pye57_available():
            raise _unsupported(E57_ADVICE, "e57_unsupported")
        try:
            params = PointCloudParams.from_config(config_dir=self.ctx.settings.config_dir)
        except ConfigError as exc:
            raise ProblemError(
                500, "The detection parameters are missing or invalid.", type_slug="config-error"
            ) from exc
        if run_detection:
            return self._analysed_cloud(data, filename, plot, params)
        return self._inspected_cloud(data, filename, plot)

    def _analysed_cloud(
        self, data: bytes, filename: str, plot: Polygon | None, params: PointCloudParams
    ) -> dict[str, Any]:
        result = analyse_point_cloud(data, filename, params)
        trees = result.trees_block(plot)
        preview, note = result.preview(plot)
        warnings = list(result.warnings)
        if note:
            warnings.append(note)
        warnings.extend(self._footprint_warnings(plot, result.bbox_wgs84, trees))
        if plot is not None and not result.georeferenced:
            warnings.append(
                "The point cloud has no coordinate system, so trees cannot be counted inside "
                "the plot."
            )
        return {
            "format": result.format,
            "kind": "point-cloud",
            "summary": result.summary_block(),
            "boundary": None,
            "trees": trees,
            "detection": result.detection_block(),
            "preview": preview,
            "warnings": warnings,
        }

    def _inspected_cloud(self, data: bytes, filename: str, plot: Polygon | None) -> dict[str, Any]:
        info = inspect_point_cloud(data, filename)
        warnings = [*info.warnings, *self._footprint_warnings(plot, info.bbox_wgs84, None)]
        return {
            "format": info.format,
            "kind": "point-cloud",
            "summary": {
                "feature_count": 1,
                "polygon_count": 0,
                "point_count": info.point_count,
                "georeferenced": info.georeferenced,
                "crs": info.crs,
            },
            "boundary": None,
            "trees": None,
            "detection": {
                "ran": False,
                "method": None,
                "parameters": None,
                "notes": ["Tree detection was switched off for this import."],
            },
            "preview": None,
            "warnings": warnings,
        }

    # -- commands ------------------------------------------------------------------------
    def create(
        self,
        data: bytes,
        filename: str,
        plot_id: str | None = None,
        purpose: str = "auto",
        run_detection: bool = True,
        min_confidence: float | None = None,
    ) -> dict[str, Any]:
        """Interpret an uploaded file and store the derived record (never the file itself)."""
        name = safe_filename(filename)
        extension = extension_of(name)
        if extension not in ALLOWED_EXTENSIONS:
            raise _unsupported(
                "Unsupported file type: upload .geojson, .json, .kml, .kmz, .csv, .las or .laz "
                "(.e57 only when the server has the optional pye57 package). "
                f"Got .{extension or '(none)'}.",
                "unsupported_extension",
            )
        if purpose not in PURPOSES:
            raise ProblemError(
                422, f"purpose must be one of {', '.join(PURPOSES)}.", type_slug="validation-error"
            )
        limit = self.ctx.settings.max_upload_bytes
        if len(data) > limit:
            raise ProblemError(
                413,
                f"The file is larger than the upload limit of {limit // (1024 * 1024)} MB.",
                type_slug="payload-too-large",
            )
        if not data:
            raise ProblemError(
                422, "The file is empty.", type_slug="invalid-file", extra={"code": "empty_file"}
            )
        problem = signature_problem(extension, data)
        if problem:
            raise _unsupported(problem, "signature_mismatch")
        linked_plot_id, plot = self._plot_polygon(plot_id)

        try:
            if extension in POINT_CLOUD_EXTENSIONS:
                parts = self._point_cloud(data, name, plot, run_detection)
            else:
                parts = self._vector(data, name, plot, purpose, min_confidence)
        except ImportDataError as exc:
            raise _file_problem(exc) from None
        except ProblemError:
            raise
        except Exception as exc:  # never let an engine message (it may hold coordinates) escape
            log.error("import processing failed (%s)", type(exc).__name__)
            raise ProblemError(
                500, "The file could not be processed.", type_slug="import-failed"
            ) from None

        import_id = short_id("IMP-")
        record: dict[str, Any] = {
            "import_id": import_id,
            "filename": name,
            "format": parts["format"],
            "size_bytes": len(data),
            "created_at": now_iso(),
            "plot_id": linked_plot_id,
            "kind": parts["kind"],
            "status": "ready",
            "summary": parts["summary"],
            "boundary": parts["boundary"],
            "trees": parts["trees"],
            "detection": parts["detection"],
            "preview": parts["preview"],
            "warnings": parts["warnings"],
            "privacy": "private",
            "provenance": self._provenance(parts["format"], parts["kind"]),
        }
        self.ctx.repo.save_record(KIND, import_id, record, linked_plot_id)
        self.ctx.repo.audit(
            "import.created",
            linked_plot_id,
            {"format": parts["format"], "kind": parts["kind"], "size_bytes": len(data)},
        )
        return record

    def list(self, plot_id: str | None = None) -> list[dict[str, Any]]:
        """Stored imports, newest first, without the map preview."""
        records = self.ctx.repo.list_records(KIND, plot_id or None, limit=LIST_LIMIT)
        return [{k: v for k, v in record.items() if k != "preview"} for record in records]

    def get(self, import_id: str) -> dict[str, Any]:
        record = self.ctx.repo.get_record(KIND, import_id)
        if record is None:
            raise ProblemError(
                404, f"Import {import_id} was not found.", type_slug="import-not-found"
            )
        return record

    def delete(self, import_id: str) -> None:
        record = self.get(import_id)
        self.ctx.repo.delete_record(KIND, import_id)
        self.ctx.repo.audit("import.deleted", record.get("plot_id"), {"kind": record.get("kind")})
