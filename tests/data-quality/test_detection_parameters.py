"""Data-quality gates on ``config/detection.yaml`` (point clouds, tree cover, vector imports).

Every tunable number must say where it comes from and how far it can be trusted
(CLAUDE.md principles 3 and 10). The numbers are project assumptions until calibrated locally, and
the file says so; a parameter that is still ``pending`` fails here, as it would in production.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from geo_engine.detection import load_detection_config

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "detection.yaml"
RAW = yaml.safe_load(PATH.read_text(encoding="utf-8"))
SECTIONS = ("point_cloud", "tree_cover", "vector_import")
STATUSES = {"verified", "assumption", "pending"}
FIELDS = {"value", "unit", "source", "verification_status"}
PARAMETERS = [(s, name, entry) for s in SECTIONS for name, entry in RAW[s].items()]


def test_the_file_has_a_version_a_date_and_the_three_sections():
    assert RAW["version"] and RAW["updated"]
    assert all(isinstance(RAW[section], dict) and RAW[section] for section in SECTIONS)


@pytest.mark.parametrize(
    "section, name, entry", PARAMETERS, ids=[f"{s}.{n}" for s, n, _ in PARAMETERS]
)
def test_every_parameter_has_value_unit_source_and_status(section, name, entry):
    assert set(entry) == FIELDS, (section, name)
    assert entry["unit"], (section, name)
    assert isinstance(entry["source"], str) and len(entry["source"]) > 20, (section, name)
    assert entry["verification_status"] in STATUSES, (section, name)
    if entry["verification_status"] == "assumption":
        assert entry["source"].startswith("project assumption"), (section, name)
    if entry["verification_status"] == "verified":
        assert "specification" in entry["source"].lower(), (section, name)  # a cited document


def test_no_parameter_is_pending():
    pending = [
        f"{s}.{n}" for s, n, entry in PARAMETERS if entry["verification_status"] == "pending"
    ]
    assert not pending, f"confirm or calibrate before shipping: {pending}"


def test_the_loader_accepts_the_file_and_reports_the_weakest_status():
    config = load_detection_config(ROOT / "config")
    for section in SECTIONS:
        assert config.weakest_status(section) in STATUSES
