/**
 * The URL is the source of truth for the Simulation Lab so scenarios are
 * shareable (`/app/simulate?country=IN&species=mango&trees=420&year=2023&horizon=30`).
 * No coordinates ever appear in the link.
 */
import type { SimulateBody } from '@/types/api';

export interface SimulationState {
  country: string;
  species: string;
  trees: number;
  year: number;
  horizon: 10 | 20 | 30;
  area: number;
  plot: string | null;
}

export const DEFAULT_SIMULATION: SimulationState = {
  country: 'IN',
  species: 'mango',
  trees: 420,
  year: new Date().getFullYear() - 3,
  horizon: 30,
  area: 2.13,
  plot: null,
};

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

export function parseSimulationParams(
  params: URLSearchParams,
  defaults: SimulationState = DEFAULT_SIMULATION,
): SimulationState {
  const num = (key: string, fallback: number) => {
    const raw = params.get(key);
    const n = raw === null ? NaN : Number(raw);
    return Number.isFinite(n) ? n : fallback;
  };
  const horizonRaw = num('horizon', defaults.horizon);
  const horizon: 10 | 20 | 30 = horizonRaw <= 10 ? 10 : horizonRaw <= 20 ? 20 : 30;
  const thisYear = new Date().getFullYear();
  return {
    country: (params.get('country') ?? defaults.country).toUpperCase().slice(0, 2),
    species: params.get('species') ?? defaults.species,
    trees: clamp(Math.round(num('trees', defaults.trees)), 0, 2000),
    year: clamp(Math.round(num('year', defaults.year)), 1900, thisYear),
    horizon,
    area: clamp(num('area', defaults.area), 0.01, 10_000),
    plot: params.get('plot'),
  };
}

export function toSearchParams(state: SimulationState): URLSearchParams {
  const params = new URLSearchParams({
    country: state.country,
    species: state.species,
    trees: String(state.trees),
    year: String(state.year),
    horizon: String(state.horizon),
    area: String(Number(state.area.toFixed(2))),
  });
  if (state.plot) params.set('plot', state.plot);
  return params;
}

/**
 * Survival is sent only when someone actually entered it; otherwise the engine
 * applies its configured default and reports it with its own source and status
 * (sending a default here would mislabel an assumption as a user value).
 */
export function toSimulateBody(state: SimulationState, survival?: number): SimulateBody {
  return {
    country: state.country,
    species_id: state.species,
    tree_count: state.trees,
    planting_year: state.year,
    horizon_years: state.horizon,
    ...(survival === undefined ? {} : { survival_rate: survival }),
    area_hectares: state.area,
  };
}

export function shareUrl(
  state: SimulationState,
  origin = typeof window !== 'undefined' ? window.location.origin : '',
): string {
  return `${origin}/app/simulate?${toSearchParams(state).toString()}`;
}

/** Linear growth ramp used only for the size of the illustrated trees (the engine owns the carbon numbers). */
export function growthFactor(age: number, maturityYears: number): number {
  if (age <= 0) return 0.12;
  return clamp(0.12 + (age / Math.max(1, maturityYears)) * 0.88, 0.12, 1);
}
