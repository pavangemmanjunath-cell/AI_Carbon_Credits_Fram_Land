# Contributing to AgriCarbon Atlas

Thank you for considering a contribution. AgriCarbon Atlas produces numbers
that farmers, landowners and reviewers may act on, so the bar for a change is
higher than "it works": every calculation must be traceable to a published
source, every dataset must carry a license, and every result must stay
labelled as an estimate. The rules in [CLAUDE.md](CLAUDE.md) bind every
contribution, whether it was written by a person or with AI assistance.

## Ways to contribute

| Kind of contribution | Where to start | Typical label |
|---|---|---|
| Translations (Tamil, Telugu, Marathi, Bengali, Punjabi, Spanish, German, French…) | `apps/web/src/i18n/` and [docs/community/starter-issues.md](docs/community/starter-issues.md) | `documentation`, `good first issue` |
| A new dataset or API adapter | [docs/developer-guide/adding-a-data-adapter.md](docs/developer-guide/adding-a-data-adapter.md) and the *Data source* issue template | `data` |
| A regional policy rule | [docs/developer-guide/adding-a-region.md](docs/developer-guide/adding-a-region.md#2-the-policy-file) and the *Region rule* issue template | `policy`, `region-*` |
| A species parameter or allometric equation | [docs/developer-guide/adding-a-species-or-parameter.md](docs/developer-guide/adding-a-species-or-parameter.md) and the *Carbon model* issue template | `carbon-model`, `research` |
| Front-end work (map, cube, simulation lab) | [docs/architecture/mapping-architecture.md](docs/architecture/mapping-architecture.md) | `frontend` |
| Back-end work (API, engines) | [docs/architecture/api-contract.md](docs/architecture/api-contract.md) | `backend` |
| Documentation fixes | [docs/README.md](docs/README.md) | `documentation` |

If you are unsure where something belongs, open a discussion or a draft pull
request and ask.

## Before you start

1. Read [CLAUDE.md](CLAUDE.md). The thirteen core principles are not
   negotiable; the most frequently missed ones are *no carbon values
   hard-coded*, *every model cites a methodology* and *privacy by default*.
2. Set up the project with
   [docs/developer-guide/setup.md](docs/developer-guide/setup.md)
   (`make install`, `make dev`).
3. Search existing issues. If none matches, open one before investing in a
   large change so that the scope and the data-licensing questions can be
   settled first.

## Development workflow

1. Fork the repository and create a branch named after the change
   (`feat/usda-nass-adapter`, `fix/ndvi-cloud-mask`, `docs/crcf-update`).
2. Make the change. Keep pull requests focused: one adapter, one rule, one
   fix. A pull request that touches `config/`, an engine and the UI at once
   is hard to review and harder to revert.
3. Add or update tests. Every calculation needs a pytest or Vitest test
   ([docs/developer-guide/testing.md](docs/developer-guide/testing.md)). A
   parameter with `verification_status: pending` must be exercised by a
   data-quality test that fails in production mode.
4. Run `make lint` and `make test` locally. CI runs the same commands plus
   CodeQL, dependency and secret scanning, a Docker build and a docs link
   check.
5. Fill in **every** section of the pull request template: why · inputs ·
   outputs · data source · licensing impact · privacy impact · testing. "N/A"
   is an acceptable answer only when it is true; a reviewer will ask.

## What reviewers look for

- **Provenance.** New parameters carry `source`, `source_table`, `unit` and
  `verification_status`. A number copied from memory is `pending`, not
  `verified`.
- **Configuration over code.** Policy logic lives in `config/policies/`,
  species parameters in `config/species/`, regional settings in
  `config/regions/`. An `if country == "IN"` inside a React component or an
  engine is a review blocker.
- **Licensing.** A new dataset appears in
  [docs/licensing/DATA_LICENSES.md](docs/licensing/DATA_LICENSES.md) and in
  the adapter's `provenance()` with the exact attribution string.
- **Privacy.** Nothing logs coordinates; nothing sends coordinates to an
  LLM; public views use the generalized centroid only.
- **Language.** Outputs say "estimated annual carbon removal (tCO₂e/yr)",
  never "ESG amount", and never present an estimate as a credit.
- **Uncertainty.** Carbon outputs are ranges with `confidence`, never single
  numbers.

## Commit messages and sign-off

Use conventional, imperative commit messages (`feat(policy): add CRCF
agroforestry rule`). By submitting a contribution you certify the
[Developer Certificate of Origin 1.1](https://developercertificate.org/);
add `Signed-off-by: Your Name <email>` with `git commit -s`. Contributions
are licensed under the project's Apache License 2.0
([LICENSE](LICENSE)); no separate contributor license agreement is required.

## AI-assisted contributions

AI tools are welcome as long as a human takes responsibility for the result.
State in the pull request that AI assistance was used, verify every cited
source yourself, and never let a model "fill in" a carbon factor, a policy
threshold or a regulatory date. A fabricated citation is treated as a
correctness bug of the highest severity.

## Reporting problems

- Bugs and feature requests: use the issue templates.
- Security or privacy issues (for example a leak of farm geometry): follow
  [SECURITY.md](SECURITY.md) and do **not** open a public issue.
- Conduct concerns: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Recognition

Merged contributions are credited in the release notes and, for sustained
work, in [CONTRIBUTORS.md](CONTRIBUTORS.md). We list real contributions only
(see that file for the policy).
