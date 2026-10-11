# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Tests of the multi-call workflows against a local fake of the CarbonCreditBuy API."""

from __future__ import annotations

from typing import Any

import pytest
from qgis_plugin_fake_server import (
    Answer,
    FakeAtlasServer,
    RecordedRequest,
    json_answer,
    problem_answer,
)

from carboncreditbuy_qgis import geometry, workflows
from carboncreditbuy_qgis.api_client import ApiProblem, ApiResponseError, AtlasClient
from carboncreditbuy_qgis.workflows import SpeciesChoice

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[77.5, 13.2], [77.6, 13.2], [77.6, 13.3], [77.5, 13.3], [77.5, 13.2]]],
}
PLOT = {"plot_id": "PLT-1", "name": "Field", "country": "IN", "area_hectares": 3.5}


def client_for(server: FakeAtlasServer) -> AtlasClient:
    return AtlasClient(server.base_url, timeout_s=5)


# --------------------------------------------------------------------------- send polygon
def test_the_polygon_is_created_then_analysed(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots", status=201, payload=PLOT)
    atlas_server.route("POST", "/plots/PLT-1/analyze", payload={"mode": "demo"})
    result = workflows.send_field_polygon(client_for(atlas_server), POLYGON, "Field", "IN")
    assert result.plot == PLOT
    assert result.analysis == {"mode": "demo"}
    assert result.analysis_error is None and result.notes == []
    assert result.source_used == "qgis-plugin"
    assert [(r.method, r.path) for r in atlas_server.requests] == [
        ("POST", "/api/v1/plots"),
        ("POST", "/api/v1/plots/PLT-1/analyze"),
    ]
    assert atlas_server.requests[0].json == {
        "name": "Field",
        "country": "IN",
        "source": "qgis-plugin",
        "geometry": POLYGON,
    }


def _accept_only_known_sources(request: RecordedRequest) -> Answer:
    body = request.json
    if body["source"] == "qgis-plugin":
        return problem_answer(
            422,
            "Unprocessable Entity",
            "Request validation failed.",
            slug="validation-error",
            errors=[
                {
                    "field": "source",
                    "message": "Input should be 'manual-drawing', 'upload' or 'api'",
                }
            ],
        )
    return json_answer(201, {**PLOT, "source": body["source"]})


def test_servers_that_do_not_know_the_plugin_source_get_a_second_try_with_api(
    atlas_server: FakeAtlasServer,
) -> None:
    atlas_server.route("POST", "/plots", _accept_only_known_sources)
    atlas_server.route("POST", "/plots/PLT-1/analyze", payload={})
    result = workflows.send_field_polygon(client_for(atlas_server), POLYGON, "Field", None)
    assert result.source_used == "api"
    assert result.plot["source"] == "api"
    assert len(result.notes) == 1 and "qgis-plugin" in result.notes[0]
    posts = atlas_server.requests_to("POST", "/plots")
    assert [r.json["source"] for r in posts] == ["qgis-plugin", "api"]
    assert posts[0].json["geometry"] == posts[1].json["geometry"] == POLYGON


def test_other_validation_errors_are_not_retried(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "POST",
        "/plots",
        problem_answer(
            422,
            "Unprocessable Entity",
            "Self-intersecting ring.",
            slug="invalid-geometry",
            errors=[{"field": "geometry", "message": "self-intersection"}],
        ),
    )
    with pytest.raises(ApiProblem) as caught:
        workflows.send_field_polygon(client_for(atlas_server), POLYGON, "Field")
    assert caught.value.type_slug == "invalid-geometry"
    assert len(atlas_server.requests) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 500, 503])
def test_other_http_errors_are_raised_without_a_retry(
    atlas_server: FakeAtlasServer, status: int
) -> None:
    atlas_server.route("POST", "/plots", problem_answer(status, "Error"))
    with pytest.raises(ApiProblem) as caught:
        workflows.send_field_polygon(client_for(atlas_server), POLYGON, "Field")
    assert caught.value.status == status
    assert len(atlas_server.requests) == 1


def test_a_failing_analysis_keeps_the_plot_and_says_why(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots", status=201, payload=PLOT)
    atlas_server.route(
        "POST",
        "/plots/PLT-1/analyze",
        problem_answer(502, "Bad Gateway", slug="upstream-unavailable"),
    )
    result = workflows.send_field_polygon(client_for(atlas_server), POLYGON, "Field")
    assert result.plot == PLOT
    assert result.analysis is None
    assert result.analysis_error and "Try again later" in result.analysis_error


@pytest.mark.parametrize("created", [{}, {"plot_id": ""}, {"plot_id": 5}, ["PLT-1"], "PLT-1"])
def test_an_answer_without_a_plot_id_is_an_error(
    atlas_server: FakeAtlasServer, created: Any
) -> None:
    atlas_server.route("POST", "/plots", json_answer(201, created))
    with pytest.raises(ApiResponseError):
        workflows.send_field_polygon(client_for(atlas_server), POLYGON, "Field")
    assert len(atlas_server.requests) == 1  # no analysis for a plot we cannot name


# --------------------------------------------------------------------------- tree inventory
def test_the_inventory_is_recorded_as_model_estimated(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots/PLT-1/trees", status=201, payload={"inventory_id": "INV-1"})
    result = workflows.post_tree_inventory(client_for(atlas_server), "PLT-1", "mango", 118, 2019)
    assert result == {"inventory_id": "INV-1"}
    assert atlas_server.requests[0].json == {
        "species_id": "mango",
        "tree_count": 118,
        "plantation_year": 2019,
        "measurement_source": "model-estimated",
    }


def test_an_unknown_species_error_reaches_the_caller(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "POST",
        "/plots/PLT-1/trees",
        problem_answer(
            422, "Unprocessable Entity", "Unknown species_id 'zzz'.", slug="unknown-species"
        ),
    )
    with pytest.raises(ApiProblem) as caught:
        workflows.post_tree_inventory(client_for(atlas_server), "PLT-1", "zzz", 3, 2020)
    assert caught.value.type_slug == "unknown-species"


# --------------------------------------------------------------------------- carbon estimate
def test_the_estimate_is_followed_by_market_scenarios_and_programme_screening(
    atlas_server: FakeAtlasServer,
) -> None:
    atlas_server.route(
        "POST", "/plots/PLT-1/carbon-estimate", status=201, payload={"estimate_id": "EST-1"}
    )
    atlas_server.route("GET", "/plots/PLT-1/market-scenario", payload={"scenarios": []})
    atlas_server.route("GET", "/plots/PLT-1/policy-eligibility", payload={"programmes": []})
    result = workflows.estimate_carbon(client_for(atlas_server), "PLT-1", activity="agroforestry")
    assert result.estimate == {"estimate_id": "EST-1"}
    assert result.market == {"scenarios": []} and result.market_error is None
    assert result.policy == {"programmes": []} and result.policy_error is None
    assert atlas_server.requests_to("GET", "/plots/PLT-1/market-scenario")[0].query == {
        "estimate_id": ["EST-1"]
    }
    assert atlas_server.requests_to("GET", "/plots/PLT-1/policy-eligibility")[0].query == {
        "activity": ["agroforestry"]
    }
    assert atlas_server.requests_to("POST", "/plots/PLT-1/carbon-estimate")[0].json == {}


def test_missing_optional_parts_do_not_hide_the_estimate(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "POST", "/plots/PLT-1/carbon-estimate", status=201, payload={"estimate_id": "EST-1"}
    )
    atlas_server.route(
        "GET", "/plots/PLT-1/market-scenario", problem_answer(404, "Not Found", slug="no-route")
    )
    atlas_server.route("GET", "/plots/PLT-1/policy-eligibility", problem_answer(503, "Unavailable"))
    result = workflows.estimate_carbon(client_for(atlas_server), "PLT-1")
    assert result.estimate == {"estimate_id": "EST-1"}
    assert result.market is None and "could not find" in (result.market_error or "")
    assert result.policy is None and "Try again later" in (result.policy_error or "")


def test_a_failing_estimate_is_an_error(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route(
        "POST",
        "/plots/PLT-1/carbon-estimate",
        problem_answer(404, "Not Found", slug="inventory-missing"),
    )
    with pytest.raises(ApiProblem) as caught:
        workflows.estimate_carbon(client_for(atlas_server), "PLT-1")
    assert caught.value.type_slug == "inventory-missing"
    assert len(atlas_server.requests) == 1


# --------------------------------------------------------------------------- agent team
def test_the_agent_team_runs_the_full_assessment_in_english(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("POST", "/plots/PLT-1/agents/run", payload={"run_id": "R1", "messages": []})
    result = workflows.run_agent_team(client_for(atlas_server), "PLT-1")
    assert result["run_id"] == "R1"
    assert atlas_server.requests[0].json == {"plan": "full-assessment", "locale": "en"}


def test_older_servers_without_the_agent_team_answer_404(atlas_server: FakeAtlasServer) -> None:
    with pytest.raises(ApiProblem) as caught:  # no route registered: the fake answers 404
        workflows.run_agent_team(client_for(atlas_server), "PLT-1")
    assert caught.value.status == 404


@pytest.mark.parametrize("payload", [[], "ok", 5, None])
def test_an_agent_answer_that_is_not_an_object_is_an_error(
    atlas_server: FakeAtlasServer, payload: Any
) -> None:
    atlas_server.route("POST", "/plots/PLT-1/agents/run", json_answer(200, payload))
    with pytest.raises(ApiResponseError):
        workflows.run_agent_team(client_for(atlas_server), "PLT-1")


# --------------------------------------------------------------------------- plots
def test_fetch_plot_checks_the_answer(atlas_server: FakeAtlasServer) -> None:
    atlas_server.route("GET", "/plots/PLT-1", payload=PLOT)
    atlas_server.route("GET", "/plots/PLT-2", payload={"name": "no id"})
    assert workflows.fetch_plot(client_for(atlas_server), "PLT-1") == PLOT
    with pytest.raises(ApiResponseError):
        workflows.fetch_plot(client_for(atlas_server), "PLT-2")


def test_plot_fingerprint_matches_the_polygon_that_was_sent() -> None:
    sent = geometry.normalize_polygon(POLYGON)
    assert workflows.plot_fingerprint({"geometry": POLYGON}) == geometry.fingerprint(sent)
    multi = {"type": "MultiPolygon", "coordinates": [POLYGON["coordinates"]]}
    assert workflows.plot_fingerprint({"geometry": multi}) == geometry.fingerprint(sent)


@pytest.mark.parametrize(
    "plot", [{}, {"geometry": None}, {"geometry": {"type": "Point"}}, {"geometry": 5}]
)
def test_plot_fingerprint_is_none_without_a_usable_geometry(plot: dict[str, Any]) -> None:
    assert workflows.plot_fingerprint(plot) is None


# --------------------------------------------------------------------------- species
def test_species_choices_are_sorted_labelled_and_deduplicated() -> None:
    payload = [
        {
            "id": "teak",
            "common_name": "Teak",
            "scientific_name": "Tectona grandis",
            "max_density_per_ha": 2500,
        },
        {
            "id": "mango",
            "common_name": "Mango",
            "scientific_name": "Mangifera indica",
            "max_density_per_ha": 600,
        },
        {"id": "mango", "common_name": "Duplicate"},
        {"id": "neem", "common_name": "Neem"},
        {"id": "sal", "scientific_name": "Shorea robusta"},
        {"id": "bare"},
    ]
    assert workflows.species_choices(payload) == [
        SpeciesChoice("bare", "bare", None),
        SpeciesChoice("mango", "Mango (Mangifera indica)", 600.0),
        SpeciesChoice("neem", "Neem", None),
        SpeciesChoice("sal", "Shorea robusta", None),
        SpeciesChoice("teak", "Teak (Tectona grandis)", 2500.0),
    ]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        "mango",
        5,
        [],
        [None, 5, "x", [], {}],
        [{"common_name": "no id"}],
        [{"id": ""}, {"id": "  "}],
    ],
)
def test_species_choices_tolerate_garbage(payload: Any) -> None:
    assert workflows.species_choices(payload) == []


@pytest.mark.parametrize("maximum", [None, 0, -5, "abc", "", float("nan")])
def test_unusable_maximum_densities_are_ignored(maximum: Any) -> None:
    (choice,) = workflows.species_choices([{"id": "x", "max_density_per_ha": maximum}])
    assert choice.max_density_per_ha is None


# --------------------------------------------------------------------------- density note
def test_density_note_reports_trees_per_hectare() -> None:
    assert workflows.density_note(300, 3.0) == "About 100 trees per hectare on 3.00 ha."
    assert workflows.density_note(0, 3.0) == "About 0 trees per hectare on 3.00 ha."
    assert workflows.density_note(300, "3.0") == "About 100 trees per hectare on 3.00 ha."


def test_density_note_warns_above_the_species_maximum() -> None:
    below = workflows.density_note(300, 3.0, 600)
    assert "above" not in below
    above = workflows.density_note(3000, 3.0, 600)
    assert "above the 600 trees/ha" in above and "check the count" in above
    equal = workflows.density_note(1800, 3.0, 600)
    assert "above" not in equal


@pytest.mark.parametrize("area", [None, 0, -1, "abc", float("nan")])
def test_density_note_is_empty_without_a_usable_area(area: Any) -> None:
    assert workflows.density_note(100, area, 600) == ""
    assert workflows.density_note(-1, 3.0) == ""
