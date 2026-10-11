# Methodologies — European Union

This page explains how CarbonCreditBuy estimates carbon for a plot in the European Union, where that estimate is weakest
for
European trees, and how far it is from what a certification under the CRCF requires. CarbonCreditBuy **references**
methodologies; it never **applies** one, and nothing here turns an estimate into a certified unit
([carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md)).

Statements about rules carry a source link. A statement we could not confirm against the primary document is marked
*(unverified)*. The programs themselves are described in [PROGRAMS.md](PROGRAMS.md); the research behind this page is
in [policy-references.md](../../research/policy-references.md).

## At a glance

| Question | Answer |
| --- | --- |
| What does CarbonCreditBuy calculate for an EU plot? | A scenario of the carbon the trees you describe remove each year, as a range, from the IPCC 2006 Tier 1 gain-loss method, or from a trunk-diameter equation when you give an average diameter |
| Is that what the CRCF certifies? | No. The CRCF certifies a net benefit above a baseline, over an activity period of at least five years, with monitoring and verification by a recognized scheme. CarbonCreditBuy does none of these ([below](#the-crcf-compared-with-a-carboncreditbuy-estimate)) |
| Is there a CRCF methodology for agroforestry? | The Commission adopted carbon-farming certification methodologies on 10 July 2026, including agriculture and agroforestry on mineral soils and afforestation. They were not confirmed in force as of 2026-10-05 ([Commission news](https://climate.ec.europa.eu/news-other-reads/news/commission-adopts-certification-methodologies-carbon-farming-under-crcf-regulation-2026-07-10_en)) |
| What is the weak point for European trees? | The diameter equation was built for tropical trees, and the zone CarbonCreditBuy assumes without live climate data may not suit olive or eucalyptus ([below](#the-temperate-allometry-gap)) |

## What CarbonCreditBuy calculates

The model is `tree-biomass` version 0.1 in [`packages/carbon-engine`](../../../packages/carbon-engine/README.md), the
same
for every region. Every number comes from [`config/`](../../../config/) with a source, a unit and a verification
status.

- **Without a trunk diameter (Tier 1).** For each year from planting to 30 years later, the model takes the
  above-ground growth for the climate zone, adjusts it for the species, for planting density against a reference
  density, for a six-year ramp-up, for slower growth after the species' maturity age and for survival, adds the roots
  with a root-to-shoot ratio, and converts carbon to carbon dioxide with the carbon fraction and 44/12. The headline is
  the **mean annual removal over the 30 years**, not this year's removal.
- **With an average trunk diameter (Tier 2).** The model estimates one tree's biomass from diameter, height and wood
  density with Chave et al. (2014) equation 4, multiplies by the surviving trees, adds roots and divides the stock by
  the
  stand age.
- **The range.** Low and high are the central value less and plus 30% (Tier 1) or 20% (Tier 2). These are project
  assumptions, not statistical confidence intervals.
- **What is included.** Living above-ground and below-ground biomass of the trees you described. Not dead wood, litter,
  soil carbon, harvested wood products or management emissions, and no baseline, leakage or reversal buffer is
  subtracted ([additionality](../../concepts/additionality.md), [permanence](../../concepts/permanence.md)).

### Parameters that matter for the EU

Values are the working values in `config/` version 0.1.0 at the time of writing; the files are authoritative.
**Pending**
means copied from the cited source and not yet checked by a reviewer, so every estimate in version 0.1 is preliminary.

| Parameter | Working value | Status | Source recorded in the config |
| --- | --- | --- | --- |
| Carbon fraction | 0.47 t C per t d.m. | verified | IPCC 2006 Vol. 4 Ch. 4 Table 4.3 |
| Carbon to carbon dioxide | 44/12 (3.6667) | verified | Molecular mass ratio |
| Per-tree biomass | AGB (kg) = 0.0673 × (ρ × D² × H)^0.976 | verified | Chave et al. 2014, equation 4 (tropical and subtropical broadleaf trees) |
| Root-to-shoot ratio, temperate zones | 0.46 below 75 t d.m./ha above-ground, 0.23 from 75 to 150, 0.24 above 150 | pending | IPCC 2006 Table 4.4 |
| Survival, ramp-up, density limits, post-maturity factor, horizon, uncertainty | 0.85; 6 years; 0.2 to 1.5; 0.5; 30 years; 30% and 20% | assumption | Project assumptions v0.1 |

Working above-ground growth values (t d.m./ha/yr, all pending, from IPCC 2006 Tables 4.10 and 4.12 as recorded in the
config) for the zones an EU plot is likely to be classified into:

| Climate zone | Growth | Range | Note |
| --- | --- | --- | --- |
| `cool_temperate_moist` | 4.0 | 2.0 to 7.0 | The EU default zone |
| `cool_temperate_dry` | 3.0 | 1.5 to 5.0 | |
| `warm_temperate_moist` | 7.0 | 3.0 to 11.0 | |
| `warm_temperate_dry` | 4.0 | 2.0 to 6.0 | |
| `boreal` | 1.5 | 0.5 to 3.0 | No species in the EU table lists boreal as suitable |
| `subtropical_dry` | 4.0 | 2.0 to 6.0 | Never chosen automatically; olive lists it as suitable |

The server classifies a plot from mean annual temperature, annual precipitation and elevation with an approximation of
the IPCC 2006 decision tree, marked as an assumption in the output
([`zones.py`](../../../packages/geo-engine/geo_engine/climate/zones.py)). Without live normals the **Evidence chain**
says
"region-default" and the default zone is used for every EU plot. That zone is not on the suitable list for **olive** or
**eucalyptus**, so their results then carry a note that the zone does not suit the species; oak, apple and poplar do
list it.

### Species available for the EU

From [`config/species/species.yaml`](../../../config/species/species.yaml) version 0.1.0. Maturity ages and densities
are bare numbers in the file, which the engine reports as project assumptions.

| Species | Equation key | Wood density, g/cm³ (pending) | Reference density, trees/ha | Maturity, years | Increment multiplier |
| --- | --- | --- | --- | --- | --- |
| Oak (*Quercus robur*, *Q. petraea*) | `temperate_generic` | 0.56 | 400 | 40 | 1.0, verified (Tier 1 broad category used directly) |
| Apple (*Malus domestica*) | `temperate_generic` | 0.61 | 600 | 7 | 0.6, assumption (dwarfing rootstocks and pruning) |
| Olive (*Olea europaea*) | `temperate_generic` | 0.80 | 250 | 12 | 0.7, assumption |
| Eucalyptus (*Eucalyptus* spp.) | `pantropical_chave_2014_with_height` | 0.60 | 1,100 | 8 | 1.5, pending: IPCC Table 4.10 lists eucalyptus separately, verify and replace |
| Poplar (*Populus* spp.) | `temperate_generic` | 0.35 | 500 | 10 | 1.6, pending |

Wood densities are working values from the [Global Wood Density Database](https://doi.org/10.5061/dryad.234) and must be
checked against the database before release. The Tier 1 growth tables are for broad forest categories, not orchards, so
the multipliers for fruit trees are project assumptions that stand in for pruning and rootstock effects.

## The temperate allometry gap

Four of the five EU species nominate the allometry `temperate_generic`, which has **no equation yet**. When you enter an
average trunk diameter, the engine therefore applies Chave et al. (2014) equation 4 to an oak, apple, olive or poplar
tree. That equation was fitted to tropical trees, and the result lists the substitution in its notes: "Chave et al. 2014
eq. 4 was applied outside its pantropical calibration domain". Treat a diameter-based number for these species as a
rough cross-check, not a better number than the Tier 1 range, until the gap is closed.

The config names the candidate for Europe: Forrester et al. (2017), with the exact citation, species groups and
coefficients still to be verified ([`ipcc-2006-tier1.yaml`](../../../config/methodologies/ipcc-2006-tier1.yaml)).
TODO(verify): confirm the citation and each coefficient against the paper, add the equation to the config with
`verification_status: pending`, write a hand-computed test, and only then mark it verified
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
oak, apple, olive and poplar. Stored carbon is not carbon a program would credit: every result says `certified:
false`, and the rules in [PROGRAMS.md](PROGRAMS.md#rules-by-tree-age) show how programs treat trees that already
stand.

## The CRCF compared with a CarbonCreditBuy estimate

The right-hand column comes from a research reading of Regulation (EU) 2024/3012. Article numbers can carry
transcription errors, so open the text before you quote it ([EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/3012/oj)).

| Topic | What the CRCF requires | What CarbonCreditBuy does |
| --- | --- | --- |
| Quantity | A net carbon-farming benefit: total removals minus baseline removals and associated emissions (Article 4) | Gross growth of the trees you describe; no baseline, no associated emissions |
| Additionality | Goes beyond Union and national statutory requirements and relies on the incentive effect of certification (Article 5) | Not assessed |
| Period | An activity period of at least five years (Article 2(10)) and monitoring for at least that period, with liability for releases during monitoring (Article 6) | A 30-year scenario with no monitoring |
| Verification and registry | Certification by a recognized scheme and certification body; a Union registry is planned for 2028 | None. `certified` is always false |
| Unit | Carbon farming units are temporary and are distinct from permanent removal units | A range in tCO₂e/yr and a stock in tCO₂e, not a unit |

Sources for the unit types and the registry are in [PROGRAMS.md](PROGRAMS.md#the-crcf). The Regulation's text does not
address existing carbon stocks explicitly; treating them as part of the baseline follows from the net-benefit formula
([research note](../../research/tree-age-carbon-rules.md#european-union)). CarbonCreditBuy's own wording is the sentence
on
every EU result: an estimate is never automatically certifiable.

## Other methodologies a project could use

See [PROGRAMS.md](PROGRAMS.md#voluntary-standards-and-national-labels) for Verra VM0047, the Gold Standard afforestation
and reforestation requirements and the French Label Bas-Carbone. The Gold Standard requires that the planting area was
not
forest for 10 years before the project start, and the research found that standards credit new removals against a
baseline, not the carbon existing trees already hold ([research
note](../../research/tree-age-carbon-rules.md#key-finding)).

## Measuring to improve the estimate

- **Diameter.** Measure trunk diameter at breast height, 1.3 m above the ground, on a sample of at least 30 trees, and
  enter the average. Many European tree rules give a trunk circumference instead. Divide the circumference by π to get
  the diameter the app asks for: the 80 cm circumference threshold at 1.30 m in Berlin's tree-protection ordinance is a
  diameter of about 25 cm ([Service Berlin](https://service.berlin.de/dienstleistung/330487/)). Other cities use other
  thresholds.
- **Height.** Add the average height; with diameter and height together the confidence grade becomes high.
- **Survival.** Count trees that died or were removed each year; the default of 0.85 is an assumption.
- **Records.** Keep records of the land's use before planting, management history and dated photographs. Certification
  schemes and CAP paying agencies usually ask for these, and the app has no place to store them
  ([results explained](../../user-guide/results-explained.md#carbon-readiness)).

## For reviewers: open items

| Item | What to do |
| --- | --- |
| Temperate allometry | Verify and add an equation for the `temperate_generic` species ([adding a parameter or equation](../../developer-guide/adding-a-species-or-parameter.md#a-new-parameter-or-equation)) |
| IPCC Tables 4.4, 4.10 and 4.12 | Check each pending value cell by cell, including the temperate and Mediterranean zones |
| Wood densities and multipliers | Check each EU species against the Global Wood Density Database; replace the eucalyptus and poplar working multipliers with table values |
| Default climate zone | One zone for 27 countries is coarse, and the Mediterranean and the far north differ from it; consider whether a documented rule can replace it when live normals are missing |
| CRCF Regulation text | Confirm the Article 2, 4, 5 and 6 readings from EUR-Lex, including the minimum monitoring period and liability |
| Delegated act C(2026)4666 | Read the text and annexes, when it enters into force and how pre-existing trees are baselined |
| Price scenario | The EU scenario is `pending` ([`carbon-price-scenarios.yaml`](../../../config/market/carbon-price-scenarios.yaml)) |

## Related pages

[README.md](README.md) · [PROGRAMS.md](PROGRAMS.md) · [DATA_SOURCES.md](DATA_SOURCES.md) ·
[India methodologies](../IN/METHODOLOGIES.md) · [United States methodologies](../US/METHODOLOGIES.md) ·
[Carbon engine notes](../../architecture/carbon-engine.md)
