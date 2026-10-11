"""Earth Search (Element 84) STAC adapter for Sentinel-2 L2A on AWS.

* Catalogue: ``EARTH_SEARCH_STAC_URL`` (default https://earth-search.aws.element84.com/v1)
* Collection ``sentinel-2-l2a``; assets ``red`` (B04), ``nir`` (B08), ``swir16`` (B11),
  ``rededge1`` (B05), ``scl`` — Cloud-Optimised GeoTIFFs, no authentication.
* Cloud filter: ``eo:cloud_cover ≤ MAX_CLOUD_COVER_PCT``.
"""

from __future__ import annotations

from typing import Any

from carboncreditbuy_integrations.base import Cache
from carboncreditbuy_integrations.stac_common import StacSatelliteAdapter
from geo_engine.satellite import PROVIDERS


class EarthSearchAdapter(StacSatelliteAdapter):
    def __init__(
        self,
        stac_url: str,
        max_cloud_cover_pct: float = 20.0,
        cache: Cache | None = None,
        gdal_options: dict[str, Any] | None = None,
    ) -> None:
        provider = PROVIDERS["earth-search"].with_overrides(url=stac_url)
        super().__init__(provider, max_cloud_cover_pct, cache=cache, gdal_options=gdal_options)
