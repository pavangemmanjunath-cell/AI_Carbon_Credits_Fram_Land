"""Tree-top detection from a LAS / LAZ (or E57) point cloud: ground -> CHM -> local maxima."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon

from geo_engine.imports.counting import count_inside
from geo_engine.imports.errors import ImportDataError, UnsupportedFormatError
from geo_engine.imports.vector import file_extension
from geo_engine.pointcloud import chm as chm_ops
from geo_engine.pointcloud.params import MAX_GRID_CELLS_PER_SIDE, PointCloudParams
from geo_engine.pointcloud.reader import (
    E57_ADVICE,
    CloudData,
    crs_label,
    crs_units,
    pye57_available,
    read_e57,
    read_header,
    read_las,
)

METHOD = "canopy height model + local maxima"
PREVIEW_DIGITS = 6
MAX_PREVIEW_TOPS = 5_000


@dataclass
class PointCloudInfo:
    """Header-level facts about a cloud (used when detection is switched off)."""

    format: str
    point_count: int
    georeferenced: bool
    crs: str | None
    bbox_wgs84: list[float] | None
    warnings: list[str] = field(default_factory=list)


@dataclass
class PointCloudResult:
    """Outcome of :func:`analyse_point_cloud`."""

    filename: str
    format: str
    point_count: int
    points_used: int
    decimation_stride: int
    georeferenced: bool
    crs: str | None
    bbox: list[float]
    bbox_wgs84: list[float] | None
    ground_method: str
    ground_classified_share: float
    point_density_per_m2: float | None
    cell_size_m: float
    count: int
    heights_m: np.ndarray
    canopy_cover_fraction: float | None
    tops_xy: np.ndarray
    tops_lonlat: np.ndarray | None
    params: PointCloudParams
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    method: str = METHOD

    # -- statistics ---------------------------------------------------------------------------
    def _stat(self, fn: Any) -> float | None:
        return round(float(fn(self.heights_m)), 2) if self.heights_m.size else None

    @property
    def mean_height_m(self) -> float | None:
        return self._stat(np.mean)

    @property
    def median_height_m(self) -> float | None:
        return self._stat(np.median)

    @property
    def p90_height_m(self) -> float | None:
        return self._stat(lambda h: np.percentile(h, 90))

    # -- plot-dependent views ---------------------------------------------------------------
    def inside_plot(self, plot: Polygon) -> np.ndarray | None:
        """Boolean mask of tree tops inside ``plot`` (``None`` when the cloud has no CRS)."""
        if self.tops_lonlat is None:
            return None
        return count_inside(plot, self.tops_lonlat[:, 0], self.tops_lonlat[:, 1])

    def count_in_plot(self, plot: Polygon | None) -> int | None:
        if plot is None:
            return None
        mask = self.inside_plot(plot)
        return None if mask is None else int(mask.sum())

    def trees_block(self, plot: Polygon | None = None) -> dict[str, Any]:
        """The contract's ``trees`` block."""
        return {
            "count": self.count,
            "count_in_plot": self.count_in_plot(plot),
            "mean_height_m": self.mean_height_m,
            "median_height_m": self.median_height_m,
            "p90_height_m": self.p90_height_m,
            "canopy_cover_fraction": self.canopy_cover_fraction,
            "confidence_field": None,
            "min_confidence": None,
            "method": (
                f"{self.method}; heights are above the estimated ground and cover the whole "
                "cloud, not only the plot"
            ),
        }

    def detection_block(self) -> dict[str, Any]:
        """The contract's ``detection`` block (``ran: true``)."""
        return {
            "ran": True,
            "method": self.method,
            "parameters": self.params.detection_parameters(self.cell_size_m),
            "notes": list(self.notes),
        }

    def preview(
        self, plot: Polygon | None = None, limit: int = MAX_PREVIEW_TOPS
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Tree tops as a FeatureCollection (``None`` without a CRS) and an optional warning."""
        if self.tops_lonlat is None:
            return None, None
        total = len(self.tops_lonlat)
        chosen = (
            np.unique(np.linspace(0, total - 1, limit).astype(int))
            if total > limit
            else np.arange(total)
        )
        mask = self.inside_plot(plot) if plot is not None else None
        features = []
        for index in chosen:
            properties: dict[str, Any] = {
                "id": int(index) + 1,
                "height_m": round(float(self.heights_m[index]), 2),
            }
            if mask is not None:
                properties["in_plot"] = bool(mask[index])
            lon, lat = self.tops_lonlat[index]
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            round(float(lon), PREVIEW_DIGITS),
                            round(float(lat), PREVIEW_DIGITS),
                        ],
                    },
                    "properties": properties,
                }
            )
        note = (
            f"The map preview shows {len(features)} of {total} tree tops."
            if total > limit
            else None
        )
        return {"type": "FeatureCollection", "features": features}, note

    def summary_block(self) -> dict[str, Any]:
        return {
            "feature_count": 1,
            "polygon_count": 0,
            "point_count": self.point_count,
            "georeferenced": self.georeferenced,
            "crs": self.crs,
        }


# ---------------------------------------------------------------------------- header only
def inspect_point_cloud(data: bytes, filename: str) -> PointCloudInfo:
    """Read the header of a LAS/LAZ file (point count, CRS, footprint) without decoding points."""
    extension = file_extension(filename)
    if extension == "e57":
        if not pye57_available():
            raise UnsupportedFormatError(E57_ADVICE, code="e57_unsupported")
        return PointCloudInfo("e57", 0, False, None, None, ["E57 headers are not inspected."])
    if extension not in ("las", "laz"):
        raise UnsupportedFormatError("point clouds must be .las, .laz or .e57")
    header = read_header(data)
    warnings = list(header.warnings)
    bbox_wgs84 = None
    if header.crs is not None:
        horizontal, _, _ = crs_units(header.crs)  # refuses geographic coordinates
        if header.bounds is not None:
            transformer = Transformer.from_crs(horizontal, "EPSG:4326", always_xy=True)
            west, south, east, north = transformer.transform_bounds(*header.bounds)
            bbox_wgs84 = [round(v, 6) for v in (west, south, east, north)]
    else:
        warnings.append("The file has no coordinate system, so it cannot be placed on the map.")
    return PointCloudInfo(
        format="laz" if header.compressed else "las",
        point_count=header.point_count,
        georeferenced=header.crs is not None,
        crs=crs_label(header.crs),
        bbox_wgs84=bbox_wgs84,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------- analysis
def _odd(window: int) -> int:
    return window if window % 2 == 1 else window + 1


def analyse_cloud(cloud: CloudData, filename: str, params: PointCloudParams) -> PointCloudResult:
    """Detect tree tops in decoded points."""
    warnings = list(cloud.warnings)
    x, y, z = cloud.x, cloud.y, cloud.z
    x0, y0 = float(x.min()), float(y.min())
    width, height = float(x.max()) - x0, float(y.max()) - y0

    cell = chm_ops.choose_cell_size(width, height, params.cell_size_m, MAX_GRID_CELLS_PER_SIDE)
    if cell > params.cell_size_m + 1e-9:
        warnings.append(
            f"The cloud spans {width:,.0f} m by {height:,.0f} m, so the canopy model cell size was "
            f"raised from {params.cell_size_m:g} m to {cell:g} m to keep the grid within "
            f"{MAX_GRID_CELLS_PER_SIDE:,} x {MAX_GRID_CELLS_PER_SIDE:,} cells."
        )
    spec = chm_ops.make_grid(x0, y0, width, height, cell)
    ground_cell = max(params.ground_cell_size_m, cell)
    ground_spec = chm_ops.make_grid(x0, y0, width, height, ground_cell)
    ground, ground_method, share, occupied = chm_ops.ground_surface(
        x,
        y,
        z,
        cloud.classification,
        ground_spec,
        params.ground_class_code,
        params.ground_class_min_share,
        params.max_ground_gap_cells,
    )
    chm, noise_high = chm_ops.canopy_height_model(
        x, y, z, ground, ground_spec, spec, params.max_tree_height_m
    )
    window = _odd(params.smoothing_window_cells)
    smoothed = chm_ops.smooth_mean(chm, window)
    radius_cells = max(1, int(round(params.window_radius_m / cell)))
    centroids, heights = chm_ops.find_tree_tops(chm, smoothed, radius_cells, params.min_height_m)

    valid = np.isfinite(smoothed)
    cover = round(float((smoothed[valid] > params.min_height_m).mean()), 4) if valid.any() else None
    area = float(occupied.sum()) * ground_cell * ground_cell
    density = round(cloud.x.size * cloud.stride / area, 2) if area > 0 else None

    # Tree-top positions: metres relative to the cloud origin -> CRS units -> WGS84.
    rel_x = x0 + (centroids[:, 1] + 0.5) * cell if centroids.size else np.zeros(0)
    rel_y = y0 + (centroids[:, 0] + 0.5) * cell if centroids.size else np.zeros(0)
    abs_x = cloud.origin[0] + rel_x / cloud.unit_h
    abs_y = cloud.origin[1] + rel_y / cloud.unit_h
    min_x = cloud.origin[0] + x0 / cloud.unit_h
    min_y = cloud.origin[1] + y0 / cloud.unit_h
    max_x = cloud.origin[0] + (x0 + width) / cloud.unit_h
    max_y = cloud.origin[1] + (y0 + height) / cloud.unit_h
    tops_lonlat = None
    bbox_wgs84 = None
    if cloud.crs is not None:
        horizontal, _, _ = crs_units(cloud.crs)
        transformer = Transformer.from_crs(horizontal, "EPSG:4326", always_xy=True)
        if abs_x.size:
            lons, lats = transformer.transform(abs_x, abs_y)
            tops_lonlat = np.column_stack([lons, lats]).astype(float)
        else:
            tops_lonlat = np.zeros((0, 2))
        west, south, east, north = transformer.transform_bounds(min_x, min_y, max_x, max_y)
        bbox_wgs84 = [round(v, 6) for v in (west, south, east, north)]

    notes = [
        (
            f"Ground: classification {params.ground_class_code} ({share:.0%} of points), "
            f"mean per {ground_cell:g} m cell, gaps filled from the nearest cells."
            if ground_method == "classification"
            else f"Ground: lowest return per {ground_cell:g} m cell, gaps filled from the nearest "
            "cells (under dense canopy this can sit above the true ground)."
        ),
        f"Canopy height model: maximum height per {cell:g} m cell, {window} x {window} mean "
        f"smoothing, tops = local maxima within {radius_cells * cell:g} m above "
        f"{params.min_height_m:g} m.",
        "Touching crowns of similar height can merge into one top and multi-stemmed trees can "
        "count twice; compare with a field count before relying on the number.",
    ]
    if noise_high:
        notes.append(
            f"{noise_high:,} points higher than {params.max_tree_height_m:g} m above ground were "
            "ignored as noise."
        )
    if radius_cells * cell < params.window_radius_m * 0.75:
        notes.append(
            "The cell size is coarse for the requested window radius; the window is one cell."
        )
    if density is not None and density < params.low_density_warning_per_m2:
        warnings.append(
            f"The point density is about {density:g} points per square metre; below "
            f"{params.low_density_warning_per_m2:g} the canopy surface has gaps that can create "
            "false tree tops, so the count may be too high."
        )

    return PointCloudResult(
        filename=filename,
        format=cloud.fmt,
        point_count=cloud.point_count,
        points_used=int(cloud.x.size),
        decimation_stride=cloud.stride,
        georeferenced=cloud.crs is not None,
        crs=crs_label(cloud.crs),
        bbox=[round(v, 3) for v in (min_x, min_y, max_x, max_y)],
        bbox_wgs84=bbox_wgs84,
        ground_method=ground_method,
        ground_classified_share=round(share, 4),
        point_density_per_m2=density,
        cell_size_m=cell,
        count=int(len(heights)),
        heights_m=heights,
        canopy_cover_fraction=cover,
        tops_xy=np.column_stack([abs_x, abs_y]) if abs_x.size else np.zeros((0, 2)),
        tops_lonlat=tops_lonlat,
        params=params,
        warnings=warnings,
        notes=notes,
    )


def analyse_point_cloud(
    data: bytes, filename: str, params: PointCloudParams | None = None
) -> PointCloudResult:
    """Decode a LAS/LAZ (or E57 when ``pye57`` is installed) file and detect tree tops.

    Raises :class:`UnsupportedFormatError` for ``.e57`` without ``pye57`` (HTTP 415 in the API,
    with advice to convert to LAS/LAZ) and :class:`ImportDataError` for unreadable, empty or
    geographic-coordinate clouds.
    """
    params = params or PointCloudParams.from_config()
    extension = file_extension(filename)
    if extension == "e57":
        if not pye57_available():
            raise UnsupportedFormatError(E57_ADVICE, code="e57_unsupported")
        cloud = read_e57(data, params)
    elif extension in ("las", "laz"):
        cloud = read_las(data, params)
    else:
        raise UnsupportedFormatError("point clouds must be .las, .laz or .e57")
    if cloud.x.size == 0:
        raise ImportDataError("empty_cloud", "the point cloud holds no usable points")
    return analyse_cloud(cloud, filename, params)
