# Permanence

Carbon stored in trees can return to the atmosphere: a felled orchard, a
fire, a drought, a pest outbreak or a change of owner's plans reverses the
removal. **Permanence** (sometimes "durability") is the set of rules by
which programmes handle that **reversal risk**. CarbonCreditBuy models no
losses and makes no permanence commitment on anyone's behalf; this page
explains what the programmes expect so that the readiness checklist makes
sense.

## How frameworks treat it

- **IPCC.** National inventories do not "guarantee" permanence; they
  report gains and losses each year, including disturbances, under the
  gain-loss or stock-difference methods (2006 Guidelines, Volume 4,
  Chapter 2 and Chapter 4,
  <https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html>). A
  reversal shows up as an emission in a later year.
- **Verra VCS.** Agriculture, forestry and other land use (AFOLU) projects
  assess non-permanence risk with the AFOLU Non-Permanence Risk Tool and
  deposit a share of their credits into a pooled buffer account that is
  drawn on if a reversal occurs; projects also commit to a minimum
  project longevity and must monitor and report reversals
  (<https://verra.org/programs/verified-carbon-standard/>). The specific
  buffer percentages and longevity requirements are version-dependent;
  verify against the current VCS Standard and tool.
- **ICVCM Core Carbon Principles.** The permanence principle requires that
  removals be permanent or, where there is a risk of reversal, that
  measures be in place to address the risk and compensate for reversals
  (<https://icvcm.org/core-carbon-principles/>).
- **EU CRCF.** Regulation (EU) 2024/3012, Article 6 ("long-term storage"),
  distinguishes *permanent carbon removals* (storage for several
  centuries), *carbon farming* and *carbon storage in products*. For
  carbon farming, operators must monitor for a defined period and are
  liable for reversals through mechanisms set in the certification
  methodologies (such as buffers, discounting or insurance); the
  Regulation specifies a minimum monitoring period for carbon farming
  activities. Verify the current article text and the delegated acts for
  the applicable periods
  (<https://eur-lex.europa.eu/eli/reg/2024/3012/oj>).
- **India.** The CCTS offset mechanism's detailed procedures and
  methodologies set the permanence and monitoring requirements for
  forestry activities; the Green Credit Programme's tree-plantation
  methodology ties credits to tree survival verified over time
  ([../regions/IN/CCTS.md](../regions/IN/CCTS.md),
  [../regions/IN/GREEN_CREDIT.md](../regions/IN/GREEN_CREDIT.md)). Verify
  against the current notifications.

## What permanence means for a farm

A permanence commitment is a **long-term land-use commitment**: keeping
the trees, replacing losses, allowing monitoring visits and reporting
disturbances for decades. For fruit and nut orchards the economic life of
the trees (often 25–50 years) may be shorter than the commitment some
methodologies require, and orchard renewal is itself a reversal event.
This is one reason why advisors recommend that smallholders look first at
incentive programmes (state agroforestry schemes, NRCS practices, CAP
eco-schemes) whose obligations are shorter and better matched to farm
realities ([../regions/IN/INCENTIVES.md](../regions/IN/INCENTIVES.md),
[../regions/US/PROGRAMS.md](../regions/US/PROGRAMS.md#usda-nrcs-conservation-programs-eqip-and-csp),
[../regions/EU/PROGRAMS.md](../regions/EU/PROGRAMS.md#cap-eco-schemes-and-agri-environment-climate-measures)).

## How CarbonCreditBuy handles it

- The carbon engine's stock is a running sum of annual gains with **no
  loss term**; the result's `notes` say so. A 30-year series should be
  read as "if the stand grows as modelled and nothing is lost".
- Survival rate is the only mortality-like input, and it is a user
  assumption.
- The readiness score lists "farm management history" because programmes
  will ask for it when assessing reversal risk.
- Policy screening returns `requires_certification` or
  `requires_methodology_assessment` for every crediting pathway partly
  *because* permanence is a commitment only the landholder can make.

Users planning to pursue a programme should factor in the length of the
commitment, the cost of monitoring, the treatment of orchard renewal, and
who bears the liability if trees are lost.
