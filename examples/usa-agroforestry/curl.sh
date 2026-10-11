#!/usr/bin/env bash
# CarbonCreditBuy — end-to-end walkthrough for the synthetic US pecan agroforestry farm.
#
# Usage:
#   ATLAS_API=http://localhost:8000/api/v1 ./curl.sh
#   ATLAS_API_KEY=... ./curl.sh          # when the server has ATLAS_API_KEYS set
#
# Requires: bash, curl, python3. Works in demo mode (synthetic provenance).
# Units: the US region reports acres first; the API always returns both.
set -euo pipefail

API="${ATLAS_API:-http://localhost:8000/api/v1}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_PLOT_ID="PLT-DEMOUS"

auth=()
if [[ -n "${ATLAS_API_KEY:-}" ]]; then auth=(-H "X-API-Key: ${ATLAS_API_KEY}"); fi

json() { python3 -c 'import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {}, {"d": d}))' "$1"; }
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "0. Health and region settings"
curl -fsS "$API/health"; echo
curl -fsS "$API/regions" | json '[(r["id"], r["units"]["area"], r["currency"]) for r in d]'

step "1. Create the plot (POST /plots) — about 8 ha (≈ 19.8 acres) near 32.5 N 83.7 W, Georgia"
PLOT_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data @"$HERE/plot.request.json" "$API/plots")"
PLOT_ID="$(printf '%s' "$PLOT_JSON" | json 'd["plot_id"]' || echo "$DEMO_PLOT_ID")"
printf '%s' "$PLOT_JSON" | json '{"plot_id": d["plot_id"], "area_acres": d.get("area_acres"), "area_hectares": d["area_hectares"], "region": d.get("region"), "public_centroid": d.get("public_centroid")}'
echo "Using plot_id=$PLOT_ID"

step "2. Analyze (POST /plots/{id}/analyze) — WorldCover, Sentinel-2 indices, Open-Meteo climate, SoilGrids"
curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data '{"layers":["landcover","vegetation","climate","soil","terrain"]}' \
  "$API/plots/$PLOT_ID/analyze" \
  | json '{"tree_cover_share": d["landcover"]["tree_cover_share"], "ndvi": d["vegetation"]["indices"]["ndvi"]["value"], "ndmi": d["vegetation"]["indices"]["ndmi"]["value"], "climate_zone": d["climate"]["zone"], "soc_g_per_kg": d["soil"]["soc_0_30cm_g_per_kg"]}'

step "3. Tree inventory — 1,200 pecan planted 2021 (POST /plots/{id}/trees)"
INV_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data @"$HERE/trees.request.json" "$API/plots/$PLOT_ID/trees")"
INV_ID="$(printf '%s' "$INV_JSON" | json 'd["inventory_id"]')"
printf '%s' "$INV_JSON" | json '{"inventory_id": d["inventory_id"], "density_per_ha": d["density_per_ha"], "age_years": d["age_years"], "confidence": d["data_quality"]["confidence"]}'

step "4. Carbon estimate (POST /plots/{id}/carbon-estimate)"
EST_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data "{\"inventory_id\":\"$INV_ID\",\"model\":\"tree-biomass\"}" "$API/plots/$PLOT_ID/carbon-estimate")"
EST_ID="$(printf '%s' "$EST_JSON" | json 'd["estimate_id"]')"
printf '%s' "$EST_JSON" | json '{"estimate_tco2e_yr": d["estimate"], "components": d.get("components"), "confidence": d["confidence"], "certified": d["certified"], "readiness": d["readiness"]["score"], "parameters_pending": [p["name"] for p in d["parameters_used"] if p["verification_status"]!="verified"]}'

step "5. Programme screening — COMET-Farm reference, voluntary ARR methodologies, NRCS EQIP/CSP"
curl -fsS "$API/plots/$PLOT_ID/policy-eligibility?activity=agroforestry" \
  | json '[(p["id"], p["status"]) for p in d["programmes"]]'

step "6. Market-value scenarios in USD — illustrative, not a quote"
curl -fsS "$API/plots/$PLOT_ID/market-scenario?estimate_id=$EST_ID" \
  | json '{"currency": d["currency"], "scenarios": [(s["id"], s["price_per_tco2e"], s["value_per_year"]["central"]) for s in d["scenarios"]], "other_income": [o["label"] for o in d["other_income"]]}'

step "7. Report in HTML (POST /plots/{id}/report)"
REPORT_URL="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data "{\"format\":\"html\",\"language\":\"en\",\"estimate_id\":\"$EST_ID\"}" \
  "$API/plots/$PLOT_ID/report" | json 'd["url"]')"
echo "report: ${API%/api/v1}$REPORT_URL"

step "8. Stateless what-if (POST /simulate) — compare the same planting across IN / US / EU climate defaults"
curl -fsS -H 'Content-Type: application/json' --data @"$HERE/simulate.request.json" "$API/simulate" \
  | json '{"climate_zone": d["climate_zone"], "annual": d["annual"], "comparison": [(c["country"], c["climate_zone"], c["annual"]["central"]) for c in d["comparison"]]}'

step "9. Shareable link parameters (no coordinates are included)"
curl -fsS -H 'Content-Type: application/json' --data @"$HERE/simulate.request.json" "$API/simulate" | json 'd["share_params"]'

# Clean up:
# curl -fsS "${auth[@]}" -X DELETE "$API/plots/$PLOT_ID"
