# Threat model

A brief STRIDE analysis of AgriCarbon Atlas, focused on the two assets
that matter most: the confidentiality of plot geometry and the integrity
of the numbers the platform publishes. It is a living document; findings
reported under [SECURITY.md](../../SECURITY.md) update it.

## Assets and trust boundaries

| Asset | Why it matters |
|---|---|
| Exact plot geometry, exact centroid, cached raster windows, cubes | Identify a person's land |
| Inventory and estimates | Reveal assets and plans; integrity affects decisions |
| Configuration (`config/`) | Changing a parameter or a rule changes every result |
| API keys, database and storage credentials, provider keys | Access to all of the above |
| The published container images and workflows | Supply chain |

Trust boundaries: browser ↔ API; API ↔ repository and caches; API ↔
upstream data providers; API ↔ optional LLM provider; CI ↔ registries;
operator ↔ production.

## STRIDE table

| Threat | Example | Affected asset | Mitigation | Status |
|---|---|---|---|---|
| **S**poofing | Caller presents another user's plot id | Geometry | Plot ids are opaque (6–12 random characters); owner scoping on every read of `geometry`/`centroid`/`cube`; `X-API-Key` when `ATLAS_API_KEYS` is set; deployments add authentication at the edge | implemented (ids, key); auth layer deployment-specific |
| Spoofing | Forged upstream response (e.g. MITM to a STAC endpoint) | Integrity of analysis | HTTPS only for every provider URL; certificate verification never disabled; provenance records the endpoint used | implemented |
| **T**ampering | Pull request changes a growth increment without a source | Integrity of estimates | Config schema requires `source`/`unit`/`verification_status`; data-quality tests; CODEOWNERS review by domain reviewers; branch protection | implemented (tests), process ([infra/github](../../infra/github/README.md)) |
| Tampering | Client sends `certified: true` or a modified estimate to the report endpoint | Report integrity | Reports are rendered from server-side stored estimates by id; `certified` is a schema constant `false`; request bodies for reports carry ids only | implemented |
| Tampering | Dependency or action compromised | Supply chain | Pinned Python requirements, `npm ci` with lockfile, Dependabot, pip-audit, npm audit, CodeQL, gitleaks; actions pinned to major versions (pin to SHAs before 1.0) | implemented in CI; SHA pinning planned |
| **R**epudiation | Operator cannot show that a plot was deleted | Compliance | Deletion event log with plot id and timestamp; backup replay procedure ([data-retention.md](data-retention.md)) | planned (Phase 11) |
| Repudiation | A parameter's `verified` status cannot be traced to a reviewer | Integrity | `source` field records table cell; pull request records reviewer; CHANGELOG entry | process |
| **I**nformation disclosure | Coordinates in logs, error messages or crash reports | Geometry | Redaction filter with tests; RFC 7807 errors never echo geometry; no third-party error trackers by default | implemented (tests required by CLAUDE.md) |
| Information disclosure | Non-owner receives `geometry` through a list endpoint or report | Geometry | `GET /plots` returns only the caller's plots; shared reports use `public_centroid` unless the owner opts in; e2e privacy spec | implemented / e2e planned |
| Information disclosure | `/explain` forwards coordinates to an LLM | Geometry | Schema rejects location keys at any depth; provider receives indicators only; `privacy_note` in response; default provider is a template | implemented |
| Information disclosure | Cached raster windows or cubes readable from a public bucket | Geometry | Cache bucket private; pre-signed URLs only for reports; lifecycle TTLs | deployment |
| Information disclosure | Upstream provider logs the bounding box with the server IP | Location (not identity) | Documented and disclosed; caching reduces repeats; self-hosting option for strict deployments | accepted, documented |
| Information disclosure | Share link leaks plot location | Geometry | `/simulate` share params contain country, species, trees, year, horizon only | implemented |
| **D**enial of service | Expensive `/analyze` requests flood upstream APIs or exhaust CPU | Availability; provider goodwill | 60 req/min default rate limit; per-adapter timeouts; cache; plot size cap 10 000 ha and 500 vertices; Nominatim interval | implemented |
| Denial of service | Pathological polygon (self-intersection, huge vertex count) | Availability | Shapely validity check; vertex and area limits before any raster read | implemented |
| **E**levation of privilege | SSRF through a configurable endpoint variable | Internal network | Endpoints come from environment only (never request parameters); outbound allow-list recommended at the network layer; no user-supplied URLs are fetched | implemented / deployment |
| Elevation of privilege | Container breakout | Host | Non-root API container (uid 10001), read-only filesystem except cache/report volumes recommended, minimal base images, no shell tools beyond the standard library | implemented / deployment |
| Elevation of privilege | Malicious GeoJSON upload executes in the browser | Browser | Files parsed as data with a strict parser; CSP forbids inline scripts; no `dangerouslySetInnerHTML` with user content | implemented (CSP), review rule |

## Out of scope

Compromise of the operator's own infrastructure, physical access,
malicious maintainers, and vulnerabilities in upstream providers are out
of scope for the software's threat model and are addressed by deployment
practice and governance ([GOVERNANCE.md](../../GOVERNANCE.md)).

## Review cadence

The table is reviewed at every minor release and whenever a new adapter,
storage backend or sharing feature is added. Each row's *Status* must be
`implemented`, `planned (phase)`, `deployment` (the deployer's
responsibility, documented) or `accepted` with a reason.
