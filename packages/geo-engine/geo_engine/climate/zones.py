"""IPCC climate-zone decision tree (approximation).

This module APPROXIMATES the climate-zone classification scheme of the
2006 IPCC Guidelines, Vol. 4, Ch. 3, Annex 3A.5, Figure 3A.5.1
(https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html) from three
inputs that are available for any point from Open-Meteo: mean annual
temperature (MAT, °C), mean annual precipitation (MAP, mm) and elevation (m).

Decision tree implemented here
------------------------------
1. ``MAT > 18 °C`` → tropical
     * elevation > 1000 m → ``tropical_mountain``
     * MAP > 2000 mm → ``tropical_wet``
     * MAP 1000–2000 mm → ``tropical_moist``
     * MAP < 1000 mm → ``tropical_dry``
2. ``10 °C < MAT ≤ 18 °C`` → warm temperate: ``_moist`` if MAP > PET else ``_dry``
3. ``0 °C < MAT ≤ 10 °C`` → cool temperate: ``_moist`` if MAP > PET else ``_dry``
4. ``MAT ≤ 0 °C`` → ``boreal`` (the parameter tables carry a single boreal row)

Where the IPCC scheme compares MAP with potential evapotranspiration (PET),
this module estimates annual PET from MAT with Holland's (1978) empirical
relation ``PET ≈ 300 + 25·T + 0.05·T³`` (mm/yr), because Open-Meteo normals
do not provide PET directly. The IPCC tree also uses frost occurrence and
seasonality that are not evaluated here.

Every result therefore carries ``verification_status = "assumption"`` and the
``method`` string so it appears in provenance. The ``subtropical_*`` zones that
exist in the parameter tables are never produced automatically; they can be
selected explicitly by a user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CLIMATE_ZONE_LABELS: dict[str, str] = {
    "tropical_wet": "Tropical wet",
    "tropical_moist": "Tropical moist",
    "tropical_dry": "Tropical dry",
    "tropical_mountain": "Tropical montane",
    "subtropical_humid": "Subtropical humid",
    "subtropical_dry": "Subtropical dry",
    "warm_temperate_moist": "Warm temperate moist",
    "warm_temperate_dry": "Warm temperate dry",
    "cool_temperate_moist": "Cool temperate moist",
    "cool_temperate_dry": "Cool temperate dry",
    "boreal": "Boreal",
}

METHOD = (
    "Approximation of IPCC 2006 Vol.4 Ch.3 Fig. 3A.5.1 from MAT/MAP/elevation; "
    "PET from Holland (1978) PET = 300 + 25T + 0.05T^3"
)
SOURCE = "IPCC 2006 Guidelines Vol.4 Ch.3 Annex 3A.5 (approximated)"
VERIFICATION_STATUS = "assumption"

TROPICAL_MAT_C = 18.0
WARM_TEMPERATE_MAT_C = 10.0
BOREAL_MAT_C = 0.0
TROPICAL_MOUNTAIN_ELEVATION_M = 1000.0
TROPICAL_WET_MAP_MM = 2000.0
TROPICAL_MOIST_MAP_MM = 1000.0


@dataclass(frozen=True)
class ClimateZoneResult:
    zone: str
    label: str
    mean_annual_temp_c: float
    annual_precip_mm: float
    elevation_m: float | None
    pet_mm: float | None
    method: str = METHOD
    source: str = SOURCE
    verification_status: str = VERIFICATION_STATUS

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone": self.zone,
            "zone_label": self.label,
            "mean_annual_temp_c": self.mean_annual_temp_c,
            "annual_precip_mm": self.annual_precip_mm,
            "elevation_m": self.elevation_m,
            "pet_mm_estimate": self.pet_mm,
            "method": self.method,
            "source": self.source,
            "verification_status": self.verification_status,
        }


def zone_label(zone: str) -> str:
    """Human label for a zone id (falls back to a title-cased id)."""
    return CLIMATE_ZONE_LABELS.get(zone, zone.replace("_", " ").capitalize())


def estimate_pet_mm(mean_annual_temp_c: float) -> float:
    """Annual potential evapotranspiration (mm) after Holland (1978).

    ``PET = 300 + 25·T + 0.05·T³`` with T in °C; negative temperatures give
    low PET, which is clamped at 0.
    """
    t = mean_annual_temp_c
    return max(0.0, 300.0 + 25.0 * t + 0.05 * t**3)


def classify_climate_zone(
    mean_annual_temp_c: float,
    annual_precip_mm: float,
    elevation_m: float | None = None,
) -> ClimateZoneResult:
    """Classify a location into one of the zone ids used by the parameter tables."""
    mat = float(mean_annual_temp_c)
    precip = float(annual_precip_mm)
    elev = None if elevation_m is None else float(elevation_m)
    pet = estimate_pet_mm(mat)

    if mat > TROPICAL_MAT_C:
        if elev is not None and elev > TROPICAL_MOUNTAIN_ELEVATION_M:
            zone = "tropical_mountain"
        elif precip > TROPICAL_WET_MAP_MM:
            zone = "tropical_wet"
        elif precip >= TROPICAL_MOIST_MAP_MM:
            zone = "tropical_moist"
        else:
            zone = "tropical_dry"
    elif mat > WARM_TEMPERATE_MAT_C:
        zone = "warm_temperate_moist" if precip > pet else "warm_temperate_dry"
    elif mat > BOREAL_MAT_C:
        zone = "cool_temperate_moist" if precip > pet else "cool_temperate_dry"
    else:
        zone = "boreal"

    return ClimateZoneResult(
        zone=zone,
        label=zone_label(zone),
        mean_annual_temp_c=round(mat, 2),
        annual_precip_mm=round(precip, 1),
        elevation_m=None if elev is None else round(elev, 1),
        pet_mm=round(pet, 1),
    )
