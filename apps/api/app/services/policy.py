"""Policy-pathway screening (config-driven, never an eligibility determination)."""

from __future__ import annotations

from typing import Any

from app.core.errors import ProblemError
from policy_engine import PolicyEngine


class PolicyService:
    def __init__(self, engine: PolicyEngine) -> None:
        self.engine = engine

    def screen(
        self,
        country: str,
        activity: str,
        land_type: str | None = None,
        area_ha: float | None = None,
    ) -> dict[str, Any]:
        try:
            region_id = self.engine.resolve_region(country)
            screening = self.engine.screen(country, activity, land_type=land_type, area_ha=area_ha)
        except KeyError as exc:
            raise ProblemError(422, str(exc), type_slug="unsupported-country") from exc
        except ValueError as exc:
            raise ProblemError(422, str(exc), type_slug="unsupported-activity") from exc
        payload = screening.to_dict()
        payload["region"] = region_id
        for programme in payload["programmes"]:
            programme.setdefault("url", self.engine.programme_url(region_id, programme["id"]))
        return payload

    def programme_links(
        self, country: str, activity: str = "tree_plantation"
    ) -> list[dict[str, Any]]:
        payload = self.screen(country, activity)
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "url": p.get("url"),
                "status": p["status"],
                "kind": p["kind"],
            }
            for p in payload["programmes"]
        ]
