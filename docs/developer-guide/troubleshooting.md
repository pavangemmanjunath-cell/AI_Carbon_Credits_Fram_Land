# Troubleshooting

Problems that come up when you set up, run, test and deploy AgriCarbon Atlas, with the cause and the
fix. Start with the checks below, then find your symptom. If you fix something that is not listed,
add it here.

## First checks

1. **Is the API up, and in which mode?** `curl http://localhost:8000/api/v1/health` returns the
   version, `mode` (`demo` or `live`) and `repository` (`memory` or `postgres`).
2. **What does the browser say?** Open the developer tools. The Console shows blocked requests and
   CORS and Content-Security-Policy messages in plain words. The Network tab shows which request
   failed, its status and the response body. The API answers errors as RFC 7807 problem documents:
   `type`, `title`, `status` and `detail` say what happened.
3. **What does the API log say?** Logs are JSON, one line per request, with the method, path, status,
   duration and request id (`X-Request-ID`). They never contain coordinates or query strings, so a
   failing request is identified by its id, not by the place.
4. **Is it the configuration?** Run `git status` and `git diff config/`. A half-edited YAML file in
   `config/` can make the API fail at start-up or on first use; the error names what it could not parse.

## Install and run

| Symptom | Likely cause and fix |
| --- | --- |
| `ModuleNotFoundError: carbon_engine` (or another package) | The editable installs are missing; run `make install-api` inside your virtual environment |
| `ModuleNotFoundError: atlas_agents` | The agent framework is not installed. Run `python3 -m pip install -e packages/agent-framework` (older `Makefile` versions do not list it) |
| `requires a different Python` while installing | The packages need Python 3.12 or newer. Check `python3 --version`, and create the virtual environment with the right interpreter |
| API ignores my `.env` | It was started from `apps/api`; see [setup](setup.md#2-configure) |
| An environment variable has no effect | Check the exact name in [setup](setup.md#environment-variables). Unknown variables are ignored without a warning. `VITE_*` values need a restart of the Vite server, and a rebuild of the Docker web image |
| Web shows "API offline — showing demo data" | The API is not running or `VITE_API_BASE_URL` points elsewhere; restart the Vite server after editing `.env`. If the API is up, look for a [CORS error](#the-browser-reports-a-cors-error) |
| Port 8000 or 5173 already in use | Run `ATLAS_API_PORT=8001 make api` (and point `VITE_API_BASE_URL` at it), or stop the other process. Vite picks the next free port by itself, so add that origin to `ATLAS_CORS_ORIGINS` |
| `docker compose up` fails with "env file .env not found" | Run `cp .env.example .env` |
| `npm run test` never exits | It starts in watch mode; use `npm run test -- --run` |
| Playwright cannot find a browser | `cd apps/web && npx playwright install chromium` |
| `npm ci` fails on the lock file | Use Node 22 or newer, and do not edit `package-lock.json` by hand; run `npm install` to update it |
| Live-mode geocoding returns an error | `NOMINATIM_USER_AGENT` is empty or still the placeholder, or you are inside the provider's rate limit (one request per second) |
| Live mode returns synthetic-looking data for US or Indian statistics | A source with a key falls back to its demo twin when the key is empty. Check the `provenance` in the response, then set `USDA_NASS_API_KEY` or `DATA_GOV_IN_API_KEY` |
| A request is rejected after many calls | The API's rate limit (`ATLAS_RATE_LIMIT`, 60 per minute by default). Raise it or set `ATLAS_RATE_LIMIT_ENABLED=false` for local work |

## Errors the API returns on purpose

| Status and `type` | Meaning and what to do |
| --- | --- |
| 409 `pending-parameters` | Production mode (or `ATLAS_ALLOW_PENDING_PARAMETERS=false`) refuses an estimate that uses a `pending` parameter. This is by design; verify the parameter ([species and parameters](adding-a-species-or-parameter.md)) or run in development mode |
| 501 `pdf-unavailable` | WeasyPrint is not installed; see [setup](setup.md#pdf-reports) |
| 501 for a model | `agroforestry`, `soil-carbon` and `crop-practice` have no documented method yet, so they refuse to run rather than guess |
| 422 `invalid-geometry` | The polygon fails validation: too many vertices, self-intersecting, too small or too large. The `detail` says which limit applies |
| 413 | An upload is larger than `ATLAS_MAX_UPLOAD_MB`, or a JSON body is larger than `ATLAS_MAX_BODY_BYTES` |
| 415 | An import format that is not supported, for example `.e57` without the optional `pye57` package. Convert it to LAS or LAZ |
| 401 or 403 | `ATLAS_API_KEYS` is set and the call has no, or a wrong, `X-API-Key`. Only mutating endpoints check it |
| 404 `plot-not-found` | The plot does not exist. With `ATLAS_REPOSITORY=memory` every restart forgets plots, except the three demo plots |
| 500 on `POST /plots` with PostgreSQL only | A polygon with `z` values or an unclosed ring passes the validator but not the database; see the "GEOMETRY CAVEAT" at the top of `data/schemas/schema.sql` |

## The map

The map is the part of the web app that depends most on the outside world, so it is built to keep
working without it.

### The map is gray or says the basemap is unavailable

The app asks for a basemap style (`VITE_BASEMAP_STYLE_URL`, which defaults to
`https://demotiles.maplibre.org/style.json`, or your own PMTiles file through
`VITE_BASEMAP_PMTILES_URL`). When that request fails, or nothing has loaded after 7 seconds, the app
switches to a **plain ground**: a flat pale green background, with the message "Basemap unavailable —
showing your plot on a plain ground" in the bar at the bottom of the map. Drawing, plots, the satellite
view and the data layers keep working; only the street map is missing. This is how the app behaves
offline, behind a firewall or when the basemap host is down.

To find the cause, open the Network tab and look at the request for the style file:

- **Blocked by a firewall or proxy.** The demo host is a third party. Self-host the basemap: build a
  PMTiles file, upload it to a bucket or a CDN you control, and set `VITE_BASEMAP_PMTILES_URL`. Then
  rebuild the web app.
- **Blocked by the Content-Security-Policy.** In the Docker image the allowed hosts come from
  `ATLAS_BASEMAP_ORIGINS`. See the next section.
- **PMTiles without CORS.** PMTiles are read with HTTP range requests from the browser, so the bucket
  must send `Access-Control-Allow-Origin` for your web origin and expose the `ETag` and `Content-Range`
  headers (`Access-Control-Expose-Headers: ETag, Content-Range`). Without it the console shows a CORS
  error and the app falls back to the plain ground.
- **The style loads but the map has no labels.** Place names come from the glyph files that the style
  points to, not from the app's own fonts. With `VITE_BASEMAP_PMTILES_URL`, the app's built-in style
  (`apps/web/src/components/map/mapStyle.ts`) takes them from `https://demotiles.maplibre.org/font/`,
  the development host, so labels still need that host even when the tiles are your own. If the glyph
  host is blocked, labels disappear while the rest of the map works.

In development, or with `?debug=map` appended to the address, the map object is available in the
browser console as `window.__atlasMap`, which helps when you inspect the style and its sources.

### A basemap or imagery works with `npm run dev` but not in Docker

The web image sends a strict Content-Security-Policy. Anything the page loads from another host must
be named in the container's environment, or the browser blocks it and the console says so:

| Blocked thing | Variable to set when you start the container |
| --- | --- |
| The API | `ATLAS_API_ORIGIN`, for example `https://api.example.org` |
| Basemap style, glyphs, sprites, tiles, PMTiles | `ATLAS_BASEMAP_ORIGINS`, space-separated |
| Satellite or aerial tile hosts (for example `tiles.maps.eox.at`, `basemap.nationalmap.gov`, `data.geopf.fr`, `www.ign.es`, `service.pdok.nl`, `ibasemaps-api.arcgis.com`) | `ATLAS_EXTRA_IMG_SRC` |
| A terrain tile host | `ATLAS_EXTRA_CONNECT_SRC` and `ATLAS_EXTRA_IMG_SRC` |

Use only the hosts of the providers you actually enable. `GET /api/v1/imagery/providers` lists them
with their licenses and whether each one needs a key. Do not add `'unsafe-eval'` to the policy to make
something work; see the notes at the top of `infra/docker/nginx.conf`.

### The satellite view is blank or a provider is "unavailable"

- A provider that needs a key (Esri World Imagery) is returned with `available: false` until the API
  has `ESRI_API_KEY`. The settings page shows it greyed out, and the app uses the recommended provider
  that works.
- Some providers cover one country only, for example USGS for the United States. Outside it the tiles do
  not exist. The API lists the providers that cover the requested country first, and the web app asks
  with the plot's country.
- Tiles stop at the provider's `max_zoom`. Beyond it the map stretches the last level, so imagery looks
  blurry rather than missing.
- The free EOX and national services are rate limited or provided as is. A burst of requests can fail
  for a while; for production traffic use a self-hosted copy or a service with an agreement.
- Imagery shown on screen is not data you may analyze. Esri World Imagery is display only. See
  [MAP_LICENSES.md](../licensing/MAP_LICENSES.md).

### The map says my browser does not support WebGL

The map needs WebGL, and without it the app shows "Your browser does not support WebGL, which the map
needs." in place of the map. The rest of the app (results, species, simulation, reports) does not need it.

- Turn on hardware acceleration in the browser settings, update the graphics driver, and check
  `about:gpu` (Chrome) or `about:support` (Firefox).
- In a virtual machine, a container or a CI runner there is often no GPU. Chromium can render WebGL in
  software: start it with `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`. The
  screenshot script uses these flags ([images/README.md](../images/README.md)).
- Some privacy extensions and enterprise policies disable WebGL. Try a clean browser profile.

### Fonts look wrong, or the browser contacts a font host

The interface fonts (Space Grotesk, IBM Plex Sans and IBM Plex Mono) are installed from `@fontsource`
packages and ship inside the web build, under the SIL Open Font License. The app does not load fonts
from Google, so it works offline and the font host never learns that someone opened it. If fonts
are missing:

- run `cd apps/web && npm install` again, so that the `@fontsource/*` packages are present;
- look for an `@import` of an external font in your own styles, which would be blocked by the
  Content-Security-Policy and should be replaced by a `@fontsource` import;
- remember that map labels use the glyphs of the map style, a separate thing (see above).

### The browser reports a CORS error

The API only answers browsers whose origin is in `ATLAS_CORS_ORIGINS`. The default list holds
`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:4173`, `http://127.0.0.1:4173` and
`http://localhost:8080`. An origin is the scheme, host and port together, so `http://localhost:3000`,
`http://[::1]:5173` and `https://atlas.example.org` are all different and must be listed:

```bash
ATLAS_CORS_ORIGINS=https://atlas.example.org,http://localhost:5173
```

Restart the API after changing it. Other things worth knowing:

- The API allows the methods `GET`, `POST`, `DELETE` and `OPTIONS` and the headers `Content-Type`,
  `X-API-Key` and `X-Request-ID`. A proxy or a client that adds another header triggers a failed
  preflight request.
- The API does not use cookies, so credentialed requests are off. List your origins rather than using `*`
  outside local work.
- A browser also reports "CORS error" when the API is down, or answered 500 before the CORS headers
  were added, or when a gateway returns its own error page. Check the status and body in the Network
  tab and the API log before you change the origin list.
- A PMTiles bucket needs its own CORS rule, separate from the API's (see above).

## PostgreSQL

| Symptom | Likely cause and fix |
| --- | --- |
| `relation "plots" does not exist` | The schema was not applied. Run `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/schemas/schema.sql`. The API never creates tables |
| The compose database has no tables after you changed the schema | The init script runs only when the data volume is empty. Apply the file by hand, or remove the volume with `docker compose down -v` (this deletes the data) |
| `permission denied to create extension "postgis"` | Enable PostGIS once as an administrator; on a managed service use its extension page. The application role does not need to create extensions |
| `type "geometry" does not exist` | PostGIS is not installed in this database. The server needs the PostGIS packages and `CREATE EXTENSION postgis` |
| `ON DELETE SET NULL (column list)` syntax error | PostgreSQL older than 15. The schema needs 15 or newer |
| A check constraint violation from the API | The database is stricter than the in-memory repository on purpose (a certified estimate, an exact public centroid, coordinates in an audit event are refused). Fix the code that wrote the record; do not loosen the constraint. See [testing the schema](testing.md#testing-the-postgresql-schema) |

## Documentation and CI

| Symptom | Likely cause and fix |
| --- | --- |
| The Docs workflow fails on a link | A relative link or `#anchor` does not resolve. The offline check is blocking, and anchors are matched against the heading text as GitHub writes it (lower case, punctuation removed, spaces turned into hyphens), so renaming a heading breaks the links to it |
| markdownlint fails on line length | Prose lines are limited to 120 columns; tables, code blocks and headings are exempt |
| `ruff format --check` flags a `.md` file | The repository formats Python code blocks in Markdown. Run `python3 -m ruff format <file>` |
| The `PostgreSQL schema` job fails | Either `schema.sql` and `postgres.py` disagree, or a constraint changed. The failing line names the check. Reproduce it with the commands in [testing](testing.md#testing-the-postgresql-schema) |
| The `Docker build` job fails at the health check | Start the image locally and read its log: `docker run --rm -p 8000:8000 -e ATLAS_MODE=demo agricarbon-atlas-api` |
| Dependabot opens many pull requests | Updates are grouped by ecosystem and by map stack in `.github/dependabot.yml`; review the groups, not each package |

## Still stuck

Search the issues and discussions first, then ask in Discussions (Q&A) with the exact error, the
command, your operating system, and the output of `curl http://localhost:8000/api/v1/health`. Never
paste a real farm boundary, an API key or a `.env` file. Security and privacy problems go through
[SECURITY.md](../../SECURITY.md), not a public issue.
