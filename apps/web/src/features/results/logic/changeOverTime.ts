/**
 * "Change over time" card: the cube's monthly mean NDVI (`stats_per_time`)
 * as a plain line series. Values come from the API; nothing is recomputed.
 */
import type { Cube } from '@/types/api';

export interface MonthlyMeanPoint {
  month: string;
  mean: number;
}

export function monthlyMeanSeries(cube: Cube | null | undefined): MonthlyMeanPoint[] {
  if (!cube) return [];
  return cube.stats_per_time
    .filter((s) => typeof s.mean === 'number' && Number.isFinite(s.mean))
    .map((s) => ({ month: s.time, mean: s.mean }))
    .sort((a, b) => a.month.localeCompare(b.month));
}

/** Y-axis domain rounded outwards to 0.1 and kept inside NDVI's −1…1 range. */
export function ndviDomain(points: MonthlyMeanPoint[]): [number, number] {
  if (points.length === 0) return [0, 1];
  const values = points.map((p) => p.mean);
  const low = Math.max(-1, Math.floor(Math.min(...values) * 10) / 10);
  let high = Math.min(1, Math.ceil(Math.max(...values) * 10) / 10);
  if (high <= low) high = Math.min(1, low + 0.1);
  return [Number(low.toFixed(1)), Number(high.toFixed(1))];
}

/** Evenly spaced y ticks (0.1 apart, or 0.2 when that would be more than six ticks). */
export function ndviTicks([low, high]: [number, number]): number[] {
  // Work in tenths so floating-point steps cannot drift (and −0 never appears).
  const from = Math.round(low * 10);
  const to = Math.round(high * 10);
  const step = to - from > 6 ? 2 : 1;
  const ticks: number[] = [];
  for (let v = from; v <= to; v += step) ticks.push(v / 10 + 0);
  return ticks;
}
