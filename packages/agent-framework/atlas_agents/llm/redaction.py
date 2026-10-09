"""Privacy filter: what may leave the process, and what may appear in a transcript.

Two layers, both deterministic:

1. :func:`redact` walks dicts and lists and **drops keys** that carry location or
   identity — ``lat``, ``lon``, ``geometry``, ``bbox``, ``name``, ``email`` … — at
   any depth. Strings inside are passed through :func:`redact_text`.
2. :func:`redact_text` **masks coordinate-looking text**: decimal pairs such as
   ``13.2923, 77.5384``, hemisphere notation (``13.29N 77.53E``), degree and
   degree-minute-second forms (``13°17'40"N``), labelled values (``lat: 13.29``),
   e-mail addresses and international phone numbers.

The same rules feed the ``no-coordinates`` guardrail (:func:`find_coordinates`),
so "what we remove" and "what we check for" can never drift apart.

Why so strict? CLAUDE.md principle 11: coordinates are never sent to a language
model and never logged. A false positive (a harmless number masked) costs a
little readability; a false negative leaks a farm's location.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

MASK = "[location removed]"
"""Replacement text for anything that looks like a location or an identity."""

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        # location
        "lat",
        "lon",
        "lng",
        "long",
        "latitude",
        "longitude",
        "geometry",
        "geom",
        "coordinates",
        "coords",
        "bbox",
        "centroid",
        "public_centroid",
        "polygon",
        "boundary",
        "line",
        "point",
        "points",
        "features",
        "preview",
        "geojson",
        "wkt",
        "address",
        # identity
        "name",
        "owner",
        "email",
        "phone",
    }
)
"""Keys removed by :func:`redact` (compared case-insensitively)."""

_NUM = r"[-+−]?\d{1,3}\.\d{3,}"  # 1–3 integer digits and at least 3 decimals

# "13.2923, 77.5384" · "13.2923 77.5384" · "13.2923;77.5384" · "13.2923/77.5384"
_DECIMAL_PAIR = re.compile(rf"(?<![\w.])({_NUM})\s*[,;/]?\s*({_NUM})(?![\w.])")
# 13°17'40"N · 77° 32′ 25″ E
_DMS = re.compile(
    r"(?<![\w.])\d{1,3}\s?°\s?\d{1,2}\s?['′]\s?(?:\d{1,2}(?:\.\d+)?\s?[\"″])?\s?[NSEWnsew]?"
)
# 13.29° N · 77.5° · 13°N  (but not "24.0 °C" or "75 °F")
_DEGREES = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d+)?\s?°(?!\s?[CFcf]\b)\s?[NSEWnsew]?")
# 13.29N · 77.53 E  (upper-case hemisphere letters after a decimal number)
_HEMISPHERE = re.compile(r"(?<![\w.])\d{1,3}\.\d+\s?[NSEW](?![\w])")
# lat: 13.29 · longitude=77.53 · lng 77.5
_LABELLED = re.compile(
    r"\b(?:lat|latitude|lon|lng|long|longitude)\b\s*[:=]?\s*[-+−]?\d{1,3}(?:\.\d+)?",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+\d[\d\s().-]{7,}\d")

_LOCATION_PATTERNS: tuple[re.Pattern[str], ...] = (_DMS, _DEGREES, _HEMISPHERE, _LABELLED)


def _is_lat_lon_pair(first: str, second: str) -> bool:
    """True when two numbers could be a latitude/longitude pair (either order)."""
    try:
        a = abs(float(first.replace("−", "-")))
        b = abs(float(second.replace("−", "-")))
    except ValueError:
        return False
    return (a <= 90 and b <= 180) or (a <= 180 and b <= 90)


def find_coordinates(text: str) -> list[str]:
    """Return the coordinate-looking snippets found in ``text`` (empty when clean).

    Used by the ``no-coordinates`` guardrail. Callers must not echo the snippets
    back to users — report *where* something was found, not *what*.
    """
    hits: list[str] = []
    for match in _DECIMAL_PAIR.finditer(text):
        if _is_lat_lon_pair(match.group(1), match.group(2)):
            hits.append(match.group(0))
    for pattern in _LOCATION_PATTERNS:
        hits.extend(m.group(0) for m in pattern.finditer(text))
    return hits


def redact_text(text: str) -> str:
    """Mask coordinates, e-mail addresses and phone numbers in free text."""

    def _pair(match: re.Match[str]) -> str:
        return MASK if _is_lat_lon_pair(match.group(1), match.group(2)) else match.group(0)

    masked = _DECIMAL_PAIR.sub(_pair, text)
    for pattern in _LOCATION_PATTERNS:
        masked = pattern.sub(MASK, masked)
    masked = _EMAIL.sub("[email removed]", masked)
    return _PHONE.sub("[phone removed]", masked)


def _decimals(value: float) -> int:
    text = repr(float(value))
    return len(text.split(".", 1)[1]) if "." in text and "e" not in text else 0


def looks_like_position(value: Any) -> bool:
    """True for ``[lon, lat]``-style lists: 2–3 numbers, precise, within range.

    ``[77.538399, 13.292298]`` is a position; ``[0.2, 1.5]`` (a parameter clamp)
    and ``[2023, 2024]`` (years) are not.
    """
    if not isinstance(value, (list, tuple)) or len(value) not in (2, 3):
        return False
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        return False
    first, second = float(value[0]), float(value[1])
    precise = _decimals(first) >= 3 and _decimals(second) >= 3
    return precise and _is_lat_lon_pair(str(first), str(second))


def is_sensitive_key(key: Any, keys: frozenset[str] = SENSITIVE_KEYS) -> bool:
    """True when ``key`` names a location or identity field (case-insensitive)."""
    return str(key).lower() in keys


def redact(value: Any, keys: frozenset[str] = SENSITIVE_KEYS) -> Any:
    """Return a copy of ``value`` without sensitive keys and with masked text.

    Works on any JSON-like structure (dicts, lists, tuples, strings, numbers).
    """
    if isinstance(value, Mapping):
        return {str(k): redact(v, keys) for k, v in value.items() if str(k).lower() not in keys}
    if isinstance(value, (list, tuple)):
        if looks_like_position(value):
            return MASK
        return [redact(v, keys) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def sensitive_number_strings(values: Iterable[float], min_decimals: int = 3) -> set[str]:
    """Text forms of exact coordinates to look for (``13.292298`` → ``13.292``, ``13.2923`` …).

    The guardrail searches transcripts for these strings, so a plot's own
    centroid can never appear even if it slips past the generic patterns.
    """
    forms: set[str] = set()
    for value in values:
        for decimals in range(min_decimals, 7):
            text = f"{float(value):.{decimals}f}"
            forms.add(text)
            stripped = text.rstrip("0").rstrip(".")
            if "." in stripped and len(stripped.split(".")[1]) >= min_decimals:
                forms.add(stripped)
    return forms
