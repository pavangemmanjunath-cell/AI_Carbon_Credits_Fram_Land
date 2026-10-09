import { describe, expect, it } from 'vitest';
import { metresPerPixel, niceDistance, scaleBarSpec } from './scale';

describe('scale bar', () => {
  it('picks 1, 2 or 5 × 10ⁿ not above the maximum', () => {
    expect(niceDistance(1)).toBe(1);
    expect(niceDistance(1.9)).toBe(1);
    expect(niceDistance(2)).toBe(2);
    expect(niceDistance(4.99)).toBe(2);
    expect(niceDistance(5)).toBe(5);
    expect(niceDistance(99)).toBe(50);
    expect(niceDistance(130)).toBe(100);
    expect(niceDistance(2600)).toBe(2000);
    expect(niceDistance(0.37)).toBeCloseTo(0.2, 9);
    expect(niceDistance(0)).toBe(0);
    expect(niceDistance(Number.NaN)).toBe(0);
  });

  it('computes Web Mercator metres per pixel for 512 px tiles', () => {
    expect(metresPerPixel(0, 0)).toBeCloseTo(78_271.517, 2);
    expect(metresPerPixel(0, 1)).toBeCloseTo(39_135.758, 2);
    expect(metresPerPixel(60, 0)).toBeCloseTo(78_271.517 / 2, 1);
  });

  it('labels metres and kilometres and sizes the bar in pixels', () => {
    const m = scaleBarSpec(1.3, 100); // 130 m max → 100 m
    expect(m).toEqual({ widthPx: 77, metres: 100, label: '100 m' });
    const km = scaleBarSpec(26, 100); // 2.6 km max → 2 km
    expect(km.label).toBe('2 km');
    expect(km.widthPx).toBe(77);
    expect(scaleBarSpec(6, 100).label).toBe('500 m');
    expect(scaleBarSpec(0.004, 100).label).toBe('0.2 m');
    expect(scaleBarSpec(0, 100).widthPx).toBe(0);
  });

  it('never makes the bar wider than allowed', () => {
    for (const zoom of [3, 8, 12, 15, 18, 20]) {
      const spec = scaleBarSpec(metresPerPixel(13.29, zoom), 96);
      expect(spec.widthPx).toBeLessThanOrEqual(96);
      expect(spec.widthPx).toBeGreaterThan(96 / 5 - 1);
    }
  });
});
