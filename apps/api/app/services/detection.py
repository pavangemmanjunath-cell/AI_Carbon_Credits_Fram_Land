"""Satellite tree-cover detection on a plot's vegetation cube ("AI detected tree cover").

The detection is deterministic: an NDVI threshold plus connected components on the vegetation cube
the map and the change-over-time chart use (``GET /plots/{id}/cube``). The latest results are stored per plot (kind
``detection``) so deleting the plot deletes them; the patch polygons are private like the plot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.errors import ProblemError
from app.services.common import base_provenance, now_iso, short_id
from geo_engine.detection import (
    ConfigError,
    DetectionError,
    TreeCoverParams,
    detect_tree_cover,
    load_detection_config,
)

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

KIND = "detection"
TARGETS = ("tree-cover",)
CUBE_INDEX = "ndvi"
CUBE_MONTHS = 36  # the cube's default window (also used by the map and charts)
KEEP_PER_PLOT = 5  # older detections of a plot are pruned
MODEL_ID = "ndvi-threshold-connected-components"
MODEL_VERSION = "0.1.0"


class DetectionService:
    """Back end of ``POST /plots/{plot_id}/detect`` and ``GET /plots/{plot_id}/detections``."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    # -- helpers -------------------------------------------------------------------------
    def _params(self) -> TreeCoverParams:
        try:
            return TreeCoverParams.from_config(config_dir=self.ctx.settings.config_dir)
        except ConfigError as exc:
            raise ProblemError(
                500, "The detection parameters are missing or invalid.", type_slug="config-error"
            ) from exc

    def _provenance(self, cube: dict[str, Any], params: TreeCoverParams) -> dict[str, Any]:
        sources = [dict(self.ctx.router.satellite.provenance())]
        provenance = base_provenance(self.ctx.settings.atlas_mode, sources)
        try:
            config = load_detection_config(self.ctx.settings.config_dir)
            version = config.version
        except ConfigError:  # already reported by _params
            version = "unknown"
        provenance["model"] = {"id": MODEL_ID, "version": MODEL_VERSION}
        provenance["parameter_set"] = {
            "id": "config/detection.yaml#tree_cover",
            "version": version,
            "verification_status": params.verification_status,
        }
        provenance["cube"] = dict(cube.get("provenance") or {})
        provenance["notes"] = [
            "Heuristic detection from satellite NDVI: the confidence is a ranking score, "
            "not a probability.",
            "Thresholds are project assumptions (config/detection.yaml) until calibrated locally.",
        ]
        return provenance

    # -- commands ------------------------------------------------------------------------
    def detect(
        self, plot_id: str, target: str = "tree-cover", min_confidence: float = 0.5
    ) -> dict[str, Any]:
        """Run the detection for a plot, store it as the plot's latest and return it."""
        if target not in TARGETS:
            raise ProblemError(
                422,
                f"target must be one of {', '.join(TARGETS)}.",
                type_slug="validation-error",
            )
        plot = self.ctx.plots.require(plot_id)
        params = self._params()
        cube = self.ctx.cube.build(plot, CUBE_INDEX, CUBE_MONTHS)
        try:
            result = detect_tree_cover(
                cube, plot["geometry"], min_confidence=min_confidence, params=params
            )
        except DetectionError as exc:
            raise ProblemError(
                422, exc.detail, type_slug="detection-failed", extra={"code": exc.code}
            ) from None
        detection_id = short_id("DET-")
        record: dict[str, Any] = {
            "detection_id": detection_id,
            "plot_id": plot["plot_id"],
            **result.to_dict(),
            "created_at": now_iso(),
            "privacy": "private",
            "provenance": self._provenance(cube, params),
        }
        repo = self.ctx.repo
        repo.save_record(KIND, detection_id, record, plot["plot_id"])
        self._prune(plot["plot_id"])
        repo.audit(
            "plot.detected",
            plot["plot_id"],
            {"target": target, "patches": record["summary"]["patches"]},
        )
        return record

    def _prune(self, plot_id: str) -> None:
        records = self.ctx.repo.list_records(KIND, plot_id, limit=KEEP_PER_PLOT + 50)
        for old in records[KEEP_PER_PLOT:]:
            self.ctx.repo.delete_record(KIND, old["detection_id"])

    def latest(self, plot_id: str) -> dict[str, Any] | None:
        """The most recent detection stored for ``plot_id`` (``None`` when none was run)."""
        records = self.ctx.repo.list_records(KIND, plot_id, limit=1)
        return records[0] if records else None
