/**
 * Offline fallback: serves the fixtures in /public/demo as if they came from
 * the API, so every screen renders when the back end is unreachable.
 *
 * Fixture values are synthetic and static. The fallback never computes a
 * carbon number — a plot or inventory created offline gets the demo estimate
 * back with a provenance note saying so (engines calculate, UI renders).
 */
import type {
  Analysis,
  AttributionResponse,
  CarbonEstimate,
  CarbonEstimateBody,
  Confidence,
  Cube,
  CubeIndex,
  DataQualityField,
  ExplainBody,
  ExplainResponse,
  FromLineBody,
  FromLineResult,
  FromPointBody,
  FromPointResult,
  GeocodeResponse,
  Health,
  MarketScenario,
  Methodology,
  ParseCoordinatesBody,
  ParseCoordinatesResult,
  Plot,
  PlotCreateBody,
  PlotList,
  PolicyEligibility,
  Region,
  ReportBody,
  ReportHandle,
  Simulation,
  SimulateBody,
  Species,
  TreeInventory,
  TreeInventoryBody,
  TreeInventoryList,
} from '@/types/api';
import { areaHectares, bboxOf, centroidOf, perimeterMetres, publicCentroid } from '@/lib/geo';
import { ACRES_PER_HECTARE } from '@/lib/format';
import { GeometryInputError, offlineFromLine, offlineFromPoint, offlineParseCoordinates } from '@/lib/geometryOffline';
import { regionIdFor } from '@/config/regions';
import { ApiError } from './api';
import { latestInventory } from '@/lib/insights';

export const DEMO_PLOT_ID = 'PLT-DEMOIN';
const OFFLINE_NOTE = 'Offline demo fixture: values are not recomputed for your inputs. Start the API with `make api`.';

function fixtureUrl(name: string): string {
  const base = (import.meta.env.BASE_URL as string | undefined) ?? '/';
  return `${base.replace(/\/+$/, '')}/demo/${name}`;
}

const cache = new Map<string, Promise<unknown>>();

export async function loadFixture<T>(name: string): Promise<T> {
  if (!cache.has(name)) {
    const promise = fetch(fixtureUrl(name)).then(async (r) => {
      if (!r.ok) throw new Error(`Demo fixture ${name} not found (${r.status})`);
      return (await r.json()) as unknown;
    });
    cache.set(name, promise);
    promise.catch(() => cache.delete(name));
  }
  return cache.get(name) as Promise<T>;
}

/** Test hook: preload fixtures without network access. */
export function primeFixture(name: string, data: unknown): void {
  cache.set(name, Promise.resolve(data));
}

export function clearFixtureCache(): void {
  cache.clear();
  offlinePlots.clear();
  offlineTrees.clear();
}

const clone = <T>(v: T): T => (typeof structuredClone === 'function' ? structuredClone(v) : (JSON.parse(JSON.stringify(v)) as T));

// In-memory state for things created while offline (plots drawn, trees edited).
const offlinePlots = new Map<string, Plot>();
const offlineTrees = new Map<string, TreeInventory[]>();
let plotCounter = 0;
let inventoryCounter = 0;

function makeId(prefix: string, n: number): string {
  return `${prefix}-${n.toString(36).toUpperCase().padStart(4, '0')}`;
}

function countryFromCentroid(c: { lat: number; lon: number }): string {
  if (c.lon >= 68.1 && c.lon <= 97.4 && c.lat >= 6.5 && c.lat <= 35.7) return 'IN';
  if (c.lon >= -125 && c.lon <= -66.9 && c.lat >= 24.4 && c.lat <= 49.4) return 'US';
  if (c.lon >= -10.5 && c.lon <= 31.6 && c.lat >= 34.5 && c.lat <= 71.2) return 'EU';
  return 'IN';
}

/** Mirrors the contract's confidence rule for tree inventories. */
export function inventoryDataQuality(body: TreeInventoryBody): { fields: DataQualityField[]; confidence: Confidence } {
  const fields: DataQualityField[] = [
    { name: 'tree_count', status: body.tree_count > 0 ? 'supplied' : 'missing' },
    { name: 'species', status: body.species_id ? 'supplied' : 'missing' },
    { name: 'age', status: Number.isFinite(body.plantation_year) ? 'supplied' : 'missing' },
    { name: 'dbh', status: body.average_dbh_cm != null ? 'supplied' : 'missing' },
    { name: 'height', status: body.average_height_m != null ? 'supplied' : 'missing' },
    { name: 'mortality', status: body.survival_rate != null ? 'supplied' : 'missing' },
  ];
  const supplied = (name: string) => fields.find((f) => f.name === name)?.status === 'supplied';
  const confidence: Confidence =
    supplied('tree_count') && supplied('species') && supplied('age') && supplied('dbh') && supplied('height')
      ? 'high'
      : supplied('tree_count') && supplied('species') && supplied('age')
        ? 'medium'
        : 'low';
  return { fields, confidence };
}

/** Features that only the server can do (imports, detection, imagery) fail offline with this. */
export class FeatureNeedsApiError extends Error {
  readonly feature: string;
  constructor(feature: string) {
    super(`${feature} needs the AgriCarbon Atlas API. Start it with \`make api\` and try again.`);
    this.name = 'FeatureNeedsApiError';
    this.feature = feature;
  }
}

/** Fallback for a server-only feature: always rejects with FeatureNeedsApiError. */
export function needsApi(feature: string): (..._args: unknown[]) => Promise<never> {
  return async () => {
    throw new FeatureNeedsApiError(feature);
  };
}

/** Offline geometry helpers answer like the API: invalid input is a 422 problem. */
function asProblem<A extends unknown[], R>(fn: (...args: A) => R): (...args: A) => Promise<R> {
  return async (...args: A) => {
    try {
      return fn(...args);
    } catch (error) {
      if (error instanceof GeometryInputError) {
        throw new ApiError(422, { title: 'Invalid geometry input', status: 422, detail: error.message }, 'Invalid geometry input');
      }
      throw error;
    }
  };
}

function notFound(resource: string, id: string): ApiError {
  return new ApiError(404, { title: 'Not found', status: 404, detail: `${resource} ${id} does not exist in the offline demo` }, 'Not found');
}

async function allPlots(): Promise<Plot[]> {
  const fixture = await loadFixture<PlotList>('plots.json');
  return [...fixture.items.map(clone), ...offlinePlots.values()];
}

export const demo = {
  health: async (): Promise<Health> => ({ ...(await loadFixture<Health>('health.json')), time: new Date().toISOString() }),
  regions: () => loadFixture<Region[]>('regions.json'),
  geocode: async (q: string, country?: string): Promise<GeocodeResponse> => {
    const fixture = await loadFixture<GeocodeResponse>('geocode.json');
    const needle = q.trim().toLowerCase();
    const results = fixture.results.filter((r) => {
      const matchesCountry = !country || regionIdFor(r.admin?.country) === regionIdFor(country);
      return matchesCountry && (needle.length === 0 || r.label.toLowerCase().includes(needle));
    });
    return { ...fixture, results };
  },
  species: async (country?: string): Promise<Species[]> => {
    const all = await loadFixture<Species[]>('species.json');
    if (!country) return all;
    const region = regionIdFor(country);
    return all.filter((s) => s.regions.includes(region));
  },
  methodologies: () => loadFixture<Methodology[]>('methodologies.json'),
  attribution: () => loadFixture<AttributionResponse>('attribution.json'),

  listPlots: async (): Promise<PlotList> => ({ items: await allPlots() }),
  getPlot: async (plotId: string): Promise<Plot> => {
    const plot = (await allPlots()).find((p) => p.plot_id === plotId);
    if (!plot) throw notFound('Plot', plotId);
    return plot;
  },
  createPlot: async (body: PlotCreateBody): Promise<Plot> => {
    plotCounter += 1;
    const ha = areaHectares(body.geometry);
    const centroid = centroidOf(body.geometry);
    const country = body.country ?? countryFromCentroid(centroid);
    const plot: Plot = {
      plot_id: makeId('PLT', 1000 + plotCounter),
      name: body.name,
      country,
      region: null,
      geometry: body.geometry,
      area_hectares: Number(ha.toFixed(2)),
      area_acres: Number((ha * ACRES_PER_HECTARE).toFixed(2)),
      perimeter_m: Number(perimeterMetres(body.geometry).toFixed(1)),
      centroid: { lat: Number(centroid.lat.toFixed(4)), lon: Number(centroid.lon.toFixed(4)) },
      public_centroid: publicCentroid(centroid),
      source: body.source,
      boundary_quality: body.boundary_quality ?? 'exact',
      privacy: 'private',
      created_at: new Date().toISOString(),
    };
    offlinePlots.set(plot.plot_id, plot);
    return plot;
  },
  deletePlot: async (plotId: string): Promise<void> => {
    offlinePlots.delete(plotId);
    offlineTrees.delete(plotId);
  },

  analyze: async (plotId: string): Promise<Analysis> => {
    const fixture = clone(await loadFixture<Analysis>('analysis.json'));
    fixture.plot_id = plotId;
    if (plotId !== DEMO_PLOT_ID) {
      fixture.data_quality = { warnings: [...fixture.data_quality.warnings, OFFLINE_NOTE] };
      const plot = offlinePlots.get(plotId);
      if (plot && fixture.landcover) {
        fixture.landcover.classes = fixture.landcover.classes.map((c) => ({ ...c, area_ha: Number((c.share * plot.area_hectares).toFixed(2)) }));
      }
    }
    return fixture;
  },
  cube: async (plotId: string, index: CubeIndex = 'ndvi'): Promise<Cube> => {
    if (index !== 'ndvi') {
      throw new ApiError(422, { title: 'Unsupported index', status: 422, detail: `Index ${index} is not available in the offline demo` }, 'Unsupported index');
    }
    const fixture = clone(await loadFixture<Cube>('cube.json'));
    fixture.plot_id = plotId;
    const plot = offlinePlots.get(plotId);
    if (plot?.geometry) {
      // Re-anchor the synthetic grid on the drawn polygon so the NDVI cells sit on the plot.
      fixture.grid = { ...fixture.grid, bbox: bboxOf(plot.geometry) };
    }
    return fixture;
  },

  listTrees: async (plotId: string): Promise<TreeInventoryList> => {
    if (offlineTrees.has(plotId)) return { items: offlineTrees.get(plotId) ?? [] };
    if (plotId === DEMO_PLOT_ID) return clone(await loadFixture<TreeInventoryList>('trees.json'));
    return { items: [] };
  },
  createTrees: async (plotId: string, body: TreeInventoryBody): Promise<TreeInventory> => {
    const [plot, species] = await Promise.all([demo.getPlot(plotId), loadFixture<Species[]>('species.json')]);
    const sp = species.find((s) => s.id === body.species_id);
    if (!sp) throw new ApiError(422, { title: 'Unknown species', status: 422, detail: `species_id ${body.species_id}` }, 'Unknown species');
    inventoryCounter += 1;
    const year = new Date().getUTCFullYear();
    const inventory: TreeInventory = {
      inventory_id: makeId('INV', 100 + inventoryCounter),
      plot_id: plotId,
      species: { id: sp.id, scientific_name: sp.scientific_name, common_name: sp.common_name },
      tree_count: body.tree_count,
      density_per_ha: Number((body.tree_count / plot.area_hectares).toFixed(1)),
      plantation_year: body.plantation_year,
      age_years: Math.max(0, year - body.plantation_year),
      average_dbh_cm: body.average_dbh_cm,
      average_height_m: body.average_height_m,
      survival_rate: body.survival_rate,
      measurement_source: body.measurement_source,
      data_quality: inventoryDataQuality(body),
      created_at: new Date().toISOString(),
    };
    const existing = offlineTrees.get(plotId) ?? (plotId === DEMO_PLOT_ID ? clone(await loadFixture<TreeInventoryList>('trees.json')).items : []);
    offlineTrees.set(plotId, [inventory, ...existing]);
    return inventory;
  },

  carbonEstimate: async (plotId: string, body: CarbonEstimateBody = {}): Promise<CarbonEstimate> => {
    const fixture = clone(await loadFixture<CarbonEstimate>('carbon-estimate.json'));
    fixture.plot_id = plotId;
    const latest = latestInventory((await demo.listTrees(plotId)).items);
    const inventoryId = body.inventory_id ?? latest?.inventory_id ?? null;
    fixture.inventory_id = inventoryId;
    if (inventoryId !== 'INV-01' || plotId !== DEMO_PLOT_ID) {
      fixture.provenance = { ...fixture.provenance, notes: [...(fixture.provenance.notes ?? []), OFFLINE_NOTE] };
      if (latest) fixture.confidence = latest.data_quality.confidence;
    }
    return fixture;
  },
  policyEligibility: async (plotId: string): Promise<PolicyEligibility> => {
    const plot = await demo.getPlot(plotId);
    const fixture = clone(await loadFixture<PolicyEligibility>('policy-eligibility.json'));
    if (regionIdFor(plot.country) !== 'IN') {
      // Only the Indian screening ships as a fixture; other regions report unknown offline.
      return {
        country: plot.country,
        activity: fixture.activity,
        disclaimer: fixture.disclaimer,
        programmes: [],
      };
    }
    return fixture;
  },
  marketScenario: async (_plotId: string, _estimateId?: string): Promise<MarketScenario> => loadFixture<MarketScenario>('market-scenario.json'),

  createReport: async (_plotId: string, _body: ReportBody): Promise<ReportHandle> => loadFixture<ReportHandle>('report.json'),
  fetchReportDocument: async (reportUrl: string): Promise<string> => {
    const url = reportUrl.startsWith('/demo/') ? fixtureUrl(reportUrl.replace('/demo/', '')) : reportUrl;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`Report not available offline (${r.status})`);
    return r.text();
  },

  simulate: async (body: SimulateBody): Promise<Simulation> => {
    const region = regionIdFor(body.country);
    const fixture = clone(await loadFixture<Simulation>(`simulate-${region}.json`));
    fixture.inputs = { ...fixture.inputs, ...body };
    fixture.share_params = {
      country: body.country,
      species: body.species_id,
      trees: body.tree_count,
      year: body.planting_year,
      horizon: body.horizon_years,
    };
    fixture.provenance = { ...fixture.provenance, notes: [...(fixture.provenance.notes ?? []), OFFLINE_NOTE] };
    return fixture;
  },

  /** Deterministic template text — same role as the API's `template` provider. */
  explain: async (body: ExplainBody): Promise<ExplainResponse> => {
    const i = body.indicators;
    const parts: string[] = [];
    if (i.area_hectares != null) parts.push(`Your plot covers about ${i.area_hectares} hectares.`);
    if (i.tree_count != null && i.species) parts.push(`You reported ${i.tree_count} ${i.species} trees.`);
    if (i.ndvi != null) {
      const health = i.ndvi >= 0.6 ? 'healthy' : i.ndvi >= 0.3 ? 'moderate' : 'sparse';
      parts.push(`The latest vegetation index (NDVI ${i.ndvi}) indicates ${health} vegetation${i.ndvi_trend_pct != null ? `, with a ${i.ndvi_trend_pct > 0 ? 'rise' : 'change'} of about ${Math.abs(i.ndvi_trend_pct).toFixed(0)}% over the evaluated period` : ''}.`);
    }
    if (i.estimate_central != null) {
      parts.push(`The model estimates roughly ${i.estimate_central} tCO₂e of annual removal (range ${i.estimate_low ?? '—'} to ${i.estimate_high ?? '—'}), with ${i.confidence ?? 'medium'} confidence.`);
    }
    if (i.missing_evidence && i.missing_evidence.length > 0) {
      parts.push(`Collecting ${i.missing_evidence.join(', ')} would narrow the range and improve programme readiness.`);
    }
    parts.push('This is a scenario estimate, not an issued carbon credit.');
    return {
      text: parts.join(' '),
      provider: 'template',
      privacy_note: 'Only derived indicators were used; no coordinates were processed.',
    };
  },

  // v0.2 geometry helpers: computed in the browser and labelled as offline.
  geometryFromPoint: asProblem((body: FromPointBody): FromPointResult => offlineFromPoint(body)),
  geometryFromLine: asProblem((body: FromLineBody): FromLineResult => offlineFromLine(body)),
  parseCoordinates: asProblem((body: ParseCoordinatesBody): ParseCoordinatesResult => offlineParseCoordinates(body)),
};

export type DemoApi = typeof demo;
