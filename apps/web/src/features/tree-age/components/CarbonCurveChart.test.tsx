import '../i18n';
import type { ComponentProps, ReactElement } from 'react';
import type * as Recharts from 'recharts';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { assessmentFixture, curveFixture } from '../fixtures';
import { curveToChartData } from '../logic/treeAgeLogic';
import { CarbonCurveChart, CurveTip } from './CarbonCurveChart';

// jsdom has no layout, so the responsive wrapper would give the chart no size and draw nothing.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof Recharts>();
  const { cloneElement } = await import('react');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      cloneElement(children as ReactElement<{ width: number; height: number }>, {
        width: 800,
        height: 290,
      }),
  };
});

function renderChart(props: Partial<ComponentProps<typeof CarbonCurveChart>> = {}, age = 30) {
  const { carbon } = assessmentFixture({ age });
  return render(
    <CarbonCurveChart
      curve={carbon.curve}
      age={age}
      storedNow={carbon.stored_now}
      method={carbon.method}
      locale="en-IN"
      {...props}
    />,
  );
}

describe('CarbonCurveChart', () => {
  it('has one title and says in words what the chart shows', () => {
    renderChart();
    expect(screen.getByText('Carbon stored as the trees age')).toBeVisible();
    expect(
      screen.getByRole('img', {
        name: 'Chart of carbon stored by tree age. At 30 years: about 72 tCO₂e, between 57.6 and 86.4.',
      }),
    ).toBeVisible();
  });

  it('draws the curve, the low to high band and the line for the trees’ age today', () => {
    const { container } = renderChart();
    expect(container.querySelector('.recharts-line-curve')).not.toBeNull();
    expect(container.querySelector('.recharts-area-area')).not.toBeNull();
    expect(container.querySelector('.recharts-reference-line')).not.toBeNull();
    expect(container.querySelector('.recharts-reference-dot')).not.toBeNull();
    // The marker is labelled on the chart itself, not only by colour.
    expect(within(container).getByText('Today')).toBeInTheDocument();
  });

  it('labels both axes with round numbers, never 129.6', () => {
    const { container } = renderChart();
    const labels = (axis: string) =>
      [
        ...container.querySelectorAll(`.${axis}-tick-labels .recharts-cartesian-axis-tick-value`),
      ].map((node) => node.textContent);
    expect(labels('recharts-xAxis')).toEqual(['0', '10', '20', '30', '40', '50']);
    expect(labels('recharts-yAxis')).toEqual(['0', '50', '100', '150', '200']);
  });

  it('keeps small numbers readable on the vertical axis', () => {
    // One young tree holds a few kilograms: 0.025 t, not "0".
    const { container } = renderChart({
      curve: curveFixture(10, 0.01),
      age: 5,
      storedNow: { low: 0.05, central: 0.07, high: 0.09, unit: 'tCO2e' },
    });
    const labels = [
      ...container.querySelectorAll(
        '.recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value',
      ),
    ].map((node) => node.textContent);
    expect(labels).toEqual(['0', '0.025', '0.05', '0.075', '0.1']);
  });

  it('puts the "Today" label on the side with room for it', () => {
    const side = (age: number) => {
      const { container, unmount } = renderChart({}, age);
      const text = [...container.querySelectorAll('text.recharts-label')].find(
        (node) => node.textContent === 'Today',
      );
      const anchor = text?.getAttribute('text-anchor');
      unmount();
      return anchor;
    };
    // Near the left edge the label opens to the right of the line; elsewhere it ends at the line.
    expect(side(0)).toBe('start');
    expect(side(30)).toBe('end');
  });

  it('says what the vertical axis measures', () => {
    renderChart();
    expect(screen.getByText('Vertical axis: tCO₂e')).toBeVisible();
  });

  it('explains the three drawn things in a legend', () => {
    renderChart();
    expect(screen.getByText('Central estimate')).toBeVisible();
    expect(screen.getByText('Low to high range')).toBeVisible();
    expect(screen.getByText('Age today')).toBeVisible();
  });

  it('gives screen-reader users the same numbers in a table, including the current age', () => {
    renderChart();
    const table = screen.getByRole('table', { name: 'Carbon stored by age' });
    // The hidden wrapper clips the table; a table cannot be shrunk to nothing by itself.
    expect(table.parentElement).toHaveClass('sr-only');
    expect(within(table).getAllByRole('columnheader')).toHaveLength(4);
    const row = within(table).getByRole('rowheader', { name: '30' }).closest('tr');
    expect(row).toHaveTextContent('72');
    expect(row).toHaveTextContent('57.6 – 86.4');
    expect(row).toHaveTextContent('3.3');
    // A handful of rows, not fifty.
    expect(within(table).getAllByRole('row').length).toBeLessThanOrEqual(13);
  });

  it('adds a note when the numbers above come from a trunk measurement', () => {
    const { rerender } = renderChart();
    expect(screen.queryByText(/Your trunk measurement gives the numbers above/)).toBeNull();
    const { carbon } = assessmentFixture({ age: 30 });
    rerender(
      <CarbonCurveChart
        curve={carbon.curve}
        age={30}
        storedNow={carbon.stored_now}
        method="tier2-girth"
        locale="en-IN"
      />,
    );
    expect(screen.getByText(/Your trunk measurement gives the numbers above/)).toBeVisible();
  });

  it('says so instead of drawing an empty chart', () => {
    renderChart({ curve: [] });
    expect(screen.getByText('There is no curve to draw yet.')).toBeVisible();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('ignores curve points that are broken', () => {
    const { carbon } = assessmentFixture({ age: 30 });
    renderChart({
      curve: [
        ...carbon.curve.slice(0, 10),
        { age: Number.NaN, stored: 1, stored_low: 1, stored_high: 1, annual: 1 },
      ],
    });
    const table = screen.getByRole('table');
    expect(within(table).queryByText('NaN')).not.toBeInTheDocument();
  });

  it('is marked busy and dimmed while the numbers are being replaced', () => {
    const { container } = renderChart({ updating: true });
    expect(container.querySelector('figure')).toHaveAttribute('aria-busy', 'true');
  });
});

describe('CurveTip (what shows when someone points at the chart)', () => {
  const point = curveToChartData(assessmentFixture({ age: 30 }).carbon.curve)[30];

  it('gives the age, the carbon stored with its range and the carbon removed that year', () => {
    render(<CurveTip active point={point} locale="en-IN" />);
    expect(screen.getByText('Age 30 years')).toBeVisible();
    const stored = screen.getByText(/^Stored:/);
    expect(stored).toHaveTextContent('Stored: 72 tCO₂e (57.6 – 86.4)');
    expect(screen.getByText(/^Removed per year:/)).toHaveTextContent(
      'Removed per year: 3.3 tCO₂e/yr',
    );
  });

  it('says "year" for one year', () => {
    render(<CurveTip active point={{ ...point, age: 1 }} locale="en-IN" />);
    expect(screen.getByText('Age 1 year')).toBeVisible();
  });

  it('shows nothing when nothing is pointed at', () => {
    const { container, rerender } = render(
      <CurveTip active={false} point={point} locale="en-IN" />,
    );
    expect(container).toBeEmptyDOMElement();
    rerender(<CurveTip active point={undefined} locale="en-IN" />);
    expect(container).toBeEmptyDOMElement();
  });
});
