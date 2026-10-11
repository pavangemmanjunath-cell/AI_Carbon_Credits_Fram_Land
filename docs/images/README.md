# Documentation images

What is in `docs/images/`, how the pictures are made, and what license they carry. The docs use two kinds of
pictures: screenshots of the web app, which are PNG files made by a script, and diagrams. Most diagrams are Mermaid text
inside Markdown pages, so there is no file to keep in step with the text; the README's architecture, workflow and agent-team
pictures (and the logo) are PNG files rendered from HTML sources in [`src/`](src/README.md).

## At a glance

| What | Where | How it is made |
| --- | --- | --- |
| Screenshots of the web app | `docs/images/screenshots/*.png` | `node scripts/capture_screenshots.mjs` ([steps](#screenshots)) |
| Diagrams | `mermaid` code blocks in four pages ([list](#diagrams)) | Written as text; GitHub draws them |
| Icons | `apps/web/public/favicon.svg` and the QGIS plugin's `icon.svg` and `icons/` | Hand-drawn SVG that belongs to the apps ([license](#licenses)) |

## Screenshots

The script drives a real browser (Playwright with Chromium) through the running web app, which talks to the API in demo
mode. Everything on screen is synthetic demo data, so no real farm appears in a picture.

### Quick start

```bash
make install-web                                    # once; the script loads Playwright from apps/web/node_modules
(cd apps/web && npx playwright install chromium)    # once; or set CHROMIUM_PATH to a Chromium you already have
make api                                            # terminal 1: the API in demo mode on port 8000
(cd apps/web && npm run build && npm run preview)   # terminal 2: the built web app on port 4173
node scripts/capture_screenshots.mjs                # terminal 3: writes docs/images/screenshots/*.png
```

A run takes about a minute and a half and prints `saved <path>` for each file. Rebuild the web app after you change the
interface, or the pictures show the old one.

### What the script needs

| Need | Detail |
| --- | --- |
| API in demo mode on port 8000 | Demo is the default (`ATLAS_MODE=demo`). At start-up it creates three synthetic plots (`ATLAS_SEED_DEMO`), and the script uses `PLT-DEMOIN`. The app finds the API at `http://localhost:8000/api/v1` unless `VITE_API_BASE_URL` was set at build time |
| The built web app on port 4173 | `npm run preview` already uses port 4173. The API's default CORS list includes `http://127.0.0.1:4173`; for another address, see [CORS](../developer-guide/troubleshooting.md#the-browser-reports-a-cors-error) |
| Playwright and Chromium | Playwright comes with the web app's dev dependencies. Chromium comes from `npx playwright install chromium`, from `CHROMIUM_PATH`, or from a copy under `/opt/pw-browsers` |
| Internet access | The map loads its basemap and the Satellite view loads imagery from outside hosts. Without access the pictures show the plain ground ([what to look for](#check-every-picture-before-you-commit)) |

The script takes two optional arguments, the web app's address and the output folder:

```bash
node scripts/capture_screenshots.mjs http://127.0.0.1:4173 /tmp/shots
```

The defaults are `http://127.0.0.1:4173` and `docs/images/screenshots`. Pass a different folder to look at a run
before it replaces anything in the repository.

### How the pictures are taken

- Desktop shots use a 1440 by 900 window at twice the pixel density, so each file is 2880 pixels wide. The phone shot
  uses 390 by 844 with touch at three times the density, so it is 1170 pixels wide. The locale is `en-IN`, the color
  scheme is light, and the interface is in English.
- Chromium starts with `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist
  --enable-webgl`. That gives the map software WebGL, so the script works in a container or on a runner without a GPU
  ([WebGL troubleshooting](../developer-guide/troubleshooting.md#the-map-says-my-browser-does-not-support-webgl)).
- Each shot opens its page, waits a fixed time for the map and data to settle, runs an optional click, and saves a
  viewport or a full-page image. On a slow machine or a slow network, raise the `settle` value of the shot that came out
  half-loaded. If a click fails, the script prints `action for <name> failed` and still saves the picture, without the
  click.

### What it captures

| File | Page | What the picture shows |
| --- | --- | --- |
| `01-landing.png` | `/` | The landing page, full height |
| `02-workspace.png` | `/app` | The workspace: map, the demo plot, plot details and result cards |
| `03-workspace-satellite.png` | `/app` | The same view with the Satellite switch on — only with `CAPTURE_SATELLITE=1` and network access to the imagery hosts |
| `04-import-dialog.png` | `/app` | The "Import data" dialog, opened from the header |
| `05-data.png` | `/app/data` | The Data page: land plots and imported files |
| `06-results.png` | `/app/plots/PLT-DEMOIN/results` | The carbon potential page, full height |
| `07-simulation.png` | `/app/simulate?...&plot=PLT-DEMOIN` | The simulation page for 420 mango trees planted in 2023, 30-year horizon |
| `08-report.png` | `/app/plots/PLT-DEMOIN/report` | The report page |
| `09-agents.png` | `/app/agents` | The AI agents page |
| `09b-agents-conversation.png` | `/app/agents` | The same page scrolled to the conversation: who said what |
| `10-tree-age.png` | `/app/tree-age?...` | The tree-age page, full height: 25 mango trees aged 80 on a farm in Haryana, India |
| `11-species.png` | `/app/species` | The tree species reference |
| `12-phone-workspace.png` | `/app` | The workspace in the phone layout |

### Check every picture before you commit

Open each file. A run that looks fine in the terminal can still produce a bad picture:

| What you see | Likely cause | What to do |
| --- | --- | --- |
| "Basemap unavailable — showing your plot on a plain ground" in the map | Captured with `CAPTURE_REAL_BASEMAP=1` on a machine that cannot reach the basemap host. By default the script answers the demo basemap with a plain one-layer style, so offline captures show a neutral ground without this notice | Run again with internet access ([troubleshooting](../developer-guide/troubleshooting.md#the-map-is-gray-or-says-the-basemap-is-unavailable)) |
| The Satellite shot shows the plain map | The imagery host is blocked or slow | Same; see the [satellite view](../developer-guide/troubleshooting.md#the-satellite-view-is-blank-or-a-provider-is-unavailable) |
| "API offline — showing demo data" | The API is not running on port 8000, or the browser's origin is not allowed | Start the API, or fix [CORS](../developer-guide/troubleshooting.md#the-browser-reports-a-cors-error) |
| Empty cards or a spinner | The page needed longer to settle | Raise that shot's `settle` value |
| A real place name, a real farm or a personal file name | You pointed the app at real data | Delete the picture. Screenshots use the synthetic demo plots or the farms in `examples/` only |

The default basemap style is MapLibre's demo style, which is meant for demos ([setup](../developer-guide/setup.md)).
For a published set, build the web app with your own basemap (`VITE_BASEMAP_PMTILES_URL`) and check its license first.

### Rules for screenshots

1. Synthetic data only. Exact plot boundaries are private by default, and a picture of a real plot is not.
2. Do not crop out the wording that says a number is an estimate. A picture of a result keeps the "not an issued
   carbon credit" line in frame.
3. Show the interface in English. The attribution strings are not translated either
   ([ATTRIBUTION.md](../licensing/ATTRIBUTION.md#localization)).
4. Give every image in a page alt text that says what it shows, in one sentence.
5. Credit the map and imagery in the caption ([below](#credits-in-captions)).
6. Refresh the set when the interface changed, at release time ([release process](../developer-guide/release-process.md)),
   not in every pull request. Each refresh adds the whole set (about 6 MB) to the git history.

## Diagrams

Diagrams are [Mermaid](https://mermaid.js.org/) code blocks. GitHub draws them when it shows the page, so the diagram
lives in the same file as the text that explains it and a change shows up in the pull request diff. Four pages have
them today:

| Page | Diagrams |
| --- | --- |
| [Architecture overview](../developer-guide/architecture-overview.md) | Components, and the path of one request |
| [System architecture](../architecture/system-architecture.md) | The components of the system: browser, API, engines, adapters and storage |
| [Data flow](../architecture/data-flow.md) | One session in sequence, from a place name to a downloaded report |
| [Agents](../agents/README.md) | The team and its blackboard, one run step by step, and how the optional LLM reasoner is used |

Guidelines:

- Put file and folder names in the boxes, so a reader can find the code.
- Quote a label that contains parentheses, slashes or a colon: `A["integrations/ (adapters)"]`. An unquoted one is the
  most common cause of a syntax error.
- Do not set colors by hand. GitHub shows the diagram in light and dark themes, and a fixed color can become unreadable
  in one of them.
- Check the syntax before you commit. A mistake shows a red error box on GitHub in place of the diagram, and CI does not
  check Mermaid. Paste the block into <https://mermaid.live> (do not paste anything private) or run it through the
  `mmdc` command from `@mermaid-js/mermaid-cli`.
- Describe the diagram in the sentence before it, for readers who cannot see it.

## Rendered diagrams, logo and social preview

Three diagrams and two brand pictures are PNG files instead of Mermaid, because they need a layout, fonts and colors
that Mermaid does not give. Each one is an HTML page in [`src/`](src/README.md) that one script turns into a PNG, so a
change to a picture is a change to a text file.

| File | Pixels | Shows |
| --- | --- | --- |
| `architecture.png` | 2400 x 1500 | The layers: browser and QGIS plugin, API, engines and agents, adapters, storage, `config/`, and the privacy rules |
| `workflow.png` | 2400 x 1000 | The five steps of a session, from marking land to a report, with the three values kept apart |
| `agents-team.png` | 2400 x 1300 | The agent team's full-assessment plan with its tools, the blackboard, the guardrails and the shorter plans |
| `logo.svg`, `logo.png` | 512 x 512 | The mark: a white leaf on a forest-green rounded square. The PNG has transparent corners |
| `social-preview.png` | 1280 x 640 | The image to upload as the repository's social preview (Settings, General) |

To change one, edit its page in `src/` and run `node docs/images/src/render.mjs`. The script needs Playwright and
Chromium but no server, and it checks text size, overlaps, contrast and arrows ([details](src/README.md)). Open the new
PNG and look at it before you commit it. These pictures carry the same license as the other diagrams
([Licenses](#licenses)); the fonts in them are under the SIL Open Font License.

## Icons

| File | What it is |
| --- | --- |
| `apps/web/public/favicon.svg` | The web app's tab icon: a white leaf on a green rounded square |
| `integrations/qgis-plugin/carboncreditbuy_qgis/icon.svg` and `icons/*.svg` | The QGIS plugin's icon and its four toolbar icons (`agents`, `carbon`, `count`, `send`) |

The plugin icons carry the comment "Original glyph", which means they were drawn for the project and are not copied from
an icon set. The interface icons in the web app are not image files: they come from the `lucide-react` package
([ISC](../licensing/THIRD_PARTY.md#web-app-appswebpackagejson)).

## Licenses

| Content | License | Notes |
| --- | --- | --- |
| Our screenshots and diagrams | The license of `docs/`: Apache-2.0 unless a page says otherwise ([ADR-0005](../architecture/adr/0005-apache-2-license.md)) | The user-guide FAQ says CC BY 4.0 instead; see [Known gaps](#known-gaps) |
| The web app's favicon | The project's license, Apache-2.0 | A plain SVG with no header of its own |
| The QGIS plugin's icons | GPL-2.0-or-later, as part of the plugin folder | [Why the plugin is separate](../licensing/THIRD_PARTY.md#the-qgis-plugin-and-the-gpl) |
| Interface fonts in screenshots | SIL Open Font License 1.1 | Self-hosted from `@fontsource` ([fonts](../licensing/THIRD_PARTY.md#fonts)) |
| OpenStreetMap data in the basemap | ODbL | Credit "© OpenStreetMap contributors" |
| Imagery from EOX 2016 or 2017, IGN Spain or PDOK | CC BY 4.0 | Credit the provider with its string from [ATTRIBUTION.md](../licensing/ATTRIBUTION.md#imagery-providers-satellite-view) |
| Imagery from USGS | Public domain | Credit it anyway; the string is in the same table |
| Imagery from IGN France | Licence Ouverte 2.0 | Name the source; add the date when you know it |
| Imagery from EOX 2025 | CC BY-NC-SA 4.0: non-commercial, share-alike | Do not publish a picture that shows it. The docs license allows commercial reuse, which this imagery does not |
| Imagery from Esri | Esri Master License Agreement; display only | Do not publish a picture that shows it. The terms were not fully reviewed for this use |
| Logos, photos or figures from other sites | Their own | None are in the repository. Add one only if its license allows redistribution, and record the source and license in its caption and here |

The terms behind the imagery rows are in [MAP_LICENSES.md](../licensing/MAP_LICENSES.md#imagery-providers). The default
imagery provider for India is EOX 2016, which is CC BY 4.0, so the Satellite shot from the script is safe to publish
with its credit. A deployment can change the default, so look at the attribution bar in the picture to see which
provider is on screen.

### Credits in captions

[ATTRIBUTION.md](../licensing/ATTRIBUTION.md#placement-rules) asks for the map and data attributions in the caption of
a screenshot or publication. The app's own attribution bar is in the picture, but it clamps a long string to one line,
so it can be cut off. Put the full text in the caption, for example:

```markdown
![The workspace with the demo orchard on satellite imagery](../images/screenshots/03-workspace-satellite.png)

*Demo data. Map: © OpenStreetMap contributors. Imagery: EOxCloudless <https://cloudless.eox.at> by EOX IT Services GmbH
(Contains modified Copernicus Sentinel data 2016) released under Creative Commons Attribution 4.0 International License.*
```

## Known gaps

- Nothing checks that a screenshot matches the current interface. The release checklist asks a person to look.
- The script takes no language option, so every picture is in English. A set per interface language would need a
  `--lang` argument and a way to set the language before each shot.

## Related

- [Setup](../developer-guide/setup.md) and [troubleshooting](../developer-guide/troubleshooting.md)
- [Release process](../developer-guide/release-process.md): the checklist that asks for a refresh
- [ATTRIBUTION.md](../licensing/ATTRIBUTION.md), [MAP_LICENSES.md](../licensing/MAP_LICENSES.md) and
  [DATA_LICENSES.md](../licensing/DATA_LICENSES.md)
