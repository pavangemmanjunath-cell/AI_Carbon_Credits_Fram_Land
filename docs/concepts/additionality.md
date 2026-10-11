# Additionality

Additionality asks a counterfactual question: **would this carbon removal
have happened anyway, without the incentive the programme provides?** A
credit is only meaningful if the answer is no. CarbonCreditBuy does not assess
additionality — it cannot, from satellite data and a tree count — and
says so in every screening result.

## Definitions in the main frameworks

- The ICVCM Core Carbon Principles require that "the greenhouse gas
  emission reductions or removals from the mitigation activity shall be
  additional, i.e., they would not have occurred in the absence of the
  incentive created by carbon credit revenues"
  (<https://icvcm.org/core-carbon-principles/>).
- The Verra VCS Program requires projects to demonstrate additionality
  using the methodology's prescribed approach, typically a regulatory
  surplus test (the activity is not required by law), a barrier or
  investment analysis, and a common-practice analysis; some methodologies
  use performance benchmarks or positive lists instead
  (<https://verra.org/programs/verified-carbon-standard/>). The UNFCCC
  CDM "Tool for the demonstration and assessment of additionality" is the
  historical reference for this structure
  (<https://cdm.unfccc.int/methodologies/PAmethodologies/tools/am-tool-01-v7.0.0.pdf>).
- Regulation (EU) 2024/3012 (CRCF), Article 5, requires that an activity
  go beyond Union and national statutory requirements and that the
  incentive effect of certification be needed for the activity to become
  financially viable; certification methodologies may use standardized
  baselines to demonstrate this
  (<https://eur-lex.europa.eu/eli/reg/2024/3012/oj>). Verify the exact
  wording against the current text of the Regulation.
- Under India's CCTS offset mechanism, projects must demonstrate
  additionality per the approved methodology before Carbon Credit
  Certificates are issued; the Green Credit Programme, by contrast, is an
  incentive scheme and does not use carbon-market additionality tests
  ([../regions/IN/CCTS.md](../regions/IN/CCTS.md),
  [../regions/IN/GREEN_CREDIT.md](../regions/IN/GREEN_CREDIT.md)).

## Why it is hard for farms

A mango orchard planted for fruit, a pecan planting for nuts or an olive
grove for oil would, in most cases, have been planted regardless of
carbon finance. That does not make the carbon they store unreal; it makes
it **non-additional** in the crediting sense, which is why orchard
systems are often screened out of afforestation methodologies or credited
only for the increment attributable to a changed practice (higher
density, longer rotation, agroforestry rows added to cropland). The
baseline scenario — what the land would have carried without the project
— is the key input, and establishing it needs land-use history, economic
information and often a comparison with regional practice.

## What CarbonCreditBuy can and cannot do

| Can | Cannot |
|---|---|
| Show land-cover history from ESA WorldCover and a three-year vegetation trend, which are evidence *toward* a baseline | Decide whether the planting is additional |
| List "baseline land-use records" as missing evidence in the readiness score | Supply those records |
| Encode in `config/policies/` that a programme requires an additionality demonstration, and return `requires_assessment` or `requires_methodology_assessment` | Return `eligible` |
| Explain in plain language why a fruit orchard may fail an additionality test | Predict the outcome |

The UI's language reflects this: screening statuses, not eligibility
determinations; "potentially applicable" at most; references to the
programme documents on every card.

## Practical guidance for users

If you are considering a programme, start collecting the documents a
baseline needs now: previous land use (crop records, old imagery, revenue
records), the date and reason for planting, any subsidies received, and
the regulations that apply to your land. A positive-list or standardized
baseline, where a methodology offers one, is the lowest-cost route for
small plots. Advisors and project developers aggregating many farms will
ask for exactly these items.
