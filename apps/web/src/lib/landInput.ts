/**
 * "Mark your land" — pure helpers behind the map's friendly input modes
 * (boundary, tree line, pin + size, coordinates, import). Components only
 * render what these return; the geometry itself comes from the API's geometry
 * helpers (or their offline stand-ins).
 */
import { regionIdFor, type AreaUnit } from '@/config/regions';
import type {
  AreaInputUnit,
  BoundaryQuality,
  FromLineBody,
  FromPointBody,
  LatLon,
  LineStringGeometry,
  PlotSource,
  PolygonGeometry,
} from '@/types/api';
import { HECTARES_PER_ACRE } from './format';

export type LandInputMode = 'none' | 'boundary' | 'tree-line' | 'pin' | 'coordinates' | 'edit';

/** The ways to add land, in toolbar and welcome-card order. `import` opens the Import dialog. */
export const ADD_LAND_OPTIONS = ['boundary', 'tree-line', 'pin', 'coordinates', 'import'] as const;
export type AddLandOption = (typeof ADD_LAND_OPTIONS)[number];

/** Everything the map toolbar can do: the add-land options plus Edit and Delete of the selected plot. */
export type LandToolAction = AddLandOption | 'edit' | 'delete';

/** i18n key suffix per tool (`map.tool_<key>` label and `map.tool_<key>Hint` tooltip). */
export const LAND_TOOL_KEYS: Record<LandToolAction, string> = {
  boundary: 'boundary',
  'tree-line': 'treeLine',
  pin: 'pin',
  coordinates: 'coordinates',
  import: 'import',
  edit: 'edit',
  delete: 'delete',
};

/** Whether a toolbar button shows as pressed for the current mode (Import and Delete are one-shot actions). */
export function isToolActive(action: LandToolAction, mode: LandInputMode): boolean {
  return action !== 'import' && action !== 'delete' && action === mode;
}

export const TREE_LINE_DEFAULTS = { spacing_m: 5, width_m: 4 } as const;
export const PIN_DEFAULT_SIZE = 2;
export const MAX_PLOT_AREA_HA = 10_000;

/** Unit offered in the "How big is your land?" field. */
export type InputAreaUnit = Extract<AreaUnit, 'acre' | 'hectare'>;

/**
 * Landowners in India and the US usually state land in acres, in the EU in
 * hectares, so the size field starts there. A unit chosen in Settings wins.
 * TODO(config): move to `units.area_input` in config/regions/<ISO>.yaml.
 */
const INPUT_UNIT_BY_REGION: Record<string, InputAreaUnit> = { IN: 'acre', US: 'acre', EU: 'hectare' };

export function defaultInputAreaUnit(country: string | null | undefined, preference: AreaUnit | 'auto' = 'auto'): InputAreaUnit {
  if (preference !== 'auto') return preference;
  return INPUT_UNIT_BY_REGION[regionIdFor(country)] ?? 'hectare';
}

export function toApiAreaUnit(unit: InputAreaUnit): AreaInputUnit {
  return unit === 'acre' ? 'ac' : 'ha';
}

export function areaToHectares(value: number, unit: InputAreaUnit): number {
  return unit === 'acre' ? value * HECTARES_PER_ACRE : value;
}

export function hectaresToUnit(hectares: number, unit: InputAreaUnit): number {
  return unit === 'acre' ? hectares / HECTARES_PER_ACRE : hectares;
}

export type SizeProblem = 'not_a_number' | 'not_positive' | 'too_large';

/** Mirrors the server rule: area > 0 and ≤ ATLAS_MAX_PLOT_AREA_HA (10 000 ha by default). */
export function validatePinSize(value: number | null | undefined, unit: InputAreaUnit): SizeProblem | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'not_a_number';
  if (value <= 0) return 'not_positive';
  if (areaToHectares(value, unit) > MAX_PLOT_AREA_HA) return 'too_large';
  return null;
}

export type LineSettingProblem = 'spacing' | 'width';

export function validateTreeLineSettings(spacing: number, width: number): LineSettingProblem | null {
  if (!(spacing >= 0.5 && spacing <= 50)) return 'spacing';
  if (!(width >= 1 && width <= 50)) return 'width';
  return null;
}

export function fromPointBody(pin: LatLon, value: number, unit: InputAreaUnit): FromPointBody {
  return { lat: pin.lat, lon: pin.lon, area: { value, unit: toApiAreaUnit(unit) }, shape: 'square' };
}

export function fromLineBody(line: LineStringGeometry, spacing: number, width: number): FromLineBody {
  return { line, spacing_m: spacing, width_m: width };
}

/** What a mode turns into when the user presses "Create plot". */
export interface NewPlotRequest {
  geometry: PolygonGeometry;
  source: PlotSource;
  boundary_quality: BoundaryQuality;
  /** Pre-fills the tree form of the new plot (tree line). */
  treeCount?: number;
  name?: string;
}

export function plotRequestFor(
  mode: 'boundary' | 'tree-line' | 'pin' | 'coordinates' | 'edit',
  geometry: PolygonGeometry,
  treeCount?: number,
): NewPlotRequest {
  switch (mode) {
    case 'tree-line':
      return { geometry, source: 'tree-line', boundary_quality: 'approximate', treeCount };
    case 'pin':
      return { geometry, source: 'pin-and-area', boundary_quality: 'approximate' };
    case 'coordinates':
      return { geometry, source: 'coordinates', boundary_quality: 'exact' };
    default:
      return { geometry, source: 'manual-drawing', boundary_quality: 'exact' };
  }
}

function letters(index: number): string {
  let n = index;
  let out = '';
  do {
    out = String.fromCharCode(65 + (n % 26)) + out;
    n = Math.floor(n / 26) - 1;
  } while (n >= 0);
  return out;
}

/** First free "<prefix> A", "<prefix> B", … "<prefix> AA" name. */
export function nextPlotName(existing: { name: string }[], prefix = 'Plot'): string {
  const taken = new Set(existing.map((p) => p.name.trim().toLowerCase()));
  for (let i = 0; i < 26 * 27; i += 1) {
    const candidate = `${prefix} ${letters(i)}`;
    if (!taken.has(candidate.toLowerCase())) return candidate;
  }
  return `${prefix} ${existing.length + 1}`;
}

export function isApproximate(plot: { boundary_quality?: BoundaryQuality | null } | null | undefined): boolean {
  return plot?.boundary_quality === 'approximate';
}
