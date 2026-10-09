# Example: pecan agroforestry in Houston County, Georgia (synthetic)

An 8-hectare (≈ 19.8-acre) pecan planting in the Georgia Coastal Plain,
where pecan orchards and row crops share the landscape. **The farm is
invented**: the polygon around 32.5° N, 83.7° W does not correspond to a
real property, and the 1,200 trees planted in 2021 are a round number
chosen to illustrate the US outputs (acres first, USD, COMET-Farm as the
methodology reference, voluntary ARR methodologies and NRCS conservation
programmes). A density of 150 trees/ha is roughly twice the 70 trees/ha
orchard reference in `config/species/species.yaml`, which exercises the
density-scaling clamp.

| Property | Value |
|---|---|
| Demo plot id (pre-seeded in demo mode) | `PLT-DEMOUS` |
| Country | `US` (Georgia, Houston County) |
| Area | ≈ 8.0 ha (≈ 19.8 acres), six-vertex polygon |
| Species | Pecan (*Carya illinoinensis*), `species_id: pecan` |
| Trees | 1,200 planted in 2021 → 150 trees/ha |
| Survival rate | 0.90 (user-reported) |
| Measurements | no DBH, no height (Tier 1 path; `temperate_generic` allometry is still `pending`) |
| Climate default | `warm_temperate_moist` |

## What the walkthrough shows

- `GET /regions` confirms the US region reports `area: acre` first.
- `POST /plots/{id}/analyze` requests all five layers including `terrain`.
- `POST /plots/{id}/carbon-estimate` prints the parameters that are not yet
  `verified`; in v0.1 that includes the temperate growth increment and the
  pecan wood density, which is why the result is labelled `medium`
  confidence at best and must be cross-checked with COMET-Farm
  ([COMET-Farm](../../docs/regions/US/PROGRAMS.md#usda-comet-farm-and-comet-planner)).
- `GET /plots/{id}/policy-eligibility?activity=agroforestry` returns
  `potentially_applicable` for COMET-Farm and NRCS EQIP/CSP (incentives, not
  credits) and `requires_methodology_assessment` for voluntary ARR
  methodologies such as Verra VM0047
  ([voluntary-market methodologies](../../docs/regions/US/PROGRAMS.md#voluntary-market-methodologies)).
- `GET /plots/{id}/market-scenario` shows USD scenarios next to nut yield
  and conservation payments as separate lines.
- `POST /simulate` compares the same planting under the IN / US / EU climate
  defaults and returns `share_params` without coordinates.

Run it:

```bash
make dev
cd examples/usa-agroforestry
chmod +x curl.sh && ./curl.sh
```

## Files

| File | Endpoint |
|---|---|
| `plot.request.json` | `POST /api/v1/plots` |
| `trees.request.json` | `POST /api/v1/plots/{plot_id}/trees` |
| `carbon-estimate.request.json` | `POST /api/v1/plots/{plot_id}/carbon-estimate` |
| `simulate.request.json` | `POST /api/v1/simulate` |
| `curl.sh` | Scripted walkthrough |

## Why pecan

Pecan is a long-lived nut tree with a documented role in US agroforestry
(alley cropping, silvopasture) and strong county-level statistics in USDA
NASS, so the "other farm income" line can be filled from public data
([USDA NASS](../../docs/regions/US/DATA_SOURCES.md#usda-nass-quick-stats-county-crop-statistics)). It is also a
species where the Tier 1 broad-category increment is a poor fit for a
managed orchard, which makes it a good test case for the validation
protocol in [research/validation/README.md](../../research/validation/README.md).
