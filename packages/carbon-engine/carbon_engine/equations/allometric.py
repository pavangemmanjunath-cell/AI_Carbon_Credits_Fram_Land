"""Pantropical allometry — Chave et al. (2014).

Chave, J. et al. (2014) *Improved allometric models to estimate the
aboveground biomass of tropical trees*. Global Change Biology 20(10):
3177–3190. https://doi.org/10.1111/gcb.12629

* Equation 4 (with height):  ``AGB_kg = 0.0673 · (ρ · D² · H)^0.976``
  where ρ is wood specific gravity (g cm⁻³), D diameter at breast height (cm)
  and H total height (m). Fitted on 4004 trees, 5 cm ≤ D ≤ 212 cm.
* Equation 7 (without height): ``AGB_kg = exp(−1.803 − 0.976·E + 0.976·ln ρ
  + 2.673·ln D − 0.0299·(ln D)²)`` where E is the bioclimatic stress variable
  (requires the Chave E raster; not bundled).

The coefficients below are the published ones and are **verified** in
``config/methodologies/ipcc-2006-tier1.yaml``. The functions are pure so they
can be checked against hand-computed values.
"""

from __future__ import annotations

import math

from carbon_engine.errors import ModelInputError

CHAVE_2014_EQ4 = "AGB_kg = 0.0673 * (rho_g_cm3 * D_cm^2 * H_m)^0.976"
_A = 0.0673
_B = 0.976


def chave_2014_agb_kg(wood_density_g_cm3: float, dbh_cm: float, height_m: float) -> float:
    """Above-ground biomass of one tree (kg dry matter), Chave et al. 2014 eq. 4.

    >>> round(chave_2014_agb_kg(0.55, 20.0, 10.0), 1)
    123.1
    """
    if wood_density_g_cm3 <= 0:
        raise ModelInputError("wood density must be positive")
    if dbh_cm < 0 or height_m < 0:
        raise ModelInputError("DBH and height must be non-negative")
    if dbh_cm == 0 or height_m == 0:
        return 0.0
    return _A * (wood_density_g_cm3 * dbh_cm**2 * height_m) ** _B


def chave_2014_no_height_agb_kg(wood_density_g_cm3: float, dbh_cm: float, e_stress: float) -> float:
    """Above-ground biomass (kg) without height, Chave et al. 2014 eq. 7.

    ``e_stress`` is the bioclimatic variable *E* (temperature seasonality,
    climatic water deficit, precipitation seasonality) read from the Chave
    *E* raster — callers must supply it; this package does not estimate it.
    """
    if wood_density_g_cm3 <= 0 or dbh_cm <= 0:
        raise ModelInputError("wood density and DBH must be positive")
    ln_d = math.log(dbh_cm)
    return math.exp(
        -1.803
        - 0.976 * e_stress
        + 0.976 * math.log(wood_density_g_cm3)
        + 2.673 * ln_d
        - 0.0299 * ln_d**2
    )
