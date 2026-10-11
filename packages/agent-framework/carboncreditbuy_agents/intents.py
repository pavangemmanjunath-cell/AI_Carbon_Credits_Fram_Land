"""A deterministic intent router: from a free-text question to a plan.

"How much carbon if I add 200 trees?" → intent ``what_if``, plan
``quick-estimate``, tree change ``+200``. No model is involved: the router walks
a table of intents **from top to bottom** and picks the first one whose
keywords appear in the question. The table is plain data — read it, extend
it, test it.

Keywords are lower-case and listed per language (``en`` plus a few words in
``hi``, ``kn``, ``de``, ``fr``, ``es``). All languages are searched for every
question, because people mix languages. Keywords written in Latin letters
must match whole words; keywords in other scripts (Devanagari, Kannada) match
as substrings, since word boundaries are unreliable around their vowel signs.

Numbers are parsed with simple, documented rules:

* :func:`parse_tree_change` — "add 200 trees", "plant 50 more", "remove 30
  trees" → ``200``, ``50``, ``-30`` (a four-digit year such as 2023 is ignored);
* :func:`parse_age_years` — "60 years old", "60 साल", "60 Jahre" → ``60``.

The default table (:data:`DEFAULT_INTENTS`) is the CarbonCreditBuy one; plan
ids refer to the plans in ``apps/api/app/agents/plans.py``. Pass your own
table to :class:`IntentRouter` for another domain.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IntentSpec:
    """One row of the routing table."""

    id: str
    plan: str
    focus: tuple[str, ...]
    """Agents whose findings answer this kind of question."""
    keywords: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    needs_tree_change: bool = False
    """Only match when the question also contains a number of trees to add or remove."""
    description: str = ""


@dataclass(frozen=True)
class Route:
    """The router's decision, with the reasons for it."""

    intent: str
    plan: str
    focus: tuple[str, ...]
    matched: tuple[str, ...]
    languages: tuple[str, ...]
    tree_change: int | None
    age_years: int | None
    fallback: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "plan": self.plan,
            "focus": list(self.focus),
            "matched": list(self.matched),
            "languages": list(self.languages),
            "tree_change": self.tree_change,
            "age_years": self.age_years,
            "fallback": self.fallback,
        }


# ----------------------------------------------------------------------------- number parsing
_TREE_WORDS = (
    r"(?:trees?|saplings?|plants?|पेड़|पेड|पौधे|ಮರಗಳ(?:ನ್ನು)?|ಮರ|ಸಸಿ|bäume?n?|baum|arbres?"
    r"|árboles?|arbol(?:es)?)"
)
_COUNT = r"(\d{1,7}(?:[,  ]\d{3})*)"
# NFC-normalised like the questions, so "पेड़" matches however its nukta was typed.
_TREE_COUNT = re.compile(
    unicodedata.normalize("NFC", rf"{_COUNT}\s+(?:\w+\s+){{0,2}}?{_TREE_WORDS}"),
    re.IGNORECASE,
)
_ADD_THEN_COUNT = re.compile(
    rf"\b(?:add|plant|another|extra|more|additional|hinzufügen|pflanzen?|ajouter|planter"
    rf"|plante|añadir|agregar|plantar|planto)\b\D{{0,12}}?{_COUNT}",
    re.IGNORECASE,
)
_REMOVE_WORDS = re.compile(
    r"\b(?:remove|removing|cut|cutting|fell|felling|lose|losing|fewer|entfernen|fällen"
    r"|couper|abattre|retirer|cortar|talar|quitar)\b|काट|हटा|ಕಡಿ",
    re.IGNORECASE,
)
_AGE = re.compile(
    r"(\d{1,3})\s*(?:-\s*)?(?:years?|yrs?|yr|साल|वर्ष|ವರ್ಷ(?:ದ)?|jahre?n?|ans|años)\b",
    re.IGNORECASE,
)


def _to_int(token: str) -> int | None:
    digits = re.sub(r"[,  ]", "", token)
    try:
        return int(digits)  # also reads Devanagari/Kannada digits
    except ValueError:
        return None


def _is_year(value: int) -> bool:
    return 1900 <= value <= 2100


def parse_tree_change(question: str) -> int | None:
    """Trees to add (positive) or remove (negative); ``None`` when no count is given.

    An explicit "add/plant N" wins over a bare "N trees"; four-digit years are ignored.
    """
    text = normalize(question)
    value: int | None = None
    for pattern in (_ADD_THEN_COUNT, _TREE_COUNT):
        for match in pattern.finditer(text):
            candidate = _to_int(match.group(1))
            if candidate is not None and candidate > 0 and not _is_year(candidate):
                value = candidate
                break
        if value is not None:
            break
    if value is None:
        return None
    return -value if _REMOVE_WORDS.search(text) else value


def parse_age_years(question: str) -> int | None:
    """A tree age written as "60 years (old)" in any supported language."""
    match = _AGE.search(normalize(question))
    if not match:
        return None
    age = _to_int(match.group(1))
    return age if age is not None and 0 <= age <= 300 else None


# ----------------------------------------------------------------------------- matching
def normalize(text: str) -> str:
    """NFC-normalise, lower-case and collapse whitespace."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip().casefold()


def _is_latin(keyword: str) -> bool:
    """True when every letter is Latin — plain ASCII or accented (é, ü, ñ …)."""
    return all(ord(ch) < 0x0250 for ch in keyword if ch.isalpha())


def _matches(keyword: str, text: str) -> bool:
    if _is_latin(keyword):  # whole words only: "ans" must not match "plans"
        return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text) is not None
    return keyword in text  # Devanagari, Kannada …: substring match


class IntentRouter:
    """Walk the table top to bottom; the first intent with a keyword hit wins."""

    def __init__(self, intents: Sequence[IntentSpec], fallback: IntentSpec) -> None:
        if not intents:
            raise ValueError("an intent router needs at least one intent")
        self.intents = tuple(intents)
        self.fallback = fallback

    def route(self, question: str) -> Route:
        text = normalize(question)
        change = parse_tree_change(question)
        age = parse_age_years(question)
        for spec in self.intents:
            if spec.needs_tree_change and change is None:
                continue
            hits: list[str] = []
            languages: list[str] = []
            for language, words in spec.keywords.items():
                found = [w for w in words if _matches(normalize(w), text)]
                if found:
                    hits.extend(found)
                    languages.append(language)
            if hits:
                return Route(
                    intent=spec.id,
                    plan=spec.plan,
                    focus=spec.focus,
                    matched=tuple(hits),
                    languages=tuple(languages),
                    tree_change=change,
                    age_years=age,
                    fallback=False,
                )
        return Route(
            intent=self.fallback.id,
            plan=self.fallback.plan,
            focus=self.fallback.focus,
            matched=(),
            languages=(),
            tree_change=change,
            age_years=age,
            fallback=True,
        )


# ----------------------------------------------------------------------------- the table
DEFAULT_INTENTS: tuple[IntentSpec, ...] = (
    IntentSpec(
        id="what_if",
        plan="quick-estimate",
        focus=("carbon",),
        needs_tree_change=True,
        description="Add or remove a number of trees and compare the estimate.",
        keywords={
            "en": (
                "add",
                "plant",
                "more",
                "extra",
                "additional",
                "another",
                "what if",
                "remove",
                "cut",
                "fewer",
            ),
            "hi": ("और", "जोड़", "लगा", "अगर", "काट"),
            "kn": ("ಹೆಚ್ಚು", "ಸೇರಿಸ", "ನೆಟ್ಟ", "ಕಡಿ"),
            "de": ("hinzufügen", "mehr", "zusätzlich", "pflanze", "pflanzen", "was wäre"),
            "fr": ("ajouter", "planter", "plante", "plus", "et si"),
            "es": ("añadir", "agregar", "plantar", "planto", "más", "y si"),
        },
    ),
    IntentSpec(
        id="tree_age",
        plan="tree-age-check",
        focus=("policy", "carbon"),
        description="Old or existing trees: carbon by age and the rules that apply by age.",
        keywords={
            "en": (
                "years old",
                "how old",
                "old trees",
                "old tree",
                "tree age",
                "age of",
                "heritage",
                "veteran",
            ),
            "hi": ("पुराने", "पुराना", "उम्र", "साल पुराने"),
            "kn": ("ಹಳೆಯ", "ವಯಸ್ಸು"),
            "de": ("jahre alt", "alte bäume", "alter baum", "baumalter"),
            "fr": ("ans", "vieux arbres", "vieil arbre", "âge"),
            "es": ("años", "árboles viejos", "árbol viejo", "edad"),
        },
    ),
    IntentSpec(
        id="report",
        plan="full-assessment",
        focus=("report",),
        description="A downloadable assessment report.",
        keywords={
            "en": ("report", "pdf", "document", "download"),
            "hi": ("रिपोर्ट",),
            "kn": ("ವರದಿ",),
            "de": ("bericht",),
            "fr": ("rapport",),
            "es": ("informe",),
        },
    ),
    IntentSpec(
        id="value",
        plan="full-assessment",
        focus=("market",),
        description="Indicative money value (scenario) and other farm income — kept separate.",
        keywords={
            "en": (
                "money",
                "value",
                "worth",
                "price",
                "income",
                "earn",
                "revenue",
                "sell",
                "pay",
                "cost",
                "costs",
                "budget",
                "break-even",
                "rupee",
                "rupees",
                "dollar",
                "dollars",
                "euro",
                "euros",
            ),
            "hi": ("पैसा", "पैसे", "कीमत", "आय", "कमाई"),
            "kn": ("ಹಣ", "ಬೆಲೆ", "ಆದಾಯ"),
            "de": ("geld", "wert", "preis", "einkommen", "verdienen"),
            "fr": ("argent", "valeur", "prix", "revenu", "gagner"),
            "es": ("dinero", "valor", "precio", "ingreso", "ganar"),
        },
    ),
    IntentSpec(
        id="programmes",
        plan="full-assessment",
        focus=("policy",),
        description="Which programmes might apply (screening, not eligibility).",
        keywords={
            "en": (
                "credit",
                "credits",
                "eligible",
                "eligibility",
                "programme",
                "programmes",
                "program",
                "programs",
                "scheme",
                "schemes",
                "certify",
                "certification",
                "registry",
                "subsidy",
                "subsidies",
                "incentive",
                "incentives",
                "ccts",
                "crcf",
                "gcp",
            ),
            "hi": ("क्रेडिट", "योजना", "पात्र"),
            "kn": ("ಕ್ರೆಡಿಟ್", "ಯೋಜನೆ", "ಅರ್ಹ"),
            "de": ("zertifikat", "zertifizierung", "förderung", "programm", "berechtigt"),
            "fr": ("crédit", "crédits", "éligible", "programme", "certification"),
            "es": ("crédito", "créditos", "elegible", "programa", "certificación"),
        },
    ),
    IntentSpec(
        id="vegetation",
        plan="full-assessment",
        focus=("imagery",),
        description="Satellite vegetation health and detected tree cover.",
        keywords={
            "en": (
                "ndvi",
                "ndmi",
                "vegetation",
                "green",
                "greenness",
                "health",
                "healthy",
                "satellite",
                "imagery",
                "canopy",
                "tree cover",
                "drought",
                "moisture",
            ),
            "hi": ("हरियाली", "उपग्रह", "सूखा"),
            "kn": ("ಹಸಿರು", "ಉಪಗ್ರಹ"),
            "de": ("vegetation", "satellit", "gesundheit", "trockenheit"),
            "fr": ("végétation", "satellite", "santé", "sécheresse"),
            "es": ("vegetación", "satélite", "salud", "sequía"),
        },
    ),
    IntentSpec(
        id="land",
        plan="quick-estimate",
        focus=("land",),
        description="Plot size, location, boundary and land cover.",
        keywords={
            "en": (
                "area",
                "size",
                "how big",
                "hectare",
                "hectares",
                "acre",
                "acres",
                "boundary",
                "land cover",
                "cropland",
                "climate",
            ),
            "hi": ("ज़मीन", "जमीन", "क्षेत्रफल", "एकड़"),
            "kn": ("ಭೂಮಿ", "ವಿಸ್ತೀರ್ಣ", "ಎಕರೆ"),
            "de": ("fläche", "größe", "hektar", "grenze", "klima"),
            "fr": ("surface", "superficie", "taille", "hectare", "limite", "climat"),
            "es": ("superficie", "tamaño", "hectárea", "límite", "clima"),
        },
    ),
    IntentSpec(
        id="carbon",
        plan="quick-estimate",
        focus=("carbon",),
        description="Estimated annual carbon removal.",
        keywords={
            "en": (
                "carbon",
                "co2",
                "co₂",
                "removal",
                "sequester",
                "sequestration",
                "estimate",
                "tco2e",
                "how much",
            ),
            "hi": ("कार्बन",),
            "kn": ("ಇಂಗಾಲ", "ಕಾರ್ಬನ್"),
            "de": ("kohlenstoff", "kohlendioxid", "bindung"),
            "fr": ("carbone",),
            "es": ("carbono",),
        },
    ),
)

FALLBACK_INTENT = IntentSpec(
    id="general",
    plan="quick-estimate",
    focus=("carbon",),
    description="No keyword matched: run a quick estimate and say so.",
)


def default_router() -> IntentRouter:
    return IntentRouter(DEFAULT_INTENTS, FALLBACK_INTENT)
