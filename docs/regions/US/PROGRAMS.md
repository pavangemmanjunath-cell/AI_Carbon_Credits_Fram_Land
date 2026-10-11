# Programs — United States

This page describes the three programs CarbonCreditBuy screens for plots in the United States, the standards and protocols
around them, and what is still unconfirmed. The rules themselves live in
[`config/policies/US.yaml`](../../../config/policies/US.yaml). The screening is never an eligibility determination:
"Initial screening only — not an eligibility determination. Voluntary-market credits require an approved methodology,
verification and registry issuance."

Statements about rules carry a source link. A statement we could not confirm against the primary document is marked
*(unverified)*. Program details, payment rates and sign-up dates change; verify them with the administrator. The research
behind this page is in [policy-references.md](../../research/policy-references.md) and
[tree-age-carbon-rules.md](../../research/tree-age-carbon-rules.md).

## Credits, estimates and incentives

| Mechanism | Kind | What it produces | Tradable |
| --- | --- | --- | --- |
| USDA EQIP and CSP | Incentive | Cost-share and stewardship payments | No |
| COMET-Farm and COMET-Planner | Estimation tool | A greenhouse-gas estimate, not a unit | No |
| Verra, Climate Action Reserve, American Carbon Registry | Voluntary standard | Credits issued after verification (VCUs, CRTs, ERTs in the research note) | Yes |

Source: the taxonomy in [policy-references.md](../../research/policy-references.md#7-carbon-credit-vs-incentive-taxonomy-the-engine-should-use).
CarbonCreditBuy shows an incentive as other farm income and an estimate as an environmental benefit. Neither is a credit
([carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md)).

## What the engine returns

These are the statuses the policy engine returns for a plot of any size, by activity. The web app always asks about
**tree plantation**; the other activities are reachable through the API
([policy engine](../../../packages/policy-engine/README.md)).

| Activity | COMET-Farm | Voluntary ARR methodologies | NRCS (EQIP, CSP) |
| --- | --- | --- | --- |
| Tree plantation | `potentially_applicable` | `requires_methodology_assessment` | `potentially_applicable` |
| Agroforestry | `potentially_applicable` | `requires_methodology_assessment` | `potentially_applicable` |
| Cropland practice | `potentially_applicable` | `requires_methodology_assessment` | `potentially_applicable` |
| Grazing | `potentially_applicable` | `unknown` | `not_applicable` |
| Soil carbon | `not_applicable` | `unknown` | `not_applicable` |

`unknown` means no rule covers the case; do not read it as "no". `not_applicable` for soil carbon under COMET-Farm comes
from the rule's list of activities, not from a finding about the tool: TODO(verify) with a USDA source whether
`soil_carbon` belongs in that rule.

## USDA COMET-Farm and COMET-Planner

**What they are.** COMET-Farm is the USDA and Colorado State University tool for estimating farm and ranch greenhouse-gas
emissions and mitigation options ([comet-farm.com](https://comet-farm.com/)). CarbonCreditBuy lists it as a **methodology
reference**: you can enter the same trees there to cross-check this estimate. CarbonCreditBuy does not call COMET-Farm and
sends it nothing; you enter your own boundary and trees there under its terms.

**What CarbonCreditBuy rule says.** Status `potentially_applicable` for tree plantation, agroforestry, cropland practice and
grazing. The reason text says that agroforestry assessments use tree numbers and sizes with growth equations based on
Forest Inventory and Analysis (FIA) data. We could not open the COMET-Farm site, which is a JavaScript application, so
the details of its agroforestry module are *(unverified)*. Requirements listed: field boundaries and management history
entered in COMET-Farm; tree species, counts and sizes for agroforestry practices.

**COMET-Planner version 4.0 (October 2025).** The planning tool covers these agroforestry practices, by NRCS
conservation practice standard (CPS) code, and estimates tree carbon from diameter-from-age models by taxon group and
Land Resource Region built from FIA data. Its results are 10-year averages of standing tree carbon only, without dead
wood or litter ([COMET-Planner report](https://comet-planner.com/api/resource/pdf/COMET-Planner_Report.pdf)).

| CPS code | Practice |
| --- | --- |
| 311 | Alley Cropping |
| 379 | Forest Farming |
| 380 | Windbreak/Shelterbelt |
| 381 | Silvopasture |
| 391 | Riparian Forest Buffer |
| 422 | Hedgerow Planting |
| 612 | Tree/Shrub Establishment |

**Comparing the two.** Expect different numbers: COMET-Planner averages 10 years of living tree carbon from FIA-based
models, while CarbonCreditBuy reports a 30-year mean annual removal from IPCC Tier 1 working values. Compare the time window,
the carbon pools, the units (acres or hectares, metric or short tons) and the inputs before you draw a conclusion
([METHODOLOGIES.md](METHODOLOGIES.md)). The registry entry says COMET-Farm is "referenced, not copied": CarbonCreditBuy
does not reuse its equations ([`registry.yaml`](../../../config/methodologies/registry.yaml)).

## Voluntary-market methodologies

**What CarbonCreditBuy rule says.** Status `requires_methodology_assessment` for tree plantation, agroforestry and cropland
practice. The requirements it lists: registration with a standard and a registry; a baseline and an additionality
demonstration; monitoring (diameter, survival, remote sensing) and a leakage assessment; a permanence commitment and a
buffer-pool contribution; third-party validation and verification. The rule notes that minimum project sizes and
costs apply and does not state them.

### New planting and cropland practices

| Methodology | What it covers | Status in the research (2026-10-05) | Source |
| --- | --- | --- | --- |
| Verra VM0047, Afforestation, Reforestation and Revegetation | Area-based approach; census-based approach for dispersed planting such as agroforestry and shelterbelts, with no more than 50 planting units per hectare, direct planting only, the pre-project land use kept, and under 10% pre-existing woody biomass cover (or continuous cropping, settlements or other lands). The stock of pre-existing woody biomass at the start is measured, not credited | Version 1.1 active since 14 May 2025; approved under the ICVCM Core Carbon Principles (version 1.0 in December 2024, version 1.1 in September 2025). How the later growth of pre-existing trees is treated was not checked | [Verra, VM0047 v1.1](https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-1/); [ICVCM status](https://icvcm.org/assessment-status/) |
| Verra VM0042, Improved Agricultural Land Management | Tillage, fertilizer, residue and water management, cover crops and grazing. Not tree planting | Version 2.2 active since 21 October 2025; Core Carbon Principles approval of 30 October 2025 with a condition against digital soil mapping for soil carbon | [Verra, VM0042 v2.2](https://verra.org/methodologies/vm0042-improved-agricultural-land-management-v2-2/); [ICVCM, 30 October 2025](https://icvcm.org/integrity-council-approves-first-sustainable-agriculture-methodologies-from-car-and-verra/) |
| Climate Action Reserve, Soil Enrichment Protocol | Soil carbon on US farmland | Version 1.1 approved under the Core Carbon Principles on 30 October 2025 with a 40-year permanence condition | [ICVCM, 30 October 2025](https://icvcm.org/integrity-council-approves-first-sustainable-agriculture-methodologies-from-car-and-verra/) |

CarbonCreditBuy policy file and registry still point to the VM0047 version 1.0 and VM0042 version 2.0 pages. The research
note recommends updating them to the versions above and adding the census-based condition to the rule text
([policy-references.md](../../research/policy-references.md#8-what-configpoliciesyaml-should-say-concrete-edits)).

### Existing forests and woodlots

If you already have trees, the research found that carbon standards credit **new, additional** removals or avoided loss
against a baseline, not the carbon the trees already hold
([research note](../../research/tree-age-carbon-rules.md#key-finding)). These protocols apply to existing forest:

| Protocol | What it rewards | Commitment | Source |
| --- | --- | --- | --- |
| Climate Action Reserve, U.S. Forest Protocol v5.1 | Reforestation, improved forest management and avoided conversion; credits are on-site stocks minus baseline estimates | Monitoring and verification for 100 years after any credit is issued; a buffer pool covers reversals | [CAR](https://climateactionreserve.org/wp-content/uploads/2023/07/Final_Forest_Protocol_V5.1_7.14.2023.pdf) |
| American Carbon Registry, Improved Forest Management on Non-Federal U.S. Forestlands v2.1 | Forgone baseline harvests and retained growth against a project-specific harvesting baseline | Minimum project term 40 years; crediting period 20 years | [ACR](https://acrcarbon.org/wp-content/uploads/2022/07/ACR-Methodology-IFM-on-Non-Federal-US-Forestlands-v2_1-20240701.pdf) |
| Family Forest Carbon Program with Verra VM0045 | A changed forest practice measured against a matched baseline. Owners need 30 or more acres of non-planted, naturally regenerating trees and the right to harvest | A 20-year commitment | [American Forest Foundation](https://familyforestcarbon.org/about-the-program/get-started/); [Verra, VM0045 v1.2](https://verra.org/methodologies/vm0045-improved-forest-management-using-dynamic-matched-baselines-from-national-forest-inventories-v1-2/) |

Urban tree protocols exist too: City Forest Credits has a planting protocol for urban trees and a preservation protocol
for at-risk existing urban stands ([City Forest Credits](https://www.cityforestcredits.org/carbon-protocols/)). The
research note has the details.

**Private company programs.** Several agricultural companies run their own carbon programs for practice changes, with
their own contract terms. A 2025 Penn State research brief compares contract terms
([Penn State](https://aglaw.psu.edu/wp-content/uploads/2025/04/RB25-036-Research-Brief-Carbon-Sequestration-Contracts.pdf)).
CarbonCreditBuy does not screen them and states none of their payments, because the terms change; read any contract with an
adviser before you sign.

## USDA NRCS conservation programs: EQIP and CSP

**What they are.** The Environmental Quality Incentives Program (EQIP) offers cost-share, and the Conservation
Stewardship Program (CSP) offers stewardship payments. They are incentives, not carbon credits ([EQIP](https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives);
[CSP](https://www.nrcs.usda.gov/programs-initiatives/csp-conservation-stewardship-program)).

**What CarbonCreditBuy rule says.** Status `potentially_applicable` for tree plantation, agroforestry and cropland practice,
otherwise `not_applicable`. The reason: cost-share and stewardship payments exist for agroforestry practices such as
windbreaks, alley cropping and riparian buffers. Requirements listed: eligible land and producer status; a
conservation plan with NRCS.

**Practice codes.** The NRCS fiscal-year 2024 CSAF mitigation practice list names these agroforestry and forestry
codes: 311, 379, 380, 381, 383, 384, 390, 391, 420, 422, 612, 643 and 666
([NRCS](https://www.nrcs.usda.gov/sites/default/files/2023-12/FY24%20%20CSAF%20Mitigation%20practice%20list.pdf)).
Payment rates, sign-up periods and ranking rules change each year, so CarbonCreditBuy states none. Your local NRCS office
knows which practices your county funds.

**If you also want carbon revenue.** Ask the carbon program how it treats cost-share that already paid for the same
trees; programs test whether a project would have happened anyway
([additionality](../../concepts/additionality.md)).

## Rules by tree age

Separately from the program screening above, the Tree age page of the web app and `POST /api/v1/tree-age/assess`
list the rules that treat trees differently by age, size or setting. They come from
[`config/tree-age/rules.yaml`](../../../config/tree-age/rules.yaml), where each rule carries its sources, the date they
were opened and a verification status. A US user sees the ten below: seven for the United States and three global
standards. At the time of writing every one is `verified` and in force, none states an amount, and none sets an age
threshold. The research and the open questions are in the
[research note](../../research/tree-age-carbon-rules.md#united-states). To add one, see
[adding a tree-age rule](../../developer-guide/adding-a-tree-age-rule.md).

| Rule id | Written for | What it says | Outcome for existing trees |
| --- | --- | --- | --- |
| `global-icvcm-ccp-additionality` | Any trees | ICVCM Core Carbon Principles 5 to 7: a credit counts only removals that would not have happened without carbon revenue, so growth that standing trees would make anyway is not creditable on its own. A methodology note, not a route to a credit | `conditional` |
| `global-verra-vm0047-arr` | New planting | Verra VM0047 credits trees a project plants or restores. The carbon in pre-existing trees is measured as a starting stock and not credited | `not-eligible` |
| `global-gold-standard-luf-ar` | New planting, outside forest | Gold Standard A/R covers only land that was not forest 10 years before the project start | `not-eligible` |
| `us-cfc-preservation-protocol` | Existing urban stands | City Forest Credits Preservation Protocol v14.40 can credit the carbon in an existing urban stand at risk of being cleared, for a 40-year commitment | `conditional` |
| `us-cfc-afforestation-protocol` | New urban planting | City Forest Credits Afforestation and Reforestation Protocol v12 credits only newly planted project trees | `not-eligible` |
| `us-car-forest-protocol-ifm` | Existing forest | Climate Action Reserve U.S. Forest Protocol v5.1 credits the extra carbon above a baseline, not the carbon the forest already stores, with 100 years of monitoring | `conditional` |
| `us-acr-ifm-non-federal-v2-1` | Existing forest | ACR Improved Forest Management on Non-Federal U.S. Forestlands v2.1 credits the extra live and dead biomass carbon against a harvest baseline. It sets no stand-age test | `conditional` |
| `us-family-forest-carbon-vm0045` | Existing forest | Family Forest Carbon Program with Verra VM0045: owners of 30 or more acres of naturally regenerating forest can enroll in a 20-year program that rewards a changed practice measured against matched baseline plots | `conditional` |
| `us-or-portland-heritage-trees` | Existing urban trees (example) | Portland City Code 11.20.060: a tree can be designated a Heritage Tree for its age, size, type, historical association or horticultural value, and a designated tree cannot be removed without Urban Forestry Commission consent | `protected` |
| `us-ca-los-angeles-protected-trees` | Existing urban trees (example) | Los Angeles Ordinance 186873: native oaks, southern California black walnut, western sycamore, California bay, Mexican elderberry and toyon are protected at 4 inches of cumulative trunk diameter at 4.5 feet. The test is species and size, not age | `protected` |

How to read it. An age only matters through the rule's own test: the engine filters by place, then by setting (farm,
town or city, forest), then by age. For a farm tree the two global standards apply and both say "not eligible", so the
credit outlook is "not eligible". For forest trees the three protocols give a "conditional" route that needs a long
commitment and a project, and an estimate from CarbonCreditBuy is never a credit. The Portland and Los Angeles rules are
municipal examples for "check your own city's rules"; the request carries no city, so the page lists them as not
applying. The sentence on every result stays the same: screening information, not legal advice.

## What CarbonCreditBuy does not screen

State programs, federal programs other than EQIP and CSP, and private contracts. Local tree-protection rules vary by
city and CarbonCreditBuy has only the two municipal examples above. TODO(verify): research which state programs exist, with
an official source for each, before adding rules.

## Open items for reviewers

| Item | What to do |
| --- | --- |
| Verra versions | Update the VM0047 and VM0042 URLs and registry entries to versions 1.1 and 2.2 |
| COMET-Farm | Confirm the agroforestry module from a USDA document, and decide whether `soil_carbon` belongs in the rule |
| Minimum project sizes and costs | The rule mentions them; add them only from a methodology or registry document |
| State programs | Not researched |
| Other cities and states in the tree-age rules | Only Portland and Los Angeles are covered, as examples. Add others from official ordinances ([adding a tree-age rule](../../developer-guide/adding-a-tree-age-rule.md)) |
| Price scenario | The US scenario describes voluntary ARR and improved forest management removal credits and is `pending` ([`carbon-price-scenarios.yaml`](../../../config/market/carbon-price-scenarios.yaml)) |

## Related pages

[README.md](README.md) · [DATA_SOURCES.md](DATA_SOURCES.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[Policy engine](../../../packages/policy-engine/README.md)
