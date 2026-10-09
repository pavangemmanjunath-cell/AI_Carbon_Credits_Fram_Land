# Starter issues

These are small, well-scoped tasks for people who are new to the repository. They cover checking data against its
sources, translations, the web app, the API and the adapters, and documentation. Each entry is written so that a
maintainer can paste it into a GitHub issue: the heading is the title, the labels come from
[`.github/labels.yml`](../../.github/labels.yml), and the text says why the task matters, where to work and how you will
know you are done.

Every problem named here was found by reading the code and the config on 5 October 2026 (version 0.1, not yet
released), and each is stated as found. Files change, so open the ones named before you start, and if something is
different, say so on the issue instead of following this page blindly. No task asks you to supply a carbon value, a
regulatory date or a payment amount from memory: where a task depends on a source document, you read the document.

Bigger tasks, and tasks that need a decision from the maintainers first, are in [roadmap ideas](roadmap-ideas.md). Some
other pages call a few of those starter issues: adding a species for India, a scripted basemap build and a page for
each EU member state's CAP plan are all listed there, because each needs a decision or a reviewer before it can start.

## How to take one

1. Read [CONTRIBUTING.md](../../CONTRIBUTING.md) and the rules in [CLAUDE.md](../../CLAUDE.md). The ones that are
   missed most often: no carbon value hard-coded, every number cites a source, and no coordinates in logs.
2. Set up the repository with the [setup guide](../developer-guide/setup.md).
3. Say on the issue that you are taking it, so that two people do not do the same work. Blank issues are disabled, so
   if the issue does not exist yet, ask in a discussion. A maintainer creates it from this page with the labels shown
   here, and without `needs-triage`, because this page is the triage.
4. Open one pull request per issue and fill in every section of the
   [pull request template](../../.github/PULL_REQUEST_TEMPLATE.md). If an AI tool helped, say so in the pull request
   and check every source yourself ([AI-assisted contributions](../../CONTRIBUTING.md#ai-assisted-contributions)).
5. Run the checks for the area you touched ([testing](../developer-guide/testing.md)). `make test` runs the Python,
   Vitest and type checks, and `make lint` runs ruff, mypy and ESLint. If a check fails on code you did not touch,
   compare with a clean checkout and say so in the pull request. Do not fix unrelated code in the same pull request.
6. Expect domain review where it applies ([CODEOWNERS](../../.github/CODEOWNERS)). Carbon reviewers read
   `config/species/`, `config/methodologies/`, `config/tree-age/` and `packages/carbon-engine/`. Regional reviewers
   read `docs/regions/<ISO>/`, `config/regions/<ISO>.yaml` and `config/policies/`. Privacy reviewers read
   `apps/api/app/services/plots.py`, `apps/api/app/repositories/` and `docs/privacy/`. Maintainers read
   `integrations/`, `config/imagery/`, `docs/licensing/` and `.github/`. Those pull requests take longer.

A privacy or security problem is never a public issue ([SECURITY.md](../../SECURITY.md)). The two gaps in issues 10 and
11 are already described in the [architecture overview](../developer-guide/architecture-overview.md#the-privacy-boundary).
Anything else you find goes through the private route.

## At a glance

Effort is relative: small means a few files and a clear finish line, medium means more reading or more files, and large
means a long list that you can split into several pull requests.

| # | Task | Area | Effort | You will need |
| --- | --- | --- | --- | --- |
| 1 | [Find the official source for one pending tree-age rule](#1-find-the-official-source-for-one-pending-tree-age-rule) | Data check | Medium | Reading government or legal documents |
| 2 | [Check one species' wood density](#2-check-one-species-wood-density) | Data check | Small | Reading a database record carefully |
| 3 | [Look at one imagery provider in the running app](#3-look-at-one-imagery-provider-in-the-running-app) | Data check, map | Small | A browser and its developer tools |
| 4 | [Add a UI language](#4-add-a-ui-language) | Translation, web | Large | Fluency in the language, JSON, a little TypeScript |
| 5 | [Review one existing translation](#5-review-one-existing-translation) | Translation, web | Small | Fluency in Hindi, Kannada, German, French or Spanish |
| 6 | [Test that the translation files stay in step](#6-test-that-the-translation-files-stay-in-step) | Web tests | Small | TypeScript, Vitest |
| 7 | [Show the analysis warnings](#7-show-the-analysis-warnings-in-the-web-app) | Web | Small | React, TypeScript |
| 8 | [Pick the newest tree inventory consistently](#8-pick-the-newest-tree-inventory-consistently) | Web | Small | TypeScript |
| 9 | [Credit the geocoder beside the search results](#9-credit-the-geocoder-beside-the-search-results) | Web, licensing | Small | React, TypeScript |
| 10 | [Stop the public plot view returning `bbox`](#10-stop-the-public-plot-view-returning-bbox) | API, privacy | Small | Python, FastAPI |
| 11 | [Delete a plot's reports with the plot](#11-delete-a-plots-reports-with-the-plot) | API, privacy | Small | Python |
| 12 | [Handle 29 February in the scene search](#12-handle-29-february-in-the-scene-search) | Adapters | Small | Python |
| 13 | [Test the geocoder adapters](#13-test-the-geocoder-adapters) | Adapters, tests | Medium | Python, pytest |
| 14 | [Write the README for one adapter](#14-write-the-readme-for-one-adapter) | Adapters, docs | Small | Reading Python |
| 15 | [Repair the dangling documentation links](#15-repair-the-dangling-documentation-links) | Docs | Medium | Markdown |

## Check the data against its sources

These tasks involve facts that people may act on. Read the primary source, not a summary and not an AI answer, copy only
what you can see, and say which edition or version you read. The status of a parameter or rule is never changed on the
strength of one person's check: a reviewer sets `verified` in a pull request that links your issue
([verifying a pending parameter](../developer-guide/adding-a-species-or-parameter.md#verifying-a-pending-parameter)).
You report with the "Verify a parameter or rule" form
([`parameter_verification.yml`](../../.github/ISSUE_TEMPLATE/parameter_verification.yml)) and do not edit `config/`.

### 1. Find the official source for one pending tree-age rule

**Labels:** `needs-verification`, `area/config`, `help wanted`, `good first issue`, and `region/IN` or `region/EU` for
the rule you pick

**Why.** [`config/tree-age/rules.yaml`](../../config/tree-age/rules.yaml) holds 22 rules, and three are `pending`.
Production mode withholds pending tree-age rules, and the app never shows one as confirmed
([pending rules and production](../developer-guide/adding-a-tree-age-rule.md#pending-rules-and-production)). Two of the
three also set an age boundary: the 50-year start of the "old" class rests on press reports about Maharashtra, and the
75-year start of the "veteran" class on press reports about Haryana
([research note](../research/tree-age-carbon-rules.md)). Each rule's `notes` field says what is still missing:

| Rule id | What the config says is still needed |
| --- | --- |
| `in-hr-pran-vayu-devta-pension` | The official notification or guidelines, to confirm the age wording ("above" or "at least" 75), the species list, the exclusions and the current annual amount. Today the rule rests on press reports |
| `in-mh-heritage-tree` | The Government notification of heritage-tree norms (Environment and Climate Change Department), or the consolidated Act on India Code. The 50-year threshold appears only in press reports; the Bill and the Act text that were opened leave the norms to be notified |
| `eu-crcf-carbon-farming-delegated-act-2026` | The delegated act text and annexes, to confirm whether pre-existing trees are baselined or credited, the land-eligibility history, the standardized baseline and the minimum activity and monitoring periods. Entry into force was not confirmed as of 5 October 2026 |

**Where.** Pick one rule. Open the "Verify a parameter or rule" form with the file `config/tree-age/rules.yaml` and the
key `rules[id=<the rule id>]`. The sources already cited in the rule are the place to start.

**Done when.**

- The form is filled in from a primary document: the order, notification, Act or legal text itself, with its title,
  publisher, date and address. A news article can lead you to the document, but it is not the document.
- It gives the page or section where the age, the amount or the rule is stated, a short quote as printed, and whether it
  matches the config's wording.
- If you cannot find or open an official source, the form says what you searched and where. "I could not access the
  source" is a valid and useful answer.
- You have not edited `config/`.

### 2. Check one species' wood density

**Labels:** `needs-verification`, `area/config`, `help wanted`, `good first issue`

**Why.** All eleven species in [`config/species/species.yaml`](../../config/species/species.yaml) carry a wood density
marked `pending`, recorded as a working value from the Global Wood Density Database
([Zanne et al. 2009](https://doi.org/10.5061/dryad.234)). Production mode refuses estimates that use a pending
parameter ([what production does with pending](../developer-guide/adding-a-species-or-parameter.md#what-production-does-with-pending)),
so each one blocks a production release.

**Where.** Pick one species id (`mango`, `teak`, `neem`, `eucalyptus`, `mixed_native_tropical`, `black_walnut`,
`pecan`, `oak`, `apple`, `olive` or `poplar`). Open the form with the file `config/species/species.yaml` and the key
`species[id=mango].wood_density_g_cm3`. Talk to the maintainers first about `mixed_native_tropical`: it stands for a mix
of species, not one taxon, and its source is a pantropical mean rather than a database record.

**Done when.**

- The form is filled in from the database record you read: the taxon, the value and unit as printed, how many records
  the taxon has, and how the working value compares.
- If the database has no record for the exact taxon, the form says so, names the closest genus or family value you found
  and states why it is or is not appropriate. It does not guess.
- You have not edited `config/`.

### 3. Look at one imagery provider in the running app

**Labels:** `needs-verification`, `area/earth-observation`, `data-licensing`, `good first issue`

**Why.** [`config/imagery/providers.yaml`](../../config/imagery/providers.yaml) lists the providers of the Satellite
view. Each one's license, attribution and address were read from the provider's own capabilities, terms or metadata on
5 October 2026, but nobody loaded them in a browser: the
[research note](../research/imagery-providers.md#not-confirmed) lists tile content and cross-origin behavior as not
confirmed, because the research tool could tell that a tile existed and not what it showed.

**Where.** Run the app (`make dev`), open Settings, choose a provider under "Map imagery", go to the workspace and
switch the map to Satellite. The choice is stored per country. Pick one provider: `usgs-imagery-only`,
`ign-france-orthophotos`, `ign-spain-pnoa`, `pdok-luchtfoto`, `eox-s2cloudless-2016`, `eox-s2cloudless-2017` or
`eox-s2cloudless-2025`. Skip `esri-world-imagery` unless you hold an Esri key (`ESRI_API_KEY`). Move the map over the
provider's coverage, a country for the national ones and anywhere for EOX, and look at several zoom levels with the
browser's developer tools open. If the layer stays blank, start with
[troubleshooting](../developer-guide/troubleshooting.md#the-satellite-view-is-blank-or-a-provider-is-unavailable).

**Done when.**

- The form (file `config/imagery/providers.yaml`, key `providers[id=<id>]`) says what you saw: whether tiles loaded at
  every zoom up to the provider's `max_zoom`, whether any tile was blank or a "no data" placeholder, and whether the
  console showed a cross-origin (CORS) or other error.
- It says whether the map kept showing the imagery past `max_zoom` by enlarging the last level, and whether the
  attribution bar showed the provider's text from the config.
- It names the place and the zoom levels you looked at. Look only at public places.
- If you could, you also opened the license page named in the config and say whether it still matches the row in
  [MAP_LICENSES.md](../licensing/MAP_LICENSES.md#imagery-providers).
- You have not edited `config/` or the licensing pages.

## Translations

The web app lives in `apps/web`. Its shared strings are in `apps/web/src/i18n/` (503 in English). The AI agents page and
the tree-age page keep their own strings in `features/agents/i18n.ts` (161 per language) and
`features/tree-age/i18n.ts` (134 per language). Reports and the "In plain words" paragraph are produced by the server in
English, so they are not part of these tasks (see the [FAQ](../user-guide/faq.md#reports-and-files)).

### 4. Add a UI language

**Labels:** `type/translation`, `area/web`, `region/IN` (for the Indian languages), `good first issue`

**Why.** The interface is available in English, Hindi, Kannada, German, French and Spanish. The roadmap names Tamil,
Telugu, Marathi, Bengali and Punjabi among its unscheduled ideas ([roadmap](../../ROADMAP.md#beyond-10-unscheduled)),
and the [India](../regions/IN/README.md), [United States](../regions/US/README.md) and [EU](../regions/EU/README.md)
pages call further languages open starter issues. Pick one language per pull request. It is a long list, about 800
strings in all, so you may split it into three pull requests: the shared file with its wiring, the AI agents page and
the tree-age page.

| Code | Language | Its own name | Region file |
| --- | --- | --- | --- |
| `ta` | Tamil | தமிழ் | `config/regions/IN.yaml` |
| `te` | Telugu | తెలుగు | `config/regions/IN.yaml` |
| `mr` | Marathi | मराठी | `config/regions/IN.yaml` |
| `bn` | Bengali | বাংলা | `config/regions/IN.yaml` |
| `pa` | Punjabi | ਪੰਜਾਬੀ | `config/regions/IN.yaml` |

For any other language, open a discussion first: name the region that would list it and the person who will review it.

**Where.**

- `apps/web/src/i18n/<code>.json`: a copy of `en.json` with every value translated and every key unchanged. Keep every
  `{{placeholder}}` and the `<browse>` tag in `import.dropText`. English has `_one` and `_other` plural keys. Check
  which forms your language needs with `new Intl.PluralRules('<code>').resolvedOptions().pluralCategories`: the five
  languages in the table need only those two, while French and Spanish also carry `_many` keys.
- `apps/web/src/i18n/index.ts`: import the file, add it to `resources`, and add its code and the language's own name to
  `LANGUAGES`.
- `apps/web/src/lib/format.ts`: add the code to `LANGUAGE_DEFAULT_REGION`. Without an entry, numbers and dates are
  formatted for the `IN` region, which suits the five languages above but should be explicit.
- `apps/web/src/features/agents/i18n.ts` and `apps/web/src/features/tree-age/i18n.ts`: add a bundle for the language
  to each file and to `agentsBundles` and `treeAgeBundles`. TypeScript fails when a key is missing, and each feature's
  `i18n.test.ts` lists the six languages, so add the code there too. Until you do, those two pages show English in the
  new language, because missing keys fall back to English.
- `config/regions/<ISO>.yaml` (`languages`) and its mirror `apps/web/src/config/regions.json`, which says it is updated
  by hand. No code reads that list today, but the region pages state it.
- The language row of the region page, for example [India](../regions/IN/README.md).

**Done when.**

- The shared file has exactly the keys of `en.json` (plus any plural keys the language needs), and every string keeps
  the same `{{placeholders}}`. Names, codes and strings made only of placeholders may stay as in English, as they do in
  the existing files.
- The disclaimers keep their meaning: `cards.notCredit`, `results.pill` and `landing.indicativeValueText` say an estimate
  is not an issued credit, and `results.policyDisclaimer` says a screening is not an eligibility determination.
- You have looked at how numbers appear. In a browser, Marathi and Bengali use their own digits by default
  (`new Intl.NumberFormat('mr-IN')`), while Hindi and Kannada show Latin digits in the app today. Describe what you see
  in the pull request and let the maintainers decide.
- You have looked at the new script on at least one real device or browser and say which. The app bundles only Latin
  fonts, so other scripts use the device's fonts. Do not add a font in this pull request: a font needs its own license
  check ([fonts](../licensing/THIRD_PARTY.md#fonts)).
- `npm run typecheck`, `npm run lint` and `npm run test -- --run` pass in `apps/web`, and the pull request has a
  screenshot of the language menu and of the results page in the new language ([what a screenshot may
  show](../images/README.md#rules-for-screenshots)).
- If a machine translation tool gave you a first draft, the pull request says so and a fluent speaker has read the
  result.

The agents' question router has keyword lists per language in `packages/agent-framework/atlas_agents/intents.py`. A new
language works without them, because every language is searched for every question, but a few words in yours would
help. Do that in a separate pull request: it changes behavior and needs tests.

### 5. Review one existing translation

**Labels:** `type/translation`, `area/web`, `good first issue`

**Why.** No native-speaker review of the Hindi, Kannada, German, French or Spanish files is recorded in the repository.
Wording matters more here than in most software, because a loose translation of "estimate", "scenario", "credit" or
"eligibility" can make an estimate sound like something it is not.

**Where.** One file in `apps/web/src/i18n/`: `hi.json`, `kn.json`, `de.json`, `fr.json` or `es.json`. Read it in the
running app (`make dev`, then the language menu) as well as in the file, because some strings are short buttons and
others are cards. The two feature bundles are separate files with their own review: do them in separate pull requests.

**Done when.**

- You have checked the meaning of the terms for estimate, scenario, credit, certified, eligibility, confidence and the
  unit labels, and that they are used the same way on every screen.
- Strings that do not fit their button or card (German and French often run long) are shortened or listed in the pull
  request.
- Only values change, never keys, and every `{{placeholder}}` is intact.
- The pull request lists each corrected string with the old text, the new text and the reason.
- The pull request raises one open question for the maintainers. The English interface says "this is a scenario, not an
  issued credit" in three wordings: "Scenario estimate — not an issued carbon credit." on the result cards, "Scenario
  estimate only. This is not an issued carbon credit." on the results, landing, AI agents and tree-age pages, and
  "Scenario estimate; not an issued carbon credit." in the carbon estimates, the simulation and the reports, which is
  also the master text in [ATTRIBUTION.md](../licensing/ATTRIBUTION.md#mandatory-disclaimers-verbatim). Check that your
  language says the same thing in each place and say which wording reads best. Do not pick a master yourself: the
  maintainers decide, and the translations follow.

### 6. Test that the translation files stay in step

**Labels:** `type/chore`, `area/web`, `good first issue`

**Why.** Nothing fails today when a key is missing from a language file (i18next falls back to English without a
warning, `fallbackLng: 'en'`) or when a `{{placeholder}}` is lost from a translated string. The AI agents page and the
tree-age page already have such tests (`features/agents/i18n.test.ts` and `features/tree-age/i18n.test.ts`), but the six
shared files have none. At the time of writing the files agree, so the new test starts green. Two things need care:
French and Spanish carry eight extra `_many` plural keys, which i18next needs for those two languages, and
`import.dropText` holds a `<browse>` tag.

**Where.** A new `apps/web/src/i18n/i18n.test.ts`. Vitest picks up every `src/**/*.test.ts(x)` file
([`vitest.config.ts`](../../apps/web/vitest.config.ts)). The feature tests show how to flatten a bundle and compare
placeholders and tags.

**Done when.**

- For each language other than English, the test fails with the language and the key when a key is missing, when there
  is an extra key that the language's plural rules do not explain, when a string's set of `{{placeholders}}` differs
  from the English one, or when its set of tags does. For a `_many` key, compare with the English `_other` string.
- It finds the language files itself (for example with `import.meta.glob`), so a new language is checked without
  editing the test, and it also fails if a file exists that `LANGUAGES` in `index.ts` does not list.
- `npm run test -- --run` passes in `apps/web`, and the pull request changes no translation.

## The web app

### 7. Show the analysis warnings in the web app

**Labels:** `type/feature`, `area/web`, `good first issue`

**Why.** The API records notes about missing or substituted data in `data_quality.warnings` of the analysis, for example
`land cover unavailable: <error name>`, `climate normals unavailable: <error name>; using region default` and, in demo
mode, `demo mode: synthetic observations`. The HTML report prints them under "Data quality". The web app has the field in
its types and shows it nowhere, so a user can read a number that rests on a region default without being told
([what a failure looks like](../data-sources/FREE_APIS.md#what-a-failure-looks-like)). The offline fallback adds its own
note to the same list ("Offline demo fixture: values are not recomputed for your inputs"), so the change shows it too.

**Where.**

- `apps/web/src/features/results/ResultsPage.tsx` for the display, next to the **Evidence chain** card.
- A pure helper in `apps/web/src/features/results/logic/resultsLogic.ts` for any filtering or formatting, because
  components render and logic lives elsewhere (CLAUDE.md principle 2).
- A new key for the block's heading in all six files in `apps/web/src/i18n/`.

**Done when.**

- When `analysis.data_quality.warnings` is not empty, the results page lists each warning under a labeled heading. When
  it is empty, nothing is shown.
- Warning text is shown as the API sends it (English). The web app does not parse it, rewrite it or translate it.
- A Vitest test covers the helper, using the fixtures in `apps/web/src/test/fixtures.ts` (one has `warnings: ['demo']`).
- The new key exists in every language file. The test from [issue 6](#6-test-that-the-translation-files-stay-in-step)
  will tell you if you missed one, once it exists.

### 8. Pick the newest tree inventory consistently

**Labels:** `type/bug`, `area/web`, `good first issue`

**Why.** The API returns a plot's inventories oldest first. The in-memory repository appends, the PostgreSQL repository
sorts by `created_at`, and the server's own "latest inventory" is the last item. Three places in the web app take the
first item of the list, which is the oldest. In the offline fallback a new inventory is put first, so the same code
picks the newest there. With two inventories on one plot, a live server shows the older one on the results page, in the
report and in the workspace, while an offline session shows the newer one.

**Where.**

- `apps/web/src/features/results/ResultsPage.tsx`, `apps/web/src/features/report/ReportPage.tsx` and
  `apps/web/src/features/workspace/useWorkspaceFlow.ts`: each takes the first item of the inventory list.
- `apps/web/src/services/demoFallback.ts`: the offline `createTrees` puts a new inventory first, and the offline
  `carbonEstimate` takes the first item as the latest.

**Done when.**

- One helper (for example `latestInventory(items)`) returns the last item of the list the API sends, and all the places
  above use it.
- The offline fallback appends new inventories, so it returns the same order as the API.
- A Vitest test checks the helper and the offline order with two inventories.
- [`docs/architecture/api-contract.md`](../architecture/api-contract.md) states the order of
  `GET /plots/{plot_id}/trees` (oldest first) in the same pull request.

### 9. Credit the geocoder beside the search results

**Labels:** `type/feature`, `area/web`, `data-licensing`, `good first issue`

**Why.** The map's search box shows places from Nominatim or Photon in live mode, and from a demo twin in demo mode. In
live mode the data is OpenStreetMap's, under the ODbL, and the Nominatim usage policy asks for attribution to be
displayed ([DATA_LICENSES.md](../licensing/DATA_LICENSES.md)). The API sends the credit with every answer (`attribution`
in `GET /geocode`, which is "AgriCarbon Atlas demo generator — not an observation" in demo mode), and so does the offline
fallback. The web app has the field in its types and shows each result as a label and coordinates, without it. The map's
attribution bar credits the basemap, not the search.

**Where.** `MapSearch` in `apps/web/src/components/map/MapPanels.tsx`. The response object already holds
`attribution` next to `results`. There is no test for this component yet;
[`LandInputPanels.test.tsx`](../../apps/web/src/components/map/LandInputPanels.test.tsx) shows the pattern.

**Done when.**

- While results are listed, the list ends with one small line that shows the `attribution` string exactly as the API
  sent it. The string is not translated ([attribution strings](../licensing/ATTRIBUTION.md#localization)).
- Nothing is shown when there are no results, and the line does not take focus away from the results or hide one.
- A Vitest test renders the search with a stubbed response and finds the string.
- The pull request notes that [ATTRIBUTION.md](../licensing/ATTRIBUTION.md#shown-when-the-corresponding-layer-or-value-is-displayed)
  lists a longer string for the geocoders ("Search by Nominatim · © OpenStreetMap contributors"). Do not decide which
  text wins: say what you showed and let the maintainers choose.

## API and adapters

### 10. Stop the public plot view returning `bbox`

**Labels:** `type/bug`, `area/api`, `privacy`, `good first issue`

**Why.** `PlotService.public_view` removes `geometry`, `centroid` and `perimeter_m` from a plot but keeps `bbox` at six
decimals. `GET /api/v1/plots/{plot_id}/public` therefore returns a rectangle that places the plot to within a few
meters, next to a `public_centroid` that is deliberately only accurate to a 0.05 degree cell (roughly 5 km, see
[geolocation](../privacy/geolocation.md#the-005-generalization)). The [privacy design](../privacy/privacy-design.md)
already says a bounding box is location. The web app does not call this endpoint today. The public view also returns
the plot name and the area to four decimals; whether those are public is a decision for the privacy reviewers, so raise
it in the pull request and leave it unchanged.

**Where.**

- `apps/api/app/services/plots.py`: `PRIVATE_FIELDS` and `public_view`.
- `apps/api/tests/test_api_demo.py`: `test_demo_plots_are_seeded_and_private_fields_hidden_in_public_view`.
- `data/sample/responses/plot-public.json`, regenerated with `python3 scripts/make_sample_responses.py`.
- `data/schemas/plot.schema.json` forbids extra properties and has no `bbox`; the API test strips `bbox` before
  validating. Ask the maintainers whether `bbox` belongs in the schema for the owner view.

**Done when.**

- `GET /api/v1/plots/{plot_id}/public` has no `bbox`. If you think a coarse box is still useful, derive it from the
  0.05 degree cell of `public_centroid` and explain why in the pull request.
- `GET /api/v1/plots/{plot_id}` (the owner view) still returns `bbox`.
- A test fails if the public view carries a `bbox` finer than the generalized cell.
- The sample file and the pages that describe the public view ([API contract](../architecture/api-contract.md),
  [privacy design](../privacy/privacy-design.md)) agree with the code.

### 11. Delete a plot's reports with the plot

**Labels:** `type/bug`, `area/api`, `privacy`, `good first issue`

**Why.** [Data retention](../privacy/data-retention.md#deletion) lists report files among the things a deletion removes.
The PostgreSQL schema does it (`reports.plot_id` has `ON DELETE CASCADE`). The in-memory repository, used in demo mode and
in tests, removes the plot, its analysis, inventories, estimates and records, but not its reports, so a deleted plot's
report can still be fetched by its id until the server restarts. The
[FAQ](../user-guide/faq.md#what-happens-when-i-delete-a-plot) already tells users about this gap.

**Where.** `apps/api/app/repositories/memory.py`, `delete_plot`. Reports are stored as `(meta, content)` pairs keyed by
report id, and `meta["plot_id"]` names the plot.

**Done when.**

- After `DELETE /api/v1/plots/{plot_id}`, `GET /api/v1/reports/{report_id}` answers 404 for each report of that plot, and
  `report_ids()` no longer lists them. Reports of other plots are untouched.
- A test in `apps/api/tests/` creates a plot, an inventory, an estimate and a report, deletes the plot, and checks both
  of the above.
- The audit trail still records `plot.deleted`, and the `Repository` interface changes only if it has to.
- The FAQ paragraph is updated to match.

### 12. Handle 29 February in the scene search

**Labels:** `type/bug`, `area/integrations`, `area/earth-observation`, `good first issue`

**Why.** `StacSatelliteAdapter.best_scene_for_year` builds its search window with `anchor.replace(year=year)`, and the
anchor defaults to today. On 29 February that raises `ValueError` for every requested year that is not a leap year. The
analysis service catches `ValueError` and reports "satellite vegetation unavailable: ValueError", so in live mode the
vegetation layer quietly disappears for that day. It happens once every four years, which is why nobody has seen it.

**Where.** `integrations/atlas_integrations/stac_common.py`, `best_scene_for_year`.

**Done when.**

- For an anchor of 29 February and a year that is not a leap year, the window is centered on a valid date (28 February
  or 1 March; say which in a comment). The window length (`window_days`) and the "no scene" note are unchanged.
- A unit test in `integrations/tests/` uses an anchor of 29 February, a stub in place of `search`, and years in the
  past, so it does not depend on today's date and needs no network.

### 13. Test the geocoder adapters

**Labels:** `type/chore`, `area/integrations`, `good first issue`

**Why.** The [integrations README](../../integrations/README.md) and the
[testing guide](../developer-guide/testing.md#known-gaps) both list Nominatim and Photon as untested. For Nominatim this
is the code that keeps the project inside the public instance's usage policy (an identifying `User-Agent`, one request
per second, a cache), so it deserves a test. One pull request per adapter is fine.

**Where.** A new `integrations/tests/test_geocoders.py`, or one file per adapter. The adapter tests use
`integrations/tests/httpmock.py` (`make_client`, `json_response`, `Recorder`) so that nothing reaches the network;
[`test_base_and_point_adapters.py`](../../integrations/tests/test_base_and_point_adapters.py) shows the pattern. Use the
synthetic demo coordinates (the demo plot near Doddaballapura), never the location of a real plot.

**Done when, for Nominatim.**

- A blank `user_agent`, or the placeholder from `.env.example` (it contains `you@example.org`), raises
  `ConfigurationError`.
- The configured `User-Agent` is sent. `search` sends `format=jsonv2`, `addressdetails=1`, a limit clamped to 1 to 10,
  and `countrycodes` in lower case.
- A result's `boundingbox` (`[south, north, west, east]`) comes back as `[west, south, east, north]`; the country is
  upper case, and the district is taken from the first admin key that differs from the state.
- A second identical search is served from the cache and does not wait for the throttle. Two reverse lookups that round
  to the same four decimals share one cache entry.
- Two uncached requests are at least `min_interval_s` apart. Use a small interval or a patched clock: the test must not
  sleep for a full second.

**Done when, for Photon.**

- `search` maps the GeoJSON features: the label has no duplicated parts, `extent`
  (`[min_lon, max_lat, max_lon, min_lat]`) becomes `[west, south, east, north]`, the country code is upper case and the
  district falls back through `county`, `district` and `city`.
- The `country` filter keeps matching results and, when none match, returns the unfiltered list. Pin that behavior in
  the test and, if you think it is wrong, open a separate issue.
- `reverse` with no features returns an empty result, and requests carry `lang=en`.

### 14. Write the README for one adapter

**Labels:** `type/docs`, `area/integrations`, `data-licensing`, `good first issue`

**Why.** CLAUDE.md principle 6 asks every adapter to ship a README with its source, license, attribution, rate limits,
caching and failure handling. None of the ten adapter folders has one. The [integrations README](../../integrations/README.md)
and [FREE_APIS.md](../data-sources/FREE_APIS.md) stand in ([known gaps](../data-sources/FREE_APIS.md#known-gaps)).

**Where.** `integrations/atlas_integrations/<adapter>/README.md` for one of `open_meteo`, `soilgrids`, `nominatim`,
`photon`, `esa_worldcover`, `earth_search`, `copernicus`, `usda_nass`, `census_geocoder` or `data_gov_in`.

**Done when.**

- The README has these parts: source and terms, configuration (environment variables and whether a key is needed),
  attribution (copied from `SOURCE.attribution`), rate limits, caching (the TTL), failure handling (which error class
  for which case), what the provider receives, the demo twin, and tests.
- Every statement is checked against `adapter.py`. Start from the matching section of FREE_APIS.md, which can be wrong.
- The adapter's row in [DATA_LICENSES.md](../licensing/DATA_LICENSES.md) is linked, and the relative links resolve.

## Documentation

### 15. Plan translations for the agents' sentences

**Labels:** `type/translation`, `area/agents`, `good first issue`

**Why.** The web app speaks six languages, but the AI agents' messages are written in English by the sentence
templates in [`apps/api/app/agents/wording.py`](../../apps/api/app/agents/wording.py), and the summaries of the tree-age
rules in [`config/tree-age/rules.yaml`](../../config/tree-age/rules.yaml) are English too. The agent endpoints already
accept a `locale`, so the plumbing exists; what is missing is a plan for the words.

**What to do.**

- List every sentence template in `wording.py` with the facts it uses (for example `carbon_sentence` uses the estimate
  range and the confidence grade). Numbers stay numbers: only the words around them are translated.
- Propose a format (one YAML file per language under `config/agents/`, keyed by template name) and how a missing
  translation falls back to English.
- Translate the templates for one language you know well, and ask a second speaker to review the wording with a farmer in
  mind.

**Done when.**

- A short design note is in the pull request and the maintainers agreed on the format.
- One language file exists, and a test shows that a run with that `locale` uses it and still passes every guardrail
  (no coordinates, values kept apart, "not a credit" wording).
