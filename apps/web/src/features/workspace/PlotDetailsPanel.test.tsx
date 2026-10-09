import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { resetUiStore, useUiStore } from '@/store/uiStore';
import { analysis, estimate, plot } from '@/test/fixtures';
import { PlotDetailsPanel } from './PlotDetailsPanel';
import { DEFAULT_FORM } from './logic/workspaceModel';

const species = [
  { id: 'mango', scientific_name: 'Mangifera indica', common_name: 'Mango', group: 'g', regions: ['IN'], suitable_climate_zones: [], reference_density_per_ha: { value: 150, source: '', verification_status: 'assumption' }, max_density_per_ha: 600, maturity_years: 8, wood_density_g_cm3: { value: 0.55, source: '', verification_status: 'pending' } },
  { id: 'teak', scientific_name: 'Tectona grandis', common_name: 'Teak', group: 'g', regions: ['IN'], suitable_climate_zones: [], reference_density_per_ha: { value: 500, source: '', verification_status: 'assumption' }, max_density_per_ha: 2500, maturity_years: 20, wood_density_g_cm3: { value: 0.55, source: '', verification_status: 'pending' } },
];

describe('PlotDetailsPanel', () => {
  beforeEach(() => resetUiStore());

  it('shows the four inputs and three result rows and forwards edits', () => {
    const onForm = vi.fn();
    render(
      <MemoryRouter>
        <PlotDetailsPanel plots={[plot]} plot={plot} species={species} form={DEFAULT_FORM} onForm={onForm} estimate={estimate} analysis={analysis} saving={false} updating={false} locale="en-IN" onSelectPlot={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText(/Land area/)).toHaveValue('2.13');
    fireEvent.change(screen.getByLabelText(/Number of trees/), { target: { value: '500' } });
    expect(onForm).toHaveBeenCalledWith(expect.objectContaining({ tree_count: 500 }));
    fireEvent.change(screen.getByLabelText(/Tree type/), { target: { value: 'teak' } });
    expect(onForm).toHaveBeenCalledWith(expect.objectContaining({ species_id: 'teak' }));
    expect(screen.getByText(/Estimated carbon removal range/)).toBeInTheDocument();
    expect(screen.getByText(/Vegetation health/)).toBeInTheDocument();
    expect(screen.getByText(/Programme readiness/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /See carbon potential/ })).toHaveAttribute('href', '/app/plots/PLT-TEST/results');
  });

  it('renders an empty state without a plot', () => {
    render(
      <MemoryRouter>
        <PlotDetailsPanel plots={[]} plot={null} species={species} form={DEFAULT_FORM} onForm={() => {}} saving={false} updating={false} locale="en-IN" onSelectPlot={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Add your land on the map/)).toBeInTheDocument();
  });

  it('keeps the title on its own line with a full-width plot selector', () => {
    render(
      <MemoryRouter>
        <PlotDetailsPanel plots={[plot]} plot={plot} species={species} form={DEFAULT_FORM} onForm={() => {}} saving={false} updating={false} locale="en-IN" onSelectPlot={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'Selected plot details' })).toHaveClass('whitespace-nowrap');
    expect(screen.getByRole('combobox', { name: 'Plot' })).toHaveClass('w-full');
    expect(screen.queryByText(/Approximate boundary/)).not.toBeInTheDocument();
  });

  it('notes an approximate boundary (not a KPI) and offers to draw the exact edges', () => {
    const approximate = { ...plot, source: 'pin-and-area' as const, boundary_quality: 'approximate' as const };
    render(
      <MemoryRouter>
        <PlotDetailsPanel plots={[approximate]} plot={approximate} species={species} form={DEFAULT_FORM} onForm={() => {}} saving={false} updating={false} locale="en-IN" onSelectPlot={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Approximate boundary — draw the exact edges for a better estimate/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Draw exact edges' }));
    expect(useUiStore.getState().landInputMode).toBe('edit');
  });
});
