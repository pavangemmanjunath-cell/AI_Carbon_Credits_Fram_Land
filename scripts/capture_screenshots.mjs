#!/usr/bin/env node
/**
 * Captures high-resolution (2×) screenshots of the running web app for the
 * documentation. Requires the API (demo mode) on :8000 and the web app on
 * :4173 (`npm run build && npx vite preview`) — see docs/images/README.md.
 *
 * Usage: node scripts/capture_screenshots.mjs [baseUrl] [outDir]
 */
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../apps/web/node_modules/playwright'));

const base = process.argv[2] ?? 'http://127.0.0.1:4173';
const outDir = process.argv[3] ?? path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../docs/images/screenshots');
mkdirSync(outDir, { recursive: true });

const PLOT = 'PLT-DEMOIN';
// The satellite shot needs network access to the imagery hosts in config/imagery/providers.yaml.
const CAPTURE_SATELLITE = process.env.CAPTURE_SATELLITE === '1';
// Offline captures: the demo basemap (demotiles.maplibre.org) is answered with a plain
// one-layer style so the map shows the same neutral ground without the
// "basemap unavailable" notice. Set CAPTURE_REAL_BASEMAP=1 to use the real style.
const PLAIN_STYLE = { version: 8, sources: {}, layers: [{ id: 'plain-ground', type: 'background', paint: { 'background-color': '#E7EEE4' } }] };
// Each shot: URL, full-page or viewport, settle time, and an optional action run before the capture.
const shots = [
  { name: '01-landing', url: '/', fullPage: true, settle: 2500 },
  { name: '02-workspace', url: '/app', fullPage: false, settle: 9000 },
  CAPTURE_SATELLITE && {
    name: '03-workspace-satellite',
    url: '/app',
    fullPage: false,
    settle: 9000,
    // "Map | Satellite" switch in the map's bottom-left corner; tiles come from GET /imagery/providers.
    action: async (page) => {
      await page.getByRole('radio', { name: 'Satellite' }).click();
      await page.waitForTimeout(6000);
    },
  },
  {
    name: '04-import-dialog',
    url: '/app',
    fullPage: false,
    settle: 6000,
    // The header's Import button opens the Trimble-style "Import data" dialog from any page.
    action: async (page) => {
      await page.getByRole('button', { name: 'Import data' }).click();
      await page.waitForTimeout(800);
    },
  },
  { name: '05-data', url: '/app/data', fullPage: false, settle: 3000 },
  { name: '06-results', url: `/app/plots/${PLOT}/results`, fullPage: true, settle: 5000 },
  { name: '07-simulation', url: `/app/simulate?country=IN&species=mango&trees=420&year=2023&horizon=30&plot=${PLOT}`, fullPage: false, settle: 4000 },
  { name: '08-report', url: `/app/plots/${PLOT}/report`, fullPage: false, settle: 6000 },
  { name: '09-agents', url: '/app/agents', fullPage: false, settle: 5000 },
  {
    name: '09b-agents-conversation',
    url: '/app/agents',
    fullPage: false,
    settle: 5000,
    // Who said what: scroll to the transcript.
    action: async (page) => {
      await page.getByRole('heading', { name: 'Conversation' }).scrollIntoViewIfNeeded();
      await page.mouse.wheel(0, 260);
      await page.waitForTimeout(600);
    },
  },
  { name: '10-tree-age', url: '/app/tree-age?country=IN&subdivision=IN-HR&setting=farm&species=mango&age=80&trees=25', fullPage: true, settle: 5000 },
  { name: '11-species', url: '/app/species', fullPage: false, settle: 2500 },
].filter(Boolean);

const executablePath = process.env.CHROMIUM_PATH ?? (['/opt/pw-browsers/chromium', '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'].find((p) => { try { return require('node:fs').statSync(p).isFile(); } catch { return false; } }));
const browser = await chromium.launch({
  headless: true,
  ...(executablePath ? { executablePath } : {}),
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'],
});
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: 'en-IN', colorScheme: 'light' });
  const plainBasemap = (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PLAIN_STYLE) });
  if (process.env.CAPTURE_REAL_BASEMAP !== '1') await context.route('https://demotiles.maplibre.org/**', plainBasemap);
  const page = await context.newPage();
  page.on('pageerror', (err) => console.warn('page error:', err.message));
  for (const shot of shots) {
    await page.goto(`${base}${shot.url}`, { waitUntil: 'networkidle', timeout: 60_000 }).catch(() => page.goto(`${base}${shot.url}`, { waitUntil: 'load' }));
    await page.waitForTimeout(shot.settle);
    if (shot.action) {
      try {
        await shot.action(page);
      } catch (error) {
        console.warn(`action for ${shot.name} failed:`, error.message);
      }
    }
    const file = path.join(outDir, `${shot.name}.png`);
    await page.screenshot({ path: file, fullPage: shot.fullPage });
    console.log('saved', file);
  }
  // phone layout of the workspace
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, locale: 'en-IN' });
  if (process.env.CAPTURE_REAL_BASEMAP !== '1') await phone.route('https://demotiles.maplibre.org/**', plainBasemap);
  const phonePage = await phone.newPage();
  await phonePage.goto(`${base}/app`, { waitUntil: 'networkidle', timeout: 60_000 }).catch(() => phonePage.goto(`${base}/app`, { waitUntil: 'load' }));
  await phonePage.waitForTimeout(8000);
  await phonePage.screenshot({ path: path.join(outDir, '12-phone-workspace.png'), fullPage: false });
  console.log('saved phone');
} finally {
  await browser.close();
}
