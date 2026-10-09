"""Tree age: carbon stored by trees of a given age and the rules that apply at that age.

Numbers come from ``carbon_engine.age`` (a thin layer over the tree-biomass model: nothing is
re-implemented here) and rules from ``policy_engine.tree_age`` (``config/tree-age/rules.yaml``).
This service picks the climate zone, maps engine errors to RFC 7807 problems and assembles the
``TreeAgeAssessment`` of ``docs/architecture/api-contract.md`` §v0.2. Nothing is stored and no
coordinates are read or logged; an optional ``plot_id`` only supplies its climate zone.

Other modules call it as ``service(ctx, "tree_age", lambda: TreeAgeService(ctx)).assess({...})``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from app.core.errors import ProblemError
from app.schemas.tree_age import TreeAgeRequest, normalise_subdivision
from app.services.common import base_provenance, current_year
from carbon_engine import (
    CarbonEngineError,
    ClimateInput,
    PendingParameterError,
    UnknownClimateZoneError,
    UnknownSpeciesError,
)
from carbon_engine.age import AgeAssessment, assess_by_age
from geo_engine.climate import zone_label
from policy_engine.tree_age import (
    TreeAgeRulesError,
    age_class_for,
    credit_outlook,
    evaluate,
    load_rules,
    load_subdivisions,
    select_rules,
    withheld_rule_ids,
)

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

log = logging.getLogger("atlas.tree_age")

ESTIMATE_DISCLAIMER = "Scenario estimate only. This is not an issued carbon credit."


class TreeAgeService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        try:
            self._doc = load_rules(ctx.settings.config_dir)
            self._subdivisions = load_subdivisions(ctx.settings.config_dir)
        except (OSError, TreeAgeRulesError) as exc:
            log.error("tree-age rules could not be loaded: %s", exc)
            raise ProblemError(
                500,
                "The tree-age rules file is missing or invalid; see the server log.",
                type_slug="tree-age-rules-unavailable",
            ) from exc

    @property
    def allow_pending(self) -> bool:
        """Same rule as the carbon estimate: production never uses unverified (pending) data."""
        settings = self.ctx.settings
        return settings.atlas_allow_pending_parameters and not settings.is_production

    # ------------------------------------------------------------------------- rules
    def rules(self, country: str | None = None, subdivision: str | None = None) -> dict[str, Any]:
        """The rules file (optionally narrowed to a country and a subdivision) as served."""
        country = country.upper() if country else None
        region = self._region(country) if country else None
        code = self._subdivision(subdivision, country)
        listed_for = country or (code.split("-")[0] if code else None)
        block = (self._subdivisions.get("countries") or {}).get(listed_for or "")
        return {
            "version": self._doc["version"],
            "updated": self._doc["updated"],
            "disclaimer": self._doc["disclaimer"],
            "age_classes": self._doc["age_classes"],
            "rules": select_rules(
                self._doc,
                country=country,
                region=region,
                subdivision=code,
                allow_pending=self.allow_pending,
            ),
            "withheld_rule_ids": self._withheld(country, region, code),
            "subdivision_label": (block or {}).get("subdivision_label"),
            "subdivisions": self._subdivision_list(listed_for),
        }

    # ----------------------------------------------------------------------- assessment
    def assess(self, body: dict[str, Any]) -> dict[str, Any]:
        request = self._request(body)
        country = request.country
        region = self._region(country)
        subdivision = self._subdivision(request.subdivision, country)
        species = self.ctx.trees.species(request.species_id)
        climate, climate_source = self._climate(region, request.plot_id)

        result = self._carbon(request, climate)
        carbon = result.to_dict()
        if region not in (species.get("regions") or []):
            carbon["notes"].insert(
                0,
                f"{species.get('common_name', request.species_id)} is not listed for {region} in "
                "the species table, so its growth parameters may not apply there.",
            )

        rules = evaluate(
            self._doc,
            country,
            region,
            subdivision,
            request.setting,
            request.age_years,
            subdivisions=self._subdivisions,
            allow_pending=self.allow_pending,
        )
        outlook = credit_outlook(rules, request.age_years)

        engine_provenance = result.provenance
        provenance = base_provenance(
            self.ctx.settings.atlas_mode,
            [*engine_provenance.get("sources", []), self._rules_source()],
        )
        provenance.update(
            {
                "model": engine_provenance.get("model"),
                "parameter_set": engine_provenance.get("parameter_set"),
                "climate_zone": {
                    "zone": climate.zone,
                    "label": zone_label(climate.zone),
                    "source": climate_source,
                },
                "species": engine_provenance.get("species"),
                "notes": list(carbon["notes"]),
            }
        )
        return {
            "inputs": {
                "country": country,
                "region": region,
                "subdivision": subdivision,
                "setting": request.setting,
                "species_id": request.species_id,
                "age_years": request.age_years,
                "tree_count": request.tree_count,
                "girth_cm": request.girth_cm,
                "height_m": request.height_m,
                "plot_id": request.plot_id,
            },
            "age_class": age_class_for(request.age_years, self._doc),
            "climate_zone": climate.zone,
            "climate_zone_label": zone_label(climate.zone),
            "climate_zone_source": climate_source,
            "carbon": carbon,
            "credit_outlook": outlook,
            "rules": rules,
            "withheld_rule_ids": self._withheld(country, region, None),
            "certified": False,
            "disclaimer": f"{self._doc['disclaimer']} {ESTIMATE_DISCLAIMER}",
            "provenance": provenance,
        }

    # ------------------------------------------------------------------------ helpers
    @staticmethod
    def _request(body: dict[str, Any]) -> TreeAgeRequest:
        """Validate like the HTTP layer does, so in-process callers (agents) get the same rules."""
        known = {k: v for k, v in body.items() if k in TreeAgeRequest.model_fields}
        try:
            return TreeAgeRequest.model_validate(known)
        except ValidationError as exc:
            errors = [
                {
                    "field": ".".join(str(p) for p in err.get("loc", [])),
                    "message": err.get("msg", "invalid"),
                }
                for err in exc.errors()
            ]
            raise ProblemError(
                422,
                "Request validation failed.",
                type_slug="validation-error",
                extra={"errors": errors},
            ) from exc

    def _region(self, country: str) -> str:
        region = self.ctx.regions.resolve(country)
        if region is None:
            raise ProblemError(
                422, f"Country {country} is not supported.", type_slug="unsupported-country"
            )
        return region

    def _subdivision(self, subdivision: str | None, country: str | None) -> str | None:
        try:
            code = normalise_subdivision(subdivision, country)
        except ValueError as exc:
            raise ProblemError(422, str(exc), type_slug="invalid-subdivision") from exc
        if code is None:
            return None
        listed = (self._subdivisions.get("countries") or {}).get(code.split("-")[0])
        if listed and code not in {s["code"] for s in listed["subdivisions"]}:
            raise ProblemError(
                422,
                f"Subdivision {code} is not in the list for {listed['name']}.",
                type_slug="unknown-subdivision",
            )
        return code

    def _withheld(self, country: str | None, region: str | None, code: str | None) -> list[str]:
        """Pending rules hidden for this place (always empty outside production)."""
        if self.allow_pending:
            return []
        return withheld_rule_ids(self._doc, country, region, code)

    def _subdivision_list(self, country: str | None) -> list[dict[str, str]]:
        blocks = self._subdivisions.get("countries") or {}
        codes = [country] if country else list(blocks)
        return [
            {"code": s["code"], "name": s["name"], "type": s["type"]}
            for code in codes
            for s in (blocks.get(code) or {}).get("subdivisions", [])
        ]

    def _climate(self, region: str, plot_id: str | None) -> tuple[ClimateInput, str]:
        """Climate zone of the plot's latest analysis when given, else the region default."""
        if plot_id:
            self.ctx.plots.require(plot_id)  # 404 when unknown
            climate = (self.ctx.repo.get_analysis(plot_id) or {}).get("climate") or {}
            if climate.get("zone"):
                source = str(climate.get("zone_source") or "derived")
                return ClimateInput(str(climate["zone"]), source), f"plot analysis ({source})"
        zone = self.ctx.regions.default_zone(region)
        return ClimateInput(zone, "region-default"), f"region default ({region})"

    def _carbon(self, request: TreeAgeRequest, climate: ClimateInput) -> AgeAssessment:
        try:
            return assess_by_age(
                self.ctx.store,
                request.species_id,
                request.age_years,
                request.tree_count,
                climate,
                girth_cm=request.girth_cm,
                height_m=request.height_m,
                as_of_year=current_year(),
                allow_pending=self.allow_pending,
            )
        except PendingParameterError as exc:
            raise ProblemError(
                409,
                f"{exc} Set ATLAS_ALLOW_PENDING_PARAMETERS=true outside production.",
                type_slug="pending-parameters",
            ) from exc
        except UnknownSpeciesError as exc:
            raise ProblemError(
                422, f"Unknown species_id {request.species_id!r}.", type_slug="unknown-species"
            ) from exc
        except UnknownClimateZoneError as exc:
            raise ProblemError(422, str(exc), type_slug="unknown-climate-zone") from exc
        except CarbonEngineError as exc:
            raise ProblemError(422, str(exc), type_slug="carbon-engine-error") from exc

    def _rules_source(self) -> dict[str, Any]:
        return {
            "id": "tree-age-rules",
            "name": "AgriCarbon Atlas tree-age rules (config/tree-age/rules.yaml)",
            "version": self._doc["version"],
            "updated": self._doc["updated"],
            "license": "Apache-2.0 (project configuration); each rule cites its own public sources",
            "attribution": "AgriCarbon Atlas contributors; each rule lists its sources and the "
            "date they were accessed",
            "url": None,
        }
