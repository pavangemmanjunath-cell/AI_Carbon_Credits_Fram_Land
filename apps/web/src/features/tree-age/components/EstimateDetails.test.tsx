import '../i18n';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { assessmentFixture } from '../fixtures';
import type { TreeAgeAssessment } from '../types';
import { EstimateDetails } from './EstimateDetails';

async function open(assessment: TreeAgeAssessment) {
  const user = userEvent.setup();
  render(<EstimateDetails assessment={assessment} locale="en-IN" />);
  await user.click(screen.getByRole('button', { name: 'How was this estimated?' }));
}

function rowText(term: string): string {
  const dt = screen.getByText(term, { selector: 'dt' });
  return dt.nextElementSibling?.textContent ?? '';
}

describe('EstimateDetails', () => {
  it('stays closed until someone asks', () => {
    render(<EstimateDetails assessment={assessmentFixture()} locale="en-IN" />);
    const toggle = screen.getByRole('button', { name: 'How was this estimated?' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Method')).not.toBeInTheDocument();
  });

  it('says which method was used, how sure it is and which climate zone it assumed', async () => {
    await open(assessmentFixture());
    expect(rowText('Method')).toBe('From the age of the trees only');
    expect(rowText('Confidence')).toBe('Low');
    expect(rowText('Climate zone')).toBe('Tropical dry · region default (IN)');
  });

  it('gives the per-tree numbers in kilograms', async () => {
    await open(assessmentFixture());
    expect(rowText('Per tree')).toBe('About 2,880 kg CO₂e stored, 132 kg CO₂e added per year');
  });

  it('says how many growth numbers are not yet verified', async () => {
    await open(assessmentFixture());
    expect(rowText('Growth numbers used')).toBe('2 numbers, 1 not yet verified');
  });

  it('says so when every growth number is verified', async () => {
    const base = assessmentFixture();
    await open({
      ...base,
      carbon: {
        ...base.carbon,
        parameters_used: base.carbon.parameters_used.map((p) => ({
          ...p,
          verification_status: 'verified',
        })),
      },
    });
    expect(rowText('Growth numbers used')).toBe('2 numbers, all verified');
  });

  it('counts a number with no verification status as not verified', async () => {
    const base = assessmentFixture();
    await open({
      ...base,
      carbon: {
        ...base.carbon,
        parameters_used: [{ ...base.carbon.parameters_used[0], verification_status: '' }],
      },
    });
    expect(rowText('Growth numbers used')).toBe('1 number, 1 not yet verified');
  });

  it('says when the numbers come from a trunk measurement', async () => {
    const base = assessmentFixture();
    await open({ ...base, carbon: { ...base.carbon, method: 'tier2-girth' } });
    expect(rowText('Method')).toBe('From your trunk measurement');
  });

  it('lists the notes from the estimate', async () => {
    await open(assessmentFixture());
    expect(
      screen.getByText('Nothing about the actual trees is measured, so confidence is low.'),
    ).toBeVisible();
  });

  it('leaves out rows it has nothing to say for', async () => {
    const base = assessmentFixture();
    await open({
      ...base,
      climate_zone: null,
      climate_zone_label: null,
      climate_zone_source: null,
      carbon: {
        ...base.carbon,
        confidence: null,
        parameters_used: [],
        notes: [],
        per_tree: { stored_now_kg_co2e: null, annual_now_kg_co2e: null },
      },
    });
    const terms = screen.getAllByText(/./, { selector: 'dt' }).map((dt) => dt.textContent);
    expect(terms).toEqual(['Method']);
  });

  it('shows a confidence level it has no word for as the API wrote it', async () => {
    const base = assessmentFixture();
    await open({ ...base, carbon: { ...base.carbon, confidence: 'moderate' } });
    expect(rowText('Confidence')).toBe('moderate');
  });
});
