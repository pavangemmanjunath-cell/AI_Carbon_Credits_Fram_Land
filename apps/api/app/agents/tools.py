"""The AgriCarbon toolbox: tools that wrap the existing services.

Each tool is a thin, documented adapter from an agent's request to one or two
service calls (``app.plots``, ``app.analysis``, ``app.carbon`` …). Tools return
small, purpose-built dicts — never geometry or coordinates — and every call is
recorded in the transcript with a redacted summary.

Rules every tool here follows:

* **No new numbers.** Tools pass through what the engines computed. The only
  arithmetic is bookkeeping (a difference of two engine outputs, a percentage
  of a stored share) and it is named as such.
* **No coordinates out.** The plot's geometry and centroid stay inside the
  services; tools return area, place names, shares and ids.
* **Optional features degrade gracefully.** Detection, imports and tree-age
  rules are built by other modules; when they are missing (``ImportError`` /
  ``AttributeError``) or have nothing for this plot (HTTP 404), the call is
  recorded as ``skipped`` with a reason instead of failing the agent.

The first argument of every tool is the :class:`~app.context.AppContext`
(the framework calls it ``deps``).
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any

from app.core.errors import ProblemError
from app.services.registry import service
from atlas_agents import ToolRegistry, ToolSkipped
from carbon_engine import DEFAULT_MODEL_ID
from geo_engine.errors import GeometryError
from geo_engine.geometry import ValidationLimits, validate_polygon

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

TOOLS = ToolRegistry()
"""Every tool the AgriCarbon agents can use (``GET /agents`` lists them per agent)."""

MAX_TREE_CHANGE = 1_000_000


# ----------------------------------------------------------------------------- helpers
def _as_dict(value: Any) -> dict[str, Any]:
    """Accept dicts, Pydantic models and dataclasses from feature services."""
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"unexpected result type {type(value).__name__}")


def _sources(provenance: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Dataset ids, names, versions, licences and URLs from a provenance block."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    blocks = [*((provenance or {}).get("sources") or [])]
    blocks += (provenance or {}).get("parameter_sources") or []
    for src in blocks:
        key = (src.get("id"), src.get("name"))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "id": src.get("id"),
                "label": src.get("name") or src.get("id"),
                "version": src.get("version"),
                "license": src.get("license"),
                "url": src.get("url"),
            }
        )
    return out


def _synthetic(provenance: Mapping[str, Any] | None) -> bool:
    prov = provenance or {}
    return prov.get("mode") == "demo" or any(
        s.get("id") == "synthetic-demo" for s in prov.get("sources") or []
    )


def _analysis(app: AppContext, plot: Mapping[str, Any]) -> dict[str, Any]:
    """The latest stored analysis; runs one (like ``GET /plots/{id}/analysis``) if none exists."""
    analysis = app.repo.get_analysis(plot["plot_id"])
    if analysis is None:
        analysis = app.analysis.analyze(
            dict(plot), ["landcover", "vegetation", "climate", "soil"], None
        )
    return analysis


def _country_label(app: AppContext, country: str | None) -> tuple[str | None, str | None]:
    """Return (region id, readable country).

    ``"IN"`` → ``("IN", "India")``; ``"ES"`` → ``("EU", "ES (European Union)")``.
    """
    region_id = app.regions.resolve(country)
    if not region_id:
        return None, country
    name = app.regions.region(region_id).get("name")
    if country and country.upper() != region_id:
        return region_id, f"{country.upper()} ({name})"
    return region_id, str(name or country)


@contextmanager
def optional_feature(feature: str) -> Iterator[None]:
    """Turn "this feature is not available (yet)" into a *skipped* tool call."""
    try:
        yield
    except ImportError as exc:
        raise ToolSkipped(f"{feature} is not available in this installation yet") from exc
    except AttributeError as exc:  # the module exists but does not offer what the tool expects
        raise ToolSkipped(
            f"{feature} is not available in this installation (incompatible service version)"
        ) from exc
    except ProblemError as exc:
        if exc.status == 404:
            raise ToolSkipped(f"{feature}: {exc.detail}") from exc
        raise


# ----------------------------------------------------------------------------- land
@TOOLS.tool()
def measure_plot(app: AppContext, plot_id: str) -> dict[str, Any]:
    """Measure the plot (area, perimeter) and check that its boundary is a valid polygon."""
    plot = app.plots.require(plot_id)
    limits = ValidationLimits(
        max_vertices=app.settings.atlas_max_plot_vertices,
        max_area_ha=app.settings.atlas_max_plot_area_ha,
    )
    problem: str | None = None
    try:
        validate_polygon(plot["geometry"], limits)
    except GeometryError as exc:
        problem = exc.code  # a stable code such as "self_intersection" — never coordinates
    region_id, country_label = _country_label(app, plot.get("country"))
    return {
        "plot_id": plot["plot_id"],
        "area_hectares": plot["area_hectares"],
        "area_acres": plot["area_acres"],
        "perimeter_m": plot.get("perimeter_m"),
        "boundary_valid": problem is None,
        "boundary_problem": problem,
        "boundary_quality": plot.get("boundary_quality", "exact"),
        "country": plot.get("country"),
        "country_label": country_label,
        "region_id": region_id,
        "state": plot.get("region"),
        "source": plot.get("source"),
    }


@TOOLS.tool()
def land_cover_shares(app: AppContext, plot_id: str) -> dict[str, Any]:
    """Land-cover shares inside the plot (ESA WorldCover classes) from the latest analysis."""
    plot = app.plots.require(plot_id)
    analysis = _analysis(app, plot)
    cover = analysis.get("landcover")
    if not cover:
        warnings = (analysis.get("data_quality") or {}).get("warnings") or []
        reason = next((w for w in warnings if "land cover" in w), "no land-cover result")
        raise LookupError(reason)
    provenance = cover.get("provenance")
    return {
        "dataset": cover.get("dataset"),
        "version": cover.get("version"),
        "resolution_m": cover.get("resolution_m"),
        "cropland_share": cover.get("cropland_share"),
        "tree_cover_share": cover.get("tree_cover_share"),
        "classes": [
            {"label": c.get("name"), "share": c.get("share")} for c in cover.get("classes") or []
        ],
        "synthetic": _synthetic(provenance),
        "sources": _sources(provenance),
    }


@TOOLS.tool()
def climate_zone(app: AppContext, plot_id: str) -> dict[str, Any]:
    """The plot's IPCC climate zone (from climate normals, or the region default)."""
    plot = app.plots.require(plot_id)
    climate = _analysis(app, plot).get("climate")
    if not climate or not climate.get("zone"):
        raise LookupError("no climate result")
    return {
        "zone": climate.get("zone"),
        "label": climate.get("zone_label") or climate.get("zone"),
        "source": climate.get("zone_source"),
        "mean_annual_temp_c": climate.get("mean_annual_temp_c"),
        "annual_precip_mm": climate.get("annual_precip_mm"),
        "verification_status": climate.get("verification_status"),
        "synthetic": _synthetic(climate.get("provenance")),
        "sources": _sources(climate.get("provenance")),
    }


# ----------------------------------------------------------------------------- imagery
@TOOLS.tool()
def vegetation_summary(app: AppContext, plot_id: str) -> dict[str, Any]:
    """Latest NDVI/NDMI with their classes and the multi-year vegetation trend (Sentinel-2)."""
    plot = app.plots.require(plot_id)
    veg = _analysis(app, plot).get("vegetation")
    if not veg or not (veg.get("indices") or {}).get("ndvi"):
        raise LookupError("no satellite vegetation reading for this plot")
    ndvi = veg["indices"]["ndvi"]
    ndmi = veg["indices"].get("ndmi") or {}
    trend = veg.get("trend") or {}
    return {
        "ndvi": ndvi.get("value"),
        "ndvi_class": ndvi.get("class"),
        "ndmi": ndmi.get("value"),
        "ndmi_class": ndmi.get("class"),
        "date": ndvi.get("date"),
        "trend_pct": trend.get("change_pct"),
        "trend_start": trend.get("start"),
        "trend_end": trend.get("end"),
        "observations": len(veg.get("time_series") or []),
        "synthetic": _synthetic(veg.get("provenance")),
        "sources": _sources(veg.get("provenance")),
    }


@TOOLS.tool()
def detect_tree_cover(app: AppContext, plot_id: str) -> dict[str, Any]:
    """Tree-cover patches detected from the vegetation grid (optional detection module).

    Reuses the plot's latest stored tree-cover detection when there is one, so
    repeated runs do not pile up detection records; otherwise runs a new one.
    """
    with optional_feature("Tree-cover detection"):
        from app.services.detection import DetectionService

        detector = service(app, "detection", lambda: DetectionService(app))
        latest = detector.latest(plot_id) if hasattr(detector, "latest") else None
        reused = bool(latest) and _as_dict(latest).get("target", "tree-cover") == "tree-cover"
        raw = latest if reused else detector.detect(plot_id, target="tree-cover")
        result = _as_dict(raw)
    summary = result.get("summary") or {}
    return {
        "reused": reused,
        "detection_id": result.get("detection_id"),
        "patches": summary.get("patches"),
        "covered_fraction": summary.get("covered_fraction"),
        "area_hectares": summary.get("area_hectares"),
        "method": result.get("method"),
        "month": result.get("month"),
        "sources": _sources(result.get("provenance")),
    }


# ----------------------------------------------------------------------------- trees
@TOOLS.tool()
def tree_inventory(app: AppContext, plot_id: str) -> dict[str, Any]:
    """The latest tree inventory: species, count, density, planting year, age and data quality."""
    app.plots.require(plot_id)
    inventory = app.trees.latest(plot_id)
    if inventory is None:
        return {"found": False}
    quality = inventory.get("data_quality") or {}
    species = inventory.get("species") or {}
    return {
        "found": True,
        "inventory_id": inventory["inventory_id"],
        "species_id": species.get("id"),
        "species": species.get("common_name"),
        "scientific_name": species.get("scientific_name"),
        "tree_count": inventory["tree_count"],
        "density_per_ha": inventory.get("density_per_ha"),
        "plantation_year": inventory.get("plantation_year"),
        "age_years": inventory.get("age_years"),
        "survival_rate": inventory.get("survival_rate"),
        "average_dbh_cm": inventory.get("average_dbh_cm"),
        "average_height_m": inventory.get("average_height_m"),
        "measurement_source": inventory.get("measurement_source"),
        "confidence": quality.get("confidence"),
        "missing_fields": [
            f.get("name") for f in quality.get("fields") or [] if f.get("status") == "missing"
        ],
    }


@TOOLS.tool()
def imported_trees(app: AppContext, plot_id: str) -> dict[str, Any]:
    """Tree counts detected in files imported for this plot (optional imports module)."""
    with optional_feature("File imports"):
        from app.services.imports import ImportService

        importer = service(app, "imports", lambda: ImportService(app))
        listed = importer.list(plot_id)
    items = listed.get("items", []) if isinstance(listed, Mapping) else list(listed or [])
    files = []
    for raw in items:
        record = _as_dict(raw)
        trees = record.get("trees") or {}
        if record.get("status") != "ready" or not trees:
            continue
        files.append(
            {
                "import_id": record.get("import_id"),
                "format": record.get("format"),
                "kind": record.get("kind"),
                "count": trees.get("count"),
                "count_in_plot": trees.get("count_in_plot"),
                "mean_height_m": trees.get("mean_height_m"),
                "method": trees.get("method"),
            }
        )
    return {"imports": len(items), "with_trees": files}


# ----------------------------------------------------------------------------- carbon
def _estimate_view(estimate: Mapping[str, Any], reused: bool) -> dict[str, Any]:
    provenance = estimate.get("provenance") or {}
    readiness = estimate.get("readiness") or {}
    parameters = [
        {"parameter": p.get("name"), "verification_status": p.get("verification_status")}
        for p in estimate.get("parameters_used") or []
    ]
    return {
        "estimate_id": estimate["estimate_id"],
        "inventory_id": estimate.get("inventory_id"),
        "reused": reused,
        "estimate": estimate["estimate"],
        "stock": estimate.get("stock"),
        "confidence": estimate.get("confidence"),
        "certified": estimate.get("certified"),
        "disclaimer": estimate.get("disclaimer"),
        "model": estimate.get("model"),
        "methodology": {
            "id": (estimate.get("methodology") or {}).get("id"),
            "name": (estimate.get("methodology") or {}).get("name"),
            "references": (estimate.get("methodology") or {}).get("references") or [],
        },
        "parameter_set": provenance.get("parameter_set"),
        "parameters": parameters,
        "pending_parameters": sorted(
            {str(p["parameter"]) for p in parameters if p["verification_status"] == "pending"}
        ),
        "readiness": {
            "score": readiness.get("score"),
            "grade": readiness.get("grade"),
            # heaviest gaps first: they matter most for the evidence file
            "missing": sorted(
                (
                    {"id": m.get("id"), "label": m.get("label"), "weight": m.get("weight")}
                    for m in readiness.get("missing_evidence") or []
                ),
                key=lambda m: -int(m["weight"] or 0),
            ),
        },
        "sources": _sources(provenance),
    }


@TOOLS.tool()
def estimate_carbon(app: AppContext, plot_id: str) -> dict[str, Any]:
    """Run the carbon engine on the latest tree inventory (or reuse its stored estimate).

    A stored estimate is reused when it was made from the same inventory, so the
    agent reports exactly what ``GET /plots/{id}/carbon-estimate`` shows.
    """
    plot = app.plots.require(plot_id)
    inventory = app.trees.latest(plot_id)
    if inventory is None:
        raise ToolSkipped("no tree inventory for this plot yet")
    latest = app.carbon.latest(plot_id)
    reused = latest is not None and latest.get("inventory_id") == inventory["inventory_id"]
    estimate = (
        latest
        if reused and latest is not None
        else app.carbon.estimate(plot, inventory, DEFAULT_MODEL_ID, None, {})
    )
    return _estimate_view(estimate, reused)


def _parameter(result: Mapping[str, Any], name: str) -> Any:
    for item in result.get("parameters_used") or []:
        if item.get("name") == name:
            return item.get("value")
    return None


@TOOLS.tool()
def simulate_what_if(app: AppContext, plot_id: str, change: int) -> dict[str, Any]:
    """What if the plot had N more (or fewer) trees? Runs the Simulation Lab twice and compares."""
    if not change or abs(int(change)) > MAX_TREE_CHANGE:
        raise ValueError(f"tree change must be between 1 and {MAX_TREE_CHANGE:,} trees")
    plot = app.plots.require(plot_id)
    inventory = app.trees.latest(plot_id)
    if inventory is None:
        raise ToolSkipped("no tree inventory to change yet")
    current = int(inventory["tree_count"])
    new_count = max(0, current + int(change))
    horizon = int(app.store.model_setting("horizon_years_default", "years").value)
    body = {
        "country": plot["country"],
        "species_id": inventory["species"]["id"],
        "tree_count": current,
        "planting_year": int(inventory["plantation_year"]),
        "horizon_years": horizon,
        "survival_rate": inventory.get("survival_rate"),
        "area_hectares": float(plot["area_hectares"]),
        "plot_id": plot_id,
    }
    baseline = app.simulate.simulate(dict(body))
    scenario = app.simulate.simulate({**body, "tree_count": new_count})
    clamp = _parameter(scenario, "density_scaling_clamp")
    reference = _parameter(scenario, "reference_density_per_ha")
    applied = _parameter(scenario, "density_factor_applied")
    cap = None
    if isinstance(clamp, (list, tuple)) and len(clamp) == 2 and reference:
        cap = {"factor": float(clamp[1]), "reference_per_ha": float(reference)}
    return {
        "change": int(change),
        "tree_count_now": current,
        "tree_count_new": new_count,
        "species": inventory["species"].get("common_name"),
        "planting_year": int(inventory["plantation_year"]),
        "horizon_years": horizon,
        "climate_zone": scenario.get("climate_zone_label") or scenario.get("climate_zone"),
        "climate_zone_source": scenario.get("climate_zone_source"),
        "baseline": baseline["annual"],
        "scenario": scenario["annual"],
        # bookkeeping on two engine outputs, not a new estimate:
        "difference_central": round(
            float(scenario["annual"]["central"]) - float(baseline["annual"]["central"]), 2
        ),
        "density_cap": cap,
        "density_capped": bool(
            cap and isinstance(applied, (int, float)) and math.isclose(applied, cap["factor"])
        ),
        "confidence": scenario.get("confidence"),
        "certified": scenario.get("certified", False),
        "disclaimer": scenario.get("disclaimer"),
        "sources": _sources(scenario.get("provenance")),
    }


# ----------------------------------------------------------------------------- policy
@TOOLS.tool()
def screen_programmes(app: AppContext, plot_id: str) -> dict[str, Any]:
    """Screen the country's tree-planting programmes (config-driven, not an eligibility check)."""
    plot = app.plots.require(plot_id)
    screening = app.policy.screen(plot["country"], "tree_plantation", area_ha=plot["area_hectares"])
    _, country_label = _country_label(app, plot.get("country"))
    return {
        "country": screening.get("country"),
        "country_label": country_label,
        "region": screening.get("region"),
        "activity": screening.get("activity"),
        "disclaimer": screening.get("disclaimer"),
        "programmes": [
            {
                "id": p.get("id"),
                "programme": p.get("name"),
                "authority": p.get("authority"),
                "kind": p.get("kind"),
                "status": p.get("status"),
                "url": p.get("url"),
                "references": p.get("references") or [],
                "distinct_from": p.get("distinct_from") or [],
            }
            for p in screening.get("programmes") or []
        ],
    }


@TOOLS.tool()
def assess_tree_age(
    app: AppContext,
    plot_id: str,
    species_id: str,
    age_years: int,
    tree_count: int,
    girth_cm: float | None = None,
    height_m: float | None = None,
) -> dict[str, Any]:
    """Carbon by tree age and the age rules that apply (optional tree-age module)."""
    plot = app.plots.require(plot_id)
    body = {
        "country": plot["country"],
        "subdivision": plot.get("subdivision"),
        "setting": "farm",
        "species_id": species_id,
        "age_years": int(age_years),
        "tree_count": int(tree_count),
        "girth_cm": girth_cm,
        "height_m": height_m,
        "plot_id": plot_id,
    }
    with optional_feature("Tree-age rules"):
        from app.services.tree_age import TreeAgeService

        assessor = service(app, "tree_age", lambda: TreeAgeService(app))
        result = _as_dict(assessor.assess(body))
    carbon = result.get("carbon") or {}
    return {
        "age_years": int(age_years),
        "tree_count": int(tree_count),
        "age_class": result.get("age_class"),
        "climate_zone": result.get("climate_zone"),
        "method": carbon.get("method"),
        "stored_now": carbon.get("stored_now"),
        "annual_now": carbon.get("annual_now"),
        "credit_outlook": result.get("credit_outlook"),
        "rules": [
            {
                "id": r.get("id"),
                "rule": r.get("name") or r.get("id"),
                "applies": r.get("applies"),
                "why": r.get("why"),
                "verification_status": r.get("verification_status"),
            }
            for r in (_as_dict(rule) for rule in result.get("rules") or [])
        ],
        "certified": result.get("certified", False),
        "disclaimer": result.get("disclaimer"),
        "sources": _sources(result.get("provenance")),
    }


# ----------------------------------------------------------------------------- market
@TOOLS.tool()
def market_scenarios(app: AppContext, plot_id: str, estimate_id: str) -> dict[str, Any]:
    """Value scenarios for an estimate (configured prices, not a quote) and other income sources."""
    plot = app.plots.require(plot_id)
    estimate = app.carbon.require(plot_id, estimate_id)
    region_id = app.regions.resolve(plot.get("country"))
    if region_id is None:
        raise LookupError(f"no market configuration for country {plot.get('country')}")
    market = app.market.scenarios_for(region_id, estimate["estimate"])
    basis = market.get("basis") or {}
    return {
        "estimate_id": estimate["estimate_id"],
        "currency": market.get("currency"),
        "currency_symbol": market.get("currency_symbol"),
        "scenarios": [
            {
                "id": s.get("id"),
                "price_per_tco2e": s.get("price_per_tco2e"),
                "value_per_year": s.get("value_per_year"),
            }
            for s in market.get("scenarios") or []
        ],
        "basis": {
            "source": basis.get("source"),
            "as_of": basis.get("as_of"),
            "verification_status": basis.get("verification_status"),
            "references": basis.get("references") or [],
        },
        "other_income": [
            {
                "id": i.get("id"),
                "label": i.get("label"),
                "value": i.get("value"),
                "unit": i.get("unit"),
            }
            for i in market.get("other_income") or []
        ],
        "disclaimer": market.get("disclaimer"),
    }


# ----------------------------------------------------------------------------- review
@TOOLS.tool()
def review_estimate(app: AppContext, plot_id: str, estimate_id: str) -> dict[str, Any]:
    """Check an estimate's range, unit, confidence, certified flag, sources and parameters."""
    estimate = app.carbon.require(plot_id, estimate_id)
    rng = estimate.get("estimate") or {}
    values: list[Any] = [rng.get(k) for k in ("low", "central", "high")]
    numeric = all(isinstance(v, (int, float)) for v in values)
    checks = {
        "a low–central–high range": numeric and values[0] <= values[1] <= values[2],
        "a unit": bool(rng.get("unit")),
        f"a confidence grade ({estimate.get('confidence')})": estimate.get("confidence")
        in ("low", "medium", "high"),
        "certified: false": estimate.get("certified") is False,
        "a disclaimer": bool(estimate.get("disclaimer")),
        "its sources": bool((estimate.get("provenance") or {}).get("sources")),
        "a methodology": bool((estimate.get("methodology") or {}).get("id")),
    }
    statuses: dict[str, int] = {}
    for item in estimate.get("parameters_used") or []:
        status = str(item.get("verification_status"))
        statuses[status] = statuses.get(status, 0) + 1
    readiness = estimate.get("readiness") or {}
    missing = sorted(
        readiness.get("missing_evidence") or [], key=lambda m: -int(m.get("weight") or 0)
    )
    return {
        "estimate_id": estimate["estimate_id"],
        "checks_passed": [name for name, ok in checks.items() if ok],
        "checks_failed": [name for name, ok in checks.items() if not ok],
        "parameter_statuses": statuses,
        "pending_parameters": sorted(
            {
                str(p.get("name"))
                for p in estimate.get("parameters_used") or []
                if p.get("verification_status") == "pending"
            }
        ),
        "readiness_score": readiness.get("score"),
        "readiness_grade": readiness.get("grade"),
        "missing_evidence": [m.get("label") for m in missing],
    }


# ----------------------------------------------------------------------------- report
@TOOLS.tool()
def create_report(
    app: AppContext, plot_id: str, estimate_id: str, language: str = "en"
) -> dict[str, Any]:
    """Render the HTML assessment report for an estimate (report engine)."""
    plot = app.plots.require(plot_id)
    meta = app.reports.create(plot, "html", language, estimate_id)
    return {
        "report_id": meta["report_id"],
        "format": meta["format"],
        "url": f"/api/v1/reports/{meta['report_id']}",
        "estimate_id": meta.get("estimate_id"),
        "generated_at": meta.get("generated_at"),
    }
