# Tests

Tests are a requirement, not a courtesy. [CLAUDE.md](../CLAUDE.md) principle 10 says every calculation has a test and
that a parameter flagged `verification_status: pending` must be caught by a production-mode data-quality test.
Unit tests sit next to the code they test. This directory holds the two suites that span several packages
(`integration/` and `data-quality/`) and the notes on the browser tests and the shared test data. How to write a good
test for each layer is in the developer guide's [testing page](../docs/developer-guide/testing.md).

All tests run offline, in demo mode, on synthetic data. None calls the public Internet, needs an API key or a
database; the API tests use FastAPI's in-process `TestClient`, and adapters are tested over `httpx.MockTransport`.

## What is in this directory

| Path | What it is |
| --- | --- |
| `integration/test_contract_fixtures.py` | Contract drift: the committed sample responses in `data/sample/responses/` against the field names the demo API returns now (6 tests) |
| `data-quality/` | Gates on the configuration files: parameters, detection settings, imagery providers and tree-age rules (below) |
| [`e2e/`](e2e/README.md) | A note on the browser smoke tests, which live in `apps/web/e2e/` |
| [`fixtures/`](fixtures/README.md) | A note on where the shared test data lives (this directory holds none) |

## Where all the tests live

Counts are the tests collected at the 0.2.0 release (2,184 Python tests and 459 web tests); they are a guide, not a
promise.

| Location | Runner | Tests | What it covers |
| --- | --- | --- | --- |
| `packages/carbon-engine/tests/` | pytest | 115 | Allometric equations against hand-computed values, the parameter store, readiness and confidence, the tree-biomass model, carbon by tree age |
| `packages/geo-engine/tests/` | pytest | 409 | Polygon validation and measurement, coordinate parsing, boundary construction, indices and climate zones, WorldCover shares, STAC helpers and the demo cube, vector and point-cloud imports, tree-cover detection |
| `packages/policy-engine/tests/` | pytest | 98 | Programme rules for IN, US and EU, status values, the tree-age rules engine |
| `packages/report-engine/tests/` | pytest | 6 | HTML, Markdown and JSON rendering, escaping, placeholders for missing blocks, the refusal of PDF without WeasyPrint |
| `packages/agent-framework/tests/` | pytest | 100 | Agents, tools, blackboard, plans, guardrails, intent routing, the template reasoner and redaction |
| `apps/api/tests/` | pytest + `TestClient` | 285 | The whole API in demo mode: errors, API keys, limits, privacy, geometry, imports, detection, tree age, imagery and agents; also keeps the agent docs in step with the code (`test_agents_docs.py`) |
| `integrations/tests/` | pytest + `httpx.MockTransport` | 19 | Adapter base (retry, status mapping, cache, provenance) and the point and statistics adapters |
| `integrations/qgis-plugin/tests/` | pytest | 620 | The QGIS plugin, against fakes of the QGIS API and a fake CarbonCreditBuy server; no QGIS needed (one smoke test is skipped when PyQt5 is missing) |
| `tests/integration/` | pytest | 6 | Sample-response contract (above) |
| `tests/data-quality/` | pytest | 526 | Configuration gates (below) |
| `apps/web/src/**/*.test.ts(x)` | Vitest + Testing Library | 459 in 45 files | Pure logic, the API client and its offline fallback, the UI store and key components |
| [`apps/web/e2e/`](e2e/README.md) | Playwright, Chromium | 4 | Smoke scenarios against the production build |
| `.github/scripts/` | CI only | n/a | The PostgreSQL schema checks: `postgres_smoke.py` and `schema_constraints.sql` against a real PostGIS |

The pytest settings are in the root `pyproject.toml`: `testpaths` are `packages`, `apps/api/tests`, `integrations` and
`tests`, `pythonpath` makes every package importable from a checkout, `asyncio_mode` is `auto` and `--strict-markers`
is on. The one registered marker is `production`.

## Running

```bash
make test                      # pytest, then web typecheck and Vitest
python3 -m pytest -q           # every Python test
python3 -m pytest tests/data-quality -q                     # configuration checks only
python3 -m pytest packages/carbon-engine apps/api/tests -q  # a few suites
cd apps/web && npm run test -- --run                        # web unit tests once (without --run it watches)
cd apps/web && npm run build && npm run test:e2e            # browser smoke tests (see e2e/README.md)
ATLAS_ENV=production ATLAS_ALLOW_PENDING_PARAMETERS=false python3 -m pytest tests/data-quality -q   # production gate
```

A full Python run takes under half a minute and ends with 2,181 passed and 4 skipped: one test needs PyQt5, and three
are production gates that run only with `ATLAS_ENV=production`.

## The data-quality suite

| File | What it guards |
| --- | --- |
| `test_parameters.py` | Every species parameter and Tier 1 constant has a source and a valid status; regions, policies and carbon-price scenarios line up; every policy programme has references with URLs; the default model runs for every species and climate zone |
| `test_detection_parameters.py` | Every number in `config/detection.yaml` has a value, unit, source and status; an `assumption` says it is a project assumption; none is `pending` |
| `test_imagery_providers.py` | Every provider in `config/imagery/providers.yaml` has a licence, attribution and https URL with no literal key; open-data providers allow commercial use and analysis; Esri and the non-commercial EOX mosaic stay display-only; every default is keyless, open and covers its country |
| `test_tree_age_rules.py` | Every tree-age rule has the required fields, vocabulary, an https source with an access date, a unit and date for each amount, and a note on what is missing when `pending`; none promises eligibility; India's Green Credits and carbon credits stay separate; every rule evaluates |

### The production gate

Each suite has one test that runs only when `ATLAS_ENV=production`. With that variable set the whole directory passes:

- `test_parameters.py` asserts that a Tier 1 estimate with pending parameters disallowed **raises**
  `PendingParameterError`. It passes today because the Tier 1 root-to-shoot ratios and growth values are still
  `pending`. When the last pending parameter that run uses is verified, the test fails with "DID NOT RAISE": that is
  progress, and the test must then target a parameter that is still pending
  ([adding a parameter](../docs/developer-guide/adding-a-species-or-parameter.md)).
- `test_tree_age_rules.py` asserts that a production deployment withholds `pending` tree-age rules (the engine and the
  API), then warns with the ids that a release still has to confirm from a primary source.
- `test_imagery_providers.py` fails when a provider's terms are not `verified`.

CI runs the gate as its own step, after the full run.

## Conventions

- **Offline and deterministic.** Adapters are exercised over `httpx.MockTransport` (helpers in
  `integrations/tests/httpmock.py`); there is no live-network marker. Randomness comes from fixed seeds.
- **Reference values come with their source.** The test names the source and the tolerance. For example
  `test_allometric.py` checks Chave et al. 2014 with a wood density of 0.55 g/cm³, D = 20 cm and H = 10 m against
  123.09 kg, to 0.01 kg. Compute the expected value by hand or from the paper, never by running your own code.
- **Carbon results are checked as a contract.** `low <= central <= high`, `unit == "tCO2e/yr"`, `certified is False`, a
  non-empty disclaimer, and `parameters_used` lists every parameter that influenced the number.
- **Privacy is tested.** No log record, problem document, adapter error or agent message may carry a coordinate pair, for
  example `test_coordinates_are_never_logged_or_echoed_in_problems` (geometry API),
  `test_no_message_contains_the_plot_coordinates` (agents) and `test_prompt_never_contains_coordinates_or_names`
  (reasoner). A source check keeps the QGIS plugin's log calls free of coordinates, bodies and keys.
- **Policy output is checked as data.** Each programme has references with URLs, `status` is one of the six contract
  values, and every tree-age rule has a source link and an access date.
- **Synthetic data only.** Use the farms in [`examples/`](../examples/README.md), the files in
  [`data/sample/`](../data/sample/README.md) or small hand-made polygons. Never commit a real boundary
  ([fixtures](fixtures/README.md)).

## What CI runs

`ci.yml` runs ruff, mypy and one pytest run over every test path on Python 3.12 and 3.13, then the production gate;
the PostgreSQL schema checks; and for the web app typecheck, ESLint, Vitest and the build. `qgis-plugin.yml` runs the
plugin tests on Python 3.9 and 3.12. **The Playwright suite is not run in CI**, and **coverage is neither collected nor
enforced** (the web app has `npm run test:coverage`; Python has no coverage tool configured). The full table is in the
[testing page](../docs/developer-guide/testing.md#what-ci-runs).

## Links

- [Testing guide for developers](../docs/developer-guide/testing.md)
- [Browser tests](e2e/README.md)
- [Test fixtures](fixtures/README.md)
- [Adding a species or parameter](../docs/developer-guide/adding-a-species-or-parameter.md)
- [Release process](../docs/developer-guide/release-process.md)
