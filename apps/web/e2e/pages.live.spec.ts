/// <reference types="node" />  // runs in Node under Playwright
import { expect, test, type Page } from '@playwright/test';

/**
 * Every page against a running API (demo mode is enough).
 *
 * Unlike smoke.spec.ts this does not mock the API: it needs the API at
 * E2E_API_URL (default http://localhost:8000/api/v1), and the preview build
 * must have been built with the same VITE_API_BASE_URL. The whole file is
 * skipped when the API does not answer.
 *
 *   E2E_API_URL=http://localhost:8001/api/v1 npx playwright test pages.live
 */
const API = (process.env.E2E_API_URL ?? 'http://localhost:8000/api/v1').replace(/\/+$/, '');
const PLOT = 'PLT-DEMOIN';

const PAGES: { name: string; path: string }[] = [
  { name: 'landing', path: '/' },
  { name: 'workspace', path: '/app' },
  { name: 'data', path: '/app/data' },
  { name: 'agents', path: `/app/agents?plot=${PLOT}` },
  { name: 'tree-age', path: '/app/tree-age' },
  { name: 'simulate', path: '/app/simulate' },
  { name: 'reports', path: '/app/reports' },
  { name: 'results', path: `/app/plots/${PLOT}/results` },
  { name: 'report', path: `/app/plots/${PLOT}/report` },
  { name: 'species', path: '/app/species' },
  { name: 'settings', path: '/app/settings' },
];

// Basemap and imagery tiles come from third-party hosts that may be offline in
// tests; their failures are not page errors. The report preview is a sandboxed
// iframe without allow-scripts (the report HTML has no scripts); Chromium logs a
// "Blocked script execution in 'about:srcdoc'" line when Playwright's own
// screenshot helper is refused there — the sandbox working, not a page error.
const IGNORED =
  /demotiles\.maplibre\.org|tile|pmtiles|imagery|favicon|ERR_INTERNET_DISCONNECTED|ERR_NAME_NOT_RESOLVED|Blocked script execution in 'about:srcdoc'/i;

function watch(page: Page) {
  const problems: string[] = [];
  page.on('pageerror', (err) => problems.push(`page error: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !IGNORED.test(msg.text()) && !IGNORED.test(msg.location().url)) {
      problems.push(`console error: ${msg.text()}`);
    }
  });
  page.on('response', (res) => {
    if (res.url().startsWith(API) && res.status() >= 500) {
      problems.push(`API ${res.status()}: ${res.url().slice(API.length)}`);
    }
  });
  return problems;
}

test.beforeAll(async ({ request }) => {
  const ok = await request
    .get(`${API}/health`, { timeout: 5_000 })
    .then((r) => r.ok())
    .catch(() => false);
  test.skip(!ok, `API not reachable at ${API}`);
});

for (const p of PAGES) {
  test(`${p.name} page loads without errors`, async ({ page }, info) => {
    const problems = watch(page);
    await page.goto(p.path);
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 20_000 });
    await page.waitForLoadState('networkidle').catch(() => undefined);
    await expect(page.getByText('API offline')).toHaveCount(0);
    await page.screenshot({ path: info.outputPath(`${p.name}.png`), fullPage: true });
    expect(problems, problems.join('\n')).toEqual([]);
  });
}

test('clicking through every sidebar tab keeps the live API (never falls into demo mode)', async ({
  page,
}) => {
  const problems = watch(page);
  await page.goto('/app');
  for (const tab of ['Data', 'AI agents', 'Tree age', 'Simulation', 'Reports', 'My land']) {
    await page.getByRole('link', { name: tab, exact: true }).first().click();
    await page.waitForLoadState('networkidle').catch(() => undefined);
    await expect(page.getByText('API offline')).toHaveCount(0);
  }
  expect(problems, problems.join('\n')).toEqual([]);
});

test('simulation explains its number and turns entered costs into a break-even price', async ({
  page,
}) => {
  const problems = watch(page);
  await page.goto(`/app/simulate?plot=${PLOT}`);
  await expect(page.getByRole('heading', { name: 'Why this number? Explainable AI' })).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText('Number of trees', { exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('heading', { name: 'From growth to a carbon credit' })).toBeVisible();
  await page.getByLabel('Sapling, per tree').fill('60');
  await expect(page.getByText('Carbon price that would cover them')).toBeVisible({
    timeout: 20_000,
  });
  expect(problems, problems.join('\n')).toEqual([]);
});

test('agents run end to end from the Agents page', async ({ page }) => {
  test.setTimeout(120_000);
  const problems = watch(page);
  await page.goto(`/app/agents?plot=${PLOT}`);
  const run = page.getByRole('button', { name: 'Run the agents' });
  await expect(run).toBeEnabled({ timeout: 20_000 });
  await run.click();
  await expect(page.getByText(/^(Completed|Completed with warnings)$/).first()).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByText('Failed', { exact: true })).toHaveCount(0);
  // The full assessment ends with the coordinator's summary and states that nothing is a credit.
  await expect(page.getByText(/not a carbon credit|not carbon credits/i).first()).toBeVisible();
  expect(problems, problems.join('\n')).toEqual([]);
});
