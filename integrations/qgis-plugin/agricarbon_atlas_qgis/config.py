# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Plugin settings model and validation (pure Python, no QGIS imports).

The QGIS-specific storage (``QgsSettings``) lives in ``qgis_helpers.py``; this module only
knows how to normalise and validate the values so the rules can be unit-tested.
"""

from __future__ import annotations

import ipaddress
import math
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

DEFAULT_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_API_PATH = "/api/v1"
DEFAULT_TIMEOUT_S = 30.0
MIN_TIMEOUT_S = 1.0
MAX_TIMEOUT_S = 600.0
DEFAULT_COUNTRY = "IN"

# Mirror of ``member_states`` in config/regions/EU.yaml. The server stays the source of truth
# and answers 422 for a country it does not support; this list only feeds the drop-down.
EU_MEMBER_STATES = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DK": "Denmark",
    "EE": "Estonia",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LV": "Latvia",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MT": "Malta",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "ES": "Spain",
    "SE": "Sweden",
}
COUNTRY_NAMES = {"IN": "India", "US": "United States", **EU_MEMBER_STATES}
SUPPORTED_COUNTRIES = ("IN", "US", *sorted(EU_MEMBER_STATES))


class ConfigError(ValueError):
    """A setting is missing or invalid; the message is written for the end user."""


def country_label(code: str) -> str:
    """Human label for a drop-down, e.g. ``"DE - Germany (EU)"``."""
    name = COUNTRY_NAMES.get(code, code)
    suffix = " (EU)" if code in EU_MEMBER_STATES else ""
    return f"{code} - {name}{suffix}"


def is_loopback_host(host: str) -> bool:
    """True for ``localhost`` and loopback IP literals (no traffic leaves the machine)."""
    name = host.strip().strip("[]").lower()
    if name == "localhost" or name.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def normalize_base_url(raw: object) -> str:
    """Validate and normalise the API base URL.

    * only ``http`` and ``https`` are accepted (never ``file:`` or ``ftp:``);
    * credentials, query strings and fragments are rejected;
    * trailing slashes are removed;
    * a bare ``http://host:port`` gets the default ``/api/v1`` path appended.
    """
    text = str(raw or "").strip()
    if not text:
        raise ConfigError("The API base URL is empty.")
    try:
        parts = urlsplit(text)
        host = parts.hostname
        _ = parts.port  # raises ValueError for an invalid port
    except ValueError:
        raise ConfigError("The API base URL is not a valid URL.") from None
    if parts.scheme.lower() not in ("http", "https"):
        raise ConfigError("The API base URL must start with http:// or https://.")
    if not host:
        raise ConfigError("The API base URL has no host name.")
    if parts.username is not None or parts.password is not None:
        raise ConfigError("Do not put credentials in the URL; use the API key field instead.")
    if parts.query or parts.fragment:
        raise ConfigError("The API base URL must not contain a query string or a fragment.")
    path = parts.path.rstrip("/") or DEFAULT_API_PATH
    return urlunsplit((parts.scheme.lower(), parts.netloc, path, "", ""))


def is_insecure_remote(base_url: str) -> bool:
    """True when the URL uses plain http to a host that is not on this machine."""
    parts = urlsplit(base_url)
    return parts.scheme.lower() == "http" and not is_loopback_host(parts.hostname or "")


def normalize_country(raw: object) -> str:
    code = str(raw or "").strip().upper()
    if code not in SUPPORTED_COUNTRIES:
        raise ConfigError(
            f"Country {code or '(empty)'} is not supported; use IN, US or an EU member state code."
        )
    return code


def normalize_timeout(raw: object) -> float:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ConfigError("The timeout must be a number of seconds.") from None
    if not math.isfinite(value) or not MIN_TIMEOUT_S <= value <= MAX_TIMEOUT_S:
        raise ConfigError(
            f"The timeout must be between {MIN_TIMEOUT_S:g} and {MAX_TIMEOUT_S:g} seconds."
        )
    return value


def normalize_api_key(raw: object) -> str:
    """Strip whitespace and refuse characters that cannot travel in an HTTP header."""
    key = str(raw or "").strip()
    if key and (not key.isascii() or not key.isprintable()):
        raise ConfigError("The API key may only contain printable ASCII characters.")
    return key


@dataclass(frozen=True)
class PluginConfig:
    """Validated plugin settings. ``repr`` never shows the API key."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str = field(default="", repr=False)
    default_country: str = DEFAULT_COUNTRY
    timeout_s: float = DEFAULT_TIMEOUT_S

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def validate_settings(
    base_url: object, api_key: object, default_country: object, timeout: object
) -> tuple[PluginConfig | None, list[str]]:
    """Validate raw dialog input. Returns ``(config, [])`` or ``(None, [error, ...])``."""
    errors: list[str] = []
    values: dict[str, object] = {}
    for name, normalizer, raw in (
        ("base_url", normalize_base_url, base_url),
        ("api_key", normalize_api_key, api_key),
        ("default_country", normalize_country, default_country),
        ("timeout_s", normalize_timeout, timeout),
    ):
        try:
            values[name] = normalizer(raw)
        except ConfigError as exc:
            errors.append(str(exc))
    if errors:
        return None, errors
    return PluginConfig(**values), []  # type: ignore[arg-type]


def coerce_config(
    base_url: object = None,
    api_key: object = None,
    default_country: object = None,
    timeout: object = None,
) -> PluginConfig:
    """Lenient variant used when reading stored settings: bad values fall back to defaults."""
    defaults = PluginConfig()
    values: dict[str, object] = {}
    for name, normalizer, raw, fallback in (
        ("base_url", normalize_base_url, base_url, defaults.base_url),
        ("api_key", normalize_api_key, api_key, defaults.api_key),
        ("default_country", normalize_country, default_country, defaults.default_country),
        ("timeout_s", normalize_timeout, timeout, defaults.timeout_s),
    ):
        try:
            values[name] = normalizer(raw)
        except ConfigError:
            values[name] = fallback
    return PluginConfig(**values)  # type: ignore[arg-type]
