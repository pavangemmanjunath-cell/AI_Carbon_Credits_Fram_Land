# CarbonCreditBuy for QGIS

A QGIS 3 plugin that connects your QGIS project to a CarbonCreditBuy API (see the
[project docs](../../docs/README.md)). Select a field polygon, count the tree crowns that an AI segmentation plugin
found inside it, and get a *scenario estimate* of the carbon those trees may remove each year.

> **Scenario estimate only. This is not an issued carbon credit.** Every result window shows `certified: false`.
> The plugin cannot issue, verify or certify anything. The three kinds of value it shows (environmental benefit,
> indicative carbon value and other farm income) are always kept apart and are never added together.

Status: **experimental, version 0.1.0.** Requires QGIS 3.28 or newer in the 3.x series (Qt 5) and a running
CarbonCreditBuy API. The plugin uses nothing but QGIS and the Python standard library.

## What it does

The plugin adds a toolbar and a **Plugins > CarbonCreditBuy** menu with these actions.

| Action | What happens | API calls |
| --- | --- | --- |
| **Send selected polygon to CarbonCreditBuy** | Takes the selected field polygon, converts it to EPSG:4326, checks it, and creates a plot on your server and analyzes it (land cover, vegetation, climate, soil) | `POST /plots`, `POST /plots/{id}/analyze` |
| **Count trees from segmentation layer** | Counts the crowns of a segmentation layer whose centre lies inside the selected field, with an optional confidence filter, and records the count as a tree inventory | `GET /species`, `POST /plots/{id}/trees` |
| **Estimate carbon (scenario)** | Shows the estimated annual carbon removal (tCO₂e/yr) as low, central and high, indicative value scenarios, other farm income, programme screening and evidence readiness | `POST /plots/{id}/carbon-estimate`, `GET /plots/{id}/market-scenario`, `GET /plots/{id}/policy-eligibility` |
| **Run AI agent team** | Runs the server's agent team on the plot and shows the transcript | `POST /plots/{id}/agents/run` |
| **Set current plot ...**, **Unlink current plot** | Link the project to a plot that already exists on the server, or forget the link | `GET /plots/{id}` |
| **Add current plot as layer** | Fetches the plot polygon and adds it to the project as a memory layer | `GET /plots/{id}` |
| **Export selected field as GeoJSON ...** | Saves the polygon exactly as it would be sent (EPSG:4326, no attributes) | none |
| **Settings ...** | API address, API key, default country and timeout, with a connection test | `GET /health` |

All network calls run in a background QGIS task, so QGIS stays responsive. Results open in a window that you can copy
as text or save as HTML. Short notices go to the message bar and the QGIS log panel (tab **CarbonCreditBuy**).

## Requirements

- QGIS 3.28 LTR or a newer 3.x release. QGIS 4 (Qt 6) is not supported yet.
- A CarbonCreditBuy API that your computer can reach. To run one locally, follow the
  [developer setup guide](../../docs/developer-guide/setup.md); the default address is `http://localhost:8000/api/v1`.
- Optional: an API key, if your server asks for one on write requests.

## Install

1. Build the ZIP archive. From this directory run `make package` (or `python scripts/package.py`). The result is
   `dist/carboncreditbuy_qgis-0.1.0.zip`. The archive is a build artifact and is not committed.
2. In QGIS open **Plugins > Manage and Install Plugins ... > Install from ZIP**, choose the file and press
   **Install Plugin**.
3. Open the **Installed** tab and check that **CarbonCreditBuy** is ticked. The toolbar and the menu appear.

For development, `make link` symlinks the plugin folder into your QGIS profile, so you can edit and reload it (for
example with the Plugin Reloader plugin). `make help` lists the other shortcuts.

## Configure

Open **Plugins > CarbonCreditBuy > Settings ...**.

| Setting | Default | Notes |
| --- | --- | --- |
| API base URL | `http://localhost:8000/api/v1` | Only `http` and `https`. A bare `http://host:8000` gets `/api/v1` added. No credentials in the URL |
| API key | empty | Optional. Sent as the `X-API-Key` header. Leave empty if your server does not ask for one |
| Default country | `IN` | `IN`, `US` or an EU member state code such as `DE`, `FR`, `ES` or `IT`. Used as the default in the send dialog |
| Request timeout | 30 s | Per request. Analysis and the agent team may take up to four times as long |

Press **Test connection** to call `GET /health`. If the address uses plain `http` to another computer, the dialog warns
you, and the plugin asks for confirmation before it sends a polygon.

**About the API key.** QGIS stores plugin settings in your user profile, and this version keeps the key there as plain
text. That is acceptable for a key on your own machine with limited rights. A better option for shared computers is the
QGIS authentication manager (**Settings > Options > Authentication**), which encrypts secrets with a master password.
This version does not read keys from the authentication manager yet. On a shared computer, leave the key empty and
protect the server by other means, or use a key that can be revoked.

## Workflow with an AI segmentation plugin

The plugin does not segment images itself. It works with the output of any segmentation tool that produces a polygon or
point layer with one feature per detected tree crown.

1. **Load imagery that you may analyse.** Read the [licensing warning](#imagery-licensing-read-this-before-you-segment)
   first. Use open imagery or your own drone, aerial or satellite imagery, at a resolution that shows single crowns.
2. **Run your AI segmentation plugin** on the imagery, for example with the prompt `tree`. Keep the resulting layer in
   the project. Most tools add a score or confidence field.
3. **Select your field polygon.** Make the layer that holds your field boundary the active layer, choose the
   **Select Features** tool and click the field. Exactly one polygon must be selected. It must be a single part with at
   most 500 vertices (use **Multipart to Singleparts** or **Simplify** if QGIS says otherwise).
4. **Run Count trees from segmentation layer.** If this field has not been sent yet, the plugin offers to send it first.
   In the dialog:
   - choose the **Tree-crown layer**; the confidence field is detected automatically (names such as `score`,
     `confidence`, `prob` or `probability`) and you can change or clear it;
   - set the **Minimum confidence** (default 0.5; use the same scale as the field, and watch the range hint);
   - press **Preview count** and compare the number with the imagery;
   - choose the **Species** from the server's list and enter the **Year planted**;
   - press **Send inventory**. The inventory is stored with the measurement source `model-estimated`.
5. **Run Estimate carbon (scenario).** Choose the activity for the programme screening and read the results window:
   the three values, the programme screening and the evidence you still lack.
6. **Run AI agent team** to let the server's agents assess the plot, and read the transcript before you use it.

Steps 4 to 6 need the plot to be linked to the project. The link (plot id and a few non-spatial fields) is saved in the
QGIS project file, so save the project to keep it.

### How the count works

A crown counts as one tree when its **centre** (centroid) lies inside the field polygon. A centre exactly on the
boundary counts as inside; a centre inside a hole of the polygon does not count. The plugin transforms the field once
into the CRS of the crown layer, so the two layers may use different CRSs.

With a confidence field and a threshold, a crown is counted only when its confidence is a number greater than or equal
to the threshold. Crowns without a usable confidence value are **not** counted, and the dialog reports how many there
were. Without a confidence field, every crown inside the field is counted.

Segmentation can merge neighbouring crowns, split one crown in two or miss small trees. The plugin shows the density
(trees per hectare) and warns when it exceeds the maximum density the server lists for the species, but the count is
only as good as the segmentation. Check it against the imagery before you send it.

## What is sent, and where

The plugin talks only to the API address in Settings. There is no telemetry and no third-party service.

| Step | Sent to your API | Never sent |
| --- | --- | --- |
| Send polygon | The polygon (GeoJSON, EPSG:4326), the plot name, the country if you chose one, and the source label `qgis-plugin` | Other attributes, layer names, imagery |
| Count trees | Species id, tree count, planting year, measurement source `model-estimated` | Crown geometries, scores, the threshold |
| Estimate carbon | The plot id (in the URL) and, for the screening, the activity | Anything else |
| Run AI agent team | The plot id, the plan `full-assessment` and the locale `en` | Anything else |

- The server keeps the exact polygon private by default. See the [privacy design](../../docs/privacy/privacy-design.md).
- The QGIS project stores the plot id, name, country, area and a SHA-256 digest of the polygon, never the coordinates.
- The log panel records the method, path, HTTP status and duration of each request. It never records coordinates,
  request or response bodies, API keys or the text of server errors.
- Text from the server is shown as plain text or escaped HTML, and links in results open in your browser only when you
  click them.
- Whether a language model takes part in the agent team is decided by the server, and the transcript says which kind of
  reasoning was used. Project rules say that coordinates are never sent to a language model and that a model never
  computes a carbon number.

## Imagery licensing: read this before you segment

AI segmentation reads the pixels of your imagery, and many imagery licences forbid that.

- Commercial basemaps such as Google, Bing and Esri imagery typically forbid automated feature extraction, machine
  learning and tile copying, even when you may look at them in QGIS. Do not segment them unless you hold a licence that
  says you may.
- Use imagery whose licence allows analysis: open orthophotos (for example USGS NAIP in the United States, or the open
  national orthophotos of France, Spain and the Netherlands) or your own drone, aerial or satellite imagery.
- Sentinel-2 imagery is open, but its 10 m pixels are too coarse to separate individual tree crowns.
- Check whether your segmentation plugin runs on your computer or sends image tiles to an online service.

The plugin does not download imagery and does not check licences. You are responsible for the imagery you analyse. The
project's research note on imagery providers, [imagery providers](../../docs/research/imagery-providers.md), lists the
licence of each provider it looked at, and whether analysis is allowed.

## Estimates, not credits

- Results are scenario estimates with a low-central-high range. They are **not** carbon credits, not money you will
  receive and not a decision that you qualify for any programme.
- The plugin always shows `certified: false`. If a server ever reports another value, the plugin ignores it and warns.
- The three values are separate: environmental benefit (estimated annual carbon removal in tCO₂e/yr), indicative
  carbon value (a price scenario) and other farm income (your own records, listed but not calculated).
- India: Green Credits and carbon credits (CCTS) are separate mechanisms. EU: a CRCF certification is required, and an
  estimate is never automatically certifiable. The programme screening is an initial screen, not an eligibility
  determination.

Read more in [carbon credit vs carbon estimate](../../docs/concepts/carbon-credit-vs-estimate.md).

## Limitations

- **Experimental.** The test suite runs without QGIS, against stand-ins for the parts of PyQGIS that the plugin uses,
  and the dialogs were exercised on a headless Qt. Test the plugin in your own QGIS 3.28+ before you rely on it, and
  please report what you find.
- One field at a time: a single-part polygon with at most 500 vertices. Fields with several parts have to be split.
- The planting year cannot be read from the crowns, so you enter it, and the carbon estimate depends strongly on tree
  age. The species list comes from the server and depends on the country.
- No de-duplication of overlapping crowns, no minimum crown size and no check of the segmentation quality.
- Network access uses the Python standard library, not the QGIS network manager: QGIS proxy settings and the
  authentication manager are not used, redirects are not followed, and only one request runs at a time. A request that
  was sent cannot be cancelled; it ends at the timeout.
- Servers older than this plugin may reject the plot source `qgis-plugin`; the plugin then retries once with `api` and
  says so. A server without the agent team answers 404, and the plugin tells you to update it.
- The API key is stored as plain text in the QGIS profile (see above).
- English only. QGIS 4 is not supported.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| "Could not connect to ..." | Start the API (`make api` in the repository) or correct the address in Settings and press **Test connection** |
| "The server requires an API key" or "rejected the API key" | Enter a valid key in Settings |
| "Select one field polygon first" | Activate the layer with your field, choose **Select Features** and click one polygon |
| "... has N vertices; the API accepts at most 500" | Simplify the polygon (**Vector > Geometry Tools > Simplify**) |
| "... 2 separate parts" | Split the field with **Multipart to Singleparts** and select one part |
| "coordinates outside the valid range" | The layer CRS is wrong: set the correct CRS, or reproject the layer |
| "The crown layer has no field called ..." | Choose an existing numeric field, or clear the confidence field |
| "This server does not offer the AI agent team (HTTP 404)" | Update the CarbonCreditBuy API to a version that has `POST /api/v1/plots/{plot_id}/agents/run` |
| "This plot has no tree inventory yet" | Run **Count trees from segmentation layer** first |

## For developers

```text
integrations/qgis-plugin/
  carboncreditbuy_qgis/   the plugin (this folder is what QGIS loads)
    metadata.txt           plugin metadata for QGIS
    __init__.py            classFactory(iface)
    plugin.py              toolbar, menu and actions        (needs QGIS)
    dialogs.py             Settings, send, count, results   (needs QGIS)
    qgis_helpers.py        settings, project state, layers  (needs QGIS)
    tasks.py               background QgsTask wrapper       (needs QGIS)
    api_client.py          HTTP client for the API          (pure Python)
    geometry.py            GeoJSON checks                   (pure Python)
    crowns.py              crown counting                   (pure Python)
    formatting.py          result pages and error texts     (pure Python)
    workflows.py           multi-call API workflows         (pure Python)
    config.py, version.py, diagnostics.py                   (pure Python)
  tests/                   pytest tests; QGIS is not needed
  scripts/package.py       builds the installable ZIP
  Makefile                 package, test, lint, format, link, clean
```

The modules marked pure Python import nothing from QGIS or Qt, so they are tested directly. The QGIS-dependent modules
are tested against fakes in `tests/qgis_fakes.py`.

```bash
cd integrations/qgis-plugin && make package               # build the ZIP in dist/
cd ../.. && python -m pytest integrations/qgis-plugin/tests -q
```

The dialog and plugin smoke tests in `tests/test_qgis_ui_smoke.py` need PyQt5 and are skipped without it. To run them,
install PyQt5 in a virtual environment and set `QT_QPA_PLATFORM=offscreen`.

The plugin relies on these API fields. If the API changes them, update `api_client.py` and `formatting.py`.

| Call | The plugin sends | The plugin reads |
| --- | --- | --- |
| `POST /plots` | `name`, `country` (optional), `source`, `geometry` | `plot_id`, `name`, `country`, `region`, `area_hectares`, `area_acres`, `source`, `privacy` |
| `POST /plots/{id}/analyze` | `{}` | `mode`, `landcover`, `vegetation`, `climate`, `soil`, `data_quality`, `provenance` |
| `GET /species?country=` | `country` | `id`, `common_name`, `scientific_name`, `max_density_per_ha` |
| `POST /plots/{id}/trees` | `species_id`, `tree_count`, `plantation_year`, `measurement_source` | `inventory_id`, `species`, `tree_count`, `density_per_ha`, `age_years`, `data_quality` |
| `POST /plots/{id}/carbon-estimate` | `{}` (the latest inventory is used) | `estimate_id`, `estimate` (`low`, `central`, `high`, `unit`), `confidence`, `certified`, `disclaimer`, `readiness`, `model`, `methodology`, `provenance` |
| `GET /plots/{id}/market-scenario` | `estimate_id` | `currency`, `scenarios`, `other_income`, `basis` |
| `GET /plots/{id}/policy-eligibility` | `activity` | `programmes` |
| `POST /plots/{id}/agents/run` | `plan`, `locale` | `messages`, `steps`, `guardrails`, `summary`, `reasoner`, `certified` |

Errors are expected as RFC 7807 `application/problem+json`. Missing fields never stop the plugin: the formatters show
"not available" instead. The server's current `PlotCreate.source` accepts `manual-drawing`, `upload` and `api`, so the
plugin falls back to `api` when `qgis-plugin` is rejected with a 422.

## Licence

This folder (`integrations/qgis-plugin/`) is licensed under the **GNU General Public License, version 2 or later**
(`GPL-2.0-or-later`; see [LICENSE](LICENSE)). QGIS plugins run inside QGIS, which is GPL-licensed, and the plugin
imports its Python API, so this subfolder uses a GPL-compatible licence.

The rest of the repository, including the CarbonCreditBuy API and web application, is licensed under Apache-2.0. The
plugin imports no code from the Apache-licensed parts, and they import nothing from the plugin. The two sides exchange
only HTTP requests and JSON, so they remain separate programs: the GPL terms of the plugin do not apply to the API or
the web application, and Apache-2.0 software may call or be called by the plugin over HTTP. This is a summary, not
legal advice. Every Python file here carries an `SPDX-License-Identifier: GPL-2.0-or-later` header. By contributing to
this folder you agree that your contribution is licensed under the same terms.

For the user's view of the plugin, see the [QGIS plugin page](../../docs/user-guide/qgis-plugin.md) in the user guide.
