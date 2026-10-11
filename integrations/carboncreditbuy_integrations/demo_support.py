"""Helpers shared by the ``Demo*`` adapter twins.

Demo twins are deterministic (seeded by their inputs) and clearly labelled
``synthetic-demo`` in provenance. They only need to be *plausible* so the UI,
tests and documentation screenshots work offline. Region bounding boxes come
from ``config/regions/*.yaml`` when available (no duplication of the region
contract); the per-region demo climate values below are synthetic.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RegionHint:
    id: str
    bbox: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    default_zone: str
    #: synthetic (MAT °C, MAP mm, elevation m) used by demo climate adapters
    demo_climate: tuple[float, float, float]
    demo_place: tuple[str, str, str]  # label, state/region, district


#: Synthetic demo climate per region (NOT observations; labelled synthetic-demo).
_DEMO_CLIMATE = {
    "IN": (24.1, 820.0, 880.0),
    "US": (17.5, 1250.0, 150.0),
    "EU": (17.8, 550.0, 120.0),
}
_DEMO_PLACE = {
    "IN": ("Demo location, Karnataka, India", "Karnataka", "Bengaluru Rural"),
    "US": ("Demo location, Georgia, United States", "Georgia", "Bibb County"),
    "EU": ("Demo location, Andalucía, Spain", "Andalucía", "Sevilla"),
}
_FALLBACK_HINTS = [
    RegionHint(
        "IN", (68.1, 6.5, 97.4, 35.7), "tropical_dry", _DEMO_CLIMATE["IN"], _DEMO_PLACE["IN"]
    ),
    RegionHint(
        "US",
        (-125.0, 24.4, -66.9, 49.4),
        "warm_temperate_moist",
        _DEMO_CLIMATE["US"],
        _DEMO_PLACE["US"],
    ),
    RegionHint(
        "EU",
        (-10.5, 34.5, 31.6, 71.2),
        "cool_temperate_moist",
        _DEMO_CLIMATE["EU"],
        _DEMO_PLACE["EU"],
    ),
]


def _find_regions_dir() -> Path | None:
    env = os.environ.get("ATLAS_CONFIG_DIR")
    if env and (Path(env) / "regions").is_dir():
        return Path(env) / "regions"
    for base in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in [base, *base.parents]:
            probe = parent / "config" / "regions"
            if probe.is_dir():
                return probe
    return None


def load_region_hints() -> list[RegionHint]:
    """Region bboxes/zone defaults from config, falling back to the built-in copies."""
    regions_dir = _find_regions_dir()
    if regions_dir is None:
        return list(_FALLBACK_HINTS)
    hints: list[RegionHint] = []
    for path in sorted(regions_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        region_id = str(data.get("id"))
        bbox = data.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        hints.append(
            RegionHint(
                id=region_id,
                bbox=tuple(float(v) for v in bbox),  # type: ignore[arg-type]
                default_zone=str((data.get("climate") or {}).get("default_zone", "tropical_dry")),
                demo_climate=_DEMO_CLIMATE.get(region_id, (15.0, 800.0, 200.0)),
                demo_place=_DEMO_PLACE.get(region_id, (f"Demo location, {region_id}", "", "")),
            )
        )
    return hints or list(_FALLBACK_HINTS)


def region_for(lat: float, lon: float, hints: list[RegionHint] | None = None) -> RegionHint | None:
    """First region whose bbox contains the point (IN is checked before US/EU)."""
    for hint in hints or load_region_hints():
        min_lon, min_lat, max_lon, max_lat = hint.bbox
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            return hint
    return None


def seed_from(*parts: object) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def unit_noise(*parts: object) -> float:
    """Deterministic pseudo-random number in [0, 1) from the parts."""
    return (seed_from(*parts) % 10_000) / 10_000.0
