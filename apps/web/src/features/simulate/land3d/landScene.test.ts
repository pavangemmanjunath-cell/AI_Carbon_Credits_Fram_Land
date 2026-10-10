import { describe, expect, it } from 'vitest';
import type { AnnualPoint, Species } from '@/types/api';
import {
  carbonInYear,
  layoutTrees,
  pointInRing,
  projectRing,
  ringArea,
  squareRing,
  treeSize,
} from './landScene';

const mango = {
  id: 'mango',
  typical_height_m_at_maturity: {
    value: 10,
    source: 'project assumption v0.1',
    verification_status: 'assumption',
  },
  reference_density_per_ha: {
    value: 156.25,
    source: '8 m × 8 m',
    verification_status: 'assumption',
  },
} as unknown as Species;

describe('projectRing', () => {
  it('turns a lon/lat square of about 100 m into metres around its centre', () => {
    // 0.0009° of latitude ≈ 100 m; at 12.97° N a degree of longitude is cos(12.97°) shorter.
    const dLon = 0.0009 / Math.cos((12.97 * Math.PI) / 180);
    const ring = projectRing({
      type: 'Polygon',
      coordinates: [
        [
          [77.59, 12.97],
          [77.59 + dLon, 12.97],
          [77.59 + dLon, 12.9709],
          [77.59, 12.9709],
          [77.59, 12.97],
        ],
      ],
    });
    expect(ring).toHaveLength(4); // the closing point is dropped
    expect(ringArea(ring) / 10_000).toBeCloseTo(1.0, 1); // ≈ 1 ha
    const xs = ring.map((p) => p[0]);
    expect(Math.min(...xs) + Math.max(...xs)).toBeCloseTo(0, 6); // centred
  });
});

describe('layoutTrees', () => {
  it('places exactly the requested number of trees, all inside the boundary', () => {
    const ring = squareRing(2.13);
    const layout = layoutTrees(ring, 420);
    expect(layout.positions).toHaveLength(420);
    expect(layout.treesPerDrawn).toBe(1);
    expect(layout.positions.every((p) => pointInRing(p, ring))).toBe(true);
    expect(layout.spacing).toBeGreaterThan(5); // ~7 m for 420 trees on 2.13 ha
  });

  it('fits trees inside an L-shaped (concave) boundary too', () => {
    const ring: [number, number][] = [
      [0, 0],
      [100, 0],
      [100, 40],
      [40, 40],
      [40, 100],
      [0, 100],
    ];
    const layout = layoutTrees(ring, 200);
    expect(layout.positions).toHaveLength(200);
    expect(layout.positions.every((p) => pointInRing(p, ring))).toBe(true);
  });

  it('draws one tree for several when the stand is very large', () => {
    const layout = layoutTrees(squareRing(50), 5000, 1000);
    expect(layout.positions).toHaveLength(1000);
    expect(layout.treesPerDrawn).toBe(5);
  });

  it('draws nothing for zero trees', () => {
    expect(layoutTrees(squareRing(1), 0).positions).toHaveLength(0);
  });
});

describe('treeSize', () => {
  it('scales the configured mature height and reference spacing by growth', () => {
    const size = treeSize(mango, 0.5, 7);
    expect(size.heightM).toBe(5); // 10 m × 0.5
    expect(size.crownDiameterM).toBe(4); // √(10 000 / 156.25) = 8 m × 0.5
    expect(size.heightStatus).toBe('assumption');
  });

  it('never guesses metres when the species has no configured size', () => {
    const size = treeSize({ id: 'x' } as unknown as Species, 1, 6);
    expect(size.heightM).toBeNull();
    expect(size.crownDiameterM).toBeNull();
    expect(size.drawHeight).toBeGreaterThan(0); // a neutral shape is still drawn
  });
});

describe('carbonInYear', () => {
  const series: AnnualPoint[] = [
    { year: 2023, age: 0, low: 0, central: 0, high: 0, cum_low: 0, cum_central: 0, cum_high: 0 },
    { year: 2024, age: 1, low: 1, central: 2, high: 3, cum_low: 1, cum_central: 2, cum_high: 3 },
  ];
  it('reads the engine series and divides by the tree count for one tree', () => {
    const c = carbonInYear(series, 2024, 400);
    expect(c?.annual.central).toBe(2);
    expect(c?.perTreeAnnualKg).toBe(5); // 2 t × 1000 / 400
  });
  it('clamps years outside the series', () => {
    expect(carbonInYear(series, 2050, 1)?.cumulative.central).toBe(2);
    expect(carbonInYear(series, 1990, 1)?.cumulative.central).toBe(0);
    expect(carbonInYear([], 2024, 1)).toBeNull();
  });
});
