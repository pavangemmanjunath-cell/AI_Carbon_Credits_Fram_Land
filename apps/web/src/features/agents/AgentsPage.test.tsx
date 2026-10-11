import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetUiStore } from '@/store/uiStore';
import AgentsPage from './AgentsPage';
import {
  catalogFixture,
  olderRunFixture,
  plotFixture,
  runFixture,
  secondPlotFixture,
} from './fixtures';
import { jsonResponse, mockApi, problemResponse, renderWithProviders } from './testUtils';
import type { AgentRun } from './types';

const answerRun: AgentRun = {
  ...runFixture,
  run_id: 'RUN-ASK01',
  plan: { id: 'question', title: 'Question', steps: ['coordinator', 'carbon', 'coordinator'] },
  status: 'completed',
  steps: [{ step: 1, agent: 'carbon', status: 'done', duration_ms: 3, summary: 'Answered' }],
  messages: [
    { ...runFixture.messages[0], id: 'A1', text: 'I will ask the carbon agent.' },
    {
      ...runFixture.messages[4],
      id: 'A2',
      kind: 'answer',
      text: 'India has two separate mechanisms: Green Credit Programme and CCTS.',
      facts: {},
      tool_calls: [],
      evidence: [],
      confidence: null,
    },
  ],
  summary: null,
  guardrails: [],
};

const olderRun: AgentRun = {
  ...olderRunFixture,
  messages: [{ ...runFixture.messages[0], id: 'O1', text: 'This is an older conversation.' }],
};

const runListItem = {
  run_id: 'RUN-TEST01',
  plot_id: 'PLT-DEMOIN',
  plan: { id: 'full-assessment', title: 'Full assessment' },
  status: 'completed-with-warnings',
  started_at: '2026-10-05T09:12:00Z',
};

function baseRoutes() {
  return {
    'GET /plots': () => jsonResponse({ items: [plotFixture, secondPlotFixture] }),
    'GET /agents': () => jsonResponse(catalogFixture),
    'GET /agents/runs': () => jsonResponse({ items: [] }),
    'POST /plots/PLT-DEMOIN/agents/run': () => jsonResponse(runFixture),
    'POST /plots/PLT-SECOND/agents/run': () =>
      jsonResponse({ ...runFixture, plot_id: 'PLT-SECOND' }),
    'POST /agents/ask': () => jsonResponse(answerRun),
    'GET /agents/runs/RUN-TEST01': () => jsonResponse(runFixture),
  };
}

beforeEach(() => {
  localStorage.clear();
  resetUiStore();
});

afterEach(() => {
  vi.restoreAllMocks();
});

async function runTheAgents(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'Run the agents' }));
}

describe('AgentsPage', () => {
  it('asks for a plot first when there is none', async () => {
    mockApi({ ...baseRoutes(), 'GET /plots': () => jsonResponse({ items: [] }) });
    renderWithProviders(<AgentsPage />);
    expect(await screen.findByRole('heading', { name: 'The agents work on a plot' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Open the workspace' })).toHaveAttribute(
      'href',
      '/app',
    );
    expect(screen.queryByRole('button', { name: 'Run the agents' })).not.toBeInTheDocument();
  });

  it('shows the three plans, the reasoner badge and an empty conversation before any run', async () => {
    mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);

    expect(await screen.findByRole('radio', { name: /Full assessment/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: /Quick estimate/ })).not.toBeChecked();
    expect(screen.getByRole('radio', { name: /Tree-age check/ })).not.toBeChecked();
    expect(screen.getByText('Deterministic · LLM off')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Run the agents' })).toBeEnabled();
    expect(await screen.findByText('No conversation yet')).toBeVisible();
    // The team is listed, waiting.
    expect(screen.getByRole('button', { name: /^Land agent: Waiting/ })).toBeInTheDocument();
  });

  it('links to the guide in a new tab and explains the four ideas', async () => {
    const user = userEvent.setup();
    mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    const guide = await screen.findByRole('link', { name: /Learn how it works/ });
    expect(guide).toHaveAttribute(
      'href',
      'https://github.com/pavangemmanjunath-cell/AI_Carbon_Credits_Fram_Land/blob/main/docs/agents/README.md',
    );
    expect(guide).toHaveAttribute('target', '_blank');

    expect(screen.queryByText('Guardrail')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /New to agents\? Four quick answers/ }));
    for (const term of ['Agent', 'Tool', 'Plan', 'Guardrail']) {
      expect(screen.getByText(term, { selector: 'dt' })).toBeVisible();
    }
  });

  it('runs the agents and shows the conversation, the summary and the guardrails', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    await runTheAgents(user);

    const log = await screen.findByRole('log', { name: 'Conversation' });
    expect(within(log).getByText(/Your plot is 2\.13 ha/)).toBeInTheDocument();
    expect(within(log).getByText(/You told me about 420 mango trees/)).toBeInTheDocument();
    expect(within(log).getByRole('article', { name: 'Land agent — Hand-off' })).toBeInTheDocument();
    expect(
      within(log).getByRole('article', { name: 'Carbon agent — Warning' }),
    ).toBeInTheDocument();

    const summary = within(log).getByRole('article', { name: 'Summary' });
    expect(within(summary).getByText(/Your 420 mango trees may remove about 18\.8/)).toBeVisible();
    expect(within(summary).getByText(/not an issued carbon credit/)).toBeVisible();

    expect(screen.getByRole('region', { name: 'Guardrails' })).toBeVisible();
    expect(screen.getByText('Completed with warnings')).toBeVisible();
    // The team column now reflects the run.
    expect(screen.getByRole('button', { name: /^Carbon agent: Needs a look/ })).toBeInTheDocument();

    const post = calls.find((c) => c.method === 'POST');
    expect(post?.path).toBe('/plots/PLT-DEMOIN/agents/run');
    expect(post?.body).toEqual({ plan: 'full-assessment', question: null, locale: 'en' });
  });

  it('runs the plan that was picked', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    await user.click(await screen.findByRole('radio', { name: /Tree-age check/ }));
    await runTheAgents(user);
    await screen.findByRole('log', { name: 'Conversation' });
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({ plan: 'tree-age-check' });
  });

  it('never sends coordinates or geometry with a run', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    await runTheAgents(user);
    await screen.findByRole('log', { name: 'Conversation' });
    const body = calls.find((c) => c.method === 'POST')?.body as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual(['locale', 'plan', 'question']);
  });

  it('shows only one agent when it is picked in the team, and everyone again on request', async () => {
    const user = userEvent.setup();
    mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    await runTheAgents(user);
    const log = await screen.findByRole('log', { name: 'Conversation' });

    await user.click(screen.getByRole('button', { name: /^Carbon agent/ }));
    expect(screen.getByText('Showing Carbon agent only.')).toBeVisible();
    expect(within(log).getByText(/The trees remove about 18\.8 tCO₂e a year/)).toBeInTheDocument();
    expect(within(log).queryByText(/Your plot is 2\.13 ha/)).not.toBeInTheDocument();
    expect(within(log).queryByRole('article', { name: 'Summary' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Show everyone' }));
    expect(within(log).getByText(/Your plot is 2\.13 ha/)).toBeInTheDocument();
    expect(within(log).getByRole('article', { name: 'Summary' })).toBeInTheDocument();
  });

  it('opens "How I know this" to show the tools and the sources', async () => {
    const user = userEvent.setup();
    mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    await runTheAgents(user);
    const bubble = await screen.findByRole('article', { name: 'Carbon agent — Finding' });
    await user.click(within(bubble).getByRole('button', { name: /How I know this/ }));
    expect(within(bubble).getByText('estimate_carbon')).toBeVisible();
    expect(
      within(bubble).getByRole('link', { name: /IPCC 2006 Guidelines, Vol\. 4, Ch\. 4/ }),
    ).toHaveAttribute('target', '_blank');
  });

  it('answers a suggested question and replaces the conversation with the answer', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    await runTheAgents(user);
    await screen.findByRole('article', { name: 'Summary' });

    await user.click(screen.getByRole('button', { name: 'Which programmes can I join?' }));
    const log = await screen.findByRole('log', { name: 'Conversation' });
    await waitFor(() =>
      expect(within(log).getByText(/India has two separate mechanisms/)).toBeInTheDocument(),
    );
    expect(within(log).getByText('Which programmes can I join?')).toBeInTheDocument();
    expect(within(log).queryByText(/Your plot is 2\.13 ha/)).not.toBeInTheDocument();

    const ask = calls.find((c) => c.path === '/agents/ask');
    expect(ask?.method).toBe('POST');
    expect(ask?.body).toEqual({
      question: 'Which programmes can I join?',
      plot_id: 'PLT-DEMOIN',
      locale: 'en',
    });
  });

  it('sends a typed question', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />);
    const input = await screen.findByLabelText('Ask the agents');
    await waitFor(() => expect(input).toBeEnabled());
    await user.type(input, 'How old are my trees?');
    await user.click(screen.getByRole('button', { name: 'Ask' }));
    await screen.findByText(/India has two separate mechanisms/);
    expect(calls.find((c) => c.path === '/agents/ask')?.body).toMatchObject({
      question: 'How old are my trees?',
    });
  });

  it('opens the latest earlier run for the plot without pressing anything', async () => {
    mockApi({
      ...baseRoutes(),
      'GET /agents/runs': () => jsonResponse({ items: [runListItem] }),
    });
    renderWithProviders(<AgentsPage />);
    expect(await screen.findByText(/Your plot is 2\.13 ha/)).toBeInTheDocument();
    expect(screen.queryByText('Earlier runs')).not.toBeInTheDocument();
  });

  it('lets people open an earlier run', async () => {
    const user = userEvent.setup();
    mockApi({
      ...baseRoutes(),
      'GET /agents/runs': () =>
        jsonResponse({
          items: [
            { ...runListItem, run_id: 'RUN-OLDER', started_at: '2026-10-04T10:00:00Z' },
            runListItem,
          ],
        }),
      'GET /agents/runs/RUN-OLDER': () => jsonResponse(olderRun),
    });
    renderWithProviders(<AgentsPage />);
    await screen.findByText(/Your plot is 2\.13 ha/);

    await user.selectOptions(screen.getByLabelText('Earlier runs'), 'RUN-OLDER');
    expect(await screen.findByText('This is an older conversation.')).toBeInTheDocument();
    expect(screen.queryByText(/Your plot is 2\.13 ha/)).not.toBeInTheDocument();
  });

  it('works on the plot named in the address', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(baseRoutes());
    renderWithProviders(<AgentsPage />, '/app/agents?plot=PLT-SECOND');
    await waitFor(() => expect(screen.getByLabelText('Plot')).toHaveValue('PLT-SECOND'));
    await runTheAgents(user);
    await screen.findByRole('log', { name: 'Conversation' });
    expect(calls.find((c) => c.method === 'POST')?.path).toBe('/plots/PLT-SECOND/agents/run');
  });

  it('tells people to start the API when it is not running', async () => {
    mockApi({
      'GET /plots': () => jsonResponse({ items: [plotFixture] }),
      'GET /agents': () => {
        throw new TypeError('Failed to fetch');
      },
      'GET /agents/runs': () => {
        throw new TypeError('Failed to fetch');
      },
    });
    renderWithProviders(<AgentsPage />);
    expect(await screen.findByText('The agents need the API')).toBeVisible();
    expect(screen.getByText('make api')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Run the agents' })).toBeDisabled();
  });

  it('shows the API problem detail when a run is refused', async () => {
    const user = userEvent.setup();
    mockApi({
      ...baseRoutes(),
      'POST /plots/PLT-DEMOIN/agents/run': () =>
        problemResponse(422, 'Unknown plan', 'Plan "full-assessment" is not available.'),
    });
    renderWithProviders(<AgentsPage />);
    await runTheAgents(user);
    expect(await screen.findByText('Unknown plan')).toBeVisible();
    expect(screen.getByText('Plan "full-assessment" is not available.')).toBeVisible();
    expect(screen.getByText('HTTP 422')).toBeVisible();
    // The page stays usable: the button is back and can be pressed again.
    expect(screen.getByRole('button', { name: 'Run the agents' })).toBeEnabled();
  });

  it('shows what went wrong when a run stops early', async () => {
    const user = userEvent.setup();
    mockApi({
      ...baseRoutes(),
      'POST /plots/PLT-DEMOIN/agents/run': () =>
        jsonResponse({
          ...runFixture,
          status: 'failed',
          steps: [
            {
              step: 1,
              agent: 'land',
              status: 'failed',
              duration_ms: 2,
              summary: 'Plot has no area',
            },
          ],
          summary: null,
          guardrails: [],
        }),
    });
    renderWithProviders(<AgentsPage />);
    await runTheAgents(user);
    expect(await screen.findByText('This run stopped early.')).toBeVisible();
    expect(screen.getByText(/Land agent: Plot has no area/)).toBeVisible();
    expect(screen.getByRole('button', { name: /^Land agent: Failed/ })).toBeInTheDocument();
  });
});
