# Benchmarks

Reproducible checks of the implementation (not of the underlying science). Run from the repository root:

```bash
python benchmarks/run_experiments.py
```

| ID | What it checks | Output |
|---|---|---|
| E1 | Age curves for all 11 species; `certified: false` and low ≤ central ≤ high in every case | `results/e1_age_curves.csv`, `figures/fig_age_curves.png` |
| E2 | Independent re-implementation of the Tier 1 equations vs the engine, year by year (max difference 0.0002 tCO₂e, rounding only) | `results/e2_level1_hand_vs_engine.csv` |
| E3 | Tier 1 (age only) vs Tier 2 (measured girth, Chave et al. 2014 eq. 4) | `results/e3_tier1_vs_tier2.csv`, `figures/fig_tier2_vs_tier1.png` |
| E4 | Census of parameter `verification_status` and the production gate that refuses `pending` values | `results/summary.json` |
| E5 | 13 adversarial cases for the agent guardrails | `results/e5_guardrails.csv` |
| E6 | Sensitivity of annual removal to the Tier 1 growth value | `results/e6_growth_sensitivity.csv` |

All inputs are synthetic. Agreement with field data and reference tools (validation levels 2 and 3 in
[`research/validation/`](../research/validation/README.md)) has **not** been performed yet.
