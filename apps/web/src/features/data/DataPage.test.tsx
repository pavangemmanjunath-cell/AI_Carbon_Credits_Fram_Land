import { fireEvent, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FeatureNeedsApiError } from '@/services/demoFallback';
import { resetUiStore, useUiStore } from '@/store/uiStore';
import { importRecord, plot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';
import DataPage from './DataPage';

const mocks = vi.hoisted(() => ({
  listPlots: vi.fn(),
  listImports: vi.fn(),
  deletePlot: vi.fn(),
  deleteImport: vi.fn(),
}));

vi.mock('@/services/client', () => ({ client: mocks, probeHealth: vi.fn() }));

const pinPlot = { ...plot, plot_id: 'PLT-PIN', name: 'Plot B', source: 'pin-and-area' as const, boundary_quality: 'approximate' as const };

describe('DataPage', () => {
  beforeEach(() => {
    resetUiStore();
    Object.values(mocks).forEach((m) => m.mockReset());
    mocks.listPlots.mockResolvedValue({ items: [plot, pinPlot] });
    mocks.listImports.mockResolvedValue({ items: [importRecord({ plot_id: plot.plot_id }), importRecord({ import_id: 'IMP-2', filename: 'broken.kml', format: 'kml', status: 'failed', trees: null, plot_id: null })] });
  });

  it('opens on the Land plots tab with friendly sources and the approximate badge', async () => {
    renderWithProviders(<DataPage />, { route: '/app/data' });
    expect(screen.getByRole('heading', { name: 'Data' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Land plots/ })).toHaveAttribute('aria-selected', 'true');
    const table = await screen.findByRole('table');
    expect(within(table).getByText('Plot B')).toBeInTheDocument();
    expect(within(table).getByText('Pin + size')).toBeInTheDocument();
    expect(within(table).getByText('Demo data')).toBeInTheDocument();
    expect(within(table).getAllByText('Approximate boundary')).toHaveLength(1);
    expect(within(table).getAllByRole('link', { name: /Results/ })[0]).toHaveAttribute('href', '/app/plots/PLT-TEST/results');
  });

  it('opens a plot on the map', async () => {
    renderWithProviders(<DataPage />, { route: '/app/data' });
    const table = await screen.findByRole('table');
    fireEvent.click(within(table).getAllByRole('button', { name: /Open on map/ })[1]);
    expect(useUiStore.getState().selectedPlotId).toBe('PLT-PIN');
    expect(await screen.findByText('workspace-route')).toBeInTheDocument();
  });

  it('lists imported files with type, linked land and result, and shows one on the map', async () => {
    renderWithProviders(<DataPage />, { route: '/app/data?tab=files' });
    expect(screen.getByRole('tab', { name: /Imported files/ })).toHaveAttribute('aria-selected', 'true');
    const table = await screen.findByRole('table');
    expect(within(table).getByText('orchard.laz')).toBeInTheDocument();
    expect(within(table).getByText('LAZ point cloud')).toBeInTheDocument();
    expect(within(table).getByText('Plot A')).toBeInTheDocument();
    expect(within(table).getByText('128 trees · mean height 6.4 m')).toBeInTheDocument();
    expect(within(table).getByText('Import failed')).toBeInTheDocument();
    const [viewTrees, viewFailed] = within(table).getAllByRole('button', { name: /View on map/ });
    expect(viewFailed).toBeDisabled();
    fireEvent.click(viewTrees);
    expect(useUiStore.getState()).toMatchObject({ mapImportId: 'IMP-1', selectedPlotId: 'PLT-TEST' });
    expect(useUiStore.getState().layers.importedTrees).toBe(true);
    expect(await screen.findByText('workspace-route')).toBeInTheDocument();
  });

  it('switches tabs and opens the Import dialog from the page', async () => {
    renderWithProviders(<DataPage />, { route: '/app/data' });
    fireEvent.click(screen.getByRole('tab', { name: /Imported files/ }));
    expect(await screen.findByText('orchard.laz')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Import' }));
    expect(useUiStore.getState().importOpen).toBe(true);
  });

  it('shows friendly empty states', async () => {
    mocks.listPlots.mockResolvedValue({ items: [] });
    mocks.listImports.mockResolvedValue({ items: [] });
    renderWithProviders(<DataPage />, { route: '/app/data' });
    expect(await screen.findByText(/No land yet\. Mark your land on the map/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /Imported files/ }));
    expect(await screen.findByText(/No imported files yet/)).toBeInTheDocument();
  });

  it('explains that imported files need the API when it is offline', async () => {
    mocks.listImports.mockRejectedValue(new FeatureNeedsApiError('Imported files'));
    renderWithProviders(<DataPage />, { route: '/app/data?tab=files' });
    expect(await screen.findByRole('alert')).toHaveTextContent('This needs the CarbonCreditBuy server');
  });
});
