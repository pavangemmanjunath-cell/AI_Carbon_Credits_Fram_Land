"""Live cube builder: monthly best Sentinel-2 scene → index → grid aggregation.

Pipeline per month (STAC search is done once for the whole period):

1. :func:`geo_engine.satellite.best_scene_per_period` picks the lowest-cloud
   scene (``eo:cloud_cover ≤ MAX_CLOUD_COVER_PCT``).
2. The required band COGs (``red``/``nir``/``swir16``/``rededge`` and ``scl``)
   are read **windowed** around the plot (GDAL range requests).
3. Digital numbers are converted to reflectance (offset −1000 DN for
   processing baseline ≥ 04.00 unless the catalogue already applied it).
4. SCL is resampled (nearest) onto the 10 m band grid and classes 4/5/6 kept.
5. The index is computed per pixel and reprojected onto the plot's lon/lat
   grid with **average** resampling (30 m cells ≈ 3 × 3 10 m pixels).

Only :func:`aggregate_to_grid` and :func:`index_from_bands` are pure enough for
offline tests; :func:`build_live_cube` needs network access and rasterio.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import numpy as np
from shapely.geometry import Polygon, mapping

from geo_engine.cube.grid import DEFAULT_CELL_SIZE_M, CubeGrid, build_grid, month_sequence
from geo_engine.cube.types import Cube
from geo_engine.errors import GeoEngineError, MissingDependencyError
from geo_engine.indices.masks import scl_clear_mask
from geo_engine.indices.spectral import normalized_difference
from geo_engine.satellite.stac import Scene, StacProvider, best_scene_per_period, search_scenes

INDEX_BANDS: dict[str, tuple[str, str]] = {
    "ndvi": ("nir", "red"),
    "ndmi": ("nir", "swir16"),
    "ndre": ("nir", "rededge"),
}


def index_from_bands(a: np.ndarray, b: np.ndarray, scl: np.ndarray | None = None) -> np.ndarray:
    """Compute ``(a-b)/(a+b)`` and apply the SCL clear mask (NaN elsewhere)."""
    result = normalized_difference(a, b)
    if scl is not None:
        clear = scl_clear_mask(scl)
        result = np.where(clear, result, np.nan).astype(np.float32)
    return result


def aggregate_to_grid(
    index_array: np.ndarray, src_transform: Any, src_crs: Any, grid: CubeGrid
) -> np.ndarray:
    """Average-resample a projected index raster onto the lon/lat cube grid.

    Requires rasterio. NaN is treated as nodata on both sides, so cloud-masked
    pixels do not drag the cell mean down.
    """
    try:
        from rasterio.enums import Resampling
        from rasterio.transform import from_bounds
        from rasterio.warp import reproject
    except ImportError as exc:  # pragma: no cover
        raise MissingDependencyError("rasterio is required for grid aggregation") from exc

    destination = np.full((grid.rows, grid.cols), np.nan, dtype=np.float32)
    dst_transform = from_bounds(*grid.bbox, grid.cols, grid.rows)
    reproject(
        source=np.asarray(index_array, dtype=np.float32),
        destination=destination,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=np.nan,
        dst_transform=dst_transform,
        dst_crs="EPSG:4326",
        dst_nodata=np.nan,
        resampling=Resampling.average,
    )
    return destination


def reflectance_offset_dn(scene: Scene, provider: StacProvider) -> float:
    """DN offset to add before scaling (−1000 for baseline ≥ 04.00, else 0)."""
    props = scene.properties
    if props.get("earthsearch:boa_offset_applied") is True:
        return 0.0
    baseline = str(props.get("s2:processing_baseline", "") or "")
    try:
        if float(baseline) >= 4.0:
            return provider.reflectance_offset_dn
    except ValueError:
        pass
    return 0.0


def _read_window(src: Any, bounds_4326: tuple[float, float, float, float], pad_px: int = 2):
    """Read the pixels covering ``bounds_4326`` from an opened rasterio dataset."""
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds as window_from_bounds

    left, bottom, right, top = transform_bounds("EPSG:4326", src.crs, *bounds_4326, densify_pts=5)
    window = window_from_bounds(left, bottom, right, top, transform=src.transform)
    window = window.round_offsets().round_lengths()
    from rasterio.windows import Window

    window = Window(
        max(0, int(window.col_off) - pad_px),
        max(0, int(window.row_off) - pad_px),
        int(window.width) + 2 * pad_px,
        int(window.height) + 2 * pad_px,
    )
    data = src.read(1, window=window, boundless=True, fill_value=0)
    return data, src.window_transform(window), src.crs


def _scene_index_on_grid(
    scene: Scene, provider: StacProvider, index: str, grid: CubeGrid, open_options: dict[str, Any]
) -> np.ndarray:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    band_a, band_b = INDEX_BANDS[index]
    missing = [role for role in (band_a, band_b, "scl") if role not in scene.assets]
    if missing:
        raise GeoEngineError(f"scene {scene.id} lacks assets for roles {missing}")
    offset = reflectance_offset_dn(scene, provider)
    with rasterio.Env(**open_options):
        with rasterio.open(scene.assets[band_a]) as src_a:
            a_dn, a_transform, a_crs = _read_window(src_a, grid.bbox)
        with rasterio.open(scene.assets[band_b]) as src_b:
            b_dn, b_transform, b_crs = _read_window(src_b, grid.bbox)
        with rasterio.open(scene.assets["scl"]) as src_scl:
            scl_raw, scl_transform, scl_crs = _read_window(src_scl, grid.bbox, pad_px=1)

    def to_grid_of_a(
        data: np.ndarray, transform: Any, crs: Any, resampling: Resampling
    ) -> np.ndarray:
        if data.shape == a_dn.shape and transform == a_transform and crs == a_crs:
            return data
        out = np.zeros(a_dn.shape, dtype=data.dtype)
        reproject(
            source=data,
            destination=out,
            src_transform=transform,
            src_crs=crs,
            dst_transform=a_transform,
            dst_crs=a_crs,
            resampling=resampling,
        )
        return out

    b_on_a = to_grid_of_a(b_dn, b_transform, b_crs, Resampling.bilinear)
    scl_on_a = to_grid_of_a(scl_raw, scl_transform, scl_crs, Resampling.nearest)
    scale = provider.reflectance_scale
    a_refl = (a_dn.astype(np.float32) + offset) * scale
    b_refl = (b_on_a.astype(np.float32) + offset) * scale
    nodata = (a_dn == 0) | (b_on_a == 0)
    index_px = index_from_bands(a_refl, b_refl, scl_on_a)
    index_px[nodata] = np.nan
    return aggregate_to_grid(index_px, a_transform, a_crs, grid)


def build_live_cube(
    plot_id: str,
    polygon: Polygon,
    provider: StacProvider,
    index: str = "ndvi",
    months: int = 36,
    end: date | None = None,
    cell_size_m: int = DEFAULT_CELL_SIZE_M,
    max_cloud_cover_pct: float = 20.0,
    open_options: dict[str, Any] | None = None,
) -> Cube:
    """Build the cube from live Sentinel-2 data (network + rasterio required)."""
    index = index.lower()
    if index not in INDEX_BANDS:
        raise ValueError(f"unsupported index {index!r}")
    end = end or datetime.now(UTC).date()
    grid, mask = build_grid(polygon, cell_size_m)
    times = month_sequence(end, months)
    start = date(int(times[0][:4]), int(times[0][5:]), 1)
    scenes = search_scenes(provider, mapping(polygon), start, end, max_cloud_cover_pct)
    best = best_scene_per_period(scenes, "month")
    values = np.full((months, grid.rows, grid.cols), np.nan, dtype=np.float32)
    inside = mask.astype(bool)
    used: list[str] = []
    for t, label in enumerate(times):
        scene = best.get(label)
        if scene is None:
            continue
        layer = _scene_index_on_grid(scene, provider, index, grid, dict(open_options or {}))
        layer[~inside] = np.nan
        values[t] = layer
        used.append(scene.id)
    provenance = {
        "source": provider.id,
        "collection": provider.collection,
        "composite": "monthly-min-cloud",
        "cloud_mask": "SCL classes 4,5,6 kept",
        "aggregation": f"{cell_size_m // 10}×{cell_size_m // 10} mean of 10 m pixels"
        if cell_size_m % 10 == 0
        else f"{cell_size_m} m cells",
        "scene_ids": used,
        "max_cloud_cover_pct": max_cloud_cover_pct,
    }
    return Cube(
        plot_id=plot_id,
        index=index,
        grid=grid,
        times=times,
        mask=mask,
        values=values,
        provenance=provenance,
    )
