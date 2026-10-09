"""Region, species, methodology, market and attribution configuration access."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

EU_MEMBER_FALLBACK = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
}


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


class RegionConfig:
    """Loads ``config/regions/*.yaml`` and ``config/market/*.yaml`` once."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.regions: dict[str, dict[str, Any]] = {}
        self.member_map: dict[str, str] = {}
        for path in sorted((config_dir / "regions").glob("*.yaml")):
            data = _load(path)
            region_id = str(data["id"]).upper()
            self.regions[region_id] = data
            for member in data.get("member_states", []) or []:
                self.member_map[str(member).upper()] = region_id
            for code in (data.get("calling_code_aliases") or {}).values():
                self.member_map.setdefault(str(code).upper(), region_id)
        if "EU" in self.regions:
            for member in EU_MEMBER_FALLBACK:
                self.member_map.setdefault(member, "EU")
        self.market = _load(config_dir / "market" / "carbon-price-scenarios.yaml")
        self.registry = _load(config_dir / "methodologies" / "registry.yaml")

    # -- lookups ----------------------------------------------------------------
    def resolve(self, country: str | None) -> str | None:
        if not country:
            return None
        code = country.upper()
        if code in self.regions:
            return code
        return self.member_map.get(code)

    def region(self, region_id: str) -> dict[str, Any]:
        return self.regions[region_id]

    def region_for_point(self, lat: float, lon: float) -> str | None:
        for region_id, data in self.regions.items():
            bbox = data.get("bbox")
            if bbox and bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                return region_id
        return None

    def default_zone(self, region_id: str) -> str:
        return str(self.region(region_id).get("climate", {}).get("default_zone", "tropical_dry"))

    def public_region(self, region_id: str) -> dict[str, Any]:
        data = self.region(region_id)
        return {
            "id": region_id,
            "name": data.get("name"),
            "calling_code": data.get("calling_code"),
            "currency": data.get("currency"),
            "currency_symbol": data.get("currency_symbol"),
            "units": data.get("units", {}),
            "languages": data.get("languages", []),
            "default_center": data.get("default_center"),
            "default_zoom": data.get("default_zoom"),
            "bbox": data.get("bbox"),
            "member_states": data.get("member_states", []),
            "programmes": [
                {k: p.get(k) for k in ("id", "name", "authority", "kind", "url")}
                for p in data.get("programmes", [])
            ],
            "other_income_sources": data.get("other_income_sources", []),
            "climate_default_zone": self.default_zone(region_id),
        }

    def public_regions(self) -> list[dict[str, Any]]:
        return [self.public_region(rid) for rid in self.regions]

    def market_scenarios(self, region_id: str) -> dict[str, Any]:
        scenarios = self.market.get("scenarios", {})
        return scenarios.get(region_id) or next(iter(scenarios.values()))

    def market_basis(self) -> dict[str, Any]:
        return {
            "source": "config/market/carbon-price-scenarios.yaml",
            "as_of": str(self.market.get("as_of", "")),
            "note": str(self.market.get("basis_note", "")).strip(),
            "references": self.market.get("references", []),
            "version": self.market.get("version"),
        }

    def methodologies(self) -> list[dict[str, Any]]:
        return list(self.registry.get("methodologies", []))

    def other_income(self, region_id: str, currency: str) -> list[dict[str, Any]]:
        items = []
        for entry in self.region(region_id).get("other_income_sources", []):
            items.append(
                {
                    "id": entry.get("id"),
                    "label": entry.get("label"),
                    "value": None,
                    "unit": f"{currency}/yr",
                    "source": entry.get("source"),
                }
            )
        return items


ATTRIBUTION_ITEMS = [
    {
        "id": "osm",
        "text": "© OpenStreetMap contributors",
        "url": "https://www.openstreetmap.org/copyright",
        "license": "ODbL",
    },
    {
        "id": "esa-worldcover",
        "text": "ESA WorldCover 2021 v200 © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium",
        "url": "https://esa-worldcover.org/",
        "license": "CC BY 4.0",
    },
    {
        "id": "copernicus-sentinel-2",
        "text": "Contains modified Copernicus Sentinel data",
        "url": "https://dataspace.copernicus.eu/",
        "license": "Copernicus data licence (free, full and open)",
    },
    {
        "id": "open-meteo",
        "text": "Weather and climate data by Open-Meteo.com",
        "url": "https://open-meteo.com/",
        "license": "CC BY 4.0",
    },
    {
        "id": "soilgrids",
        "text": "SoilGrids © ISRIC — World Soil Information",
        "url": "https://soilgrids.org/",
        "license": "CC BY 4.0",
    },
    {
        "id": "maplibre",
        "text": "MapLibre GL JS",
        "url": "https://maplibre.org/",
        "license": "BSD-3-Clause",
    },
    {
        "id": "usda-nass",
        "text": "USDA National Agricultural Statistics Service, Quick Stats",
        "url": "https://quickstats.nass.usda.gov/",
        "license": "US public data (acknowledge source)",
    },
    {
        "id": "data-gov-in",
        "text": "Open Government Data (OGD) Platform India, Ministry of Agriculture & Farmers Welfare",
        "url": "https://data.gov.in/",
        "license": "Government Open Data License – India (GODL)",
    },
]


@lru_cache(maxsize=4)
def get_region_config(config_dir: str) -> RegionConfig:
    return RegionConfig(Path(config_dir))
