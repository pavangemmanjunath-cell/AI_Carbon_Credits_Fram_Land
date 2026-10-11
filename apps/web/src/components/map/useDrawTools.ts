import { useCallback, useEffect, useRef } from 'react';
import type { Map as MapLibreMap } from 'maplibre-gl';
import { simplify } from '@turf/turf';
import {
  TerraDraw,
  TerraDrawCircleMode,
  TerraDrawFreehandMode,
  TerraDrawLineStringMode,
  TerraDrawPolygonMode,
  TerraDrawRectangleMode,
  TerraDrawSelectMode,
} from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';
import type { ShapeOption } from '@/lib/landInput';
import type { LineStringGeometry, PolygonGeometry } from '@/types/api';

/** terra-draw mode name for each Paint-style tool. */
const SHAPE_MODE: Record<ShapeOption, string> = {
  pen: 'freehand',
  rectangle: 'rectangle',
  circle: 'circle',
};
const POLYGON_MODES = new Set(['polygon', 'freehand', 'rectangle', 'circle']);
/** The API accepts at most 500 vertices (ATLAS_MAX_PLOT_VERTICES); a pen stroke can produce more. */
const MAX_VERTICES = 500;

const SHAPE_STYLE = {
  fillColor: '#2FA85B',
  fillOpacity: 0.18,
  outlineColor: '#1E6B41',
  outlineWidth: 3,
} as const;

/** A freehand stroke is simplified (about 0.5 m tolerance) until it fits the API's vertex limit. */
function withinVertexLimit(geometry: PolygonGeometry): PolygonGeometry {
  let out = geometry;
  for (const tolerance of [0.000005, 0.00001, 0.00002, 0.00005, 0.0001]) {
    if ((out.coordinates[0]?.length ?? 0) <= MAX_VERTICES) break;
    out = simplify({ type: 'Feature', geometry, properties: {} }, { tolerance, highQuality: true })
      .geometry as PolygonGeometry;
  }
  return out;
}

interface Options {
  map: MapLibreMap | null;
  ready: boolean;
  onPolygon: (geometry: PolygonGeometry) => void;
  onLine: (geometry: LineStringGeometry) => void;
}

/** terra-draw on top of MapLibre: Boundary, Pen, Rectangle and Circle (all polygons), Tree line, and vertex editing (Edit). */
export function useDrawTools({ map, ready, onPolygon, onLine }: Options) {
  const drawRef = useRef<TerraDraw | null>(null);
  const handlers = useRef({ onPolygon, onLine });
  useEffect(() => {
    handlers.current = { onPolygon, onLine };
  });

  useEffect(() => {
    if (!map || !ready || drawRef.current) return;
    const draw = new TerraDraw({
      adapter: new TerraDrawMapLibreGLAdapter({ map, coordinatePrecision: 6 }),
      modes: [
        new TerraDrawPolygonMode({
          styles: {
            fillColor: '#2FA85B',
            fillOpacity: 0.18,
            outlineColor: '#1E6B41',
            outlineWidth: 3,
            closingPointColor: '#FFFFFF',
            closingPointOutlineColor: '#1E6B41',
            closingPointWidth: 6,
            closingPointOutlineWidth: 2,
          },
        }),
        // Paint-like: press and drag (or click, move, click) for Pen, Rectangle and Circle.
        new TerraDrawFreehandMode({
          drawInteraction: 'click-move-or-drag',
          styles: {
            ...SHAPE_STYLE,
            closingPointColor: '#FFFFFF',
            closingPointOutlineColor: '#1E6B41',
            closingPointWidth: 6,
            closingPointOutlineWidth: 2,
          },
        }),
        new TerraDrawRectangleMode({ drawInteraction: 'click-move-or-drag', styles: SHAPE_STYLE }),
        new TerraDrawCircleMode({ drawInteraction: 'click-move-or-drag', styles: SHAPE_STYLE }),
        new TerraDrawLineStringMode({
          styles: {
            lineStringColor: '#1E6B41',
            lineStringWidth: 4,
            closingPointColor: '#FFFFFF',
            closingPointOutlineColor: '#1E6B41',
            closingPointWidth: 6,
            closingPointOutlineWidth: 2,
          },
        }),
        new TerraDrawSelectMode({
          flags: {
            polygon: {
              feature: {
                draggable: false,
                coordinates: { midpoints: true, draggable: true, deletable: true },
              },
            },
          },
          styles: {
            selectedPolygonColor: '#2FA85B',
            selectedPolygonFillOpacity: 0.2,
            selectedPolygonOutlineColor: '#1E6B41',
            selectedPolygonOutlineWidth: 3,
            selectionPointColor: '#FFFFFF',
            selectionPointOutlineColor: '#1E6B41',
            selectionPointWidth: 6,
            selectionPointOutlineWidth: 2,
            midPointColor: '#BFE3CC',
            midPointOutlineColor: '#1E6B41',
            midPointWidth: 4,
            midPointOutlineWidth: 1.5,
          },
        }),
      ],
    });
    draw.start();
    draw.setMode('static');
    draw.on('finish', (id, context) => {
      if (context.action !== 'draw') return;
      const feature = draw.getSnapshotFeature(id);
      if (!feature) return;
      if (POLYGON_MODES.has(context.mode) && feature.geometry.type === 'Polygon') {
        handlers.current.onPolygon(withinVertexLimit(feature.geometry as PolygonGeometry));
      } else if (context.mode === 'linestring' && feature.geometry.type === 'LineString') {
        handlers.current.onLine(feature.geometry as LineStringGeometry);
      } else {
        return;
      }
      draw.clear();
      draw.setMode('static');
    });
    drawRef.current = draw;
    return () => {
      try {
        draw.stop();
      } catch {
        /* already stopped */
      }
      drawRef.current = null;
    };
  }, [map, ready]);

  const startDrawing = useCallback(() => {
    const draw = drawRef.current;
    if (!draw) return;
    draw.clear();
    draw.setMode('polygon');
  }, []);

  const startShape = useCallback((shape: ShapeOption) => {
    const draw = drawRef.current;
    if (!draw) return;
    draw.clear();
    draw.setMode(SHAPE_MODE[shape]);
  }, []);

  const startLine = useCallback(() => {
    const draw = drawRef.current;
    if (!draw) return;
    draw.clear();
    draw.setMode('linestring');
  }, []);

  const startEditing = useCallback((geometry: PolygonGeometry) => {
    const draw = drawRef.current;
    if (!draw) return;
    draw.clear();
    draw.addFeatures([
      {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: geometry.coordinates },
        properties: { mode: 'polygon' },
      },
    ]);
    draw.setMode('select');
    const first = draw.getSnapshot()[0];
    if (first?.id !== undefined) draw.selectFeature(first.id);
  }, []);

  const editedGeometry = useCallback((): PolygonGeometry | null => {
    const draw = drawRef.current;
    if (!draw) return null;
    const feature = draw.getSnapshot().find((f) => f.geometry.type === 'Polygon');
    return feature ? (feature.geometry as PolygonGeometry) : null;
  }, []);

  const cancel = useCallback(() => {
    const draw = drawRef.current;
    if (!draw) return;
    draw.clear();
    draw.setMode('static');
  }, []);

  return { startDrawing, startShape, startLine, startEditing, editedGeometry, cancel };
}
