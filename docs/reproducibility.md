# Reproducibility

This page explains how to reproduce the project's results exactly, and what can and cannot be reproduced.

## What "results" means here

The project produces **scenario estimates**, not measurements. Reproducibility therefore means:

1. the same inputs and the same configuration give the same numbers, bit for bit; and
2. the implementation checks in [`benchmarks/`](../benchmarks/README.md) regenerate the committed result files.

It does **not** mean the estimates agree with trees measured in the field. That comparison (validation levels 2 and 3
in [research/validation/](../research/validation/README.md)) has not been performed yet.

## Determinism

- The carbon, geo, policy and report engines are deterministic: no random sampling, no learned weights, no network
  calls. The same request and the same `config/` give the same output.
- The AI agents are deterministic by default. Sentences come from templates and numbers from engine tool calls. An
  optional language model can only reword text; if it changes a number, the template text is kept.
- The "Why this number?" explanation re-runs the deterministic engine (one-at-a-time sensitivity), so it is
  deterministic too.
- **Demo mode** (`ATLAS_MODE=demo`, the default) uses synthetic, labelled stand-ins for every external dataset and
  needs no network, so it is fully reproducible offline.
- **Live mode** (`ATLAS_MODE=live`) calls public APIs (ESA WorldCover, Sentinel-2 STAC, Open-Meteo, SoilGrids and
  others). Upstream data can change, so live results are reproducible only together with the dataset versions and
  acquisition dates recorded in each result's `provenance`.

## Environment

| Component | Version used for the checks below |
|---|---|
| Python | 3.13.5 locally (Windows 11); CI runs 3.12 and 3.13 on Ubuntu |
| Node.js | 24.20 locally; CI runs 22 |
| Python dependencies | exact pins in [`requirements.txt`](../requirements.txt) |
| JavaScript dependencies | exact lock in [`apps/web/package-lock.json`](../apps/web/package-lock.json) |
| Parameters | [`config/`](../config/): every value has `source`, `unit` and `verification_status` |

## Step by step

```bash
git clone https://github.com/pavangemmanjunath-cell/AI_Carbon_Credits_Fram_Land.git
cd AI_Carbon_Credits_Fram_Land
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt matplotlib
(cd apps/web && npm ci)
```

### 1. Run the test suites

```bash
python -m pytest -q                                   # engines, adapters, API, agents, data quality
ATLAS_ENV=production ATLAS_ALLOW_PENDING_PARAMETERS=false python -m pytest -q tests/data-quality
cd apps/web && npm run typecheck && npm run test -- --run && npm run build
```

### 2. Regenerate the implementation checks

```bash
python benchmarks/run_experiments.py
git status benchmarks/        # no changes means the committed results were reproduced exactly
```

| ID | Check | Committed output |
|---|---|---|
| E1 | Age curves for all 11 species; `certified: false` and low ≤ central ≤ high in every case | `results/e1_age_curves.csv`, `figures/fig_age_curves.png` |
| E2 | Independent re-implementation of the Tier 1 equations vs the engine, year by year | `results/e2_level1_hand_vs_engine.csv` |
| E3 | Tier 1 (age only) vs Tier 2 (measured girth, Chave et al. 2014 eq. 4) | `results/e3_tier1_vs_tier2.csv`, `figures/fig_tier2_vs_tier1.png` |
| E4 | Census of parameter `verification_status` and the production gate | `results/summary.json` |
| E5 | 13 adversarial cases for the agent guardrails | `results/e5_guardrails.csv` |
| E6 | Sensitivity of annual removal to the Tier 1 growth value | `results/e6_growth_sensitivity.csv` |

### 3. Run the agent team on the demo plot

```bash
python examples/agents/run_team.py      # or: make agents-demo
```

## Verified on 2026-10-11

| Check | Result |
|---|---|
| `python -m pytest -q` | 2,195 passed, 4 skipped (PyQt5 not installed; production-gate tests that run in the next row). One QGIS test expecting a Linux "connection refused" error was deselected on Windows |
| Production data-quality gate | 526 passed |
| Ruff (lint and format), mypy | clean (mypy: 192 source files, no issues) |
| Web: Prettier, ESLint, TypeScript, Vitest, build | clean; 481 tests passed; build succeeded |
| Browser tests (Playwright, with the API running) | 18 passed |
| `benchmarks/run_experiments.py` | committed results reproduced exactly (`git status` unchanged); E5: 13 of 13 guardrail cases as expected |
| `examples/agents/run_team.py` | runs; full assessment with disclaimers |

Parameter census (E4): 28 `verified`, 20 `pending`, 64 `assumption`. Production mode refuses `pending` values.

## Known limits to reproducibility

- Estimates depend on parameters still marked `pending` or `assumption`; changing a parameter changes the numbers,
  and every change is recorded in [CHANGELOG.md](../CHANGELOG.md).
- Live-mode results depend on upstream data versions (recorded in provenance, but not frozen).
- The 3D view and browser tests render with WebGL. Software rendering in headless browsers is slower, so the
  Playwright configuration limits parallel workers locally.

## Release checklist

Before a release, confirm:

- [ ] README describes only implemented functionality
- [ ] ORCID and authors correct in `CITATION.cff` and `AUTHORS.md`
- [ ] `cffconvert --validate -i CITATION.cff` passes
- [ ] Licence confirmed (Apache-2.0; QGIS plugin GPL-2.0-or-later)
- [ ] All test suites above pass, and CI is green on GitHub
- [ ] Secret scan of the tree and the history is clean
- [ ] No synthetic data presented as real; no invented citations, DOIs or adoption claims
- [ ] Examples and benchmarks run
- [ ] Documentation links resolve (offline link check)
- [ ] Version numbers and [CHANGELOG.md](../CHANGELOG.md) updated; release notes ready
