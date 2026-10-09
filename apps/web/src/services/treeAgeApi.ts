/**
 * Typed calls and TanStack hooks for the tree-age endpoints (tag `tree-age` in
 * docs/architecture/api-contract.md). Built on `request` from ./api, so errors arrive as
 * `ApiError` (RFC 7807) or `NetworkError`. There is deliberately no offline demo fallback: the
 * numbers and the rules come from the server, and the page tells people to start the API instead.
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { requestKey } from '@/features/tree-age/logic/treeAgeLogic';
import {
  normalizeAssessment,
  normalizeRulesInfo,
} from '@/features/tree-age/logic/normalizeAssessment';
import type {
  RawAssessment,
  RawRulesInfo,
  TreeAgeAssessment,
  TreeAgeRequestBody,
  TreeAgeRulesInfo,
} from '@/features/tree-age/types';
import { ApiError, request } from './api';

const MINUTE = 60_000;

/** Retry once, and only when the failure may be temporary (a 4xx means the request was wrong). */
function retryTransient(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 1;
}

export const treeAgeApi = {
  /** Rules, age classes and (for India, the US and Germany) the list of states or regions. */
  rules: (country?: string, subdivision?: string | null, signal?: AbortSignal) =>
    request<RawRulesInfo>('/tree-age/rules', {
      params: { country, subdivision: subdivision ?? undefined },
      signal,
    }).then(normalizeRulesInfo),

  assess: (body: TreeAgeRequestBody, signal?: AbortSignal) =>
    request<RawAssessment>('/tree-age/assess', { method: 'POST', body, signal }).then(
      normalizeAssessment,
    ),
};

export const treeAgeKeys = {
  all: ['tree-age'] as const,
  rules: (country: string) => ['tree-age', 'rules', country] as const,
  assess: (key: string | null) => ['tree-age', 'assess', key] as const,
};

/** The list of states or regions for a country (and the age classes). Rarely changes. */
export function useTreeAgeRules(country: string) {
  return useQuery<TreeAgeRulesInfo>({
    queryKey: treeAgeKeys.rules(country),
    queryFn: ({ signal }) => treeAgeApi.rules(country, null, signal),
    staleTime: 30 * MINUTE,
    retry: retryTransient,
  });
}

/**
 * `POST /tree-age/assess` as a query: the same inputs always give the same answer, so it is
 * cached by the request itself. The previous answer stays on screen while a new one loads.
 */
export function useTreeAgeAssessment(body: TreeAgeRequestBody | null) {
  return useQuery<TreeAgeAssessment>({
    queryKey: treeAgeKeys.assess(requestKey(body)),
    queryFn: ({ signal }) => treeAgeApi.assess(body as TreeAgeRequestBody, signal),
    enabled: body !== null,
    placeholderData: keepPreviousData,
    staleTime: 5 * MINUTE,
    retry: retryTransient,
  });
}
