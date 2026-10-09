# ADR-0001: Vite + React single-page app instead of Next.js

- **Status:** accepted
- **Date:** 2026-10-04
- **Deciders:** project lead, front-end engineer

## Context

The web application is a map-centric tool: a WebGL basemap (MapLibre GL
JS), polygon drawing, deck.gl overlays, two React Three Fiber scenes and a
client-side-filtered vegetation cube. Almost every view depends on browser
APIs (`WebGL`, `fetch` with Range requests, `Worker`) and on client state;
there is no content that benefits from server rendering, and search-engine
indexing of a farmer's private workspace is undesirable. The back end is a
separate FastAPI service with a documented contract, and deployments must
work as static files behind nginx or any object store, including offline
workshop set-ups and a possible future PWA.

Next.js was considered because of its ecosystem, routing and image
handling. React Router with Vite was considered as the lightweight
alternative.

## Decision

Build `apps/web` as a Vite + React 19 + TypeScript single-page
application. Routing uses a client router; data fetching uses TanStack
Query against `/api/v1`; global UI state lives in Zustand; translations in
i18next. The production artifact is a static `dist/` served by nginx with
an SPA fallback ([../../../infra/docker/nginx.conf](../../../infra/docker/nginx.conf)).

## Consequences

Positive:

- A static build deploys anywhere (nginx, S3 + CDN, GitHub Pages for
  demos) with no Node runtime in production and a smaller attack surface;
  the CSP can be strict.
- MapLibre, deck.gl and three.js, which touch `window` and WebGL at import
  time, need no `dynamic(..., { ssr: false })` workarounds or hydration
  care.
- Vite's dev server starts in well under a second and its code splitting
  handles the heavy 3D routes cleanly.
- The API contract remains the only coupling between front and back end;
  there is no second server with its own routes and secrets.

Negative:

- No server-side rendering: the first paint shows an app shell until the
  bundle loads. Mitigated by code splitting and the performance budget in
  [../mapping-architecture.md](../mapping-architecture.md).
- No built-in server functions; anything that needs a secret (for example
  a future authenticated share link) goes through the FastAPI service.
- Public marketing pages, if any, live outside this app (a static site),
  so that this app stays a tool.

## Alternatives considered

- **Next.js (App Router).** Rejected for this project because the
  benefits (SSR, server components, image optimization) do not apply to a
  WebGL tool, while the costs (Node runtime in production, hydration
  constraints with map libraries, duplicated routing between Next and
  FastAPI) are real.
- **SvelteKit or SolidStart.** Smaller bundles, but the React Three Fiber
  and deck.gl React bindings, TanStack Query and the contributor pool are
  stronger in React.

## Revisit when

A requirement appears for indexable public pages generated from data (for
example public, consented project showcases), or when a PWA with offline
caching needs a service worker strategy that Vite's PWA plugin cannot
provide.
