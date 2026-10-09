/**
 * MapLibre sources and layers drawn by the workspace map. Everything is a
 * plain 2D GeoJSON or raster layer; the order (bottom → top) is fixed so the
 * satellite imagery stays below the data, the data below the plots, and the
 * terra-draw drawing layers (`td-*`) stay on top.
 */
import type { ExpressionSpecification, FilterSpecification, GeoJSONSource, LayerSpecification, Map as MapLibreMap } from 'maplibre-gl';
import type { Feature, FeatureCollection, Geometry, Polygon } from 'geojson';
import { CONFIDENCE_OPACITY_EXPRESSION } from '@/lib/detection';
import type { ImageryProvider, Plot } from '@/types/api';

export const IMAGERY_SOURCE = 'atlas-imagery';
export const IMAGERY_LAYER = 'atlas-imagery-layer';
export const NDVI_SOURCE = 'atlas-ndvi';
export const NDVI_FILL = 'atlas-ndvi-fill';
export const DETECT_SOURCE = 'atlas-detect';
export const DETECT_FILL = 'atlas-detect-fill';
export const DETECT_LINE = 'atlas-detect-line';
export const PLOT_SOURCE = 'atlas-plots';
export const PLOT_FILL = 'atlas-plot-fill';
export const PLOT_LINE = 'atlas-plot-line';
export const PLOT_LINE_APPROX = 'atlas-plot-line-approx';
export const IMPORT_SOURCE = 'atlas-import';
export const IMPORT_CROWNS = 'atlas-import-crowns';
export const IMPORT_POINTS = 'atlas-import-points';
export const PREVIEW_SOURCE = 'atlas-preview';
export const PREVIEW_FILL = 'atlas-preview-fill';
export const PREVIEW_LINE = 'atlas-preview-line';
export const PREVIEW_POINT = 'atlas-preview-point';

export type OverlaySource = typeof NDVI_SOURCE | typeof DETECT_SOURCE | typeof PLOT_SOURCE | typeof IMPORT_SOURCE | typeof PREVIEW_SOURCE;

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };
const IS_POLYGON: FilterSpecification = ['==', ['geometry-type'], 'Polygon'];
const IS_POINT: FilterSpecification = ['==', ['geometry-type'], 'Point'];

/** Overlay layers, bottom → top. */
const OVERLAYS: LayerSpecification[] = [
  {
    id: NDVI_FILL,
    type: 'fill',
    source: NDVI_SOURCE,
    paint: { 'fill-color': ['get', 'color'], 'fill-opacity': ['case', ['==', ['get', 'value'], null], 0.25, 0.72] },
  },
  {
    id: DETECT_FILL,
    type: 'fill',
    source: DETECT_SOURCE,
    paint: { 'fill-color': '#1E6B41', 'fill-opacity': CONFIDENCE_OPACITY_EXPRESSION as unknown as ExpressionSpecification },
  },
  { id: DETECT_LINE, type: 'line', source: DETECT_SOURCE, paint: { 'line-color': '#0F3D24', 'line-width': 1.6 } },
  {
    id: PLOT_FILL,
    type: 'fill',
    source: PLOT_SOURCE,
    paint: { 'fill-color': '#2FA85B', 'fill-opacity': ['case', ['boolean', ['get', 'selected'], false], 0.16, 0.08] },
  },
  {
    id: PLOT_LINE,
    type: 'line',
    source: PLOT_SOURCE,
    filter: ['!=', ['get', 'approximate'], true],
    paint: {
      'line-color': ['case', ['boolean', ['get', 'selected'], false], '#1E6B41', '#5E6E65'],
      'line-width': ['case', ['boolean', ['get', 'selected'], false], 3.5, 2],
    },
  },
  {
    id: PLOT_LINE_APPROX,
    type: 'line',
    source: PLOT_SOURCE,
    filter: ['==', ['get', 'approximate'], true],
    paint: {
      'line-color': ['case', ['boolean', ['get', 'selected'], false], '#1E6B41', '#5E6E65'],
      'line-width': ['case', ['boolean', ['get', 'selected'], false], 3, 2],
      'line-dasharray': [2, 1.5],
    },
  },
  { id: IMPORT_CROWNS, type: 'line', source: IMPORT_SOURCE, filter: IS_POLYGON, paint: { 'line-color': '#B7791F', 'line-width': 1.4 } },
  {
    id: IMPORT_POINTS,
    type: 'circle',
    source: IMPORT_SOURCE,
    filter: IS_POINT,
    paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 1.5, 18, 5], 'circle-color': '#B7791F', 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 0.8 },
  },
  { id: PREVIEW_FILL, type: 'fill', source: PREVIEW_SOURCE, filter: IS_POLYGON, paint: { 'fill-color': '#2A6FB0', 'fill-opacity': 0.14 } },
  {
    id: PREVIEW_LINE,
    type: 'line',
    source: PREVIEW_SOURCE,
    filter: ['!=', ['geometry-type'], 'Point'],
    paint: { 'line-color': '#1F4E8A', 'line-width': 2.5, 'line-dasharray': [2, 1.2] },
  },
  {
    id: PREVIEW_POINT,
    type: 'circle',
    source: PREVIEW_SOURCE,
    filter: IS_POINT,
    paint: { 'circle-radius': 8, 'circle-color': '#1F4E8A', 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 3 },
  },
];

const OVERLAY_SOURCES: OverlaySource[] = [NDVI_SOURCE, DETECT_SOURCE, PLOT_SOURCE, IMPORT_SOURCE, PREVIEW_SOURCE];

function firstDrawLayerId(map: MapLibreMap): string | undefined {
  return map.getStyle()?.layers?.find((l) => l.id.startsWith('td-'))?.id;
}

/** Adds every overlay source and layer once (empty), in order and below the drawing layers. */
export function ensureOverlayLayers(map: MapLibreMap): void {
  for (const id of OVERLAY_SOURCES) {
    if (!map.getSource(id)) map.addSource(id, { type: 'geojson', data: EMPTY });
  }
  const before = firstDrawLayerId(map);
  for (const layer of OVERLAYS) {
    if (!map.getLayer(layer.id)) map.addLayer(layer, before);
  }
}

export function setOverlayData(map: MapLibreMap, sourceId: OverlaySource, data: FeatureCollection | null | undefined): void {
  const source = map.getSource(sourceId) as GeoJSONSource | undefined;
  source?.setData(data ?? EMPTY);
}

export function setLayersVisible(map: MapLibreMap, layerIds: string[], visible: boolean): void {
  for (const id of layerIds) {
    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
  }
}

export function plotsToGeoJson(plots: Plot[], selectedId: string | null): FeatureCollection<Polygon> {
  const features: Feature<Polygon>[] = [];
  for (const plot of plots) {
    if (!plot.geometry) continue;
    features.push({
      type: 'Feature',
      geometry: plot.geometry as Polygon,
      properties: {
        plot_id: plot.plot_id,
        name: plot.name,
        selected: plot.plot_id === selectedId,
        approximate: plot.boundary_quality === 'approximate',
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

export function geometryToCollection(geometry: Geometry | null | undefined): FeatureCollection {
  if (!geometry) return EMPTY;
  return { type: 'FeatureCollection', features: [{ type: 'Feature', geometry, properties: {} }] };
}

/**
 * Shows the provider's XYZ tiles below every overlay. `maxzoom` is the
 * provider's max zoom so MapLibre over-zooms instead of requesting missing
 * tiles. Passing `null` (or `visible: false`) hides the imagery.
 */
const imageryUrlByMap = new WeakMap<MapLibreMap, string>();

export function syncImageryLayer(map: MapLibreMap, provider: ImageryProvider | null, visible: boolean): void {
  if (map.getSource(IMAGERY_SOURCE) && (!provider || imageryUrlByMap.get(map) !== provider.url)) {
    if (map.getLayer(IMAGERY_LAYER)) map.removeLayer(IMAGERY_LAYER);
    map.removeSource(IMAGERY_SOURCE);
    imageryUrlByMap.delete(map);
  }
  if (!provider || !visible) {
    if (map.getLayer(IMAGERY_LAYER)) map.setLayoutProperty(IMAGERY_LAYER, 'visibility', 'none');
    return;
  }
  if (!map.getSource(IMAGERY_SOURCE)) {
    imageryUrlByMap.set(map, provider.url);
    map.addSource(IMAGERY_SOURCE, {
      type: 'raster',
      tiles: [provider.url],
      tileSize: provider.tile_size || 256,
      maxzoom: provider.max_zoom || 19,
      attribution: provider.attribution,
    });
  }
  if (!map.getLayer(IMAGERY_LAYER)) {
    const before = map.getLayer(NDVI_FILL) ? NDVI_FILL : firstDrawLayerId(map);
    map.addLayer({ id: IMAGERY_LAYER, type: 'raster', source: IMAGERY_SOURCE, paint: { 'raster-fade-duration': 150 } }, before);
  }
  map.setLayoutProperty(IMAGERY_LAYER, 'visibility', 'visible');
}
