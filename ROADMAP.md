# Roadmap

Where CarbonCreditBuy stands and what comes next. **Releases V_1.1 and v1.1.1 were archived on 2026-10-11**
(latest DOI [10.5281/zenodo.23298816](https://doi.org/10.5281/zenodo.23298816)); 0.2.0 was the development milestone
before it. The steps after it have
no dates: each one waits for a source to be read, a reviewer to agree or a decision to be written down, and a date would
be a promise nobody can keep. What changed in each release is in the [changelog](CHANGELOG.md). The larger ideas, with
what is open today and the first step for each, are in [roadmap ideas](docs/community/roadmap-ideas.md).

## Versions at a glance

| Version | Theme | Status |
| --- | --- | --- |
| 0.1 | Foundations: the twelve build phases of [CLAUDE.md](CLAUDE.md), first pass | Built. It was not released on its own; it is the base of 0.2.0 |
| **0.2** | A simpler 2D map, an AI agent team, imports with tree detection, tree age, imagery providers and a QGIS plugin | **Delivered 2026-10-05** |
| Next | The [next steps](#next-steps) below | Not scheduled |
| 1.0 | Ready for production: a production release is possible, and `/api/v1` stops changing between minor versions | Not scheduled |

A production release needs every parameter that a default calculation uses to be verified or a documented assumption
([release process](docs/developer-guide/release-process.md#two-kinds-of-release)). Until 1.0 the API may change between
minor versions, and every change is recorded under **Changed** in the changelog with a migration note.

## What 0.2.0 delivered

| Area | What it gives you | Read |
| --- | --- | --- |
| A simpler web app | A flat 2D map with a left navigation: My land, Data, AI agents, Tree age, Simulation, Reports and Settings. Land is marked by drawing a boundary or a tree line, dropping a pin and typing the size, typing coordinates, or importing a file | [Mark your land](docs/user-guide/mark-your-land.md) |
| Import data | GeoJSON, KML, KMZ, CSV, LAS and LAZ files are read on the server and dropped. Only a derived record is kept: a boundary, tree counts, tree tops from point clouds, and a map preview | [Import data](docs/user-guide/import-data.md), [imports and detection](docs/architecture/imports-and-detection.md) |
| AI detected tree cover | Patches of dense green vegetation found in Sentinel-2 vegetation data, each with a heuristic confidence and a list of limitations. Every threshold is in `config/detection.yaml` and is marked as an assumption | [Detection](docs/architecture/imports-and-detection.md#3-detection-ai-detected-tree-cover-from-satellite-data) |
| Tree age | Carbon by tree age or by trunk girth, and 22 rules that treat existing trees differently by age and place. A rule that is still `pending` is flagged, and production mode withholds it | [Tree age](docs/user-guide/tree-age.md), [tree-age model](docs/architecture/tree-age-model.md) |
| Imagery for the Satellite view | Eight providers in `config/imagery/providers.yaml`, each with its licence, attribution, key requirement and whether automated analysis is allowed. The API lists them and the browser loads the tiles | [Satellite imagery](docs/user-guide/satellite-imagery.md), [integrations/imagery](integrations/imagery/README.md) |
| AI agents | Nine agents and three plans. The agents call the engines, so every number comes from an engine, and guardrails check each run. They are deterministic by default; a language model is optional and may only reword sentences | [AI agents](docs/user-guide/ai-agents.md), [agents guide](docs/agents/README.md), [ADR-0006](docs/architecture/adr/0006-agentic-framework.md) |
| QGIS plugin | Select a field polygon in QGIS, count the tree crowns of a segmentation layer inside it, and ask the API for a scenario estimate and the agent team's assessment. Experimental, GPL-2.0-or-later | [QGIS plugin](docs/user-guide/qgis-plugin.md), [plugin README](integrations/qgis-plugin/README.md) |

**Removed.** All 3D views went: three.js, React Three Fiber and deck.gl, the 4D cube and the tilt and terrain control.
The map is flat and north-up. The vegetation cube stays plain JSON and is drawn as a flat NDVI layer, and DuckDB-WASM
was
never added ([ADR-0002](docs/architecture/adr/0002-json-cube-no-duckdb.md)).

## The twelve build phases

[CLAUDE.md](CLAUDE.md) fixes the order in which the first version was built. A phase counts as done when its tests pass
in CI and its documentation exists, not when its code compiles.

| Phase | What it delivered | State |
| --- | --- | --- |
| 1 Scaffold | Monorepo (`apps/`, `packages/`, `integrations/`, `config/`), FastAPI skeleton, Vite + React + TypeScript app, shared API contract, `make` targets, CI with lint, type checks and tests, Docker images | Built |
| 2 MapLibre + PMTiles | Self-hosted vector basemap from a Protomaps PMTiles archive on S3-compatible storage, attribution, region switching (`IN`, `US`, `EU`) from `config/regions/`, no production dependency on `tile.openstreetmap.org` ([mapping architecture](docs/architecture/mapping-architecture.md)) | Built. 0.2 made the map flat and added imagery providers |
| 3 Plot drawing and persistence | terra-draw boundaries, validation (up to 500 vertices, 0.01 to 10,000 ha), `POST /plots` with an in-memory repository and optional PostGIS, a generalized `public_centroid` from day one | Built. 0.2 added pin and size, tree line, typed coordinates and file import |
| 4 ESA WorldCover analysis | Land-cover class shares per plot from WorldCover 2021 v200 (10 m) read as COGs, with provenance and attribution | Built |
| 5 Sentinel-2 STAC integration | STAC search (Earth Search or the Copernicus Data Space), cloud filtering with the scene classification layer, band reads limited to the plot's bounding box | Built |
| 6 NDVI, NDMI and the cube | Vegetation indices, a three-year monthly series with a trend statement, and the vegetation cube as plain JSON ([ADR-0002](docs/architecture/adr/0002-json-cube-no-duckdb.md)) | Built. The 3D cube was removed in 0.2 |
| 7 Tree inventory | Species table from `config/species/`, an inventory with `measurement_source` and a field-level data-quality block, the confidence rule from the API contract | Built |
| 8 Carbon engine | IPCC 2006 Tier 1 gain-loss with climate-zone defaults, Chave 2014 allometry when DBH or height exist, density scaling, ramp-up, survival, uncertainty bounds, readiness scoring, and a production-mode refusal to run with `pending` parameters ([carbon engine](docs/architecture/carbon-engine.md)) | Built, with `pending` parameters. See the first and last [next steps](#next-steps) |
| 9 IN, US and EU policy engine | Config-driven screening from `config/policies/` (Green Credit Programme and CCTS for India; COMET-Farm, voluntary methodologies and NRCS programmes for the US; CRCF, CAP and voluntary standards for the EU), with every status carrying references | Built |
| 10 Report | HTML, Markdown, JSON and optional PDF reports with the three separated values, the evidence checklist and full attribution | Built |
| 11 Privacy controls | Deleting a plot deletes everything derived from it, a generalized public view, logs without coordinates, and an `/explain` that takes derived indicators only ([privacy](docs/privacy/privacy-design.md)) | Built |
| 12 Tests and documentation | pytest, Vitest, Playwright smoke tests, data-quality tests over `config/`, and the documentation set ([testing](docs/developer-guide/testing.md)) | Built |

Two phases name an exit criterion. Phase 1: a fresh clone runs in demo mode in under five minutes
([getting started](docs/user-guide/getting-started.md)). Phase 8: the validation protocol in
[research/validation/README.md](research/validation/README.md) runs end to end on the three example farms. Only the
first level of that protocol is automated so far.

## Next steps

These are in no order of priority. Each row says where the work stands today, because most of them need a source, a
reviewer or a decision before any code.

| Step | Where it stands today | Read |
| --- | --- | --- |
| Verify the pending IPCC values | The Tier 1 file marks the root-to-shoot ratios (IPCC 2006 Table 4.4) and the plantation growth values (Tables 4.10 and 4.12) as `pending`, and the species wood densities and some increment multipliers are `pending` too. Production mode refuses an estimate that uses one (HTTP 409 `pending-parameters`). Table 4.9, the natural-forest growth by age class that would replace the tree-age model's 50 % growth after maturity, could not be read in the research of 2026-10-05. A domain reviewer sets `verified` after reading each cell | [IPCC age-class growth](docs/research/ipcc-age-class-growth.md), [verifying a parameter](docs/developer-guide/adding-a-species-or-parameter.md#verifying-a-pending-parameter) |
| Tree cover on 10 m Sentinel-2 pixels in live mode | The detection reads the vegetation cube, whose cells are 30 m (3 by 3 Sentinel-2 pixels), so it finds groups of trees and never single crowns. In demo mode the cube is synthetic. Every threshold is an uncalibrated assumption | [Detection](docs/architecture/imports-and-detection.md#3-detection-ai-detected-tree-cover-from-satellite-data), [detection.yaml](config/detection.yaml) |
| User accounts and sign-in | There are no accounts. `ATLAS_API_KEYS` protects only the endpoints that change data, and a client that can reach the API can list plots and read their exact boundaries. A decision comes first, in an ADR: one key per deployment, a token per person, or a login in front of CarbonCreditBuy | [Threat model](docs/privacy/threat-model.md), [roadmap ideas](docs/community/roadmap-ideas.md#privacy-and-access) |
| Offline-first mobile use | The web app has no service worker and no web app manifest, and it keeps only interface settings and the selected plot's id on the device. When the API cannot be reached, pages that need only existing data show bundled demo fixtures and say so. What may be stored on a phone is the first decision, because exact boundaries are private | [Offline behaviour](apps/web/README.md#offline-behaviour), [roadmap ideas](docs/community/roadmap-ideas.md#the-web-app) |
| More regions | India, the United States and the EU (member states by ISO code) are supported. A region is configuration plus a reviewer who can read the official texts. The countries named so far are Brazil, Kenya and Indonesia, each once a domain reviewer is available | [Adding a region](docs/developer-guide/adding-a-region.md), [roadmap ideas](docs/community/roadmap-ideas.md#regions-and-policy) |
| An optional SAM-based segmentation provider | The API runs no image model. Tree crowns come from an imported file, for example the output of an AI segmentation plugin in QGIS. A provider based on the Segment Anything Model would be optional, and could run only on imagery whose licence allows automated analysis (`analysis_allowed: true`) or on the user's own imagery | [Imagery providers](integrations/imagery/README.md), [import data](docs/user-guide/import-data.md) |
| Agent narration in more languages | The agents' sentences are English templates. With the optional language model on they may be reworded or translated into the requested `locale`, and without it the transcript says messages stay in English. Every number is fixed before any model is called, and a changed number drops the model's answer | [Agents guide](docs/agents/README.md), [ADR-0006](docs/architecture/adr/0006-agentic-framework.md) |
| Run the validation protocol beyond Level 1 | Only the comparison of the engine with hand calculation is automated. The comparison with COMET-Farm (Level 2) and with field data (Level 3) has not been run, so the carbon-engine page has no results to summarize | [Validation protocol](research/validation/README.md), [validation status](docs/architecture/carbon-engine.md#validation-status) |

## Beyond 1.0 (unscheduled)

Ideas tracked as issues, not promises: soil organic carbon indicators with a documented methodology; uncertainty
propagation beyond fixed fractions; integration with field-data apps for DBH capture; additional Indian languages
(Tamil, Telugu, Marathi, Bengali, Punjabi). See [roadmap ideas](docs/community/roadmap-ideas.md) and the
[starter issues](docs/community/starter-issues.md).

## What will not be on the roadmap

Issuing or brokering carbon credits, computing carbon numbers with a language model, or any feature that requires
sharing exact farm geometry with a third party by default. These are governance guardrails
([GOVERNANCE.md](GOVERNANCE.md#scope-guardrails)), not scheduling decisions. The 3D views that version 0.2.0 removed,
and
an in-browser SQL engine, are not planned either: the map stays flat and 2D to keep the app simple.
