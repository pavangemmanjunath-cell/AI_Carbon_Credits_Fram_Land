#!/usr/bin/env bash
# AgriCarbon Atlas — end-to-end walkthrough for the synthetic India mango farm.
#
# Usage:
#   ATLAS_API=http://localhost:8000/api/v1 ./curl.sh
#   ATLAS_API_KEY=... ./curl.sh          # when the server has ATLAS_API_KEYS set
#
# Requires: bash, curl, python3 (for JSON field extraction; jq is not needed).
# The server may run in demo mode (no network) — provenance is then labelled
# "synthetic-demo". Nothing here is a carbon credit; every response says so.
set -euo pipefail

API="${ATLAS_API:-http://localhost:8000/api/v1}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_PLOT_ID="PLT-DEMOIN"   # id of the pre-seeded demo plot, used only as a fallback

auth=()
if [[ -n "${ATLAS_API_KEY:-}" ]]; then auth=(-H "X-API-Key: ${ATLAS_API_KEY}"); fi

json() { python3 -c 'import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {}, {"d": d}))' "$1"; }
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "0. Health"
curl -fsS "$API/health"; echo

step "1. Create the plot (POST /plots) — 2.13 ha near 13.29 N 77.54 E"
PLOT_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data @"$HERE/plot.request.json" "$API/plots")"
PLOT_ID="$(printf '%s' "$PLOT_JSON" | json 'd["plot_id"]' || echo "$DEMO_PLOT_ID")"
printf '%s' "$PLOT_JSON" | json '{"plot_id": d["plot_id"], "area_hectares": d["area_hectares"], "area_acres": d.get("area_acres"), "region": d.get("region"), "public_centroid": d.get("public_centroid")}'
echo "Using plot_id=$PLOT_ID"

step "2. Analyze land cover, vegetation, climate and soil (POST /plots/{id}/analyze)"
curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data '{"layers":["landcover","vegetation","climate","soil"],"years":[2024,2025,2026]}' \
  "$API/plots/$PLOT_ID/analyze" \
  | json '{"tree_cover_share": d["landcover"]["tree_cover_share"], "cropland_share": d["landcover"]["cropland_share"], "ndvi": d["vegetation"]["indices"]["ndvi"], "trend": d["vegetation"]["trend"]["statement"], "climate_zone": d["climate"]["zone"], "warnings": d["data_quality"]["warnings"]}'

step "3. Record the tree inventory — 420 mango planted 2023 (POST /plots/{id}/trees)"
INV_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data @"$HERE/trees.request.json" "$API/plots/$PLOT_ID/trees")"
INV_ID="$(printf '%s' "$INV_JSON" | json 'd["inventory_id"]')"
printf '%s' "$INV_JSON" | json '{"inventory_id": d["inventory_id"], "density_per_ha": d["density_per_ha"], "age_years": d["age_years"], "confidence": d["data_quality"]["confidence"], "missing": [f["name"] for f in d["data_quality"]["fields"] if f["status"]=="missing"]}'

step "4. Carbon estimate — IPCC 2006 Tier 1 gain-loss (POST /plots/{id}/carbon-estimate)"
EST_JSON="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data "{\"inventory_id\":\"$INV_ID\",\"model\":\"tree-biomass\"}" "$API/plots/$PLOT_ID/carbon-estimate")"
EST_ID="$(printf '%s' "$EST_JSON" | json 'd["estimate_id"]')"
printf '%s' "$EST_JSON" | json '{"estimate_tco2e_yr": d["estimate"], "confidence": d["confidence"], "certified": d["certified"], "readiness": {"score": d["readiness"]["score"], "grade": d["readiness"]["grade"]}, "missing_evidence": [m["label"] for m in d["readiness"]["missing_evidence"]], "disclaimer": d["disclaimer"]}'

step "5. Programme screening — Green Credit Programme vs CCTS (GET /plots/{id}/policy-eligibility)"
curl -fsS "$API/plots/$PLOT_ID/policy-eligibility?activity=tree_plantation" \
  | json '[(p["id"], p["status"]) for p in d["programmes"]]'

step "6. Indicative market-value scenarios in INR — not a quote (GET /plots/{id}/market-scenario)"
curl -fsS "$API/plots/$PLOT_ID/market-scenario?estimate_id=$EST_ID" \
  | json '{"currency": d["currency"], "scenarios": [(s["id"], s["price_per_tco2e"], s["value_per_year"]["central"]) for s in d["scenarios"]], "disclaimer": d["disclaimer"]}'

step "7. Report (POST /plots/{id}/report → GET /reports/{id})"
REPORT_URL="$(curl -fsS "${auth[@]}" -H 'Content-Type: application/json' \
  --data "{\"format\":\"markdown\",\"language\":\"en\",\"estimate_id\":\"$EST_ID\"}" \
  "$API/plots/$PLOT_ID/report" | json 'd["url"]')"
echo "report: $REPORT_URL"
curl -fsS "${API%/api/v1}$REPORT_URL" | head -n 20

step "8. Stateless what-if (POST /simulate) — same farm, 30-year horizon"
curl -fsS -H 'Content-Type: application/json' --data @"$HERE/simulate.request.json" "$API/simulate" \
  | json '{"climate_zone": d["climate_zone"], "annual": d["annual"], "year_10": [r for r in d["series"] if r["age"]==10][:1], "comparison": [(c["country"], c["annual"]["central"]) for c in d["comparison"]], "share_params": d["share_params"]}'

step "9. Privacy-preserving explanation (POST /explain) — indicators only, no coordinates"
curl -fsS -H 'Content-Type: application/json' \
  --data '{"language":"en","indicators":{"area_hectares":2.13,"tree_count":420,"species":"Mango","ndvi":0.76,"ndvi_trend_pct":22.6,"estimate_central":18.8,"estimate_low":13.2,"estimate_high":24.4,"confidence":"medium","missing_evidence":["dbh","baseline"]}}' \
  "$API/explain" | json '{"provider": d["provider"], "privacy_note": d["privacy_note"]}'

step "Done. Remove the plot? (DELETE /plots/{id}) — uncomment to clean up"
# curl -fsS "${auth[@]}" -X DELETE "$API/plots/$PLOT_ID" && echo "deleted $PLOT_ID"
