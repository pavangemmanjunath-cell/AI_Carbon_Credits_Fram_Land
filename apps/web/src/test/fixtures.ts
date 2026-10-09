/** Tiny deterministic fixtures for unit tests (no network, no files). */
import type { Analysis, CarbonEstimate, Cube, ImportRecord, Plot, TreeInventory } from '@/types/api';

export function makeCube(rows = 3, cols = 3, months = 36): Cube {
  const times = Array.from({ length: months }, (_, i) => {
    const year = 2023 + Math.floor((i + 9) / 12);
    const month = ((i + 9) % 12) + 1;
    return `${year}-${String(month).padStart(2, '0')}`;
  });
  const mask = Array.from({ length: rows }, (_, r) => Array.from({ length: cols }, (_, c) => (r === 0 && c === 0 ? 0 : 1)));
  const values = times.map((_, t) =>
    Array.from({ length: rows }, (_, r) =>
      Array.from({ length: cols }, (_, c) => {
        if (!mask[r][c]) return null;
        // cell (2,2) is stressed mid-series; others grow steadily
        if (r === 2 && c === 2 && t >= 18 && t <= 22) return 0.3;
        return Math.min(0.9, 0.5 + t * 0.01 + (r + c) * 0.02);
      }),
    ),
  );
  return {
    plot_id: 'PLT-TEST',
    index: 'ndvi',
    mode: 'demo',
    grid: { rows, cols, cell_size_m: 30, bbox: [77.53, 13.29, 77.531, 13.291], crs: 'EPSG:4326' },
    times,
    mask,
    values,
    stats_per_time: times.map((time) => ({ time, mean: 0.6, min: 0.3, max: 0.9, valid_share: 1 })),
    provenance: { source: 'synthetic-demo', composite: 'monthly-min-cloud', cloud_mask: 'SCL', aggregation: '3×3 mean', scene_ids: [] },
  };
}

export const plot: Plot = {
  plot_id: 'PLT-TEST',
  name: 'Plot A',
  country: 'IN',
  region: 'Karnataka',
  geometry: { type: 'Polygon', coordinates: [[[77.53, 13.29], [77.54, 13.29], [77.54, 13.3], [77.53, 13.3], [77.53, 13.29]]] },
  area_hectares: 2.13,
  area_acres: 5.26,
  perimeter_m: 612,
  centroid: { lat: 13.295, lon: 77.535 },
  public_centroid: { lat: 13.3, lon: 77.55 },
  source: 'synthetic-demo',
  privacy: 'private',
  created_at: '2026-10-05T00:00:00Z',
};

export const inventory: TreeInventory = {
  inventory_id: 'INV-1',
  plot_id: 'PLT-TEST',
  species: { id: 'mango', scientific_name: 'Mangifera indica', common_name: 'Mango' },
  tree_count: 420,
  density_per_ha: 197.2,
  plantation_year: 2023,
  age_years: 3,
  average_dbh_cm: null,
  average_height_m: null,
  survival_rate: 0.85,
  measurement_source: 'user-reported',
  data_quality: {
    fields: [
      { name: 'tree_count', status: 'supplied' },
      { name: 'species', status: 'supplied' },
      { name: 'age', status: 'supplied' },
      { name: 'dbh', status: 'missing' },
    ],
    confidence: 'medium',
  },
  created_at: '2026-10-05T00:00:00Z',
};

export const estimate: CarbonEstimate = {
  estimate_id: 'EST-1',
  plot_id: 'PLT-TEST',
  inventory_id: 'INV-1',
  model: { id: 'tree-biomass', version: '0.1.0', tier: '1' },
  methodology: { id: 'ipcc-2006-vol4-ch4', name: 'IPCC 2006 Vol.4 Ch.4 Tier 1' },
  estimate: { low: 7.4, central: 10.6, high: 13.8, unit: 'tCO2e/yr' },
  stock: { low: 16, central: 23, high: 30, unit: 'tCO2e' },
  annual_series: [0, 1, 2, 3].map((i) => ({ year: 2023 + i, age: i, low: i * 2, central: i * 3, high: i * 4, cum_low: i * 2, cum_central: i * 3, cum_high: i * 4 })),
  parameters_used: [
    { name: 'carbon_fraction', value: 0.47, unit: 't C/t d.m.', source: 'IPCC 2006 Table 4.3', verification_status: 'verified' },
    { name: 'above_ground_biomass_growth', value: 4, unit: 't d.m./ha/yr', source: 'IPCC Table 4.12', verification_status: 'pending' },
    { name: 'survival_rate', value: 0.85, unit: 'fraction', source: 'assumption v0.1', verification_status: 'assumption' },
  ],
  confidence: 'medium',
  certified: false,
  disclaimer: 'Scenario estimate; not an issued carbon credit.',
  readiness: {
    score: 55,
    grade: 'medium',
    present_evidence: [{ id: 'polygon', label: 'Land polygon' }],
    missing_evidence: [{ id: 'dbh', label: 'Tree diameter measurements', weight: 15 }],
  },
  provenance: { generated_at: '2026-10-05T00:00:00Z', api_version: '1', mode: 'demo', sources: [] },
  generated_at: '2026-10-05T00:00:00Z',
};

export const analysis: Analysis = {
  plot_id: 'PLT-TEST',
  mode: 'demo',
  landcover: {
    dataset: 'ESA WorldCover',
    version: '2021 v200',
    resolution_m: 10,
    classes: [
      { code: 40, name: 'Cropland', share: 0.62, area_ha: 1.32 },
      { code: 10, name: 'Tree cover', share: 0.38, area_ha: 0.81 },
    ],
    tree_cover_share: 0.38,
    cropland_share: 0.62,
    provenance: { generated_at: '', api_version: '1', mode: 'demo', sources: [] },
  },
  vegetation: {
    indices: { ndvi: { value: 0.76, class: 'healthy', date: '2026-09-21', scene_id: 'S2X' } },
    time_series: [
      { date: '2024-09-22', ndvi: 0.62, ndmi: 0.14, cloud_cover: 2, scene_id: 'a' },
      { date: '2026-09-21', ndvi: 0.76, ndmi: 0.21, cloud_cover: 3, scene_id: 'b' },
    ],
    trend: { start: '2024-09', end: '2026-09', change_pct: 22.6, statement: 'up' },
    provenance: { generated_at: '', api_version: '1', mode: 'demo', sources: [] },
  },
  climate: { zone: 'tropical_dry', zone_label: 'Tropical dry', mean_annual_temp_c: 24, annual_precip_mm: 820, elevation_m: 880, provenance: { generated_at: '', api_version: '1', mode: 'demo', sources: [] } },
  data_quality: { warnings: ['demo'] },
  generated_at: '2026-10-05T00:00:00Z',
};

/** A LAZ point-cloud import linked to the demo plot (128 tree tops, 120 inside the plot). */
export function importRecord(extra: Partial<ImportRecord> = {}): ImportRecord {
  return {
    import_id: 'IMP-1',
    filename: 'orchard.laz',
    format: 'laz',
    size_bytes: 1_840_221,
    created_at: '2026-10-05T08:00:00Z',
    plot_id: 'PLT-DEMOIN',
    kind: 'point-cloud',
    status: 'ready',
    summary: { feature_count: 0, polygon_count: 0, point_count: 412_883, georeferenced: true, crs: 'EPSG:32643' },
    boundary: null,
    trees: { count: 128, count_in_plot: 120, mean_height_m: 6.43, median_height_m: 6.1, p90_height_m: 8.9, canopy_cover_fraction: 0.42, confidence_field: null, min_confidence: null, method: 'chm + local maxima' },
    detection: { ran: true, method: 'canopy height model + local maxima', parameters: { cell_size_m: 0.5 }, notes: [] },
    preview: null,
    warnings: [],
    privacy: 'private',
    ...extra,
  };
}
