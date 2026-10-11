import { describe, expect, it } from 'vitest';
import { makeCube } from '@/test/fixtures';
import { activeYear, cubeSliceToGeoJson, cubeYears, timeIndexForYear } from './ndviGrid';
import { NDVI_NULL_HEX, ndviColor } from './ndvi';

describe('NDVI cube cells as GeoJSON', () => {
  const cube = makeCube(); // 3 × 3, cell (0,0) outside the plot, bbox [77.53, 13.29, 77.531, 13.291]

  it('builds one square polygon per cell inside the plot mask', () => {
    const fc = cubeSliceToGeoJson(cube, 0);
    expect(fc.features).toHaveLength(8);
    expect(fc.features.some((f) => f.properties.row === 0 && f.properties.col === 0)).toBe(false);
    for (const f of fc.features) {
      const ring = f.geometry.coordinates[0];
      expect(ring).toHaveLength(5);
      expect(ring[0]).toEqual(ring[4]);
    }
  });

  it('puts row 0 at the north edge and columns west → east', () => {
    const fc = cubeSliceToGeoJson(cube, 0, 0);
    const cell = (r: number, c: number) =>
      fc.features.find((f) => f.properties.row === r && f.properties.col === c)!;
    const north = Math.max(...cell(0, 1).geometry.coordinates[0].map((p) => p[1]));
    expect(north).toBeCloseTo(13.291, 9);
    const south = Math.min(...cell(2, 1).geometry.coordinates[0].map((p) => p[1]));
    expect(south).toBeCloseTo(13.29, 9);
    const west = Math.min(...cell(1, 0).geometry.coordinates[0].map((p) => p[0]));
    expect(west).toBeCloseTo(77.53, 9);
    const east = Math.max(...cell(1, 2).geometry.coordinates[0].map((p) => p[0]));
    expect(east).toBeCloseTo(77.531, 9);
  });

  it('colours cells with the discrete NDVI palette and greys null cells', () => {
    const withNull = {
      ...cube,
      values: cube.values.map((slice, t) =>
        t === 0 ? slice.map((row, r) => row.map((v, c) => (r === 1 && c === 1 ? null : v))) : slice,
      ),
    };
    const fc = cubeSliceToGeoJson(withNull, 0);
    for (const f of fc.features) expect(f.properties.color).toBe(ndviColor(f.properties.value));
    expect(
      fc.features.find((f) => f.properties.row === 1 && f.properties.col === 1)?.properties.color,
    ).toBe(NDVI_NULL_HEX);
  });

  it('follows the year slider: latest month of the chosen year', () => {
    expect(cubeYears(cube)).toEqual([2023, 2024, 2025, 2026]);
    expect(cube.times[timeIndexForYear(cube, 2024)]).toBe('2024-12');
    expect(timeIndexForYear(cube, 1999)).toBe(cube.times.length - 1);
    expect(timeIndexForYear(undefined, 2024)).toBe(0);
    const slices = [
      cubeSliceToGeoJson(cube, timeIndexForYear(cube, 2023)),
      cubeSliceToGeoJson(cube, timeIndexForYear(cube, 2026)),
    ];
    expect(slices[0].features[0].properties.value).not.toBe(slices[1].features[0].properties.value);
  });

  it('chooses the stored year when the cube has it, else the latest', () => {
    expect(activeYear(cube, 2024)).toBe(2024);
    expect(activeYear(cube, 2010)).toBe(2026);
    expect(activeYear(null, null, 2030)).toBe(2030);
  });

  it('clamps out-of-range time indexes', () => {
    expect(cubeSliceToGeoJson(cube, 999).features[0].properties.value).toBe(
      cubeSliceToGeoJson(cube, cube.times.length - 1).features[0].properties.value,
    );
  });
});
