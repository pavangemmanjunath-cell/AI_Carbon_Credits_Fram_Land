/**
 * Small deterministic fixtures shaped like the API contract (tests only; never imported by
 * production code). Numbers are illustrative test values, not real estimates.
 */
import type { Plot } from '@/types/api';
import type { AgentCatalog, AgentMessage, AgentRun } from './types';

export const catalogFixture: AgentCatalog = {
  framework: { name: 'atlas-agents', version: '0.1.0', reasoner: 'template', llm_enabled: false },
  agents: [
    {
      id: 'coordinator',
      title: 'Coordinator',
      role: 'Plans the work and writes the summary',
      says: 'the plan and the final summary',
      tools: [{ name: 'plan_run', description: 'Chooses the order of the agents' }],
      reads: ['plot'],
      writes: ['summary'],
    },
    {
      id: 'land',
      title: 'Land agent',
      role: 'Measures the plot',
      says: 'size and land cover of the plot',
      tools: [
        { name: 'measure_plot', description: 'Area and perimeter' },
        { name: 'land_cover', description: 'Share of tree cover and cropland' },
      ],
      reads: ['plot'],
      writes: ['landcover'],
    },
    {
      id: 'trees',
      title: 'Tree agent',
      role: 'Reads the tree inventory',
      says: 'species, number and age of your trees',
      tools: [{ name: 'read_inventory', description: 'Latest tree inventory' }],
      reads: ['plot'],
      writes: ['inventory'],
    },
    {
      id: 'carbon',
      title: 'Carbon agent',
      role: 'Estimates carbon',
      says: 'the carbon estimate with a low–high range',
      tools: [{ name: 'estimate_carbon', description: 'Tier 1 carbon estimate' }],
      reads: ['plot', 'inventory'],
      writes: ['estimate'],
    },
    {
      id: 'review',
      title: 'Review agent',
      role: 'Checks the guardrails',
      says: 'whether the safety checks passed',
      tools: [{ name: 'check_guardrails', description: 'Runs the guardrails' }],
      reads: ['estimate'],
      writes: [],
    },
  ],
  plans: [
    {
      id: 'full-assessment',
      title: 'Full assessment',
      steps: ['coordinator', 'land', 'trees', 'carbon', 'review', 'coordinator'],
    },
    {
      id: 'quick-estimate',
      title: 'Quick estimate',
      steps: ['coordinator', 'land', 'trees', 'carbon', 'review', 'coordinator'],
    },
    {
      id: 'tree-age-check',
      title: 'Tree-age check',
      steps: ['coordinator', 'trees', 'carbon', 'review', 'coordinator'],
    },
  ],
};

export const plotFixture: Plot = {
  plot_id: 'PLT-DEMOIN',
  name: 'Demo mango orchard',
  country: 'IN',
  region: 'Karnataka',
  area_hectares: 2.13,
  area_acres: 5.26,
  perimeter_m: 612.4,
  public_centroid: { lat: 13.3, lon: 77.55 },
  source: 'synthetic-demo',
  privacy: 'private',
  created_at: '2026-10-05T08:00:00Z',
};

export const secondPlotFixture: Plot = {
  ...plotFixture,
  plot_id: 'PLT-SECOND',
  name: 'North field',
  area_hectares: 0.8,
  area_acres: 1.98,
};

function message(
  partial: Partial<AgentMessage> & Pick<AgentMessage, 'id' | 'agent' | 'kind' | 'text'>,
): AgentMessage {
  return {
    step: 0,
    agent_title: '',
    to: 'team',
    facts: {},
    tool_calls: [],
    evidence: [],
    confidence: null,
    created_at: '2026-10-05T09:12:00Z',
    ...partial,
  };
}

export const runFixture: AgentRun = {
  run_id: 'RUN-TEST01',
  plot_id: 'PLT-DEMOIN',
  plan: catalogFixture.plans[0],
  status: 'completed-with-warnings',
  reasoner: { mode: 'template', llm_enabled: false, provider: null },
  started_at: '2026-10-05T09:12:00Z',
  finished_at: '2026-10-05T09:12:01Z',
  duration_ms: 42,
  steps: [
    { step: 1, agent: 'land', status: 'done', duration_ms: 3, summary: 'Measured the plot' },
    { step: 2, agent: 'trees', status: 'done', duration_ms: 1, summary: 'Read 420 mango trees' },
    { step: 3, agent: 'carbon', status: 'warning', duration_ms: 6, summary: 'Estimated carbon' },
    { step: 4, agent: 'review', status: 'done', duration_ms: 2, summary: 'Checked guardrails' },
  ],
  messages: [
    message({
      id: 'M1',
      step: 0,
      agent: 'coordinator',
      agent_title: 'Coordinator',
      kind: 'plan',
      text: 'I will ask the land, tree, carbon and review agents, in that order.',
      created_at: '2026-10-05T09:12:00Z',
    }),
    message({
      id: 'M2',
      step: 1,
      agent: 'land',
      agent_title: 'Land agent',
      kind: 'finding',
      text: 'Your plot is 2.13 ha. About 24% of it is tree cover.',
      facts: { area_hectares: 2.13, tree_cover_share: 0.24 },
      tool_calls: [
        {
          tool: 'measure_plot',
          status: 'ok',
          duration_ms: 1,
          input: { plot_id: 'PLT-DEMOIN' },
          output: { area_hectares: 2.13, perimeter_m: 612.4 },
        },
      ],
      evidence: [
        {
          label: 'ESA WorldCover 2021',
          source: 'esa-worldcover',
          url: 'https://esa-worldcover.org/',
        },
      ],
      confidence: 'high',
      created_at: '2026-10-05T09:12:01Z',
    }),
    message({
      id: 'M3',
      step: 1,
      agent: 'land',
      agent_title: 'Land agent',
      kind: 'handoff',
      to: 'trees',
      text: 'Passing the plot size to the Tree agent.',
      created_at: '2026-10-05T09:12:01Z',
    }),
    message({
      id: 'M4',
      step: 2,
      agent: 'trees',
      agent_title: 'Tree agent',
      kind: 'finding',
      text: 'You told me about 420 mango trees planted in 2023.',
      facts: { tree_count: 420, species: 'Mango', age_years: 3 },
      created_at: '2026-10-05T09:12:02Z',
    }),
    message({
      id: 'M5',
      step: 3,
      agent: 'carbon',
      agent_title: 'Carbon agent',
      kind: 'finding',
      text: 'The trees remove about 18.8 tCO₂e a year, somewhere between 13.2 and 24.4.',
      facts: { estimate_central_tco2e_yr: 18.8 },
      tool_calls: [
        {
          tool: 'estimate_carbon',
          status: 'ok',
          duration_ms: 4,
          input: { species_id: 'mango', tree_count: 420 },
          output: { central: 18.8, low: 13.2, high: 24.4, unit: 'tCO2e/yr' },
        },
      ],
      evidence: [
        {
          label: 'IPCC 2006 Guidelines, Vol. 4, Ch. 4',
          source: 'ipcc-2006-vol4-ch4',
          url: 'https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html',
        },
      ],
      confidence: 'medium',
      created_at: '2026-10-05T09:12:03Z',
    }),
    message({
      id: 'M6',
      step: 3,
      agent: 'carbon',
      agent_title: 'Carbon agent',
      kind: 'warning',
      text: 'Two growth parameters are still pending verification, so treat the range with care.',
      created_at: '2026-10-05T09:12:03Z',
    }),
    message({
      id: 'M7',
      step: 4,
      agent: 'review',
      agent_title: 'Review agent',
      kind: 'finding',
      text: 'The result says it is not a credit and shows its uncertainty.',
      created_at: '2026-10-05T09:12:04Z',
    }),
    message({
      id: 'M8',
      step: 0,
      agent: 'coordinator',
      agent_title: 'Coordinator',
      kind: 'summary',
      text: 'Your trees may remove roughly 18.8 tCO₂e a year.',
      created_at: '2026-10-05T09:12:05Z',
    }),
  ],
  summary: {
    headline: 'Your 420 mango trees may remove about 18.8 tCO₂e a year.',
    estimate: { low: 13.2, central: 18.8, high: 24.4, unit: 'tCO2e/yr' },
    readiness: 55,
    next_steps: ['Measure trunk diameters', 'Add baseline land-use records'],
    certified: false,
  },
  guardrails: [
    {
      id: 'not-a-credit',
      status: 'pass',
      detail: 'Every number is labelled as a scenario estimate.',
    },
    {
      id: 'uncertainty-present',
      status: 'pass',
      detail: 'Low, central and high values are shown.',
    },
    {
      id: 'provenance-present',
      status: 'pass',
      detail: 'Sources and model versions are recorded.',
    },
    { id: 'no-coordinates', status: 'pass', detail: 'No coordinates were shared.' },
    {
      id: 'pending-parameters',
      status: 'warn',
      detail: '2 parameters are still pending verification.',
    },
    {
      id: 'values-separated',
      status: 'pass',
      detail: 'Carbon, price and other income are not added.',
    },
  ],
  certified: false,
  disclaimer: 'Scenario estimate; not an issued carbon credit.',
};

export const olderRunFixture: AgentRun = {
  ...runFixture,
  run_id: 'RUN-OLDER',
  plan: catalogFixture.plans[2],
  status: 'completed',
  started_at: '2026-10-04T10:00:00Z',
  messages: runFixture.messages.slice(0, 2),
  summary: null,
  guardrails: [],
};
