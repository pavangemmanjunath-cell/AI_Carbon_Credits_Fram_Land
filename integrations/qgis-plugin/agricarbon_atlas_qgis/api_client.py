# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Minimal JSON client for the AgriCarbon Atlas REST API (standard library only).

Contract: docs/architecture/api-contract.md (base path ``/api/v1``, snake_case JSON, errors as
RFC 7807 ``application/problem+json``, optional ``X-API-Key`` header).

Design rules that matter for users:

* **Privacy.** Request bodies, query strings and response bodies are never logged. Log lines
  carry the HTTP method, the path (plot ids only), the status and the duration.
* **Secrets.** The API key lives in a private attribute, is hidden from ``repr`` and is only
  ever sent to the configured server. Redirects are *not* followed, so the key and the polygon
  cannot be forwarded to another host.
* **No blocking forever.** Every call has a timeout; long operations use a longer one.
* **Clear failures.** Every failure is an :class:`ApiError` subclass whose ``str()`` is a
  message that can be shown to the user.
"""

from __future__ import annotations

import http.client
import json
import logging
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any

from .config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT_S, ConfigError, is_loopback_host
from .config import normalize_base_url as _normalize_base_url
from .version import USER_AGENT

log = logging.getLogger(__name__)

#: Multiplier applied to the configured timeout for slow endpoints (analysis, agent runs).
LONG_TIMEOUT_FACTOR = 4.0
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
MAX_ERROR_BODY_BYTES = 1024 * 1024

#: ``source`` value sent with new plots (documented in the plugin README).
PLOT_SOURCE = "qgis-plugin"
#: Value the API accepted before ``qgis-plugin`` was added; used as a fallback on HTTP 422.
FALLBACK_PLOT_SOURCE = "api"

MEASUREMENT_SOURCES = (
    "user-reported",
    "satellite-derived",
    "government-data",
    "field-measured",
    "model-estimated",
)
POLICY_ACTIVITIES = (
    "tree_plantation",
    "agroforestry",
    "soil_carbon",
    "cropland_practice",
    "grazing",
)
MIN_PLANTATION_YEAR = 1900
MAX_PLANTATION_YEAR = 2100
MAX_TREE_COUNT = 10_000_000
_REDIRECT_CODES = (301, 302, 303, 307, 308)


# --------------------------------------------------------------------------- errors
class ApiError(Exception):
    """Base class of every client error. ``str(exc)`` is safe to show to the user."""


class ApiConfigError(ApiError):
    """The configured base URL (or another setting) cannot be used."""


class ApiConnectionError(ApiError):
    """The server could not be reached or did not answer in time.

    ``reason`` is one of ``timeout``, ``refused``, ``dns``, ``tls``, ``closed``, ``network``.
    """

    def __init__(self, message: str, reason: str = "network") -> None:
        super().__init__(message)
        self.reason = reason


class ApiResponseError(ApiError):
    """The server answered, but not with something this client understands."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class ApiProblem(ApiError):
    """An HTTP error response, parsed from RFC 7807 ``application/problem+json``.

    Attributes mirror the RFC members: ``status``, ``title``, ``detail``, ``type``,
    ``instance``. ``errors`` is the list of ``{"field", "message"}`` objects the Atlas API adds
    to 422 responses. ``request_id`` comes from ``X-Request-ID`` and ``retry_after`` from the
    ``Retry-After`` header (seconds) when present.
    """

    def __init__(
        self,
        status: int,
        title: str | None = None,
        detail: str | None = None,
        type_: str | None = None,
        instance: str | None = None,
        errors: Sequence[Mapping[str, str]] | None = None,
        request_id: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.status = int(status)
        self.title = title or _status_phrase(self.status)
        self.detail = detail or ""
        self.type = type_ or ""
        self.instance = instance or ""
        self.errors: list[dict[str, str]] = [dict(e) for e in (errors or [])]
        self.request_id = request_id or ""
        self.retry_after = retry_after
        super().__init__(self._compose())

    # -- construction ---------------------------------------------------------------------
    @classmethod
    def from_response(
        cls,
        status: int,
        body: bytes,
        headers: Mapping[str, str] | None = None,
        reason: str = "",
    ) -> ApiProblem:
        """Build a problem from an error response; tolerates non-JSON and odd shapes."""
        headers = headers or {}
        data: Any = None
        if body:
            try:
                data = json.loads(body.decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError):
                data = None
        title = detail = type_ = instance = None
        errors: list[dict[str, str]] = []
        if isinstance(data, Mapping):
            title = _text(data.get("title"))
            type_ = _text(data.get("type"))
            instance = _text(data.get("instance"))
            raw_detail = data.get("detail")
            if isinstance(raw_detail, list):  # FastAPI's default validation shape
                for item in raw_detail:
                    if isinstance(item, Mapping):
                        loc = ".".join(str(p) for p in item.get("loc") or [] if p != "body")
                        errors.append({"field": loc, "message": _text(item.get("msg")) or ""})
            else:
                detail = _text(raw_detail)
            raw_errors = data.get("errors")
            if isinstance(raw_errors, list):
                for item in raw_errors:
                    if isinstance(item, Mapping):
                        errors.append(
                            {
                                "field": _text(item.get("field")) or "",
                                "message": _text(item.get("message")) or "",
                            }
                        )
        return cls(
            status,
            title=title or reason or None,
            detail=detail,
            type_=type_,
            instance=instance,
            errors=errors,
            request_id=_header(headers, "X-Request-ID"),
            retry_after=_retry_after(_header(headers, "Retry-After")),
        )

    # -- helpers ----------------------------------------------------------------------------
    @property
    def type_slug(self) -> str:
        """Last path segment of the problem ``type`` URI, e.g. ``plot-not-found``."""
        return self.type.rstrip("/").rsplit("/", 1)[-1] if self.type else ""

    def mentions_field(self, name: str) -> bool:
        """True when a 422 field error points at ``name`` (or one of its sub-fields)."""
        prefix = name + "."
        return any(
            e.get("field") == name or e.get("field", "").startswith(prefix) for e in self.errors
        )

    def safe_summary(self) -> str:
        """A short string for logs: never includes the detail text (it may echo user input)."""
        slug = self.type_slug or self.title
        return f"HTTP {self.status} {slug}".strip()

    def plain_message(self) -> str:
        """Detail and field errors without the ``HTTP <status> <title>`` prefix (for dialogs)."""
        text = self.detail or self.title
        fields = self._field_summary()
        return f"{text} ({fields})" if fields else text

    def _field_summary(self) -> str:
        return "; ".join(
            f"{e['field']}: {e['message']}" if e.get("field") else e.get("message", "")
            for e in self.errors
            if e.get("field") or e.get("message")
        )

    def _compose(self) -> str:
        text = f"HTTP {self.status} {self.title}"
        if self.detail:
            text += f": {self.detail}"
        fields = self._field_summary()
        if fields:
            text += f" ({fields})"
        return text


def _status_phrase(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:2000]


def _header(headers: Mapping[str, str], name: str) -> str:
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return ""


def _retry_after(value: str) -> float | None:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    return seconds if seconds >= 0 else None


# --------------------------------------------------------------------------- transport
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: they could forward the API key and the polygon elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _build_opener(base_url: str) -> urllib.request.OpenerDirector:
    handlers: list[Any] = [_NoRedirect()]
    host = urllib.parse.urlsplit(base_url).hostname or ""
    if is_loopback_host(host):
        # Traffic to this machine must never be routed through a corporate proxy.
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


def _origin_of(parts: urllib.parse.SplitResult) -> str:
    return f"{parts.scheme}://{parts.netloc}"


def _origin(base_url: str) -> str:
    return _origin_of(urllib.parse.urlsplit(base_url))


def _segment(value: Any, what: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{what} must not be empty.")
    return urllib.parse.quote(text, safe="")


class AtlasClient:
    """Typed convenience wrapper around :meth:`request` for the endpoints the plugin uses."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "",
        timeout_s: float = DEFAULT_TIMEOUT_S,
        *,
        opener: Any = None,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        try:
            self.base_url = _normalize_base_url(base_url)
        except ConfigError as exc:
            raise ApiConfigError(str(exc)) from exc
        self._api_key = str(api_key or "").strip()
        self.timeout_s = float(timeout_s)
        self.max_response_bytes = int(max_response_bytes)
        self._opener = opener if opener is not None else _build_opener(self.base_url)

    def __repr__(self) -> str:
        key = "set" if self._api_key else "unset"
        return f"AtlasClient(base_url={self.base_url!r}, api_key={key}, timeout={self.timeout_s})"

    @property
    def long_timeout_s(self) -> float:
        return self.timeout_s * LONG_TIMEOUT_FACTOR

    # ------------------------------------------------------------------ low level
    def request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        params: Mapping[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> Any:
        """Send one request and return the decoded JSON (``None`` for an empty body).

        Raises :class:`ApiProblem` for HTTP errors, :class:`ApiConnectionError` when the
        server is unreachable or too slow and :class:`ApiResponseError` for unusable answers.
        """
        if not path.startswith("/"):
            raise ValueError("path must start with '/'")
        url = self.base_url + path
        if params:
            query = [(k, str(v)) for k, v in params.items() if v is not None]
            if query:
                url += "?" + urllib.parse.urlencode(query)
        headers = {
            "Accept": "application/json, application/problem+json",
            "User-Agent": USER_AGENT,
        }
        payload: bytes | None = None
        if body is not None:
            text = json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            payload = text.encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        verb = method.upper()
        timeout = float(timeout_s if timeout_s is not None else self.timeout_s)
        req = urllib.request.Request(url, data=payload, headers=headers, method=verb)
        started = time.monotonic()
        try:
            status, result = self._send(req, timeout)
        except ApiError as exc:
            log.warning("%s %s failed: %s", verb, path, _log_reason(exc))
            raise
        elapsed_ms = int((time.monotonic() - started) * 1000)
        log.info("%s %s -> %s (%d ms)", verb, path, status, elapsed_ms)
        return result

    def _send(self, req: urllib.request.Request, timeout: float) -> tuple[int, Any]:
        try:
            with self._opener.open(req, timeout=timeout) as response:
                status = int(getattr(response, "status", None) or response.getcode())
                raw = self._read_limited(response, self.max_response_bytes)
        except urllib.error.HTTPError as err:
            raise self._http_error(err) from None
        except urllib.error.URLError as err:
            raise self._connection_error(err.reason, timeout) from None
        except (TimeoutError, socket.timeout) as err:
            raise self._connection_error(err, timeout) from None
        except (OSError, http.client.HTTPException) as err:
            raise self._connection_error(err, timeout) from None
        if not raw.strip():
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            ctype = self._content_type(response)
            raise ApiResponseError(
                "The server answered with something that is not JSON"
                + (f" (content type {ctype})" if ctype else "")
                + ". Check the API base URL in Settings; it should end with /api/v1.",
                status=status,
            ) from None

    @staticmethod
    def _content_type(response: Any) -> str:
        try:
            return str(response.headers.get("Content-Type", "")).split(";")[0].strip()
        except Exception:  # header access must never mask the real error
            return ""

    @staticmethod
    def _read_limited(response: Any, limit: int) -> bytes:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ApiResponseError(
                f"The server response is larger than the limit of {_human_bytes(limit)}."
            )
        return raw

    def _http_error(self, err: urllib.error.HTTPError) -> ApiError:
        try:
            if err.code in _REDIRECT_CODES:
                location = urllib.parse.urlsplit(
                    err.headers.get("Location", "") if err.headers else ""
                )
                where = f" to {_origin_of(location)}" if location.scheme and location.netloc else ""
                return ApiResponseError(
                    f"The server redirected the request{where} (HTTP {err.code}) and the plugin "
                    "does not follow redirects. Correct the API base URL in Settings (for example "
                    "use https:// instead of http://).",
                    status=err.code,
                )
            body = err.read(MAX_ERROR_BODY_BYTES)
            return ApiProblem.from_response(
                err.code, body, dict(err.headers or {}), str(err.reason or "")
            )
        except OSError:
            return ApiProblem(err.code, title=str(err.reason or ""))
        finally:
            err.close()

    def _connection_error(self, reason: Any, timeout: float) -> ApiConnectionError:
        origin = _origin(self.base_url)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return ApiConnectionError(
                f"No answer from {origin} within {timeout:g} seconds. The server may be busy; "
                "raise the timeout in Settings or try again.",
                reason="timeout",
            )
        if isinstance(reason, ssl.SSLError):
            return ApiConnectionError(
                f"The secure connection to {origin} failed ({_short(reason)}). Check the "
                "certificate of the server or use the URL it is issued for.",
                reason="tls",
            )
        if isinstance(reason, socket.gaierror):
            return ApiConnectionError(
                f"The host name in {origin} could not be resolved. Check the API base URL in "
                "Settings.",
                reason="dns",
            )
        if isinstance(reason, ConnectionRefusedError):
            return ApiConnectionError(
                f"Could not connect to {origin}. Is the AgriCarbon Atlas API running, and is the "
                "API base URL in Settings correct?",
                reason="refused",
            )
        if isinstance(reason, (ConnectionError, http.client.HTTPException)):
            return ApiConnectionError(
                f"The connection to {origin} was closed unexpectedly. Try again.", reason="closed"
            )
        return ApiConnectionError(
            f"Could not reach {origin} ({type(reason).__name__}: {_short(reason)}).",
            reason="network",
        )

    # ------------------------------------------------------------------ endpoints
    def health(self, timeout_s: float | None = None) -> Any:
        """``GET /health`` -> ``{"status", "version", "mode", "time"}``."""
        return self.request("GET", "/health", timeout_s=timeout_s)

    def list_species(self, country: str | None = None) -> Any:
        """``GET /species?country=<ISO>`` -> list of species objects."""
        return self.request("GET", "/species", params={"country": country or None})

    def get_plot(self, plot_id: str) -> Any:
        """``GET /plots/{plot_id}`` -> Plot (owner view includes the geometry)."""
        return self.request("GET", f"/plots/{_segment(plot_id, 'plot_id')}")

    def create_plot(
        self,
        geometry: Mapping[str, Any],
        name: str,
        country: str | None = None,
        source: str = PLOT_SOURCE,
    ) -> Any:
        """``POST /plots`` with ``{name, country, source, geometry}``; ``country`` is optional."""
        body: dict[str, Any] = {"name": name}
        if country:
            body["country"] = country
        body["source"] = source
        body["geometry"] = dict(geometry)
        return self.request("POST", "/plots", body=body)

    def analyze_plot(
        self,
        plot_id: str,
        layers: Sequence[str] | None = None,
        years: Sequence[int] | None = None,
    ) -> Any:
        """``POST /plots/{plot_id}/analyze``; the body is optional (server defaults apply)."""
        body: dict[str, Any] = {}
        if layers:
            body["layers"] = list(layers)
        if years:
            body["years"] = [int(y) for y in years]
        return self.request(
            "POST",
            f"/plots/{_segment(plot_id, 'plot_id')}/analyze",
            body=body,
            timeout_s=self.long_timeout_s,
        )

    def create_tree_inventory(
        self,
        plot_id: str,
        species_id: str,
        tree_count: int,
        plantation_year: int,
        measurement_source: str = "model-estimated",
        survival_rate: float | None = None,
        average_dbh_cm: float | None = None,
        average_height_m: float | None = None,
    ) -> Any:
        """``POST /plots/{plot_id}/trees``. Optional measurements are omitted when ``None``."""
        species = str(species_id or "").strip()
        if not species:
            raise ValueError("species_id must not be empty.")
        if isinstance(tree_count, bool) or int(tree_count) != tree_count:
            raise ValueError("tree_count must be a whole number.")
        if not 1 <= int(tree_count) <= MAX_TREE_COUNT:
            raise ValueError(f"tree_count must be between 1 and {MAX_TREE_COUNT}.")
        if not MIN_PLANTATION_YEAR <= int(plantation_year) <= MAX_PLANTATION_YEAR:
            raise ValueError(
                f"plantation_year must be between {MIN_PLANTATION_YEAR} and {MAX_PLANTATION_YEAR}."
            )
        if measurement_source not in MEASUREMENT_SOURCES:
            raise ValueError(f"measurement_source must be one of {', '.join(MEASUREMENT_SOURCES)}.")
        body: dict[str, Any] = {
            "species_id": species,
            "tree_count": int(tree_count),
            "plantation_year": int(plantation_year),
            "measurement_source": measurement_source,
        }
        for key, value in (
            ("survival_rate", survival_rate),
            ("average_dbh_cm", average_dbh_cm),
            ("average_height_m", average_height_m),
        ):
            if value is not None:
                body[key] = float(value)
        return self.request("POST", f"/plots/{_segment(plot_id, 'plot_id')}/trees", body=body)

    def estimate_carbon(
        self, plot_id: str, inventory_id: str | None = None, model: str | None = None
    ) -> Any:
        """``POST /plots/{plot_id}/carbon-estimate``; both body fields are optional."""
        body: dict[str, Any] = {}
        if inventory_id:
            body["inventory_id"] = inventory_id
        if model:
            body["model"] = model
        return self.request(
            "POST", f"/plots/{_segment(plot_id, 'plot_id')}/carbon-estimate", body=body
        )

    def get_market_scenario(self, plot_id: str, estimate_id: str | None = None) -> Any:
        """``GET /plots/{plot_id}/market-scenario?estimate_id=...``."""
        return self.request(
            "GET",
            f"/plots/{_segment(plot_id, 'plot_id')}/market-scenario",
            params={"estimate_id": estimate_id or None},
        )

    def get_policy_eligibility(self, plot_id: str, activity: str = "tree_plantation") -> Any:
        """``GET /plots/{plot_id}/policy-eligibility?activity=...`` (screening only)."""
        if activity not in POLICY_ACTIVITIES:
            raise ValueError(f"activity must be one of {', '.join(POLICY_ACTIVITIES)}.")
        return self.request(
            "GET",
            f"/plots/{_segment(plot_id, 'plot_id')}/policy-eligibility",
            params={"activity": activity},
        )

    def run_agents(self, plot_id: str, plan: str = "full-assessment", locale: str = "en") -> Any:
        """``POST /plots/{plot_id}/agents/run`` with ``{"plan", "locale"}``."""
        return self.request(
            "POST",
            f"/plots/{_segment(plot_id, 'plot_id')}/agents/run",
            body={"plan": plan, "locale": locale},
            timeout_s=self.long_timeout_s,
        )


def _short(value: Any) -> str:
    return " ".join(str(value).split())[:160]


def _human_bytes(count: int) -> str:
    if count >= 1024 * 1024:
        return f"{count // (1024 * 1024)} MB"
    if count >= 1024:
        return f"{count // 1024} KB"
    return f"{count} bytes"


def _log_reason(exc: ApiError) -> str:
    """Describe an error for the log without echoing server-provided text."""
    if isinstance(exc, ApiProblem):
        return exc.safe_summary()
    if isinstance(exc, ApiConnectionError):
        return f"connection error ({exc.reason})"
    return type(exc).__name__
