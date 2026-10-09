import { describe, expect, it } from 'vitest';
import { makeCube } from '@/test/fixtures';
import { monthlyMeanSeries, ndviDomain, ndviTicks } from './changeOverTime';

describe('Change over time card', () => {
  it('uses the cube monthly means in time order', () => {
    const cube = makeCube();
    const shuffled = { ...cube, stats_per_time: [...cube.stats_per_time].reverse().map((s, i) => ({ ...s, mean: 0.4 + i / 100 })) };
    const series = monthlyMeanSeries(shuffled);
    expect(series).toHaveLength(36);
    expect(series[0].month).toBe(cube.times[0]);
    expect(series[35].month).toBe(cube.times[35]);
  });

  it('skips months without a valid mean and handles a missing cube', () => {
    const cube = makeCube();
    const gaps = { ...cube, stats_per_time: cube.stats_per_time.map((s, i) => (i === 3 ? { ...s, mean: Number.NaN } : s)) };
    expect(monthlyMeanSeries(gaps)).toHaveLength(35);
    expect(monthlyMeanSeries(undefined)).toEqual([]);
  });

  it('rounds the y-axis outwards to 0.1 inside −1…1', () => {
    expect(ndviDomain([{ month: 'a', mean: 0.43 }, { month: 'b', mean: 0.78 }])).toEqual([0.4, 0.8]);
    expect(ndviDomain([{ month: 'a', mean: 0.5 }])).toEqual([0.5, 0.6]);
    expect(ndviDomain([{ month: 'a', mean: -1 }, { month: 'b', mean: 1 }])).toEqual([-1, 1]);
    expect(ndviDomain([])).toEqual([0, 1]);
  });

  it('spaces y ticks evenly', () => {
    expect(ndviTicks([0.2, 0.7])).toEqual([0.2, 0.3, 0.4, 0.5, 0.6, 0.7]);
    expect(ndviTicks([-1, 1])).toEqual([-1, -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1]);
    expect(ndviTicks([0.5, 0.6])).toEqual([0.5, 0.6]);
  });
});
