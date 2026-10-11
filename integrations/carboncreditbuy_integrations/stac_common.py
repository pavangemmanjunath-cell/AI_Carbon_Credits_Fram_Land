"""Shared Sentinel-2 logic for the earth-search and Copernicus STAC adapters.

Both adapters produce the same two things:

* a **vegetation block** (latest NDVI/NDMI with classes, a yearly time series
  of the best — lowest-cloud — scene around an anchor date, and a trend), and
* a **space-time cube** (via ``geo_engine.cube``).

Live reads need ``pystac-client`` and ``rasterio`` (imported lazily); the
:class:`DemoSatelliteAdapter` twin uses the deterministic demo cube so the
analysis and the cube endpoint are consistent offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import numpy as np
from shapely.geometry import Polygon, mapping

from carboncreditbuy_integrations.base import (
    Cache,
    DependencyMissingError,
    SourceProvenance,
    UpstreamError,
    cache_key,
    demo_source,
)
from carboncreditbuy_integrations.demo_support import unit_noise
from geo_engine.cube import Cube, build_demo_cube, build_grid, build_live_cube
from geo_engine.cube.live import _scene_index_on_grid
from geo_engine.indices.classify import classify_ndmi, classify_ndvi, trend_statement
from geo_engine.satellite import Scene, StacProvider, best_scene_per_period, search_scenes

SENTINEL_LICENSE = "Copernicus Sentinel data — free, full and open (Copernicus data licence)"
SENTINEL_ATTRIBUTION = (
    "Contains modified Copernicus Sentinel data {year} processed by CarbonCreditBuy"
)


@dataclass(frozen=True)
class Observation:
    date: date
    ndvi: float | None
    ndmi: float | None
    cloud_cover: float
    scene_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "ndvi": None if self.ndvi is None else round(self.ndvi, 3),
            "ndmi": None if self.ndmi is None else round(self.ndmi, 3),
            "cloud_cover": round(self.cloud_cover, 1),
            "scene_id": self.scene_id,
        }


@dataclass
class VegetationResult:
    observations: list[Observation]
    source: dict[str, Any]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        valid = [o for o in self.observations if o.ndvi is not None]
        latest = valid[-1] if valid else None
        first = valid[0] if valid else None
        change_pct: float | None = None
        if first and latest and first is not latest and first.ndvi:
            change_pct = round((latest.ndvi - first.ndvi) / abs(first.ndvi) * 100.0, 1)  # type: ignore[operator]
        indices = {
            "ndvi": {
                "value": None if latest is None else round(latest.ndvi, 3),  # type: ignore[arg-type]
                "class": None if latest is None else classify_ndvi(latest.ndvi),
                "date": None if latest is None else latest.date.isoformat(),
                "scene_id": None if latest is None else latest.scene_id,
            },
            "ndmi": {
                "value": None if latest is None or latest.ndmi is None else round(latest.ndmi, 3),
                "class": None if latest is None else classify_ndmi(latest.ndmi),
                "date": None if latest is None else latest.date.isoformat(),
                "scene_id": None if latest is None else latest.scene_id,
            },
        }
        return {
            "indices": indices,
            "time_series": [o.to_dict() for o in self.observations],
            "trend": {
                "start": first.date.strftime("%Y-%m") if first else None,
                "end": latest.date.strftime("%Y-%m") if latest else None,
                "change_pct": change_pct,
                "statement": trend_statement(change_pct),
            },
        }

    @property
    def scene_ids(self) -> list[str]:
        return [o.scene_id for o in self.observations if o.scene_id]


def _source_for(provider: StacProvider) -> SourceProvenance:
    year = datetime.now(UTC).year
    if provider.id == "earth-search":
        return SourceProvenance(
            id="sentinel-2-l2a-earth-search",
            name="Sentinel-2 L2A (Earth Search STAC, Element 84 / AWS)",
            version="L2A",
            license=SENTINEL_LICENSE,
            attribution=SENTINEL_ATTRIBUTION.format(year=year) + "; catalogue by Element 84",
            url=provider.url,
        )
    return SourceProvenance(
        id="sentinel-2-l2a-copernicus",
        name="Sentinel-2 L2A (Copernicus Data Space Ecosystem STAC)",
        version="L2A",
        license=SENTINEL_LICENSE,
        attribution=SENTINEL_ATTRIBUTION.format(year=year) + "; catalogue by ESA/CDSE",
        url=provider.url,
    )


class StacSatelliteAdapter:
    """Live Sentinel-2 adapter over any supported STAC provider."""

    def __init__(
        self,
        provider: StacProvider,
        max_cloud_cover_pct: float = 20.0,
        cache: Cache | None = None,
        cache_ttl_s: float = 6 * 3600.0,
        window_days: int = 45,
        gdal_options: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.max_cloud_cover_pct = max_cloud_cover_pct
        self.cache = cache
        self.cache_ttl_s = cache_ttl_s
        self.window_days = window_days
        self.gdal_options = gdal_options or {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR"}
        self.source = _source_for(provider)

    # -- discovery -----------------------------------------------------------
    def search(self, polygon: Polygon, start: date, end: date) -> list[Scene]:
        try:
            return search_scenes(
                self.provider, mapping(polygon), start, end, self.max_cloud_cover_pct
            )
        except ImportError as exc:
            raise DependencyMissingError("pystac-client is required for live STAC search") from exc
        except Exception as exc:
            raise UpstreamError(f"STAC search failed: {exc.__class__.__name__}") from exc

    def best_scene_for_year(self, polygon: Polygon, year: int, anchor: date) -> Scene | None:
        centre = anchor.replace(year=year)
        start = centre - timedelta(days=self.window_days)
        end = min(centre + timedelta(days=self.window_days), datetime.now(UTC).date())
        if start > end:
            return None
        scenes = self.search(polygon, start, end)
        best = best_scene_per_period(scenes, "year")
        return best.get(f"{year:04d}")

    # -- measurement ---------------------------------------------------------
    def scene_plot_means(self, scene: Scene, polygon: Polygon) -> tuple[float | None, float | None]:
        grid, mask = build_grid(polygon, 10)
        inside = mask.astype(bool)
        means: list[float | None] = []
        for index in ("ndvi", "ndmi"):
            try:
                layer = _scene_index_on_grid(scene, self.provider, index, grid, self.gdal_options)
            except ImportError as exc:
                raise DependencyMissingError(
                    "rasterio is required for live Sentinel-2 reads"
                ) from exc
            except Exception as exc:
                raise UpstreamError(
                    f"Sentinel-2 asset read failed: {exc.__class__.__name__}"
                ) from exc
            values = layer[inside]
            valid = values[~np.isnan(values)]
            means.append(float(valid.mean()) if valid.size else None)
        return means[0], means[1]

    def fetch_vegetation(
        self, polygon: Polygon, years: list[int], anchor: date | None = None, **_: Any
    ) -> VegetationResult:
        anchor = anchor or datetime.now(UTC).date()
        key = cache_key("vegetation", self.provider.id, mapping(polygon), years, anchor.isoformat())
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        observations: list[Observation] = []
        notes: list[str] = []
        for year in sorted(years):
            scene = self.best_scene_for_year(polygon, year, anchor)
            if scene is None:
                notes.append(
                    f"{year}: no scene with cloud cover ≤ {self.max_cloud_cover_pct}% in window"
                )
                continue
            ndvi, ndmi = self.scene_plot_means(scene, polygon)
            observations.append(Observation(scene.date, ndvi, ndmi, scene.cloud_cover, scene.id))
        result = VegetationResult(
            observations=observations,
            source=self.source.to_dict(
                datetime.now(UTC), scene_ids=[o.scene_id for o in observations]
            ),
            notes=notes,
        )
        if self.cache is not None:
            self.cache.set(key, result, self.cache_ttl_s)
        return result

    def build_cube(
        self,
        plot_id: str,
        polygon: Polygon,
        index: str,
        months: int,
        end: date | None = None,
        cell_size_m: int = 30,
        **_: Any,
    ) -> Cube:
        try:
            return build_live_cube(
                plot_id,
                polygon,
                self.provider,
                index=index,
                months=months,
                end=end,
                cell_size_m=cell_size_m,
                max_cloud_cover_pct=self.max_cloud_cover_pct,
                open_options=self.gdal_options,
            )
        except ImportError as exc:
            raise DependencyMissingError(
                "rasterio/pystac-client are required for the live cube"
            ) from exc

    def provenance(self) -> dict[str, Any]:
        return self.source.to_dict()


class DemoSatelliteAdapter:
    """Synthetic twin: yearly observations are read off the demo cube at the anchor month."""

    def __init__(self, provider_id: str = "earth-search") -> None:
        self.provider_id = provider_id
        base = _source_for(StacProvider(id=provider_id, url="demo://stac"))
        self.source = demo_source(base)

    def fetch_vegetation(
        self,
        polygon: Polygon,
        years: list[int],
        anchor: date | None = None,
        plot_id: str = "demo",
        planting_year: int | None = None,
        **_: Any,
    ) -> VegetationResult:
        anchor = anchor or datetime.now(UTC).date()
        years = sorted(years)
        months = (anchor.year - years[0]) * 12 + 12
        ndvi_cube = build_demo_cube(
            plot_id, polygon, "ndvi", months=months, end=anchor, planting_year=planting_year
        )
        ndmi_cube = build_demo_cube(
            plot_id, polygon, "ndmi", months=months, end=anchor, planting_year=planting_year
        )
        ndvi_stats = {s.time: s for s in ndvi_cube.stats_per_time()}
        ndmi_stats = {s.time: s for s in ndmi_cube.stats_per_time()}
        observations: list[Observation] = []
        for year in years:
            label = f"{year:04d}-{anchor.month:02d}"
            if label not in ndvi_stats:
                continue
            day = 15 + int(unit_noise(plot_id, year, "day") * 12)
            when = min(date(year, anchor.month, min(day, 28)), anchor)
            cloud = round(unit_noise(plot_id, year, "cloud") * 6.0, 1)
            scene_id = f"S2A_MSIL2A_{when.strftime('%Y%m%d')}T050659_N0511_R019_T43PGQ_DEMO"
            observations.append(
                Observation(
                    date=when,
                    ndvi=ndvi_stats[label].mean,
                    ndmi=ndmi_stats[label].mean,
                    cloud_cover=cloud,
                    scene_id=scene_id,
                )
            )
        return VegetationResult(
            observations=observations,
            source=self.source.to_dict(
                datetime.now(UTC), scene_ids=[o.scene_id for o in observations]
            ),
            notes=["demo mode: synthetic observations"],
        )

    def build_cube(
        self,
        plot_id: str,
        polygon: Polygon,
        index: str,
        months: int,
        end: date | None = None,
        cell_size_m: int = 30,
        planting_year: int | None = None,
        **_: Any,
    ) -> Cube:
        return build_demo_cube(
            plot_id,
            polygon,
            index,
            months=months,
            end=end,
            cell_size_m=cell_size_m,
            planting_year=planting_year,
        )

    def provenance(self) -> dict[str, Any]:
        return self.source.to_dict()
