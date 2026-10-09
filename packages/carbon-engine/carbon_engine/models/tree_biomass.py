"""``tree-biomass`` v0.1 — IPCC 2006 Tier 1 gain-loss with an optional
Tier 2 (measured DBH) path.

Methodology: 2006 IPCC Guidelines Vol. 4 (AFOLU) Ch. 4 Forest Land, Tier 1
gain-loss method (Eq. 2.9/2.10: ΔC = A · G_total · CF, with
G_total = G_w · (1 + R)), parameters from Tables 4.3 (CF), 4.4 (R) and
4.10/4.12 (G_w); allometry from Chave et al. (2014) eq. 4. Every number used
comes from ``config/`` and is listed in ``parameters_used`` with its source and
verification status — the model itself holds no coefficients.

Tier 1 path (no DBH)
--------------------
For every year ``y`` from ``plantation_year`` to ``plantation_year + horizon``::

    age            = y − plantation_year
    ramp(age)      = min(age / years_to_full_increment, 1)        (0 at planting)
    maturity(age)  = 1 if age ≤ species.maturity_years else post_maturity_increment_factor
    density_factor = clamp(planted_density / reference_density, clamp_lo, clamp_hi)
    ΔAGB [t d.m./ha] = G_w(zone) · increment_multiplier · density_factor · ramp · maturity · survival
    AGB_stock      += ΔAGB                   (selects the root-to-shoot class, Table 4.4)
    ΔB              = ΔAGB · (1 + R(zone, AGB_stock))
    ΔCO₂e [t/yr]    = ΔB · CF · (44/12) · area_ha

``low/high = central × (1 ∓ uncertainty_fraction_tier1)``. The headline
``estimate`` is the **mean annual removal over the horizon** (time-invariant,
so shareable simulations stay deterministic); ``stock`` is the cumulative
removal up to ``as_of_year``.

Tier 2 path (DBH supplied)
--------------------------
``AGB_kg = 0.0673 · (ρ · D² · H)^0.976`` per tree (height = reported, else the
species' typical mature height scaled by ``min(age / maturity_years, 1)`` with a
10 % floor); ``stock = N · survival · AGB · (1 + R) · CF · 44/12 / 1000``;
``estimate = stock / max(age, 1)`` (documented simplification), with
``uncertainty_fraction_tier2``. The series spreads the stock evenly over the
stand age and carries the rate forward until maturity.

Assumptions beyond the IPCC tables are in ``tree-biomass-model.yaml`` and
appear in ``parameters_used`` with ``verification_status: assumption``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from carbon_engine.confidence import confidence_for_inventory
from carbon_engine.equations.allometric import CHAVE_2014_EQ4, chave_2014_agb_kg
from carbon_engine.errors import ModelInputError
from carbon_engine.parameters import (
    ParameterStore,
    assert_production_safe,
    get_store,
    worst_verification_status,
)
from carbon_engine.readiness import score_readiness
from carbon_engine.types import (
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
from carbon_engine.uncertainty import bounds_from_fraction, clamp

METHODOLOGY_ID = "ipcc-2006-vol4-ch4"
UNIT_ANNUAL = "tCO2e/yr"
UNIT_STOCK = "tCO2e"
KG_PER_T = 1000.0
MIN_HEIGHT_FRACTION = 0.1


def _year_now() -> int:
    return datetime.now(UTC).year


class TreeBiomassModel:
    """See module docstring."""

    def __init__(self, store: ParameterStore | None = None) -> None:
        self.store = store or get_store()
        self.id = self.store.model_id
        self.version = self.store.model_version

    # ------------------------------------------------------------------ public
    def estimate(
        self,
        plot: PlotInput,
        inventory: InventoryInput,
        climate: ClimateInput,
        params: ModelParams | None = None,
    ) -> CarbonEstimate:
        params = params or ModelParams()
        self._validate(plot, inventory)
        species = self.store.species(inventory.species_id)
        used: list[ParameterUsed] = []
        notes: list[str] = []

        horizon_param = self.store.model_setting("horizon_years_default", "years")
        horizon = int(params.horizon_years or horizon_param.value)
        as_of_year = params.as_of_year or _year_now()
        if params.horizon_years is None:
            used.append(horizon_param)

        survival_param = self._survival(inventory, used)
        survival = float(survival_param.value)

        if inventory.average_dbh_cm:
            tier = "2"
            series, components, headline, stock_now = self._tier2(
                plot, inventory, climate, species, survival, horizon, as_of_year, used, notes
            )
        else:
            tier = "1"
            series, components, headline, stock_now = self._tier1(
                plot,
                inventory,
                climate,
                species,
                survival,
                horizon,
                as_of_year,
                params,
                used,
                notes,
            )

        assert_production_safe(used, params.allow_pending_parameters)

        confidence, _fields = confidence_for_inventory(
            inventory.tree_count,
            inventory.species_id,
            inventory.plantation_year,
            inventory.average_dbh_cm,
            inventory.average_height_m,
            inventory.survival_rate,
        )
        present = {
            "polygon": plot.has_polygon,
            "tree_count": inventory.tree_count > 0,
            "species": True,
            "age": True,
            "satellite": plot.has_satellite_observation,
            "dbh": bool(inventory.average_dbh_cm),
            "height": bool(inventory.average_height_m),
            "baseline": bool(params.evidence.get("baseline", False)),
            "management": bool(params.evidence.get("management", False)),
            "ownership": bool(params.evidence.get("ownership", False)),
        }
        readiness = score_readiness(present, self.store.readiness_config)
        methodology = self._methodology()
        provenance = self._provenance(used, tier, climate, species)
        notes.append(
            f"Headline estimate: {self.store.model_config['headline_definition']['tier' + tier]}."
        )
        notes.append(f"Climate zone {climate.zone!r} from {climate.zone_source}.")
        provenance["notes"] = list(notes)
        return CarbonEstimate(
            model_id=self.id,
            model_version=self.version,
            tier=tier,
            methodology=methodology,
            estimate=headline,
            stock=stock_now,
            components=components,
            annual_series=series,
            parameters_used=used,
            confidence=confidence,
            readiness=readiness,
            provenance=provenance,
            notes=notes,
        )

    # ------------------------------------------------------------------ tier 1
    def _tier1(
        self,
        plot: PlotInput,
        inventory: InventoryInput,
        climate: ClimateInput,
        species: dict[str, Any],
        survival: float,
        horizon: int,
        as_of_year: int,
        params: ModelParams,
        used: list[ParameterUsed],
        notes: list[str],
    ) -> tuple[list[SeriesPoint], dict[str, float], Range, Range]:
        store = self.store
        growth = store.growth(climate.zone)
        multiplier = store.species_param(
            inventory.species_id, "increment_multiplier", "dimensionless"
        )
        reference_density = store.species_param(
            inventory.species_id, "reference_density_per_ha", "trees/ha"
        )
        maturity = store.species_param(inventory.species_id, "maturity_years", "years")
        carbon_fraction = store.constant("carbon_fraction")
        co2_per_c = store.constant("co2_per_c")
        clamp_lo, clamp_hi, clamp_param = store.density_clamp()
        post_maturity = store.model_setting("post_maturity_increment_factor", "fraction")
        u_low, u_high = store.uncertainty_fraction(1)
        if params.years_to_full_increment is not None:
            ramp_years = ParameterUsed(
                "years_to_full_increment",
                float(params.years_to_full_increment),
                "years",
                "caller-supplied",
                "assumption",
            )
        else:
            ramp_years = store.assumption_param("years_to_full_increment_default", "years")
        used.extend(
            [
                growth,
                multiplier,
                reference_density,
                maturity,
                carbon_fraction,
                co2_per_c,
                clamp_param,
                ramp_years,
                post_maturity,
                u_low,
                u_high,
            ]
        )

        planted_density = inventory.tree_count / plot.area_hectares
        raw_factor = planted_density / float(reference_density.value)
        # No trees → no increment; the clamp floor only applies to sparse stands.
        density_factor = clamp(raw_factor, clamp_lo, clamp_hi) if inventory.tree_count > 0 else 0.0
        used.append(
            ParameterUsed(
                "density_factor_applied",
                round(density_factor, 4),
                "ratio to reference density",
                f"planted density {planted_density:.1f} trees/ha ÷ reference "
                f"{float(reference_density.value):.0f} trees/ha, clamped to [{clamp_lo}, {clamp_hi}]",
                "assumption",
            )
        )
        if raw_factor != density_factor:
            notes.append(
                f"Stocking density ratio {raw_factor:.2f} clamped to {density_factor:.2f}."
            )
        if climate.zone not in species.get("suitable_climate_zones", []):
            notes.append(
                f"Species {inventory.species_id!r} is not listed as suitable for climate zone "
                f"{climate.zone!r}; growth parameters may not apply."
            )

        cf = float(carbon_fraction.value)
        co2 = float(co2_per_c.value)
        full_increment = float(growth.value) * float(multiplier.value) * density_factor * survival
        maturity_years = int(maturity.value)
        ramp_len = max(float(ramp_years.value), 1e-9)
        agb_stock_per_ha = 0.0
        series: list[SeriesPoint] = []
        above_total = 0.0
        below_total = 0.0
        cum_low = cum_central = cum_high = 0.0
        r_params_used: list[ParameterUsed] = []
        for age in range(0, horizon + 1):
            year = inventory.plantation_year + age
            ramp = min(age / ramp_len, 1.0)
            maturity_factor = 1.0 if age <= maturity_years else float(post_maturity.value)
            agb_increment = full_increment * ramp * maturity_factor
            agb_stock_per_ha += agb_increment
            r_param = store.root_to_shoot(climate.zone, agb_stock_per_ha)
            if r_param not in r_params_used:
                r_params_used.append(r_param)
            r = float(r_param.value)
            above = agb_increment * cf * co2 * plot.area_hectares
            below = agb_increment * r * cf * co2 * plot.area_hectares
            central = above + below
            low, _, high = bounds_from_fraction(central, float(u_low.value), float(u_high.value))
            cum_low += low
            cum_central += central
            cum_high += high
            above_total += above
            below_total += below
            series.append(
                SeriesPoint(
                    year=year,
                    age=age,
                    low=round(low, 3),
                    central=round(central, 3),
                    high=round(high, 3),
                    cum_low=round(cum_low, 3),
                    cum_central=round(cum_central, 3),
                    cum_high=round(cum_high, 3),
                )
            )
        used.extend(r_params_used)
        if len(r_params_used) > 1:
            notes.append(
                "Root-to-shoot ratio follows the above-ground biomass stock class: "
                + " → ".join(f"{p.value}" for p in r_params_used)
                + " (IPCC 2006 Table 4.4)."
            )

        years = max(horizon, 1)
        mean_central = cum_central / years
        mean_low, _, mean_high = bounds_from_fraction(
            mean_central, float(u_low.value), float(u_high.value)
        )
        headline = Range(
            round(mean_low, 2), round(mean_central, 2), round(mean_high, 2), UNIT_ANNUAL
        )
        components = {
            "above_ground_tco2e_yr": round(above_total / years, 2),
            "below_ground_tco2e_yr": round(below_total / years, 2),
        }
        stock_now = self._stock_at(series, as_of_year)
        return series, components, headline, stock_now

    # ------------------------------------------------------------------ tier 2
    def _tier2(
        self,
        plot: PlotInput,
        inventory: InventoryInput,
        climate: ClimateInput,
        species: dict[str, Any],
        survival: float,
        horizon: int,
        as_of_year: int,
        used: list[ParameterUsed],
        notes: list[str],
    ) -> tuple[list[SeriesPoint], dict[str, float], Range, Range]:
        store = self.store
        age_now = max(as_of_year - inventory.plantation_year, 0)
        wood_density = store.species_param(inventory.species_id, "wood_density_g_cm3", "g/cm3")
        maturity = store.species_param(inventory.species_id, "maturity_years", "years")
        carbon_fraction = store.constant("carbon_fraction")
        co2_per_c = store.constant("co2_per_c")
        post_maturity = store.model_setting("post_maturity_increment_factor", "fraction")
        extrapolation = store.model_setting("tier2_series_extrapolation", "method")
        u_low, u_high = store.uncertainty_fraction(2)
        allometry = store.allometry("pantropical_chave_2014_with_height")
        used.extend(
            [
                wood_density,
                maturity,
                carbon_fraction,
                co2_per_c,
                post_maturity,
                extrapolation,
                u_low,
                u_high,
                ParameterUsed(
                    "allometry_equation",
                    CHAVE_2014_EQ4,
                    "equation",
                    str(allometry["source"]),
                    str(allometry["verification_status"]),
                ),
            ]
        )
        nominated = str(species.get("allometry", "pantropical_chave_2014_with_height"))
        if nominated != "pantropical_chave_2014_with_height":
            entry = store.allometry(nominated)
            used.append(
                ParameterUsed(
                    "species_allometry",
                    f"{nominated} (no verified equation; Chave 2014 substituted)",
                    "equation",
                    str(entry["source"]),
                    str(entry["verification_status"]),
                )
            )
            notes.append(
                f"Species allometry {nominated!r} has no verified equation yet; Chave et al. 2014 "
                "eq. 4 was applied outside its pantropical calibration domain."
            )

        dbh = float(inventory.average_dbh_cm)  # type: ignore[arg-type]
        if inventory.average_height_m:
            height = float(inventory.average_height_m)
            used.append(ParameterUsed("average_height_m", height, "m", "reported", "assumption"))
        else:
            typical = store.species_param(inventory.species_id, "typical_height_m_at_maturity", "m")
            fraction = clamp(age_now / max(int(maturity.value), 1), MIN_HEIGHT_FRACTION, 1.0)
            height = float(typical.value) * fraction
            used.append(typical)
            used.append(
                ParameterUsed(
                    "height_estimated_m",
                    round(height, 2),
                    "m",
                    f"typical mature height × clamp(age/maturity_years, {MIN_HEIGHT_FRACTION}, 1); "
                    "project assumption v0.1",
                    "assumption",
                )
            )
            notes.append(
                "Tree height was not reported; estimated from species typical height and age."
            )

        agb_kg = chave_2014_agb_kg(float(wood_density.value), dbh, height)
        cf = float(carbon_fraction.value)
        co2 = float(co2_per_c.value)
        surviving = inventory.tree_count * survival
        agb_stock_t_ha = surviving * agb_kg / KG_PER_T / plot.area_hectares
        r_param = store.root_to_shoot(climate.zone, agb_stock_t_ha)
        used.append(r_param)
        r = float(r_param.value)
        used.append(
            ParameterUsed(
                "agb_per_tree_kg",
                round(agb_kg, 2),
                "kg d.m.",
                "Chave et al. 2014 eq. 4 applied to reported DBH",
                "verified",
            )
        )
        above_stock = surviving * agb_kg / KG_PER_T * cf * co2
        below_stock = above_stock * r
        stock_central = above_stock + below_stock
        rate = stock_central / max(age_now, 1)
        above_rate = above_stock / max(age_now, 1)
        below_rate = below_stock / max(age_now, 1)
        maturity_years = int(maturity.value)

        series: list[SeriesPoint] = []
        cum_low = cum_central = cum_high = 0.0
        for age in range(0, horizon + 1):
            year = inventory.plantation_year + age
            if age == 0:
                central = 0.0
            elif age <= age_now:
                central = rate
            else:
                central = rate * (1.0 if age <= maturity_years else float(post_maturity.value))
            low, _, high = bounds_from_fraction(central, float(u_low.value), float(u_high.value))
            cum_low += low
            cum_central += central
            cum_high += high
            series.append(
                SeriesPoint(
                    year=year,
                    age=age,
                    low=round(low, 3),
                    central=round(central, 3),
                    high=round(high, 3),
                    cum_low=round(cum_low, 3),
                    cum_central=round(cum_central, 3),
                    cum_high=round(cum_high, 3),
                )
            )
        low, _, high = bounds_from_fraction(rate, float(u_low.value), float(u_high.value))
        headline = Range(round(low, 2), round(rate, 2), round(high, 2), UNIT_ANNUAL)
        s_low, _, s_high = bounds_from_fraction(
            stock_central, float(u_low.value), float(u_high.value)
        )
        stock_now = Range(round(s_low, 2), round(stock_central, 2), round(s_high, 2), UNIT_STOCK)
        components = {
            "above_ground_tco2e_yr": round(above_rate, 2),
            "below_ground_tco2e_yr": round(below_rate, 2),
        }
        return series, components, headline, stock_now

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _validate(plot: PlotInput, inventory: InventoryInput) -> None:
        if plot.area_hectares <= 0:
            raise ModelInputError("area_hectares must be positive")
        if inventory.tree_count < 0:
            raise ModelInputError("tree_count must be non-negative")
        if inventory.survival_rate is not None and not 0.0 <= inventory.survival_rate <= 1.0:
            raise ModelInputError("survival_rate must be within [0, 1]")
        if inventory.average_dbh_cm is not None and inventory.average_dbh_cm < 0:
            raise ModelInputError("average_dbh_cm must be non-negative")
        if inventory.average_height_m is not None and inventory.average_height_m < 0:
            raise ModelInputError("average_height_m must be non-negative")

    def _survival(self, inventory: InventoryInput, used: list[ParameterUsed]) -> ParameterUsed:
        if inventory.survival_rate is not None:
            param = ParameterUsed(
                "survival_rate",
                float(inventory.survival_rate),
                "fraction",
                f"reported ({inventory.measurement_source})",
                "assumption",
            )
        else:
            default = self.store.assumption_param("survival_rate_default", "fraction")
            param = ParameterUsed(
                "survival_rate",
                float(default.value),
                default.unit,
                default.source,
                default.verification_status,
            )
        used.append(param)
        return param

    @staticmethod
    def _stock_at(series: list[SeriesPoint], as_of_year: int) -> Range:
        if not series or as_of_year < series[0].year:
            return Range(0.0, 0.0, 0.0, UNIT_STOCK)
        point = series[-1]
        for candidate in series:
            if candidate.year <= as_of_year:
                point = candidate
        return Range(
            round(point.cum_low, 2),
            round(point.cum_central, 2),
            round(point.cum_high, 2),
            UNIT_STOCK,
        )

    def _methodology(self) -> Methodology:
        entry = self.store.methodology_entry(METHODOLOGY_ID)
        references = [{"title": str(entry["name"]), "url": str(entry.get("url", ""))}]
        for ref in self.store.references():
            if ref not in references:
                references.append({"title": str(ref["title"]), "url": str(ref.get("url", ""))})
        return Methodology(
            id=METHODOLOGY_ID,
            name="IPCC 2006 Guidelines, Vol. 4, Ch. 4 (Forest Land), Tier 1 gain-loss",
            references=references,
        )

    def _provenance(
        self, used: list[ParameterUsed], tier: str, climate: ClimateInput, species: dict[str, Any]
    ) -> dict[str, Any]:
        sources: list[dict[str, Any]] = [
            {
                "id": METHODOLOGY_ID,
                "name": "2006 IPCC Guidelines for National GHG Inventories, Vol. 4 Ch. 4",
                "version": "2006",
                "license": "IPCC publication — citation required",
                "attribution": "IPCC (2006). 2006 IPCC Guidelines for National Greenhouse Gas "
                "Inventories, Volume 4: Agriculture, Forestry and Other Land Use. IGES, Japan.",
                "url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html",
            },
            {
                "id": "species-table",
                "name": "AgriCarbon Atlas species table",
                "version": self.store.species_version,
                "license": "Apache-2.0 (project configuration)",
                "attribution": "AgriCarbon Atlas contributors; wood density working values after "
                "Zanne et al. (2009) Global Wood Density Database (Dryad, CC0)",
                "url": "https://doi.org/10.5061/dryad.234",
            },
        ]
        if tier == "2":
            sources.append(
                {
                    "id": "chave-2014",
                    "name": "Chave et al. 2014 pantropical allometric models",
                    "version": "2014",
                    "license": "Published equation — citation required",
                    "attribution": "Chave, J. et al. (2014) Global Change Biology 20(10): 3177–3190",
                    "url": "https://doi.org/10.1111/gcb.12629",
                }
            )
        return {
            "sources": sources,
            "model": {"id": self.id, "version": self.version},
            "parameter_set": {
                "id": self.store.parameter_set_id,
                "version": self.store.parameter_set_version,
                "verification_status": worst_verification_status(used),
            },
            "climate_zone": {"zone": climate.zone, "source": climate.zone_source},
            "species": {"id": species["id"], "scientific_name": species["scientific_name"]},
            "notes": [],
        }
