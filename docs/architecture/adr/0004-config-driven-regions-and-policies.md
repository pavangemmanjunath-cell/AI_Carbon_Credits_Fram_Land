# ADR-0004: Regions, species, methodologies and policy rules are configuration, not code

- **Status:** accepted
- **Date:** 2026-10-04
- **Deciders:** project lead, back-end engineer

## Context

The platform supports India, the United States and the European Union
from the first release, with more regions expected. Each region differs
in units, currency, languages, data sources, climate defaults and, above
all, in the programmes that matter: the Green Credit Programme and the
CCTS in India; COMET-Farm, voluntary registries and NRCS programmes in the
US; the CRCF and the CAP in the EU. Programme rules change by notification
and delegated act, often several times a year. Species parameters come
from tables that must be verified cell by cell. If this knowledge were
spread through Python conditionals and React components, every regulatory
update would be a code change reviewed by people who may not know the
domain, and the provenance of a number would be lost in a diff.

## Decision

All regional, species, methodology, policy and market knowledge lives in
versioned YAML under `config/` and is loaded by engines at startup:

| File(s) | Content | Consumed by |
|---|---|---|
| `config/regions/<ISO>.yaml` | id, calling code (UX alias only), currency, locale, units, languages, map defaults, admin levels, climate default, data-source ids, programme list, other-income sources | API `/regions`, web app, policy engine (member-state mapping) |
| `config/species/species.yaml` | per-species group, regions, climate zones, densities, maturity, wood density, increment multiplier, allometry key — each numeric with `source` and `verification_status` | carbon engine, `/species` |
| `config/methodologies/ipcc-2006-tier1.yaml` | constants, root-to-shoot table, growth increments by climate zone, allometric equations, model assumptions, uncertainty fractions | carbon engine |
| `config/methodologies/registry.yaml` | what the platform can *reference* (guidelines, standards, government methodologies, frameworks, tools) with status and URLs | `/methodologies`, reports |
| `config/policies/<ISO>.yaml` | programmes with `rules` (`when` → `status`, `reason`), `requirements`, `references`, `distinct_from` | policy engine |
| `config/market/carbon-price-scenarios.yaml` | illustrative low/reference/high prices per region with `as_of`, references and `verification_status` | `/market-scenario`, `/simulate` |

Rules of the scheme:

1. ISO 3166-1 alpha-2 codes are the primary key; EU member states are
   listed in `EU.yaml` and resolve to EU rules while keeping their own code
   for data lookups and languages. Calling codes (+91) are UX aliases.
2. Every numeric parameter is an object with `value`, `source`, `unit` and
   `verification_status`; bare numbers are rejected by the data-quality
   tests.
3. Every policy rule has `references` with URLs; a rule without a source
   does not load.
4. Engines contain no `if country == …`; UI components contain no policy
   conditions. Adding a region means adding files, not branches
   ([../../developer-guide/adding-a-region.md](../../developer-guide/adding-a-region.md)).
5. Configuration is versioned (`version:` keys) and the version appears in
   every result's `provenance`.

## Consequences

Positive:

- Domain reviewers can propose and review changes in the format they
  think in (programme, rule, source), via the dedicated issue templates.
- Provenance is structural: the same object that holds the value holds its
  source and status.
- Tests over configuration (`tests/data-quality/`) catch missing sources,
  inconsistent densities and pending parameters in production.
- Regions can be added by contributors who never touch Python or
  TypeScript.

Negative:

- YAML has no types; the loaders validate against schemas and fail fast,
  which adds code. Worth it.
- Complex rule logic is harder to express than in code. The `when` clause
  is intentionally limited (activity, and later land-use and size
  predicates); anything beyond that is a sign the programme needs a
  domain-specific assessment, which is what the `requires_assessment`
  statuses say.
- A screening is only as current as the configuration. Each file carries
  the dates of the documents it cites, and release notes list policy
  changes.

## Alternatives considered

- **Rules in Python modules per country.** Rejected: provenance lost in
  code, review requires engineers, country branches proliferate.
- **A rules engine with a DSL (e.g. Open Policy Agent).** Considered;
  deferred because the rule shapes needed are simple and an extra runtime
  would complicate deployment. Could be revisited for the `when` grammar.
- **A database of rules edited through an admin UI.** Rejected for now:
  git history, pull-request review and CI tests are the audit trail we
  want.

## Revisit when

Rule complexity outgrows the `when` grammar in more than one region, or
when non-technical reviewers need to update rules without pull requests.
