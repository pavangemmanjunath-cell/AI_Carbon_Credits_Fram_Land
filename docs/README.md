# AgriCarbon Atlas documentation

AgriCarbon Atlas is an open-source geospatial platform that helps farmers, landowners and researchers understand tree
cover, agricultural conditions and *potential* carbon benefits, and shows which evidence a recognized programme would
still require. Every carbon figure it produces is a scenario estimate with a range, a confidence grade and provenance;
none is a carbon credit. If you read only one page, read
[concepts/carbon-credit-vs-estimate.md](concepts/carbon-credit-vs-estimate.md).

These pages describe version 0.2.0 ([changelog](../CHANGELOG.md)): a flat 2D map, simpler ways to mark land, imports
with tree detection, tree age, imagery providers for the Satellite view, an AI agent team and a QGIS plugin.

## Start here

| If you are… | Read |
| --- | --- |
| A farmer or advisor who wants to try it | [Getting started](user-guide/getting-started.md) → [Mark your land](user-guide/mark-your-land.md) → [Results explained](user-guide/results-explained.md) → [FAQ](user-guide/faq.md) |
| A developer setting up the repository | [Setup](developer-guide/setup.md) → [Architecture overview](developer-guide/architecture-overview.md) → [Testing](developer-guide/testing.md) |
| Someone who wants to contribute | [Contributing](../CONTRIBUTING.md) → [Developer guide](developer-guide/README.md) → [Starter issues](community/starter-issues.md) |
| An integrator calling the API | [API contract](architecture/api-contract.md) and the [examples](../examples/README.md) |
| A reviewer of carbon or policy content | [Carbon engine](architecture/carbon-engine.md), [regions](#regions), [research](#research-and-data-sources) and the [validation protocol](../research/validation/README.md) |
| Curious about the AI agents | [AI agents in the user guide](user-guide/ai-agents.md) → [Agents guide](agents/README.md) → [Agent catalog](agents/catalog.md) |
| A QGIS user | [QGIS plugin guide](user-guide/qgis-plugin.md) |
| Someone concerned about data privacy | [Privacy design](privacy/privacy-design.md) |

## User guide

Written for farmers, landowners and advisors; no technical background needed.

| Page | Read it when you want to… |
| --- | --- |
| [User guide home](user-guide/README.md) | See the steps and the pages in one place |
| [Getting started](user-guide/getting-started.md) | Open the app, tell demo data from real data, and reach a first result |
| [Mark your land](user-guide/mark-your-land.md) | Draw a boundary or a tree line, drop a pin and type the size, or type coordinates |
| [Import data](user-guide/import-data.md) | Bring in a boundary, tree points, tree crowns or a point cloud from a file |
| [Satellite imagery](user-guide/satellite-imagery.md) | Switch the map to imagery and learn which pictures you get and who owns them |
| [Results explained](user-guide/results-explained.md) | Understand each card of the carbon potential page |
| [AI agents](user-guide/ai-agents.md) | Put the agent team to work on a plot and ask it questions |
| [Tree age](user-guide/tree-age.md) | See what trees of a given age hold and which rules apply to them |
| [Simulation](user-guide/simulation-lab.md) | Try "what if I plant more trees?" and compare scenarios |
| [Reports](user-guide/reports.md) | Print or save an evidence file for an advisor |
| [QGIS plugin](user-guide/qgis-plugin.md) | Send a field polygon from QGIS and count trees from a segmentation layer |
| [FAQ](user-guide/faq.md) | Find a quick answer, including privacy, languages and units |

## Architecture

| Page | Content |
| --- | --- |
| [architecture/README.md](architecture/README.md) | Overview, reading order and where each version 0.2 feature lives |
| [architecture/system-architecture.md](architecture/system-architecture.md) | Components, request lifecycle, demo vs live mode |
| [architecture/data-flow.md](architecture/data-flow.md) | Sequence from locating a place to a report, the version 0.2 flows, and where coordinates stop |
| [architecture/carbon-engine.md](architecture/carbon-engine.md) | Model interface, equations, uncertainty, readiness, what it is not |
| [architecture/mapping-architecture.md](architecture/mapping-architecture.md) | The flat 2D map: MapLibre, PMTiles, imagery, GeoJSON layers and the JSON vegetation cube |
| [architecture/imports-and-detection.md](architecture/imports-and-detection.md) | Pins, tree lines, typed coordinates, imported files and "AI detected tree cover" |
| [architecture/tree-age-model.md](architecture/tree-age-model.md) | Carbon by tree age, the age curve and the rules that treat trees differently by age |
| [architecture/api-contract.md](architecture/api-contract.md) | The `/api/v1` contract, the source of truth for both apps and the plugin |

### Architecture decision records

| ADR | Decision |
| --- | --- |
| [0001](architecture/adr/0001-vite-react-over-nextjs.md) | Vite + React SPA rather than Next.js |
| [0002](architecture/adr/0002-json-cube-no-duckdb.md) | The vegetation cube stays plain JSON; no in-browser SQL engine |
| [0003](architecture/adr/0003-deterministic-before-ai.md) | Deterministic calculations first; language models only explain |
| [0004](architecture/adr/0004-config-driven-regions-and-policies.md) | Regions, species, methodologies and policy rules are configuration |
| [0005](architecture/adr/0005-apache-2-license.md) | Apache License 2.0 |
| [0006](architecture/adr/0006-agentic-framework.md) | A small in-house agent framework, deterministic by default |

ADR-0001 and ADR-0002 were written for version 0.1, when the web app also drew 3D scenes. Those scenes were removed in
0.2; read their 3D passages as history ([architecture overview](architecture/README.md#architecture-decision-records)).

## AI agents

[Agents guide](agents/README.md) (how the team works, with exercises) ·
[Agent catalog](agents/catalog.md) (each agent, tool, plan and guardrail) ·
[ADR-0006](architecture/adr/0006-agentic-framework.md) ·
[Agent framework package](../packages/agent-framework/README.md)

## Concepts

[Carbon credit vs estimate](concepts/carbon-credit-vs-estimate.md) ·
[ESG and the three separated values](concepts/esg.md) ·
[Additionality](concepts/additionality.md) ·
[Permanence](concepts/permanence.md) ·
[Leakage](concepts/leakage.md) ·
[MRV](concepts/mrv.md)

## Regions

| Region | Pages |
| --- | --- |
| India | [README](regions/IN/README.md) · [Green Credit Programme](regions/IN/GREEN_CREDIT.md) · [CCTS](regions/IN/CCTS.md) · [Incentives](regions/IN/INCENTIVES.md) · [Methodologies](regions/IN/METHODOLOGIES.md) · [Data sources](regions/IN/DATA_SOURCES.md) |
| United States | [README](regions/US/README.md) · [Programs](regions/US/PROGRAMS.md) · [Methodologies](regions/US/METHODOLOGIES.md) · [Data sources](regions/US/DATA_SOURCES.md) |
| European Union | [README](regions/EU/README.md) · [Programs](regions/EU/PROGRAMS.md) · [Methodologies](regions/EU/METHODOLOGIES.md) · [Data sources](regions/EU/DATA_SOURCES.md) |

## Research and data sources

| Page | Content |
| --- | --- |
| [data-sources/FREE_APIS.md](data-sources/FREE_APIS.md) | Each free and open API the platform reads: terms, configuration, limits and what a provider receives |
| [research/policy-references.md](research/policy-references.md) | Sourced facts behind the IN, US and EU policy rules, with unverified items marked |
| [research/tree-age-carbon-rules.md](research/tree-age-carbon-rules.md) | Tree age, carbon credits and the law: the research behind `config/tree-age/rules.yaml` |
| [research/ipcc-age-class-growth.md](research/ipcc-age-class-growth.md) | What the IPCC defaults say about growth by age class, and what could not be read |
| [research/imagery-providers.md](research/imagery-providers.md) | The imagery providers considered for the Satellite view and their terms |
| [../research/README.md](../research/README.md) | Notebooks, experiments, the [validation protocol](../research/validation/README.md) and publication drafts |

## Privacy

[Privacy design](privacy/privacy-design.md) ·
[Geolocation](privacy/geolocation.md) ·
[Farmer data](privacy/farmer-data.md) ·
[Data retention](privacy/data-retention.md) ·
[Threat model](privacy/threat-model.md)

## Licensing

[Data licenses](licensing/DATA_LICENSES.md) ·
[Map and imagery licenses](licensing/MAP_LICENSES.md) ·
[Third-party software](licensing/THIRD_PARTY.md) ·
[Attribution strings](licensing/ATTRIBUTION.md)

## Developer guide

| Page | Read it when you want to… |
| --- | --- |
| [Developer guide home](developer-guide/README.md) | Start, and see the rules, commands and conventions (including coding standards) |
| [Setup](developer-guide/setup.md) | Install, configure, run in demo or live mode, and look up an environment variable |
| [Architecture overview](developer-guide/architecture-overview.md) | Find the file to open for a change; see the repository map |
| [Testing](developer-guide/testing.md) | Run and write tests and see what CI checks |
| [Adding a region](developer-guide/adding-a-region.md) | Support a new country, or change program rules for a region |
| [Adding a species or parameter](developer-guide/adding-a-species-or-parameter.md) | Verify a `pending` value, add a species or change an equation |
| [Adding a tree-age rule](developer-guide/adding-a-tree-age-rule.md) | Record a law or program that treats trees differently by age |
| [Adding an integration](developer-guide/adding-an-integration.md) | Connect an external API or dataset, or add an imagery provider |
| [Release process](developer-guide/release-process.md) | Cut a version and understand why production needs verified parameters |
| [Troubleshooting](developer-guide/troubleshooting.md) | Fix a gray map, a CORS error, a failing install or a docs check |

Module READMEs: [API](../apps/api/README.md) · [web app](../apps/web/README.md) ·
[carbon engine](../packages/carbon-engine/README.md) · [geo engine](../packages/geo-engine/README.md) ·
[policy engine](../packages/policy-engine/README.md) · [report engine](../packages/report-engine/README.md) ·
[agent framework](../packages/agent-framework/README.md) · [integrations](../integrations/README.md) ·
[imagery providers](../integrations/imagery/README.md) · [QGIS plugin](../integrations/qgis-plugin/README.md) ·
[tests](../tests/README.md) · [sample data](../data/sample/README.md) · [examples](../examples/README.md)

## Community and project

[Starter issues](community/starter-issues.md) ·
[Roadmap ideas](community/roadmap-ideas.md) ·
[Contributing](../CONTRIBUTING.md) ·
[Code of conduct](../CODE_OF_CONDUCT.md) ·
[Governance](../GOVERNANCE.md) ·
[Security policy](../SECURITY.md) ·
[Roadmap](../ROADMAP.md) ·
[Changelog](../CHANGELOG.md) ·
[Images](images/README.md)

## Conventions used in these pages

American spelling; SI units with the regional display unit noted where it differs (acres in the US); ISO 3166-1
alpha-2 country codes; "tCO₂e/yr" for annual removals. Regulatory statements link to their source, and a statement we
could not confirm against the primary document carries the phrase *verify against the current notification*. Dates,
thresholds and prices are never stated without a source.
