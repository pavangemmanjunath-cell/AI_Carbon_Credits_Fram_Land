# Tree age, carbon credits and the law

Research of 2026-10-05 for the "Tree age" dashboard, behind `config/tree-age/rules.yaml`. A landowner enters the
age of existing trees (for example 5, 30, 60 or 100 years), species and count; the dashboard shows what the trees store
and which real rules treat trees of that age differently. This page covers global carbon standards and the three
supported regions (India, the United States, the European Union). It is screening information, not legal advice: rules
change, and the responsible authority has the last word. The rule file holds 22 rules, 19 `verified` and 3 `pending`.

## Key finding

**Carbon-credit standards reward new, additional removals or avoided loss. They do not pay for the carbon that old
trees already hold.** A 60-year-old or 100-year-old tree stores a great deal of carbon, but in the methodologies
reviewed
that stock is the starting point (the baseline), not a creditable removal. The one clear exception is avoided-loss
credit for an existing urban stand that is at risk of being cleared (City Forest Credits, Preservation protocol), which
needs a 40-year preservation commitment. Existing trees are protected or rewarded mainly through other instruments:
felling-permission and heritage-tree laws, compensatory-planting rules, and in Haryana a pension for very old trees.

| Instrument | What it credits or does | Existing trees | Rule id |
|---|---|---|---|
| ICVCM Core Carbon Principles 5 to 7 | Only removals that would not have happened without carbon revenue | Growth that happens anyway is not additional (CarbonCreditBuy reading) | `global-icvcm-ccp-additionality` |
| Verra VM0047 (ARR) v1.1 | Trees a project plants or restores | The t = 0 stock of pre-existing woody biomass is measured, not credited | `global-verra-vm0047-arr` |
| Gold Standard A/R (LUF) | Planting on land that was not forest 10 years before the start | No credits for existing forests | `global-gold-standard-luf-ar` |
| India, Green Credit Programme | Restoration of degraded forest land of 5 ha or more under a Forest Department | Not a route for farm or town trees; credits are non-tradable | `in-gcp-tree-plantation` |
| India, CCTS offset (BM FR05.002) | Net removals above a baseline that includes tree biomass already standing | Not credited on their own | `in-ccts-offset-bm-fr05-002` |
| Haryana, Pran Vayu Devta Pension | Annual payment to the custodian of a tree about 75 years old or more | Payment, not a credit (pending) | `in-hr-pran-vayu-devta-pension` |
| City Forest Credits, Preservation v14.40 | Carbon in an at-risk existing urban stand, for a 40-year commitment | Conditional: avoided loss, not new removals | `us-cfc-preservation-protocol` |
| City Forest Credits, Afforestation v12 | Newly planted urban project trees | Not eligible | `us-cfc-afforestation-protocol` |
| CAR Forest Protocol v5.1, ACR IFM v2.1, VM0045 | The increase against a baseline in existing forests | Conditional: the stock itself is not credited | `us-car-forest-protocol-ifm`, `us-acr-ifm-non-federal-v2-1`, `us-family-forest-carbon-vm0045` |
| EU CRCF Regulation 2024/3012 | Net benefit above a baseline from an activity of at least five years | Conditional: baseline is subtracted; certification by a recognised scheme is required | `eu-crcf-regulation-2024-3012` |
| EU carbon-farming delegated act (adopted 10 July 2026) | Afforestation, agroforestry on mineral soils, peatland rewetting | Unknown until the text is read (pending) | `eu-crcf-carbon-farming-delegated-act-2026` |

Three consequences for the dashboard. First, stored carbon and credit potential must be separate outputs, because the
first can be large while the second is zero. Second, an estimate is never a credit: nothing in the rule file converts a
tree into a credit, and every carbon output stays `certified: false` (CLAUDE.md principle 1). Third, only two of the 22
rules have an age threshold at all (Haryana at 75 years, Maharashtra heritage trees at 50 years), and both are
`pending`; most protection rules turn on trunk size or species, not age.

## Age classes and why they are where they are

The classes in the rule file are labels for screening, not legal categories.

| Class | Years | Where the boundary comes from |
|---|---|---|
| Young | 0 to 20 | The IPCC Tier 1 split of natural-forest growth into "up to 20 years" and "over 20 years": 2003 Good Practice Guidance for LULUCF, Table 3A.1.5 (page 3.163), and 2006 IPCC Guidelines, Vol. 4 Ch. 4, Table 4.9. Requena Suarez et al. (2019) describe it: "IPCC 2006 default ∆AGB rates divide natural forest stands into above and below 20 years". |
| Mature | 21 to 49 | Everything over 20 years and below the heritage threshold. |
| Old | 50 to 74 | 50 years: the heritage-tree age reported for Maharashtra ("any tree with an estimated age of 50 years or above", press reports of June 2021). The amended Act and the Bill do not state it; pending. |
| Veteran | 75 and over | 75 years: the age in Haryana's Pran Vayu Devta Pension Scheme, reported as "older than 75 years" in 2023 and "75 years or older" later (press; pending). |

Notes. The 20-year boundary is a growth-science boundary, so its numbers are in
[ipcc-age-class-growth.md](ipcc-age-class-growth.md), where the IPCC table values are explicitly not verified. The 50 and
75-year boundaries are Indian rules and say nothing about trees in the United States or the EU, whose protection rules
use size and species. The refined tropical growth classes in the scientific literature place old-growth at 100 years or
more without disturbance; CarbonCreditBuy does not add a 100-year class.

## Global standards

### ICVCM Core Carbon Principles

The Integrity Council's principle 5 (additionality) says removals "shall be additional, i.e., they would not have
occurred in the absence of the incentive created by carbon credit revenues". Principle 6 (permanence) requires them to
be
"permanent or, where there is a risk of reversal, there shall be measures in place to address those risks and compensate
reversals", and principle 7 requires them to be "robustly quantified, based on conservative approaches, completeness and
scientific methods". Reading these for existing trees is CarbonCreditBuy's interpretation, not ICVCM text: growth that
trees
would make anyway is not additional, which is why every methodology below works against a baseline. See
[../concepts/additionality.md](../concepts/additionality.md).

### Verra VM0047, Afforestation, Reforestation and Revegetation, v1.1 (effective 14 May 2025)

- Area-based approach: the project land must not have met the definition of managed forest at any point in the 10 years
  before the project start date, although v1.1 also allows enhancing forest carbon stocks where existing forest cover
  has
  not been managed for wood products in the past ten years.
- A t = 0 carbon-stock estimate is required for pre-existing woody biomass, and removing that biomass is allowed only
  where it is treated as a waste product with no commercial value.
- Census-based approach, for dispersed planting such as agroforestry: no more than 50 planting units per hectare, direct
  planting only, the pre-project land use maintained, and less than 10 percent pre-existing woody biomass cover (or
  continuous cropping, "settlements" or "other lands").
- So a farm with scattered old trees can sit inside a VM0047 project, but only trees the project plants earn credits.
  How
  the later growth of pre-existing trees is treated was not checked in this research.
- Section references were read through a page-summarising tool and cross-checked against the Verra page and an
  independent summary; quote from the PDF before external publication.

### Gold Standard, Land Use and Forests, A/R

- Activity Requirements v1.2.1, Section 2.1.1(b): "The eligible area shall not meet the definition of forest 10 years
  before project start date and at project start date." Credits are not issued for existing forests, improved forest
  management or avoided deforestation under these A/R requirements, and the project start date is the earliest date when
  the first trees are planted.
- A/R methodology v2.1 (16 May 2024), Section 3.5.1: the baseline is the "tree" and "non-tree" biomass present in the
  eligible planting area just before planting starts, and baseline trees are tracked inside the baseline.
- Gold Standard consulted on a successor framework, STARR, from 22 April to 22 May 2026, which also targets non-forest
  land. Final publication, and whether it replaces the documents above, was not confirmed.

### Plan Vivo (PV Climate), note only

The public PV Climate page lists four categories (restoration, agroforestry, protection and improved management) and
says
a project "must have a strong additionality argument for any historic activities that it wishes to accredit". It does
not
say how existing trees are treated, so no rule was written for it.

## India

### Green Credits and carbon credits are separate mechanisms

- **Green Credit Programme (GCP), tree plantation.** Eligible land is "Degraded forest land parcels under the control
  and
  management of the State/UT Forest Department", each a compact area of at least 5 hectares free from encumbrances;
  wildlife sanctuaries, national parks and tiger reserves are excluded. Credit claims are possible "After 5 years of
  restoration work and when canopy density reaches at least 40 percent". Green Credits for tree plantation "shall be
  non-tradable" and are non-transferable except between a holding company and its subsidiaries. The methodology was
  first
  notified on 22 February 2024 and revised on 29 August 2025 (recorded in
  [policy-references.md](policy-references.md) as G.S.R. 592(E); the gazette text was not opened). Secondary reports add
  one credit per surviving tree aged five years or more; that detail is not in the rule file. Green Credits are a
  government recognition scheme, not carbon credits and not a cash payment. For a farmer's own land or for existing
  trees
  the screening answer is "not a GCP route".
- **Carbon Credit Trading Scheme (CCTS), offset mechanism.** BM FR05.002, "Afforestation and reforestation of lands
  except wetlands", Version 1.0 of 8 September 2025, is adopted from the UNFCCC CDM methodology AR-ACM0003. Baseline net
  removals include the "Change in carbon stock in baseline tree biomass" and baseline shrub biomass (Section 4.4,
  Equation 1), so pre-existing tree biomass sits in the baseline. Applicability (Section 3.2) excludes wetlands and
  limits
  soil disturbance to 10 per cent of the area of organic-soil land or of land with baseline management practices.
  Credits
  are issued as temporary (tCCC) or long-term (lCCC) Carbon Credit Certificates (Section 4.8). The applicability text is
  silent on agroforestry and cropland, so neither should be assumed eligible; ask the Bureau of Energy Efficiency. No
  Carbon Credit Certificate trade or price signal was confirmed.
- The official line, as quoted in [policy-references.md](policy-references.md), is that the generation of Green Credit
  "is
  independent of the carbon credit under Carbon Credit Trading Scheme 2023". CarbonCreditBuy never mixes the two.

### Haryana: Pran Vayu Devta Pension Scheme (pending)

- **What the press reports.** A pension for trees "older than 75 years" (June 2023; later reports say 75 years or
  older).
  Fallen, hollow, dead, dry or diseased trees and trees on forest land are excluded, and a grove grown from one seed
  (for
  example a banyan) counts as one tree. Later reports add that the tree must be one of 40 designated native species,
  that
  applicants apply to the district forest department (21-column proforma), and that a five-member district committee
  approves, with the pension paid to the custodian's bank account.
- **Amount history (press only).** Rs 2,500 per tree per year (June 2023), Rs 2,750 (July 2024) and Rs 3,000 (June to
  September 2025, and again on 13 July 2026), meant to rise each year in line with the Old Age Samman pension. The rule
  file records Rs 3,000 per tree per year with `as_of: "2026-07"`, the latest report, in which a Faridabad forest
  officer
  is quoted. A cap of 4,000 trees until a five-year review was reported in 2023, and 3,876 trees in 22 districts in
  September 2025.
- **What is missing.** The only official page found (Haryana Forest Department, message from the PCCF's desk) names the
  scheme but gives no age or amount; the haryana.gov.in scheme page returned 404 and the Chief Minister's Office page
  was
  blocked to the fetch tool. The official notification or guidelines are needed to confirm the age wording (above or at
  least 75), the species list, the exclusions and the current amount. Until then the rule is `pending` and the pension
  is
  other farm income, shown with its date and never added to any carbon figure.

### Maharashtra: Urban Areas Protection and Preservation of Trees Act, 1975, amended 2021

- **Heritage trees (pending).** The 2021 amendment defines a heritage tree as "a tree categorised as such by the Tree
  Authority, in accordance with the norms as may be notified by the Government" and sends a proposal to fell one to the
  Maharashtra State Tree Authority (Section 2 and the proviso to Section 8(3)). The Bill and Act text opened state no
  age. News reports of the June 2021 Cabinet decision say "any tree with an estimated age of 50 years or above" would be
  classified as a heritage tree (The Tribune, Mumbai Live). The Tree Officer determines a tree's age "as per the
  criteria
  and method as may be notified by the Government" (Section 8(5)(b)). The notified norms, or the consolidated Act on
  India
  Code (blocked to the fetch tool), are still needed.
- **Compensatory planting equal to estimated age (verified).** Section 8(5), as amended in 2021: the applicant "shall
  plant such number of trees equal to the estimated age of the tree being felled and such trees to be planted shall be
  of
  atleast six feet height". A 60-year-old tree therefore means 60 new trees. The Bill text also requires the planted
  trees to survive at least seven years (Section 8(5A)) and offers a deposit of not less than the valuation of the
  felled
  trees as an alternative; check the enacted text. The penalty under Section 21 is the valuation of the tree, but not
  more
  than one lakh rupees, and applications covering more than two hundred trees of age five years or more go to the State
  Tree Authority. The Act covers urban areas, not farmland outside them.

### Karnataka: Preservation of Trees Act, 1976 (and an incentive scheme)

- Section 8: "no person shall fell any tree or cause any tree to be felled in any land ... except with the previous
  permission of the Tree Officer". A "tree" is a woody plant whose trunk is not less than five and a half centimetres in
  diameter and not less than one metre in height (Section 2). Permission must be granted for dead, diseased or
  wind-fallen trees, silviculturally mature trees, trees that endanger life or property, obstruct traffic or are
  substantially damaged by natural causes (Section 8(3)); casuarina, coconut, rubber, bamboo and other listed species
  are exempt (Section 8(7)). The applicant "shall plant another tree or trees of the same or any other suitable species
  on the same site or other suitable place within thirty days". The Act has no age test. It extends to the whole of
  Karnataka, but its provisions were brought into force area by area through notifications (Section 1). The 1976 text
  gives a penalty of up to three months' imprisonment or a fine up to Rs 1,000, or both (Section 22). Later amendments,
  the notified areas and the current penalty were not checked, and the India Code copy is blocked to the fetch tool; the
  text used is the PRS India copy.
- **Krushi Aranya Protsaha Yojane (KAPY), pending and not in the rule file.** A new-planting incentive, not age-based.
  An
  undated Karnataka government document ("Karnataka Welfare Schemes on Poverty Alleviation") says Rs 35 per surviving
  seedling is paid in the first year, Rs 40 in the second and Rs 50 in the third, to Karnataka farmers who own land,
  under
  a scheme launched in 2011 and run by the Forest Department. The official Forest Department page (aranya.gov.in) was
  blocked and the myScheme page held no scheme text, so the amounts stay unconfirmed.

### Delhi: Preservation of Trees Act, 1994

- Section 8: "no person shall fell or remove or dispose of any tree or forest produce in any land ... except with the
  previous permission of the Tree Officer". A "tree" is a woody plant whose trunk is not less than five centimetres in
  diameter at a height of thirty centimetres from the ground and not less than one metre in height (Section 2). Section
  9(2) lists cases where permission cannot be refused, including dead, diseased or wind-fallen trees, silviculturally
  mature trees (except on steep slopes) and trees that endanger life, property or traffic. The Tree Officer must decide
  within 60 days (otherwise permission is deemed granted) and applicants state the girth at 1.85 m above ground (Section
  9(1)). A person given permission must plant the number and kind of trees the Tree Officer directs in the area where
  the
  tree was felled (Section 10). The Act text read has no age or heritage-tree provision. Its penalty (Section 24) is
  up to one year's imprisonment or a fine up to Rs 1,000, or both; amendments and the consolidated text were not
  checked.
- **Compensatory planting circular.** Circular No. FAWL-L/3/2023-Tree Cell, I/76547/2023 of 2 June 2023 says felling
  permission is granted "on conditions ... one of them being plantation of 10 saplings for each tree felled and
  maintaining the same for 5-7 years". The ratio does not depend on the age of the tree, unlike Maharashtra's.

### Other Indian states

Tamil Nadu has no heritage-tree law that this research found: a Down To Earth article of 15 February 2018 advocates a
"Heritage Tree Conservation Act" and says the main criteria for a heritage tree are "size, form, shape, age, colour and
rarity", with no threshold. No other age-based Indian rule with a solid source was found; other states' tree acts were
not reviewed, so the file is not a national survey.

## United States

### City Forest Credits

- **Preservation protocol v14.40 (10 August 2026, 40-year).** It covers "at-risk forested stands" with at least 80
  percent tree canopy where precipitation is 20 inches a year or more, or 60 percent where it is less (Section 1.4.C).
  Existing carbon stock is quantified for trees at least 5 inches in diameter at breast height (Section 11.1.B), and
  stand age is established from documentation or tree coring (Section 11.1.A.ii). The stand must show risk of conversion
  by one of three tests (at least 30 percent of its perimeter bordering non-forest, developed or improved uses; a sale
  or assessed value above USD 8,000 per acre within three years; or a higher value in non-forest use) (Section 4.4) and
  must not already be protected by a recorded encumbrance (Section 4.2). The project lasts 40 years including the
  preservation commitment (Section 2.2), and 10 percent of credits go to the registry reversal pool (Section 11.4). This
  is avoided loss of existing stock, not new removals, and quantification applies deductions (an 80 percent factor with
  the USFS tables method, one standard error with inventory methods). A 100-year version (v14.100) is listed but was not
  opened.
- **Afforestation and Reforestation protocol v12 (26-year).** Covers urban tree planting for conservation, not harvest.
  Section 1.9: "Proposed projects that convert a forested land use or that cut down healthy, non-invasive trees and
  plant
  project trees for crediting are not eligible." Section 1.8: "Trees required to be planted by a law or ordinance are
  not
  eligible for crediting, unless they are replacement trees" for trees removed for reasons such as poor health, safety
  hazards, disease, age, invasive species or best management practices. Duration is 26 years from the date the last
  project tree is planted (Section 2.2), with ex ante credits at five milestones (Section 6.1). Interpretation, not
  protocol text: planting that a permit makes compulsory, such as compensatory planting for removing a healthy tree, is
  unlikely to qualify under the legal-requirement test.

### Improved forest management of existing forests

- **Climate Action Reserve U.S. Forest Protocol v5.1** (July 2023 file). Project types are reforestation, improved
  forest
  management ("maintain or increase carbon stocks on forested land relative to baseline levels") and avoided conversion
  (Section 2.1); IFM needs more than ten percent tree canopy cover and natural forest management practices. Credits are
  actual onsite stocks minus baseline estimates (Section 6), so existing standing carbon is not credited in itself, and
  projects must go beyond what any law would deliver (Section 3.3.1). Monitoring and verification run 100 years after
  issuance of any credit, the baseline is assumed valid for 100 years and a buffer pool covers reversals.
- **ACR Improved Forest Management on Non-Federal U.S. Forestlands v2.1** (July 2024). Emission Reduction Tons come from
  forgone baseline harvests and from retained with-project growth against a project-specific harvesting baseline. The
  project must show "an increase in with-project live biomass carbon and dead wood pools, in sum, relative to those
  pools
  in the baseline scenario by the end of the Crediting Period" (Section 1.2). No explicit stand-age requirement appears
  in the eligibility text, but the baseline uses "financially mature timber (i.e., at least as old as the optimal
  rotation
  age)" (Section 4.1.4). Minimum project term 40 years, crediting period 20 years.
- **Family Forest Carbon Program with Verra VM0045.** Owners need "30 or more acres of non-planted, naturally
  regenerating trees", the legal right to harvest, and a listed state, with a 20-year commitment and practices such as
  "Growing Mature Forests" and "Grow Older Forests". Under VM0045 eligible projects "adopt one or more specific,
  non-pre-existing, IFM practices", with baselines from matched project and control plots in national forest inventory
  data; accounting focuses "on the estimation of GHG emissions and/or carbon stock change on permanent plots, not on the
  estimation of stocks per se" (v1.2 active from 10 July 2025). The programme pages state no tree-age or tree-size
  requirement and no payment amount. Rewards follow a changed practice measured against a baseline, not tree age.

### Municipal examples (check your own city)

- **Portland City Code 11.20.060, Heritage Trees.** Heritage Trees are "Trees that because of their age, size, type,
  historical association or horticultural value, are of special importance to the City". The Urban Forestry Commission
  recommends and Council may designate once an arborist certifies the tree's health; designation on private property
  needs the owner's consent and is recorded on the deed; "Heritage Trees may be removed only with the consent of the
  UFC".
  The code sets no minimum age.
- **Los Angeles, Protected Tree and Shrub regulations (Ordinance 186873).** Native oaks (excluding scrub oak), Southern
  California black walnut, Western sycamore and California bay, plus the shrubs Mexican elderberry and toyon, measuring
  "four inches or more in cumulative diameter, four and one-half feet above the ground level" are protected, and a
  permit
  from the Board of Public Works is needed to remove, trim or relocate them. The ordinance was adopted on 15 December
  2020 and took effect on 4 February 2021; the city's summary says the replacement ratio changed to 4:1. The test is
  species and size, not age.

### USDA tools and programmes

No age-based USDA rule was verified. [policy-references.md](policy-references.md) records that COMET-Planner v4.0
estimates
tree carbon from age-based diameter models by taxon group and region for new plantings, and that EQIP and CSP are
cost-share and stewardship payments, not carbon credits. Those entries were not re-opened here.

## European Union

### CRCF Regulation (EU) 2024/3012

Article 2(10) defines carbon farming as "any practice or process carried out over an activity period of at least five
years, related to the management of a terrestrial or coastal environment" that results in carbon storage or lower soil
emissions. Article 4 calculates the net carbon-farming benefit by subtracting baseline removals and associated emissions
from total removals, preferring standardised baselines "highly representative of the standard performance of comparable
practices". Article 5(1) requires that the activity goes "beyond Union and national statutory requirements at the level
of an individual operator" and needs "the incentive effect of the certification" to be financially viable, and Article
5(2)
presumes additionality when a standardised baseline is used. Article 6 requires monitoring for at least the activity
period, with operators liable for releases during monitoring. The text read does not address existing carbon stocks
explicitly; treating them as part of the baseline follows from Article 4's net-benefit formula. **A CarbonCreditBuy
estimate is
never automatically CRCF-certifiable**: certification by a recognised scheme is required.

### Carbon-farming delegated act, adopted 10 July 2026 (pending)

The Commission news item of 10 July 2026 says the delegated act (C(2026)4666) covers agriculture and agroforestry on
mineral soils, rewetting and restoration of peatlands and other organic soils, and afforestation, and that "once the
Delegated Regulation enters in force, certification schemes will be able to apply for recognition" under Implementing
Regulation (EU) 2025/2358. The news item and the methodologies page do not state the methodologies' rules on existing
trees, baselines, additionality or monitoring period, and entry into force after Parliament and Council scrutiny was not
confirmed as of 2026-10-05. Third-party critiques of earlier drafts (Carbon Market Watch, March 2025: a zero
standardised
baseline with sparse existing trees on up to 10 percent of the area ignored; Bellona, 25 February 2026: pre-existing
vegetation ignored with a zero baseline) are not evidence of the adopted text. The rule is `proposed` and `pending`.

### EU guidelines on primary and old-growth forests (SWD(2023) 62 final)

The Commission staff working document of 21 March 2023 defines old-growth forest in Section 2.3 (page 7) as "A forest
stand or area consisting of native tree species that have developed, predominantly through natural processes, structures
and dynamics normally associated with late-seral developmental phases in primary or undisturbed forests of the same
type". Section 3.2 lists seven indicators (three main, four complementary); the main ones include native species
composition, a high proportion and diversity of standing and lying deadwood, and the "presence of old or large trees,
some of which may reach the maximum age known for the species". The guidelines contain no numerical age threshold and
are
"voluntary and not prescriptive". The full text was read from a third-party copy because the Commission link redirected
to the documents register; protection depends on Member State mapping and national law.

### Germany, Berlin: Baumschutzverordnung (example)

Protected are all deciduous trees except fruit trees, Scots pine (Pinus sylvestris) and, among fruit trees, walnut and
Turkish hazel; a single-stem tree needs a trunk circumference of at least 80 cm and a multi-stem tree at least one stem
of 50 cm, measured at 130 cm above the ground. Felling, significant pruning and root interventions need an exemption
permit, which the district office can grant only in the cases listed in section 5 of the ordinance and usually with
conditions for replacement planting (Ersatzpflanzung) or a compensation payment (Ausgleichszahlung). Newly planted
replacement trees are protected whatever their circumference. The ordinance text itself could not be read (the
umwelt-online.de copy was unreadable), so details come from the Berlin service portal and a district office page. Other
German cities have their own Baumschutzsatzung with different thresholds. The test is size, not age.

### France and Spain

No age-based tree rule for France or Spain was researched or found; they are not covered by the rule file.

## Science notes for the dashboard

Two statements can both be true and the dashboard should keep them apart: an individual large tree can add carbon faster
than a small one, and a forest stand's growth per hectare falls as the stand ages.

- **Individual trees: bigger trees add more carbon.** Stephenson et al. (2014), *Nature* 507: 90-93,
  DOI [10.1038/nature12914](https://doi.org/10.1038/nature12914). The abstract reports "a global analysis of 403
  tropical
  and temperate tree species, showing that for most species mass growth rate increases continuously with tree size", so
  that "large, old trees do not act simply as senescent carbon reservoirs but actively fix large amounts of carbon
  compared to smaller trees; at the extreme, a single big tree can add the same amount of carbon to the forest within a
  year as is contained in an entire mid-sized tree".
- **Stands: productivity declines with age after canopy development.** Ryan, Binkley and Fownes (1997), *Advances in
  Ecological Research* 27: 213-262, DOI [10.1016/S0065-2504(08)60009-4](https://doi.org/10.1016/S0065-2504(08)60009-4).
  The publisher summary says photosynthesis and above-ground dry-matter production increase with canopy development and
  then decline as leaf area, photosynthetic capacity and photosynthesis decline.
- **Stands, across biomes.** Pregitzer and Euskirchen (2004), *Global Change Biology* 10(12): 2052-2077,
  DOI [10.1111/j.1365-2486.2004.00866.x](https://doi.org/10.1111/j.1365-2486.2004.00866.x). The abstract reports higher
  net primary and ecosystem productivity in intermediate-aged forests (30 to 120 years), older forests generally less
  productive, and carbon pool sizes generally increasing with age across all biomes.
- **IPCC age classes.** Requena Suarez et al. (2019), *Global Change Biology* 25(11): 3609-3624,
  DOI [10.1111/gcb.14767](https://doi.org/10.1111/gcb.14767): refined growth rates for younger secondary (up to 20
  years),
  older secondary and old-growth tropical and subtropical forest. Values and caveats are in
  [ipcc-age-class-growth.md](ipcc-age-class-growth.md).
- **Further reading, not used for any statement above.** Luyssaert et al. (2008), "Old-growth forests as global carbon
  sinks", *Nature* 455: 213-215, DOI [10.1038/nature07276](https://doi.org/10.1038/nature07276). Only the bibliographic
  record was opened; its abstract was not.

What the dashboard may say: a large old tree holds a large carbon stock and may still be adding carbon each year, and
neither fact makes the tree a source of credits. What it should not say: that old trees stop growing, or that old trees
earn credits.

## How the app uses this

`config/tree-age/rules.yaml` is data. The engine reads it; components render the result and contain no rule
logic (CLAUDE.md principle 2). The programme-level screening files `config/policies/IN.yaml`, `US.yaml` and `EU.yaml`
stay
as they are; this file adds an age-focused layer.

Proposed matching, to be implemented and tested in the policy engine (it is not implemented by this research):

1. **Geography, a hard filter.** `GLOBAL` rules always apply. `EU` rules apply to EU member states (the file's Berlin
   rule
   is `scope: EU` with `country: DE`). `IN` and `US` rules apply to the matching country. A rule with a `subdivision`
   applies only inside it (Haryana `IN-HR`, Maharashtra `IN-MH`, Karnataka `IN-KA`, Delhi `IN-DL`, and the US and German
   municipal examples).
2. **Age, a hard filter.** A rule applies when the entered age is within `min_age_years` and `max_age_years`, where
   `null` means no bound. Only two rules carry a bound: Haryana (75 and over) and Maharashtra heritage trees (50 and
   over), and both are `pending`.
3. **Tree status and setting, soft filters.** `applies_to.trees` and `applies_to.setting` describe what a rule
   regulates.
   A rule written for new plantings (VM0047, Gold Standard, the Green Credit Programme) is still the answer to "can my
   old
   trees earn credits here", so it should be shown to a user with existing trees, in a group such as "does not apply to
   your trees", rather than hidden.
4. **Output.** For existing trees the headline is `outcome_for_existing_trees`: `not-eligible`, `eligible`,
   `conditional`, `protected`, `payment` or `not-applicable`, with the `summary` and `details` text, the `sources` and
   the
   `accessed` date.
5. **Verification badge.** `pending` rules are labelled "not confirmed from a primary source" with the `notes` text.
   Under CLAUDE.md principle 10 a pending parameter must fail a production-mode data-quality test, so the three pending
   rules (Haryana, Maharashtra heritage age, the EU delegated act) must be confirmed against primary sources or excluded
   before a production release.
6. **`status`.** Show `proposed`, `superseded` and `unknown` rules with that label; the EU delegated act is `proposed`.
7. **`is_example`.** A municipal example stands for "check your own local ordinance". Label it as an example, and show
   it
   only as such unless the user's city matches `locality`.
8. **`amount`.** Show an amount only when the field is present, with its currency, unit and `as_of` date, and say when
   it
   comes from press reports. A payment such as the Haryana pension is "other farm income". The app shows three separate
   values (environmental benefit, indicative carbon value as a scenario, other farm income) and never sums them.
9. **Never a credit.** No rule here turns a tree into a credit. India's Green Credits (GCP) and carbon credits (CCTS)
   are
   separate mechanisms, and in the EU an estimate is never automatically CRCF-certifiable.
10. **Disclaimer.** Show the file's `disclaimer` text with every result: screening information only, not legal advice.

**Ask for size as well as age.** Most legal thresholds are size, not age, and they are measured at different heights:
trunk 5.5 cm diameter and 1 m height (Karnataka), 5 cm at 30 cm and 1 m height with girth stated at 1.85 m (Delhi),
circumference 80 cm at 1.30 m (Berlin), 4 inches at 4.5 feet (Los Angeles), 5 inches at breast height for stock
quantification (City Forest Credits). The dashboard should collect trunk diameter or girth and the measurement height
rather than converting between thresholds silently.

### What changes with the age entered

| Age entered | Rules that switch on because of age |
|---|---|
| 5 or 30 years | None. Felling-permission and size-based protection rules apply regardless of age; the 20-year class boundary changes the growth estimate, not the law. |
| 60 years | Maharashtra heritage-tree status becomes possible in urban areas (pending), and the number of replacement trees under Maharashtra's rule is the tree's estimated age. |
| 100 years | Haryana's pension becomes possible for a living tree outside forest land (pending, with species and exclusion conditions), together with the Maharashtra heritage rule. |

### Rule index

| Rule id | Where | Category | Outcome for existing trees | Status | Verification |
|---|---|---|---|---|---|
| `global-icvcm-ccp-additionality` | GLOBAL | methodology-note | conditional | in-force | verified |
| `global-verra-vm0047-arr` | GLOBAL | carbon-credit-eligibility | not-eligible | in-force | verified |
| `global-gold-standard-luf-ar` | GLOBAL | carbon-credit-eligibility | not-eligible | in-force | verified |
| `in-gcp-tree-plantation` | IN | incentive-payment | not-eligible | in-force | verified |
| `in-ccts-offset-bm-fr05-002` | IN | carbon-credit-eligibility | not-eligible | in-force | verified |
| `in-hr-pran-vayu-devta-pension` | IN, IN-HR | incentive-payment | payment | in-force | pending |
| `in-mh-heritage-tree` | IN, IN-MH | tree-protection | protected | in-force | pending |
| `in-mh-compensatory-planting-estimated-age` | IN, IN-MH | compensatory-planting | conditional | in-force | verified |
| `in-ka-preservation-of-trees-act` | IN, IN-KA | tree-protection | protected | in-force | verified |
| `in-dl-preservation-of-trees-act` | IN, IN-DL | tree-protection | protected | in-force | verified |
| `in-dl-compensatory-plantation-circular` | IN, IN-DL | compensatory-planting | conditional | in-force | verified |
| `us-cfc-preservation-protocol` | US | carbon-credit-eligibility | conditional | in-force | verified |
| `us-cfc-afforestation-protocol` | US | carbon-credit-eligibility | not-eligible | in-force | verified |
| `us-car-forest-protocol-ifm` | US | carbon-credit-eligibility | conditional | in-force | verified |
| `us-acr-ifm-non-federal-v2-1` | US | carbon-credit-eligibility | conditional | in-force | verified |
| `us-family-forest-carbon-vm0045` | US | carbon-credit-eligibility | conditional | in-force | verified |
| `us-or-portland-heritage-trees` | US, US-OR, Portland (example) | tree-protection | protected | in-force | verified |
| `us-ca-los-angeles-protected-trees` | US, US-CA, Los Angeles (example) | tree-protection | protected | in-force | verified |
| `eu-crcf-regulation-2024-3012` | EU | carbon-credit-eligibility | conditional | in-force | verified |
| `eu-crcf-carbon-farming-delegated-act-2026` | EU | carbon-credit-eligibility | conditional | proposed | pending |
| `eu-old-growth-forests-guidelines` | EU | tree-protection | conditional | in-force | verified |
| `eu-de-berlin-baumschutzverordnung` | EU, DE, DE-BE, Berlin (example) | tree-protection | protected | in-force | verified |

Totals: 22 rules (19 `verified`, 3 `pending`); 21 `in-force` and 1 `proposed`; scope GLOBAL 3, IN 8, US 7, EU 4.

## Open questions

- **Haryana.** The official notification or guidelines for the age wording, the species list, exclusions and the current
  amount.
- **Maharashtra.** The Government's notified heritage-tree norms (is it 50 years?), the age-estimation method, and the
  consolidated Act on India Code.
- **EU delegated act C(2026)4666.** The text and annexes, the entry-into-force date, and how pre-existing trees and
  biomass are baselined.
- **Karnataka and Delhi.** Amendments, the notified areas and the current penalties; the official KAPY amounts.
- **VM0047.** How the later growth of pre-existing trees is treated; Gold Standard STARR final text; Plan Vivo.
- **City Forest Credits.** The 100-year Preservation version (v14.100) was not opened.
- **IFM protocols.** Newer versions of the CAR and ACR protocols; the ICVCM label for VM0045, reported by the American
  Forest Foundation and not read on the ICVCM site.
- **Coverage.** France and Spain age rules, other Indian states and other US cities were not researched. The IPCC Table
  4.9 values are not verified ([ipcc-age-class-growth.md](ipcc-age-class-growth.md)).

## Sources and method

All pages were accessed on 2026-10-05 through a page-summarising fetch tool, so quotations, section numbers and article
numbers can carry transcription errors; open the cited page before quoting. "Verified" in the rule file means the source
was opened and states the condition. Pages that could not be read: India Code PDFs, aranya.gov.in and the Haryana Chief
Minister's Office page (blocked by robots.txt); haryana.gov.in scheme page (404); myScheme KAPY page (no scheme text);
umwelt-online.de Berlin ordinance (unreadable); the Wiley copy of Requena Suarez et al. (403). The IPCC Table 4.9 PDF
text
was truncated by the tool.

### Sources cited in the rule file

Each source is listed once, under the region of the first rule that cites it, with the rule ids that use it.

#### Global standards

| Title | Publisher | URL | Rules |
|---|---|---|---|
| Core Carbon Principles | Integrity Council for the Voluntary Carbon Market | <https://icvcm.org/core-carbon-principles/> | `global-icvcm-ccp-additionality` |
| VM0047 Afforestation, Reforestation and Revegetation, v1.1 (methodology document) | Verra | <https://verra.org/documents/vm0047-afforestation-reforestation-and-revegetation-v1-1/> | `global-verra-vm0047-arr` |
| VM0047 Afforestation, Reforestation and Revegetation, v1.1 (methodology page) | Verra | <https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-1/> | `global-verra-vm0047-arr` |
| VM0047 v1.1: what you need to know (independent cross-check) | Space Intelligence | <https://www.space-intelligence.com/vm0047-v-1-1-what-you-need-to-know/> | `global-verra-vm0047-arr` |
| Land Use & Forests Activity Requirements, version 1.2.1 (A/R eligibility) | Gold Standard Foundation | <https://globalgoals.goldstandard.org/standards/203_V1.2.1_AR_LUF-Activity-Requirements.pdf> | `global-gold-standard-luf-ar` |
| Land Use & Forests A/R Methodology, version 2.1 | Gold Standard Foundation | <https://globalgoals.goldstandard.org/standards/403_V2.1_LUF_AR-Methodology-GHGs-emission-reduction-and-Sequestration-Methodology.pdf> | `global-gold-standard-luf-ar` |
| Sustainable Transformation through Afforestation, Reforestation and Revegetation (STARR) consultation | Gold Standard Foundation | <https://www.goldstandard.org/consultations/sustainable-transformation-afforestation-reforestation-revegetation-starr> | `global-gold-standard-luf-ar` |

#### India

| Title | Publisher | URL | Rules |
|---|---|---|---|
| Green Credit Programme FAQ | MoEFCC Green Credit Programme portal | <https://www.moefcc-gcp.in/faq> | `in-gcp-tree-plantation` |
| About the Green Credit Programme | MoEFCC Green Credit Programme portal | <https://www.moefcc-gcp.in/about/aboutGCP> | `in-gcp-tree-plantation` |
| Green Credit Programme: Lok Sabha written reply, 16 March 2026 | Press Information Bureau, Government of India | <https://www.pib.gov.in/PressReleasePage.aspx?PRID=2240640&reg=3&lang=1> | `in-gcp-tree-plantation` |
| Green Credit Programme home page (notification list) | MoEFCC Green Credit Programme portal | <https://www.moefcc-gcp.in/> | `in-gcp-tree-plantation` |
| BM FR05.002 Afforestation and reforestation of lands except wetlands, Version 1.0 | Bureau of Energy Efficiency | <https://beeindia.gov.in/sites/default/files/BM_FR05.002_Afforestation_and_reforestation_of_lands_except_wetlands.pdf> | `in-ccts-offset-bm-fr05-002` |
| Haryana to give Rs 2,500 annually to custodians of trees older than 75 years (23 June 2023) | The Tribune | <https://www.tribuneindia.com/news/haryana/haryana-to-give-rs-2-500-annually-to-custodians-of-trees-older-than-75-years-says-minister-519354> | `in-hr-pran-vayu-devta-pension` |
| Old Haryana trees: Rs 3,000 pension and the long red tape (6 September 2025) | ThePrint | <https://theprint.in/ground-reports/old-haryana-trees-rs-3000-pension-and-the-long-red-tape/2737061/> | `in-hr-pran-vayu-devta-pension` |
| 51 trees in Faridabad aged 75 years are receiving an annual pension of Rs 3,000 (13 July 2026) | Amar Ujala | <https://www.amarujala.com/delhi-ncr/faridabad/51-trees-in-faridabad-aged-75-years-are-receiving-an-annual-pension-of-3-000-2026-07-13> | `in-hr-pran-vayu-devta-pension` |
| 55 more trees in Karnal get heritage tag under Pran Vayu Devta scheme (12 June 2025) | The Tribune | <https://www.tribuneindia.com/news/haryana/55-more-trees-in-karnal-get-heritage-tag-under-pran-vayu-devta-scheme/amp> | `in-hr-pran-vayu-devta-pension` |
| Haryana's Pran Vayu Devta Yojana (2 July 2024) | OneIndia | <https://www.oneindia.com/india/haryanas-pran-vayu-devta-yojana-financial-aid-for-elderly-tree-care-011-3863365.html> | `in-hr-pran-vayu-devta-pension` |
| Message from PCCF's Desk (acknowledges the scheme; no amount or age) | Haryana Forest Department | <https://haryanaforest.gov.in/message-from-pccfs-desk/> | `in-hr-pran-vayu-devta-pension` |
| Bill No. VIII of 2021, a Bill further to amend the Maharashtra (Urban Areas) Protection and Preservation of Trees Act, 1975 | Maharashtra Legislature | <https://mls.org.in/assembly-bill/one-house/Bill%20no%208%20of%202021%20Eng.%20One%20House.pdf> | `in-mh-heritage-tree`, `in-mh-compensatory-planting-estimated-age` |
| Maharashtra (Urban Areas) Protection and Preservation of Trees (Amendment) Act, 2021 (text) | Legitquest | <https://www.legitquest.com/act/maharashtra-urban-areas-protection-and-preservation-of-trees-amendment-act-2021/A265> | `in-mh-heritage-tree`, `in-mh-compensatory-planting-estimated-age` |
| Now Maharashtra to give 50-year-old urban trees heritage tag (11 June 2021) | The Tribune | <https://www.tribuneindia.com/news/schools/now-maharashtra-to-give-50-year-old-urban-trees-heritage-tag-266830> | `in-mh-heritage-tree` |
| More than 50 years old tree will be declared as a heritage tree in Maharashtra | Mumbai Live | <https://www.mumbailive.com/en/environment/more-than-50-years-old-tree-will-be-declared-as-a-heritage-tree-in-maharashtra-65671> | `in-mh-heritage-tree` |
| Reply by Respondent 1 in OA No. 92/2024 (quotes the 2021 Amendment Act, State Tree Authority) | National Green Tribunal | <https://www.greentribunal.gov.in/sites/default/files/news_updates/Reply%20by%20R-1%20in%20OA%20No.92-2024%20(page%20nos.10-88).pdf> | `in-mh-heritage-tree` |
| The Karnataka Preservation of Trees Act, 1976 (Karnataka Act 76 of 1976) | PRS Legislative Research (copy of the Act) | <https://prsindia.org/files/bills_acts/acts_states/karnataka/1976/1976KR76.pdf> | `in-ka-preservation-of-trees-act` |
| The Delhi Preservation of Trees Act, 1994 | India Code (Government of India) | <https://www.indiacode.nic.in/bitstream/123456789/13589/1/the_delhi_preservation_of_trees_act_1994.pdf> | `in-dl-preservation-of-trees-act` |
| Circular No. FAWL-L/3/2023-Tree Cell, I/76547/2023 (2 June 2023) | Department of Forests & Wildlife, GNCTD | <https://dpta.eforest.delhi.gov.in/TEMP/CIRCULAR.pdf> | `in-dl-compensatory-plantation-circular` |

#### United States

| Title | Publisher | URL | Rules |
|---|---|---|---|
| Preservation Protocol v14.40 (40-year) | City Forest Credits | <https://www.cityforestcredits.org/wp-content/uploads/2026/08/CFC-Preservation-Protocol-v14.40.pdf> | `us-cfc-preservation-protocol` |
| Carbon protocols (current versions) | City Forest Credits | <https://www.cityforestcredits.org/carbon-protocols/> | `us-cfc-preservation-protocol`, `us-cfc-afforestation-protocol` |
| Afforestation and Reforestation Protocol v12 (26 years) | City Forest Credits | <https://www.cityforestcredits.org/wp-content/uploads/2024/03/CFC-Afforestation-Protocol-v12.pdf> | `us-cfc-afforestation-protocol` |
| U.S. Forest Protocol, Version 5.1 | Climate Action Reserve | <https://climateactionreserve.org/wp-content/uploads/2023/07/Final_Forest_Protocol_V5.1_7.14.2023.pdf> | `us-car-forest-protocol-ifm` |
| Improved Forest Management (IFM) on Non-Federal U.S. Forestlands, Version 2.1 (July 2024) | American Carbon Registry | <https://acrcarbon.org/wp-content/uploads/2022/07/ACR-Methodology-IFM-on-Non-Federal-US-Forestlands-v2_1-20240701.pdf> | `us-acr-ifm-non-federal-v2-1` |
| Family Forest Carbon Program: how it works | American Forest Foundation | <https://familyforestcarbon.org/about-the-program/how-it-works/> | `us-family-forest-carbon-vm0045` |
| Family Forest Carbon Program: get started (eligibility) | American Forest Foundation | <https://familyforestcarbon.org/about-the-program/get-started/> | `us-family-forest-carbon-vm0045` |
| VM0045 Improved Forest Management Using Dynamic Matched Baselines from National Forest Inventories, v1.2 | Verra | <https://verra.org/methodologies/vm0045-improved-forest-management-using-dynamic-matched-baselines-from-national-forest-inventories-v1-2/> | `us-family-forest-carbon-vm0045` |
| First improved forest management methodology designed for family forests recognized by global body for high integrity | American Forest Foundation | <https://www.forestfoundation.org/why-we-do-it/family-forest-blog/first-improved-forest-management-methodology-designed-for-family-forests-recognized-by-global-body-for-high-integrity/> | `us-family-forest-carbon-vm0045` |
| Portland City Code 11.20.060 Heritage Trees | City of Portland | <https://www.portland.gov/code/11/20/060> | `us-or-portland-heritage-trees` |
| Heritage Trees | City of Portland, Urban Forestry | <https://www.portland.gov/trees/heritage> | `us-or-portland-heritage-trees` |
| Protected Tree and Shrub regulations (Ordinance 186873) summary | City of Los Angeles, Department of City Planning | <https://planning.lacity.gov/odocument/555281f6-f5ef-44e9-b094-1fce25c1c4dc> | `us-ca-los-angeles-protected-trees` |
| Guidelines and requirements for regulated trees (P/ZC 2024-022) | City of Los Angeles, Department of Building and Safety | <https://dbs.lacity.gov/sites/default/files/efs/pdf/publications/zoning/IB-GUIDELINES-AND-REQUIREMENTS-FOR-REGULATED-TREES.pdf> | `us-ca-los-angeles-protected-trees` |

#### European Union

| Title | Publisher | URL | Rules |
|---|---|---|---|
| Regulation (EU) 2024/3012 establishing a Union certification framework for permanent carbon removals, carbon farming and carbon storage in products | EUR-Lex (Official Journal of the European Union) | <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202403012> | `eu-crcf-regulation-2024-3012` |
| Commission adopts certification methodologies for carbon farming under the CRCF Regulation (10 July 2026) | European Commission, DG CLIMA | <https://climate.ec.europa.eu/news-other-reads/news/commission-adopts-certification-methodologies-carbon-farming-under-crcf-regulation-2026-07-10_en> | `eu-crcf-carbon-farming-delegated-act-2026` |
| Certification methodologies under the CRCF Regulation | European Commission, DG CLIMA | <https://climate.ec.europa.eu/areas-action/carbon-removals-and-carbon-farming/certification-methodologies_en> | `eu-crcf-carbon-farming-delegated-act-2026` |
| CRCF tree planting rules (critique of an earlier draft, March 2025) | Carbon Market Watch | <https://carbonmarketwatch.org/wp-content/uploads/2025/03/TREE-PLANTING.pdf> | `eu-crcf-carbon-farming-delegated-act-2026` |
| Takeaways from the carbon farming expert group (25 February 2026) | Bellona Europa | <https://eu.bellona.org/2026/02/25/takeaways-from-the-carbon-farming-expert-group/> | `eu-crcf-carbon-farming-delegated-act-2026` |
| Guidelines for defining, mapping, monitoring and strictly protecting EU primary and old-growth forests (publication page) | European Commission, DG Environment | <https://environment.ec.europa.eu/publications/guidelines-defining-mapping-monitoring-and-strictly-protecting-eu-primary-and-old-growth-forests_en> | `eu-old-growth-forests-guidelines` |
| Commission Staff Working Document SWD(2023) 62 final (full text, third-party copy) | actu-environnement.com (copy of the Commission document) | <https://www.actu-environnement.com/media/pdf/news-41427-lignes-directrices-forets-primaires-ue.pdf> | `eu-old-growth-forests-guidelines` |
| Baumschutzverordnung: Ausnahmegenehmigung (service description) | Service Berlin (Land Berlin) | <https://service.berlin.de/dienstleistung/330487/> | `eu-de-berlin-baumschutzverordnung` |
| Baumschutz (Umwelt- und Naturschutzamt Mitte) | Bezirksamt Mitte von Berlin | <https://www.berlin.de/ba-mitte/politik-und-verwaltung/aemter/umwelt-und-naturschutzamt/naturschutz/artikel.246719.php> | `eu-de-berlin-baumschutzverordnung` |

### Sources used in this report only

| Title | Publisher | URL | Used for |
|---|---|---|---|
| PV Climate standard | Plan Vivo Foundation | <https://www.planvivo.org/projects/certify-a-project/pvclimate> | Plan Vivo note |
| Karnataka Welfare Schemes on Poverty Alleviation (undated; lists KAPY payments) | Government of Karnataka (departmental source material) | <https://cdnbbsr.s3waas.gov.in/s38182fa34e3615c643a9dddca59ab80f9/uploads/2026/02/202602191242606134.pdf> | KAPY amounts (pending) |
| Krushi Aranya Protsaha Yojane (official page, blocked by robots.txt) | Karnataka Forest Department | <https://aranya.gov.in/aranyacms/English/IndividualScheme.aspx?HkxuiBwcRAlH/nwkzKruPQ=%3D> | KAPY, not read |
| Protecting heritage trees through a special law (15 February 2018) | Down To Earth | <https://www.downtoearth.org.in/india/protecting-heritage-trees-through-a-special-law-59703> | Tamil Nadu note |
| Rate of tree carbon accumulation increases continuously with tree size | Nature 507: 90-93 | <https://www.nature.com/articles/nature12914> | Science notes (abstract read) |
| Age-related decline in forest productivity: pattern and process | Advances in Ecological Research 27 | <https://www.sciencedirect.com/science/article/abs/pii/S0065250408600094> | Science notes (publisher summary read) |
| Carbon cycling and storage in world forests: biome patterns related to forest age | Global Change Biology 10(12) | <https://api.crossref.org/works/10.1111/j.1365-2486.2004.00866.x> | Science notes (Crossref abstract read) |
| Old-growth forests as global carbon sinks | Nature 455: 213-215 | <https://api.crossref.org/works/10.1038/nature07276> | Further reading (record only) |
| Estimating aboveground net biomass change for tropical and subtropical forests (Requena Suarez et al. 2019) | Global Change Biology 25(11) | <https://pmc.ncbi.nlm.nih.gov/articles/PMC6852081/> | IPCC age classes |
| Policy references (repository note) | CarbonCreditBuy | [policy-references.md](policy-references.md) | GCP and CCTS background, COMET-Planner and EQIP/CSP entries, G.S.R. number |
