"""Privacy-preserving plain-language explanation.

The default provider is a deterministic template: no network, no model. An
LLM provider can be enabled with ``ATLAS_EXPLAIN_PROVIDER=llm`` and still only
ever receives the validated indicator payload (no coordinates, no identity).
"""

from __future__ import annotations

from typing import Any

PRIVACY_NOTE = "Only derived indicators were used; no coordinates or personal data were processed."

_LABELS = {
    "dbh": "tree diameter measurements",
    "height": "tree height measurements",
    "baseline": "a land-use baseline",
    "management": "farm management records",
    "ownership": "land ownership documents",
    "satellite": "a satellite observation",
}


def _fmt(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


class TemplateExplainer:
    provider = "template"

    def explain(self, indicators: dict[str, Any], language: str = "en") -> str:
        parts: list[str] = []
        trees = indicators.get("tree_count")
        species = indicators.get("species")
        area = indicators.get("area_hectares")
        if trees and species and area:
            parts.append(
                f"Your {int(trees):,} {str(species).lower()} trees on {_fmt(area, 2)} hectares"
            )
        elif trees:
            parts.append(f"Your {int(trees):,} trees")
        else:
            parts.append("Your plot")

        ndvi = indicators.get("ndvi")
        trend = indicators.get("ndvi_trend_pct")
        if ndvi is not None:
            health = (
                "healthy"
                if float(ndvi) >= 0.6
                else ("moderate" if float(ndvi) >= 0.3 else "sparse")
            )
            sentence = f" show {health} vegetation (NDVI {_fmt(ndvi, 2)})"
            if trend is not None:
                direction = "risen" if float(trend) > 0 else "fallen"
                sentence += f"; the vegetation index has {direction} about {abs(float(trend)):.0f}% over the evaluated period"
            parts.append(sentence + ".")
        else:
            parts.append(" have no satellite vegetation reading yet.")

        central = indicators.get("estimate_central")
        low = indicators.get("estimate_low")
        high = indicators.get("estimate_high")
        if central is not None:
            rng = (
                f" (roughly {_fmt(low)} to {_fmt(high)})"
                if low is not None and high is not None
                else ""
            )
            parts.append(
                f" A documented biomass model suggests they remove about {_fmt(central)} tonnes of CO₂e per year{rng}."
            )
        confidence = indicators.get("confidence")
        if confidence:
            parts.append(f" Confidence in this estimate is {confidence}.")
        missing = indicators.get("missing_evidence") or []
        if missing:
            names = [_LABELS.get(str(m), str(m).replace("_", " ")) for m in missing[:3]]
            parts.append(
                " Whether this can become a Green Credit or a carbon credit depends on evidence you do not have yet: "
                + ", ".join(names)
                + "."
            )
        parts.append(" This is a scenario estimate, not an issued credit.")
        return "".join(parts)


class ExplainService:
    def __init__(self, provider: str = "template") -> None:
        self.provider_name = provider if provider in {"template", "llm"} else "template"
        self.template = TemplateExplainer()

    def explain(self, indicators: dict[str, Any], language: str) -> dict[str, Any]:
        # The llm provider is opt-in and not bundled; it falls back to the template
        # so a misconfigured deployment never silently sends data elsewhere.
        text = self.template.explain(indicators, language)
        return {
            "text": text,
            "provider": "template",
            "language": language,
            "privacy_note": PRIVACY_NOTE,
        }
