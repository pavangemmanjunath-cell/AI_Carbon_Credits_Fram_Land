# Novelty

This page states what the project does differently, as a set of testable design choices. It makes no claim about
accuracy against field data, which has not been evaluated yet (see [reproducibility.md](reproducibility.md)).

## Existing Approaches

The landscape review in [research/competitive-landscape.md](research/competitive-landscape.md) (2026-10, with
sources) groups existing work into two kinds:

- **Commercial carbon-project developers and marketplaces** (for example Varaha, Boomitra, Agreena, Pachama). They
  aggregate farmers or land, apply a registry methodology and sell credits.
- **Open monitoring and research platforms** (for example Global Forest Watch, Restor, FAO Open Foris / SEPAL /
  Collect Earth, CarbonPlan). They map forests, restoration potential or offset projects at landscape or programme
  scale.

## Current Limitations

For a single farmer or advisor asking "what might the trees on *my* plot remove, and what would a programme need?",
these approaches leave gaps:

- Project developers answer inside a commercial contract, with their own methodology and pricing.
- Landscape platforms work at a scale and in terms (pixels, regions) that do not map to one plot and its trees.
- Simple calculators usually return one number without a range, without the source and status of each parameter,
  and without separating an estimate from an issued credit.

## Our Technical Approach

A self-hostable, plot-level screening tool built from deterministic, inspectable parts:

1. **Configuration-driven parameters with provenance.** Every carbon parameter in `config/` carries a source, unit
   and verification status (`verified`, `pending`, `assumption`). Production mode refuses `pending` values; a
   data-quality test enforces this.
2. **Ranges, not single numbers.** IPCC 2006 Tier 1 gain-loss (Tier 2 with a measured diameter, Chave et al. 2014)
   produces low–central–high ranges with a confidence grade and provenance.
3. **Evidence readiness instead of a price.** Each estimate sits beside a readiness score and the list of evidence
   still missing for a recognised programme. A separate panel shows the generic project cycle (design, validation,
   monitoring, verification, issuance) and never marks a step as done.
4. **Agents that cannot calculate.** Nine deterministic agents describe and route; every number comes from a tool
   call into an engine. Six guardrails (not a credit, uncertainty shown, provenance recorded, no coordinates, pending
   parameters flagged, values kept apart) must pass. An optional language model may only reword redacted text.
5. **Explanation by re-computation.** "Why this number?" re-runs the engine with each user-controlled input moved by
   ±10 % and lists every factor with its source and status. This is one-at-a-time sensitivity analysis, not a
   learned surrogate.
6. **Tree age kept apart from credit rules.** The carbon held by existing (often old) trees is separated from the
   rules that decide whether any credit is possible, since old trees can hold much carbon and still earn none.
7. **Privacy boundary.** Exact plot geometry stays private; coordinates are never logged or sent to a language model.

## Technical Differences

| | This project | Typical project developer | Typical open monitoring platform |
|---|---|---|---|
| Unit of analysis | One plot, its trees | A project portfolio | Landscape / pixel |
| Output | Range + confidence + missing evidence | Credits under contract | Maps and statistics |
| Parameter provenance | Shown per value, with status | Methodology documents | Dataset documentation |
| Explanation of a number | Engine re-runs and cited factors | Methodology | Dataset metadata |
| Language model role | Optional rewording only | Varies | Usually none |
| Deployment | Self-hostable, open source (Apache-2.0) | Proprietary | Hosted service, often open data |

## Research Hypothesis

Showing plot-level estimates as ranges, with the provenance and verification status of every parameter and the
evidence still missing, helps farmers and advisors judge whether pursuing a carbon or environmental programme is worth
the effort, better than a single headline number or price. This hypothesis has **not** been tested with users yet.

## Known Limitations

- No validation against field measurements or reference tools yet (validation levels 2 and 3 are planned).
- Many parameters are `pending` (20) or `assumption` (64); only 28 are `verified`.
- Demo mode uses synthetic data; results must not be read as observations.
- Regions are limited to India, the United States and the European Union.
- The tree-detection components are heuristics (NDVI thresholds, canopy-height local maxima), not trained models.
