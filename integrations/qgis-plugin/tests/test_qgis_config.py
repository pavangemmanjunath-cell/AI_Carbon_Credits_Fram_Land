# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Tests of the settings model: URL, key, country and timeout validation."""

from __future__ import annotations

from typing import Any

import pytest

from carboncreditbuy_qgis import config
from carboncreditbuy_qgis.config import (
    ConfigError,
    PluginConfig,
    coerce_config,
    normalize_api_key,
    normalize_base_url,
    normalize_country,
    normalize_timeout,
    validate_settings,
)


# --------------------------------------------------------------------------- base URL
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost:8000/api/v1", "http://localhost:8000/api/v1"),
        ("  http://localhost:8000/api/v1/  ", "http://localhost:8000/api/v1"),
        ("http://localhost:8000", "http://localhost:8000/api/v1"),
        ("http://localhost:8000/", "http://localhost:8000/api/v1"),
        ("HTTPS://Atlas.Example.org/api/v1", "https://Atlas.Example.org/api/v1"),
        ("https://atlas.example.org/custom/base", "https://atlas.example.org/custom/base"),
        ("http://[::1]:8000/api/v1", "http://[::1]:8000/api/v1"),
    ],
)
def test_base_urls_are_normalised(raw: str, expected: str) -> None:
    assert normalize_base_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        None,
        "localhost:8000",
        "ftp://example.org/api",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://",
        "http://user:secret@example.org/api/v1",
        "http://user@example.org/api/v1",
        "http://example.org/api/v1?key=1",
        "http://example.org/api/v1#frag",
        "http://example.org:99999/api/v1",
        "http://example.org:abc/api/v1",
    ],
)
def test_unusable_base_urls_are_refused_with_a_message(raw: Any) -> None:
    with pytest.raises(ConfigError) as caught:
        normalize_base_url(raw)
    assert str(caught.value)


def test_credentials_are_never_accepted_in_the_url() -> None:
    with pytest.raises(ConfigError, match="API key field"):
        normalize_base_url("https://user:pw@example.org")


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost", True),
        ("LOCALHOST", True),
        ("api.localhost", True),
        ("127.0.0.1", True),
        ("127.5.5.5", True),
        ("::1", True),
        ("[::1]", True),
        ("example.org", False),
        ("192.168.1.10", False),
        ("10.0.0.1", False),
        ("localhost.example.org", False),
        ("", False),
    ],
)
def test_loopback_detection(host: str, expected: bool) -> None:
    assert config.is_loopback_host(host) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://localhost:8000/api/v1", False),
        ("http://127.0.0.1:8000/api/v1", False),
        ("https://atlas.example.org/api/v1", False),
        ("http://atlas.example.org/api/v1", True),
        ("http://192.168.1.10:8000/api/v1", True),
    ],
)
def test_plain_http_to_another_computer_is_flagged(url: str, expected: bool) -> None:
    assert config.is_insecure_remote(url) is expected


# --------------------------------------------------------------------------- country
@pytest.mark.parametrize("code", ["IN", "US", "DE", "FR", "ES", "IT", "NL", "SE", "PL"])
def test_supported_countries(code: str) -> None:
    assert normalize_country(code) == code
    assert normalize_country(f"  {code.lower()} ") == code


@pytest.mark.parametrize("code", ["", None, "GB", "CN", "EU", "ZZ", "India", "+91", "D"])
def test_unsupported_countries_are_refused(code: Any) -> None:
    with pytest.raises(ConfigError):
        normalize_country(code)


def test_the_country_list_matches_the_mvp_regions() -> None:
    assert config.SUPPORTED_COUNTRIES[:2] == ("IN", "US")
    assert len(config.EU_MEMBER_STATES) == 27
    assert set(config.SUPPORTED_COUNTRIES) == {"IN", "US", *config.EU_MEMBER_STATES}
    assert all(len(code) == 2 and code.isupper() for code in config.SUPPORTED_COUNTRIES)
    assert config.country_label("DE") == "DE - Germany (EU)"
    assert config.country_label("IN") == "IN - India"
    assert config.country_label("XX") == "XX - XX"


# --------------------------------------------------------------------------- timeout
@pytest.mark.parametrize(("raw", "expected"), [(30, 30.0), ("45", 45.0), (1, 1.0), (600, 600.0)])
def test_valid_timeouts(raw: Any, expected: float) -> None:
    assert normalize_timeout(raw) == expected


@pytest.mark.parametrize("raw", [0, 0.5, -1, 601, 1e9, "abc", None, float("nan"), float("inf"), []])
def test_invalid_timeouts_are_refused(raw: Any) -> None:
    with pytest.raises(ConfigError):
        normalize_timeout(raw)


# --------------------------------------------------------------------------- API key
def test_api_key_is_trimmed_and_may_be_empty() -> None:
    assert normalize_api_key("  abc123  ") == "abc123"
    assert normalize_api_key("") == ""
    assert normalize_api_key(None) == ""


@pytest.mark.parametrize("raw", ["clé", "key\nwith newline", "tab\tkey", "ключ", "\x00"])
def test_api_keys_that_cannot_travel_in_a_header_are_refused(raw: str) -> None:
    with pytest.raises(ConfigError):
        normalize_api_key(raw)


# --------------------------------------------------------------------------- whole settings
def test_valid_settings_produce_a_config() -> None:
    cfg, errors = validate_settings("http://localhost:8000", " k ", "de", "20")
    assert errors == []
    assert cfg == PluginConfig("http://localhost:8000/api/v1", "k", "DE", 20.0)
    assert cfg is not None and cfg.has_api_key


def test_all_problems_are_reported_together() -> None:
    cfg, errors = validate_settings("ftp://x", "bad\nkey", "ZZ", "0")
    assert cfg is None
    assert len(errors) == 4


def test_repr_hides_the_api_key() -> None:
    cfg = PluginConfig(api_key="topsecret")
    assert "topsecret" not in repr(cfg)
    assert "api_key" not in repr(cfg)


def test_defaults_match_the_documented_values() -> None:
    cfg = PluginConfig()
    assert cfg.base_url == "http://localhost:8000/api/v1"
    assert cfg.api_key == "" and not cfg.has_api_key
    assert cfg.default_country == "IN"
    assert cfg.timeout_s == 30.0


def test_stored_values_that_became_invalid_fall_back_to_the_defaults() -> None:
    cfg = coerce_config("ftp://nope", "bad\nkey", "ZZ", "never")
    assert cfg == PluginConfig()
    mixed = coerce_config("https://atlas.example.org/api/v1", "key", "ZZ", 99)
    assert mixed == PluginConfig("https://atlas.example.org/api/v1", "key", "IN", 99.0)
    assert coerce_config() == PluginConfig()
