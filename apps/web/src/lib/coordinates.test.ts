import { describe, expect, it } from 'vitest';
import { formatLatLon, parseCoordinateLine, parseCoordinateText, ringFromPoints } from './coordinates';

describe('coordinate text parsing (offline mirror of /geometry/parse-coordinates)', () => {
  it('reads decimal degrees with comma, space or semicolon separators', () => {
    for (const line of ['13.2923, 77.5384', '13.2923 77.5384', '13.2923;77.5384', '  13.2923 ,  77.5384 ']) {
      expect(parseCoordinateLine(line, 1).point).toEqual({ lat: 13.2923, lon: 77.5384 });
    }
    expect(parseCoordinateLine('-33.86, -70.65', 1).point).toEqual({ lat: -33.86, lon: -70.65 });
  });

  it('reads hemisphere letters before or after the number', () => {
    expect(parseCoordinateLine('13.29N 77.53E', 1).point).toEqual({ lat: 13.29, lon: 77.53 });
    expect(parseCoordinateLine('N 13.29, E 77.53', 1).point).toEqual({ lat: 13.29, lon: 77.53 });
    expect(parseCoordinateLine('33.9s 18.4e', 1).point).toEqual({ lat: -33.9, lon: 18.4 });
  });

  it('reads degrees-minutes-seconds, including typographic primes', () => {
    const p = parseCoordinateLine('13°17\'32"N 77°32\'18"E', 1).point;
    expect(p?.lat).toBeCloseTo(13 + 17 / 60 + 32 / 3600, 9);
    expect(p?.lon).toBeCloseTo(77 + 32 / 60 + 18 / 3600, 9);
    const q = parseCoordinateLine('13° 17′ 32″ N, 77° 32′ 18″ E', 1).point;
    expect(q?.lat).toBeCloseTo(p?.lat ?? 0, 9);
    const dm = parseCoordinateLine("13°17.5'N 77°32.25'W", 1).point;
    expect(dm?.lat).toBeCloseTo(13 + 17.5 / 60, 9);
    expect(dm?.lon).toBeCloseTo(-(77 + 32.25 / 60), 9);
  });

  it('uses hemisphere letters to fix the order when longitude comes first', () => {
    expect(parseCoordinateLine('77.53E 13.29N', 1).point).toEqual({ lat: 13.29, lon: 77.53 });
  });

  it('swaps an obvious lon, lat pair (first value outside ±90) with a warning', () => {
    const parsed = parseCoordinateLine('-122.4194, 37.7749', 3);
    expect(parsed.point).toEqual({ lat: 37.7749, lon: -122.4194 });
    expect(parsed.warning).toMatch(/Line 3/);
    // 77.5 is a valid latitude, so an Indian lon, lat pair cannot be detected and is kept as typed
    expect(parseCoordinateLine('77.5384, 13.2923', 1)).toMatchObject({ point: { lat: 77.5384, lon: 13.2923 }, warning: null });
  });

  it('rejects junk, out-of-range values and impossible minutes', () => {
    expect(parseCoordinateLine('hello world', 1).point).toBeNull();
    expect(parseCoordinateLine('13.29', 1).point).toBeNull();
    expect(parseCoordinateLine('13.29 77.53 12', 1).point).toBeNull();
    expect(parseCoordinateLine('95, 200', 1).point).toBeNull();
    expect(parseCoordinateLine("13°75'N 77°32'E", 1).point).toBeNull();
    expect(parseCoordinateLine('13.29N 77.53N', 1).point).toBeNull();
    expect(parseCoordinateLine('13,2923 77,5384', 1).point).toBeNull();
  });

  it('classifies 1 point, 2 points and polygons; a repeated first corner is not a new corner', () => {
    expect(parseCoordinateText('13.29, 77.53').kind).toBe('point');
    const two = parseCoordinateText('13.29, 77.53\n13.30, 77.54');
    expect(two.kind).toBe('invalid');
    expect(two.warnings.join(' ')).toMatch(/Two points/);
    const ring = '13.290, 77.530\n13.290, 77.540\n13.300, 77.540\n13.290, 77.530';
    expect(parseCoordinateText(ring).kind).toBe('polygon');
    expect(parseCoordinateText(ring).points).toHaveLength(3);
    expect(parseCoordinateText('\n\n').kind).toBe('invalid');
  });

  it('keeps good lines and reports bad ones by line number', () => {
    const parsed = parseCoordinateText('13.29, 77.53\nnot a point\n13.30, 77.54\n13.30, 77.53');
    expect(parsed.kind).toBe('polygon');
    expect(parsed.points).toHaveLength(3);
    expect(parsed.warnings).toEqual([expect.stringMatching(/^Line 2:/)]);
  });

  it('enforces the 20 000 character limit', () => {
    expect(parseCoordinateText('1'.repeat(20_001)).kind).toBe('invalid');
  });

  it('closes rings and formats a point for display', () => {
    expect(ringFromPoints([{ lat: 1, lon: 2 }, { lat: 3, lon: 4 }, { lat: 5, lon: 6 }])).toEqual([[2, 1], [4, 3], [6, 5], [2, 1]]);
    expect(formatLatLon({ lat: -13.29231, lon: 77.53844 })).toBe('13.2923° S, 77.5384° E');
  });
});
