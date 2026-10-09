import { describe, expect, it } from 'vitest';
import { DEFAULT_SIMULATION, growthFactor, parseSimulationParams, shareUrl, toSearchParams, toSimulateBody } from './simulationParams';
import { MAX_GLYPHS, standLayout } from './standIllustration';

describe('simulationParams', () => {
  it('parses and clamps URL parameters', () => {
    const state = parseSimulationParams(new URLSearchParams('country=in&species=teak&trees=99999&year=1800&horizon=15&area=0'));
    expect(state.country).toBe('IN');
    expect(state.species).toBe('teak');
    expect(state.trees).toBe(2000);
    expect(state.year).toBe(1900);
    expect(state.horizon).toBe(20);
    expect(state.area).toBe(0.01);
  });

  it('falls back to defaults for missing or invalid values', () => {
    const state = parseSimulationParams(new URLSearchParams('trees=abc'));
    expect(state).toEqual({ ...DEFAULT_SIMULATION, trees: DEFAULT_SIMULATION.trees });
  });

  it('round-trips through search params and never includes coordinates', () => {
    const params = toSearchParams({ ...DEFAULT_SIMULATION, plot: 'PLT-X' });
    const again = parseSimulationParams(params);
    expect(again.plot).toBe('PLT-X');
    expect(again.trees).toBe(DEFAULT_SIMULATION.trees);
    expect(shareUrl(DEFAULT_SIMULATION, 'https://atlas.example')).not.toMatch(/[?&](lat|lon|latitude|longitude)=/);
  });

  it('builds the API body with an explicit survival rate', () => {
    const body = toSimulateBody(DEFAULT_SIMULATION);
    expect(body.survival_rate).toBe(0.85);
    expect(body.horizon_years).toBe(30);
  });

  it('ramps canopy growth from a seedling to maturity', () => {
    expect(growthFactor(0, 8)).toBeCloseTo(0.12);
    expect(growthFactor(4, 8)).toBeCloseTo(0.56);
    expect(growthFactor(20, 8)).toBe(1);
  });
});

describe('standIllustration', () => {
  it('draws every tree when there are few, in up to five rows', () => {
    const layout = standLayout(12, 1);
    expect(layout.glyphs).toHaveLength(12);
    expect(layout.treesPerGlyph).toBe(1);
    expect(new Set(layout.glyphs.map((g) => g.row)).size).toBeLessThanOrEqual(5);
  });

  it('caps the glyphs and says how many trees one glyph stands for', () => {
    const layout = standLayout(420, 0.5);
    expect(layout.glyphs).toHaveLength(MAX_GLYPHS);
    expect(layout.treesPerGlyph).toBe(7);
  });

  it('scales glyphs with growth and keeps them inside the picture', () => {
    const young = standLayout(30, 0.12);
    const mature = standLayout(30, 1);
    const maxScale = (l: typeof young) => Math.max(...l.glyphs.map((g) => g.scale));
    expect(maxScale(mature)).toBeGreaterThan(maxScale(young));
    expect(maxScale(mature)).toBeLessThanOrEqual(1);
    for (const g of mature.glyphs) {
      expect(g.x).toBeGreaterThan(0);
      expect(g.x).toBeLessThan(mature.width);
      expect(g.y).toBeGreaterThan(mature.horizon);
      expect(g.y).toBeLessThanOrEqual(mature.height);
    }
    // back rows are drawn smaller than the front row
    const back = mature.glyphs.filter((g) => g.row === 0)[0];
    const front = mature.glyphs.filter((g) => g.row === Math.max(...mature.glyphs.map((x) => x.row)))[0];
    expect(back.scale).toBeLessThan(front.scale);
  });

  it('draws nothing for zero trees', () => {
    expect(standLayout(0, 1).glyphs).toHaveLength(0);
  });
});
