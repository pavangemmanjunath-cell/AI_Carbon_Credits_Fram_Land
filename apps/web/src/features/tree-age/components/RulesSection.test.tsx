import '../i18n';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ruleFixture, rulesFixture } from '../fixtures';
import { RulesSection } from './RulesSection';

const DISCLAIMER =
  'Screening information only — not legal advice. Rules change; confirm with the responsible authority before acting. Scenario estimate only. This is not an issued carbon credit.';

function renderSection(rules = rulesFixture) {
  return render(
    <RulesSection rules={rules} regionLabel="India" locale="en-IN" disclaimer={DISCLAIMER} />,
  );
}

describe('RulesSection', () => {
  it('lists the rules that apply to these trees first, most local first', () => {
    renderSection();
    expect(
      screen.getByRole('heading', { level: 2, name: 'Rules for trees of this age' }),
    ).toBeVisible();
    const list = screen.getAllByRole('list')[0];
    const names = within(list)
      .getAllByRole('heading', { level: 3 })
      .map((h) => h.textContent);
    expect(names).toEqual([
      'Karnataka Preservation of Trees Act, 1976',
      'Carbon Credit Trading Scheme offset mechanism: BM FR05.002',
      'Verra VM0047 Afforestation, Reforestation and Revegetation',
      'ICVCM Core Carbon Principles: additionality',
    ]);
  });

  it('keeps the rules that do not apply behind one collapsed button with their count', async () => {
    const user = userEvent.setup();
    renderSection();
    expect(screen.queryByText('Haryana Pran Vayu Devta Pension Scheme')).not.toBeInTheDocument();

    const toggle = screen.getByRole('button', { name: /Other rules in India/ });
    expect(toggle).toHaveAccessibleName('Other rules in India (2)');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const haryana = screen.getByRole('article', { name: 'Haryana Pran Vayu Devta Pension Scheme' });
    expect(within(haryana).getByText('Only in Haryana (IN-HR)')).toBeVisible();
    const portland = screen.getByRole('article', { name: 'Portland heritage trees' });
    expect(within(portland).getByText(/Municipal example for Portland/)).toBeVisible();
    expect(within(portland).getByText('Example — check your own city’s rules')).toBeVisible();
  });

  it('does not repeat an outcome badge on the rules that do not apply', async () => {
    const user = userEvent.setup();
    renderSection();
    await user.click(screen.getByRole('button', { name: /Other rules in India/ }));
    const other = screen.getByRole('article', { name: 'Haryana Pran Vayu Devta Pension Scheme' });
    expect(other.querySelector('[data-outcome]')).toBeNull();
  });

  it('puts the disclaimer last, word for word', () => {
    renderSection();
    const disclaimer = screen.getByText(DISCLAIMER);
    expect(disclaimer).toBeVisible();
    const section = disclaimer.closest('section') as HTMLElement;
    expect(section.lastElementChild).toBe(disclaimer);
  });

  it('says so when no rule applies, and still offers the others', () => {
    renderSection(rulesFixture.map((r) => ({ ...r, applies: false })));
    expect(
      screen.getByText('No rule matches these trees. The other rules we checked are listed below.'),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Other rules in India (6)' })).toBeInTheDocument();
  });

  it('has no "other rules" button when every rule applies', () => {
    renderSection(rulesFixture.map((r) => ({ ...r, applies: true })));
    expect(screen.queryByRole('button', { name: /Other rules/ })).not.toBeInTheDocument();
  });

  it('shows the reason of a rule that does not apply, not an outcome that would mislead', async () => {
    const user = userEvent.setup();
    renderSection([
      ruleFixture({ id: 'a', name: 'Applies', applies: true }),
      ruleFixture({
        id: 'b',
        name: 'Does not apply',
        applies: false,
        outcome_for_you: 'payment',
        why: 'Only for trees aged 75 or more',
      }),
    ]);
    await user.click(screen.getByRole('button', { name: /Other rules/ }));
    expect(screen.getByText('Only for trees aged 75 or more')).toBeVisible();
    expect(screen.queryByText('Payment')).not.toBeInTheDocument();
  });
});
