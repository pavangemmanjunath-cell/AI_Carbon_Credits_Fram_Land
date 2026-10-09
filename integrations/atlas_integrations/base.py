"""Shared plumbing for every adapter: typed errors, provenance records, a TTL
cache hook and an httpx wrapper with timeouts and one retry on 5xx/transport
errors.

Privacy: error messages never include request parameters (which may carry
coordinates) — only the host and status code.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx

DEFAULT_TIMEOUT_S = 20.0
DEFAULT_RETRIES = 1
DEFAULT_CACHE_TTL_S = 3600.0
USER_AGENT = "agricarbon-atlas/0.1 (+https://github.com/agricarbon-atlas)"


# --------------------------------------------------------------------------- errors
class AdapterError(Exception):
    """Base class for adapter failures."""


class ConfigurationError(AdapterError):
    """Missing API key / User-Agent / URL."""


class DependencyMissingError(AdapterError, ImportError):
    """An optional dependency (rasterio, pystac-client) is not installed."""


class UpstreamError(AdapterError):
    """The upstream service failed or could not be reached."""

    def __init__(
        self, message: str, *, status_code: int | None = None, host: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.host = host


class NotFoundError(UpstreamError):
    """Upstream returned 404 / an empty result where one was required."""


class RateLimitedError(UpstreamError):
    """Upstream returned 429."""


class UpstreamDataError(AdapterError):
    """Upstream answered but the payload could not be interpreted."""


# --------------------------------------------------------------------------- provenance
@dataclass(frozen=True)
class SourceProvenance:
    """Dataset-level provenance (mirrors ``provenance.schema.json#sources[]``)."""

    id: str
    name: str
    version: str | None
    license: str
    attribution: str
    url: str | None

    def to_dict(self, accessed_at: datetime | None = None, **extra: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "license": self.license,
            "attribution": self.attribution,
            "url": self.url,
            "accessed_at": (accessed_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        }
        data.update({k: v for k, v in extra.items() if v is not None})
        return data


def demo_source(base: SourceProvenance) -> SourceProvenance:
    """Provenance for a demo twin: clearly labelled synthetic, keeps the dataset it imitates."""
    return SourceProvenance(
        id="synthetic-demo",
        name=f"Synthetic demo data (imitating {base.name})",
        version=base.version,
        license="Apache-2.0 (generated)",
        attribution="AgriCarbon Atlas demo generator — not an observation",
        url=None,
    )


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# --------------------------------------------------------------------------- cache
class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl_s: float) -> None: ...


class MemoryTTLCache:
    """Small thread-safe in-memory TTL cache (per-process)."""

    def __init__(self, max_items: int = 2048) -> None:
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._max_items = max_items

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < time.monotonic():
                del self._items[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_s: float) -> None:
        with self._lock:
            if len(self._items) >= self._max_items:
                oldest = min(self._items.items(), key=lambda kv: kv[1][0])[0]
                del self._items[oldest]
            self._items[key] = (time.monotonic() + ttl_s, value)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def cache_key(*parts: Any) -> str:
    """Stable hash of the request identity (coordinates never appear in logs)."""
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Query parameters: a mapping, or (key, value) pairs when a key repeats
# (e.g. SoilGrids' `depth=0-5cm&depth=5-15cm`). httpx accepts both.
QueryParams = Mapping[str, Any] | Sequence[tuple[str, Any]]


# --------------------------------------------------------------------------- http
class HttpAdapter:
    """httpx wrapper with timeout, retry-once, optional cache and typed errors."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        cache: Cache | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        retries: int = DEFAULT_RETRIES,
        retry_backoff_s: float = 0.5,
        user_agent: str = USER_AGENT,
        cache_ttl_s: float = DEFAULT_CACHE_TTL_S,
    ) -> None:
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout_s, follow_redirects=True)
        self.cache = cache
        self.retries = retries
        self.retry_backoff_s = retry_backoff_s
        self.user_agent = user_agent
        self.cache_ttl_s = cache_ttl_s

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    # -- requests ------------------------------------------------------------
    def request(
        self,
        method: str,
        url: str,
        *,
        params: QueryParams | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
    ) -> httpx.Response:
        merged_headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        if headers:
            merged_headers.update(headers)
        host = urlsplit(url).netloc
        attempt = 0
        while True:
            try:
                response = self.client.request(
                    method, url, params=params, headers=merged_headers, json=json_body
                )
            except httpx.TransportError as exc:
                if attempt < self.retries:
                    attempt += 1
                    time.sleep(self.retry_backoff_s)
                    continue
                raise UpstreamError(f"{host}: {exc.__class__.__name__}", host=host) from exc
            if response.status_code >= 500 and attempt < self.retries:
                attempt += 1
                time.sleep(self.retry_backoff_s)
                continue
            return self._check(response, host)

    @staticmethod
    def _check(response: httpx.Response, host: str) -> httpx.Response:
        status = response.status_code
        if status == 404:
            raise NotFoundError(f"{host}: not found (404)", status_code=404, host=host)
        if status == 429:
            raise RateLimitedError(f"{host}: rate limited (429)", status_code=429, host=host)
        if status in (401, 403):
            raise ConfigurationError(f"{host}: authentication failed ({status}) — check API key")
        if status >= 400:
            raise UpstreamError(f"{host}: HTTP {status}", status_code=status, host=host)
        return response

    def get_json(
        self,
        url: str,
        *,
        params: QueryParams | None = None,
        headers: Mapping[str, str] | None = None,
        cache_ttl_s: float | None = None,
    ) -> Any:
        key = cache_key(url, params, headers and sorted(headers))
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        response = self.request("GET", url, params=params, headers=headers)
        try:
            data = response.json()
        except ValueError as exc:
            raise UpstreamDataError(f"{urlsplit(url).netloc}: response is not JSON") from exc
        if self.cache is not None:
            self.cache.set(key, data, cache_ttl_s if cache_ttl_s is not None else self.cache_ttl_s)
        return data
