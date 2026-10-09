# Adding a species, or verifying and changing a parameter

Carbon numbers are never typed into code. Every factor, table cell, species value and assumption the
carbon engine uses lives in `config/` with a source and a verification status, and the engine echoes each
one it touched in the `parameters_used` list of every estimate ([CLAUDE.md](../../CLAUDE.md) principles
3, 4 and 10). This page covers three jobs: verifying a parameter that is still `pending`, adding a
species, and adding a new parameter or equation. Tree-age **rules** (laws and programs that treat trees
differently by age) are a different kind of data and have their own page:
[adding a tree-age rule](adding-a-tree-age-rule.md). Read the
[carbon engine architecture](../architecture/carbon-engine.md) first if the model is new to you, and the
[carbon-engine README](../../packages/carbon-engine/README.md) for the API.

## The three statuses

Every cited parameter carries `verification_status`:

| Status | Meaning | Who sets it | In production |
| --- | --- | --- | --- |
| `verified` | The value was checked against the cited table or equation in the primary source, by a person, and matches | A domain reviewer, after checking the source themselves | Allowed |
| `assumption` | A project assumption that is not a literature value (for example the 0.85 default survival rate). The `source` says why it is reasonable. Shown in provenance | A contributor, with a reviewer's agreement | Allowed |
| `pending` | A working value copied from notes that **must** be checked before release | The default for anything not yet checked | **Refused** |

Rules that follow from this:

- A contributor proposes; a **reviewer** sets `verified` ([GOVERNANCE.md](../../GOVERNANCE.md): "the
  parameter's `verification_status` is updated to `verified` only by the reviewer who checked the source
  table").
- Never copy a value from memory, a secondary summary or an AI answer. Read the primary source.
- If a later check finds an error or a newer edition, downgrade to `pending` in the same pull request that
  raises the question.
- Do not label a project assumption `verified`, and do not invent a source for it.

## What production does with `pending`

The engine collects every parameter a calculation used and calls `assert_production_safe`. If pending
parameters are not allowed and any used parameter is `pending`, it raises `PendingParameterError`, which
the API returns as **HTTP 409 `pending-parameters`** with the parameter names. The API disallows pending
parameters when `ATLAS_ENV=production`, whatever `ATLAS_ALLOW_PENDING_PARAMETERS` says, and also when that
variable is `false` ([setup](setup.md#demo-mode-and-live-mode)). The engine itself defaults to allowing
pending parameters, so a script that calls it directly must pass
`ModelParams(allow_pending_parameters=False)` to test the gate. The tree-age endpoint follows the same
rule for carbon parameters, and withholds `pending` tree-age rules instead of refusing.

Only parameters the calculation actually used count. With the v0.1 configuration:

| Calculation | Pending parameters it uses |
| --- | --- |
| Tier 1 (no diameter), also the tree-age curve | `above_ground_biomass_growth`, `root_to_shoot_ratio` |
| Tier 2 (diameter given), tropical species | `root_to_shoot_ratio`, `wood_density_g_cm3` |
| Tier 2, species with the `temperate_generic` allometry | The above plus `species_allometry` |

So with the v0.1 configuration a production deployment cannot return an estimate at all: the root-to-shoot
table (Table 4.4) blocks both tiers, and Tier 1 additionally needs Tables 4.10 and 4.12. That is intended.

## Where parameters live

| File | Holds | Entry shape |
| --- | --- | --- |
| `config/methodologies/ipcc-2006-tier1.yaml` | Constants, root-to-shoot table, Tier 1 growth table, allometry registry, behavior assumptions | `constants.<name>`: `{value, unit, source, verification_status}`. `root_to_shoot` and `above_ground_biomass_growth`: one `source` and one `verification_status` for the whole table, values per climate zone. `allometry.<key>`: `{equation, source, verification_status}`. `assumptions.<name>` |
| `config/methodologies/tree-biomass-model.yaml` | Model behavior settings (horizon, post-maturity factor) | `settings.<name>`: `{value, unit, source, verification_status}` |
| `config/species/species.yaml` | One row per species | Numeric fields as `{value, source, verification_status}` |
| `config/readiness.yaml` | Evidence weights for the readiness score | Weights are project assumptions |
| `config/detection.yaml` | Thresholds for point-cloud and satellite tree detection | `{value, unit, source, verification_status}`. Most are uncalibrated assumptions |
| `config/market/carbon-price-scenarios.yaml` | Illustrative prices per region | `verification_status: pending` per region |
| `config/imagery/providers.yaml` | Imagery providers, licenses, attribution | `verification_status` per provider; see [adding a region](adding-a-region.md#6-tree-age-rules-and-imagery) |
| `config/tree-age/rules.yaml` | Laws and programs by tree age | `verified` or `pending` per rule; see [adding a tree-age rule](adding-a-tree-age-rule.md) |

Notes on the entry shape:

- The **table** goes in the `source` string, for example `IPCC 2006 Vol.4 Ch.4 Table 4.4`. CLAUDE.md and the
  pull request template also mention a `source_table` key; the files do not use it, and the parameter
  store ignores extra keys, so keep the table inside `source`.
- Root-to-shoot class keys are read by `carbon_engine/parameters.py`: `default`, `agb_lt_<n>`,
  `agb_ge_<n>`, `agb_gt_<n>` and `agb_<a>_<b>` (inclusive range). Any other key raises a `ValueError` when
  that zone is evaluated.
- A bare number in a species row (`maturity_years`, `max_density_per_ha`) is treated by the store as an
  `assumption` sourced to the species file. Prefer the explicit `{value, source, verification_status}`
  form for anything that affects a result.
- Missing keys are errors, not defaults. The engine contains no numeric literals except unit conversions,
  so there is nothing to silently fall back to.

## Verifying a pending parameter

1. **Open the issue.** Use the "Verify a parameter or rule" form
   ([`parameter_verification.yml`](../../.github/ISSUE_TEMPLATE/parameter_verification.yml)). It asks for
   the file and the key, the current value, the cited table and edition, the value you found, where you
   found it (page, table, row), how it compares, and your confirmation that you read the primary source.
   Quote only the short row you need.
2. **Find the entry.** List what is pending:

   ```python
   from carbon_engine import get_store

   for p in get_store().all_cited_parameters():
       if p.verification_status == "pending":
           print(p.name, "|", p.source)
   ```

3. **Check it yourself** against the edition named in `source` (the 2006 Guidelines, Vol. 4, or the 2019
   Refinement, or the original paper). Confirm the unit and the applicability: climate zone, age class,
   ecological zone, species or genus.
4. **Edit the YAML.** Correct `value` (and `range` for growth increments) if it differs, and write the
   exact table, page and edition into `source`. For the table-level entries (`root_to_shoot`,
   `above_ground_biomass_growth`) the status covers the whole table: check **every cell**, then change the
   table's `verification_status`. Until then leave it `pending` and say in the `source` which cells you
   checked.
5. **Record who and when.** The schema has no field for the verifier, so name the reviewer and the date in
   the pull request, in the [CHANGELOG](../../CHANGELOG.md) entry ("names the configuration file, the
   source document and the reviewer") and, briefly, in `source`.
6. **Run the tests**, including the production gate (below), and update any test that hard-codes a changed
   value. A changed growth table also moves the tree-age curve, so run
   `python3 -m pytest packages/carbon-engine apps/api/tests -q`.
7. **Get the domain review.** `config/methodologies/` and `config/species/` have carbon-reviewers as code
   owners ([`CODEOWNERS`](../../.github/CODEOWNERS)). The reviewer repeats step 3 independently and sets
   `verified`.

To see where help is needed, run the snippet above. At the time of writing the pending items are
`above_ground_biomass_growth` (Tables 4.10 and 4.12, 11 zones), `root_to_shoot_ratio` (Table 4.4, 11
zones), the `temperate_generic` allometry (its equation is `null` until a documented equation is chosen),
`wood_density_g_cm3` for every species (Zanne et al. 2009 working values), `increment_multiplier` for
teak, eucalyptus and poplar, and the market price scenarios for all three regions. The CI job summary
prints the current counts per file.

## Adding a species

Propose it first with the "Carbon model / parameter proposal" form
([`carbon_model.yml`](../../.github/ISSUE_TEMPLATE/carbon_model.yml)). The species needs a documented
source for its wood density (the Global Wood Density Database record, with the value you read) and either a
documented growth increment or an explicit decision to use the broad Tier 1 category. A species without
these does not ship.

Add a row to `config/species/species.yaml` (bump `version` for a change in meaning):

```yaml
  - id: <slug>                       # lower case, underscores; never reused for another taxon
    scientific_name: <Genus species>
    common_name: <Name>
    group: <broad group>             # reuse a value from an existing row, for example broadleaf_tropical_timber
    regions: [<region id>, ...]      # region ids, not member-state codes
    suitable_climate_zones: [<zone>, ...]   # from the 11 IPCC zones in ipcc-2006-tier1.yaml
    reference_density_per_ha: {value: <trees/ha>, source: "<spacing or citation>", verification_status: assumption}
    max_density_per_ha: <trees/ha>
    maturity_years: <years>
    typical_height_m_at_maturity: {value: <m>, source: "<citation or reason>", verification_status: assumption}
    wood_density_g_cm3: {value: <g/cm3>, source: "Zanne et al. 2009 GWDD, <record>", verification_status: pending}
    increment_multiplier: {value: <number>, source: "<table row, or why this adjustment>", verification_status: assumption}
    allometry: pantropical_chave_2014_with_height   # or temperate_generic (see below)
    notes: <what a reviewer or farmer should know>
```

Guidance:

- **Statuses for a new row.** Start at `pending` for values you copied from a table or database and
  `assumption` for judgments. Do not submit `verified`; the reviewer sets it.
- **`increment_multiplier`.** It scales the Tier 1 broad-category growth. A value of 1.0 means "use the
  category value unchanged" (as the existing `mixed_native_tropical`, `black_walnut` and `oak` rows do).
  Any other value needs a citation (for example a genus-specific table row) or an honest `assumption`
  explaining the reasoning.
- **`allometry`.** The Tier 2 path applies Chave et al. 2014 equation 4 (`pantropical_chave_2014_with_height`).
  For a temperate species use `temperate_generic`; the result then says the pantropical equation was
  applied outside its calibration domain. Supporting a better equation needs a code change (see "A new
  parameter or equation").
- **Density.** `reference_density_per_ha` is what the density scaling compares against (the factor is
  clamped to 0.2-1.5). `max_density_per_ha` is shown in the tree library and used by the QGIS plugin as a
  sanity warning.
- Species names are not translated: the interface shows `common_name` as given.
- Add the region ids where the species is grown ([adding a region](adding-a-region.md)). The species also
  appears in the tree-age calculator for those regions.
- Fruit and timber income are *other farm income*; the note may say so, but nothing here adds a monetary
  value.

`tests/data-quality/test_parameters.py` then checks that every cited field has a `value`, a `source` and a
valid status, that `suitable_climate_zones` is not empty, and that the model runs for the species in every
listed zone with `0 < low <= central <= high`.

## A new parameter or equation

Changing the model is a larger change. Propose it first with the "Carbon model / parameter proposal" form,
then before you open a pull request:

1. **Cite the methodology** (CLAUDE.md principle 4). A model or equation without a documented source does
   not ship. Add or update the entry in `config/methodologies/registry.yaml` (`id`, `name`, `kind`,
   `regions`, `url`, `status`, `used_by_models`).
2. **Put every number in `config/`.** Add it to the matching YAML with `source` and `verification_status`,
   and read it through `ParameterStore` (`constant`, `assumption_param`, `model_setting`, `species_param`).
   A missing key must stay an error.
3. **Echo it.** Append the `ParameterUsed` object to the `used` list in the model, so it appears in
   `parameters_used` and in the production gate.
4. **Keep equations pure.** Put the formula in `packages/carbon-engine/carbon_engine/equations/` as a plain
   function with a docstring that names the source and a doctest or test with a hand-computed reference
   value (as `chave_2014_agb_kg` does).
5. **Test it** in `packages/carbon-engine/tests/`: a reference value with its source and tolerance, the
   invariant `low <= central <= high`, `unit == "tCO2e/yr"`, `certified is False`, and that the new
   parameter appears in `parameters_used`.
6. **Document it** in `docs/architecture/carbon-engine.md` and the package README, and add a CHANGELOG
   entry naming the file, the source and the reviewer.
7. **Never change meaning silently.** A change to a formula or a default alters every user's estimate; say
   so in the pull request and bump the model or parameter-set `version` in the YAML.

A stub model (`agroforestry`, `soil-carbon`, `crop-practice`) raises `ModelNotImplementedError` (HTTP 501)
until it has a documented, tested method. Do not replace a stub with a placeholder equation. An agent never
adds a number either: it reports what the engines computed.

## Tests and the production gate

```bash
python3 -m pytest tests/data-quality packages/carbon-engine -q
ATLAS_ENV=production ATLAS_ALLOW_PENDING_PARAMETERS=false python3 -m pytest tests/data-quality -q
```

The second command is also a CI step. It runs `test_production_refuses_pending_parameters`, which asserts
that a mango Tier 1 estimate with pending parameters disallowed **raises** `PendingParameterError`. It
passes today because two tables are still pending. That has a consequence for you:

- When the last pending parameter that Tier 1 mango run uses is verified, the test will fail with "DID NOT
  RAISE". That is a sign of progress, not a regression. Update the test to target a parameter that is still
  pending (for example a Tier 2 run, which needs wood density), and add a test that the verified path
  succeeds in production.
- The test only runs when `ATLAS_ENV=production`; without it, it is skipped.
- `tests/README.md` says this command is expected to fail. It does not: the test asserts the refusal, and
  it passes. Treat the README as out of date.

## Pull request checklist

- [ ] Every new or changed number has `source` (with the table or page) and a status
- [ ] No status was raised to `verified` by the author; the reviewer is named
- [ ] Units checked against the source, conversions described
- [ ] Tests updated; the production gate still passes or was updated deliberately
- [ ] `parameters_used` shows the new parameter; `certified` remains `false`
- [ ] CHANGELOG entry names the file, the source and the reviewer
- [ ] The "Inputs, outputs, data source, licensing and privacy impact" sections of the PR template are
      filled in

Next: [testing](testing.md) and [release process](release-process.md).
