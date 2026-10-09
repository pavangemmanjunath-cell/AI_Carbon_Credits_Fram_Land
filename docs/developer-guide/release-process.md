# Release process

How a version of AgriCarbon Atlas is cut. A release is a checklist that a maintainer follows by hand. The workflows
test, scan and package, and none of them tags, publishes or pushes anything. The project lead releases versions and
maintainers rotate release duty ([GOVERNANCE.md](../../GOVERNANCE.md)). Two ideas run through the whole page:

1. A release changes numbers that people may act on, so it is reviewed like a change to the numbers, not only like a
   change to the code.
2. A **production** release needs its parameters verified. A `pending` parameter is a working value that nobody has
   checked against its source, and production mode refuses to run with one.

## What is automated and what is not

| Workflow | Runs on | What it gives a release |
| --- | --- | --- |
| `CI` | Pull requests, `main`, on demand | Python 3.12 and 3.13 (ruff, mypy, pytest, the production data-quality gate), the PostgreSQL schema job, the web build and tests, and a Docker build of both images with a smoke test |
| `Lint` | Pull requests, `main`, on demand | Prettier and ESLint for the web app, `ruff format --check`, yamllint on `config/` and the workflows |
| `Security` | Pull requests, `main`, weekly, on demand | CodeQL for Python and JavaScript/TypeScript, pip-audit, npm audit, gitleaks, dependency review on pull requests |
| `Docs` | Markdown changes, weekly | markdownlint, internal links (blocking), external links (advisory) |
| `QGIS plugin` | Changes under `integrations/qgis-plugin/` | Plugin tests on Python 3.9 and 3.12, then the installable ZIP as the artifact `agricarbon-atlas-qgis-plugin`, kept for 30 days |
| `Labeler` | Pull requests | Area labels |

Not automated, so on the checklist: the version bump, the changelog, the tag, the GitHub release, publishing the
images or the plugin, and any deployment. No container registry is configured in this repository.

## Versioning

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and keeps a
[CHANGELOG](../../CHANGELOG.md) in the Keep a Changelog format. Until 1.0.0 the public API (`/api/v1`) may change
between minor versions, and every such change is recorded under **Changed** with a migration note. Some changes need
extra care:

| Change | Treat it as | Also |
| --- | --- | --- |
| Response shape or endpoint of `/api/v1` | At least a minor version before 1.0, a major after | Update [`api-contract.md`](../architecture/api-contract.md) and the schemas in `data/schemas/` in the same pull request |
| A formula, default or parameter that changes any user's estimate | At least a minor version | CHANGELOG entry naming the configuration file, the source document and the reviewer |
| A policy rule or status, or a tree-age rule | A minor version | The entry names the notification, regulation or rule id it follows |
| `data/schemas/schema.sql` | Note in the release | Raise the revision in the file (see below), and tell operators to apply the file again with `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/schemas/schema.sql` |
| A bug fix with no output change | Patch | |
| Configuration only (a new region, species, imagery provider or price review) | Minor | Config files carry their own `version:` too |

Configuration versions (`version:` in `config/species/species.yaml`, the Tier 1 file, the model file, `readiness.yaml`,
`tree-age/rules.yaml` and the price scenarios) appear in the provenance of every result. Bump one when its content
changes in meaning, even between releases.

The database schema has its own revision, written in the header of `data/schemas/schema.sql` and recorded in the
`schema_version` table when the file is applied. The file is idempotent, and its upgrade block brings a database that
was created from an older revision up to date inside one transaction. If an existing row breaks a new constraint, the
whole upgrade rolls back and the error names the constraint. Say in the release notes which revision the release needs.

## Two kinds of release

| | Development or demo release | Production release |
| --- | --- | --- |
| Purpose | Developers, demos, workshops, review | Real use with `ATLAS_ENV=production` |
| `pending` parameters | May remain. The release notes list them | Every parameter the default calculations use is `verified` or a documented `assumption`; none is `pending` |
| `pending` tree-age rules | Shown with a "not yet confirmed" flag. The notes list them | Withheld by the API. The notes list the withheld rule ids, or the rules are confirmed first |
| Who signs off | A maintainer | A maintainer **and** a domain reviewer for each affected area |
| Gate | CI green | CI green **and** the production gate passes **and** the review below is complete |

`verified` is never set by the person who prepares the release or by the author of a change. A **domain reviewer** sets
it after checking the cited table or equation themselves
([species and parameters](adding-a-species-or-parameter.md#verifying-a-pending-parameter); for rules,
[adding a tree-age rule](adding-a-tree-age-rule.md#pending-rules-and-production)). That is a project rule
([GOVERNANCE.md](../../GOVERNANCE.md)), not a formality: it is what stops an unchecked number from reaching a farmer as
a result.

Run the snippet in [species and parameters](adding-a-species-or-parameter.md#verifying-a-pending-parameter) to see
which parameters are still `pending`. As long as the growth tables or the species wood densities are pending, a build
can be demoed and developed but cannot return an estimate in production mode: the API answers HTTP 409
`pending-parameters`. Reaching a production release means verifying those parameters first.

## Checklist: before the release

Work on a branch (for example `chore/release-x.y.z`) and open a pull request, like any other change.

### Scope

- [ ] The milestone in [ROADMAP.md](../../ROADMAP.md) is met: each phase's exit criterion holds, with its tests and
      documentation, not just its code.
- [ ] No open issue that the maintainers consider a blocker for this release.

### Quality gates

Job names are as in the workflows. The required checks are set up as in
[`infra/github/README.md`](../../infra/github/README.md).

- [ ] `CI` is green on `main`: `Python 3.12`, `Python 3.13`, `PostgreSQL schema (PostGIS 3.4)`, `Web (Node 22 ...)` and
      `Docker build (api · web)`.
- [ ] `Lint`, `Security` (both CodeQL languages, pip-audit, npm audit, gitleaks) and `Docs` (markdownlint, link check)
      are green. If the plugin changed, `QGIS plugin` is green too.
- [ ] `ATLAS_ENV=production ATLAS_ALLOW_PENDING_PARAMETERS=false python3 -m pytest tests/data-quality -q` passes. Read
      [what this gate does and does not prove](adding-a-species-or-parameter.md#tests-and-the-production-gate): it
      asserts that production refuses pending parameters, so it needs a deliberate update when the last one is
      verified.
- [ ] `ATLAS_ENV=production python3 -m pytest tests/data-quality/test_tree_age_rules.py -k production -q` passes and
      its warning lists the withheld tree-age rules. Put them in the release notes.
- [ ] Locally, `make test` and `make lint` pass, and `docker compose up --build` starts a working stack in demo mode.
- [ ] If `data/schemas/schema.sql` changed, the schema job ran the smoke test and the constraint script
      ([testing the PostgreSQL schema](testing.md#testing-the-postgresql-schema)), and the revision in the file header
      and the `schema_version` row are raised.

### Numbers and policy (production release)

- [ ] The parameters listed by the snippet in
      [species and parameters](adding-a-species-or-parameter.md#verifying-a-pending-parameter) contain no `pending`
      entry that a default calculation uses; the reviewer who verified each one is named in the CHANGELOG.
- [ ] `config/market/carbon-price-scenarios.yaml` was reviewed against the sources named in its own `basis_note`;
      `as_of` and the references are updated. The prices stay illustrative.
- [ ] Each `config/policies/<ISO>.yaml` was re-read against the current notifications by the region's reviewer, and its
      statuses and references are current. Open questions are listed in
      [policy references](../research/policy-references.md).
- [ ] Each rule in `config/tree-age/rules.yaml` is `verified`, or is listed in the notes as withheld, and its sources
      were opened again if they are more than a year old. `updated` and `version` are raised.
- [ ] The release notes say which regions' rules were last checked and when.

### Map and imagery

- [ ] `config/imagery/providers.yaml` lists only providers whose license, attribution and key requirement are in
      [`MAP_LICENSES.md`](../licensing/MAP_LICENSES.md), and the attribution strings match.
- [ ] The default basemap is not the MapLibre demo style. `VITE_BASEMAP_STYLE_URL` or `VITE_BASEMAP_PMTILES_URL` points
      at a basemap you may use, and `ATLAS_BASEMAP_ORIGINS` and `ATLAS_EXTRA_IMG_SRC` allow exactly its hosts
      ([setup](setup.md#web-container-run-time)).

### Licensing and privacy

- [ ] The "Checked" column in [`DATA_LICENSES.md`](../licensing/DATA_LICENSES.md) is current for every source, and
      [`ATTRIBUTION.md`](../licensing/ATTRIBUTION.md) matches what the API serves at `GET /api/v1/attribution`.
- [ ] The dependency license inventories are regenerated with the commands in
      [`THIRD_PARTY.md`](../licensing/THIRD_PARTY.md#regenerating-the-inventories) and attached to the release; no
      disallowed license appears. The `NOTICE` file is added with the first release.
- [ ] The [threat model](../privacy/threat-model.md) table was reviewed (it is reviewed at every minor release), and
      each row's status is current. Spot-check that logs hold no coordinates, public views are generalized, and
      `/explain` and the agent team's optional language model get derived indicators only.

### Documentation, fixtures and the plugin

- [ ] The API contract and schemas match the code.
- [ ] Sample data is regenerated, so the offline fallback matches the API:

  ```bash
  python3 scripts/make_sample_responses.py
  python3 scripts/make_sample_tree_age.py --check     # without --check it rewrites the files
  python3 scripts/make_sample_imports.py --check      # same
  (cd apps/web && npm run fixtures:demo)
  ```

- [ ] Screenshots under `docs/images/screenshots/` are refreshed if the interface changed
      ([how they are made](../images/README.md)).
- [ ] [Setup](setup.md) works from a clean clone.
- [ ] If the plugin is released together, `metadata.txt` and `version.py` carry the same version (the packaging script
      refuses to build otherwise), and the `changelog=` entry in `metadata.txt` is added.

### Before the first public release only

- [ ] The placeholders are replaced: `<org>` in `CITATION.cff`, `CHANGELOG.md` (compare links), `.lychee.toml` and
      `infra/docker/Dockerfile.web`; the contact addresses `security@example.org` in `SECURITY.md` and
      `conduct@example.org` in `CODE_OF_CONDUCT.md`; the `email` and URLs in the plugin's `metadata.txt`; the
      repository and discussion links in `.github/ISSUE_TEMPLATE/config.yml`; and the team handles in
      [`.github/CODEOWNERS`](../../.github/CODEOWNERS), whose header explains why a handle that does not exist makes
      GitHub ignore the line.

## Checklist: the version bump

The version appears in several places. Change them together, in one commit, and regenerate the fixtures that echo them:

| Place | What |
| --- | --- |
| `apps/api/pyproject.toml` and `apps/api/app/__init__.py` | API version (reported by `GET /api/v1/health` and in provenance) |
| `packages/{carbon-engine,geo-engine,policy-engine,report-engine,agent-framework}/pyproject.toml` and each package's `__init__.py` | Engine and agent-framework versions |
| `integrations/pyproject.toml` and `integrations/atlas_integrations/__init__.py` | Adapter package |
| `integrations/qgis-plugin/agricarbon_atlas_qgis/metadata.txt` (`version=`, `changelog=`) and `version.py` | QGIS plugin, if released together. The two versions must match |
| `apps/web/package.json` (and the lock file via `npm install`) | Web app |
| `config/**/version:` keys | Only those whose content changed |
| `data/schemas/schema.sql` | Header revision and the `schema_version` insert, only if the schema changed |
| `CITATION.cff` | `version` and `date-released` |
| `CHANGELOG.md` | Rename `[Unreleased]` to `[x.y.z]` with the date, add a fresh `[Unreleased]`, update the compare links at the bottom |
| `SECURITY.md` | The supported-versions table |
| `data/sample/responses/`, `apps/web/public/demo/` | Regenerate; they contain the version |

Search for the old version string to catch anything missing, and ignore generated files and lock files:

```bash
grep -rn --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude=package-lock.json "0\.1\.0" .
```

## Cutting the release

1. Merge the release pull request into `main` with a squash or rebase merge (history stays linear), after the required
   reviews and checks. Commits carry a DCO sign-off (`git commit -s`).
2. Tag the merge commit and push the tag. A signed tag is recommended:

   ```bash
   git tag -s vX.Y.Z -m "AgriCarbon Atlas X.Y.Z"
   git push origin vX.Y.Z
   ```

3. Create the GitHub release from the tag. Use the CHANGELOG section as the notes, and attach the license inventories.
   For a development release, state in the first line that it is **not** a production release and list the `pending`
   parameters and tree-age rules. Credit contributors and reporters (reporters of security issues unless they prefer to
   stay anonymous).
4. If the plugin is part of the release, open the `QGIS plugin` workflow run for the tagged commit, download the
   artifact `agricarbon-atlas-qgis-plugin` (it expires after 30 days), check that the file name carries the release
   version, and attach the ZIP to the GitHub release. The plugin is licensed GPL-2.0-or-later and stays in its own
   folder ([why](../licensing/THIRD_PARTY.md#the-qgis-plugin-and-the-gpl)). Publishing it elsewhere is a separate
   decision that this repository does not automate.
5. Build the images from the tag if you publish them:

   ```bash
   docker build -f infra/docker/Dockerfile.api -t agricarbon-atlas-api:X.Y.Z .
   docker build -f infra/docker/Dockerfile.web -t agricarbon-atlas-web:X.Y.Z .
   ```

   Where to push is a deployment decision. Never bake secrets into an image. `VITE_*` values are compiled into the web
   image, so build it for the target environment.
6. Verify from the tag: a clean `docker compose up --build` in demo mode, `GET /api/v1/health` reporting the new
   version, the web container answering `/healthz`, and one plot taken through to a report.
7. Announce in the repository (Discussions, and the changelog) with a pointer to the migration notes.

## Deploying a production release

The [reference infrastructure notes](../../infra/terraform/README.md) list what a deployment needs. The settings that
make it production (the full list is in [setup](setup.md#environment-variables)):

| Setting | Value | Why |
| --- | --- | --- |
| `ATLAS_ENV` | `production` | Refuses estimates that use a `pending` parameter and withholds `pending` tree-age rules |
| `ATLAS_MODE` | `live` | Real data through the adapters |
| `ATLAS_API_KEYS` | Non-empty | Mutating endpoints require `X-API-Key`. Read endpoints stay open, so keep the API behind a gateway if it holds real farm boundaries |
| `ATLAS_CORS_ORIGINS` | The web origin only | The API sets no cookies, so list origins instead of using `*` |
| `NOMINATIM_USER_AGENT` | A real contact string | Required by the Nominatim usage policy; the adapter refuses an empty one |
| `ATLAS_REPOSITORY` and `DATABASE_URL` | `postgres`, with the schema applied | Memory storage is lost on restart |
| `ATLAS_AGENT_REASONER`, `ATLAS_EXPLAIN_PROVIDER` | `template`, unless you set up a language model on purpose | A model only rephrases agent sentences from redacted facts and gets derived indicators, never coordinates |
| Web container | `ATLAS_API_ORIGIN`, `ATLAS_BASEMAP_ORIGINS`, `ATLAS_EXTRA_IMG_SRC` | The Content-Security-Policy is built from them at start-up. A host that is not listed is blocked by the browser |
| Edge | TLS, HSTS, rate limiting | The API's own limit is 60 requests per minute per client |

**Database.** `docker-compose.yml` runs `schema.sql` once, on the first start of an empty data directory. For an
existing database, take a backup and apply the file by hand with the `psql` command in the versioning section. It
upgrades revision 0.1 databases in place. Do it before you start the new API version.

Confirm that the Open-Meteo free tier and any other non-commercial terms apply to your use, or take a subscription
([DATA_LICENSES.md](../licensing/DATA_LICENSES.md)). Check the terms of every imagery provider you enable
([MAP_LICENSES.md](../licensing/MAP_LICENSES.md)): some layers are for display only.

## After the release

- Open the next `[Unreleased]` section and keep adding entries as changes merge.
- If a released parameter or rule is found to be wrong, publish a patch release that says so plainly, naming the file,
  the old and corrected value and the affected versions. Stored estimates keep the parameter and model versions they
  were computed with in their provenance, so users can tell which ones are affected. Downgrade the parameter or rule to
  `pending` first if you are unsure.

## Security releases

Reports arrive through private vulnerability reporting ([SECURITY.md](../../SECURITY.md)): acknowledge within 3
business days, triage within 10, and aim to publish within the 90-day coordinated-disclosure window. Develop the fix
privately (a GitHub security advisory with a temporary private fork), release as a patch version of every supported
version, credit the reporter unless they prefer otherwise, and update the supported-versions table. A leak of exact farm
geometry is treated like remote code execution.

Next: [contributing](../../CONTRIBUTING.md) or [troubleshooting](troubleshooting.md).
