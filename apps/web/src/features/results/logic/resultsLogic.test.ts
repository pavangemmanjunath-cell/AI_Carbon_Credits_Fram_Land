import { describe, expect, it } from 'vitest';
import { analysis, estimate, inventory, plot } from '@/test/fixtures';
import { evidenceChainLines, explainBody, parameterCounts, resultsExport } from './resultsLogic';

describe('resultsLogic', () => {
  it('builds an evidence chain that starts with the estimate and ends with provenance', () => {
    const lines = evidenceChainLines(plot, inventory, analysis, estimate);
    expect(lines[0]).toContain('10.6 tCO2e/yr');
    expect(lines.some((l) => l.includes('Mangifera indica'))).toBe(true);
    expect(lines.some((l) => l.includes('ESA WorldCover'))).toBe(true);
    expect(lines[lines.length - 1]).toContain('certified: false');
  });

  it('never sends coordinates or names to /explain', () => {
    const body = explainBody('en', inventory, analysis, estimate, plot);
    const keys = JSON.stringify(body.indicators);
    expect(keys).not.toMatch(/lat|lon|geometry|coordinates|name/);
    expect(body.indicators.tree_count).toBe(420);
    expect(body.indicators.missing_evidence).toEqual(['dbh']);
  });

  it('counts parameter verification status', () => {
    expect(parameterCounts(estimate)).toEqual({ verified: 1, pending: 1, assumption: 1 });
  });

  it('strips private geometry from the export bundle', () => {
    const bundle = resultsExport(plot, inventory, analysis, estimate, {});
    expect(bundle.plot.geometry).toBeUndefined();
    expect(bundle.plot.centroid).toBeUndefined();
    expect(bundle.estimate.estimate_id).toBe('EST-1');
  });
});
