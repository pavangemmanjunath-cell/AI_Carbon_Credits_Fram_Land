# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Turn API JSON into the HTML shown in plugin dialogs (pure Python, no QGIS imports).

Rules that every page follows (they come from the repository's CLAUDE.md):

* every page that shows API-derived results carries ``certified: false`` and the sentence
  "Scenario estimate only. This is not an issued carbon credit.";
* the three values are shown separately and never summed: environmental benefit (estimated
  annual removal in tCO2e/yr, a low-central-high range), indicative carbon value (scenario
  prices, not a credit) and other farm income;
* every piece of text that comes from the server, a layer or the user passes through
  :func:`html.escape` (agent transcripts may contain model-written text);
* missing or unexpected fields never raise: they render as "not available".

The HTML sticks to the subset Qt's rich-text engine (``QTextBrowser``) understands: simple
tables, inline colours and no scripts, so it also renders in a browser.
"""

from __future__ import annotations

import html
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .api_client import ApiConfigError, ApiError, ApiProblem
from .crowns import CrownCount
from .geometry import GeometryError
from .version import DISCLAIMER

NOT_AVAILABLE = "not available"
_SEP = " · "

# Colours are always set in pairs (background + text) so the pages stay readable in dark themes.
_AMBER = ("#FFF3CD", "#5C4400")
_GREEN = ("#D1E7DD", "#0A3622")
_RED = ("#F8D7DA", "#58151C")
_GREY = ("#E9ECEF", "#212529")

_STATUS_COLOURS = {
    "done": _GREEN,
    "ok": _GREEN,
    "pass": _GREEN,
    "completed": _GREEN,
    "warning": _AMBER,
    "warn": _AMBER,
    "completed-with-warnings": _AMBER,
    "skipped": _GREY,
    "failed": _RED,
    "error": _RED,
    "fail": _RED,
}


# --------------------------------------------------------------------------- small helpers
def esc(value: Any) -> str:
    """HTML-escape any value (``None`` becomes an empty string)."""
    return html.escape("" if value is None else str(value), quote=True)


def esc_multiline(value: Any) -> str:
    """Escape text and keep its line breaks."""
    return esc(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _dict(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _dicts(value: Any) -> list[Mapping[str, Any]]:
    return [_dict(item) for item in _list(value)]


def _get(value: Any, *keys: str) -> Any:
    """Safe nested lookup: ``_get(d, "a", "b")`` is ``d["a"]["b"]`` or ``None``."""
    current = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def fmt_num(value: Any, decimals: int = 2, trim: bool = False) -> str:
    """Format a number with thousands separators; ``not available`` for missing values."""
    number = to_number(value)
    if number is None:
        return NOT_AVAILABLE
    text = f"{number:,.{decimals}f}"
    if trim and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def fmt_percent(share: Any) -> str:
    number = to_number(share)
    return NOT_AVAILABLE if number is None else f"{number * 100:.0f}%"


def fmt_ms(value: Any) -> str:
    return f"{fmt_num(value, 0)} ms" if to_number(value) is not None else ""


def pretty_unit(unit: Any) -> str:
    """``tCO2e/yr`` -> ``tCO₂e/yr`` (the notation used throughout the project)."""
    return str(unit or "").replace("CO2e", "CO₂e")


def words(value: Any) -> str:
    """``requires_assessment`` -> ``requires assessment``."""
    return str(value or "").replace("_", " ").replace("-", " ").strip()


def safe_url(value: Any) -> str | None:
    """Only plain http(s) links are ever rendered as links."""
    text = str(value or "").strip()
    if not text.lower().startswith(("http://", "https://")):
        return None
    return None if any(c in text for c in " \t\r\n<>") else text


def link(label: Any, url: Any) -> str:
    target = safe_url(url)
    if target is None:
        return esc(label)
    return f'<a href="{esc(target)}">{esc(label or target)}</a>'


def _badge(text: Any, status: str | None = None) -> str:
    background, foreground = _STATUS_COLOURS.get(str(status or text).lower(), _GREY)
    return (
        f'<span style="background-color:{background}; color:{foreground};">'
        f"&nbsp;{esc(text)}&nbsp;</span>"
    )


def _banner(inner_html: str, colours: tuple[str, str] = _AMBER) -> str:
    background, foreground = colours
    return (
        '<table width="100%" cellspacing="0" cellpadding="8"><tr>'
        f'<td bgcolor="{background}"><span style="color:{foreground};">{inner_html}</span>'
        "</td></tr></table>"
    )


def _table(rows: Iterable[Sequence[str]], header: Sequence[str] | None = None) -> str:
    parts = ['<table border="0" cellspacing="0" cellpadding="4">']
    if header:
        parts.append("<tr>" + "".join(f"<td><b>{esc(h)}</b></td>" for h in header) + "</tr>")
    for row in rows:
        parts.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    parts.append("</table>")
    return "".join(parts)


def _bullets(items: Iterable[str]) -> str:
    rendered = "".join(f"<li>{item}</li>" for item in items)
    return f"<ul>{rendered}</ul>" if rendered else ""


def _facts(pairs: Iterable[tuple[str, Any]]) -> str:
    rows = [
        (f"<b>{esc(label)}</b>", esc(value)) for label, value in pairs if value not in (None, "")
    ]
    return _table(rows)


def _p(inner_html: str) -> str:
    return f"<p>{inner_html}</p>" if inner_html else ""


def _unavailable(reason: str | None = None) -> str:
    return _p(f"{NOT_AVAILABLE} ({esc(reason)})." if reason else f"{NOT_AVAILABLE}.")


def page(title: str, body_html: str) -> str:
    """Wrap a body in a minimal HTML document."""
    return (
        '<html><head><meta charset="utf-8">'
        f"<title>{esc(title)}</title></head><body>{body_html}</body></html>"
    )


# --------------------------------------------------------------------------- shared blocks
def certified_flag(value: Any = False) -> tuple[str, str | None]:
    """Return the text to display and, when the server disagrees, a warning.

    The plugin *always* displays ``certified: false``. A server value other than ``false`` is
    ignored (nothing in this plugin can verify a registry serial number) and flagged.
    """
    if value is False or value is None:
        return "certified: false", None
    return (
        "certified: false",
        "The server reported a certified flag that is not false. The plugin ignores it: "
        "treat every figure as an estimate.",
    )


def disclaimer_banner(certified: Any = False, extra: Iterable[Any] = ()) -> str:
    """The banner shown on every results page."""
    flag, warning = certified_flag(certified)
    lines = [f"<b>{esc(DISCLAIMER)}</b> &nbsp; <code>{esc(flag)}</code>"]
    seen = {DISCLAIMER}
    for text in extra:
        value = str(text or "").strip()
        if value and value not in seen:
            seen.add(value)
            lines.append(esc(value))
    banners = [_banner("<br>".join(lines))]
    if warning:
        banners.append(_banner(esc(warning), _RED))
    return "".join(banners)


def _mode_notice(mode: Any) -> str:
    if str(mode or "").lower() != "demo":
        return ""
    return _banner(
        "<b>The server is in demo mode.</b> Data in this window is synthetic and is not an "
        "observation of your field.",
        _GREY,
    )


def _source_label(source: Mapping[str, Any]) -> str:
    name = " ".join(
        part
        for part in (
            str(source.get("name") or source.get("id") or ""),
            str(source.get("version") or ""),
        )
        if part
    )
    tail = [str(source[k]) for k in ("license", "attribution") if source.get(k)]
    return esc(name) + (f" — {esc('; '.join(tail))}" if tail else "")


def _provenance_block(blocks: Iterable[Any]) -> str:
    """List the distinct data sources named in the provenance of the given result blocks."""
    seen: set[tuple[str, str]] = set()
    items: list[str] = []
    for block in blocks:
        for source in _dicts(_get(block, "provenance", "sources")):
            key = (str(source.get("id") or ""), str(source.get("name") or ""))
            if key in seen or not any(key):
                continue
            seen.add(key)
            items.append(_source_label(source))
    return "<h3>Data sources</h3>" + _bullets(items) if items else ""


def _references(refs: Any, limit: int = 4) -> str:
    links = []
    for ref in _dicts(refs)[:limit]:
        if ref.get("title") or ref.get("url"):
            links.append(link(ref.get("title") or ref.get("url"), ref.get("url")))
    return " · ".join(links)


# --------------------------------------------------------------------------- errors
def describe_error(exc: BaseException, context: str | None = None) -> str:
    """Plain-text, user-facing description of a failure (never raises).

    ``context`` can be ``"agents"`` to explain a 404 from servers that predate the agent team.
    """
    if isinstance(exc, ApiProblem):
        return _describe_problem(exc, context)
    if isinstance(exc, ApiConfigError):
        return f"{exc} Open AgriCarbon Atlas > Settings to fix it."
    if isinstance(exc, (ApiError, GeometryError, ValueError)):
        return str(exc)
    return f"Unexpected error ({type(exc).__name__}). See the QGIS log panel (AgriCarbon Atlas)."


def _describe_problem(exc: ApiProblem, context: str | None) -> str:
    status, slug, plain = exc.status, exc.type_slug, exc.plain_message()
    suffix = f" (request id {exc.request_id})" if exc.request_id else ""
    if status == 401:
        text = "The server requires an API key. Enter it in AgriCarbon Atlas > Settings."
    elif status == 403:
        text = "The server rejected the API key. Check it in AgriCarbon Atlas > Settings."
    elif status == 404 and slug == "plot-not-found":
        text = (
            "This plot does not exist on the server (it may have been deleted, or it belongs "
            "to another server). Send the field polygon again or use AgriCarbon Atlas > "
            "Set current plot."
        )
    elif status == 404 and slug == "inventory-missing":
        text = (
            "This plot has no tree inventory yet. Run 'Count trees from segmentation layer' first."
        )
    elif status == 404 and slug == "estimate-missing":
        text = "This plot has no carbon estimate yet. Run 'Estimate carbon' first."
    elif status in (404, 405, 501) and context == "agents":
        text = (
            f"This server does not offer the AI agent team (HTTP {status}). Update the "
            "AgriCarbon Atlas API to a version that includes "
            "POST /api/v1/plots/{plot_id}/agents/run."
        )
    elif status == 404:
        text = (
            f"The server could not find what was requested ({plain}). "
            "Check the API base URL in Settings."
        )
    elif status == 409 and slug == "pending-parameters":
        text = (
            "The server will not produce an estimate while some carbon parameters are still "
            "pending verification (production mode). Ask the server administrator."
        )
    elif status == 413:
        text = "The request was too large for the server."
    elif status == 422 and slug == "invalid-geometry":
        text = f"The server rejected the field polygon: {plain}"
    elif status == 422 and slug == "country-unresolved":
        text = (
            "The server could not tell which country this field is in. Choose the country "
            "explicitly in the dialog."
        )
    elif status == 422 and slug == "unsupported-country":
        text = f"The server does not support this country: {plain}"
    elif status == 422 and slug == "unknown-species":
        text = f"The server does not know this species: {plain} Pick one from the list."
    elif status == 422:
        text = f"The server could not accept the data: {plain}"
    elif status == 429:
        wait = f" Try again in about {exc.retry_after:g} seconds." if exc.retry_after else ""
        text = "The server's rate limit was reached." + wait
    elif status == 501:
        text = f"The server does not implement this yet: {plain}"
    elif status >= 500:
        text = f"The server reported an error ({exc.safe_summary()}). Try again later."
    else:
        text = str(exc)
    return text + suffix


def describe_health(payload: Any) -> str:
    """Plain-text result of a successful ``GET /health`` for the Settings dialog."""
    data = _dict(payload)
    version = f" {data['version']}" if data.get("version") else ""
    text = f"Connected: AgriCarbon Atlas API{version}"
    if data.get("mode"):
        text += f", mode {data['mode']}"
    text += "."
    if str(data.get("mode") or "").lower() == "demo":
        text += " Demo mode: the server returns synthetic data."
    if not data:
        text = "The server answered, but not with the usual health information."
    return text


def describe_confidence_range(
    low: float | None, high: float | None, threshold: float | None
) -> str:
    """Hint shown under the confidence field: its value range and a scale-mismatch warning."""
    if low is None or high is None:
        return ""
    text = f"Values in this field range from {low:g} to {high:g}."
    if threshold is None:
        return text
    if high > 1.0 and threshold <= 1.0:
        text += " If they are percentages, enter the threshold on the same scale (for example 50)."
    elif threshold > high:
        text += " No detection reaches this threshold, so nothing would be counted."
    return text


def describe_crown_count(count: CrownCount, field: str | None = None) -> str:
    """Plain-text summary of a crown count for labels and result pages."""
    lines = [
        f"{count.inside:,} crown centroids inside the field ({count.examined:,} features examined)."
    ]
    if count.threshold is None:
        lines.append(f"Counted: {count.counted:,} (no confidence filter).")
    else:
        lines.append(
            f"Counted: {count.counted:,} with {field or 'confidence'} >= {count.threshold:g}. "
            f"Below the threshold: {count.below_threshold:,}. "
            f"Without a confidence value (not counted): {count.missing_confidence:,}."
        )
    if count.invalid:
        lines.append(f"Skipped {count.invalid:,} features without a usable location.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- plot + analysis
def format_plot_page(
    plot: Mapping[str, Any],
    analysis: Mapping[str, Any] | None = None,
    analysis_error: str | None = None,
    notes: Iterable[str] = (),
) -> str:
    """Page shown after a field polygon was sent: the new plot and its land/vegetation analysis."""
    data = _dict(plot)
    area_ha, area_ac = to_number(data.get("area_hectares")), to_number(data.get("area_acres"))
    area = None
    if area_ha is not None:
        acres = f" ({fmt_num(area_ac)} acres)" if area_ac is not None else ""
        area = f"{fmt_num(area_ha)} ha{acres}"
    parts = [
        "<h2>Field sent to AgriCarbon Atlas</h2>",
        disclaimer_banner(),
        _facts(
            [
                ("Plot id", data.get("plot_id")),
                ("Name", data.get("name")),
                ("Country", data.get("country")),
                ("Region", data.get("region")),
                ("Area", area),
                ("Source", data.get("source")),
                ("Privacy", data.get("privacy")),
            ]
        ),
    ]
    parts.extend(_banner(esc(note), _GREY) for note in notes)
    if analysis_error:
        failed = f"<b>The plot was created, but the analysis failed:</b> {esc(analysis_error)}"
        parts.append(_banner(failed, _RED))
    if analysis:
        parts.append(format_analysis(analysis))
    parts.append(
        _p(
            "Next: select your tree-crown layer and run <i>Count trees from segmentation "
            "layer</i>, then <i>Estimate carbon</i>."
        )
    )
    return page("Field sent", "".join(parts))


def format_analysis(analysis: Mapping[str, Any]) -> str:
    """HTML block for the ``POST /plots/{id}/analyze`` response (no carbon values)."""
    data = _dict(analysis)
    parts = [_mode_notice(data.get("mode")), "<h2>Analysis</h2>"]
    parts.append(_landcover_block(_dict(data.get("landcover"))))
    parts.append(_vegetation_block(_dict(data.get("vegetation"))))
    parts.append(_climate_soil_block(_dict(data.get("climate")), _dict(data.get("soil"))))
    warnings = [esc(w) for w in _list(_get(data, "data_quality", "warnings"))]
    if warnings:
        parts.append("<h3>Data quality warnings</h3>" + _bullets(warnings))
    parts.append(
        _provenance_block(
            _dict(data.get(k)) for k in ("landcover", "vegetation", "climate", "soil", "terrain")
        )
    )
    return "".join(parts)


def _landcover_block(landcover: Mapping[str, Any]) -> str:
    if not landcover:
        return ""
    title = " ".join(str(x) for x in (landcover.get("dataset"), landcover.get("version")) if x)
    resolution = to_number(landcover.get("resolution_m"))
    if resolution is not None:
        title += f", {fmt_num(resolution, 0, trim=True)} m"
    heading = f"Land cover ({title})" if title else "Land cover"
    rows = [
        (
            esc(c.get("name") or c.get("code")),
            fmt_percent(c.get("share")),
            fmt_num(c.get("area_ha")),
        )
        for c in _dicts(landcover.get("classes"))
    ]
    return (
        f"<h3>{esc(heading)}</h3>"
        + (_table(rows, header=("Class", "Share", "Area (ha)")) if rows else "")
        + _p(
            f"Tree cover: <b>{fmt_percent(landcover.get('tree_cover_share'))}</b>{_SEP}"
            f"cropland: <b>{fmt_percent(landcover.get('cropland_share'))}</b>"
        )
    )


def _vegetation_block(vegetation: Mapping[str, Any]) -> str:
    if not vegetation:
        return ""
    indices = _dict(vegetation.get("indices"))
    lines = []
    for key in ("ndvi", "ndmi"):
        item = _dict(indices.get(key))
        if item:
            date = f" on {esc(item.get('date'))}" if item.get("date") else ""
            lines.append(
                f"<b>{key.upper()}</b> {fmt_num(item.get('value'))} "
                f"({esc(item.get('class') or NOT_AVAILABLE)}){date}"
            )
    statement = _get(vegetation, "trend", "statement")
    return (
        "<h3>Vegetation indices</h3>"
        + _p(_SEP.join(lines))
        + _p(esc(statement) if statement else "")
    )


def _climate_soil_block(climate: Mapping[str, Any], soil: Mapping[str, Any]) -> str:
    bits = []
    zone = climate.get("zone_label") or words(climate.get("zone"))
    if zone:
        bits.append(f"zone: <b>{esc(zone)}</b>")
    for key, label, unit, decimals in (
        ("mean_annual_temp_c", "mean annual temperature", "°C", 1),
        ("annual_precip_mm", "annual precipitation", "mm", 0),
        ("elevation_m", "elevation", "m", 0),
    ):
        if to_number(climate.get(key)) is not None:
            bits.append(f"{label} {fmt_num(climate[key], decimals)} {unit}")
    soc = soil.get("soc_0_30cm_g_per_kg")
    soil_line = (
        f"Soil organic carbon (0–30 cm): <b>{fmt_num(soc)}</b> g/kg"
        if to_number(soc) is not None
        else ""
    )
    if not bits and not soil_line:
        return ""
    return "<h3>Climate and soil</h3>" + _p(_SEP.join(bits)) + _p(soil_line)


# --------------------------------------------------------------------------- tree inventory
def format_inventory_page(
    inventory: Mapping[str, Any],
    crown_count: CrownCount | None = None,
    confidence_field: str | None = None,
    layer_name: str | None = None,
) -> str:
    """Page shown after a tree inventory was posted."""
    inv = _dict(inventory)
    species = _dict(inv.get("species"))
    latin = f"({species['scientific_name']})" if species.get("scientific_name") else ""
    species_label = " ".join(
        part for part in (str(species.get("common_name") or species.get("id") or ""), latin) if part
    )
    quality = _dict(inv.get("data_quality"))
    fields = _dicts(quality.get("fields"))
    supplied = [esc(f.get("name")) for f in fields if f.get("status") == "supplied"]
    missing = [esc(f.get("name")) for f in fields if f.get("status") == "missing"]
    count = fmt_num(inv.get("tree_count"), 0) if to_number(inv.get("tree_count")) else None
    density = (
        f"{fmt_num(inv.get('density_per_ha'), 1)} trees/ha"
        if to_number(inv.get("density_per_ha"))
        else None
    )
    parts = [
        "<h2>Tree inventory recorded</h2>",
        disclaimer_banner(),
        _facts(
            [
                ("Inventory id", inv.get("inventory_id")),
                ("Plot id", inv.get("plot_id")),
                ("Species", species_label),
                ("Tree count", count),
                ("Density", density),
                ("Planted", inv.get("plantation_year")),
                ("Age (years)", inv.get("age_years")),
                ("Measurement source", inv.get("measurement_source")),
                ("Data confidence", quality.get("confidence")),
            ]
        ),
    ]
    if supplied or missing:
        parts.append(
            _p(
                f"Supplied: {', '.join(supplied) or NOT_AVAILABLE}. "
                f"Missing: {', '.join(missing) or 'none'}."
            )
        )
    if crown_count is not None:
        origin = f" from layer <i>{esc(layer_name)}</i>" if layer_name else ""
        summary = esc_multiline(describe_crown_count(crown_count, confidence_field))
        parts.append("<h3>How the count was made</h3>" + _p(summary))
        parts.append(
            _p(
                f"The tree count comes from crown centroids detected{origin}. Segmentation can "
                "merge neighbouring crowns or miss small trees, so check the count against the "
                "imagery."
            )
        )
    parts.append(_p("Next: run <i>Estimate carbon</i>."))
    return page("Tree inventory", "".join(parts))


# --------------------------------------------------------------------------- carbon estimate
def format_carbon_results(
    estimate: Mapping[str, Any],
    market: Mapping[str, Any] | None = None,
    policy: Mapping[str, Any] | None = None,
    market_error: str | None = None,
    policy_error: str | None = None,
) -> str:
    """Results page for a carbon estimate: three separate values, screening and readiness."""
    est = _dict(estimate)
    provenance = _dict(est.get("provenance"))
    parts = [
        "<h2>Carbon estimate (scenario)</h2>",
        disclaimer_banner(est.get("certified"), [est.get("disclaimer")]),
        _mode_notice(provenance.get("mode")),
        _p("The three values below are shown separately. They are never added together."),
        _removal_section(est),
        _market_section(market, market_error),
        _other_income_section(market),
        _policy_section(policy, policy_error),
        _readiness_section(est.get("readiness")),
        _estimate_footer(est),
    ]
    return page("Carbon estimate", "".join(parts))


def _removal_section(est: Mapping[str, Any]) -> str:
    heading = "<h3>1 · Environmental benefit: estimated annual carbon removal</h3>"
    rng = _dict(est.get("estimate"))
    if not rng:
        return heading + _unavailable()
    unit = esc(pretty_unit(rng.get("unit") or "tCO2e/yr"))
    central = f'<span style="font-size:16pt;"><b>{fmt_num(rng.get("central"))}</b></span>'
    parts = [
        heading,
        _table(
            [(fmt_num(rng.get("low")), central, fmt_num(rng.get("high")))],
            header=("Low", "Central", "High"),
        ),
        _p(f"{unit}{_SEP}confidence: <b>{esc(est.get('confidence') or NOT_AVAILABLE)}</b>"),
    ]
    stock = _dict(est.get("stock"))
    if stock:
        stock_unit = esc(pretty_unit(stock.get("unit") or "tCO2e"))
        parts.append(
            _p(
                f"Carbon stock at the end of the evaluation window ({stock_unit}): "
                f"{fmt_num(stock.get('low'))} – {fmt_num(stock.get('central'))} – "
                f"{fmt_num(stock.get('high'))}"
            )
        )
    components = _dict(est.get("components"))
    if components:
        parts.append(
            _p(
                "Components of the central estimate: above-ground "
                f"{fmt_num(components.get('above_ground_tco2e_yr'))}, below-ground "
                f"{fmt_num(components.get('below_ground_tco2e_yr'))} {unit}"
            )
        )
    model, methodology = _dict(est.get("model")), _dict(est.get("methodology"))
    lines = []
    if model:
        tier = f", tier {esc(model.get('tier'))}" if model.get("tier") else ""
        lines.append(f"Model: {esc(model.get('id'))} {esc(model.get('version'))}{tier}")
    if methodology:
        lines.append(f"Methodology: {esc(methodology.get('name') or methodology.get('id'))}")
    parts.append(_p("<br>".join(lines)))
    references = _references(methodology.get("references"))
    parts.append(_p(f"References: {references}" if references else ""))
    parts.append(_p(_parameter_summary(est.get("parameters_used"))))
    return "".join(parts)


def _parameter_summary(parameters: Any) -> str:
    items = _dicts(parameters)
    if not items:
        return ""
    counts = Counter(str(p.get("verification_status") or "unknown") for p in items)
    labels = {
        "verified": "verified",
        "pending": "pending verification",
        "assumption": "assumptions",
    }
    pieces = [f"{counts[k]} {label}" for k, label in labels.items() if counts.get(k)]
    pieces += [f"{n} {esc(k)}" for k, n in counts.items() if k not in labels]
    text = f"{len(items)} parameters used: {', '.join(pieces)}."
    if counts.get("pending") or counts.get("assumption"):
        text += " Parameters that are pending or assumptions have not been verified yet."
    return text


def _market_section(market: Mapping[str, Any] | None, error: str | None) -> str:
    heading = "<h3>2 · Indicative carbon value: scenario, not a credit</h3>"
    data = _dict(market)
    scenarios = _dicts(data.get("scenarios"))
    if not scenarios:
        return heading + _unavailable(error)
    symbol = str(data.get("currency_symbol") or data.get("currency") or "")

    def money(value: Any) -> str:
        number = to_number(value)
        return NOT_AVAILABLE if number is None else esc(f"{symbol}{number:,.0f}")

    rows = []
    for item in scenarios:
        value = _dict(item.get("value_per_year"))
        rows.append(
            (
                f"<b>{esc(item.get('label') or item.get('id'))}</b>",
                money(item.get("price_per_tco2e")),
                money(value.get("low")),
                money(value.get("central")),
                money(value.get("high")),
            )
        )
    header = (
        "Scenario",
        f"Price per {pretty_unit('tCO2e')}",
        "Value per year: low",
        "central",
        "high",
    )
    basis = _dict(data.get("basis"))
    notes = " ".join(esc(n) for n in (basis.get("note"), basis.get("region_note")) if n)
    as_of = f" (prices as of {esc(basis.get('as_of'))})" if basis.get("as_of") else ""
    status = str(basis.get("verification_status") or "")
    disclaimer = data.get("disclaimer") or "Market-value scenario, not guaranteed revenue."
    return (
        heading
        + _table(rows, header=header)
        + _p(f"{notes}{as_of}" if notes else "")
        + _p(
            f"Price table verification status: <b>{esc(status)}</b>."
            if status not in ("", "verified")
            else ""
        )
        + _p(f"<i>{esc(disclaimer)}</i>")
    )


def _other_income_section(market: Mapping[str, Any] | None) -> str:
    heading = "<h3>3 · Other farm income: reported separately</h3>"
    items = _dicts(_dict(market).get("other_income"))
    if not items:
        return heading + _unavailable()
    rows = []
    for item in items:
        value = item.get("value")
        if to_number(value) is None:
            shown = "not provided"
        else:
            shown = esc(f"{fmt_num(value, 0)} {item.get('unit') or ''}".strip())
        rows.append((esc(item.get("label") or item.get("id")), shown, esc(item.get("source"))))
    return (
        heading
        + _table(rows, header=("Source of income", "Value", "Where the figure comes from"))
        + _p(
            "The API leaves these empty until district statistics or your own records are "
            "supplied; nothing is estimated for you."
        )
    )


def _policy_section(policy: Mapping[str, Any] | None, error: str | None) -> str:
    heading = "<h3>Programme screening: initial screening, not an eligibility determination</h3>"
    data = _dict(policy)
    programmes = _dicts(data.get("programmes"))
    if not programmes:
        return heading + _unavailable(error)
    parts = [heading]
    for programme in programmes:
        status = programme.get("status")
        authority = f"<br>{esc(programme.get('authority'))}" if programme.get("authority") else ""
        kind = f" ({esc(words(programme.get('kind')))})" if programme.get("kind") else ""
        badge = _badge(words(status) or "unknown", str(status or ""))
        parts.append(
            _p(
                f"<b>{esc(programme.get('name') or programme.get('id'))}</b>{authority}{kind}"
                f"<br>Status: {badge}"
            )
        )
        requirements = [esc(r) for r in _list(programme.get("requirements"))]
        if requirements:
            parts.append(_p("What it would require:") + _bullets(requirements))
        parts.append(_bullets(esc(n) for n in _list(programme.get("notes"))))
        references = _references(programme.get("references"), limit=3)
        parts.append(_p(f"Sources: {references}" if references else ""))
    parts.append(_p(f"<i>{esc(data.get('disclaimer') or 'Initial screening only.')}</i>"))
    return "".join(parts)


def _readiness_section(readiness: Any) -> str:
    heading = "<h3>Evidence readiness</h3>"
    data = _dict(readiness)
    if not data:
        return heading + _unavailable()
    present = [esc(e.get("label") or e.get("id")) for e in _dicts(data.get("present_evidence"))]
    missing = []
    for entry in _dicts(data.get("missing_evidence")):
        weight = f" (weight {esc(entry.get('weight'))})" if entry.get("weight") is not None else ""
        missing.append(esc(entry.get("label") or entry.get("id")) + weight)
    return (
        heading
        + _p(
            f"Readiness score: <b>{fmt_num(data.get('score'), 0)}</b> "
            f"(grade: {esc(data.get('grade') or NOT_AVAILABLE)}). A higher score means more of "
            "the evidence a programme would ask for is already present; it is not a "
            "probability of certification."
        )
        + _p(f"Present: {', '.join(present)}." if present else "")
        + (_p("Still missing:") + _bullets(missing) if missing else "")
    )


def _estimate_footer(est: Mapping[str, Any]) -> str:
    provenance = _dict(est.get("provenance"))
    generated = est.get("generated_at") or provenance.get("generated_at")
    bits = [
        f"estimate {esc(est.get('estimate_id'))}" if est.get("estimate_id") else "",
        f"plot {esc(est.get('plot_id'))}" if est.get("plot_id") else "",
        f"inventory {esc(est.get('inventory_id'))}" if est.get("inventory_id") else "",
        f"generated {esc(generated)}" if generated else "",
        f"server mode {esc(provenance.get('mode'))}" if provenance.get("mode") else "",
    ]
    notes = [esc(n) for n in _list(est.get("notes"))]
    return (
        "<hr>"
        + _p(_SEP.join(b for b in bits if b))
        + (_p("Notes from the carbon engine:") + _bullets(notes) if notes else "")
        + _provenance_block([provenance])
    )


# --------------------------------------------------------------------------- agent transcript
def format_agent_run(run: Mapping[str, Any]) -> str:
    """Transcript page for ``POST /plots/{id}/agents/run`` (every field is optional)."""
    data = _dict(run)
    plan, reasoner = _dict(data.get("plan")), _dict(data.get("reasoner"))
    status = data.get("status")
    head = []
    if plan.get("title") or plan.get("id"):
        head.append(f"Plan: <b>{esc(plan.get('title') or plan.get('id'))}</b>")
    if status:
        head.append(f"Status: {_badge(status, str(status))}")
    if reasoner:
        provider = f", provider {esc(reasoner.get('provider'))}" if reasoner.get("provider") else ""
        head.append(f"Reasoner: <b>{esc(reasoner.get('mode') or NOT_AVAILABLE)}</b>{provider}")
    if to_number(data.get("duration_ms")) is not None:
        head.append(f"Duration: {fmt_ms(data.get('duration_ms'))}")
    parts = [
        "<h2>AI agent team</h2>",
        disclaimer_banner(data.get("certified"), [data.get("disclaimer")]),
        _p("<br>".join(head)),
    ]
    if str(reasoner.get("mode") or "").lower() == "llm":
        parts.append(
            _p(
                "<i>Parts of this transcript were written by a language model. Check every "
                "statement against the figures on the carbon estimate page.</i>"
            )
        )
    planned = [esc(s) for s in _list(plan.get("steps"))]
    if planned:
        parts.append("<h3>Plan</h3>" + _bullets(planned))
    steps = _dicts(data.get("steps"))
    if steps:
        rows = [
            (
                esc(s.get("step")),
                esc(s.get("agent")),
                _badge(s.get("status") or NOT_AVAILABLE, str(s.get("status") or "")),
                fmt_ms(s.get("duration_ms")),
            )
            for s in steps
        ]
        parts.append("<h3>Steps</h3>" + _table(rows, header=("#", "Agent", "Status", "Time")))

    messages = _dicts(data.get("messages"))
    parts.append("<h3>Transcript</h3>")
    parts.extend(_format_message(m) for m in messages)
    if not messages:
        parts.append(_p("The server returned no messages."))

    guardrails = _dicts(data.get("guardrails"))
    if guardrails:
        items = [
            f"{_badge(str(g.get('status') or 'unknown').upper(), str(g.get('status') or ''))} "
            f"<b>{esc(g.get('id'))}</b> {esc(g.get('detail'))}"
            for g in guardrails
        ]
        parts.append("<h3>Guardrails</h3>" + _bullets(items))
    headline = _get(data, "summary", "headline")
    if headline:
        parts.append("<h3>Summary</h3>" + _p(f"<b>{esc(headline)}</b>"))
    run_bits = [
        f"run {esc(data.get('run_id'))}" if data.get("run_id") else "",
        f"plot {esc(data.get('plot_id'))}" if data.get("plot_id") else "",
        f"started {esc(data.get('started_at'))}" if data.get("started_at") else "",
        f"finished {esc(data.get('finished_at'))}" if data.get("finished_at") else "",
    ]
    parts.append("<hr>" + _p(_SEP.join(b for b in run_bits if b)))
    return page("AI agent team", "".join(parts))


def _format_message(message: Mapping[str, Any]) -> str:
    title = message.get("agent_title") or message.get("agent") or "Agent"
    kind = str(message.get("kind") or "").strip()
    kind_html = f" {_badge(kind, kind if kind in _STATUS_COLOURS else None)}" if kind else ""
    to_html = f" → {esc(message.get('to'))}" if message.get("to") else ""
    step = f"step {esc(message.get('step'))}{_SEP}" if message.get("step") is not None else ""
    meta = f"{step}{esc(message.get('created_at') or '')}{to_html}"
    meta_html = f'<br><span style="color:#6c757d;">{meta}</span>' if meta.strip() else ""
    parts = [
        _p(f"<b>{esc(title)}</b>{kind_html}{meta_html}"),
        _p(esc_multiline(message.get("text") or "")),
    ]
    calls = []
    for call in _dicts(message.get("tool_calls")):
        status = str(call.get("status") or "")
        duration = f", {fmt_ms(call.get('duration_ms'))}" if fmt_ms(call.get("duration_ms")) else ""
        calls.append(
            f"<code>{esc(call.get('tool') or 'tool')}</code> "
            f"{_badge(status or NOT_AVAILABLE, status)}{duration}"
        )
    if calls:
        parts.append(_p("Tool calls:") + _bullets(calls))
    evidence = []
    for item in _dicts(message.get("evidence")):
        label = item.get("label") or item.get("source") or item.get("url")
        source = f" ({esc(item.get('source'))})" if item.get("source") and item.get("label") else ""
        evidence.append(link(label, item.get("url")) + source)
    if evidence:
        parts.append(_p("Evidence:") + _bullets(evidence))
    if message.get("confidence"):
        parts.append(_p(f"Confidence: <b>{esc(message.get('confidence'))}</b>"))
    return "".join(parts)
