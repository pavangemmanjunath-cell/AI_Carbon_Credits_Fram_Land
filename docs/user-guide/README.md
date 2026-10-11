# User guide

CarbonCreditBuy lets you mark your land on a map, say which trees grow on it, and see a cautious estimate of how much
carbon those trees may be taking out of the air each year. It also shows what evidence you would still need before you
could approach a carbon or environmental programme. This guide is written for farmers, landowners, extension workers
and advisors. You do not need a technical background.

> **Read this first.** Every number in the app is a *scenario estimate* with a range. It is not an issued carbon
> credit, it is not money you will receive, and it is not a decision that you qualify for any programme. Please do not
> sign an agreement, take a loan or change how you use your land because of this app alone. Use it to ask better
> questions of an advisor or a programme office.

![The My land page with a demo plot: the left menu, the four-step strip, the map with its Mark your land toolbar, three result cards under the map and the Selected plot details panel at the right.](../images/screenshots/02-workspace.png)

The screenshots in this guide show demo data, a made-up farm. The numbers in them are scenario estimates, not issued
carbon credits.

## The four steps

The strip at the top of the app shows the same four steps that this guide follows.

| Step | What you do | Read |
| --- | --- | --- |
| 1. **Select land** | Find your place on the map and mark your field: draw a boundary, draw a row of trees, drop a pin with a size, type coordinates or import a file | [Mark your land](mark-your-land.md) |
| 2. **Add trees** | Say which trees you have, how many, and the year they were planted | [Getting started, step 2](getting-started.md#step-2-add-your-trees) |
| 3. **Analyze** | The app reads open satellite, land cover, climate and soil data for your plot | [Getting started, step 3](getting-started.md#step-3-the-app-analyzes-your-plot) |
| 4. **Carbon potential** | See the estimate, its range, the evidence you still lack and programmes to look into | [Results explained](results-explained.md) |

## Three numbers, kept apart

The **Carbon potential** page shows three different kinds of value. The app never adds them together, because they are
not the same kind of thing.

| Value | What it is | Where you see it |
| --- | --- | --- |
| **Environmental benefit** | Estimated annual carbon removal in tCO₂e/yr (tonnes of carbon dioxide equivalent per year), as a low, central and high value | The **Estimated carbon removal** card on the **My land** page and the **Carbon potential** page |
| **Indicative carbon value** | What that removal could be worth at three illustrative prices. A scenario, not a credit and not guaranteed revenue | **Carbon potential** page |
| **Other farm income** | Fruit, timber, intercrops and incentives, from your own records. The app lists the kinds of income but does not calculate them | **Carbon potential** page |

## Pages in this guide

| Page | Read it when you want to... |
| --- | --- |
| [Getting started](getting-started.md) | Open the app, tell demo data from real data, find your way around, and walk through the four steps |
| [Mark your land](mark-your-land.md) | Find your place, mark your field with **Boundary**, **Tree line**, **Pin + size**, **Coordinates** or **Import file**, fix mistakes, and switch between **Map** and **Satellite** |
| [Import data](import-data.md) | Bring in a boundary file, detected trees or a point cloud, and use the **Data** page to see what you have added |
| [Satellite imagery](satellite-imagery.md) | See which pictures you get in each country, how sharp and how old they are, who owns them, and why they are for looking and not for measuring |
| [Results explained](results-explained.md) | Understand every card on the **Carbon potential** page, and why an estimate is not a credit |
| [AI agents](ai-agents.md) | Let a small team of helpers explain one of your plots, and see how they relate to the numbers you see |
| [Tree age](tree-age.md) | See what carbon trees of a given age hold, and which programmes and laws treat them differently |
| [Simulation](simulation-lab.md) | Try "What if I plant more trees?" and compare India, the United States and the EU |
| [Reports](reports.md) | Print or save a report to show an advisor, and keep or share it safely |
| [QGIS plugin](qgis-plugin.md) | Send a field polygon from QGIS to the app, if you already use QGIS |
| [FAQ](faq.md) | Find a quick answer, including privacy, licences, languages, units and what is not yet built |

The ideas behind the app are explained in
[carbon credit vs carbon estimate](../concepts/carbon-credit-vs-estimate.md) and the
[privacy pages](../privacy/farmer-data.md). Programme notes for each region are in the
[India](../regions/IN/README.md), [United States](../regions/US/README.md) and
[European Union](../regions/EU/README.md) pages.

## Good to know before you start

- **Demo data or real data.** The app can run on example data. In that case the satellite, climate and soil values are
  made up. [Getting started](getting-started.md#is-this-real-data) shows how to tell.
- **Languages.** The interface is available in English, हिन्दी, ಕನ್ನಡ, Deutsch, Français and Español. Use the language
  box at the top right. Some longer texts, such as the "In plain words" paragraph, the printed report, the AI agent
  messages and the rules on the **Tree age** page, stay in English in this version.
- **Units.** Areas are shown in hectares or acres (see **Settings**). Carbon is always in tCO₂e/yr. Prices are in the
  currency of the country you chose: ₹, $ or €.
- **No sign-in.** This version has no accounts. Whoever can open the copy of the app you use can see the plots stored
  on it. See [privacy in the FAQ](faq.md#privacy-and-your-data).
- **Phones.** On a small screen the left menu is closed. Open it with the **Menu** button at the top left. Small
  screens hide the layers panel and the four-step strip to leave room for the map.
- **Screenshots** in this guide show example data, not a real farm.

## Getting help

Look in the [FAQ](faq.md) first. Ask a question in the project's Discussions, or open an issue with one of the
templates if something looks wrong. If you think your location data is exposed, do not post it publicly; follow
[SECURITY.md](../../SECURITY.md). Anyone can help improve these pages: see [CONTRIBUTING.md](../../CONTRIBUTING.md).
