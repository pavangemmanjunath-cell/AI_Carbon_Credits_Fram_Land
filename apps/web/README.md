# Web app (apps/web)

The React front end of CarbonCreditBuy: a map workspace where a landowner marks their land (draw a boundary, draw a
tree line, drop a pin and type the size, type coordinates or import a file), adds trees, sees vegetation condition and a
carbon-removal **scenario range**, and reads which programmes might be relevant. Around the workspace sit a
Trimble-style left navigation (My land, Data, AI agents, Tree age, Simulation, Reports, Settings), an **Import data**
dialog reachable from the header, the Data page (land plots and imported files), the AI agents page, the tree-age
page, the results and report pages, and the simulation page. The app is flat 2D: there is no WebGL scene other than the
MapLibre map.

The UI renders; it does not calculate. Carbon numbers, programme statuses and readiness scores come from the API, and
policy rules live in `config/policies/` (CLAUDE.md principle 2). When the API cannot be reached, the pages that only
need existing data fall back to static demo fixtures and say so in a banner (see
[Offline behaviour](#offline-behaviour)).

## Stack

React 19, Vite 6, TypeScript, Tailwind CSS 4, MapLibre GL JS with PMTiles, terra-draw (boundary and tree-line
drawing), @turf/turf, recharts, TanStack Query, Zustand, react-router 7 and i18next; fonts (IBM Plex, Space Grotesk)
are self-hosted through `@fontsource`. Node 22 or newer.

The map is MapLibre in flat 2D: a vector basemap (PMTiles or a style URL), an optional raster imagery layer, and plain
GeoJSON layers for NDVI cells, detected tree cover, plots and imported trees. The vegetation cube arrives as JSON from
the API and is drawn as a MapLibre `fill` layer; there is no in-browser database
([ADR 0002](../../docs/architecture/adr/0002-json-cube-no-duckdb.md)). The 3D and 4D views of v0.1 and the libraries
behind them were removed in v0.2 ([CHANGELOG](../../CHANGELOG.md)).

## Run it

```bash
make install-web              # npm install in apps/web
make web                      # Vite dev server, http://localhost:5173
make api                      # in a second terminal, or use: make dev
```

Vite reads `VITE_*` variables from the **repository root** `.env` (see `envDir` in `vite.config.ts`), so the API and
the web app share one file. Copy [`.env.example`](../../.env.example) to `.env` at the root.

## Scripts (run inside `apps/web`)

| Command                                  | What it does                                          |
| ---------------------------------------- | ----------------------------------------------------- |
| `npm run dev`                            | Dev server with hot reload (port 5173)                |
| `npm run build`                          | Production build into `dist/`                         |
| `npm run preview`                        | Serve the build on port 4173                          |
| `npm run typecheck`                      | `tsc` for the app and node configs                    |
| `npm run lint`, `npm run lint:fix`       | ESLint                                                |
| `npm run format`, `npm run format:check` | Prettier                                              |
| `npm run test -- --run`                  | Vitest once (without `--run` it starts in watch mode) |
| `npm run test:coverage`                  | Vitest with coverage                                  |
| `npm run test:e2e`                       | Playwright smoke tests against the preview build      |
| `npm run fixtures:demo`                  | Refresh `public/demo/` from `data/sample/responses/`  |

From the repository root, `make test-web` runs the typecheck and the unit tests, `make lint` includes ESLint,
`make samples` regenerates the sample responses and then the demo fixtures, and `make screenshots` captures the
documentation screenshots (see [Screenshots](#screenshots)).

## Configuration (build-time `VITE_*` variables)

Every `VITE_*` value is compiled into the bundle and is therefore **public**; never put a secret in one.

| Variable                                                 | Purpose                                                                                                                                                                                                                                                |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `VITE_API_BASE_URL`                                      | API root, for example `http://localhost:8000/api/v1`                                                                                                                                                                                                   |
| `VITE_BASEMAP_STYLE_URL`                                 | MapLibre style JSON; the default is the MapLibre demo style, for development only                                                                                                                                                                      |
| `VITE_BASEMAP_PMTILES_URL`                               | Your own Protomaps PMTiles basemap (ODbL attribution required); it takes precedence over the style URL                                                                                                                                                 |
| `VITE_SATELLITE_TILES_URL`, `VITE_SATELLITE_ATTRIBUTION` | Optional override for the Satellite view and its mandatory attribution. Without it the app uses the provider recommended by `GET /imagery/providers`; respect the provider's licence                                                                   |
| `VITE_DEFAULT_COUNTRY`, `VITE_DEFAULT_LANGUAGE`          | Initial country (`IN`, `US`, `EU`) and language                                                                                                                                                                                                        |
| `VITE_API_KEY`                                           | Optional `X-API-Key` header value for an API that sets `ATLAS_API_KEYS`; read by `services/api.ts`, not listed in `.env.example`. It sits in the bundle, so anyone who loads the app can read it: it identifies the deployment, it does not protect it |

`VITE_TERRAIN_TILES_URL` (still passed by `infra/docker/Dockerfile.web`) is no longer read: the terrain views went with
the 3D scenes.

The Satellite view needs either the API (`GET /imagery/providers`) or `VITE_SATELLITE_TILES_URL`; otherwise the switch is
disabled with a tooltip. Deployments behind `infra/docker/nginx.conf` must add the imagery tile origins to
`ATLAS_EXTRA_IMG_SRC` and `ATLAS_EXTRA_CONNECT_SRC`. The providers, licences and key handling are described in
[`integrations/imagery/`](../../integrations/imagery/README.md).

## Layout

```text
src/
  App.tsx, main.tsx     routes (lazy-loaded pages) and bootstrap
  components/           layout (AppShell, SideNav + navItems, Stepper), map (MapView, land input
                        toolbar/panels/welcome, attribution bar, layers, drawing), import (ImportDialog),
                        ui (Button, Dialog, Field, ...), brand
  features/             workspace, data, results, simulate, reports, report, species, settings, landing,
                        agents, tree-age
    <feature>/logic/    pure functions with their unit tests (no React)
    <feature>/i18n.ts   agents and tree-age register their own strings (agentsPage.*, treeAge.*)
  services/             api.ts (the only module that knows URLs), client.ts (demo fallback),
                        queries.ts (TanStack Query hooks), demoFallback.ts,
                        agentsApi.ts and treeAgeApi.ts (typed calls and hooks, no offline fallback)
  store/uiStore.ts      Zustand store; persists language, units, country, layers, Map or Satellite view,
                        imagery choice per country, processing mode and the selected plot id
  config/               mapEnv.ts (VITE_*), regions.ts and regions.json
  i18n/                 en, hi, kn, de, fr, es JSON files and the i18next setup
  lib/                  formatting, geometry, NDVI classes and cube cells, coordinates parser, offline
                        geometry helpers, land input, imports, imagery, detection, attribution, scale bar,
                        errors, downloads
  hooks/, styles/       small hooks; Tailwind tokens and global CSS
  types/api.ts          types mirroring docs/architecture/api-contract.md
  test/                 Vitest setup, render helper and shared fixtures
public/demo/            static API fixtures used when the API is unreachable (21 files)
e2e/                    Playwright smoke tests
scripts/                make-demo-fixtures.mjs
```

The logic/UI split is deliberate and follows CLAUDE.md principle 2: a `logic/` module takes plain data and returns plain
data (view models, sorting, grouping, URL parsing, request bodies), has a `.test.ts` next to it and imports no React.
Components arrange what the logic returns. The numbers always come from the API.

Routes: `/` landing; `/app` workspace (My land); `/app/data` (`?tab=files` for imported files); `/app/agents`;
`/app/tree-age`; `/app/simulate`; `/app/reports`; `/app/plots/:id/results` and `/report`; `/app/species` (linked from
Settings); `/app/settings`. `/app/plots` redirects to `/app/data`, and the retired `/app/cube` and
`/app/plots/:id/cube` redirect to the results page.

## Behaviour worth knowing

- **Privacy.** Plot polygons are held by the API; the browser stores only settings and the selected plot id in
  `localStorage` (key `carboncreditbuy-ui`, store version 2, with a migration from v1). The "Share private link"
  button copies the page URL; it does not create a token. The results JSON export removes the geometry and the exact
  centroid. The explain request is built from derived indicators in `features/results/logic/resultsLogic.ts` and
  contains no location.
- **Auto-save.** A new plot gets a default tree form that is saved after a 600 ms pause as a new inventory version, so
  the first estimate appears without pressing a button. A plot created from a tree line starts with the suggested tree
  count.
- **Mark your land.** Boundary and Tree line use terra-draw; Pin + size and Coordinates call
  `POST /geometry/from-point`, `/from-line` and `/parse-coordinates`. Pin and tree-line plots are saved with
  `boundary_quality: "approximate"` and the details panel suggests drawing the exact edges.
- **Import data.** `POST /imports`, one file at a time with upload progress. Boundaries can become plots
  (`source: "import"`) and detected trees a `model-estimated` inventory. The Data page lists imported files, and "View
  on map" shows an import's preview.
- **Map.** A "Map | Satellite" switch (provider from `GET /imagery/providers`, chosen per country in Settings, over-zoomed
  beyond its `max_zoom`), NDVI cells for the selected year, "Tree cover (AI detected)" patches with their confidence,
  imported tree tops and crowns, and the app's own attribution bar with a metric scale bar. If the imagery tiles keep
  failing, the attribution bar says so and the basemap shows underneath; if the basemap style cannot be loaded at all,
  the plot and the data layers are drawn on a plain ground colour.
- **AI agents.** The page lists the plots, offers the three plans and a question box (`POST /agents/ask`), and shows
  the run as a transcript: who said what, which tools ran, which guardrails passed. It reads from `GET /agents`
  whether a language model is on and says so. It sends a plot id and a question, never coordinates. See the
  [agents guide](../../docs/agents/README.md).
- **Tree age.** A form for country, state or region, setting, species, age, tree count and optionally girth and height;
  the state lives in the URL so a result can be shared. It shows the carbon the trees hold now, the carbon curve over
  their age, the credit outlook and the rules that apply at that age.
- **Languages.** English, Hindi, Kannada, German, French and Spanish. Add keys to `en.json` first (or to the feature's
  `i18n.ts`, where a type check fails if a language lacks a key); identifiers, units and attribution strings are never
  translated.
- **Accessibility.** Form controls have labels, live regions announce saving and updating, the map tools have visible
  labels, and the Data page lists every plot and imported file in a table so nothing depends on the map alone.

## Offline behaviour

`services/client.ts` wraps the calls of the original app: on a connectivity failure it serves `public/demo/*.json` and
shows "API offline - showing demo data". Genuine API errors (404, 422 and so on) are never hidden. The fallback never
computes a number; a plot created offline gets the demo estimate back with a note saying so.

| Area                                                                               | When the API is unreachable                                                                          |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Plots, analysis, trees, estimates, policy, market, simulation, explanation, report | Demo fixtures, with the banner                                                                       |
| Pin + size, tree line, typed coordinates                                           | Browser calculations, labelled as such                                                               |
| Imports, tree-cover detection, imagery providers                                   | A message that the API is needed; the Satellite switch is unavailable                                |
| AI agents, tree age                                                                | A message that the API is needed: the transcript, the rules and the numbers exist only on the server |

## Tests

```bash
cd apps/web
npm run typecheck && npm run test -- --run     # what CI runs
npm run build && npm run test:e2e              # smoke tests (needs Playwright browsers)
```

Vitest (jsdom, setup in `src/test/setup.ts`, 45 test files with about 460 tests) covers the pure logic: units and
formatting, the workspace model, results logic, simulation parameters and stand illustration, NDVI cells, coordinates,
offline geometry, land input, imports, imagery, detection, attribution, the scale bar, navigation, the API client and
the UI store with its migration, plus the agents and tree-age logic (normalising API responses, URL state, request
bodies, translations). Component tests cover `PlotDetailsPanel`, `ResultCards`, `ImportDialog`, the land-input panels,
`DataPage`, and the parts of the agents and tree-age pages.

Playwright (`playwright.config.ts`, Chromium) runs four smoke scenarios against `npm run preview`: the landing page
opens the workspace, the workspace falls back to demo data when the API is offline, the header opens the Import dialog,
and old 4D cube links redirect to the results page. `PLAYWRIGHT_BASE_URL` points it at another server. Install the
browser once with `npx playwright install chromium`. The suite is described in [`tests/e2e/`](../../tests/e2e/README.md).

## Screenshots

`make screenshots` (that is `node scripts/capture_screenshots.mjs`) drives the built app with Playwright and writes the
PNG files in [`docs/images/screenshots/`](../../docs/images/README.md) that the user guide uses. It needs the API in
demo mode on port 8000 and the preview build on port 4173 (`npm run build && npm run preview`). The Satellite shot is
captured only with `CAPTURE_SATELLITE=1`, because it needs network access to the imagery hosts.

## Design notes

- Put calculations in the API or an engine, never in a component. A component may format, filter and arrange.
- New text goes through i18next keys; never hard-code a user-facing string.
- A new endpoint needs an entry in `services/api.ts` (or its own module like `agentsApi.ts`), a type in `types/api.ts`,
  and a hook in `services/queries.ts`. If the page should work offline, add a demo fixture in `public/demo/` through
  `npm run fixtures:demo`; otherwise say clearly that the API is needed.
- The Content-Security-Policy in [`infra/docker/nginx.conf`](../../infra/docker/nginx.conf) is strict (no
  `unsafe-eval`); a dependency that needs it is not acceptable.

## Links

- [User guide](../../docs/user-guide/README.md) for the screens and labels
- [Mapping architecture](../../docs/architecture/mapping-architecture.md)
- [Map licences](../../docs/licensing/MAP_LICENSES.md)
- [API README](../api/README.md)
