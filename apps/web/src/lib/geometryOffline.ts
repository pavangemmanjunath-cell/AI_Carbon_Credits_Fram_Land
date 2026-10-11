/**
 * Offline stand-ins for the geometry helper endpoints (api-contract §v0.2).
 * They run only when the API cannot be reached, label every result as
 * computed in the browser, and follow the same validation limits; the server
 * remains the source of truth and rechecks every plot that is saved.
 */
import * as turf from '@turf/turf';
import type { Feature, LineString, Position } from 'geojson';
import type {
  AreaInputUnit,
  FromLineBody,
  FromLineResult,
  FromPointBody,
  FromPointResult,
  LatLon,
  ParseCoordinatesBody,
  ParseCoordinatesResult,
  PolygonGeometry,
} from '@/types/api';
import { ACRES_PER_HECTARE, HECTARES_PER_ACRE } from './format';
import { areaHectares, localProjection, validatePolygon } from './geo';
import { parseCoordinateText, ringFromPoints } from './coordinates';

export const OFFLINE_GEOMETRY_NOTE =
  'Calculated offline in your browser; the server rechecks the plot when it is saved.';
export const MAX_PLOT_AREA_HA = 10_000;
export const LINE_LIMITS = {
  minWidth: 1,
  maxWidth: 50,
  minSpacing: 0.5,
  maxSpacing: 50,
  minVertices: 2,
  maxVertices: 500,
  maxLengthM: 50_000,
};

const SQUARE_METRES: Record<AreaInputUnit, number> = {
  ha: 10_000,
  ac: HECTARES_PER_ACRE * 10_000,
  m2: 1,
};

export class GeometryInputError extends Error {
  readonly reason: string;
  constructor(reason: string, message: string) {
    super(message);
    this.name = 'GeometryInputError';
    this.reason = reason;
  }
}

function offlineProvenance() {
  return {
    mode: 'demo' as const,
    generated_at: new Date().toISOString(),
    notes: [OFFLINE_GEOMETRY_NOTE],
  };
}

const round = (value: number, digits: number) => Number(value.toFixed(digits));

/** Square (default) or circle of the requested area centred on the pin, in a local metric projection. */
export function offlineFromPoint(body: FromPointBody): FromPointResult {
  const squareMetres = body.area.value * SQUARE_METRES[body.area.unit];
  if (!Number.isFinite(squareMetres) || squareMetres <= 0)
    throw new GeometryInputError('area_not_positive', 'Area must be greater than 0.');
  if (squareMetres / 10_000 > MAX_PLOT_AREA_HA)
    throw new GeometryInputError('area_too_large', `Area must be at most ${MAX_PLOT_AREA_HA} ha.`);
  const projection = localProjection({ lat: body.lat, lon: body.lon });
  let ring: Position[];
  let method: string;
  if (body.shape === 'circle') {
    const segments = 64;
    // Enlarge the radius so the 64-gon (not the ideal circle) has the requested area.
    const radius = Math.sqrt((2 * squareMetres) / (segments * Math.sin((2 * Math.PI) / segments)));
    ring = Array.from({ length: segments }, (_, i) => {
      const angle = (2 * Math.PI * i) / segments;
      return projection.toLonLat(radius * Math.cos(angle), radius * Math.sin(angle));
    });
    method = `offline: circle centred on the pin (radius ${radius.toFixed(1)} m)`;
  } else {
    const half = Math.sqrt(squareMetres) / 2;
    ring = [
      projection.toLonLat(-half, -half),
      projection.toLonLat(half, -half),
      projection.toLonLat(half, half),
      projection.toLonLat(-half, half),
    ];
    method = `offline: square centred on the pin (side ${(half * 2).toFixed(1)} m)`;
  }
  ring.push([...ring[0]]);
  const geometry: PolygonGeometry = {
    type: 'Polygon',
    coordinates: [ring.map(([lon, lat]) => [round(lon, 7), round(lat, 7)])],
  };
  const ha = areaHectares(geometry);
  return {
    geometry,
    area_hectares: round(ha, 4),
    area_acres: round(ha * ACRES_PER_HECTARE, 4),
    boundary_quality: 'approximate',
    method,
    provenance: offlineProvenance(),
  };
}

export function lineLengthMetres(coordinates: number[][]): number {
  if (coordinates.length < 2) return 0;
  return (
    turf.length(turf.lineString(coordinates as Position[]) as Feature<LineString>, {
      units: 'kilometers',
    }) * 1000
  );
}

/** Contract formula: trees = floor(length / spacing) + 1. */
export function suggestedTreeCount(lengthMetres: number, spacingMetres: number): number {
  if (!(lengthMetres > 0) || !(spacingMetres > 0)) return 0;
  return Math.floor(lengthMetres / spacingMetres + 1e-9) + 1;
}

/**
 * Offsets the line by ±width/2 with mitred joins (limited to 3× the half width)
 * and closes the strip. Good for bunds and roadside rows; very sharp zig-zags
 * can self-intersect, which the plot validation then reports.
 */
export function stripAroundLine(coordinates: number[][], widthMetres: number): PolygonGeometry {
  const origin: LatLon = { lon: coordinates[0][0], lat: coordinates[0][1] };
  const projection = localProjection(origin);
  const pts = coordinates.map(([lon, lat]) => projection.toLocal(lon, lat));
  const half = widthMetres / 2;
  const normals: [number, number][] = [];
  for (let i = 0; i < pts.length - 1; i += 1) {
    const dx = pts[i + 1][0] - pts[i][0];
    const dy = pts[i + 1][1] - pts[i][1];
    const len = Math.hypot(dx, dy) || 1;
    normals.push([-dy / len, dx / len]);
  }
  const offsets = pts.map((_, i) => {
    const before = normals[Math.max(0, i - 1)];
    const after = normals[Math.min(normals.length - 1, i)];
    const mx = before[0] + after[0];
    const my = before[1] + after[1];
    const mlen = Math.hypot(mx, my);
    if (mlen < 1e-9) return [after[0] * half, after[1] * half];
    const ux = mx / mlen;
    const uy = my / mlen;
    const cos = ux * after[0] + uy * after[1];
    const scale = Math.min(half / Math.max(cos, 1e-6), half * 3);
    return [ux * scale, uy * scale];
  });
  const left = pts.map((p, i) => projection.toLonLat(p[0] + offsets[i][0], p[1] + offsets[i][1]));
  const right = pts
    .map((p, i) => projection.toLonLat(p[0] - offsets[i][0], p[1] - offsets[i][1]))
    .reverse();
  const ring = [...left, ...right];
  ring.push([...ring[0]]);
  return {
    type: 'Polygon',
    coordinates: [ring.map(([lon, lat]) => [round(lon, 7), round(lat, 7)])],
  };
}

export function offlineFromLine(body: FromLineBody): FromLineResult {
  const coords = body.line.coordinates;
  if (coords.length < LINE_LIMITS.minVertices || coords.length > LINE_LIMITS.maxVertices) {
    throw new GeometryInputError(
      'vertex_count',
      `A tree line needs ${LINE_LIMITS.minVertices}–${LINE_LIMITS.maxVertices} points.`,
    );
  }
  if (!(body.width_m >= LINE_LIMITS.minWidth && body.width_m <= LINE_LIMITS.maxWidth)) {
    throw new GeometryInputError(
      'width',
      `Strip width must be ${LINE_LIMITS.minWidth}–${LINE_LIMITS.maxWidth} m.`,
    );
  }
  if (!(body.spacing_m >= LINE_LIMITS.minSpacing && body.spacing_m <= LINE_LIMITS.maxSpacing)) {
    throw new GeometryInputError(
      'spacing',
      `Spacing must be ${LINE_LIMITS.minSpacing}–${LINE_LIMITS.maxSpacing} m.`,
    );
  }
  const length = lineLengthMetres(coords);
  if (length <= 0) throw new GeometryInputError('length', 'The line has no length.');
  if (length > LINE_LIMITS.maxLengthM)
    throw new GeometryInputError('length', 'A tree line can be at most 50 km long.');
  const geometry = stripAroundLine(coords, body.width_m);
  return {
    geometry,
    length_m: round(length, 1),
    area_hectares: round(areaHectares(geometry), 4),
    suggested_tree_count: suggestedTreeCount(length, body.spacing_m),
    boundary_quality: 'approximate',
    method:
      'offline: line offset by width/2 in a local metric projection; trees = floor(length / spacing) + 1',
    provenance: offlineProvenance(),
  };
}

export function offlineParseCoordinates(body: ParseCoordinatesBody): ParseCoordinatesResult {
  const parsed = parseCoordinateText(body.text);
  if (parsed.kind === 'point') {
    const p = parsed.points[0];
    return {
      points: parsed.points,
      kind: 'point',
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
      area_hectares: null,
      warnings: parsed.warnings,
    };
  }
  if (parsed.kind === 'polygon') {
    const geometry: PolygonGeometry = {
      type: 'Polygon',
      coordinates: [ringFromPoints(parsed.points)],
    };
    const check = validatePolygon(geometry);
    if (!check.ok) {
      return {
        points: parsed.points,
        kind: 'invalid',
        geometry: null,
        area_hectares: null,
        warnings: [
          ...parsed.warnings,
          `The corners do not form a valid plot (${check.reason.replace(/_/g, ' ')}).`,
        ],
      };
    }
    return {
      points: parsed.points,
      kind: 'polygon',
      geometry,
      area_hectares: round(areaHectares(geometry), 4),
      warnings: parsed.warnings,
    };
  }
  return {
    points: parsed.points,
    kind: 'invalid',
    geometry: null,
    area_hectares: null,
    warnings: parsed.warnings,
  };
}
