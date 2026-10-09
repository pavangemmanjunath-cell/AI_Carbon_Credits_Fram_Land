"""Tree inventory records (every measurement has a source)."""

from __future__ import annotations

from typing import Any

from app.core.errors import ProblemError
from app.repositories.base import Repository
from app.services.common import current_year, now_iso, short_id
from carbon_engine import ParameterStore, UnknownSpeciesError, confidence_for_inventory


class TreeService:
    def __init__(self, repo: Repository, store: ParameterStore) -> None:
        self.repo = repo
        self.store = store

    def species_list(self, country: str | None) -> list[dict[str, Any]]:
        return [self._public_species(s) for s in self.store.species_list(country)]

    def species(self, species_id: str) -> dict[str, Any]:
        try:
            return self.store.species(species_id)
        except UnknownSpeciesError as exc:
            raise ProblemError(
                422, f"Unknown species_id {species_id!r}.", type_slug="unknown-species"
            ) from exc

    @staticmethod
    def _public_species(entry: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "id",
            "scientific_name",
            "common_name",
            "group",
            "regions",
            "suitable_climate_zones",
            "max_density_per_ha",
            "maturity_years",
            "notes",
            "allometry",
        )
        data = {k: entry.get(k) for k in keys}
        for cited in (
            "reference_density_per_ha",
            "wood_density_g_cm3",
            "increment_multiplier",
            "typical_height_m_at_maturity",
        ):
            value = entry.get(cited)
            data[cited] = value if isinstance(value, dict) else {"value": value}
        return data

    def create(self, plot: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
        species = self.species(body["species_id"])
        if body["plantation_year"] > current_year():
            raise ProblemError(422, "plantation_year cannot be in the future.")
        confidence, fields = confidence_for_inventory(
            body["tree_count"],
            body["species_id"],
            body["plantation_year"],
            body.get("average_dbh_cm"),
            body.get("average_height_m"),
            body.get("survival_rate"),
        )
        inventory = {
            "inventory_id": short_id("INV-", 4),
            "plot_id": plot["plot_id"],
            "species": {
                "id": species["id"],
                "scientific_name": species["scientific_name"],
                "common_name": species["common_name"],
            },
            "tree_count": int(body["tree_count"]),
            "density_per_ha": round(body["tree_count"] / plot["area_hectares"], 1),
            "plantation_year": int(body["plantation_year"]),
            "age_years": current_year() - int(body["plantation_year"]),
            "average_dbh_cm": body.get("average_dbh_cm"),
            "average_height_m": body.get("average_height_m"),
            "survival_rate": body.get("survival_rate"),
            "measurement_source": body.get("measurement_source", "user-reported"),
            "data_quality": {"fields": [f.to_dict() for f in fields], "confidence": confidence},
            "created_at": now_iso(),
        }
        self.repo.save_inventory(inventory)
        self.repo.audit(
            "inventory.created", plot["plot_id"], {"tree_count": inventory["tree_count"]}
        )
        return inventory

    def latest(self, plot_id: str) -> dict[str, Any] | None:
        items = self.repo.list_inventories(plot_id)
        return items[-1] if items else None

    def require(self, plot_id: str, inventory_id: str | None) -> dict[str, Any]:
        inventory = (
            self.repo.get_inventory(plot_id, inventory_id) if inventory_id else self.latest(plot_id)
        )
        if inventory is None:
            raise ProblemError(
                404,
                "No tree inventory for this plot yet — POST /plots/{plot_id}/trees first.",
                type_slug="inventory-missing",
            )
        return inventory
