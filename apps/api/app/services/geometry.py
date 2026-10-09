"""Geometry helpers: plot boundaries from a pin, a tree line or typed coordinates.

Pure calculations - nothing is stored and no coordinate is logged. Engine errors become RFC 7807
problems whose ``detail`` never contains the submitted coordinates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shapely.errors import ShapelyError

from app.core.errors import ProblemError
from app.services.common import base_provenance
from geo_engine.construct import polygon_from_point, strip_from_line, suggest_tree_count
from geo_engine.coordinates import parse_coordinates
from geo_engine.errors import GeometryError
from geo_engine.geometry import ValidationLimits
from geo_engine.geometry.measure import ACRES_PER_HA, M2_PER_HA

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

APPROXIMATE = "approximate"
TREE_COUNT_RULE = "trees = floor(length / spacing) + 1"
_UNIT_TO_HECTARES = {"ha": 1.0, "ac": 1.0 / ACRES_PER_HA, "m2": 1.0 / M2_PER_HA}


class GeometryService:
    """Back end of ``POST /geometry/from-point``, ``/from-line`` and ``/parse-coordinates``."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        settings = ctx.settings
        self.limits = ValidationLimits(
            max_vertices=settings.atlas_max_plot_vertices,
            max_area_ha=settings.atlas_max_plot_area_ha,
        )

    # -- helpers -------------------------------------------------------------------------
    def _provenance(self, note: str) -> dict[str, Any]:
        provenance = base_provenance(self.ctx.settings.atlas_mode, [])
        provenance["notes"] = [note, "Nothing is stored: this is a calculation on the values sent."]
        return provenance

    @staticmethod
    def _problem(exc: GeometryError | ShapelyError | ValueError) -> ProblemError:
        """RFC 7807 problem for an engine failure (the message never holds coordinates)."""
        if isinstance(exc, GeometryError):
            return ProblemError(
                422, exc.detail, type_slug="invalid-geometry", extra={"code": exc.code}
            )
        return ProblemError(
            422,
            "The geometry could not be built from these values.",
            type_slug="invalid-geometry",
            extra={"code": "geometry_failed"},
        )

    # -- pin + area ----------------------------------------------------------------------
    def from_point(
        self, lat: float, lon: float, area_value: float, unit: str, shape: str = "square"
    ) -> dict[str, Any]:
        """A plot polygon centred on a pin with the typed area (an approximate boundary)."""
        area_ha = area_value * _UNIT_TO_HECTARES[unit]
        try:
            built = polygon_from_point(lat, lon, area_ha, shape, self.limits)
        except (GeometryError, ShapelyError, ValueError) as exc:
            raise self._problem(exc) from None
        area_hectares = float(built["area_hectares"])
        result: dict[str, Any] = {
            "geometry": built["geometry"],
            "area_hectares": round(area_hectares, 4),
            "area_acres": round(area_hectares * ACRES_PER_HA, 4),
            "boundary_quality": APPROXIMATE,
            "method": built["method"],
        }
        for key in ("side_m", "radius_m"):
            if key in built:
                result[key] = built[key]
        result["provenance"] = self._provenance(
            "Geodesic polygon on the WGS84 ellipsoid; the boundary is an approximation, "
            "not a survey."
        )
        return result

    # -- tree line -----------------------------------------------------------------------
    def from_line(
        self, coordinates: list[list[float]], width_m: float, spacing_m: float
    ) -> dict[str, Any]:
        """A strip polygon around a tree line plus how many trees fit at ``spacing_m``."""
        try:
            built = strip_from_line(coordinates, width_m, self.limits)
            length_m = float(built["length_m"])
            trees = suggest_tree_count(length_m, spacing_m)
        except (GeometryError, ShapelyError, ValueError) as exc:
            raise self._problem(exc) from None
        provenance = self._provenance(
            "Strip built in a local metric projection around the line; the boundary is an "
            "approximation, not a survey."
        )
        return {
            "geometry": built["geometry"],
            "length_m": round(length_m, 1),
            "area_hectares": round(float(built["area_hectares"]), 4),
            "suggested_tree_count": trees,
            "boundary_quality": APPROXIMATE,
            "method": f"{built['method']}; {TREE_COUNT_RULE}",
            "provenance": provenance,
        }

    # -- typed coordinates ---------------------------------------------------------------
    def parse_coordinates(self, text: str) -> dict[str, Any]:
        """Parse one point per line (decimal, hemisphere letters or degrees-minutes-seconds)."""
        try:
            parsed = parse_coordinates(text, self.limits)
        except (GeometryError, ShapelyError, ValueError) as exc:
            raise self._problem(exc) from None
        return parsed.to_dict()
