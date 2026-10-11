# Carbon credit vs carbon estimate

CarbonCreditBuy produces **estimates**. A **carbon credit** is something
else entirely, and the difference is the single most important idea in
this documentation.

## What a carbon credit is

A carbon credit is a tradable unit, normally representing one tonne of
carbon dioxide equivalent (1 tCO₂e) of emission reductions or removals,
that has been **issued by a registry** after a project went through a
defined process. The Verra VCS Program Definitions describe a Verified
Carbon Unit as a unit issued by the Verra registry after validation of
the project and verification of the monitored outcome by an approved
third party
(<https://verra.org/programs/verified-carbon-standard/>). The Integrity
Council for the Voluntary Carbon Market's Core Carbon Principles require,
among other things, effective governance, tracking in a registry,
transparency, robust independent third-party validation and verification,
additionality, permanence, robust quantification and no double counting
(<https://icvcm.org/core-carbon-principles/>). In India, the Carbon Credit
Trading Scheme defines a Carbon Credit Certificate issued under the
scheme ([../regions/IN/CCTS.md](../regions/IN/CCTS.md)); in the EU, the
CRCF creates certified units only after a certification body has audited
the activity against an adopted methodology
([../regions/EU/PROGRAMS.md](../regions/EU/PROGRAMS.md#the-crcf)).

In every system the unit exists because a sequence happened: a recognized
**methodology** was applied; a **baseline** (what would have happened
anyway) was established; **additionality** was demonstrated; **leakage**
was assessed; **permanence** was addressed with buffers or liability;
monitoring data were collected; an accredited **verifier** checked them;
and a **registry** issued serialized units and retired them when claimed.

## What an estimate is

An estimate is a model's answer to "roughly how much carbon might trees on
this land be accumulating, given what we know?" CarbonCreditBuy computes it from
your plot area, climate zone, species, tree count and age using IPCC Tier
1 defaults and, where measurements exist, allometric equations
([../architecture/carbon-engine.md](../architecture/carbon-engine.md)).
It is returned as a **range** (low, central, high) with a confidence
grade, the parameters used and their verification status, and the
constant `certified: false`.

## Side by side

| | Carbon estimate (this tool) | Carbon credit |
|---|---|---|
| What it is | A modelled scenario | A registry-issued, serialized unit |
| Who produces it | Software applying published defaults | Project developer + verifier + registry |
| Baseline and additionality | Not assessed | Required |
| Leakage, permanence | Not assessed | Required |
| Measurement | User-reported inventory; satellite indices as context | Monitored per methodology, field-verified |
| Uncertainty | Explicit range | Conservative deductions and buffers |
| Can it be sold? | No | Yes, subject to the programme's rules |
| Legal status | Information | Defined by the programme and jurisdiction |

## Why CarbonCreditBuy insists on the distinction

Presenting an estimate as a credit would mislead a farmer about income,
mislead a buyer about a claim, and expose everyone to the double-counting
and greenwashing problems the CCPs and the CRCF were written to prevent.
CarbonCreditBuy therefore never uses the words "credit", "offset" or "issued"
for its own numbers; shows the readiness checklist that names the
evidence a programme would still need; and labels market figures as
scenarios ([esg.md](esg.md)).

## What an estimate is good for

Deciding whether a programme is worth investigating; understanding which
measurements (DBH, height, survival counts, baseline records) would move a
Tier 1 guess toward a defensible figure; comparing species and densities
in the Simulation Lab; and giving a researcher or advisor a transparent
starting point with every parameter's source attached. An estimate is the
beginning of evidence, not its conclusion.

## Further reading

- IPCC 2006 Guidelines, Volume 4, Chapter 4 — the source of the Tier 1
  method: <https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html>
- ICVCM Core Carbon Principles and Assessment Framework:
  <https://icvcm.org/core-carbon-principles/>
- Regulation (EU) 2024/3012 (CRCF), Articles 4–7 (QU.A.L.ITY criteria):
  <https://eur-lex.europa.eu/eli/reg/2024/3012/oj>
- The other concept pages: [additionality](additionality.md),
  [permanence](permanence.md), [leakage](leakage.md), [MRV](mrv.md).
