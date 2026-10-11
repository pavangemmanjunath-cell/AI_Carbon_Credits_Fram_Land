# India (IN)

India is the first region CarbonCreditBuy was designed for. This page summarizes
how the platform behaves for Indian plots and what a farmer, advisor or
researcher in India should expect from it. Configuration lives in
[`config/regions/IN.yaml`](../../../config/regions/IN.yaml) and
[`config/policies/IN.yaml`](../../../config/policies/IN.yaml).

## Regional settings

| Setting | Value | Note |
|---|---|---|
| Primary key | `IN` (ISO 3166-1 alpha-2) | `+91` is a UX alias only |
| Units | hectare, with acre as secondary | Local units (guntha, bigha, cent, kanal) vary by state and are not converted automatically; a contributor can add a per-state table ([adding-a-region.md](../../developer-guide/adding-a-region.md)) |
| Currency | INR (₹), locale `en-IN` (lakh/crore grouping) | |
| Languages | English, Hindi, Kannada in v0.1; Tamil, Telugu, Marathi, Bengali and Punjabi are open starter issues | [starter-issues.md](../../community/starter-issues.md) |
| Admin levels | state, district | From reverse geocoding; district drives crop statistics |
| Default climate zone | `tropical_dry` (semi-arid Deccan default) | Derived per plot from Open-Meteo normals in live mode; India spans tropical wet (Western Ghats, North-East), tropical moist, tropical dry and mountain zones |
| Map default | center 20.59 N, 78.96 E, zoom 4.5 | |

## Data sources used for Indian plots

ESA WorldCover for land cover, Copernicus Sentinel-2 via STAC for
vegetation indices, Open-Meteo for climate normals, ISRIC SoilGrids for
soil organic carbon, Nominatim for place search, and data.gov.in for
district crop-production statistics. Details, licenses and access notes
are in [DATA_SOURCES.md](DATA_SOURCES.md) and
[../../licensing/DATA_LICENSES.md](../../licensing/DATA_LICENSES.md).

## Programmes screened

| Programme | Authority | What CarbonCreditBuy says |
|---|---|---|
| Green Credit Programme (GCP) | MoEFCC; administrator ICFRE | `requires_assessment` for tree plantation and agroforestry: the notified tree-plantation methodology targets identified degraded land parcels made available through the programme, so applicability to private farmland must be confirmed with the administrator. See [GREEN_CREDIT.md](GREEN_CREDIT.md) |
| Carbon Credit Trading Scheme (CCTS), offset mechanism | Bureau of Energy Efficiency, Ministry of Power | `requires_methodology_assessment`: a project needs an approved offset methodology, baseline, additionality, monitoring and verification by an accredited agency before any Carbon Credit Certificate exists. See [CCTS.md](CCTS.md) |
| State agroforestry and horticulture incentives | State governments (for example Karnataka's Krishi Aranya Protsaha Yojane) | `potentially_applicable`: per-surviving-tree incentives and subsidized seedlings exist in several states; conditions vary. See [INCENTIVES.md](INCENTIVES.md) |

Every Indian screening result carries the sentence **"Green Credits (GCP)
and carbon credits (CCTS) are separate mechanisms."** This is not a
stylistic choice: the two schemes have different administrators, units,
purposes and rules, and conflating them is the most common
misunderstanding we encounter.

## What farmers in India should expect

- **An estimate, not a payment.** The platform tells you roughly how much
  carbon your trees may be removing each year, as a range, with the
  sources of every number. It does not register you anywhere, does not
  issue credits and does not promise income.
- **Three separate values.** Carbon removal in tCO₂e/yr; an indicative
  value in rupees under three illustrative price scenarios (India has no
  public, liquid price for agroforestry removals yet, so these are global
  voluntary-market ranges converted to INR and marked `pending`); and
  other farm income (fruit, intercrop, timber, incentives) kept apart.
- **A checklist.** The readiness score names what you would still need:
  tree measurements (girth at breast height, height), land-use records
  (RTC/pahani or equivalent, old photographs, crop records), management
  history, and survival counts.
- **Honesty about small plots.** At 10 m resolution a one-hectare orchard
  is about one hundred pixels; mixed-pixel effects at the boundary are
  real, and the data-quality warnings say so.
- **Your location stays yours.** The exact boundary is private; shared
  views use a point rounded to roughly 5 km
  ([../../privacy/farmer-data.md](../../privacy/farmer-data.md)).

## Species in the v0.1 table for India

Mango, teak, neem, eucalyptus, poplar and a mixed-native-species entry
([`config/species/species.yaml`](../../../config/species/species.yaml)).
Coconut, arecanut, cashew, sandalwood, bamboo (a grass; separate
methodology considerations), *Melia dubia* and casuarina are frequently
requested and are listed as starter issues; each needs a documented
allometric equation and wood density before it can be added
([adding a species](../../developer-guide/adding-a-species-or-parameter.md#adding-a-species)).

## Related pages

[GREEN_CREDIT.md](GREEN_CREDIT.md) · [CCTS.md](CCTS.md) ·
[DATA_SOURCES.md](DATA_SOURCES.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[INCENTIVES.md](INCENTIVES.md)
