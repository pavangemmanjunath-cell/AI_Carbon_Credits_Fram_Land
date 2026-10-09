# Adding a tree-age rule

A tree-age rule records one real program or law that treats trees differently by age, size or
setting: a carbon standard that credits only new planting, a payment for a very old tree, a
felling-permission law, a replanting duty. All rules live in one data file,
[`config/tree-age/rules.yaml`](../../config/tree-age/rules.yaml). The policy engine reads and matches them
([`policy_engine/tree_age.py`](../../packages/policy-engine/policy_engine/tree_age.py)), the API serves them
(`GET /api/v1/tree-age/rules` and `POST /api/v1/tree-age/assess`), and the "Tree age" page of the web app and the
policy agent of the agent team show what comes back. No rule is ever written as an `if` in code
([CLAUDE.md](../../CLAUDE.md) principles 2, 3 and 13), so adding a rule is a data change plus tests. It needs no code
change as long as you use the vocabulary the file already has.

The research behind the file is in
[`docs/research/tree-age-carbon-rules.md`](../research/tree-age-carbon-rules.md). Read its "Key finding" and
"How the app uses this" sections before you start. The short version: carbon standards reward new, additional removals,
not the carbon that old trees already hold, so most rules here say "not eligible", "protected" or "conditional", and
none of them turns a tree into a credit.

## Is it a tree-age rule?

| You have | It belongs in |
| --- | --- |
| A law or program whose outcome depends on tree age, trunk size, or whether the trees already stand | `config/tree-age/rules.yaml` (this page) |
| A program a farm might apply to, screened by land use, size or practice rather than tree age | The region's policy file `config/policies/<ISO>.yaml`: [adding a region, step 2](adding-a-region.md#2-the-policy-file) |
| A growth, biomass or carbon-fraction number | A parameter with a source and `verification_status`: [adding a species or parameter](adding-a-species-or-parameter.md) |
| A rule you have seen only in the press, or whose text you could not open | This file, as `pending` with `notes` that say what is missing. The file already does this for a few rules. Never mark it `verified` |
| A rule you cannot source at all | Nowhere. The Atlas never invents policy eligibility ([CLAUDE.md](../../CLAUDE.md) principle 13). Open a "Data source proposal" issue instead |

## The fields

The file has five top-level fields: `version`, `updated`, `disclaimer`, `age_classes` and `rules`. You will touch
`rules`, and `updated` (and usually `version`). Every rule has these 17 fields, plus an optional `notes`. The engine
lists every problem at once when a rule breaks the schema, so run it often.

| Field | What to write | Allowed values |
| --- | --- | --- |
| `id` | A unique lowercase slug that starts with the scope and place: `in-ka-preservation-of-trees-act` | `a-z`, `0-9` and hyphens. An id that starts `in-gcp` must not be a carbon-credit rule, and one that starts `in-ccts` must be (the two Indian mechanisms stay separate) |
| `scope` | Whose users see it | `GLOBAL`, `IN`, `US`, `EU` |
| `country` | ISO 3166-1 alpha-2 code, or `null` | `GLOBAL`: `null`. `IN` and `US`: the same code or `null`. `EU`: `null` for every member state, or one member state such as `DE` |
| `subdivision` | ISO 3166-2 code, or `null` for a national rule | Must belong to its country (`IN-KA` for `IN`), and must be listed in [`subdivisions.yaml`](../../config/tree-age/subdivisions.yaml) |
| `locality` | A city or town name, or `null` | Needs a `subdivision`. Only for municipal examples |
| `name` | The official title, with its year or version | Non-empty text |
| `authority` | Who issues or administers it | Non-empty text |
| `category` | What kind of rule it is | `carbon-credit-eligibility`, `incentive-payment`, `tree-protection`, `compensatory-planting`, `methodology-note` |
| `applies_to` | What the rule regulates. Exactly four keys | `min_age_years` and `max_age_years`: whole years or `null` (no bound). `trees`: `any`, `new-planting`, `existing`. `setting`: `any`, `non-forest`, `forest`, `urban` |
| `outcome_for_existing_trees` | What the rule means for trees that already stand | `not-eligible`, `eligible`, `conditional`, `protected`, `payment`, `not-applicable` |
| `summary` | One plain sentence a farmer can read | Non-empty text |
| `details` | The conditions, with section or article numbers | Non-empty text |
| `amount` | A payment or penalty the source states, else `null` | `{value, currency, unit, as_of}`: `value` is a number of 0 or more, `as_of` is `2026-07` or `2026-07-15` |
| `status` | Where the rule stands today | `in-force`, `proposed`, `superseded`, `unknown` |
| `is_example` | `true` only for a municipal rule that stands for "check your own local ordinance" | `true` or `false` |
| `sources` | At least one | Each has `title`, `publisher`, an `https://` `url` and an `accessed` date like `2026-10-05` |
| `verification_status` | Did you open the source and does it state the condition? | `verified`, `pending` |
| `notes` | What is still unconfirmed, and caveats | Text or `null`. Required while a rule is `pending` |

### Choosing the values

- **`outcome_for_existing_trees`** is the headline a landowner with standing trees sees.
  `not-eligible`: the rule credits only new planting, so trees that already stand earn nothing under it.
  `conditional`: a route exists under stated conditions (for example avoided loss in an at-risk urban stand).
  `protected`: the rule limits felling, and it is allowed only for a `tree-protection` rule.
  `payment`: the rule pays the custodian, and it is allowed only for an `incentive-payment` rule.
  `eligible`: only when the rule is `verified` and `in-force`, and rarely even then. No rule can make a tree eligible
  for a credit, and the engine's credit outlook never says `eligible`; only the program itself can.
- **`applies_to.trees`** says what the rule is written for. It changes the answer only when the user enters age 0
  ("I am planning new trees"): a rule for `existing` trees then reads `not-applicable`, and any other rule reads
  `conditional`.
- **`applies_to.setting`**: a farm tree is `non-forest`, and `non-forest` also matches urban trees. `any` never
  excludes a rule.
- **Age bounds** are a hard filter. Most laws turn on trunk size or species, not age, so most rules have `null` for
  both bounds, and the size test belongs in `summary` and `details`. Do not convert a size threshold into an age.
- **`amount`** is filled only when a source states it, with its unit and an `as_of` date. A payment such as the
  Haryana pension is other farm income: the app shows it beside the indicative carbon value and never adds the two.

## A template

Copy the shape of a real rule rather than writing one from scratch. This is a template, not a rule: every value is a
placeholder, and the file already contains real rules to read.
[`in-ka-preservation-of-trees-act`](../../config/tree-age/rules.yaml) is a good one to start with.

```yaml
  - id: xx-place-short-name            # scope first; unique in the file
    scope: IN                          # GLOBAL | IN | US | EU
    country: IN                        # null for GLOBAL
    subdivision: IN-KA                 # null for a national rule; must be in subdivisions.yaml
    locality: null                     # a city name only for a municipal example
    name: "Official title of the law or program, with its year or version"
    authority: "The body that issues or administers it"
    category: tree-protection
    applies_to: {min_age_years: null, max_age_years: null, trees: existing, setting: any}
    outcome_for_existing_trees: protected
    summary: >-
      One plain sentence: what the rule does to trees like these, and which test it uses (age, size, species).
    details: >-
      The conditions, with section numbers. Quote a sentence at most and paraphrase the rest. Say what the text
      does not state.
    amount: null                       # or {value: 0, currency: "INR", unit: "per year", as_of: "2026-07"}
    status: in-force
    is_example: false
    sources:
      - {title: "Title of the page or document", publisher: "Who published it", url: "https://example.org/document", accessed: "2026-10-05"}
    verification_status: pending       # verified only when you opened the source and it states the condition
    notes: >-
      Required while pending: say exactly what is not yet confirmed and where the confirmation would come from.
```

## Steps

1. **Open the primary source.** The official text (a gazette, a statute site, a program's own document) beats a
   summary. Note the title, publisher, URL and the date you opened it. A rule is `verified` only if you read the text
   and it states the condition. If you could read only a news report, a summary or a search snippet, the rule is
   `pending`.
2. **Place it.** Choose `scope`, `country`, `subdivision` and `locality`. If the subdivision is not in
   [`subdivisions.yaml`](../../config/tree-age/subdivisions.yaml), add it with its exact ISO 3166-2 code (check the
   ISO Online Browsing Platform; Odisha is `IN-OD`, not `IN-OR`). A new country needs its own block there. A rule for
   one EU member state keeps `scope: EU` and names the country; the engine then shows it only to users in that
   country. The scopes themselves are a constant in the engine, so a new region is a code change
   ([adding a region, step 6](adding-a-region.md#6-tree-age-rules-and-imagery)).
3. **Say what it regulates.** Set `applies_to`, `category` and `outcome_for_existing_trees` using the table above.
4. **Write `summary` and `details`.** Use plain American English. Say what the rule does and what it does not do. Quote
   sparingly: a program's document is its owner's text, and this file is not a mirror of it. Date-stamp anything that
   changes by notification.
5. **Add `amount` only if the source states it.** Otherwise `null`.
6. **Set `status`.** A bill, a draft or an adopted act that is not yet in force is `proposed`. The web app labels it.
7. **Set `verification_status`.** If it is `pending`, write `notes` that say what is missing: which document you could
   not open, which number is from the press. The data-quality test fails a pending rule without notes.
8. **Bump the header.** Set `updated` to today. The test requires every `accessed` date to be on or before it. Bump
   `version` too. The file does not prescribe a scheme; the API reports both values in the provenance of every
   assessment, so a changed rule should change the version.
9. **Run the checks** (next section) and read your rule the way the page will show it.
10. **Update the prose.** Add a row to the "Rule index" table and the totals in
    [`docs/research/tree-age-carbon-rules.md`](../research/tree-age-carbon-rules.md), and add the source to its
    source list. If the rule belongs to a program that a region page covers, link it from that region's
    `PROGRAMS.md` or `METHODOLOGIES.md` under [`docs/regions/`](../regions/). Describe it in your pull request:
    why, source, licensing impact (you quote public text), privacy impact (none: rules hold no personal data) and tests.

## Check it locally

```bash
# 1. Schema and vocabulary. Raises one error that lists every problem at once.
python3 -c "from pathlib import Path; from policy_engine.tree_age import load_rules; load_rules(Path('config')); print('ok')"

# 2. What a user in your place sees: IN, state IN-KA, farm trees, 40 years old.
python3 - <<'EOF'
from pathlib import Path
from policy_engine.tree_age import evaluate, load_rules

doc = load_rules(Path("config"))
for rule in evaluate(doc, "IN", "IN", "IN-KA", "farm", 40):
    print(rule["id"], rule["applies"], rule["outcome_for_you"], "|", rule["why"])
EOF

# 3. The tests that guard the file, the engine and the API.
python3 -m pytest tests/data-quality/test_tree_age_rules.py packages/policy-engine apps/api/tests/test_tree_age_api.py -q
```

`evaluate` takes the country, the region (`IN`, `US` or `EU`; a German user is `DE` in `EU`), the subdivision, the
setting (`farm`, `urban`, `forest` or `any`) and the age. With the API running (`make api`), the same data is at
`GET /api/v1/tree-age/rules?country=IN&subdivision=IN-KA`, and `/docs` on the API shows the assessment request.

Geography is a hard filter: rules of other regions are not returned. Everything else comes back with `applies`,
`why` and `outcome_for_you`, so a user can see what would apply elsewhere. Applicable rules are listed first, then by
category, then by id.

### What the tests check

| Test | It fails when |
| --- | --- |
| `test_the_engine_accepts_the_shipped_files` | Any schema problem: a missing field, an unknown field, a bad value, a duplicate id, a subdivision that is not listed |
| `test_rule_has_a_source_with_an_https_link_and_an_access_date` | A rule has no source, a link is not `https://`, or an `accessed` date is later than the file's `updated` |
| `test_links_are_https_only` | The text `http://` appears anywhere in `rules.yaml`, comments included |
| `test_a_pending_rule_says_what_is_missing` | A `pending` rule has empty `notes` |
| `test_no_rule_promises_eligibility_without_verification` | `eligible` on a rule that is not both `verified` and `in-force` |
| `test_outcomes_match_their_category` | `protected` outside `tree-protection`, or `payment` outside `incentive-payment` |
| `test_municipal_examples_name_their_place` | An example without a `locality` and a `subdivision`, or a `locality` without a `subdivision` |
| `test_geography_is_consistent_and_listed` | A global rule that names a place, a subdivision outside its country, or one missing from `subdivisions.yaml` |
| `test_gcp_and_ccts_stay_separate_mechanisms` | An `in-gcp` rule in the credit category, or an `in-ccts` rule outside it |
| `test_every_scope_and_category_the_app_shows_has_rules` | Removing the last rule of a scope or a category |
| `test_every_rule_evaluates_to_a_sentence_and_an_outcome` | Any rule that cannot be evaluated for IN, US, DE or FR at any age or setting |

If your rule adds behavior the engine cannot express yet, do not bend the data to fit it. Open an issue, then change the
engine with its own tests in `packages/policy-engine/tests/test_tree_age_rules_engine.py`.

## Pending rules and production

A `pending` rule ships in development, flagged "not yet confirmed from a primary source". A production deployment
(`ATLAS_ENV=production`, or `ATLAS_ALLOW_PENDING_PARAMETERS=false`) withholds it, the way the carbon engine refuses
pending parameters ([CLAUDE.md](../../CLAUDE.md) principle 10). The endpoints leave the rule out of `rules` and name
it in `withheld_rule_ids`, so a client can say that something exists but is not confirmed.

Unlike a pending carbon parameter, a pending rule does not make the production gate fail. The gate holds, and the test
prints which rules are withheld:

```bash
ATLAS_ENV=production python3 -m pytest tests/data-quality/test_tree_age_rules.py -k production -q
```

Before a release, someone should try to confirm each withheld rule. To promote one: open the primary source, check
every condition in `summary`, `details` and `amount`, fix whatever differs, set `verification_status: verified`, trim
`notes` to the caveats that remain, and bump `updated`. Use the "Verify a parameter or rule" issue form to track it
([adding a species or parameter](adding-a-species-or-parameter.md#verifying-a-pending-parameter)).

## Changing the vocabulary

A new `category`, `outcome`, `status`, `setting` or scope is not a data change. The allowed values are constants in
`policy_engine/tree_age.py`, and the web app has a label and a style for each one in
[`apps/web/src/features/tree-age/`](../../apps/web/src/features/tree-age/) (`i18n.ts` and `logic/treeAgeLogic.ts`).
An unknown outcome renders as "Unknown" in gray, and an unknown category as a humanized key, which is a fallback, not a
design. If you really need a new value, change the constant, the validator tests, the web labels in every language, the
contract in [`docs/architecture/api-contract.md`](../architecture/api-contract.md) and the research note together, in
one pull request.

## Wording rules

- **Estimates are not credits.** Nothing in a rule converts a tree into a credit, and every assessment says
  `certified: false`. Write "can qualify only under these conditions", never "earns credits".
- **India.** Green Credits (GCP) and carbon credits (CCTS) are separate mechanisms. Keep them in separate rules.
- **EU.** CRCF certification is required, and an estimate is never automatically certifiable.
- **Terms.** "Estimated annual carbon removal (tCO₂e/yr)", never "ESG amount". A payment is other farm income and is
  never summed with the carbon value or the environmental benefit.
- **Privacy.** A rule describes a law, not a person or a place on a map. Never put coordinates, owner names or a
  specific plot in a rule.

## Checklist for the pull request

- [ ] I opened every source. `verified` only where the text states the condition
- [ ] Every `sources` entry has a title, a publisher, an `https://` link and an `accessed` date
- [ ] `pending` rules have `notes` that say what is missing
- [ ] `amount` is `null` or states its unit and `as_of`
- [ ] The subdivision exists in `subdivisions.yaml` with its exact ISO 3166-2 code
- [ ] `updated` (and `version`) bumped
- [ ] The three test groups pass, and the production gate still holds
- [ ] The research note's rule index and totals are updated
- [ ] The pull request names the sources and says what I could not confirm

Next: [release process](release-process.md) or [testing](testing.md).
