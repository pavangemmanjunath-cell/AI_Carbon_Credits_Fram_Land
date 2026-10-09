# Security Policy

AgriCarbon Atlas handles two things that deserve protection: the exact
geometry of farm plots (which identifies a person's land and, often, the
person) and the integrity of the numbers the platform publishes. We treat a
leak of private geometry with the same seriousness as remote code execution.

## Reporting a vulnerability

Please **do not** open a public issue for security or privacy problems.

Use GitHub's private vulnerability reporting on the repository
(*Security → Report a vulnerability*) or e-mail
**security@example.org** (replace with the project's address once the
organization is created). If you prefer encryption, ask for the current PGP
key in your first message.

Include, as far as you can:

- the version or commit affected and the mode (`demo` or `live`);
- steps to reproduce, ideally as a request/response pair or a failing test;
- the impact you believe it has (for example "exact polygon of another
  user's plot is returned to a non-owner");
- whether the problem is already public.

You will receive an acknowledgement within **3 business days** and a
triage decision (accepted, needs more information, or not a vulnerability)
within **10 business days**. We ask for up to **90 days** of coordinated
disclosure from acknowledgement; if a fix is ready earlier we publish
earlier, and if we need longer we will say so and explain why. We credit
reporters in the release notes unless they prefer to stay anonymous.

## Supported versions

| Version | Status | Security fixes |
|---|---|---|
| `main` branch | development | yes, as regular commits |
| 0.2.x | pre-release (current) | yes |
| 0.1.x | superseded pre-release | no — upgrade to 0.2.x |

Once 1.0.0 is released, the latest minor release of the current major
version and the final minor release of the previous major version receive
fixes for twelve months. This table is updated with every release
([release-process.md](docs/developer-guide/release-process.md)).

## Scope

In scope:

- The FastAPI back end (`apps/api`) and the engines under `packages/`.
- The web application (`apps/web`), including the map, cube, simulation
  lab and report views.
- Adapters under `integrations/` (for example SSRF through a configurable
  endpoint, or credentials leaking into logs or provenance blocks).
- Container images and workflows under `infra/` and `.github/`.
- **Privacy of farm geometry.** Any path by which an exact polygon, exact
  centroid, raw coordinates or a sub-0.05° location can reach a party other
  than the plot owner is in scope: API responses, logs, error messages,
  reports, cached rasters, shareable links, telemetry, or the optional
  `/explain` provider. See
  [docs/privacy/privacy-design.md](docs/privacy/privacy-design.md) for what
  the system promises.
- Integrity of published numbers: a way to make the API return a carbon
  estimate with `certified: true`, drop the uncertainty range or disclaimer,
  or bypass the production-mode rejection of `pending` parameters.

Out of scope (please report these to the respective projects):

- Vulnerabilities in third-party services we call (Nominatim, Open-Meteo,
  STAC catalogs, SoilGrids, USDA NASS, data.gov.in).
- Rate-limit exhaustion of public upstream APIs caused by your own
  deployment's configuration.
- Issues that require a compromised host, a malicious maintainer, or
  physical access.
- Findings from automated scanners without a demonstrated impact.

## Hardening defaults you should know about

- `ATLAS_API_KEYS` enables mandatory `X-API-Key` on mutating endpoints;
  deployments exposed to the Internet should set it.
- `ATLAS_ALLOW_PENDING_PARAMETERS` must be `false` in production
  (`ATLAS_ENV=production`), otherwise unverified parameters are allowed.
- `ATLAS_EXPLAIN_PROVIDER=llm` is opt-in and still receives only derived
  indicators; the request schema rejects coordinate-bearing keys.
- Coordinates are never logged. If you find a log line containing them,
  that is a vulnerability.
- The web image ships a Content Security Policy
  ([infra/docker/nginx.conf](infra/docker/nginx.conf)); report any need to
  loosen it rather than disabling it.

## Dependency and secret scanning

CI runs CodeQL (Python and JavaScript), `pip-audit`, `npm audit` and
gitleaks on every push and weekly ([.github/workflows/security.yml](.github/workflows/security.yml));
Dependabot opens weekly update pull requests. If you accidentally commit a
secret, rotate it first and then tell us; removing it from history alone is
not enough.
