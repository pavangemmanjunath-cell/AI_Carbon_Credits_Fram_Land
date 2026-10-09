"""Sentinel-2 L2A scene discovery via STAC (SpatioTemporal Asset Catalog).

Two public catalogues are supported; both expose collection ``sentinel-2-l2a``
but with different asset keys:

* **earth-search** (Element 84, AWS, no authentication)
  ``https://earth-search.aws.element84.com/v1`` — assets ``red`` (B04),
  ``nir`` (B08), ``swir16`` (B11), ``rededge1`` (B05), ``scl``; COGs in
  ``s3://sentinel-cogs`` (requester-pays off, public HTTPS).
* **copernicus** (Copernicus Data Space Ecosystem STAC)
  ``https://stac.dataspace.copernicus.eu/v1`` — asset keys follow the SAFE
  band naming (``B04_10m``, ``B08_10m``, ``B11_20m``, ``B05_20m``, ``SCL_20m``);
  downloading assets requires a CDSE access token. Keys are configurable
  because the catalogue is still evolving — verify against the live catalogue
  before relying on them.

Cloud filtering uses the ``eo:cloud_cover`` item property (percent). The
"best" scene of a period is the one with the lowest cloud cover; ties go to the
most recent acquisition.

``pystac_client`` is imported lazily inside :func:`search_scenes` so demo mode
and the unit tests never need it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from geo_engine.errors import GeoEngineError, MissingDependencyError

ASSET_ROLES = ("red", "nir", "swir16", "rededge", "scl")


@dataclass(frozen=True)
class StacProvider:
    """How to talk to one STAC catalogue."""

    id: str
    url: str
    collection: str = "sentinel-2-l2a"
    asset_keys: Mapping[str, str] = field(
        default_factory=lambda: {
            "red": "red",
            "nir": "nir",
            "swir16": "swir16",
            "rededge": "rededge1",
            "scl": "scl",
        }
    )
    cloud_property: str = "eo:cloud_cover"
    token: str | None = None
    #: Scale/offset to convert DN → reflectance when needed (L2A baseline ≥ 04.00)
    reflectance_scale: float = 1.0 / 10_000.0
    reflectance_offset_dn: float = -1000.0

    def with_overrides(self, **changes: Any) -> StacProvider:
        data = {**self.__dict__, **{k: v for k, v in changes.items() if v is not None}}
        return StacProvider(**data)


PROVIDERS: dict[str, StacProvider] = {
    "earth-search": StacProvider(
        id="earth-search", url="https://earth-search.aws.element84.com/v1"
    ),
    "copernicus": StacProvider(
        id="copernicus",
        url="https://stac.dataspace.copernicus.eu/v1",
        asset_keys={
            "red": "B04_10m",
            "nir": "B08_10m",
            "swir16": "B11_20m",
            "rededge": "B05_20m",
            "scl": "SCL_20m",
        },
    ),
}


@dataclass(frozen=True)
class Scene:
    """A Sentinel-2 acquisition relevant to a plot."""

    id: str
    datetime: datetime
    cloud_cover: float
    assets: Mapping[str, str]  # role → href
    provider: str
    properties: Mapping[str, Any] = field(default_factory=dict)

    @property
    def date(self) -> date:
        return self.datetime.date()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.id,
            "date": self.date.isoformat(),
            "cloud_cover": round(self.cloud_cover, 2),
            "provider": self.provider,
        }


def period_key(when: date | datetime, period: str = "month") -> str:
    """Return ``YYYY-MM`` (month) or ``YYYY`` (year) for grouping scenes."""
    if period == "month":
        return f"{when.year:04d}-{when.month:02d}"
    if period == "year":
        return f"{when.year:04d}"
    raise ValueError(f"unknown period {period!r}")


def best_scene_per_period(scenes: Iterable[Scene], period: str = "month") -> dict[str, Scene]:
    """Pick the lowest-cloud scene in each period (ties → most recent)."""
    best: dict[str, Scene] = {}
    for scene in scenes:
        key = period_key(scene.datetime, period)
        current = best.get(key)
        if (
            current is None
            or scene.cloud_cover < current.cloud_cover
            or (scene.cloud_cover == current.cloud_cover and scene.datetime > current.datetime)
        ):
            best[key] = scene
    return dict(sorted(best.items()))


def scene_from_item(item: Any, provider: StacProvider) -> Scene:
    """Build a :class:`Scene` from a pystac Item (or a plain STAC item dict)."""
    if isinstance(item, Mapping):
        item_id = str(item["id"])
        props = dict(item.get("properties", {}))
        assets = {k: v.get("href") for k, v in item.get("assets", {}).items()}
    else:  # pystac.Item
        item_id = str(item.id)
        props = dict(item.properties)
        assets = {k: a.href for k, a in item.assets.items()}
    stamp = props.get("datetime")
    if isinstance(stamp, str):
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    elif isinstance(stamp, datetime):
        when = stamp
    else:
        raise GeoEngineError(f"STAC item {item_id} has no datetime")
    cloud = float(props.get(provider.cloud_property, 100.0))
    hrefs = {
        role: assets[key]
        for role, key in provider.asset_keys.items()
        if key in assets and assets[key]
    }
    return Scene(
        id=item_id,
        datetime=when,
        cloud_cover=cloud,
        assets=hrefs,
        provider=provider.id,
        properties=props,
    )


def search_scenes(
    provider: StacProvider,
    geometry: dict[str, Any],
    start: date,
    end: date,
    max_cloud_cover_pct: float = 20.0,
    limit: int = 500,
) -> list[Scene]:
    """Search ``provider`` for scenes intersecting ``geometry`` between two dates.

    Requires ``pystac-client``. Results are filtered to ``eo:cloud_cover ≤ max``
    and sorted by acquisition time.
    """
    try:
        from pystac_client import Client
    except ImportError as exc:  # pragma: no cover - only without the live extra
        raise MissingDependencyError("pystac-client is required for live STAC search") from exc

    headers = {"Authorization": f"Bearer {provider.token}"} if provider.token else None
    client = Client.open(provider.url, headers=headers)
    search = client.search(
        collections=[provider.collection],
        intersects=geometry,
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={provider.cloud_property: {"lte": max_cloud_cover_pct}},
        max_items=limit,
    )
    scenes = [scene_from_item(item, provider) for item in search.items()]
    scenes = [s for s in scenes if s.cloud_cover <= max_cloud_cover_pct]
    scenes.sort(key=lambda s: s.datetime)
    return scenes
