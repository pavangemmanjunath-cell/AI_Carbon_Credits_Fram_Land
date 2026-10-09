"""Confidence rule from docs/architecture/api-contract.md (TreeInventory):

* ``high``   — count, species, age, DBH **and** height supplied;
* ``medium`` — count, species and age supplied;
* ``low``    — otherwise.

The same rule grades carbon estimates, because v0.1 estimates are driven by
exactly these inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

FIELD_ORDER = ("tree_count", "species", "age", "dbh", "height", "mortality")


@dataclass(frozen=True)
class FieldStatus:
    name: str
    status: str  # supplied | missing

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status}


def field_statuses(
    tree_count: int | None,
    species_id: str | None,
    plantation_year: int | None,
    average_dbh_cm: float | None,
    average_height_m: float | None,
    survival_rate: float | None,
) -> list[FieldStatus]:
    present = {
        "tree_count": tree_count is not None and tree_count > 0,
        "species": bool(species_id),
        "age": plantation_year is not None,
        "dbh": average_dbh_cm is not None and average_dbh_cm > 0,
        "height": average_height_m is not None and average_height_m > 0,
        "mortality": survival_rate is not None,
    }
    return [FieldStatus(name, "supplied" if present[name] else "missing") for name in FIELD_ORDER]


def confidence_from_fields(fields: list[FieldStatus]) -> str:
    """Apply the contract rule to a list of :class:`FieldStatus`."""
    supplied = {f.name for f in fields if f.status == "supplied"}
    core = {"tree_count", "species", "age"}
    if core.issubset(supplied) and {"dbh", "height"}.issubset(supplied):
        return "high"
    if core.issubset(supplied):
        return "medium"
    return "low"


def confidence_for_inventory(
    tree_count: int | None,
    species_id: str | None,
    plantation_year: int | None,
    average_dbh_cm: float | None = None,
    average_height_m: float | None = None,
    survival_rate: float | None = None,
) -> tuple[str, list[FieldStatus]]:
    """Convenience: returns ``(confidence, fields)``."""
    fields = field_statuses(
        tree_count, species_id, plantation_year, average_dbh_cm, average_height_m, survival_rate
    )
    return confidence_from_fields(fields), fields
