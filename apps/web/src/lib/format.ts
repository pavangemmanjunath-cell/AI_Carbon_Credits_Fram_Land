import { regionFor, type AreaUnit } from '@/config/regions';
import type { Range } from '@/types/api';

export const HECTARES_PER_ACRE = 0.40468564224;
export const ACRES_PER_HECTARE = 1 / HECTARES_PER_ACRE;

const LANGUAGE_DEFAULT_REGION: Record<string, string> = {
  en: 'IN',
  hi: 'IN',
  kn: 'IN',
  de: 'DE',
  fr: 'FR',
  es: 'ES',
};

/**
 * Builds the Intl locale from the UI language and the active region, e.g.
 * en + IN → en-IN (lakh/crore grouping), en + US → en-US, de + EU → de-DE.
 */
export function intlLocale(language: string, country?: string | null): string {
  const lang = (language || 'en').split('-')[0];
  if (lang === 'en' && country) return regionFor(country).locale;
  if (lang === 'es' && country === 'US') return 'es-US';
  const region = LANGUAGE_DEFAULT_REGION[lang] ?? 'IN';
  return `${lang}-${region}`;
}

export function formatNumber(
  value: number | null | undefined,
  locale = 'en-IN',
  options: Intl.NumberFormatOptions = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1, ...options }).format(value);
}

export function formatInteger(value: number | null | undefined, locale = 'en-IN'): string {
  return formatNumber(value, locale, { maximumFractionDigits: 0 });
}

export function formatDecimal(
  value: number | null | undefined,
  locale = 'en-IN',
  digits = 2,
): string {
  return formatNumber(value, locale, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatPercent(
  fraction: number | null | undefined,
  locale = 'en-IN',
  digits = 0,
): string {
  if (fraction === null || fraction === undefined || Number.isNaN(fraction)) return '—';
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: digits,
  }).format(fraction);
}

export function formatSignedPercent(
  pct: number | null | undefined,
  locale = 'en-IN',
  digits = 1,
): string {
  if (pct === null || pct === undefined || Number.isNaN(pct)) return '—';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${formatNumber(pct, locale, { maximumFractionDigits: digits })}%`;
}

/** Currency symbols come from the region config, never guessed from Intl. */
export function formatCurrency(
  value: number | null | undefined,
  symbol: string,
  locale = 'en-IN',
  digits = 0,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const n = new Intl.NumberFormat(locale, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
  return `${symbol}${n}`;
}

export function formatRange(range: Range | null | undefined, locale = 'en-IN', digits = 1): string {
  if (!range) return '—';
  return `${formatNumber(range.low, locale, { maximumFractionDigits: digits })} – ${formatNumber(range.high, locale, { maximumFractionDigits: digits })}`;
}

export function unitLabel(unit: string): string {
  // tCO2e/yr on the wire → tCO₂e/yr for humans. Units are never translated.
  return unit.replace('CO2', 'CO₂');
}

export interface AreaDisplay {
  primary: string;
  secondary: string;
  primaryUnit: AreaUnit;
  secondaryUnit: AreaUnit;
  primaryValue: number;
  secondaryValue: number;
}

export const AREA_UNIT_SHORT: Record<AreaUnit, string> = { hectare: 'ha', acre: 'ac' };

/**
 * Area per region: hectares primary for IN/EU, acres primary for US, with the
 * secondary unit returned for the small print. `override` lets Settings force a unit.
 */
export function formatArea(
  hectares: number,
  country: string,
  locale = 'en-IN',
  override: AreaUnit | 'auto' = 'auto',
): AreaDisplay {
  const region = regionFor(country);
  const primaryUnit: AreaUnit = override === 'auto' ? region.units.area : override;
  const secondaryUnit: AreaUnit = primaryUnit === 'hectare' ? 'acre' : 'hectare';
  const toUnit = (unit: AreaUnit) => (unit === 'hectare' ? hectares : hectares * ACRES_PER_HECTARE);
  const primaryValue = toUnit(primaryUnit);
  const secondaryValue = toUnit(secondaryUnit);
  return {
    primaryUnit,
    secondaryUnit,
    primaryValue,
    secondaryValue,
    primary: `${formatNumber(primaryValue, locale, { maximumFractionDigits: 2 })} ${AREA_UNIT_SHORT[primaryUnit]}`,
    secondary: `${formatNumber(secondaryValue, locale, { maximumFractionDigits: 2 })} ${AREA_UNIT_SHORT[secondaryUnit]}`,
  };
}

export function formatDate(iso: string | null | undefined, locale = 'en-IN'): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(d);
}

export function formatDateTime(iso: string | null | undefined, locale = 'en-IN'): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(d);
}

/** "2026-09" → "Sep 2026" in the given locale. */
export function monthLabel(
  yyyymm: string,
  locale = 'en-IN',
  style: 'short' | 'long' = 'short',
): string {
  const match = /^(\d{4})-(\d{2})/.exec(yyyymm);
  if (!match) return yyyymm;
  const d = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1));
  return new Intl.DateTimeFormat(locale, { year: 'numeric', month: style, timeZone: 'UTC' }).format(
    d,
  );
}

export function densityPerHa(treeCount: number, hectares: number): number {
  if (!hectares || hectares <= 0) return 0;
  return treeCount / hectares;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Localised country name for an ISO 3166-1 alpha-2 code ("ES" → "Spain" / "Spanien"); the code itself when unknown. */
export function countryName(code: string | null | undefined, language = 'en'): string {
  if (!code) return '';
  try {
    return new Intl.DisplayNames([language], { type: 'region' }).of(code.toUpperCase()) ?? code;
  } catch {
    return code;
  }
}
