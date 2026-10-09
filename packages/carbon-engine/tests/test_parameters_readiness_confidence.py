from __future__ import annotations

import pytest

from carbon_engine import (
    ParameterUsed,
    PendingParameterError,
    assert_production_safe,
    confidence_for_inventory,
    find_config_dir,
    score_readiness,
    worst_verification_status,
)
from carbon_engine.parameters import _class_matches
from carbon_engine.readiness import grade_for


def test_config_dir_is_found_and_contains_species():
    assert (find_config_dir() / "species" / "species.yaml").is_file()


def test_store_exposes_every_zone_and_species(store):
    zones = store.climate_zones()
    assert "tropical_dry" in zones and "boreal" in zones
    assert store.growth("tropical_dry").value == 4.0
    assert store.growth("tropical_dry").verification_status == "pending"
    assert store.constant("carbon_fraction").value == 0.47
    assert {s["id"] for s in store.species_list("IN")} >= {"mango", "teak", "neem"}
    assert all("EU" in s["regions"] for s in store.species_list("EU"))
    assert store.species("olive")["common_name"] == "Olive"


def test_root_to_shoot_class_selection(store):
    assert store.root_to_shoot("tropical_dry", 10).value == 0.56
    assert store.root_to_shoot("tropical_dry", 20).value == 0.28
    assert store.root_to_shoot("tropical_moist", 124.9).value == 0.20
    assert store.root_to_shoot("tropical_moist", 125).value == 0.24
    assert store.root_to_shoot("warm_temperate_moist", 74.9).value == 0.46
    assert store.root_to_shoot("warm_temperate_moist", 100).value == 0.23
    assert store.root_to_shoot("warm_temperate_moist", 150.1).value == 0.24
    assert store.root_to_shoot("boreal", 80).value == 0.24
    assert store.root_to_shoot("tropical_wet", 999).value == 0.37
    assert _class_matches("agb_75_150", 75) and _class_matches("agb_75_150", 150)
    assert not _class_matches("agb_gt_150", 150)
    with pytest.raises(ValueError):
        _class_matches("weird_key", 1.0)


def test_all_cited_parameters_have_sources(store):
    params = store.all_cited_parameters()
    assert len(params) > 40
    for p in params:
        assert p.source, p.name
        assert p.verification_status in {"verified", "pending", "assumption"}, p.name
    assert any(p.verification_status == "pending" for p in params)


def test_worst_status_and_production_guard():
    params = [
        ParameterUsed("a", 1, "", "x", "verified"),
        ParameterUsed("b", 1, "", "x", "assumption"),
    ]
    assert worst_verification_status(params) == "assumption"
    assert_production_safe(params, allow_pending=False)  # no pending → fine
    params.append(ParameterUsed("c", 1, "", "x", "pending"))
    assert worst_verification_status(params) == "pending"
    assert_production_safe(params, allow_pending=True)
    with pytest.raises(PendingParameterError) as excinfo:
        assert_production_safe(params, allow_pending=False)
    assert excinfo.value.names == ["c"]


def test_readiness_math(store):
    cfg = store.readiness_config
    total = sum(e["weight"] for e in cfg["evidence"])
    assert total == 116
    none = score_readiness({}, cfg)
    assert none.score == 0 and none.grade == "low" and len(none.missing_evidence) == 10
    everything = score_readiness({e["id"]: True for e in cfg["evidence"]}, cfg)
    assert everything.score == 100 and everything.grade == "high"
    partial = score_readiness(
        {"polygon": True, "tree_count": True, "species": True, "age": True, "satellite": True}, cfg
    )
    assert partial.score == round(100 * 64 / 116) == 55
    assert partial.grade == "medium"
    assert [e.id for e in partial.present_evidence] == [
        "polygon",
        "tree_count",
        "species",
        "age",
        "satellite",
    ]
    assert partial.missing_evidence[0].to_dict() == {
        "id": "dbh",
        "label": "Tree diameter measurements",
        "weight": 15,
    }
    assert grade_for(39, cfg["grades"]) == "low"
    assert grade_for(40, cfg["grades"]) == "medium"
    assert grade_for(69, cfg["grades"]) == "medium"
    assert grade_for(70, cfg["grades"]) == "high"


@pytest.mark.parametrize(
    "count, species, year, dbh, height, expected",
    [
        (420, "mango", 2023, 20.0, 8.0, "high"),
        (420, "mango", 2023, None, None, "medium"),
        (420, "mango", 2023, 20.0, None, "medium"),
        (420, None, 2023, 20.0, 8.0, "low"),
        (0, "mango", 2023, None, None, "low"),
        (420, "mango", None, None, None, "low"),
    ],
)
def test_confidence_rules(count, species, year, dbh, height, expected):
    confidence, fields = confidence_for_inventory(count, species, year, dbh, height, None)
    assert confidence == expected
    assert [f.name for f in fields] == [
        "tree_count",
        "species",
        "age",
        "dbh",
        "height",
        "mortality",
    ]
    assert fields[-1].status == "missing"
