# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Multi-call API workflows used by the plugin actions (pure Python, no QGIS imports).

Each function does blocking network I/O, so the plugin runs them in a background task. They
return plain data (dataclasses holding API JSON) and never touch the user interface.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from .api_client import (
    FALLBACK_PLOT_SOURCE,
    PLOT_SOURCE,
    ApiError,
    ApiProblem,
    ApiResponseError,
    AtlasClient,
)
from .formatting import describe_error, to_number
from .geometry import GeometryError, fingerprint, normalize_polygon

log = logging.getLogger(__name__)


@dataclass
class SendResult:
    """Outcome of :func:`send_field_polygon`."""

    plot: dict[str, Any]
    analysis: dict[str, Any] | None = None
    analysis_error: str | None = None
    source_used: str = PLOT_SOURCE
    notes: list[str] = field(default_factory=list)


@dataclass
class CarbonResult:
    """Outcome of :func:`estimate_carbon`: the estimate plus optional market and policy parts."""

    estimate: dict[str, Any]
    market: dict[str, Any] | None = None
    market_error: str | None = None
    policy: dict[str, Any] | None = None
    policy_error: str | None = None


def _require_mapping(value: Any, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApiResponseError(f"The server returned an unexpected answer for {what}.")
    return value


class SpeciesChoice(NamedTuple):
    """One entry of the species drop-down."""

    id: str
    label: str
    max_density_per_ha: float | None = None


def species_choices(payload: Any) -> list[SpeciesChoice]:
    """``GET /species`` payload -> choices for a combo box, sorted by label.

    Tolerates anything: a non-list payload or entries without an ``id`` give fewer (or no)
    choices, never an exception. The label is ``Common name (Scientific name)``.
    """
    items = payload if isinstance(payload, list) else []
    choices: list[SpeciesChoice] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        species_id = str(item.get("id") or "").strip()
        if not species_id or species_id in seen:
            continue
        seen.add(species_id)
        common = str(item.get("common_name") or "").strip()
        scientific = str(item.get("scientific_name") or "").strip()
        if common and scientific:
            label = f"{common} ({scientific})"
        else:
            label = common or scientific or species_id
        maximum = to_number(item.get("max_density_per_ha"))
        usable = maximum if maximum is not None and maximum > 0 else None
        choices.append(SpeciesChoice(species_id, label, usable))
    return sorted(choices, key=lambda choice: choice.label.lower())


def density_note(
    tree_count: int, area_hectares: Any, max_density_per_ha: float | None = None
) -> str:
    """One line about the stand density, with a warning above the species maximum.

    ``max_density_per_ha`` is the value the server lists for the species; it is only used to
    flag counts that look too high (for example crowns counted twice), never to change them.
    """
    area = to_number(area_hectares)
    if not area or area <= 0 or tree_count < 0:
        return ""
    density = tree_count / area
    text = f"About {density:,.0f} trees per hectare on {area:,.2f} ha."
    if max_density_per_ha and density > max_density_per_ha:
        text += (
            f" That is above the {max_density_per_ha:,.0f} trees/ha the server lists as the "
            "maximum for this species: check the count against the imagery before sending."
        )
    return text


def plot_fingerprint(plot: Mapping[str, Any]) -> str | None:
    """Fingerprint of the polygon in an API plot (``None`` when it has no usable geometry).

    The owner view of ``GET /plots/{id}`` includes the geometry; a public view does not.
    """
    try:
        return fingerprint(normalize_polygon(plot.get("geometry")))
    except GeometryError:
        return None


def fetch_plot(client: AtlasClient, plot_id: str) -> dict[str, Any]:
    """``GET /plots/{plot_id}`` with a sanity check on the answer."""
    plot = _require_mapping(client.get_plot(plot_id), "the plot")
    if not isinstance(plot.get("plot_id"), str) or not plot["plot_id"]:
        raise ApiResponseError("The server did not return a plot id.")
    return plot


def send_field_polygon(
    client: AtlasClient, polygon: dict[str, Any], name: str, country: str | None = None
) -> SendResult:
    """Create a plot from a validated polygon, then run the analysis.

    The plot is sent with ``source: "qgis-plugin"``. Servers that predate that value answer
    422 for the ``source`` field; the call is then repeated once with ``source: "api"`` and the
    result says so. A failing analysis does not lose the plot: it is reported in
    ``analysis_error`` so the user keeps the plot id.
    """
    notes: list[str] = []
    source = PLOT_SOURCE
    try:
        created = client.create_plot(polygon, name, country, source=source)
    except ApiProblem as exc:
        if exc.status != 422 or not exc.mentions_field("source"):
            raise
        source = FALLBACK_PLOT_SOURCE
        notes.append(
            "This server does not know the plot source 'qgis-plugin' yet, so the plot was "
            "created with source 'api'."
        )
        log.info("server rejected plot source %s; retrying with %s", PLOT_SOURCE, source)
        created = client.create_plot(polygon, name, country, source=source)
    plot = _require_mapping(created, "the new plot")
    plot_id = plot.get("plot_id")
    if not isinstance(plot_id, str) or not plot_id:
        raise ApiResponseError("The server did not return a plot id.")

    result = SendResult(plot=plot, source_used=source, notes=notes)
    try:
        result.analysis = _require_mapping(client.analyze_plot(plot_id), "the analysis")
    except ApiError as exc:
        result.analysis_error = describe_error(exc)
        log.warning("analysis failed for %s after the plot was created", plot_id)
    return result


def post_tree_inventory(
    client: AtlasClient,
    plot_id: str,
    species_id: str,
    tree_count: int,
    plantation_year: int,
) -> dict[str, Any]:
    """Record a crown-count based inventory (``measurement_source: "model-estimated"``)."""
    created = client.create_tree_inventory(
        plot_id,
        species_id,
        tree_count,
        plantation_year,
        measurement_source="model-estimated",
    )
    return _require_mapping(created, "the tree inventory")


def estimate_carbon(
    client: AtlasClient,
    plot_id: str,
    inventory_id: str | None = None,
    activity: str = "tree_plantation",
) -> CarbonResult:
    """Run the carbon estimate, then fetch the market scenarios and the programme screening.

    The estimate is required. The other two parts are best effort: if one fails, its message
    is kept next to the result and the rest is still shown.
    """
    estimate = _require_mapping(client.estimate_carbon(plot_id, inventory_id), "the estimate")
    result = CarbonResult(estimate=estimate)
    estimate_id = estimate.get("estimate_id")
    try:
        result.market = _require_mapping(
            client.get_market_scenario(
                plot_id, estimate_id if isinstance(estimate_id, str) else None
            ),
            "the market scenarios",
        )
    except ApiError as exc:
        result.market_error = describe_error(exc)
    try:
        result.policy = _require_mapping(
            client.get_policy_eligibility(plot_id, activity), "the programme screening"
        )
    except ApiError as exc:
        result.policy_error = describe_error(exc)
    return result


def run_agent_team(
    client: AtlasClient, plot_id: str, plan: str = "full-assessment", locale: str = "en"
) -> dict[str, Any]:
    """Run the multi-agent assessment and return the raw response (shape is read defensively)."""
    return _require_mapping(client.run_agents(plot_id, plan=plan, locale=locale), "the agent run")
