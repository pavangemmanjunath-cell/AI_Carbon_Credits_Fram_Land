# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Tests of the plugin's HTTP client against a local fake of the CarbonCreditBuy API."""

from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.request
from typing import Any

import pytest
from qgis_plugin_fake_server import (
    Answer,
    FakeAtlasServer,
    json_answer,
    problem_answer,
)

from carboncreditbuy_qgis import api_client
from carboncreditbuy_qgis.api_client import (
    ApiConfigError,
    ApiConnectionError,
    ApiError,
    ApiProblem,
    ApiResponseError,
    AtlasClient,
)

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[77.5, 13.2], [77.6, 13.2], [77.6, 13.3], [77.5, 13.3], [77.5, 13.2]]],
}


def client_for(server: FakeAtlasServer, **kwargs: Any) -> AtlasClient:
    return AtlasClient(server.base_url, **kwargs)


# --------------------------------------------------------------------------- basics
def test_get_returns_json_and_sends_standard_headers(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/health", payload={"status": "ok", "version": "0.1.0"})
    result = client_for(atlas_server).health()
    assert result == {"status": "ok", "version": "0.1.0"}
    (request,) = atlas_server.requests
    assert "application/json" in request.headers["accept"]
    assert request.headers["user-agent"].startswith("CarbonCreditBuy-QGIS/")
    assert "x-api-key" not in request.headers
    assert request.body == b""


def test_api_key_is_sent_as_header_only_when_configured(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/health", payload={})
    client_for(atlas_server, api_key="  secret-key  ").health()
    client_for(atlas_server).health()
    with_key, without_key = atlas_server.requests
    assert with_key.headers["x-api-key"] == "secret-key"
    assert "x-api-key" not in without_key.headers


def test_create_plot_sends_the_documented_body(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots", status=201, payload={"plot_id": "PLT-1"})
    result = client_for(atlas_server).create_plot(SQUARE, "North field", "IN")
    assert result == {"plot_id": "PLT-1"}
    (request,) = atlas_server.requests
    assert request.headers["content-type"] == "application/json"
    assert request.json == {
        "name": "North field",
        "country": "IN",
        "source": "qgis-plugin",
        "geometry": SQUARE,
    }


def test_create_plot_omits_the_country_when_the_server_should_detect_it(
    atlas_server: FakeAtlasServer,
) -> None:
    atlas_server.route("POST", "/plots", status=201, payload={"plot_id": "PLT-1"})
    client_for(atlas_server).create_plot(SQUARE, "Field", None, source="api")
    body = atlas_server.requests[0].json
    assert "country" not in body
    assert body["source"] == "api"


def test_non_ascii_names_survive_the_round_trip(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots", status=201, payload={})
    client_for(atlas_server).create_plot(SQUARE, "Würzburg Äcker 田", "DE")
    assert atlas_server.requests[0].json["name"] == "Würzburg Äcker 田"


def test_empty_success_body_returns_none(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/health", Answer(status=204))
    assert client_for(atlas_server).health() is None


def test_query_parameters_are_encoded_and_none_is_dropped(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/species", payload=[])
    atlas_server.route("GET", "/plots/PLT-1/market-scenario", payload={})
    client = client_for(atlas_server)
    client.list_species("IN")
    client.list_species(None)
    client.get_market_scenario("PLT-1")
    client.get_market_scenario("PLT-1", "EST 1&x")
    species_with, species_without, market_without, market_with = atlas_server.requests
    assert species_with.query == {"country": ["IN"]}
    assert species_without.query == {}
    assert market_without.query == {}
    assert market_with.query == {"estimate_id": ["EST 1&x"]}


def test_path_segments_are_quoted(atlas_server: FakeAtlasServer) -> None:
    client = client_for(atlas_server)
    with pytest.raises(ApiProblem):  # no route: 404, but the path is what we check
        client.get_plot("a/b c")
    assert atlas_server.requests[0].path == "/api/v1/plots/a%2Fb%20c"


@pytest.mark.parametrize("plot_id", ["", "   ", None])
def test_empty_plot_ids_are_rejected_before_any_request(
    atlas_server: FakeAtlasServer, plot_id: Any
) -> None:
    with pytest.raises(ValueError):
        client_for(atlas_server).get_plot(plot_id)
    assert atlas_server.requests == []


def test_path_must_start_with_a_slash(atlas_server: FakeAtlasServer) -> None:
    with pytest.raises(ValueError):
        client_for(atlas_server).request("GET", "health")


# --------------------------------------------------------------------------- endpoints
def test_tree_inventory_body(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots/PLT-1/trees", status=201, payload={"inventory_id": "INV-1"})
    client_for(atlas_server).create_tree_inventory("PLT-1", "mango", 120, 2019)
    assert atlas_server.requests[0].json == {
        "species_id": "mango",
        "tree_count": 120,
        "plantation_year": 2019,
        "measurement_source": "model-estimated",
    }


def test_tree_inventory_optional_measurements_are_sent_only_when_given(
    atlas_server: FakeAtlasServer,
) -> None:
    atlas_server.route("POST", "/plots/PLT-1/trees", status=201, payload={})
    client_for(atlas_server).create_tree_inventory(
        "PLT-1", "teak", 5, 2020, "field-measured", survival_rate=0.9, average_height_m=4.5
    )
    body = atlas_server.requests[0].json
    assert body["measurement_source"] == "field-measured"
    assert body["survival_rate"] == 0.9
    assert body["average_height_m"] == 4.5
    assert "average_dbh_cm" not in body


@pytest.mark.parametrize(
    ("species", "count", "year", "source"),
    [
        ("", 10, 2019, "model-estimated"),
        ("mango", 0, 2019, "model-estimated"),
        ("mango", -3, 2019, "model-estimated"),
        ("mango", 2.5, 2019, "model-estimated"),
        ("mango", True, 2019, "model-estimated"),
        ("mango", 10_000_001, 2019, "model-estimated"),
        ("mango", 10, 1899, "model-estimated"),
        ("mango", 10, 2101, "model-estimated"),
        ("mango", 10, 2019, "guess"),
    ],
)
def test_tree_inventory_rejects_invalid_input_before_sending(
    atlas_server: FakeAtlasServer, species: str, count: Any, year: int, source: str
) -> None:
    with pytest.raises(ValueError):
        client_for(atlas_server).create_tree_inventory("PLT-1", species, count, year, source)
    assert atlas_server.requests == []


def test_estimate_carbon_body_has_only_the_given_fields(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots/PLT-1/carbon-estimate", status=201, payload={})
    client = client_for(atlas_server)
    client.estimate_carbon("PLT-1")
    client.estimate_carbon("PLT-1", inventory_id="INV-1", model="tree-biomass-v0")
    first, second = atlas_server.requests
    assert first.json == {}
    assert second.json == {"inventory_id": "INV-1", "model": "tree-biomass-v0"}


def test_policy_eligibility_checks_the_activity(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/plots/PLT-1/policy-eligibility", payload={"programmes": []})
    client = client_for(atlas_server)
    client.get_policy_eligibility("PLT-1", "agroforestry")
    assert atlas_server.requests[0].query == {"activity": ["agroforestry"]}
    with pytest.raises(ValueError):
        client.get_policy_eligibility("PLT-1", "carbon_farming_miracle")


def test_run_agents_body(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots/PLT-1/agents/run", payload={"run_id": "R1"})
    client_for(atlas_server).run_agents("PLT-1")
    assert atlas_server.requests[0].json == {"plan": "full-assessment", "locale": "en"}


def test_analyze_sends_an_empty_object_by_default(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots/PLT-1/analyze", payload={})
    client = client_for(atlas_server)
    client.analyze_plot("PLT-1")
    client.analyze_plot("PLT-1", layers=["landcover"], years=[2023, 2024])
    first, second = atlas_server.requests
    assert first.json == {}
    assert second.json == {"layers": ["landcover"], "years": [2023, 2024]}


class _RecordingOpener:
    """Captures the timeout of each call instead of using the network."""

    def __init__(self) -> None:
        self.timeouts: list[float] = []

    def open(self, request: urllib.request.Request, timeout: float) -> Any:
        self.timeouts.append(timeout)
        raise urllib.error.URLError(ConnectionRefusedError("recorded"))


def test_slow_endpoints_use_the_longer_timeout() -> None:
    opener = _RecordingOpener()
    client = AtlasClient("http://localhost:8000", timeout_s=10, opener=opener)
    calls = [
        lambda: client.health(),
        lambda: client.create_plot(SQUARE, "x"),
        lambda: client.analyze_plot("P1"),
        lambda: client.run_agents("P1"),
    ]
    for call in calls:
        with pytest.raises(ApiError):
            call()
    assert opener.timeouts == [10.0, 10.0, 40.0, 40.0]


# --------------------------------------------------------------------------- errors
def test_problem_json_is_parsed(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "POST",
        "/plots",
        problem_answer(
            422,
            "Unprocessable Entity",
            "Request validation failed.",
            slug="validation-error",
            errors=[
                {"field": "source", "message": "Input should be 'manual-drawing'"},
                {"field": "geometry.coordinates", "message": "too few positions"},
            ],
            headers={"X-Request-ID": "req-42"},
        ),
    )
    with pytest.raises(ApiProblem) as caught:
        client_for(atlas_server).create_plot(SQUARE, "x")
    problem = caught.value
    assert problem.status == 422
    assert problem.title == "Unprocessable Entity"
    assert problem.detail == "Request validation failed."
    assert problem.type_slug == "validation-error"
    assert problem.request_id == "req-42"
    assert problem.mentions_field("source")
    assert problem.mentions_field("geometry")
    assert not problem.mentions_field("name")
    text = str(problem)
    assert "HTTP 422" in text and "Request validation failed." in text and "source:" in text
    assert problem.plain_message().startswith("Request validation failed.")
    assert "HTTP" not in problem.plain_message()


def test_fastapi_default_validation_detail_is_understood(atlas_server: FakeAtlasServer) -> None:
    body = {"detail": [{"loc": ["body", "source"], "msg": "Input should be 'api'", "type": "x"}]}
    atlas_server.route("POST", "/plots", json_answer(422, body))
    with pytest.raises(ApiProblem) as caught:
        client_for(atlas_server).create_plot(SQUARE, "x")
    assert caught.value.mentions_field("source")
    assert caught.value.errors == [{"field": "source", "message": "Input should be 'api'"}]


def test_a_non_json_error_page_becomes_a_clean_problem(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "GET",
        "/health",
        Answer(status=502, body=b"<html><body>Bad gateway: secret</body></html>"),
    )
    with pytest.raises(ApiProblem) as caught:
        client_for(atlas_server).health()
    assert caught.value.status == 502
    assert caught.value.detail == ""
    assert "secret" not in str(caught.value)


def test_retry_after_is_parsed_and_junk_is_ignored(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "GET", "/health", problem_answer(429, "Too Many Requests", headers={"Retry-After": "7"})
    )
    with pytest.raises(ApiProblem) as caught:
        client_for(atlas_server).health()
    assert caught.value.retry_after == 7.0
    atlas_server.route(
        "GET", "/health", problem_answer(429, "Too Many Requests", headers={"Retry-After": "soon"})
    )
    with pytest.raises(ApiProblem) as caught:
        client_for(atlas_server).health()
    assert caught.value.retry_after is None


@pytest.mark.parametrize("status", [401, 403, 404, 409, 500, 503])
def test_every_error_status_is_an_api_problem(atlas_server: FakeAtlasServer, status: int) -> None:
    atlas_server.route("GET", "/health", problem_answer(status, "Oops", "detail text"))
    with pytest.raises(ApiProblem) as caught:
        client_for(atlas_server).health()
    assert caught.value.status == status
    assert isinstance(caught.value, ApiError)


def test_a_non_json_success_body_points_at_the_base_url(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "GET", "/health", Answer(body=b"<html>login</html>", headers={"Content-Type": "text/html"})
    )
    with pytest.raises(ApiResponseError) as caught:
        client_for(atlas_server).health()
    message = str(caught.value)
    assert "not JSON" in message and "text/html" in message and "/api/v1" in message


def test_oversized_responses_are_refused(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/health", Answer(body=b"[" + b"1," * 400 + b"1]"))
    with pytest.raises(ApiResponseError, match="larger than"):
        client_for(atlas_server, max_response_bytes=100).health()


def test_redirects_are_not_followed_so_the_key_and_polygon_cannot_leak(
    atlas_server: FakeAtlasServer,
) -> None:
    other = FakeAtlasServer()
    try:
        other.route("POST", "/plots", status=201, payload={"plot_id": "LEAK"})
        atlas_server.route(
            "POST",
            "/plots",
            Answer(status=307, headers={"Location": f"{other.base_url}/plots"}),
        )
        with pytest.raises(ApiResponseError) as caught:
            client_for(atlas_server, api_key="secret").create_plot(SQUARE, "x")
        assert caught.value.status == 307
        assert "redirect" in str(caught.value).lower()
        assert other.requests == []
    finally:
        other.close()


def test_a_slow_server_gives_a_timeout_error(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/health", Answer(body=b"{}", delay_s=1.5))
    with pytest.raises(ApiConnectionError) as caught:
        client_for(atlas_server, timeout_s=0.3).health()
    assert caught.value.reason == "timeout"
    assert "0.3 seconds" in str(caught.value)


def test_a_closed_port_gives_a_connection_refused_error() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(ApiConnectionError) as caught:
        AtlasClient(f"http://127.0.0.1:{port}/api/v1", timeout_s=2).health()
    assert caught.value.reason == "refused"
    assert "Is the CarbonCreditBuy API running" in str(caught.value)


# --------------------------------------------------------------------------- construction
@pytest.mark.parametrize(
    "url",
    ["ftp://example.org/api", "file:///etc/passwd", "http://user:pw@example.org/api/v1", "", "x"],
)
def test_invalid_base_urls_are_refused(url: str) -> None:
    with pytest.raises(ApiConfigError):
        AtlasClient(url)


def test_a_bare_origin_gets_the_default_api_path() -> None:
    assert AtlasClient("http://localhost:8000").base_url == "http://localhost:8000/api/v1"
    assert AtlasClient("https://atlas.example/api/v1/").base_url == "https://atlas.example/api/v1"


def test_repr_never_shows_the_api_key() -> None:
    client = AtlasClient("http://localhost:8000", api_key="topsecret")
    assert "topsecret" not in repr(client)
    assert "api_key=set" in repr(client)


def test_loopback_traffic_bypasses_proxies(
    atlas_server: FakeAtlasServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configured proxy (here: a closed port) must not be used for the local server."""
    for name in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy"):
        monkeypatch.setenv(name, "http://127.0.0.1:1")
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    atlas_server.route("GET", "/health", payload={"status": "ok"})
    assert client_for(atlas_server).health() == {"status": "ok"}


def test_remote_hosts_still_honour_the_proxy_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("http_proxy", "http://proxy.invalid:3128")
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)

    def has_proxy_handler(url: str) -> bool:
        opener = api_client._build_opener(url)
        return any(isinstance(h, urllib.request.ProxyHandler) for h in opener.handlers)

    assert not has_proxy_handler("http://localhost:8000/api/v1")
    assert not has_proxy_handler("http://127.0.0.1:8000/api/v1")
    assert has_proxy_handler("http://atlas.example/api/v1")


def test_redirect_handler_refuses_everything() -> None:
    handler = api_client._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", {}, "http://elsewhere") is None


# --------------------------------------------------------------------------- privacy
def test_logs_never_contain_coordinates_bodies_keys_or_server_text(
    atlas_server: FakeAtlasServer, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="carboncreditbuy_qgis")
    secret_key = "key-9f8e7d6c"
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [[77.123456, 13.654321], [77.2, 13.654321], [77.2, 13.7], [77.123456, 13.654321]]
        ],
    }
    atlas_server.route("POST", "/plots", status=201, payload={"plot_id": "PLT-1", "note": "n"})
    atlas_server.route(
        "POST",
        "/plots/PLT-1/trees",
        problem_answer(422, "Unprocessable Entity", "Unknown species_id 'my-private-orchard'."),
    )
    client = client_for(atlas_server, api_key=secret_key)
    client.create_plot(polygon, "Ramesh private farm", "IN")
    with pytest.raises(ApiProblem):
        client.create_tree_inventory("PLT-1", "my-private-orchard", 3, 2020)
    with pytest.raises(ApiProblem):
        client.get_plot("PLT-404")

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "POST /plots" in logged  # something is logged ...
    for forbidden in (
        "77.123456",
        "13.654321",
        "Ramesh",
        "my-private-orchard",
        secret_key,
        "Unknown species",
    ):
        assert forbidden not in logged, forbidden


def test_problem_summary_for_logs_leaves_out_the_detail() -> None:
    problem = ApiProblem(
        422,
        title="Unprocessable Entity",
        detail="Unknown species_id 'my-private-orchard'.",
        type_="https://x/problems/unknown-species",
    )
    assert problem.safe_summary() == "HTTP 422 unknown-species"
    assert "orchard" not in problem.safe_summary()


def test_error_classes_share_one_base() -> None:
    for cls in (ApiConfigError, ApiConnectionError, ApiResponseError, ApiProblem):
        assert issubclass(cls, ApiError)


def test_json_helpers_do_not_crash_on_odd_payloads() -> None:
    """``from_response`` copes with bodies that are not objects."""
    for body in (b"", b"null", b"[]", b'"text"', b"\xff\xfe", b"{", b'{"detail": 5, "errors": 3}'):
        problem = ApiProblem.from_response(500, body, {})
        assert problem.status == 500
        assert json.dumps(str(problem))  # printable
