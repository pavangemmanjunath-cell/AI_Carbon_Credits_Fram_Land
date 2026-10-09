/**
 * Import data (Trimble-style dialog) — pure helpers: file type detection, the
 * upload queue, and turning an ImportRecord into the actions the user can take
 * ("Use as my land", "Use 128 trees for Plot A"). No React here.
 */
import type { ImportRecord, PlotCreateBody, TreeInventoryBody } from '@/types/api';

export type ImportFileType = 'geojson' | 'kml' | 'kmz' | 'csv' | 'las' | 'laz' | 'e57' | 'unknown';

const EXTENSIONS: Record<string, ImportFileType> = {
  geojson: 'geojson',
  json: 'geojson',
  kml: 'kml',
  kmz: 'kmz',
  csv: 'csv',
  las: 'las',
  laz: 'laz',
  e57: 'e57',
};

/** `accept` attribute of the file input. `.e57` is listed; servers without pye57 answer 415 with advice. */
export const IMPORT_ACCEPT = '.geojson,.json,.kml,.kmz,.csv,.las,.laz,.e57';

export function importFileType(filename: string): ImportFileType {
  const match = /\.([a-z0-9]+)$/i.exec(filename.trim());
  return (match && EXTENSIONS[match[1].toLowerCase()]) || 'unknown';
}

export function isPointCloud(type: ImportFileType): boolean {
  return type === 'las' || type === 'laz' || type === 'e57';
}

/** SI file sizes ("1.8 MB"); unit symbols are never translated. */
export function formatBytes(bytes: number, locale = 'en-IN'): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '—';
  const units = ['B', 'kB', 'MB', 'GB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)} ${units[unit]}`;
}

// ─── Upload queue ────────────────────────────────────────────────────────────

export type QueueStatus = 'ready' | 'unsupported' | 'uploading' | 'done' | 'error' | 'cancelled';

export interface QueueItem {
  id: string;
  file: File;
  type: ImportFileType;
  status: QueueStatus;
  /** Upload progress 0–1. */
  progress: number;
  record: ImportRecord | null;
  error: unknown;
}

export type QueueAction =
  | { type: 'add'; files: File[] }
  | { type: 'remove'; id: string }
  | { type: 'start'; id: string }
  | { type: 'progress'; id: string; progress: number }
  | { type: 'done'; id: string; record: ImportRecord }
  | { type: 'error'; id: string; error: unknown }
  | { type: 'cancelPending' }
  | { type: 'reset' };

export function fileKey(file: File): string {
  return `${file.name}|${file.size}|${file.lastModified}`;
}

export function queueReducer(state: QueueItem[], action: QueueAction): QueueItem[] {
  switch (action.type) {
    case 'add': {
      const known = new Set(state.map((item) => item.id));
      const added: QueueItem[] = [];
      for (const file of action.files) {
        const id = fileKey(file);
        if (known.has(id)) continue;
        known.add(id);
        const type = importFileType(file.name);
        added.push({ id, file, type, status: type === 'unknown' ? 'unsupported' : 'ready', progress: 0, record: null, error: null });
      }
      return added.length ? [...state, ...added] : state;
    }
    case 'remove':
      return state.filter((item) => item.id !== action.id || item.status === 'uploading');
    case 'start':
      return state.map((item) => (item.id === action.id ? { ...item, status: 'uploading', progress: 0, error: null } : item));
    case 'progress':
      return state.map((item) => (item.id === action.id && item.status === 'uploading' ? { ...item, progress: Math.max(item.progress, Math.min(1, action.progress)) } : item));
    case 'done':
      return state.map((item) => (item.id === action.id ? { ...item, status: 'done', progress: 1, record: action.record } : item));
    case 'error':
      return state.map((item) => (item.id === action.id ? { ...item, status: 'error', error: action.error } : item));
    case 'cancelPending':
      return state.map((item) => (item.status === 'ready' || item.status === 'uploading' ? { ...item, status: 'cancelled' } : item));
    case 'reset':
      return [];
    default:
      return state;
  }
}

export function nextReady(queue: QueueItem[]): QueueItem | undefined {
  return queue.find((item) => item.status === 'ready');
}

export type QueuePhase = 'empty' | 'ready' | 'running' | 'finished';

export function queuePhase(queue: QueueItem[]): QueuePhase {
  if (queue.length === 0) return 'empty';
  if (queue.some((item) => item.status === 'uploading')) return 'running';
  if (queue.some((item) => item.status === 'ready')) return 'ready';
  return 'finished';
}

// ─── Results → actions ───────────────────────────────────────────────────────

export type ImportOutcome =
  | { kind: 'boundary'; areaHectares: number; name: string | null }
  | { kind: 'trees'; count: number; countInPlot: number | null; meanHeightM: number | null }
  | { kind: 'nothing' }
  | { kind: 'failed'; reason: string | null };

/** What an import found, in display order (a file can hold a boundary and trees). */
export function importOutcomes(record: ImportRecord): ImportOutcome[] {
  if (record.status === 'failed') return [{ kind: 'failed', reason: record.warnings[0] ?? null }];
  const outcomes: ImportOutcome[] = [];
  if (record.boundary) {
    outcomes.push({ kind: 'boundary', areaHectares: record.boundary.area_hectares, name: record.boundary.name ?? null });
  }
  if (record.trees && record.trees.count > 0) {
    outcomes.push({
      kind: 'trees',
      count: record.trees.count,
      countInPlot: record.trees.count_in_plot ?? null,
      meanHeightM: record.trees.mean_height_m ?? null,
    });
  }
  return outcomes.length ? outcomes : [{ kind: 'nothing' }];
}

/**
 * Trees to use for `targetPlotId`: the count inside that plot when the import
 * was linked to it and the server could tell, else every tree in the file.
 * Without a target, the linked plot is assumed.
 */
export function treeCountToUse(record: ImportRecord, targetPlotId?: string | null): number | null {
  if (!record.trees || record.trees.count <= 0) return null;
  const sameTarget = targetPlotId === undefined || targetPlotId === record.plot_id;
  return sameTarget && record.trees.count_in_plot != null ? record.trees.count_in_plot : record.trees.count;
}

export interface TreeFormDefaults {
  species_id: string;
  plantation_year: number;
  survival_rate: number | null;
}

/**
 * Inventory body for "Use N trees for <plot>": the count (and mean height from
 * a point cloud) come from the import; species and year from the tree form.
 */
export function inventoryFromImport(record: ImportRecord, form: TreeFormDefaults, targetPlotId?: string | null): TreeInventoryBody | null {
  const count = treeCountToUse(record, targetPlotId);
  if (!count) return null;
  const height = record.trees?.mean_height_m;
  return {
    species_id: form.species_id,
    tree_count: count,
    plantation_year: form.plantation_year,
    average_dbh_cm: null,
    average_height_m: height != null && height > 0 ? Number(height.toFixed(1)) : null,
    survival_rate: form.survival_rate,
    measurement_source: 'model-estimated',
  };
}

/**
 * `POST /plots` body for "Use as my land". `country` is left out on purpose:
 * the server derives it from the polygon (reverse geocoding, else region bbox).
 */
export function plotFromImport(record: ImportRecord, name: string): PlotCreateBody | null {
  if (!record.boundary) return null;
  return {
    name: record.boundary.name?.trim() || name,
    source: 'import',
    boundary_quality: 'exact',
    geometry: record.boundary.geometry,
  };
}
