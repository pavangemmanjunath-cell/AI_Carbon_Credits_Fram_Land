# Architecture

AgriCarbon Atlas is a monorepo with a Python back end, a TypeScript web app, a QGIS plugin and a set of configuration
files that carry all regional, species, methodology, policy, detection, tree-age and imagery knowledge. The architecture
follows from the principles in [CLAUDE.md](../../CLAUDE.md): engines calculate, adapters fetch, components render,
configuration decides, and every result carries provenance and an uncertainty range.

Version 0.2 added an agent team, imports with tree detection, tree age, imagery providers and the QGIS plugin, and it
removed every 3D view: the web app is a flat 2D map. The pages below describe the system as it is in 0.2.

## Reading order

1. [system-architecture.md](system-architecture.md): the components, how a request moves through them, and the
   difference between `demo` and `live` mode.
2. [data-flow.md](data-flow.md): the sequence from locating a place to downloading a report, the version 0.2 flows
   (imports, detection, tree age, imagery, agents) and the point beyond which coordinates do not travel.
3. [carbon-engine.md](carbon-engine.md): the model interface, the Tier 1 and Tier 2 equations, uncertainty, confidence
   and readiness scoring, and an explicit statement of what the engine is not.
4. [mapping-architecture.md](mapping-architecture.md): the flat 2D map: MapLibre GL with PMTiles on S3-compatible
   storage, optional raster imagery, the GeoJSON layers and the JSON vegetation cube.
5. [imports-and-detection.md](imports-and-detection.md): how a pin, a tree line, typed coordinates, an imported file and
   the "AI detected tree cover" produce their results.
6. [tree-age-model.md](tree-age-model.md): carbon by tree age, the age curve and the rules that treat trees differently
   by age and place.
7. The agent team: the [agents guide](../agents/README.md), the [catalog](../agents/catalog.md) and
   [ADR-0006](adr/0006-agentic-framework.md).
8. [api-contract.md](api-contract.md): the single source of truth for the `/api/v1` wire format, shared by every client,
   with the implementation notes for version 0.2 at the end.
9. The decision records under [adr/](adr/0001-vite-react-over-nextjs.md), listed below.

## Where each version 0.2 feature lives

| Feature | Endpoints | Code and configuration | Read |
| --- | --- | --- | --- |
| Simpler land input | `POST /geometry/from-point`, `/from-line`, `/parse-coordinates` | `geo_engine.construct`, `geo_engine.coordinates` | [imports-and-detection.md](imports-and-detection.md) |
| Import data | `POST /imports`, `GET /imports`, `GET` and `DELETE /imports/{id}` | `geo_engine.imports`, `geo_engine.pointcloud` | [imports-and-detection.md](imports-and-detection.md) |
| AI detected tree cover | `POST /plots/{id}/detect`, `GET /plots/{id}/detections` | `geo_engine.detection`, `config/detection.yaml` | [imports-and-detection.md](imports-and-detection.md) |
| Tree age | `GET /tree-age/rules`, `POST /tree-age/assess` | `carbon_engine.age`, `policy_engine.tree_age`, `config/tree-age/` | [tree-age-model.md](tree-age-model.md) |
| Imagery for the Satellite view | `GET /imagery/providers` | `config/imagery/providers.yaml`, the browser loads the tiles | [mapping-architecture.md](mapping-architecture.md) |
| AI agents | `GET /agents`, `POST /plots/{id}/agents/run`, `POST /agents/ask`, `GET /agents/runs` | `packages/agent-framework`, `apps/api/app/agents` | [agents guide](../agents/README.md) |
| QGIS plugin | A client of the endpoints above | `integrations/qgis-plugin` | [plugin README](../../integrations/qgis-plugin/README.md) |

## Architecture decision records

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](adr/0001-vite-react-over-nextjs.md) | Vite + React SPA rather than Next.js | accepted |
| [0002](adr/0002-json-cube-no-duckdb.md) | The vegetation cube stays plain JSON, filtered in the browser; no in-browser SQL engine | accepted |
| [0003](adr/0003-deterministic-before-ai.md) | Deterministic calculations first; language models only explain, never compute | accepted |
| [0004](adr/0004-config-driven-regions-and-policies.md) | Regions, species, methodologies and policy rules are configuration, not code | accepted |
| [0005](adr/0005-apache-2-license.md) | Apache License 2.0 | accepted |
| [0006](adr/0006-agentic-framework.md) | Small in-house agent framework; deterministic by default, LLM optional | accepted |

ADR-0001 and ADR-0002 were written for version 0.1, when the web app also drew 3D scenes. Those scenes and their
libraries were removed in 0.2 (see the [changelog](../../CHANGELOG.md)); both decisions still hold, and the two records
are kept as they were written, so read their 3D passages as history.

New ADRs follow the same template (context, decision, consequences, alternatives) and are numbered sequentially. A
superseded ADR stays in place with a pointer to its replacement ([GOVERNANCE.md](../../GOVERNANCE.md)).

## Invariants worth memorizing

- The web app never computes a carbon number; it displays what the API returns. The simulation lab calls
  `POST /simulate`. The browser's own geometry is limited to drawing aids (the area shown while you draw) and, when the
  API is offline, the shapes of a pin, a tree line and typed coordinates, which are labelled as such.
- Policy logic is evaluated from `config/policies/<ISO>.yaml` and the tree-age rules from `config/tree-age/`; there is no
  country-specific branch in engine or UI code.
- Parameters enter the engines from `config/` with `source`, `unit` and `verification_status`. Production mode refuses
  `pending` carbon parameters, withholds `pending` tree-age rules and ships no imagery provider whose terms are
  unconfirmed.
- Exact plot geometry is returned by the owner endpoints only; the public view (`GET /plots/{id}/public`) carries a
  `public_centroid` on a 0.05° grid. There are no user accounts yet, so the owner endpoints are not access controlled
  beyond the optional API key on writes ([threat model](../privacy/threat-model.md)).
- `POST /explain` receives derived indicators only; the schema rejects coordinate-bearing keys.
- Agents never see coordinates. The optional language model only rephrases sentences whose numbers were fixed before it
  was called, and its answer is dropped if a number changes ([ADR-0003](adr/0003-deterministic-before-ai.md)).
- An uploaded file is read in memory and dropped. Only the derived record (shapes, counts, a map preview) is kept, and
  deleting the plot deletes it.
- Imagery is configuration. The API never fetches or stores a tile, and imagery whose licence bars automated analysis
  is for viewing only (`analysis_allowed: false`).
- Every response that depends on external data carries `provenance` with dataset ids, versions, licenses, attribution
  and access times, and every carbon figure is `certified: false`.
