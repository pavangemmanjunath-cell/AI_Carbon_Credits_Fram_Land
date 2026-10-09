# Carbon engine

`packages/carbon-engine` turns a plot area, a climate zone and a tree
inventory into an **estimated annual carbon removal** expressed as a range
in tCO₂e/yr, together with the cumulative stock, the parameters that were
used, a confidence grade and a readiness score. It is deterministic,
configuration-driven and cites its methodology on every result. It is not
a crediting tool; the final section says what it is not.

## Model interface

Every model implements the same protocol so that the API, the simulation
endpoint and the validation scripts can call any registered model
identically.

```python
class CarbonModel(Protocol):
    id: str  # "tree-biomass"
    version: str  # "0.1.0"
    tier: Literal["1", "2"]
    methodology_id: str  # key in config/methodologies/registry.yaml

    def estimate(self, inputs: ModelInputs, params: ParameterSet) -> ModelResult: ...


@dataclass(frozen=True)
class ModelInputs:
    area_hectares: float
    climate_zone: str  # e.g. "tropical_dry" (IPCC zone)
    climate_zone_source: Literal["plot-normals", "region-default"]
    species: SpeciesEntry  # from config/species/species.yaml
    tree_count: int
    plantation_year: int
    reference_year: int  # usually the current year
    horizon_years: int  # for the annual series
    survival_rate: float | None
    average_dbh_cm: float | None
    average_height_m: float | None
    measurement_source: str
    evidence: EvidenceFlags  # polygon, satellite, baseline, management…


@dataclass(frozen=True)
class ModelResult:
    estimate: Range  # tCO2e/yr for the reference year
    stock: Range  # tCO2e accumulated to the reference year
    components: dict[str, float]  # above_ground_tco2e_yr, below_ground_tco2e_yr
    annual_series: list[YearRow]  # year, age, low/central/high, cumulative
    parameters_used: list[ParameterUse]
    confidence: Literal["low", "medium", "high"]
    readiness: Readiness
    tier: str
    notes: list[str]
```

`ParameterSet` is loaded from `config/methodologies/ipcc-2006-tier1.yaml`
and `config/species/species.yaml`; each value arrives with `unit`,
`source` and `verification_status`, and every value the model touches is
echoed in `parameters_used`. The engine has no numeric literals of its
own except unit conversions.

## Tier 1 — gain-loss method

The default path follows the IPCC 2006 Guidelines, Volume 4 (AFOLU),
Chapter 2 equations 2.9–2.10 and the Chapter 4 default tables
(<https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html>), as refined
in 2019 (<https://www.ipcc-nggip.iges.or.jp/public/2019rf/vol4.html>).
The annual carbon gain in living biomass is

$$
\Delta C = A \times G_{\text{total}} \times CF,
\qquad
G_{\text{total}} = G_w \times (1 + R),
$$

where $A$ is the area (ha), $G_w$ the above-ground net biomass growth
(t d.m. ha⁻¹ yr⁻¹) for the climate zone and age class, $R$ the
root-to-shoot ratio (dimensionless) and $CF$ the carbon fraction of dry
matter (0.47 t C per t d.m., Table 4.3). Carbon is converted to carbon
dioxide equivalent with the molecular mass ratio

$$
\text{CO}_2\text{e} = C \times \frac{44}{12}.
$$

The engine applies three adjustments on top of the broad-category
increment, each of them a documented project assumption rather than an
IPCC value:

| Adjustment | Formula | Parameter (config) | Rationale |
|---|---|---|---|
| Species multiplier | $G_w' = G_w \cdot m_{sp}$ | `species.<id>.increment_multiplier` | Pruned orchards grow slower than natural stands; fast-growing plantations faster. Values are `assumption` or `pending` until replaced by Table 4.10/4.12 entries. |
| Density scaling | $f_d = \operatorname{clamp}\!\left(\dfrac{N \cdot s / A}{d_{\text{ref}}},\,0.2,\,1.5\right)$ | `assumptions.density_scaling.clamp`, `species.<id>.reference_density_per_ha` | Per-hectare increments assume a typical stocking; the clamp prevents absurd results for very sparse or very dense plantings. $s$ is the survival rate (default 0.85). |
| Ramp-up | $f_t(a) = \min\!\left(1,\,\dfrac{a}{T_{\text{ramp}}}\right)$ | `assumptions.years_to_full_increment_default` (6 yr) | Newly planted trees do not accumulate at the mature-stand rate; a linear ramp is the simplest defensible shape. |

so that for a stand of age $a$

$$
\Delta C(a) = A \times \big[\,G_w \, m_{sp} \, f_d \, f_t(a)\,\big] \times (1 + R) \times CF .
$$

$R$ is selected from Table 4.4 by climate zone and by the standing
above-ground biomass per hectare, which the engine tracks cumulatively
year by year (for example tropical dry: 0.56 below 20 t d.m./ha, 0.28
above). The annual series runs from the planting year to the horizon;
the stock is the running sum of annual gains. No loss term (harvest,
disturbance, mortality beyond the survival rate) is modelled in v0.1, and
the result says so in `notes`.

### Worked example (v0.1 working values)

India example farm: $A$ = 2.13 ha, 420 mango, survival 0.85, climate
`tropical_dry`. Effective density 420 × 0.85 / 2.13 = 167.6 trees/ha
against a reference of 150 → $f_d$ = 1.12. $G_w$ = 4.0 t d.m./ha/yr
(working value, `pending`), $m_{sp}$ = 0.9, $R$ = 0.56, $CF$ = 0.47.

At full increment ($a \geq 6$): 2.13 × (4.0 × 0.9 × 1.12) × 1.56 × 0.47 =
6.3 t C/yr → **23.0 tCO₂e/yr** (range 16.1–29.9 with ±30 %). At age 3 the
ramp halves it to about 11.5 tCO₂e/yr. The numbers move when the
`pending` increment is verified against Table 4.12, which is precisely why
they are shown as a range with their sources.

## Tier 2 — allometry when measurements exist

When the inventory carries a mean diameter at breast height (and
optionally height), the engine estimates standing above-ground biomass per
tree with the pantropical model of Chave et al. (2014), equation 4
(<https://doi.org/10.1111/gcb.12629>):

$$
AGB_{\text{kg}} = 0.0673 \times \left(\rho \, D^{2} \, H\right)^{0.976},
$$

with wood density $\rho$ in g cm⁻³ (`species.<id>.wood_density_g_cm3`,
working values from the Global Wood Density Database, Zanne et al. 2009,
<https://doi.org/10.5061/dryad.234>), $D$ in cm and $H$ in m. When height
is missing, v0.1 uses the species' typical height scaled by the ramp
rather than equation 7 (which needs the bioclimatic stress raster $E$):

$$
AGB_{\text{kg}} = \exp\!\big(-1.803 - 0.976E + 0.976\ln\rho + 2.673\ln D - 0.0299[\ln D]^{2}\big).
$$

Stand stock follows as $N \cdot s \cdot AGB / 1000$ t d.m., below-ground
biomass through $R$, carbon through $CF$, and CO₂e through 44/12. The
annual figure on the Tier 2 path is the mean annual increment (stock
divided by age) cross-checked against the Tier 1 increment; a large
disagreement is reported in `notes` and lowers confidence. The
`temperate_generic` allometry key is still `pending` in v0.1: for
temperate species the engine falls back to the Tier 1 path and says so.

## Uncertainty bounds

Ranges are symmetric fractions of the central value:
$\text{low} = c(1-u)$, $\text{high} = c(1+u)$ with $u$ = 0.30 on the
Tier 1 path and 0.20 on the Tier 2 path
(`assumptions.uncertainty_fraction_*`). These are placeholders until the
Monte Carlo study in
[../../research/notebooks/README.md](../../research/notebooks/README.md)
replaces them with propagated intervals; the IPCC guidance on Tier 1
uncertainty (Chapter 4, section 4.2.1.4) is the reference the replacement
must cite. Low and high are reported for the annual estimate, the stock
and every row of the annual series.

## Confidence grading

The grade combines data quality and parameter quality:

1. Start from the inventory confidence defined in the API contract: `high`
   when count, species, age, DBH and height are supplied; `medium` when
   count, species and age are supplied; otherwise `low`.
2. Cap at `medium` while any entry in `parameters_used` has
   `verification_status` other than `verified`.
3. Lower one grade when the climate zone came from the regional default
   (`climate_zone_source = region-default`) because no analysis was
   available, or when the Tier 2 cross-check disagrees with Tier 1 by more
   than a factor of two.

In v0.1 nothing can reach `high`, because growth increments and wood
densities are `pending`; that is the intended behaviour.

## Readiness scoring

Readiness answers a different question from confidence: not "how good is
this number" but "how far is this plot from the evidence a programme would
ask for". Items and weights sum to 100:

| Evidence item | Weight | Source of the flag |
|---|---|---|
| Land polygon | 16 | plot exists |
| Tree count and species | 16 | inventory |
| Plantation age | 16 | inventory |
| Satellite observation | 16 | analysis with vegetation block |
| Tree diameter (and height) measurements | 15 | inventory `average_dbh_cm` |
| Baseline land-use records | 12 | user-supplied documents (planned) or WorldCover history |
| Farm management history | 9 | user-supplied (planned) |

Grades: `low` < 40, `medium` 40–74, `high` ≥ 75. The example in the API
contract (polygon, count, age, satellite present; DBH, baseline,
management missing) scores 64, `medium`. Missing items are returned with
their weights so the UI can show what closes the gap.

## Parameter provenance and `verification_status`

Every parameter carries one of three statuses, and the semantics are
enforced, not advisory:

| Status | Meaning | Behaviour |
|---|---|---|
| `verified` | A maintainer checked the value against the cited table cell or equation and recorded who and when | Used freely |
| `pending` | Copied from working notes or a secondary source; must be checked before release | Allowed in development; **refused** when `ATLAS_ENV=production` and `ATLAS_ALLOW_PENDING_PARAMETERS=false` (HTTP 409 `pending-parameters` naming the parameter); a data-quality test fails in production mode |
| `assumption` | A project assumption, not a literature value | Allowed, but always listed in `parameters_used` and in the report's assumptions section |

The `provenance.parameter_set.verification_status` of a result is the
worst status among the parameters used. Changing a status to `verified`
is a reviewed pull request that names the source document
([../developer-guide/adding-a-species-or-parameter.md](../developer-guide/adding-a-species-or-parameter.md#verifying-a-pending-parameter)).

## Validation status

The protocol and acceptance criteria are in
[../../research/validation/README.md](../../research/validation/README.md).
As of v0.1 only Level 1 (implementation against hand calculation) is
automated in the test suite; Level 2 (COMET-Farm) and Level 3 (field data)
results will be summarized here when available.

## What this engine is not

- **Not a crediting methodology.** It does not compute a baseline scenario,
  additionality, leakage or a permanence buffer, all of which a registry
  methodology requires ([../concepts/](../concepts/carbon-credit-vs-estimate.md)).
- **Not species-accurate.** Tier 1 uses broad climate-zone increments
  with multipliers that are mostly assumptions.
- **Not a soil carbon model.** Soil organic carbon from SoilGrids is
  context, not a modelled flux.
- **Not a measurement.** Satellite indices describe vegetation vigor; they
  do not measure biomass. Field measurements are what move a result from
  Tier 1 to Tier 2.
- **Not certified, ever.** `certified` is a constant `false` in the schema
  (`data/schemas/carbon-estimate.schema.json`); a registry-issued serial
  number is the only thing that changes that, and it is not produced here.
