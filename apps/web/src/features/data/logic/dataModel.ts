/**
 * Data page helpers: friendly labels and one-line summaries for plots and
 * imported files. Pure functions — the page only renders what they return.
 */
import { importFileType, importOutcomes, type ImportFileType } from '@/lib/imports';
import type { ImportRecord, Plot, PlotSource } from '@/types/api';

export type DataTab = 'plots' | 'files';

export function tabFromParam(value: string | null): DataTab {
  return value === 'files' ? 'files' : 'plots';
}

const KNOWN_SOURCES: PlotSource[] = ['manual-drawing', 'upload', 'import', 'pin-and-area', 'tree-line', 'coordinates', 'qgis-plugin', 'api', 'synthetic-demo'];

/** i18n key of the friendly source label (`source.tree-line` → "Tree line"). */
export function plotSourceKey(source: string): string {
  return KNOWN_SOURCES.includes(source as PlotSource) ? `source.${source}` : 'source.other';
}

/** File type label key from the server's `format`, falling back to the file name. */
export function importTypeOf(record: Pick<ImportRecord, 'format' | 'filename'>): ImportFileType {
  const fromFormat = importFileType(`x.${record.format}`);
  return fromFormat !== 'unknown' ? fromFormat : importFileType(record.filename);
}

export type ImportResultLine =
  | { kind: 'boundary'; areaHectares: number }
  | { kind: 'trees'; count: number; meanHeightM: number | null }
  | { kind: 'boundary-trees'; areaHectares: number; count: number }
  | { kind: 'failed' }
  | { kind: 'nothing' };

/** The "Result" column of the Imported files table. */
export function importResultLine(record: ImportRecord): ImportResultLine {
  const outcomes = importOutcomes(record);
  const boundary = outcomes.find((o) => o.kind === 'boundary');
  const trees = outcomes.find((o) => o.kind === 'trees');
  if (outcomes[0]?.kind === 'failed') return { kind: 'failed' };
  if (boundary?.kind === 'boundary' && trees?.kind === 'trees') return { kind: 'boundary-trees', areaHectares: boundary.areaHectares, count: trees.count };
  if (boundary?.kind === 'boundary') return { kind: 'boundary', areaHectares: boundary.areaHectares };
  if (trees?.kind === 'trees') return { kind: 'trees', count: trees.count, meanHeightM: trees.meanHeightM };
  return { kind: 'nothing' };
}

/** Something to draw: the import found a boundary or trees (the preview is fetched on demand). */
export function canShowOnMap(record: ImportRecord): boolean {
  const line = importResultLine(record);
  return line.kind !== 'failed' && line.kind !== 'nothing';
}

export function linkedPlot(record: Pick<ImportRecord, 'plot_id'>, plots: Plot[]): Plot | null {
  return record.plot_id ? (plots.find((p) => p.plot_id === record.plot_id) ?? null) : null;
}
