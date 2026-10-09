import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/services/api';
import { resetUiStore, useUiStore } from '@/store/uiStore';
import { importRecord, plot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';
import type { ImportRecord, ImportUploadOptions, Plot } from '@/types/api';
import { ImportDialog } from './ImportDialog';

const mocks = vi.hoisted(() => ({
  uploadImport: vi.fn(),
  createPlot: vi.fn(),
  createTrees: vi.fn(),
  listPlots: vi.fn(),
  species: vi.fn(),
}));

vi.mock('@/services/client', () => ({
  client: mocks,
  probeHealth: vi.fn(),
}));

const boundaryRecord: ImportRecord = importRecord({
  import_id: 'IMP-B',
  filename: 'field.kml',
  format: 'kml',
  kind: 'boundary',
  trees: null,
  boundary: { geometry: plot.geometry!, area_hectares: 2.13, name: 'Field 7' },
});

function addFiles(files: File[]) {
  const input = screen.getByLabelText('Choose files to import');
  fireEvent.change(input, { target: { files } });
}

describe('ImportDialog', () => {
  beforeEach(() => {
    resetUiStore();
    Object.values(mocks).forEach((m) => m.mockReset());
    mocks.listPlots.mockResolvedValue({ items: [plot] });
    mocks.species.mockResolvedValue([{ id: 'mango', common_name: 'Mango', scientific_name: 'Mangifera indica', regions: ['IN'] }]);
    useUiStore.setState({ selectedPlotId: plot.plot_id, country: 'IN' });
  });

  it('shows the Trimble-style drop zone, privacy line and both switches on by default', () => {
    renderWithProviders(<ImportDialog onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: 'Import data' })).toBeInTheDocument();
    expect(screen.getByTestId('import-drop-zone')).toHaveTextContent('Drag GeoJSON, KML/KMZ, CSV, LAS or LAZ files here or browse to upload');
    expect(screen.getByText('.e57 if your server supports it')).toBeInTheDocument();
    expect(screen.getByText('Only the results are kept — the file itself is not stored.')).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Use boundary files as my land' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('switch', { name: 'Run tree detection on import' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('button', { name: /^Import$/ })).toBeDisabled();
  });

  it('lists added files with type and size, flags unsupported ones and removes them', () => {
    renderWithProviders(<ImportDialog onClose={() => {}} />);
    addFiles([new File(['x'.repeat(2048)], 'orchard.laz'), new File(['x'], 'photo.jpg')]);
    const list = screen.getByRole('list', { name: 'Files to import' });
    expect(within(list).getByText('orchard.laz')).toBeInTheDocument();
    expect(within(list).getByText(/2 kB · LAZ point cloud/)).toBeInTheDocument();
    expect(within(list).getByText(/This file type cannot be imported/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Remove photo.jpg' }));
    expect(screen.queryByText('photo.jpg')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Import$/ })).toBeEnabled();
  });

  it('accepts dropped files', () => {
    renderWithProviders(<ImportDialog onClose={() => {}} />);
    fireEvent.drop(screen.getByTestId('import-drop-zone'), { dataTransfer: { files: [new File(['{}'], 'field.geojson')] } });
    expect(screen.getByText('field.geojson')).toBeInTheDocument();
  });

  it('uploads one file at a time with the selected plot and the switch values, then uses a boundary as land', async () => {
    const order: string[] = [];
    mocks.uploadImport.mockImplementation(async (file: File, options: ImportUploadOptions) => {
      order.push(`${file.name}:${options.plotId}:${options.purpose}:${options.runDetection}`);
      options.onProgress?.(1);
      return file.name === 'field.kml' ? boundaryRecord : importRecord({ plot_id: 'PLT-NEW' });
    });
    const created: Plot = { ...plot, plot_id: 'PLT-NEW', name: 'Field 7', source: 'import' };
    mocks.createPlot.mockResolvedValue(created);
    renderWithProviders(<ImportDialog onClose={() => {}} />);
    fireEvent.click(screen.getByRole('switch', { name: 'Run tree detection on import' }));
    addFiles([new File(['<kml/>'], 'field.kml'), new File(['x'], 'orchard.laz')]);
    fireEvent.click(screen.getByRole('button', { name: /^Import$/ }));

    expect(await screen.findByText('Boundary found · 2.13 ha')).toBeInTheDocument();
    await waitFor(() => expect(mocks.createPlot).toHaveBeenCalledTimes(1));
    expect(mocks.createPlot.mock.calls[0][0]).toMatchObject({ name: 'Field 7', source: 'import', boundary_quality: 'exact' });
    expect(await screen.findByText('Added as Field 7')).toBeInTheDocument();
    await waitFor(() => expect(order).toHaveLength(2));
    // the second file is linked to the land created from the first one
    expect(order).toEqual(['field.kml:PLT-TEST:auto:false', 'orchard.laz:PLT-NEW:auto:false']);
    expect(useUiStore.getState().selectedPlotId).toBe('PLT-NEW');
    expect(await screen.findByRole('button', { name: 'Done' })).toBeInTheDocument();
  });

  it('offers "Use as my land" when the boundary switch is off', async () => {
    mocks.uploadImport.mockResolvedValue(boundaryRecord);
    mocks.createPlot.mockResolvedValue({ ...plot, plot_id: 'PLT-NEW', name: 'Field 7' });
    renderWithProviders(<ImportDialog onClose={() => {}} />);
    fireEvent.click(screen.getByRole('switch', { name: 'Use boundary files as my land' }));
    addFiles([new File(['<kml/>'], 'field.kml')]);
    fireEvent.click(screen.getByRole('button', { name: /^Import$/ }));
    const use = await screen.findByRole('button', { name: 'Use as my land' });
    expect(mocks.createPlot).not.toHaveBeenCalled();
    fireEvent.click(use);
    await waitFor(() => expect(mocks.createPlot).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('Added as Field 7')).toBeInTheDocument();
  });

  it('turns detected trees into a model-estimated inventory for the plot', async () => {
    useUiStore.setState({ activeTreeForm: { plotId: plot.plot_id, species_id: 'teak', plantation_year: 2018, survival_rate: 0.9 } });
    mocks.uploadImport.mockResolvedValue(importRecord({ plot_id: plot.plot_id }));
    mocks.createTrees.mockImplementation(async (plotId: string, body: Record<string, unknown>) => ({ inventory_id: 'INV-9', plot_id: plotId, ...body }));
    renderWithProviders(<ImportDialog onClose={() => {}} />);
    addFiles([new File(['x'], 'orchard.laz')]);
    fireEvent.click(screen.getByRole('button', { name: /^Import$/ }));
    expect(await screen.findByText(/128 trees detected \(mean height 6\.4 m\)/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Use 120 trees for Plot A' }));
    await waitFor(() => expect(mocks.createTrees).toHaveBeenCalledTimes(1));
    expect(mocks.createTrees).toHaveBeenCalledWith('PLT-TEST', {
      species_id: 'teak',
      tree_count: 120,
      plantation_year: 2018,
      average_dbh_cm: null,
      average_height_m: 6.4,
      survival_rate: 0.9,
      measurement_source: 'model-estimated',
    });
    expect(await screen.findByText('Saved as the tree count of Plot A')).toBeInTheDocument();
  });

  it('shows the RFC 7807 detail inline when a file is rejected', async () => {
    mocks.uploadImport.mockRejectedValue(new ApiError(415, { title: 'Unsupported Media Type', detail: 'Convert the E57 file to LAS/LAZ with CloudCompare or PDAL.' }, '415'));
    renderWithProviders(<ImportDialog onClose={() => {}} />);
    addFiles([new File(['x'], 'scan.e57')]);
    fireEvent.click(screen.getByRole('button', { name: /^Import$/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Import failed: Convert the E57 file to LAS/LAZ with CloudCompare or PDAL.');
  });

  it('closes on Cancel', () => {
    const onClose = vi.fn();
    renderWithProviders(<ImportDialog onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalled();
  });
});
