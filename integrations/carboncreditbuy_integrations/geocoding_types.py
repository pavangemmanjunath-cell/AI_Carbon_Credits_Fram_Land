"""Shared result types for geocoders (Nominatim, Photon)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GeocodeResult:
    label: str
    lat: float
    lon: float
    bbox: list[float] | None  # [min_lon, min_lat, max_lon, max_lat]
    country: str | None
    state: str | None
    district: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "lat": round(self.lat, 6),
            "lon": round(self.lon, 6),
            "bbox": self.bbox,
            "admin": {"country": self.country, "state": self.state, "district": self.district},
        }


@dataclass(frozen=True)
class ReverseResult:
    country: str | None
    state: str | None
    district: str | None
    label: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "state": self.state,
            "district": self.district,
            "label": self.label,
        }
