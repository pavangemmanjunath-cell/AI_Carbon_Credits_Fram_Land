"""Carbon by tree age — a thin, deterministic layer over :class:`TreeBiomassModel`.

Question answered: *"I have N trees of species S that are A years old — how much carbon
do they hold now, how fast are they adding more, and what does the age curve look like?"*

No coefficient is defined here: every growth, wood-density, root-to-shoot, carbon-fraction
and uncertainty value comes from ``config/`` through the parameter store, exactly as in the
plot-based estimate, and appears in ``parameters_used`` with its source and
``verification_status``. This module only turns an *age* into the inputs the model needs.

Tier 1 path (age only, ``method = "tier1-age"``)
------------------------------------------------
* ``plantation_year = as_of_year − age`` and the model runs for
  ``horizon = max(age + 20, 40)`` years, so the curve always shows 20 years beyond today
  (at least 40 years in total).
* ``stored_now`` is the cumulative removal from planting up to today (the series'
  ``cum_*`` at ``age``); ``annual_now`` is the series value at ``age`` (tCO2e per year in
  that year, with the model's ±uncertainty).
* **Survival.** For ``age ≥ 1`` the model is run with ``survival_rate = 1.0``: the trees the
  caller lists are *counted alive today*, so the mortality they went through is already in
  that count and must not be applied a second time. For ``age = 0`` (trees being
  *planned*) the model's configured default survival is kept, because some planted trees
  will die.
* **Area.** Without ``area_hectares`` the stand is assumed to sit at the species'
  ``reference_density_per_ha`` (area = trees ÷ reference density, i.e. a density factor of
  exactly 1.0). With ``area_hectares`` the model's own density factor applies: very dense
  planting is capped and very sparse planting is floored by its clamp (which *raises* the
  per-tree figure of a sparse stand), so the API does not pass a plot area for scattered trees.
* **Precision.** The model rounds its series to 3 decimals of tCO2e, which is coarse for a
  stand of a handful of trees. The model is therefore run on ``k`` identical copies of the
  stand (``k·trees`` on ``k·area``, same density) and the results are divided by ``k``;
  Tier 1 is exactly linear in stand size at constant density, so nothing else changes.

Girth path (trunk circumference supplied, ``method = "tier2-girth"``)
---------------------------------------------------------------------
``DBH = girth / π`` is passed as ``average_dbh_cm`` (with ``height_m`` when given) so the
model's Tier 2 path applies Chave et al. (2014) equation 4. ``stored_now`` is the Tier 2
stock; ``annual_now`` is the Tier 2 headline, **stock ÷ age** (a documented simplification:
it averages the tree's whole life, so it understates a young tree's current growth and
overstates an old tree's). The *curve* still comes from the Tier 1 run and is labelled
``curve_method = "tier1-age"``; it can differ from ``stored_now`` at the current age.

Long lives
----------
The model horizon always reaches the current age (a stock can only be read from a run that
covers it). When the horizon reaches 150 years the returned curve is thinned to at most 150
points (ages 0, the current age and the last age are always kept).

Everything returned is a scenario estimate: ``certified`` is always ``False``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from carbon_engine.confidence import confidence_for_inventory
from carbon_engine.errors import ModelInputError
from carbon_engine.models.tree_biomass import UNIT_ANNUAL, UNIT_STOCK, TreeBiomassModel
from carbon_engine.parameters import ParameterStore, worst_verification_status
from carbon_engine.types import (
    DISCLAIMER,
    CarbonEstimate,
    ClimateInput,
    InventoryInput,
    Methodology,
    ModelParams,
    ParameterUsed,
    PlotInput,
    Range,
    SeriesPoint,
)

METHOD_TIER1 = "tier1-age"
METHOD_TIER2 = "tier2-girth"

#: the curve always reaches this many years beyond today …
CURVE_YEARS_AHEAD = 20
#: … and covers at least this many years in total (API contract, "v0.2 additions").
CURVE_MIN_YEARS = 40
#: the largest number of curve points returned (API contract: "≤ 150 points").
MAX_CURVE_POINTS = 150
_FULL_RESOLUTION_HORIZON = MAX_CURVE_POINTS - 1

#: size the model runs at so its 3-decimal rounding is negligible (see module docstring).
_UNIT_STAND_TREES = 1000

#: published calibration range of Chave et al. (2014) eq. 4 (see ``equations.allometric``).
_CHAVE_DBH_RANGE_CM = (5.0, 212.0)

_KG_PER_T = 1000.0
_PRECISION_T = 3
_PRECISION_KG = 1


@dataclass(frozen=True)
class AgeCurvePoint:
    """One age on the curve: stored carbon (with range) and the annual removal in that year."""

    age: int
    stored: float
    stored_low: float
    stored_high: float
    annual: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "age": self.age,
            "stored": self.stored,
            "stored_low": self.stored_low,
            "stored_high": self.stored_high,
            "annual": self.annual,
        }


@dataclass
class AgeAssessment:
    """Result of :func:`assess_by_age` — never certified, always a range with provenance."""

    method: str
    curve_method: str
    age_years: int
    tree_count: int
    plantation_year: int
    as_of_year: int
    area_hectares: float
    area_basis: str
    stored_now: Range
    annual_now: Range
    per_tree_stored_now_kg_co2e: float
    per_tree_annual_now_kg_co2e: float
    curve: list[AgeCurvePoint]
    parameters_used: list[ParameterUsed]
    notes: list[str]
    confidence: str
    model_id: str
    model_version: str
    methodology: Methodology
    provenance: dict[str, Any]
    certified: bool = False
    disclaimer: str = DISCLAIMER
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """The ``carbon`` block of the API's TreeAgeAssessment."""
        return {
            "method": self.method,
            "curve_method": self.curve_method,
            "stored_now": self.stored_now.to_dict(),
            "annual_now": self.annual_now.to_dict(),
            "per_tree": {
                "stored_now_kg_co2e": self.per_tree_stored_now_kg_co2e,
                "annual_now_kg_co2e": self.per_tree_annual_now_kg_co2e,
            },
            "curve": [point.to_dict() for point in self.curve],
            "confidence": self.confidence,
            "model": {
                "id": self.model_id,
                "version": self.model_version,
                "tier": "2" if self.method == METHOD_TIER2 else "1",
            },
            "methodology": self.methodology.to_dict(),
            "parameters_used": [p.to_dict() for p in self.parameters_used],
            "notes": list(self.notes),
        }


# --------------------------------------------------------------------------- public API
def assess_by_age(
    store: ParameterStore,
    species_id: str,
    age_years: int,
    tree_count: int,
    climate: ClimateInput,
    girth_cm: float | None = None,
    height_m: float | None = None,
    as_of_year: int | None = None,
    allow_pending: bool = True,
    area_hectares: float | None = None,
) -> AgeAssessment:
    """Carbon stored now, annual removal now and the age curve for ``tree_count`` trees.

    Raises :class:`~carbon_engine.errors.ModelInputError` for out-of-domain inputs,
    :class:`~carbon_engine.errors.UnknownSpeciesError` /
    :class:`~carbon_engine.errors.UnknownClimateZoneError` for unknown ids and
    :class:`~carbon_engine.errors.PendingParameterError` when ``allow_pending`` is false
    and a used parameter is still ``pending``.
    """
    age = _validate(age_years, tree_count, girth_cm, height_m, area_hectares)
    species = store.species(species_id)  # UnknownSpeciesError
    year_now = int(as_of_year) if as_of_year is not None else datetime.now(UTC).year
    plantation_year = year_now - age
    horizon = max(age + CURVE_YEARS_AHEAD, CURVE_MIN_YEARS)

    reference_density = store.species_param(species_id, "reference_density_per_ha", "trees/ha")
    if area_hectares is None:
        area = tree_count / float(reference_density.value)
        area_basis = "stand at the species' reference density"
    else:
        area = float(area_hectares)
        area_basis = "area supplied by the caller"

    copies = max(1, math.ceil(_UNIT_STAND_TREES / tree_count))
    plot = PlotInput(area_hectares=area * copies, has_polygon=False)
    model = TreeBiomassModel(store)
    run_params = ModelParams(
        horizon_years=horizon, as_of_year=year_now, allow_pending_parameters=allow_pending
    )
    # trees already standing are counted alive; new trees keep the model's default survival
    survival = 1.0 if age >= 1 else None

    tier1 = model.estimate(
        plot,
        InventoryInput(
            species_id,
            tree_count * copies,
            plantation_year,
            survival_rate=survival,
            measurement_source="age-assessment",
        ),
        climate,
        run_params,
    )
    series = tier1.annual_series
    ages = _curve_ages(horizon, age)
    curve = [_curve_point(series[a], copies) for a in ages]

    used: list[ParameterUsed] = []
    notes: list[str] = []
    if girth_cm is None:
        method = METHOD_TIER1
        point = series[age]
        stored_raw = (point.cum_low, point.cum_central, point.cum_high)
        annual_raw = (point.low, point.central, point.high)
        main = tier1
        used.extend(_with_survival(tier1.parameters_used, age, store))
        confidence = "low"  # nothing about the actual trees is measured
        if height_m is not None:
            notes.append("Height is only used together with trunk girth, so it was ignored.")
        notes.extend(_tier1_notes(tier1, age))
    else:
        method = METHOD_TIER2
        dbh_cm = float(girth_cm) / math.pi
        tier2 = model.estimate(
            plot,
            InventoryInput(
                species_id,
                tree_count * copies,
                plantation_year,
                average_dbh_cm=dbh_cm,
                average_height_m=height_m,
                survival_rate=1.0,
                measurement_source="user-reported",
            ),
            climate,
            run_params,
        )
        stored_raw = (tier2.stock.low, tier2.stock.central, tier2.stock.high)
        annual_raw = (tier2.estimate.low, tier2.estimate.central, tier2.estimate.high)
        main = tier2
        used.extend(_with_survival(tier2.parameters_used, age, store))
        used.append(
            ParameterUsed(
                "average_dbh_cm",
                round(dbh_cm, 2),
                "cm",
                f"reported trunk girth {float(girth_cm):g} cm at 1.3 m ÷ π",
                "assumption",
            )
        )
        used.extend(_extra_curve_parameters(tier1.parameters_used, used))
        confidence, _fields = confidence_for_inventory(
            tree_count, species_id, plantation_year, dbh_cm, height_m, 1.0
        )
        notes.extend(_tier2_notes(tier2, float(girth_cm), dbh_cm))

    if area_hectares is None:
        used.append(
            ParameterUsed(
                "stand_area_hectares",
                round(area, 4),
                "ha",
                f"{tree_count} trees ÷ species reference density "
                f"{float(reference_density.value):g} trees/ha (stand at the reference density)",
                "assumption",
            )
        )
        notes.append(
            f"No area was given, so the {tree_count} trees are treated as a stand at the species' "
            f"reference density of {float(reference_density.value):g} trees per hectare "
            f"({area:.4g} ha)."
        )
    else:
        used.append(
            ParameterUsed(
                "stand_area_hectares", round(area, 4), "ha", "supplied by the caller", "assumption"
            )
        )
    if age == 0:
        notes.append(
            "Age 0 means trees you are planning to plant: nothing is stored yet and the curve is "
            "a scenario for the years ahead."
        )
    pending = sorted({p.name for p in used if p.verification_status == "pending"})
    if pending:
        notes.append(
            "Parameters still pending verification: "
            + ", ".join(pending)
            + ". Treat the figures as screening estimates."
        )
    notes.append(
        "Carbon counted is above- plus below-ground tree biomass, expressed as CO2e; soil, litter "
        "and dead wood are not included."
    )
    notes.append(
        "Scenario estimate only: removals already made by existing trees are not carbon credits."
    )

    stored = _range(stored_raw, copies, UNIT_STOCK)
    annual = _range(annual_raw, copies, UNIT_ANNUAL)
    per_tree_stored = stored_raw[1] / copies * _KG_PER_T / tree_count
    per_tree_annual = annual_raw[1] / copies * _KG_PER_T / tree_count

    provenance = dict(main.provenance)
    provenance["parameter_set"] = {
        **dict(provenance.get("parameter_set") or {}),
        "verification_status": worst_verification_status(used),
    }
    provenance["notes"] = list(notes)
    return AgeAssessment(
        method=method,
        curve_method=METHOD_TIER1,
        age_years=age,
        tree_count=tree_count,
        plantation_year=plantation_year,
        as_of_year=year_now,
        area_hectares=round(area, 6),
        area_basis=area_basis,
        stored_now=stored,
        annual_now=annual,
        per_tree_stored_now_kg_co2e=round(per_tree_stored, _PRECISION_KG),
        per_tree_annual_now_kg_co2e=round(per_tree_annual, _PRECISION_KG),
        curve=curve,
        parameters_used=_dedupe(used),
        notes=notes,
        confidence=confidence,
        model_id=main.model_id,
        model_version=main.model_version,
        methodology=main.methodology,
        provenance=provenance,
        extras={"species": {"id": species["id"], "scientific_name": species["scientific_name"]}},
    )


# --------------------------------------------------------------------------- helpers
def _validate(
    age_years: int,
    tree_count: int,
    girth_cm: float | None,
    height_m: float | None,
    area_hectares: float | None,
) -> int:
    age = int(age_years)
    if age < 0:
        raise ModelInputError("age_years must be zero or more")
    if int(tree_count) < 1 or int(tree_count) != tree_count:
        raise ModelInputError("tree_count must be a whole number of at least 1")
    if girth_cm is not None:
        if girth_cm <= 0:
            raise ModelInputError("girth_cm must be positive")
        if age < 1:
            raise ModelInputError(
                "girth_cm needs age_years of at least 1: a tree with a measured trunk is not "
                "newly planted"
            )
    if height_m is not None and height_m <= 0:
        raise ModelInputError("height_m must be positive")
    if area_hectares is not None and area_hectares <= 0:
        raise ModelInputError("area_hectares must be positive")
    return age


def _curve_ages(horizon: int, age: int) -> list[int]:
    """Ages 0…horizon, thinned to at most :data:`MAX_CURVE_POINTS` when the horizon is long."""
    if horizon <= _FULL_RESOLUTION_HORIZON:
        return list(range(horizon + 1))
    stride = math.ceil(horizon / (_FULL_RESOLUTION_HORIZON - 2))
    return sorted({*range(0, horizon + 1, stride), age, horizon})


def _curve_point(point: SeriesPoint, copies: int) -> AgeCurvePoint:
    return AgeCurvePoint(
        age=point.age,
        stored=round(point.cum_central / copies, _PRECISION_T),
        stored_low=round(point.cum_low / copies, _PRECISION_T),
        stored_high=round(point.cum_high / copies, _PRECISION_T),
        annual=round(point.central / copies, _PRECISION_T),
    )


def _range(raw: tuple[float, float, float], copies: int, unit: str) -> Range:
    low, central, high = (round(v / copies, _PRECISION_T) for v in raw)
    return Range(low, central, high, unit)


def _with_survival(
    parameters: Iterable[ParameterUsed], age: int, store: ParameterStore
) -> list[ParameterUsed]:
    """Replace the model's ``survival_rate`` entry (it says "reported") with the real basis."""
    result: list[ParameterUsed] = []
    for param in parameters:
        if param.name == "survival_rate" and age >= 1:
            param = ParameterUsed(
                "survival_rate",
                1.0,
                "fraction",
                "the trees you list are counted alive today, so their past mortality is already "
                "in the count and no further mortality is applied to the existing stand",
                "assumption",
            )
        result.append(param)
    return result


def _extra_curve_parameters(
    curve_parameters: Iterable[ParameterUsed], already: Iterable[ParameterUsed]
) -> list[ParameterUsed]:
    seen = {_key(p) for p in already}
    return [p for p in curve_parameters if _key(p) not in seen and p.name != "survival_rate"]


def _key(param: ParameterUsed) -> tuple[str, str, str]:
    return (param.name, repr(param.value), param.source)


def _dedupe(parameters: Iterable[ParameterUsed]) -> list[ParameterUsed]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ParameterUsed] = []
    for param in parameters:
        key = _key(param)
        if key not in seen:
            seen.add(key)
            unique.append(param)
    return unique


def _named(parameters: Iterable[ParameterUsed], name: str) -> ParameterUsed | None:
    return next((p for p in parameters if p.name == name), None)


_MODEL_NOTE_PREFIXES = ("Headline estimate:", "Climate zone ")


def _model_notes(estimate: CarbonEstimate) -> list[str]:
    """The model's own notes, minus the two that describe its plot-level headline."""
    return [n for n in estimate.notes if not n.startswith(_MODEL_NOTE_PREFIXES)]


def _tier1_notes(tier1: CarbonEstimate, age: int) -> list[str]:
    if age >= 1:
        notes = [
            "Method: stand-level IPCC Tier 1 growth for this species and climate zone, added up "
            "from planting to today. The individual trees are not measured.",
            "The trees you list are counted as alive today, so no further mortality is applied.",
        ]
    else:
        survival = _named(tier1.parameters_used, "survival_rate")
        share = (
            f" {float(survival.value):.0%} of planted trees are assumed to survive."
            if survival
            else ""
        )
        notes = [
            "Method: stand-level IPCC Tier 1 growth for this species and climate zone, applied "
            "to trees planted today; the curve is a scenario, not a measurement." + share
        ]
    maturity = _named(tier1.parameters_used, "maturity_years")
    post = _named(tier1.parameters_used, "post_maturity_increment_factor")
    if maturity is not None and post is not None and age > int(maturity.value):
        notes.append(
            f"These trees are past the species' maturity age ({int(maturity.value)} years): "
            f"stand-level Tier 1 continues at the post-maturity factor ({post.value} of the full "
            "increment) — measure trunk girth for a better estimate."
        )
    notes.extend(_model_notes(tier1))
    return notes


def _tier2_notes(tier2: CarbonEstimate, girth_cm: float, dbh_cm: float) -> list[str]:
    lower_dbh_cm, upper_dbh_cm = _CHAVE_DBH_RANGE_CM
    notes = [
        f"Method: measured trunk girth {girth_cm:g} cm → diameter {dbh_cm:.1f} cm (girth ÷ π), "
        "Chave et al. 2014 equation 4 with the species' wood density, plus roots (IPCC Table 4.4).",
        "Annual removal now is the stored carbon divided by age (a simplification: it averages "
        "the tree's whole life).",
        "The curve is the age-only Tier 1 scenario (curve_method tier1-age), so it can differ "
        "from the measured stored carbon at today's age.",
    ]
    if not lower_dbh_cm <= dbh_cm <= upper_dbh_cm:
        notes.append(
            f"A diameter of {dbh_cm:.1f} cm is outside the {lower_dbh_cm:g}–{upper_dbh_cm:g} cm "
            "range the Chave et al. 2014 equation was fitted on; treat the figure as indicative."
        )
    notes.extend(_model_notes(tier2))
    return notes
