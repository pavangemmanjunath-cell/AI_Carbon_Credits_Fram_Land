/**
 * Small deterministic fixtures shaped like the API's responses (tests only; never imported by
 * production code). Carbon numbers are illustrative test values, not real estimates; the rules
 * are abridged copies of entries in config/tree-age/rules.yaml.
 */
import type { Species } from '@/types/api';
import type {
  CurvePoint,
  Subdivision,
  TreeAgeAssessment,
  TreeAgeRule,
  TreeAgeRulesInfo,
} from './types';

const round3 = (value: number) => Math.round(value * 1000) / 1000;

/**
 * The curve for `trees` trees (the API's curve is for the whole group, on the same scale as
 * `stored_now`): one tree holds 0.06 t CO2e per year of age plus a little more as it grows.
 */
export function curveFixture(maxAge: number, trees = 1): CurvePoint[] {
  return Array.from({ length: maxAge + 1 }, (_, age) => {
    const stored = round3((0.06 * age + 0.0012 * age * age) * trees);
    return {
      age,
      stored,
      stored_low: round3(stored * 0.8),
      stored_high: round3(stored * 1.2),
      annual: round3((0.06 + 0.0024 * age) * trees),
    };
  });
}

type RuleOverrides = Partial<TreeAgeRule> & Pick<TreeAgeRule, 'id' | 'name'>;

export function ruleFixture(overrides: RuleOverrides): TreeAgeRule {
  return {
    scope: 'GLOBAL',
    country: null,
    subdivision: null,
    locality: null,
    authority: 'Test Authority',
    category: 'carbon-credit-eligibility',
    applies_to: { min_age_years: null, max_age_years: null, trees: 'any', setting: 'any' },
    outcome_for_existing_trees: 'conditional',
    outcome_for_you: 'conditional',
    summary: 'A short plain-language summary.',
    amount: null,
    status: 'in-force',
    is_example: false,
    sources: [
      {
        title: 'Official page',
        publisher: 'Test Publisher',
        url: 'https://example.org/rule',
        accessed: '2026-10-05',
      },
    ],
    verification_status: 'verified',
    applies: true,
    why: 'Applies worldwide at any age',
    ...overrides,
  };
}

export const rulesFixture: TreeAgeRule[] = [
  ruleFixture({
    id: 'global-verra-vm0047-arr',
    name: 'Verra VM0047 Afforestation, Reforestation and Revegetation',
    authority: 'Verra',
    outcome_for_existing_trees: 'not-eligible',
    outcome_for_you: 'not-eligible',
    applies_to: { min_age_years: null, max_age_years: null, trees: 'new-planting', setting: 'any' },
    summary: 'VM0047 credits trees that a project plants; trees that already stand earn nothing.',
  }),
  ruleFixture({
    id: 'global-icvcm-ccp-additionality',
    name: 'ICVCM Core Carbon Principles: additionality',
    authority: 'Integrity Council for the Voluntary Carbon Market',
    category: 'methodology-note',
    summary: 'Growth that would happen anyway is not additional.',
  }),
  ruleFixture({
    id: 'in-hr-pran-vayu-devta-pension',
    name: 'Haryana Pran Vayu Devta Pension Scheme',
    authority: 'Government of Haryana',
    scope: 'IN',
    country: 'IN',
    subdivision: 'IN-HR',
    category: 'incentive-payment',
    outcome_for_existing_trees: 'payment',
    outcome_for_you: 'payment',
    applies: false,
    why: 'Only in Haryana (IN-HR)',
    applies_to: {
      min_age_years: 75,
      max_age_years: null,
      trees: 'existing',
      setting: 'non-forest',
    },
    amount: { value: 3000, currency: 'INR', unit: 'per tree per year', as_of: '2026-07' },
    verification_status: 'pending',
    summary: 'A yearly pension for owners of trees aged 75 years or more.',
  }),
  ruleFixture({
    id: 'in-ka-preservation-of-trees-act',
    name: 'Karnataka Preservation of Trees Act, 1976',
    authority: 'Government of Karnataka',
    scope: 'IN',
    country: 'IN',
    subdivision: 'IN-KA',
    category: 'tree-protection',
    outcome_for_existing_trees: 'protected',
    outcome_for_you: 'protected',
    why: 'Applies in Karnataka (IN-KA) at any age',
    summary: 'Felling trees needs permission from the tree officer.',
  }),
  ruleFixture({
    id: 'in-ccts-offset-bm-fr05-002',
    name: 'Carbon Credit Trading Scheme offset mechanism: BM FR05.002',
    authority: 'Bureau of Energy Efficiency',
    scope: 'IN',
    country: 'IN',
    applies_to: { min_age_years: null, max_age_years: null, trees: 'new-planting', setting: 'any' },
    outcome_for_existing_trees: 'not-eligible',
    outcome_for_you: 'not-eligible',
    why: 'Applies in India at any age',
  }),
  ruleFixture({
    id: 'us-or-portland-heritage-trees',
    name: 'Portland heritage trees',
    authority: 'City of Portland',
    scope: 'US',
    country: 'US',
    subdivision: 'US-OR',
    locality: 'Portland',
    category: 'tree-protection',
    outcome_for_existing_trees: 'protected',
    outcome_for_you: 'protected',
    is_example: true,
    applies: false,
    why: 'Municipal example for Portland (US-OR); check your own city’s rules',
  }),
];

export const subdivisionsFixture: Subdivision[] = [
  { code: 'IN-KA', name: 'Karnataka', type: 'state' },
  { code: 'IN-HR', name: 'Haryana', type: 'state' },
  { code: 'IN-DL', name: 'Delhi', type: 'union-territory' },
];

export const rulesInfoFixture: TreeAgeRulesInfo = {
  version: '0.1.0',
  updated: '2026-10-05',
  disclaimer:
    'Screening information only — not legal advice. Rules change; confirm with the responsible authority before acting.',
  age_classes: [
    { id: 'young', label: 'Young (0–20 years)', min_age: 0, max_age: 20 },
    { id: 'mature', label: 'Mature (21–49 years)', min_age: 21, max_age: 49 },
    { id: 'old', label: 'Old (50–74 years)', min_age: 50, max_age: 74 },
    { id: 'veteran', label: 'Veteran (75+ years)', min_age: 75, max_age: null },
  ],
  subdivision_label: 'State or union territory',
  subdivisions: subdivisionsFixture,
};

export const speciesFixture = [
  { id: 'mango', common_name: 'Mango', scientific_name: 'Mangifera indica', regions: ['IN'] },
  { id: 'teak', common_name: 'Teak', scientific_name: 'Tectona grandis', regions: ['IN'] },
  { id: 'neem', common_name: 'Neem', scientific_name: 'Azadirachta indica', regions: ['IN'] },
] as unknown as Species[];

export const usSpeciesFixture = [
  {
    id: 'black_walnut',
    common_name: 'Black walnut',
    scientific_name: 'Juglans nigra',
    regions: ['US'],
  },
  { id: 'pecan', common_name: 'Pecan', scientific_name: 'Carya illinoinensis', regions: ['US'] },
] as unknown as Species[];

export function assessmentFixture(
  overrides: Partial<TreeAgeAssessment> & { age?: number; trees?: number } = {},
): TreeAgeAssessment {
  const { age = 30, trees = 25, ...rest } = overrides;
  const curve = curveFixture(Math.max(age + 20, 40), trees);
  const here = curve.find((p) => p.age === age) ?? curve[0];
  return {
    inputs: {
      country: 'IN',
      region: 'IN',
      subdivision: null,
      setting: 'farm',
      species_id: 'mango',
      age_years: age,
      tree_count: trees,
      girth_cm: null,
    },
    age_class:
      age <= 20
        ? { id: 'young', label: 'Young (0–20 years)' }
        : age <= 49
          ? { id: 'mature', label: 'Mature (21–49 years)' }
          : age <= 74
            ? { id: 'old', label: 'Old (50–74 years)' }
            : { id: 'veteran', label: 'Veteran (75+ years)' },
    climate_zone: 'tropical_dry',
    climate_zone_label: 'Tropical dry',
    climate_zone_source: 'region default (IN)',
    carbon: {
      method: 'tier1-age',
      curve_method: 'tier1-age',
      stored_now: {
        low: here.stored_low,
        central: here.stored,
        high: here.stored_high,
        unit: 'tCO2e',
      },
      annual_now: {
        low: round3(here.annual * 0.8),
        central: here.annual,
        high: round3(here.annual * 1.2),
        unit: 'tCO2e/yr',
      },
      per_tree: {
        stored_now_kg_co2e: Math.round((here.stored / trees) * 1000),
        annual_now_kg_co2e: Math.round((here.annual / trees) * 1000),
      },
      curve,
      confidence: 'low',
      parameters_used: [
        {
          name: 'growth_rate',
          value: 1.2,
          unit: 'tC/ha/yr',
          source: 'IPCC 2006',
          verification_status: 'verified',
        },
        {
          name: 'root_to_shoot',
          value: 0.24,
          unit: 'ratio',
          source: 'IPCC 2006',
          verification_status: 'pending',
        },
      ],
      notes: ['Nothing about the actual trees is measured, so confidence is low.'],
    },
    credit_outlook: {
      existing_trees: age === 0 ? 'conditional' : 'not-eligible',
      summary:
        age === 0
          ? 'Newly planted trees can earn removal credits only through a project that meets a programme’s rules.'
          : 'Trees that already stand usually do not earn removal credits under the rules that apply here, because credits reward carbon added by new planting, not carbon already stored.',
      based_on_rule_ids: ['global-verra-vm0047-arr', 'in-ccts-offset-bm-fr05-002'],
    },
    rules: rulesFixture,
    certified: false,
    disclaimer:
      'Screening information only — not legal advice. Rules change; confirm with the responsible authority before acting. Scenario estimate only. This is not an issued carbon credit.',
    ...rest,
  };
}
