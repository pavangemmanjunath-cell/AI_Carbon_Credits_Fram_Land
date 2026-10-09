"""Data-quality gates on the configuration files.

These run in every CI job. The ``production`` marker variants fail when a
parameter the default model uses is still ``pending`` and
``ATLAS_ENV=production`` — a release cannot ship unverified carbon factors.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from carbon_engine import (
    ClimateInput,
    InventoryInput,
    ModelParams,
    PendingParameterError,
    PlotInput,
    get_model,
    get_store,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
ALLOWED_STATUS = {"verified", "pending", "assumption"}


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_every_species_parameter_is_cited():
    species = _yaml(CONFIG / "species" / "species.yaml")["species"]
    assert species, "species table is empty"
    for entry in species:
        for key in (
            "reference_density_per_ha",
            "wood_density_g_cm3",
            "increment_multiplier",
            "typical_height_m_at_maturity",
        ):
            cited = entry[key]
            assert {"value", "source", "verification_status"} <= set(cited), f"{entry['id']}.{key}"
            assert cited["verification_status"] in ALLOWED_STATUS, f"{entry['id']}.{key}"
        assert entry["suitable_climate_zones"], entry["id"]


def test_tier1_parameters_have_sources_and_valid_status():
    params = _yaml(CONFIG / "methodologies" / "ipcc-2006-tier1.yaml")
    for name, constant in params["constants"].items():
        assert constant["source"] and constant["verification_status"] in ALLOWED_STATUS, name
    growth = params["above_ground_biomass_growth"]
    assert growth["verification_status"] in ALLOWED_STATUS
    for zone, entry in growth["by_climate_zone"].items():
        assert entry["value"] > 0 and entry["range"][0] <= entry["value"] <= entry["range"][1], zone
    assert params["constants"]["carbon_fraction"]["value"] == 0.47
    assert abs(params["constants"]["co2_per_c"]["value"] - 44 / 12) < 1e-3


def test_regions_and_policies_align():
    region_ids = {p.stem for p in (CONFIG / "regions").glob("*.yaml")}
    policy_ids = {p.stem for p in (CONFIG / "policies").glob("*.yaml")}
    assert region_ids == policy_ids == {"IN", "US", "EU"}
    market = _yaml(CONFIG / "market" / "carbon-price-scenarios.yaml")["scenarios"]
    assert set(market) == region_ids
    for region in region_ids:
        data = _yaml(CONFIG / "regions" / f"{region}.yaml")
        assert data["currency"] == market[region]["currency"]
        prices = [market[region][k]["price_per_tco2e"] for k in ("low", "reference", "high")]
        assert prices == sorted(prices) and prices[0] > 0


def test_policy_rules_reference_documents():
    for path in (CONFIG / "policies").glob("*.yaml"):
        policy = _yaml(path)
        assert "screening" in policy["disclaimer"].lower()
        for programme in policy["programmes"]:
            assert programme["references"], programme["id"]
            assert all(ref.get("url") for ref in programme["references"]), programme["id"]
            statuses = [rule.get("status") or rule.get("default") for rule in programme["rules"]]
            assert statuses and "potentially_applicable" not in [
                programme["rules"][-1].get("default")
            ], programme["id"]


def test_default_model_runs_for_every_species_and_zone():
    store = get_store(str(CONFIG))
    model = get_model("tree-biomass", store)
    for species in store.species_list():
        for zone in species["suitable_climate_zones"]:
            result = model.estimate(
                PlotInput(area_hectares=1.0, plot_id="PLT-TEST"),
                InventoryInput(species_id=species["id"], tree_count=200, plantation_year=2020),
                ClimateInput(zone=zone),
                ModelParams(as_of_year=2026, allow_pending_parameters=True),
            )
            assert 0 < result.estimate.low <= result.estimate.central <= result.estimate.high, (
                species["id"],
                zone,
            )


@pytest.mark.skipif(
    os.environ.get("ATLAS_ENV", "").lower() != "production", reason="production gate"
)
def test_production_refuses_pending_parameters():
    store = get_store(str(CONFIG))
    model = get_model("tree-biomass", store)
    with pytest.raises(PendingParameterError):
        model.estimate(
            PlotInput(area_hectares=1.0),
            InventoryInput(species_id="mango", tree_count=100, plantation_year=2020),
            ClimateInput(zone="tropical_dry"),
            ModelParams(as_of_year=2026, allow_pending_parameters=False),
        )
