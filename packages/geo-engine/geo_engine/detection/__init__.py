"""Satellite tree-cover detection and the shared ``config/detection.yaml`` loader."""

from geo_engine.detection.config import (
    ConfigError,
    ConfigParameter,
    DetectionConfig,
    find_config_file,
    load_detection_config,
)
from geo_engine.detection.tree_cover import (
    DetectionError,
    TreeCoverParams,
    TreeCoverResult,
    composite_median,
    connected_patches,
    detect_tree_cover,
    heuristic_confidence,
)

__all__ = [
    "ConfigError",
    "ConfigParameter",
    "DetectionConfig",
    "DetectionError",
    "TreeCoverParams",
    "TreeCoverResult",
    "composite_median",
    "connected_patches",
    "detect_tree_cover",
    "find_config_file",
    "heuristic_confidence",
    "load_detection_config",
]
