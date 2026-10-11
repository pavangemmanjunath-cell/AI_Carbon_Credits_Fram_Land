# QGIS plugin

If you already work in QGIS, the CarbonCreditBuy plugin lets you send a field polygon to the app's server without
leaving QGIS. It can also count the trees that an AI segmentation plugin found inside the field, and it shows the same
carbon potential results in a QGIS window. This page is the short version. The
[plugin README](../../integrations/qgis-plugin/README.md) has every setting, the troubleshooting table and the
developer notes.

> **Read this first.** Every number the plugin shows is a *scenario estimate* with a range. It is not a carbon credit,
> it is not money you will receive, and it is not a decision that you qualify for any programme. The plugin shows
> `certified: false` and "Scenario estimate only. This is not an issued carbon credit." on every result. The plugin is
> **experimental** (version 0.1.0): check what it does in your own QGIS before you rely on it.

## What you need

- **QGIS 3.28 or newer** in the 3.x series. QGIS 4 is not supported yet.
- **A CarbonCreditBuy server.** This is the API of your own copy of the app, for example
  `http://localhost:8000/api/v1` on your own computer, or the address someone gave you. If it asks for an API key,
  you need that too.
- **A field polygon** in a QGIS layer, one polygon per field.
- For the tree count: **a layer of detected tree crowns**, for example the result of an AI segmentation plugin, over
  imagery that you are allowed to analyse (see [imagery](#imagery-check-the-licence-first)).

## Install

1. Get the ZIP file `carboncreditbuy_qgis-0.1.0.zip` from whoever runs your copy of the app, or build it yourself from
   the repository with `make package` in the folder `integrations/qgis-plugin` (the
   [README](../../integrations/qgis-plugin/README.md) explains how).
2. In QGIS choose **Plugins > Manage and Install Plugins ... > Install from ZIP**, pick the file and press
   **Install Plugin**.
3. Choose **Plugins > CarbonCreditBuy > Settings ...**, type the API address (and the key, if you have one) and press
   **Test connection**. A line starting with "Connected" means it works. Press **Save**.

The plugin adds an **CarbonCreditBuy** toolbar and menu. The default country in Settings (`IN`, `US` or an EU country
code such as `DE`) is only a starting point for the dialogs.

## Try it in five steps

1. **Select your field.** Activate the layer that holds your field boundary, use the **Select Features** tool and click
   the field. Exactly one polygon must be selected. It must be one part with at most 500 vertices, like the polygons the
   [web app accepts](mark-your-land.md#boundary).
2. **Count the trees.** Choose **Count trees from segmentation layer**. If this field is not on the server yet, the
   plugin offers to send it first. Pick the layer with the detected crowns, set the minimum confidence if the layer has
   a score (the default is 0.5), press **Preview count**, then choose the tree type and the year the trees were planted
   and press **Send inventory**. A crown counts as one tree when its centre lies inside your field. Check the preview
   against the imagery: segmentation can merge or miss trees.
3. **Estimate the carbon.** Choose **Estimate carbon (scenario)**, pick the kind of activity for the programme
   screening and read the window that opens.
4. **Ask the AI agent team** (optional). Choose **Run AI agent team** and read the transcript. If the server is older
   and does not have the agent team, the plugin says so.
5. **Save your QGIS project.** The link between the project and the plot (the plot ID and a few non-spatial details) is
   stored in the project file.

**Send selected polygon to CarbonCreditBuy** does only the first part of step 2: it creates the plot and shows the
analysis of land cover, vegetation, climate and soil.

A plot made this way also shows up in the web app, on the **Data** page, with the source **QGIS plugin**. Once it has
tree details, open **Results** next to it to see the same [Carbon potential page](results-explained.md) as for any
other plot.

## Three numbers, kept apart

The results window follows the rules of the app. The values are never added together.

| Value | What it is | Where you see it |
| --- | --- | --- |
| **Environmental benefit** | Estimated annual carbon removal in tCO₂e/yr, as low, central and high | Section 1 of the carbon window |
| **Indicative carbon value** | What that removal could be worth at illustrative prices. A scenario, not a credit and not guaranteed revenue | Section 2 |
| **Other farm income** | Fruit, timber and other income from your own records. Listed, not calculated | Section 3 |

The window also lists programmes to look into (an initial screening, not an eligibility decision) and the evidence you
still lack. [Results explained](results-explained.md) describes each of these in plain words, and
[carbon credit vs carbon estimate](../concepts/carbon-credit-vs-estimate.md) explains why an estimate is never a credit.

## What stays on your computer

- The plugin talks only to the server address in Settings. It has no tracking and calls no other service.
- The server receives your field polygon, a plot name, the country, and later the tree count, tree type and planting
  year. Other attributes of your layers, layer names and imagery are never sent.
- The QGIS project keeps the plot ID and a fingerprint of the polygon, not its coordinates. The QGIS log records only
  which request was made and whether it worked.
- The API key is saved as plain text in your QGIS user profile. If the address uses plain `http` to another computer,
  the plugin warns you, because the polygon and the key would travel unencrypted. Prefer `https`.

See [how the app handles your data](../privacy/farmer-data.md) for what the server does with a polygon.

## Imagery: check the licence first

AI segmentation reads the pixels of your imagery. Commercial basemaps such as Google, Bing and Esri imagery typically
forbid automated feature extraction, so do not segment them unless your licence says you may. Use open imagery or your
own drone, aerial or satellite images. Free Sentinel-2 images are open but their 10 m pixels are too coarse for
individual trees. The plugin does not download imagery and does not check licences. The project's note on
[imagery providers](../research/imagery-providers.md) lists which providers allow analysis. The same rule holds in the
web app: its **Satellite** view is for looking, and [Satellite imagery](satellite-imagery.md#viewing-versus-analysing)
explains the difference.

## Good to know

- The tree count is an estimate made by a model. The server's carbon estimate depends strongly on the tree type and
  on the year the trees were planted, and you enter both.
- Fields with several parts have to be split first (**Vector > Geometry Tools > Multipart to Singleparts**), and
  polygons with more than 500 vertices have to be simplified.
- Everything is in English. Only one request runs at a time, and a request that was sent cannot be cancelled.

## Getting help

Start with the troubleshooting table in the [plugin README](../../integrations/qgis-plugin/README.md#troubleshooting).
If something looks wrong, open an issue with one of the templates and describe what you did, but do not post your field
coordinates. If you think location data is exposed, follow [SECURITY.md](../../SECURITY.md). Anyone can help improve
the plugin and these pages: see [CONTRIBUTING.md](../../CONTRIBUTING.md). The plugin's source code is licensed under
GPL-2.0-or-later, while the rest of the project is licensed under Apache-2.0.
