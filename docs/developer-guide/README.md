# Developer guide

Everything you need to build, change and extend AgriCarbon Atlas. The platform produces numbers that farmers, advisors
and reviewers may act on, so the guide is as much about *how to change things safely* as about how to run them. If you
only read one page first, read the rules below and then [setup](setup.md).

## Your first hour

1. Read the rules that bind every contribution: [CLAUDE.md](../../CLAUDE.md) (thirteen principles) and
   [CONTRIBUTING.md](../../CONTRIBUTING.md).
2. Get it running in demo mode, which needs no network and no keys: [setup](setup.md) (`make install`, then
   `make dev`).
3. Follow one request through the code: [architecture overview](architecture-overview.md).
4. Pick a small first task from the [starter issues](../community/starter-issues.md).

## Pages

| Page | Read it when you want to... |
| --- | --- |
| [Setup](setup.md) | Install, configure, run in demo or live mode, use PostgreSQL or Docker, look up an environment variable |
| [Architecture overview](architecture-overview.md) | Find the file to open for a change; see the repository map, the request path and the privacy boundary |
| [Testing](testing.md) | Run and write tests, test the PostgreSQL schema, and see what CI checks |
| [Adding a region](adding-a-region.md) | Support a new country, or change program rules and price scenarios for a region |
| [Adding a species or parameter](adding-a-species-or-parameter.md) | Verify a `pending` value, add a species, or change an equation |
| [Adding a tree-age rule](adding-a-tree-age-rule.md) | Record a law or program that treats trees differently by age or size |
| [Adding an integration](adding-an-integration.md) | Connect a new external API or dataset with its demo twin, or add an imagery provider |
| [Release process](release-process.md) | Cut a version; understand why production needs verified parameters |
| [Troubleshooting](troubleshooting.md) | Fix a gray map, a CORS error, a missing font, a failing install or a docs check |

Module READMEs describe each package's public API: [API](../../apps/api/README.md),
[web app](../../apps/web/README.md), [carbon engine](../../packages/carbon-engine/README.md),
[geo engine](../../packages/geo-engine/README.md), [policy engine](../../packages/policy-engine/README.md),
[report engine](../../packages/report-engine/README.md), [agent framework](../../packages/agent-framework/README.md) and
[integrations](../../integrations/README.md). The agent team is explained in [docs/agents](../agents/README.md). The QGIS
plugin has its own [README](../../integrations/qgis-plugin/README.md) and a
[user guide](../user-guide/qgis-plugin.md).

Some pages elsewhere in the documentation use other names for topics covered here:

| Looking for | It is in |
| --- | --- |
| Adding a species | [Adding a species or parameter, "Adding a species"](adding-a-species-or-parameter.md#adding-a-species) |
| Adding a policy rule | [Adding a region, "The policy file"](adding-a-region.md#2-the-policy-file) |
| Adding a data adapter | [Adding an integration](adding-an-integration.md) |
| Adding an imagery provider | [Adding an integration, "Which kind of integration is it?"](adding-an-integration.md#which-kind-of-integration-is-it) |
| Repository layout, architecture tour | [Architecture overview, "Repository map"](architecture-overview.md#repository-map) |
| Release | [Release process](release-process.md) |
| Coding standards | ["Conventions"](#conventions) below |

The older file names `architecture-tour.md`, `adding-a-parameter.md` and `adding-a-data-adapter.md` remain as short
pointers, so that links from other pages keep working.

## The rules that matter most

These come from [CLAUDE.md](../../CLAUDE.md); a change that breaks one is not merged.

- **An estimate is not a carbon credit.** Every carbon output carries `certified: false` until a registry serial number
  exists, and says "Scenario estimate; not an issued carbon credit."
- **Three values, never summed.** Environmental benefit (tCO₂e/yr), indicative carbon value (a scenario price times the
  estimate) and other farm income are reported separately.
- **No carbon values in code.** Parameters live in `config/` with a `source`, a `unit` and a `verification_status`
  (`verified`, `pending` or `assumption`). Production refuses `pending`.
- **React renders, engines calculate, adapters fetch.** No business logic in components; policy rules live in
  `config/policies/` and `config/tree-age/`, not in `if` statements. Agents organize and explain; they never
  calculate.
- **Regions are configuration.** ISO 3166-1 alpha-2 codes are the key; calling codes are UX aliases.
- **Privacy by default.** Exact polygons are private, public views use the 0.05 degree generalized centroid,
  coordinates are never logged and never sent to a language model.
- **Never invent data.** Environmental data, eligibility rules, carbon factors and equations come from a cited source.
  When you do not know, write `TODO(verify)` and name the document that would settle it.
- **India: Green Credits (GCP) and carbon credits (CCTS) are separate mechanisms. EU: CRCF certification is required,
  and an estimate is never automatically certifiable.**

## Commands you will use

```bash
make install        # Python packages (editable) and web dependencies
make dev            # API on :8000 and web on :5173
make test           # pytest, then web typecheck and Vitest
make lint           # ruff, mypy, ESLint
make format         # ruff format, Prettier
python3 -m pytest packages/carbon-engine -q            # one package
cd apps/web && npm run test -- --run                   # web unit tests once
docker compose up --build                              # whole stack (needs .env)
```

## Conventions

- **Python 3.12+**, formatted and linted by ruff (line length 100; rules E, F, I, B, UP; the settings are in the root
  `pyproject.toml`) and type-checked by mypy. Public functions have type hints. Keep functions pure where you can;
  engines have no I/O except reading `config/`.
- **TypeScript**: Prettier (100 columns, single quotes, trailing commas) and ESLint, with `import type` for type-only
  imports. User-facing text goes through i18next keys, never string literals.
- **Markdown**: American spelling, SI units, ISO codes and "tCO₂e/yr"; one source link per regulatory statement; an
  unconfirmed fact is written `TODO(verify)` or "verify against the current notification"
  ([docs conventions](../README.md#conventions-used-in-these-pages)). markdownlint allows 120 columns for prose; tables,
  code blocks and headings are exempt. Note that `ruff format` also reformats Python code blocks in Markdown files.
- **Commits**: conventional, imperative messages (`feat(policy): add CRCF agroforestry rule`) with a DCO sign-off
  (`git commit -s`). Keep pull requests focused: one adapter, one rule, one fix.
- **Pull requests** fill in every section of the template: why, inputs, outputs, data source, licensing impact, privacy
  impact, testing performed.
- **Language in the product**: "estimated annual carbon removal (tCO₂e/yr)", never "ESG amount"; carbon outputs are
  ranges with a confidence grade, never single numbers.
- **Licenses**: the repository is Apache-2.0. The QGIS plugin in `integrations/qgis-plugin/` is
  GPL-2.0-or-later, and stays in its own folder ([why](../licensing/THIRD_PARTY.md#the-qgis-plugin-and-the-gpl)).
  Every new dependency and dataset gets a row in [`docs/licensing/`](../licensing/THIRD_PARTY.md).

## What lives in `.github/`

| Path | What it holds |
| --- | --- |
| `workflows/` | `ci.yml` (Python, PostgreSQL schema, web, Docker), `lint.yml`, `security.yml`, `docs.yml`, `qgis-plugin.yml` and `labeler.yml`. What each one checks is in [testing](testing.md#what-ci-runs) |
| `ISSUE_TEMPLATE/` | The issue forms: bug report, feature request, data source proposal, verify a parameter or rule, region request, carbon model proposal and policy rule proposal. Blank issues are off. `config.yml` holds the contact links |
| `PULL_REQUEST_TEMPLATE.md` | The sections [CLAUDE.md](../../CLAUDE.md) requires for every change |
| `labels.yml`, `labeler.yml` | The label list (`type/*`, `area/*`, `region/*` and a few plain ones) and the paths that apply `area/*` to pull requests. Every label an issue form or Dependabot uses must be listed in `labels.yml` |
| `CODEOWNERS` | Who reviews carbon parameters, policy rules, tree-age rules and the privacy boundary |
| `dependabot.yml` | Weekly grouped dependency updates for pip, npm, Docker and GitHub Actions |
| `scripts/` | The PostgreSQL smoke test and constraint checks that the schema job runs |

## Getting help

Ask in the repository's Discussions (Q&A) or open a draft pull request. Security and privacy problems go through
[SECURITY.md](../../SECURITY.md), not a public issue. The roles and the way decisions are made are in
[GOVERNANCE.md](../../GOVERNANCE.md).
