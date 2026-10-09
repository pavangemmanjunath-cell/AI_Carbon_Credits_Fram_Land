# GitHub repository settings

Settings that cannot be expressed as files in the repository are documented
here so that a new administrator can reproduce them. Workflows, templates,
labels and Dependabot live under [`.github/`](../../.github/).

## Branch protection for `main`

Configure a ruleset (or classic branch protection) on `main` with:

| Setting | Value | Why |
|---|---|---|
| Require a pull request before merging | on, 1 approving review | Lazy consensus per [GOVERNANCE.md](../../GOVERNANCE.md) |
| Dismiss stale approvals on new commits | on | Approval applies to what was reviewed |
| Require review from Code Owners | on (once CODEOWNERS exists) | Carbon and policy changes need domain review |
| Require status checks to pass | on, strict (branch up to date) | See required checks below |
| Require conversation resolution | on | Reviewer questions are answered, not ignored |
| Require signed commits | recommended | DCO sign-off is required; signature is extra assurance |
| Require linear history | on | Squash or rebase merges keep `CHANGELOG.md` tidy |
| Block force pushes and deletions | on | |
| Restrict who can push | maintainers team | Everyone else works through forks |

Allow administrators to bypass only in an emergency, and record any bypass
in the pull request thread.

## Required status checks

The job names below are the `name:` values in the workflows; GitHub matches
on them.

| Workflow | Required check |
|---|---|
| `CI` | `Python 3.12 (ruff · mypy · pytest)` |
| `CI` | `Python 3.13 (ruff · mypy · pytest)` |
| `CI` | `Web (Node 22 · lint · typecheck · vitest · build)` |
| `CI` | `Docker build (api · web)` |
| `Lint` | `Prettier check · ESLint (apps/web)` |
| `Lint` | `Ruff format --check (Python)` |
| `Lint` | `yamllint (config/ and workflows)` |
| `Security` | `CodeQL (python)`, `CodeQL (javascript-typescript)`, `pip-audit (Python dependencies)`, `npm audit (web dependencies)`, `gitleaks (secret scanning)` |
| `Docs` | `markdownlint`, `Link check (lychee)` (only when Markdown changed) |

`Docs` runs on Markdown changes only; mark it required with the "required
on matching paths" behaviour of rulesets, or accept that it is skipped for
code-only pull requests.

## Suggested CODEOWNERS

Create `.github/CODEOWNERS` once maintainers exist. The suggested mapping
mirrors the label rules in [`.github/labeler.yml`](../../.github/labeler.yml):

```text
# Default owner for everything
*                                   @<org>/maintainers

# Numbers people act on: require domain review
/config/species/                    @<org>/carbon-reviewers
/config/methodologies/              @<org>/carbon-reviewers
/packages/carbon-engine/            @<org>/carbon-reviewers
/config/policies/IN.yaml            @<org>/policy-india
/config/policies/US.yaml            @<org>/policy-usa
/config/policies/EU.yaml            @<org>/policy-eu
/docs/regions/IN/                   @<org>/policy-india
/docs/regions/US/                   @<org>/policy-usa
/docs/regions/EU/                   @<org>/policy-eu
/config/market/                     @<org>/policy-eu @<org>/policy-usa @<org>/policy-india

# Privacy boundary
/docs/privacy/                      @<org>/privacy-reviewers
/apps/api/app/routes/explain.py     @<org>/privacy-reviewers

# Licensing metadata
/docs/licensing/                    @<org>/maintainers

# Supply chain
/.github/workflows/                 @<org>/maintainers
/infra/                             @<org>/maintainers
/requirements.txt                   @<org>/maintainers
/apps/web/package.json              @<org>/maintainers
/apps/web/package-lock.json         @<org>/maintainers
```

Teams are placeholders; a single-maintainer project can point every line at
one handle and still benefit from the review requirement being explicit.

## Repository features

- **Private vulnerability reporting**: enabled (Settings → Code security),
  referenced from [SECURITY.md](../../SECURITY.md).
- **Dependabot alerts and security updates**: enabled; version updates come
  from [`.github/dependabot.yml`](../../.github/dependabot.yml).
- **Secret scanning with push protection**: enabled.
- **Discussions**: enabled, with categories *Q&A*, *Ideas*, *Show and tell*,
  *Regions* (IN / US / EU) and *Research*.
- **Issues**: blank issues disabled; templates under
  [`.github/ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/).
- **Labels**: created from [`.github/labels.yml`](../../.github/labels.yml)
  (for example with `crazy-max/ghaction-github-labeler` or the `gh label`
  CLI).
- **Actions permissions**: allow actions from GitHub and verified creators;
  default `GITHUB_TOKEN` permission *read*; workflows request write scopes
  explicitly (`security-events: write` for CodeQL, `pull-requests: write`
  for the labeler).
- **Merge options**: squash and rebase enabled, merge commits disabled;
  automatically delete head branches.
- **Environments**: `staging` and `production` with required reviewers for
  `production` deployments; production secrets exist only there.

## Secrets used by workflows

| Secret | Used by | Required? |
|---|---|---|
| `GITHUB_TOKEN` | all (automatic) | yes |
| `GITLEAKS_LICENSE` | `Security` / gitleaks | only for organization accounts |

No deployment credentials are stored at repository level; deployments use
environment-scoped secrets or OIDC federation to the cloud provider.
