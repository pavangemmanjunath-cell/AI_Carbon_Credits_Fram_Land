"""Parameter store: loads every YAML the models need and exposes each value
together with its ``source`` and ``verification_status``.

Files (all under ``config/``, found via ``ATLAS_CONFIG_DIR`` or by walking up
from this package to the repository root):

* ``methodologies/ipcc-2006-tier1.yaml`` — constants, root-to-shoot ratios,
  Tier 1 above-ground growth, allometry registry, behaviour assumptions.
* ``methodologies/tree-biomass-model.yaml`` — model-behaviour settings.
* ``methodologies/registry.yaml`` — methodology registry (names, references).
* ``species/species.yaml`` — species table.
* ``readiness.yaml`` — evidence weights.

Nothing numeric is defined in Python; a missing YAML key is a hard error so
silent defaults cannot creep in.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from carbon_engine.errors import (
    PendingParameterError,
    UnknownClimateZoneError,
    UnknownSpeciesError,
)
from carbon_engine.types import ParameterUsed

VERIFICATION_ORDER = {"verified": 0, "assumption": 1, "pending": 2}


def find_config_dir(start: Path | None = None) -> Path:
    """Locate the repository ``config/`` directory.

    Order: ``ATLAS_CONFIG_DIR`` env var → walk up from ``start`` (default: this
    file) looking for ``config/species/species.yaml`` → walk up from CWD.
    """
    env = os.environ.get("ATLAS_CONFIG_DIR")
    if env:
        path = Path(env).expanduser().resolve()
        if path.is_dir():
            return path
    candidates = [start or Path(__file__).resolve(), Path.cwd().resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            probe = parent / "config" / "species" / "species.yaml"
            if probe.is_file():
                return probe.parent.parent
    raise FileNotFoundError(
        "could not locate the CarbonCreditBuy config/ directory; set ATLAS_CONFIG_DIR"
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def _cited(
    entry: Mapping[str, Any], name: str, unit: str, *, source_suffix: str = ""
) -> ParameterUsed:
    """Turn a ``{value, source, verification_status[, unit]}`` mapping into ParameterUsed."""
    missing = [k for k in ("value", "source", "verification_status") if k not in entry]
    if missing:
        raise KeyError(f"parameter {name!r} is missing {missing} in its YAML entry")
    source = str(entry["source"]) + (f" {source_suffix}" if source_suffix else "")
    return ParameterUsed(
        name=name,
        value=entry["value"],
        unit=str(entry.get("unit", unit)),
        source=source,
        verification_status=str(entry["verification_status"]),
    )


_RANGE_KEY = re.compile(r"^agb_(?:(lt|ge|gt)_(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)_(\d+(?:\.\d+)?))$")


def _class_matches(key: str, agb_t_ha: float) -> bool:
    """Interpret Table 4.4 class keys: default, agb_lt_N, agb_ge_N, agb_gt_N, agb_A_B."""
    if key == "default":
        return True
    match = _RANGE_KEY.match(key)
    if not match:
        raise ValueError(f"unrecognised root-to-shoot class key {key!r}")
    op, bound, lower, upper = match.groups()
    if op == "lt":
        return agb_t_ha < float(bound)
    if op == "ge":
        return agb_t_ha >= float(bound)
    if op == "gt":
        return agb_t_ha > float(bound)
    return float(lower) <= agb_t_ha <= float(upper)


class ParameterStore:
    """Read-only access to all model parameters with citations."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = (config_dir or find_config_dir()).resolve()
        self.tier1 = _load_yaml(self.config_dir / "methodologies" / "ipcc-2006-tier1.yaml")
        self.model_config = _load_yaml(
            self.config_dir / "methodologies" / "tree-biomass-model.yaml"
        )
        self.registry = _load_yaml(self.config_dir / "methodologies" / "registry.yaml")
        self.species_table = _load_yaml(self.config_dir / "species" / "species.yaml")
        self.readiness_config = _load_yaml(self.config_dir / "readiness.yaml")
        self._species: dict[str, dict[str, Any]] = {
            str(s["id"]): s for s in self.species_table.get("species", [])
        }

    # ---- species -----------------------------------------------------------
    @property
    def species_version(self) -> str:
        return str(self.species_table.get("version", "0"))

    def species(self, species_id: str) -> dict[str, Any]:
        try:
            return self._species[species_id]
        except KeyError as exc:
            raise UnknownSpeciesError(species_id) from exc

    def species_list(self, country: str | None = None) -> list[dict[str, Any]]:
        items = list(self._species.values())
        if country:
            items = [s for s in items if country in s.get("regions", [])]
        return items

    def species_param(self, species_id: str, key: str, unit: str) -> ParameterUsed:
        species = self.species(species_id)
        entry = species[key]
        if isinstance(entry, Mapping):
            return _cited(entry, key, unit, source_suffix=f"[species: {species_id}]")
        # Bare scalar in the species table: by convention a project assumption.
        return ParameterUsed(
            name=key,
            value=entry,
            unit=unit,
            source=f"config/species/species.yaml v{self.species_version} [species: {species_id}]",
            verification_status="assumption",
        )

    # ---- IPCC tier 1 tables -------------------------------------------------
    @property
    def parameter_set_id(self) -> str:
        return str(self.tier1["id"])

    @property
    def parameter_set_version(self) -> str:
        return str(self.tier1["version"])

    def climate_zones(self) -> list[str]:
        return list(self.tier1["above_ground_biomass_growth"]["by_climate_zone"].keys())

    def growth(self, zone: str) -> ParameterUsed:
        table = self.tier1["above_ground_biomass_growth"]
        try:
            entry = table["by_climate_zone"][zone]
        except KeyError as exc:
            raise UnknownClimateZoneError(zone) from exc
        return ParameterUsed(
            name="above_ground_biomass_growth",
            value=float(entry["value"]),
            unit=str(table["unit"]),
            source=f"{table['source']} [zone: {zone}; age class: {table.get('age_class', 'n/a')}]",
            verification_status=str(table["verification_status"]),
        )

    def growth_range(self, zone: str) -> tuple[float, float] | None:
        entry = self.tier1["above_ground_biomass_growth"]["by_climate_zone"].get(zone, {})
        rng = entry.get("range")
        return (float(rng[0]), float(rng[1])) if rng else None

    def root_to_shoot(self, zone: str, agb_t_ha: float) -> ParameterUsed:
        table = self.tier1["root_to_shoot"]
        try:
            classes = table["by_climate_zone"][zone]
        except KeyError as exc:
            raise UnknownClimateZoneError(zone) from exc
        for key, value in classes.items():
            if _class_matches(str(key), agb_t_ha):
                return ParameterUsed(
                    name="root_to_shoot_ratio",
                    value=float(value),
                    unit=str(table["unit"]),
                    source=f"{table['source']} [zone: {zone}; class: {key}]",
                    verification_status=str(table["verification_status"]),
                )
        raise ValueError(f"no root-to-shoot class matched zone={zone} agb={agb_t_ha}")

    def constant(self, name: str) -> ParameterUsed:
        entry = self.tier1["constants"][name]
        return _cited(entry, name, str(entry.get("unit", "")))

    def assumption(self, name: str) -> dict[str, Any]:
        return dict(self.tier1["assumptions"][name])

    def assumption_param(self, name: str, unit: str = "") -> ParameterUsed:
        return _cited(self.assumption(name), name, unit)

    def uncertainty_fraction(self, tier: int) -> tuple[ParameterUsed, ParameterUsed]:
        entry = self.assumption(f"uncertainty_fraction_tier{tier}")
        low = ParameterUsed(
            f"uncertainty_fraction_tier{tier}_low",
            float(entry["low"]),
            "fraction of central",
            str(entry["source"]),
            str(entry["verification_status"]),
        )
        high = ParameterUsed(
            f"uncertainty_fraction_tier{tier}_high",
            float(entry["high"]),
            "fraction of central",
            str(entry["source"]),
            str(entry["verification_status"]),
        )
        return low, high

    def density_clamp(self) -> tuple[float, float, ParameterUsed]:
        entry = self.assumption("density_scaling")
        lo, hi = entry["clamp"]
        param = ParameterUsed(
            "density_scaling_clamp",
            [float(lo), float(hi)],
            "ratio to reference density",
            str(entry["source"]),
            str(entry["verification_status"]),
        )
        return float(lo), float(hi), param

    def allometry(self, key: str) -> dict[str, Any]:
        return dict(self.tier1["allometry"][key])

    def references(self) -> list[dict[str, str]]:
        return [dict(r) for r in self.tier1.get("references", [])]

    # ---- model behaviour -------------------------------------------------------
    @property
    def model_id(self) -> str:
        return str(self.model_config["id"])

    @property
    def model_version(self) -> str:
        return str(self.model_config["version"])

    def model_setting(self, name: str, unit: str = "") -> ParameterUsed:
        return _cited(self.model_config["settings"][name], name, unit)

    def methodology_entry(self, methodology_id: str) -> dict[str, Any]:
        for entry in self.registry.get("methodologies", []):
            if entry.get("id") == methodology_id:
                return dict(entry)
        raise KeyError(methodology_id)

    # ---- quality -----------------------------------------------------------------
    def all_cited_parameters(self) -> list[ParameterUsed]:
        """Every cited parameter in the configuration (for data-quality tests)."""
        found: list[ParameterUsed] = []
        for zone in self.climate_zones():
            found.append(self.growth(zone))
        for zone in self.tier1["root_to_shoot"]["by_climate_zone"]:
            found.append(self.root_to_shoot(zone, 0.0))
        for name in self.tier1["constants"]:
            found.append(self.constant(name))
        for name in self.tier1["assumptions"]:
            entry = self.assumption(name)
            found.append(
                ParameterUsed(
                    name,
                    entry.get("value", entry.get("clamp", entry.get("low"))),
                    str(entry.get("unit", "")),
                    str(entry["source"]),
                    str(entry["verification_status"]),
                )
            )
        for key, entry in self.tier1["allometry"].items():
            found.append(
                ParameterUsed(
                    f"allometry:{key}",
                    entry.get("equation"),
                    "equation",
                    str(entry["source"]),
                    str(entry["verification_status"]),
                )
            )
        for species_id, species in self._species.items():
            for key, entry in species.items():
                if isinstance(entry, Mapping) and "verification_status" in entry:
                    found.append(_cited(entry, f"{species_id}.{key}", ""))
        return found


def worst_verification_status(parameters: Iterable[ParameterUsed]) -> str:
    """``pending`` > ``assumption`` > ``verified`` (the weakest status wins)."""
    worst = "verified"
    for param in parameters:
        status = param.verification_status
        if VERIFICATION_ORDER.get(status, 2) > VERIFICATION_ORDER[worst]:
            worst = status if status in VERIFICATION_ORDER else "pending"
    return worst


def assert_production_safe(parameters: Iterable[ParameterUsed], allow_pending: bool) -> None:
    """Raise :class:`PendingParameterError` when a used parameter is ``pending``
    and pending parameters are not allowed (``ATLAS_ALLOW_PENDING_PARAMETERS=false``)."""
    if allow_pending:
        return
    pending = sorted({p.name for p in parameters if p.verification_status == "pending"})
    if pending:
        raise PendingParameterError(pending)


@lru_cache(maxsize=4)
def get_store(config_dir: str | None = None) -> ParameterStore:
    """Process-wide cached store (config files are read once)."""
    return ParameterStore(Path(config_dir) if config_dir else None)
