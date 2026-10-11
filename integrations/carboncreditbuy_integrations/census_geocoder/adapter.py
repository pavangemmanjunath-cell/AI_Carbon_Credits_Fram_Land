"""US Census Bureau Geocoder — coordinates → state / county FIPS.

``CENSUS_GEOCODER_URL`` (https://geocoding.geo.census.gov/geocoder/geographies/coordinates)
with ``x=lon&y=lat&benchmark=Public_AR_Current&vintage=Current_Current&format=json``.
No key; public domain (US Government work). Fair use: single-point lookups
only (the batch endpoint exists for bulk).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from carboncreditbuy_integrations.base import (
    Cache,
    HttpAdapter,
    NotFoundError,
    SourceProvenance,
    UpstreamDataError,
    demo_source,
)
from carboncreditbuy_integrations.demo_support import region_for

SOURCE = SourceProvenance(
    id="census-geocoder",
    name="US Census Bureau Geocoder (geographies by coordinates)",
    version="Public_AR_Current / Current_Current",
    license="Public domain (US Government work)",
    attribution="U.S. Census Bureau Geocoding Services",
    url="https://geocoding.geo.census.gov/",
)


@dataclass(frozen=True)
class CountyLookup:
    state_fips: str
    county_fips: str
    state_name: str | None
    state_abbr: str | None
    county_name: str | None
    source: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_fips": self.state_fips,
            "county_fips": self.county_fips,
            "state_name": self.state_name,
            "state_abbr": self.state_abbr,
            "county_name": self.county_name,
        }


class CensusGeocoderAdapter(HttpAdapter):
    def __init__(self, url: str, cache: Cache | None = None, **kwargs: Any) -> None:
        super().__init__(cache=cache, cache_ttl_s=30 * 86_400.0, **kwargs)
        self.url = url

    def lookup(self, lat: float, lon: float) -> CountyLookup:
        params = {
            "x": lon,
            "y": lat,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "format": "json",
            "layers": "Counties,States",
        }
        data = self.get_json(self.url, params=params)
        try:
            geographies = data["result"]["geographies"]
            counties = geographies.get("Counties") or []
            states = geographies.get("States") or []
        except (KeyError, TypeError) as exc:
            raise UpstreamDataError("Census geocoder payload malformed") from exc
        if not counties:
            raise NotFoundError("Census geocoder: point is outside US counties")
        county = counties[0]
        state = states[0] if states else {}
        return CountyLookup(
            state_fips=str(county.get("STATE", "")).zfill(2),
            county_fips=str(county.get("COUNTY", "")).zfill(3),
            state_name=state.get("NAME"),
            state_abbr=state.get("STUSAB"),
            county_name=county.get("NAME") or county.get("BASENAME"),
            source=SOURCE.to_dict(datetime.now(UTC)),
        )

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()


class DemoCensusGeocoderAdapter:
    def lookup(self, lat: float, lon: float) -> CountyLookup:
        hint = region_for(lat, lon)
        if hint is None or hint.id != "US":
            raise NotFoundError("demo census geocoder: point is outside the US bbox")
        return CountyLookup(
            "13",
            "021",
            "Georgia",
            "GA",
            "Bibb County",
            demo_source(SOURCE).to_dict(datetime.now(UTC)),
        )

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
