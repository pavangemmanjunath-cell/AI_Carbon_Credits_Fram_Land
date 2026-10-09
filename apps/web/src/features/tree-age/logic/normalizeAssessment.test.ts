import { describe, expect, it } from 'vitest';
import { assessmentFixture, ruleFixture, rulesInfoFixture } from '../fixtures';
import type { RawAssessment } from '../types';
import { normalizeAssessment, normalizeRulesInfo } from './normalizeAssessment';

describe('normalizeAssessment', () => {
  it('keeps a complete response as it is', () => {
    const complete = assessmentFixture({ age: 30 });
    const result = normalizeAssessment(complete as RawAssessment);
    expect(result.inputs).toEqual(complete.inputs);
    expect(result.age_class).toEqual({ id: 'mature', label: 'Mature (21–49 years)' });
    expect(result.carbon.stored_now).toEqual(complete.carbon.stored_now);
    expect(result.carbon.annual_now).toEqual(complete.carbon.annual_now);
    expect(result.carbon.curve).toHaveLength(complete.carbon.curve.length);
    expect(result.carbon.method).toBe('tier1-age');
    expect(result.credit_outlook.based_on_rule_ids).toEqual(
      complete.credit_outlook.based_on_rule_ids,
    );
    expect(result.rules).toHaveLength(complete.rules.length);
    expect(result.disclaimer).toBe(complete.disclaimer);
  });

  it('never reports an estimate as certified, whatever the response says', () => {
    const lying = { ...assessmentFixture(), certified: true } as unknown as RawAssessment;
    expect(normalizeAssessment(lying).certified).toBe(false);
    expect(normalizeAssessment({}).certified).toBe(false);
  });

  it('survives an empty response with safe defaults', () => {
    const result = normalizeAssessment({});
    expect(result.inputs).toMatchObject({
      country: '',
      region: null,
      subdivision: null,
      setting: 'any',
      age_years: 0,
      tree_count: 0,
      girth_cm: null,
    });
    expect(result.age_class).toEqual({ id: '', label: '' });
    expect(result.carbon.stored_now).toEqual({ low: 0, central: 0, high: 0, unit: 'tCO2e' });
    expect(result.carbon.annual_now.unit).toBe('tCO2e/yr');
    expect(result.carbon.curve).toEqual([]);
    expect(result.carbon.parameters_used).toEqual([]);
    expect(result.carbon.notes).toEqual([]);
    expect(result.carbon.per_tree).toEqual({ stored_now_kg_co2e: null, annual_now_kg_co2e: null });
    expect(result.credit_outlook).toEqual({
      existing_trees: '',
      summary: '',
      based_on_rule_ids: [],
    });
    expect(result.rules).toEqual([]);
    expect(result.climate_zone).toBeNull();
  });

  it('turns null or malformed numbers into safe numbers instead of NaN in the headline', () => {
    const result = normalizeAssessment({
      carbon: {
        stored_now: { low: null, central: 'x', high: Number.NaN, unit: '' },
      } as unknown as RawAssessment['carbon'],
    });
    expect(result.carbon.stored_now).toEqual({ low: 0, central: 0, high: 0, unit: '' });
  });

  it('marks unreadable curve points with NaN so the chart can leave them out', () => {
    const result = normalizeAssessment({
      carbon: {
        curve: [{ age: 0, stored: 1, stored_low: 1, stored_high: 1, annual: 1 }, null, {}],
      } as unknown as RawAssessment['carbon'],
    });
    expect(result.carbon.curve).toHaveLength(3);
    expect(Number.isNaN(result.carbon.curve[1].age)).toBe(true);
    expect(Number.isNaN(result.carbon.curve[2].stored)).toBe(true);
    expect(result.carbon.curve[0].age).toBe(0);
  });

  it('treats a missing verification status as not verified', () => {
    const result = normalizeAssessment({
      rules: [{ id: 'r1', name: 'A rule' }] as RawAssessment['rules'],
    });
    expect(result.rules[0].verification_status).toBe('pending');
    const noParameterStatus = normalizeAssessment({
      carbon: {
        parameters_used: [{ name: 'growth_rate', value: 1.2, unit: 'x', source: 's' }],
      } as unknown as RawAssessment['carbon'],
    });
    expect(noParameterStatus.carbon.parameters_used[0].verification_status).toBe('pending');
  });

  it('fills in a rule that has only its name and id', () => {
    const [rule] = normalizeAssessment({
      rules: [{ id: 'r1', name: 'A rule' }] as RawAssessment['rules'],
    }).rules;
    expect(rule).toMatchObject({
      id: 'r1',
      name: 'A rule',
      scope: 'GLOBAL',
      country: null,
      subdivision: null,
      locality: null,
      authority: '',
      outcome_for_existing_trees: 'not-applicable',
      outcome_for_you: 'not-applicable',
      amount: null,
      status: 'in-force',
      is_example: false,
      sources: [],
      applies: true,
      why: '',
      applies_to: { min_age_years: null, max_age_years: null, trees: 'any', setting: 'any' },
    });
  });

  it('uses the rule’s own outcome for the trees when the API sends no outcome_for_you', () => {
    const [rule] = normalizeAssessment({
      rules: [
        { id: 'r1', name: 'Older API', outcome_for_existing_trees: 'protected' },
      ] as RawAssessment['rules'],
    }).rules;
    expect(rule.outcome_for_you).toBe('protected');
  });

  it('keeps a rule that does not apply, marked as such', () => {
    const { rules } = normalizeAssessment({
      rules: [ruleFixture({ id: 'r1', name: 'Elsewhere', applies: false })],
    });
    expect(rules[0].applies).toBe(false);
  });

  it('drops an amount that has no usable value', () => {
    const { rules } = normalizeAssessment({
      rules: [
        { id: 'a', name: 'A', amount: { value: null, currency: 'INR', unit: 'x' } },
        { id: 'b', name: 'B', amount: { value: 3000, currency: 'INR', unit: 'per tree per year' } },
      ] as unknown as RawAssessment['rules'],
    });
    expect(rules[0].amount).toBeNull();
    expect(rules[1].amount).toEqual({
      value: 3000,
      currency: 'INR',
      unit: 'per tree per year',
      as_of: null,
    });
  });

  it('keeps sources that have no link, and leaves empty text as null', () => {
    const { rules } = normalizeAssessment({
      rules: [
        { id: 'a', name: 'A', sources: [{ title: 'Paper only', publisher: '', url: '' }] },
      ] as unknown as RawAssessment['rules'],
    });
    expect(rules[0].sources).toEqual([
      { title: 'Paper only', publisher: null, url: null, accessed: null },
    ]);
  });

  it('keeps only text entries in the notes and in the rule ids behind the outlook', () => {
    const result = normalizeAssessment({
      carbon: { notes: ['A note', 3, null] } as unknown as RawAssessment['carbon'],
      credit_outlook: {
        existing_trees: 'not-eligible',
        summary: 'Because.',
        based_on_rule_ids: ['one', 2, null, 'two'],
      } as unknown as RawAssessment['credit_outlook'],
    });
    expect(result.carbon.notes).toEqual(['A note']);
    expect(result.credit_outlook.based_on_rule_ids).toEqual(['one', 'two']);
  });

  it('keeps the climate zone label and where the zone came from', () => {
    const result = normalizeAssessment(assessmentFixture() as RawAssessment);
    expect(result.climate_zone_label).toBe('Tropical dry');
    expect(result.climate_zone_source).toBe('region default (IN)');
  });

  it('reads the per-tree numbers only when they are numbers', () => {
    const result = normalizeAssessment({
      carbon: {
        per_tree: { stored_now_kg_co2e: 12.5, annual_now_kg_co2e: 'many' },
      } as unknown as RawAssessment['carbon'],
    });
    expect(result.carbon.per_tree).toEqual({ stored_now_kg_co2e: 12.5, annual_now_kg_co2e: null });
  });
});

describe('normalizeRulesInfo', () => {
  it('keeps the age classes and the states the API lists', () => {
    const info = normalizeRulesInfo(rulesInfoFixture);
    expect(info.age_classes).toHaveLength(4);
    expect(info.age_classes[3]).toEqual({
      id: 'veteran',
      label: 'Veteran (75+ years)',
      min_age: 75,
      max_age: null,
    });
    expect(info.subdivisions.map((s) => s.code)).toEqual(['IN-KA', 'IN-HR', 'IN-DL']);
    expect(info.subdivision_label).toBe('State or union territory');
    expect(info.disclaimer).toContain('not legal advice');
  });

  it('copes with nothing at all and with a country that has no states', () => {
    expect(normalizeRulesInfo(undefined)).toEqual({
      version: '',
      updated: '',
      disclaimer: '',
      age_classes: [],
      subdivision_label: null,
      subdivisions: [],
    });
    expect(normalizeRulesInfo(null).subdivisions).toEqual([]);
    expect(
      normalizeRulesInfo({ ...rulesInfoFixture, subdivisions: undefined }).subdivisions,
    ).toEqual([]);
  });

  it('skips list entries that are missing their code, name or limits', () => {
    const info = normalizeRulesInfo({
      age_classes: [
        { id: 'young', label: 'Young', min_age: 0, max_age: 20 },
        { id: 'broken' },
        { label: 'no id', min_age: 1 },
      ],
      subdivisions: [
        { code: 'IN-KA', name: 'Karnataka', type: 'state' },
        { code: 'IN-XX' },
        { name: 'No code' },
      ],
    } as unknown as Parameters<typeof normalizeRulesInfo>[0]);
    expect(info.age_classes.map((c) => c.id)).toEqual(['young']);
    expect(info.subdivisions.map((s) => s.code)).toEqual(['IN-KA']);
  });
});
