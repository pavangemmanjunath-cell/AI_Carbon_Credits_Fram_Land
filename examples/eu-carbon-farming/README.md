# Example: olive grove in Córdoba province, Andalusia (synthetic)

A 5-hectare olive grove on the Guadalquivir plain, the heart of Spain's
olive sector. **The farm is invented**: the polygon around 37.6° N, 4.8° W
is not a real parcel and the 900 trees planted in 2020 (180 trees/ha, a
moderately intensive layout) were chosen to show the EU outputs: euros,
CRCF certification status, CAP eco-scheme screening and the reminder that
an estimate is never automatically certifiable.

| Property | Value |
|---|---|
| Demo plot id (pre-seeded in demo mode) | `PLT-DEMOEU` |
| Country | `ES` on the plot (member states keep their ISO code); policy rules resolve to `EU` |
| Area | ≈ 5.0 ha, five-vertex polygon |
| Species | Olive (*Olea europaea*), `species_id: olive` |
| Trees | 900 planted in 2020 → 180 trees/ha |
| Survival rate | 0.92 (user-reported) |
| Measurements | no DBH, no height (Tier 1 path) |
| Climate zone | derived from climate normals: `warm_temperate_dry` (demo mode uses synthetic normals for this location; live mode uses Open-Meteo). The EU region default `cool_temperate_moist` is only used when no normals are available |

The last row matters: the climate zone selects the growth parameters, and
the EU region default (`cool_temperate_moist`) would be a poor match for
Andalusia. The zone is derived from the plot's own climate normals
(synthetic in demo mode, Open-Meteo in live mode), and the default is only a
fallback. This is the clearest illustration of why
[results-explained.md](../../docs/user-guide/results-explained.md)
asks users to check the `climate_zone` field before anything else.

## What the walkthrough shows

- `POST /plots` with `country: "ES"`; the response keeps `ES` and the
  region name, while `GET /plots/{id}/policy-eligibility` evaluates
  `config/policies/EU.yaml`.
- CRCF returns `requires_certification` with the QU.A.L.ITY criteria in
  the requirements list; CAP eco-schemes return `potentially_applicable`
  (incentives, not credits); voluntary standards return
  `requires_methodology_assessment`
  ([the CRCF](../../docs/regions/EU/PROGRAMS.md#the-crcf),
  [CAP eco-schemes](../../docs/regions/EU/PROGRAMS.md#cap-eco-schemes-and-agri-environment-climate-measures)).
- `GET /plots/{id}/market-scenario` carries the basis note that CRCF units
  are not yet traded and that EU ETS allowance prices do not apply to farm
  removals.
- `POST /plots/{id}/report` with `format: "json"` lists the report sections
  so that integrators can see the structure.
- `GET /attribution` prints the strings a deployment must display
  ([docs/licensing/ATTRIBUTION.md](../../docs/licensing/ATTRIBUTION.md)).

Run it:

```bash
make dev
cd examples/eu-carbon-farming
chmod +x curl.sh && ./curl.sh
```

## Files

| File | Endpoint |
|---|---|
| `plot.request.json` | `POST /api/v1/plots` |
| `trees.request.json` | `POST /api/v1/plots/{plot_id}/trees` |
| `carbon-estimate.request.json` | `POST /api/v1/plots/{plot_id}/carbon-estimate` |
| `simulate.request.json` | `POST /api/v1/simulate` (uses `country: "EU"`; member-state codes are accepted and resolve to EU rules) |
| `curl.sh` | Scripted walkthrough |

## Why olive

Olive groves cover a large share of Andalusian farmland, are the subject of
several voluntary carbon-farming pilots, and are a case where the Tier 1
increment for broadleaf stands overstates growth for a pruned, low-stature
crop; the species entry therefore carries an `increment_multiplier` of
0.7 flagged as a project assumption. Field data from olive systems is one
of the priorities in [research/validation/README.md](../../research/validation/README.md).
