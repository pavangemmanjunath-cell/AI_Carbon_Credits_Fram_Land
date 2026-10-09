/**
 * Metric scale bar maths. MapLibre renders a 512 px world at zoom 0
 * (Web Mercator), so metres per pixel = equator length · cos(lat) / (512 · 2^zoom).
 */

const EQUATOR_M = 40_075_016.686;

export function metresPerPixel(latitude: number, zoom: number, tileSize = 512): number {
  const lat = Math.max(-85.0511, Math.min(85.0511, latitude));
  return (EQUATOR_M * Math.cos((lat * Math.PI) / 180)) / (tileSize * 2 ** zoom);
}

/** Largest "nice" distance (1, 2 or 5 × 10ⁿ) not exceeding `maxMetres`. */
export function niceDistance(maxMetres: number): number {
  if (!(maxMetres > 0) || !Number.isFinite(maxMetres)) return 0;
  const base = 10 ** Math.floor(Math.log10(maxMetres));
  for (const step of [5, 2, 1]) {
    if (step * base <= maxMetres + 1e-9) return step * base;
  }
  return base;
}

export interface ScaleBarSpec {
  /** Bar width in CSS pixels. */
  widthPx: number;
  metres: number;
  /** "500 m", "2 km" — units are never translated. */
  label: string;
}

export function scaleBarSpec(metresPerPx: number, maxWidthPx = 100): ScaleBarSpec {
  const metres = niceDistance(metresPerPx * maxWidthPx);
  if (metres <= 0 || !(metresPerPx > 0)) return { widthPx: 0, metres: 0, label: '' };
  const label = metres >= 1000 ? `${trim(metres / 1000)} km` : `${trim(metres)} m`;
  return { widthPx: Math.round(metres / metresPerPx), metres, label };
}

function trim(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(3)));
}
