# Methodology

## Carbon estimation

**Tier 1 (age and area).** Annual change in biomass carbon follows the IPCC 2006 gain–loss method
(Vol. 4, Ch. 2 and 4): `ΔC = A · G_w · m_sp · f_d · s · f_t(a) · (1 + R) · CF`, converted with `CO₂e = C · 44/12`.
Growth `G_w`, root-to-shoot ratio `R` and carbon fraction `CF` come from `config/` with a source and a
`verification_status`.

**Tier 2 (measured trunk).** Above-ground biomass uses Chave et al. (2014) equation 4,
`AGB = 0.0673 (ρ D² H)^0.976`, with wood density from the Global Wood Density Database.

**Uncertainty.** Every carbon output is `low / central / high` with unit, confidence, model and methodology.

**Verification gate.** Parameters are `verified`, `pending` or `assumption`. Production mode refuses `pending`.

**Cost scenario.** `carbon_engine.economics` adds up costs that the user enters (no built-in cost values),
undiscounted, and divides them by the engine's cumulative removal to give a break-even carbon price per tCO₂e. It is
compared with configured price scenarios and is never presented as revenue.

## AI and decision components

The project uses no trained machine-learning models. Its "AI" components are deterministic and inspectable:

| Component | Method | Inputs | Output |
|---|---|---|---|
| Tree-cover detection (satellite) | NDVI threshold on a multi-month composite, 8-connected components, confidence from NDVI margin, patch size and persistence | Sentinel-2 vegetation cube (synthetic in demo mode) | Patches with a confidence score |
| Tree detection (point clouds) | Canopy height model and local maxima | LAS/LAZ file | Tree tops and heights |
| Agent team | Nine rule-based agents in fixed plans; shared blackboard with access rules; a deterministic intent router for questions | Plot id, question, optional costs | Messages with tools and evidence |
| Guardrails | Six checks after every run: not a credit, uncertainty present, provenance present, no coordinates, pending parameters flagged, values kept apart | The run's messages and facts | Pass / warn / fail per check |
| Optional language model | OpenAI-compatible endpoint that may only reword template sentences from redacted facts; output that changes a number is rejected | Redacted text (no coordinates, names or contact data) | Reworded sentence or the template |
| Explanation ("Why this number?") | One-at-a-time sensitivity: re-run the engine with each user-controlled input (tree count, survival rate, plot area) at ±10 % | A simulation request | Percentage change per input, plus every factor with source and status |

## Evaluation

- **Implementation checks** ([benchmarks/](../benchmarks/README.md)): an independent re-implementation of the
  Tier 1 equations matches the engine to within rounding; 13 adversarial cases for the guardrails; parameter census;
  sensitivity of removal to the growth value.
- **Tests:** about 2,200 Python and about 480 web tests, plus browser tests (see
  [reproducibility.md](reproducibility.md)).
- **Not yet done:** validation against field measurements or reference tools (levels 2 and 3 in
  [research/validation/](../research/validation/README.md)).

## What the numbers are not

Estimates are not carbon credits (`certified: false`). A language model never computes a number.

Details: [architecture/carbon-engine.md](architecture/carbon-engine.md),
[research/validation/README.md](../research/validation/README.md),
[benchmarks/](../benchmarks/README.md).
