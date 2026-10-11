"""carboncreditbuy_integrations — adapters for every external API CarbonCreditBuy uses.

Each sub-package has a live adapter (httpx / rasterio / pystac-client, all
endpoints injected from environment-driven settings) and a ``Demo*`` twin that
returns deterministic synthetic data labelled ``synthetic-demo``.

Sub-packages: ``esa_worldcover``, ``earth_search``, ``copernicus``,
``open_meteo``, ``soilgrids``, ``nominatim``, ``photon``, ``usda_nass``,
``census_geocoder``, ``data_gov_in``.
"""

from carboncreditbuy_integrations.base import (
    AdapterError,
    ConfigurationError,
    DependencyMissingError,
    MemoryTTLCache,
    NotFoundError,
    RateLimitedError,
    SourceProvenance,
    UpstreamDataError,
    UpstreamError,
)

__version__ = "0.1.0"
__all__ = [
    "AdapterError",
    "ConfigurationError",
    "DependencyMissingError",
    "MemoryTTLCache",
    "NotFoundError",
    "RateLimitedError",
    "SourceProvenance",
    "UpstreamDataError",
    "UpstreamError",
]
