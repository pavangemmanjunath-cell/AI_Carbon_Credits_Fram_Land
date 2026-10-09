"""geo_engine — geospatial primitives for AgriCarbon Atlas.

Sub-packages:

* ``geometry`` — polygon validation, geodesic measurement, privacy-safe
  centroid generalisation and plot-id generation.
* ``raster`` — ESA WorldCover class table, tile naming and masked reads.
* ``satellite`` — Sentinel-2 L2A STAC search helpers (pystac-client is
  imported lazily so demo mode never needs it).
* ``indices`` — NDVI/NDMI/NDRE, SCL cloud mask, plot statistics and the
  contract's index classes.
* ``climate`` — IPCC climate-zone decision tree (approximation).
* ``cube`` — the space-time cube (grid + demo generator + live builder).

Heavy dependencies (rasterio, pystac-client) are only imported inside the
functions that need them.
"""

from geo_engine.errors import GeoEngineError, GeometryError

__all__ = ["GeoEngineError", "GeometryError", "__version__"]
__version__ = "0.1.0"
