# Similar platforms and open-source projects — and how AgriCarbon Atlas differs

Research of 2026-10-05/06 for the project brief ("check similar carbon credit sites and GitHub, and how to
differentiate"). The descriptions below are deliberately short and only say what the cited pages show; they are not
reviews, and product details change. Check each source before quoting it.

## What exists

| Name | Kind | What it does (per the sources) | Sources |
|---|---|---|---|
| **Varaha** (India) | Commercial carbon project developer | Works with smallholder farmers in the Global South on nature-based carbon removal, including agroforestry projects (for example in Andhra Pradesh); reported a USD 20 million raise in February 2026 | [TechCrunch, 3 Feb 2026](https://techcrunch.com/2026/02/03/indias-varaha-bags-20m-to-scale-carbon-removal-from-the-global-south/) · [ImpactAlpha](https://impactalpha.com/varaha-scores-4-million-to-help-smallholder-farmers-create-nature-based-carbon-credits/) · [Klimate project page](https://www.klimate.co/project/varaha-andhra-pradesh-agroforestry) |
| **Boomitra** (India / global) | Commercial soil-carbon marketplace | Uses satellite data to support soil-carbon projects with farmers; Earthshot Prize winner 2023; reported the first soil-carbon credit issuance from its India project with Social Carbon | [Earthshot Prize](https://earthshotprize.org/winners-finalists/boomitra/) · [Boomitra](https://boomitra.com/landmark-urvara-issuance-india/) · [Carbon Herald](https://carbonherald.com/boomitra-and-social-carbon-issue-first-soil-carbon-credits-from-india-project/) |
| **Agreena** (EU) | Commercial carbon-certificate programme | Issues carbon certificates for regenerative agriculture practices on arable farms ("AgreenaCarbon") | [Agreena](https://agreena.com/) · [FAO STI portal](https://sti-portal.fao.org/innovations/agreenacarbon-certificates) |
| **Pachama** (US) | Commercial forest-carbon platform | Uses satellite data and machine learning for forest carbon; Verra announced a pilot of digital measurement of forest carbon | [Verra](https://verra.org/worlds-largest-carbon-program-pilots-digital-measuring-of-forest-carbon/) · [Contrary Research](https://research.contrary.com/company/pachama) |
| **Restor** (Switzerland) | Open data platform for restoration | Started by the Crowther Lab at ETH Zürich; maps restoration sites and the restoration potential of places worldwide | [ETH News](https://ethz.ch/en/news-and-events/eth-news/news/2021/06/a-social-network-for-global-ecosystem-restoration.html) · [Restor blog](https://about.restor.eco/blog/restor-new-platform-connects-the-global-restoration-movement-for-the-first) |
| **Global Forest Watch** (WRI) | Open forest-monitoring platform and data | Open maps of tree cover, loss and gain; WRI's open-source `carbon-budget` model computes gross emissions, gross removals and net carbon flux of forests | [Global Forest Watch blog](https://www.globalforestwatch.org/blog/data-and-tools/tree-cover-data-comparison/) · [wri/carbon-budget (GitHub)](https://github.com/wri/carbon-budget) |
| **Open Foris / SEPAL / Collect Earth** (FAO) | Free open-source forest and land monitoring tools | Tools used by countries for forest inventories and land monitoring; won a Google Geo for Good Impact Award | [FAO Open Foris](https://fao.org/in-action/openforis/overview/en) · [FAO news](https://www.fao.org/forestry/newsroom/news-detail/fao-s-open-foris-and-sepal-win-google-geo-for-good-impact-award/en) |
| **CarbonPlan** | Non-profit, open-source research | Open data and code on carbon removal and offsets, e.g. OffsetsDB and a retrospective analysis of compliance forest-offset projects | [carbonplan on GitHub](https://github.com/carbonplan) · [offsets-db-api](https://github.com/carbonplan/offsets-db-api) · [forest-offsets](https://github.com/carbonplan/forest-offsets) |
| **QGIS "AI Segmentation" plugin** | Free desktop plugin | Text-prompted segmentation of imagery into separate polygons with confidence scores (the example the project owner shared) | QGIS Plugin Manager (search "AI Segmentation") |

## Where AgriCarbon Atlas fits

The commercial platforms above run carbon **projects**: they aggregate farmers, apply a registry methodology and sell
credits. The open platforms (Global Forest Watch, Restor, Open Foris, CarbonPlan) map forests, restoration or offsets at
landscape and programme scale. AgriCarbon Atlas sits in a gap between them: a **self-hostable, farmer-facing screening
tool for one plot**, which says honestly what trees on that plot might remove, which programmes or laws could apply,
and what evidence is still missing — before anyone signs a contract.

| | AgriCarbon Atlas | Typical commercial project developer | Typical open monitoring platform |
|---|---|---|---|
| Unit of work | One farmer's plot, tree line or orchard | A project of many farms | A landscape, country or project portfolio |
| Output | Scenario **estimate** with low–central–high range, `certified: false`, provenance | Issued credits after verification | Maps and statistics |
| Money | Indicative value shown **separately** from environmental benefit and other farm income, never summed | Revenue share of credit sales | Not applicable |
| Rules | Config-driven per region (IN/US/EU): Green Credits ≠ CCTS, EU CRCF, and **tree-age rules** (heritage trees, tree pensions, compensatory planting) with sources and verification status | The programme of their methodology | Usually not in scope |
| How land is entered | Draw a boundary, **tree line** (bund/boundary planting), **pin + size**, **typed coordinates**, GeoJSON/KML/CSV, **LAS/LAZ point clouds**, QGIS plugin | Field teams and project tooling | Datasets |
| AI | A small, readable **agent team** that shows who said what, with guardrails; numbers only from engines; an optional LLM may only rephrase and never receives coordinates | Proprietary models | Varies |
| Privacy | Exact boundaries private; generalised public centroids; no coordinates in logs or LLM prompts | Company policy | Mostly public data |
| Licence and hosting | Apache-2.0, runs offline in demo mode, self-hostable (QGIS plugin GPL-2.0-or-later) | Proprietary SaaS | Open, hosted by the organisation |

## What the project deliberately does **not** do

- It does not issue, sell or broker credits, and it never presents an estimate as a credit.
- It does not decide eligibility; programme results are screening only.
- It does not run automated analysis on imagery whose licence forbids it (for example Esri World Imagery is display-only).

See also [tree-age-carbon-rules.md](tree-age-carbon-rules.md), [imagery-providers.md](imagery-providers.md) and
[policy-references.md](policy-references.md).
