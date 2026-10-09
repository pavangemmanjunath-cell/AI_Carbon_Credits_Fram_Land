# Experiments

An experiment is a reproducible run of the engines under a defined
configuration, with its results committed as data. Experiments differ from
notebooks in that they are scripted (no interactive state) and can be
re-run in CI or by a reviewer with one command.

## Layout

```text
research/experiments/
├── README.md
├── _template/
│   ├── config.yaml        # inputs: commit, config versions, plots, species, overrides
│   ├── run.py             # produces results.csv and summary.md
│   └── README.md          # question, method, result, decision
└── YYYY-MM-DD-<slug>/     # one folder per experiment
```

## Config format

```yaml
experiment: tier1-vs-comet-pecan
commit: <git sha>
config_versions:
  species: 0.1.0
  ipcc-2006-tier1: 0.1.0
  market: 0.1.0
inputs:
  plots: [examples/usa-agroforestry/plot.request.json]
  inventories: [examples/usa-agroforestry/trees.request.json]
  mode: demo
overrides:            # parameter overrides under test, each with a source
  - path: species.pecan.increment_multiplier.value
    value: 0.75
    source: "COMET-Planner agroforestry rates, Georgia, 2024 — https://comet-planner.com/"
outputs:
  - results.csv
  - summary.md
```

Overrides never modify files under `config/`; they are applied in memory
by `run.py` so that the committed configuration remains the single source
of truth. If an experiment concludes that a parameter should change, the
change goes through a pull request with the usual review.

## Planned experiments

| Slug | Question | Compares |
|---|---|---|
| `tier1-vs-comet-pecan` | How far is the Tier 1 default from COMET-Farm for a Georgia pecan planting at ages 5, 10, 20? | engine vs COMET-Farm output entered manually from the tool |
| `tier1-vs-field-mango` | Does the ramp + density scaling approximate published mango orchard biomass at 5–10 years? | engine vs literature values (with citations) |
| `density-clamp-sensitivity` | How does the [0.2, 1.5] density clamp affect estimates for over- and under-stocked plots? | clamp on/off across densities |
| `survival-default` | Effect of survival rate 0.70–0.95 on the 30-year series | sensitivity sweep |
| `climate-zone-misassignment` | Cost of using the region default instead of per-plot normals (the Andalusia case) | demo vs live climate zone |
| `cube-size-budget` | Payload size and render time of the JSON cube at 12×12×36 vs 24×24×36 vs 12×12×72 | front-end timing |

## Result conventions

`results.csv` has one row per (plot, species, age, scenario) with
`low`, `central`, `high`, `unit`, `confidence` and the override set
applied. `summary.md` states the question, the headline numbers and a
decision: *adopt*, *reject*, or *needs field data*. Decisions that change
`config/` link to the pull request.
