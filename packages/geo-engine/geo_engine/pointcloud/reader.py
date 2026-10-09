"""Read LAS / LAZ (laspy) and, when ``pye57`` is installed, E57 point clouds into metric arrays.

Points are read in chunks, noise classes are dropped, clouds above ``max_points`` are thinned
deterministically (every k-th point of the file order) and coordinates are stored as float32
offsets from the first chunk's minimum, in **metres** (CRS units are converted), which keeps
30 million points under about 400 MB. Clouds in geographic coordinates (degrees) are refused.
Without a CRS the cloud is analysed with its coordinates taken as metres.
"""

from __future__ import annotations

import io
import math
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from pyproj import CRS

from geo_engine.imports.errors import ImportDataError, UnsupportedFormatError
from geo_engine.pointcloud.params import PointCloudParams

CHUNK_POINTS = 1_000_000
E57_ADVICE = (
    "E57 files need the optional 'pye57' package, which is not installed on this server. "
    "Convert the cloud to LAS or LAZ first (CloudCompare: File > Save as .las; PDAL: "
    "pdal translate in.e57 out.laz) and upload that instead."
)


@dataclass
class CloudHeader:
    """What the header of a LAS/LAZ file says (no points decoded)."""

    point_count: int
    crs: CRS | None
    compressed: bool
    version: str
    point_format: int
    bounds: tuple[float, float, float, float] | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class CloudData:
    """Points as float32 metres relative to ``origin`` (CRS units, z in its own unit)."""

    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    classification: np.ndarray | None
    origin: tuple[float, float, float]
    unit_h: float
    unit_v: float
    crs: CRS | None
    point_count: int
    stride: int
    noise_removed: int
    fmt: str
    warnings: list[str] = field(default_factory=list)


def crs_units(crs: CRS) -> tuple[CRS, float, float]:
    """``(horizontal CRS, metres per horizontal unit, metres per vertical unit)``."""
    horizontal = crs
    vertical: CRS | None = None
    if crs.is_compound:
        parts = crs.sub_crs_list
        horizontal = parts[0]
        vertical = parts[1] if len(parts) > 1 else None
    if horizontal.is_geographic:
        raise ImportDataError(
            "geographic_crs",
            "the point cloud uses geographic coordinates (degrees); export it in a projected "
            "CRS in metres (for example the UTM zone of the site) and upload again",
        )
    unit_h = 1.0
    if horizontal.axis_info:
        unit_h = float(horizontal.axis_info[0].unit_conversion_factor or 1.0)
    unit_v = unit_h
    if vertical is not None and vertical.axis_info:
        unit_v = float(vertical.axis_info[0].unit_conversion_factor or unit_h)
    return horizontal, unit_h, unit_v


def crs_label(crs: CRS | None) -> str | None:
    """``EPSG:32643`` when the CRS has an EPSG code, otherwise its name."""
    if crs is None:
        return None
    for candidate in (crs, *(crs.sub_crs_list if crs.is_compound else [])):
        epsg = candidate.to_epsg()
        if epsg:
            return f"EPSG:{epsg}"
    return crs.name or "unknown CRS"


def _open_las(data: bytes) -> Any:
    import laspy

    try:
        return laspy.open(io.BytesIO(data))
    except Exception as exc:
        if "backend" in str(exc).lower():
            raise UnsupportedFormatError(
                "this server cannot decode LAZ (no LAZ backend installed); upload LAS instead",
                code="laz_backend_missing",
            ) from exc
        raise ImportDataError(
            "invalid_content", "the file is not a readable LAS/LAZ point cloud"
        ) from exc


def _parse_crs(header: Any, warnings: list[str]) -> CRS | None:
    try:
        crs = header.parse_crs()
    except Exception:
        warnings.append("The coordinate system in the file header could not be read.")
        return None
    return crs if isinstance(crs, CRS) else None


def read_header(data: bytes) -> CloudHeader:
    """Read only the header of a LAS/LAZ file (point count, CRS, compression)."""
    warnings: list[str] = []
    with _open_las(data) as reader:
        header = reader.header
        crs = _parse_crs(header, warnings)
        bounds: tuple[float, float, float, float] | None = None
        try:
            mins, maxs = header.mins, header.maxs
            candidate = (float(mins[0]), float(mins[1]), float(maxs[0]), float(maxs[1]))
            if all(math.isfinite(v) for v in candidate) and candidate[0] <= candidate[2]:
                bounds = candidate
        except Exception:  # a damaged header: the points themselves are checked later
            bounds = None
        return CloudHeader(
            point_count=int(header.point_count),
            crs=crs,
            compressed=bool(header.are_points_compressed),
            version=str(header.version),
            point_format=int(header.point_format.id),
            bounds=bounds,
            warnings=warnings,
        )


def read_las(data: bytes, params: PointCloudParams) -> CloudData:
    """Decode a LAS/LAZ file (chunked, thinned above ``params.max_points``)."""
    warnings: list[str] = []
    reader = _open_las(data)
    try:
        header = reader.header
        count = int(header.point_count)
        if count <= 0:
            raise ImportDataError("empty_cloud", "the point cloud holds no points")
        if count > params.max_points_hard_limit:
            raise ImportDataError(
                "too_many_points",
                f"the point cloud declares {count:,} points; the limit is "
                f"{params.max_points_hard_limit:,}. Thin or tile it first.",
            )
        if not header.are_points_compressed and count * int(header.point_format.size) > len(data):
            raise ImportDataError("truncated", "the LAS file is shorter than its header declares")
        crs = _parse_crs(header, warnings)
        unit_h = unit_v = 1.0
        if crs is not None:
            _, unit_h, unit_v = crs_units(crs)
        stride = max(1, math.ceil(count / params.max_points))
        if stride > 1:
            warnings.append(
                f"The cloud has {count:,} points; every {stride}th point was used "
                f"(about {math.ceil(count / stride):,} points) to stay within "
                f"{params.max_points:,}."
            )
        noise = np.array(params.noise_class_codes, dtype=np.uint8)
        xs: list[np.ndarray] = []
        ys: list[np.ndarray] = []
        zs: list[np.ndarray] = []
        classes: list[np.ndarray] = []
        origin: tuple[float, float, float] | None = None
        seen = 0
        removed = 0
        try:
            for chunk in reader.chunk_iterator(CHUNK_POINTS):
                size = len(chunk)
                first = (-seen) % stride
                seen += size
                picked = slice(first, size, stride)
                x = np.asarray(chunk.x, dtype=np.float64)[picked]
                y = np.asarray(chunk.y, dtype=np.float64)[picked]
                z = np.asarray(chunk.z, dtype=np.float64)[picked]
                cls = np.asarray(chunk.classification, dtype=np.uint8)[picked]
                keep = ~np.isin(cls, noise)
                removed += int((~keep).sum())
                if not keep.all():
                    x, y, z, cls = x[keep], y[keep], z[keep], cls[keep]
                if x.size == 0:
                    continue
                if origin is None:
                    origin = (float(x.min()), float(y.min()), float(z.min()))
                xs.append(((x - origin[0]) * unit_h).astype(np.float32))
                ys.append(((y - origin[1]) * unit_h).astype(np.float32))
                zs.append(((z - origin[2]) * unit_v).astype(np.float32))
                classes.append(cls)
        except ImportDataError:
            raise
        except Exception as exc:
            raise ImportDataError(
                "invalid_content",
                "the point cloud is damaged or truncated and could not be decoded",
            ) from exc
        if seen < count:
            warnings.append(f"The file ended after {seen:,} of {count:,} declared points.")
    finally:
        reader.close()
    if origin is None:
        raise ImportDataError("empty_cloud", "the point cloud holds no usable points")
    if removed:
        warnings.append(f"{removed:,} points classified as noise were ignored.")
    if crs is None:
        warnings.append(
            "The file has no coordinate system: it was analysed with coordinates and heights "
            "taken as metres. Tree positions are relative, so trees cannot be counted inside "
            "a plot."
        )
    return CloudData(
        x=np.concatenate(xs),
        y=np.concatenate(ys),
        z=np.concatenate(zs),
        classification=np.concatenate(classes),
        origin=origin,
        unit_h=unit_h,
        unit_v=unit_v,
        crs=crs,
        point_count=count,
        stride=stride,
        noise_removed=removed,
        fmt="laz" if header.are_points_compressed else "las",
        warnings=warnings,
    )


def pye57_available() -> bool:
    try:
        import pye57  # noqa: F401
    except ImportError:
        return False
    return True


def read_e57(data: bytes, params: PointCloudParams) -> CloudData:  # pragma: no cover - optional
    """Decode an E57 file with ``pye57`` (optional dependency). E57 carries no CRS here."""
    try:
        import pye57
    except ImportError as exc:
        raise UnsupportedFormatError(E57_ADVICE, code="e57_unsupported") from exc
    warnings: list[str] = []
    try:
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "upload.e57")
            with open(path, "wb") as handle:
                handle.write(data)
            scan_file = pye57.E57(path)
            parts = []
            for index in range(scan_file.scan_count):
                raw = scan_file.read_scan_raw(index)
                parts.append(
                    np.column_stack([raw["cartesianX"], raw["cartesianY"], raw["cartesianZ"]])
                )
    except Exception as exc:
        raise ImportDataError("invalid_content", "the E57 file could not be read") from exc
    cloud = np.concatenate(parts) if parts else np.zeros((0, 3))
    cloud = cloud[np.isfinite(cloud).all(axis=1)]
    if cloud.shape[0] == 0:
        raise ImportDataError("empty_cloud", "the point cloud holds no usable points")
    count = int(cloud.shape[0])
    stride = max(1, math.ceil(count / params.max_points))
    if stride > 1:
        cloud = cloud[::stride]
        warnings.append(f"Every {stride}th point was used to stay within {params.max_points:,}.")
    origin = (float(cloud[:, 0].min()), float(cloud[:, 1].min()), float(cloud[:, 2].min()))
    warnings.append(
        "E57 files carry no coordinate system here: the cloud was analysed in its own metres "
        "and trees cannot be counted inside a plot."
    )
    return CloudData(
        x=(cloud[:, 0] - origin[0]).astype(np.float32),
        y=(cloud[:, 1] - origin[1]).astype(np.float32),
        z=(cloud[:, 2] - origin[2]).astype(np.float32),
        classification=None,
        origin=origin,
        unit_h=1.0,
        unit_v=1.0,
        crs=None,
        point_count=count,
        stride=stride,
        noise_removed=0,
        fmt="e57",
        warnings=warnings,
    )
