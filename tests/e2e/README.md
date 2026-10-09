# End-to-end tests (Playwright)

Browser tests drive the built web app in Chromium. **The suite lives in the web app, not in this directory:** the
specs are in [`apps/web/e2e/`](../../apps/web/e2e/) and the configuration is
[`apps/web/playwright.config.ts`](../../apps/web/playwright.config.ts). This directory holds only this note, so that
the browser tests are described next to the other suites in [`tests/`](../README.md).

The suite is small on purpose: one file with four smoke scenarios. It is **not part of CI** (no workflow runs it), so
run it yourself before a change to routing, the header or the offline fallback.

## What exists

`apps/web/e2e/smoke.spec.ts`:

| Scenario | What it checks |
| --- | --- |
| The landing page renders the core message and opens the workspace | `/` has a level-1 heading containing "Understand your land" and the sentence "never issued carbon credits"; the first "Open workspace" link leads to `/app`, which shows the heading "Selected plot details" |
| The workspace falls back to demo data when the API is offline | Every request to `/api/v1/` is aborted. `/app` shows "API offline", the "Demo mango orchard" plot, the "See carbon potential" link and the "Mark your land" toolbar |
| The header Import button opens the Import data dialog from any page | From `/app/data`, the "Import data" button opens a dialog with the heading "Import data" and the sentence "Only the results are kept — the file itself is not stored." |
| Old 4D cube links land on the results page | `/app/plots/PLT-DEMOIN/cube`, a route of version 0.1, ends at `/app/plots/PLT-DEMOIN/results` |

The configuration starts only the web app (`npm run preview` on `127.0.0.1:4173`). It does not start the API, so the
app runs on its built-in demo fallback (`apps/web/public/demo/`), with or without an API on port 8000. The map
requests its basemap style from the network (`VITE_BASEMAP_STYLE_URL`, by default MapLibre's demo tiles); no scenario
asserts anything about map tiles.

## Run

```bash
cd apps/web
npm ci
npx playwright install chromium     # once
npm run build                       # the tests run against the production build (dist/)
npm run test:e2e                    # headless, all scenarios
npx playwright test --ui            # interactive
```

- `PLAYWRIGHT_BASE_URL` changes the address the tests open. The configuration still starts the preview server on port
  4173 unless one is already running (it reuses a running server outside CI).
- A failed scenario keeps a trace in `apps/web/test-results/`; open it with `npx playwright show-trace <trace.zip>`.
- The reporter is `list` locally and `github` in CI, with one retry in CI only, so there is no HTML report.

## What is not covered

No scenario draws a plot, runs the carbon or tree-age pages, uses the AI agents, switches the satellite view or the
language, generates a report, or checks accessibility; none starts the API. The most valuable missing test is a privacy
journey that watches the network traffic and fails when a request to a third-party origin carries coordinates or when
the `/explain` payload has a location key ([privacy design](../../docs/privacy/privacy-design.md)). Running the browser
suite in CI is listed in [roadmap ideas](../../docs/community/roadmap-ideas.md). Until then, the unit tests in
`apps/web/src/` and the API tests in `apps/api/tests/` carry the behaviour.

## Rules

- Use the synthetic demo plot (`PLT-DEMOIN`) and the farms in [`examples/`](../../examples/README.md). Never record a
  real plot.
- Do not widen retries to hide a flaky test. Quarantine it with `test.fixme` and a link to the issue.
- Screenshots for the documentation are not written by the test run. `make screenshots` runs
  `scripts/capture_screenshots.mjs`, which needs the API in demo mode on port 8000 and the built web app on port 4173
  ([screenshots guide](../../docs/images/README.md)).

## Links

- [Tests overview](../README.md)
- [Testing guide for developers](../../docs/developer-guide/testing.md)
- [Web app README](../../apps/web/README.md)
