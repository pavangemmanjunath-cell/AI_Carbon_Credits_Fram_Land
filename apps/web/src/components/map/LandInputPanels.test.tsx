import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { resetUiStore, useUiStore } from '@/store/uiStore';
import { renderWithProviders } from '@/test/render';
import type { FromLineBody, FromPointBody, PolygonGeometry } from '@/types/api';
import { CoordinatesPanel, PinSizePanel, TreeLinePanel } from './LandInputPanels';

const mocks = vi.hoisted(() => ({
  geometryFromPoint: vi.fn(),
  geometryFromLine: vi.fn(),
  parseCoordinates: vi.fn(),
}));

vi.mock('@/services/client', () => ({ client: mocks, probeHealth: vi.fn() }));

const square: PolygonGeometry = {
  type: 'Polygon',
  coordinates: [
    [
      [77.53, 13.29],
      [77.531, 13.29],
      [77.531, 13.291],
      [77.53, 13.291],
      [77.53, 13.29],
    ],
  ],
};
const slow = { timeout: 3000 };

describe('Pin + size panel', () => {
  beforeEach(() => {
    resetUiStore();
    Object.values(mocks).forEach((m) => m.mockReset());
    mocks.geometryFromPoint.mockImplementation(async (body: FromPointBody) => ({
      geometry: square,
      area_hectares: body.area.unit === 'ac' ? body.area.value * 0.4047 : body.area.value,
      area_acres: 4.94,
      boundary_quality: 'approximate',
      method: 'geodesic square centred on the pin',
    }));
  });

  it('asks for a pin first and starts the size in acres for India', () => {
    renderWithProviders(
      <PinSizePanel
        pin={null}
        country="IN"
        locale="en-IN"
        onUseCentre={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    expect(screen.getByText(/Click the map to drop a pin/)).toBeInTheDocument();
    expect(screen.getByLabelText('How big is your land?')).toHaveValue(2);
    expect(screen.getByRole('radio', { name: 'acres' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('button', { name: 'Create plot' })).toBeDisabled();
    expect(mocks.geometryFromPoint).not.toHaveBeenCalled();
  });

  it('uses hectares in the EU', () => {
    renderWithProviders(
      <PinSizePanel
        pin={null}
        country="EU"
        locale="en-IE"
        onUseCentre={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    expect(screen.getByRole('radio', { name: 'hectares' })).toHaveAttribute('aria-checked', 'true');
  });

  it('turns the pin and size into an approximate plot via /geometry/from-point', async () => {
    const onCreate = vi.fn();
    const onPreview = vi.fn();
    renderWithProviders(
      <PinSizePanel
        pin={{ lat: 13.2923, lon: 77.5384 }}
        country="IN"
        locale="en-IN"
        onUseCentre={() => {}}
        onCreate={onCreate}
        onCancel={() => {}}
        onPreview={onPreview}
      />,
    );
    expect(screen.getByText('Pin at 13.2923° N, 77.5384° E')).toBeInTheDocument();
    await waitFor(() => expect(mocks.geometryFromPoint).toHaveBeenCalled(), slow);
    expect(mocks.geometryFromPoint.mock.calls[0][0]).toEqual({
      lat: 13.2923,
      lon: 77.5384,
      area: { value: 2, unit: 'ac' },
      shape: 'square',
    });
    await waitFor(
      () => expect(screen.getByRole('button', { name: 'Create plot' })).toBeEnabled(),
      slow,
    );
    expect(onPreview).toHaveBeenLastCalledWith(square);

    fireEvent.click(screen.getByRole('radio', { name: 'hectares' }));
    fireEvent.change(screen.getByLabelText('How big is your land?'), { target: { value: '3' } });
    await waitFor(
      () =>
        expect(mocks.geometryFromPoint).toHaveBeenLastCalledWith(
          expect.objectContaining({ area: { value: 3, unit: 'ha' } }),
          expect.anything(),
        ),
      slow,
    );
    await waitFor(
      () => expect(screen.getByRole('button', { name: 'Create plot' })).toBeEnabled(),
      slow,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Create plot' }));
    expect(onCreate).toHaveBeenCalledWith({
      geometry: square,
      source: 'pin-and-area',
      boundary_quality: 'approximate',
    });
  });

  it('explains an invalid size instead of calling the API', () => {
    renderWithProviders(
      <PinSizePanel
        pin={{ lat: 13.29, lon: 77.53 }}
        country="IN"
        locale="en-IN"
        onUseCentre={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText('How big is your land?'), { target: { value: '0' } });
    expect(screen.getByRole('alert')).toHaveTextContent('The size must be larger than 0.');
  });

  it('offers the map centre as the pin', () => {
    const onUseCentre = vi.fn();
    renderWithProviders(
      <PinSizePanel
        pin={null}
        country="IN"
        locale="en-IN"
        onUseCentre={onUseCentre}
        onCreate={() => {}}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Use map centre' }));
    expect(onUseCentre).toHaveBeenCalled();
  });
});

describe('Tree line panel', () => {
  const line = {
    type: 'LineString' as const,
    coordinates: [
      [77.537, 13.291],
      [77.5395, 13.2912],
    ],
  };

  beforeEach(() => {
    resetUiStore();
    Object.values(mocks).forEach((m) => m.mockReset());
    mocks.geometryFromLine.mockImplementation(async (body: FromLineBody) => ({
      geometry: square,
      length_m: 270.6,
      area_hectares: (270.6 * body.width_m) / 10_000,
      suggested_tree_count: Math.floor(270.6 / body.spacing_m) + 1,
      boundary_quality: 'approximate',
      method: 'line buffered by width/2',
    }));
  });

  it('asks the user to draw the line first', () => {
    renderWithProviders(
      <TreeLinePanel
        line={null}
        locale="en-IN"
        onCreate={() => {}}
        onRedraw={() => {}}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    expect(screen.getByText(/Click along the row of trees/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create plot' })).not.toBeInTheDocument();
  });

  it('shows length and suggested trees, follows spacing and creates a plot with the tree count', async () => {
    const onCreate = vi.fn();
    renderWithProviders(
      <TreeLinePanel
        line={line}
        locale="en-IN"
        onCreate={onCreate}
        onRedraw={() => {}}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    expect(await screen.findByText('271 m', {}, slow)).toBeInTheDocument();
    expect(screen.getByText('55')).toBeInTheDocument();
    expect(mocks.geometryFromLine.mock.calls[0][0]).toEqual({ line, spacing_m: 5, width_m: 4 });

    fireEvent.change(screen.getByLabelText(/Space between trees/), { target: { value: '10' } });
    expect(await screen.findByText('28', {}, slow)).toBeInTheDocument();
    await waitFor(
      () => expect(screen.getByRole('button', { name: 'Create plot' })).toBeEnabled(),
      slow,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Create plot' }));
    expect(onCreate).toHaveBeenCalledWith({
      geometry: square,
      source: 'tree-line',
      boundary_quality: 'approximate',
      treeCount: 28,
    });
  });

  it('rejects spacing outside 0.5–50 m', () => {
    renderWithProviders(
      <TreeLinePanel
        line={line}
        locale="en-IN"
        onCreate={() => {}}
        onRedraw={() => {}}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Space between trees/), { target: { value: '0' } });
    expect(screen.getByRole('alert')).toHaveTextContent('Space between trees must be 0.5–50 m.');
  });
});

describe('Coordinates panel', () => {
  beforeEach(() => {
    resetUiStore();
    Object.values(mocks).forEach((m) => m.mockReset());
  });

  it('previews typed corners as a polygon and creates an exact plot', async () => {
    mocks.parseCoordinates.mockResolvedValue({
      points: [
        { lat: 13.29, lon: 77.53 },
        { lat: 13.29, lon: 77.531 },
        { lat: 13.291, lon: 77.531 },
        { lat: 13.291, lon: 77.53 },
      ],
      kind: 'polygon',
      geometry: square,
      area_hectares: 1.2,
      warnings: [],
    });
    const onCreate = vi.fn();
    const onPreview = vi.fn();
    renderWithProviders(
      <CoordinatesPanel
        country="IN"
        locale="en-IN"
        onCreate={onCreate}
        onCancel={() => {}}
        onPreview={onPreview}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Paste or type latitude, longitude/), {
      target: { value: '13.29, 77.53\n13.29, 77.531\n13.291, 77.531\n13.291, 77.53' },
    });
    expect(await screen.findByText('4 corners · 1.2 ha', {}, slow)).toBeInTheDocument();
    expect(mocks.parseCoordinates).toHaveBeenCalledWith(
      { text: '13.29, 77.53\n13.29, 77.531\n13.291, 77.531\n13.291, 77.53' },
      expect.anything(),
    );
    expect(onPreview).toHaveBeenLastCalledWith(square);
    fireEvent.click(screen.getByRole('button', { name: 'Create plot' }));
    expect(onCreate).toHaveBeenCalledWith({
      geometry: square,
      source: 'coordinates',
      boundary_quality: 'exact',
    });
  });

  it('treats one point like Pin + size and shows server warnings', async () => {
    useUiStore.setState({ areaUnit: 'hectare' });
    mocks.parseCoordinates.mockResolvedValue({
      points: [{ lat: 13.29, lon: 77.53 }],
      kind: 'point',
      geometry: { type: 'Point', coordinates: [77.53, 13.29] },
      area_hectares: null,
      warnings: ['Line 2: could not read a coordinate.'],
    });
    mocks.geometryFromPoint.mockResolvedValue({
      geometry: square,
      area_hectares: 2,
      area_acres: 4.94,
      boundary_quality: 'approximate',
      method: 'square',
    });
    const onCreate = vi.fn();
    renderWithProviders(
      <CoordinatesPanel
        country="IN"
        locale="en-IN"
        onCreate={onCreate}
        onCancel={() => {}}
        onPreview={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Paste or type latitude, longitude/), {
      target: { value: '13.29, 77.53\nhello' },
    });
    expect(
      await screen.findByText(/One point: 13\.2900° N, 77\.5300° E/, {}, slow),
    ).toBeInTheDocument();
    expect(screen.getByText('Line 2: could not read a coordinate.')).toBeInTheDocument();
    await waitFor(
      () =>
        expect(mocks.geometryFromPoint).toHaveBeenCalledWith(
          { lat: 13.29, lon: 77.53, area: { value: 2, unit: 'ha' }, shape: 'square' },
          expect.anything(),
        ),
      slow,
    );
    await waitFor(
      () => expect(screen.getByRole('button', { name: 'Create plot' })).toBeEnabled(),
      slow,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Create plot' }));
    expect(onCreate).toHaveBeenCalledWith({
      geometry: square,
      source: 'pin-and-area',
      boundary_quality: 'approximate',
    });
  });
});
