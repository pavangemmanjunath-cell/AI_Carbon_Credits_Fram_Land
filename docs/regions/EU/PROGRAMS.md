# Programs — European Union

This page describes the three programs CarbonCreditBuy screens for plots in the European Union and what is still
unconfirmed. The rules themselves live in [`config/policies/EU.yaml`](../../../config/policies/EU.yaml). The screening
is never an eligibility determination: "Initial screening only — not an eligibility determination. Under the CRCF a
calculated estimate is never automatically certifiable; certification by a recognised scheme is required."

Statements about rules carry a source link. A statement we could not confirm against the primary document is marked
*(unverified)*: verify it against the current text before you rely on it, because this area changes quickly. The
research behind this page is in [policy-references.md](../../research/policy-references.md) and
[tree-age-carbon-rules.md](../../research/tree-age-carbon-rules.md), last verified on 2026-10-05.

## Certification, incentives and credits

| Mechanism | Kind | What it produces | Tradable |
| --- | --- | --- | --- |
| EU CRCF | Certification framework | Units, including temporary carbon-farming units, issued through recognized certification schemes | Scheme-dependent; the units are for EU climate objectives only |
| CAP eco-schemes | Incentive | Area payments | No |
| Voluntary standards and national labels | Voluntary standard | Credits issued after verification | Yes |

Source: the taxonomy in
[policy-references.md](../../research/policy-references.md#7-carbon-credit-vs-incentive-taxonomy-the-engine-should-use).
CarbonCreditBuy shows an incentive as other farm income and an estimate as an environmental benefit. Neither is a credit
([carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md)).

## What the engine returns

These are the statuses the policy engine returns by activity. A member-state code such as `DE` returns the same
statuses as `EU`. The web app always asks about **tree plantation**; the other activities are reachable through the API
([policy engine](../../../packages/policy-engine/README.md)).

| Activity | CRCF | CAP eco-schemes | Voluntary standards |
| --- | --- | --- | --- |
| Tree plantation | `requires_certification` | `potentially_applicable` | `requires_methodology_assessment` |
| Agroforestry | `requires_certification` | `potentially_applicable` | `requires_methodology_assessment` |
| Cropland practice | `requires_certification` | `potentially_applicable` | `requires_methodology_assessment` |
| Soil carbon | `requires_certification` | `not_applicable` | `requires_methodology_assessment` |
| Grazing | `unknown` | `not_applicable` | `unknown` |

`unknown` means no rule covers the case; do not read it as "no". The `not_applicable` entries for CAP come from the
rule's list of activities, not from a finding about the CAP: TODO(verify) with a Commission or member-state source
whether soil practices and grazing belong in that rule.

## The CRCF

The Carbon Removals and Carbon Farming Certification Framework is a **voluntary EU framework for certifying** permanent
carbon removals, carbon farming and carbon storage in products. It certifies; it does not itself pay anyone or run a
market.

| Item | Detail | Source |
| --- | --- | --- |
| Regulation | Regulation (EU) 2024/3012 of 27 November 2024, published in the Official Journal on 6 December 2024 and in force since 26 December 2024 | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/3012/oj/eng); [Carbon Gap tracker](https://tracker.carbongap.org/policy/crcf/) |
| Criteria | Quantification, additionality, long-term storage and sustainability, the "QU.A.L.ITY" criteria (Articles 4 to 7) | [Carbon Gap tracker](https://tracker.carbongap.org/policy/crcf/) |
| Unit types | Permanent removal units; carbon farming sequestration units and carbon farming emission-reduction units (both temporary); carbon storage in products units. The four types remain distinct | [Carbon Gap tracker](https://tracker.carbongap.org/policy/crcf/) |
| Use of units | Solely for the EU's climate objectives and nationally determined contribution; not counted toward third-country targets or CORSIA | [Carbon Gap tracker](https://tracker.carbongap.org/policy/crcf/); [Global ELR, March 2026](https://www.globalelr.com/2026/03/carbon-removals-and-carbon-farming-recent-eu-developments/) |
| Recognition of schemes | Implementing Regulation (EU) 2025/2358 (November 2025) covers the recognition of certification schemes, certification bodies and audits | [Global ELR, March 2026](https://www.globalelr.com/2026/03/carbon-removals-and-carbon-farming-recent-eu-developments/) |
| Permanent removals | Delegated Regulation (EU) 2026/285, adopted 3 February 2026: direct air capture, bioenergy with capture, and biochar | [Commission methodologies page](https://climate.ec.europa.eu/areas-action/carbon-removals-and-carbon-farming/certification-methodologies_en) |
| **Carbon farming** | Delegated act adopted on 10 July 2026 (C(2026)4666) covering agriculture and agroforestry on mineral soils, rewetting and restoration of peatlands and organic soils, and afforestation. It enters into force after scrutiny by Parliament and Council, and certification schemes can then apply for recognition. Entry into force was not confirmed as of 2026-10-05 | [Commission news, 10 July 2026](https://climate.ec.europa.eu/news-other-reads/news/commission-adopts-certification-methodologies-carbon-farming-under-crcf-regulation-2026-07-10_en) |
| Still to come | Carbon storage in buildings (end of 2026); further permanent pathways under consideration; a Union registry planned for 2028 | [Commission methodologies page](https://climate.ec.europa.eu/areas-action/carbon-removals-and-carbon-farming/certification-methodologies_en); [Carbon Gap tracker](https://tracker.carbongap.org/policy/crcf/) |

### What the Regulation says about carbon farming

The following comes from a research reading of the Regulation's text. Article and paragraph numbers can carry
transcription errors, so open the text before you quote it
([EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202403012)).

| Topic | Reading |
| --- | --- |
| Definition | Carbon farming is a practice carried out over an activity period of at least five years (Article 2(10)) |
| Net benefit | The benefit is total removals minus baseline removals and associated emissions, with a preference for standardized baselines (Article 4) |
| Additionality | The activity must go beyond Union and national statutory requirements, and the certification must have an incentive effect (Article 5) |
| Monitoring | Monitoring runs for at least the activity period, and operators are liable for releases during monitoring (Article 6) |
| Existing carbon stocks | Not addressed explicitly; treating them as part of the baseline follows from the net-benefit formula in Article 4 |

### What CarbonCreditBuy rule says

Status `requires_certification` for tree plantation, agroforestry, soil carbon and cropland practice, otherwise
`unknown`. The requirements it lists: an activity covered by an adopted CRCF certification methodology; a baseline and
an
additionality demonstration per the methodology; monitoring, reporting and verification by a certification body; a
liability mechanism for reversals and a minimum monitoring period; registration in a recognized scheme's registry.

The reason text on the card says afforestation and agroforestry on mineral soils "are addressed by Commission
certification methodologies". As of the research date those methodologies were adopted but not confirmed in force, and
no scheme could yet be recognized to issue units for them, so we found no scheme issuing CRCF units for agroforestry
*(unverified)*. The research note recommends a date-stamped reason and a note that units serve EU climate objectives
only
([policy-references.md](../../research/policy-references.md#8-what-configpoliciesyaml-should-say-concrete-edits)).

### What this means for a farmer

- **CarbonCreditBuy estimate is not a CRCF unit and cannot become one by itself.** A scheme recognized under the CRCF
  has to
  certify your activity against a certification methodology, with a baseline, monitoring and verification.
- **Ask which scheme, and when.** Because recognition follows entry into force, a scheme that accepts agroforestry may
  not
  exist yet where you farm. Ask your adviser or your forestry authority.
- **Read critiques as critiques.** Civil-society groups criticized earlier drafts, for example for how a zero
  standardized
  baseline treats existing trees ([Carbon Market Watch, March
  2025](https://carbonmarketwatch.org/wp-content/uploads/2025/03/TREE-PLANTING.pdf);
  [Bellona, 25 February 2026](https://eu.bellona.org/2026/02/25/takeaways-from-the-carbon-farming-expert-group/)). They
  are not evidence of what the adopted text says.

## CAP eco-schemes and agri-environment-climate measures

**What they are.** The Common Agricultural Policy pays farmers through national CAP Strategic Plans. The plans include
eco-schemes and investment support. They are incentives, not carbon credits
([Commission, CAP Strategic Plans](https://agriculture.ec.europa.eu/cap-my-country/cap-strategic-plans_en)).

**What CarbonCreditBuy rule says.** Status `potentially_applicable` for tree plantation, agroforestry and cropland
practice,
otherwise `not_applicable`. The reason: national plans include eco-schemes and investment support for agroforestry and
afforestation. Requirements listed: active-farmer status and CAP registration in the member state; compliance with the
national eco-scheme conditions.

**What it does not say.** CarbonCreditBuy does not know your member state's plan, so it lists no national scheme,
payment rate,
deadline or eligibility condition. These differ from one member state to the next. Ask your paying agency. TODO(verify):
a per-country page for each member state, each with an official source, would close this gap; see
[roadmap ideas](../../community/roadmap-ideas.md#regions-and-policy).

**If you also want carbon revenue.** Ask the certification scheme or standard how it treats a subsidy that already paid
for the same trees ([additionality](../../concepts/additionality.md)). Under the CRCF an activity must go beyond
statutory requirements and rely on the incentive effect of certification (reading above).

## Voluntary standards and national labels

**What CarbonCreditBuy rule says.** Status `requires_methodology_assessment` for tree plantation, agroforestry, soil
carbon and
cropland practice, otherwise `unknown`. Requirements listed: an approved methodology for the activity; a baseline,
additionality, leakage and permanence assessment; third-party verification and registry issuance.

| Standard or label | What the research found | Source |
| --- | --- | --- |
| Verra VM0047, Afforestation, Reforestation and Revegetation | Version 1.1 active since 14 May 2025, with an area-based approach and a census-based approach for dispersed planting. Details are on the [United States programs page](../US/PROGRAMS.md#new-planting-and-cropland-practices); the methodology is global. The EU policy file still points to version 1.0 | [Verra, VM0047 v1.1](https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-1/) |
| Gold Standard, Land Use and Forests, afforestation and reforestation | The eligible area must not have met the definition of forest 10 years before the project start date (Activity Requirements v1.2.1, Section 2.1.1(b)), so credits are not issued for existing forests. The baseline is the tree and non-tree biomass present just before planting (methodology v2.1). A successor framework, STARR, was consulted on from 22 April to 22 May 2026; final publication was not confirmed | [Gold Standard Activity Requirements v1.2.1](https://globalgoals.goldstandard.org/standards/203_V1.2.1_AR_LUF-Activity-Requirements.pdf); [STARR consultation](https://www.goldstandard.org/consultations/sustainable-transformation-afforestation-reforestation-revegetation-starr) |
| Label Bas-Carbone (France) | A French national label, named in CarbonCreditBuy rule. TODO(verify): its approved methods, eligibility and payment arrangements were not researched | [Ministry of Ecological Transition](https://www.ecologie.gouv.fr/label-bas-carbone) |

Other national labels and schemes exist or may exist in other member states. None has been researched, and
CarbonCreditBuy
names only the French label.

## Rules by tree age

Separately from the program screening above, the Tree age page of the web app and `POST /api/v1/tree-age/assess`
list the rules that treat trees differently by age, size or setting. They come from
[`config/tree-age/rules.yaml`](../../../config/tree-age/rules.yaml), where each rule carries its sources, the date they
were opened and a verification status. A user in any member state sees the seven below: four for the EU and three global
standards. None states an amount, and none sets an age threshold. The research and the open questions are in the
[research note](../../research/tree-age-carbon-rules.md#european-union). To add one, see
[adding a tree-age rule](../../developer-guide/adding-a-tree-age-rule.md).

| Rule id | Written for | What it says | Outcome for existing trees | Status |
| --- | --- | --- | --- | --- |
| `global-icvcm-ccp-additionality` | Any trees | ICVCM Core Carbon Principles 5 to 7: a credit counts only removals that would not have happened without carbon revenue, so growth that standing trees would make anyway is not creditable on its own. A methodology note, not a route to a credit | `conditional` | In force, `verified` |
| `global-verra-vm0047-arr` | New planting | Verra VM0047 credits trees a project plants or restores. The carbon in pre-existing trees is measured as a starting stock and not credited | `not-eligible` | In force, `verified` |
| `global-gold-standard-luf-ar` | New planting, outside forest | Gold Standard A/R covers only land that was not forest 10 years before the project start | `not-eligible` | In force, `verified` |
| `eu-crcf-regulation-2024-3012` | Any trees | Regulation (EU) 2024/3012: only net removals above a baseline, from an activity of at least five years, can be certified, and the activity must go beyond legal requirements and need the incentive of certification | `conditional` | In force, `verified` |
| `eu-crcf-carbon-farming-delegated-act-2026` | New planting | Commission delegated act C(2026)4666, adopted 10 July 2026, with certification methodologies for afforestation, agroforestry on mineral soils and peatland rewetting. Until it enters into force, certification schemes cannot apply for recognition for these activities | `conditional` | `proposed`, `pending` |
| `eu-old-growth-forests-guidelines` | Existing forest | Guidelines SWD(2023) 62 final: non-binding guidance for Member States to identify and strictly protect old-growth forests with structural indicators such as old or large trees and deadwood. No numeric age threshold | `conditional` | In force, `verified` |
| `eu-de-berlin-baumschutzverordnung` | Existing urban trees (example) | Berlin's Baumschutzverordnung protects deciduous trees (except fruit trees), Scots pines, walnuts and Turkish hazels from a trunk circumference of 80 cm at 1.30 m, or 50 cm on at least one stem of a multi-stem tree. The test is size, not age | `protected` | In force, `verified` |

How to read it. The engine filters by place, then by setting (farm, town or city, forest), then by age. A member-state
code such as `DE` returns the EU rules, and the Berlin example applies only when the state is Berlin (`DE-BE`) and the
trees are urban. The credit outlook for existing trees reads "conditional" because of the CRCF Regulation, which sets
conditions rather than a yes or no. The research reads the net-benefit formula as treating the carbon that standing
trees
already hold as part of the baseline, but the Regulation does not address existing stocks explicitly, so confirm the
reading from the text. The outlook never says "eligible", an estimate is never automatically certifiable, and the
sentence on every result stays the same: screening information, not legal advice.

**The pending rule.** `eu-crcf-carbon-farming-delegated-act-2026` is `proposed` and `pending`: its text and annexes were
not read, and entry into force was not confirmed on 2026-10-05. In development the page shows it with a "not yet
confirmed" flag. A production deployment withholds it and lists its id in `withheld_rule_ids` until a reviewer has read
the primary source and set it to `verified`.

## What CarbonCreditBuy does not screen

Member-state programs and national forestry or afforestation grants; national and local tree-protection rules; and any
standard other than the ones above. Tree protection varies widely: the tree-age rules hold one municipal example,
Berlin's ordinance, which protects trees by trunk circumference, not age, and the Commission's guidelines on old-growth
forests contain no numerical age threshold ([research note](../../research/tree-age-carbon-rules.md#european-union)).
Check your own local rules before you fell or prune a large tree.

## Open items for reviewers

| Item | What to do |
| --- | --- |
| CRCF reason text | Date-stamp it: delegated act adopted 10 July 2026, not yet in force, units for EU objectives only |
| CRCF Regulation text | Confirm the Article 2, 4, 5 and 6 readings above, including the minimum monitoring period and liability, from EUR-Lex |
| Delegated act C(2026)4666 | Read the text and annexes, the entry-into-force date and how pre-existing trees are baselined. Until then its tree-age rule stays `pending` and is withheld in production ([adding a tree-age rule](../../developer-guide/adding-a-tree-age-rule.md#pending-rules-and-production)) |
| Other member states | The tree-age rules have one municipal example (Berlin); France and Spain were not researched. Add rules from official texts |
| Verra versions | Update the VM0047 URL and registry entry to version 1.1 |
| CAP | Add per-member-state pages from official sources; decide whether soil practices and grazing belong in the rule |
| Label Bas-Carbone and other labels | Research from official sources before adding detail |
| Price scenario | The EU scenario is `pending` ([`carbon-price-scenarios.yaml`](../../../config/market/carbon-price-scenarios.yaml)) |

## Related pages

[README.md](README.md) · [DATA_SOURCES.md](DATA_SOURCES.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[Policy engine](../../../packages/policy-engine/README.md)
