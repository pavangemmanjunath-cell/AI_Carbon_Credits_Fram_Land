# United States (US)

This page summarizes how CarbonCreditBuy behaves for plots in the United States and what a farmer, adviser or researcher
in
the US should expect from it. Configuration lives in
[`config/regions/US.yaml`](../../../config/regions/US.yaml) and
[`config/policies/US.yaml`](../../../config/policies/US.yaml). The sister regions are [India](../IN/README.md) and the
[European Union](../EU/README.md).

## Regional settings

| Setting | Value | Note |
| --- | --- | --- |
| Primary key | `US` (ISO 3166-1 alpha-2) | `+1` is a UX alias only; other countries share that calling code |
| Units | Acre first, hectare second, for display | The engine and the API work in hectares. In **Settings**, **Area units** can force hectares first. See the note on tons below |
| Currency | USD ($), locale `en-US` | Price scenarios are in dollars per metric ton of CO₂e |
| Languages | English and Spanish in v0.1 | Other languages are open starter issues ([starter-issues.md](../../community/starter-issues.md)) |
| Admin levels | state, county | From reverse geocoding when the server looks the place up; the Census Geocoder adapter that would give exact county codes is built but not called yet ([DATA_SOURCES.md](DATA_SOURCES.md)) |
| Default climate zone | `warm_temperate_moist` | A continental default; the US spans several climate zones. Derived per plot in live mode, otherwise the Evidence chain says "region-default" |
| Map default | Center 39.5 N, 98.35 W, zoom 3.8 | |
| Bounding box | West -125.0, south 24.4, east -66.9, north 49.4 | Covers the contiguous states. Alaska, Hawaii and the territories lie outside it, so CarbonCreditBuy cannot guess the region from a point there: choose the country explicitly |

**Tons.** In the US a "ton" usually means the short ton of 2,000 pounds, which is about 0.907 metric tons. Every
CarbonCreditBuy
figure is in metric tons (tonnes) of CO₂e. Check which one a program, a price quote or another tool uses before you
compare numbers.

**Place search.** When the selected country is the United States, the search box asks the geocoder for results in the
US only, and it starts after three characters.

## Data sources used for US plots

ESA WorldCover for land cover, Copernicus Sentinel-2 for vegetation indices, Open-Meteo for climate normals, ISRIC
SoilGrids for soil organic carbon and Nominatim for place search. USDA NASS Quick Stats (county crop statistics) and the
US Census Bureau Geocoder (county lookup) have adapters, but no service calls them yet, so the "other farm income"
context stays empty in v0.1. Details, licenses and access notes are in [DATA_SOURCES.md](DATA_SOURCES.md) and
[`docs/licensing/DATA_LICENSES.md`](../../licensing/DATA_LICENSES.md).

## Map imagery

The map's **Satellite** view starts with the USGS "Imagery Only" layer for US plots. It is mostly National Agricultural
Imagery Program (NAIP) aerial photography, public domain, and needs no key. Outside the US the default is the global
Sentinel-2 mosaic from EOX, and a deployer who holds an Esri license can add Esri World Imagery, for viewing only. A
person can pick another provider under **Settings**, **Map imagery**. Imagery is for viewing: CarbonCreditBuy's own
analysis
uses Sentinel-2 scenes and WorldCover, not map tiles. Licenses, attribution texts and zoom limits are in
[MAP_LICENSES.md](../../licensing/MAP_LICENSES.md) and
[`config/imagery/providers.yaml`](../../../config/imagery/providers.yaml). The US details, and what is still
unconfirmed, are in [DATA_SOURCES.md](DATA_SOURCES.md#imagery-for-the-map).

## Programs screened

| Program | Authority | What CarbonCreditBuy says |
| --- | --- | --- |
| USDA COMET-Farm (methodology reference) | USDA and Colorado State University | `potentially_applicable` for tree plantation, agroforestry, cropland practice and grazing: a whole-farm greenhouse-gas tool you can use to cross-check this estimate. It is not a credit scheme |
| Voluntary-market afforestation and reforestation methodologies | Verra VCS, American Carbon Registry, Climate Action Reserve | `requires_methodology_assessment`: an approved methodology, baseline, additionality, leakage and permanence arrangements, monitoring and third-party verification are needed before any credit exists |
| USDA NRCS conservation programs (EQIP and CSP) | USDA Natural Resources Conservation Service | `potentially_applicable`: cost-share and stewardship payments exist for practices such as windbreaks, alley cropping and riparian buffers. These are incentives, not carbon credits |

Each program is described, with its sources and its open questions, in [PROGRAMS.md](PROGRAMS.md). Every US
screening result carries the sentence "Initial screening only — not an eligibility determination. Voluntary-market
credits require an approved methodology, verification and registry issuance."

CarbonCreditBuy keeps **credits** (a tradable unit issued by a registry) and **incentives** (a payment or cost-share)
apart.
A USDA payment is never shown as a carbon value, and a voluntary credit is never implied by a USDA program.

## Trees of different ages

The **Tree age** page of the web app (`POST /api/v1/tree-age/assess` in the API) takes the number and age of trees you
already have and answers two questions: how much carbon trees of that age hold, and which rules treat trees of that age
differently. The rules come from [`config/tree-age/rules.yaml`](../../../config/tree-age/rules.yaml), each with its
sources and the date they were opened. For a US user the engine returns ten: seven for the United States and three
global ones. None of them sets an age threshold. They turn on whether the trees are new, where they stand and, for city
rules, trunk size or species.

| Where the trees stand | What the rules say | Rule ids |
| --- | --- | --- |
| Farm or other land that is not forest | Standards credit new planting, or avoided loss against a baseline, and not the carbon that trees already hold. No rule gives standing farm trees a credit route, so the outlook is "not eligible" | `global-verra-vm0047-arr`, `global-gold-standard-luf-ar` |
| Forest | Improved forest management protocols can credit the extra carbon an existing forest keeps compared with a baseline, over a long commitment. The outlook is "conditional" | `us-car-forest-protocol-ifm`, `us-acr-ifm-non-federal-v2-1`, `us-family-forest-carbon-vm0045` |
| Town or city | City Forest Credits can credit an existing urban stand that is at risk of being cleared, for a 40-year preservation commitment. Planting protocols credit only new trees. City ordinances protect trees by size or species | `us-cfc-preservation-protocol`, `us-cfc-afforestation-protocol`, `us-or-portland-heritage-trees`, `us-ca-los-angeles-protected-trees` |

The Portland and Los Angeles rules are municipal examples that stand for "check your own city's rules"; the request has
no city, so the page lists them as not applying. The outlook is screening information, never a promise: it does not
say "eligible", an estimate is never a credit, and the carbon figure on the page is a scenario with `certified: false`.
The full list, with sources and the open questions, is in [PROGRAMS.md](PROGRAMS.md#rules-by-tree-age) and in the
[research note](../../research/tree-age-carbon-rules.md). A production deployment withholds any rule that is not yet
confirmed from a primary source; at the time of writing all ten are marked `verified`.

## What farmers in the US should expect

- **An estimate, not a payment.** The platform tells you roughly how much carbon your trees may remove each year, as a
  range, with the sources of every number. It does not register you anywhere, issue credits or promise income
  ([carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md)).
- **Three separate values.** Carbon removal in tCO₂e/yr; an indicative value in dollars under three illustrative price
  scenarios (global voluntary-market ranges, marked `pending` and meant to be reviewed each release against public price
  reports); and other farm income (nut and fruit yield, timber, conservation program payments) kept apart and never
  added to the others. In v0.1 you cannot enter income values yet.
- **A checklist.** The readiness score names what you would still need: tree measurements (diameter, height), records
  of how the land was used before planting, management history, survival counts and ownership documents.
- **Honesty about small plots.** At 10 m resolution one acre is about 40 satellite pixels, so boundary effects are
  large for small plots; the data-quality notes say so.
- **Your location.** The design keeps the exact boundary out of public views and uses a point rounded to roughly 5 km
  ([farmer data](../../privacy/farmer-data.md)). Version 0.1 has no sign-in, so read
  [Privacy and your data](../../user-guide/faq.md#privacy-and-your-data) before you enter a real boundary on a shared
  server.
- **One more caution for temperate trees.** The growth values are broad Tier 1 working values, and the equation used
  when
  you enter a trunk diameter was built for tropical trees. See [METHODOLOGIES.md](METHODOLOGIES.md) before you read
  anything into a diameter-based number for walnut, pecan, apple or poplar.

## Species in the v0.1 table for the US

Black walnut (*Juglans nigra*), pecan (*Carya illinoinensis*), eucalyptus, apple (*Malus domestica*) and poplar
(*Populus* spp.) ([`config/species/species.yaml`](../../../config/species/species.yaml)). Other species can be added
once each has a documented growth value, a wood density and an allometric equation
([adding a species](../../developer-guide/adding-a-species-or-parameter.md#adding-a-species)).

## Related pages

[PROGRAMS.md](PROGRAMS.md) · [DATA_SOURCES.md](DATA_SOURCES.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[Carbon credit vs estimate](../../concepts/carbon-credit-vs-estimate.md) ·
[Policy references research note](../../research/policy-references.md) ·
[Tree age research note](../../research/tree-age-carbon-rules.md) ·
[Imagery providers research note](../../research/imagery-providers.md)
