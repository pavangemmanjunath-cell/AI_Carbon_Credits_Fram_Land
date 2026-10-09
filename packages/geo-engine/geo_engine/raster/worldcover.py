"""ESA WorldCover 10 m land-cover (2021 v200).

Source: Zanaga, D. et al. (2022) *ESA WorldCover 10 m 2021 v200*,
https://doi.org/10.5281/zenodo.7254221 — licence CC BY 4.0. Required
attribution: "© ESA WorldCover project 2021 / Contains modified Copernicus
Sentinel data (2021) processed by ESA WorldCover consortium".

Tiles are 3° × 3° Cloud-Optimised GeoTIFFs named after the **lower-left
(south-west) corner** of the tile, e.g. ``ESA_WorldCover_10m_2021_v200_N12E075_Map.tif``
covers 12–15 °N, 75–78 °E. The product is served from
``s3://esa-worldcover/v200/2021/map/`` (mirrored over HTTPS); the base URL is
configured through ``ESA_WORLDCOVER_BASE_URL``.

Only :func:`read_class_shares` needs rasterio; everything else is pure Python
/ NumPy so it is testable offline.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from geo_engine.errors import MissingDependencyError

#: Class table from the ESA WorldCover 2021 v200 product user manual (Table 3).
WORLDCOVER_CLASSES: Mapping[int, str] = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

NODATA = 0
TILE_DEGREES = 3
PRODUCT_NAME = "ESA WorldCover 2021 v200"
RESOLUTION_M = 10


@dataclass(frozen=True)
class ClassShare:
    """Share of one land-cover class inside a plot."""

    code: int
    name: str
    share: float
    area_ha: float
    pixel_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "share": self.share,
            "area_ha": self.area_ha,
        }


def class_name(code: int) -> str:
    """Return the class label for a WorldCover code (``"Unknown (n)"`` when absent)."""
    return WORLDCOVER_CLASSES.get(int(code), f"Unknown ({code})")


def tile_name(lon: float, lat: float, year: int = 2021, version: str = "v200") -> str:
    """Return the WorldCover tile file name containing ``(lon, lat)``.

    The tile origin is floored to a multiple of 3° (lower-left corner), so
    13.29 °N, 77.54 °E → ``N12E075`` and -0.5 °S, -84.4 °W → ``S03W087``.
    """
    lat0 = int(math.floor(lat / TILE_DEGREES) * TILE_DEGREES)
    lon0 = int(math.floor(lon / TILE_DEGREES) * TILE_DEGREES)
    ns = "N" if lat0 >= 0 else "S"
    ew = "E" if lon0 >= 0 else "W"
    return f"ESA_WorldCover_10m_{year}_{version}_{ns}{abs(lat0):02d}{ew}{abs(lon0):03d}_Map.tif"


def tiles_for_bbox(
    bbox: tuple[float, float, float, float], year: int = 2021, version: str = "v200"
) -> list[str]:
    """Return every tile name intersecting ``(min_lon, min_lat, max_lon, max_lat)``."""
    min_lon, min_lat, max_lon, max_lat = bbox
    names: list[str] = []
    lat = math.floor(min_lat / TILE_DEGREES) * TILE_DEGREES
    while lat <= max_lat:
        lon = math.floor(min_lon / TILE_DEGREES) * TILE_DEGREES
        while lon <= max_lon:
            names.append(tile_name(lon + 0.5, lat + 0.5, year, version))
            lon += TILE_DEGREES
        lat += TILE_DEGREES
    return names


def class_shares(
    values: np.ndarray,
    plot_area_ha: float,
    valid_mask: np.ndarray | None = None,
    nodata: int = NODATA,
) -> list[ClassShare]:
    """Compute per-class shares from a masked array of class codes.

    ``valid_mask`` (bool, same shape) selects the pixels inside the polygon;
    ``nodata`` pixels are excluded from the denominator. ``area_ha`` is the
    class share multiplied by the plot's geodesic area (not pixel counts × 100 m²,
    which would misstate the area at the polygon edge).
    """
    arr = np.asarray(values)
    mask = np.ones(arr.shape, dtype=bool) if valid_mask is None else np.asarray(valid_mask, bool)
    selected = arr[mask & (arr != nodata)]
    total = int(selected.size)
    if total == 0:
        return []
    codes, counts = np.unique(selected, return_counts=True)
    shares = [
        ClassShare(
            code=int(code),
            name=class_name(int(code)),
            share=round(float(count) / total, 4),
            area_ha=round(float(count) / total * plot_area_ha, 4),
            pixel_count=int(count),
        )
        for code, count in zip(codes, counts, strict=True)
    ]
    shares.sort(key=lambda s: s.share, reverse=True)
    return shares


def share_of(shares: Iterable[ClassShare], code: int) -> float:
    """Return the share of ``code`` (0.0 when absent)."""
    for item in shares:
        if item.code == code:
            return item.share
    return 0.0


def read_class_shares(
    dataset_url: str,
    polygon_geojson: dict[str, Any],
    plot_area_ha: float,
    *,
    open_options: Mapping[str, Any] | None = None,
) -> tuple[list[ClassShare], dict[str, Any]]:
    """Windowed, polygon-masked read of a WorldCover COG and class shares.

    Returns ``(shares, info)`` where ``info`` has ``pixel_count`` and the
    dataset ``nodata``. Requires rasterio (installed with the ``live`` extra);
    ``dataset_url`` may be a local path or an ``https://`` / ``s3://`` COG URL
    (GDAL reads only the needed byte ranges).
    """
    try:
        import rasterio
        from rasterio.mask import mask as rio_mask
    except ImportError as exc:  # pragma: no cover - exercised only without rasterio
        raise MissingDependencyError("rasterio is required for live WorldCover reads") from exc

    env_options = dict(open_options or {})
    with rasterio.Env(**env_options), rasterio.open(dataset_url) as src:
        data, _transform = rio_mask(
            src, [polygon_geojson], crop=True, all_touched=False, filled=True
        )
        band = data[0]
        nodata = src.nodata if src.nodata is not None else NODATA
        inside = band != nodata
        shares = class_shares(band, plot_area_ha, valid_mask=inside, nodata=int(nodata))
        info = {"pixel_count": int(inside.sum()), "nodata": int(nodata), "crs": str(src.crs)}
    return shares, info
