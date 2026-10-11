# Paper outline

**Working title.** CarbonCreditBuy: An Open Geospatial MRV Framework for
Evidence-Based Agricultural Carbon Assessment Using Earth Observation and
Regional Carbon Policies

**Target venues (to decide).** *Environmental Modelling & Software*
(software-and-methods focus), *Carbon Balance and Management* (open
access, MRV audience), or *Remote Sensing of Environment* if the
observation component becomes the main contribution. A short companion
paper in the *Journal of Open Source Software* can describe the software
itself.

**Status.** Outline. Results sections depend on the validation protocol in
[../validation/README.md](../validation/README.md) being executed.

## Abstract (draft, 180 words)

Smallholders and landowners who consider tree planting for climate benefit
face a gap between what public Earth-observation data can show about their
land and what a recognized carbon or environmental programme requires as
evidence. We present CarbonCreditBuy, an open-source (Apache-2.0)
geospatial platform that combines land-cover (ESA WorldCover), Sentinel-2
vegetation indices, climate and soil data with a deterministic,
configuration-driven carbon engine (IPCC 2006 Tier 1 gain-loss; Chave 2014
allometry where measurements exist) and a policy-screening engine encoding
programme requirements for India, the United States and the European
Union. Every output is a range with provenance, a confidence grade and a
readiness score that names missing evidence; no output is presented as a
credit. We describe the architecture, the privacy boundary (exact
geometry never leaves the owner's context; 0.05° generalization for public
views; derived indicators only for optional explanation), and a validation
against COMET-Farm and published field data. We discuss where Tier 1
defaults are adequate, where they are not, and how the framework supports
the collection of the evidence that programmes such as the Green Credit
Programme, CCTS, voluntary ARR methodologies and the EU CRCF demand.

## Research questions

- **RQ1 — Evidence gap.** Which inputs that recognized programmes require
  (baseline, additionality evidence, tree measurements, monitoring) can be
  derived from open Earth-observation data for small agricultural plots,
  and which cannot? How does plot size (0.5–10 ha) affect what 10 m
  products can support?
- **RQ2 — Accuracy of default models.** How close are IPCC Tier 1
  gain-loss estimates, with climate-zone defaults and simple density and
  survival adjustments, to reference tools (COMET-Farm) and field
  measurements for orchard and agroforestry systems (mango, pecan, olive,
  teak, eucalyptus), and does the stated uncertainty range contain the
  reference values?
- **RQ3 — Policy translation.** Can programme requirements in three
  jurisdictions be encoded as configuration that yields consistent,
  explainable screening statuses, and what does a readiness score add for
  users compared with a bare carbon number?

## Methods

1. **System design.** Monorepo with FastAPI back end, deterministic engines
   (`carbon-engine`, `geo-engine`, `policy-engine`, `report-engine`),
   adapters with provenance, and a React/MapLibre front end with a JSON
   space-time cube. Reference: [docs/architecture/](../../docs/architecture/README.md).
2. **Carbon model.** Tier 1 gain-loss (ΔC = A·G_total·CF, G_total =
   G_w(1+R), CO₂e = 44/12·C) with density scaling, linear ramp-up, survival
   and fixed uncertainty bands; Tier 2 path with Chave 2014 eq. 4; parameter
   provenance and verification status. Reference:
   [docs/architecture/carbon-engine.md](../../docs/architecture/carbon-engine.md).
3. **Earth observation pipeline.** STAC search, SCL-based cloud masking,
   monthly composites, NDVI/NDMI, 36-month cube at 30 m.
4. **Policy encoding.** Rule schema (`when` → `status`, `reason`,
   `requirements`, `references`), source documents per rule, screening
   statuses.
5. **Validation.** Levels 1–3 of the validation protocol; acceptance
   criteria stated a priori.
6. **Privacy evaluation.** Threat model (STRIDE) and empirical check that
   no coordinates leave the owner boundary in logs, reports or the
   explanation payload.

## Datasets

| Dataset | Use | License |
|---|---|---|
| ESA WorldCover 2021 v200 | land-cover shares | CC BY 4.0 |
| Copernicus Sentinel-2 L2A (Earth Search / CDSE STAC) | NDVI, NDMI, cube | free, full and open; attribution required |
| Open-Meteo archive and elevation | climate zone, elevation | CC BY 4.0 |
| ISRIC SoilGrids 2.0 | SOC 0–30 cm context | CC BY 4.0 |
| USDA NASS Quick Stats | county crop statistics (other income) | US public domain |
| data.gov.in district crop production | district statistics (other income) | GODL-India |
| COMET-Farm outputs | reference values (entered manually) | referenced, not redistributed |
| Published field studies | reference biomass | cited |
| Synthetic plots (`examples/`) | all experiments | project-generated |

See [docs/licensing/DATA_LICENSES.md](../../docs/licensing/DATA_LICENSES.md).

## Evaluation plan

- **RQ1.** For 30 synthetic plots across the three regions and sizes
  0.5–10 ha, tabulate which programme requirements (from `config/policies/`)
  are satisfiable from data alone, from data plus user-reported inventory,
  or only from field work; analyze sensitivity to plot size via the share
  of mixed WorldCover pixels.
- **RQ2.** Execute validation Levels 2 and 3; report coverage of the range,
  median absolute relative difference and signed bias per species and
  climate zone; show the effect of adding DBH/height.
- **RQ3.** Inter-rater agreement between two domain reviewers assigning
  statuses by hand versus the engine for 20 cases per region; a small user
  study (n ≈ 15 per region, farmers and advisors) on comprehension of the
  three separated values and the readiness checklist compared with a
  single carbon number.

## Limitations to state plainly

Tier 1 defaults are not species-specific; several v0.1 parameters are
pending verification; 10 m products are coarse for plots under 1 ha; the
tool screens programmes but cannot determine eligibility; market scenarios
are illustrative; no soil organic carbon model is included in the first
release.

## Reproducibility

The paper will cite a tagged release and archive it with a DOI (Zenodo);
all experiments live under `research/experiments/` with pinned
configuration; figures are regenerated by scripts committed alongside.
