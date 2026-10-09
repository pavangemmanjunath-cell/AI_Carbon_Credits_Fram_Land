import { describe, expect, it } from 'vitest';
import { importRecord } from '@/test/fixtures';
import {
  fileKey,
  formatBytes,
  importFileType,
  importOutcomes,
  inventoryFromImport,
  isPointCloud,
  nextReady,
  plotFromImport,
  queuePhase,
  queueReducer,
  treeCountToUse,
  type QueueItem,
} from './imports';

const ring = [[[77.53, 13.29], [77.54, 13.29], [77.54, 13.3], [77.53, 13.3], [77.53, 13.29]]];
const file = (name: string, size = 10, lastModified = 1) => new File(['x'.repeat(size)], name, { lastModified });

describe('import file types', () => {
  it('detects every supported extension, case-insensitively', () => {
    expect(importFileType('field.geojson')).toBe('geojson');
    expect(importFileType('field.JSON')).toBe('geojson');
    expect(importFileType('farm.kml')).toBe('kml');
    expect(importFileType('farm.kmz')).toBe('kmz');
    expect(importFileType('corners.csv')).toBe('csv');
    expect(importFileType('scan.las')).toBe('las');
    expect(importFileType('scan.LAZ')).toBe('laz');
    expect(importFileType('scan.e57')).toBe('e57');
    expect(importFileType('photo.jpg')).toBe('unknown');
    expect(importFileType('noextension')).toBe('unknown');
    expect(isPointCloud('laz')).toBe(true);
    expect(isPointCloud('kml')).toBe(false);
  });

  it('formats file sizes with SI units', () => {
    expect(formatBytes(512, 'en-US')).toBe('512 B');
    expect(formatBytes(12_300, 'en-US')).toBe('12.3 kB');
    expect(formatBytes(1_840_221, 'en-US')).toBe('1.8 MB');
    expect(formatBytes(250_000_000, 'en-US')).toBe('250 MB');
    expect(formatBytes(-1)).toBe('—');
  });
});

describe('upload queue', () => {
  it('adds files once, flags unsupported types and removes them', () => {
    const a = file('a.geojson');
    let queue = queueReducer([], { type: 'add', files: [a, file('b.jpg'), a] });
    expect(queue.map((i) => [i.file.name, i.status])).toEqual([
      ['a.geojson', 'ready'],
      ['b.jpg', 'unsupported'],
    ]);
    queue = queueReducer(queue, { type: 'add', files: [a] });
    expect(queue).toHaveLength(2);
    queue = queueReducer(queue, { type: 'remove', id: fileKey(a) });
    expect(queue.map((i) => i.file.name)).toEqual(['b.jpg']);
  });

  it('walks a file through upload, progress and done; phases follow', () => {
    const a = file('a.laz');
    let queue: QueueItem[] = queueReducer([], { type: 'add', files: [a] });
    expect(queuePhase(queue)).toBe('ready');
    expect(nextReady(queue)?.file.name).toBe('a.laz');
    queue = queueReducer(queue, { type: 'start', id: fileKey(a) });
    expect(queuePhase(queue)).toBe('running');
    queue = queueReducer(queue, { type: 'progress', id: fileKey(a), progress: 0.4 });
    queue = queueReducer(queue, { type: 'progress', id: fileKey(a), progress: 0.2 });
    expect(queue[0].progress).toBe(0.4);
    // a file being uploaded cannot be removed
    expect(queueReducer(queue, { type: 'remove', id: fileKey(a) })).toHaveLength(1);
    queue = queueReducer(queue, { type: 'done', id: fileKey(a), record: importRecord() });
    expect(queue[0]).toMatchObject({ status: 'done', progress: 1 });
    expect(queuePhase(queue)).toBe('finished');
    expect(queuePhase([])).toBe('empty');
  });

  it('records errors and cancels what is still pending', () => {
    const a = file('a.kml');
    const b = file('b.kml');
    let queue = queueReducer([], { type: 'add', files: [a, b] });
    queue = queueReducer(queue, { type: 'start', id: fileKey(a) });
    queue = queueReducer(queue, { type: 'error', id: fileKey(a), error: new Error('415') });
    expect(queue[0].status).toBe('error');
    queue = queueReducer(queue, { type: 'cancelPending' });
    expect(queue.map((i) => i.status)).toEqual(['error', 'cancelled']);
    expect(queueReducer(queue, { type: 'reset' })).toEqual([]);
  });
});

describe('import results → actions', () => {
  it('maps a point cloud to a tree outcome with the mean height', () => {
    expect(importOutcomes(importRecord())).toEqual([{ kind: 'trees', count: 128, countInPlot: 120, meanHeightM: 6.43 }]);
  });

  it('maps a boundary file (and a file with both) in display order', () => {
    const boundary = { geometry: { type: 'Polygon' as const, coordinates: ring }, area_hectares: 2.13, name: 'Field 7' };
    expect(importOutcomes(importRecord({ kind: 'boundary', boundary, trees: null }))).toEqual([{ kind: 'boundary', areaHectares: 2.13, name: 'Field 7' }]);
    expect(importOutcomes(importRecord({ boundary })).map((o) => o.kind)).toEqual(['boundary', 'trees']);
  });

  it('reports failed and empty imports', () => {
    expect(importOutcomes(importRecord({ status: 'failed', trees: null, warnings: ['No CRS'] }))).toEqual([{ kind: 'failed', reason: 'No CRS' }]);
    expect(importOutcomes(importRecord({ trees: { ...importRecord().trees!, count: 0 } }))).toEqual([{ kind: 'nothing' }]);
  });

  it('uses the trees inside the linked plot when the server could tell', () => {
    expect(treeCountToUse(importRecord())).toBe(120);
    expect(treeCountToUse(importRecord(), 'PLT-DEMOIN')).toBe(120);
    // a different target plot: the inside count does not apply, use every tree in the file
    expect(treeCountToUse(importRecord(), 'PLT-OTHER')).toBe(128);
    expect(treeCountToUse(importRecord({ trees: { ...importRecord().trees!, count_in_plot: null } }))).toBe(128);
    expect(treeCountToUse(importRecord({ trees: null }))).toBeNull();
  });

  it('builds a model-estimated inventory with species and year from the tree form', () => {
    const body = inventoryFromImport(importRecord(), { species_id: 'mango', plantation_year: 2019, survival_rate: 0.85 });
    expect(body).toEqual({
      species_id: 'mango',
      tree_count: 120,
      plantation_year: 2019,
      average_dbh_cm: null,
      average_height_m: 6.4,
      survival_rate: 0.85,
      measurement_source: 'model-estimated',
    });
    const noHeight = inventoryFromImport(importRecord({ trees: { ...importRecord().trees!, mean_height_m: null } }), { species_id: 'teak', plantation_year: 2020, survival_rate: null });
    expect(noHeight?.average_height_m).toBeNull();
    expect(inventoryFromImport(importRecord({ trees: null }), { species_id: 'teak', plantation_year: 2020, survival_rate: null })).toBeNull();
  });

  it('builds the "Use as my land" plot body (source import, country left to the server)', () => {
    const boundary = { geometry: { type: 'Polygon' as const, coordinates: ring }, area_hectares: 2.13, name: 'Field 7' };
    expect(plotFromImport(importRecord({ boundary }), 'Plot B')).toEqual({ name: 'Field 7', source: 'import', boundary_quality: 'exact', geometry: boundary.geometry });
    expect(plotFromImport(importRecord({ boundary: { ...boundary, name: null } }), 'Plot B')?.name).toBe('Plot B');
    expect(plotFromImport(importRecord(), 'Plot B')).toBeNull();
  });
});
