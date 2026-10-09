/**
 * Typed calls and TanStack hooks for the agentic AI framework (tag `agents` in
 * docs/architecture/api-contract.md). Built on `request` from ./api, so errors arrive as
 * `ApiError` (RFC 7807) or `NetworkError`. There is deliberately no offline demo fallback:
 * agents run on the server, and the page tells people to start the API instead.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { normalizeRun, normalizeRunList } from '@/features/agents/logic/normalizeRun';
import type {
  AgentAskBody,
  AgentCatalog,
  AgentRun,
  AgentRunBody,
  AgentRunListItem,
  RawAgentRun,
} from '@/features/agents/types';
import { ApiError, request } from './api';

const MINUTE = 60_000;
/** Runs can take a moment when an optional language model rewords the text. */
const RUN_TIMEOUT_MS = 60_000;

/** Retry once, and only when the failure may be temporary (a 4xx means the request was wrong). */
function retryTransient(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 1;
}

export const agentsApi = {
  catalog: (signal?: AbortSignal) => request<AgentCatalog>('/agents', { signal }),

  run: (plotId: string, body: AgentRunBody) =>
    request<RawAgentRun>(`/plots/${encodeURIComponent(plotId)}/agents/run`, {
      method: 'POST',
      body,
      timeoutMs: RUN_TIMEOUT_MS,
    }).then(normalizeRun),

  ask: (body: AgentAskBody) =>
    request<RawAgentRun>('/agents/ask', { method: 'POST', body, timeoutMs: RUN_TIMEOUT_MS }).then(
      normalizeRun,
    ),

  getRun: (runId: string, signal?: AbortSignal) =>
    request<RawAgentRun>(`/agents/runs/${encodeURIComponent(runId)}`, { signal }).then(
      normalizeRun,
    ),

  listRuns: (plotId: string, signal?: AbortSignal) =>
    request<unknown>('/agents/runs', { params: { plot_id: plotId }, signal }).then(
      normalizeRunList,
    ),
};

export const agentKeys = {
  all: ['agents'] as const,
  catalog: ['agents', 'catalog'] as const,
  runs: (plotId: string) => ['agents', 'runs', plotId] as const,
  run: (runId: string) => ['agents', 'run', runId] as const,
};

export function useAgentCatalog() {
  return useQuery({
    queryKey: agentKeys.catalog,
    queryFn: ({ signal }) => agentsApi.catalog(signal),
    staleTime: 30 * MINUTE,
    retry: retryTransient,
  });
}

/** Run summaries for a plot, as returned by `GET /agents/runs?plot_id=`. */
export function useAgentRuns(plotId: string | null | undefined) {
  return useQuery<AgentRunListItem[]>({
    queryKey: agentKeys.runs(plotId ?? ''),
    queryFn: ({ signal }) => agentsApi.listRuns(plotId as string, signal),
    enabled: Boolean(plotId),
    staleTime: 30_000,
    retry: retryTransient,
  });
}

/** A stored run never changes, so it is cached for good. */
export function useAgentRun(runId: string | null | undefined) {
  return useQuery<AgentRun>({
    queryKey: agentKeys.run(runId ?? ''),
    queryFn: ({ signal }) => agentsApi.getRun(runId as string, signal),
    enabled: Boolean(runId),
    staleTime: Infinity,
    retry: retryTransient,
  });
}

/** `POST /plots/{plot_id}/agents/run`. The new run is cached so it shows without another request. */
export function useRunAgents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ plotId, body }: { plotId: string; body: AgentRunBody }) =>
      agentsApi.run(plotId, body),
    onSuccess: (run, { plotId }) => {
      queryClient.setQueryData(agentKeys.run(run.run_id), run);
      void queryClient.invalidateQueries({ queryKey: agentKeys.runs(plotId) });
    },
  });
}

/** `POST /agents/ask`: the answer is a run, so it is cached the same way. */
export function useAskAgents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentAskBody) => agentsApi.ask(body),
    onSuccess: (run, body) => {
      queryClient.setQueryData(agentKeys.run(run.run_id), run);
      void queryClient.invalidateQueries({ queryKey: agentKeys.runs(body.plot_id) });
    },
  });
}
