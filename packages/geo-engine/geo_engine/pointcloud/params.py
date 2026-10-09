"""Point-cloud parameters, read from ``config/detection.yaml`` (section ``point_cloud``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geo_engine.detection.config import DetectionConfig, load_detection_config

SECTION = "point_cloud"
MAX_GRID_CELLS_PER_SIDE = 4_000  # contract: the CHM grid stays within 4 000 x 4 000 cells


@dataclass(frozen=True)
class PointCloudParams:
    """Tree-top detection parameters. All values are project assumptions (see the YAML)."""

    cell_size_m: float
    min_height_m: float
    window_radius_m: float
    max_tree_height_m: float
    ground_cell_size_m: float
    ground_class_code: int
    noise_class_codes: tuple[int, ...]
    ground_class_min_share: float
    smoothing_window_cells: int
    max_points: int
    max_points_hard_limit: int
    max_ground_gap_cells: int
    low_density_warning_per_m2: float

    @classmethod
    def from_config(
        cls, config: DetectionConfig | None = None, config_dir: Path | str | None = None
    ) -> PointCloudParams:
        config = config or load_detection_config(config_dir)
        get = config.value
        return cls(
            cell_size_m=float(get(SECTION, "cell_size_m")),
            min_height_m=float(get(SECTION, "min_height_m")),
            window_radius_m=float(get(SECTION, "window_radius_m")),
            max_tree_height_m=float(get(SECTION, "max_tree_height_m")),
            ground_cell_size_m=float(get(SECTION, "ground_cell_size_m")),
            ground_class_code=int(get(SECTION, "ground_class_code")),
            noise_class_codes=tuple(int(c) for c in get(SECTION, "noise_class_codes")),
            ground_class_min_share=float(get(SECTION, "ground_class_min_share")),
            smoothing_window_cells=int(get(SECTION, "smoothing_window_cells")),
            max_points=int(get(SECTION, "max_points")),
            max_points_hard_limit=int(get(SECTION, "max_points_hard_limit")),
            max_ground_gap_cells=int(get(SECTION, "max_ground_gap_cells")),
            low_density_warning_per_m2=float(get(SECTION, "low_density_warning_per_m2")),
        )

    def detection_parameters(self, effective_cell_size_m: float | None = None) -> dict[str, Any]:
        """The ``detection.parameters`` block of the import record."""
        return {
            "cell_size_m": effective_cell_size_m or self.cell_size_m,
            "min_height_m": self.min_height_m,
            "window_radius_m": self.window_radius_m,
            "ground_cell_size_m": self.ground_cell_size_m,
            "smoothing_window_cells": self.smoothing_window_cells,
            "max_tree_height_m": self.max_tree_height_m,
        }
