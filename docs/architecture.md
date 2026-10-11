# Architecture

Components render, engines calculate, adapters fetch, agents explain.

```mermaid
flowchart LR
  subgraph Browser["Web app (React 19 + Vite, apps/web)"]
    MAP["Map: MapLibre + OpenFreeMap<br/>draw, import, lock land"]
    SIM["Simulation: 3D land view<br/>(three.js), costs, explanation"]
    AG["AI agents page"]
  end
  subgraph API["FastAPI service (apps/api)"]
    R["REST /api/v1<br/>(OpenAPI)"]
    SVC["Services"]
    AGT["Agent team: 9 agents,<br/>3 plans, 6 guardrails"]
  end
  subgraph Engines["Deterministic engines (packages/)"]
    CE["carbon-engine<br/>IPCC Tier 1/2, uncertainty,<br/>readiness, tree age, economics"]
    GE["geo-engine<br/>geometry, imports, indices,<br/>detection, cube"]
    PE["policy-engine<br/>programmes, tree-age rules"]
    RE["report-engine"]
    AF["agent-framework<br/>(carboncreditbuy_agents)"]
  end
  CFG[("config/<br/>parameters with source<br/>and verification status")]
  ADP["Adapters (integrations/)<br/>WorldCover, Sentinel-2 STAC,<br/>Open-Meteo, SoilGrids, geocoders"]
  LLM["Optional OpenAI-compatible LLM<br/>(rewording only, redacted input)"]
  DB[("PostgreSQL + PostGIS<br/>or in-memory demo store")]

  MAP --> R
  SIM --> R
  AG --> R
  R --> SVC
  SVC --> CE & GE & PE & RE
  SVC --> AGT
  AGT --> AF
  AGT -.tool calls.-> SVC
  AGT -. optional .-> LLM
  CE & PE --> CFG
  SVC --> ADP
  SVC --> DB
```

**Boundaries that are enforced:** the React app never computes a carbon number; engines never touch the network;
adapters never decide policy; agents never invent a number (every figure comes from a tool call into an engine);
coordinates never reach logs or a language model.

## Detailed documents

- Overview with diagrams: [architecture/system-architecture.md](architecture/system-architecture.md)
- Data flow: [architecture/data-flow.md](architecture/data-flow.md)
- Carbon engine: [architecture/carbon-engine.md](architecture/carbon-engine.md)
- Tree-age model: [architecture/tree-age-model.md](architecture/tree-age-model.md)
- Mapping: [architecture/mapping-architecture.md](architecture/mapping-architecture.md)
- API contract: [architecture/api-contract.md](architecture/api-contract.md)
- Agents: [agents/README.md](agents/README.md) and [agents/catalog.md](agents/catalog.md)
- Decision records: [architecture/adr/](architecture/adr/)
