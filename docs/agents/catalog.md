# Agent catalog

The per-agent reference for the AgriCarbon Atlas team. The learning guide is [README.md](README.md); the live
version of this metadata is `GET /api/v1/agents`, built from the agent classes in
[`apps/api/app/agents/`](../../apps/api/app/agents/). A test (`apps/api/tests/test_agents_docs.py`) fails when
an agent, tool or blackboard key is missing from this page.

Every agent follows the same rules: numbers only from tools (which call the engines), evidence on every finding,
a warning — not an invented value — when something is missing, and no coordinates in any text, fact or tool
summary.

## Coordinator (`coordinator`)

**Role.** Opens every run with the plan and closes it with a summary or the answer to your question.

**Says.** At the start: which agents will work and in which order. At the end: the headline numbers, evidence
readiness and next steps — or a direct answer to your question.

| | |
|---|---|
| Tools | none — it only reads the blackboard |
| Reads | `*` (the only agent allowed to read every key) |
| Writes | `summary` (becomes `summary` of the stored run) |
| Steps | first and last step of every plan; the last step has `run_always` |
| Messages | `plan` at the start; `summary` at the end, or `answer` when the run has a question |
| Pinned disclaimer | "These are estimates and screening results — not carbon credits, certifications or eligibility decisions; money values are scenarios, not guaranteed revenue." |

Opening: names the plan and the agents, says that numbers come from the engines and that nothing is a carbon
credit, flags demo mode, and — for a question — which topic the intent router matched and why. When the locale
is not English and no LLM is on, it says that messages stay in English.

Closing: the headline (`Plot PLT-DEMOIN (2.13 ha, Karnataka, India): estimated removal 7.7–14.3 tCO₂e per year
(central 11.0), confidence medium, evidence readiness 55/100.`), any skipped or failed steps with their reason,
and up to five next steps built from data: redraw an invalid boundary, add a tree inventory, the three heaviest
missing evidence items from the readiness score, and the first programme that still needs an assessment. For a
question, the answer reuses the specialists' sentences for the matched topic (what-if, tree age, programmes,
value, vegetation, land, report or carbon).

## Land agent (`land`)

**Role.** Checks the plot itself: size, location, boundary, land cover and climate zone.

**Says.** How big the plot is and where it lies (state, country), whether the boundary is valid, the land-cover
shares and the climate zone.

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `measure_plot` | `PlotService.require` + `geo_engine.validate_polygon` | area in ha and acres, perimeter, `boundary_valid`, `boundary_problem` (a code such as `self_intersection`), `boundary_quality`, country, state |
| `land_cover_shares` | `AnalysisService` — the latest analysis, or a new one when none exists | dataset and version, cropland and tree-cover shares, classes, `synthetic`, sources |
| `climate_zone` | `AnalysisService` | IPCC zone and label, how it was set (`derived` or `region-default`), temperature and rainfall normals, sources |

Reads `plot_id`; writes `plot_summary`, `landcover`, `climate`. Posts one `finding`
("Your plot is 2.13 ha (5.26 acres) in Karnataka, India. The boundary is valid. About 68 % is cropland and 27 %
tree cover (ESA WorldCover 2021 v200 — synthetic demo values, not an observation). The climate zone is tropical
dry …"), plus a `warning` when the boundary fails validation or land cover or climate are unavailable. Evidence:
the geodesic measurement and the land-cover and climate sources. No confidence grade (the services give none).

## Imagery agent (`imagery`)

**Role.** Reads the satellite vegetation indices for the plot and, when the detection module is installed, the
detected tree cover.

**Says.** How green the plot looks from space (NDVI, moisture NDMI), how that changed over the years, and the
detected tree-cover patches when detection is available.

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `vegetation_summary` | `AnalysisService` vegetation block (Sentinel-2 in live mode) | NDVI and NDMI with classes, date, trend in % with start and end, number of observations, `synthetic`, sources |
| `detect_tree_cover` | `DetectionService.latest`, else `DetectionService.detect(plot_id, target="tree-cover")` — optional module | patches, covered fraction, area in ha, method, month, `reused`, sources |

Reads `plot_id`; writes `vegetation`, `detection`. Posts one `finding`. When the detection module is not
installed the tool call is `skipped` and the finding says so in one sentence; a `warning` follows only when the
vegetation reading is missing or detection raised an error. NDVI classes come from the analysis (`sparse` < 0.3,
`moderate` 0.3–0.6, `healthy` ≥ 0.6, per the API contract).

## Tree agent (`trees`)

**Role.** Reads the tree inventory and any tree counts detected in imported files.

**Says.** How many trees of which species, when they were planted, their age and survival, which measurements
are still missing — and trees counted in imported files.

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `tree_inventory` | `TreeService.latest` | `found`, inventory id, species, count, density, planting year, age, survival, DBH, height, measurement source, confidence, missing fields |
| `imported_trees` | `ImportService.list(plot_id)` — optional module | number of imports, and per import with trees: id, format, kind, count, count inside the plot, mean height, method |

Reads `plot_id`; writes `inventory`, `imported_trees`. Posts a `finding` with the inventory's confidence grade,
then a `handoff` to the Carbon agent when the plan has one ("Carbon agent: please estimate removal for 420 mango
trees planted in 2023 (survival 85 %)."). With no inventory it posts a `warning` asking for species, count and
planting year — and the plan's skip rules then skip Carbon, Market, Review and Report. File names are never
repeated (they can contain names); imports are referred to by id.

## Carbon agent (`carbon`)

**Role.** Runs the carbon engine on the tree inventory and answers what-if questions with the Simulation Lab.

**Says.** Estimated carbon removal per year as a low–central–high range with the method and confidence, and
what-if scenarios — always "an estimate, not a carbon credit".

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `estimate_carbon` | `CarbonService.latest` when it matches the latest inventory, else `CarbonService.estimate` (carbon engine, model `tree-biomass`) | estimate id, annual range, stock range, confidence, `certified`, disclaimer, model, methodology with references, parameter set, parameters with verification status, readiness (missing evidence heaviest first), sources, `reused` |
| `simulate_what_if` | `SimulationService.simulate`, run twice (current and changed tree count) | change, tree counts, baseline and scenario ranges, difference of the central values, horizon, climate zone, density cap, confidence, `certified`, sources |

Reads `plot_id`, `inventory`, `what_if`; writes `estimate`, `what_if_result`. Skipped by every plan when there is
no `inventory` on the blackboard. Messages:

- `finding` — "Estimated removal is 7.7–14.3 tCO₂e per year (central 11.0) using IPCC Tier 1. Since planting,
  about 16.1–29.9 tCO₂e (central 23.0) has been removed. Confidence is medium." + pinned
  "This is an estimate, not a carbon credit."
- `finding` for a what-if (when the request has `what_if`) — both ranges, the difference of the central values,
  and two caveats from the model: all trees are treated as one planting (so later planting removes carbon later),
  and above the species' density cap extra trees add less. Pinned "This is a scenario, not a carbon credit."
- `handoff` to the Market agent (or the Review agent when there is no market step) with the range.
- `warning` when the engine cannot run — for example a production deployment refusing `pending` parameters.

The horizon of the what-if is `horizon_years_default` from `config/methodologies/` (30 years in v0.1).

## Policy agent (`policy`)

**Role.** Screens the country's carbon and environmental programmes and, in the tree-age check, the rules that
treat trees differently by age.

**Says.** Which programmes might apply and what each still needs — an initial screening, never an eligibility
decision; in the tree-age check also the age class, carbon by age and the age rules that apply.

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `screen_programmes` | `PolicyService.screen(country, "tree_plantation")` (`config/policies/`) | country, activity, disclaimer, programmes with id, name, authority, kind, status, URL, references |
| `assess_tree_age` | `TreeAgeService.assess` (`config/tree-age/rules.yaml`) — optional module, `tree-age-check` plan only | age class, carbon stored now and growing now (ranges), credit outlook, rules with `applies`, `why` and verification status, `certified`, disclaimer, sources |

Reads `plot_id`, `inventory`, `age_years`; writes `programmes`, `tree_age`. The screening `finding` ends with
the policy engine's own disclaimer (for India: "Initial screening only — not an eligibility determination.
Green Credits (GCP) and carbon credits (CCTS) are separate mechanisms."). Statuses are put in plain words:

| Status | Said as |
|---|---|
| `potentially_applicable` | may apply |
| `requires_assessment` | needs an assessment |
| `requires_methodology_assessment` | needs an approved methodology and assessment |
| `requires_certification` | needs certification |
| `not_applicable` | does not apply |
| `unknown` | unknown — not enough information |

In the tree-age check the age comes from your question when it states one ("60 years old", "60 साल", "60 Jahre"),
otherwise from the inventory — and the message says which, when they differ. Girth is passed as π × DBH when the
inventory has a diameter. Rules still `pending` verification are counted as "not confirmed". A missing tree-age
module gives a `warning`; the programme screening still stands.

## Market agent (`market`)

**Role.** Puts configured scenario prices on the carbon estimate and lists the other farm income sources for the
region.

**Says.** Three separate values — environmental benefit (tCO₂e per year), indicative carbon value (a price
scenario, not a credit) and other farm income — never added together.

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `market_scenarios` | `MarketService.scenarios_for` (`config/market/carbon-price-scenarios.yaml`) | currency, low / reference / high scenarios with price and value per year, price basis with verification status and references, other income sources (value `null` until you add records), disclaimer |

| `cost_scenario` | `SimulationService.simulate` with `costs` → `carbon_engine.economics.cost_scenario` — only when the request carries costs | currency, totals (establishment, upkeep and monitoring over the horizon, undiscounted), cumulative removal range, break-even carbon price per tCO₂e (low–central–high), per price scenario the indicative value over the horizon and the share of costs covered, `not_entered`, `certified: false`, disclaimer |

Reads `plot_id`, `estimate`, `costs`; writes `market`, `cost`. Skipped when there is no `estimate`. One `finding` in three
sentences — environmental benefit, indicative value (reference price, with the low and high scenario values in
brackets), other farm income (not estimated) — and "These three values answer different questions and are never
added together." The market disclaimer is pinned. The facts keep the three values under separate keys
(`environmental_benefit_tco2e_per_year`, `indicative_value_per_year`, `other_farm_income`).

When the run or question carries `costs` (your own sapling, planting, upkeep and monitoring costs — the platform
has no built-in cost values), a second `finding` follows: the entered costs over the horizon, the carbon price at
which an indicative value would match them, the share covered at the reference price scenario, which costs were
not entered (counted as zero), and that credits exist only after a programme validates, monitors and verifies the
removal.

## Review agent (`review`)

**Role.** Double-checks the carbon estimate: range, unit, confidence, certified flag, sources, parameter
verification status and missing evidence.

**Says.** Whether the estimate carries a range, a confidence grade, its sources and certified: false; which
parameters are still pending verification; and which evidence is still missing.

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `review_estimate` | `CarbonService.require` | checks passed and failed, parameter counts by verification status, pending parameter names, readiness score and grade, missing evidence (heaviest first) |

Reads `plot_id`, `estimate`; writes `review`. Skipped when there is no `estimate`. Posts a `finding` with the
estimate's confidence, or a `warning` when any check fails. The same facts feed the `pending-parameters`
guardrail of the run.

## Report agent (`report`)

**Role.** Writes the HTML assessment report for the current estimate with the report engine.

**Says.** That a report was written, its id and where to open it.

| Tool | Wraps | Returns (summary) |
|---|---|---|
| `create_report` | `ReportService.create(plot, "html", locale, estimate_id)` | report id, format, URL (`/api/v1/reports/{report_id}`), estimate id, time |

Reads `plot_id`, `estimate`, `locale`; writes `report`. Skipped when there is no `estimate`. Only the
`full-assessment` plan writes a report.

## Plans

| Plan | Steps | Skip rules |
|---|---|---|
| `full-assessment` | coordinator → land → imagery → trees → carbon → policy → market → review → report → coordinator | carbon needs `inventory`; market, review and report need `estimate` |
| `quick-estimate` | coordinator → land → trees → carbon → review → coordinator | carbon needs `inventory`; review needs `estimate` |
| `tree-age-check` | coordinator → trees → carbon → policy → review → coordinator | carbon needs `inventory`; review needs `estimate` |

The closing coordinator step always runs. `POST /agents/ask` picks the plan with the intent router: what-if,
carbon and land questions → `quick-estimate`; tree age → `tree-age-check`; report, value, programme and
vegetation questions → `full-assessment`; anything else → `quick-estimate`, and the coordinator says it could
not match the question.

## Blackboard keys

| Key | Written by | Read by | Holds |
|---|---|---|---|
| `plot_id`, `locale`, `mode` | request | all agents that declare them | the run's inputs |
| `question`, `intent`, `what_if`, `age_years` | request (questions only) | coordinator, carbon, policy | the redacted question, the router's decision, a tree change, an age |
| `plot_summary` | land | coordinator | area, place, boundary validity |
| `landcover` | land | coordinator | land-cover shares and sources |
| `climate` | land | coordinator | climate zone and sources |
| `vegetation` | imagery | coordinator | NDVI, NDMI, trend, sources |
| `detection` | imagery | coordinator | detected tree-cover summary |
| `inventory` | trees | carbon, policy, coordinator; the carbon skip rule | the latest tree inventory |
| `imported_trees` | trees | coordinator | tree counts from imported files |
| `estimate` | carbon | market, review, report, coordinator; skip rules | the estimate view (range, confidence, parameters, readiness, sources) |
| `what_if_result` | carbon | coordinator | the what-if comparison |
| `programmes` | policy | coordinator | the programme screening |
| `tree_age` | policy | coordinator | the tree-age assessment |
| `market` | market | coordinator | the value scenarios |
| `costs` | request (optional) | market | your entered costs |
| `cost` | market | coordinator | the cost scenario and break-even carbon price |
| `review` | review | coordinator | the review checks |
| `report` | report | coordinator | the report id and URL |
| `summary` | coordinator | the service (stored as the run's `summary`) | headline, estimate, readiness, next steps |

## Message kinds

| Kind | Used for |
|---|---|
| `plan` | the coordinator's opening |
| `finding` | what a specialist found — always with evidence |
| `warning` | something is missing or went wrong (never reworded by an LLM) |
| `handoff` | a short note to the next agent that uses a result (`to` is that agent's id) |
| `answer` | the coordinator's closing message when the run has a question — always with evidence |
| `summary` | the coordinator's closing message otherwise |
