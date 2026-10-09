"""Evidence readiness score (config/readiness.yaml).

``score = round(100 × Σ weight(present) / Σ weight(all))``; the grade comes
from the inclusive lower bounds in the same file (low < 40, medium 40–69,
high ≥ 70 in v0.1).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from carbon_engine.types import EvidenceItem, Readiness


def evidence_items(readiness_config: Mapping[str, Any]) -> list[EvidenceItem]:
    return [
        EvidenceItem(id=str(e["id"]), label=str(e["label"]), weight=int(e["weight"]))
        for e in readiness_config["evidence"]
    ]


def grade_for(score: int, grades: Mapping[str, int]) -> str:
    for grade, lower in sorted(grades.items(), key=lambda kv: kv[1], reverse=True):
        if score >= int(lower):
            return str(grade)
    return "low"


def score_readiness(present: Mapping[str, bool], readiness_config: Mapping[str, Any]) -> Readiness:
    """Score the evidence file; ``present`` maps evidence id → bool."""
    items = evidence_items(readiness_config)
    total = sum(i.weight for i in items)
    present_items = [i for i in items if present.get(i.id, False)]
    missing_items = [i for i in items if not present.get(i.id, False)]
    have = sum(i.weight for i in present_items)
    score = int(round(100.0 * have / total)) if total else 0
    return Readiness(
        score=score,
        grade=grade_for(score, readiness_config["grades"]),
        present_evidence=present_items,
        missing_evidence=missing_items,
    )
