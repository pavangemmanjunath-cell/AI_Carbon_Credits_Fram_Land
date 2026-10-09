import '../i18n';
import type { ComponentProps } from 'react';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { assessmentFixture, rulesInfoFixture } from '../fixtures';
import { HeadlineCards } from './HeadlineCards';

function renderCards(props: Partial<ComponentProps<typeof HeadlineCards>> = {}, age = 30) {
  const { carbon, age_class } = assessmentFixture({ age });
  return render(
    <HeadlineCards
      stored={carbon.stored_now}
      annual={carbon.annual_now}
      ageClass={age_class}
      ageClasses={rulesInfoFixture.age_classes}
      locale="en-IN"
      {...props}
    />,
  );
}

describe('HeadlineCards', () => {
  it('shows exactly three values and nothing else', () => {
    renderCards();
    const region = screen.getByRole('region', { name: 'Results' });
    const cards = within(region).getAllByRole('article');
    expect(cards.map((c) => c.getAttribute('aria-label'))).toEqual([
      'Carbon stored now',
      'Carbon removed per year now',
      'Age class',
    ]);
  });

  it('puts the central estimate first and bold, with the low to high range under it', () => {
    renderCards();
    const stored = screen.getByRole('article', { name: 'Carbon stored now' });
    expect(within(stored).getByText('72')).toBeVisible();
    expect(within(stored).getByText('tCO₂e')).toBeVisible();
    expect(stored).toHaveTextContent('57.6 – 86.4');
    expect(within(stored).getByText('Low to high:')).toBeInTheDocument();
    expect(
      within(stored).getByText('All the carbon these trees have taken in so far.'),
    ).toBeVisible();
  });

  it('shows the carbon removed each year in tCO₂e a year, with its range', () => {
    renderCards();
    const annual = screen.getByRole('article', { name: 'Carbon removed per year now' });
    expect(within(annual).getByText('3.3')).toBeVisible();
    expect(within(annual).getByText('tCO₂e/yr')).toBeVisible();
    expect(annual).toHaveTextContent('2.64 – 3.96');
  });

  it('gives a small number enough decimals not to read as zero', () => {
    renderCards({
      stored: { low: 0.0096, central: 0.012, high: 0.0144, unit: 'tCO2e' },
      annual: { low: 0.48, central: 0.6, high: 0.72, unit: 'tCO2e/yr' },
    });
    const stored = screen.getByRole('article', { name: 'Carbon stored now' });
    expect(within(stored).getByText('0.012')).toBeVisible();
    expect(stored).toHaveTextContent('0.01 – 0.014');
  });

  it('names the age class and gives the years it covers', () => {
    renderCards();
    const card = screen.getByRole('article', { name: 'Age class' });
    expect(within(card).getByText('Mature')).toBeVisible();
    expect(within(card).getByText('21–49 years')).toBeVisible();
  });

  it('writes the oldest class as an open-ended span', () => {
    renderCards({}, 90);
    const card = screen.getByRole('article', { name: 'Age class' });
    expect(within(card).getByText('Veteran')).toBeVisible();
    expect(within(card).getByText('75+ years')).toBeVisible();
  });

  it('leaves the span out when the limits are not known, and shows a class it does not know as the API wrote it', () => {
    renderCards({ ageClasses: undefined, ageClass: { id: 'ancient', label: 'Ancient (200+)' } });
    const card = screen.getByRole('article', { name: 'Age class' });
    expect(within(card).getByText('Ancient (200+)')).toBeVisible();
    expect(card).not.toHaveTextContent('years');
  });

  it('marks the numbers as being replaced while new ones load', () => {
    const { rerender } = renderCards({ updating: true });
    expect(screen.getByRole('region', { name: 'Results' })).toHaveAttribute('aria-busy', 'true');
    const { carbon, age_class } = assessmentFixture({ age: 30 });
    rerender(
      <HeadlineCards
        stored={carbon.stored_now}
        annual={carbon.annual_now}
        ageClass={age_class}
        locale="en-IN"
      />,
    );
    expect(screen.getByRole('region', { name: 'Results' })).toHaveAttribute('aria-busy', 'false');
  });

  it('formats numbers for the language and region', () => {
    renderCards(
      {
        stored: { low: 1_150_000, central: 1_234_567, high: 1_300_000, unit: 'tCO2e' },
        locale: 'en-IN',
      },
      30,
    );
    // Indian digit grouping: 12,34,567.
    expect(screen.getByText('12,34,567')).toBeVisible();
  });
});
