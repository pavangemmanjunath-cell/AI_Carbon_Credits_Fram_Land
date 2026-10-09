"""Parse typed or pasted coordinates (one point per line) into points, a polygon or an error.

Accepted per line (latitude first):

* decimal degrees: ``13.2923, 77.5384`` · ``13.2923 77.5384`` · ``13.2923;77.5384`` (a decimal
  comma is understood when the line has no dot: ``13,2923;77,5384``);
* hemisphere letters, prefix or suffix: ``13.29N 77.53E`` · ``N13.29 E77.53`` · ``S33.9 E151.2``
  (S and W are negative; the letters decide which value is the latitude);
* degrees-minutes-seconds with ``°  '  "`` or ``d m s`` markers and decimal seconds:
  ``13°17'32.3"N 77°32'18.2"E`` · ``13d17m32.3sN 77d32m18.2sE`` · ``13 17 32.3 N 77 32 18.2 E``;
  degrees and decimal minutes (``13°17.538'N``) work too;
* optional ``lat:`` / ``lon:`` labels, which also fix the order.

Header lines (no digits) and blank lines are ignored. Without hemisphere letters or labels the
first value is the latitude; when it is outside ±90 and the second value is inside, the pair is
swapped and a warning says so. One point gives ``kind = "point"``, three or more give
``"polygon"`` (ring closed automatically and validated like ``POST /plots``), two give
``"invalid"`` with a warning. Limits: 500 data lines and 20 000 characters.

Warnings mention line numbers only — never the coordinates themselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import Polygon

from geo_engine.construct import polygon_to_geojson
from geo_engine.errors import GeometryError
from geo_engine.geometry import ValidationLimits, measure_polygon, validate_polygon

MAX_LINES = 500
MAX_CHARS = 20_000
POINT_DIGITS = 7

_NUM = r"\d+(?:\.\d+)?"
_TRANSLATE = str.maketrans(
    {
        "′": "'",
        "’": "'",
        "‘": "'",
        "`": "'",
        "´": "'",
        "″": '"',
        "”": '"',
        "“": '"',
        "‟": '"',
        "º": "°",
        "˚": "°",
        "∘": "°",
        "−": "-",
        "–": "-",
        "—": "-",
        " ": " ",
        " ": " ",
        " ": " ",
        "﻿": "",
    }
)
_LABEL_RE = re.compile(r"\b(lat(?:itude)?|lon(?:g(?:itude)?)?|lng)\b\.?\s*[:=]?", re.IGNORECASE)
_SEPARATORS = " ,;\t'\""
_SYM_POST = re.compile(
    rf"(?P<sign>[+-])?\s*(?P<d>{_NUM})\s*°\s*(?:(?P<m>{_NUM})\s*'\s*)?"
    rf"(?:(?P<s>{_NUM})\s*\"\s*)?(?P<hem>[NSEWnsew])?"
)
_SYM_PRE = re.compile(
    rf"(?P<hem>[NSEWnsew])\s*(?P<sign>[+-])?\s*(?P<d>{_NUM})\s*°\s*(?:(?P<m>{_NUM})\s*'\s*)?"
    rf"(?:(?P<s>{_NUM})\s*\"\s*)?"
)
_TOKEN_RE = re.compile(rf"(?P<letter>[NSEWnsew])|(?P<number>[+-]?{_NUM})")


@dataclass(frozen=True)
class ParsedPoint:
    lat: float
    lon: float

    def to_dict(self) -> dict[str, float]:
        return {"lat": self.lat, "lon": self.lon}


@dataclass
class ParsedCoordinates:
    """Result of :func:`parse_coordinates` (contract: ``POST /geometry/parse-coordinates``)."""

    points: list[ParsedPoint]
    kind: str  # "point" | "polygon" | "invalid"
    geometry: dict[str, Any] | None
    area_hectares: float | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": [p.to_dict() for p in self.points],
            "kind": self.kind,
            "geometry": self.geometry,
            "area_hectares": self.area_hectares,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class _Component:
    value: float  # signed decimal degrees
    axis: str | None  # "lat" | "lon" when a hemisphere letter said so


# ---------------------------------------------------------------------------- one component
def _to_component(
    numbers: list[str], sign: str | None, hemisphere: str | None
) -> _Component | None:
    """Degrees (+ minutes (+ seconds)) and a hemisphere letter into a signed value."""
    values = [float(n) for n in numbers]
    if not 1 <= len(values) <= 3:
        return None
    degrees = values[0]
    if len(values) > 1 and (degrees != int(degrees) or values[1] >= 60.0):
        return None
    if len(values) == 3 and (values[1] != int(values[1]) or values[2] >= 60.0):
        return None
    value = degrees + (values[1] / 60.0 if len(values) > 1 else 0.0)
    if len(values) == 3:
        value += values[2] / 3600.0
    letter = hemisphere.upper() if hemisphere else None
    axis = None
    if letter in ("N", "S"):
        axis = "lat"
    elif letter in ("E", "W"):
        axis = "lon"
    if letter in ("S", "W"):
        value = -abs(value)
    elif sign == "-":
        if letter in ("N", "E"):
            return None  # a minus sign contradicting the hemisphere letter
        value = -value
    return _Component(value=value, axis=axis)


def _clean(text: str) -> str:
    return text.translate(_TRANSLATE).replace("''", '"')


def _normalise_markers(text: str) -> str:
    """Turn ``13d17m32.3s`` word markers into ``13° 17' 32.3"`` symbols.

    The letters d, m and s are only read as markers when a ``d`` sits between two numbers; a lone
    trailing ``S`` stays the southern hemisphere.
    """
    converted = re.sub(r"(?<=\d)\s*[dD](?:eg)?\.?\s*(?=\d)", "° ", text)
    if converted == text:
        return text
    stop = r"(?=\d|\s|$|[,;NSEWnsew])"
    text = re.sub(rf"(?<=\d)\s*[mM](?:in)?\.?{stop}", "' ", converted)
    return re.sub(rf"('\s*{_NUM})\s*[sS](?:ec)?\.?(?=$|[\s,;NSEWnsew])", r'\1"', text)


def _symbol_components(text: str, expected: int) -> list[_Component] | None:
    stripped = text.strip()
    pattern = _SYM_PRE if re.match(r"^[NSEWnsew]", stripped) else _SYM_POST
    components: list[_Component] = []
    position = 0
    for match in pattern.finditer(stripped):
        if stripped[position : match.start()].strip(_SEPARATORS):
            return None
        position = match.end()
        numbers = [g for g in (match["d"], match["m"], match["s"]) if g]
        component = _to_component(numbers, match["sign"], match["hem"])
        if component is None:
            return None
        components.append(component)
    if stripped[position:].strip(_SEPARATORS) or len(components) != expected:
        return None
    return components


def _letter_components(text: str, expected: int) -> list[_Component] | None:
    tokens = list(_TOKEN_RE.finditer(text))
    covered = sum(len(m.group(0)) for m in tokens)
    leftover = "".join(ch for ch in text if ch not in _SEPARATORS and not ch.isspace())
    if len(leftover) != covered or not tokens:
        return None
    prefix_style = tokens[0].group("letter") is not None
    groups: list[list[re.Match[str]]] = []
    for token in tokens:
        is_letter = token.group("letter") is not None
        if prefix_style:
            if is_letter:
                groups.append([token])
            else:
                groups[-1].append(token)
        else:
            if not groups or (groups[-1] and groups[-1][-1].group("letter") is not None):
                groups.append([])
            groups[-1].append(token)
    if len(groups) != expected:
        return None
    components: list[_Component] = []
    for group in groups:
        letters = [t.group("letter") for t in group if t.group("letter")]
        numbers = [t.group("number") for t in group if t.group("number")]
        if len(letters) > 1 or not numbers:
            return None
        sign = "-" if numbers[0].startswith("-") else None
        component = _to_component(
            [n.lstrip("+-") for n in numbers], sign, letters[0] if letters else None
        )
        if component is None:
            return None
        components.append(component)
    return components


def _numeric_components(text: str, expected: int) -> list[_Component] | None:
    numbers = re.findall(rf"[+-]?{_NUM}", text)
    leftover = "".join(ch for ch in text if ch not in _SEPARATORS and not ch.isspace())
    if len("".join(numbers)) != len(leftover):
        return None
    if expected == 1:
        if len(numbers) not in (1, 2, 3):
            return None
        per_group = len(numbers)
    else:
        if len(numbers) not in (2, 4, 6):
            return None
        per_group = len(numbers) // 2
    components: list[_Component] = []
    for start in range(0, len(numbers), per_group):
        chunk = numbers[start : start + per_group]
        sign = "-" if chunk[0].startswith("-") else None
        component = _to_component([n.lstrip("+-") for n in chunk], sign, None)
        if component is None:
            return None
        components.append(component)
    return components


def _components(text: str, expected: int) -> list[_Component] | None:
    text = _normalise_markers(text)
    if "°" in text:
        return _symbol_components(text, expected)
    if re.search(r"[NSEWnsew]", text):
        return _letter_components(text, expected)
    return _numeric_components(text, expected)


def _decimal_comma(text: str) -> str:
    """``13,2923;77,5384`` and ``13,29 77,53`` use a decimal comma: turn it into a dot."""
    if "." not in text and len(re.findall(r"\d,\d", text)) == 2:
        return re.sub(r"(?<=\d),(?=\d)", ".", text)
    return text


# ---------------------------------------------------------------------------- one value (CSV cells)
def parse_coordinate_value(text: str, axis: str | None = None) -> float:
    """Parse a single latitude or longitude (decimal, hemisphere letter or DMS) to degrees.

    ``axis`` is ``"lat"``, ``"lon"`` or ``None``; the range and any hemisphere letter are checked
    against it. Raises ``ValueError`` when the text is not a coordinate.
    """
    cleaned = _clean(str(text)).strip()
    if not cleaned:
        raise ValueError("empty coordinate")
    if "." not in cleaned and re.fullmatch(r"[+-]?\d+,\d+", cleaned):
        cleaned = cleaned.replace(",", ".")
    parsed = _components(cleaned, 1)
    if not parsed:
        raise ValueError("not a coordinate")
    component = parsed[0]
    if axis and component.axis and component.axis != axis:
        raise ValueError(f"hemisphere letter does not match the {axis} column")
    limit = 90.0 if (axis or component.axis) == "lat" else 180.0
    if not -limit <= component.value <= limit:
        raise ValueError("coordinate out of range")
    return component.value


# ---------------------------------------------------------------------------- one line
def parse_coordinate_line(line: str) -> tuple[float, float, bool] | None:
    """Parse one line into ``(lat, lon, swapped)``; ``None`` when it is not a coordinate pair."""
    cleaned = _clean(line).strip()
    labels = [m.group(1).lower()[:3] for m in _LABEL_RE.finditer(cleaned)]
    lon_first = False
    if labels:
        labels = ["lon" if label in ("lon", "lng") else "lat" for label in labels]
        if sorted(labels) != ["lat", "lon"]:
            return None
        lon_first = labels[0] == "lon"
        cleaned = _LABEL_RE.sub(" ", cleaned)
    cleaned = _decimal_comma(cleaned)
    parsed = _components(cleaned, 2)
    if not parsed:
        return None
    first, second = parsed
    swapped = False  # True only for the range rule: letters and labels reorder silently
    if first.axis or second.axis:
        if first.axis is not None and first.axis == second.axis:
            return None  # two latitudes or two longitudes
        # The letters decide; a value without a letter takes the remaining axis.
        first_axis = first.axis or ("lon" if second.axis == "lat" else "lat")
        if first_axis == "lon":
            first, second = second, first
    elif lon_first:
        first, second = second, first
    elif abs(first.value) > 90.0 and abs(second.value) <= 90.0:
        first, second = second, first
        swapped = True
    lat, lon = first.value, second.value
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return round(lat, POINT_DIGITS), round(lon, POINT_DIGITS), swapped


# ---------------------------------------------------------------------------- the text
def _line_list(numbers: list[int]) -> str:
    shown = ", ".join(str(n) for n in numbers[:8])
    return shown + (f" and {len(numbers) - 8} more" if len(numbers) > 8 else "")


def parse_coordinates(text: str, limits: ValidationLimits | None = None) -> ParsedCoordinates:
    """Parse pasted coordinates (see the module docstring). Never logs or echoes coordinates."""
    limits = limits or ValidationLimits()
    if not isinstance(text, str):
        raise GeometryError("invalid_input", "text must be a string")
    if len(text) > MAX_CHARS:
        raise GeometryError("text_too_long", f"text has more than {MAX_CHARS} characters")
    points: list[ParsedPoint] = []
    swapped_lines: list[int] = []
    skipped_lines: list[int] = []
    data_lines = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or not re.search(r"\d", raw):
            continue  # blank and header lines
        data_lines += 1
        if data_lines > MAX_LINES:
            raise GeometryError("too_many_lines", f"more than {MAX_LINES} coordinate lines")
        parsed = parse_coordinate_line(raw)
        if parsed is None:
            skipped_lines.append(number)
            continue
        lat, lon, swapped = parsed
        if swapped:
            swapped_lines.append(number)
        points.append(ParsedPoint(lat=lat, lon=lon))

    warnings: list[str] = []
    if skipped_lines:
        warnings.append(
            f"Line(s) {_line_list(skipped_lines)} could not be read as a coordinate pair and "
            "were skipped."
        )
    if swapped_lines:
        warnings.append(
            f"Line(s) {_line_list(swapped_lines)}: the values were read as longitude, latitude "
            "and swapped (latitude comes first, between -90 and 90)."
        )
    return _classify(points, warnings, limits)


def _classify(
    points: list[ParsedPoint], warnings: list[str], limits: ValidationLimits
) -> ParsedCoordinates:
    if not points:
        warnings.append("No coordinates found. Enter one latitude, longitude pair per line.")
        return ParsedCoordinates([], "invalid", None, None, warnings)
    if len(points) == 1:
        only = points[0]
        geometry = {"type": "Point", "coordinates": [only.lon, only.lat]}
        return ParsedCoordinates(points, "point", geometry, None, warnings)
    if len(points) == 2:
        warnings.append(
            "Two points describe a line, not an area: add at least a third corner to make a "
            "polygon, or use the tree-line tool."
        )
        return ParsedCoordinates(points, "invalid", None, None, warnings)

    ring: list[tuple[float, float]] = []
    for point in points:
        position = (point.lon, point.lat)
        if not ring or ring[-1] != position:
            ring.append(position)
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()  # the user closed the ring themselves
    if len(ring) != len(points):
        warnings.append("Repeated consecutive or closing points were merged.")
    if len(ring) < 3:
        warnings.append("Fewer than three different corners: cannot make a polygon.")
        return ParsedCoordinates(points, "invalid", None, None, warnings)
    candidate = {"type": "Polygon", "coordinates": [[*[list(p) for p in ring], list(ring[0])]]}
    try:
        polygon: Polygon = validate_polygon(candidate, limits)
    except GeometryError as exc:
        message = re.sub(r"\s*\[[^\]]*\]", "", exc.detail).strip()  # drop coordinates from the text
        if exc.code == "self_intersection":
            message += ". List the corners in order around the boundary."
        warnings.append(message[0].upper() + message[1:] if message else "Invalid polygon.")
        return ParsedCoordinates(points, "invalid", None, None, warnings)
    area = measure_polygon(polygon).area_hectares
    return ParsedCoordinates(points, "polygon", polygon_to_geojson(polygon), area, warnings)
