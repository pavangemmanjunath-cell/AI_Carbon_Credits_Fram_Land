# ADR-0002: The 4D vegetation cube is plain JSON filtered in the browser; DuckDB-WASM deferred

- **Status:** accepted
- **Date:** 2026-10-04
- **Deciders:** project lead, front-end engineer, back-end engineer

## Context

The 4D view shows how a vegetation index over a plot changes through time:
a grid of cells (space) stacked along months (time). Users scrub time,
apply thresholds, compare two dates and read per-time statistics. The
early design proposed DuckDB-WASM in the browser so that these operations
could be expressed as SQL over a Parquet file, which would scale to large
cubes and allow ad-hoc queries.

Measuring the actual data changed the picture. The API serves a cube of
12 × 12 cells × 36 months = 5,184 values (`GET /plots/{id}/cube`,
[../api-contract.md](../api-contract.md)): a few tens of kilobytes of JSON,
less after gzip. Plots are capped at 10 000 ha and the grid stays 12 × 12
regardless of size, so the payload does not grow with the plot. Every
interaction the UI needs is a single pass over an array.

DuckDB-WASM, by contrast, costs roughly 30–40 MB of WebAssembly and
JavaScript to download on first use, requires `script-src` allowances for
WebAssembly in the Content Security Policy, needs cross-origin isolation
headers for its threaded build, complicates the offline/PWA path, and adds
a second query language to a code base whose rule is "no business logic
in UI components" ([CLAUDE.md](../../../CLAUDE.md)).

## Decision

The cube travels as plain JSON in the shape defined by the API contract
(`grid`, `times`, `mask`, `values`, `stats_per_time`, `provenance`) and
is filtered, thresholded and aggregated in the browser with typed arrays.
DuckDB-WASM is **not** part of the stack. The cube module in `apps/web`
exposes pure functions (`filterByThreshold`, `sliceTime`, `diffTimes`,
`meanPerTime`) that are unit-tested in Vitest and shared by the 2D grid
layer and the React Three Fiber scene.

## Consequences

Positive:

- No multi-megabyte runtime; the cube view loads in the same time as any
  other route and works offline once the JSON is cached.
- The CSP stays strict (`script-src 'self'`, no `wasm-unsafe-eval`).
- One source of truth for cube semantics (the API), one place for display
  logic (pure functions), both testable without a browser.
- Demo mode and tests use the same JSON fixtures.

Negative:

- Ad-hoc analytical queries across many plots or many years are not
  possible in the browser; they belong in the API or in research
  notebooks.
- A future product need for finer grids (for example 48 × 48 × 120 ≈
  276k cells) would push JSON to several megabytes; at that point a binary
  encoding (typed-array buffers or Zarr chunks) is the next step, not
  necessarily a database.

## Alternatives considered

- **DuckDB-WASM over Parquet.** Deferred, for the reasons above. It
  remains the right tool if the cube ever becomes a multi-plot, multi-year
  analytical dataset that users query freely.
- **Server-side slicing endpoints** (`/cube?time=…&threshold=…`).
  Rejected: round trips for every slider move, and more endpoints to
  maintain for no gain at this size.
- **Zarr in the browser.** Attractive for large arrays and consistent with
  the export format, but adds a chunk-fetching layer that 5k cells do not
  justify.

## Revisit when

A documented user need requires cubes above roughly 50k cells per plot,
multi-plot analytics in the browser, or indices beyond NDVI/NDMI at
10 m native resolution without aggregation. The revisit should start by
measuring payload size and interaction latency, as this decision did.
