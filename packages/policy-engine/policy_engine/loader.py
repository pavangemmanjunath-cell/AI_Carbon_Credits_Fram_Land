"""Load policy and region YAML files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def find_config_dir(start: Path | None = None) -> Path:
    """Locate ``config/`` (``ATLAS_CONFIG_DIR`` or walk up from this file / CWD)."""
    env = os.environ.get("ATLAS_CONFIG_DIR")
    if env:
        path = Path(env).expanduser().resolve()
        if path.is_dir():
            return path
    for base in (start or Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in [base, *base.parents]:
            probe = parent / "config" / "policies"
            if probe.is_dir() and (parent / "config" / "regions").is_dir():
                return parent / "config"
    raise FileNotFoundError("could not locate config/; set ATLAS_CONFIG_DIR")


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


@dataclass(frozen=True)
class PolicyConfig:
    country: str
    disclaimer: str
    programmes: list[dict[str, Any]]
    path: Path


@dataclass(frozen=True)
class RegionIndex:
    """Region configs keyed by id plus the member-state → region map."""

    regions: dict[str, dict[str, Any]]
    member_map: dict[str, str] = field(default_factory=dict)

    def resolve(self, country_code: str | None) -> str | None:
        """Map an ISO 3166-1 alpha-2 code to a region id (``DE`` → ``EU``)."""
        if not country_code:
            return None
        code = country_code.upper()
        if code in self.regions:
            return code
        return self.member_map.get(code)

    def region(self, region_id: str) -> dict[str, Any]:
        return self.regions[region_id]


def load_regions(config_dir: Path | None = None) -> RegionIndex:
    config_dir = config_dir or find_config_dir()
    regions: dict[str, dict[str, Any]] = {}
    member_map: dict[str, str] = {}
    for path in sorted((config_dir / "regions").glob("*.yaml")):
        data = _load_yaml(path)
        region_id = str(data["id"])
        regions[region_id] = data
        for member in data.get("member_states", []) or []:
            member_map[str(member).upper()] = region_id
    return RegionIndex(regions=regions, member_map=member_map)


def load_policy(region_id: str, config_dir: Path | None = None) -> PolicyConfig:
    config_dir = config_dir or find_config_dir()
    path = config_dir / "policies" / f"{region_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no policy file for region {region_id!r} at {path}")
    data = _load_yaml(path)
    return PolicyConfig(
        country=str(data["country"]),
        disclaimer=str(data["disclaimer"]),
        programmes=list(data.get("programmes", [])),
        path=path,
    )
