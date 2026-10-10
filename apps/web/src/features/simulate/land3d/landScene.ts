/**
 * Geometry and growth for the 3D land view. Pure functions, no three.js, so
 * they are unit-tested.
 *
 * Where every number comes from:
 * - plot shape: the saved boundary, projected to metres here in the browser
 *   (it is never sent anywhere); without one, a square of the plot's area;
 * - tree positions: an orchard grid inside the boundary, spaced from the
 *   entered tree count and area;
 * - tree height: `typical_height_m_at_maturity` × the page's growth factor
 *   (config/species/species.yaml; verification status shown in the UI);
 * - crown width: the reference spacing √(10 000 / reference_density_per_ha)
 *   × the growth factor (the canopy closes at the reference density);
 * - carbon: the simulation engine's yearly series — never computed here
 *   beyond dividing the engine's totals by the tree count.
 */
import type { AnnualPoint, PolygonGeometry, Species } from '@/types/api';

export type Point = [number, number];

const EARTH_RADIUS_M = 6_371_008.8;
/** Above this many trees, one drawn tree stands for several (keeps the scene fast). */
export const MAX_DRAWN_TREES = 1200;

/** Equirectangular projection around the ring's centre — accurate to well under 1 % for farm plots. */
export function projectRing(geometry: PolygonGeometry): Point[] {
  const ring = geometry.coordinates[0] ?? [];
  const open =
    ring.length > 1 &&
    ring[0][0] === ring[ring.length - 1][0] &&
    ring[0][1] === ring[ring.length - 1][1]
      ? ring.slice(0, -1)
      : ring;
  if (open.length < 3) return [];
  const lon0 = open.reduce((s, p) => s + p[0], 0) / open.length;
  const lat0 = open.reduce((s, p) => s + p[1], 0) / open.length;
  const k = Math.PI / 180;
  const cos = Math.cos(lat0 * k);
  return open.map(([lon, lat]) => [
    (lon - lon0) * k * EARTH_RADIUS_M * cos,
    (lat - lat0) * k * EARTH_RADIUS_M,
  ]);
}

export function squareRing(areaHectares: number): Point[] {
  const half = Math.sqrt(Math.max(areaHectares, 0.0001) * 10_000) / 2;
  return [
    [-half, -half],
    [half, -half],
    [half, half],
    [-half, half],
  ];
}

export function ringArea(ring: Point[]): number {
  let sum = 0;
  for (let i = 0; i < ring.length; i += 1) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[(i + 1) % ring.length];
    sum += x1 * y2 - x2 * y1;
  }
  return Math.abs(sum) / 2;
}

export function pointInRing([x, y]: Point, ring: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export function bounds(ring: Point[]) {
  const xs = ring.map((p) => p[0]);
  const ys = ring.map((p) => p[1]);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

export interface TreeLayout {
  positions: Point[];
  /** Real trees per drawn tree (1 unless the stand is very large). */
  treesPerDrawn: number;
  /** Grid spacing in metres. */
  spacing: number;
}

/**
 * An offset orchard grid inside the ring. Spacing starts at √(area / count)
 * and shrinks until enough grid points fall inside an irregular boundary.
 */
export function layoutTrees(
  ring: Point[],
  treeCount: number,
  maxDrawn = MAX_DRAWN_TREES,
): TreeLayout {
  const count = Math.max(0, Math.round(treeCount));
  const drawn = Math.min(count, maxDrawn);
  if (drawn === 0 || ring.length < 3) return { positions: [], treesPerDrawn: 1, spacing: 0 };
  const area = ringArea(ring);
  const box = bounds(ring);
  let spacing = Math.sqrt(area / drawn);
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const points: Point[] = [];
    let row = 0;
    for (let y = box.minY + spacing / 2; y < box.maxY; y += spacing * 0.866, row += 1) {
      const offset = row % 2 ? spacing / 2 : 0;
      for (let x = box.minX + spacing / 2 + offset; x < box.maxX; x += spacing) {
        if (pointInRing([x, y], ring)) points.push([x, y]);
      }
    }
    if (points.length >= drawn) {
      // Spread the chosen points over the whole grid instead of filling rows from one side.
      const step = points.length / drawn;
      const positions = Array.from({ length: drawn }, (_, i) => points[Math.floor(i * step)]);
      return { positions, treesPerDrawn: count / drawn, spacing };
    }
    spacing *= 0.9;
  }
  return { positions: [], treesPerDrawn: 1, spacing: 0 };
}

export interface TreeSize {
  /** Metres from config × growth; null when the species has no configured value (never guessed). */
  heightM: number | null;
  crownDiameterM: number | null;
  /** What the scene draws: the metres above, or — without config — a neutral shape scaled to the grid. */
  drawHeight: number;
  drawCrown: number;
  /** Verification status of the config values, for the UI. */
  heightStatus: string | null;
  densityStatus: string | null;
}

/** Size from species config × growth factor (0–1). */
export function treeSize(
  species: Species | undefined,
  growth: number,
  gridSpacing: number,
): TreeSize {
  const g = Math.max(0, Math.min(1, growth));
  const matureHeight = species?.typical_height_m_at_maturity?.value;
  const density = species?.reference_density_per_ha?.value;
  const heightM = typeof matureHeight === 'number' ? Number((matureHeight * g).toFixed(1)) : null;
  const crownDiameterM =
    typeof density === 'number' && density > 0
      ? Number((Math.sqrt(10_000 / density) * g).toFixed(1))
      : null;
  const neutral = Math.max(gridSpacing, 1) * g;
  return {
    heightM,
    crownDiameterM,
    drawHeight: heightM ?? neutral * 1.2,
    drawCrown: crownDiameterM ?? neutral * 0.8,
    heightStatus: species?.typical_height_m_at_maturity?.verification_status ?? null,
    densityStatus: species?.reference_density_per_ha?.verification_status ?? null,
  };
}

export interface YearCarbon {
  /** Engine's estimated removal in that year (stand), tCO₂e/yr. */
  annual: { low: number; central: number; high: number };
  /** Engine's cumulative removal since planting (stand), tCO₂e. */
  cumulative: { low: number; central: number; high: number };
  /** The stand values divided by the tree count. */
  perTreeAnnualKg: number;
  perTreeCumulativeKg: number;
}

/** The engine's series point for a calendar year (clamped to the series). */
export function carbonInYear(
  series: AnnualPoint[],
  year: number,
  treeCount: number,
): YearCarbon | null {
  if (!series.length) return null;
  const point =
    series.find((p) => p.year === year) ??
    (year < series[0].year ? series[0] : series[series.length - 1]);
  const trees = Math.max(1, treeCount);
  return {
    annual: { low: point.low, central: point.central, high: point.high },
    cumulative: { low: point.cum_low, central: point.cum_central, high: point.cum_high },
    perTreeAnnualKg: (point.central * 1000) / trees,
    perTreeCumulativeKg: (point.cum_central * 1000) / trees,
  };
}

/** Steps a recognised programme requires before any credit exists (generic ARR project cycle). */
export const CREDIT_STEPS = [
  'design',
  'validation',
  'monitoring',
  'verification',
  'issuance',
] as const;
export type CreditStep = (typeof CREDIT_STEPS)[number];
