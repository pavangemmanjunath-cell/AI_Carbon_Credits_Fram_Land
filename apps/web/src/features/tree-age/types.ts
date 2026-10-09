/**
 * Types for the tree-age endpoints (`GET /tree-age/rules`, `POST /tree-age/assess`). They mirror
 * the "Tree age" section of docs/architecture/api-contract.md and the response of the API
 * (`apps/api/app/services/tree_age.py`). Field names stay snake_case exactly as on the wire; the
 * page's own state uses camelCase (`TreeAgeInputs`).
 */

/** Where the trees stand. `any` means "not stated": it never hides a rule. */
export type TreeSetting = 'farm' | 'urban' | 'forest' | 'any';

/** What the person edits on the page. The address bar holds exactly these values. */
export interface TreeAgeInputs {
  /** ISO 3166-1 alpha-2, e.g. `IN`. */
  country: string;
  /** ISO 3166-2, e.g. `IN-KA`; `null` = "Not sure". */
  subdivision: string | null;
  setting: TreeSetting;
  /** `null` until the species list has loaded and no species is named in the address. */
  speciesId: string | null;
  /** Whole years, 0 = "I am planning new trees". */
  age: number;
  trees: number;
  /** Trunk circumference at 1.3 m, in cm. Optional. */
  girthCm: number | null;
}

// ─── POST /tree-age/assess ───────────────────────────────────────────────────

export interface TreeAgeRequestBody {
  country: string;
  subdivision: string | null;
  setting: TreeSetting;
  species_id: string;
  age_years: number;
  tree_count: number;
  girth_cm: number | null;
}

export interface CarbonRange {
  low: number;
  central: number;
  high: number;
  /** `tCO2e` or `tCO2e/yr`. */
  unit: string;
}

/** One age on the curve: stored carbon with its range, and the removal in that year. */
export interface CurvePoint {
  age: number;
  stored: number;
  stored_low: number;
  stored_high: number;
  annual: number;
}

export interface ParameterUsed {
  name: string;
  value: unknown;
  unit: string;
  source: string;
  verification_status: string;
}

export type CarbonMethod = 'tier1-age' | 'tier2-girth';

export interface TreeAgeCarbon {
  method: CarbonMethod | (string & {});
  curve_method: string | null;
  stored_now: CarbonRange;
  annual_now: CarbonRange;
  per_tree: { stored_now_kg_co2e: number | null; annual_now_kg_co2e: number | null };
  curve: CurvePoint[];
  confidence: string | null;
  parameters_used: ParameterUsed[];
  notes: string[];
}

export interface AgeClass {
  id: string;
  label: string;
}

/** What the applicable carbon-credit rules say about trees that already stand. */
export type CreditOutlookKind = 'not-eligible' | 'conditional' | 'eligible';

export interface CreditOutlook {
  existing_trees: CreditOutlookKind | (string & {});
  summary: string;
  based_on_rule_ids: string[];
}

export type RuleOutcome =
  'not-eligible' | 'eligible' | 'conditional' | 'protected' | 'payment' | 'not-applicable';

export type RuleCategory =
  | 'carbon-credit-eligibility'
  | 'incentive-payment'
  | 'tree-protection'
  | 'compensatory-planting'
  | 'methodology-note';

export interface RuleSource {
  title: string;
  publisher: string | null;
  url: string | null;
  accessed: string | null;
}

export interface RuleAmount {
  value: number;
  /** ISO 4217, e.g. `INR`. */
  currency: string;
  /** e.g. `per tree per year`. */
  unit: string;
  /** `YYYY-MM` or `YYYY-MM-DD`. */
  as_of: string | null;
}

export interface RuleAppliesTo {
  min_age_years: number | null;
  max_age_years: number | null;
  trees: 'any' | 'new-planting' | 'existing' | (string & {});
  setting: 'any' | 'non-forest' | 'forest' | 'urban' | (string & {});
}

export interface TreeAgeRule {
  id: string;
  scope: 'GLOBAL' | 'IN' | 'US' | 'EU' | (string & {});
  country: string | null;
  subdivision: string | null;
  locality: string | null;
  name: string;
  authority: string;
  category: RuleCategory | (string & {});
  applies_to: RuleAppliesTo;
  outcome_for_existing_trees: RuleOutcome | (string & {});
  /** The outcome for these trees (`not-applicable` when the trees are only planned). */
  outcome_for_you: RuleOutcome | (string & {});
  summary: string;
  amount: RuleAmount | null;
  /** `in-force`, `proposed`, … */
  status: string;
  is_example: boolean;
  sources: RuleSource[];
  /** `verified` or `pending`. */
  verification_status: string;
  /** Does this rule apply to the trees described? Rules that do not are still listed. */
  applies: boolean;
  /** In plain words, why the rule does or does not apply. */
  why: string;
}

export interface TreeAgeAssessment {
  inputs: {
    country: string;
    region: string | null;
    subdivision: string | null;
    setting: TreeSetting;
    species_id: string;
    age_years: number;
    tree_count: number;
    girth_cm: number | null;
  };
  age_class: AgeClass;
  climate_zone: string | null;
  climate_zone_label: string | null;
  climate_zone_source: string | null;
  carbon: TreeAgeCarbon;
  credit_outlook: CreditOutlook;
  rules: TreeAgeRule[];
  /** Always `false`: an estimate is never an issued credit. */
  certified: false;
  disclaimer: string;
}

// ─── GET /tree-age/rules ─────────────────────────────────────────────────────

export interface AgeClassRange extends AgeClass {
  min_age: number;
  max_age: number | null;
}

export interface Subdivision {
  code: string;
  name: string;
  type: string;
}

export interface TreeAgeRulesInfo {
  version: string;
  updated: string;
  disclaimer: string;
  age_classes: AgeClassRange[];
  /** e.g. "State or union territory"; `null` when the country has no list. */
  subdivision_label: string | null;
  subdivisions: Subdivision[];
}

/** The raw wire shapes: everything optional, so a thin or older API cannot break the page. */
export type RawAssessment = Partial<Omit<TreeAgeAssessment, 'carbon' | 'rules'>> & {
  carbon?: Partial<TreeAgeCarbon> | null;
  rules?: Partial<TreeAgeRule>[] | null;
};
export type RawRulesInfo = Partial<TreeAgeRulesInfo> | null;
