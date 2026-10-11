import { beforeEach, describe, expect, it } from 'vitest';
import {
  DEFAULT_LAYERS,
  migrateUiState,
  resetUiStore,
  sanitizeLayers,
  useUiStore,
} from './uiStore';

describe('uiStore', () => {
  beforeEach(() => resetUiStore());

  it('toggles layers and re-arms the offline banner when the API recovers', () => {
    const s = useUiStore.getState();
    s.toggleLayer('treeCover');
    expect(useUiStore.getState().layers.treeCover).toBe(true);
    s.setApiStatus('offline');
    s.dismissOfflineBanner();
    expect(useUiStore.getState().offlineBannerDismissed).toBe(true);
    s.setApiStatus('online', 'demo');
    expect(useUiStore.getState().offlineBannerDismissed).toBe(false);
    expect(useUiStore.getState().apiMode).toBe('demo');
  });

  it('keeps selection and preferences', () => {
    useUiStore.getState().setSelectedPlotId('PLT-1');
    useUiStore.getState().setAreaUnit('acre');
    expect(useUiStore.getState().selectedPlotId).toBe('PLT-1');
    expect(useUiStore.getState().areaUnit).toBe('acre');
  });

  it('remembers the imagery provider per country and clears it again', () => {
    const s = useUiStore.getState();
    s.setImageryChoice('ES', 'ign-spain-pnoa');
    s.setImageryChoice('IN', 'eox-s2cloudless-2017');
    expect(useUiStore.getState().imageryChoice).toEqual({
      ES: 'ign-spain-pnoa',
      IN: 'eox-s2cloudless-2017',
    });
    s.setImageryChoice('ES', null);
    expect(useUiStore.getState().imageryChoice).toEqual({ IN: 'eox-s2cloudless-2017' });
  });

  it('shows an import on the map by turning on the imported-trees layer and selecting its plot', () => {
    useUiStore.getState().showImportOnMap('IMP-1', 'PLT-9');
    const s = useUiStore.getState();
    expect(s.mapImportId).toBe('IMP-1');
    expect(s.layers.importedTrees).toBe(true);
    expect(s.selectedPlotId).toBe('PLT-9');
  });

  it('migrates v1 storage: drops the removed 3D field and maps the old satellite layer to the switch', () => {
    const migrated = migrateUiState(
      {
        cube3d: true,
        layers: { satellite: true, landuse: false, ndvi: true, soil: true },
        language: 'kn',
      },
      1,
    );
    expect(migrated).not.toHaveProperty('cube3d');
    expect(migrated.mapView).toBe('satellite');
    expect(migrated.language).toBe('kn');
    expect(migrated.layers).toEqual({ ...DEFAULT_LAYERS, landuse: false, ndvi: true, soil: true });
    expect(migrated.layers).not.toHaveProperty('satellite');
    expect(migrateUiState(null, 1).layers).toEqual(DEFAULT_LAYERS);
    expect(migrateUiState({ layers: { satellite: false } }, 1).mapView).toBe('map');
  });

  it('fills missing layer keys and ignores junk values', () => {
    expect(sanitizeLayers({ ndvi: false, treeCover: 'yes', bogus: true })).toEqual({
      ...DEFAULT_LAYERS,
      ndvi: false,
    });
  });
});
