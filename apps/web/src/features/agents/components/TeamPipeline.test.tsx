import '../i18n';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { catalogFixture, runFixture } from '../fixtures';
import { pipelineRows } from '../logic/agentsLogic';
import type { AgentNames } from '../useAgentNames';
import { TeamPipeline } from './TeamPipeline';

const names: AgentNames = {
  title: (id) =>
    ({
      coordinator: 'Coordinator',
      land: 'Land agent',
      trees: 'Tree agent',
      carbon: 'Carbon agent',
      review: 'Review agent',
    })[id] ?? id,
  role: (id) => catalogFixture.agents.find((a) => a.id === id)?.role ?? '',
};

const planSteps = catalogFixture.plans[0].steps;

function renderTeam(overrides: Partial<Parameters<typeof TeamPipeline>[0]> = {}) {
  const onSelect = vi.fn();
  const rows = pipelineRows({ planSteps, run: runFixture, pending: false });
  render(
    <TeamPipeline
      rows={rows}
      planTitle="Full assessment"
      selected={null}
      onSelect={onSelect}
      names={names}
      catalogAgents={catalogFixture.agents}
      locale="en"
      {...overrides}
    />,
  );
  return { onSelect, rows };
}

describe('TeamPipeline', () => {
  it('lists each agent once, in plan order, with a status in words', () => {
    renderTeam();
    const team = screen.getByRole('region', { name: 'Team' });
    const buttons = within(team).getAllByRole('button');
    expect(buttons).toHaveLength(5);
    expect(buttons.map((b) => b.getAttribute('aria-label'))).toEqual([
      expect.stringMatching(/^Coordinator: Done/),
      expect.stringMatching(/^Land agent: Done/),
      expect.stringMatching(/^Tree agent: Done/),
      expect.stringMatching(/^Carbon agent: Needs a look/),
      expect.stringMatching(/^Review agent: Done/),
    ]);
  });

  it('shows the one-line role of every agent', () => {
    renderTeam();
    expect(screen.getByText('Measures the plot')).toBeInTheDocument();
    expect(screen.getByText('Estimates carbon')).toBeInTheDocument();
  });

  it('picks an agent on click and puts it back on a second click', async () => {
    const user = userEvent.setup();
    const { onSelect } = renderTeam();
    await user.click(screen.getByRole('button', { name: /^Carbon agent/ }));
    expect(onSelect).toHaveBeenLastCalledWith('carbon');
  });

  it('marks the selected agent and describes what it says and which tools it has', async () => {
    const user = userEvent.setup();
    const { onSelect } = renderTeam({ selected: 'land' });
    const selected = screen.getByRole('button', { name: /^Land agent/ });
    expect(selected).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /^Tree agent/ })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
    expect(screen.getByText('size and land cover of the plot')).toBeInTheDocument();
    expect(screen.getByText('measure_plot, land_cover')).toBeInTheDocument();

    await user.click(selected);
    expect(onSelect).toHaveBeenLastCalledWith(null);
  });

  it('shows the whole team as waiting before any run', () => {
    const rows = pipelineRows({ planSteps, run: null, pending: false });
    renderTeam({ rows });
    for (const button of screen.getAllByRole('button')) {
      expect(button.getAttribute('aria-label')).toMatch(/Waiting/);
    }
  });

  it('shows who is working while a run is requested', () => {
    const rows = pipelineRows({ planSteps, run: null, pending: true });
    renderTeam({ rows });
    expect(screen.getByRole('button', { name: /^Coordinator: Working/ })).toBeInTheDocument();
  });
});
