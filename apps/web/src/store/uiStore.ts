import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { AreaUnit } from '@/config/regions';
import { mapEnv } from '@/config/mapEnv';
import type { LandInputMode } from '@/lib/landInput';

export type ApiStatus = 'unknown' | 'online' | 'offline';
export type LayerKey = 'landuse' | 'ndvi' | 'soil' | 'treeCover' | 'importedTrees';
/** The basemap switch in the map's corner: plain map or real satellite imagery. */
export type MapViewMode = 'map' | 'satellite';

export interface LayerState {
  landuse: boolean;
  ndvi: boolean;
  soil: boolean;
  /** "Tree cover (AI detected)" patches from `POST /plots/{id}/detect`. */
  treeCover: boolean;
  /** Tree tops / crowns from an imported file's preview. */
  importedTrees: boolean;
}

/** Species, year and survival of the tree form the user is editing — the Import dialog reuses them. */
export interface ActiveTreeForm {
  plotId: string;
  species_id: string;
  plantation_year: number;
  survival_rate: number | null;
}

export interface UiState {
  selectedPlotId: string | null;
  layers: LayerState;
  observationYear: number | null;
  language: string;
  areaUnit: AreaUnit | 'auto';
  country: string;
  apiStatus: ApiStatus;
  apiMode: 'demo' | 'live' | null;
  offlineBannerDismissed: boolean;
  navOpen: boolean;
  mapView: MapViewMode;
  /** Imagery provider id chosen in Settings, per country code sent to `/imagery/providers`. */
  imageryChoice: Record<string, string>;
  landInputMode: LandInputMode;
  importOpen: boolean;
  /** Import whose preview the map shows ("View on map" on the Data page). */
  mapImportId: string | null;
  activeTreeForm: ActiveTreeForm | null;
  welcomeDismissed: boolean;

  setSelectedPlotId: (id: string | null) => void;
  toggleLayer: (key: LayerKey, value?: boolean) => void;
  setObservationYear: (year: number | null) => void;
  setLanguage: (language: string) => void;
  setAreaUnit: (unit: AreaUnit | 'auto') => void;
  setCountry: (country: string) => void;
  setApiStatus: (status: ApiStatus, mode?: 'demo' | 'live' | null) => void;
  dismissOfflineBanner: () => void;
  setNavOpen: (open: boolean) => void;
  setMapView: (view: MapViewMode) => void;
  setImageryChoice: (countryKey: string, providerId: string | null) => void;
  setLandInputMode: (mode: LandInputMode) => void;
  setImportOpen: (open: boolean) => void;
  showImportOnMap: (importId: string, plotId?: string | null) => void;
  setMapImportId: (importId: string | null) => void;
  setActiveTreeForm: (form: ActiveTreeForm | null) => void;
  dismissWelcome: () => void;
}

export const DEFAULT_LAYERS: LayerState = { landuse: true, ndvi: true, soil: false, treeCover: false, importedTrees: false };

/** Fields kept in localStorage (`carboncreditbuy-ui`). */
type PersistedUi = Pick<UiState, 'selectedPlotId' | 'layers' | 'language' | 'areaUnit' | 'country' | 'mapView' | 'imageryChoice'>;

export const UI_STORE_VERSION = 2;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

/** Keeps only known layer keys with boolean values; missing keys get their defaults. */
export function sanitizeLayers(raw: unknown): LayerState {
  const source = isRecord(raw) ? raw : {};
  const out = { ...DEFAULT_LAYERS };
  for (const key of Object.keys(DEFAULT_LAYERS) as LayerKey[]) {
    if (typeof source[key] === 'boolean') out[key] = source[key] as boolean;
  }
  return out;
}

/**
 * Upgrades what an older build saved. v1 stored `cube3d` (3D columns, removed)
 * and a `satellite` layer flag (now the Map | Satellite switch).
 */
export function migrateUiState(persisted: unknown, version: number): Partial<PersistedUi> {
  const state = isRecord(persisted) ? { ...persisted } : {};
  delete state.cube3d;
  delete state.drawMode;
  const oldLayers = isRecord(state.layers) ? state.layers : {};
  const satelliteWasOn = version < 2 && oldLayers.satellite === true;
  const imageryChoice = isRecord(state.imageryChoice)
    ? Object.fromEntries(Object.entries(state.imageryChoice).filter(([, v]) => typeof v === 'string'))
    : {};
  return {
    ...(state as Partial<PersistedUi>),
    layers: sanitizeLayers(oldLayers),
    mapView: state.mapView === 'satellite' || satelliteWasOn ? 'satellite' : 'map',
    imageryChoice: imageryChoice as Record<string, string>,
  };
}

const initialState = () => ({
  selectedPlotId: null,
  layers: { ...DEFAULT_LAYERS },
  observationYear: null,
  language: mapEnv.defaultLanguage,
  areaUnit: 'auto' as AreaUnit | 'auto',
  country: mapEnv.defaultCountry,
  apiStatus: 'unknown' as ApiStatus,
  apiMode: null,
  offlineBannerDismissed: false,
  navOpen: false,
  mapView: 'map' as MapViewMode,
  imageryChoice: {} as Record<string, string>,
  landInputMode: 'none' as LandInputMode,
  importOpen: false,
  mapImportId: null,
  activeTreeForm: null,
  welcomeDismissed: false,
});

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      ...initialState(),

      setSelectedPlotId: (id) => set({ selectedPlotId: id }),
      toggleLayer: (key, value) => set((s) => ({ layers: { ...s.layers, [key]: value ?? !s.layers[key] } })),
      setObservationYear: (year) => set({ observationYear: year }),
      setLanguage: (language) => set({ language }),
      setAreaUnit: (unit) => set({ areaUnit: unit }),
      setCountry: (country) => set({ country }),
      setApiStatus: (status, mode) =>
        set((s) => ({
          apiStatus: status,
          apiMode: mode === undefined ? s.apiMode : mode,
          // A recovered connection re-arms the banner for the next outage.
          offlineBannerDismissed: status === 'online' ? false : s.offlineBannerDismissed,
        })),
      dismissOfflineBanner: () => set({ offlineBannerDismissed: true }),
      setNavOpen: (open) => set({ navOpen: open }),
      setMapView: (view) => set({ mapView: view }),
      setImageryChoice: (countryKey, providerId) =>
        set((s) => {
          const next = { ...s.imageryChoice };
          if (providerId) next[countryKey] = providerId;
          else delete next[countryKey];
          return { imageryChoice: next };
        }),
      setLandInputMode: (mode) => set({ landInputMode: mode }),
      setImportOpen: (open) => set({ importOpen: open }),
      showImportOnMap: (importId, plotId) =>
        set((s) => ({
          mapImportId: importId,
          layers: { ...s.layers, importedTrees: true },
          selectedPlotId: plotId ?? s.selectedPlotId,
        })),
      setMapImportId: (importId) => set({ mapImportId: importId }),
      setActiveTreeForm: (form) => set({ activeTreeForm: form }),
      dismissWelcome: () => set({ welcomeDismissed: true }),
    }),
    {
      name: 'carboncreditbuy-ui',
      version: UI_STORE_VERSION,
      storage: createJSONStorage(() => localStorage),
      partialize: (s): PersistedUi => ({
        selectedPlotId: s.selectedPlotId,
        layers: s.layers,
        language: s.language,
        areaUnit: s.areaUnit,
        country: s.country,
        mapView: s.mapView,
        imageryChoice: s.imageryChoice,
      }),
      migrate: (persisted, version) => migrateUiState(persisted, version) as UiState,
      // Same-version data can still miss newer layer keys: merge them field by field.
      merge: (persisted, current) => {
        const p = isRecord(persisted) ? (persisted as Partial<PersistedUi>) : {};
        return { ...current, ...p, layers: sanitizeLayers(p.layers ?? current.layers) };
      },
    },
  ),
);

/** Reset helper for tests. */
export function resetUiStore(): void {
  useUiStore.setState(initialState());
}
