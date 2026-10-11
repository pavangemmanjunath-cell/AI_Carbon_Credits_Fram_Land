"""Copernicus Data Space Ecosystem (CDSE) STAC adapter for Sentinel-2 L2A.

* Catalogue: ``COPERNICUS_STAC_URL`` (default https://stac.dataspace.copernicus.eu/v1)
* Collection ``sentinel-2-l2a``; asset keys follow SAFE band naming and are
  configurable because the catalogue is evolving — defaults ``B04_10m``,
  ``B08_10m``, ``B11_20m``, ``B05_20m``, ``SCL_20m``. **Verify against the live
  catalogue** before relying on them.
* Searching is anonymous; **downloading assets requires a CDSE access token**
  (``COPERNICUS_TOKEN``), sent as ``Authorization: Bearer`` and, for GDAL
  reads, through ``GDAL_HTTP_HEADERS``.
"""

from __future__ import annotations

from typing import Any

from carboncreditbuy_integrations.base import Cache
from carboncreditbuy_integrations.stac_common import StacSatelliteAdapter
from geo_engine.satellite import PROVIDERS


class CopernicusAdapter(StacSatelliteAdapter):
    def __init__(
        self,
        stac_url: str,
        token: str | None = None,
        max_cloud_cover_pct: float = 20.0,
        asset_keys: dict[str, str] | None = None,
        cache: Cache | None = None,
    ) -> None:
        base = PROVIDERS["copernicus"]
        provider = base.with_overrides(
            url=stac_url,
            token=token or None,
            asset_keys={**base.asset_keys, **(asset_keys or {})},
        )
        gdal_options: dict[str, Any] = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR"}
        if token:
            gdal_options["GDAL_HTTP_HEADERS"] = f"Authorization: Bearer {token}"
        super().__init__(provider, max_cloud_cover_pct, cache=cache, gdal_options=gdal_options)
