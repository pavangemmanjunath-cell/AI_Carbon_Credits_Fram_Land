"""Photon (komoot) geocoder adapter — OpenStreetMap data, GeoJSON responses.

* Search ``PHOTON_URL/api?q=…&limit=…&lang=en`` (optional ``bbox``), reverse
  ``PHOTON_URL/reverse?lat=…&lon=…``.
* The public instance (photon.komoot.io) asks for fair use (no heavy bulk
  traffic, identify yourself with a User-Agent); self-host for production.
* Data © OpenStreetMap contributors (ODbL 1.0); software Apache-2.0.
"""

from __future__ import annotations

from typing import Any

from atlas_integrations.base import Cache, HttpAdapter, MemoryTTLCache, SourceProvenance, cache_key
from atlas_integrations.geocoding_types import GeocodeResult, ReverseResult

SOURCE = SourceProvenance(
    id="osm-photon",
    name="Photon geocoder (komoot, OpenStreetMap data)",
    version=None,
    license="ODbL 1.0 (data) / Apache-2.0 (software)",
    attribution="© OpenStreetMap contributors",
    url="https://photon.komoot.io/",
)


def _from_feature(feature: dict[str, Any]) -> GeocodeResult:
    props = feature.get("properties") or {}
    lon, lat = feature["geometry"]["coordinates"][:2]
    name = props.get("name") or props.get("street") or ""
    parts = [p for p in (name, props.get("county"), props.get("state"), props.get("country")) if p]
    extent = props.get("extent")  # [min_lon, max_lat, max_lon, min_lat]
    bbox = [extent[0], extent[3], extent[2], extent[1]] if extent and len(extent) == 4 else None
    return GeocodeResult(
        label=", ".join(dict.fromkeys(parts)),
        lat=float(lat),
        lon=float(lon),
        bbox=bbox,
        country=(props.get("countrycode") or "").upper() or None,
        state=props.get("state"),
        district=props.get("county") or props.get("district") or props.get("city"),
    )


class PhotonAdapter(HttpAdapter):
    def __init__(self, base_url: str, cache: Cache | None = None, **kwargs: Any) -> None:
        super().__init__(cache=cache or MemoryTTLCache(), cache_ttl_s=86_400.0, **kwargs)
        self.base_url = base_url.rstrip("/")

    def search(self, query: str, country: str | None = None, limit: int = 5) -> list[GeocodeResult]:
        params: dict[str, Any] = {"q": query, "limit": max(1, min(limit, 10)), "lang": "en"}
        data = self.get_json(f"{self.base_url}/api", params=params)
        results = [_from_feature(f) for f in data.get("features", [])]
        if country:
            wanted = country.upper()
            results = [r for r in results if r.country == wanted] or results
        return results

    def reverse(self, lat: float, lon: float) -> ReverseResult:
        data = self.get_json(
            f"{self.base_url}/reverse",
            params={"lat": lat, "lon": lon, "lang": "en"},
            cache_ttl_s=86_400.0,
        )
        features = data.get("features") or []
        if not features:
            return ReverseResult(None, None, None, "")
        best = _from_feature(features[0])
        return ReverseResult(best.country, best.state, best.district, best.label)

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()

    @staticmethod
    def key_for(query: str) -> str:
        return cache_key("photon", query)
