# policy-engine

Screens a plot and an activity against the programme rules in
`config/policies/<REGION>.yaml` and returns, for each programme, a **screening
status**, the requirements a project would need to meet and the references that
support the rule.

The output is never an eligibility determination. Every result carries the
region's disclaimer, for example "Initial screening only - not an eligibility
determination." The rules live in YAML; this package only evaluates them, so a
policy change is a configuration change reviewed by a regional domain reviewer,
not a code change.

A second module, [`policy_engine.tree_age`](#tree-age-rules), does the same for rules that treat trees differently by
age or size: it reads `config/tree-age/rules.yaml`, checks it against a schema, and says which rules apply to trees of
a given age, in a given place and setting.

## Install

```bash
python3 -m pip install -e packages/policy-engine       # or: make install
```

The only dependency is PyYAML. `config/` is found through `ATLAS_CONFIG_DIR` or
by walking up from the package and then from the working directory.

## Public API

Import from `policy_engine`:

| Name | Purpose |
| --- | --- |
| `get_engine(config_dir=None)` | Cached `PolicyEngine` |
| `PolicyEngine.screen(country, activity, land_type=None, area_ha=None)` | Returns a `Screening` |
| `PolicyEngine.resolve_region(country)` | ISO 3166-1 alpha-2 to region id (`DE` to `EU`); unknown codes raise `KeyError` |
| `PolicyEngine.programme_url(region_id, programme_id)` | Programme link from the region file, else the first reference URL |
| `Screening`, `ProgrammeScreening` | Result dataclasses with `to_dict()`; `Screening.summary()` gives a one-line label |
| `ACTIVITIES` | `tree_plantation`, `agroforestry`, `soil_carbon`, `cropland_practice`, `grazing` |
| `STATUSES` | `potentially_applicable`, `requires_assessment`, `requires_methodology_assessment`, `requires_certification`, `not_applicable`, `unknown` |
| `load_policy`, `load_regions`, `PolicyConfig`, `RegionIndex`, `find_config_dir` | Loaders |

### Example

```python
from policy_engine import get_engine

screening = get_engine().screen("IN", "tree_plantation", area_ha=2.0)
print(screening.disclaimer)
for programme in screening.programmes:
    print(programme.id, programme.status, programme.distinct_from)
# in-gcp   requires_assessment               ['in-ccts']
# in-ccts  requires_methodology_assessment   ['in-gcp']
# in-state-agroforestry  potentially_applicable  []
```

Country codes accept any EU member state: `screen("DE", "agroforestry")`
resolves to the `EU` rules through `member_states` in
`config/regions/EU.yaml`.

## Rule format

```yaml
programmes:
  - id: in-gcp
    name: ...
    authority: ...
    kind: government_programme          # free text used for display
    distinct_from: [in-ccts]            # optional; produces a "separate mechanism" note
    rules:
      - when: {activity: [tree_plantation, agroforestry]}
        status: requires_assessment
        reason: "Text shown to the user, factual, no promises."
      - when: {activity: agroforestry, land_type: cropland, min_area: 1.0}
        status: potentially_applicable
        reason: "..."
      - default: not_applicable
    requirements: ["..."]
    references:
      - {title: "...", url: "https://..."}
```

Evaluation:

1. Rules are tried in order; **the first rule whose `when` matches wins**.
2. The supported `when` keys are `activity` (string or list), `land_type`
   (string or list), `min_area` and `max_area` (hectares, inclusive). A rule
   with `land_type`, `min_area` or `max_area` does not match when the caller
   did not supply that value.
3. If no rule matches, the programme's `default` status applies; with no
   default the status is `unknown`.
4. `distinct_from` adds a note such as "CCTS is a separate mechanism from Green
   Credits" unless the programme is `not_applicable`.

Unknown `when` keys are silently ignored, so a misspelt key makes a rule match
more broadly than intended. Keep rules narrow, review them against the
reference documents and cover every new rule with a test.

## Statuses in plain words

| Status | Meaning |
| --- | --- |
| `potentially_applicable` | The programme may fit this activity; conditions still have to be checked with the administrator |
| `requires_assessment` | A programme-specific assessment (for example of land or scope) is needed first |
| `requires_methodology_assessment` | An approved methodology, baseline and verification are needed |
| `requires_certification` | Certification by a recognised scheme is required (for example under the EU CRCF) |
| `not_applicable` | The programme does not address this activity |
| `unknown` | No rule covers this case; do not read it as "no" |

## Tree-age rules

`policy_engine/tree_age.py` loads, validates and evaluates [`config/tree-age/rules.yaml`](../../config/tree-age/rules.yaml)
(22 rules in this release) together with
[`config/tree-age/subdivisions.yaml`](../../config/tree-age/subdivisions.yaml), the ISO 3166-2 names of states and
regions. The file lists real programmes and laws: carbon-credit eligibility, incentive payments, tree-protection laws,
compensatory planting and methodology notes. The module only reads and matches them; every rule, number, source and
`verification_status` stays in the YAML, and the output is screening information, never an eligibility decision. The
module is imported by its own path (`from policy_engine import tree_age`), not from the package root.

| Name | Purpose |
| --- | --- |
| `load_rules(config_dir=None)`, `load_subdivisions(config_dir=None)` | Load, validate and return a private copy; a schema problem raises `TreeAgeRulesError` listing every problem |
| `validate_rules(doc, subdivisions=None)`, `rule_problems(...)` | The schema check on its own; `rule_problems` returns the problems as sentences |
| `age_class_for(age_years, rules_doc=None)` | The age class from the file: `young`, `mature`, `old` or `veteran`, with its label |
| `select_rules(rules_doc, country, region, subdivision, allow_pending=True)` | The rules of a place, as written in the file |
| `evaluate(rules_doc, country, region, subdivision, setting, age_years, locality=None, subdivisions=None, allow_pending=True)` | The rules of a place with `applies`, `why` and `outcome_for_you` added to each |
| `credit_outlook(rules, age_years)` | One statement about carbon credits for the trees: `not-eligible` or `conditional` |
| `pending_rules(doc)`, `withheld_rule_ids(...)` | Rules not yet confirmed from a primary source, and the ids that production hides |
| `SCOPES`, `CATEGORIES`, `OUTCOMES`, `RULE_STATUSES`, `REQUEST_SETTINGS`, `CREDIT_OUTLOOKS` | The enumerations of the schema |

```python
from policy_engine import tree_age

doc = tree_age.load_rules()
rules = tree_age.evaluate(doc, "IN", "IN", "IN-HR", "farm", 80)
for rule in rules[:3]:
    print(rule["id"], rule["applies"], rule["outcome_for_you"])
print(tree_age.credit_outlook(rules, 80)["existing_trees"])  # not-eligible
print(tree_age.age_class_for(80, doc)["id"])  # veteran
```

How `evaluate` decides:

1. **Geography is a hard filter.** Rules with scope `GLOBAL`, the user's region (`IN`, `US`, `EU`) and, when a rule names
   a country, that country are returned. Rules of other regions are not.
2. **A rule that does not fit is returned with `applies: false`**, never dropped, so people can see what would apply
   elsewhere. The cases: a different `subdivision`, a municipal example when the place is not that locality, an age
   outside `min_age_years` and `max_age_years` (`null` means no bound), and a rule written for another `setting`
   (`urban`, `forest` or `non-forest`; a farm tree is non-forest; `any` never excludes a rule). `why` says in plain
   words which condition decided.
3. **`outcome_for_you`** is the rule's `outcome_for_existing_trees` when `age_years` is 1 or more. At age 0, trees being
   planned, rules written for new planting or for any trees become `conditional` and rules about existing trees become
   `not-applicable`.
4. **Order:** applicable rules first, then by category, then by rule id.
5. **`credit_outlook`** looks only at applicable, in-force carbon-credit rules. It answers `not-eligible` unless a rule
   gives existing trees a route (`conditional`), and at age 0 it answers `conditional`. It never answers `eligible`:
   only a programme's own verification can decide that.

**Production.** A rule is `verified` or `pending`. With `allow_pending=False` the pending rules are withheld, the way the
carbon engine refuses pending parameters (CLAUDE.md principle 10), and `withheld_rule_ids` names them so a client can
say that something was left out. The API passes `allow_pending` from `ATLAS_ALLOW_PENDING_PARAMETERS` and
`ATLAS_ENV`; a data-quality test (run with `ATLAS_ENV=production`) checks that no pending rule is served.

Adding a rule is a configuration change with its own checklist:
[adding a tree-age rule](../../docs/developer-guide/adding-a-tree-age-rule.md). The research behind the file is in
[tree-age carbon rules](../../docs/research/tree-age-carbon-rules.md).

## Tests

```bash
python3 -m pytest packages/policy-engine -q
```

`tests/test_policy_engine.py` covers member-state resolution, every activity for
India, the United States and the EU, status values staying inside the contract
enum, rejection of unknown activities and the rule-matching semantics.
`tests/data-quality/test_parameters.py` checks that every programme has
references with URLs and that no programme's final `default` is `potentially_applicable`.

`tests/test_tree_age_rules_engine.py` covers the tree-age module: schema validation with clear messages, contiguous age
classes, geography, the age and setting filters, municipal examples and Berlin, `outcome_for_you` at age 0, ordering,
the credit outlook (never `eligible`, only in-force rules lift it), and withholding of pending rules.
`tests/data-quality/test_tree_age_rules.py` checks the shipped file: sources, `verification_status` and, with
`ATLAS_ENV=production`, that no pending rule is served.

## Design notes

- The engine does not compute eligibility, money or carbon. It reads rules.
- Keep India's Green Credit Programme (GCP) and the Carbon Credit Trading Scheme
  (CCTS) as separate programmes joined by `distinct_from`; they are separate
  mechanisms.
- A rule's `reason` is displayed verbatim in the web app and in reports. Write
  it so a farmer could read it, and cite the document in `references`.
- Rules cite sources; do not add thresholds, dates or prices that you cannot
  link to an official document. When unsure, use a lower-commitment status and
  write `TODO(verify)` in the pull request.

## Links

- [Adding a region and its policy rules](../../docs/developer-guide/adding-a-region.md)
- [Region notes](../../docs/regions/IN/README.md), [US](../../docs/regions/US/README.md), [EU](../../docs/regions/EU/README.md)
- [Policy references research note](../../docs/research/policy-references.md)
- [Tree-age model](../../docs/architecture/tree-age-model.md) and the
  [tree-age carbon rules research note](../../docs/research/tree-age-carbon-rules.md)
- [Policy files](../../config/policies/) and [region files](../../config/regions/)
