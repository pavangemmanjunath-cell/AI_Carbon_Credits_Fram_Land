import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import * as maplibregl from 'maplibre-gl';
import type { Feature, FeatureCollection } from 'geojson';
import { regionFor } from '@/config/regions';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { detectionSummary, patchInfo } from '@/lib/detection';
import { landUseShares, soilInsight } from '@/lib/insights';
import { formatArea } from '@/lib/format';
import { boundsOf, validatePolygon } from '@/lib/geo';
import {
  isShapeMode,
  plotRequestFor,
  type LandToolAction,
  type NewPlotRequest,
} from '@/lib/landInput';
import { activeYear, cubeSliceToGeoJson, cubeYears, timeIndexForYear } from '@/lib/ndviGrid';
import { useUiStore } from '@/store/uiStore';
import type {
  Analysis,
  Cube,
  Detection,
  GeocodeResult,
  ImageryProvider,
  ImportRecord,
  LatLon,
  LineStringGeometry,
  Plot,
  PolygonGeometry,
} from '@/types/api';
import { AttributionBar } from './AttributionBar';
import {
  DETECT_FILL,
  DETECT_LINE,
  DETECT_SOURCE,
  ensureOverlayLayers,
  geometryToCollection,
  IMPORT_CROWNS,
  IMPORT_POINTS,
  IMPORT_SOURCE,
  NDVI_FILL,
  NDVI_SOURCE,
  PLOT_FILL,
  PLOT_SOURCE,
  plotsToGeoJson,
  PREVIEW_SOURCE,
  setLayersVisible,
  setOverlayData,
  syncImageryLayer,
} from './layers';
import {
  CoordinatesPanel,
  DrawHintPanel,
  PinSizePanel,
  TreeLinePanel,
  type PreviewGeometry,
} from './LandInputPanels';
import { LandInputToolbar } from './LandInputToolbar';
import { LandInputWelcome } from './LandInputWelcome';
import { LiveClock, MapViewSwitch, ViewControls } from './MapControls';
import { LayerPanel, MapSearch, YearSlider } from './MapPanels';
import { useDrawTools } from './useDrawTools';
import { useMapLibre } from './useMapLibre';

export interface MapViewProps {
  plots: Plot[];
  plotsLoading?: boolean;
  selectedPlot: Plot | null;
  cube?: Cube;
  /** Latest analysis of the selected plot (land-use and soil insights in the layer panel). */
  analysis?: Analysis;
  analysisLoading?: boolean;
  country: string;
  locale: string;
  initialQuery?: string;
  imagery: { provider: ImageryProvider | null; loading: boolean };
  detection: { data?: Detection; loading: boolean; error: unknown };
  importedTrees: {
    record?: ImportRecord | null;
    loading: boolean;
    error: unknown;
    fitOnLoad?: boolean;
  };
  onSelectPlot: (plotId: string) => void;
  onCreatePlot: (request: NewPlotRequest) => void;
  onDeletePlot: (plotId: string) => void;
}

/** Frames `bounds` while keeping it clear of the toolbar (left) and the layer panel (right, md+). */
function fitTo(map: maplibregl.Map, bounds: [number, number, number, number] | null, maxZoom = 17) {
  if (!bounds) return;
  const { clientWidth: w, clientHeight: h } = map.getContainer();
  const padding = {
    top: Math.round(Math.min(130, h * 0.25)),
    // Clear of the Map | Satellite switch and the observation-year slider.
    bottom: Math.round(Math.min(140, h * 0.24)),
    // Never less than the labelled toolbar (82 px from the left edge) plus a margin.
    left: Math.round(Math.max(96, Math.min(110, w * 0.22))),
    right: Math.round(w >= 768 ? Math.min(300, w * 0.4) : Math.min(70, w * 0.16)),
  };
  map.fitBounds(
    [
      [bounds[0], bounds[1]],
      [bounds[2], bounds[3]],
    ],
    { padding, maxZoom, duration: 900 },
  );
}

export function MapView({
  plots,
  plotsLoading,
  selectedPlot,
  cube,
  country,
  locale,
  initialQuery,
  imagery,
  detection,
  importedTrees,
  analysis,
  analysisLoading = false,
  onSelectPlot,
  onCreatePlot,
  onDeletePlot,
}: MapViewProps) {
  const { t } = useTranslation();
  const container = useRef<HTMLDivElement>(null);
  const region = regionFor(country);
  const { map, ready, error, basemapFallback } = useMapLibre(container, {
    center: [region.default_center.lon, region.default_center.lat],
    zoom: region.default_zoom,
  });
  const layers = useUiStore((s) => s.layers);
  const areaUnit = useUiStore((s) => s.areaUnit);
  const observationYear = useUiStore((s) => s.observationYear);
  const setObservationYear = useUiStore((s) => s.setObservationYear);
  const mapView = useUiStore((s) => s.mapView);
  const setMapView = useUiStore((s) => s.setMapView);
  const mode = useUiStore((s) => s.landInputMode);
  const setMode = useUiStore((s) => s.setLandInputMode);
  const setImportOpen = useUiStore((s) => s.setImportOpen);
  const welcomeDismissed = useUiStore((s) => s.welcomeDismissed);
  const dismissWelcome = useUiStore((s) => s.dismissWelcome);
  const [notice, setNotice] = useState<string | null>(null);
  const [line, setLine] = useState<LineStringGeometry | null>(null);
  const [pin, setPin] = useState<LatLon | null>(null);
  const [preview, setPreview] = useState<PreviewGeometry | null>(null);
  const [imageryFailed, setImageryFailed] = useState(false);
  // md and up: the mode panel floats over the map; on phones it sits below the map.
  const wide = useMediaQuery('(min-width: 768px)');

  const live = useRef({ mode, layers, onSelectPlot, selectedPlot, locale, country, areaUnit, t });
  useEffect(() => {
    live.current = { mode, layers, onSelectPlot, selectedPlot, locale, country, areaUnit, t };
  });

  const reasonText = useCallback(
    (reason: string) =>
      t('map.polygonInvalid', { reason: t(`map.reason_${reason}`, { defaultValue: reason }) }),
    [t],
  );

  // -- drawing (Boundary, Tree line, Edit) -------------------------------------------
  const finishPolygon = useCallback(
    (geometry: PolygonGeometry, kind: 'boundary' | 'edit') => {
      setMode('none');
      const check = validatePolygon(geometry);
      if (!check.ok) {
        setNotice(reasonText(check.reason));
        return;
      }
      onCreatePlot(plotRequestFor(kind, geometry));
    },
    [onCreatePlot, reasonText, setMode],
  );
  const onPolygon = useCallback(
    (geometry: PolygonGeometry) => finishPolygon(geometry, 'boundary'),
    [finishPolygon],
  );
  const { startDrawing, startShape, startLine, startEditing, editedGeometry, cancel } =
    useDrawTools({ map, ready, onPolygon, onLine: setLine });

  useEffect(() => {
    if (!ready) return;
    cancel();
    setLine(null);
    setPin(null);
    setPreview(null);
    if (mode === 'boundary') startDrawing();
    else if (isShapeMode(mode)) startShape(mode);
    else if (mode === 'tree-line') startLine();
    else if (mode === 'edit') {
      const geometry = live.current.selectedPlot?.geometry;
      if (geometry) startEditing(geometry);
      else setMode('none');
    }
  }, [mode, ready, cancel, startDrawing, startShape, startLine, startEditing, setMode]);

  // Leaving the workspace ends any input mode.
  useEffect(() => () => setMode('none'), [setMode]);

  useEffect(() => {
    if (!map || !ready) return;
    map.getCanvas().style.cursor = mode === 'pin' ? 'crosshair' : '';
  }, [map, ready, mode]);

  const onToolbar = (action: LandToolAction) => {
    setNotice(null);
    if (action === 'import') {
      setMode('none');
      setImportOpen(true);
      return;
    }
    if (action === 'delete') {
      if (selectedPlot && window.confirm(t('map.deleteConfirm')))
        onDeletePlot(selectedPlot.plot_id);
      return;
    }
    setMode(mode === action ? 'none' : action);
  };
  const create = (request: NewPlotRequest) => {
    setMode('none');
    onCreatePlot(request);
  };

  // -- overlay layers ---------------------------------------------------------------
  useEffect(() => {
    if (!map || !ready) return;
    ensureOverlayLayers(map);
  }, [map, ready]);

  useEffect(() => {
    if (!map || !ready) return;
    setOverlayData(map, PLOT_SOURCE, plotsToGeoJson(plots, selectedPlot?.plot_id ?? null));
  }, [map, ready, plots, selectedPlot]);

  const years = useMemo(() => cubeYears(cube), [cube]);
  const year = activeYear(cube, observationYear);
  const timeIndex = timeIndexForYear(cube, year);
  const ndviCells = useMemo(
    () => (cube ? cubeSliceToGeoJson(cube, timeIndex) : null),
    [cube, timeIndex],
  );
  useEffect(() => {
    if (!map || !ready) return;
    const visible = layers.ndvi && Boolean(selectedPlot) && Boolean(ndviCells);
    setOverlayData(map, NDVI_SOURCE, visible ? ndviCells : null);
    setLayersVisible(map, [NDVI_FILL], visible);
  }, [map, ready, layers.ndvi, selectedPlot, ndviCells]);

  useEffect(() => {
    if (!map || !ready) return;
    const visible = layers.treeCover && Boolean(selectedPlot) && Boolean(detection.data);
    setOverlayData(
      map,
      DETECT_SOURCE,
      visible ? (detection.data?.features as unknown as FeatureCollection) : null,
    );
    setLayersVisible(map, [DETECT_FILL, DETECT_LINE], visible);
  }, [map, ready, layers.treeCover, selectedPlot, detection.data]);

  const importPreview = importedTrees.record?.preview ?? null;
  useEffect(() => {
    if (!map || !ready) return;
    const visible = layers.importedTrees && Boolean(importPreview);
    setOverlayData(
      map,
      IMPORT_SOURCE,
      visible ? (importPreview as unknown as FeatureCollection) : null,
    );
    setLayersVisible(map, [IMPORT_CROWNS, IMPORT_POINTS], visible);
  }, [map, ready, layers.importedTrees, importPreview]);

  // "View on map" from the Data page frames the import once it has loaded.
  const fittedImport = useRef<string | null>(null);
  useEffect(() => {
    const record = importedTrees.record;
    if (
      !map ||
      !ready ||
      !importedTrees.fitOnLoad ||
      !record?.preview ||
      fittedImport.current === record.import_id
    )
      return;
    fittedImport.current = record.import_id;
    fitTo(map, boundsOf(record.preview), 18);
  }, [map, ready, importedTrees.fitOnLoad, importedTrees.record]);

  useEffect(() => {
    if (!map || !ready) return;
    const features: Feature[] = [...geometryToCollection(preview).features];
    if (pin && preview?.type !== 'Point')
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [pin.lon, pin.lat] },
        properties: {},
      });
    if (line && preview?.type !== 'LineString')
      features.push({ type: 'Feature', geometry: line, properties: {} });
    setOverlayData(map, PREVIEW_SOURCE, { type: 'FeatureCollection', features });
  }, [map, ready, preview, pin, line]);

  // Typed coordinates can be anywhere: frame the preview whenever its extent changes.
  const previewBounds = useMemo(
    () => (mode === 'coordinates' && preview ? boundsOf(preview) : null),
    [mode, preview],
  );
  const previewKey = previewBounds ? previewBounds.join(',') : null;
  const framedPreview = useRef<string | null>(null);
  useEffect(() => {
    if (!map || !ready || !previewKey || framedPreview.current === previewKey) return;
    framedPreview.current = previewKey;
    fitTo(map, previewBounds);
  }, [map, ready, previewKey, previewBounds]);

  // -- satellite imagery --------------------------------------------------------------
  const satelliteOn = mapView === 'satellite' && Boolean(imagery.provider);
  useEffect(() => {
    if (!map || !ready) return;
    setImageryFailed(false);
    syncImageryLayer(map, imagery.provider, satelliteOn);
  }, [map, ready, imagery.provider, satelliteOn]);
  useEffect(() => {
    if (!map) return;
    let failures = 0;
    // MapLibre 6 types 'error' events as ErrorEvent; tile errors also carry `sourceId`.
    const onError = (event: unknown) => {
      if ((event as { sourceId?: string }).sourceId !== 'atlas-imagery') return;
      failures += 1;
      // A few failed tiles happen; many mean the service is down. The basemap stays underneath.
      if (failures >= 6) setImageryFailed(true);
    };
    map.on('error', onError);
    return () => {
      map.off('error', onError);
    };
  }, [map, imagery.provider]);

  // -- clicks: pin, tree-cover popup, plot selection -----------------------------------
  const popup = useRef<maplibregl.Popup | null>(null);
  useEffect(() => {
    if (!map || !ready) return;
    const onClick = (event: maplibregl.MapMouseEvent) => {
      const current = live.current;
      if (current.mode === 'pin') {
        setPin({ lat: event.lngLat.lat, lon: event.lngLat.lng });
        return;
      }
      if (current.mode !== 'none') return;
      if (current.layers.treeCover && map.getLayer(DETECT_FILL)) {
        const patch = map.queryRenderedFeatures(event.point, { layers: [DETECT_FILL] })[0];
        const info = patchInfo(patch?.properties);
        if (info) {
          popup.current?.remove();
          const area = formatArea(
            info.hectares,
            current.selectedPlot?.country ?? current.country,
            current.locale,
            current.areaUnit,
          ).primary;
          popup.current = new maplibregl.Popup({
            closeButton: true,
            maxWidth: '280px',
            className: 'atlas-popup',
          })
            .setLngLat(event.lngLat)
            .setText(current.t('map.treeCoverPopup', { confidence: info.confidence, area }))
            .addTo(map);
          return;
        }
      }
      const id = map.queryRenderedFeatures(event.point, { layers: [PLOT_FILL] })[0]?.properties
        ?.plot_id as string | undefined;
      if (id) current.onSelectPlot(id);
    };
    map.on('click', onClick);
    return () => {
      map.off('click', onClick);
      popup.current?.remove();
    };
  }, [map, ready]);

  // -- fly to the selected plot -----------------------------------------------------------
  const lastFlown = useRef<string | null>(null);
  useEffect(() => {
    if (!map || !ready || !selectedPlot?.geometry || lastFlown.current === selectedPlot.plot_id)
      return;
    lastFlown.current = selectedPlot.plot_id;
    popup.current?.remove();
    fitTo(map, boundsOf(selectedPlot.geometry));
  }, [map, ready, selectedPlot]);

  // -- handlers ---------------------------------------------------------------------
  const pickPlace = (r: GeocodeResult) => {
    map?.flyTo({ center: [r.lon, r.lat], zoom: 15, duration: 1200 });
  };
  const locate = () => {
    if (!navigator.geolocation) {
      setNotice(t('map.locateFailed'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => map?.flyTo({ center: [pos.coords.longitude, pos.coords.latitude], zoom: 15 }),
      () => setNotice(t('map.locateFailed')),
      { timeout: 8000 },
    );
  };
  const useCentre = () => {
    const c = map?.getCenter();
    if (c) setPin({ lat: c.lat, lon: c.lng });
  };
  const applyEdit = () => {
    const geometry = editedGeometry();
    cancel();
    if (geometry) finishPolygon(geometry, 'edit');
    else setMode('none');
  };

  const area = selectedPlot
    ? formatArea(selectedPlot.area_hectares, selectedPlot.country, locale, areaUnit)
    : null;
  const stats = cube?.stats_per_time[timeIndex];
  const showWelcome = !plotsLoading && plots.length === 0 && mode === 'none' && !welcomeDismissed;
  const inputActive = mode !== 'none';
  const satelliteNote = imagery.provider
    ? imagery.provider.name
    : imagery.loading
      ? t('app.loading')
      : t('map.satelliteUnavailable');

  let panel: ReactNode = null;
  if (mode === 'boundary' || mode === 'edit' || isShapeMode(mode))
    panel = <DrawHintPanel mode={mode} onApply={applyEdit} onCancel={() => setMode('none')} />;
  else if (mode === 'tree-line')
    panel = (
      <TreeLinePanel
        line={line}
        locale={locale}
        onCreate={create}
        onRedraw={() => {
          setLine(null);
          setPreview(null);
          startLine();
        }}
        onCancel={() => setMode('none')}
        onPreview={setPreview}
      />
    );
  else if (mode === 'pin')
    panel = (
      <PinSizePanel
        pin={pin}
        country={country}
        locale={locale}
        onUseCentre={useCentre}
        onCreate={create}
        onCancel={() => setMode('none')}
        onPreview={setPreview}
      />
    );
  else if (mode === 'coordinates')
    panel = (
      <CoordinatesPanel
        country={country}
        locale={locale}
        onCreate={create}
        onCancel={() => setMode('none')}
        onPreview={setPreview}
      />
    );

  return (
    <div>
      <div className="relative flex h-[600px] max-h-[72vh] min-h-[420px] flex-col overflow-hidden rounded-[14px] border border-line bg-[#E7EEE4]">
        <div className="relative min-h-0 flex-1">
          {/* `.maplibregl-map` forces position: relative, so the container is sized with h-full w-full (never inset-0). */}
          <div
            ref={container}
            className="h-full w-full"
            aria-label={t('map.mapLabel')}
            role="application"
          />
          {error === 'webgl' && (
            <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-ink-2">
              {t('map.webglUnsupported')}
            </div>
          )}

          {/* Left column: search, then the labelled land tools (scrolls if the map is short). */}
          <div className="pointer-events-none absolute bottom-[66px] left-3.5 top-3.5 z-10 flex flex-col gap-2.5">
            <div className="pointer-events-auto shrink-0">
              <MapSearch country={country} onPick={pickPlace} initialQuery={initialQuery} />
            </div>
            {!showWelcome && (
              <div className="pointer-events-auto min-h-0 self-start overflow-y-auto rounded-[10px]">
                <LandInputToolbar
                  mode={mode}
                  canEdit={Boolean(selectedPlot?.geometry)}
                  onAction={onToolbar}
                />
              </div>
            )}
          </div>

          {/* Bottom row: Map | Satellite, then the observation year (kept clear of the layer column). */}
          <div className="pointer-events-none absolute bottom-3.5 left-3.5 right-3.5 z-10 flex items-end gap-2.5 lg:right-[300px]">
            <div className="pointer-events-auto shrink-0">
              <MapViewSwitch
                value={satelliteOn ? 'satellite' : 'map'}
                onChange={setMapView}
                satelliteAvailable={Boolean(imagery.provider)}
                satelliteNote={satelliteNote}
              />
            </div>
            {years.length > 1 && !inputActive && layers.ndvi && selectedPlot && (
              <div className="pointer-events-auto hidden min-w-0 flex-1 lg:block">
                <YearSlider
                  years={years}
                  value={year}
                  onChange={setObservationYear}
                  caption={
                    stats?.mean != null ? `${year} · NDVI ${stats.mean.toFixed(2)}` : String(year)
                  }
                />
              </div>
            )}
          </div>

          <div className="pointer-events-none absolute bottom-3.5 right-3.5 top-3.5 z-10 flex flex-col items-end gap-2.5">
            <div className="pointer-events-auto flex shrink-0 items-start gap-2">
              <LiveClock locale={locale} />
              <ViewControls
                onZoomIn={() => map?.zoomIn()}
                onZoomOut={() => map?.zoomOut()}
                onLocate={locate}
              />
            </div>
            {!inputActive && (
              <div className="pointer-events-auto hidden min-h-0 md:flex">
                <LayerPanel
                  hasPlot={Boolean(selectedPlot)}
                  locale={locale}
                  treeCover={{
                    summary: detectionSummary(detection.data),
                    loading: detection.loading,
                    error: detection.error,
                  }}
                  importedTrees={{
                    count: importedTrees.record?.trees?.count ?? null,
                    filename: importedTrees.record?.filename ?? null,
                    loading: importedTrees.loading,
                    error: importedTrees.error,
                  }}
                  insights={{
                    landUse: landUseShares(analysis),
                    soil: soilInsight(analysis),
                    loading: analysisLoading,
                  }}
                  showLegend={!satelliteOn}
                />
              </div>
            )}
          </div>

          {selectedPlot && area && !inputActive && !notice && (
            <div
              data-testid="plot-chip"
              className="pointer-events-none absolute left-1/2 top-[68px] z-10 max-w-[calc(100%-188px)] -translate-x-1/2 truncate rounded-[10px] bg-panel-dark px-3 py-2 text-center text-[13px] font-semibold text-white shadow-float"
            >
              {selectedPlot.name}
              <span className="block font-mono text-[12px] font-normal text-mint-on-dark">
                {area.primary} · {area.secondary}
              </span>
            </div>
          )}

          {notice && (
            <div
              role="alert"
              className="absolute left-1/2 top-[68px] z-20 max-w-[calc(100%-188px)] -translate-x-1/2 rounded-[10px] border border-amber-tint bg-amber-tint px-4 py-2 text-[13px] text-amber-text shadow-float"
            >
              {notice}
              <button
                type="button"
                className="ml-3 font-semibold underline"
                onClick={() => setNotice(null)}
              >
                {t('app.close')}
              </button>
            </div>
          )}

          {panel && wide && (
            <div className="absolute left-[156px] top-[68px] z-20 max-h-[calc(100%-130px)] w-[316px] overflow-y-auto rounded-[10px]">
              {panel}
            </div>
          )}

          {showWelcome && (
            <LandInputWelcome
              onChoose={(option) => {
                dismissWelcome();
                if (option === 'import') setImportOpen(true);
                else setMode(option);
              }}
              onDismiss={dismissWelcome}
            />
          )}
        </div>
        <AttributionBar
          map={map}
          ready={ready}
          imageryAttribution={satelliteOn ? imagery.provider?.attribution : null}
          basemapFallback={basemapFallback}
          imageryFailed={satelliteOn && imageryFailed}
          centroid={selectedPlot?.centroid ?? null}
        />
      </div>
      {panel && !wide && <div className="mt-3">{panel}</div>}
    </div>
  );
}
