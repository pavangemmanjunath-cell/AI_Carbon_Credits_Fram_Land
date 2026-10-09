# Green Credit Programme (India)

The Green Credit Programme (GCP) is a government incentive mechanism, not
a carbon market. This page explains what it is, what its tree-plantation
methodology covers, why **Green Credits are distinct from carbon credits
under the CCTS**, and what the Atlas shows for it. Statements about the
rules are summarized from the notifications linked below; where we could
not confirm a detail against the current text, the page says *verify
against the current notification*.

## Legal basis and administration

| Item | Detail | Source |
|---|---|---|
| Rules | Green Credit Rules, 2023, notified by the Ministry of Environment, Forest and Climate Change (MoEFCC) under the Environment (Protection) Act, 1986, in October 2023 (draft published June 2023) | MoEFCC, <https://moef.gov.in/> ; e-Gazette notification — verify the G.S.R. number and date against the current notification |
| Administrator | Indian Council of Forestry Research and Education (ICFRE), Dehradun | <https://icfre.gov.in/> |
| Governance | Steering committee chaired by the MoEFCC Secretary; a technical committee; the Administrator operates the programme and the registry/platform | Green Credit Rules, 2023 |
| Portal | The Green Credit Programme portal operated by the Administrator (registration of applicants and of land parcels) | <https://www.moefcc-gcp.in/> — verify the current address |
| Activities listed in the Rules | Tree plantation, water management, sustainable agriculture, waste management, air pollution reduction, mangrove conservation and restoration, Ecomark, sustainable building and infrastructure | Green Credit Rules, 2023 |

## The tree-plantation methodology (February 2024)

The first activity methodology notified was for tree plantation (MoEFCC
notification of February 2024; verify the date and any later amendments).
Its scope, as we understand it:

- **Land**: plantation takes place on **degraded land parcels** — such as
  open forest, scrub land, wasteland and catchment areas — that state and
  union-territory forest departments identify and register on the portal,
  typically as blocks of a minimum size (the notification specifies a
  minimum block size; verify). The land is public forest-department land,
  not the applicant's private land.
- **Who applies**: individuals, companies, philanthropies, public-sector
  undertakings and other entities register on the portal, select a parcel
  and pay the forest department's cost of plantation and maintenance.
- **Who plants**: the forest department carries out the plantation and
  maintenance according to a management plan.
- **Credits**: after an evaluation period (the notification specifies the
  timing), the Administrator verifies the plantation and issues Green
  Credits at a rate linked to the number of trees, subject to a **minimum
  tree density per hectare** stated in the methodology (verify the rate
  and the density threshold against the current notification; a 2024
  value widely reported was one credit per tree with a minimum density of
  1,100 trees per hectare).
- **Use**: Green Credits are intended for environmental reporting and
  corporate social responsibility or similar disclosures, may be traded on
  the programme's domestic platform once trading rules are in place, and
  MoEFCC guidelines have linked GCP plantations to the fulfilment of
  compensatory afforestation obligations under forest-conservation law
  (verify the current guidelines).

The consequence for this platform is direct: **a farmer's own orchard or
agroforestry plot is not the pathway the 2024 tree-plantation methodology
describes.** That is why `config/policies/IN.yaml` returns
`requires_assessment` rather than `potentially_applicable` for tree
plantation and agroforestry on private land, with the reason text
pointing to the Administrator. Later methodologies (for example for
sustainable agriculture or agroforestry) may change this; the policy file
is updated by pull request when a notification appears.

## Green Credits are not carbon credits

| | Green Credit (GCP) | Carbon credit (CCTS) |
|---|---|---|
| Ministry | MoEFCC | Ministry of Power (BEE administers) |
| Unit | A Green Credit for a specified environmental activity (for tree plantation: tied to trees planted and surviving) | A Carbon Credit Certificate for one tCO₂e reduced or removed |
| Purpose | Incentivize voluntary environmental actions; reporting and CSR-type use; compensatory-afforestation linkage | Compliance with emission-intensity targets; voluntary offset projects |
| Quantification | Activity-based (counts, density, survival) | GHG-based (baseline, additionality, monitoring, verification) |
| Fungibility | Not a carbon credit; cannot be used for CCTS compliance | Not a Green Credit |

The Green Credit Rules state that a Green Credit is distinct from a carbon
credit, and MoEFCC has clarified that an activity which earns Green
Credits may *separately* earn carbon credits under a carbon-market scheme
if it meets that scheme's own requirements (verify the exact wording in
the Rules and the ministry's clarifications). The Atlas never implies
convertibility between the two.

## What the Atlas shows

- Programme card "Green Credit Programme" with status
  `requires_assessment`, the reason above, the requirements list
  (registration on the portal, plantation on parcels identified under the
  programme, survival verification per the methodology, understanding that
  Green Credits are not carbon credits), and references to MoEFCC and
  ICFRE.
- The `distinct_from: [in-ccts]` relation, rendered as a visible note.
- Nothing quantitative: the Atlas does not estimate how many Green Credits
  a plantation might earn, because the methodology's counting rules apply
  to programme parcels and are verified by the Administrator, not by a
  model.

## What a person interested in the GCP needs to do

Register on the portal; browse parcels identified by a forest department;
agree to fund the plantation per the department's cost norms; wait for
the Administrator's verification; receive credits. A landowner who wants
trees on **their own** land is better served by state agroforestry
incentives ([INCENTIVES.md](INCENTIVES.md)) and, if a carbon project is
the goal, by the CCTS offset mechanism or a voluntary methodology
([CCTS.md](CCTS.md), [METHODOLOGIES.md](METHODOLOGIES.md)).

## Sources

- MoEFCC — Green Credit Programme (Rules, methodologies, notifications):
  <https://moef.gov.in/>
- ICFRE — programme administrator: <https://icfre.gov.in/>
- Green Credit Programme portal: <https://www.moefcc-gcp.in/> (verify)
- Press Information Bureau releases on the GCP launch (October 2023) and
  the tree-plantation methodology (February 2024): <https://pib.gov.in/>
