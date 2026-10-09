import { describe, expect, it } from 'vitest';
import { GeometryInputError, lineLengthMetres, offlineFromLine, offlineFromPoint, offlineParseCoordinates, stripAroundLine, suggestedTreeCount } from './geometryOffline';
import { areaHectares, validatePolygon } from './geo';
import { HECTARES_PER_ACRE } from './format';

describe('offline geometry helpers', () => {
  it('builds a square of the requested area around the pin (within 0.5 %)', () => {
    const result = offlineFromPoint({ lat: 13.2923, lon: 77.5384, area: { value: 5, unit: 'ac' }, shape: 'square' });
    expect(result.area_hectares).toBeCloseTo(5 * HECTARES_PER_ACRE, 2);
    expect(Math.abs(result.area_acres - 5) / 5).toBeLessThan(0.005);
    expect(result.boundary_quality).toBe('approximate');
    expect(result.method).toMatch(/^offline/);
    expect(result.provenance?.notes?.[0]).toMatch(/offline/i);
    expect(validatePolygon(result.geometry).ok).toBe(true);
    const ring = result.geometry.coordinates[0];
    expect(ring[0]).toEqual(ring[ring.length - 1]);
  });

  it('supports hectares, square metres and circles', () => {
    expect(offlineFromPoint({ lat: 50, lon: 10, area: { value: 2, unit: 'ha' } }).area_hectares).toBeCloseTo(2, 2);
    expect(offlineFromPoint({ lat: 50, lon: 10, area: { value: 5000, unit: 'm2' } }).area_hectares).toBeCloseTo(0.5, 2);
    const circle = offlineFromPoint({ lat: 37.6, lon: -4.8, area: { value: 3, unit: 'ha' }, shape: 'circle' });
    expect(Math.abs(circle.area_hectares - 3) / 3).toBeLessThan(0.005);
    expect(circle.geometry.coordinates[0]).toHaveLength(65);
  });

  it('rejects empty and oversized areas', () => {
    expect(() => offlineFromPoint({ lat: 0, lon: 0, area: { value: 0, unit: 'ha' } })).toThrow(GeometryInputError);
    expect(() => offlineFromPoint({ lat: 0, lon: 0, area: { value: 10_001, unit: 'ha' } })).toThrow(/at most/);
  });

  it('suggests trees = floor(length / spacing) + 1', () => {
    expect(suggestedTreeCount(270.6, 5)).toBe(55);
    expect(suggestedTreeCount(100, 5)).toBe(21);
    expect(suggestedTreeCount(0, 5)).toBe(0);
    expect(suggestedTreeCount(10, 0)).toBe(0);
  });

  it('turns a tree line into a strip of the given width', () => {
    const line = { type: 'LineString' as const, coordinates: [[77.537, 13.291], [77.5395, 13.2912]] };
    const result = offlineFromLine({ line, width_m: 4, spacing_m: 5 });
    const length = lineLengthMetres(line.coordinates);
    expect(result.length_m).toBeCloseTo(length, 0);
    expect(result.suggested_tree_count).toBe(Math.floor(length / 5) + 1);
    // a straight strip is length × width
    expect(result.area_hectares).toBeCloseTo((length * 4) / 10_000, 3);
    expect(result.boundary_quality).toBe('approximate');
  });

  it('keeps a bent line strip valid and about length × width', () => {
    const coords = [[77.537, 13.291], [77.538, 13.291], [77.538, 13.292]];
    const strip = stripAroundLine(coords, 6);
    expect(validatePolygon(strip).ok).toBe(true);
    const expected = (lineLengthMetres(coords) * 6) / 10_000;
    expect(Math.abs(areaHectares(strip) - expected) / expected).toBeLessThan(0.05);
  });

  it('validates tree-line settings like the API', () => {
    const line = { type: 'LineString' as const, coordinates: [[0, 0], [0.001, 0]] };
    expect(() => offlineFromLine({ line, width_m: 0.5, spacing_m: 5 })).toThrow(/width/i);
    expect(() => offlineFromLine({ line, width_m: 4, spacing_m: 60 })).toThrow(/Spacing/);
    expect(() => offlineFromLine({ line: { type: 'LineString', coordinates: [[0, 0]] }, width_m: 4, spacing_m: 5 })).toThrow(GeometryInputError);
  });

  it('parses coordinates into a point or a validated polygon', () => {
    const point = offlineParseCoordinates({ text: '13.29, 77.53' });
    expect(point.kind).toBe('point');
    expect(point.geometry).toEqual({ type: 'Point', coordinates: [77.53, 13.29] });
    const polygon = offlineParseCoordinates({ text: '13.290, 77.530\n13.290, 77.534\n13.294, 77.534\n13.294, 77.530' });
    expect(polygon.kind).toBe('polygon');
    expect(polygon.area_hectares).toBeGreaterThan(18);
    const tiny = offlineParseCoordinates({ text: '13.29, 77.53\n13.29, 77.53001\n13.29001, 77.53001' });
    expect(tiny.kind).toBe('invalid');
    expect(tiny.warnings.join(' ')).toMatch(/too small/);
  });
});
