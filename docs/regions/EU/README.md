# European Union (EU)

This page summarizes how CarbonCreditBuy behaves for plots in the European Union and what a farmer, adviser or researcher in
a member state should expect from it. Configuration lives in
[`config/regions/EU.yaml`](../../../config/regions/EU.yaml) and
[`config/policies/EU.yaml`](../../../config/policies/EU.yaml). The sister regions are [India](../IN/README.md) and the
[United States](../US/README.md).

The EU is a bloc, not a country. CarbonCreditBuy keeps one set of rules for the bloc and maps each member state to it, so a
farmer in Germany and one in Spain see the same EU programs. National rules, such as a member state's Common
Agricultural Policy (CAP) plan, are not screened.

## Regional settings

| Setting | Value | Note |
| --- | --- | --- |
| Primary key | `EU` | A bloc id. The 27 member states resolve to it by their ISO 3166-1 alpha-2 codes: AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES and SE. A plot can carry its own member-state code, for example `DE`, and the API and the policy engine map it to `EU` |
| Calling codes | None for the bloc | `+49`, `+33`, `+34`, `+39`, `+31`, `+48`, `+351` and `+43` are UX aliases for DE, FR, ES, IT, NL, PL, PT and AT. They are never keys |
| Units | Hectare first, acre second | |
| Currency | EUR (€), locale `en-IE` | Prices are shown in euros for every member state, including those whose national currency is different |
| Languages | English, German, French and Spanish in v0.1 | Other languages are open starter issues ([starter-issues.md](../../community/starter-issues.md)) |
| Admin levels | country, NUTS 2, NUTS 3 | Listed in the region file; version 0.1 does not use them. NUTS is Eurostat's regional classification |
| Default climate zone | `cool_temperate_moist` | A temperate default. Derived per plot in live mode, otherwise the Evidence chain says "region-default". See the note on olive and eucalyptus in [METHODOLOGIES.md](METHODOLOGIES.md) |
| Map default | Center 50.0 N, 10.0 E, zoom 3.8 | |
| Bounding box | West -10.5, south 34.5, east 31.6, north 71.2 | Covers the member states in Europe, from Portugal to Finland. Cyprus and the outermost regions (for example Madeira, the Azores and the Canary Islands) lie outside it, so CarbonCreditBuy cannot guess the region from a point there: choose the country explicitly |

**Place search.** When the selected country is the European Union, the search box does not restrict the geocoder to one
country, and it starts after three characters. Results may therefore include places outside the EU.

## Data sources used for EU plots

ESA WorldCover for land cover, Copernicus Sentinel-2 for vegetation indices, Open-Meteo for climate normals, ISRIC
SoilGrids for soil organic carbon and Nominatim for place search. The region file names no source of crop statistics, and
no adapter exists for one, so the "other farm income" context is empty. Eurostat is a candidate. Details, licenses and
access notes are in [DATA_SOURCES.md](DATA_SOURCES.md) and
[`docs/licensing/DATA_LICENSES.md`](../../licensing/DATA_LICENSES.md).

## Map imagery

The map's **Satellite** view starts with a national open orthophoto where CarbonCreditBuy has a verified one: France (IGN
BD ORTHO, 20 cm), Spain (IGN PNOA, 25 to 50 cm) and the Netherlands (PDOK, 8 cm). For every other member state it starts
with the global Sentinel-2 mosaic from EOX, which has 10 m pixels and shows 2016: a village or a large field is visible,
individual trees are not. A deployer who holds an Esri license can add Esri World Imagery, for viewing only. A person
can pick another provider under **Settings**, **Map imagery**. Imagery is for viewing: CarbonCreditBuy's own analysis uses
Sentinel-2 scenes and WorldCover, not map tiles. Licenses, attribution texts and zoom limits are in
[MAP_LICENSES.md](../../licensing/MAP_LICENSES.md) and
[`config/imagery/providers.yaml`](../../../config/imagery/providers.yaml). The EU details, and what is still
unconfirmed, are in [DATA_SOURCES.md](DATA_SOURCES.md#imagery-for-the-map).

## Programs screened

| Program | Authority | What CarbonCreditBuy says |
| --- | --- | --- |
| Carbon Removals and Carbon Farming Certification Framework (CRCF) | European Commission, Regulation (EU) 2024/3012 | `requires_certification` for tree plantation, agroforestry, soil carbon and cropland practice: activities must meet the quantification, additionality, long-term storage and sustainability criteria and be certified by a recognized scheme |
| CAP eco-schemes and agri-environment-climate measures | Member-state paying agencies | `potentially_applicable` for tree plantation, agroforestry and cropland practice: national plans include eco-schemes and investment support. These are incentives, not carbon credits |
| Voluntary carbon-farming standards and national labels | Verra VCS, Gold Standard, Label Bas-Carbone (France) and others | `requires_methodology_assessment`: an approved methodology, baseline, additionality, permanence, monitoring and third-party verification are needed before any credit exists |

Each program is described, with its sources and open questions, in [PROGRAMS.md](PROGRAMS.md). Every EU screening
result carries the sentence "Initial screening only — not an eligibility determination. Under the CRCF a calculated
estimate is never automatically certifiable; certification by a recognised scheme is required."

**A CarbonCreditBuy estimate is never automatically certifiable under the CRCF.** CarbonCreditBuy does no baseline, no monitoring, no
verification and no certification, and it is not a recognized certification scheme. A CRCF unit exists only after a
recognized scheme certifies an activity. As of the research date, 2026-10-05, the Commission had adopted the
carbon-farming certification methodologies on 10 July 2026 and they were not confirmed in force; certification schemes
can apply for recognition only after that ([Commission news](https://climate.ec.europa.eu/news-other-reads/news/commission-adopts-certification-methodologies-carbon-farming-under-crcf-regulation-2026-07-10_en)).
See [PROGRAMS.md](PROGRAMS.md#the-crcf).

## Trees of different ages

The **Tree age** page of the web app (`POST /api/v1/tree-age/assess` in the API) takes the number and age of trees you
already have and answers two questions: how much carbon trees of that age hold, and which rules treat trees of that age
differently. The rules come from [`config/tree-age/rules.yaml`](../../../config/tree-age/rules.yaml), each with its
sources and the date they were opened. A user in any member state sees seven: four for the EU and three global ones.
None sets an age threshold.

| Rule id | What it says | Status |
| --- | --- | --- |
| `eu-crcf-regulation-2024-3012` | Under the CRCF only net removals above a baseline, from an activity of at least five years, can be certified, and the activity must go beyond legal requirements. Outcome for existing trees: `conditional` | In force, `verified` |
| `eu-crcf-carbon-farming-delegated-act-2026` | The Commission adopted carbon-farming certification methodologies on 10 July 2026. Until they enter into force, certification schemes cannot apply for recognition for these activities | `proposed`, `pending`. Flagged in development, **withheld in production** |
| `eu-old-growth-forests-guidelines` | Non-binding guidance on identifying and strictly protecting old-growth forests with structural indicators. No numeric age threshold | In force, `verified` |
| `eu-de-berlin-baumschutzverordnung` | A municipal example: Berlin protects listed trees by trunk circumference (80 cm at 1.30 m, or 50 cm on a stem of a multi-stem tree), not age. It applies when the state is Berlin (`DE-BE`) | In force, `verified` |
| `global-icvcm-ccp-additionality`, `global-verra-vm0047-arr`, `global-gold-standard-luf-ar` | The three global standards also shown in the other regions: credits reward new, additional removals, not the carbon that standing trees hold | In force, `verified` |

The credit outlook for existing trees in the EU reads "conditional", and it rests on the CRCF Regulation, which sets
conditions rather than a yes or no. It never reads "eligible": certification by a recognized scheme is required, and an
estimate is never automatically certifiable. The full list, with sources and the open questions, is in
[PROGRAMS.md](PROGRAMS.md#rules-by-tree-age) and in the
[research note](../../research/tree-age-carbon-rules.md#european-union).

## What farmers in the EU should expect

- **An estimate, not a payment.** The platform tells you roughly how much carbon your trees may remove each year, as a
  range, with the sources of every number. It does not register you anywhere, issue credits or promise income
  ([carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md)).
- **Three separate values.** Carbon removal in tCO₂e/yr; an indicative value in euros under three illustrative price
  scenarios, marked `pending`; and other farm income (fruit, olive and nut yield, timber, CAP eco-scheme payments),
  kept apart and never added to the others. In v0.1 you cannot enter income values yet. The price file notes that
  voluntary carbon-farming removals are the basis and that CRCF units are not yet traded
  ([`carbon-price-scenarios.yaml`](../../../config/market/carbon-price-scenarios.yaml)).
- **A national picture is yours to add.** Your member state's CAP plan, its forestry rules and any national label are
  not screened. Ask your paying agency and your forestry authority.
- **A checklist.** The readiness score names what you would still need: tree measurements, records of the land's use
  before planting, management history, survival counts and ownership documents.
- **Honesty about small plots.** At 10 m resolution a one-hectare orchard is about one hundred pixels, so boundary
  effects are large for small plots; the data-quality notes say so.
- **Your location.** The design keeps the exact boundary out of public views and uses a point rounded to roughly 5 km
  ([farmer data](../../privacy/farmer-data.md)). Version 0.1 has no sign-in, so read
  [Privacy and your data](../../user-guide/faq.md#privacy-and-your-data) before you enter a real boundary on a shared
  server. An organization that operates CarbonCreditBuy in the EU is responsible for its own data-protection obligations;
  the privacy pages are not legal advice.
- **A caution for temperate trees.** The growth values are broad Tier 1 working values, and the equation used when you
  enter a trunk diameter was built for tropical trees. See [METHODOLOGIES.md](METHODOLOGIES.md).

## Species in the v0.1 table for the EU

Oak (*Quercus robur* and *Quercus petraea*), apple (*Malus domestica*), olive (*Olea europaea*), eucalyptus and poplar
(*Populus* spp.) ([`config/species/species.yaml`](../../../config/species/species.yaml)). Nordic and boreal species
are not in the table. Other species can be added once each has a documented growth value, a wood density and an
allometric equation ([adding a species](../../developer-guide/adding-a-species-or-parameter.md#adding-a-species)).

## Related pages

[PROGRAMS.md](PROGRAMS.md) · [DATA_SOURCES.md](DATA_SOURCES.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[Carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md) ·
[Policy references research note](../../research/policy-references.md) ·
[Tree age research note](../../research/tree-age-carbon-rules.md) ·
[Imagery providers research note](../../research/imagery-providers.md)
