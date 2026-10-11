"""ISRIC SoilGrids 2.0 adapter — soil organic carbon 0–30 cm (mean).

Endpoint ``SOILGRIDS_URL`` (https://rest.isric.org/soilgrids/v2.0/properties/query)
with ``property=soc``, depths ``0-5cm``, ``5-15cm``, ``15-30cm`` and
``value=mean``. SoilGrids reports SOC in **dg/kg**; the depth-weighted mean
(weights 5, 10, 15 cm) is divided by 10 to give **g/kg**.

Licence CC BY 4.0 — "SoilGrids 2.0, ISRIC — World Soil Information (Poggio et
al. 2021, SOIL 7, 217–240)". Fair use: ≤ 5 requests/minute per the ISRIC
usage policy; cache aggressively (soil does not change between calls).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from carboncreditbuy_integrations.base import (
    Cache,
    HttpAdapter,
    SourceProvenance,
    UpstreamDataError,
    demo_source,
)
from carboncreditbuy_integrations.demo_support import region_for, unit_noise

SOURCE = SourceProvenance(
    id="soilgrids",
    name="SoilGrids 2.0 (ISRIC World Soil Information)",
    version="2.0 (2020)",
    license="CC BY 4.0",
    attribution="SoilGrids 2.0 — ISRIC World Soil Information; Poggio et al. (2021) SOIL 7:217–240",
    url="https://soilgrids.org/",
)
DEPTHS = (("0-5cm", 5.0), ("5-15cm", 10.0), ("15-30cm", 15.0))


@dataclass(frozen=True)
class SoilResult:
    soc_0_30cm_g_per_kg: float | None
    source: dict[str, Any]
    depths_used: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "soc_0_30cm_g_per_kg": None
            if self.soc_0_30cm_g_per_kg is None
            else round(self.soc_0_30cm_g_per_kg, 2),
        }


class SoilGridsAdapter(HttpAdapter):
    def __init__(self, url: str, cache: Cache | None = None, **kwargs: Any) -> None:
        super().__init__(cache=cache, cache_ttl_s=30 * 86_400.0, **kwargs)
        self.url = url

    def fetch_soc_0_30(self, lat: float, lon: float) -> SoilResult:
        params: list[tuple[str, Any]] = [
            ("lon", lon),
            ("lat", lat),
            ("property", "soc"),
            ("value", "mean"),
        ]
        params += [("depth", label) for label, _ in DEPTHS]
        data = self.get_json(self.url, params=params)
        try:
            layers = data["properties"]["layers"]
            soc_layer = next(layer for layer in layers if layer.get("name") == "soc")
            by_depth = {d["label"]: d["values"].get("mean") for d in soc_layer["depths"]}
        except (KeyError, StopIteration, TypeError) as exc:
            raise UpstreamDataError("SoilGrids payload malformed") from exc
        weighted = 0.0
        weight_sum = 0.0
        used: list[str] = []
        for label, thickness in DEPTHS:
            value = by_depth.get(label)
            if value is None:
                continue
            weighted += float(value) * thickness
            weight_sum += thickness
            used.append(label)
        soc = (weighted / weight_sum) / 10.0 if weight_sum else None  # dg/kg → g/kg
        return SoilResult(soc, SOURCE.to_dict(datetime.now(UTC)), used)

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()


class DemoSoilGridsAdapter:
    def fetch_soc_0_30(self, lat: float, lon: float) -> SoilResult:
        hint = region_for(lat, lon)
        base = {"IN": 9.5, "US": 14.0, "EU": 11.0}.get(hint.id if hint else "", 12.0)
        soc = base + 3.0 * (unit_noise("soilgrids", round(lat, 2), round(lon, 2)) - 0.5)
        return SoilResult(
            soc, demo_source(SOURCE).to_dict(datetime.now(UTC)), [d for d, _ in DEPTHS]
        )

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
