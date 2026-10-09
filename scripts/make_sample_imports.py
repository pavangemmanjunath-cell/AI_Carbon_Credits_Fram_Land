#!/usr/bin/env python3
"""Regenerate ``data/sample/imports/*`` - SYNTHETIC files for trying "Import data".

Usage (from the repository root)::

    python3 scripts/make_sample_imports.py          # write the files
    python3 scripts/make_sample_imports.py --check  # exit 1 when a file is out of date

Everything is generated from fixed seeds around the synthetic demo plot ``PLT-DEMOIN``
(``data/sample/plots/india-mango-farm.json``), so the output is byte-for-byte reproducible.
Nothing here is a real farm, tree or survey. The files are released under CC0 1.0.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "geo-engine"))

from geo_engine.pointcloud.synthetic import make_orchard, to_las_bytes  # noqa: E402

PLOT_FILE = ROOT / "data" / "sample" / "plots" / "india-mango-farm.json"
OUT_DIR = ROOT / "data" / "sample" / "imports"
UTM_EPSG = 32643  # WGS 84 / UTM zone 43N (72-78 degrees east): the demo plot is near 77.54 E
SEED = 20261005
SPACING_M = 9.0  # planting grid of the synthetic orchard
JITTER_M = 1.2
GAP_SHARE = 0.08  # trees missing from the grid
CROWN_MARGIN_M = 3.4  # crowns stay this far inside the plot boundary
CLOUD_MARGIN_M = 12.0  # the point cloud extends a little beyond the plot (neighbour trees)
HEIGHT_RANGE_M = (3.0, 7.0)
CROWN_RADIUS_BASE_M = 1.0  # same crown model as the point cloud generator
CROWN_RADIUS_PER_HEIGHT = 0.25
CROWN_VERTICES = 14
LOW_SCORE_SHARE = 0.10
MAX_LAZ_BYTES = 3 * 1024 * 1024
LICENSE = "CC0-1.0"


def _load_plot() -> list[tuple[float, float]]:
    data = json.loads(PLOT_FILE.read_text(encoding="utf-8"))
    return [(float(lon), float(lat)) for lon, lat in data["geometry"]["coordinates"][0]]


def _fmt(value: float) -> str:
    return f"{value:.7f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------- boundary files
def make_kml(ring: list[tuple[float, float]]) -> bytes:
    coords = " ".join(f"{_fmt(lon)},{_fmt(lat)},0" for lon, lat in ring)
    text = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Demo orchard boundary (synthetic)</name>
    <description>Synthetic boundary around the demo plot PLT-DEMOIN. Not a real farm.
    License: {LICENSE}.</description>
    <Placemark>
      <name>Demo mango orchard (synthetic)</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>{coords}</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    return text.encode("utf-8")


def make_corners_csv(ring: list[tuple[float, float]]) -> bytes:
    lines = ["name,lat,lon"]
    for number, (lon, lat) in enumerate(ring[:-1], start=1):  # the ring repeats its first point
        lines.append(f"Corner {number},{_fmt(lat)},{_fmt(lon)}")
    return ("\n".join(lines) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------- orchard
class Orchard:
    """The synthetic planting: tree positions in UTM metres plus their heights."""

    def __init__(self, ring: list[tuple[float, float]]) -> None:
        self.to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{UTM_EPSG}", always_xy=True)
        self.to_lonlat = Transformer.from_crs(f"EPSG:{UTM_EPSG}", "EPSG:4326", always_xy=True)
        self.plot_utm = transform(self.to_utm.transform, Polygon(ring))
        rng = np.random.default_rng(SEED)
        west, south, east, north = self.plot_utm.bounds
        inner = self.plot_utm.buffer(-CROWN_MARGIN_M)
        outer_box = (
            west - CLOUD_MARGIN_M,
            south - CLOUD_MARGIN_M,
            east + CLOUD_MARGIN_M,
            north + CLOUD_MARGIN_M,
        )
        self.origin = (math.floor(outer_box[0]), math.floor(outer_box[1]))
        self.size_m = (
            math.ceil(outer_box[2] - self.origin[0]),
            math.ceil(outer_box[3] - self.origin[1]),
        )
        xs: list[float] = []
        ys: list[float] = []
        columns = np.arange(outer_box[0] + SPACING_M / 2, outer_box[2], SPACING_M)
        rows = np.arange(outer_box[1] + SPACING_M / 2, outer_box[3], SPACING_M)
        for y in rows:
            for x in columns:
                if rng.random() < GAP_SHARE:
                    continue
                jx, jy = rng.uniform(-JITTER_M, JITTER_M, size=2)
                xs.append(float(x + jx))
                ys.append(float(y + jy))
        self.tree_xy = np.column_stack([xs, ys])
        self.inner = inner

    def cloud(self) -> bytes:
        relative = self.tree_xy - np.array(self.origin, dtype=float)
        orchard = make_orchard(
            tree_xy=relative,
            origin=(float(self.origin[0]), float(self.origin[1])),
            size_m=(float(self.size_m[0]), float(self.size_m[1])),
            height_range_m=HEIGHT_RANGE_M,
            crown_radius_per_height=CROWN_RADIUS_PER_HEIGHT,
            crown_radius_base_m=CROWN_RADIUS_BASE_M,
            ground_points_per_m2=3.0,
            crown_points_per_m2=8.0,
            ground_elevation_m=915.0,
            classified=True,
            seed=SEED,
            epsg=UTM_EPSG,
        )
        self.heights = orchard.tree_height_m
        return to_las_bytes(orchard, compressed=True, epsg=UTM_EPSG)

    def crowns(self) -> bytes:
        """One polygon per tree whose whole crown lies inside the plot, with a ``score``."""
        rng = np.random.default_rng(SEED + 1)
        features: list[dict[str, Any]] = []
        for (x, y), height in zip(self.tree_xy, self.heights, strict=True):
            if not self.inner.contains(Point(x, y)):
                continue
            radius = CROWN_RADIUS_BASE_M + CROWN_RADIUS_PER_HEIGHT * float(height)
            angles = np.linspace(0.0, 2.0 * math.pi, CROWN_VERTICES, endpoint=False)
            radii = radius * rng.uniform(0.9, 1.1, size=CROWN_VERTICES)
            ring = [
                self.to_lonlat.transform(x + r * math.cos(a), y + r * math.sin(a))
                for a, r in zip(angles, radii, strict=True)
            ]
            ring.append(ring[0])
            if rng.random() < LOW_SCORE_SHARE:
                score = float(rng.uniform(0.2, 0.49))
            else:
                score = float(0.5 + 0.5 * rng.beta(6.0, 1.6))
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": len(features) + 1,
                        "class": "tree",
                        "score": round(score, 3),
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[round(lon, 7), round(lat, 7)] for lon, lat in ring]],
                    },
                }
            )
        head = {
            "type": "FeatureCollection",
            "name": "Demo tree crowns (synthetic)",
            "license": LICENSE,
            "description": (
                "Synthetic crown polygons with a score, shaped like the output of a tree-crown "
                "segmentation tool, inside the demo plot PLT-DEMOIN. Not real trees."
            ),
        }
        body = ",\n".join(json.dumps(f, separators=(",", ":")) for f in features)
        top = json.dumps(head, separators=(",", ":"))[:-1]
        return f'{top},"features":[\n{body}\n]}}\n'.encode()


def build_all() -> dict[str, bytes]:
    ring = _load_plot()
    orchard = Orchard(ring)
    laz = orchard.cloud()
    if len(laz) >= MAX_LAZ_BYTES:
        raise SystemExit(f"demo-orchard.laz is {len(laz)} bytes; the limit is {MAX_LAZ_BYTES}")
    return {
        "demo-boundary.kml": make_kml(ring),
        "demo-corners.csv": make_corners_csv(ring),
        "demo-crowns.geojson": orchard.crowns(),
        "demo-orchard.laz": laz,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="only verify the files are current")
    args = parser.parse_args()
    files = build_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, content in files.items():
        path = OUT_DIR / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content:
                stale.append(name)
            continue
        path.write_bytes(content)
        print(f"wrote {path.relative_to(ROOT)} ({len(content):,} bytes)")
    if stale:
        print("out of date: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
