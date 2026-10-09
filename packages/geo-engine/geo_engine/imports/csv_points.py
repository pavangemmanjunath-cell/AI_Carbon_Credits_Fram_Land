"""CSV reader: one point per row.

* Delimiter: comma, semicolon, tab or pipe (sniffed from the first rows).
* Header: columns named ``lat`` / ``latitude`` / ``y`` and ``lon`` / ``lng`` / ``long`` /
  ``longitude`` / ``x`` (any case, any order). Without a header the first two cells (or the single
  cell) of a row are read as a coordinate pair, latitude first.
* Cells may hold decimal degrees, hemisphere letters or degrees-minutes-seconds (the same grammar
  as the coordinate parser); a decimal comma is understood.
* Other numeric columns become point attributes (``score`` / ``confidence`` / ``prob`` /
  ``probability`` and ``height`` / ``h`` are used by the classifier); a ``name`` column labels
  the point.
"""

from __future__ import annotations

import csv
import io
import math

from geo_engine.coordinates import parse_coordinate_line, parse_coordinate_value
from geo_engine.imports.errors import ImportDataError
from geo_engine.imports.shapes import MAX_NAME_CHARS, Collector
from geo_engine.imports.types import MAX_FEATURES, ParsedVector

LAT_NAMES = {"lat", "latitude", "y", "lat_deg", "latitude_deg"}
LON_NAMES = {"lon", "lng", "long", "longitude", "x", "lon_deg", "longitude_deg"}
NAME_COLUMNS = {"name", "label", "title"}
_DELIMITERS = (",", ";", "\t", "|")


def decode_text(data: bytes) -> tuple[str, bool]:
    """Decode bytes to text; returns ``(text, fell_back_to_cp1252)``."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace"), False
    try:
        return data.decode("utf-8-sig"), False
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace"), True


def _sniff_delimiter(lines: list[str]) -> str:
    sample = lines[:5]
    best, best_score = ",", 0
    for delimiter in _DELIMITERS:
        counts = [line.count(delimiter) for line in sample]
        if counts and min(counts) > 0 and len(set(counts)) == 1 and counts[0] > best_score:
            best, best_score = delimiter, counts[0]
    if best_score == 0:  # inconsistent counts: take the delimiter that appears most overall
        totals = {d: sum(line.count(d) for line in sample) for d in _DELIMITERS}
        winner = max(totals, key=lambda d: totals[d])
        best = winner if totals[winner] else ","
    return best


def _number(cell: str) -> float | None:
    text = cell.strip().strip('"')
    if not text:
        return None
    if "." not in text and text.count(",") == 1:
        text = text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _rows(text: str, delimiter: str) -> list[list[str]]:
    try:
        rows = [row for row in csv.reader(io.StringIO(text), delimiter=delimiter) if any(row)]
    except csv.Error as exc:
        raise ImportDataError("invalid_content", "the file is not a readable CSV") from exc
    return rows


def _row_list(numbers: list[int]) -> str:
    shown = ", ".join(str(n) for n in numbers[:8])
    return shown + (f" and {len(numbers) - 8} more" if len(numbers) > 8 else "")


def parse_csv(data: bytes) -> ParsedVector:
    """Read a CSV of points from bytes."""
    text, fell_back = decode_text(data)
    if "\x00" in text[:4096]:
        raise ImportDataError("invalid_content", "the file contains binary data, not CSV text")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ImportDataError("empty_file", "the file is empty")
    if len(lines) > MAX_FEATURES + 1:
        raise ImportDataError(
            "too_many_features", f"the file holds more than {MAX_FEATURES} rows; split it first"
        )
    delimiter = _sniff_delimiter(lines)
    rows = _rows(text, delimiter)
    first = [cell.strip().strip('"').lower() for cell in rows[0]]
    has_header = any(cell in LAT_NAMES or cell in LON_NAMES for cell in first)

    out = Collector()
    warnings: list[str] = []
    if fell_back:
        warnings.append("The file is not UTF-8; it was read as Windows-1252.")
    skipped: list[int] = []
    swapped: list[int] = []
    ignored_columns = False

    if has_header:
        lat_cols = [i for i, cell in enumerate(first) if cell in LAT_NAMES]
        lon_cols = [i for i, cell in enumerate(first) if cell in LON_NAMES]
        if not lat_cols or not lon_cols:
            raise ImportDataError(
                "invalid_content",
                "the header needs both a latitude (lat, latitude, y) and a longitude "
                "(lon, lng, longitude, x) column",
            )
        lat_col, lon_col = lat_cols[0], lon_cols[0]
        name_col = next((i for i, cell in enumerate(first) if cell in NAME_COLUMNS), None)
        reserved = {lat_col, lon_col, *([name_col] if name_col is not None else [])}
        header = [cell.strip().strip('"') for cell in rows[0]]
        for number, row in enumerate(rows[1:], start=2):
            if len(row) <= max(lat_col, lon_col):
                skipped.append(number)
                continue
            try:
                lat = parse_coordinate_value(row[lat_col], "lat")
                lon = parse_coordinate_value(row[lon_col], "lon")
            except ValueError:
                skipped.append(number)
                continue
            props: dict[str, float | str] = {}
            for index, cell in enumerate(row):
                if index in reserved or index >= len(header) or not header[index]:
                    continue
                value = _number(cell)
                if value is not None:
                    props[header[index]] = value
            name = (
                row[name_col].strip()[:MAX_NAME_CHARS]
                if name_col is not None and name_col < len(row) and row[name_col].strip()
                else None
            )
            if name:
                props["name"] = name
            out.add_point([lon, lat], props, name)
    else:
        for number, row in enumerate(rows, start=1):
            cells = [cell.strip() for cell in row]
            line = " ".join(cells[:2]) if len(cells) >= 2 else (cells[0] if cells else "")
            if len(cells) > 2:
                ignored_columns = True
            parsed = parse_coordinate_line(line) if any(ch.isdigit() for ch in line) else None
            if parsed is None:
                if number == 1 and not any(ch.isdigit() for ch in line):
                    continue  # a header row with unknown column names
                skipped.append(number)
                continue
            lat, lon, was_swapped = parsed
            if was_swapped:
                swapped.append(number)
            out.add_point([lon, lat], {}, None)
        if ignored_columns:
            warnings.append(
                "The CSV has no header, so only the first two columns (latitude, longitude) were "
                "used; name the columns lat, lon, score, height to import more."
            )

    if skipped:
        warnings.append(
            f"Skipped {len(skipped)} row(s) without readable coordinates "
            f"(row {_row_list(skipped)})."
        )
    if swapped:
        warnings.append(
            f"Row(s) {_row_list(swapped)}: the values were read as longitude, latitude and swapped."
        )
    if not out.features:
        raise ImportDataError("no_coordinates", "no rows with readable coordinates were found")
    warnings.extend(out.warnings())
    return ParsedVector(format="csv", features=out.features, warnings=warnings)
