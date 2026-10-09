import { describe, expect, it } from 'vitest';
import { assessmentFixture, curveFixture, rulesFixture, ruleFixture } from '../fixtures';
import type { TreeAgeInputs } from '../types';
import {
  AGE_MAX,
  DEFAULT_AGE,
  DEFAULT_SETTING,
  DEFAULT_TREES,
  SUPPORTED_COUNTRIES,
  ageClassSpan,
  amountUnitKey,
  buildRequestBody,
  carbonDigits,
  checkGirth,
  checkWholeNumber,
  countryOptions,
  curveToChartData,
  formatAmountValue,
  formatAxisNumber,
  formatCarbon,
  formatRangeParts,
  humanize,
  inputProblems,
  isAgeSpecific,
  niceTicks,
  outcomeOf,
  outcomeStyle,
  outlookKey,
  parseTreeAgeParams,
  pointAtAge,
  regionName,
  requestKey,
  resolveSpeciesId,
  resolveSubdivision,
  ruleSpecificity,
  safeHttpUrl,
  sampleCurve,
  sortRules,
  splitRules,
  toSearchParams,
  verificationOf,
  withCountry,
} from './treeAgeLogic';

const inputs: TreeAgeInputs = {
  country: 'IN',
  subdivision: 'IN-KA',
  setting: 'farm',
  speciesId: 'mango',
  age: 60,
  trees: 25,
  girthCm: 120,
};

describe('reading numbers a person typed', () => {
  it('accepts whole numbers inside the limits', () => {
    expect(checkWholeNumber('30', 0, 300)).toEqual({ ok: true, value: 30 });
    expect(checkWholeNumber(' 0 ', 0, 300)).toEqual({ ok: true, value: 0 });
    expect(checkWholeNumber('300', 0, 300)).toEqual({ ok: true, value: 300 });
    expect(checkWholeNumber('007', 0, 300)).toEqual({ ok: true, value: 7 });
  });

  it('says what is wrong, in a way that can be translated', () => {
    expect(checkWholeNumber('', 0, 300)).toEqual({ ok: false, problem: 'empty' });
    expect(checkWholeNumber('   ', 0, 300)).toEqual({ ok: false, problem: 'empty' });
    expect(checkWholeNumber('abc', 0, 300)).toEqual({ ok: false, problem: 'not-a-number' });
    expect(checkWholeNumber('12abc', 0, 300)).toEqual({ ok: false, problem: 'not-a-number' });
    expect(checkWholeNumber('1e3', 0, 300)).toEqual({ ok: false, problem: 'not-a-number' });
    expect(checkWholeNumber('12.5', 0, 300)).toEqual({ ok: false, problem: 'not-whole' });
    expect(checkWholeNumber('12,5', 0, 300)).toEqual({ ok: false, problem: 'not-whole' });
    expect(checkWholeNumber('-1', 0, 300)).toEqual({ ok: false, problem: 'too-small' });
    expect(checkWholeNumber('0', 1, 300)).toEqual({ ok: false, problem: 'too-small' });
    expect(checkWholeNumber('301', 0, 300)).toEqual({ ok: false, problem: 'too-big' });
  });

  it('treats an empty girth as "not measured" and checks the 10–2000 cm range', () => {
    expect(checkGirth('')).toEqual({ ok: true, value: null });
    expect(checkGirth('  ')).toEqual({ ok: true, value: null });
    expect(checkGirth('120')).toEqual({ ok: true, value: 120 });
    expect(checkGirth('120.5')).toEqual({ ok: true, value: 120.5 });
    expect(checkGirth('120,5')).toEqual({ ok: true, value: 120.5 });
    expect(checkGirth('9.9')).toEqual({ ok: false, problem: 'too-small' });
    expect(checkGirth('2001')).toEqual({ ok: false, problem: 'too-big' });
    expect(checkGirth('wide')).toEqual({ ok: false, problem: 'not-a-number' });
    expect(checkGirth('-5')).toEqual({ ok: false, problem: 'not-a-number' });
  });
});

describe('address-bar parameters', () => {
  it('reads every parameter', () => {
    const params = new URLSearchParams(
      'country=in&subdivision=in-ka&species=teak&age=60&trees=25&girth=120.5&setting=urban',
    );
    expect(parseTreeAgeParams(params)).toEqual({
      country: 'IN',
      subdivision: 'IN-KA',
      setting: 'urban',
      speciesId: 'teak',
      age: 60,
      trees: 25,
      girthCm: 120.5,
    });
  });

  it('falls back to defaults for an empty address', () => {
    expect(parseTreeAgeParams(new URLSearchParams())).toEqual({
      country: 'IN',
      subdivision: null,
      setting: DEFAULT_SETTING,
      speciesId: null,
      age: DEFAULT_AGE,
      trees: DEFAULT_TREES,
      girthCm: null,
    });
  });

  it('uses the country the app is set to when the address has none', () => {
    expect(parseTreeAgeParams(new URLSearchParams(), { country: 'DE' }).country).toBe('DE');
    expect(parseTreeAgeParams(new URLSearchParams('country=US'), { country: 'DE' }).country).toBe(
      'US',
    );
  });

  it('accepts India, the United States and every EU member state', () => {
    expect(SUPPORTED_COUNTRIES).toContain('IN');
    expect(SUPPORTED_COUNTRIES).toContain('US');
    for (const code of ['DE', 'FR', 'ES', 'IT', 'SE']) expect(SUPPORTED_COUNTRIES).toContain(code);
    expect(parseTreeAgeParams(new URLSearchParams('country=FR')).country).toBe('FR');
    expect(parseTreeAgeParams(new URLSearchParams('country=BR')).country).toBe('IN');
  });

  it('pulls numbers back inside the allowed range instead of failing', () => {
    expect(parseTreeAgeParams(new URLSearchParams('age=999&trees=0')).age).toBe(AGE_MAX);
    expect(parseTreeAgeParams(new URLSearchParams('age=-4')).age).toBe(0);
    expect(parseTreeAgeParams(new URLSearchParams('trees=0')).trees).toBe(1);
    expect(parseTreeAgeParams(new URLSearchParams('trees=5000000')).trees).toBe(1_000_000);
    expect(parseTreeAgeParams(new URLSearchParams('age=12.7')).age).toBe(12);
  });

  it('ignores values it cannot read', () => {
    const read = parseTreeAgeParams(
      new URLSearchParams(
        'age=old&trees=many&girth=big&setting=moon&subdivision=Karnataka&species=%20',
      ),
    );
    expect(read.age).toBe(DEFAULT_AGE);
    expect(read.trees).toBe(DEFAULT_TREES);
    expect(read.girthCm).toBeNull();
    expect(read.setting).toBe(DEFAULT_SETTING);
    expect(read.subdivision).toBeNull();
    expect(read.speciesId).toBeNull();
  });

  it('drops a girth outside 10–2000 cm and a state that belongs to another country', () => {
    expect(parseTreeAgeParams(new URLSearchParams('girth=5')).girthCm).toBeNull();
    expect(parseTreeAgeParams(new URLSearchParams('girth=5000')).girthCm).toBeNull();
    expect(
      parseTreeAgeParams(new URLSearchParams('country=IN&subdivision=US-CA')).subdivision,
    ).toBeNull();
    expect(
      parseTreeAgeParams(new URLSearchParams('country=US&subdivision=us-ca')).subdivision,
    ).toBe('US-CA');
  });

  it('keeps "any" as a setting only when it is written in the address', () => {
    expect(parseTreeAgeParams(new URLSearchParams('setting=any')).setting).toBe('any');
    expect(parseTreeAgeParams(new URLSearchParams('setting=forest')).setting).toBe('forest');
  });

  it('writes every input, so a copied link is complete, and reads it back the same', () => {
    const written = toSearchParams(inputs);
    expect(written.toString()).toBe(
      'country=IN&subdivision=IN-KA&setting=farm&species=mango&age=60&trees=25&girth=120',
    );
    expect(parseTreeAgeParams(written)).toEqual(inputs);
  });

  it('leaves out what is not set and keeps parameters that are not ours', () => {
    const base = new URLSearchParams('utm=x&subdivision=IN-KA&girth=99');
    const written = toSearchParams({ ...inputs, subdivision: null, girthCm: null }, base);
    expect(written.get('utm')).toBe('x');
    expect(written.has('subdivision')).toBe(false);
    expect(written.has('girth')).toBe(false);
    expect(written.get('age')).toBe('60');
  });
});

describe('lists that come from the API', () => {
  const species = [{ id: 'mango' }, { id: 'teak' }];

  it('keeps the species named in the address when the list has it', () => {
    expect(resolveSpeciesId('teak', species)).toBe('teak');
  });

  it('falls back to the first species when it is not in the list', () => {
    expect(resolveSpeciesId('oak', species)).toBe('mango');
    expect(resolveSpeciesId(null, species)).toBe('mango');
  });

  it('keeps what the address says while the list is still loading', () => {
    expect(resolveSpeciesId('teak', undefined)).toBe('teak');
    expect(resolveSpeciesId(null, undefined)).toBeNull();
    expect(resolveSpeciesId('teak', [])).toBe('teak');
  });

  it('keeps a state only when the API lists it for the country', () => {
    const list = [
      { code: 'IN-KA', name: 'Karnataka', type: 'state' },
      { code: 'IN-HR', name: 'Haryana', type: 'state' },
    ];
    expect(resolveSubdivision('IN-KA', list)).toBe('IN-KA');
    expect(resolveSubdivision('IN-XX', list)).toBeNull();
    expect(resolveSubdivision('IN-KA', [])).toBeNull();
    expect(resolveSubdivision('IN-KA', undefined)).toBe('IN-KA');
    expect(resolveSubdivision(null, list)).toBeNull();
  });

  it('forgets the state when the country changes', () => {
    expect(withCountry(inputs, 'US').subdivision).toBeNull();
    expect(withCountry(inputs, 'US').country).toBe('US');
    expect(withCountry(inputs, 'IN')).toBe(inputs);
  });
});

describe('the request to the API', () => {
  it('has the fields of POST /tree-age/assess and nothing else', () => {
    expect(buildRequestBody(inputs)).toEqual({
      country: 'IN',
      subdivision: 'IN-KA',
      setting: 'farm',
      species_id: 'mango',
      age_years: 60,
      tree_count: 25,
      girth_cm: 120,
    });
  });

  it('leaves the girth out for trees that are only planned', () => {
    expect(buildRequestBody({ ...inputs, age: 0 })?.girth_cm).toBeNull();
    expect(buildRequestBody({ ...inputs, age: 1 })?.girth_cm).toBe(120);
  });

  it('is not built while something is missing or out of range', () => {
    expect(buildRequestBody({ ...inputs, speciesId: null })).toBeNull();
    expect(buildRequestBody({ ...inputs, age: 301 })).toBeNull();
    expect(buildRequestBody({ ...inputs, age: -1 })).toBeNull();
    expect(buildRequestBody({ ...inputs, trees: 0 })).toBeNull();
    expect(buildRequestBody({ ...inputs, age: 2.5 })).toBeNull();
    expect(buildRequestBody({ ...inputs, girthCm: 5 })).toBeNull();
    expect(buildRequestBody({ ...inputs, country: 'BR' })).toBeNull();
    expect(inputProblems({ ...inputs, speciesId: null, trees: 0 })).toEqual(['species', 'trees']);
    expect(inputProblems(inputs)).toEqual([]);
  });

  it('never carries a plot or a coordinate', () => {
    const body = buildRequestBody(inputs);
    expect(body).not.toBeNull();
    expect(Object.keys(body ?? {}).sort()).toEqual([
      'age_years',
      'country',
      'girth_cm',
      'setting',
      'species_id',
      'subdivision',
      'tree_count',
    ]);
  });

  it('gives the same key for the same request, so a debounce can compare them', () => {
    const a = requestKey(buildRequestBody(inputs));
    expect(a).toBe(requestKey(buildRequestBody({ ...inputs })));
    expect(a).not.toBe(requestKey(buildRequestBody({ ...inputs, age: 61 })));
    expect(requestKey(null)).toBeNull();
  });
});

describe('numbers and names for display', () => {
  it('uses more decimals for small numbers', () => {
    expect(carbonDigits(250)).toBe(0);
    expect(carbonDigits(25)).toBe(1);
    expect(carbonDigits(2.5)).toBe(2);
    expect(carbonDigits(0.5)).toBe(2);
    expect(carbonDigits(0.012)).toBe(3);
    expect(formatCarbon(0.012, 'en')).toBe('0.012');
    expect(formatCarbon(14.123, 'en')).toBe('14.1');
    expect(formatCarbon(1234.5, 'en-US')).toBe('1,235');
    expect(formatCarbon(Number.NaN, 'en')).toBe('—');
  });

  it('groups digits the way the locale does (lakh in en-IN)', () => {
    expect(formatCarbon(123456, 'en-IN')).toBe('1,23,456');
    expect(formatCarbon(123456, 'de-DE')).toBe('123.456');
  });

  it('formats low, central and high with the same decimals', () => {
    expect(
      formatRangeParts({ low: 11.44, central: 14.1, high: 17.22, unit: 'tCO2e' }, 'en'),
    ).toEqual({
      low: '11.4',
      central: '14.1',
      high: '17.2',
    });
    expect(formatRangeParts({ low: 0, central: 0, high: 0, unit: 'tCO2e' }, 'en').central).toBe(
      '0',
    );
  });

  it('shortens axis numbers', () => {
    expect(formatAxisNumber(1500, 'en-US')).toBe('1.5K');
    expect(formatAxisNumber(12, 'en-US')).toBe('12');
    expect(formatAxisNumber(Number.NaN, 'en')).toBe('');
  });

  it('keeps the decimals an axis needs, so a small number never reads as zero', () => {
    expect(formatAxisNumber(0.05, 'en-US', 2)).toBe('0.05');
    expect(formatAxisNumber(0.25, 'en-US', 2)).toBe('0.25');
    expect(formatAxisNumber(0.005, 'en-US', 3)).toBe('0.005');
    expect(formatAxisNumber(0.05, 'de-DE', 2)).toBe('0,05');
    // From a thousand up the short form takes over, whatever the decimals.
    expect(formatAxisNumber(25000, 'en-US', 2)).toBe('25K');
    expect(formatAxisNumber(150000, 'en-IN', 0)).toBe('1.5L');
  });
});

describe('round axis labels', () => {
  it('reads 0, 50, 100, 150 and never 129.6', () => {
    const { ticks, top, decimals } = niceTicks(129.6, 5);
    expect(ticks).toEqual([0, 50, 100, 150]);
    expect(top).toBe(150);
    expect(decimals).toBe(0);
  });

  it('ends on the first round number at or above the largest value', () => {
    expect(niceTicks(100, 5).ticks).toEqual([0, 20, 40, 60, 80, 100]);
    expect(niceTicks(101, 5).ticks).toEqual([0, 25, 50, 75, 100, 125]);
    expect(niceTicks(558.1, 4).ticks).toEqual([0, 200, 400, 600]);
    expect(niceTicks(180, 4).ticks).toEqual([0, 50, 100, 150, 200]);
  });

  it('never gives more gaps than asked for', () => {
    for (const max of [0.07, 0.4, 3, 7.7, 12, 99, 180, 1234, 98765, 4_500_000]) {
      for (const intervals of [3, 4, 5, 6]) {
        const { ticks } = niceTicks(max, intervals);
        expect(ticks.length - 1, `${max}/${intervals}`).toBeLessThanOrEqual(intervals);
        expect(ticks[0]).toBe(0);
        expect(ticks[ticks.length - 1], `${max}/${intervals}`).toBeGreaterThanOrEqual(max);
      }
    }
  });

  it('counts up in even steps without floating-point noise', () => {
    const { ticks, decimals } = niceTicks(0.9, 5);
    expect(ticks).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1]);
    expect(decimals).toBe(1);
    const small = niceTicks(0.0144, 4);
    expect(small.ticks).toEqual([0, 0.005, 0.01, 0.015]);
    expect(small.decimals).toBe(3);
    expect(niceTicks(0.7, 4).ticks).toEqual([0, 0.2, 0.4, 0.6, 0.8]);
    // A quarter step needs two decimals: 0.25, 0.5, 0.75.
    expect(niceTicks(0.96, 4).ticks).toEqual([0, 0.25, 0.5, 0.75, 1]);
    expect(niceTicks(0.96, 4).decimals).toBe(2);
  });

  it('uses whole numbers only for ages', () => {
    expect(niceTicks(50, 5, true).ticks).toEqual([0, 10, 20, 30, 40, 50]);
    expect(niceTicks(70, 5, true).ticks).toEqual([0, 20, 40, 60, 80]);
    expect(niceTicks(12, 6, true).ticks).toEqual([0, 2, 4, 6, 8, 10, 12]);
    expect(niceTicks(3, 6, true).ticks).toEqual([0, 1, 2, 3]);
    expect(niceTicks(150, 5, true).ticks).toEqual([0, 50, 100, 150]);
    for (const tick of niceTicks(7, 6, true).ticks) expect(Number.isInteger(tick)).toBe(true);
  });

  it('copes with nothing to scale', () => {
    expect(niceTicks(0).ticks).toEqual([0, 1]);
    expect(niceTicks(-3).ticks).toEqual([0, 1]);
    expect(niceTicks(Number.NaN).ticks).toEqual([0, 1]);
    expect(niceTicks(Number.POSITIVE_INFINITY).ticks).toEqual([0, 1]);
  });
});

describe('names and lists for display', () => {
  it('names regions in the reader’s language', () => {
    expect(regionName('IN', 'en')).toBe('India');
    expect(regionName('DE', 'de')).toBe('Deutschland');
    expect(regionName('EU', 'en')).toBe('European Union');
  });

  it('lists India and the United States first, then the EU members by name', () => {
    const { top, eu } = countryOptions('en');
    expect(top.map((c) => c.code)).toEqual(['IN', 'US']);
    expect(eu).toHaveLength(27);
    expect(eu[0].name).toBe('Austria');
    expect(eu.map((c) => c.name)).toEqual(
      [...eu.map((c) => c.name)].sort((a, b) => a.localeCompare(b)),
    );
    expect(eu.some((c) => c.code === 'IN')).toBe(false);
  });

  it('makes a readable label out of a key', () => {
    expect(humanize('carbon-credit-eligibility')).toBe('Carbon credit eligibility');
    expect(humanize('in_force')).toBe('In force');
    expect(humanize('')).toBe('');
  });

  it('finds the years of an age class', () => {
    const classes = [
      { id: 'young', label: 'Young', min_age: 0, max_age: 20 },
      { id: 'veteran', label: 'Veteran', min_age: 75, max_age: null },
    ];
    expect(ageClassSpan('young', classes)).toEqual({ min: 0, max: 20 });
    expect(ageClassSpan('veteran', classes)).toEqual({ min: 75, max: null });
    expect(ageClassSpan('old', classes)).toBeNull();
    expect(ageClassSpan('young', undefined)).toBeNull();
  });
});

describe('credit outlook sentence', () => {
  const outlook = (existing_trees: string) => ({
    existing_trees,
    summary: 'x',
    based_on_rule_ids: [],
  });

  it('picks the ready-made sentence that matches the API verdict', () => {
    expect(outlookKey(outlook('not-eligible'), 30)).toBe('not-eligible');
    expect(outlookKey(outlook('conditional'), 30)).toBe('conditional');
    expect(outlookKey(outlook('eligible'), 30)).toBe('eligible');
  });

  it('has its own sentence for trees that are only planned', () => {
    expect(outlookKey(outlook('conditional'), 0)).toBe('planned');
  });

  it('returns null for a verdict it does not know, so the API sentence is used', () => {
    expect(outlookKey(outlook('maybe'), 30)).toBeNull();
    expect(outlookKey(outlook(''), 30)).toBeNull();
  });
});

describe('chart data', () => {
  it('maps the curve to points with a [low, high] band, in age order', () => {
    const data = curveToChartData([
      { age: 2, stored: 2, stored_low: 1.5, stored_high: 2.5, annual: 1 },
      { age: 0, stored: 0, stored_low: 0, stored_high: 0, annual: 0 },
      { age: 1, stored: 1, stored_low: 0.8, stored_high: 1.2, annual: 0.9 },
    ]);
    expect(data.map((p) => p.age)).toEqual([0, 1, 2]);
    expect(data[2]).toEqual({
      age: 2,
      stored: 2,
      low: 1.5,
      high: 2.5,
      band: [1.5, 2.5],
      annual: 1,
    });
  });

  it('keeps the band ordered even if the API sends it the wrong way round', () => {
    const [point] = curveToChartData([
      { age: 5, stored: 3, stored_low: 4, stored_high: 2, annual: 1 },
    ]);
    expect(point.band).toEqual([2, 4]);
  });

  it('drops points with broken numbers and survives no curve at all', () => {
    expect(
      curveToChartData([
        { age: 1, stored: Number.NaN, stored_low: 0, stored_high: 0, annual: 0 },
        { age: 2, stored: 1, stored_low: 1, stored_high: 1, annual: 1 },
      ]),
    ).toHaveLength(1);
    expect(curveToChartData(undefined)).toEqual([]);
    expect(curveToChartData([])).toEqual([]);
  });

  it('finds the point at or nearest to an age', () => {
    const data = curveToChartData(curveFixture(10));
    expect(pointAtAge(data, 4)?.age).toBe(4);
    expect(pointAtAge(data, 99)?.age).toBe(10);
    expect(pointAtAge([], 4)).toBeNull();
  });

  it('samples a few ages for a screen-reader table and always includes today', () => {
    const data = curveToChartData(curveFixture(50));
    const rows = sampleCurve(data, 33, 8);
    expect(rows.length).toBeLessThanOrEqual(9);
    expect(rows[0].age).toBe(0);
    expect(rows[rows.length - 1].age).toBe(50);
    expect(rows.map((r) => r.age)).toContain(33);
    expect(rows.map((r) => r.age)).toEqual([...rows.map((r) => r.age)].sort((a, b) => a - b));
    expect(sampleCurve(curveToChartData(curveFixture(4)), 2, 8)).toHaveLength(5);
  });

  it('is built from the real fixture without losing the headline age', () => {
    const fixture = assessmentFixture({ age: 30 });
    const data = curveToChartData(fixture.carbon.curve);
    expect(data).toHaveLength(51);
    expect(pointAtAge(data, 30)?.stored).toBeCloseTo(fixture.carbon.stored_now.central, 3);
  });
});

describe('what a rule means for these trees', () => {
  it('gives every outcome its own colour, icon and label', () => {
    const outcomes = [
      'not-eligible',
      'eligible',
      'conditional',
      'protected',
      'payment',
      'not-applicable',
    ];
    const styles = outcomes.map((o) => outcomeStyle(o));
    expect(new Set(styles.map((s) => s.tone)).size).toBe(outcomes.length);
    expect(new Set(styles.map((s) => s.icon)).size).toBe(outcomes.length);
    expect(styles.map((s) => s.labelKey)).toEqual(outcomes);
  });

  it('maps the outcomes to the expected colours', () => {
    expect(outcomeStyle('not-eligible').tone).toBe('rose');
    expect(outcomeStyle('eligible').tone).toBe('green');
    expect(outcomeStyle('conditional').tone).toBe('amber');
    expect(outcomeStyle('protected').tone).toBe('blue');
    expect(outcomeStyle('payment').tone).toBe('violet');
    expect(outcomeStyle('not-applicable').tone).toBe('grey');
  });

  it('shows an unknown outcome as grey and unknown, never as eligible', () => {
    expect(outcomeStyle('mystery')).toEqual({ tone: 'grey', icon: 'minus', labelKey: 'unknown' });
    expect(outcomeStyle(undefined).labelKey).toBe('unknown');
  });

  it('shows the outcome for these trees, else the rule’s own', () => {
    expect(
      outcomeOf({ outcome_for_you: 'not-applicable', outcome_for_existing_trees: 'protected' }),
    ).toBe('not-applicable');
    expect(outcomeOf({ outcome_for_you: '', outcome_for_existing_trees: 'protected' })).toBe(
      'protected',
    );
  });

  it('counts a rule as verified only when the API says so', () => {
    expect(verificationOf({ verification_status: 'verified' })).toBe('verified');
    expect(verificationOf({ verification_status: 'pending' })).toBe('pending');
    expect(verificationOf({ verification_status: '' })).toBe('pending');
    expect(verificationOf({ verification_status: 'confirmed' })).toBe('pending');
  });
});

describe('ordering and grouping rules', () => {
  it('knows which rules are written for an age range', () => {
    expect(isAgeSpecific(rulesFixture[2])).toBe(true);
    expect(isAgeSpecific(rulesFixture[0])).toBe(false);
    expect(
      isAgeSpecific({
        applies_to: { min_age_years: 0, max_age_years: null, trees: 'any', setting: 'any' },
      }),
    ).toBe(true);
  });

  it('ranks places: city, state, country, region, worldwide', () => {
    const base = { locality: null, subdivision: null, country: null, scope: 'GLOBAL' };
    expect(
      ruleSpecificity({
        ...base,
        locality: 'Berlin',
        subdivision: 'DE-BE',
        country: 'DE',
        scope: 'EU',
      }),
    ).toBe(4);
    expect(ruleSpecificity({ ...base, subdivision: 'IN-KA', country: 'IN', scope: 'IN' })).toBe(3);
    expect(ruleSpecificity({ ...base, country: 'DE', scope: 'EU' })).toBe(2);
    expect(ruleSpecificity({ ...base, scope: 'IN' })).toBe(1);
    expect(ruleSpecificity(base)).toBe(0);
  });

  it('puts age-specific rules first, then the most local, then by kind of rule', () => {
    const rules = [
      ruleFixture({ id: 'a-global-note', name: 'Global note', category: 'methodology-note' }),
      ruleFixture({ id: 'b-country-credit', name: 'Country credit', scope: 'IN', country: 'IN' }),
      ruleFixture({
        id: 'c-state-protection',
        name: 'State protection',
        scope: 'IN',
        country: 'IN',
        subdivision: 'IN-KA',
        category: 'tree-protection',
      }),
      ruleFixture({
        id: 'd-age-pension',
        name: 'Age pension',
        scope: 'IN',
        country: 'IN',
        subdivision: 'IN-HR',
        category: 'incentive-payment',
        applies_to: { min_age_years: 75, max_age_years: null, trees: 'existing', setting: 'any' },
      }),
      ruleFixture({ id: 'e-global-credit', name: 'Global credit' }),
    ];
    expect(sortRules(rules).map((r) => r.id)).toEqual([
      'd-age-pension',
      'c-state-protection',
      'b-country-credit',
      'e-global-credit',
      'a-global-note',
    ]);
  });

  it('does not change the list it is given', () => {
    const copy = [...rulesFixture];
    sortRules(rulesFixture);
    expect(rulesFixture).toEqual(copy);
  });

  it('splits rules into those that apply and those that do not, each sorted', () => {
    const { applying, other } = splitRules(rulesFixture);
    expect(applying.every((r) => r.applies)).toBe(true);
    expect(other.every((r) => !r.applies)).toBe(true);
    expect(applying.length + other.length).toBe(rulesFixture.length);
    expect(other.map((r) => r.id)).toEqual([
      'in-hr-pran-vayu-devta-pension',
      'us-or-portland-heritage-trees',
    ]);
    expect(applying[0].id).toBe('in-ka-preservation-of-trees-act');
  });
});

describe('rule amounts and links', () => {
  it('writes the amount with the symbol from the region config', () => {
    expect(
      formatAmountValue(
        { value: 3000, currency: 'INR', unit: 'per tree per year', as_of: '2026-07' },
        'en-IN',
      ),
    ).toBe('₹3,000');
    expect(formatAmountValue({ value: 25, currency: 'USD', unit: '', as_of: null }, 'en-US')).toBe(
      '$25',
    );
    expect(
      formatAmountValue({ value: 1500, currency: 'EUR', unit: '', as_of: null }, 'de-DE'),
    ).toBe('€1.500');
  });

  it('shows an unknown currency by its code, never a guessed symbol', () => {
    expect(formatAmountValue({ value: 5, currency: 'CHF', unit: '', as_of: null }, 'en')).toBe(
      'CHF 5',
    );
  });

  it('knows a few units and leaves others as written', () => {
    expect(amountUnitKey('per tree per year')).toBe('perTreePerYear');
    expect(amountUnitKey(' Per Tree ')).toBe('perTree');
    expect(amountUnitKey('per branch')).toBeNull();
    expect(amountUnitKey(null)).toBeNull();
  });

  it('only allows http(s) links', () => {
    expect(safeHttpUrl('https://example.org/a')).toBe('https://example.org/a');
    expect(safeHttpUrl('javascript:alert(1)')).toBeNull();
    expect(safeHttpUrl('data:text/html,hi')).toBeNull();
    expect(safeHttpUrl('not a url')).toBeNull();
    expect(safeHttpUrl(null)).toBeNull();
  });
});
