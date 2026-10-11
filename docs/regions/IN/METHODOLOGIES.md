# Methodologies — India

This page explains how CarbonCreditBuy estimates carbon for a plot in India, which methodologies a real carbon or
green-credit project in India would use instead, and how far apart the two are. CarbonCreditBuy **references**
methodologies; it never **applies** one, and nothing here turns an estimate into a credit
([carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md)).

Statements about rules carry a source link. A statement we could not confirm against the primary document is marked
*(unverified)*: verify it against the current notification before you rely on it. The research behind this page is
in [policy-references.md](../../research/policy-references.md) and
[tree-age-carbon-rules.md](../../research/tree-age-carbon-rules.md).

## At a glance

| Question | Answer |
|---|---|
| What does CarbonCreditBuy calculate for an Indian plot? | A scenario of the carbon the trees you describe remove each year, as a range, from the IPCC 2006 Tier 1 gain-loss method, or from Chave et al. (2014) when you give an average trunk diameter |
| Does that method issue credits? | No. It is national-inventory guidance, used here only for default parameters ([registry entry](../../../config/methodologies/registry.yaml)) |
| What could a carbon project for trees on land in India use? | The CCTS offset mechanism has an approved afforestation and reforestation methodology, BM FR05.002 ([BEE](https://beeindia.gov.in/sites/default/files/BM_FR05.002_Afforestation_and_reforestation_of_lands_except_wetlands.pdf)). Whether it covers trees planted among crops is not stated in its applicability text *(unverified)* |
| What could a Green Credit project use? | The Green Credit tree-plantation methodology, which concerns degraded forest land under state forest departments, not a farmer's own land ([GCP FAQ](https://www.moefcc-gcp.in/faq)) |
| What about the voluntary market? | Verra VM0047 (afforestation, reforestation and revegetation) has a census-based approach for scattered planting ([Verra](https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-1/)). VM0042 covers farming practices, not trees |

## What CarbonCreditBuy calculates for an Indian plot

The model is `tree-biomass` version 0.1 in [`packages/carbon-engine`](../../../packages/carbon-engine/README.md). Every
number it uses comes from [`config/`](../../../config/), with a source, a unit and a verification status.

**Without a trunk diameter (Tier 1).** For each year from planting to 30 years later, the model takes the
above-ground growth for the climate zone, adjusts it for the species, for how densely the trees are planted
compared with a reference density, for a six-year ramp-up from planting, for slower growth after the species'
maturity age and for survival, then adds the roots with a root-to-shoot ratio and converts carbon to carbon
dioxide with the carbon fraction and 44/12. The headline is the **mean annual removal over the 30 years**, not what
the plot removes this year.

**With an average trunk diameter (Tier 2).** The model estimates the biomass of one tree from diameter, height and
wood density with Chave et al. (2014) equation 4, multiplies by the surviving trees, adds roots and divides the
stock by the stand age. Without a reported height it uses a species height scaled by age.

**The range.** Low and high are the central value less and plus 30% (Tier 1) or 20% (Tier 2). These fractions are
project assumptions, not statistical confidence intervals.

**What the number includes.** Living above-ground and below-ground biomass of the trees you described. It does not
include dead wood, litter, soil carbon, harvested wood products or emissions from management. It subtracts no
baseline, no leakage and no buffer for reversals, which every credit methodology does. See
[additionality](../../concepts/additionality.md), [leakage](../../concepts/leakage.md) and
[permanence](../../concepts/permanence.md).

### Parameters that matter for India

Values below are the working values in `config/` version 0.1.0 at the time of writing. The configuration files are
authoritative; check them before you quote a number from this page. **Pending** means copied from the cited source
and not yet checked by a reviewer, so every estimate in version 0.1 is preliminary
([results explained](../../user-guide/results-explained.md#tree-data-quality)).

| Parameter | Working value | Status | Source recorded in the config |
|---|---|---|---|
| Carbon fraction | 0.47 t C per t d.m. | verified | IPCC 2006 Vol. 4 Ch. 4 Table 4.3 |
| Carbon to carbon dioxide | 44/12 (3.6667) | verified | Molecular mass ratio |
| Per-tree biomass | AGB (kg) = 0.0673 × (ρ × D² × H)^0.976 | verified | Chave et al. 2014, equation 4 |
| Root-to-shoot ratio, tropical dry | 0.56 below 20 t d.m./ha above-ground, 0.28 at or above | pending | IPCC 2006 Table 4.4 |
| Above-ground growth, tropical dry (the default zone for IN) | 4.0 t d.m./ha/yr (range 2.0 to 6.0) | pending | IPCC 2006 Tables 4.10 and 4.12, working values |
| Survival of planted trees | 0.85 | assumption | Project assumption v0.1 |
| Years from planting to full increment | 6 | assumption | Project assumption v0.1 |
| Density factor limits | 0.2 to 1.5 | assumption | Project assumption v0.1 |
| Growth after maturity | 0.5 of full increment | assumption | Project assumption v0.1 |
| Evaluation horizon | 30 years | assumption | Project assumption v0.1 |
| Uncertainty | 30% (Tier 1), 20% (Tier 2) | assumption | Project assumption v0.1 |

India spans several climate zones. These are the zones in the Tier 1 table that Indian species list as suitable, with
their working above-ground growth values (all pending):

| Climate zone | Growth, t d.m./ha/yr | Range |
|---|---|---|
| `tropical_wet` | 10.0 | 5.0 to 15.0 |
| `tropical_moist` | 7.0 | 3.0 to 11.0 |
| `tropical_dry` | 4.0 | 2.0 to 6.0 |
| `tropical_mountain` | 5.0 | 2.0 to 8.0 |
| `subtropical_humid` | 7.0 | 3.0 to 11.0 |
| `subtropical_dry` | 4.0 | 2.0 to 6.0 |

The default zone for India is `tropical_dry`, a semi-arid Deccan assumption
([`config/regions/IN.yaml`](../../../config/regions/IN.yaml)). When the server has live climate normals, it classifies
the plot's mean annual temperature, annual precipitation and elevation into a zone with an approximation of the IPCC
2006 decision tree, marked as an assumption in the output
([`zones.py`](../../../packages/geo-engine/geo_engine/climate/zones.py)). The two `subtropical` zones are never chosen
automatically. Without live normals the **Evidence chain** says "region-default". A plot in the Western Ghats or the
north-east is wetter than the default, so check the line before you trust the estimate. The model adds a note when a
species is not listed as suitable for the zone in use.

### Species available for India

From [`config/species/species.yaml`](../../../config/species/species.yaml) version 0.1.0. Maturity ages and densities
are bare numbers in the file, which by convention the engine reports as project assumptions.

| Species | Equation key | Wood density, g/cm³ (pending) | Reference density, trees/ha | Maturity, years | Increment multiplier |
|---|---|---|---|---|---|
| Mango (*Mangifera indica*) | `pantropical_chave_2014_with_height` | 0.55 | 150 | 8 | 0.9, assumption |
| Teak (*Tectona grandis*) | `pantropical_chave_2014_with_height` | 0.55 | 500 | 20 | 1.1, pending: IPCC Table 4.10 lists teak separately, verify and replace |
| Neem (*Azadirachta indica*) | `pantropical_chave_2014_with_height` | 0.68 | 400 | 15 | 0.9, assumption |
| Eucalyptus (*Eucalyptus* spp.) | `pantropical_chave_2014_with_height` | 0.60 | 1,100 | 8 | 1.5, pending: IPCC Table 4.10 lists eucalyptus separately, verify and replace |
| Mixed native species | `pantropical_chave_2014_with_height` | 0.58 | 400 | 20 | 1.0, verified (Tier 1 broad category used directly) |
| Poplar (*Populus* spp.) | `temperate_generic` | 0.35 | 500 | 10 | 1.6, pending |

Wood densities are working values from the [Global Wood Density Database](https://doi.org/10.5061/dryad.234) and must
be checked against the database before release; the mixed-native value is a pantropical mean. Poplar nominates
`temperate_generic`, an allometry that has no equation yet, so a Tier 2 estimate for poplar substitutes Chave et al.
(2014) equation 4 outside its pantropical calibration domain and says so in its notes. Poplar is also not listed as
suitable for the default `tropical_dry` zone.

Not available yet: coconut, arecanut, cashew, sandalwood, bamboo (a grass, so not a tree-biomass case),
*Melia dubia* and casuarina. Each needs a documented growth value, a wood density and an allometric equation
([adding a parameter](../../developer-guide/adding-a-parameter.md); [starter issues](../../community/starter-issues.md)).
Soil carbon and crop-practice models are not implemented: the engine has typed stubs that return HTTP 501 and name the
sources a real implementation needs.

## Methodologies a real project would use

| Methodology | Kind | What it covers | Status as of the research (2026-10-05) | Source |
|---|---|---|---|---|
| BM FR05.002, Afforestation and reforestation of lands except wetlands, v1.0 | CCTS offset methodology (BEE) | Afforestation and reforestation derived from the CDM methodology AR-ACM0003; above-ground and below-ground biomass are mandatory pools; the baseline includes tree biomass already standing; credits are temporary (tCCC) or long-term (lCCC) certificates with reversal replacement; wetlands are excluded | Approved 8 September 2025. The applicability text does not mention agroforestry or cropland *(unverified)* | [BEE, BM FR05.002](https://beeindia.gov.in/sites/default/files/BM_FR05.002_Afforestation_and_reforestation_of_lands_except_wetlands.pdf) |
| BM FR05.001, mangrove afforestation and reforestation, v1.0 | CCTS offset methodology (BEE) | Mangroves | Approved 27 March 2025 | [BEE, BM FR05.001](https://beeindia.gov.in/sites/default/files/BM%20FR05.001.pdf) |
| Detailed Procedure for Offset Mechanism | CCTS procedure (BEE) | Lists ten sectors, including agriculture and forestry; registration, validation and verification by an accredited agency | March 2025 | [BEE procedure](https://beeindia.gov.in/sites/default/files/Detailed%20Procedure%20for%20Offset%20Mechanism_CCTS.pdf); [IETA brief](https://www.ieta.org/uploads/wp-content/Resources/Busines-briefs/2025/IETA_Business_Brief-India_July_final-one.pdf) |
| Green Credit tree-plantation methodology | Government programme (MoEFCC) | Degraded forest land parcels of at least 5 ha under state or union-territory forest departments; credits are non-tradable and are counted per surviving tree, not per tonne of CO₂e | First notified 22 February 2024, revised 29 August 2025: credits only after at least five years and 40% canopy density. The G.S.R. number comes from a secondary source and the gazette text was not opened *(unverified)* | [GCP FAQ](https://www.moefcc-gcp.in/faq); [SCC Online analysis](https://www.scconline.com/blog/post/2026/02/11/ecological-concerns-green-credit-programme-india-analysis/) |
| Verra VM0047, Afforestation, Reforestation and Revegetation | Voluntary standard | Area-based approach; census-based approach for dispersed planting with no more than 50 planting units per hectare and no change of land use | Version 1.1 active since 14 May 2025. The registry in `config/` still lists version 1.0 | [Verra VM0047 v1.1](https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-1/) |
| Verra VM0042, Improved Agricultural Land Management | Voluntary standard | Tillage, fertilizer, residue, water, cover crop and grazing practices; not tree planting | Version 2.2 active since 21 October 2025 | [Verra VM0042 v2.2](https://verra.org/methodologies/vm0042-improved-agricultural-land-management-v2-2/) |
| IPCC 2006 Guidelines, Vol. 4, Ch. 4 (Forest Land), with the 2019 Refinement | National-inventory guidance | Default factors for carbon fraction, root-to-shoot ratio and growth; the source of CarbonCreditBuy's Tier 1 parameters | Active guidance; not a credit methodology | [IPCC NGGIP](https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html) |

The pages [CCTS.md](CCTS.md) and [GREEN_CREDIT.md](GREEN_CREDIT.md) describe the two schemes and ask readers to verify
whether an afforestation methodology exists (CCTS) and what the current Green Credit rules say. The research note
records BM FR05.002 and the 2025 revision of the Green Credit methodology as above; confirm both against the
notifications.

### What a real methodology asks for that CarbonCreditBuy does not do

| Step | Why it matters |
|---|---|
| Baseline | A methodology credits only what happens beyond the baseline. BM FR05.002 counts the tree biomass already standing in the baseline, so trees you already have are not credited on their own ([research note](../../research/tree-age-carbon-rules.md#india)) |
| Additionality | The project must show it would not have happened without carbon revenue; public subsidies for the same trees ([INCENTIVES.md](INCENTIVES.md)) can matter, so ask the programme how it treats them |
| Monitoring on the ground | Measured sample plots (diameter, height, survival), supported by remote sensing, repeated on a schedule |
| Leakage and permanence | Methodology-specific rules and buffers; BM FR05.002 uses temporary and long-term certificates |
| Verification | By an Accredited Carbon Verification Agency listed by BEE ([BEE register](https://beeindia.gov.in/view_content.php?lid=568&lang=1)) |
| Registration and issuance | Through the scheme's registry; only then does a unit exist |

BM FR05.002 and CarbonCreditBuy both cover the above-ground and below-ground biomass pools. That does not make a CarbonCreditBuy
estimate comparable to a methodology result: it has no baseline, no deductions and no verification.

## Green Credits count trees

The Green Credit Programme measures activity, not tonnes. For tree plantation it counts surviving trees on a
programme parcel ([GCP FAQ](https://www.moefcc-gcp.in/faq)), and the official wording is that Green Credit generation
"is independent of the carbon credit under Carbon Credit Trading Scheme 2023"
([PIB](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=1989495&reg=48&lang=2)). CarbonCreditBuy never converts an
estimate into a Green Credit count or the other way round: "Green Credits (GCP) and carbon credits (CCTS) are
separate mechanisms."

## Measuring to improve the estimate

- **Diameter.** Measure trunk diameter at breast height, 1.3 m above the ground, on a sample of at least 30 trees, and
  enter the average. If your records give the girth (the distance around the trunk), divide by π (3.14) to get the
  diameter. CarbonCreditBuy then uses Tier 2 and shows a narrower range.
- **Height.** Add the average height; with diameter and height together the confidence grade becomes high.
- **Survival.** Count trees that died or were removed each year. The default of 0.85 is an assumption, not a
  measurement.
- **Records.** Keep land records from before planting, a management log and dated photographs. Programmes usually
  ask for these, and the app has no place to store them ([results explained](../../user-guide/results-explained.md#carbon-readiness)).

## For reviewers: open items

| Item | What to do |
|---|---|
| IPCC Tables 4.4, 4.10 and 4.12 | Check each pending value cell by cell and record the table cell in `source` ([adding a parameter](../../developer-guide/adding-a-parameter.md)) |
| Wood densities | Check each Indian species against the Global Wood Density Database export |
| Teak and eucalyptus multipliers | Replace the working values with the IPCC Table 4.10 plantation values |
| Climate zones | The default `tropical_dry` does not suit much of the country; consider state-level defaults only with a documented source |
| BM FR05.002 and agroforestry | Ask BEE, or read the tool BM-T-AR-001, whether trees on cropland qualify |
| Green Credit notifications | Obtain the gazette texts of S.O. 4458(E), S.O. 884(E) and G.S.R. 592(E) |
| Registry versions | Update the VM0047 entry to version 1.1 and the VM0042 URL when the policy files are next revised ([policy-references.md](../../research/policy-references.md#8-what-configpoliciesyaml-should-say-concrete-edits)) |
| Price scenarios | The India scenario has no public price behind it: no Carbon Credit Certificate trade was confirmed ([IETA brief](https://www.ieta.org/uploads/wp-content/Resources/Busines-briefs/2025/IETA_Business_Brief-India_July_final-one.pdf)) |

## Related pages

[README.md](README.md) · [GREEN_CREDIT.md](GREEN_CREDIT.md) · [CCTS.md](CCTS.md) · [INCENTIVES.md](INCENTIVES.md) ·
[DATA_SOURCES.md](DATA_SOURCES.md) · [Carbon engine notes](../../architecture/carbon-engine.md)
