"""Reproducible experiments for the manuscript (run from the repository root).

    .venv\\Scripts\\python paper\\run_experiments.py

Everything here calls the project's own deterministic engines with synthetic inputs.
Outputs: benchmarks/results/*.csv, benchmarks/results/summary.json, benchmarks/figures/*.png
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("carbon-engine", "geo-engine", "policy-engine", "report-engine", "agent-framework"):
    sys.path.insert(0, str(ROOT / "packages" / sub))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from carboncreditbuy_agents.guardrails import (
    check_no_coordinates,
    check_not_a_credit,
    check_pending_parameters,
    check_values_separated,
)
from carboncreditbuy_agents.messages import AgentMessage
from carbon_engine import (
    ClimateInput,
    InventoryInput,
    ModelParams,
    ParameterStore,
    PendingParameterError,
    PlotInput,
    TreeBiomassModel,
)
from carbon_engine.age import assess_by_age
from carbon_engine.equations.allometric import chave_2014_agb_kg

RES, FIG = ROOT / "benchmarks" / "results", ROOT / "benchmarks" / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
YEAR = 2026
store = ParameterStore()
model = TreeBiomassModel(store)
summary: dict = {}


def write_csv(name: str, rows: list[dict]) -> None:
    with open(RES / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------ E1: age curves for every species
species_cfg = yaml.safe_load((ROOT / "config/species/species.yaml").read_text(encoding="utf-8"))["species"]
TROPICAL = {"mango", "teak", "neem", "eucalyptus", "mixed_native_tropical"}


def zone_for(sp: str) -> str:
    return "tropical_dry" if sp in TROPICAL else "warm_temperate_moist"


rows = []
for sp in species_cfg:
    for age in (1, 3, 6, 10, 20, 40):
        a = assess_by_age(store, sp["id"], age, 1000, ClimateInput(zone_for(sp["id"]), "region-default"), as_of_year=YEAR)
        rows.append({
            "species": sp["id"], "climate_zone": zone_for(sp["id"]), "age_years": age,
            "stored_low": a.stored_now.low, "stored_central": a.stored_now.central,
            "stored_high": a.stored_now.high, "annual_low": a.annual_now.low,
            "annual_central": a.annual_now.central, "annual_high": a.annual_now.high,
            "per_tree_stored_kg": a.per_tree_stored_now_kg_co2e, "confidence": a.confidence,
            "certified": a.certified,
        })
write_csv("e1_age_curves.csv", rows)
summary["e1_cases"] = len(rows)
summary["e1_all_uncertified"] = all(r["certified"] is False for r in rows)
summary["e1_all_ordered"] = all(
    r["stored_low"] <= r["stored_central"] <= r["stored_high"]
    and r["annual_low"] <= r["annual_central"] <= r["annual_high"] for r in rows)
summary["e1_species"] = len(species_cfg)

fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
for sp in ("mango", "teak", "eucalyptus", "oak", "olive"):
    sub = [r for r in rows if r["species"] == sp]
    axes[0].plot([r["age_years"] for r in sub], [r["per_tree_stored_kg"] for r in sub], marker="o", label=sp)
    a = assess_by_age(store, sp, 40, 1000, ClimateInput(zone_for(sp)), as_of_year=YEAR)
    axes[1].plot([c.age for c in a.curve], [c.annual for c in a.curve], label=sp)
axes[0].set(xlabel="Tree age (years)", ylabel="Stored carbon (kg CO$_2$e per tree)", title="(a) Stored carbon, central estimate")
axes[1].set(xlabel="Tree age (years)", ylabel="Annual removal (t CO$_2$e / yr, 1000 trees)", title="(b) Annual removal curve")
axes[0].legend(); axes[0].grid(alpha=.3); axes[1].grid(alpha=.3)
fig.savefig(FIG / "fig_age_curves.png", dpi=200); plt.close(fig)

# ------------------------------------------------ E2: Level-1 independent check (mango example farm)
plot = PlotInput(area_hectares=2.13)
inv = InventoryInput(species_id="mango", tree_count=420, plantation_year=2023, survival_rate=0.85)
est = model.estimate(plot, inv, ClimateInput("tropical_dry"), ModelParams(as_of_year=YEAR))
Gw, m_sp, R, CF = 4.0, 0.9, 0.56, 0.47
fd = min(1.5, max(0.2, 420 / 2.13 / 150)) * 0.85  # density factor x survival
full = 2.13 * Gw * m_sp * fd * (1 + R) * CF * 44 / 12
summary["e2_hand_full_increment_tco2e_yr"] = round(full, 3)
summary["e2_headline_definition"] = "horizon-mean annual removal (tier 1)"
summary["e2_headline_range"] = [est.estimate.low, est.estimate.central, est.estimate.high]
# Independent re-implementation of the documented equations, year by year (ramp 6 y, maturity 8 y,
# post-maturity factor 0.5, root-to-shoot 0.56 below 20 t d.m./ha cumulative AGB, 0.28 above).
post = store.model_setting("post_maturity_increment_factor", "fraction").value
hand_rows, agb = [], 0.0
for pt in est.annual_series:
    inc = Gw * m_sp * fd * min(pt.age / 6.0, 1.0) * (1.0 if pt.age <= 8 else float(post))
    agb += inc
    r = 0.56 if agb < 20 else 0.28
    h = 2.13 * inc * (1 + r) * CF * 44 / 12
    hand_rows.append({"year": pt.year, "age": pt.age, "engine_central": pt.central, "hand_central": round(h, 3),
                      "abs_diff": round(abs(pt.central - h), 4)})
write_csv("e2_level1_hand_vs_engine.csv", hand_rows)
summary["e2_years_compared"] = len(hand_rows)
summary["e2_max_abs_diff_tco2e"] = max(r["abs_diff"] for r in hand_rows)
summary["e2_year_2026"] = next(r for r in hand_rows if r["year"] == 2026)

# ------------------------------------------------ E3: Tier 1 vs Tier 2 (girth)
rows = []
for age in (5, 10, 20, 40, 60):
    t1 = assess_by_age(store, "mango", age, 25, ClimateInput("tropical_dry"), as_of_year=YEAR)
    for girth in (30, 60, 100, 150, 188):
        t2 = assess_by_age(store, "mango", age, 25, ClimateInput("tropical_dry"), girth_cm=girth, as_of_year=YEAR)
        rows.append({"age": age, "girth_cm": girth, "dbh_cm": round(girth / math.pi, 1),
                     "tier1_stored": t1.stored_now.central, "tier2_stored": t2.stored_now.central,
                     "ratio_t2_over_t1": round(t2.stored_now.central / t1.stored_now.central, 3),
                     "tier1_conf": t1.confidence, "tier2_conf": t2.confidence})
write_csv("e3_tier1_vs_tier2.csv", rows)
chk = assess_by_age(store, "mango", 60, 25, ClimateInput("tropical_dry"), girth_cm=188, as_of_year=YEAR)
hand = 25 * chave_2014_agb_kg(0.55, 188 / math.pi, 10.0) / 1000 * 0.47 * 44 / 12 * 1.28
summary["e3_girth_case_engine_stock"] = chk.stored_now.central
summary["e3_girth_case_hand_stock"] = round(hand, 3)
summary["e3_girth_rel_diff"] = abs(chk.stored_now.central - hand) / hand
summary["e3_t2_over_t1_range"] = [min(r["ratio_t2_over_t1"] for r in rows), max(r["ratio_t2_over_t1"] for r in rows)]

fig, ax = plt.subplots(figsize=(5.5, 4), constrained_layout=True)
for age in (10, 20, 40):
    sub = [r for r in rows if r["age"] == age]
    ax.plot([r["dbh_cm"] for r in sub], [r["ratio_t2_over_t1"] for r in sub], marker="o", label=f"age {age} y")
ax.axhline(1, color="k", lw=.8, ls="--")
ax.set(xlabel="Measured DBH (cm)", ylabel="Tier 2 / Tier 1 stored carbon", title="Effect of adding a trunk measurement")
ax.legend(); ax.grid(alpha=.3)
fig.savefig(FIG / "fig_tier2_vs_tier1.png", dpi=200); plt.close(fig)

# ------------------------------------------------ E4: parameter verification census + production gate
status: Counter = Counter()


def walk(node) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("verification_status"), str):
            status[node["verification_status"]] += 1
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)


for f in ["config/methodologies/ipcc-2006-tier1.yaml", "config/methodologies/tree-biomass-model.yaml",
          "config/species/species.yaml", "config/tree-age/rules.yaml", "config/readiness.yaml", "config/detection.yaml"]:
    walk(yaml.safe_load((ROOT / f).read_text(encoding="utf-8")))
summary["e4_verification_census"] = dict(status)
try:
    model.estimate(plot, inv, ClimateInput("tropical_dry"), ModelParams(as_of_year=YEAR, allow_pending_parameters=False))
    summary["e4_production_gate_blocks_pending"] = False
except PendingParameterError:
    summary["e4_production_gate_blocks_pending"] = True

# ------------------------------------------------ E5: guardrail adversarial suite


def msg(text: str, facts: dict | None = None) -> AgentMessage:
    return AgentMessage(id="M1", step=1, agent="x", agent_title="X", kind="finding", text=text, facts=facts or {})


def nac(text: str, **kw):
    return check_not_a_credit([text], [], **{"run_certified": False, "disclaimer": "d", **kw})


cases = [
    ("claims an issued credit", lambda: nac("You now hold issued carbon credits."), "fail"),
    ("promises guaranteed income", lambda: nac("This gives guaranteed income."), "fail"),
    ("run flagged certified", lambda: nac("ok", run_certified=True), "fail"),
    ("disclaimer missing", lambda: nac("ok", disclaimer=""), "fail"),
    ("negated claim is allowed", lambda: nac("This is not an issued carbon credit."), "pass"),
    ("coordinates in text", lambda: check_no_coordinates([msg("Plot is at 12.9716, 77.5946 near town.")]), "fail"),
    ("polygon in facts", lambda: check_no_coordinates([msg("ok", {"boundary": {"type": "Polygon", "coordinates": [[[77.5, 12.9], [77.6, 12.9], [77.6, 13.0], [77.5, 12.9]]]}})]), "fail"),
    ("clean message", lambda: check_no_coordinates([msg("The plot is 2.13 ha in Karnataka.")]), "pass"),
    ("values summed in text", lambda: check_values_separated([msg("The total of benefit and income is $5,000 combined.")]), "fail"),
    ("combined fact key", lambda: check_values_separated([msg("ok", {"total_value": 10})]), "fail"),
    ("values kept separate", lambda: check_values_separated([msg("Indicative value is $400. Farm income is $900.")]), "pass"),
    ("pending parameter flagged", lambda: check_pending_parameters([{"name": "g", "verification_status": "pending"}]), "warn"),
    ("verified parameter", lambda: check_pending_parameters([{"name": "g", "verification_status": "verified"}]), "pass"),
]
rows, ok = [], 0
for label, fn, expected in cases:
    r = fn()
    ok += r.status == expected
    rows.append({"case": label, "guardrail": r.id, "expected": expected, "observed": r.status, "match": r.status == expected})
write_csv("e5_guardrails.csv", rows)
summary["e5_cases"], summary["e5_matches"] = len(cases), ok

# ------------------------------------------------ E6: sensitivity to the Tier-1 growth value
rows = [{"growth_factor_vs_default": f, "annual_central_full_increment_tco2e": round(full * f, 2)}
        for f in (0.5, 0.75, 1.0, 1.25, 1.5)]
write_csv("e6_growth_sensitivity.csv", rows)

(RES / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
print(json.dumps(summary, indent=2, default=str))
