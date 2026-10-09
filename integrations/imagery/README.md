# imagery

Satellite and aerial imagery for the **Satellite** view of the web map. This integration is **configuration and
documentation, not a Python adapter**: the API never fetches a tile. It serves the list of providers (with licence,
attribution, coverage and a tile URL), and the visitor's browser loads the tiles from the provider. This README is where
CLAUDE.md principle 6 is met for imagery: source, licence, attribution, key handling, rate limits, caching and failure
handling are stated for every provider, and the endpoints come from configuration and environment variables, never from
literals in application code.

Imagery here is for **viewing**. Nothing is stored, no calculation reads a tile, and the tree-cover detection works on
Sentinel-2 vegetation data from the STAC adapters, not on these pictures.

## Providers

Configured in [`config/imagery/providers.yaml`](../../config/imagery/providers.yaml) (version 0.1.0, verified from each
provider's own terms on 2026-10-05). The full quotations, sources and what could not be confirmed are in the
[research note](../../docs/research/imagery-providers.md); the licence rows are in
[`DATA_LICENSES.md`](../../docs/licensing/DATA_LICENSES.md) and [`MAP_LICENSES.md`](../../docs/licensing/MAP_LICENSES.md).

| Id | Source (tile host) | Coverage | Detail | Max zoom | Key | Licence | Commercial use | Analysis allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `eox-s2cloudless-2016` | EOX Sentinel-2 cloudless (`tiles.maps.eox.at`) | Global | 10 m, 2016 | 14 | none | CC BY 4.0 | yes | yes |
| `eox-s2cloudless-2017` | EOX Sentinel-2 cloudless | Global | 10 m, 2017 | 14 | none | CC BY 4.0 | yes | yes |
| `eox-s2cloudless-2025` | EOX Sentinel-2 cloudless | Global | 10 m, 2025 | 14 | none | CC BY-NC-SA 4.0 | **no** | review terms |
| `usgs-imagery-only` | USGS The National Map (`basemap.nationalmap.gov`) | United States | NAIP, 0.6 to 1 m | 16 | none | Public domain | yes | yes |
| `ign-france-orthophotos` | IGN Géoplateforme (`data.geopf.fr`) | France | 20 cm | 19 | none | Licence Ouverte 2.0 | yes | yes |
| `ign-spain-pnoa` | IGN España PNOA (`www.ign.es`) | Spain | 25 to 50 cm | 19 | none | CC BY 4.0 scne.es | yes | yes |
| `pdok-luchtfoto` | PDOK, Beeldmateriaal Nederland (`service.pdok.nl`) | Netherlands | 8 cm | 21 | none | CC BY 4.0 | yes | yes |
| `esri-world-imagery` | Esri World Imagery (`ibasemaps-api.arcgis.com`) | Global | 15 m to 3 cm, varies by place | 19 | `ESRI_API_KEY` | Esri Master License Agreement (proprietary) | review terms | **no, display only** |

`default_by_country` recommends one provider per country: the United States, France, Spain and the Netherlands get their
national orthophotos, and every other country, India included, gets `eox-s2cloudless-2016`. A country is mapped only
where the provider covers it **and** is keyless, openly licensed and allows analysis. Esri is never the default, because
it needs a key, restricts commercial use and forbids automated analysis; a deployer who holds an Esri licence may set
`default: esri-world-imagery` for sharper display-only imagery. India has no verified open high-resolution tile
service, and Google and Bing imagery cannot be used through direct tile URLs, so neither is listed.

## Where it is configured

| What | Where |
| --- | --- |
| Providers, licences, attributions, `default_by_country` | `config/imagery/providers.yaml` |
| Serving the list, filling in keys | `apps/api/app/services/imagery.py`, `GET /api/v1/imagery/providers?country=XX` |
| The Esri key | `ESRI_API_KEY` in `.env` (API setting) |
| Which provider is shown | The recommendation for the country; the user's choice in Settings, "Map imagery" (stored in the browser) |
| A fixed tile source for a deployment | `VITE_SATELLITE_TILES_URL` and `VITE_SATELLITE_ATTRIBUTION` (web build), shown as "Configured imagery" |
| Which hosts the browser may contact | `ATLAS_EXTRA_IMG_SRC` and `ATLAS_EXTRA_CONNECT_SRC` of the nginx image (the image defaults list the hosts above) |

The web app reads the list once per country and session; the API reads the file once per process, so restart the API
after editing it.

## Attribution

Every provider carries the attribution text it requires. The web app shows it in the map's own attribution bar while
the Satellite view is on, next to the basemap's, and the Settings page shows each provider's licence and whether analysis
is allowed. Do not shorten or hide it. Some strings are composed from the licence requirement where the provider
mandates no verbatim text (IGN France, IGN Spain, PDOK); the YAML `notes` say so and ask deployers to add the survey
date where it is known. The EOX layers show their year in the name, because a 2016 mosaic does not show a plantation made
in 2020.

## Licence and the analysis rule

`analysis_allowed` answers one question: may segmentation, machine learning or other automated extraction run on these
tiles? `true` for the open providers, `false` for Esri World Imagery, `review-terms` where the terms were not
conclusive. Display-only providers stay `false` or `review-terms`, and a data-quality test enforces that. Run tree
detection on imagery you own, or on a provider with `analysis_allowed: true`. The QGIS plugin repeats this warning for
the user's own segmentation workflow. A tile source set through `VITE_SATELLITE_TILES_URL` is `review-terms`: its
licence is the deployer's to check.

## Keys

- **Never in the repository.** The YAML holds `${ESRI_API_KEY}` in the URL, not a value. A test fails on a literal key or
  secret query parameter.
- **How the API fills it in.** `ESRI_API_KEY` comes from the API's settings (which also read `.env`). Any other
  `${..._KEY}` or `${..._TOKEN}` placeholder is read from the process environment, except the names the application uses
  for another integration (`LLM_API_KEY`, `USDA_NASS_API_KEY`, and so on), so a typo or a bad pull request cannot
  publish those secrets. The value is URL-encoded and never logged.
- **Missing key.** The provider is returned with `available: false`, `url: null` and `unavailable_reason` ("Set
  ESRI_API_KEY to enable"). An unfilled `${...}` is never sent to a client, and the web app does not offer an
  unavailable provider.
- **The key reaches the browser.** The tile URL contains it, so anyone who opens the Satellite view can read it. Use a
  referrer-restricted, basemap-only key and rotate it if it leaks. Do not use a key with other privileges.

## Rate limits and caching

The API does not proxy or cache tiles, so its own rate limit covers only the small provider list. The browser requests
tiles from the providers directly, and only while the Satellite view is on. That has two consequences: each provider's
own limits apply to your visitors, and **the provider sees the visitor's IP address and which map tiles they view**
(an approximate area, never a plot boundary). A deployment that cannot accept that should serve its own tiles.

| Provider | What is known |
| --- | --- |
| EOX | The free service is "as is", under heavy load and rate limited; EOX recommends a service-level agreement or a self-hosted mosaic for production. Copying the tiles needs EOX's written confirmation of the licence first |
| USGS | No fair-use or rate-limit policy was found. For bulk analysis, use the NAIP source data instead of harvesting tiles |
| IGN France | The WMTS tile service is free and outside the documented rate limits of the Géoplateforme |
| IGN Spain | No conditions on fees; the credit must be visible on the map |
| PDOK | Free for all uses; no fair-use policy was confirmed |
| Esri | Governed by the deployer's ArcGIS Location Platform account and Esri's terms. Harvesting, redistributing and self-hosting Esri tiles is prohibited |

Tiles are cached only by the browser's normal HTTP cache. Do not store or redistribute tiles.

## Failure handling

The Satellite view is optional: drawing, plots, NDVI cells, detected tree cover and imported trees work on the plain map.

| Failure | What happens |
| --- | --- |
| The providers file is missing or invalid | `GET /imagery/providers` answers 500 `imagery-providers-unavailable` (the server log says why); the Satellite switch stays unavailable |
| A provider needs a key that is not set | The provider is listed as unavailable with the reason and is never offered |
| The API is offline and no tile URL is configured | The switch is disabled with "Satellite imagery needs the API (or VITE_SATELLITE_TILES_URL)" |
| A provider's tiles keep failing (six failed requests) | The attribution bar says "Satellite tiles could not be loaded — showing the plain map" and the basemap shows underneath |
| The basemap style cannot be loaded | The plot and the data layers are drawn on a plain ground colour |
| The user zooms beyond `max_zoom` | MapLibre over-zooms the last level instead of requesting tiles that do not exist |

## Adding or changing a provider

1. Read the provider's own terms. Add an entry to `config/imagery/providers.yaml` with every field (the data-quality test
   lists them): `url` as an XYZ template with `{z}/{x}/{y}`, `max_zoom`, `coverage`, licence and its URL, attribution,
   `requires_key`, `commercial_use`, `analysis_allowed`, `open_data`, `verification_status`, `sources` (https links) and
   `notes` that say what you could not confirm.
2. Put a key in the URL only as `${NAME}` with a name that ends in `_KEY` or `_TOKEN`, and document the variable in
   `.env.example`.
3. Add the provider to the imagery tables of `docs/licensing/DATA_LICENSES.md` and `docs/licensing/MAP_LICENSES.md`.
4. Add its tile host to `ATLAS_EXTRA_IMG_SRC` and `ATLAS_EXTRA_CONNECT_SRC` (the image defaults in
   `infra/docker/Dockerfile.web`, or the deployer's environment); otherwise the Content-Security-Policy blocks the tiles.
5. Map a country in `default_by_country` only if the provider is keyless, open, covers the country and allows analysis.
6. Run the tests below, then look at the layer in the running app: the research could request single tiles but could not
   inspect their content.

## Tests

```bash
python3 -m pytest tests/data-quality/test_imagery_providers.py apps/api/tests/test_imagery_api.py -q
cd apps/web && npm run test -- --run src/lib/imagery.test.ts
```

`tests/data-quality/test_imagery_providers.py` guards the file: required fields and vocabulary, https and no literal keys,
licence and attribution present, open-data providers allow commercial use and analysis, Esri and the non-commercial EOX
mosaic stay display-only, every default is keyless, open and covers its country, the global default is not Esri, and no
provider with unconfirmed terms ships in production. `apps/api/tests/test_imagery_api.py` covers the endpoint, key
substitution and the reserved names; `src/lib/imagery.test.ts` covers the browser's choice of provider.

## Links

- [Imagery providers research note](../../docs/research/imagery-providers.md)
- [Map software and imagery licences](../../docs/licensing/MAP_LICENSES.md)
- [Data licences](../../docs/licensing/DATA_LICENSES.md)
- [Mapping architecture](../../docs/architecture/mapping-architecture.md)
- [Integrations overview](../README.md)
