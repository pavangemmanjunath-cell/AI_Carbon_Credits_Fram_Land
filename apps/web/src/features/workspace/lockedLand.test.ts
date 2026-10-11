import { describe, expect, it } from 'vitest';
import type { PolygonGeometry, Species } from '@/types/api';
import { corners, cornersText, simulateLink, treesThatFit } from './lockedLand';

const square: PolygonGeometry = {
  type: 'Polygon',
  coordinates: [
    [
      [77.59, 12.97],
      [77.591, 12.97],
      [77.591, 12.971],
      [77.59, 12.971],
      [77.59, 12.97],
    ],
  ],
};
const mango = {
  id: 'mango',
  reference_density_per_ha: {
    value: 150,
    source: '8 m × 8 m orchard spacing',
    verification_status: 'assumption',
  },
} as unknown as Species;

describe('locked land', () => {
  it('lists the corners as lat, lon without the closing point', () => {
    const list = corners(square);
    expect(list).toHaveLength(4);
    expect(list[1]).toEqual({ lat: 12.97, lon: 77.591 });
    expect(cornersText(list).split('\n')[0]).toBe('12.970000, 77.590000');
  });

  it('fits trees from the configured reference density, with its source', () => {
    const fit = treesThatFit(2.13, mango);
    expect(fit.trees).toBe(319); // floor(2.13 × 150)
    expect(fit.spacingM).toBe(8.2); // √(10 000 / 150)
    expect(fit.status).toBe('assumption');
  });

  it('never guesses a count when the species has no density', () => {
    expect(treesThatFit(2, { id: 'x' } as unknown as Species).trees).toBeNull();
    expect(treesThatFit(0, mango).trees).toBeNull();
  });

  it('links to the simulation with the plot id and no coordinates', () => {
    const link = simulateLink(
      { plot_id: 'PLT-1', country: 'IN', area_hectares: 2.13 },
      'mango',
      319,
      2026,
    );
    expect(link).toContain('plot=PLT-1');
    expect(link).toContain('trees=319');
    expect(link).not.toMatch(/77\.59|12\.97|[?&](lat|lon)=/);
  });
});
