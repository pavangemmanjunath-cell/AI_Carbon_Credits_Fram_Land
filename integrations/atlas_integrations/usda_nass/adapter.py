"""USDA NASS Quick Stats adapter (county crop statistics).

* ``USDA_NASS_API_URL`` (https://quickstats.nass.usda.gov/api/api_GET/) with a
  free key ``USDA_NASS_API_KEY`` (https://quickstats.nass.usda.gov/api).
* Query: ``source_desc=SURVEY``, ``sector_desc=CROPS``, ``agg_level_desc=COUNTY``,
  ``commodity_desc``, ``state_fips_code``, ``county_code``, ``year__GE``.
  Responses are capped at 50 000 records; errors come back as HTTP 400/413.
* Public domain (US Government work); cite "USDA National Agricultural
  Statistics Service, Quick Stats". Rate limits are not published — be polite
  and cache (24 h here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from atlas_integrations.base import (
    Cache,
    ConfigurationError,
    HttpAdapter,
    SourceProvenance,
    UpstreamDataError,
    demo_source,
)
from atlas_integrations.demo_support import unit_noise

SOURCE = SourceProvenance(
    id="usda-nass-quickstats",
    name="USDA NASS Quick Stats",
    version=None,
    license="Public domain (US Government work)",
    attribution="USDA National Agricultural Statistics Service, Quick Stats database",
    url="https://quickstats.nass.usda.gov/",
)


@dataclass(frozen=True)
class StatRecord:
    year: int
    commodity: str
    statistic: str  # e.g. PRODUCTION / YIELD / AREA HARVESTED
    value: float | None
    unit: str
    state: str | None = None
    county: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "commodity": self.commodity,
            "statistic": self.statistic,
            "value": self.value,
            "unit": self.unit,
            "state": self.state,
            "county": self.county,
        }


def _to_number(raw: Any) -> float | None:
    text = str(raw).replace(",", "").strip()
    if not text or text.startswith("("):  # "(D)" withheld, "(Z)" rounds to zero
        return None
    try:
        return float(text)
    except ValueError:
        return None


class UsdaNassAdapter(HttpAdapter):
    def __init__(
        self, api_url: str, api_key: str, cache: Cache | None = None, **kwargs: Any
    ) -> None:
        if not api_key:
            raise ConfigurationError("USDA_NASS_API_KEY is required for Quick Stats")
        super().__init__(cache=cache, cache_ttl_s=86_400.0, **kwargs)
        self.api_url = api_url
        self.api_key = api_key

    def fetch_county_statistics(
        self,
        state_fips: str,
        county_code: str,
        commodity: str,
        years: list[int],
        statistic: str | None = None,
    ) -> list[StatRecord]:
        params: dict[str, Any] = {
            "key": self.api_key,
            "source_desc": "SURVEY",
            "sector_desc": "CROPS",
            "agg_level_desc": "COUNTY",
            "commodity_desc": commodity.upper(),
            "state_fips_code": str(state_fips).zfill(2),
            "county_code": str(county_code).zfill(3),
            "year__GE": min(years),
            "year__LE": max(years),
            "format": "JSON",
        }
        if statistic:
            params["statisticcat_desc"] = statistic.upper()
        data = self.get_json(self.api_url, params=params)
        if "data" not in data:
            raise UpstreamDataError("Quick Stats payload has no 'data' key")
        records = [
            StatRecord(
                year=int(row.get("year", 0)),
                commodity=str(row.get("commodity_desc", commodity)),
                statistic=str(row.get("statisticcat_desc", "")),
                value=_to_number(row.get("Value")),
                unit=str(row.get("unit_desc", "")),
                state=row.get("state_name"),
                county=row.get("county_name"),
            )
            for row in data["data"]
        ]
        records.sort(key=lambda r: (r.year, r.statistic))
        return records

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict(datetime.now(UTC))


class DemoUsdaNassAdapter:
    def fetch_county_statistics(
        self,
        state_fips: str,
        county_code: str,
        commodity: str,
        years: list[int],
        statistic: str | None = None,
    ) -> list[StatRecord]:
        base = 1_200_000.0 if commodity.upper() == "PECANS" else 50_000.0
        out = []
        for year in sorted(years):
            value = base * (
                0.8 + 0.4 * unit_noise("nass", state_fips, county_code, commodity, year)
            )
            out.append(
                StatRecord(
                    year,
                    commodity.upper(),
                    statistic or "PRODUCTION",
                    round(value),
                    "LB" if commodity.upper() == "PECANS" else "BU",
                    "GEORGIA",
                    "DEMO COUNTY",
                )
            )
        return out

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
