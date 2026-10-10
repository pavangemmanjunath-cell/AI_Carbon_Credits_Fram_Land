import type { CostInputs } from '@/types/api';

export const COST_FIELDS = [
  'sapling_per_tree',
  'planting_per_tree',
  'maintenance_per_ha_per_year',
  'monitoring_per_year',
] as const;
export type CostField = (typeof COST_FIELDS)[number];
export type CostDraft = Record<CostField, string>;
export const EMPTY_COSTS: CostDraft = {
  sapling_per_tree: '',
  planting_per_tree: '',
  maintenance_per_ha_per_year: '',
  monitoring_per_year: '',
};

/** Only what was typed: blank stays "not entered" (never a default value). */
export function toCostInputs(draft: CostDraft): CostInputs | undefined {
  const out: CostInputs = {};
  for (const field of COST_FIELDS) {
    const raw = draft[field].trim();
    const n = raw === '' ? NaN : Number(raw);
    if (Number.isFinite(n) && n >= 0) out[field] = n;
  }
  return Object.keys(out).length ? out : undefined;
}
