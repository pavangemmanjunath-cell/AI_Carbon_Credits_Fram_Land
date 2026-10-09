"""Interpretation parameters for vector imports, read from ``config/detection.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geo_engine.detection.config import DetectionConfig, load_detection_config

SECTION = "vector_import"


@dataclass(frozen=True)
class VectorImportParams:
    """How ``purpose = auto`` reads a file (all values are project assumptions)."""

    crown_median_area_m2: float
    min_polygons_for_median: int
    crown_count_threshold: int
    crown_max_area_ha: float
    default_min_confidence: float
    corner_points_min: int
    corner_points_max: int
    corner_min_area_ha: float

    @classmethod
    def from_config(
        cls, config: DetectionConfig | None = None, config_dir: Path | str | None = None
    ) -> VectorImportParams:
        config = config or load_detection_config(config_dir)
        get = config.value
        return cls(
            crown_median_area_m2=float(get(SECTION, "crown_median_area_m2")),
            min_polygons_for_median=int(get(SECTION, "min_polygons_for_median")),
            crown_count_threshold=int(get(SECTION, "crown_count_threshold")),
            crown_max_area_ha=float(get(SECTION, "crown_max_area_ha")),
            default_min_confidence=float(get(SECTION, "default_min_confidence")),
            corner_points_min=int(get(SECTION, "corner_points_min")),
            corner_points_max=int(get(SECTION, "corner_points_max")),
            corner_min_area_ha=float(get(SECTION, "corner_min_area_ha")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "crown_median_area_m2": self.crown_median_area_m2,
            "min_polygons_for_median": self.min_polygons_for_median,
            "crown_count_threshold": self.crown_count_threshold,
            "crown_max_area_ha": self.crown_max_area_ha,
            "default_min_confidence": self.default_min_confidence,
            "corner_points_min": self.corner_points_min,
            "corner_points_max": self.corner_points_max,
            "corner_min_area_ha": self.corner_min_area_ha,
        }
