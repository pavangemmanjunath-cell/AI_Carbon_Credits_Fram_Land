/**
 * Turns one month of the space-time vegetation cube into flat map cells:
 * one square polygon per grid cell inside the plot, coloured with the
 * discrete NDVI palette. Row 0 is the northern edge of the grid bbox.
 */
import type { Feature, FeatureCollection, Polygon } from 'geojson';
import type { Cube } from '@/types/api';
import { ndviColor } from './ndvi';

export interface NdviCellProperties {
  row: number;
  col: number;
  value: number | null;
  color: string;
}

/** Fraction of each cell left as a gap so the grid stays readable over imagery. */
export const CELL_GAP = 0.04;

export function cubeSliceToGeoJson(cube: Cube, timeIndex: number, gap = CELL_GAP): FeatureCollection<Polygon, NdviCellProperties> {
  const { rows, cols, bbox } = cube.grid;
  const [west, south, east, north] = bbox;
  const dLon = (east - west) / cols;
  const dLat = (north - south) / rows;
  const t = Math.max(0, Math.min(timeIndex, cube.times.length - 1));
  const slice = cube.values[t] ?? [];
  const insetLon = (dLon * gap) / 2;
  const insetLat = (dLat * gap) / 2;
  const features: Feature<Polygon, NdviCellProperties>[] = [];
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      if (!cube.mask[r]?.[c]) continue;
      const value = slice[r]?.[c] ?? null;
      const w = west + c * dLon + insetLon;
      const e = west + (c + 1) * dLon - insetLon;
      const n = north - r * dLat - insetLat;
      const s = north - (r + 1) * dLat + insetLat;
      features.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] },
        properties: { row: r, col: c, value, color: ndviColor(value) },
      });
    }
  }
  return { type: 'FeatureCollection', features };
}

/** Distinct calendar years covered by the cube, ascending. */
export function cubeYears(cube: Cube | null | undefined): number[] {
  if (!cube) return [];
  return [...new Set(cube.times.map((m) => Number(m.slice(0, 4))))].filter(Number.isFinite).sort((a, b) => a - b);
}

/** Index of the latest month of `year` (or the last month when the year is not in the cube). */
export function timeIndexForYear(cube: Cube | null | undefined, year: number | null | undefined): number {
  if (!cube || cube.times.length === 0) return 0;
  let index = -1;
  cube.times.forEach((m, i) => {
    if (Number(m.slice(0, 4)) === year) index = i;
  });
  return index >= 0 ? index : cube.times.length - 1;
}

/** The year the slider should show: the stored one when the cube covers it, else the latest. */
export function activeYear(cube: Cube | null | undefined, stored: number | null | undefined, fallback = new Date().getFullYear()): number {
  const years = cubeYears(cube);
  if (stored != null && years.includes(stored)) return stored;
  return years[years.length - 1] ?? fallback;
}
