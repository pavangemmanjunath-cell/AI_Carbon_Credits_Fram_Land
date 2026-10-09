# Validation protocol

This protocol defines how the carbon engine's output is compared against
independent references, what counts as acceptable agreement, and which
results gate a release. It exists because an estimate shown to a farmer
should be known to be *roughly right*, with the size of "roughly" stated,
before anyone relies on it. The protocol validates the **engine as
implemented**, including its configuration; it does not validate IPCC or
Chave et al. as science.

## Scope

| Component | Reference | Phase |
|---|---|---|
| Tier 1 gain-loss implementation | Hand calculation from IPCC 2006 Vol. 4 Ch. 4 equations and tables | every release |
| Chave 2014 allometry | Published worked examples and the BIOMASS R package (Réjou-Méchain et al. 2017, <https://doi.org/10.1111/2041-210X.12753>) | every release |
| End-to-end estimates for US agroforestry | USDA COMET-Farm / COMET-Planner outputs for the same inputs (<https://comet-farm.com/>, <https://comet-planner.com/>) | v0.3 onward |
| End-to-end estimates for Indian orchards and plantations | Peer-reviewed field studies with reported stand age, density and biomass or carbon stock | v0.3 onward |
| End-to-end estimates for EU agroforestry | Published national inventories and field studies; CRCF methodology default factors once adopted | v1.0 onward |
| Vegetation indices | Independent computation on the same scenes (see `research/notebooks/01-ndvi-validation`) | v0.2 onward |
| Land-cover shares | Visual interpretation of high-resolution imagery for synthetic plots | v0.2 onward |

## Method

### Level 1 — implementation correctness

For each species × climate zone × age in a fixed grid (ages 1, 3, 6, 10,
20, 30; densities 0.5×, 1×, 1.5× reference), compute the estimate by hand
(spreadsheet committed as CSV) and with the engine. The engine must match
to within floating-point tolerance (relative 1e-6) because both apply the
same equations to the same configuration. Any difference is a bug.

### Level 2 — agreement with reference tools

For the US example farm and at least four further synthetic US cases
(different species, states and ages), enter identical inputs into
COMET-Farm's agroforestry module and record its annual carbon
accumulation. Compare against the engine's central estimate and range.
COMET-Farm uses growth equations derived from Forest Inventory and
Analysis data, so differences are expected; the purpose is to quantify
them and to confirm that the engine's range contains the reference value.
We reference COMET-Farm's output; we never copy its equations or data
([docs/regions/US/PROGRAMS.md](../../docs/regions/US/PROGRAMS.md#usda-comet-farm-and-comet-planner)).

### Level 3 — agreement with field data

Compile a table of published measurements with, at minimum: species, age,
stocking density, climate zone, and above-ground biomass or carbon stock
per hectare, each with a DOI. Run the engine with the same inputs and
compare stock estimates. Field data contributed by farms or research
partners is used only with written consent, stored outside the repository,
and reported in aggregate.

## Acceptance criteria

| Level | Metric | Threshold for release | Action when failed |
|---|---|---|---|
| 1 | Relative difference engine vs hand calculation | ≤ 1e-6 | Fix the bug; no release |
| 2 | Share of reference cases where the COMET-Farm value lies within the engine's [low, high] range | ≥ 80 % | Widen the uncertainty band or lower the confidence grade for the affected species/zone; document in the release notes |
| 2 | Median absolute relative difference of central estimates | ≤ 35 % for Tier 1 inputs; ≤ 25 % when DBH and height are supplied | Investigate the increment multiplier and density scaling; open a carbon-model issue |
| 3 | Share of field cases within the range | ≥ 70 % (field data is noisier than tools) | Same as above; mark `verification_status: pending` on the parameters involved |
| 3 | Systematic bias (mean signed relative difference) | within ±20 % | A bias outside the band blocks `verified` status for the affected parameters |
| indices | Mean absolute NDVI difference vs independent computation | ≤ 0.02 | Fix the pipeline |

Thresholds are deliberately wide for v0.x because the configuration is
Tier 1 with pending parameters. They tighten when parameters become
`verified` and are revisited at each minor release.

## Reporting

Each validation run produces `research/validation/results/<version>/`
with the comparison tables (CSV), a short `report.md` (method, numbers,
pass/fail per criterion, decisions) and the commit hash. The report is
linked from the release notes and summarized in
[docs/architecture/carbon-engine.md](../../docs/architecture/carbon-engine.md)
under "Validation status". Failures are not hidden: a release can ship
with a failed Level 2 criterion only if the UI's confidence grading for
the affected species/zone is lowered accordingly and the release notes
say so.

## Independence

The person running Level 2 and Level 3 comparisons should not be the
person who tuned the parameters under test. Reviewer identity and date are
recorded in the report, as they are for `verification_status: verified`
entries in `config/`.
