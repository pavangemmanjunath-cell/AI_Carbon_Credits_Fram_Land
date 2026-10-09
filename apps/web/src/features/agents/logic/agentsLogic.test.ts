import { describe, expect, it } from 'vitest';
import { catalogFixture, olderRunFixture, runFixture } from '../fixtures';
import type { AgentRun } from '../types';
import {
  agentTitle,
  agentVisual,
  factChips,
  filterMessagesByAgent,
  findSummaryMessage,
  firstAttentionGuardrail,
  formatClock,
  formatDuration,
  formatFactValue,
  groupMessagesByAgent,
  groupMessagesByStep,
  guardrailTone,
  humanizeKey,
  isHiddenKey,
  isKnownAgent,
  kindStyle,
  messageCountsByAgent,
  pipelineRows,
  planAgentIds,
  recipientAgentId,
  resolvePlanId,
  resolvePlotId,
  safeHttpUrl,
  splitFactKey,
  summarizeRecord,
  validateQuestion,
} from './agentsLogic';
import { normalizeRun, normalizeRunList, sortRunsNewestFirst } from './normalizeRun';

const planSteps = runFixture.plan.steps;

describe('agent visuals', () => {
  it('gives every contract agent its own icon and soft colour', () => {
    const ids = [
      'coordinator',
      'land',
      'imagery',
      'trees',
      'carbon',
      'policy',
      'market',
      'review',
      'report',
    ];
    expect(agentVisual('coordinator')).toEqual({ icon: 'compass', tone: 'indigo' });
    expect(agentVisual('land').icon).toBe('map');
    expect(agentVisual('imagery').icon).toBe('satellite');
    expect(agentVisual('trees').icon).toBe('tree');
    expect(agentVisual('carbon').icon).toBe('leaf');
    expect(agentVisual('policy').icon).toBe('scale');
    expect(agentVisual('market').icon).toBe('coins');
    expect(agentVisual('review').icon).toBe('shield');
    expect(agentVisual('report').icon).toBe('file');
    const tones = ids.map((id) => agentVisual(id).tone);
    expect(new Set(tones).size).toBe(ids.length);
    expect(ids.every(isKnownAgent)).toBe(true);
  });

  it('falls back to a neutral robot for an unknown agent', () => {
    expect(agentVisual('mystery')).toEqual({ icon: 'bot', tone: 'slate' });
    expect(isKnownAgent('mystery')).toBe(false);
  });
});

describe('names', () => {
  it('humanises ids and keeps acronyms upper-case', () => {
    expect(humanizeKey('tree_count')).toBe('Tree count');
    expect(humanizeKey('ndvi_trend')).toBe('NDVI trend');
    expect(humanizeKey('land-use')).toBe('Land use');
    expect(humanizeKey('')).toBe('');
  });

  it('prefers a translated title, then the catalog, then the message, then the id', () => {
    expect(agentTitle('land', { translated: 'Landagent', catalog: catalogFixture.agents })).toBe(
      'Landagent',
    );
    expect(agentTitle('land', { catalog: catalogFixture.agents })).toBe('Land agent');
    expect(
      agentTitle('market', {
        messages: [{ ...runFixture.messages[0], agent: 'market', agent_title: 'Market agent' }],
      }),
    ).toBe('Market agent');
    expect(agentTitle('policy')).toBe('Policy');
  });
});

describe('plans', () => {
  it('lists each agent once, in order of first appearance', () => {
    expect(planAgentIds(planSteps)).toEqual(['coordinator', 'land', 'trees', 'carbon', 'review']);
  });

  it('keeps a valid wanted plan and otherwise prefers the full assessment', () => {
    expect(resolvePlanId(catalogFixture.plans, 'tree-age-check')).toBe('tree-age-check');
    expect(resolvePlanId(catalogFixture.plans, 'nope')).toBe('full-assessment');
    expect(resolvePlanId([catalogFixture.plans[2]], 'nope')).toBe('tree-age-check');
    expect(resolvePlanId(undefined, null)).toBe('full-assessment');
  });

  it('resolves the plot: URL first, then the store, then the first plot', () => {
    const ids = ['A', 'B', 'C'];
    expect(resolvePlotId('B', 'C', ids)).toBe('B');
    expect(resolvePlotId('X', 'C', ids)).toBe('C');
    expect(resolvePlotId(null, 'X', ids)).toBe('A');
    expect(resolvePlotId(null, null, [])).toBeNull();
  });
});

describe('pipelineRows', () => {
  it('shows everyone as pending before a run', () => {
    const rows = pipelineRows({ planSteps, run: null, pending: false });
    expect(rows.map((r) => r.agent)).toEqual(['coordinator', 'land', 'trees', 'carbon', 'review']);
    expect(rows.every((r) => r.status === 'pending')).toBe(true);
  });

  it('shows the coordinator as running while a run is requested', () => {
    const rows = pipelineRows({ planSteps, run: null, pending: true });
    expect(rows.map((r) => r.status)).toEqual([
      'running',
      'pending',
      'pending',
      'pending',
      'pending',
    ]);
  });

  it('uses the API step status and duration; the coordinator is done once the run exists', () => {
    const rows = pipelineRows({ planSteps, run: runFixture, pending: false });
    const byAgent = Object.fromEntries(rows.map((r) => [r.agent, r]));
    expect(byAgent.coordinator.status).toBe('done');
    expect(byAgent.land).toMatchObject({ status: 'done', durationMs: 3, messageCount: 2 });
    expect(byAgent.carbon).toMatchObject({ status: 'warning', durationMs: 6, messageCount: 2 });
    expect(byAgent.review.status).toBe('done');
  });

  it('adds up durations and lets failed beat warning beat done for repeated steps', () => {
    const run: AgentRun = {
      ...runFixture,
      steps: [
        { step: 1, agent: 'land', status: 'done', duration_ms: 2, summary: '' },
        { step: 2, agent: 'land', status: 'warning', duration_ms: 3, summary: '' },
        { step: 3, agent: 'trees', status: 'failed', duration_ms: null, summary: '' },
        { step: 4, agent: 'trees', status: 'done', duration_ms: null, summary: '' },
      ],
    };
    const rows = pipelineRows({ planSteps, run, pending: false });
    expect(rows.find((r) => r.agent === 'land')).toMatchObject({
      status: 'warning',
      durationMs: 5,
    });
    expect(rows.find((r) => r.agent === 'trees')).toMatchObject({
      status: 'failed',
      durationMs: null,
    });
  });

  it('falls back to messages when a step is missing, and marks silent agents skipped', () => {
    const run: AgentRun = { ...runFixture, steps: [] };
    const rows = pipelineRows({ planSteps, run, pending: false });
    expect(rows.find((r) => r.agent === 'carbon')?.status).toBe('warning'); // has a warning message
    expect(rows.find((r) => r.agent === 'land')?.status).toBe('done');
    const silent: AgentRun = { ...runFixture, steps: [], messages: [] };
    const silentRows = pipelineRows({ planSteps, run: silent, pending: false });
    expect(silentRows.find((r) => r.agent === 'coordinator')?.status).toBe('done');
    expect(silentRows.find((r) => r.agent === 'review')?.status).toBe('skipped');
  });

  it('shows the next silent agent as running when the run itself is still running', () => {
    const run: AgentRun = {
      ...runFixture,
      status: 'running',
      steps: [{ step: 1, agent: 'land', status: 'done', duration_ms: 3, summary: '' }],
      messages: runFixture.messages.filter((m) => m.agent === 'land' || m.agent === 'coordinator'),
    };
    const rows = pipelineRows({ planSteps, run, pending: false });
    expect(rows.map((r) => r.status)).toEqual(['done', 'done', 'running', 'pending', 'pending']);
  });
});

describe('transcript helpers', () => {
  it('filters by agent and returns everything without a filter', () => {
    expect(filterMessagesByAgent(runFixture.messages, null)).toHaveLength(
      runFixture.messages.length,
    );
    expect(filterMessagesByAgent(runFixture.messages, 'land').map((m) => m.id)).toEqual([
      'M2',
      'M3',
    ]);
    expect(filterMessagesByAgent(runFixture.messages, 'policy')).toEqual([]);
  });

  it('groups consecutive messages by step and agent, preserving order', () => {
    const groups = groupMessagesByStep(runFixture.messages);
    expect(groups.map((g) => `${g.step}:${g.agent}:${g.messages.length}`)).toEqual([
      '0:coordinator:1',
      '1:land:2',
      '2:trees:1',
      '3:carbon:2',
      '4:review:1',
      '0:coordinator:1',
    ]);
  });

  it('groups by agent in order of first appearance and counts messages', () => {
    const groups = groupMessagesByAgent(runFixture.messages);
    expect(groups.map((g) => g.agent)).toEqual([
      'coordinator',
      'land',
      'trees',
      'carbon',
      'review',
    ]);
    expect(groups[0].messages).toHaveLength(2);
    expect(messageCountsByAgent(runFixture.messages)).toMatchObject({
      coordinator: 2,
      land: 2,
      carbon: 2,
    });
  });

  it('finds the last summary message', () => {
    expect(findSummaryMessage(runFixture.messages)?.id).toBe('M8');
    expect(findSummaryMessage(olderRunFixture.messages)).toBeNull();
  });

  it('shows a recipient only for a specific agent', () => {
    expect(recipientAgentId('trees')).toBe('trees');
    expect(recipientAgentId('team')).toBeNull();
    expect(recipientAgentId(null)).toBeNull();
  });

  it('styles message kinds with a tone and an icon (never colour only)', () => {
    expect(kindStyle('warning')).toEqual({ tone: 'amber', icon: 'warning' });
    expect(kindStyle('handoff').icon).toBe('handoff');
    expect(kindStyle('summary').icon).toBe('summary');
    expect(kindStyle('finding').tone).toBe('mint');
    expect(kindStyle('something-else').icon).toBe('finding');
  });

  it('maps guardrail statuses to a mark and surfaces the one needing attention', () => {
    expect(guardrailTone('pass').mark).toBe('✓');
    expect(guardrailTone('warn').mark).toBe('!');
    expect(guardrailTone('fail').mark).toBe('✕');
    expect(firstAttentionGuardrail(runFixture.guardrails)?.id).toBe('pending-parameters');
    const withFail = [
      ...runFixture.guardrails,
      { id: 'no-coordinates', status: 'fail' as const, detail: 'x' },
    ];
    expect(firstAttentionGuardrail(withFail)?.status).toBe('fail');
    expect(firstAttentionGuardrail([])).toBeNull();
  });
});

describe('facts', () => {
  it('splits unit suffixes off the key', () => {
    expect(splitFactKey('area_hectares')).toEqual({ base: 'area', unit: 'ha' });
    expect(splitFactKey('estimate_central_tco2e_yr')).toEqual({
      base: 'estimate_central',
      unit: 'tCO₂e/yr',
    });
    expect(splitFactKey('ndvi_trend_pct')).toEqual({ base: 'ndvi_trend', unit: '%' });
    expect(splitFactKey('ndvi')).toEqual({ base: 'ndvi', unit: null });
    expect(splitFactKey('_m')).toEqual({ base: '_m', unit: null });
  });

  it('formats numbers, shares, booleans, lists and ranges; skips objects and empties', () => {
    expect(formatFactValue('area_hectares', 2.13, 'en-IN')).toBe('2.13 ha');
    expect(formatFactValue('tree_cover_share', 0.24, 'en-IN')).toBe('24%');
    expect(formatFactValue('tree_count', 1200, 'en-US')).toBe('1,200');
    expect(formatFactValue('ok', true, 'en')).toBe('yes');
    expect(formatFactValue('ok', false, 'en', { yes: 'ja', no: 'nein' })).toBe('nein');
    expect(formatFactValue('species', 'Mango', 'en')).toBe('Mango');
    expect(formatFactValue('programmes', ['a', 'b', 'c', 'd'], 'en')).toBe('a, b, c +1');
    expect(
      formatFactValue(
        'estimate',
        { low: 13.2, central: 18.8, high: 24.4, unit: 'tCO2e/yr' },
        'en-IN',
      ),
    ).toBe('13.2 – 24.4 tCO₂e/yr');
    expect(formatFactValue('nested', { a: 1 }, 'en')).toBeNull();
    expect(formatFactValue('empty', null, 'en')).toBeNull();
    expect(formatFactValue('empty', '', 'en')).toBeNull();
    expect(formatFactValue('bad', Number.NaN, 'en')).toBeNull();
  });

  it('returns a few chips, only when facts exist, and never coordinates', () => {
    expect(factChips({}, 'en').chips).toEqual([]);
    expect(factChips(undefined, 'en')).toEqual({ chips: [], hidden: 0 });
    const result = factChips({ a: 1, b: 2, c: 3, d: 4, lat: 13.2, geometry: 'x', e: 5 }, 'en', 3);
    expect(result.chips.map((c) => c.key)).toEqual(['a', 'b', 'c']);
    expect(result.hidden).toBe(2);
    expect(factChips({ lat: 1, lon: 2 }, 'en').chips).toEqual([]);
  });

  it('formats small quantities without rounding them to zero', () => {
    expect(formatFactValue('estimate_central_tco2e_yr', 0.012, 'en')).toBe('0.01 tCO₂e/yr');
    expect(formatFactValue('range', { low: 0.004, high: 0.02 }, 'en')).toBe('0.004 – 0.02');
  });
});

describe('summaries and links', () => {
  it('summarises tool input and output as short key=value text', () => {
    expect(summarizeRecord({ area_hectares: 2.13, crs: 'EPSG:4326' })).toBe(
      'area_hectares=2.13, crs=EPSG:4326',
    );
    expect(summarizeRecord(null)).toBe('');
    expect(summarizeRecord({ list: [1, 2, 3, 4, 5, 6] })).toBe('list=[1, 2, 3, 4, …]');
    expect(summarizeRecord({ a: 'x'.repeat(300) }, 40).length).toBeLessThanOrEqual(40);
  });

  it('never shows coordinates even if one slips into a tool summary', () => {
    const text = summarizeRecord({
      plot_id: 'P',
      lat: 13.29,
      lon: 77.54,
      geometry: { type: 'Polygon' },
    });
    expect(text).toContain('plot_id=P');
    expect(text).toContain('lat=[hidden]');
    expect(text).toContain('lon=[hidden]');
    expect(text).toContain('geometry=[hidden]');
    expect(text).not.toContain('13.29');
  });

  it('hides every key that names a location, in any spelling', () => {
    for (const key of [
      'lat',
      'LON',
      'latitude',
      'centroid_lat',
      'plotLon',
      'public-centroid',
      'bbox',
      'geometry',
      'geojson',
    ]) {
      expect(isHiddenKey(key), key).toBe(true);
    }
    for (const key of ['plate_count', 'latency_ms', 'latest_value', 'area_hectares', 'plot_id']) {
      expect(isHiddenKey(key), key).toBe(false);
    }
  });

  it('only allows http(s) links', () => {
    expect(safeHttpUrl('https://esa-worldcover.org/')).toBe('https://esa-worldcover.org/');
    expect(safeHttpUrl('http://example.org/a')).toBe('http://example.org/a');
    expect(safeHttpUrl('javascript:alert(1)')).toBeNull();
    expect(safeHttpUrl('data:text/html,hi')).toBeNull();
    expect(safeHttpUrl('not a url')).toBeNull();
    expect(safeHttpUrl(null)).toBeNull();
    expect(safeHttpUrl('  ')).toBeNull();
  });
});

describe('time and questions', () => {
  it('formats durations compactly', () => {
    expect(formatDuration(3)).toBe('3 ms');
    expect(formatDuration(999.4)).toBe('999 ms');
    expect(formatDuration(1500, 'en')).toBe('1.5 s');
    expect(formatDuration(null)).toBe('');
  });

  it('formats a clock time and tolerates bad input', () => {
    expect(formatClock('2026-10-05T09:12:04Z', 'en-GB', 'UTC')).toBe('09:12:04');
    expect(formatClock('nope', 'en')).toBe('');
    expect(formatClock(undefined, 'en')).toBe('');
  });

  it('validates a question: trimmed, 1–500 characters', () => {
    expect(validateQuestion('   ')).toEqual({ ok: false, reason: 'empty' });
    expect(validateQuestion('  How much carbon?  ')).toEqual({
      ok: true,
      question: 'How much carbon?',
    });
    expect(validateQuestion('x'.repeat(500)).ok).toBe(true);
    expect(validateQuestion('x'.repeat(501))).toEqual({ ok: false, reason: 'too-long' });
  });
});

describe('normalising API responses', () => {
  it('defaults every optional list and block so the UI can rely on them', () => {
    const run = normalizeRun({ run_id: 'RUN-1' });
    expect(run).toMatchObject({
      run_id: 'RUN-1',
      status: 'completed',
      steps: [],
      messages: [],
      guardrails: [],
      summary: null,
      certified: false,
      disclaimer: '',
    });
    expect(run.reasoner).toEqual({ mode: 'template', llm_enabled: false, provider: null });
  });

  it('fills message gaps without inventing content and never reports certified', () => {
    const run = normalizeRun({
      run_id: 'RUN-2',
      plan: { id: 'quick-estimate' },
      messages: [{ agent: 'land', kind: 'finding', text: 'hi' }],
      summary: { headline: 'h', certified: true },
    });
    expect(run.plan).toEqual({ id: 'quick-estimate', title: 'quick-estimate', steps: [] });
    expect(run.messages[0]).toMatchObject({
      id: 'M1',
      facts: {},
      tool_calls: [],
      evidence: [],
      confidence: null,
      to: null,
    });
    expect(run.summary).toMatchObject({
      headline: 'h',
      estimate: null,
      readiness: null,
      next_steps: [],
      certified: false,
    });
  });

  it('accepts a bare array or {items} for the run list and ignores junk', () => {
    expect(normalizeRunList([{ run_id: 'A' }, { nope: 1 }, null])).toEqual([{ run_id: 'A' }]);
    expect(normalizeRunList({ items: [{ run_id: 'B' }] })).toEqual([{ run_id: 'B' }]);
    expect(normalizeRunList(undefined)).toEqual([]);
    expect(normalizeRunList({ items: 'x' })).toEqual([]);
  });

  it('sorts runs newest first and keeps undated runs after dated ones in server order', () => {
    const sorted = sortRunsNewestFirst([
      { run_id: 'undated-1' },
      { run_id: 'old', started_at: '2026-10-01T00:00:00Z' },
      { run_id: 'new', started_at: '2026-10-05T00:00:00Z' },
      { run_id: 'undated-2' },
    ]);
    expect(sorted.map((r) => r.run_id)).toEqual(['new', 'old', 'undated-1', 'undated-2']);
  });
});
