#!/usr/bin/env node
/**
 * Re-renders the README diagrams, the logo and the social preview from the HTML files next to this script.
 *
 *   node docs/images/src/render.mjs                    # every picture, written to docs/images/
 *   node docs/images/src/render.mjs architecture logo  # only the named ones
 *   node docs/images/src/render.mjs --out /tmp/preview # write somewhere else first
 *   node docs/images/src/render.mjs --no-lint          # skip the layout checks
 *
 * Needs Playwright (it ships with the web app: `make install-web`) and a Chromium. Set CHROMIUM_PATH to use
 * a browser you already have; otherwise /opt/pw-browsers/chromium is used when it exists, else the browser
 * Playwright installed. No network access is needed: the fonts are the self-hosted @fontsource files.
 *
 * Every page is rendered at the size of its <body> (the "CSS size") and a device scale factor, so the PNG is
 * `size x scale` pixels. Before the screenshot a layout check runs in the page and fails the run on: text
 * smaller than 14 px, a font weight that was not loaded, text that sticks out of its box or the picture,
 * overlapping text, arrows that do not touch the boxes they connect, arrows that cross text, and low contrast.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from '../../../apps/web/node_modules/playwright/index.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));

/** name: HTML file stem, size: CSS pixels, scale: device scale factor, out: file name inside the output folder. */
const JOBS = [
  { name: 'architecture', width: 1200, height: 750, scale: 2, out: 'architecture.png' },
  { name: 'workflow', width: 1200, height: 500, scale: 2, out: 'workflow.png' },
  { name: 'agents-team', width: 1200, height: 650, scale: 2, out: 'agents-team.png' },
  { name: 'logo', width: 512, height: 512, scale: 1, out: 'logo.png', transparent: true, lint: false },
  { name: 'social-preview', width: 1280, height: 640, scale: 1, out: 'social-preview.png' },
];

const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const outIndex = args.indexOf('--out');
const outDir = path.resolve(outIndex >= 0 ? args[outIndex + 1] : path.join(here, '..'));
const wanted = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--out');
const jobs = wanted.length ? JOBS.filter((j) => wanted.includes(j.name)) : JOBS;
if (wanted.length && jobs.length !== wanted.length) {
  const known = JOBS.map((j) => j.name).join(', ');
  console.error(`Unknown name in: ${wanted.join(' ')}. Known: ${known}`);
  process.exit(2);
}
fs.mkdirSync(outDir, { recursive: true });

function chromiumPath() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  return fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined;
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}

/** Runs inside the page. Returns a list of "error: ..." / "warn: ..." strings. */
function layoutCheck({ minFontPx }) {
  const issues = [];
  const err = (m) => issues.push(`error: ${m}`);
  const warn = (m) => issues.push(`warn: ${m}`);
  const body = document.body;
  const W = body.getBoundingClientRect().width;
  const H = body.getBoundingClientRect().height;
  const short = (s) => (s.length > 38 ? `${s.slice(0, 36)}…` : s);

  if (document.documentElement.scrollWidth > W + 1 || document.documentElement.scrollHeight > H + 1) {
    err(`content is larger than the ${W}x${H} picture (scroll ${document.documentElement.scrollWidth}x${document.documentElement.scrollHeight})`);
  }

  // ---- fonts: every text run must use a loaded face of exactly the requested weight
  const faces = [];
  document.fonts.forEach((f) => faces.push({ family: f.family.replace(/["']/g, ''), weight: String(f.weight), status: f.status }));
  for (const f of faces) if (f.status === 'error') err(`font ${f.family} ${f.weight} failed to load`);

  // ---- colour helpers
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(parseFloat);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (top, bottom) => {
    const a = top.a + bottom.a * (1 - top.a);
    if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
    const mix = (t, b) => (t * top.a + b * bottom.a * (1 - top.a)) / a;
    return { r: mix(top.r, bottom.r), g: mix(top.g, bottom.g), b: mix(top.b, bottom.b), a };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const contrast = (a, b) => {
    const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };
  const effectiveBg = (el) => {
    const layers = [];
    for (let e = el; e; e = e.parentElement) {
      const c = parse(getComputedStyle(e).backgroundColor);
      if (c && c.a > 0) layers.push(c);
      if (c && c.a === 1) break;
    }
    let acc = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc);
    return acc;
  };
  const isPainted = (el) => {
    const cs = getComputedStyle(el);
    const bg = parse(cs.backgroundColor);
    const border = ['Top', 'Right', 'Bottom', 'Left'].some((s) => parseFloat(cs[`border${s}Width`]) > 0 && cs[`border${s}Style`] !== 'none');
    return (bg && bg.a > 0.02) || border;
  };

  // ---- collect text runs
  const runs = [];
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const value = node.nodeValue.replace(/\s+/g, ' ').trim();
    const el = node.parentElement;
    if (!value || !el || el.closest('style,script,title,defs,marker')) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0.5 && r.height > 0.5);
    if (!rects.length) continue;
    runs.push({ node, el, value, rects });
  }

  for (const run of runs) {
    const cs = getComputedStyle(run.el);
    const size = parseFloat(cs.fontSize);
    const family = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
    const label = `"${short(run.value)}"`;
    // A subscript or superscript (the 2 in tCO2e) is allowed to be smaller than its line, but not tiny.
    const scripted = run.el.closest('sub, sup');
    if (scripted) {
      const parentSize = parseFloat(getComputedStyle(scripted.parentElement).fontSize);
      if (parentSize < minFontPx) err(`${label} sits in ${parentSize}px text (minimum ${minFontPx}px)`);
      else if (size < parentSize * 0.7) err(`${label} is ${size}px next to ${parentSize}px text (script too small)`);
    } else if (size < minFontPx) err(`${label} is ${size}px (minimum ${minFontPx}px)`);
    const face = faces.find((f) => f.family === family && f.weight === cs.fontWeight);
    if (!face) err(`${label} uses ${family} ${cs.fontWeight}, which has no @font-face (the browser would fake the weight)`);
    else if (face.status !== 'loaded') err(`${label}: font ${family} ${cs.fontWeight} is ${face.status}`);

    // contrast against whatever is painted behind the text
    const fg = parse(cs.color);
    const bg = effectiveBg(run.el);
    if (fg) {
      const text = fg.a < 1 ? over(fg, bg) : fg;
      const ratio = contrast(text, bg);
      if (ratio < 3) err(`${label} contrast ${ratio.toFixed(2)}:1 (needs 4.5:1)`);
      else if (ratio < 4.5) warn(`${label} contrast ${ratio.toFixed(2)}:1 (below 4.5:1)`);
    }

    // inside the picture
    for (const r of run.rects) {
      if (r.left < -0.5 || r.top < -0.5 || r.right > W + 0.5 || r.bottom > H + 0.5) {
        err(`${label} leaves the picture`);
        break;
      }
    }
    // inside the nearest box that has a background or a border
    let box = run.el;
    while (box && box !== body && !isPainted(box)) box = box.parentElement;
    if (box && box !== body) {
      const b = box.getBoundingClientRect();
      for (const r of run.rects) {
        if (r.left < b.left + 3 || r.right > b.right - 3 || r.top < b.top + 1 || r.bottom > b.bottom - 1) {
          err(`${label} does not fit inside its box (${box.className || box.tagName})`);
          break;
        }
      }
    }
  }

  // ---- overlapping text
  const inset = (r) => ({ left: r.left + 0.5, right: r.right - 0.5, top: r.top + 2, bottom: r.bottom - 2 });
  for (let i = 0; i < runs.length; i++) {
    for (let j = i + 1; j < runs.length; j++) {
      let hit = false;
      for (const a of runs[i].rects) {
        const A = inset(a);
        for (const b of runs[j].rects) {
          const B = inset(b);
          const w = Math.min(A.right, B.right) - Math.max(A.left, B.left);
          const h = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top);
          if (w > 1 && h > 1) hit = true;
        }
      }
      if (hit) err(`text overlaps: "${short(runs[i].value)}" and "${short(runs[j].value)}"`);
    }
  }

  // ---- arrows: endpoints must touch the boxes named in data-from / data-to, and nothing may cross text
  const distToRect = (p, r) => {
    const dx = Math.max(r.left - p.x, 0, p.x - r.right);
    const dy = Math.max(r.top - p.y, 0, p.y - r.bottom);
    if (dx > 0 || dy > 0) return Math.hypot(dx, dy);
    return Math.min(p.x - r.left, r.right - p.x, p.y - r.top, r.bottom - p.y); // inside: distance to the nearest edge
  };
  const svgRoot = document.querySelector('svg.wires');
  const toPage = (path, pt) => {
    const m = path.getScreenCTM();
    return { x: m.a * pt.x + m.c * pt.y + m.e, y: m.b * pt.x + m.d * pt.y + m.f };
  };
  for (const wire of document.querySelectorAll('[data-wire]')) {
    const id = wire.getAttribute('data-wire') || wire.id || 'wire';
    const total = wire.getTotalLength();
    const start = toPage(wire, wire.getPointAtLength(0));
    const end = toPage(wire, wire.getPointAtLength(total));
    const before = toPage(wire, wire.getPointAtLength(Math.max(total - 1, 0)));
    const len = Math.hypot(end.x - before.x, end.y - before.y) || 1;
    const hasHead = (wire.getAttribute('marker-end') || '').includes('url');
    const tipOffset = Number(wire.getAttribute('data-tip') ?? (hasHead ? 3 : 0));
    const tip = { x: end.x + ((end.x - before.x) / len) * tipOffset, y: end.y + ((end.y - before.y) / len) * tipOffset };
    const from = wire.getAttribute('data-from');
    const to = wire.getAttribute('data-to');
    if (from) {
      const el = document.querySelector(from);
      if (!el) err(`wire ${id}: data-from ${from} not found`);
      else if (distToRect(start, el.getBoundingClientRect()) > 1.6) err(`wire ${id}: starts ${distToRect(start, el.getBoundingClientRect()).toFixed(1)}px away from ${from}`);
    }
    if (to) {
      const el = document.querySelector(to);
      if (!el) err(`wire ${id}: data-to ${to} not found`);
      else if (distToRect(tip, el.getBoundingClientRect()) > 1.6) err(`wire ${id}: arrow tip is ${distToRect(tip, el.getBoundingClientRect()).toFixed(1)}px away from ${to}`);
    }
    for (let s = 0; s <= total; s += 2) {
      const p = toPage(wire, wire.getPointAtLength(s));
      for (const run of runs) {
        for (const r of run.rects) {
          if (p.x > r.left + 1 && p.x < r.right - 1 && p.y > r.top + 2 && p.y < r.bottom - 2) {
            err(`wire ${id} crosses the text "${short(run.value)}"`);
            s = total;
            break;
          }
        }
        if (s >= total) break;
      }
    }
  }
  void svgRoot;
  return [...new Set(issues)];
}

const browser = await chromium.launch({ executablePath: chromiumPath() });
let failed = false;
try {
  for (const job of jobs) {
    const htmlPath = path.join(here, `${job.name}.html`);
    const target = path.join(outDir, job.out);
    const context = await browser.newContext({
      viewport: { width: job.width, height: job.height },
      deviceScaleFactor: job.scale,
      reducedMotion: 'reduce',
    });
    const page = await context.newPage();
    const external = [];
    page.on('request', (req) => {
      if (!req.url().startsWith('file:') && !req.url().startsWith('data:')) external.push(req.url());
    });
    page.on('pageerror', (e) => console.error(`  page error: ${e.message}`));
    await page.goto(pathToFileURL(htmlPath).href);
    await page.evaluate(async () => {
      await Promise.all(Array.from(document.fonts).map((f) => f.load().catch(() => null)));
      await document.fonts.ready;
    });
    let issues = [];
    if (job.lint !== false && !flag('--no-lint')) issues = await page.evaluate(layoutCheck, { minFontPx: 14 });
    if (external.length) issues.push(`error: the page asked for network resources: ${external.join(', ')}`);
    await page.screenshot({ path: target, omitBackground: Boolean(job.transparent), clip: { x: 0, y: 0, width: job.width, height: job.height } });
    const size = pngSize(target);
    const wantW = job.width * job.scale;
    const wantH = job.height * job.scale;
    if (size.width !== wantW || size.height !== wantH) issues.push(`error: wrote ${size.width}x${size.height}, expected ${wantW}x${wantH}`);
    const bad = issues.filter((i) => i.startsWith('error'));
    console.log(`${bad.length ? 'FAIL' : 'ok  '} ${path.relative(process.cwd(), target) || target}  ${size.width}x${size.height}`);
    for (const i of issues) console.log(`     ${i}`);
    if (bad.length) failed = true;
    await context.close();
  }
} finally {
  await browser.close();
}
process.exit(failed && !flag('--keep-going') ? 1 : 0);
