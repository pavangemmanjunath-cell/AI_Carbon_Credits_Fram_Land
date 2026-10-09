/**
 * API facade used by the query hooks: tries the live API and transparently
 * falls back to the offline demo fixtures when the server is unreachable.
 * Real API errors (404, 422, …) are NOT swallowed — only connectivity failures.
 */
import { ApiError, api, isUnreachable } from './api';
import { demo, needsApi } from './demoFallback';
import { useUiStore } from '@/store/uiStore';
import type { Detection } from '@/types/api';

type AnyFn = (...args: never[]) => Promise<unknown>;

function withFallback<F extends AnyFn>(live: F, fallback: F): F {
  const wrapped = (async (...args: Parameters<F>) => {
    const { apiStatus, setApiStatus } = useUiStore.getState();
    if (apiStatus === 'offline') return fallback(...args);
    try {
      const result = await live(...args);
      if (apiStatus !== 'online') setApiStatus('online');
      return result;
    } catch (error) {
      if (isUnreachable(error)) {
        setApiStatus('offline');
        return fallback(...args);
      }
      throw error;
    }
  }) as unknown as F;
  return wrapped;
}

export const client = {
  health: withFallback(api.health, demo.health),
  regions: withFallback(api.regions, demo.regions),
  geocode: withFallback(api.geocode, demo.geocode),
  species: withFallback(api.species, demo.species),
  methodologies: withFallback(api.methodologies, demo.methodologies),
  attribution: withFallback(api.attribution, demo.attribution),
  listPlots: withFallback(api.listPlots, demo.listPlots),
  getPlot: withFallback(api.getPlot, demo.getPlot),
  createPlot: withFallback(api.createPlot, demo.createPlot),
  deletePlot: withFallback(api.deletePlot, demo.deletePlot),
  analyze: withFallback(api.analyze, demo.analyze),
  cube: withFallback(api.cube, demo.cube),
  listTrees: withFallback(api.listTrees, demo.listTrees),
  createTrees: withFallback(api.createTrees, demo.createTrees),
  carbonEstimate: withFallback(api.carbonEstimate, demo.carbonEstimate),
  policyEligibility: withFallback(api.policyEligibility, demo.policyEligibility),
  marketScenario: withFallback(api.marketScenario, demo.marketScenario),
  createReport: withFallback(api.createReport, demo.createReport),
  fetchReportDocument: withFallback(api.fetchReportDocument, demo.fetchReportDocument),
  simulate: withFallback(api.simulate, demo.simulate),
  explain: withFallback(api.explain, demo.explain),

  // v0.2 — geometry helpers fall back to clearly labelled browser calculations.
  geometryFromPoint: withFallback(api.geometryFromPoint, demo.geometryFromPoint),
  geometryFromLine: withFallback(api.geometryFromLine, demo.geometryFromLine),
  parseCoordinates: withFallback(api.parseCoordinates, demo.parseCoordinates),
  // v0.2 — imports, detection and imagery only exist on the server.
  uploadImport: withFallback(api.uploadImport, needsApi('Importing files')),
  listImports: withFallback(api.listImports, needsApi('Imported files')),
  getImport: withFallback(api.getImport, needsApi('Imported files')),
  deleteImport: withFallback(api.deleteImport, needsApi('Imported files')),
  detect: withFallback(api.detect, needsApi('Tree-cover detection')),
  latestDetection: withFallback(api.latestDetection, needsApi('Tree-cover detection')),
  imageryProviders: withFallback(api.imageryProviders, needsApi('Satellite imagery')),

  /** Latest stored tree-cover detection for the plot, or a new one when none exists yet. */
  latestOrDetect: async (plotId: string, minConfidence = 0.5): Promise<Detection> => {
    try {
      return await client.latestDetection(plotId);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return client.detect(plotId, { target: 'tree-cover', min_confidence: minConfidence });
      }
      throw error;
    }
  },
};

/**
 * Probes /health directly (bypassing the fallback) so a recovered server
 * flips the app back online.
 */
export async function probeHealth(): Promise<'online' | 'offline'> {
  const { setApiStatus } = useUiStore.getState();
  try {
    const health = await api.health();
    setApiStatus('online', health.mode);
    return 'online';
  } catch (error) {
    if (isUnreachable(error)) {
      setApiStatus('offline');
      return 'offline';
    }
    // The server answered (even with an error) — it is reachable.
    setApiStatus('online');
    return 'online';
  }
}
