# MRV — measurement, reporting and verification

MRV is the chain of activities that turns a claim about carbon into
something a third party can trust: **measuring** (or monitoring) what
happened, **reporting** it in a defined format, and having it
**verified** by an independent, accredited body. Every crediting and
certification system is, at its core, an MRV system with a registry at the
end. AgriCarbon Atlas is best described as a tool that helps users prepare
for MRV: it shows what open data can already say and what still has to be
measured.

## The three parts

| Part | What it means | Who does it |
|---|---|---|
| Measurement / monitoring | Collecting the data a methodology requires: tree counts, species, DBH and height on permanent sample plots, survival, disturbances, land-use records, often supported by remote sensing | The project proponent or an aggregator, following the methodology's monitoring plan |
| Reporting | Compiling measurements and calculations into a monitoring report with a fixed structure, assumptions and uncertainty treatment | The proponent |
| Verification | An accredited validation/verification body audits the report, visits sites, re-measures samples and issues a verification statement | A third party accredited by the programme (for example BEE-accredited carbon verification agencies in India; VVBs approved by Verra; certification bodies under the CRCF) |

## How programmes define it

- The UNFCCC's transparency framework built the term for national
  reporting
  (<https://unfccc.int/process-and-meetings/transparency-and-reporting/the-big-picture/what-is-transparency-and-reporting>);
  project-level systems borrowed it.
- The ICVCM Core Carbon Principles make "robust independent third-party
  validation and verification" one of the ten principles, alongside
  tracking in a registry and transparency
  (<https://icvcm.org/core-carbon-principles/>).
- The Verra VCS Program requires validation of the project description and
  periodic verification of monitoring reports by an approved
  validation/verification body before issuance
  (<https://verra.org/programs/verified-carbon-standard/>).
- Regulation (EU) 2024/3012 (CRCF) requires an operator to submit to a
  certification audit by a certification body before a certificate of
  compliance is issued, followed by re-certification audits over the
  monitoring period; certification schemes recognized by the Commission
  operate registries (Articles 9–13; verify article numbers against the
  current text, <https://eur-lex.europa.eu/eli/reg/2024/3012/oj>).
- India's CCTS defines accredited carbon verification agencies and the
  roles of the Bureau of Energy Efficiency as administrator and of the
  registry ([../regions/IN/CCTS.md](../regions/IN/CCTS.md)).

## Where satellite data fits

Remote sensing supports MRV; it rarely replaces field measurement for
biomass. Sentinel-2 indices such as NDVI and NDMI indicate vegetation
vigor and moisture, detect disturbances and confirm that trees are
present and growing, which is valuable for monitoring plans and
plausibility checks. They do not measure diameter, height, wood density or
carbon, and the relationship between an index and biomass saturates in
dense canopies. Methodologies therefore combine remote sensing with sample
plots; some (for example VM0047's area-based approach) prescribe how
remote-sensing evidence is used
(<https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-0/>).

## The Atlas as MRV preparation

| Atlas feature | MRV role |
|---|---|
| Plot polygon with area and perimeter | The project boundary |
| ESA WorldCover classes and history | Evidence toward the baseline land use |
| Sentinel-2 time series and 36-month cube | Monitoring evidence of presence, growth and disturbance |
| Tree inventory with `measurement_source` and data-quality fields | The start of a monitoring record; distinguishes user-reported from field-measured data |
| Carbon estimate with `parameters_used` and provenance | A transparent, reproducible calculation that a verifier could follow — but not a monitoring report |
| Readiness score and missing-evidence list | A checklist of what a verifier will ask for |
| Report with attribution and disclaimers | Documentation that can accompany an application, clearly marked as an estimate |

What the Atlas does not do: operate permanent sample plots, produce
methodology-compliant monitoring reports, or verify anything. The
`certified: false` field is the honest statement of where in the MRV chain
its output sits — before measurement by a methodology's standards, before
reporting in a methodology's format, and before any verification.
