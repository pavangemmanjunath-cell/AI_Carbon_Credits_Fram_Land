import * as turf from '@turf/turf';
import type { Feature, FeatureCollection, Geometry, Polygon, Position } from 'geojson';
import type { LatLon, PolygonGeometry } from '@/types/api';

const EARTH_RADIUS_M = 6_371_008.8;

export interface LocalProjection {
  origin: LatLon;
  toLocal: (lon: number, lat: number) => [number, number];
  toLonLat: (x: number, y: number) => [number, number];
}

/**
 * Equirectangular projection centred on the polygon — accurate to well under
 * a metre for farm-scale plots; used by the offline geometry helpers.
 * x grows east, y grows north, both in metres.
 */
export function localProjection(origin: LatLon): LocalProjection {
  const lat0 = (origin.lat * Math.PI) / 180;
  const cos = Math.cos(lat0);
  const toLocal = (lon: number, lat: number): [number, number] => [
    ((lon - origin.lon) * Math.PI * EARTH_RADIUS_M * cos) / 180,
    ((lat - origin.lat) * Math.PI * EARTH_RADIUS_M) / 180,
  ];
  const toLonLat = (x: number, y: number): [number, number] => [
    origin.lon + (x * 180) / (Math.PI * EARTH_RADIUS_M * cos),
    origin.lat + (y * 180) / (Math.PI * EARTH_RADIUS_M),
  ];
  return { origin, toLocal, toLonLat };
}

export function polygonFeature(geometry: PolygonGeometry): Feature<Polygon> {
  return turf.polygon(geometry.coordinates as Position[][]);
}

export function areaHectares(geometry: PolygonGeometry): number {
  return turf.area(polygonFeature(geometry)) / 10_000;
}

export function perimeterMetres(geometry: PolygonGeometry): number {
  return turf.length(turf.polygonToLine(polygonFeature(geometry)) as Feature<Geometry>, { units: 'kilometers' }) * 1000;
}

export function centroidOf(geometry: PolygonGeometry): LatLon {
  const c = turf.centroid(polygonFeature(geometry)).geometry.coordinates;
  return { lat: c[1], lon: c[0] };
}

export function bboxOf(geometry: PolygonGeometry): [number, number, number, number] {
  const b = turf.bbox(polygonFeature(geometry));
  return [b[0], b[1], b[2], b[3]];
}

/** Generalised centroid for public views (0.05° grid, per contract). */
export function publicCentroid(c: LatLon): LatLon {
  const round = (v: number) => Math.round(v / 0.05) * 0.05;
  return { lat: Number(round(c.lat).toFixed(2)), lon: Number(round(c.lon).toFixed(2)) };
}

export function pointInPolygon(lon: number, lat: number, geometry: PolygonGeometry): boolean {
  return turf.booleanPointInPolygon(turf.point([lon, lat]), polygonFeature(geometry));
}

/** Accepts a Feature, FeatureCollection or bare geometry and returns the first polygon ring set. */
export function extractPolygon(input: unknown): PolygonGeometry | null {
  if (!input || typeof input !== 'object') return null;
  const obj = input as { type?: string; coordinates?: unknown; geometry?: unknown; features?: unknown[] };
  if (obj.type === 'Polygon' && Array.isArray(obj.coordinates)) {
    return { type: 'Polygon', coordinates: obj.coordinates as number[][][] };
  }
  if (obj.type === 'MultiPolygon' && Array.isArray(obj.coordinates)) {
    const first = (obj.coordinates as number[][][][])[0];
    return first ? { type: 'Polygon', coordinates: first } : null;
  }
  if (obj.type === 'Feature') return extractPolygon(obj.geometry);
  if (obj.type === 'FeatureCollection' && Array.isArray(obj.features)) {
    for (const f of obj.features) {
      const poly = extractPolygon(f);
      if (poly) return poly;
    }
  }
  return null;
}

/** Contract validation, mirrored client-side so users get instant feedback. */
export function validatePolygon(geometry: PolygonGeometry): { ok: true } | { ok: false; reason: string } {
  const ring = geometry.coordinates[0];
  if (!ring || ring.length < 4) return { ok: false, reason: 'too_few_vertices' };
  if (ring.length > 501) return { ok: false, reason: 'too_many_vertices' };
  for (const [lon, lat] of ring) {
    if (lon < -180 || lon > 180 || lat < -90 || lat > 90) return { ok: false, reason: 'out_of_bounds' };
  }
  const ha = areaHectares(geometry);
  if (ha < 0.01) return { ok: false, reason: 'too_small' };
  if (ha > 10_000) return { ok: false, reason: 'too_large' };
  if (turf.kinks(polygonFeature(geometry)).features.length > 0) return { ok: false, reason: 'self_intersecting' };
  return { ok: true };
}

export function plotToFeatureCollection(
  plots: { plot_id: string; name: string; geometry?: PolygonGeometry; area_hectares: number }[],
): FeatureCollection<Polygon> {
  return {
    type: 'FeatureCollection',
    features: plots
      .filter((p) => p.geometry)
      .map((p) => ({
        type: 'Feature',
        id: p.plot_id,
        properties: { plot_id: p.plot_id, name: p.name, area_hectares: p.area_hectares },
        geometry: p.geometry as Polygon,
      })),
  };
}

/** [west, south, east, north] of any GeoJSON object, or null when it has no coordinates. */
export function boundsOf(geojson: unknown): [number, number, number, number] | null {
  try {
    const b = turf.bbox(geojson as Parameters<typeof turf.bbox>[0]);
    return b.every((v) => Number.isFinite(v)) ? [b[0], b[1], b[2], b[3]] : null;
  } catch {
    return null;
  }
}
