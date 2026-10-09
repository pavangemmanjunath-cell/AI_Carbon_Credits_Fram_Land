# Sources of the rendered pictures

Each picture here is a small HTML page with inline SVG and CSS. `render.mjs` opens the page in Chromium and saves a PNG
next to the folder. Edit the page, run the renderer and commit both files. Do not edit a PNG by hand.

| Page | Writes | Pixels | Shows |
| --- | --- | --- | --- |
| `architecture.html` | `../architecture.png` | 2400 x 1500 | Browser, API, engines and agents, adapters, storage, `config/` and the QGIS plugin |
| `workflow.html` | `../workflow.png` | 2400 x 1000 | The five steps from marking land to a report |
| `agents-team.html` | `../agents-team.png` | 2400 x 1300 | The `full-assessment` plan, the blackboard, the guardrails and the two shorter plans |
| `logo.html` | `../logo.png` | 512 x 512 | `../logo.svg` on a transparent background |
| `social-preview.html` | `../social-preview.png` | 1280 x 640 | The GitHub social preview |

The three diagrams are laid out at 1200 CSS pixels wide and rendered at twice the pixel density. The mark itself is
`../logo.svg`; the logo page only displays it.

## Render

```bash
make install-web                                    # once; the renderer loads Playwright from apps/web/node_modules
(cd apps/web && npx playwright install chromium)    # once; or set CHROMIUM_PATH to a Chromium you already have
node docs/images/src/render.mjs                     # all five pictures, written to docs/images/
node docs/images/src/render.mjs workflow            # only the named ones (names are the page names above)
node docs/images/src/render.mjs --out /tmp/preview  # write somewhere else first
```

No server and no network access are needed. The fonts are the self-hosted `@fontsource` files from
`apps/web/node_modules` (Space Grotesk for headings, IBM Plex Sans for text, IBM Plex Mono for code), loaded with
relative paths, so the pages must stay in this folder. The fonts are under the SIL Open Font License 1.1
([licenses](../README.md#licenses)).

## What the renderer checks

Before it saves a diagram, `render.mjs` runs a layout check in the page and stops with a list of problems:

- text smaller than 14 CSS pixels (a subscript is allowed to be smaller than its line, but not tiny);
- a font weight that has no `@font-face`, so the browser would invent it;
- text that sticks out of its box or out of the picture, and text that overlaps other text;
- low contrast between text and what is behind it (WCAG 4.5:1 is a warning, below 3:1 is an error);
- arrows (`data-wire` paths) whose ends do not touch the boxes named in `data-from` and `data-to`, or that cross text;
- anything that asks for a network resource, and a PNG whose size is not the expected one.

The check does not judge looks. Open every new PNG and look at it before you commit it.

## Style

- Colors are the app's tokens, copied into `:root` at the top of each page: ground `#F3F6F2`, surface `#FFFFFF`, ink
  `#14211A`, forest `#1E6B41`, mint `#E6F2EA`, amber `#8A4B08` on `#FFF1DC`, and the dark panel `#14211A`.
- Flat shapes, rounded corners of 12 to 14 pixels and 1 pixel borders in `#DCE5DE`. No gradients and no third-party
  logos. A provider is a text label.
- Mint boxes are project code, outlined boxes are outside services, the dark band is the one public door (the API in
  the architecture, the blackboard in the agent team), and a dashed box is optional.
- Estimates are never shown as credits. Keep the three values (environmental benefit, indicative carbon value and other
  farm income) in separate boxes and never add them.
- The Latin subsets of the fonts have no arrows, check marks or a subscript two. Draw those in SVG, and write
  CO<sub>2</sub>e with a `<sub>` element.

## Add or change a picture

1. Copy the closest page, keep its `@font-face` and `:root` blocks, and set the `body` width and height to the size in
   CSS pixels.
2. Add the page to `JOBS` in `render.mjs` with its size, scale and output file name.
3. Run the renderer with `--out` set to a scratch folder and fix what the check reports.
4. Render again without `--out`, view the PNG, and link it from the page that explains it.
