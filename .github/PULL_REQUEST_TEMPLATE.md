<!--
Thank you for contributing to AgriCarbon Atlas.
Every section below is required by CLAUDE.md ("Pull request rule"):
why · inputs · outputs · data source · licensing impact · privacy impact · testing performed.
Write "none" where a section genuinely does not apply; a reviewer will check.
-->

## Why

<!-- The problem or need. Link the issue (Closes #123). For carbon or policy
changes, name the source document that motivates the change. -->

## Inputs

<!-- What the change consumes: request fields, config keys, environment
variables, datasets, user actions. New config keys list `source`,
`source_table`, `unit` and `verification_status`. -->

## Outputs

<!-- What the change produces: response fields, UI elements, files, logs.
Carbon outputs must remain ranges (low, central, high) with confidence,
`certified: false` and the disclaimer. -->

## Data source

<!-- Dataset or API touched or added, with URL, version and update cadence.
"none" if no external data is involved. -->

## Licensing impact

<!-- New or changed licenses, attribution strings, terms-of-use constraints
(rate limits, non-commercial clauses). Confirm docs/licensing/DATA_LICENSES.md
and the adapter `provenance()` were updated. "none" if nothing changed. -->

## Privacy impact

<!-- Does the change touch plot geometry, centroids, coordinates, logs,
caches, shareable links or the /explain payload? State how the privacy
boundary in docs/privacy/privacy-design.md is preserved. -->

## Testing performed

<!-- Commands run (make lint, make test, Playwright), new tests added, and
how a reviewer can reproduce. For parameter changes: which table cell was
checked, in which edition of the source, and by whom. -->

## Checklist

Carbon and policy content

- [ ] No hard-coded carbon values: numbers live in `config/` with `source`, `source_table`, `unit` and
      `verification_status`.
- [ ] Every parameter I added or changed cites its source; anything I could not check is marked `pending` (or
      `assumption`), never `verified`.
- [ ] Outputs are labeled as estimates, not credits: `certified: false`, the disclaimer is present, and wording follows
      the terminology in CLAUDE.md.
- [ ] Results keep their provenance: dataset versions, acquisition dates, model and parameter versions, generation time.
- [ ] Environmental benefit, indicative carbon value and other farm income stay separate and are never summed.
- [ ] Policy results stay a screening (never "eligible"); India Green Credits (GCP) and CCTS stay distinct; EU wording
      keeps CRCF certification as a requirement.

Privacy and architecture

- [ ] No coordinates are logged, put in error messages, or sent to an LLM (agents and `/explain` receive derived
      indicators only) or to a third-party service beyond what the adapter already documents.
- [ ] No business logic in UI components; no `if country == ...` outside `config/`.
- [ ] Models cite a methodology; new datasets and APIs are listed in `docs/licensing/DATA_LICENSES.md` (new imagery
      providers also in `docs/licensing/ATTRIBUTION.md`), with endpoints read from environment variables.
- [ ] Database changes keep `data/schemas/schema.sql` idempotent and in step with
      `apps/api/app/repositories/postgres.py` (the *PostgreSQL schema* CI job checks this).

Quality

- [ ] Tests added or updated (pytest or Vitest); `make lint` and `make test` pass locally.
- [ ] Documentation updated (`docs/`, and `CHANGELOG.md` under *Unreleased*). A new dependency is added to
      `docs/licensing/THIRD_PARTY.md` with its license.
- [ ] AI assistance, if used, is disclosed and every citation was verified by me.
- [ ] Commits are signed off (`git commit -s`, DCO 1.1).

See [CLAUDE.md](../CLAUDE.md) for the rules behind each box.
