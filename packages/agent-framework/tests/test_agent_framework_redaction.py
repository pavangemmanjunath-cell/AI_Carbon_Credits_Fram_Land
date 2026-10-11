"""Redaction: what may leave the process or appear in a transcript."""

from __future__ import annotations

import pytest

from carboncreditbuy_agents.llm.redaction import (
    MASK,
    find_coordinates,
    looks_like_position,
    redact,
    redact_text,
)


def test_redact_drops_location_and_identity_keys_at_any_depth():
    payload = {
        "area_hectares": 2.13,
        "Name": "Ramesh's farm",
        "plot": {
            "geometry": {"type": "Polygon", "coordinates": [[[77.53, 13.29]]]},
            "centroid": {"lat": 13.29, "lon": 77.53},
            "region": "Karnataka",
            "owner": {"email": "a@b.org", "phone": "+91 98765 43210"},
        },
        "history": [{"bbox": [77.5, 13.2, 77.6, 13.3], "ndvi": 0.63}],
        "note": "pin at 13.2923, 77.5384",
    }
    assert redact(payload) == {
        "area_hectares": 2.13,
        "plot": {"region": "Karnataka"},
        "history": [{"ndvi": 0.63}],
        "note": f"pin at {MASK}",
    }


def test_positions_are_masked_but_ordinary_pairs_are_kept():
    assert looks_like_position([77.538399, 13.292298])
    assert not looks_like_position([0.2, 1.5])  # a parameter clamp
    assert not looks_like_position([2023, 2024])  # years
    assert not looks_like_position([77.538399, 13.292298, 5, 6])
    assert redact({"center": [77.538399, 13.292298], "clamp": [0.2, 1.5]}) == {
        "center": MASK,
        "clamp": [0.2, 1.5],
    }


@pytest.mark.parametrize(
    "text",
    [
        "13.2923, 77.5384",
        "13.2923 77.5384",
        "-33.8688;151.2093",
        "13.29N 77.53E",
        "13°17'40\"N 77°32'25\"E",
        "13.29° N",
        "lat: 13.29",
        "longitude=77.53",
    ],
)
def test_coordinate_patterns_are_found_and_masked(text: str):
    assert find_coordinates(text), text
    masked = redact_text(f"my farm is at {text} near the river")
    assert MASK in masked and "13.29" not in masked and "77.53" not in masked


@pytest.mark.parametrize(
    "text",
    [
        "Estimated removal is 7.7–14.3 tCO₂e per year (central 11.0).",
        "Your plot is 2.13 ha (5.26 acres) in Karnataka, India.",
        "NDVI 0.63, NDMI 0.23, mean annual temperature 24.0 °C.",
        "About ₹12,122 per year at ₹1,100 per tCO₂e (as of 2026-10-05).",
        "Evidence readiness is 55/100.",
    ],
)
def test_ordinary_numbers_are_left_alone(text: str):
    assert find_coordinates(text) == []
    assert redact_text(text) == text


def test_contact_details_are_masked_in_text():
    masked = redact_text("Write to farmer@example.org or call +91 98765 43210.")
    assert "farmer@" not in masked and "98765" not in masked
