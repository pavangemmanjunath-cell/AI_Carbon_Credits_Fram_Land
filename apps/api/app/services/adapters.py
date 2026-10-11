"""ModeRouter — picks demo or live adapters from settings.

Every external dependency is reached through an adapter from
``integrations/``; the router is the only place that knows which twin to use.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any

from app.core.config import Settings
from carboncreditbuy_integrations import MemoryTTLCache
from carboncreditbuy_integrations.census_geocoder import (
    CensusGeocoderAdapter,
    DemoCensusGeocoderAdapter,
)
from carboncreditbuy_integrations.copernicus import CopernicusAdapter
from carboncreditbuy_integrations.data_gov_in import DataGovInAdapter, DemoDataGovInAdapter
from carboncreditbuy_integrations.earth_search import EarthSearchAdapter
from carboncreditbuy_integrations.esa_worldcover import DemoWorldCoverAdapter, WorldCoverAdapter
from carboncreditbuy_integrations.nominatim import DemoNominatimAdapter, NominatimAdapter
from carboncreditbuy_integrations.open_meteo import DemoOpenMeteoAdapter, OpenMeteoAdapter
from carboncreditbuy_integrations.photon import PhotonAdapter
from carboncreditbuy_integrations.soilgrids import DemoSoilGridsAdapter, SoilGridsAdapter
from carboncreditbuy_integrations.stac_common import DemoSatelliteAdapter
from carboncreditbuy_integrations.usda_nass import DemoUsdaNassAdapter, UsdaNassAdapter


@dataclass
class ModeRouter:
    settings: Settings

    @cached_property
    def cache(self) -> MemoryTTLCache:
        return MemoryTTLCache()

    @property
    def mode(self) -> str:
        return self.settings.atlas_mode

    @cached_property
    def landcover(self) -> Any:
        if self.settings.is_demo:
            return DemoWorldCoverAdapter()
        return WorldCoverAdapter(
            self.settings.esa_worldcover_base_url,
            version=self.settings.esa_worldcover_version,
            cache=self.cache,
        )

    @cached_property
    def satellite(self) -> Any:
        if self.settings.is_demo:
            return DemoSatelliteAdapter(self.settings.atlas_stac_provider)
        if self.settings.atlas_stac_provider == "copernicus":
            return CopernicusAdapter(
                self.settings.copernicus_stac_url,
                token=self.settings.copernicus_token or None,
                max_cloud_cover_pct=self.settings.max_cloud_cover_pct,
                cache=self.cache,
            )
        return EarthSearchAdapter(
            self.settings.earth_search_stac_url,
            max_cloud_cover_pct=self.settings.max_cloud_cover_pct,
            cache=self.cache,
        )

    @cached_property
    def climate(self) -> Any:
        if self.settings.is_demo:
            return DemoOpenMeteoAdapter()
        return OpenMeteoAdapter(
            self.settings.open_meteo_archive_url,
            self.settings.open_meteo_elevation_url,
            cache=self.cache,
        )

    @cached_property
    def soil(self) -> Any:
        if self.settings.is_demo:
            return DemoSoilGridsAdapter()
        return SoilGridsAdapter(self.settings.soilgrids_url, cache=self.cache)

    @cached_property
    def geocoder(self) -> Any:
        if self.settings.is_demo:
            return DemoNominatimAdapter()
        if self.settings.atlas_geocoder == "photon":
            return PhotonAdapter(self.settings.photon_url, cache=self.cache)
        return NominatimAdapter(
            self.settings.nominatim_url,
            self.settings.nominatim_user_agent,
            min_interval_s=self.settings.geocoder_min_interval_seconds,
            cache=self.cache,
        )

    @cached_property
    def usda_nass(self) -> Any:
        if self.settings.is_demo or not self.settings.usda_nass_api_key:
            return DemoUsdaNassAdapter()
        return UsdaNassAdapter(
            self.settings.usda_nass_api_url, self.settings.usda_nass_api_key, cache=self.cache
        )

    @cached_property
    def census(self) -> Any:
        if self.settings.is_demo:
            return DemoCensusGeocoderAdapter()
        return CensusGeocoderAdapter(self.settings.census_geocoder_url, cache=self.cache)

    @cached_property
    def data_gov_in(self) -> Any:
        if self.settings.is_demo or not self.settings.data_gov_in_api_key:
            return DemoDataGovInAdapter()
        return DataGovInAdapter(
            self.settings.data_gov_in_api_url,
            self.settings.data_gov_in_api_key,
            self.settings.data_gov_in_crop_resource_id,
            cache=self.cache,
        )
