/**
 * Helpers for this feature's tests only: a render wrapper with the app's providers, a tiny `fetch`
 * router so page tests exercise the real API module against canned responses, and canned
 * responses for the three endpoints the page uses.
 */
import type { ReactElement } from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createMemoryRouter } from 'react-router';
import { vi } from 'vitest';
import { assessmentFixture, rulesInfoFixture, speciesFixture, usSpeciesFixture } from './fixtures';
import type { TreeAgeRequestBody } from './types';

/**
 * Renders with a fresh QueryClient (no retries to wait for) and a memory router. The router is
 * returned so a test can read the address the page wrote (`router.state.location.search`).
 */
export function renderWithProviders(ui: ReactElement, route = '/app/tree-age') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 1, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
  const router = createMemoryRouter([{ path: '*', element: ui }], { initialEntries: [route] });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...result, router };
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
  /** Path below the API base, e.g. `/tree-age/assess`. */
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
    const url = new URL(href, 'http://localhost');
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

/**
 * Puts the real `fetch` back. Tests that draw the chart use this instead of
 * `vi.restoreAllMocks()`, which would also wipe the `matchMedia` stub the chart relies on.
 */
export function restoreFetch() {
  if (vi.isMockFunction(globalThis.fetch)) vi.mocked(globalThis.fetch).mockRestore();
}

/** The bodies of every `POST /tree-age/assess` so far, in order. */
export function assessBodies(calls: MockCall[]): TreeAgeRequestBody[] {
  return calls
    .filter((call) => call.method === 'POST' && call.path === '/tree-age/assess')
    .map((call) => call.body as TreeAgeRequestBody);
}

/** What the API would answer for this request: the fixture, with the person's own inputs echoed. */
export function assessmentFor(body: TreeAgeRequestBody) {
  return {
    ...assessmentFixture({ age: body.age_years, trees: body.tree_count }),
    inputs: {
      country: body.country,
      region: body.country,
      subdivision: body.subdivision,
      setting: body.setting,
      species_id: body.species_id,
      age_years: body.age_years,
      tree_count: body.tree_count,
      girth_cm: body.girth_cm,
    },
  };
}

/** The three endpoints the page calls, answering like a healthy API. */
export function treeAgeRoutes(
  overrides: Record<string, MockRoute> = {},
): Record<string, MockRoute> {
  return {
    'GET /species': ({ search }) => {
      const country = new URLSearchParams(search).get('country');
      return jsonResponse(country === 'US' ? usSpeciesFixture : speciesFixture);
    },
    'GET /tree-age/rules': ({ search }) => {
      const country = new URLSearchParams(search).get('country') ?? 'IN';
      if (country === 'IN') return jsonResponse(rulesInfoFixture);
      if (country === 'US') {
        return jsonResponse({
          ...rulesInfoFixture,
          subdivision_label: 'State',
          subdivisions: [
            { code: 'US-OR', name: 'Oregon', type: 'state' },
            { code: 'US-CA', name: 'California', type: 'state' },
          ],
        });
      }
      return jsonResponse({ ...rulesInfoFixture, subdivision_label: null, subdivisions: [] });
    },
    'POST /tree-age/assess': ({ body }) => jsonResponse(assessmentFor(body as TreeAgeRequestBody)),
    ...overrides,
  };
}
