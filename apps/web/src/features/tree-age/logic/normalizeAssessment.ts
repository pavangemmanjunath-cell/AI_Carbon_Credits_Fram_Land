/**
 * Turns the API's JSON into the shapes the page uses, filling gaps with safe defaults so a thin
 * or older response cannot crash a render. Two rules are deliberate: `certified` is always
 * `false` (an estimate is never an issued credit), and a rule counts as verified only when the
 * API says `verified` outright.
 */
import type {
  AgeClassRange,
  CarbonRange,
  CurvePoint,
  ParameterUsed,
  RawAssessment,
  RawRulesInfo,
  RuleAmount,
  RuleAppliesTo,
  RuleSource,
  Subdivision,
  TreeAgeAssessment,
  TreeAgeCarbon,
  TreeAgeRule,
  TreeAgeRulesInfo,
  TreeSetting,
} from '../types';

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function textOrNull(value: unknown): string | null {
  return typeof value === 'string' && value !== '' ? value : null;
}

function number(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function list<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function range(value: unknown, unit: string): CarbonRange {
  const raw = (value ?? {}) as Partial<CarbonRange>;
  return {
    low: number(raw.low),
    central: number(raw.central),
    high: number(raw.high),
    unit: text(raw.unit, unit),
  };
}

function curvePoint(raw: unknown): CurvePoint {
  const point = (raw ?? {}) as Partial<CurvePoint>;
  return {
    age: number(point.age, Number.NaN),
    stored: number(point.stored, Number.NaN),
    stored_low: number(point.stored_low, Number.NaN),
    stored_high: number(point.stored_high, Number.NaN),
    annual: number(point.annual, Number.NaN),
  };
}

function carbon(raw: RawAssessment['carbon']): TreeAgeCarbon {
  const block = raw ?? {};
  const perTree = block.per_tree ?? { stored_now_kg_co2e: null, annual_now_kg_co2e: null };
  return {
    method: text(block.method, 'tier1-age'),
    curve_method: textOrNull(block.curve_method),
    stored_now: range(block.stored_now, 'tCO2e'),
    annual_now: range(block.annual_now, 'tCO2e/yr'),
    per_tree: {
      stored_now_kg_co2e: numberOrNull(perTree.stored_now_kg_co2e),
      annual_now_kg_co2e: numberOrNull(perTree.annual_now_kg_co2e),
    },
    curve: list(block.curve).map(curvePoint),
    confidence: textOrNull(block.confidence),
    parameters_used: list<Partial<ParameterUsed>>(block.parameters_used).map((p) => ({
      name: text(p.name),
      value: p.value,
      unit: text(p.unit),
      source: text(p.source),
      verification_status: text(p.verification_status, 'pending'),
    })),
    notes: list<unknown>(block.notes).filter((n): n is string => typeof n === 'string'),
  };
}

function source(raw: Partial<RuleSource> | null | undefined): RuleSource {
  return {
    title: text(raw?.title),
    publisher: textOrNull(raw?.publisher),
    url: textOrNull(raw?.url),
    accessed: textOrNull(raw?.accessed),
  };
}

function amount(raw: Partial<RuleAmount> | null | undefined): RuleAmount | null {
  if (!raw || typeof raw.value !== 'number' || !Number.isFinite(raw.value)) return null;
  return {
    value: raw.value,
    currency: text(raw.currency),
    unit: text(raw.unit),
    as_of: textOrNull(raw.as_of),
  };
}

function rule(raw: Partial<TreeAgeRule>): TreeAgeRule {
  const own = text(raw.outcome_for_existing_trees, 'not-applicable');
  const appliesTo: Partial<RuleAppliesTo> = raw.applies_to ?? {};
  return {
    id: text(raw.id),
    scope: text(raw.scope, 'GLOBAL'),
    country: textOrNull(raw.country),
    subdivision: textOrNull(raw.subdivision),
    locality: textOrNull(raw.locality),
    name: text(raw.name),
    authority: text(raw.authority),
    category: text(raw.category),
    applies_to: {
      min_age_years: numberOrNull(appliesTo.min_age_years),
      max_age_years: numberOrNull(appliesTo.max_age_years),
      trees: text(appliesTo.trees, 'any'),
      setting: text(appliesTo.setting, 'any'),
    },
    outcome_for_existing_trees: own,
    outcome_for_you: text(raw.outcome_for_you, own),
    summary: text(raw.summary),
    amount: amount(raw.amount),
    status: text(raw.status, 'in-force'),
    is_example: raw.is_example === true,
    sources: list<Partial<RuleSource>>(raw.sources).map(source),
    // Unknown is never "verified".
    verification_status: text(raw.verification_status, 'pending'),
    applies: raw.applies !== false,
    why: text(raw.why),
  };
}

export function normalizeAssessment(raw: RawAssessment): TreeAgeAssessment {
  const inputs = raw.inputs ?? ({} as Partial<TreeAgeAssessment['inputs']>);
  const outlook = raw.credit_outlook ?? { existing_trees: '', summary: '', based_on_rule_ids: [] };
  return {
    inputs: {
      country: text(inputs.country),
      region: textOrNull(inputs.region),
      subdivision: textOrNull(inputs.subdivision),
      setting: text(inputs.setting, 'any') as TreeSetting,
      species_id: text(inputs.species_id),
      age_years: number(inputs.age_years),
      tree_count: number(inputs.tree_count),
      girth_cm: numberOrNull(inputs.girth_cm),
    },
    age_class: { id: text(raw.age_class?.id), label: text(raw.age_class?.label) },
    climate_zone: textOrNull(raw.climate_zone),
    climate_zone_label: textOrNull(raw.climate_zone_label),
    climate_zone_source: textOrNull(raw.climate_zone_source),
    carbon: carbon(raw.carbon),
    credit_outlook: {
      existing_trees: text(outlook.existing_trees),
      summary: text(outlook.summary),
      based_on_rule_ids: list<unknown>(outlook.based_on_rule_ids).filter(
        (id): id is string => typeof id === 'string',
      ),
    },
    rules: list<Partial<TreeAgeRule>>(raw.rules).map(rule),
    certified: false,
    disclaimer: text(raw.disclaimer),
  };
}

export function normalizeRulesInfo(raw: RawRulesInfo | undefined): TreeAgeRulesInfo {
  const info = raw ?? {};
  return {
    version: text(info.version),
    updated: text(info.updated),
    disclaimer: text(info.disclaimer),
    age_classes: list<Partial<AgeClassRange>>(info.age_classes)
      .filter((c) => typeof c.id === 'string' && typeof c.min_age === 'number')
      .map((c) => ({
        id: text(c.id),
        label: text(c.label),
        min_age: number(c.min_age),
        max_age: numberOrNull(c.max_age),
      })),
    subdivision_label: textOrNull(info.subdivision_label),
    subdivisions: list<Partial<Subdivision>>(info.subdivisions)
      .filter((s) => typeof s.code === 'string' && typeof s.name === 'string')
      .map((s) => ({ code: text(s.code), name: text(s.name), type: text(s.type) })),
  };
}
