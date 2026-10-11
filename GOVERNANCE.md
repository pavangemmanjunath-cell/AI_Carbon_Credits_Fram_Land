# Governance

CarbonCreditBuy is an open-source project licensed under Apache-2.0. This
document describes how decisions are made today and how the structure is
expected to evolve as the contributor base grows. It is deliberately
lightweight; the project is young and a heavyweight process would slow it
down without protecting anyone.

## Roles

| Role | Who | Responsibilities |
|---|---|---|
| Project lead | Pavan Manjunath (original author; see [AUTHORS.md](AUTHORS.md)) | Sets direction and roadmap, has final say on disputed technical decisions, administers the GitHub organization, releases versions. |
| Maintainers | Appointed by the project lead from active contributors | Review and merge pull requests in their area, triage issues, uphold [CLAUDE.md](CLAUDE.md), rotate release duty. |
| Domain reviewers | Volunteers with recognized expertise (forestry, remote sensing, carbon policy for IN / US / EU, privacy law) | Review changes to `config/`, `packages/carbon-engine`, `packages/policy-engine` and `docs/regions/`; their approval is required for changes to carbon parameters or policy rules. |
| Contributors | Anyone who has had a change merged | Listed in [CONTRIBUTORS.md](CONTRIBUTORS.md) for sustained contributions. |

Maintainership is earned by sustained, high-quality contribution and is
recorded in `.github/CODEOWNERS` once the repository adopts it (see
[infra/github/README.md](infra/github/README.md)). Maintainers who are
inactive for twelve months are moved to emeritus status; they can return at
any time by asking.

## Decision making

Most decisions are made by **lazy consensus** on a pull request or issue: a
proposal that receives no objection from a maintainer within seven days, and
at least one approving review, may be merged. Larger changes follow a
documented path:

1. **Architecture decisions** are recorded as ADRs under
   [docs/architecture/adr/](docs/architecture/adr/). A new ADR is opened as a
   pull request, discussed for at least seven days, and accepted when the
   project lead and a majority of active maintainers approve.
2. **Carbon-model and policy-rule changes** additionally require approval
   from a domain reviewer for the affected area, because they change numbers
   that users may act on. The approval is recorded in the pull request, and
   the parameter's `verification_status` is updated to `verified` only by the
   reviewer who checked the source table.
3. **Breaking API changes** require an update to
   [docs/architecture/api-contract.md](docs/architecture/api-contract.md) in
   the same pull request and a note in [CHANGELOG.md](CHANGELOG.md).

If consensus cannot be reached, the project lead decides and documents the
reasoning in the thread. Decisions can be revisited when new evidence
appears; a revisited ADR supersedes the old one rather than editing it.

## Scope guardrails

Some decisions are settled by the project's mission rather than by vote. The
project will not:

- present an uncertified estimate as a carbon credit, in code, UI or
  documentation;
- compute carbon numbers with a language model;
- add a data source whose license or terms of use cannot be documented;
- weaken the privacy defaults (private polygons, generalized public
  centroids, no coordinates to third-party AI services).

A change that would cross one of these lines is out of scope regardless of
who proposes it; changing the guardrails themselves requires an ADR and a
public comment period of at least thirty days.

## Communication

- GitHub issues and pull requests are the primary record. Decisions made
  elsewhere (calls, chat) are summarized back into the relevant thread.
- Release announcements and roadmap updates are posted in the repository
  (see [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md)).
- Security reports follow [SECURITY.md](SECURITY.md) and are handled
  privately until a fix is available.

## Conflict of interest

Contributors who work for a registry, standards body, carbon-project
developer, data vendor or agency referenced by the platform are welcome, and
are asked to disclose the affiliation in the pull request when it touches
content about that organization. Disclosure is not a reason to reject a
contribution; undisclosed conflicts are.

## Changing this document

Governance changes are proposed as pull requests to this file, stay open for
at least fourteen days, and require approval from the project lead and a
majority of active maintainers.
