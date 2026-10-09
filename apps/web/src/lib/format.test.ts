import { describe, expect, it } from 'vitest';
import { formatArea, formatCurrency, formatRange, formatSignedPercent, intlLocale, unitLabel } from './format';

describe('format helpers', () => {
  it('puts hectares first for India/EU and acres first for the US', () => {
    expect(formatArea(2.13, 'IN', 'en-IN').primaryUnit).toBe('hectare');
    expect(formatArea(2.13, 'US', 'en-US').primaryUnit).toBe('acre');
    expect(formatArea(2.13, 'DE', 'de-DE').primaryUnit).toBe('hectare');
    expect(formatArea(1, 'IN', 'en-IN', 'acre').primary).toMatch(/2\.47 ac/);
  });

  it('formats ranges, currency and percentages per locale', () => {
    expect(formatRange({ low: 7.4, central: 10.6, high: 13.8, unit: 'tCO2e/yr' }, 'en-IN')).toBe('7.4 – 13.8');
    expect(formatCurrency(12122, '₹', 'en-IN')).toBe('₹12,122');
    expect(formatCurrency(293, '$', 'en-US')).toBe('$293');
    expect(formatSignedPercent(22.6, 'en-IN', 0)).toBe('+23%');
  });

  it('humanises units and resolves locales', () => {
    expect(unitLabel('tCO2e/yr')).toContain('CO₂e');
    expect(intlLocale('en', 'US')).toBe('en-US');
    expect(intlLocale('kn')).toBe('kn-IN');
  });
});
