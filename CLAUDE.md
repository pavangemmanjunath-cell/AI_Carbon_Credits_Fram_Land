# CarbonCreditBuy — development rules for AI-assisted contributions

These rules bind every contribution, human or AI-assisted. They exist because
this software produces numbers that farmers, researchers and reviewers may
act on.

## Mission

Build an open-source geospatial platform that helps landowners, farmers and
researchers understand tree cover, agricultural conditions and potential
carbon benefits — and what evidence they still need to pursue a recognised
carbon or environmental programme.

## Core principles (non-negotiable)

1. **Estimates are not carbon credits.** Never present an uncertified result as
   certified. Every carbon output carries `certified: false` until a
   registry-issued serial number exists.
2. **No business logic in UI components.** React components render; engines
   calculate; adapters fetch. Policy rules live in `config/policies/`, never in
   `if` statements inside components.
3. **No carbon values hard-coded.** Parameters live in `config/` with a
   `source`, `source_table`, `unit` and `verification_status`.
4. **Every model cites a methodology.** A model without a documented equation
   source does not ship.
5. **Every external dataset has licensing metadata** in
   `docs/licensing/DATA_LICENSES.md` and in the adapter's `provenance()`.
6. **Every external API has an adapter** under `integrations/` with README,
   source, license, attribution, rate limits, caching and failure handling.
   Endpoints come from environment variables, never literals in app code.
7. **Configuration is regional.** `config/regions/<ISO>.yaml` drives units,
   currency, languages, climate defaults and programme links. ISO 3166-1
   alpha-2 codes are the primary key; calling codes (+91) are UX aliases only.
8. **All results carry provenance** — dataset versions, acquisition dates,
   model and parameter versions, generation time.
9. **Carbon outputs include uncertainty** — `low`, `central`, `high`, `unit`,
   `confidence`, `model`, `methodology`.
10. **Tests are required for every calculation** (pytest for Python, Vitest for
    TypeScript). A parameter flagged `verification_status: pending` must fail a
    production-mode data-quality test.
11. **Privacy by default.** Exact polygons are private; public views use
    generalized centroids. Coordinates are never sent to an LLM; the optional
    AI explanation receives derived indicators only. Never log coordinates.
12. **Prefer deterministic calculations over LLM calculations.** An LLM never
    computes a carbon number.
13. **Never invent** environmental data, policy eligibility, carbon factors or
    scientific equations. Where information is missing, create a typed
    interface or TODO that names the authoritative source required.

## Supported regions (MVP)

`IN` India · `US` United States · `EU` European Union (member states by ISO
code, e.g. `DE`, `FR`, `ES`, `IT`, mapped to `EU` rules).

## Stack

- Frontend: React 19 + Vite + TypeScript, MapLibre GL JS (PMTiles basemap, raster
  satellite/aerial imagery, GeoJSON layers — the map stays a flat 2D map for
  simplicity; on the owner's request (2026-10-11) the Simulation page adds an
  optional, lazy-loaded 3D land view with three.js + React Three Fiber that only
  renders engine and config values), TanStack Query, Zustand, i18next (en, hi, kn,
  de, fr, es), Tailwind CSS, recharts, terra-draw, Turf, Vitest, Playwright.
  All data exchange is JSON (no DuckDB; see ADR-0002).
- Backend: Python 3.12+, FastAPI, Pydantic v2, Shapely, PyProj, NumPy,
  Rasterio, pystac-client, httpx, PyYAML, laspy (+lazrs) for point clouds,
  defusedxml for KML, pytest, ruff, mypy.
- Agents: `packages/agent-framework` (`carboncreditbuy_agents`) — agents, tools, plans,
  blackboard, guardrails; deterministic templates by default; an optional
  OpenAI-compatible LLM may only rephrase text from redacted facts (ADR-0006).
- QGIS plugin: `integrations/qgis-plugin` (GPL-2.0-or-later, calls the API).
- Storage: PostgreSQL + PostGIS (optional; in-memory repository for demo mode),
  S3-compatible object storage for PMTiles and cached rasters.
- Geospatial formats: GeoJSON, STAC, COG, PMTiles, Zarr (export).

## Terminology

- Say "estimated annual carbon removal (tCO₂e/yr)", never "ESG amount".
- Show three separated values: environmental benefit, indicative carbon value
  (scenario, not a credit) and other farm income. Never sum them.
- India: Green Credits (GCP) and carbon credits (CCTS) are separate mechanisms.
- EU: CRCF certification is required; an estimate is never automatically
  certifiable.

## Required tests

`make test` runs pytest (all Python packages and the API), Vitest and
TypeScript checks. CI also runs ruff, mypy, eslint, prettier, CodeQL,
dependency and secret scanning, Docker build and a docs-link check.

## Pull request rule

Every change documents: why · inputs · outputs · data source · licensing
impact · privacy impact · testing performed. Use the PR template.

## Implementation order

1 scaffold → 2 MapLibre + PMTiles → 3 plot drawing + persistence →
4 ESA WorldCover analysis → 5 Sentinel-2 STAC integration → 6 NDVI/NDMI + cube →
7 tree inventory → 8 carbon-engine v0.1 → 9 IN/US/EU policy engine →
10 report → 11 privacy controls → 12 tests and documentation →
13 (v0.2) imports + tree detection, tree-age rules, imagery providers,
agent framework, QGIS plugin.
Do not attempt all phases simultaneously.

## Agents (v0.2)

- Agents describe and route; engines calculate. An agent never invents a number:
  every figure in a message comes from a tool call into an engine or service.
- Every message names its agent, its tools and its evidence (who said what).
- The Review agent's guardrails must pass (not a credit, uncertainty shown,
  provenance recorded, no coordinates in any message, pending parameters
  flagged, values kept apart) before a run is reported as completed.
- Redact before any LLM call; keep the template text when the LLM output adds
  or changes a number.
