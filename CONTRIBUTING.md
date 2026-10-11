# Contributing to CarbonCreditBuy

Thank you for considering a contribution. CarbonCreditBuy produces numbers
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

Read [CLAUDE.md](CLAUDE.md). Its thirteen core principles are not negotiable; the most often missed are *no carbon
values hard-coded*, *every model cites a methodology* and *privacy by default*. Search existing issues; for a large
change, open an issue first so scope and data-licensing questions are settled before you invest time.

## Development workflow

1. **Fork** the repository on GitHub and **clone** your fork:

   ```bash
   git clone https://github.com/<your-account>/AI_Carbon_Credits_Fram_Land.git
   cd AI_Carbon_Credits_Fram_Land
   ```

2. **Set up the environment** (Python 3.12+, Node.js 22+). Full details:
   [docs/developer-guide/setup.md](docs/developer-guide/setup.md).

   ```bash
   python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
   make install                                     # Python packages (editable) + web dependencies
   make test                                        # must pass before you change anything
   ```

   On Windows without `make`, `run_all.bat` installs and runs the tests, and `START.bat` starts the app.

3. **Create a branch** named after the kind of change:

   | Prefix | Use for | Example |
   |---|---|---|
   | `feature/` | New functionality | `feature/usda-nass-adapter` |
   | `fix/` | Bug fixes | `fix/ndvi-cloud-mask` |
   | `docs/` | Documentation only | `docs/crcf-update` |
   | `research/` | Validation, parameter verification, benchmarks | `research/teak-wood-density-check` |

4. **Follow the coding conventions.** Python: `ruff` (lint and format, line length 100) and `mypy`. TypeScript:
   ESLint and Prettier (`apps/web/.prettierrc`). Engines calculate, adapters fetch, components render. Keep pull
   requests focused: one adapter, one rule or one fix.
5. **Add or update tests.** Every calculation needs a pytest or Vitest test
   ([docs/developer-guide/testing.md](docs/developer-guide/testing.md)). A parameter with
   `verification_status: pending` must be exercised by a data-quality test that fails in production mode.
6. **Update the documentation** that describes the behaviour you changed, and add a line to
   [CHANGELOG.md](CHANGELOG.md) under *Unreleased*.
7. **Run the checks locally:** `make lint` and `make test`. CI runs the same commands plus CodeQL, dependency and
   secret scanning, a Docker build and a documentation link check.
8. **Open a pull request** and fill in every section of the template: why · inputs · outputs · data source ·
   licensing impact · privacy impact · testing. "N/A" is acceptable only when it is true.

## Research contributions

Independent researchers are especially welcome to test the project's claims:

- **Reproduce** the implementation checks: `python benchmarks/run_experiments.py` (see
  [docs/reproducibility.md](docs/reproducibility.md)) and report any difference in the result files.
- **Validate** against field data or reference tools. This is validation levels 2 and 3 in
  [research/validation/](research/validation/README.md), which have not been performed yet. Use a `research/`
  branch and include the data's licence.
- **Verify parameters.** Many parameters are `pending` or `assumption`. Replacing one with a value from a primary
  source (with `source`, `source_table` and the reviewer) is one of the most valuable contributions.
- **Benchmark** against other tools on the same synthetic or open inputs, and report both agreement and disagreement.

Independent reuse, citations and validations are recorded in [docs/research-impact.md](docs/research-impact.md)
with links to the evidence.

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
