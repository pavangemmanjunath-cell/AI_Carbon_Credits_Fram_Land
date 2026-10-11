# Adding a region

A region is configuration, not code ([CLAUDE.md](../../CLAUDE.md) principle 7 and
[ADR 0004](../architecture/adr/0004-config-driven-regions-and-policies.md)). The primary key is an ISO
3166-1 alpha-2 code, and a region can be one country (`IN`, `US`) or a bloc (`EU`) whose member states
resolve to it. This page lists everything a complete region contains, in the order you would do it,
including the few places where the code or a test still names the regions.

Read the existing regions first: [`config/regions/IN.yaml`](../../config/regions/IN.yaml),
[`US.yaml`](../../config/regions/US.yaml), [`EU.yaml`](../../config/regions/EU.yaml) and the matching
files in [`config/policies/`](../../config/policies/). The documentation pages in
[`docs/regions/`](../regions/IN/README.md) show the depth to aim for.

## Before you start

Open a "Region request" issue (the form is
[`region_request.yml`](../../.github/ISSUE_TEMPLATE/region_request.yml)). To correct or add a rule in a
region that already exists, use "Policy rule proposal"
([`region_rule.yml`](../../.github/ISSUE_TEMPLATE/region_rule.yml)) and read step 2 below. A region is
only worth adding if you can say, with official sources:

- which programs exist for tree planting, agroforestry or soil carbon, who administers each and where
  the official page is;
- for each program, whether it issues a **credit** (a tradable unit that needs a methodology, baseline
  and verification) or is an **incentive** (a payment or subsidy). CarbonCreditBuy never lets the two blur
  ([carbon credit vs estimate](../concepts/carbon-credit-vs-estimate.md));
- where an indicative price range could come from;
- a domain reviewer for the region ([GOVERNANCE.md](../../GOVERNANCE.md)). Policy rules and parameters
  are not merged without one.

If you cannot confirm a fact, write `TODO(verify)` and name the document that would settle it. Never fill
a gap from memory (CLAUDE.md principle 13), and never invent a program: a program that you cannot
link to an official page does not go in.

## 1. The region file

Create `config/regions/<ID>.yaml`. The file name must be `<ID>.yaml` and `id` must equal the file stem.
Start from the closest existing region. Values below are placeholders in angle brackets.

```yaml
id: <ID>                      # ISO 3166-1 alpha-2, upper case (or a bloc id such as EU)
name: <Country name>
calling_code: "<+nn>"         # UX alias only, never a key; null for a bloc
currency: <ISO 4217 code>
currency_symbol: "<symbol>"
locale: <BCP 47 tag>          # number and date formatting in the web app
units:
  area: hectare               # hectare or acre
  area_secondary: acre
languages: [en]               # languages the UI offers for this region
default_center: {lat: <deg>, lon: <deg>}
default_zoom: <number>
bbox: [<min_lon>, <min_lat>, <max_lon>, <max_lat>]
admin_levels: [<state>, <district>]
climate:
  default_zone: <zone id>     # used when a simulation has no coordinates
  default_zone_note: "<how the default was chosen>"
data_sources: {}              # descriptive: which dataset serves each need
programmes:
  - id: <id>-<short-name>     # must match the id in config/policies/<ID>.yaml
    name: <program name>
    authority: <administering body>
    kind: <see list below>
    url: <official page>
    policy_file: ../policies/<ID>.yaml
market_scenarios: <ID>
other_income_sources:
  - {id: <id>, label: <label>, source: <where the figure would come from>}
# Blocs only:
# member_states: [<ISO>, ...] # each resolves to this region; keeps its own code for data lookups
# calling_code_aliases: {"<+nn>": <ISO>}
```

What the code actually reads:

| Key | Read by | Notes |
| --- | --- | --- |
| `id` | API, policy engine, demo twins | Required; a missing `id` stops start-up |
| `name`, `calling_code`, `currency`, `currency_symbol`, `units`, `languages`, `default_center`, `default_zoom`, `bbox`, `member_states`, `other_income_sources` | `GET /api/v1/regions` | The web app falls back to its own copy (step 7) |
| `climate.default_zone` | API (`RegionConfig.default_zone`) | Must be one of the 11 zones in `above_ground_biomass_growth.by_climate_zone` in `config/methodologies/ipcc-2006-tier1.yaml`. If the key is missing the code silently uses `tropical_dry` |
| `bbox` | `region_for_point`, demo twins | Guesses the region from a point when no country is given. The first match in alphabetical file order wins, so avoid overlapping boxes |
| `programmes[].url` | policy engine (`programme_url`) | Falls back to the first reference URL in the policy file |
| `locale` | web app (`lib/format.ts`) | From the web copy of the region file |
| `member_states` | API and policy engine | `DE` resolves to `EU`, and the plot keeps `country: DE` |
| `admin_levels`, `data_sources`, `market_scenarios`, `policy_file`, `default_zone_note` | nothing | Descriptive. Keep them accurate anyway: reviewers and docs rely on them |

Program `kind` values used so far: `certification_framework`, `compliance_market`,
`government_programme`, `incentive_programme`, `methodology_tool`, `voluntary_standard`. Reuse one of
them; add a new value only with a note in your pull request.

`other_income_sources` lists what a farmer might earn besides carbon (fruit, timber, incentives). The
platform never fills the numbers: the "Other farm income" card stays empty until the farmer enters them,
and it is never added to the other two values.

## 2. The policy file

Create `config/policies/<ID>.yaml`. The loader opens that path for region `<ID>`, so the name must match.

```yaml
country: <ID>
disclaimer: Initial screening only — not an eligibility determination. <region-specific sentence>
programmes:
  - id: <id>-<short-name>
    name: <program name>
    authority: <body>
    kind: <kind>
    distinct_from: [<other program id>]   # optional: two mechanisms people confuse
    rules:
      - when: {activity: [tree_plantation, agroforestry]}
        status: requires_methodology_assessment
        reason: <what the program requires, citing the instrument>
      - default: unknown
    requirements:
      - <what a project would need, one plain-language item per line>
    references:
      - {title: <document title>, url: <primary source URL>}
```

### How rules are evaluated

`packages/policy-engine` reads the `rules` of each program in order:

1. The **first rule whose `when` matches wins**. A rule matches when every condition it names holds.
2. If none matches, the `default` rule applies. With no default the status is `unknown`.
3. Supported `when` keys: `activity` (string or list), `land_type` (string or list), `min_area` and
   `max_area` (hectares, inclusive). **Any other key is silently ignored**, which makes the rule match
   more than you meant, so do not invent keys.
4. The activity is one of `tree_plantation`, `agroforestry`, `soil_carbon`, `cropland_practice`,
   `grazing`.
5. The API passes the activity and the plot area, but **not** `land_type`, so a rule that sets
   `land_type` cannot match through the API.

### Choosing a status

| Status | Use it when |
| --- | --- |
| `potentially_applicable` | An incentive or cross-checking tool exists for this activity in this region and the person should look into it. Not for a scheme that issues credits |
| `requires_assessment` | The program is relevant, but whether this kind of land or owner qualifies has to be confirmed with the administrator |
| `requires_methodology_assessment` | A credit scheme: an approved methodology, baseline, additionality, monitoring and third-party verification are needed first |
| `requires_certification` | Certification by a recognized body is required, as under the EU CRCF |
| `not_applicable` | The program does not cover this activity |
| `unknown` | CarbonCreditBuy has not assessed the combination. This is the honest default for credit schemes |

Writing rules that hold up in review:

- State what is **required**, never that someone is eligible. The screening is not an eligibility
  determination, and the disclaimer says so.
- Every program needs `references` with real URLs. The data-quality tests fail on a program without
  them. Cite the notification or regulation, not a news article, unless no primary source is reachable;
  say so in the reason.
- Use `distinct_from` for mechanisms that are routinely confused (India's Green Credits and carbon
  credits). The engine adds a visible "separate mechanism" note.
- The last `default` must not be `potentially_applicable`. Use `not_applicable` for incentive programs
  and `unknown` for credit or certification schemes.
- Date-stamp anything that changes by notification ("adopted in March 2026; not yet in force"), and put
  a `TODO(verify)` in the reason where you could not confirm it.
- Do not copy another region's reason text. Each reason must be true for this region.

## 3. Price scenarios

In `config/market/carbon-price-scenarios.yaml`, add `scenarios.<ID>` with `currency` (it must equal the
region's currency), a `note`, `verification_status: pending`, and `low`, `reference` and `high` entries
holding `price_per_tco2e` and a `label`. Prices must be positive and ascending. Update `as_of` and
`references` if you used a source that is not listed. These are illustrative ranges to review each
release, never quotes.

Do not skip this step. When a region has no entry, `RegionConfig.market_scenarios` silently returns the
**first** scenario in the file, so the user would see another region's prices in another currency. The
data-quality test below guards against it.

## 4. Species

Add the region id to the `regions` list of each species in `config/species/species.yaml` that grows
there, and add new species following [species and parameters](adding-a-species-or-parameter.md).
`GET /species?country=<ISO>` resolves the country to a region and filters on that list, so a member
state sees the bloc's species. Each species lists `suitable_climate_zones`, which must be among the 11
zones of the Tier 1 tables. Most of those table values are still `pending` or `assumption`, so check the
status of the zone your region defaults to before promising anything to users.

## 5. Methodology registry

If the region has a government methodology or standard the platform may *reference*, add an entry to
`config/methodologies/registry.yaml` with `regions: [<ID>]`, a `status` and the official URL. The
registry only lists what exists; it never means CarbonCreditBuy applies it.

## 6. Tree-age rules and imagery

Two optional files make a region more useful, and both are configuration:

- **Tree-age rules.** If programs or tree-protection laws in the region treat trees differently by
  age, add them to `config/tree-age/rules.yaml` with `scope: <ID>`
  ([adding a tree-age rule](adding-a-tree-age-rule.md)). A subdivision a rule names (a state or
  province) must be listed in `config/tree-age/subdivisions.yaml`. The list of allowed scopes is the
  constant `SCOPES` in `packages/policy-engine/policy_engine/tree_age.py`, so a brand-new region id also
  needs that one-line code change and a test.
- **Imagery.** In `config/imagery/providers.yaml`, add a provider whose license, key requirement and
  analysis terms you have read, and map the country to it in `default_by_country` only if it is
  open, keyless and allows analysis. A region with no such provider uses the global default. Say so in
  the region's data-sources page rather than adding a provider whose terms are unclear.

## 7. Web app

The browser keeps a static copy of the region data for offline use:

- Update `apps/web/src/config/regions.json` by hand to match your YAML (its `_comment` says so).
  `GET /regions` stays authoritative at run time.
- `regionIdFor` in `apps/web/src/config/regions.ts` returns `IN` for a code it does not know, so a new
  region only works there once it is in `regions.json`. Bloc members come from the `eu_member_states`
  list in the same file; another bloc needs a code change.
- A new interface language needs `apps/web/src/i18n/<code>.json` and an entry in `LANGUAGES` and
  `resources` in `apps/web/src/i18n/index.ts`. Add keys to `en.json` first. Missing keys fall back to
  English. English, German, Spanish, French, Hindi and Kannada exist today; translations are a good first
  contribution ([starter issues](../community/starter-issues.md)).
- If API responses changed, regenerate the offline fixtures: `python3 scripts/make_sample_responses.py`,
  then `npm run fixtures:demo` inside `apps/web`.

## 8. Code that still lists regions

These are the exceptions to "no `if country == ...` outside `config/`". Fix them in your pull request or
open an issue for each:

| File | What to do |
| --- | --- |
| `apps/api/app/services/simulate.py` | `PROGRAMME_SUMMARY` has one line per region (empty if missing), and the "same plantation under other rules" comparison loops over `("IN", "US", "EU")` only |
| `integrations/carboncreditbuy_integrations/demo_support.py` | Demo climate and place per region. Unknown regions get generic values, so demo mode still works. Add yours for a nicer demo |
| `integrations/carboncreditbuy_integrations/nominatim/adapter.py` and `soilgrids/adapter.py` | Demo-twin place list and demo soil values; optional |
| `packages/policy-engine/policy_engine/tree_age.py` | `SCOPES` lists `GLOBAL`, `IN`, `US` and `EU`; see step 6 |
| `apps/api/app/services/{plots,carbon,analysis,reports}.py`, `api/v1/routers/plots.py` | A stored plot whose country does not resolve is treated as `IN` |

## 9. Tests

Run these before you push, and update the lines that name the current regions:

```bash
python3 -m pytest packages/policy-engine tests/data-quality apps/api -q
```

| Test | Change needed |
| --- | --- |
| `tests/data-quality/test_parameters.py::test_regions_and_policies_align` | Add `<ID>` to the expected set. The test also checks that every region has a policy file and a price scenario in the same currency with ascending, positive prices |
| `tests/data-quality/test_parameters.py::test_policy_rules_reference_documents` | Runs on your policy file: the disclaimer must say "screening", every program needs references with URLs, and the final default must not be `potentially_applicable` |
| `tests/data-quality/test_tree_age_rules.py` | Runs on your tree-age rules and on `subdivisions.yaml`. It requires at least one rule for every scope in `SCOPES`, so a new scope needs its first rule in the same pull request |
| `packages/policy-engine/tests/test_policy_engine.py` | Add a parametrized test like `test_us_every_activity`: one row per activity with the expected status of each program. `test_member_states_resolve_to_eu` uses `BR` as an unsupported country; pick another code if you add `BR` |
| `apps/api/tests/test_api_demo.py` | The regions test asserts the set `{"IN", "US", "EU"}`, and the per-country simulation test has one row per region. Add yours |

Then check the behavior end to end:

```python
from policy_engine import PolicyEngine

screening = PolicyEngine().screen("<ID>", "tree_plantation")
for p in screening.programmes:
    print(p.id, p.status)
```

```bash
make api &
curl -s http://localhost:8000/api/v1/regions | python3 -m json.tool | head -40
curl -s -X POST http://localhost:8000/api/v1/simulate -H 'Content-Type: application/json' \
  -d '{"country": "<ID>", "species_id": "<species id>", "tree_count": 100, "planting_year": 2024}'
```

Simulation needs a species that is listed for your region and a climate zone it supports.

## 10. Documentation

Create `docs/regions/<ID>/` with the same pages as the other regions:

- `README.md`: settings, data sources, programs screened, what users should expect
  ([India](../regions/IN/README.md), [United States](../regions/US/README.md) and
  [European Union](../regions/EU/README.md) are the models);
- a programs page (the existing regions call it `PROGRAMS.md`; use the same name so the pages stay
  parallel), `DATA_SOURCES.md` and `METHODOLOGIES.md`, or one page per program for a region with
  several large schemes;
- a link from [`docs/README.md`](../README.md).

The rules for these pages are the rules for the policy file: every program in the page is in
`config/policies/<ID>.yaml`, every statement about a law, program or price has a link to the primary
source, and what you could not confirm is marked `TODO(verify)` or "not verified". Describe what a
program requires, not what the reader is entitled to, and keep credits and incentives apart.

Every new external dataset also needs a row in
[`docs/licensing/DATA_LICENSES.md`](../licensing/DATA_LICENSES.md), a row in
[`docs/data-sources/FREE_APIS.md`](../data-sources/FREE_APIS.md) and an adapter
([adding an integration](adding-an-integration.md)).

## 11. Repository metadata

So that the new region is routed to the right people:

- add a `region/<ID>` label to [`.github/labels.yml`](../../.github/labels.yml), and a matching block
  to [`.github/labeler.yml`](../../.github/labeler.yml) for `config/regions/<ID>.yaml`,
  `config/policies/<ID>.yaml` and `docs/regions/<ID>/**`;
- add the three patterns to [`.github/CODEOWNERS`](../../.github/CODEOWNERS) with the region's
  reviewers;
- add the region to the dropdowns in `region_rule.yml` and `data_source.yml` if you want it listed.

## Checklist for the pull request

- [ ] `config/regions/<ID>.yaml`, `config/policies/<ID>.yaml` and the price scenario
- [ ] Every program has primary-source references; unconfirmed facts say `TODO(verify)`; no program
      is included without an official page
- [ ] Credits and incentives are not mixed; `distinct_from` is set where needed
- [ ] Species and registry entries updated; tree-age rules and imagery considered
- [ ] Web copy (`regions.json`) and languages updated
- [ ] Tests updated and passing (`make test`)
- [ ] `docs/regions/<ID>/` written; licensing rows added for new data sources
- [ ] Label, labeler and code-owner entries added
- [ ] A domain reviewer for the region has approved the policy and price files

Next: [species and parameters](adding-a-species-or-parameter.md) or
[adding an integration](adding-an-integration.md).
