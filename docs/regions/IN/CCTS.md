# Carbon Credit Trading Scheme (India)

The Carbon Credit Trading Scheme, 2023 (CCTS) is India's domestic carbon
market framework. It has a **compliance mechanism** for designated
industrial sectors and an **offset mechanism** for voluntary projects,
including, in principle, agriculture and forestry. This page summarizes
the scheme, names the institutions, lists what a project would need, and
states how CarbonCreditBuy treats it. Details marked *verify* must be checked
against the current notifications and BEE procedures, which have been
evolving quickly.

## Legal basis and institutions

| Item | Detail | Source |
|---|---|---|
| Notification | Carbon Credit Trading Scheme, 2023, notified by the Ministry of Power in June 2023 under the Energy Conservation Act, 2001 as amended in 2022; amended in December 2023 to add the offset mechanism (verify dates and amendment numbers) | <https://beeindia.gov.in/> ; Ministry of Power, <https://powermin.gov.in/> |
| Governance | National Steering Committee for the Indian Carbon Market (NSCICM) | CCTS, 2023 |
| Administrator | Bureau of Energy Efficiency (BEE) | <https://beeindia.gov.in/> |
| Registry | Grid Controller of India Limited (Grid-India) as the Indian Carbon Market registry (verify) | CCTS, 2023 |
| Trading regulator and platforms | Central Electricity Regulatory Commission (CERC); trading through power exchanges (verify) | CCTS, 2023 |
| Verification | Accredited Carbon Verification Agencies (ACVAs) accredited by BEE under its ACVA regulations | BEE, <https://beeindia.gov.in/> |
| Unit | Carbon Credit Certificate (CCC), one tonne of CO₂ equivalent | CCTS, 2023 |

## Compliance mechanism

Obligated entities in notified energy-intensive sectors receive
greenhouse-gas **emission-intensity targets**; entities that beat their
target are issued CCCs, those that miss must buy and surrender CCCs or pay
an environmental compensation. The initial sectors announced include
aluminium, cement, chlor-alkali, fertilizer, iron and steel, pulp and
paper, petrochemicals, petroleum refining and textiles; targets for the
first compliance years were published by MoEFCC through greenhouse-gas
emission-intensity target rules in 2025 (verify the final notification
and the sector list). Farms are not obligated entities.

## Offset mechanism

Non-obligated entities may register **projects** that reduce, remove or
avoid emissions and, after verification, receive CCCs that obligated
entities (and others, once permitted) can buy. BEE's detailed procedure
for the offset mechanism lists eligible sectors; the list published by
BEE includes energy, industry, agriculture, waste handling and disposal,
forestry, transport, construction, fugitive emissions, solvent use and
carbon capture, utilization and storage (verify the current list). BEE
has been publishing offset **methodologies** sector by sector; the first
sets released for consultation in 2025 covered items such as renewable
energy with storage, green hydrogen, industrial energy efficiency,
landfill methane recovery, mangrove afforestation and reforestation and
compressed biogas (verify which methodologies are final and whether an
afforestation, reforestation or agroforestry methodology for private
agricultural land has been approved).

Until a methodology covering the activity is approved, no project of that
type can be registered, which is why CarbonCreditBuy returns
`requires_methodology_assessment` for tree plantation, agroforestry and
soil carbon rather than anything more encouraging.

## What a project needs

| Requirement | Meaning for a farm or an aggregator |
|---|---|
| Approved offset methodology applicable to the activity | Check BEE's list; if none fits, the project cannot proceed under the CCTS yet |
| Project design and registration | A project proponent (often an aggregator for smallholders) prepares the design document and registers with BEE/the registry |
| Baseline and additionality | Document previous land use and demonstrate the project would not happen without carbon revenue ([../../concepts/additionality.md](../../concepts/additionality.md)) |
| Monitoring plan | Measurements on sample plots (girth/DBH, height, survival), remote sensing support, leakage assessment, record keeping |
| Validation and verification | By a BEE-accredited ACVA, at registration and at each issuance |
| Permanence | Methodology-specific buffers or monitoring periods ([../../concepts/permanence.md](../../concepts/permanence.md)) |
| Issuance and trading | CCCs issued to the registry account; sold through the designated platforms |

Costs of design, validation, verification and registry fees are
significant relative to the value of credits from a single small plot;
in practice, smallholders participate through aggregated or grouped
projects run by cooperatives, companies or NGOs.

## Relationship to other mechanisms

- **Green Credit Programme**: separate ministry, unit and purpose; a Green
  Credit is not a CCC and cannot be used for CCTS compliance
  ([GREEN_CREDIT.md](GREEN_CREDIT.md)).
- **International voluntary standards (Verra, Gold Standard)**: separate
  registries; India has signalled that projects should avoid double
  counting between the domestic market and international transfers, and
  the Ministry has published lists of activities eligible for Article 6.2
  transfers (verify). A project cannot sell the same tonne twice.
- **Perform, Achieve and Trade (PAT)** and **Renewable Energy
  Certificates**: predecessor and parallel instruments administered by
  BEE and the power sector; not relevant to farms.

## What CarbonCreditBuy shows

A programme card "Carbon Credit Trading Scheme (offset mechanism)" with
status `requires_methodology_assessment`, the requirements above,
references to BEE, and the `distinct_from: [in-gcp]` relation. The
carbon estimate shown alongside is a Tier 1 scenario; it is not a
baseline, not a monitored value and not something an ACVA would verify
as-is, and the readiness checklist lists what would have to be added.

## Sources

- Bureau of Energy Efficiency — Indian Carbon Market / CCTS pages,
  detailed procedures, ACVA regulations and offset methodologies:
  <https://beeindia.gov.in/>
- Ministry of Power — CCTS notification and amendments:
  <https://powermin.gov.in/>
- MoEFCC — emission-intensity target rules: <https://moef.gov.in/>
- Press Information Bureau releases on the CCTS: <https://pib.gov.in/>
