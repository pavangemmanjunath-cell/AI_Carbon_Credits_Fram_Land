import '../i18n';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { runFixture } from '../fixtures';
import { GuardrailsStrip } from './GuardrailsStrip';

describe('GuardrailsStrip', () => {
  it('renders nothing when the run has no guardrails', () => {
    const { container } = render(<GuardrailsStrip guardrails={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('lists every check with its status in words, not only colour', () => {
    render(<GuardrailsStrip guardrails={runFixture.guardrails} />);
    const strip = screen.getByRole('region', { name: 'Guardrails' });
    expect(strip).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /passed|needs attention|failed/ })).toHaveLength(
      6,
    );
    expect(screen.getByRole('button', { name: /Not a credit.*passed/ })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Parameter check.*needs attention/ }),
    ).toBeInTheDocument();
  });

  it('explains a warning straight away instead of hiding it behind a hover', () => {
    render(<GuardrailsStrip guardrails={runFixture.guardrails} />);
    expect(
      screen.getAllByText(/2 parameters are still pending verification/).length,
    ).toBeGreaterThan(0);
  });

  it('shows the detail of a check on hover and focus', async () => {
    const user = userEvent.setup();
    const allPass = runFixture.guardrails.map((g) => ({ ...g, status: 'pass' as const }));
    render(<GuardrailsStrip guardrails={allPass} />);
    expect(screen.getByText(/Automatic safety checks on every result/)).toBeVisible();

    await user.hover(screen.getByRole('button', { name: /No coordinates shared/ }));
    expect(screen.getAllByText(/No coordinates were shared\./).length).toBeGreaterThan(0);

    await user.unhover(screen.getByRole('button', { name: /No coordinates shared/ }));
    await user.tab();
    await user.tab();
    expect(
      screen.getAllByText(/Every number is labelled as a scenario estimate\./)[0],
    ).toBeVisible();
  });

  it('marks a failed check as failed', () => {
    render(
      <GuardrailsStrip
        guardrails={[
          { id: 'not-a-credit', status: 'fail', detail: 'A number looked like a credit.' },
        ]}
      />,
    );
    expect(screen.getByRole('button', { name: /Not a credit.*failed/ })).toBeInTheDocument();
    expect(screen.getAllByText(/A number looked like a credit\./).length).toBeGreaterThan(0);
  });
});
