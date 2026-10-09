import { describe, expect, it } from 'vitest';
import {
  ADD_LAND_OPTIONS,
  areaToHectares,
  defaultInputAreaUnit,
  fromLineBody,
  fromPointBody,
  hectaresToUnit,
  isApproximate,
  isToolActive,
  LAND_TOOL_KEYS,
  nextPlotName,
  plotRequestFor,
  toApiAreaUnit,
  validatePinSize,
  validateTreeLineSettings,
} from './landInput';

const square = { type: 'Polygon' as const, coordinates: [[[0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01], [0, 0]]] };

describe('land input helpers', () => {
  it('offers the five friendly ways to add land in a fixed order, each with labels', () => {
    expect(ADD_LAND_OPTIONS).toEqual(['boundary', 'tree-line', 'pin', 'coordinates', 'import']);
    for (const option of ADD_LAND_OPTIONS) expect(LAND_TOOL_KEYS[option]).toBeTruthy();
    expect(isToolActive('pin', 'pin')).toBe(true);
    expect(isToolActive('import', 'none')).toBe(false);
    expect(isToolActive('delete', 'none')).toBe(false);
    expect(isToolActive('edit', 'edit')).toBe(true);
  });

  it('starts the size field in acres for India and the US, hectares in the EU, unless Settings says otherwise', () => {
    expect(defaultInputAreaUnit('IN')).toBe('acre');
    expect(defaultInputAreaUnit('US')).toBe('acre');
    expect(defaultInputAreaUnit('EU')).toBe('hectare');
    expect(defaultInputAreaUnit('DE')).toBe('hectare');
    expect(defaultInputAreaUnit('IN', 'hectare')).toBe('hectare');
    expect(defaultInputAreaUnit(null)).toBe('acre');
  });

  it('converts pin sizes between acres and hectares', () => {
    expect(toApiAreaUnit('acre')).toBe('ac');
    expect(toApiAreaUnit('hectare')).toBe('ha');
    expect(areaToHectares(2, 'acre')).toBeCloseTo(0.809371, 6);
    expect(areaToHectares(2, 'hectare')).toBe(2);
    expect(hectaresToUnit(0.40468564224, 'acre')).toBeCloseTo(1, 9);
    expect(hectaresToUnit(hectaresToUnit(3, 'acre') * 0.40468564224, 'hectare')).toBeCloseTo(3, 9);
  });

  it('validates the size like the server (> 0, ≤ 10 000 ha)', () => {
    expect(validatePinSize(2, 'acre')).toBeNull();
    expect(validatePinSize(Number.NaN, 'acre')).toBe('not_a_number');
    expect(validatePinSize(null, 'acre')).toBe('not_a_number');
    expect(validatePinSize(0, 'hectare')).toBe('not_positive');
    expect(validatePinSize(10_000, 'hectare')).toBeNull();
    expect(validatePinSize(24_710, 'acre')).toBeNull(); // 9 999.8 ha
    expect(validatePinSize(24_711, 'acre')).toBe('too_large'); // 10 000.2 ha
  });

  it('validates tree-line spacing and strip width', () => {
    expect(validateTreeLineSettings(5, 4)).toBeNull();
    expect(validateTreeLineSettings(0.4, 4)).toBe('spacing');
    expect(validateTreeLineSettings(5, 51)).toBe('width');
    expect(validateTreeLineSettings(Number.NaN, 4)).toBe('spacing');
  });

  it('builds the geometry helper bodies', () => {
    expect(fromPointBody({ lat: 13.29, lon: 77.53 }, 2, 'acre')).toEqual({ lat: 13.29, lon: 77.53, area: { value: 2, unit: 'ac' }, shape: 'square' });
    const line = { type: 'LineString' as const, coordinates: [[0, 0], [1, 1]] };
    expect(fromLineBody(line, 5, 4)).toEqual({ line, spacing_m: 5, width_m: 4 });
  });

  it('maps every mode to the plot source and boundary quality of the contract', () => {
    expect(plotRequestFor('tree-line', square, 55)).toEqual({ geometry: square, source: 'tree-line', boundary_quality: 'approximate', treeCount: 55 });
    expect(plotRequestFor('pin', square)).toMatchObject({ source: 'pin-and-area', boundary_quality: 'approximate' });
    expect(plotRequestFor('coordinates', square)).toMatchObject({ source: 'coordinates', boundary_quality: 'exact' });
    expect(plotRequestFor('boundary', square)).toMatchObject({ source: 'manual-drawing', boundary_quality: 'exact' });
    expect(plotRequestFor('edit', square)).toMatchObject({ source: 'manual-drawing', boundary_quality: 'exact' });
  });

  it('names new plots with the first free letter', () => {
    expect(nextPlotName([])).toBe('Plot A');
    expect(nextPlotName([{ name: 'Plot A' }, { name: 'plot b' }])).toBe('Plot C');
    expect(nextPlotName([{ name: 'Plot B' }])).toBe('Plot A');
    const many = Array.from({ length: 26 }, (_, i) => ({ name: `Plot ${String.fromCharCode(65 + i)}` }));
    expect(nextPlotName(many)).toBe('Plot AA');
    expect(nextPlotName([], 'Fläche')).toBe('Fläche A');
  });

  it('flags approximate plots only', () => {
    expect(isApproximate({ boundary_quality: 'approximate' })).toBe(true);
    expect(isApproximate({ boundary_quality: 'exact' })).toBe(false);
    expect(isApproximate({})).toBe(false);
    expect(isApproximate(null)).toBe(false);
  });
});
