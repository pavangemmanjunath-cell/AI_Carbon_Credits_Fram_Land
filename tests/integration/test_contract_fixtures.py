"""Contract check: the committed sample responses still match what the API produces.

Regenerate fixtures with ``python3 scripts/make_sample_responses.py`` after an
intentional contract change; this test fails on accidental drift of field names.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("ATLAS_MODE", "demo")
os.environ.setdefault("ATLAS_RATE_LIMIT_ENABLED", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "sample" / "responses"

ENDPOINTS = {
    "plot.json": "/api/v1/plots/PLT-DEMOIN",
    "analysis.json": "/api/v1/plots/PLT-DEMOIN/analysis",
    "carbon-estimate.json": "/api/v1/plots/PLT-DEMOIN/carbon-estimate",
    "policy-eligibility.json": "/api/v1/plots/PLT-DEMOIN/policy-eligibility",
    "market-scenario.json": "/api/v1/plots/PLT-DEMOIN/market-scenario",
    "regions.json": "/api/v1/regions",
}


def _keys(obj, prefix=""):
    if isinstance(obj, dict):
        out = set()
        for k, v in obj.items():
            out.add(prefix + k)
            out |= _keys(v, prefix + k + ".")
        return out
    if isinstance(obj, list) and obj:
        return _keys(obj[0], prefix + "[].")
    return set()


@pytest.mark.skipif(not FIXTURES.exists(), reason="fixtures not generated")
@pytest.mark.parametrize("name,path", sorted(ENDPOINTS.items()))
def test_fixture_keys_match_live_response(name, path):
    fixture_path = FIXTURES / name
    if not fixture_path.exists():
        pytest.skip(f"{name} not generated")
    expected = json.loads(fixture_path.read_text())
    settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False, ATLAS_API_KEYS="")  # type: ignore[call-arg]
    with TestClient(create_app(settings)) as client:
        actual = client.get(path).json()
    missing = _keys(expected) - _keys(actual)
    assert not missing, f"keys missing from live response: {sorted(missing)[:10]}"
