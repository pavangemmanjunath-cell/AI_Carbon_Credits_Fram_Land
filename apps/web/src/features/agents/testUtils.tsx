/**
 * Helpers for this feature's tests only: a render wrapper with the app's providers and a tiny
 * `fetch` router, so page tests exercise the real API module against canned responses.
 */
import type { ReactElement } from 'react';
import { render, type RenderResult } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { vi } from 'vitest';

export function renderWithProviders(ui: ReactElement, route = '/app/agents'): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 1, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

export function jsonResponse(body: unknown, status = 200, contentType = 'application/json') {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': contentType } });
}

/** An RFC 7807 problem response, as the API sends for every error. */
export function problemResponse(status: number, title: string, detail: string) {
  return jsonResponse(
    { type: 'about:blank', title, status, detail },
    status,
    'application/problem+json',
  );
}

export interface MockCall {
  method: string;
  /** Path below the API base, e.g. `/agents/runs`. */
  path: string;
  search: string;
  body: unknown;
}

export type MockRoute = (call: MockCall) => Response | Promise<Response>;

/**
 * Replaces `fetch` with a router keyed by `"METHOD /path"`. A route that throws simulates an API
 * that is not running. Unknown routes answer 404 so a missing mock is obvious in the test.
 */
export function mockApi(routes: Record<string, MockRoute>) {
  const calls: MockCall[] = [];
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const href = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(href);
    const method = (init?.method ?? 'GET').toUpperCase();
    const call: MockCall = {
      method,
      path: url.pathname.replace(/^\/api\/v1/, ''),
      search: url.search,
      body: typeof init?.body === 'string' ? (JSON.parse(init.body) as unknown) : undefined,
    };
    calls.push(call);
    const route = routes[`${method} ${call.path}`];
    if (!route) {
      return Promise.resolve(
        problemResponse(404, 'Not found', `No mock for ${method} ${call.path}`),
      );
    }
    try {
      return Promise.resolve(route(call));
    } catch (error) {
      return Promise.reject(error);
    }
  });
  return { calls, spy };
}
