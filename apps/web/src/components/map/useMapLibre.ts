import { useEffect, useRef, useState, type RefObject } from 'react';
import maplibregl, { type Map as MapLibreMap, type StyleSpecification } from 'maplibre-gl';
import { Protocol } from 'pmtiles';
import { mapEnv } from '@/config/mapEnv';
import { pmtilesStyle } from './mapStyle';

let protocolRegistered = false;

/** Plain ground used when the configured basemap cannot be fetched (offline, blocked network). */
export const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    { id: 'atlas-fallback-ground', type: 'background', paint: { 'background-color': '#E7EEE4' } },
  ],
};
const BASEMAP_TIMEOUT_MS = 7000;

function ensurePmtilesProtocol() {
  if (protocolRegistered) return;
  const protocol = new Protocol();
  maplibregl.addProtocol('pmtiles', protocol.tile);
  protocolRegistered = true;
}

export function webglSupported(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

interface Options {
  center: [number, number];
  zoom: number;
}

/** Creates a MapLibre map once per container; style comes from the environment. */
export function useMapLibre(containerRef: RefObject<HTMLDivElement | null>, options: Options) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [basemapFallback, setBasemapFallback] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    if (!webglSupported()) {
      setError('webgl');
      return;
    }
    ensurePmtilesProtocol();
    const style = mapEnv.basemapPmtilesUrl
      ? pmtilesStyle(mapEnv.basemapPmtilesUrl)
      : mapEnv.basemapStyleUrl;
    const instance = new maplibregl.Map({
      container: containerRef.current,
      style,
      center: options.center,
      zoom: options.zoom,
      // Attribution and the scale bar are drawn by our own bottom bar (AttributionBar).
      attributionControl: false,
      // A flat, north-up map: no tilt, no rotation.
      maxPitch: 0,
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
      canvasContextAttributes: { antialias: true, preserveDrawingBuffer: true },
    });
    instance.touchZoomRotate.disableRotation();
    instance.keyboard.disableRotation();
    let loaded = false;
    let fellBack = false;
    const useFallback = () => {
      if (loaded || fellBack) return;
      fellBack = true;
      setBasemapFallback(true);
      instance.setStyle(FALLBACK_STYLE);
    };
    const timer = window.setTimeout(useFallback, BASEMAP_TIMEOUT_MS);
    instance.on('load', () => {
      loaded = true;
      setReady(true);
    });
    // Once the style itself has arrived the basemap works; a full street map can take
    // longer than the timeout to draw (slow network, phone, software GL), so only a
    // style that never arrives falls back to the plain ground.
    instance.once('styledata', () => window.clearTimeout(timer));
    instance.on('error', (event) => {
      // A failed style fetch means no tiles at all: fall back to a plain ground so
      // the plot, drawing tools and data layers still work. Tile errors are ignored.
      const message = event.error?.message ?? '';
      if (
        !loaded &&
        (/style/i.test(message) || /Failed to fetch|NetworkError|AJAXError/i.test(message))
      )
        useFallback();
    });
    mapRef.current = instance;
    setMap(instance);
    // Debug hook (dev server or `?debug=map`): lets the browser console / Playwright inspect the map.
    if (import.meta.env.DEV || new URLSearchParams(window.location.search).get('debug') === 'map') {
      (window as unknown as { __atlasMap?: MapLibreMap }).__atlasMap = instance;
    }
    return () => {
      window.clearTimeout(timer);
      instance.remove();
      mapRef.current = null;
      setMap(null);
      setReady(false);
    };
    // The map is created once; later center/zoom changes use flyTo.
  }, [containerRef]);

  return { map, ready, error, basemapFallback };
}
