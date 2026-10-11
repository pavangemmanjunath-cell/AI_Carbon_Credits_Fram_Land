import { describe, expect, it } from 'vitest';
import { analysis, estimate, inventory } from '@/test/fixtures';
import {
  DEFAULT_FORM,
  formEquals,
  formForPlot,
  formFromInventory,
  isExternalInventory,
  isFormValid,
  observationYears,
  summarize,
  toInventoryBody,
} from './workspaceModel';

describe('workspaceModel', () => {
  it('derives the form from the latest inventory and back', () => {
    const form = formFromInventory(inventory, 'teak');
    expect(form.species_id).toBe('mango');
    expect(form.tree_count).toBe(420);
    expect(formEquals(form, formFromInventory(inventory, 'x'))).toBe(true);
    const body = toInventoryBody(form);
    expect(body.measurement_source).toBe('user-reported');
    expect(toInventoryBody({ ...form, average_dbh_cm: 12 }).measurement_source).toBe(
      'field-measured',
    );
  });

  it('uses the fallback species when there is no inventory', () => {
    expect(formFromInventory(null, 'olive').species_id).toBe('olive');
  });

  it('pre-fills the tree count of a new tree-line plot, never over an existing inventory', () => {
    expect(formForPlot(null, 'mango', 55).tree_count).toBe(55);
    expect(formForPlot(null, 'mango', null).tree_count).toBe(DEFAULT_FORM.tree_count);
    expect(formForPlot(null, 'mango', 0).tree_count).toBe(DEFAULT_FORM.tree_count);
    expect(formForPlot(inventory, 'mango', 55).tree_count).toBe(420);
  });

  it('detects inventories saved outside the form (e.g. from an import)', () => {
    const own = new Set(['INV-OWN']);
    expect(isExternalInventory('INV-IMPORT', 'INV-1', own)).toBe(true);
    expect(isExternalInventory('INV-OWN', 'INV-1', own)).toBe(false);
    expect(isExternalInventory('INV-1', 'INV-1', own)).toBe(false);
    expect(isExternalInventory(null, 'INV-1', own)).toBe(false);
  });

  it('validates the form bounds', () => {
    expect(isFormValid(DEFAULT_FORM)).toBe(true);
    expect(isFormValid({ ...DEFAULT_FORM, tree_count: 0 })).toBe(false);
    expect(isFormValid({ ...DEFAULT_FORM, plantation_year: new Date().getFullYear() + 1 })).toBe(
      false,
    );
    expect(isFormValid({ ...DEFAULT_FORM, average_dbh_cm: -1 })).toBe(false);
  });

  it('summarizes estimate and analysis into the three result rows', () => {
    const summary = summarize(estimate, analysis);
    expect(summary.removal?.central).toBe(10.6);
    expect(summary.ndvi).toBe(0.76);
    expect(summary.ndviClass).toBe('healthy');
    expect(summary.readinessScore).toBe(55);
    expect(summary.missing).toEqual(['Tree diameter measurements']);
    expect(summarize(undefined, undefined).removal).toBeNull();
  });

  it('extracts observation years from the vegetation series', () => {
    expect(observationYears(analysis)).toEqual([2024, 2026]);
    expect(observationYears(undefined)).toEqual([]);
  });
});
