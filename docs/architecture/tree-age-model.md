# Tree age model

The **Tree age** feature answers one question for a landowner: *"I have N trees of species S, about A years old, in
this place. How much carbon do they hold, how fast are they adding more, and do any real rules treat trees of this age
differently?"* It is a screening tool. It keeps two things apart on purpose, because they often disagree:

- **Carbon stored and added** by the trees: a range in tCO₂e computed by the same deterministic carbon engine as the
  plot estimate.
- **Rules and programmes** that apply at that age and place: read from `config/tree-age/rules.yaml`, each with its
  sources and a verification status.

Old trees can hold a great deal of carbon and still be worth no credits, because credit standards reward carbon that is
*added* (new planting) or *loss that is avoided*, not carbon that already stands. Every result therefore carries
`certified: false` and a disclaimer: **an estimate is never a carbon credit** (CLAUDE.md principle 1). An LLM never
computes any of these numbers (principle 12); the agents call the same service as the web app.

The HTTP shapes are in [api-contract.md](api-contract.md) ("v0.2 additions"). This page explains how the numbers and
the rule matching work, and where each piece lives.

## Data flow

```text
POST /api/v1/tree-age/assess      (apps/api/app/api/v1/routers/tree_age.py)
  └─ TreeAgeService.assess        (apps/api/app/services/tree_age.py)
       ├─ validate request, pick the climate zone (plot analysis when plot_id is given, else the region default)
       ├─ carbon_engine.age.assess_by_age      → carbon block: ranges, per-tree values, age curve, parameters, notes
       │    └─ TreeBiomassModel (Tier 1 / Tier 2)   ← config/methodologies, config/species (via the parameter store)
       ├─ policy_engine.tree_age.evaluate      → every rule for this place, with applies / why / outcome_for_you
       │    └─ config/tree-age/rules.yaml, config/tree-age/subdivisions.yaml
       └─ policy_engine.tree_age.credit_outlook → one sentence on credits for existing trees
```

Nothing is stored. No coordinates are read or logged: an optional `plot_id` only supplies the climate zone of that
plot's latest analysis.

`GET /api/v1/tree-age/rules?country=IN&subdivision=IN-HR` returns the rules file as served (header, disclaimer, age
classes, the rules for that place) plus the list of subdivisions for the drop-down and the ids of any rules withheld in
production (see "Pending data and production" below).

## Inputs

| Field | Meaning | Limits |
|---|---|---|
| `country` | ISO 3166-1 alpha-2 code; EU member states map to the EU rules | must be a supported country |
| `subdivision` | ISO 3166-2 code such as `IN-HR`; optional | must belong to `country`; checked against `config/tree-age/subdivisions.yaml` where the country has a list |
| `setting` | `farm`, `urban`, `forest` or `any` (unknown never excludes a rule) | |
| `species_id` | species from `config/species/species.yaml` | unknown id gives 422 |
| `age_years` | age of the trees now; `0` means trees being planned | 0 to 300 |
| `tree_count` | number of trees | 1 to 1 000 000 |
| `girth_cm` | trunk circumference at 1.3 m; switches to the measured-tree path | 10 to 2 000; needs `age_years` of 1 or more |
| `height_m` | tree height; used only together with `girth_cm` | 0.5 to 120 |
| `plot_id` | take the climate zone from this plot's analysis | optional; 404 when unknown |

## Carbon: how an age becomes a number

`packages/carbon-engine/carbon_engine/age.py` is a thin layer over `TreeBiomassModel`
(see [carbon-engine.md](carbon-engine.md)). It defines **no coefficient**: growth, wood density, root-to-shoot ratio,
carbon fraction and uncertainty all come from `config/` through the parameter store and are echoed in
`parameters_used` with their source and `verification_status`. The layer only turns an age into the inputs the model
needs.

### Tier 1: age only (`method: tier1-age`)

The model is run as if the stand were planted `age_years` ago (`plantation_year = as_of_year − age`) for
`max(age + 20, 40)` years. Then:

- `stored_now` is the cumulative removal from planting to today, and `annual_now` is the removal in the current year,
  each as `low`, `central` and `high` (±30 % for Tier 1, a project assumption until IPCC's default uncertainty is
  adopted).
- **Survival.** The trees you list are counted alive today, so the mortality they went through is already in that count.
  For `age ≥ 1` the model runs with a survival rate of 1.0. For `age = 0` (planned trees) the configured default
  survival applies, because some planted trees will die.
- **Area.** Without an area the trees are treated as a stand at the species' reference density, so the density factor is
  exactly 1. The API does not pass a plot area for scattered trees, because the model's density clamp would raise the
  per-tree value of a sparse stand. The assumed area is listed in `parameters_used` as `stand_area_hectares`.
- **Precision.** The model rounds to three decimals of tCO₂e, which is coarse for a handful of trees. The layer runs
  1 000 or more identical trees and divides the result; Tier 1 is linear in stand size at constant density, so nothing
  else changes.

### Measured trunk: girth path (`method: tier2-girth`)

With `girth_cm`, the diameter is `DBH = girth ÷ π` and the model's Tier 2 path applies the Chave et al. (2014)
pantropical equation 4 with the species' wood density (and `height_m` when given, otherwise the species' typical height
scaled for age). Roots are added with the IPCC Table 4.4 ratio. `stored_now` is the Tier 2 stock.

`annual_now` on this path is **stock ÷ age**, a documented simplification: it averages the tree's whole life, so it
understates the current growth of a young tree and overstates that of an old one. The notes say so. Outside the
equation's calibration range (DBH 5 to 212 cm) and for species without a verified allometry the notes say that too.

### The age curve

`curve` gives `age`, `stored`, `stored_low`, `stored_high` and `annual` for ages 0 to `max(age + 20, 40)`, one point per
year. When that would exceed 150 points the curve is thinned (ages 0, today and the last age are always kept). The curve
**always comes from the Tier 1 run** and is labelled `curve_method: tier1-age`, even on the girth path, so on the girth
path it can sit well below or above `stored_now` at today's age. Both are returned, and the notes explain the gap,
rather than rescaling one to meet the other: a rescaling would be a made-up method.

### Confidence

Tier 1 by age alone is always `low`, because nothing about the actual trees is measured. The girth path grades with the
same rules as the plot estimate: more evidence (a measured girth, a height, a known planting year) raises it. Ranges are
reported, not single values (CLAUDE.md principle 9).

### Worked example: 25 mango trees, 60 years old, India

Climate zone `tropical_dry` (region default). Values as of `config` version 0.1.0; several are still `pending`.

| Step | Value | Source |
|---|---|---|
| Above-ground growth | 4.0 t d.m./ha/yr × species multiplier 0.9 = 3.6 | IPCC 2006 Vol. 4 Ch. 4 (pending), project assumption |
| Growth years | 6-year ramp, full increment to maturity at 8 years, then 50 % | project assumptions |
| Cumulative factor at 60 years | (1+2+3+4+5)/6 + 3 + 52 × 0.5 = 31.5 | |
| Above-ground stock | 3.6 × 31.5 = 113.4 t d.m./ha | |
| Root-to-shoot | 0.56 while the stock is under 20 t/ha (to age 8), then 0.28 | IPCC 2006 Table 4.4 (pending) |
| Carbon and CO₂e | × 0.47 × 44/12 | IPCC 2006 Table 4.3, molecular mass ratio |
| Per hectare | 3.6 × (5.5 × 1.56 + 26 × 1.28) × 0.47 × 44/12 = 259.7 tCO₂e/ha | |
| Stand area | 25 trees ÷ 150 trees/ha = 0.1667 ha | project assumption |

Result: **stored now 30.3 to 56.3 tCO₂e (central 43.3)**, and **annual now 0.46 to 0.86 tCO₂e/yr (central 0.66)**.
That is about 1 731 kg CO₂e stored and 26.5 kg CO₂e per year for each tree. The same trees with a measured girth of
188 cm (DBH 59.8 cm, 10 m typical height, wood density 0.55) give 1 045.6 kg of dry biomass per tree and about
57.7 tCO₂e in total. Both hand calculations are unit tests (`packages/carbon-engine/tests/test_age.py`).

### What the model does not know

- Tier 1 uses a flat per-hectare increment, so it says nothing about how an individual large tree grows or ages.
  Research shows individual trees keep adding carbon as they get bigger, while stand productivity falls after canopy
  closure (see the
  [science notes](../research/tree-age-carbon-rules.md#science-notes-for-the-dashboard) in the research page). The app
  may say that a large old tree holds a large stock and may still be adding carbon; it must not say that old trees
  stop growing, or that they earn credits.
- Growth after maturity uses a 50 % factor that is a project assumption. IPCC's age-class increments for stands older
  than 20 years are not used yet because their values are not verified; see
  [ipcc-age-class-growth.md](../research/ipcc-age-class-growth.md).
- Only living tree biomass (above and below ground) is counted: no soil, litter or dead wood, and no harvest or loss.
- A species outside its listed regions still computes, with a note that its growth parameters may not apply there.

## Rules: what applies at this age and place

`packages/policy-engine/policy_engine/tree_age.py` reads and matches `config/tree-age/rules.yaml`; no rule or number is
in code (CLAUDE.md principles 2, 3 and 13). The file has 22 rules (global standards, India, the United States and the
EU) covering carbon-credit eligibility, incentive payments, tree protection, compensatory planting and methodology
notes. Its research is in [tree-age-carbon-rules.md](../research/tree-age-carbon-rules.md).

1. **Geography is a hard filter.** `GLOBAL` rules always apply. `IN` and `US` rules match the country. `EU` rules match
   any member state; a rule that names a country (the Berlin ordinance is scope `EU`, country `DE`) also needs that
   country. Rules of other regions are not returned.
2. **Everything else is returned with `applies` true or false** and a plain-language `why`, so a user can see what
   would apply elsewhere: a different subdivision, an age outside `[min_age_years, max_age_years]`, a setting the rule
   does not cover (a farm tree is non-forest), or a municipal example for another place. Municipal examples
   (`locality`) are labelled as examples; the Berlin rule applies in Berlin because the city is its own subdivision
   (`DE-BE`).
3. **`outcome_for_you`** is the rule's outcome for existing trees (`not-eligible`, `conditional`, `protected`,
   `payment`, …). For `age_years = 0` it becomes `conditional` for rules written for new planting and
   `not-applicable` for rules that regulate existing trees.
4. **Order:** applicable rules first, then by category, then by id.

The age classes (young 0 to 20, mature 21 to 49, old 50 to 74, veteran 75 and over) are screening labels, not legal
categories; the reasoning behind the boundaries is in the research note.

### Credit outlook

`credit_outlook` condenses the applicable carbon-credit rules into one of `not-eligible` or `conditional`, with a
summary sentence and the ids it rests on. It is `not-eligible` unless a rule that is in force names a route for
existing trees (for example City Forest Credits' preservation protocol, which credits avoided loss), and it **never says
`eligible`**: only a programme can decide that. India's Green Credits and carbon credits are described as separate
mechanisms, and in the EU an estimate is never automatically certifiable.

## Pending data and production

Principle 10 says unverified data must fail a production-mode check. This feature follows it on both sides:

| Data | In development | With `ATLAS_ENV=production` or `ATLAS_ALLOW_PENDING_PARAMETERS=false` |
|---|---|---|
| Carbon parameters marked `pending` | used, listed in `parameters_used`, the notes say they are pending | `POST /tree-age/assess` answers 409 `pending-parameters`, like the carbon estimate |
| Rules marked `pending` | returned, flagged as "not yet confirmed from a primary source" | withheld from `rules` and reported in `withheld_rule_ids` |

Today the Tier 1 growth and root-to-shoot values are still `pending`, so production refuses the estimate until they are
verified cell by cell against the IPCC tables. Three rules are `pending` (Haryana's pension for very old trees,
Maharashtra's heritage-tree age and the EU carbon-farming delegated act). `tests/data-quality/test_tree_age_rules.py`
checks the file in every run (sources with `https` links and access dates, vocabulary, geography, amounts with an
`as_of` date) and, under `ATLAS_ENV=production`, asserts that no pending rule is served and reports which ones a
release still has to confirm.

## Files

| Path | Role |
|---|---|
| `packages/carbon-engine/carbon_engine/age.py` | age → carbon assessment on top of `TreeBiomassModel` |
| `packages/policy-engine/policy_engine/tree_age.py` | load, validate and evaluate the rules |
| `config/tree-age/rules.yaml` | the 22 sourced rules and the age classes |
| `config/tree-age/subdivisions.yaml` | ISO 3166-2 codes for India, the United States and Germany (the drop-down and validation) |
| `apps/api/app/services/tree_age.py` | `TreeAgeService`: validation, climate zone, error mapping, response assembly |
| `apps/api/app/schemas/tree_age.py` | request model |
| `apps/api/app/api/v1/routers/tree_age.py` | `GET /tree-age/rules`, `POST /tree-age/assess` |
| `scripts/make_sample_tree_age.py` | regenerates `data/sample/responses/tree-age-*.json` and `imagery-providers-*.json` |

Tests: `packages/carbon-engine/tests/test_age.py`, `packages/policy-engine/tests/test_tree_age_rules_engine.py`,
`apps/api/tests/test_tree_age_api.py`, `tests/data-quality/test_tree_age_rules.py`.

### Changing the data

- **A new or corrected rule:** edit `config/tree-age/rules.yaml` with at least one `https` source and its access date,
  bump `updated`, then run `python3 -m pytest -q packages/policy-engine tests/data-quality` and regenerate the samples.
- **Confirming a pending rule or parameter:** read the primary source, update `sources`, `accessed` and the note, then
  set `verification_status: verified`. Never edit a value to make a result look better.
- **A new subdivision list:** add the country to `config/tree-age/subdivisions.yaml` from the ISO 3166-2 list.

## Imagery providers (the Satellite view)

`GET /api/v1/imagery/providers?country=IN` serves `config/imagery/providers.yaml` through
`apps/api/app/services/imagery.py`. The research and licence notes are in
[imagery-providers.md](../research/imagery-providers.md). What the service adds:

- **Keys never reach the repository or a log.** A URL may contain `${NAME}` placeholders. `ESRI_API_KEY` comes from the
  settings (which also read `.env`); any other `${…_KEY}` or `${…_TOKEN}` comes from the environment, but never a
  variable the application owns for another integration (such as `LLM_API_KEY`). A provider whose key is missing is
  returned with `available: false`, a reason and `url: null`; an unsubstituted `${…}` is never sent to a client.
- **The key is part of the tile URL the browser needs**, so a deployer should use a referrer-restricted key that can
  only load basemap tiles.
- **Order and default:** providers that cover the country come first (an EU country is covered by providers that list a
  member state), then the rest in file order. `recommended` is `default_by_country[country]`, else `default`, and falls
  back to the first available provider. The default is open and keyless, never the licensed Esri service.
- **Licence flags travel with each provider:** `commercial_use`, `analysis_allowed` (display-only imagery such as Esri
  stays `false`, so no segmentation or machine learning is run on it) and `open_data`. The data-quality test
  `tests/data-quality/test_imagery_providers.py` enforces these invariants.
