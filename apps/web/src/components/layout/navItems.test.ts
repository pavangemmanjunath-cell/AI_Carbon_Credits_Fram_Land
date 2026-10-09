import { describe, expect, it } from 'vitest';
import { activeNavKey, NAV_GROUPS, NAV_ITEMS } from './navItems';

describe('left navigation', () => {
  it('has the Trimble-style sections in order, without 4D analysis or the tree library', () => {
    expect(NAV_ITEMS.map((i) => [i.key, i.to])).toEqual([
      ['myLand', '/app'],
      ['data', '/app/data'],
      ['agents', '/app/agents'],
      ['treeAge', '/app/tree-age'],
      ['simulation', '/app/simulate'],
      ['reports', '/app/reports'],
      ['settings', '/app/settings'],
    ]);
    expect(NAV_GROUPS.map((g) => g.key)).toEqual(['land', 'insights', 'share', 'system']);
    expect(NAV_ITEMS.some((i) => i.to.includes('cube') || i.to.includes('species'))).toBe(false);
  });

  it('highlights the section that owns a detail page', () => {
    expect(activeNavKey('/app')).toBe('myLand');
    expect(activeNavKey('/app/')).toBe('myLand');
    expect(activeNavKey('/app/plots/PLT-1/results')).toBe('myLand');
    expect(activeNavKey('/app/data')).toBe('data');
    expect(activeNavKey('/app/plots')).toBe('data');
    expect(activeNavKey('/app/agents')).toBe('agents');
    expect(activeNavKey('/app/tree-age')).toBe('treeAge');
    expect(activeNavKey('/app/simulate')).toBe('simulation');
    expect(activeNavKey('/app/reports')).toBe('reports');
    expect(activeNavKey('/app/plots/PLT-1/report')).toBe('reports');
    expect(activeNavKey('/app/settings')).toBe('settings');
    expect(activeNavKey('/app/species')).toBe('settings');
    expect(activeNavKey('/')).toBeNull();
  });
});
