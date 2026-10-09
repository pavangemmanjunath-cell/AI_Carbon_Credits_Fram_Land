/**
 * Client-side mirror of `POST /geometry/parse-coordinates` (api-contract §v0.2),
 * used only as the clearly labelled offline fallback. The server stays the
 * authority: when the API is reachable the UI shows the server's parse.
 *
 * One point per line, latitude first:
 *   13.2923, 77.5384 · 13.2923 77.5384 · 13.2923;77.5384
 *   13.29N 77.53E · N 13.29, E 77.53
 *   13°17'40"N 77°32'25"E · 13°17.67'N 77°32.42'E
 * If the first value is outside ±90 and the second inside, the pair is swapped
 * with a warning. Coordinates are never logged.
 */
import type { LatLon } from '@/types/api';

export const MAX_COORDINATE_LINES = 500;
export const MAX_COORDINATE_CHARS = 20_000;

type Hemisphere = 'N' | 'S' | 'E' | 'W';

interface Component {
  value: number;
  hemisphere: Hemisphere | null;
}

export interface ParsedLine {
  line: number;
  point: LatLon | null;
  warning: string | null;
}

export interface CoordinateParse {
  points: LatLon[];
  kind: 'point' | 'polygon' | 'invalid';
  warnings: string[];
}

/** One coordinate component: optional leading hemisphere, degrees, optional minutes/seconds, optional trailing hemisphere. */
const COMPONENT = /^([NSEW])?\s*([+-]?\d+(?:\.\d+)?)\s*(?:°\s*)?(?:(\d+(?:\.\d+)?)\s*'\s*)?(?:(\d+(?:\.\d+)?)\s*"\s*)?([NSEW])?/;
const SEPARATORS = /^[\s,;]+/;

function normalise(line: string): string {
  return line
    .toUpperCase()
    .replace(/[′’‘`´]/g, "'")
    .replace(/[″“”]/g, '"')
    .replace(/''/g, '"')
    .replace(/[º˚]/g, '°')
    .replace(/\t/g, ' ')
    .trim();
}

function readComponent(text: string): { component: Component; rest: string } | null {
  const match = COMPONENT.exec(text);
  if (!match || match[0].trim() === '') return null;
  const [whole, lead, deg, min, sec, trail] = match;
  if (lead && trail) return null;
  const degrees = Number(deg);
  const minutes = min === undefined ? 0 : Number(min);
  const seconds = sec === undefined ? 0 : Number(sec);
  if (minutes >= 60 || seconds >= 60) return null;
  if ((min !== undefined || sec !== undefined) && !Number.isInteger(degrees)) return null;
  const magnitude = Math.abs(degrees) + minutes / 60 + seconds / 3600;
  const hemisphere = (lead ?? trail ?? null) as Hemisphere | null;
  const negative = degrees < 0 || deg.startsWith('-') || hemisphere === 'S' || hemisphere === 'W';
  return { component: { value: negative ? -magnitude : magnitude, hemisphere }, rest: text.slice(whole.length) };
}

/** Parses one line into a point (or a warning). `lineNumber` is 1-based, for messages only. */
export function parseCoordinateLine(raw: string, lineNumber: number): ParsedLine {
  const text = normalise(raw);
  const first = readComponent(text);
  if (!first) return { line: lineNumber, point: null, warning: `Line ${lineNumber}: could not read a coordinate.` };
  const second = readComponent(first.rest.replace(SEPARATORS, ''));
  if (!second || second.rest.replace(SEPARATORS, '').length > 0) {
    return { line: lineNumber, point: null, warning: `Line ${lineNumber}: expected latitude and longitude.` };
  }
  const a = first.component;
  const b = second.component;
  const isLat = (c: Component) => c.hemisphere === 'N' || c.hemisphere === 'S';
  const isLon = (c: Component) => c.hemisphere === 'E' || c.hemisphere === 'W';
  if ((isLat(a) && isLat(b)) || (isLon(a) && isLon(b))) {
    return { line: lineNumber, point: null, warning: `Line ${lineNumber}: both values have the same hemisphere.` };
  }
  let lat = a.value;
  let lon = b.value;
  let warning: string | null = null;
  if (isLon(a) || isLat(b)) {
    // Hemisphere letters say the user typed longitude first.
    lat = b.value;
    lon = a.value;
  } else if (!a.hemisphere && !b.hemisphere && Math.abs(a.value) > 90 && Math.abs(b.value) <= 90) {
    lat = b.value;
    lon = a.value;
    warning = `Line ${lineNumber}: the first value is not a latitude, so the pair was read as longitude, latitude.`;
  }
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) {
    return { line: lineNumber, point: null, warning: `Line ${lineNumber}: latitude must be within ±90° and longitude within ±180°.` };
  }
  return { line: lineNumber, point: { lat, lon }, warning };
}

function samePoint(a: LatLon, b: LatLon): boolean {
  return Math.abs(a.lat - b.lat) < 1e-9 && Math.abs(a.lon - b.lon) < 1e-9;
}

/** Parses the whole text: 1 point → `point`, ≥ 3 → `polygon`, otherwise `invalid`. */
export function parseCoordinateText(text: string): CoordinateParse {
  if (text.length > MAX_COORDINATE_CHARS) {
    return { points: [], kind: 'invalid', warnings: [`The text is longer than ${MAX_COORDINATE_CHARS} characters.`] };
  }
  const lines = text.split(/\r?\n/);
  const filled = lines.map((line, index) => ({ line, index })).filter(({ line }) => line.trim() !== '');
  if (filled.length > MAX_COORDINATE_LINES) {
    return { points: [], kind: 'invalid', warnings: [`At most ${MAX_COORDINATE_LINES} lines are allowed.`] };
  }
  const warnings: string[] = [];
  const points: LatLon[] = [];
  for (const { line, index } of filled) {
    const parsed = parseCoordinateLine(line, index + 1);
    if (parsed.warning) warnings.push(parsed.warning);
    if (parsed.point) points.push(parsed.point);
  }
  // A ring typed with its first corner repeated at the end is still the same polygon.
  if (points.length > 1 && samePoint(points[0], points[points.length - 1])) points.pop();
  if (points.length === 0) return { points, kind: 'invalid', warnings: warnings.length ? warnings : ['No coordinates found.'] };
  if (points.length === 1) return { points, kind: 'point', warnings };
  if (points.length === 2) {
    return { points, kind: 'invalid', warnings: [...warnings, 'Two points cannot make an area: add at least one more corner, or keep one point and give the size.'] };
  }
  return { points, kind: 'polygon', warnings };
}

/** Closed GeoJSON ring `[lon, lat]` from corner points. */
export function ringFromPoints(points: LatLon[]): number[][] {
  const ring = points.map((p) => [p.lon, p.lat]);
  if (ring.length > 0) ring.push([...ring[0]]);
  return ring;
}

/** "13.2923° N, 77.5384° E" for display next to a pin (never logged or sent to an LLM). */
export function formatLatLon(point: LatLon, digits = 4): string {
  const lat = `${Math.abs(point.lat).toFixed(digits)}° ${point.lat >= 0 ? 'N' : 'S'}`;
  const lon = `${Math.abs(point.lon).toFixed(digits)}° ${point.lon >= 0 ? 'E' : 'W'}`;
  return `${lat}, ${lon}`;
}
