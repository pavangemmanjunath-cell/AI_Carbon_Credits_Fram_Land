"""data.gov.in Open Government Data (OGD) Platform India adapter.

* ``DATA_GOV_IN_API_URL`` (https://api.data.gov.in/resource) + ``/<resource_id>``
  with ``api-key`` (free, https://data.gov.in), ``format=json``, ``limit``,
  ``offset`` and ``filters[<field>]=<value>``.
* The district-wise crop production resource id is configurable
  (``DATA_GOV_IN_CROP_RESOURCE_ID``); field names differ per resource (e.g.
  ``state_name`` / ``district_name`` / ``crop`` / ``crop_year`` / ``season`` /
  ``area_`` / ``production_``), so filter keys are parameters here — verify
  against the resource's "Fields" tab.
* Licence: Government Open Data License – India (GODL); attribution
  "Source: data.gov.in (Open Government Data Platform India)".
* Rate limit: the platform caps keys per minute/day (see your key's page).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from carboncreditbuy_integrations.base import (
    Cache,
    ConfigurationError,
    HttpAdapter,
    SourceProvenance,
    UpstreamDataError,
    demo_source,
)
from carboncreditbuy_integrations.demo_support import unit_noise

SOURCE = SourceProvenance(
    id="data-gov-in",
    name="Open Government Data (OGD) Platform India — data.gov.in",
    version=None,
    license="Government Open Data License – India (GODL)",
    attribution="Source: data.gov.in (Open Government Data Platform India)",
    url="https://data.gov.in/",
)


@dataclass(frozen=True)
class ResourceRecords:
    resource_id: str
    total: int | None
    records: list[dict[str, Any]]
    source: dict[str, Any]


class DataGovInAdapter(HttpAdapter):
    def __init__(
        self,
        api_url: str,
        api_key: str,
        crop_resource_id: str | None = None,
        cache: Cache | None = None,
        state_field: str = "state_name",
        district_field: str = "district_name",
        crop_field: str = "crop",
        **kwargs: Any,
    ) -> None:
        if not api_key:
            raise ConfigurationError("DATA_GOV_IN_API_KEY is required")
        super().__init__(cache=cache, cache_ttl_s=86_400.0, **kwargs)
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.crop_resource_id = crop_resource_id
        self.state_field = state_field
        self.district_field = district_field
        self.crop_field = crop_field

    def query_resource(
        self,
        resource_id: str,
        filters: dict[str, str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ResourceRecords:
        params: dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": max(1, min(limit, 1000)),
            "offset": max(0, offset),
        }
        for key, value in (filters or {}).items():
            params[f"filters[{key}]"] = value
        data = self.get_json(f"{self.api_url}/{resource_id}", params=params)
        if "records" not in data:
            raise UpstreamDataError("data.gov.in payload has no 'records' key")
        total = data.get("total")
        return ResourceRecords(
            resource_id,
            int(total) if total is not None else None,
            list(data["records"]),
            SOURCE.to_dict(datetime.now(UTC)),
        )

    def fetch_crop_production(
        self, state: str, district: str | None = None, crop: str | None = None, limit: int = 200
    ) -> ResourceRecords:
        if not self.crop_resource_id:
            raise ConfigurationError("DATA_GOV_IN_CROP_RESOURCE_ID is not configured")
        filters = {self.state_field: state}
        if district:
            filters[self.district_field] = district
        if crop:
            filters[self.crop_field] = crop
        return self.query_resource(self.crop_resource_id, filters, limit=limit)

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()


class DemoDataGovInAdapter:
    def fetch_crop_production(
        self, state: str, district: str | None = None, crop: str | None = None, limit: int = 200
    ) -> ResourceRecords:
        crop_name = crop or "Mango"
        records = []
        for year in range(2019, 2024):
            noise = unit_noise("datagovin", state, district, crop_name, year)
            records.append(
                {
                    "state_name": state,
                    "district_name": district or "Bengaluru Rural",
                    "crop_year": year,
                    "season": "Whole Year",
                    "crop": crop_name,
                    "area_": round(2500 + 500 * noise),
                    "production_": round(22_000 + 6000 * noise),
                }
            )
        return ResourceRecords(
            "demo-crop-production",
            len(records),
            records[:limit],
            demo_source(SOURCE).to_dict(datetime.now(UTC)),
        )

    def query_resource(
        self,
        resource_id: str,
        filters: dict[str, str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ResourceRecords:
        f = filters or {}
        return self.fetch_crop_production(
            f.get("state_name", "Karnataka"), f.get("district_name"), f.get("crop"), limit
        )

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
