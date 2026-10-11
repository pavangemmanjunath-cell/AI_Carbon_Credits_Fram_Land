# carbon-engine

Deterministic, parameter-cited carbon removal **scenarios** for CarbonCreditBuy.
Given a plot, a tree inventory and a climate zone, it returns a range
(`low`, `central`, `high`), a confidence grade, an evidence-readiness score and
the full list of parameters behind the number. A second entry point,
[`carbon_engine.age`](#carbon-by-tree-age), answers a different question: how
much carbon do N trees of a given age hold, and what does their age curve look
like?

Everything it returns is an estimate. `certified` is always `false` and every
result carries the disclaimer "Scenario estimate; not an issued carbon credit."
(see [carbon credit vs estimate](../../docs/concepts/carbon-credit-vs-estimate.md)).

## What it does and does not do

| It does | It does not |
| --- | --- |
| Compute annual removal ranges from IPCC 2006 Tier 1 gain-loss parameters, or from a measured diameter (Tier 2) | Issue, verify or certify anything |
| Read every number from `config/` with `source`, `unit` and `verification_status` | Hold coefficients in Python; a missing YAML key is a hard error |
| Refuse to run on `pending` parameters when pending values are not allowed | Touch the network, a clock-dependent random source or a language model |
| Report which evidence is still missing (readiness) | Decide programme eligibility (that is the [policy engine](../policy-engine/README.md)) |

Only one model is implemented: `tree-biomass`. The other ids
(`agroforestry`, `soil-carbon`, `crop-practice`) are typed stubs that raise
`ModelNotImplementedError` naming the authoritative sources a real
implementation would need. The API maps that error to HTTP 501.

## Install

```bash
python3 -m pip install -e packages/carbon-engine     # or: make install
```

The only runtime dependency is PyYAML. The engine finds `config/` through the
`ATLAS_CONFIG_DIR` environment variable, otherwise by walking up from the
package (and then from the working directory) until it finds
`config/species/species.yaml`.

## Public API

Import from `carbon_engine`:

| Name | Kind | Purpose |
| --- | --- | --- |
| `get_model(model_id="tree-biomass", store=None)` | function | Return a model instance; unknown ids raise `KeyError` |
| `TreeBiomassModel` | class | The v0.1 model; `estimate(plot, inventory, climate, params=None)` |
| `CarbonModel` | protocol | What every model implements: `id`, `version`, `estimate(...)` |
| `get_store(config_dir=None)`, `ParameterStore` | function, class | Cached loader for the parameter YAML files |
| `PlotInput`, `InventoryInput`, `ClimateInput`, `ModelParams` | dataclasses | Inputs |
| `CarbonEstimate`, `Range`, `SeriesPoint`, `ParameterUsed`, `Readiness`, `EvidenceItem`, `Methodology` | dataclasses | Outputs (`to_dict()` for JSON) |
| `score_readiness`, `confidence_for_inventory`, `confidence_from_fields` | functions | Readiness score and confidence grade |
| `assert_production_safe`, `worst_verification_status` | functions | Production guard over a list of `ParameterUsed` |
| `find_config_dir` | function | Locate `config/` |
| `DISCLAIMER`, `DEFAULT_MODEL_ID`, `IMPLEMENTED_MODEL_IDS`, `ALL_MODEL_IDS` | constants | |
| `CarbonEngineError`, `ModelInputError`, `ModelNotImplementedError`, `PendingParameterError`, `UnknownClimateZoneError`, `UnknownSpeciesError` | exceptions | |

The age module is imported by its own path, not from the package root:

| Name | Kind | Purpose |
| --- | --- | --- |
| `carbon_engine.age.assess_by_age(store, species_id, age_years, tree_count, climate, girth_cm=None, height_m=None, as_of_year=None, allow_pending=True, area_hectares=None)` | function | Carbon held now, annual removal now and the age curve |
| `AgeAssessment`, `AgeCurvePoint` | dataclasses | The result; `AgeAssessment.to_dict()` is the `carbon` block of the API's tree-age response |
| `METHOD_TIER1`, `METHOD_TIER2` | constants | `"tier1-age"` and `"tier2-girth"` |

### Example

```python
from carbon_engine import (
    ClimateInput,
    InventoryInput,
    ModelParams,
    PlotInput,
    get_model,
    get_store,
)

model = get_model("tree-biomass", get_store())
result = model.estimate(
    PlotInput(area_hectares=2.0, country="IN"),
    InventoryInput(species_id="mango", tree_count=300, plantation_year=2020),
    ClimateInput(zone="tropical_dry"),
    ModelParams(as_of_year=2026),
)

print(result.estimate.low, result.estimate.central, result.estimate.high, result.estimate.unit)
print(result.certified)  # always False
print(result.confidence)  # low | medium | high
print(result.readiness.score)  # 0-100, "how complete is the evidence file"
for p in result.parameters_used:  # every number behind the result
    print(p.name, p.value, p.unit, p.verification_status, p.source)
```

`result.to_dict()` is the JSON shape the API serves: `model`, `methodology`,
`estimate`, `stock`, `components`, `annual_series`, `parameters_used`,
`confidence`, `certified`, `disclaimer`, `readiness`, `provenance`, `notes`.

## How the number is produced (tree-biomass v0.1)

Methodology: 2006 IPCC Guidelines, Volume 4, Chapter 4 (Forest Land), Tier 1
gain-loss, plus the Chave et al. (2014) allometric equation for the measured
path. The module docstring in
[`models/tree_biomass.py`](carbon_engine/models/tree_biomass.py) is the
authoritative description; in short:

**Tier 1 (no diameter supplied).** For each year of the horizon (default 30)
the model grows the stand with

```text
ramp(age)         = min(age / years_to_full_increment, 1)
maturity(age)     = 1 while age <= maturity_years, otherwise post_maturity_increment_factor
density_factor    = clamp(planted_density / reference_density, 0.2, 1.5)
AGB increment     = growth(zone) x increment_multiplier x density_factor x ramp x maturity x survival
CO2e per year     = AGB increment x (1 + R) x carbon_fraction x 44/12 x area_ha
```

`R` is the root-to-shoot ratio selected by climate zone and accumulated
above-ground biomass class. `low` and `high` are `central` minus and plus a
fixed fraction (an assumption, shown in `parameters_used`). The headline
`estimate` is the **mean annual removal over the horizon**, not what the plot
removes this year; `stock` is the cumulative removal to `as_of_year`.

**Tier 2 (average DBH supplied).** Per-tree above-ground biomass
`AGB_kg = 0.0673 x (rho x D^2 x H)^0.976` (Chave et al. 2014 eq. 4), with
height taken from the inventory or estimated from the species' typical mature
height and the stand age. Stock is spread evenly over the stand age.

**Confidence** follows inventory completeness (high needs count, species, age,
DBH and height; medium needs count, species and age; otherwise low).
**Readiness** is `round(100 x weight present / total weight)` over the evidence
items in [`config/readiness.yaml`](../../config/readiness.yaml); grades are
high at 70 or more, medium at 40 or more, otherwise low. Readiness describes
the completeness of the evidence file, not eligibility.

## Carbon by tree age

`carbon_engine/age.py` is a thin layer over `TreeBiomassModel`. It turns an **age** into the inputs the model needs and
adds no coefficient of its own: every growth, wood-density, root-to-shoot, carbon-fraction and uncertainty value comes
from `config/` through the parameter store and is listed in `parameters_used` with its source and
`verification_status`.

```python
from carbon_engine import ClimateInput, get_store
from carbon_engine.age import assess_by_age

result = assess_by_age(
    get_store(),
    species_id="mango",
    age_years=60,
    tree_count=25,
    climate=ClimateInput(zone="tropical_dry"),
    girth_cm=188,  # optional: switches to the measured-tree path
)

print(result.method)  # tier2-girth (tier1-age without girth)
print(result.stored_now.central, result.stored_now.unit)  # carbon held now, tCO2e
print(result.annual_now.central)  # annual removal now, tCO2e per year
print(len(result.curve))  # at most 150 points: age, stored, stored_low, stored_high, annual
```

- **Age only (`method = "tier1-age"`).** The plantation year is `as_of_year - age` and the model runs for
  `max(age + 20, 40)` years, so the curve always reaches 20 years past today and covers at least 40 years.
  `stored_now` is the cumulative removal from planting to today, `annual_now` the removal in the current year. The
  confidence is always `low`, because nothing about the actual trees is measured.
- **Survival.** For `age >= 1` the trees are counted as alive today, so the run uses a survival rate of 1.0 and no
  mortality is applied a second time. For `age = 0` (trees being planned) the model's configured default survival stays.
- **Area.** Without `area_hectares` the trees are treated as a stand at the species' reference density (the density
  factor is exactly 1.0). With an area the model's own density factor applies. The API does not pass an area for
  scattered trees.
- **Measured trunk (`method = "tier2-girth"`).** `girth_cm` is the circumference at 1.3 m; `DBH = girth / pi` goes to
  the Tier 2 path (Chave et al. 2014, equation 4), with `height_m` when given. `stored_now` is the Tier 2 stock and
  `annual_now` is stock divided by age, a simplification that understates a young tree's current growth and overstates
  an old tree's. The curve still comes from the Tier 1 run (`curve_method = "tier1-age"`), so it can differ from
  `stored_now` at today's age. A diameter outside the 5 to 212 cm calibration range of the equation is flagged in
  `notes`.
- **Precision.** The model rounds to three decimals, which is coarse for a handful of trees, so it runs on identical
  copies of the stand and divides the result back. Tier 1 is linear in stand size at constant density, so nothing else
  changes.
- **Long lives.** The horizon always reaches the current age; when it reaches 150 years the curve is thinned to at most
  150 points, always keeping age 0, the current age and the last age.
- **Errors.** `ModelInputError` for out-of-domain input (negative age, fewer than one tree, girth with age 0),
  `UnknownSpeciesError`, `UnknownClimateZoneError`, and `PendingParameterError` when `allow_pending` is false and a used
  parameter is still `pending`.

The result is never certified. The rules that apply to trees of a given age (felling permits, programme eligibility) are
a separate question answered by the [policy engine](../policy-engine/README.md#tree-age-rules); the model and its
limits are explained in the [tree-age model](../../docs/architecture/tree-age-model.md).

## Parameters and verification status

Parameters live in:

- [`config/methodologies/ipcc-2006-tier1.yaml`](../../config/methodologies/ipcc-2006-tier1.yaml): constants,
  root-to-shoot ratios, Tier 1 growth, allometry registry, behaviour assumptions
- [`config/methodologies/tree-biomass-model.yaml`](../../config/methodologies/tree-biomass-model.yaml): horizon,
  post-maturity factor, Tier 2 extrapolation
- [`config/species/species.yaml`](../../config/species/species.yaml): per-species density, height, wood density,
  increment multiplier
- [`config/readiness.yaml`](../../config/readiness.yaml): evidence weights

Each carries `verification_status`: `verified`, `pending` or `assumption`.
`ModelParams(allow_pending_parameters=False)` makes the engine raise
`PendingParameterError` when a used parameter is `pending`. The API sets this
from `ATLAS_ALLOW_PENDING_PARAMETERS` (ignored in production, where pending is
always refused). How to add or verify a parameter:
[adding-a-parameter](../../docs/developer-guide/adding-a-parameter.md).

Known limits, all visible in the output notes:

- Temperate species nominate the `temperate_generic` allometry, which has no
  verified equation yet; Tier 2 then falls back to the pantropical Chave 2014
  equation outside its calibration domain and says so in `notes`.
- The uncertainty fractions are project assumptions, not statistical
  confidence intervals.
- Tier 2 divides stock by age; it is a simplification, flagged as an assumption.

## Tests

```bash
python3 -m pytest packages/carbon-engine -q            # this package
python3 -m pytest tests/data-quality -q                # config invariants
ATLAS_ENV=production ATLAS_ALLOW_PENDING_PARAMETERS=false \
  python3 -m pytest tests/data-quality -q              # production gate
```

| File | Covers |
| --- | --- |
| `tests/test_allometric.py` | Chave 2014 with and without height, monotonicity, bad inputs |
| `tests/test_parameters_readiness_confidence.py` | Config discovery, citation of every parameter, root-to-shoot classes, production guard, readiness and confidence |
| `tests/test_tree_biomass.py` | Hand-computed Tier 1 and Tier 2 cases, bounds ordering, survival scaling, pending-parameter refusal, stubs, `to_dict` shape |
| `tests/test_age.py` | `assess_by_age`: a hand-computed girth case, curve length, ordering and thinning, age 0, survival basis, equality with the tree-biomass model, per-tree totals, calibration warning, pending parameters, input errors, every species |

A new calculation needs a test with a reference value written down together
with its source and tolerance.

## Design notes

- Pure functions of inputs and configuration: same input, same output.
- No business rule about a country lives here; region and programme logic is in
  `config/` and the policy engine.
- Every output is a range with provenance; there is no code path that returns
  a single number without `parameters_used`.

## Links

- [Carbon engine architecture](../../docs/architecture/carbon-engine.md)
- [Tree-age model](../../docs/architecture/tree-age-model.md)
- [Adding a parameter or a species](../../docs/developer-guide/adding-a-parameter.md)
- [Methodology notes per region](../../docs/regions/IN/METHODOLOGIES.md)
- [CLAUDE.md](../../CLAUDE.md), principles 1, 3, 4, 9, 10, 12 and 13
