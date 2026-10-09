/**
 * TanStack Query hooks — the only way components talk to the API.
 * Server state lives here; UI state lives in the Zustand store.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { client, probeHealth } from './client';
import { useUiStore } from '@/store/uiStore';
import type {
  CubeIndex,
  ExplainBody,
  FromLineBody,
  FromPointBody,
  ImportList,
  ImportRecord,
  ImportUploadOptions,
  PlotCreateBody,
  PlotList,
  ReportBody,
  SimulateBody,
  TreeInventoryBody,
  TreeInventoryList,
} from '@/types/api';

const MINUTE = 60_000;

export const queryKeys = {
  health: ['health'] as const,
  regions: ['regions'] as const,
  species: (country?: string) => ['species', country ?? 'all'] as const,
  plots: ['plots'] as const,
  plot: (id: string) => ['plot', id] as const,
  analysis: (id: string) => ['analysis', id] as const,
  cube: (id: string, index: CubeIndex) => ['cube', id, index] as const,
  trees: (id: string) => ['trees', id] as const,
  estimate: (id: string, inventoryId?: string | null) => ['estimate', id, inventoryId ?? 'latest'] as const,
  policy: (id: string) => ['policy', id] as const,
  market: (id: string, estimateId?: string) => ['market', id, estimateId ?? 'latest'] as const,
  simulate: (body: SimulateBody) => ['simulate', body] as const,
  explain: (body: ExplainBody) => ['explain', body] as const,
  geocode: (q: string, country?: string) => ['geocode', q, country ?? ''] as const,
  report: (id: string, language: string, estimateId?: string) => ['report', id, language, estimateId ?? 'latest'] as const,
  imports: (plotId?: string | null) => ['imports', plotId ?? 'all'] as const,
  importRecord: (id: string) => ['import', id] as const,
  detection: (plotId: string) => ['detection', plotId] as const,
  imagery: (country?: string) => ['imagery', country ?? 'default'] as const,
  fromPoint: (body: FromPointBody) => ['geometry', 'from-point', body] as const,
  fromLine: (body: FromLineBody) => ['geometry', 'from-line', body] as const,
  parseCoordinates: (text: string) => ['geometry', 'parse-coordinates', text] as const,
};

/** Polls /health; keeps the offline banner honest when the server comes back. */
export function useHealth() {
  const apiStatus = useUiStore((s) => s.apiStatus);
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: probeHealth,
    refetchInterval: apiStatus === 'offline' ? 20_000 : 5 * MINUTE,
    refetchOnWindowFocus: true,
    staleTime: 10_000,
    retry: false,
  });
}

export function useRegions() {
  return useQuery({ queryKey: queryKeys.regions, queryFn: () => client.regions(), staleTime: Infinity });
}

export function useSpecies(country?: string) {
  return useQuery({
    queryKey: queryKeys.species(country),
    queryFn: () => client.species(country),
    staleTime: Infinity,
  });
}

export function usePlots() {
  return useQuery({ queryKey: queryKeys.plots, queryFn: () => client.listPlots(), staleTime: 5 * MINUTE });
}

export function usePlot(plotId: string | null | undefined) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: queryKeys.plot(plotId ?? ''),
    queryFn: () => client.getPlot(plotId as string),
    enabled: Boolean(plotId),
    staleTime: 5 * MINUTE,
    // Reuse the list entry while the detail request is in flight.
    placeholderData: () => queryClient.getQueryData<PlotList>(queryKeys.plots)?.items.find((p) => p.plot_id === plotId),
  });
}

/** POST /analyze is idempotent for a plot, so it is cached like a query. */
export function useAnalysis(plotId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.analysis(plotId ?? ''),
    queryFn: () => client.analyze(plotId as string, { layers: ['landcover', 'vegetation', 'climate', 'soil', 'terrain'] }),
    enabled: Boolean(plotId),
    staleTime: Infinity,
    retry: 1,
  });
}

export function useCube(plotId: string | null | undefined, index: CubeIndex = 'ndvi', enabled = true) {
  return useQuery({
    queryKey: queryKeys.cube(plotId ?? '', index),
    queryFn: () => client.cube(plotId as string, index, 36),
    enabled: Boolean(plotId) && enabled,
    staleTime: Infinity,
    retry: 1,
  });
}

export function useTrees(plotId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.trees(plotId ?? ''),
    queryFn: () => client.listTrees(plotId as string),
    enabled: Boolean(plotId),
    staleTime: 5 * MINUTE,
  });
}

export function useCarbonEstimate(plotId: string | null | undefined, inventoryId?: string | null, enabled = true) {
  return useQuery({
    queryKey: queryKeys.estimate(plotId ?? '', inventoryId),
    queryFn: () => client.carbonEstimate(plotId as string, inventoryId ? { inventory_id: inventoryId } : {}),
    enabled: Boolean(plotId) && enabled,
    staleTime: 10 * MINUTE,
    placeholderData: keepPreviousData,
  });
}

export function usePolicyEligibility(plotId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.policy(plotId ?? ''),
    queryFn: () => client.policyEligibility(plotId as string, 'tree_plantation'),
    enabled: Boolean(plotId),
    staleTime: 30 * MINUTE,
  });
}

export function useMarketScenario(plotId: string | null | undefined, estimateId?: string) {
  return useQuery({
    queryKey: queryKeys.market(plotId ?? '', estimateId),
    queryFn: () => client.marketScenario(plotId as string, estimateId),
    enabled: Boolean(plotId) && Boolean(estimateId),
    staleTime: 30 * MINUTE,
  });
}

export function useSimulation(body: SimulateBody | null) {
  return useQuery({
    queryKey: body ? queryKeys.simulate(body) : ['simulate', 'idle'],
    queryFn: ({ signal }) => client.simulate(body as SimulateBody, signal),
    enabled: Boolean(body),
    staleTime: 30 * MINUTE,
    placeholderData: keepPreviousData,
  });
}

export function useExplain(body: ExplainBody | null) {
  return useQuery({
    queryKey: body ? queryKeys.explain(body) : ['explain', 'idle'],
    queryFn: () => client.explain(body as ExplainBody),
    enabled: Boolean(body),
    staleTime: 30 * MINUTE,
  });
}

export function useGeocode(q: string, country?: string) {
  const trimmed = q.trim();
  return useQuery({
    queryKey: queryKeys.geocode(trimmed, country),
    queryFn: ({ signal }) => client.geocode(trimmed, country, signal),
    enabled: trimmed.length >= 3,
    staleTime: 10 * MINUTE,
    placeholderData: keepPreviousData,
  });
}

export function useReportDocument(plotId: string | null | undefined, language: string, estimateId?: string) {
  return useQuery({
    queryKey: queryKeys.report(plotId ?? '', language, estimateId),
    queryFn: async () => {
      const body: ReportBody = { format: 'html', language, estimate_id: estimateId };
      const handle = await client.createReport(plotId as string, body);
      const html = await client.fetchReportDocument(handle.url);
      return { handle, html };
    },
    enabled: Boolean(plotId),
    staleTime: 10 * MINUTE,
    retry: 1,
  });
}

// ─── Mutations ───────────────────────────────────────────────────────────────

export function useCreatePlot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PlotCreateBody) => client.createPlot(body),
    onSuccess: (plot) => {
      queryClient.setQueryData(queryKeys.plot(plot.plot_id), plot);
      void queryClient.invalidateQueries({ queryKey: queryKeys.plots });
    },
  });
}

export function useDeletePlot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (plotId: string) => client.deletePlot(plotId),
    onSuccess: (_, plotId) => {
      queryClient.removeQueries({ queryKey: queryKeys.plot(plotId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.plots });
    },
  });
}

export function useCreateTrees(plotId: string | null | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: TreeInventoryBody) => client.createTrees(plotId as string, body),
    onSuccess: (inventory) => {
      queryClient.setQueryData<TreeInventoryList>(queryKeys.trees(inventory.plot_id), (prev) => ({
        items: [inventory, ...(prev?.items ?? []).filter((i) => i.inventory_id !== inventory.inventory_id)],
      }));
    },
  });
}

export function useAddTrees() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ plotId, body }: { plotId: string; body: TreeInventoryBody }) => client.createTrees(plotId, body),
    onSuccess: (inventory) => {
      queryClient.setQueryData<TreeInventoryList>(queryKeys.trees(inventory.plot_id), (prev) => ({
        items: [inventory, ...(prev?.items ?? []).filter((i) => i.inventory_id !== inventory.inventory_id)],
      }));
    },
  });
}

// ─── v0.2 · geometry helpers (pure calculations, cached like queries) ────────

export function useGeometryFromPoint(body: FromPointBody | null) {
  return useQuery({
    queryKey: body ? queryKeys.fromPoint(body) : ['geometry', 'from-point', 'idle'],
    queryFn: ({ signal }) => client.geometryFromPoint(body as FromPointBody, signal),
    enabled: Boolean(body),
    staleTime: Infinity,
    retry: false,
    placeholderData: keepPreviousData,
  });
}

export function useGeometryFromLine(body: FromLineBody | null) {
  return useQuery({
    queryKey: body ? queryKeys.fromLine(body) : ['geometry', 'from-line', 'idle'],
    queryFn: ({ signal }) => client.geometryFromLine(body as FromLineBody, signal),
    enabled: Boolean(body),
    staleTime: Infinity,
    retry: false,
    placeholderData: keepPreviousData,
  });
}

export function useParseCoordinates(text: string) {
  const trimmed = text.trim();
  return useQuery({
    queryKey: queryKeys.parseCoordinates(trimmed),
    queryFn: ({ signal }) => client.parseCoordinates({ text: trimmed }, signal),
    enabled: trimmed.length > 0,
    staleTime: Infinity,
    retry: false,
  });
}

// ─── v0.2 · imports ──────────────────────────────────────────────────────────

export function useImports(plotId?: string | null, enabled = true) {
  return useQuery<ImportList>({
    queryKey: queryKeys.imports(plotId),
    queryFn: () => client.listImports(plotId ?? undefined),
    enabled,
    staleTime: MINUTE,
    retry: false,
  });
}

/** Full record including the `preview` FeatureCollection (tree tops, crowns or boundary). */
export function useImportRecord(importId: string | null | undefined) {
  return useQuery<ImportRecord>({
    queryKey: queryKeys.importRecord(importId ?? ''),
    queryFn: () => client.getImport(importId as string),
    enabled: Boolean(importId),
    staleTime: Infinity,
    retry: false,
  });
}

export function useUploadImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, options }: { file: File; options?: ImportUploadOptions }) => client.uploadImport(file, options),
    onSuccess: (record) => {
      queryClient.setQueryData(queryKeys.importRecord(record.import_id), record);
      void queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
  });
}

export function useDeleteImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (importId: string) => client.deleteImport(importId),
    onSuccess: (_, importId) => {
      queryClient.removeQueries({ queryKey: queryKeys.importRecord(importId) });
      void queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
  });
}

// ─── v0.2 · detection and imagery ────────────────────────────────────────────

/** Latest "AI detected" tree cover for a plot (`GET …/detections`, else `POST …/detect`). */
export function useDetection(plotId: string | null | undefined, enabled = true) {
  return useQuery({
    queryKey: queryKeys.detection(plotId ?? ''),
    queryFn: () => client.latestOrDetect(plotId as string),
    enabled: Boolean(plotId) && enabled,
    staleTime: Infinity,
    retry: false,
  });
}

export function useImageryProviders(country?: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.imagery(country),
    queryFn: () => client.imageryProviders(country),
    enabled,
    staleTime: Infinity,
    retry: false,
  });
}
