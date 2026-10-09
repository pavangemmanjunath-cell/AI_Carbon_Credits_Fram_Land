/**
 * Pure helpers for the tree-age page: address-bar parameters, input checks, chart data, how a
 * rule's outcome looks, and how rules are grouped and ordered. No React, no network, no
 * translations (components pass `t` results in), so every rule here is unit-tested.
 *
 * Nothing here calculates carbon or decides eligibility: numbers and rules come from the API.
 */
import { EU_MEMBER_STATES, REGIONS } from '@/config/regions';
import type {
  AgeClassRange,
  CarbonRange,
  CreditOutlook,
  CurvePoint,
  RuleAmount,
  Subdivision,
  TreeAgeInputs,
  TreeAgeRequestBody,
  TreeAgeRule,
  TreeSetting,
} from '../types';

// ─── Limits (the same as the API's request schema) ───────────────────────────

export const AGE_MIN = 0;
export const AGE_MAX = 300;
/** The slider stops here; the number box accepts up to `AGE_MAX`. */
export const AGE_SLIDER_MAX = 150;
export const TREES_MIN = 1;
export const TREES_MAX = 1_000_000;
export const GIRTH_MIN = 10;
export const GIRTH_MAX = 2000;
export const DEFAULT_AGE = 30;
export const DEFAULT_TREES = 25;
export const DEFAULT_SETTING: TreeSetting = 'farm';
/** Wait this long after the last change before asking the API again. */
export const DEBOUNCE_MS = 400;

/** The three places the page offers. `any` only arrives from a hand-edited link. */
export const SETTING_CHOICES = ['farm', 'urban', 'forest'] as const;
const ALL_SETTINGS: readonly TreeSetting[] = ['farm', 'urban', 'forest', 'any'];

export const AGE_CLASS_IDS = ['young', 'mature', 'old', 'veteran'] as const;

/** India, the United States and the EU member states (which use the EU rules). */
export const TOP_COUNTRIES = ['IN', 'US'] as const;
export const SUPPORTED_COUNTRIES: readonly string[] = [...TOP_COUNTRIES, ...EU_MEMBER_STATES];

/** Address-bar parameter names. */
export const PARAM = {
  country: 'country',
  subdivision: 'subdivision',
  species: 'species',
  age: 'age',
  trees: 'trees',
  girth: 'girth',
  setting: 'setting',
} as const;

// ─── Reading what was typed ──────────────────────────────────────────────────

export type NumberProblem = 'empty' | 'not-a-number' | 'not-whole' | 'too-small' | 'too-big';
export type NumberCheck = { ok: true; value: number } | { ok: false; problem: NumberProblem };

/** A whole number from a text box: digits only, between `min` and `max`. */
export function checkWholeNumber(text: string, min: number, max: number): NumberCheck {
  const trimmed = text.trim();
  if (trimmed === '') return { ok: false, problem: 'empty' };
  if (/^[+-]?\d+[.,]\d+$/.test(trimmed)) return { ok: false, problem: 'not-whole' };
  if (!/^[+-]?\d+$/.test(trimmed)) return { ok: false, problem: 'not-a-number' };
  const value = Number.parseInt(trimmed, 10);
  if (value < min) return { ok: false, problem: 'too-small' };
  if (value > max) return { ok: false, problem: 'too-big' };
  return { ok: true, value };
}

export type GirthCheck =
  | { ok: true; value: number | null }
  | { ok: false; problem: 'not-a-number' | 'too-small' | 'too-big' };

/** The optional trunk girth: empty is fine (no measurement); otherwise 10–2000 cm. */
export function checkGirth(text: string): GirthCheck {
  const trimmed = text.trim();
  if (trimmed === '') return { ok: true, value: null };
  if (!/^\d+([.,]\d+)?$/.test(trimmed)) return { ok: false, problem: 'not-a-number' };
  const value = Number.parseFloat(trimmed.replace(',', '.'));
  if (value < GIRTH_MIN) return { ok: false, problem: 'too-small' };
  if (value > GIRTH_MAX) return { ok: false, problem: 'too-big' };
  return { ok: true, value };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

// ─── Address bar ↔ inputs ────────────────────────────────────────────────────

/**
 * Reads the inputs from the address bar. It never throws: anything missing or unreadable falls
 * back to a default, and numbers outside the allowed range are pulled back inside it, so a
 * hand-edited link always opens a page that can be calculated.
 */
export function parseTreeAgeParams(
  params: URLSearchParams,
  defaults: { country?: string | null } = {},
): TreeAgeInputs {
  const wantedCountry = (params.get(PARAM.country) ?? defaults.country ?? 'IN').toUpperCase();
  const country = SUPPORTED_COUNTRIES.includes(wantedCountry) ? wantedCountry : 'IN';

  const rawSubdivision = (params.get(PARAM.subdivision) ?? '').trim().toUpperCase();
  const subdivision =
    /^[A-Z]{2}-[A-Z0-9]{1,3}$/.test(rawSubdivision) && rawSubdivision.startsWith(`${country}-`)
      ? rawSubdivision
      : null;

  const rawSetting = (params.get(PARAM.setting) ?? '').trim().toLowerCase();
  const setting = ALL_SETTINGS.find((s) => s === rawSetting) ?? DEFAULT_SETTING;

  const rawSpecies = (params.get(PARAM.species) ?? '').trim();
  const speciesId = /^[A-Za-z0-9_-]{1,64}$/.test(rawSpecies) ? rawSpecies : null;

  return {
    country,
    subdivision,
    setting,
    speciesId,
    age: readWhole(params.get(PARAM.age), AGE_MIN, AGE_MAX, DEFAULT_AGE),
    trees: readWhole(params.get(PARAM.trees), TREES_MIN, TREES_MAX, DEFAULT_TREES),
    girthCm: readGirth(params.get(PARAM.girth)),
  };
}

function readWhole(raw: string | null, min: number, max: number, fallback: number): number {
  if (raw === null || !/^[+-]?\d+(\.\d+)?$/.test(raw.trim())) return fallback;
  return clamp(Math.trunc(Number.parseFloat(raw)), min, max);
}

function readGirth(raw: string | null): number | null {
  if (raw === null || !/^\d+(\.\d+)?$/.test(raw.trim())) return null;
  const value = Number.parseFloat(raw);
  return value >= GIRTH_MIN && value <= GIRTH_MAX ? value : null;
}

/**
 * Writes the inputs into address-bar parameters (all of them, so a copied link is complete).
 * Parameters that are not ours are kept as they were.
 */
export function toSearchParams(
  inputs: TreeAgeInputs,
  base: URLSearchParams = new URLSearchParams(),
): URLSearchParams {
  const next = new URLSearchParams(base);
  const put = (key: string, value: string | number | null) => {
    if (value === null || value === '') next.delete(key);
    else next.set(key, String(value));
  };
  put(PARAM.country, inputs.country);
  put(PARAM.subdivision, inputs.subdivision);
  put(PARAM.setting, inputs.setting);
  put(PARAM.species, inputs.speciesId);
  put(PARAM.age, inputs.age);
  put(PARAM.trees, inputs.trees);
  put(PARAM.girth, inputs.girthCm);
  return next;
}

// ─── Choices that depend on lists from the API ───────────────────────────────

/** The species named in the address if the list has it, otherwise the first species. */
export function resolveSpeciesId(
  wanted: string | null,
  species: readonly { id: string }[] | undefined,
): string | null {
  if (!species || species.length === 0) return wanted;
  if (wanted && species.some((s) => s.id === wanted)) return wanted;
  return species[0].id;
}

/**
 * Keeps a subdivision only when the API lists it for the country. While the list is still
 * loading the address-bar value is kept; a country without a list has no subdivision.
 */
export function resolveSubdivision(
  wanted: string | null,
  subdivisions: readonly Subdivision[] | undefined,
): string | null {
  if (!wanted) return null;
  if (!subdivisions) return wanted;
  return subdivisions.some((s) => s.code === wanted) ? wanted : null;
}

/** When the country changes, the old state or region is meaningless. */
export function withCountry(inputs: TreeAgeInputs, country: string): TreeAgeInputs {
  if (country === inputs.country) return inputs;
  return { ...inputs, country, subdivision: null };
}

// ─── The request ─────────────────────────────────────────────────────────────

export type InputProblem = 'species' | 'age' | 'trees' | 'girth' | 'country';

/** What is wrong with the inputs (empty when they can be sent). */
export function inputProblems(inputs: TreeAgeInputs): InputProblem[] {
  const problems: InputProblem[] = [];
  if (!SUPPORTED_COUNTRIES.includes(inputs.country)) problems.push('country');
  if (!inputs.speciesId) problems.push('species');
  if (!Number.isInteger(inputs.age) || inputs.age < AGE_MIN || inputs.age > AGE_MAX) {
    problems.push('age');
  }
  if (!Number.isInteger(inputs.trees) || inputs.trees < TREES_MIN || inputs.trees > TREES_MAX) {
    problems.push('trees');
  }
  if (inputs.girthCm !== null && (inputs.girthCm < GIRTH_MIN || inputs.girthCm > GIRTH_MAX)) {
    problems.push('girth');
  }
  return problems;
}

/**
 * The body for `POST /tree-age/assess`, or `null` while the inputs cannot be sent. A planned
 * tree (age 0) has no trunk yet, so its girth is left out. No plot, no coordinates.
 */
export function buildRequestBody(inputs: TreeAgeInputs): TreeAgeRequestBody | null {
  if (inputProblems(inputs).length > 0 || !inputs.speciesId) return null;
  return {
    country: inputs.country,
    subdivision: inputs.subdivision,
    setting: inputs.setting,
    species_id: inputs.speciesId,
    age_years: inputs.age,
    tree_count: inputs.trees,
    girth_cm: inputs.age >= 1 ? inputs.girthCm : null,
  };
}

/** The same body always gives the same key, so a debounce can compare them as text. */
export function requestKey(body: TreeAgeRequestBody | null): string | null {
  return body ? JSON.stringify(body) : null;
}

// ─── Numbers and names for display ───────────────────────────────────────────

/** More decimals for small numbers, so one young tree (0.012 t) never shows as "0". */
export function carbonDigits(value: number): number {
  const abs = Math.abs(value);
  if (abs >= 100) return 0;
  if (abs >= 10) return 1;
  if (abs >= 0.1) return 2;
  return 3;
}

export function formatCarbon(value: number, locale: string, digits = carbonDigits(value)): string {
  if (!Number.isFinite(value)) return '—';
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value);
}

export interface RangeText {
  central: string;
  low: string;
  high: string;
}

/** Low, central and high with the same number of decimals, chosen from the central value. */
export function formatRangeParts(range: CarbonRange, locale: string): RangeText {
  const digits = carbonDigits(range.central);
  return {
    central: formatCarbon(range.central, locale, digits),
    low: formatCarbon(range.low, locale, digits),
    high: formatCarbon(range.high, locale, digits),
  };
}

/** Short numbers for the chart axis: 1.5K (12L in en-IN) from a thousand up, else plain. */
export function formatAxisNumber(value: number, locale: string, decimals = 1): string {
  if (!Number.isFinite(value)) return '';
  if (Math.abs(value) >= 1000) {
    return new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(
      value,
    );
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: decimals }).format(value);
}

export interface NiceTicks {
  /** The gap between two labels. */
  step: number;
  /** The last label: the first round number at or above `max`. */
  top: number;
  ticks: number[];
  /** How many decimals the labels need, so 0.05 never shows as 0. */
  decimals: number;
}

/**
 * Round axis labels from 0 to just past `max`, at most `maxIntervals` gaps apart: steps of 1, 2,
 * 2.5 or 5 times a power of ten, so an axis reads 0, 50, 100, 150 and never 129.6.
 * `wholeNumbers` leaves out steps below 1 and the 2.5 step (for ages).
 */
export function niceTicks(max: number, maxIntervals = 5, wholeNumbers = false): NiceTicks {
  if (!Number.isFinite(max) || max <= 0) return { step: 1, top: 1, ticks: [0, 1], decimals: 0 };
  const rough = max / Math.max(1, maxIntervals);
  const power = Math.floor(Math.log10(rough));
  const multipliers = wholeNumbers ? [1, 2, 5, 10] : [1, 2, 2.5, 5, 10];
  const multiplier =
    multipliers.find((m) => m * 10 ** power >= rough * (1 - 1e-9)) ??
    multipliers[multipliers.length - 1];
  let step = multiplier * 10 ** power;
  if (wholeNumbers && step < 1) step = 1;
  const decimals = wholeNumbers ? 0 : Math.max(0, -power + (multiplier === 2.5 ? 1 : 0));
  const count = Math.ceil(max / step - 1e-9);
  const ticks = Array.from({ length: count + 1 }, (_, i) => Number((i * step).toFixed(decimals)));
  return { step, top: ticks[ticks.length - 1], ticks, decimals };
}

export function regionName(code: string, locale: string): string {
  try {
    return new Intl.DisplayNames([locale], { type: 'region' }).of(code) ?? code;
  } catch {
    return code;
  }
}

export interface CountryOption {
  code: string;
  name: string;
}

/** India and the United States first, then the EU members, each group sorted by name. */
export function countryOptions(locale: string): { top: CountryOption[]; eu: CountryOption[] } {
  const named = (code: string): CountryOption => ({ code, name: regionName(code, locale) });
  const byName = (a: CountryOption, b: CountryOption) => a.name.localeCompare(b.name, locale);
  return {
    top: TOP_COUNTRIES.map(named),
    eu: EU_MEMBER_STATES.map(named).sort(byName),
  };
}

/** "tree_cover_share" → "Tree cover share"; used when a label has no translation. */
export function humanize(key: string): string {
  const spaced = key.replace(/[_-]+/g, ' ').trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : key;
}

export function isAgeClassId(id: string): id is (typeof AGE_CLASS_IDS)[number] {
  return (AGE_CLASS_IDS as readonly string[]).includes(id);
}

/** Years that make up an age class, from the rules endpoint; `null` when it does not say. */
export function ageClassSpan(
  id: string,
  classes: readonly AgeClassRange[] | undefined,
): { min: number; max: number | null } | null {
  const found = classes?.find((c) => c.id === id);
  if (!found || !Number.isFinite(found.min_age)) return null;
  return { min: found.min_age, max: found.max_age ?? null };
}

// ─── The credit outlook sentence ─────────────────────────────────────────────

export type OutlookKey = 'planned' | 'not-eligible' | 'conditional' | 'eligible';

/**
 * Which ready-made sentence matches the API's verdict. Trees that are only planned (age 0) have
 * their own sentence. `null` for a verdict this page does not know: the caller then shows the
 * API's own sentence.
 */
export function outlookKey(outlook: CreditOutlook, ageYears: number): OutlookKey | null {
  if (ageYears === 0) return 'planned';
  const kind: string = outlook.existing_trees;
  return kind === 'not-eligible' || kind === 'conditional' || kind === 'eligible' ? kind : null;
}

// ─── Chart ───────────────────────────────────────────────────────────────────

export interface ChartPoint {
  age: number;
  stored: number;
  low: number;
  high: number;
  /** `[low, high]`, the shaded band. */
  band: [number, number];
  annual: number;
}

/** Curve points in age order, with the band ordered low → high and no broken numbers. */
export function curveToChartData(curve: readonly CurvePoint[] | null | undefined): ChartPoint[] {
  const points: ChartPoint[] = [];
  for (const point of curve ?? []) {
    const values = [point.age, point.stored, point.stored_low, point.stored_high, point.annual];
    if (!values.every((v) => typeof v === 'number' && Number.isFinite(v))) continue;
    const low = Math.min(point.stored_low, point.stored_high, point.stored);
    const high = Math.max(point.stored_low, point.stored_high, point.stored);
    points.push({
      age: point.age,
      stored: point.stored,
      low,
      high,
      band: [low, high],
      annual: point.annual,
    });
  }
  return points.sort((a, b) => a.age - b.age);
}

/** The curve point at (or nearest to) an age. */
export function pointAtAge(data: readonly ChartPoint[], age: number): ChartPoint | null {
  let best: ChartPoint | null = null;
  for (const point of data) {
    if (best === null || Math.abs(point.age - age) < Math.abs(best.age - age)) best = point;
  }
  return best;
}

/** A handful of points for a screen-reader table: evenly spaced, plus the current age. */
export function sampleCurve(
  data: readonly ChartPoint[],
  currentAge: number,
  maxRows = 10,
): ChartPoint[] {
  if (data.length <= maxRows) return [...data];
  const chosen = new Set<ChartPoint>();
  for (let i = 0; i < maxRows; i += 1) {
    chosen.add(data[Math.round((i * (data.length - 1)) / (maxRows - 1))]);
  }
  const current = pointAtAge(data, currentAge);
  if (current) chosen.add(current);
  return [...chosen].sort((a, b) => a.age - b.age);
}

// ─── Rules ───────────────────────────────────────────────────────────────────

export type OutcomeTone = 'rose' | 'green' | 'amber' | 'blue' | 'violet' | 'grey';
export type OutcomeIcon = 'x' | 'check' | 'help' | 'shield' | 'coins' | 'minus';

export interface OutcomeStyle {
  tone: OutcomeTone;
  icon: OutcomeIcon;
  /** Translation key suffix under `treeAge.outcome`. */
  labelKey: string;
}

const OUTCOME_STYLES: Record<string, OutcomeStyle> = {
  'not-eligible': { tone: 'rose', icon: 'x', labelKey: 'not-eligible' },
  eligible: { tone: 'green', icon: 'check', labelKey: 'eligible' },
  conditional: { tone: 'amber', icon: 'help', labelKey: 'conditional' },
  protected: { tone: 'blue', icon: 'shield', labelKey: 'protected' },
  payment: { tone: 'violet', icon: 'coins', labelKey: 'payment' },
  'not-applicable': { tone: 'grey', icon: 'minus', labelKey: 'not-applicable' },
};

/** Colour, icon and label for an outcome. Every outcome has its own colour AND icon AND word. */
export function outcomeStyle(outcome: string | null | undefined): OutcomeStyle {
  return (
    (outcome && OUTCOME_STYLES[outcome]) || { tone: 'grey', icon: 'minus', labelKey: 'unknown' }
  );
}

/** Which outcome to show: the one for these trees, else the rule's own. */
export function outcomeOf(
  rule: Pick<TreeAgeRule, 'outcome_for_you' | 'outcome_for_existing_trees'>,
) {
  return rule.outcome_for_you || rule.outcome_for_existing_trees || 'not-applicable';
}

export const CATEGORY_ORDER = [
  'carbon-credit-eligibility',
  'incentive-payment',
  'tree-protection',
  'compensatory-planting',
  'methodology-note',
] as const;

/** Anything but an explicit "verified" is shown as not yet verified, never as confirmed. */
export function verificationOf(
  rule: Pick<TreeAgeRule, 'verification_status'>,
): 'verified' | 'pending' {
  return rule.verification_status === 'verified' ? 'verified' : 'pending';
}

/** Is the rule written for an age range (so it matters at this age in particular)? */
export function isAgeSpecific(rule: Pick<TreeAgeRule, 'applies_to'>): boolean {
  const { min_age_years: min, max_age_years: max } = rule.applies_to ?? {};
  return (min ?? null) !== null || (max ?? null) !== null;
}

/** 4 city · 3 state · 2 country · 1 region (IN, US, EU) · 0 worldwide. */
export function ruleSpecificity(
  rule: Pick<TreeAgeRule, 'locality' | 'subdivision' | 'country' | 'scope'>,
) {
  if (rule.locality) return 4;
  if (rule.subdivision) return 3;
  if (rule.country) return 2;
  return rule.scope === 'GLOBAL' ? 0 : 1;
}

function categoryRank(category: string): number {
  const index = (CATEGORY_ORDER as readonly string[]).indexOf(category);
  return index === -1 ? CATEGORY_ORDER.length : index;
}

/**
 * Most relevant first: rules written for an age range, then the most local rules, then by kind
 * of rule (credits, payments, protection, replanting, notes), then by name. Stable and pure.
 */
export function sortRules(rules: readonly TreeAgeRule[]): TreeAgeRule[] {
  return [...rules].sort(
    (a, b) =>
      Number(isAgeSpecific(b)) - Number(isAgeSpecific(a)) ||
      ruleSpecificity(b) - ruleSpecificity(a) ||
      categoryRank(a.category) - categoryRank(b.category) ||
      a.name.localeCompare(b.name) ||
      a.id.localeCompare(b.id),
  );
}

/** Rules that apply to these trees, and the others the API still listed (with their reason). */
export function splitRules(rules: readonly TreeAgeRule[]): {
  applying: TreeAgeRule[];
  other: TreeAgeRule[];
} {
  return {
    applying: sortRules(rules.filter((rule) => rule.applies)),
    other: sortRules(rules.filter((rule) => !rule.applies)),
  };
}

// ─── Rule amounts ────────────────────────────────────────────────────────────

const AMOUNT_UNITS: Record<string, string> = {
  'per tree per year': 'perTreePerYear',
  'per tree': 'perTree',
  'per year': 'perYear',
  'per hectare': 'perHectare',
  'per hectare per year': 'perHectarePerYear',
};

/** Translation key suffix for a known unit text, or `null` (then the text is shown as written). */
export function amountUnitKey(unit: string | null | undefined): string | null {
  return (unit && AMOUNT_UNITS[unit.trim().toLowerCase()]) || null;
}

/** "₹3,000": the symbol comes from the region config, never from Intl. */
export function formatAmountValue(amount: RuleAmount, locale: string): string {
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(amount.value);
  const region = REGIONS.find((r) => r.currency === amount.currency);
  return region ? `${region.currency_symbol}${number}` : `${amount.currency} ${number}`;
}

// ─── Links ───────────────────────────────────────────────────────────────────

/** Only http(s) addresses become links. */
export function safeHttpUrl(url: unknown): string | null {
  if (typeof url !== 'string' || !url.trim()) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? url : null;
  } catch {
    return null;
  }
}
