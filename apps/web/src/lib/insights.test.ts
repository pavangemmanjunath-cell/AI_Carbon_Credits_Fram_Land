import { describe, expect, it } from 'vitest';
import type { Analysis, TreeInventory } from '@/types/api';
import { landUseShares, latestInventory, soilInsight } from './insights';

const analysis = {
  plot_id: 'PLT-1',
  mode: 'demo',
  landcover: {
    dataset: 'ESA WorldCover',
    version: '2021 v200',
    resolution_m: 10,
    classes: [
      { code: 30, name: 'Grassland', share: 0.02, area_ha: 0.04 },
      { code: 40, name: 'Cropland', share: 0.68, area_ha: 1.45 },
      { code: 10, name: 'Tree cover', share: 0.27, area_ha: 0.58 },
      { code: 50, name: 'Built-up', share: 0.03, area_ha: 0.06 },
      { code: 99, name: 'Mystery', share: 0, area_ha: 0 },
    ],
  },
  soil: { soc_0_30cm_g_per_kg: 10.53 },
  climate: { zone: 'tropical_dry', zone_label: 'Tropical dry' },
  data_quality: { warnings: [] },
  generated_at: '2026-10-05T00:00:00Z',
} as unknown as Analysis;

describe('landUseShares', () => {
  it('returns the largest classes first with i18n keys', () => {
    const shares = landUseShares(analysis);
    expect(shares.map((s) => s.name)).toEqual(['Cropland', 'Tree cover', 'Built-up']);
    expect(shares[0].key).toBe('landcover.cropland');
    expect(shares[1].key).toBe('landcover.tree_cover');
  });

  it('honours the limit and ignores empty classes', () => {
    expect(landUseShares(analysis, 10)).toHaveLength(4);
    expect(landUseShares(analysis, 1)).toHaveLength(1);
  });

  it('is empty without an analysis', () => {
    expect(landUseShares(undefined)).toEqual([]);
  });
});

describe('soilInsight', () => {
  it('reads soil carbon and the climate zone', () => {
    expect(soilInsight(analysis)).toEqual({
      socGPerKg: 10.53,
      climateZone: 'tropical_dry',
      climateZoneLabel: 'Tropical dry',
    });
  });

  it('is null when nothing is known', () => {
    expect(soilInsight(null)).toBeNull();
    expect(
      soilInsight({
        plot_id: 'x',
        mode: 'demo',
        data_quality: { warnings: [] },
        generated_at: '',
      } as unknown as Analysis),
    ).toBeNull();
  });
});

describe('latestInventory', () => {
  const inv = (id: string, created: string) =>
    ({ inventory_id: id, created_at: created }) as unknown as TreeInventory;

  it('picks the most recently saved inventory, not the first in the list', () => {
    const items = [
      inv('INV-01', '2026-10-01T10:00:00Z'),
      inv('INV-02', '2026-10-05T10:00:00Z'),
      inv('INV-03', '2026-10-03T10:00:00Z'),
    ];
    expect(latestInventory(items)?.inventory_id).toBe('INV-02');
  });

  it('prefers the later list item when timestamps are equal', () => {
    const items = [inv('A', '2026-10-05T10:00:00Z'), inv('B', '2026-10-05T10:00:00Z')];
    expect(latestInventory(items)?.inventory_id).toBe('B');
  });

  it('handles empty input', () => {
    expect(latestInventory([])).toBeNull();
    expect(latestInventory(undefined)).toBeNull();
  });
});
