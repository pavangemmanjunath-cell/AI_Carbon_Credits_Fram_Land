import '../i18n';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { runFixture } from '../fixtures';
import type { AgentMessage } from '../types';
import type { AgentNames } from '../useAgentNames';
import { MessageBubble } from './MessageBubble';
import { SummaryPanel } from './SummaryPanel';

const names: AgentNames = {
  title: (id) =>
    ({
      coordinator: 'Coordinator',
      land: 'Land agent',
      trees: 'Tree agent',
      carbon: 'Carbon agent',
      review: 'Review agent',
    })[id] ?? id,
  role: () => '',
};

function bubble(id: string): AgentMessage {
  const found = runFixture.messages.find((m) => m.id === id);
  if (!found) throw new Error(`fixture message ${id} missing`);
  return found;
}

describe('MessageBubble', () => {
  it('says who spoke, what kind of message it is and the text', () => {
    render(<MessageBubble message={bubble('M2')} names={names} locale="en" />);
    const article = screen.getByRole('article', { name: 'Land agent — Finding' });
    expect(within(article).getByText('Land agent')).toBeInTheDocument();
    expect(within(article).getByText('Finding')).toBeInTheDocument();
    expect(within(article).getByText(/Your plot is 2\.13 ha/)).toBeInTheDocument();
  });

  it('shows fact chips only when the message has facts', () => {
    const { rerender } = render(<MessageBubble message={bubble('M2')} names={names} locale="en" />);
    const facts = screen.getByRole('list', { name: 'Facts' });
    expect(within(facts).getByText('Area')).toBeInTheDocument();
    expect(within(facts).getByText('2.13 ha')).toBeInTheDocument();
    expect(within(facts).getByText('24%')).toBeInTheDocument();

    rerender(<MessageBubble message={bubble('M1')} names={names} locale="en" />);
    expect(screen.queryByRole('list', { name: 'Facts' })).not.toBeInTheDocument();
  });

  it('keeps tool calls and sources behind "How I know this"', async () => {
    const user = userEvent.setup();
    render(<MessageBubble message={bubble('M2')} names={names} locale="en" />);
    const toggle = screen.getByRole('button', { name: /How I know this/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('measure_plot')).not.toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('measure_plot')).toBeInTheDocument();
    expect(screen.getByText(/plot_id=PLT-DEMOIN/)).toBeInTheDocument();
    expect(screen.getByText(/area_hectares=2\.13/)).toBeInTheDocument();

    const link = screen.getByRole('link', { name: /ESA WorldCover 2021/ });
    expect(link).toHaveAttribute('href', 'https://esa-worldcover.org/');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('has no "How I know this" when there is nothing behind the message', () => {
    render(<MessageBubble message={bubble('M1')} names={names} locale="en" />);
    expect(screen.queryByRole('button', { name: /How I know this/ })).not.toBeInTheDocument();
  });

  it('never makes a link from an unsafe address', async () => {
    const user = userEvent.setup();
    const message: AgentMessage = {
      ...bubble('M2'),
      evidence: [{ label: 'Odd source', source: 'x', url: 'javascript:alert(1)' }],
    };
    render(<MessageBubble message={message} names={names} locale="en" />);
    await user.click(screen.getByRole('button', { name: /How I know this/ }));
    expect(screen.getByText('Odd source')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Odd source/ })).not.toBeInTheDocument();
  });

  it('shows who a hand-off is for', () => {
    render(<MessageBubble message={bubble('M3')} names={names} locale="en" />);
    const article = screen.getByRole('article', { name: 'Land agent — Hand-off' });
    expect(within(article).getByText('Tree agent')).toBeInTheDocument();
    expect(within(article).getByText('→')).toBeInTheDocument();
  });

  it('does not show coordinates, even when a message carries them', () => {
    const message: AgentMessage = {
      ...bubble('M2'),
      facts: { lat: 13.3, lon: 77.5, centroid_lat: 13.2, area_hectares: 2.13 },
    };
    render(<MessageBubble message={message} names={names} locale="en" />);
    const facts = screen.getByRole('list', { name: 'Facts' });
    expect(within(facts).getAllByRole('listitem')).toHaveLength(1);
    expect(facts).not.toHaveTextContent('13.3');
  });
});

describe('SummaryPanel', () => {
  it('shows the headline, the range, readiness, next steps and the not-a-credit line', () => {
    render(
      <SummaryPanel
        message={bubble('M8')}
        summary={runFixture.summary}
        names={names}
        locale="en"
      />,
    );
    const panel = screen.getByRole('article', { name: 'Summary' });
    expect(
      within(panel).getByText(/Your 420 mango trees may remove about 18\.8/),
    ).toBeInTheDocument();
    expect(within(panel).getByText(/Range 13\.2 – 24\.4/)).toBeInTheDocument();
    expect(within(panel).getByText(/55/)).toBeInTheDocument();
    expect(within(panel).getByText('Measure trunk diameters')).toBeInTheDocument();
    expect(within(panel).getByText('Add baseline land-use records')).toBeInTheDocument();
    expect(
      within(panel).getByText('Scenario estimate only. This is not an issued carbon credit.'),
    ).toBeInTheDocument();
  });

  it('still says it is not a credit when there is no estimate at all', () => {
    render(<SummaryPanel message={null} summary={null} names={names} locale="en" />);
    expect(screen.getByText(/not an issued carbon credit/i)).toBeInTheDocument();
    expect(screen.queryByText(/Estimated range/)).not.toBeInTheDocument();
  });
});
