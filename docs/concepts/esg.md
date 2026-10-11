# ESG and the three separated values

Early sketches of tools like this one tend to end in a single headline:
"your ESG amount is ₹ 48,000". CarbonCreditBuy does not do that, for a reason
that is conceptual before it is stylistic: **"ESG amount" is not a unit.**

## What ESG means

ESG stands for environmental, social and governance: a family of criteria
and disclosure frameworks that investors, lenders and regulators use to
assess organizations. Frameworks such as the IFRS Sustainability
Disclosure Standards (IFRS S1/S2,
<https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/>),
the EU's Corporate Sustainability Reporting Directive and its European
Sustainability Reporting Standards
(<https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en>),
and the GHG Protocol
(<https://ghgprotocol.org/>) define *what to disclose and how to measure
it*, in physical units (tCO₂e, hectares, cubic metres) and in money where
money is involved. None of them defines an "ESG amount" that a farm could
earn. A tonne of carbon dioxide removed is an environmental quantity; what
someone might pay for a certified unit representing it is a market price;
what the farm earns from fruit is farm income. Adding them, or giving the
sum a name, mixes a physical measure, a hypothetical price and an
unrelated cash flow into a number that means nothing and can mislead
everyone who reads it.

## The three separated values

Everywhere CarbonCreditBuy presents results — the results view, the Simulation
Lab, reports and the `/market-scenario` response — it shows three values
separately, never summed:

| Value | Unit | What it is | Where it comes from |
|---|---|---|---|
| **Environmental benefit** | tCO₂e/yr, as a range | Estimated annual carbon removal by the trees | The carbon engine, with confidence and provenance ([../architecture/carbon-engine.md](../architecture/carbon-engine.md)) |
| **Indicative carbon value** | currency per year, per scenario | *If* a certified unit existed for each tonne and *if* it sold at a scenario price, the annual value | `config/market/carbon-price-scenarios.yaml`: low, reference and high prices with an `as_of` year and references; never a quote |
| **Other farm income** | currency per year | Fruit, nuts, timber, intercrops, conservation or scheme payments | District/county statistics and the farmer's own records; often `null` until supplied |

The terminology rule in [CLAUDE.md](../../CLAUDE.md) follows from this:
say "estimated annual carbon removal (tCO₂e/yr)", never "ESG amount", and
never sum the three values.

## Why separation protects the user

- **Different certainty.** The removal estimate has a modelled range; the
  carbon value depends on a market that may not exist for the farm's
  jurisdiction (India's CCTS offset market and the EU's CRCF units had no
  liquid price for agroforestry removals at the time of writing, as the
  market configuration notes); farm income is comparatively knowable.
- **Different conditions.** Carbon value requires certification,
  additionality, permanence commitments and a buyer
  ([carbon-credit-vs-estimate.md](carbon-credit-vs-estimate.md)); fruit
  income requires a harvest. Summing them hides that one is conditional on
  a long process and the other is not.
- **Different audiences.** An ESG analyst wants tCO₂e with methodology and
  uncertainty; a farmer wants to know what changes on the farm; a lender
  wants cash flows. Each gets a value in its own unit.
- **Avoiding misleading claims.** A "total benefit" figure invites the
  reading that the farm *will receive* that amount, which is the claim
  that consumer-protection and green-claims rules target (for example
  the EU Directive 2024/825 on empowering consumers for the green
  transition,
  <https://eur-lex.europa.eu/eli/dir/2024/825/oj>).

## How this appears in the interface

Three cards or table rows, each with its unit, its disclaimer and its
source. The carbon value card always carries "Market-value scenario — not
guaranteed revenue" and shows all three price scenarios rather than one.
The other-income row says where the figure comes from and is empty rather
than invented when there are no statistics. Reports reproduce the same
structure ([../user-guide/results-explained.md](../user-guide/results-explained.md)).
