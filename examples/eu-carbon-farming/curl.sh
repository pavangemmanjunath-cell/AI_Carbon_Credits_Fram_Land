#!/usr/bin/env bash
# AgriCarbon Atlas — end-to-end walkthrough for the synthetic EU (Andalusia) olive grove.
#
# Usage:
#   ATLAS_API=http://localhost:8000/api/v1 ./curl.sh
#   ATLAS_API_KEY=... ./curl.sh          # when the server has ATLAS_API_KEYS set
#
# Requires: bash, curl, python3. Works in demo mode (synthetic provenance).
# The plot is created with country "ES"; policy rules resolve member states to EU.
set -euo pipefail

API="${ATLAS_API:-http://localhost:8000/api/v1}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_PLOT_ID="PLT-DEMOEU"

auth=()
if [[ -n "${ATLAS_API_KEY:-}" ]]; then auth=(-H "X-API-Key: ${ATLAS_API_KEY}"); fi

json() { python3 -c 'import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {}, {"d": d}))' "$1"; }
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "0. Health"
curl -fsS "$API/health"; echo

step "1. Create the plot (POST /plots) — about 5 ha near 37.6 N 4.8 W, Córdoba province"
PLOT_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data @"$HERE/plot.request.json" "$API/plots")"
PLOT_ID="$(printf '%s' "$PLOT_JSON" | json 'd["plot_id"]' || echo "$DEMO_PLOT_ID")"
printf '%s' "$PLOT_JSON" | json '{"plot_id": d["plot_id"], "country": d["country"], "area_hectares": d["area_hectares"], "region": d.get("region"), "public_centroid": d.get("public_centroid")}'
echo "Using plot_id=$PLOT_ID"

step "2. Analyze (POST /plots/{id}/analyze)"
curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data '{"layers":["landcover","vegetation","climate","soil"]}' \
  "$API/plots/$PLOT_ID/analyze" \
  | json '{"classes": [(c["name"], c["share"]) for c in d["landcover"]["classes"]], "ndvi": d["vegetation"]["indices"]["ndvi"], "climate": {"zone": d["climate"]["zone"], "precip_mm": d["climate"]["annual_precip_mm"]}}'

step "3. Tree inventory — 900 olive planted 2020 (POST /plots/{id}/trees)"
INV_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data @"$HERE/trees.request.json" "$API/plots/$PLOT_ID/trees")"
INV_ID="$(printf '%s' "$INV_JSON" | json 'd["inventory_id"]')"
printf '%s' "$INV_JSON" | json '{"inventory_id": d["inventory_id"], "density_per_ha": d["density_per_ha"], "age_years": d["age_years"], "confidence": d["data_quality"]["confidence"]}'

step "4. Carbon estimate (POST /plots/{id}/carbon-estimate)"
EST_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data "{\"inventory_id\":\"$INV_ID\",\"model\":\"tree-biomass\"}" "$API/plots/$PLOT_ID/carbon-estimate")"
EST_ID="$(printf '%s' "$EST_JSON" | json 'd["estimate_id"]')"
printf '%s' "$EST_JSON" | json '{"estimate_tco2e_yr": d["estimate"], "stock_tco2e": d.get("stock"), "confidence": d["confidence"], "certified": d["certified"], "methodology": d["methodology"]["id"], "readiness": d["readiness"]["grade"]}'

step "5. Programme screening — CRCF (certification required), CAP eco-schemes, voluntary standards"
curl -fsS "$API/plots/$PLOT_ID/policy-eligibility?activity=tree_plantation" \
  | json '{"disclaimer": d["disclaimer"], "programmes": [(p["id"], p["status"]) for p in d["programmes"]]}'

step "6. Market-value scenarios in EUR — CRCF units are not yet traded; values are illustrative"
curl -fsS "$API/plots/$PLOT_ID/market-scenario?estimate_id=$EST_ID" \
  | json '{"currency": d["currency"], "scenarios": [(s["id"], s["price_per_tco2e"], s["value_per_year"]["central"]) for s in d["scenarios"]], "basis": d["basis"]["note"]}'

step "7. Report in JSON (POST /plots/{id}/report)"
REPORT_URL="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data "{\"format\":\"json\",\"language\":\"en\",\"estimate_id\":\"$EST_ID\"}" \
  "$API/plots/$PLOT_ID/report" | json 'd["url"]')"
curl -fsS "${API%/api/v1}$REPORT_URL" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sorted(d.keys()))'

step "8. Stateless what-if (POST /simulate) with a 30-year horizon"
curl -fsS -H 'Content-Type: application/json' --data @"$HERE/simulate.request.json" "$API/simulate" \
  | json '{"climate_zone": d["climate_zone"], "annual": d["annual"], "cumulative_year_30": [(r["year"], r["cum_central"]) for r in d["series"] if r["age"]==30][:1], "programmes": [(p["id"], p["status"]) for p in d["programmes"]]}'

step "9. Attribution strings to display with any map or report (GET /attribution)"
curl -fsS "$API/attribution" | json '[(i["id"], i["text"]) for i in d["items"]]'

# Clean up:
# curl -fsS "${auth[@]}" -X DELETE "$API/plots/$PLOT_ID"
