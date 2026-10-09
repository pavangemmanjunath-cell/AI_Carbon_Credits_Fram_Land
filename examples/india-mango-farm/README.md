# Example: mango orchard near Doddaballapura, Karnataka (synthetic)

A small horticultural plot on the semi-arid Deccan plateau, typical of the
Bengaluru Rural district. **The farm is invented.** The polygon is drawn
around 13.29° N, 77.54° E on land that may be anything in reality; the tree
count, planting year and survival rate were chosen to be plausible for a
young commercial mango orchard, not measured anywhere. Use this example to
learn the API, to test the engines, and to see the India-specific outputs
(hectares with acres as secondary unit, INR, Green Credit Programme and
CCTS screening).

| Property | Value |
|---|---|
| Demo plot id (pre-seeded in demo mode) | `PLT-DEMOIN` |
| Country | `IN` (Karnataka, Bengaluru Rural) |
| Area | ≈ 2.13 ha (≈ 5.26 acres), six-vertex polygon |
| Species | Mango (*Mangifera indica*), `species_id: mango` |
| Trees | 420 planted in 2023 → ≈ 197 trees/ha |
| Survival rate | 0.85 (user-reported) |
| Measurements | no DBH, no height (Tier 1 path) |
| Climate default | `tropical_dry` (derived from Open-Meteo normals in live mode) |

## What the walkthrough shows

1. `POST /plots` — the plot is accepted and the response contains both the
   exact `centroid` (owner only) and the `public_centroid` rounded to 0.05°,
   which is what any public view would show (13.30 N, 77.55 E).
2. `POST /plots/{id}/analyze` — ESA WorldCover class shares (expect a
   cropland/tree-cover mix for a young orchard), Sentinel-2 NDVI/NDMI with a
   three-season trend, Open-Meteo climate normals and SoilGrids SOC.
3. `POST /plots/{id}/trees` — the inventory confidence is `medium` because
   count, species and age are supplied but DBH and height are missing.
4. `POST /plots/{id}/carbon-estimate` — a Tier 1 gain-loss range in
   tCO₂e/yr with `certified: false`, the parameters used (growth increment
   for tropical dry Asia is `pending` verification in v0.1), and a
   readiness score listing the missing evidence (DBH, baseline records,
   management history).
5. `GET /plots/{id}/policy-eligibility` — the Green Credit Programme returns
   `requires_assessment` (the 2024 tree-plantation methodology targets
   identified degraded land parcels, so applicability to private farmland
   must be confirmed with ICFRE) and the CCTS offset mechanism returns
   `requires_methodology_assessment`. The response states that the two
   mechanisms are distinct.
6. `GET /plots/{id}/market-scenario` — three INR price scenarios from
   `config/market/carbon-price-scenarios.yaml`, shown next to (never summed
   with) fruit income, which the API leaves `null` until district statistics
   or farmer records are supplied.
7. `POST /plots/{id}/report` and `POST /simulate` — the report and the
   30-year what-if, including the IN / US / EU comparison.

Run it:

```bash
make dev                      # or: docker compose up
cd examples/india-mango-farm
chmod +x curl.sh && ./curl.sh
```

## Reading the numbers

For a 3-year-old orchard the central estimate is low and the range wide:
the engine ramps the increment linearly over the first six years, scales by
stocking density relative to the 150 trees/ha reference, applies survival,
and brackets the result with ±30 % Tier 1 uncertainty
([carbon-engine.md](../../docs/architecture/carbon-engine.md)). Supplying
measured DBH and height later switches the path to Chave 2014 allometry and
narrows the range. Nothing in the output is a credit; see
[docs/regions/IN/GREEN_CREDIT.md](../../docs/regions/IN/GREEN_CREDIT.md)
and [docs/regions/IN/CCTS.md](../../docs/regions/IN/CCTS.md) for what a
real project would need.

## Files

| File | Endpoint |
|---|---|
| `plot.request.json` | `POST /api/v1/plots` |
| `trees.request.json` | `POST /api/v1/plots/{plot_id}/trees` |
| `carbon-estimate.request.json` | `POST /api/v1/plots/{plot_id}/carbon-estimate` (`inventory_id: null` → latest inventory) |
| `simulate.request.json` | `POST /api/v1/simulate` |
| `curl.sh` | Scripted walkthrough of all steps |
