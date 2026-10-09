# Third-party software

AgriCarbon Atlas is Apache-2.0 ([ADR-0005](../architecture/adr/0005-apache-2-license.md)) and depends on permissively
licensed software, with one LGPL library used as a dynamically linked dependency. One folder is licensed differently:
the QGIS plugin in `integrations/qgis-plugin/` is GPL-2.0-or-later
([why](#the-qgis-plugin-and-the-gpl)). This page gives the overview and the commands that regenerate the full
inventory; the generated inventories are the authoritative lists and are attached to each release.

The licenses below were read on 2026-10-05 from the installed package metadata (`pip show`, `importlib.metadata` and
each npm package's `package.json`), not copied from memory. WeasyPrint was not installed, so its row is not verified.

## Python back end (from `requirements.txt`)

| Package | Role | License |
| --- | --- | --- |
| fastapi | HTTP framework | MIT |
| uvicorn[standard] | ASGI server | BSD-3-Clause |
| pydantic, pydantic-settings | Validation and settings | MIT |
| python-multipart | Parses the multipart uploads of `POST /imports` (GeoJSON, KML, KMZ, CSV, LAS, LAZ) | Apache-2.0 |
| slowapi | Rate limiting | MIT |
| shapely | Geometry | BSD-3-Clause |
| pyproj | Projections, geodesic area | MIT |
| numpy | Arrays | BSD-3-Clause (the wheel also carries parts under 0BSD, MIT, Zlib and CC0-1.0) |
| httpx | HTTP client for adapters | BSD-3-Clause |
| defusedxml | Safe XML parsing for KML and KMZ imports: no external entities, no entity-expansion bombs | PSF-2.0 (Python Software Foundation License, version 2) |
| PyYAML | Configuration loading | MIT |
| Jinja2 | Report templates | BSD-3-Clause |
| jsonschema | Schema validation of results | MIT |
| laspy | Reads LAS and LAZ point clouds (`geo_engine.pointcloud`) | BSD-2-Clause |
| lazrs (installed by the `laspy[lazrs]` extra) | Decodes LAZ, the compressed point-cloud format; a compiled Rust library | MIT |
| rasterio (bundles GDAL and PROJ in wheels) | COG window reads | BSD-3-Clause (GDAL: MIT/X; PROJ: MIT) |
| pystac-client | STAC search | Apache-2.0 |
| psycopg[binary] | PostgreSQL driver (optional) | LGPL-3.0-only. Used unmodified as a library; the binary wheel bundles libpq (PostgreSQL License) |
| pytest, pytest-asyncio, respx | Tests | MIT / Apache-2.0 / BSD-3-Clause |
| ruff, mypy, types-PyYAML | Tooling | MIT / MIT / Apache-2.0 |
| WeasyPrint (optional extra) | PDF reports | BSD-3-Clause (depends on Pango and Cairo, LGPL, as system libraries). Not verified here |

Notes on the four newest packages:

- **laspy** reports `BSD-2-Clause` and carries a BSD license file.
- **lazrs** reports `MIT` in its installed metadata, and its license file is the MIT text. The comment in
  `requirements.txt` says "MIT/Apache-2.0". The wheel holds compiled Rust code, and the metadata does not list the
  licenses of the Rust crates inside it. TODO(verify): the upstream licenses of those crates before the first release
  (check the lazrs and laz-rs repositories), and correct whichever statement is wrong.
- **defusedxml** reports `PSFL` and carries the PSF License version 2.
- **python-multipart** reports `Apache-2.0`.

`packages/geo-engine` imports `defusedxml` and `laspy`, but they are listed only in `requirements.txt`, not in the
`pyproject.toml` of that package or of `apps/api`. Install from `requirements.txt` (what `make install` and the Docker
image do) so that the imports work.

## Web app (`apps/web/package.json`)

Runtime dependencies, which ship in the web build:

| Package | Role | License |
| --- | --- | --- |
| react, react-dom | UI | MIT |
| react-router | Routing | MIT |
| maplibre-gl | Map renderer | BSD-3-Clause |
| pmtiles | Tile archive protocol | BSD-3-Clause |
| terra-draw, terra-draw-maplibre-gl-adapter | Drawing | MIT |
| @turf/turf | Geospatial helpers in the browser | MIT |
| recharts | Charts | MIT |
| motion | Animation | MIT |
| lucide-react | Icons | ISC |
| @tanstack/react-query | Server state | MIT |
| zustand | UI state | MIT |
| i18next, react-i18next | Internationalization | MIT |
| @fontsource/space-grotesk, @fontsource/ibm-plex-sans, @fontsource/ibm-plex-mono | Self-hosted fonts | OFL-1.1 ([fonts](#fonts)) |

Build and test tools, which do not ship:

| Package | Role | License |
| --- | --- | --- |
| typescript | Language | Apache-2.0 |
| vite, @vitejs/plugin-react | Build tool | MIT |
| tailwindcss, @tailwindcss/vite | Styling | MIT |
| vitest, @vitest/coverage-v8, jsdom, @testing-library/* | Unit tests | MIT |
| @playwright/test | End-to-end tests | Apache-2.0 |
| eslint, typescript-eslint, eslint plugins, prettier | Lint and format | MIT |

The exact dependency tree, including transitive packages, is what the generated inventory records; the tables above
are the direct dependencies at the time of writing.

**Not dependencies.** `deck.gl` (with luma.gl and loaders.gl), `three`, `@react-three/fiber`, `@react-three/drei`
and DuckDB-WASM are not listed in `apps/web/package.json` (checked 2026-10-05), so they have no row here or in
[MAP_LICENSES.md](MAP_LICENSES.md). If one is added back, add its row to both pages in the same pull request.

## Fonts

The web app bundles three font families from `@fontsource` packages. They are installed with `npm install`, copied
into the build output by Vite, and served from your own host. The app asks no third party for a font.

| Family | Used for | Package and version checked | License | Copyright notice |
| --- | --- | --- | --- | --- |
| Space Grotesk | Headings and large numbers | `@fontsource/space-grotesk` 5.3.0 | SIL Open Font License 1.1 | Copyright 2020 The Space Grotesk Project Authors (<https://github.com/floriankarsten/space-grotesk>) |
| IBM Plex Sans | Body text | `@fontsource/ibm-plex-sans` 5.3.0 | SIL Open Font License 1.1 | Copyright 2019 IBM Corp. All rights reserved. |
| IBM Plex Mono | Code, identifiers, labels and coordinates | `@fontsource/ibm-plex-mono` 5.3.0 | SIL Open Font License 1.1 | Copyright 2017 IBM Corp. All rights reserved. |

The license and copyright lines are from each package's `package.json` and `LICENSE` file; the license text itself is
in `apps/web/node_modules/@fontsource/<name>/LICENSE`. What the OFL asks of us, in short (the license text rules; this
is not legal advice):

- Each copy of the font files that we distribute keeps the copyright notice and the license. The font files carry the
  copyright line and the OFL address in their metadata (checked on the `latin-400` files of the three families).
  The v0.1 build does not copy the `LICENSE` files into its output, so attach the license text with a release
  ([notices](#notices)).
- The fonts are not sold on their own, and a modified font may not use a reserved font name. The Atlas does not modify
  them: `src/styles/globals.css` imports the Latin subsets that `@fontsource` ships (Space Grotesk 500, 600 and 700;
  IBM Plex Sans 400, 500 and 600; IBM Plex Mono 400 and 500).
- The OFL covers the font files, not the documents or the software that use them.

Only the Latin subsets are bundled. Hindi and Kannada text falls back to the system's fonts, because the font stacks in
`src/styles/tokens.css` end in `system-ui`. A deployer who wants bundled fonts for those scripts adds an OFL family
from `@fontsource` and a row here. Map labels use the glyph files of the map style, which are a separate matter
([troubleshooting](../developer-guide/troubleshooting.md#fonts-look-wrong-or-the-browser-contacts-a-font-host)).

## The QGIS plugin and the GPL

The plugin in `integrations/qgis-plugin/` is licensed **GPL-2.0-or-later**. Everything else in the repository is
Apache-2.0. The two licenses do not mix, so the plugin lives in its own folder with its own `LICENSE` file.

**Why the plugin is GPL.** A QGIS plugin runs inside QGIS and imports its Python API (`qgis.core`, `qgis.gui` and
`qgis.PyQt`). QGIS and the Qt bindings it exposes are distributed under the GPL, so the plugin uses a GPL-compatible
license ([`integrations/qgis-plugin/LICENSE`](../../integrations/qgis-plugin/LICENSE) and its README say the same).

**Why it is separate.** What we checked on 2026-10-05:

- Every Python file in the folder starts with `SPDX-License-Identifier: GPL-2.0-or-later`.
- The plugin imports only `qgis`, `qgis.PyQt` and the Python standard library. It imports nothing from `apps/`,
  `packages/` or `integrations/atlas_integrations/`, and nothing outside the folder imports the plugin.
- The two sides exchange only HTTP requests and JSON. The plugin calls the Atlas API like any other client, so they
  remain separate programs. The plugin's `LICENSE` says that Apache-2.0 software called by the plugin, or calling it,
  is not affected.
- `scripts/package.py` builds the installable ZIP from the plugin folder alone, plus its `LICENSE` and `README.md`.
  The plugin has no dependencies to install: it uses QGIS's own Python.

**What this means for you.**

| You are | What applies |
| --- | --- |
| Running the API or the web app | Only Apache-2.0 and the licenses in the tables above. The GPL does not reach your server |
| Using the plugin | GPL-2.0-or-later. You may use, change and share it under the GPL. Share it with its source and `LICENSE` (the ZIP includes both) |
| Contributing to the plugin | Your contribution is licensed GPL-2.0-or-later, as the plugin README says. Keep the SPDX header on new files. Add no dependency beyond QGIS and the standard library unless its license is GPL-compatible, and give it a row here |
| Contributing anywhere else | Apache-2.0. Do not import the plugin, and do not copy code between the plugin and the rest of the repository in either direction. If both sides need the same logic, put it behind an API endpoint, or write it twice |
| Building a container image | The API image copies the whole `integrations/` folder (`infra/docker/Dockerfile.api`), so it also holds the plugin's files. They are not loaded, but they are there. A `.dockerignore` entry for `integrations/qgis-plugin/` would keep them out. See [known gaps](#known-gaps) |

This is a summary of the repository's own statements, not legal advice. A change to the plugin's license, or an import
across the boundary, needs a maintainer decision first ([GOVERNANCE.md](../../GOVERNANCE.md)).

## Regenerating the inventories

Python (run inside the project's virtual environment after `make install`):

```bash
python -m pip install pip-licenses
pip-licenses --format=markdown --with-urls --with-license-file --no-license-path \
  --output-file docs/licensing/generated/python-licenses.md
pip-licenses --format=json --with-urls --output-file docs/licensing/generated/python-licenses.json
# Fail the build on licenses we do not accept:
pip-licenses --fail-on="GPL-3.0-only;GPL-3.0-or-later;AGPL-3.0-only;AGPL-3.0-or-later;SSPL-1.0"
```

JavaScript (inside `apps/web`):

```bash
npx license-checker --production --json --out ../../docs/licensing/generated/web-licenses.json
npx license-checker --production --summary
# Fail on disallowed licenses:
npx license-checker --production --failOn "GPL-3.0;AGPL-3.0;SSPL-1.0"
```

The `docs/licensing/generated/` directory is created by these commands and is attached to release artifacts
([release process](../developer-guide/release-process.md)); it is not committed, to keep the repository free of large
generated files. The QGIS plugin has no inventory because it has no dependencies of its own.

## Policy

| Category | Accepted? | Notes |
| --- | --- | --- |
| Permissive (MIT, BSD, Apache-2.0, ISC, CC0, Unlicense, PostgreSQL, Python-2.0, PSF-2.0) | Yes | |
| Weak copyleft as a dynamically linked library (LGPL-2.1/3.0, MPL-2.0) | Yes, with a note here | psycopg is the current example |
| Fonts under the SIL Open Font License | Yes, for bundled fonts | Keep the notices; do not sell the fonts alone; do not modify them under a reserved name ([fonts](#fonts)) |
| Strong copyleft (GPL, AGPL) | No for runtime dependencies of the Apache-2.0 parts | Development-only tools under GPL may be used if not redistributed. Our own GPL code is the QGIS plugin folder only ([the QGIS plugin and the GPL](#the-qgis-plugin-and-the-gpl)) |
| Source-available / non-OSI (SSPL, BUSL, Commons Clause) | No | |
| Non-commercial data or services | Deployment decision, documented in [DATA_LICENSES.md](DATA_LICENSES.md) | Open-Meteo free tier, the 2018 and later EOX imagery mosaics ([MAP_LICENSES.md](MAP_LICENSES.md)) |

A new dependency is reviewed for license, maintenance status and size in the pull request; Dependabot keeps versions
current and the `Security` workflow audits for known vulnerabilities. Licenses are not gated by the workflow, so the
reviewer checks them against this page.

## Notices

There is no `NOTICE` file yet, and the v0.1 web build does not copy dependency license texts into its output. Before
the first release, attach the generated inventories ([above](#regenerating-the-inventories)), add a `NOTICE` file that
lists the bundled software that needs one (at least the three font families, with the OFL text), and tell the team here
when it exists. Data attributions are a separate obligation, handled in [ATTRIBUTION.md](ATTRIBUTION.md).

## Known gaps

- **The API image holds the plugin's files.** `infra/docker/Dockerfile.api` copies the whole `integrations/` folder.
  Excluding `integrations/qgis-plugin/` keeps GPL files out of an Apache-2.0 image.
- **No NOTICE file and no license texts in the web build** ([notices](#notices)).
- **lazrs license.** `requirements.txt` says MIT/Apache-2.0 and the installed metadata says MIT only
  ([Python back end](#python-back-end-from-requirementstxt)).
- **Narrower `pyproject.toml` files.** `defusedxml` and `laspy` are listed only in `requirements.txt`, although
  `packages/geo-engine` imports them.
