"""Rule evaluation.

A programme in ``config/policies/<region>.yaml`` has ordered ``rules``::

    rules:
      - when: {activity: tree_plantation}                 # string or list
        status: requires_assessment
        reason: "..."
      - when: {activity: [agroforestry], land_type: cropland, min_area: 1.0}
        status: potentially_applicable
        reason: "..."
      - default: not_applicable

Matching: ``activity`` must equal (or be contained in) ``when.activity``;
``land_type`` (string or list) and ``min_area`` (hectares, inclusive) are
optional extra conditions. **The first matching rule wins**; if none match,
the ``default`` rule applies; if there is no default the status is
``unknown``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from policy_engine.loader import PolicyConfig, RegionIndex, load_policy, load_regions

ACTIVITIES = (
    "tree_plantation",
    "agroforestry",
    "soil_carbon",
    "cropland_practice",
    "grazing",
)
STATUSES = (
    "potentially_applicable",
    "requires_assessment",
    "requires_methodology_assessment",
    "requires_certification",
    "not_applicable",
    "unknown",
)


@dataclass(frozen=True)
class ProgrammeScreening:
    id: str
    name: str
    authority: str
    kind: str
    status: str
    requirements: list[str]
    notes: list[str]
    references: list[dict[str, str]]
    distinct_from: list[str] = field(default_factory=list)
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "authority": self.authority,
            "kind": self.kind,
            "status": self.status,
            "requirements": list(self.requirements),
            "notes": list(self.notes),
            "references": [dict(r) for r in self.references],
            "distinct_from": list(self.distinct_from),
        }


@dataclass(frozen=True)
class Screening:
    country: str
    region: str
    activity: str
    disclaimer: str
    programmes: list[ProgrammeScreening]

    def to_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "activity": self.activity,
            "disclaimer": self.disclaimer,
            "programmes": [p.to_dict() for p in self.programmes],
        }

    def summary(self) -> str:
        """``"Green Credit Programme · CCTS (separate mechanisms)"``-style one-liner."""
        names = [_short_name(p.name) for p in self.programmes if p.status != "not_applicable"]
        text = " · ".join(names) if names else "No programme screened as applicable"
        if any(p.distinct_from for p in self.programmes if p.status != "not_applicable"):
            text += " (separate mechanisms)"
        return text


def _short_name(name: str) -> str:
    """Trim parenthetical qualifiers and keep well-known abbreviations."""
    base = name.split(" (")[0].strip()
    if "Carbon Credit Trading Scheme" in base:
        return "CCTS"
    if "Carbon Removals and Carbon Farming" in base:
        return "CRCF"
    return base


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def rule_matches(
    when: Mapping[str, Any], activity: str, land_type: str | None, area_ha: float | None
) -> bool:
    activities = _as_list(when.get("activity"))
    if activities and activity not in activities:
        return False
    land_types = _as_list(when.get("land_type"))
    if land_types and (land_type is None or land_type not in land_types):
        return False
    min_area = when.get("min_area")
    if min_area is not None and (area_ha is None or float(area_ha) < float(min_area)):
        return False
    max_area = when.get("max_area")
    if max_area is not None and (area_ha is None or float(area_ha) > float(max_area)):
        return False
    return True


def evaluate_rules(
    rules: list[Mapping[str, Any]], activity: str, land_type: str | None, area_ha: float | None
) -> tuple[str, str | None]:
    """Return ``(status, reason)`` for the first matching rule (or default/unknown)."""
    default_status: str | None = None
    for rule in rules:
        if "default" in rule:
            default_status = str(rule["default"])
            continue
        when = rule.get("when") or {}
        if rule_matches(when, activity, land_type, area_ha):
            return str(rule["status"]), (str(rule["reason"]) if rule.get("reason") else None)
    return default_status or "unknown", None


class PolicyEngine:
    """Evaluate screening rules for IN / US / EU (+ EU member states)."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir
        self.regions: RegionIndex = load_regions(config_dir)
        self._policies: dict[str, PolicyConfig] = {}

    def resolve_region(self, country: str) -> str:
        region = self.regions.resolve(country)
        if region is None:
            raise KeyError(f"no policy rules for country {country!r}")
        return region

    def policy(self, region_id: str) -> PolicyConfig:
        if region_id not in self._policies:
            self._policies[region_id] = load_policy(region_id, self.config_dir)
        return self._policies[region_id]

    def programme_url(self, region_id: str, programme_id: str) -> str | None:
        """URL from the region config's programme list, else the first reference URL."""
        for programme in self.regions.region(region_id).get("programmes", []):
            if programme.get("id") == programme_id and programme.get("url"):
                return str(programme["url"])
        for programme in self.policy(region_id).programmes:
            if programme.get("id") == programme_id:
                for ref in programme.get("references", []):
                    if ref.get("url"):
                        return str(ref["url"])
        return None

    def screen(
        self,
        country: str,
        activity: str,
        land_type: str | None = None,
        area_ha: float | None = None,
    ) -> Screening:
        if activity not in ACTIVITIES:
            raise ValueError(f"unknown activity {activity!r}; expected one of {ACTIVITIES}")
        region_id = self.resolve_region(country)
        policy = self.policy(region_id)
        programmes: list[ProgrammeScreening] = []
        for programme in policy.programmes:
            status, reason = evaluate_rules(
                programme.get("rules", []), activity, land_type, area_ha
            )
            notes: list[str] = [reason] if reason else []
            distinct = _as_list(programme.get("distinct_from"))
            if distinct and status != "not_applicable":
                names = [self._programme_name(policy, d) for d in distinct]
                notes.append(
                    f"{_short_name(str(programme['name']))} is a separate mechanism from "
                    + ", ".join(names)
                    + "."
                )
            programmes.append(
                ProgrammeScreening(
                    id=str(programme["id"]),
                    name=str(programme["name"]),
                    authority=str(programme.get("authority", "")),
                    kind=str(programme.get("kind", "")),
                    status=status,
                    requirements=[str(r) for r in programme.get("requirements", [])],
                    notes=notes,
                    references=[
                        {"title": str(r.get("title", "")), "url": str(r.get("url", ""))}
                        for r in programme.get("references", [])
                    ],
                    distinct_from=distinct,
                    url=self.programme_url(region_id, str(programme["id"])),
                )
            )
        return Screening(
            country=country.upper(),
            region=region_id,
            activity=activity,
            disclaimer=policy.disclaimer,
            programmes=programmes,
        )

    @staticmethod
    def _programme_name(policy: PolicyConfig, programme_id: str) -> str:
        for programme in policy.programmes:
            if programme.get("id") == programme_id:
                return _short_name(str(programme["name"]))
        return programme_id


@lru_cache(maxsize=2)
def get_engine(config_dir: str | None = None) -> PolicyEngine:
    return PolicyEngine(Path(config_dir) if config_dir else None)
