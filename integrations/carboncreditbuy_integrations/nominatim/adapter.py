"""Nominatim (OpenStreetMap) geocoder adapter.

Usage policy (https://operations.osmfoundation.org/policies/nominatim/):
**max 1 request/second**, a **valid identifying User-Agent is mandatory**
(``NOMINATIM_USER_AGENT``), results must be cached, no bulk geocoding on the
public instance. This adapter enforces the User-Agent, throttles with
``GEOCODER_MIN_INTERVAL_SECONDS`` (process-wide lock) and caches results for
24 h. Self-hosted instances can relax these via constructor arguments.

Data © OpenStreetMap contributors, ODbL 1.0 — attribution
"© OpenStreetMap contributors" must be displayed.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from carboncreditbuy_integrations.base import (
    Cache,
    ConfigurationError,
    HttpAdapter,
    MemoryTTLCache,
    SourceProvenance,
    cache_key,
    demo_source,
)
from carboncreditbuy_integrations.demo_support import load_region_hints, region_for
from carboncreditbuy_integrations.geocoding_types import GeocodeResult, ReverseResult

SOURCE = SourceProvenance(
    id="osm-nominatim",
    name="Nominatim geocoder (OpenStreetMap data)",
    version=None,
    license="ODbL 1.0",
    attribution="© OpenStreetMap contributors",
    url="https://www.openstreetmap.org/copyright",
)
ATTRIBUTION = "© OpenStreetMap contributors"
_DISTRICT_KEYS = ("state_district", "district", "county", "city_district", "municipality", "city")
_STATE_KEYS = ("state", "region", "province", "state_district")


class _Throttle:
    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = min_interval_s
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._last + self.min_interval_s - now
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


def _admin(address: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    country = (address.get("country_code") or "").upper() or None
    state = next((address[k] for k in _STATE_KEYS if address.get(k)), None)
    district = next(
        (address[k] for k in _DISTRICT_KEYS if address.get(k) and address[k] != state), None
    )
    return country, state, district


class NominatimAdapter(HttpAdapter):
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        min_interval_s: float = 1.0,
        cache: Cache | None = None,
        cache_ttl_s: float = 86_400.0,
        **kwargs: Any,
    ) -> None:
        if not user_agent or not user_agent.strip() or "you@example.org" in user_agent:
            raise ConfigurationError(
                "NOMINATIM_USER_AGENT must identify your application and a contact "
                "(Nominatim usage policy)"
            )
        super().__init__(
            cache=cache or MemoryTTLCache(),
            cache_ttl_s=cache_ttl_s,
            user_agent=user_agent,
            **kwargs,
        )
        self.base_url = base_url.rstrip("/")
        self.throttle = _Throttle(min_interval_s)

    def _cached(self, key: str, fetch: Any) -> Any:
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        self.throttle.wait()
        value = fetch()
        if self.cache is not None:
            self.cache.set(key, value, self.cache_ttl_s)
        return value

    def search(self, query: str, country: str | None = None, limit: int = 5) -> list[GeocodeResult]:
        params: dict[str, Any] = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": max(1, min(limit, 10)),
        }
        if country:
            params["countrycodes"] = country.lower()
        key = cache_key("nominatim-search", self.base_url, params)

        def fetch() -> list[GeocodeResult]:
            response = self.request("GET", f"{self.base_url}/search", params=params)
            results: list[GeocodeResult] = []
            for item in response.json():
                bbox_raw = item.get("boundingbox")  # [south, north, west, east]
                bbox = None
                if bbox_raw and len(bbox_raw) == 4:
                    s, n, w, e = (float(v) for v in bbox_raw)
                    bbox = [w, s, e, n]
                c, st, d = _admin(item.get("address") or {})
                results.append(
                    GeocodeResult(
                        str(item.get("display_name", "")),
                        float(item["lat"]),
                        float(item["lon"]),
                        bbox,
                        c,
                        st,
                        d,
                    )
                )
            return results

        return self._cached(key, fetch)

    def reverse(self, lat: float, lon: float, zoom: int = 10) -> ReverseResult:
        params = {"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1, "zoom": zoom}
        key = cache_key("nominatim-reverse", self.base_url, round(lat, 4), round(lon, 4), zoom)

        def fetch() -> ReverseResult:
            response = self.request("GET", f"{self.base_url}/reverse", params=params)
            item = response.json()
            c, st, d = _admin(item.get("address") or {})
            return ReverseResult(c, st, d, str(item.get("display_name", "")))

        return self._cached(key, fetch)

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()


class DemoNominatimAdapter:
    """Offline geocoder: a few demo places plus region-bbox reverse lookup."""

    PLACES = [
        (
            "Doddaballapura, Bengaluru Rural, Karnataka, India",
            13.2923,
            77.5384,
            "IN",
            "Karnataka",
            "Bengaluru Rural",
        ),
        (
            "Macon, Bibb County, Georgia, United States",
            32.8407,
            -83.6324,
            "US",
            "Georgia",
            "Bibb County",
        ),
        ("Sevilla, Andalucía, España", 37.3891, -5.9845, "ES", "Andalucía", "Sevilla"),
        ("Dresden, Sachsen, Deutschland", 51.0504, 13.7373, "DE", "Sachsen", "Dresden"),
    ]

    def __init__(self) -> None:
        self.hints = load_region_hints()

    def search(self, query: str, country: str | None = None, limit: int = 5) -> list[GeocodeResult]:
        q = query.strip().lower()
        results = []
        for label, lat, lon, c, state, district in self.PLACES:
            if (
                country
                and c != country.upper()
                and not (country.upper() == "EU" and c in {"ES", "DE"})
            ):
                continue
            if (
                not q
                or any(part.strip().lower().startswith(q[:4]) for part in label.split(","))
                or q in label.lower()
            ):
                results.append(
                    GeocodeResult(
                        label,
                        lat,
                        lon,
                        [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05],
                        c,
                        state,
                        district,
                    )
                )
        return results[:limit]

    def reverse(self, lat: float, lon: float, zoom: int = 10) -> ReverseResult:
        hint = region_for(lat, lon, self.hints)
        if hint is None:
            return ReverseResult(None, None, None, "Demo location (outside configured regions)")
        label, state, district = hint.demo_place
        country = {"IN": "IN", "US": "US", "EU": "ES"}.get(hint.id, hint.id)
        return ReverseResult(country, state, district, label)

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
