# Incentives — India

State governments in India run schemes that pay farmers to plant and keep trees, or sell them seedlings at a low
price. They are **incentives**: payments or subsidies, not carbon credits. They carry no tonnes of CO₂e, they are not
issued by a registry, and CarbonCreditBuy treats them as part of **other farm income**, never added to the carbon
figures
([results explained](../../user-guide/results-explained.md#why-the-three-values-are-never-added)). They are also
separate from the Green Credit Programme ([GREEN_CREDIT.md](GREEN_CREDIT.md)) and from the carbon-credit scheme
([CCTS.md](CCTS.md)).

This page says what CarbonCreditBuy shows for them, what is known about two named schemes, and what to ask the office
before
you apply. Facts that came from news reports or secondary pages, or that we could not read on an official page, are
marked *(unverified)*. Amounts change: verify every number against the current scheme order with the responsible
department. The research behind this page is in [policy-references.md](../../research/policy-references.md) and
[tree-age-carbon-rules.md](../../research/tree-age-carbon-rules.md).

## What CarbonCreditBuy shows

In the "Potential policy pathways" list for India, one card is called **State agroforestry / horticulture missions
(incentives)** (`in-state-agroforestry` in [`config/policies/IN.yaml`](../../../config/policies/IN.yaml)).

| Item | What the rule says |
|---|---|
| Status for tree plantation or agroforestry | `potentially_applicable`: worth looking into, not a statement that you qualify |
| Status for any other activity | `not_applicable` |
| Reason shown | Several states pay per-surviving-tree incentives or subsidize saplings for farmers; conditions vary by state |
| Requirements listed | Farmer registration with the state forest or horticulture department; survival verification after 1 to 3 years |
| Reference | Karnataka Forest Department, Krishi Aranya Protsaha Yojane ([aranya.gov.in](https://aranya.gov.in/)) |

Three things to keep in mind:

- **The screening does not know your state.** In version 0.1 it looks only at the activity and the plot area, so every
  plot in India gets the same card, and the Karnataka scheme named on it is an example, not a finding about your plot.
  The policy engine has no state or district input yet ([policy engine](../../../packages/policy-engine/README.md)).
- **The card names no amounts.** CarbonCreditBuy does not calculate what an incentive might pay.
- **The income line is empty.** The **Other farm income** card lists "Eligible incentives (state agroforestry /
  horticulture missions)" with the source "programme screening", and in version 0.1 you cannot type values in. Keep
  the amounts in your own records.

## Karnataka: Krushi Aranya Protsaha Yojane (KAPY)

KAPY is a Karnataka Forest Department scheme for farmers who plant trees on their own land. CarbonCreditBuy
configuration
spells the name "Krishi"; other sources write "Krushi". Neither official page could be read in the research: the
Forest Department page was blocked to the fetch tool and the myScheme page held no scheme text
([research
note](../../research/tree-age-carbon-rules.md#karnataka-preservation-of-trees-act-1976-and-an-incentive-scheme)).
Everything below is therefore *(unverified)*. Do not plan around these numbers; ask the Range Forest Office.

| Item | What is reported | Source |
|---|---|---|
| Run by, started | The Karnataka Forest Department; launched in 2011 *(unverified)* | [Government of Karnataka, welfare schemes document (undated)](https://cdnbbsr.s3waas.gov.in/s38182fa34e3615c643a9dddca59ab80f9/uploads/2026/02/202602191242606134.pdf) |
| Who | Farmers who own land, shown by land records (RTC or pahani) *(unverified)* | [govtschemes.in](https://www.govtschemes.in/karnataka-krushi-aranya-protsaha-yojane) |
| Incentive | ₹35 for each surviving seedling in the first year, ₹40 in the second and ₹50 in the third, ₹125 in all *(unverified)* | [Government of Karnataka, welfare schemes document (undated)](https://cdnbbsr.s3waas.gov.in/s38182fa34e3615c643a9dddca59ab80f9/uploads/2026/02/202602191242606134.pdf) |
| Seedlings | Sold at ₹1, ₹3 or ₹5, depending on bag size *(unverified)* | [govtschemes.in](https://www.govtschemes.in/karnataka-krushi-aranya-protsaha-yojane) |
| How to apply | At the Range Forest Office before the end of May, with a ₹10 fee *(unverified)* | [govtschemes.in](https://www.govtschemes.in/karnataka-krushi-aranya-protsaha-yojane) |
| Limit | Up to 400 trees per hectare *(unverified)* | [bhoomiforrtc.in](https://bhoomiforrtc.in/krushi-aranya-protsaha-yojane-kapy/) |
| Species left out | Eucalyptus, acacia and grafted mango are reported as excluded *(unverified)* | [bhoomiforrtc.in](https://bhoomiforrtc.in/krushi-aranya-protsaha-yojane-kapy/) |

The last row matters for CarbonCreditBuy users: eucalyptus and mango are both in CarbonCreditBuy species table for
India, but a species
CarbonCreditBuy can estimate is not necessarily one a scheme pays for. Ask which species and which planting material
count.

KAPY is not in the age-based rule file ([`config/tree-age/rules.yaml`](../../../config/tree-age/rules.yaml))
because its amounts are unconfirmed. The research note recommends recording the ₹35, ₹40 and ₹50 schedule as a
`pending` value when the Karnataka entry in `config/policies/IN.yaml` is next revised
([policy-references.md](../../research/policy-references.md#6-karnataka--krushi-aranya-protsaha-yojane-kapy)).

## Haryana: Pran Vayu Devta Pension Scheme

This scheme is about trees that already stand, not new planting, so it matters mostly to the **Tree age** feature
([tree-age rules](../../research/tree-age-carbon-rules.md#haryana-pran-vayu-devta-pension-scheme-pending)). Haryana
reportedly pays the custodian of a very old living tree outside forest land an annual pension. The details are all
*(unverified)*, because the only official page found names the scheme but gives no age or amount
([Haryana Forest Department](https://haryanaforest.gov.in/message-from-pccfs-desk/)).

| Item | What is reported | Source |
|---|---|---|
| Age | Trees "older than 75 years" in 2023; later reports say 75 years or older | [The Tribune, 23 June 2023](https://www.tribuneindia.com/news/haryana/haryana-to-give-rs-2-500-annually-to-custodians-of-trees-older-than-75-years-says-minister-519354) |
| Amount per tree per year | ₹2,500 in 2023; ₹2,750 in 2024; ₹3,000 in 2025 and again in July 2026 | [The Tribune, 2023](https://www.tribuneindia.com/news/haryana/haryana-to-give-rs-2-500-annually-to-custodians-of-trees-older-than-75-years-says-minister-519354); [OneIndia, 2 July 2024](https://www.oneindia.com/india/haryanas-pran-vayu-devta-yojana-financial-aid-for-elderly-tree-care-011-3863365.html); [ThePrint, 6 September 2025](https://theprint.in/ground-reports/old-haryana-trees-rs-3000-pension-and-the-long-red-tape/2737061/); [Amar Ujala, 13 July 2026](https://www.amarujala.com/delhi-ncr/faridabad/51-trees-in-faridabad-aged-75-years-are-receiving-an-annual-pension-of-3-000-2026-07-13) |
| Conditions reported | The tree stands outside forest land; fallen, hollow, dead, dry or diseased trees are excluded; later reports add a list of 40 native species and approval by a district committee | Press reports summarized in the [research note](../../research/tree-age-carbon-rules.md#haryana-pran-vayu-devta-pension-scheme-pending) |

In the rule file the scheme is `in-hr-pran-vayu-devta-pension` with `verification_status: pending`. A pending rule
must be confirmed against the official notification, or excluded, before a production release. It is other farm
income and is never added to a carbon value.

## Horticulture missions

The data-source notes for India refer to state horticulture missions (MIDH) as a source of orchard-establishment
subsidies ([DATA_SOURCES.md](DATA_SOURCES.md)). TODO(verify): this project has not read the scheme documents, so it
states no rates, crops or eligibility rules for them. If you plant fruit trees, ask the district horticulture office
which mission applies to your crop and area.

Other states may pay per-surviving-tree incentives too, as the rule text says. Only the two schemes above were
researched.

## Questions to ask before you apply

1. Which office runs the scheme in my state, and what is the application window?
2. Which land records and which farmer registration does it require?
3. Which species and which planting material are allowed or excluded?
4. What are the minimum area and the maximum number of trees per hectare?
5. When is survival checked, how is it counted, and when and how is the payment made?
6. Must I keep the trees for a minimum period, and what happens if some die?
7. If I later want the same trees in a carbon project, how does that programme treat a subsidy that already paid for
   planting? Programmes test whether a project would have happened anyway, so read
   [additionality](../../concepts/additionality.md) and ask them before you sign anything.

Keep records for each answer. Dated photographs, yearly survival counts and land records also raise your evidence
readiness in the app ([results explained](../../user-guide/results-explained.md#carbon-readiness)).

## Adding or correcting a state

Open a "Policy rule proposal" issue
([`region_rule.yml`](../../../.github/ISSUE_TEMPLATE/region_rule.yml)) with the official scheme page or order, the
department, who is eligible, the amounts with their date, and what you could not confirm. The policy engine has no
state input in version 0.1, so a state-specific rule would apply to every plot in India. Until that is added, state
schemes are described on this page rather than as separate rules ([adding a
region](../../developer-guide/adding-a-region.md)).

## Related pages

[README.md](README.md) · [GREEN_CREDIT.md](GREEN_CREDIT.md) · [CCTS.md](CCTS.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[DATA_SOURCES.md](DATA_SOURCES.md)
