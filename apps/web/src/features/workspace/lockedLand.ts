/**
 * "Locked land": the saved boundary's corners, its size and how many trees of
 * a species fit — pure helpers, unit-tested. The tree count is the area times
 * the species' configured reference density (config/species/species.yaml,
 * shown with its source and verification status); nothing is guessed.
 */
import type { PolygonGeometry, Species } from '@/types/api';

export interface Corner {
  lat: number;
  lon: number;
}

/** The ring's corners without the closing point (GeoJSON order is lon, lat). */
export function corners(geometry: PolygonGeometry | undefined): Corner[] {
  const ring = geometry?.coordinates[0] ?? [];
  const closed =
    ring.length > 1 &&
    ring[0][0] === ring[ring.length - 1][0] &&
    ring[0][1] === ring[ring.length - 1][1];
  return (closed ? ring.slice(0, -1) : ring).map(([lon, lat]) => ({ lat, lon }));
}

/** "lat, lon" per line, six decimals (about 0.1 m) — what the Copy button puts on the clipboard. */
export function cornersText(list: Corner[]): string {
  return list.map((c) => `${c.lat.toFixed(6)}, ${c.lon.toFixed(6)}`).join('\n');
}

export interface TreeFit {
  /** Whole trees that fit at the reference density; null when the species has none configured. */
  trees: number | null;
  densityPerHa: number | null;
  /** Grid spacing implied by the density, in metres. */
  spacingM: number | null;
  source: string | null;
  status: string | null;
}

export function treesThatFit(areaHectares: number, species: Species | undefined): TreeFit {
  const density = species?.reference_density_per_ha?.value;
  if (typeof density !== 'number' || density <= 0 || !(areaHectares > 0)) {
    return { trees: null, densityPerHa: null, spacingM: null, source: null, status: null };
  }
  return {
    trees: Math.floor(areaHectares * density),
    densityPerHa: density,
    spacingM: Number(Math.sqrt(10_000 / density).toFixed(1)),
    source: species?.reference_density_per_ha.source ?? null,
    status: species?.reference_density_per_ha.verification_status ?? null,
  };
}

/** The Simulation link: plot id, species and counts only — never coordinates. */
export function simulateLink(
  plot: { plot_id: string; country: string; area_hectares: number },
  speciesId: string,
  trees: number,
  year: number,
): string {
  const params = new URLSearchParams({
    plot: plot.plot_id,
    country: plot.country,
    species: speciesId,
    trees: String(trees),
    year: String(year),
    horizon: '30',
    area: String(plot.area_hectares),
  });
  return `/app/simulate?${params.toString()}`;
}
