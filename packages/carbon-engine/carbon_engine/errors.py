"""Typed errors for carbon_engine."""

from __future__ import annotations


class CarbonEngineError(Exception):
    """Base class."""


class UnknownSpeciesError(CarbonEngineError, KeyError):
    def __init__(self, species_id: str) -> None:
        super().__init__(species_id)
        self.species_id = species_id

    def __str__(self) -> str:  # KeyError quotes its message otherwise
        return f"unknown species id {self.species_id!r}"


class UnknownClimateZoneError(CarbonEngineError, KeyError):
    def __init__(self, zone: str) -> None:
        super().__init__(zone)
        self.zone = zone

    def __str__(self) -> str:
        return f"unknown climate zone {self.zone!r}"


class PendingParameterError(CarbonEngineError, RuntimeError):
    """Raised in production mode when a used parameter is still ``pending``."""

    def __init__(self, names: list[str]) -> None:
        super().__init__(
            "parameters with verification_status=pending cannot be used in production: "
            + ", ".join(names)
        )
        self.names = names


class ModelInputError(CarbonEngineError, ValueError):
    """An input value is outside the model's domain."""


class ModelNotImplementedError(CarbonEngineError, NotImplementedError):
    """A model interface exists but no verified methodology has been implemented."""
