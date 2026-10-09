# Methodologies — United States

This page explains how the Atlas estimates carbon for a plot in the United States, where that estimate is weakest for
US trees, and how it differs from what a USDA tool or a voluntary-market project would produce. The Atlas
**references** methodologies; it never **applies** one, and nothing here turns an estimate into a credit
([carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md)).

Statements about rules carry a source link. A statement we could not confirm against the primary document is marked
*(unverified)*. The programs and standards themselves are described in [PROGRAMS.md](PROGRAMS.md); the research behind
this page is in [policy-references.md](../../research/policy-references.md).

## At a glance

| Question | Answer |
| --- | --- |
| What does the Atlas calculate for a US plot? | A scenario of the carbon the trees you describe remove each year, as a range, from the IPCC 2006 Tier 1 gain-loss method, or from a trunk-diameter equation when you give an average diameter |
| What is the weak point for US trees? | The diameter equation (Chave et al. 2014) was built for tropical trees. The equation the config names for US species, `temperate_generic`, has no verified equation yet, so the tropical one is used and the result says so |
| Is the number comparable to COMET-Planner or COMET-Farm? | Not directly: different time window, pools, models and units ([below](#comparing-with-other-us-tools)) |
| Which methodologies could a project use? | Verra VM0047 for new planting, VM0042 for farming practices, and protocols for existing forest ([PROGRAMS.md](PROGRAMS.md#voluntary-market-methodologies)) |

## What the Atlas calculates

The model is `tree-biomass` version 0.1 in [`packages/carbon-engine`](../../../packages/carbon-engine/README.md), the same
for every region. Every number comes from [`config/`](../../../config/) with a source, a unit and a verification
status.

- **Without a trunk diameter (Tier 1).** For each year from planting to 30 years later, the model takes the
  above-ground growth for the climate zone, adjusts it for the species, for planting density against a reference
  density, for a six-year ramp-up, for slower growth after the species' maturity age and for survival, adds the roots
  with a root-to-shoot ratio, and converts carbon to carbon dioxide with the carbon fraction and 44/12. The headline is
  the **mean annual removal over the 30 years**, not this year's removal.
- **With an average trunk diameter (Tier 2).** The model estimates one tree's biomass from diameter, height and wood
  density with Chave et al. (2014) equation 4, multiplies by the surviving trees, adds roots and divides the stock by the
  stand age.
- **The range.** Low and high are the central value less and plus 30% (Tier 1) or 20% (Tier 2). These are project
  assumptions, not statistical confidence intervals.
- **What is included.** Living above-ground and below-ground biomass of the trees you described. Not dead wood, litter,
  soil carbon, harvested wood products or management emissions, and no baseline, leakage or reversal buffer is
  subtracted ([additionality](../../concepts/additionality.md), [permanence](../../concepts/permanence.md)).

### Parameters that matter for the US

Values are the working values in `config/` version 0.1.0 at the time of writing; the files are authoritative. **Pending**
means copied from the cited source and not yet checked by a reviewer, so every estimate in version 0.1 is preliminary.

| Parameter | Working value | Status | Source recorded in the config |
| --- | --- | --- | --- |
| Carbon fraction | 0.47 t C per t d.m. | verified | IPCC 2006 Vol. 4 Ch. 4 Table 4.3 |
| Carbon to carbon dioxide | 44/12 (3.6667) | verified | Molecular mass ratio |
| Per-tree biomass | AGB (kg) = 0.0673 × (ρ × D² × H)^0.976 | verified | Chave et al. 2014, equation 4 (tropical and subtropical broadleaf trees) |
| Root-to-shoot ratio, temperate zones | 0.46 below 75 t d.m./ha above-ground, 0.23 from 75 to 150, 0.24 above 150 | pending | IPCC 2006 Table 4.4 |
| Survival, ramp-up, density limits, post-maturity factor, horizon, uncertainty | 0.85; 6 years; 0.2 to 1.5; 0.5; 30 years; 30% and 20% | assumption | Project assumptions v0.1 |

Working above-ground growth values (t d.m./ha/yr, all pending, from IPCC 2006 Tables 4.10 and 4.12 as recorded in the
config) for the zones a US plot is likely to be classified into:

| Climate zone | Growth | Range | Note |
| --- | --- | --- | --- |
| `warm_temperate_moist` | 7.0 | 3.0 to 11.0 | The US default zone |
| `warm_temperate_dry` | 4.0 | 2.0 to 6.0 | |
| `cool_temperate_moist` | 4.0 | 2.0 to 7.0 | |
| `cool_temperate_dry` | 3.0 | 1.5 to 5.0 | |
| `subtropical_humid` | 7.0 | 3.0 to 11.0 | Never chosen automatically |

The server classifies a plot from mean annual temperature, annual precipitation and elevation with an approximation of
the IPCC 2006 decision tree, marked as an assumption in the output
([`zones.py`](../../../packages/geo-engine/geo_engine/climate/zones.py)). A point above 18 °C mean annual temperature is
classed as tropical; none of the US species except eucalyptus lists a tropical zone as suitable, so the result then
carries a note that the zone does not suit the species. Without live normals the **Evidence chain** says
"region-default".

### Species available for the US

From [`config/species/species.yaml`](../../../config/species/species.yaml) version 0.1.0. Densities are per hectare;
divide by 2.47 for trees per acre. Maturity ages and densities are bare numbers in the file, which the engine reports as
project assumptions.

| Species | Equation key | Wood density, g/cm³ (pending) | Reference density, trees/ha | Maturity, years | Increment multiplier |
| --- | --- | --- | --- | --- | --- |
| Black walnut (*Juglans nigra*) | `temperate_generic` | 0.51 | 300 | 30 | 1.0, verified (Tier 1 broad category used directly) |
| Pecan (*Carya illinoinensis*) | `temperate_generic` | 0.60 | 70 | 12 | 0.9, assumption |
| Eucalyptus (*Eucalyptus* spp.) | `pantropical_chave_2014_with_height` | 0.60 | 1,100 | 8 | 1.5, pending: IPCC Table 4.10 lists eucalyptus separately, verify and replace |
| Apple (*Malus domestica*) | `temperate_generic` | 0.61 | 600 | 7 | 0.6, assumption (dwarfing rootstocks and pruning) |
| Poplar (*Populus* spp.) | `temperate_generic` | 0.35 | 500 | 10 | 1.6, pending |

Wood densities are working values from the [Global Wood Density Database](https://doi.org/10.5061/dryad.234) and must be
checked against the database before release. The Tier 1 growth tables are for broad forest categories, not orchards, so
the multipliers for fruit and nut trees are project assumptions that stand in for pruning and rootstock effects.

## The temperate allometry gap

Four of the five US species nominate the allometry `temperate_generic`, which has **no equation yet**. When you enter an
average trunk diameter, the engine therefore applies Chave et al. (2014) equation 4 to a walnut, pecan, apple or poplar
tree. That equation was fitted to tropical trees, and the result lists the substitution in its notes: "Chave et al. 2014
eq. 4 was applied outside its pantropical calibration domain". Treat a diameter-based number for these species as a
rough cross-check, not a better number than the Tier 1 range, until the gap is closed.

The config names the candidate to fill the gap for North America: Chojnacky et al. (2014), with the exact citation,
species groups and coefficients still to be verified
([`ipcc-2006-tier1.yaml`](../../../config/methodologies/ipcc-2006-tier1.yaml)). TODO(verify): confirm the citation and
each coefficient against the paper, add the equation to the config with `verification_status: pending`, write a
hand-computed test, and only then mark it verified
([adding a parameter or equation](../../developer-guide/adding-a-species-or-parameter.md#a-new-parameter-or-equation)).

## Trees of a known age

The **Tree age** page and `POST /api/v1/tree-age/assess` ask a different question from a plot estimate: "I have N trees
of this species that are A years old. How much carbon do they hold now, and how fast are they adding more?" They use
the same `tree-biomass` model and the same `config/` parameters, so every value appears in `parameters_used` with its
source and verification status ([`carbon_engine/age.py`](../../../packages/carbon-engine/carbon_engine/age.py)).

| You enter | Method | What you get |
| --- | --- | --- |
| Age only | `tier1-age`: the Tier 1 model runs from the planting year to 20 years beyond today (at least 40 years in all) | Carbon stored so far (the sum of the removals since planting) and this year's removal, each as low, central and high, plus an age curve |
| Age and trunk girth | `tier2-girth`: diameter is girth divided by π and goes to the Tier 2 equation (Chave et al. 2014, equation 4); a height makes the grade higher | Stored carbon from the equation, and an annual figure that is the stock divided by the age. That simplification understates a young tree's growth and overstates an old tree's |

Trees you count as alive today are not reduced by the default survival rate a second time, because their deaths are
already in the count. Trees you are only planning (age 0) are. The temperate gap above applies to the girth path for
walnut, pecan, apple and poplar. Stored carbon is not carbon a program would credit: every result says `certified:
false`, and the rules in [PROGRAMS.md](PROGRAMS.md#rules-by-tree-age) show how programs treat trees that already
stand.

## Comparing with other US tools

| Tool | Time window | Pools | Basis |
| --- | --- | --- | --- |
| Atlas | Mean annual removal over 30 years (Tier 1), or stock divided by age (Tier 2) | Living above-ground and below-ground biomass | IPCC 2006 Tier 1 working values, Chave et al. 2014 |
| COMET-Planner v4.0 | 10-year averages | Standing tree carbon only, without dead wood or litter | Diameter-from-age models by taxon group and Land Resource Region from FIA data ([COMET-Planner report](https://comet-planner.com/api/resource/pdf/COMET-Planner_Report.pdf)) |
| COMET-Farm | Set by the tool | Agroforestry assessments use tree numbers and sizes with FIA-based growth equations *(unverified; the site could not be opened)* | [comet-farm.com](https://comet-farm.com/) |

Before you compare numbers, check acres or hectares, metric or short tons (one short ton is about 0.907 metric tons),
tons of carbon or of CO₂ (multiply carbon by 44/12 for CO₂), the time window, and the trees entered.

## What a real project asks for that the Atlas does not do

| Step | Why it matters |
| --- | --- |
| Baseline | Credit standards reward what happens beyond the baseline, not the carbon trees already hold ([research note](../../research/tree-age-carbon-rules.md#key-finding)) |
| Additionality, leakage, permanence | Required by every methodology listed in [PROGRAMS.md](PROGRAMS.md); commitments run from 20 to 100 years in the protocols the research reviewed |
| Monitoring | Measured sample plots, remote sensing and repeated field visits, not a model |
| Verification and registry issuance | By an accredited third party; only then does a credit exist |

## Measuring to improve the estimate

- **Diameter.** Measure trunk diameter at breast height on a sample of at least 30 trees and enter the average. The app
  advises 1.3 m above the ground. Some US programs and ordinances specify another height, for example 4.5 feet in the Los
  Angeles ordinance ([Los Angeles](https://planning.lacity.gov/odocument/555281f6-f5ef-44e9-b094-1fce25c1c4dc)); follow
  the one your program requires. If you measure in inches, multiply by 2.54 to get centimeters; if you have the girth
  (around the trunk), divide by π.
- **Height.** Add the average height; with diameter and height together the confidence grade becomes high.
- **Survival.** Count trees that died or were removed each year; the default of 0.85 is an assumption.
- **Records.** Keep records of the land's use before planting, management history and dated photographs. Programs usually
  ask for these, and the app has no place to store them ([results explained](../../user-guide/results-explained.md#carbon-readiness)).

## For reviewers: open items

| Item | What to do |
| --- | --- |
| Temperate allometry | Verify and add an equation for the `temperate_generic` species ([adding a parameter or equation](../../developer-guide/adding-a-species-or-parameter.md#a-new-parameter-or-equation)) |
| IPCC Tables 4.4, 4.10 and 4.12 | Check each pending value cell by cell, including the temperate zones |
| Wood densities and multipliers | Check each US species against the Global Wood Density Database; replace the eucalyptus and poplar working multipliers with table values |
| Default climate zone | One zone for a whole country is coarse; consider whether a documented rule can replace it when live normals are missing |
| COMET-Farm agroforestry module | Confirm from a USDA document |
| Price scenario | The US scenario is `pending` ([`carbon-price-scenarios.yaml`](../../../config/market/carbon-price-scenarios.yaml)) |

## Related pages

[README.md](README.md) · [PROGRAMS.md](PROGRAMS.md) · [DATA_SOURCES.md](DATA_SOURCES.md) ·
[India methodologies](../IN/METHODOLOGIES.md) · [Carbon engine notes](../../architecture/carbon-engine.md)
