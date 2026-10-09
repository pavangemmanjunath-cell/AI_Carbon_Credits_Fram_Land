# Roadmap ideas

The [starter issues](starter-issues.md) are small tasks with a clear finish line. This page holds the larger ideas: the
ones that need a decision from the maintainers or a domain reviewer first, that depend on a source nobody has read yet,
or that are too big for one pull request. They are not commitments and they have no dates. The agreed plan is the
[roadmap](../../ROADMAP.md), and what the project will not do is in its
[scope guardrails](../../GOVERNANCE.md#scope-guardrails).

Every row says what is open today and what to do first. The facts were found by reading the code and the config on
5 October 2026 (version 0.1, not yet released), and some of them will have changed by the time you read this. Open the
files named, and if they differ, say so in your proposal. Every idea in the roadmap's
[unscheduled list](../../ROADMAP.md#beyond-10-unscheduled) is here, except the Indian languages, which are
[starter issue 4](starter-issues.md#4-add-a-ui-language).

## How to propose one

1. Read the row and the pages it links to, then [CONTRIBUTING.md](../../CONTRIBUTING.md) and
   [CLAUDE.md](../../CLAUDE.md).
2. Open a discussion before you write any code. Say which row you mean, what you would do first and who could review
   it. The review groups in [CODEOWNERS](../../.github/CODEOWNERS) are described in the
   [starter issues](starter-issues.md#how-to-take-one). Work that needs a domain reviewer waits until one agrees to
   review it.
3. Where a row says **Decide first**, the maintainers decide before anyone writes code. An architecture decision is
   recorded as an ADR ([governance](../../GOVERNANCE.md#decision-making)); any other decision is recorded in the
   discussion.
4. When there is agreement, file it with the form that fits, and split the work into pull requests that each have a
   finish line you can state.

| You propose | Form |
| --- | --- |
| A species, an equation or a parameter table | [Carbon model / parameter proposal](../../.github/ISSUE_TEMPLATE/carbon_model.yml) |
| To check a `pending` value against its source | [Verify a parameter or rule](../../.github/ISSUE_TEMPLATE/parameter_verification.yml) |
| A program screening rule | [Policy rule proposal](../../.github/ISSUE_TEMPLATE/region_rule.yml) |
| A new country or region | [Region request](../../.github/ISSUE_TEMPLATE/region_request.yml) |
| A new dataset or API | [Data source proposal](../../.github/ISSUE_TEMPLATE/data_source.yml) |
| Anything else | [Feature request](../../.github/ISSUE_TEMPLATE/feature_request.yml) |

Have an idea that is not here? Open a discussion. If it holds up, add a row to this page in a pull request. A privacy or
security problem is not an idea: report it privately ([SECURITY.md](../../SECURITY.md)).

## Rules that apply to every idea

These come from [CLAUDE.md](../../CLAUDE.md) and the [scope guardrails](../../GOVERNANCE.md#scope-guardrails). An idea
that crosses one of them is out of scope, whoever proposes it.

- An estimate is never presented as a carbon credit. Every carbon output says `certified: false` until a registry has
  issued a serial number.
- Environmental benefit, indicative carbon value (a scenario) and other farm income are shown separately and are never
  added together.
- No carbon value, price, date or eligibility rule comes from memory. It comes from a source you have read, it is
  cited, and it carries a `verification_status`
  ([the three statuses](../developer-guide/adding-a-species-or-parameter.md#the-three-statuses)).
- A language model never computes a carbon number ([ADR-0003](../architecture/adr/0003-deterministic-before-ai.md)).
- Every dataset and external API has documented license terms and attribution
  ([DATA_LICENSES.md](../licensing/DATA_LICENSES.md)), and every external API has an adapter.
- Exact boundaries are private by default. Coordinates are never logged and never sent to a language model.

## At a glance

| Theme | Ideas | Reviewed by |
| --- | --- | --- |
| [Numbers and methods](#numbers-and-methods) | 5 | Carbon reviewers |
| [Regions and policy](#regions-and-policy) | 5 | Regional reviewers (India, United States, EU) |
| [Privacy and access](#privacy-and-access) | 3 | Privacy reviewers |
| [Data and adapters](#data-and-adapters) | 8 | Maintainers, and privacy reviewers where a row says so |
| [The web app](#the-web-app) | 7 | Maintainers |
| [The QGIS plugin](#the-qgis-plugin) | 2 | Maintainers |
| [Tooling, infrastructure and documentation](#tooling-infrastructure-and-documentation) | 6 | Maintainers |

## Numbers and methods

These ideas change numbers that people may act on. Each one starts with reading a primary source and ends with a
hand-computed test.

| Idea | What is open today | First step |
| --- | --- | --- |
| **Check the Tier 1 parameters against the IPCC tables, and settle the edition** | The root-to-shoot ratios and the above-ground growth values in [`ipcc-2006-tier1.yaml`](../../config/methodologies/ipcc-2006-tier1.yaml) are `pending`, and production mode refuses pending parameters. The [research note](../research/ipcc-age-class-growth.md) could not open the growth table (Table 4.9) in either edition. It read the 2019 Refinement's root-to-shoot table as organized by continent, origin and species group, with tropical values that differ from the config's | **Decide first** which edition the model follows. Then open the official PDFs locally and copy each cell with its page number, as the last section of the note describes. One table per pull request; a reviewer sets `verified` ([verifying a pending parameter](../developer-guide/adding-a-species-or-parameter.md#verifying-a-pending-parameter)) |
| **Close the temperate allometry gap** | Six of the eleven species (black walnut, pecan, oak, apple, olive and poplar) name the allometry `temperate_generic`, which has no equation. Given a trunk diameter, the engine applies a tropical equation (Chave et al. 2014, equation 4) and says so in the result's notes. The config names two candidates to fill the gap, Chojnacky et al. (2014) for North America and Forrester et al. (2017) for Europe, with the citation, species groups and coefficients still to be verified | Read the papers and list each species group, its coefficients and the size range it was fitted to. Add the equation as `pending` with a hand-computed test ([a new parameter or equation](../developer-guide/adding-a-species-or-parameter.md#a-new-parameter-or-equation)). The [US](../regions/US/METHODOLOGIES.md#the-temperate-allometry-gap) and [EU](../regions/EU/METHODOLOGIES.md#the-temperate-allometry-gap) pages describe the gap for their regions |
| **Add a species for India** | The India table has mango, teak, neem, eucalyptus, poplar and a mixed-native entry. The [India methodology page](../regions/IN/METHODOLOGIES.md) lists coconut, arecanut, cashew, sandalwood, bamboo, *Melia dubia* and casuarina as not available. Each needs a documented growth value, a wood density and an allometric equation. Bamboo is a grass, so it may need its own model rather than a tree-biomass entry | Pick one species and collect its sources first: a value without a citation does not go in. Add it as `pending` ([adding a species](../developer-guide/adding-a-species-or-parameter.md#adding-a-species)). For bamboo, **decide first** whether a separate model is wanted |
| **Implement one of the three models that are only interfaces** | `agroforestry`, `soil-carbon` and `crop-practice` are typed stubs. Each raises an error that names the sources a real implementation needs, and the API answers 501. No number ships until the tables are in `config/` with their sources. The roadmap lists soil organic carbon indicators with a documented methodology as an unscheduled idea | **Decide first**, with the carbon reviewers, which model and which region come first. The sources are listed in each stub's docstring in `packages/carbon-engine/carbon_engine/models/`. Transcribe one table into `config/` as `pending`, with its source, unit and table number, before writing any code. The SoilGrids stock stays an indicator, never a removal |
| **Replace the fixed uncertainty fractions** | The low and high bounds come from fixed fractions that the config marks `assumption` (`uncertainty_fraction_tier1` and `uncertainty_fraction_tier2`), and the Tier 1 one is waiting for the IPCC default uncertainty. The roadmap lists uncertainty propagation beyond fixed fractions as an unscheduled idea | Read the IPCC section the config cites (Vol. 4, Ch. 4, section 4.2.1.4) and write down what it provides. **Decide first** how the ranges in the parameter files should combine into the bounds, then change the engine with hand-computed tests. Every result keeps `low`, `central` and `high` |

## Regions and policy

Programs and rules differ from place to place, so these ideas need a regional reviewer who can read the official texts.
A program that cannot be linked to an official page does not go in, and anything unconfirmed is marked `TODO(verify)`.

| Idea | What is open today | First step |
| --- | --- | --- |
| **Add a region** | The roadmap names Brazil, Kenya and Indonesia, once a domain reviewer is available. A region is a config file, a policy file, price scenarios, species, tree-age rules and imagery ([adding a region](../developer-guide/adding-a-region.md)). A few places in the code still list regions by name ([step 8](../developer-guide/adding-a-region.md#8-code-that-still-lists-regions)) | Open a [Region request](../../.github/ISSUE_TEMPLATE/region_request.yml) that names the reviewer and the official page of each program. **Decide first**: without a reviewer who can read the sources, the region waits |
| **A page for each EU member state's CAP plan** | The EU rule says only that national plans include eco-schemes and investment support for agroforestry and afforestation. It lists no national scheme, payment rate, deadline or condition, because they differ from one member state to the next ([EU programs](../regions/EU/PROGRAMS.md#cap-eco-schemes-and-agri-environment-climate-measures)) | Pick one member state. Find its CAP Strategic Plan and its paying agency's own page, and write what each source says about trees, with a link for every statement and a `TODO(verify)` for anything you could not confirm. One state per pull request |
| **State programs in the US, national labels in the EU** | The US page says state programs were not researched. The EU page lists national labels, such as Label Bas-Carbone, as open items ([US](../regions/US/PROGRAMS.md#open-items-for-reviewers), [EU](../regions/EU/PROGRAMS.md#open-items-for-reviewers)) | Pick one state or one label. Write who runs it, what it pays or certifies, who can take part, and whether it issues a credit or is an incentive: the Atlas never lets the two blur. Link the official source |
| **More tree-age rules** | [`rules.yaml`](../../config/tree-age/rules.yaml) holds 22 rules. The [research note](../research/tree-age-carbon-rules.md#open-questions) lists what was not researched (France and Spain, other Indian states, other US cities) and what was not checked: later amendments, notified areas and current penalties for the Karnataka and Delhi tree acts; Karnataka's Krushi Aranya Protsaha Yojane incentive, which the note describes and the file does not hold; how Verra VM0047 treats the later growth of trees that already stand; the final Gold Standard text and Plan Vivo; the City Forest Credits 100-year version; newer versions of the improved-forest-management protocols | Pick one jurisdiction or standard and read the primary text, not a summary. Follow [adding a tree-age rule](../developer-guide/adding-a-tree-age-rule.md), which starts by checking that the rule belongs there. A rule you could read only in the press stays `pending` and is withheld in production |
| **Review the price scenarios** | All three regional scenarios in [`carbon-price-scenarios.yaml`](../../config/market/carbon-price-scenarios.yaml) are `pending`, are dated 2025 and are described as placeholders. The file says to review them every release against two annual reports: the World Bank's State and Trends of Carbon Pricing and Ecosystem Marketplace's State of the Voluntary Carbon Market | Read the latest edition of each and note, for each region, what it says about nature-based removal prices and where. **Decide first** what counts as a review (who signs off, what is recorded). A price from memory never goes in. The scenario stays illustrative and is never a quote |

## Privacy and access

Privacy by default is a [scope guardrail](../../GOVERNANCE.md#scope-guardrails). These ideas close the distance between
what the privacy pages promise and what the code does
([architecture overview](../developer-guide/architecture-overview.md#the-privacy-boundary)). Privacy reviewers read
them.

| Idea | What is open today | First step |
| --- | --- | --- |
| **Sign-in and plot ownership** | Version 0.1 has no accounts. `ATLAS_API_KEYS`, when set, protects only the endpoints that change data. `GET /api/v1/plots` lists every plot to anyone who can reach the server, and with a technical tool that includes the exact boundaries ([FAQ](../user-guide/faq.md#who-can-see-my-boundary)) | **Decide first**, in an ADR: one shared key per deployment, a token for each person, or a login in front of the Atlas. The answer also decides what a "public view" means. No code before the decision |
| **Send less location to open services** | In live mode Earth Search receives the exact plot polygon in its search, and the scene hosts receive byte ranges around the plot. Open-Meteo, SoilGrids and the geocoders receive the exact centroid ([what each provider receives](../data-sources/FREE_APIS.md#at-a-glance)). The [geolocation page](../privacy/geolocation.md) says the API may round the climate point to the provider's native grid, and it does not | Write down, for each request in [what one analysis calls](../data-sources/FREE_APIS.md#what-one-analysis-calls), the least location detail that still works. Change one request at a time, with a test that shows the answer stays the same within a tolerance you state. For the satellite search, a STAC catalog of your own is a deployment answer that `EARTH_SEARCH_STAC_URL` already allows |
| **Search only when the user asks** | The search box sends a request after a 350 millisecond pause once three characters are typed. The public Nominatim policy, as [DATA_LICENSES.md](../licensing/DATA_LICENSES.md) quotes it, allows no autocomplete. The adapter keeps to one request per second and caches for 24 hours, but each pause still sends the typed text to the geocoder | **Decide first**: search on Enter, or point the deployment at a self-hosted Nominatim or Photon, which the [infrastructure notes](../../infra/terraform/README.md) already recommend for heavy traffic. Either way, test that nothing is sent for a query that is too short |

## Data and adapters

Adapters bring in outside data. Each idea here keeps the rules in
[adding an integration](../developer-guide/adding-an-integration.md): documented license, attribution, a demo twin and
tests that never reach the network.

| Idea | What is open today | First step |
| --- | --- | --- |
| **Decide what "other farm income" shows, then connect the statistics adapters** | The adapters for USDA NASS, the US Census geocoder and data.gov.in are built and tested, and no service calls them. Every region's "other farm income" lines have a label and a source and no value ([known gaps](../data-sources/FREE_APIS.md#known-gaps)). Statistics about what a county or district produces are not the income of one farm | **Decide first** what the Atlas may show: context about the district, or a figure. Whatever it shows stays separate from the other two values and is never added to them. Then wire one adapter into one service, with its demo twin and tests. NASS and data.gov.in need free keys |
| **Tests for the raster and satellite adapters** | No test imports the WorldCover, Earth Search or Copernicus adapters or the shared STAC code. The helpers underneath them are tested, and the API tests use the demo twins ([testing](../developer-guide/testing.md#known-gaps)) | Work out how to give each adapter local inputs, such as a small GeoTIFF in a temporary folder and canned STAC answers, so that nothing reaches the network. Do the geocoders first ([starter issue 13](starter-issues.md#13-test-the-geocoder-adapters)) |
| **A disk cache for raster windows, with deletion** | `ATLAS_CACHE_DIR` is defined and no code reads it. The architecture and privacy pages say raster windows are cached on disk; the code caches in memory only ([known gaps](../data-sources/FREE_APIS.md#known-gaps)). The [data retention page](../privacy/data-retention.md) lists a cache time limit setting, `ATLAS_CACHE_TTL_DAYS`, as planned | **Decide first**, with the privacy reviewers, whether to build the cache or to correct the pages. A cached window is the plot's bounding box, so it is location data: the [infrastructure notes](../../infra/terraform/README.md) already say to treat it as personal data. A design needs a retention time and deletion when the plot is deleted |
| **Settings for values fixed in code, and one timeout policy** | The WorldCover year, the Open-Meteo window, the cache lifetimes, the satellite search window, the cube cell size and the Copernicus file keys cannot be changed by a setting. WorldCover and the STAC adapters do not use the 20 second timeout and one retry that the other adapters share ([known gaps](../data-sources/FREE_APIS.md#known-gaps)) | Pick one value, move it into a setting with today's value as the default, list it in `.env.example`, and test the default and an override. Settings come from the environment, never from literals in application code (CLAUDE.md principle 6) |
| **More imagery for the Satellite view** | Only four countries have a national default. India falls back to the global one, which has 10 m pixels from 2016. The [research note](../research/imagery-providers.md#recommendation-for-production) names a self-built cloud-free Sentinel-2 mosaic, published as PMTiles from the project's own bucket, as the best option for India. NRSC's Bhuvan is not listed because no openly licensed tile service was found | For the mosaic, **decide first** who builds and hosts it and what attribution wording it carries ([map licenses](../licensing/MAP_LICENSES.md)). For another country, one provider per pull request, read from the provider's own terms: coverage fits, the license is open, no key is needed and analysis is allowed ([adding an integration](../developer-guide/adding-an-integration.md#which-kind-of-integration-is-it)) |
| **A scripted basemap build** | The PMTiles archive is built by hand, with the two commands shown in the [mapping architecture](../architecture/mapping-architecture.md#building-the-archive) page. Each region file already holds a bounding box (`bbox` in `config/regions/<ISO>.yaml`) | **Decide first** where the archive is stored and how its build date is recorded. Then write a script in `scripts/` that reads a region's `bbox`, runs `pmtiles extract`, and prints the build date and the credit to show ([map licenses](../licensing/MAP_LICENSES.md)). It needs the `pmtiles` command-line tool and network access, so keep it out of the test suite |
| **Attribution in one place** | Attribution text lives in three places that disagree: [ATTRIBUTION.md](../licensing/ATTRIBUTION.md), each adapter's `SOURCE` and `GET /attribution` ([attribution strings](../data-sources/FREE_APIS.md#attribution-strings)). The imagery strings are copied by hand into `providers.yaml` and two licensing pages | **Decide first** which one is the source of truth. Then add a test that compares the others with it, so that a change in one place cannot drift from the rest. ATTRIBUTION.md already says to copy strings verbatim |
| **Integration with field-data apps** | The roadmap lists integration with field-data apps for trunk-diameter capture as an unscheduled idea. The app imports files (GeoJSON, KML, KMZ, CSV, LAS and LAZ; [imports](../architecture/imports-and-detection.md#2-imports-import-data)) and has no connection to a field app | **Decide first** which app, and which of its export formats. Document the format from the app's own documentation, never from memory. Exact positions in a field record are private data: the import keeps only a derived record, and a new path needs the same rule |

## The web app

The app is in `apps/web`. Components render, engines calculate and adapters fetch (CLAUDE.md principle 2), so any logic
in these ideas goes into a function with its own test. Text goes through the six language files, and every new string
needs all six.

| Idea | What is open today | First step |
| --- | --- | --- |
| **Region-aware, translated explanations and reports** | The "In plain words" paragraph comes from one fixed English template that ignores the language and names "Green Credit" for every country. The report request takes a `language`, and the report text is in English whatever it says ([FAQ](../user-guide/faq.md#the-numbers), [reports](../user-guide/faq.md#reports-and-files)) | **Decide first** where the text lives (the config, or the report templates). The numbers and every "not a credit" sentence must stay deterministic and exact, so the way is translated templates, not a language model. Native speakers must review them. A first piece: make the paragraph name the programs of the user's region instead of "Green Credit" |
| **Wire or remove the controls that do nothing** | The map's **Land use layer** and **Soil & terrain** switches and the **Data-processing mode** setting are saved, and nothing reads them ([FAQ](../user-guide/faq.md#the-map-and-the-views)). The "AI-assisted explanation" choice changes nothing: the API's explanation is always the deterministic template, and its `llm` provider is not bundled | **Decide first**, control by control: connect it or remove it. A control that does nothing misleads, especially one that appears to switch on AI. Anything AI-assisted keeps the rule that only derived indicators leave the server ([privacy design](../privacy/privacy-design.md)) |
| **Fonts for Devanagari and Kannada** | Only Latin fonts are bundled. Hindi and Kannada text depends on the fonts of the device ([fonts](../licensing/THIRD_PARTY.md#fonts)) | Choose open-license families, check their licenses and their file size, serve them from your own host, and add rows to the fonts table. A browser must never contact a font host. Look at the result on a device that lacks such fonts |
| **Map style: glyph host and credits** | With your own PMTiles archive, the app's style loads label glyphs from the MapLibre demo host. The address is written in `mapStyle.ts`, not set in the environment, and that host sees each viewer's address. The style credits only OpenStreetMap, and [ATTRIBUTION.md](../licensing/ATTRIBUTION.md) says to add Protomaps if your builds ask for it | Add an environment variable for the glyph address and document how to host the glyph files (CLAUDE.md principle 6). **Decide first** whether the demo address stays as the development default |
| **Let people say which evidence they hold** | The readiness score counts baseline land-use records, farm management history and a land ownership or tenure document (`baseline`, `management` and `ownership` in [`readiness.yaml`](../../config/readiness.yaml)). The API takes them as an `evidence` object on the estimate request. The web app never sends it, so they stay "missing" however complete your file is ([FAQ](../user-guide/faq.md#your-data)) | **Decide first** what the form asks. Yes or no is enough for the score and needs no document upload. Add the controls, the request and tests, with every new string in all six languages. The weights are project assumptions and are not part of this idea |
| **One sentence for "this is not a credit"** | The English interface says it in three wordings, and the master text is in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md#mandatory-disclaimers-verbatim). The five translations follow all three ([starter issue 5](starter-issues.md#5-review-one-existing-translation)) | **Decide first**: the maintainers choose the master wording. Then make every screen use one string for it in each language, and ask a speaker of each language to check the result. Keep `certified: false` in the data wherever the sentence appears |
| **Field use without a connection** | The roadmap lists an offline-capable progressive web app for field use as an unscheduled idea. The app has no service worker and no web app manifest. Its offline fallback serves stored example data when the API cannot be reached ([FAQ](../user-guide/faq.md#can-i-use-the-app-without-internet)) | **Decide first**, with the privacy reviewers, what may be stored on a device: exact boundaries are private and a phone can be lost. Write that down before choosing a design |

## The QGIS plugin

The plugin is GPL-2.0-or-later and lives in `integrations/qgis-plugin`
([third-party software](../licensing/THIRD_PARTY.md#the-qgis-plugin-and-the-gpl)). It has to keep working on Python 3.9,
because QGIS 3.28 on Windows embeds that version ([plugin tests](../developer-guide/testing.md#qgis-plugin-tests)).

| Idea | What is open today | First step |
| --- | --- | --- |
| **Read the API key from the QGIS authentication manager** | The plugin keeps the key as plain text in the QGIS user profile and does not read keys from the authentication manager ([plugin README](../../integrations/qgis-plugin/README.md)). On a shared computer its advice is to leave the key empty | Read the authentication manager's documentation for QGIS 3.28, the oldest version the plugin supports. Add a way to choose a stored configuration, keep the plain-text field working for now, and test with the fakes in `tests/qgis_fakes.py`. The key must never appear in a log or an error message |
| **Support QGIS 4 (Qt 6)** | The plugin declares QGIS 3.28 to 3.99, and its README says QGIS 4 is not supported yet | Run the plugin's tests, including the dialog smoke tests (which need PyQt5 today), against a Qt 6 build and list what fails. **Decide first** whether one package keeps supporting 3.28 or the plugin is released separately for QGIS 4 |

## Tooling, infrastructure and documentation

These ideas change how the project is built, checked and explained. Changes to workflows go through the checks in
[testing](../developer-guide/testing.md#what-ci-runs).

| Idea | What is open today | First step |
| --- | --- | --- |
| **Run the browser tests in CI, and build the larger suite** | The Playwright suite is one smoke file with two scenarios, and it is not part of CI. [`tests/e2e/README.md`](../../tests/e2e/README.md) describes ten planned journeys in a different layout, and the roadmap's last phase includes an end-to-end suite ([web tests](../developer-guide/testing.md#web-tests)) | Treat that README as a wish list and check each step against the app. A good first journey is the privacy one: watch the network traffic and fail if a request to a third-party origin carries coordinates, or if the `/explain` payload has a location key. Then add a CI job that builds the web app, starts the API in demo mode and runs the suite |
| **Terraform modules for one provider** | [`infra/terraform/`](../../infra/terraform/README.md) documents a reference layout and holds no `.tf` files | Pick a provider you run yourself. Write one module (storage with the CORS headers that PMTiles need is the smallest) with placeholder variables, no secrets and no state, and say in the pull request what you tested it against |
| **Keep the plugin out of the API image** | `infra/docker/Dockerfile.api` copies the whole `integrations/` folder, so the plugin's GPL-licensed files are inside the API image, and the repository has no `.dockerignore` ([third-party software](../licensing/THIRD_PARTY.md#known-gaps)) | Exclude `integrations/qgis-plugin/` in a `.dockerignore` at the repository root, then check that the Docker build job in CI still passes and the container starts |
| **Make screenshots one command, in every language** | `make screenshots` runs a script that does not exist, because the real one is `scripts/capture_screenshots.mjs`. The script has no language option. The old eight-file set is still in `docs/images/screenshots/`, and the user guide still points at four of its names ([images README](../images/README.md#known-gaps)) | Point the target at the real script and add a `--lang` option. Run it, review every picture against the [rules](../images/README.md#rules-for-screenshots), delete the old files, and update the image links in the user guide. Name the files with the language code, and check that the Docs workflow still passes |
| **Translate the user guide** | The user guide is in English only, and the app is in six languages | **Decide first** where translated pages live, how they stay in step with the English ones and who reviews them. Start with one page ([getting started](../user-guide/getting-started.md)) in one language, and use the same words for "estimate", "scenario" and "credit" as the app's translation does |
| **Decide the license of the documentation** | [ADR-0005](../architecture/adr/0005-apache-2-license.md) says the pages in `docs/` are covered by Apache-2.0 unless a page says otherwise. The [FAQ](../user-guide/faq.md#does-it-cost-anything-do-i-need-an-account) says the documentation is under CC BY 4.0. Pictures and diagrams have their own terms ([images README](../images/README.md#licenses)) | **Decide first**: the maintainers choose. If the answer is not ADR-0005's, a new ADR supersedes it ([governance](../../GOVERNANCE.md#decision-making)). Then make every page that mentions the license say the same thing |

## Related pages

[Starter issues](starter-issues.md) · [Roadmap](../../ROADMAP.md) · [CONTRIBUTING.md](../../CONTRIBUTING.md) ·
[Governance](../../GOVERNANCE.md) · [Developer guide](../developer-guide/README.md) ·
[Free APIs](../data-sources/FREE_APIS.md) · [Contributors](../../CONTRIBUTORS.md)
