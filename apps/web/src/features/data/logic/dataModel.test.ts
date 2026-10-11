import { describe, expect, it } from 'vitest';
import { importRecord, plot } from '@/test/fixtures';
import {
  canShowOnMap,
  importResultLine,
  importTypeOf,
  linkedPlot,
  plotSourceKey,
  tabFromParam,
} from './dataModel';

const boundary = { geometry: plot.geometry!, area_hectares: 2.13, name: 'Field 7' };

describe('Data page model', () => {
  it('reads the tab from the URL', () => {
    expect(tabFromParam('files')).toBe('files');
    expect(tabFromParam(null)).toBe('plots');
    expect(tabFromParam('other')).toBe('plots');
  });

  it('gives every plot source a friendly label key, including the new ones', () => {
    expect(plotSourceKey('pin-and-area')).toBe('source.pin-and-area');
    expect(plotSourceKey('tree-line')).toBe('source.tree-line');
    expect(plotSourceKey('coordinates')).toBe('source.coordinates');
    expect(plotSourceKey('import')).toBe('source.import');
    expect(plotSourceKey('synthetic-demo')).toBe('source.synthetic-demo');
    expect(plotSourceKey('something-new')).toBe('source.other');
  });

  it('labels the file type from the server format, then the file name', () => {
    expect(importTypeOf({ format: 'laz', filename: 'x.bin' })).toBe('laz');
    expect(importTypeOf({ format: 'geojson', filename: 'x' })).toBe('geojson');
    expect(importTypeOf({ format: '???', filename: 'farm.kml' })).toBe('kml');
  });

  it('summarises the result column', () => {
    expect(importResultLine(importRecord())).toEqual({
      kind: 'trees',
      count: 128,
      meanHeightM: 6.43,
    });
    expect(importResultLine(importRecord({ kind: 'boundary', boundary, trees: null }))).toEqual({
      kind: 'boundary',
      areaHectares: 2.13,
    });
    expect(importResultLine(importRecord({ boundary }))).toEqual({
      kind: 'boundary-trees',
      areaHectares: 2.13,
      count: 128,
    });
    expect(importResultLine(importRecord({ status: 'failed', trees: null }))).toEqual({
      kind: 'failed',
    });
    expect(importResultLine(importRecord({ trees: null }))).toEqual({ kind: 'nothing' });
  });

  it('offers "View on map" only when there is something to draw', () => {
    expect(canShowOnMap(importRecord())).toBe(true);
    expect(canShowOnMap(importRecord({ trees: null }))).toBe(false);
    expect(canShowOnMap(importRecord({ status: 'failed' }))).toBe(false);
  });

  it('finds the linked plot', () => {
    expect(linkedPlot({ plot_id: 'PLT-TEST' }, [plot])?.name).toBe('Plot A');
    expect(linkedPlot({ plot_id: 'PLT-GONE' }, [plot])).toBeNull();
    expect(linkedPlot({ plot_id: null }, [plot])).toBeNull();
  });
});
