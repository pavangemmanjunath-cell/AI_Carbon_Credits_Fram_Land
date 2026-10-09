"""Loader for ``config/detection.yaml`` (point clouds, satellite tree cover, vector imports).

Every tunable number lives in the YAML as ``{value, unit, source, verification_status}``;
nothing numeric is hidden in Python. A missing key is a hard error so silent defaults cannot
creep in. The file is located through ``ATLAS_CONFIG_DIR`` or by walking up from this package
and from the current directory to the repository ``config/`` folder.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from geo_engine.errors import GeoEngineError

ALLOWED_STATUS = ("verified", "pending", "assumption")
CONFIG_FILE = "detection.yaml"


class ConfigError(GeoEngineError):
    """``config/detection.yaml`` is missing or malformed."""


@dataclass(frozen=True)
class ConfigParameter:
    """One cited parameter."""

    name: str
    value: Any
    unit: str
    source: str
    verification_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "verification_status": self.verification_status,
        }


@dataclass(frozen=True)
class DetectionConfig:
    """Parsed ``detection.yaml``."""

    path: Path
    version: str
    updated: str
    sections: dict[str, dict[str, ConfigParameter]]

    def section(self, name: str) -> dict[str, ConfigParameter]:
        try:
            return self.sections[name]
        except KeyError as exc:
            raise ConfigError(f"{self.path} has no section {name!r}") from exc

    def parameter(self, section: str, name: str) -> ConfigParameter:
        try:
            return self.section(section)[name]
        except KeyError as exc:
            raise ConfigError(
                f"{self.path}: section {section!r} has no parameter {name!r}"
            ) from exc

    def value(self, section: str, name: str) -> Any:
        return self.parameter(section, name).value

    def parameters(self, section: str) -> list[ConfigParameter]:
        return list(self.section(section).values())

    def weakest_status(self, section: str) -> str:
        """The least-verified status in a section (pending < assumption < verified)."""
        order = {"verified": 0, "assumption": 1, "pending": 2}
        statuses = [p.verification_status for p in self.section(section).values()]
        return max(statuses, key=lambda s: order[s]) if statuses else "verified"


def find_config_file(config_dir: Path | str | None = None) -> Path:
    """Locate ``detection.yaml`` (explicit directory, ``ATLAS_CONFIG_DIR``, then walking up)."""
    candidates: list[Path] = []
    if config_dir is not None:
        candidates.append(Path(config_dir).expanduser())
    env = os.environ.get("ATLAS_CONFIG_DIR")
    if env:
        candidates.append(Path(env).expanduser())
    for base in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in [base, *base.parents]:
            candidates.append(parent / "config")
    for directory in candidates:
        probe = directory / CONFIG_FILE
        if probe.is_file():
            return probe.resolve()
    raise ConfigError(
        f"could not locate config/{CONFIG_FILE}; set ATLAS_CONFIG_DIR to the config directory"
    )


def _parse_parameter(section: str, name: str, entry: Any) -> ConfigParameter:
    if not isinstance(entry, dict):
        raise ConfigError(
            f"{section}.{name} must be a mapping with value/source/verification_status"
        )
    missing = [k for k in ("value", "source", "verification_status") if k not in entry]
    if missing:
        raise ConfigError(f"{section}.{name} is missing {missing}")
    status = str(entry["verification_status"])
    if status not in ALLOWED_STATUS:
        raise ConfigError(
            f"{section}.{name}: verification_status {status!r} is not one of {ALLOWED_STATUS}"
        )
    return ConfigParameter(
        name=name,
        value=entry["value"],
        unit=str(entry.get("unit", "")),
        source=str(entry["source"]),
        verification_status=status,
    )


@lru_cache(maxsize=8)
def _load(path_text: str) -> DetectionConfig:
    path = Path(path_text)
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a mapping")
    sections: dict[str, dict[str, ConfigParameter]] = {}
    for section, body in raw.items():
        if section in ("version", "updated") or not isinstance(body, dict):
            continue
        sections[section] = {
            str(name): _parse_parameter(section, str(name), entry) for name, entry in body.items()
        }
    return DetectionConfig(
        path=path,
        version=str(raw.get("version", "0")),
        updated=str(raw.get("updated", "")),
        sections=sections,
    )


def load_detection_config(config_dir: Path | str | None = None) -> DetectionConfig:
    """Load (and cache) ``detection.yaml``."""
    return _load(str(find_config_file(config_dir)))
