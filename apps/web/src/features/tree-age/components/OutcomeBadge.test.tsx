import '../i18n';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OutcomeBadge } from './OutcomeBadge';

const OUTCOMES = [
  ['not-eligible', 'Not eligible'],
  ['eligible', 'Eligible'],
  ['conditional', 'Conditional'],
  ['protected', 'Protected'],
  ['payment', 'Payment'],
  ['not-applicable', 'Not applicable'],
] as const;

describe('OutcomeBadge', () => {
  it.each(OUTCOMES)('writes the outcome "%s" in words: %s', (outcome, label) => {
    render(<OutcomeBadge outcome={outcome} />);
    expect(screen.getByText(label)).toBeVisible();
  });

  it('gives every outcome its own colour, its own icon and its own word', () => {
    const colours = new Set<string>();
    const icons = new Set<string>();
    const words = new Set<string>();
    for (const [outcome] of OUTCOMES) {
      const { container, unmount } = render(<OutcomeBadge outcome={outcome} />);
      const badge = container.querySelector<HTMLElement>('[data-outcome]');
      const icon = badge?.querySelector('svg');
      expect(badge).not.toBeNull();
      // The icon is decoration: the word carries the meaning for screen readers.
      expect(icon).toHaveAttribute('aria-hidden', 'true');
      colours.add(badge?.className ?? '');
      icons.add(icon?.getAttribute('class') ?? '');
      words.add(badge?.textContent ?? '');
      unmount();
    }
    expect(colours.size).toBe(OUTCOMES.length);
    expect(icons.size).toBe(OUTCOMES.length);
    expect(words.size).toBe(OUTCOMES.length);
  });

  it('shows an outcome it does not know as "Unknown", in grey, without guessing', () => {
    const { container } = render(<OutcomeBadge outcome="something-new" />);
    expect(screen.getByText('Unknown')).toBeVisible();
    const badge = container.querySelector<HTMLElement>('[data-outcome="something-new"]');
    expect(badge?.className).toContain('bg-ground');
  });
});
