import '../i18n';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ruleFixture, rulesFixture } from '../fixtures';
import { RuleCard } from './RuleCard';

function ruleById(id: string) {
  const rule = rulesFixture.find((r) => r.id === id);
  if (!rule) throw new Error(`No fixture rule ${id}`);
  return rule;
}

const haryana = ruleById('in-hr-pran-vayu-devta-pension');
const karnataka = ruleById('in-ka-preservation-of-trees-act');
const portland = ruleById('us-or-portland-heritage-trees');

describe('RuleCard', () => {
  it('names the rule and its authority, says what it means for the trees and gives the summary', () => {
    render(<RuleCard rule={karnataka} locale="en-IN" />);
    const card = screen.getByRole('article', { name: 'Karnataka Preservation of Trees Act, 1976' });
    expect(within(card).getByRole('heading', { level: 3 })).toHaveTextContent(
      'Karnataka Preservation of Trees Act, 1976',
    );
    expect(within(card).getByText('Government of Karnataka')).toBeVisible();
    expect(within(card).getByText('Protected')).toBeVisible();
    expect(within(card).getByText('Tree protection')).toBeVisible();
    expect(
      within(card).getByText('Felling trees needs permission from the tree officer.'),
    ).toBeVisible();
  });

  it('writes an amount with its currency, its unit and the month it was checked', () => {
    render(<RuleCard rule={{ ...haryana, applies: true }} locale="en-IN" />);
    const card = screen.getByRole('article');
    expect(within(card).getByText(/₹3,000/)).toHaveTextContent(
      '₹3,000 per tree per year (as of 2026-07)',
    );
  });

  it('shows an amount in a currency the app has no symbol for with its code', () => {
    const rule = ruleFixture({
      id: 'x',
      name: 'Other money',
      amount: { value: 12.5, currency: 'CHF', unit: 'per tree', as_of: null },
    });
    render(<RuleCard rule={rule} locale="en-IN" />);
    expect(screen.getByText(/CHF 12\.5/)).toHaveTextContent('CHF 12.5 per tree');
  });

  it('keeps a unit it has no translation for exactly as the API wrote it', () => {
    const rule = ruleFixture({
      id: 'x',
      name: 'Odd unit',
      amount: { value: 40, currency: 'INR', unit: 'per canopy', as_of: null },
    });
    render(<RuleCard rule={rule} locale="en-IN" />);
    expect(screen.getByText(/₹40/)).toHaveTextContent('₹40 per canopy');
  });

  it('never calls a source verified unless the API says so', () => {
    const { rerender } = render(<RuleCard rule={karnataka} locale="en-IN" />);
    expect(screen.getByText('Verified source')).toBeVisible();

    rerender(<RuleCard rule={{ ...karnataka, verification_status: 'pending' }} locale="en-IN" />);
    expect(screen.getByText('Not yet verified — check with the authority')).toBeVisible();
    expect(screen.queryByText('Verified source')).not.toBeInTheDocument();

    rerender(<RuleCard rule={{ ...karnataka, verification_status: '' }} locale="en-IN" />);
    expect(screen.getByText('Not yet verified — check with the authority')).toBeVisible();

    rerender(<RuleCard rule={{ ...karnataka, verification_status: 'VERIFIED?' }} locale="en-IN" />);
    expect(screen.getByText('Not yet verified — check with the authority')).toBeVisible();
  });

  it('opens each source in a new tab and says so to screen readers', () => {
    render(<RuleCard rule={karnataka} locale="en-IN" />);
    const link = screen.getByRole('link', { name: /Official page/ });
    expect(link).toHaveAttribute('href', 'https://example.org/rule');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(within(link).getByText('(opens in a new tab)')).toBeInTheDocument();
    expect(screen.getByText('Test Publisher', { exact: false })).toBeVisible();
  });

  it('shows a source with a risky address as plain text, never as a link', () => {
    const rule = ruleFixture({
      id: 'x',
      name: 'Risky',
      sources: [
        { title: 'Click me', publisher: null, url: 'javascript:alert(1)', accessed: null },
        { title: 'Paper copy only', publisher: 'Registry', url: null, accessed: null },
      ],
    });
    render(<RuleCard rule={rule} locale="en-IN" />);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('Click me')).toBeVisible();
    expect(screen.getByText('Paper copy only')).toBeVisible();
  });

  it('labels a municipal example as an example', () => {
    render(<RuleCard rule={portland} locale="en-US" />);
    expect(screen.getByText('Example — check your own city’s rules')).toBeVisible();
  });

  it('flags a rule that is not in force yet', () => {
    const { rerender } = render(
      <RuleCard rule={{ ...karnataka, status: 'proposed' }} locale="en-IN" />,
    );
    expect(screen.getByText('Proposed, not yet in force')).toBeVisible();
    // A rule in force gets no status chip at all.
    rerender(<RuleCard rule={karnataka} locale="en-IN" />);
    expect(screen.queryByText('Proposed, not yet in force')).not.toBeInTheDocument();
  });

  it('puts a rule that does not apply in a quieter card with the reason instead of an outcome', () => {
    render(<RuleCard rule={haryana} locale="en-IN" muted />);
    const card = screen.getByRole('article', { name: 'Haryana Pran Vayu Devta Pension Scheme' });
    expect(card).toHaveAttribute('data-applies', 'false');
    expect(within(card).getByText('Only in Haryana (IN-HR)')).toBeVisible();
    expect(card.querySelector('[data-outcome]')).toBeNull();
    expect(within(card).getByText('Not yet verified — check with the authority')).toBeVisible();
  });

  it('does not repeat the reason on a rule that applies', () => {
    render(<RuleCard rule={karnataka} locale="en-IN" />);
    expect(screen.queryByText('Applies in Karnataka (IN-KA) at any age')).not.toBeInTheDocument();
  });

  it('writes a kind of rule it has no label for in plain words', () => {
    render(
      <RuleCard
        rule={ruleFixture({ id: 'x', name: 'New kind', category: 'new-kind' })}
        locale="en"
      />,
    );
    expect(screen.getByText('New kind', { selector: 'span' })).toBeVisible();
  });

  it('survives a rule that is missing nearly everything', () => {
    render(
      <RuleCard
        rule={ruleFixture({
          id: 'bare',
          name: 'Bare rule',
          authority: '',
          summary: '',
          sources: [],
          amount: null,
          category: '',
        })}
        locale="en-IN"
      />,
    );
    expect(screen.getByRole('article', { name: 'Bare rule' })).toBeVisible();
    expect(screen.queryByText('Sources')).not.toBeInTheDocument();
  });
});
