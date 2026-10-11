"""Plain-language wording shared by the agents — the deterministic templates.

Every sentence an agent says is built here (or in the agent) from facts that
came out of the engines. Keeping the wording in small functions means:

* the same number is always written the same way (``7.7–14.3 tCO₂e``);
* the coordinator can repeat a specialist's sentence in its answer without
  re-deriving anything;
* tests can check the wording without running a whole team.

Nothing in this module computes a carbon number, a price or an eligibility
result — it only formats what the services returned.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from carboncreditbuy_agents import Evidence

NOT_A_CREDIT = "This is an estimate, not a carbon credit."
SCENARIO_NOT_A_CREDIT = "This is a scenario, not a carbon credit."
RUN_DISCLAIMER = (
    "Agent findings come from deterministic engines and configuration. Carbon figures are "
    "scenario estimates with uncertainty ranges — not issued carbon or green credits and not "
    "certified. Programme results are an initial screening, not an eligibility decision. "
    "Market values are scenarios, not guaranteed revenue."
)

# Programme screening statuses (policy engine) in plain words — display text only.
STATUS_WORDS = {
    "potentially_applicable": "may apply",
    "requires_assessment": "needs an assessment",
    "requires_methodology_assessment": "needs an approved methodology and assessment",
    "requires_certification": "needs certification",
    "not_applicable": "does not apply",
    "unknown": "unknown — not enough information",
}

# Inventory data-quality field names (carbon engine) in plain words.
FIELD_WORDS = {
    "tree_count": "tree count",
    "species": "species",
    "age": "planting year",
    "dbh": "trunk diameter (DBH)",
    "height": "tree height",
    "mortality": "survival records",
}

# How a tree count was obtained (contract: measurement_source).
SOURCE_WORDS = {
    "user-reported": "You reported",
    "field-measured": "Field measurements show",
    "satellite-derived": "Satellite data indicates",
    "government-data": "Government records list",
    "model-estimated": "A model estimated",
}


# ----------------------------------------------------------------------------- numbers
def num(value: Any, digits: int = 1) -> str:
    """``11.02`` → ``"11.0"``; thousands separated: ``12122`` → ``"12,122"``."""
    return f"{float(value):,.{digits}f}"


def pct(share: Any, digits: int = 0) -> str:
    """A 0–1 share as a percentage: ``0.68`` → ``"68 %"``."""
    return f"{float(share) * 100:.{digits}f} %"


def tonnes(rng: Mapping[str, Any]) -> str:
    """``{"low": 7.71, "central": 11.02, "high": 14.32}`` → ``"7.7–14.3 tCO₂e"``."""
    return f"{num(rng['low'])}–{num(rng['high'])} tCO₂e"


def per_year(rng: Mapping[str, Any]) -> str:
    """``"7.7–14.3 tCO₂e per year (central 11.0)"``."""
    return f"{tonnes(rng)} per year (central {num(rng['central'])})"


def stored(rng: Mapping[str, Any]) -> str:
    """``"16.1–30.0 tCO₂e (central 23.0)"``."""
    return f"{tonnes(rng)} (central {num(rng['central'])})"


def money(amount: Any, symbol: str) -> str:
    """``(12122.0, "₹")`` → ``"₹12,122"``."""
    return f"{symbol}{float(amount):,.0f}"


def join_words(items: Sequence[str]) -> str:
    """``["a", "b", "c"]`` → ``"a, b and c"``."""
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def lower_first(text: str) -> str:
    """Lower-case the first letter for use mid-sentence, unless it starts an acronym ("NDVI")."""
    if not text or (len(text) > 1 and text[1].isupper()):
        return text
    return text[:1].lower() + text[1:]


# ----------------------------------------------------------------------------- evidence
def evidence_from_sources(sources: Iterable[Mapping[str, Any]] | None) -> list[Evidence]:
    """Evidence items from a service provenance ``sources`` list (name, id and URL only)."""
    items: list[Evidence] = []
    for source in sources or []:
        label = source.get("label") or source.get("name") or source.get("id")
        if not label:
            continue
        items.append(
            Evidence(label=str(label), source=str(source.get("id") or label), url=source.get("url"))
        )
    return items


def evidence_from_references(
    references: Iterable[Mapping[str, Any]] | None, source: str
) -> list[Evidence]:
    """Evidence items from ``{"title", "url"}`` reference lists (methodologies, programmes)."""
    return [
        Evidence(label=str(ref.get("title")), source=source, url=ref.get("url"))
        for ref in references or []
        if ref.get("title")
    ]


# ----------------------------------------------------------------------------- sentences
def plot_sentence(plot: Mapping[str, Any]) -> str:
    """Size and place, e.g. "Your plot is 2.13 ha (5.26 acres) in Karnataka, India."."""
    where = join_place(plot.get("state"), plot.get("country_label"))
    place = f" in {where}" if where else ""
    return (
        f"Your plot is {num(plot['area_hectares'], 2)} ha "
        f"({num(plot['area_acres'], 2)} acres){place}."
    )


def join_place(state: Any, country: Any) -> str:
    return ", ".join(str(p) for p in (state, country) if p)


def boundary_sentence(plot: Mapping[str, Any]) -> str:
    if not plot.get("boundary_valid"):
        return "The boundary is not a valid polygon — please redraw it."
    if plot.get("boundary_quality") == "approximate":
        return "The boundary is valid but approximate (built from a pin or a tree line)."
    return "The boundary is valid."


def landcover_sentence(cover: Mapping[str, Any]) -> str:
    dataset = f"{cover.get('dataset')} {cover.get('version')}".strip()
    if cover.get("synthetic"):
        dataset += " — synthetic demo values, not an observation"
    return (
        f"About {pct(cover['cropland_share'])} is cropland and "
        f"{pct(cover['tree_cover_share'])} tree cover ({dataset})."
    )


def climate_sentence(climate: Mapping[str, Any]) -> str:
    how = {
        "derived": "derived from local climate normals",
        "region-default": "the default for the region",
    }.get(str(climate.get("source")), str(climate.get("source") or "source unknown"))
    return f"The climate zone is {lower_first(str(climate['label']))} ({how})."


def vegetation_sentences(veg: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    if veg.get("ndvi") is not None:
        when = f" ({veg['date']})" if veg.get("date") else ""
        out.append(
            f"The latest satellite reading{when} shows {veg.get('ndvi_class', 'unclassified')} "
            f"vegetation: NDVI {num(veg['ndvi'], 2)}."
        )
    if veg.get("ndmi") is not None:
        out.append(
            f"The moisture index NDMI is {num(veg['ndmi'], 2)} "
            f"({veg.get('ndmi_class', 'unclassified')})."
        )
    if veg.get("trend_pct") is not None:
        change = float(veg["trend_pct"])
        verb = "rose" if change > 0 else ("fell" if change < 0 else "stayed level")
        span = (
            f" from {veg['trend_start']} to {veg['trend_end']}"
            if veg.get("trend_start") and veg.get("trend_end")
            else ""
        )
        amount = f" by about {num(abs(change))} %" if change else ""
        out.append(f"The vegetation index {verb}{amount}{span}.")
    if veg.get("synthetic"):
        out.append("(Demo mode: synthetic Sentinel-2 values.)")
    return out


def detection_sentence(det: Mapping[str, Any]) -> str:
    """One sentence, e.g. "Tree-cover detection (2026-09) found 6 patches covering …"."""
    patches = det.get("patches")
    noun = "patch" if patches == 1 else "patches"
    when = f" ({det['month']})" if det.get("month") else ""
    text = f"Tree-cover detection{when} found {patches} {noun}"
    if det.get("covered_fraction") is not None:
        text += f" covering about {pct(det['covered_fraction'])} of the plot"
    if det.get("area_hectares") is not None:
        text += f" ({num(det['area_hectares'], 2)} ha)"
    if det.get("method"):
        text += f", using {lower_first(str(det['method']))}"
    return text + "."


def inventory_sentence(inv: Mapping[str, Any]) -> str:
    opener = SOURCE_WORDS.get(str(inv.get("measurement_source")), "The inventory lists")
    species = str(inv.get("species") or inv.get("species_id") or "unknown species").lower()
    text = (
        f"{opener} {int(inv['tree_count']):,} {species} trees "
        f"(about {num(inv['density_per_ha'], 0)} per hectare), planted in "
        f"{inv['plantation_year']} — about {inv['age_years']} years old."
    )
    if inv.get("survival_rate") is not None:
        text += f" Survival rate {pct(inv['survival_rate'])}."
    missing = [FIELD_WORDS.get(str(f), str(f)) for f in inv.get("missing_fields") or []]
    if missing:
        text += f" Not measured yet: {join_words(missing)}"
        text += f", so confidence is {inv['confidence']}." if inv.get("confidence") else "."
    elif inv.get("confidence"):
        text += f" Confidence is {inv['confidence']}."
    return text


def method_phrase(estimate: Mapping[str, Any]) -> str:
    """Return "IPCC Tier 1" for the IPCC gain-loss path, otherwise the methodology name."""
    methodology = estimate.get("methodology") or {}
    tier = (estimate.get("model") or {}).get("tier")
    if str(methodology.get("id", "")).startswith("ipcc") and tier:
        return f"IPCC Tier {tier}"
    return str(methodology.get("name") or (estimate.get("model") or {}).get("id") or "the model")


def carbon_sentence(estimate: Mapping[str, Any]) -> str:
    text = f"Estimated removal is {per_year(estimate['estimate'])} using {method_phrase(estimate)}."
    if estimate.get("stock"):
        text += f" Since planting, about {stored(estimate['stock'])} has been removed."
    if estimate.get("confidence"):
        text += f" Confidence is {estimate['confidence']}."
    return text


def what_if_sentences(result: Mapping[str, Any], *, lead: bool = True) -> list[str]:
    """The what-if comparison; ``lead`` adds the opening question ("What if you add 200 trees?")."""
    change = int(result["change"])
    verb = "add" if change > 0 else "remove"
    species = str(result.get("species") or "").lower()
    trees = f"{species} trees" if species else "trees"
    baseline, scenario = result["baseline"], result["scenario"]
    difference = float(result["difference_central"])
    direction = "more" if difference >= 0 else "less"
    opening = f"What if you {verb} {abs(change):,} trees? " if lead else ""
    out = [
        f"{opening}With {int(result['tree_count_new']):,} "
        f"{trees} instead of {int(result['tree_count_now']):,} (same planting year "
        f"{result['planting_year']}), the simulation estimates {per_year(scenario)} instead of "
        f"{tonnes(baseline)} (central {num(baseline['central'])}) — about "
        f"{num(abs(difference))} tCO₂e per year {direction} (difference of the central values).",
    ]
    if change > 0:
        out.append(
            f"The model treats all trees as one planting from {result['planting_year']}, so "
            "trees planted later would start removing carbon later than this suggests."
        )
    cap = result.get("density_cap")
    if cap and result.get("density_capped"):
        out.append(
            f"Above {num(cap['factor'])} × the reference density "
            f"({num(cap['reference_per_ha'], 0)} trees per hectare for this species) the model "
            "adds no extra growth per hectare, so extra trees add less."
        )
    return out


def programmes_sentence(screening: Mapping[str, Any]) -> str:
    items = [
        f"{p['programme']} — {STATUS_WORDS.get(str(p['status']), str(p['status']))}"
        for p in screening.get("programmes") or []
    ]
    where = screening.get("country_label") or screening.get("country")
    activity = str(screening.get("activity", "")).replace("_", " ")
    return f"Initial screening for {where} ({activity}): " + "; ".join(items) + "."


def tree_age_sentences(result: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    inventory_age = result.get("inventory_age_years")
    if result.get("age_source") == "question" and inventory_age not in (None, result["age_years"]):
        out.append(
            f"I used the age from your question ({result['age_years']} years); the tree "
            f"inventory says {inventory_age} years."
        )
    age_class = result.get("age_class") or {}
    who = f"{int(result['tree_count']):,} " if result.get("tree_count") else ""
    out.append(
        f"Your {who}trees are about {result.get('age_years')} years old: age class "
        f"{age_class.get('label') or age_class.get('id') or 'unknown'}."
    )
    if result.get("stored_now") and result.get("annual_now"):
        out.append(
            f"The tree-age model puts the carbon stored now at {stored(result['stored_now'])} "
            f"and current growth at {per_year(result['annual_now'])}."
        )
    outlook = result.get("credit_outlook") or {}
    if outlook:
        out.append(
            f"Credit outlook for existing trees: {outlook.get('existing_trees')} — "
            f"{lower_first(str(outlook.get('summary', '')).rstrip('.'))}."
        )
    rules = result.get("rules") or []
    applying = [r for r in rules if r.get("applies")]
    pending = [r for r in applying if r.get("verification_status") == "pending"]
    if rules:
        text = f"{len(applying)} of {len(rules)} age rules apply here"
        if pending:
            text += f" ({len(pending)} still pending verification, so not confirmed)"
        out.append(text + ".")
    return out


def cost_sentences(cost: Mapping[str, Any]) -> list[str]:
    """The user's costs against the simulated removal — a break-even price, not revenue."""
    symbol = str(cost.get("currency_symbol") or "")
    years = int(cost["horizon_years"])
    removal = cost["removal_over_horizon_tco2e"]
    out = [
        f"Your entered costs come to {money(cost['total_cost'], symbol)} over {years} years "
        f"(planting {money(cost['establishment'], symbol)}, upkeep "
        f"{money(cost['maintenance_over_horizon'], symbol)}, monitoring "
        f"{money(cost['monitoring_over_horizon'], symbol)}; undiscounted)."
    ]
    even = cost.get("break_even_price_per_tco2e") or {}
    if even.get("central") is not None:
        out.append(
            f"Against an estimated {stored(removal)} removed over those years, a carbon price of "
            f"about {money(even['central'], symbol)} per tCO₂e "
            f"({money(even['low'], symbol)}–{money(even['high'], symbol)}) would match these costs."
        )
    for scenario in cost.get("price_scenarios") or []:
        if (
            scenario.get("id") == "reference"
            and scenario.get("share_of_costs_covered_pct") is not None
        ):
            out.append(
                f"At the reference price scenario of {money(scenario['price_per_tco2e'], symbol)} "
                f"per tCO₂e that is about {num(scenario['share_of_costs_covered_pct'], 0)} % of the "
                "entered costs."
            )
    if cost.get("not_entered"):
        names = [n.replace("_", " ") for n in cost["not_entered"]]
        out.append(f"Not entered, so counted as zero: {join_words(names)}.")
    out.append(
        "Credits only exist after a recognised programme validates, monitors and verifies the "
        "removal; this is a planning scenario, not revenue."
    )
    return out


def market_sentences(market: Mapping[str, Any], estimate_range: Mapping[str, Any]) -> list[str]:
    """Three separate values, three separate sentences — never added together."""
    symbol = str(market.get("currency_symbol") or "")
    scenarios = {s["id"]: s for s in market.get("scenarios") or []}
    out = [f"Environmental benefit: an estimated {per_year(estimate_range)} of carbon removal."]
    reference = scenarios.get("reference")
    if reference:
        text = (
            f"Indicative carbon value (scenario): about "
            f"{money(reference['value_per_year']['central'], symbol)} per year at the reference "
            f"price of {money(reference['price_per_tco2e'], symbol)} per tCO₂e"
        )
        low, high = scenarios.get("low"), scenarios.get("high")
        if low and high:
            text += (
                f" ({money(low['value_per_year']['central'], symbol)} at the low price, "
                f"{money(high['value_per_year']['central'], symbol)} at the high price)"
            )
        out.append(text + ".")
    labels = [
        lower_first(str(i.get("label"))) for i in market.get("other_income") or [] if i.get("label")
    ]
    if labels:
        out.append(
            "Other farm income — " + "; ".join(labels) + " — is not estimated here; add your "
            "own records."
        )
    out.append("These three values answer different questions and are never added together.")
    return out


def review_sentences(review: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    passed = review.get("checks_passed") or []
    failed = review.get("checks_failed") or []
    if passed:
        out.append(f"I checked the carbon estimate: {join_words(passed)}.")
    if failed:
        out.append(f"Problems found: {join_words(failed)}.")
    pending = review.get("pending_parameters") or []
    if pending:
        names = join_words([p.replace("_", " ") for p in pending])
        out.append(
            f"{len(pending)} parameter(s) are still pending verification ({names}); a production "
            "deployment refuses this estimate until they are verified."
        )
    if review.get("readiness_score") is not None:
        text = f"Evidence readiness is {review['readiness_score']}/100"
        if review.get("readiness_grade"):
            text += f" ({review['readiness_grade']})"
        missing = [lower_first(str(m)) for m in review.get("missing_evidence") or []]
        if missing:
            text += f"; still missing: {join_words(missing)}"
        out.append(text + ".")
    return out


def report_sentence(report: Mapping[str, Any]) -> str:
    return (
        f"I wrote an {str(report.get('format', 'html')).upper()} report "
        f"({report['report_id']}) with the plot, trees, carbon estimate, programmes and value "
        f"scenarios. Open it at {report['url']}."
    )
