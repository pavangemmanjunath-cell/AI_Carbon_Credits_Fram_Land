"""ESA WorldCover 10 m 2021 v200 adapter.

Live reads use rasterio/GDAL range requests against the public COG tiles
(``ESA_WORLDCOVER_BASE_URL/<tile>.tif``); no API key is needed. GDAL reads
only the bytes covering the plot, so a 2 ha plot costs a few hundred kB.

Licence CC BY 4.0 — attribution text is in :data:`SOURCE`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from atlas_integrations.base import (
    Cache,
    DependencyMissingError,
    SourceProvenance,
    UpstreamError,
    cache_key,
    demo_source,
)
from atlas_integrations.demo_support import unit_noise
from geo_engine.raster.worldcover import (
    PRODUCT_NAME,
    RESOLUTION_M,
    ClassShare,
    class_name,
    read_class_shares,
    tile_name,
    tiles_for_bbox,
)

SOURCE = SourceProvenance(
    id="esa-worldcover",
    name=PRODUCT_NAME,
    version="v200",
    license="CC BY 4.0",
    attribution=(
        "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) "
        "processed by ESA WorldCover consortium"
    ),
    url="https://esa-worldcover.org/",
)
TREE_COVER_CODE = 10
CROPLAND_CODE = 40


@dataclass
class LandCoverResult:
    classes: list[ClassShare]
    tiles: list[str]
    source: dict[str, Any]
    pixel_count: int
    notes: list[str] = field(default_factory=list)

    @property
    def tree_cover_share(self) -> float:
        return next((c.share for c in self.classes if c.code == TREE_COVER_CODE), 0.0)

    @property
    def cropland_share(self) -> float:
        return next((c.share for c in self.classes if c.code == CROPLAND_CODE), 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": "ESA WorldCover",
            "version": "2021 v200",
            "resolution_m": RESOLUTION_M,
            "classes": [c.to_dict() for c in self.classes],
            "tree_cover_share": self.tree_cover_share,
            "cropland_share": self.cropland_share,
        }


def _merge_counts(partials: list[list[ClassShare]], area_ha: float) -> list[ClassShare]:
    counts: dict[int, int] = {}
    for shares in partials:
        for share in shares:
            counts[share.code] = counts.get(share.code, 0) + share.pixel_count
    total = sum(counts.values())
    if total == 0:
        return []
    merged = [
        ClassShare(
            code=code,
            name=class_name(code),
            share=round(n / total, 4),
            area_ha=round(n / total * area_ha, 4),
            pixel_count=n,
        )
        for code, n in counts.items()
    ]
    merged.sort(key=lambda s: s.share, reverse=True)
    return merged


class WorldCoverAdapter:
    """Live adapter (rasterio required)."""

    def __init__(
        self,
        base_url: str,
        version: str = "v200",
        year: int = 2021,
        cache: Cache | None = None,
        cache_ttl_s: float = 86_400.0,
        gdal_options: dict[str, Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.version = version
        self.year = year
        self.cache = cache
        self.cache_ttl_s = cache_ttl_s
        self.gdal_options = gdal_options or {
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
            "AWS_NO_SIGN_REQUEST": "YES",
        }

    def tile_url(self, lon: float, lat: float) -> str:
        return f"{self.base_url}/{tile_name(lon, lat, self.year, self.version)}"

    def fetch_land_cover(
        self,
        polygon_geojson: dict[str, Any],
        bbox: tuple[float, float, float, float],
        area_ha: float,
    ) -> LandCoverResult:
        key = cache_key("worldcover", self.version, polygon_geojson, round(area_ha, 4))
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        tiles = tiles_for_bbox(bbox, self.year, self.version)
        partials: list[list[ClassShare]] = []
        pixels = 0
        for tile in tiles:
            url = f"{self.base_url}/{tile}"
            try:
                shares, info = read_class_shares(
                    url, polygon_geojson, area_ha, open_options=self.gdal_options
                )
            except ImportError as exc:
                raise DependencyMissingError(
                    "rasterio is required for live WorldCover reads"
                ) from exc
            except Exception as exc:  # rasterio raises RasterioIOError (subclass of OSError)
                raise UpstreamError(
                    f"WorldCover tile read failed: {exc.__class__.__name__}"
                ) from exc
            partials.append(shares)
            pixels += int(info.get("pixel_count", 0))
        result = LandCoverResult(
            classes=_merge_counts(partials, area_ha),
            tiles=tiles,
            source=SOURCE.to_dict(datetime.now(UTC)),
            pixel_count=pixels,
        )
        if self.cache is not None:
            self.cache.set(key, result, self.cache_ttl_s)
        return result

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()


class DemoWorldCoverAdapter:
    """Deterministic synthetic land-cover shares (seeded by the plot id)."""

    def __init__(self, seed_salt: str = "worldcover") -> None:
        self.seed_salt = seed_salt

    def fetch_land_cover(
        self,
        polygon_geojson: dict[str, Any],
        bbox: tuple[float, float, float, float],
        area_ha: float,
        plot_id: str = "demo",
    ) -> LandCoverResult:
        n1 = unit_noise(self.seed_salt, plot_id, 1)
        n2 = unit_noise(self.seed_salt, plot_id, 2)
        cropland = round(0.45 + 0.25 * n1, 2)
        tree = round(min(0.15 + 0.20 * n2, 0.95 - cropland), 2)
        grass = round(max(0.0, 0.97 - cropland - tree), 2)
        built = round(max(0.0, 1.0 - cropland - tree - grass), 2)
        raw = {40: cropland, 10: tree, 30: grass, 50: built}
        total_px = 10_000
        shares = [
            ClassShare(
                code, class_name(code), share, round(share * area_ha, 4), int(share * total_px)
            )
            for code, share in raw.items()
            if share > 0
        ]
        shares.sort(key=lambda s: s.share, reverse=True)
        return LandCoverResult(
            classes=shares,
            tiles=tiles_for_bbox(bbox),
            source=demo_source(SOURCE).to_dict(datetime.now(UTC)),
            pixel_count=total_px,
            notes=["demo mode: synthetic land-cover shares"],
        )

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
