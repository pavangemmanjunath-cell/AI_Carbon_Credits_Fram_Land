"""Open-Meteo adapter — climate normals (ERA5 archive) and elevation.

* Archive: ``OPEN_METEO_ARCHIVE_URL`` (https://archive-api.open-meteo.com/v1/archive)
  with ``daily=temperature_2m_mean,precipitation_sum``; MAT = mean of daily
  means, MAP = total precipitation ÷ number of years. Default window 2015–2024
  (10 years; a 30-year normal would be ~11 000 rows per call).
* Elevation: ``OPEN_METEO_ELEVATION_URL`` (https://api.open-meteo.com/v1/elevation),
  Copernicus GLO-90 DEM.
* No API key for non-commercial use (≤ 10 000 calls/day). Licence CC BY 4.0;
  attribution "Weather data by Open-Meteo.com".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from carboncreditbuy_integrations.base import (
    Cache,
    HttpAdapter,
    SourceProvenance,
    UpstreamDataError,
    demo_source,
)
from carboncreditbuy_integrations.demo_support import region_for, unit_noise

SOURCE = SourceProvenance(
    id="open-meteo",
    name="Open-Meteo Historical Weather API (ERA5) and Elevation API (Copernicus DEM GLO-90)",
    version="v1",
    license="CC BY 4.0",
    attribution="Weather data by Open-Meteo.com (CC BY 4.0); ERA5 © ECMWF/Copernicus; "
    "elevation © Copernicus DEM GLO-90",
    url="https://open-meteo.com/",
)
DEFAULT_START_YEAR = 2015
DEFAULT_END_YEAR = 2024


@dataclass(frozen=True)
class ClimateNormals:
    mean_annual_temp_c: float
    annual_precip_mm: float
    elevation_m: float | None
    start_year: int
    end_year: int
    source: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean_annual_temp_c": round(self.mean_annual_temp_c, 2),
            "annual_precip_mm": round(self.annual_precip_mm, 1),
            "elevation_m": None if self.elevation_m is None else round(self.elevation_m, 1),
            "period": f"{self.start_year}-{self.end_year}",
        }


class OpenMeteoAdapter(HttpAdapter):
    def __init__(
        self,
        archive_url: str,
        elevation_url: str,
        cache: Cache | None = None,
        start_year: int = DEFAULT_START_YEAR,
        end_year: int = DEFAULT_END_YEAR,
        **kwargs: Any,
    ) -> None:
        super().__init__(cache=cache, cache_ttl_s=7 * 86_400.0, **kwargs)
        self.archive_url = archive_url
        self.elevation_url = elevation_url
        self.start_year = start_year
        self.end_year = end_year

    def fetch_elevation(self, lat: float, lon: float) -> float:
        data = self.get_json(self.elevation_url, params={"latitude": lat, "longitude": lon})
        try:
            return float(data["elevation"][0])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise UpstreamDataError("Open-Meteo elevation payload malformed") from exc

    def fetch_climate_normals(
        self, lat: float, lon: float, with_elevation: bool = True
    ) -> ClimateNormals:
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{self.start_year}-01-01",
            "end_date": f"{self.end_year}-12-31",
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "UTC",
        }
        data = self.get_json(self.archive_url, params=params)
        try:
            temps = [t for t in data["daily"]["temperature_2m_mean"] if t is not None]
            precip = [p for p in data["daily"]["precipitation_sum"] if p is not None]
        except (KeyError, TypeError) as exc:
            raise UpstreamDataError("Open-Meteo archive payload malformed") from exc
        if not temps or not precip:
            raise UpstreamDataError("Open-Meteo archive returned no daily values")
        years = self.end_year - self.start_year + 1
        mat = sum(temps) / len(temps)
        map_mm = sum(precip) / years
        elevation: float | None = None
        if with_elevation:
            elevation = self.fetch_elevation(lat, lon)
        if elevation is None and isinstance(data.get("elevation"), int | float):
            elevation = float(data["elevation"])
        return ClimateNormals(
            mat,
            map_mm,
            elevation,
            self.start_year,
            self.end_year,
            SOURCE.to_dict(datetime.now(UTC)),
        )

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()


class DemoOpenMeteoAdapter:
    """Synthetic normals: region demo climate (IN/US/EU) with a small deterministic jitter;
    a latitude-based formula elsewhere."""

    def fetch_elevation(self, lat: float, lon: float) -> float:
        return self.fetch_climate_normals(lat, lon).elevation_m or 0.0

    def fetch_climate_normals(
        self, lat: float, lon: float, with_elevation: bool = True
    ) -> ClimateNormals:
        hint = region_for(lat, lon)
        jitter = unit_noise("open-meteo", round(lat, 2), round(lon, 2)) - 0.5
        if hint is not None:
            mat, precip, elev = hint.demo_climate
        else:
            mat = 27.0 - 0.55 * abs(lat)
            precip = 1200.0 - 15.0 * abs(lat)
            elev = 250.0
        return ClimateNormals(
            mean_annual_temp_c=mat + 0.4 * jitter,
            annual_precip_mm=max(50.0, precip + 40.0 * jitter),
            elevation_m=max(0.0, elev + 20.0 * jitter),
            start_year=DEFAULT_START_YEAR,
            end_year=DEFAULT_END_YEAR,
            source=demo_source(SOURCE).to_dict(datetime.now(UTC)),
        )

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
