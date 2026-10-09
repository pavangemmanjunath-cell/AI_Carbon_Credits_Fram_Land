# Notebooks

Planned Jupyter notebooks. Each one is self-contained, runs from the
repository root, writes its results tables to `research/experiments/`, and
states the commit and configuration versions it used. Notebooks are
reviewed like code; outputs are cleared before committing (use `nbstripout`)
so that diffs stay readable.

## 01 — NDVI validation (`01-ndvi-validation.ipynb`)

**Question.** Does the geo-engine's NDVI/NDMI pipeline (STAC search, cloud
mask from the Sentinel-2 scene classification layer, monthly minimum-cloud
composite, 3 × 3 mean aggregation to 30 m) reproduce reference values?

**Method.** For a set of synthetic plots placed on known land-cover types
(dense evergreen forest, irrigated cropland, bare soil, water), compute
indices with the engine and independently with a plain `rasterio` script on
the same scenes; compare per-scene values, class assignments (`sparse` <
0.3, `moderate` 0.3–0.6, `healthy` ≥ 0.6) and the 36-month cube statistics.
Cross-check against the harmonized Landsat–Sentinel-2 record where
available.

**Outputs.** Agreement table (mean absolute difference per index), a plot
of engine vs reference NDVI, and a list of edge cases (partial cloud, snow,
nodata at tile edges) with the behaviour observed.

**Acceptance.** Mean absolute NDVI difference ≤ 0.02 against the
independent computation; identical class assignment in ≥ 98 % of scenes.

## 02 — Allometry comparison (`02-allometry-comparison.ipynb`)

**Question.** How do per-tree above-ground biomass estimates differ between
Chave et al. 2014 eq. 4 (with height), eq. 7 (without height, with the
environmental stress variable E), and species-specific equations reported
in the literature for mango, teak, eucalyptus, pecan, olive and oak?

**Method.** Sweep DBH from 5 to 60 cm and heights from species allometric
height–diameter relationships; compute AGB under each equation; express
differences relative to the engine's default; identify the DBH ranges where
the pantropical equation departs by more than 25 % from a published
species equation.

**Outputs.** Curves per species, a table of relative differences at DBH 10,
20, 30, 40 cm, and recommended `allometry` keys and `verification_status`
updates for `config/species/species.yaml`, each with its citation.

**Acceptance.** Every recommended change carries a DOI and the equation's
stated applicability range.

## 03 — Uncertainty propagation (`03-uncertainty-propagation.ipynb`)

**Question.** Are the fixed ±30 % (Tier 1) and ±20 % (Tier 2) bands in
`config/methodologies/ipcc-2006-tier1.yaml` conservative enough, and how
should they depend on data quality?

**Method.** Monte Carlo propagation of parameter uncertainty (growth
increment range, root-to-shoot ratio, wood density, survival, carbon
fraction) through the gain-loss model for the three example farms; compare
the simulated 5th–95th percentile interval with the fixed band; test
sensitivity to each input with Sobol indices; model the effect of adding
DBH/height measurements.

**Outputs.** Interval comparison table, sensitivity ranking per species and
climate zone, and a proposal for data-quality-dependent bands expressed in
`config/` terms.

**Acceptance.** The proposal is adopted only if the fixed bands are shown
to under-cover the simulated interval in any supported case; otherwise the
notebook documents that the fixed bands are conservative.

## Planned additions

- `04-worldcover-accuracy.ipynb` — WorldCover class shares against
  higher-resolution reference imagery for small plots (< 1 ha), where 10 m
  pixels matter.
- `05-climate-zone-assignment.ipynb` — Open-Meteo normals to IPCC climate
  zones, compared with the published IPCC climate-zone map.
