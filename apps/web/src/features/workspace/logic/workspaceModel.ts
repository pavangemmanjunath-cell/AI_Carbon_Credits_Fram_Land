/**
 * Pure helpers for the workspace screen — no React, fully unit-testable.
 */
import type { Analysis, CarbonEstimate, Confidence, Range, TreeInventory, TreeInventoryBody } from '@/types/api';

export interface TreeForm {
  species_id: string;
  tree_count: number;
  plantation_year: number;
  average_dbh_cm: number | null;
  average_height_m: number | null;
  survival_rate: number | null;
}

export const DEFAULT_FORM: TreeForm = {
  species_id: 'mango',
  tree_count: 420,
  plantation_year: new Date().getFullYear() - 3,
  average_dbh_cm: null,
  average_height_m: null,
  survival_rate: 0.85,
};

export function formFromInventory(inventory: TreeInventory | null | undefined, fallbackSpecies: string): TreeForm {
  if (!inventory) return { ...DEFAULT_FORM, species_id: fallbackSpecies };
  return {
    species_id: inventory.species.id,
    tree_count: inventory.tree_count,
    plantation_year: inventory.plantation_year,
    average_dbh_cm: inventory.average_dbh_cm ?? null,
    average_height_m: inventory.average_height_m ?? null,
    survival_rate: inventory.survival_rate ?? null,
  };
}

/**
 * Form for a plot that was just selected. A plot created from a tree line has
 * no inventory yet; its suggested tree count pre-fills the form.
 */
export function formForPlot(inventory: TreeInventory | null | undefined, fallbackSpecies: string, prefillTreeCount?: number | null): TreeForm {
  const form = formFromInventory(inventory, fallbackSpecies);
  if (!inventory && prefillTreeCount && prefillTreeCount > 0) return { ...form, tree_count: Math.round(prefillTreeCount) };
  return form;
}

/**
 * True when the newest inventory was saved somewhere else (for example
 * "Use 128 trees" in the Import dialog), so the form must show it instead of
 * auto-saving its own older values over it.
 */
export function isExternalInventory(latestId: string | null | undefined, lastSeenId: string | null, ownIds: ReadonlySet<string>): boolean {
  return Boolean(latestId) && latestId !== lastSeenId && !ownIds.has(latestId as string);
}

export function formEquals(a: TreeForm, b: TreeForm): boolean {
  return (
    a.species_id === b.species_id &&
    a.tree_count === b.tree_count &&
    a.plantation_year === b.plantation_year &&
    (a.average_dbh_cm ?? null) === (b.average_dbh_cm ?? null) &&
    (a.average_height_m ?? null) === (b.average_height_m ?? null) &&
    (a.survival_rate ?? null) === (b.survival_rate ?? null)
  );
}

export function isFormValid(form: TreeForm): boolean {
  const year = new Date().getFullYear();
  return (
    Boolean(form.species_id) &&
    Number.isInteger(form.tree_count) &&
    form.tree_count >= 1 &&
    form.tree_count <= 10_000_000 &&
    form.plantation_year >= 1900 &&
    form.plantation_year <= year &&
    (form.average_dbh_cm === null || (form.average_dbh_cm > 0 && form.average_dbh_cm <= 500)) &&
    (form.average_height_m === null || (form.average_height_m > 0 && form.average_height_m <= 120))
  );
}

export function toInventoryBody(form: TreeForm): TreeInventoryBody {
  return {
    species_id: form.species_id,
    tree_count: form.tree_count,
    plantation_year: form.plantation_year,
    average_dbh_cm: form.average_dbh_cm,
    average_height_m: form.average_height_m,
    survival_rate: form.survival_rate,
    measurement_source: form.average_dbh_cm ? 'field-measured' : 'user-reported',
  };
}

export interface ResultSummary {
  removal: Range | null;
  confidence: Confidence | null;
  ndvi: number | null;
  ndviClass: string | null;
  ndviDate: string | null;
  trendPct: number | null;
  readinessScore: number | null;
  readinessGrade: string | null;
  missing: string[];
}

export function summarize(estimate: CarbonEstimate | undefined, analysis: Analysis | undefined): ResultSummary {
  const ndvi = analysis?.vegetation?.indices.ndvi;
  return {
    removal: estimate?.estimate ?? null,
    confidence: estimate?.confidence ?? null,
    ndvi: ndvi?.value ?? null,
    ndviClass: ndvi?.class ?? null,
    ndviDate: ndvi?.date ?? null,
    trendPct: analysis?.vegetation?.trend?.change_pct ?? null,
    readinessScore: estimate?.readiness.score ?? null,
    readinessGrade: estimate?.readiness.grade ?? null,
    missing: estimate?.readiness.missing_evidence.map((e) => e.label) ?? [],
  };
}

/** Years available for the observation slider from the vegetation time series. */
export function observationYears(analysis: Analysis | undefined): number[] {
  const years = new Set<number>();
  for (const point of analysis?.vegetation?.time_series ?? []) years.add(Number(point.date.slice(0, 4)));
  return [...years].sort();
}
