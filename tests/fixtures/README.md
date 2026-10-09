# Test fixtures

**This directory holds no fixture files.** Shared test data lives next to what produces or uses it, and each test
suite builds the small inputs it needs in code. This note says where each kind of fixture is, how it is made, and the
rules for adding one. It replaces an earlier plan for a `tests/fixtures/` tree of recorded upstream responses,
rasters and golden files; none of that was built.

Fixtures let the suites run without network access, keys or a database, and make a failure reproducible. They are all
**synthetic**: no real farm boundary, tree or survey is committed ([privacy design](../../docs/privacy/privacy-design.md)).

## Where the data is

| Data | Where | Made by | Used by |
| --- | --- | --- | --- |
| Three demo plots with an inventory and a note (IN, US, EU) | `data/sample/plots/*.json` | Written by hand from generated polygons | The API seeds them in demo mode (`PLT-DEMOIN`, `PLT-DEMOUS`, `PLT-DEMOEU`); the geo-engine detection tests read them |
| API sample responses (plot, analysis, estimate, policy, simulation, report, tree age, imagery providers) | `data/sample/responses/*.json` and `report.html` | `scripts/make_sample_responses.py` and `scripts/make_sample_tree_age.py`, which call the API in-process | The contract test, the QGIS plugin's formatting tests, the web demo fallback (below) and the documentation |
| Files to try "Import data" (KML, CSV, GeoJSON crowns, a LAZ point cloud) | `data/sample/imports/` | `scripts/make_sample_imports.py`, from fixed seeds | `apps/api/tests/test_imports_api.py`; you, with `curl` or the web app |
| Offline data for the web app | `apps/web/public/demo/` (21 files) | `npm run fixtures:demo`, which copies from `data/sample/responses/` | The web app's demo fallback when the API is offline, and the Playwright smoke tests |
| Small objects for web unit tests | `apps/web/src/test/fixtures.ts` | By hand | Vitest |
| Example farms with request bodies and `curl.sh` | `examples/` | By hand | You and the documentation; use them as the starting point for an API test |
| Synthetic point clouds and vegetation cubes | `geo_engine.pointcloud.synthetic`, `geo_engine.cube` (`build_demo_cube`) | Library code, deterministic from the inputs | The geo-engine, API and agent tests |
| Responses of external APIs | Built inside each test with `httpx.MockTransport` ([`integrations/tests/httpmock.py`](../../integrations/tests/httpmock.py)) | By hand, from the provider's documentation | The adapter tests |
| The configuration under test | `config/` | The project | `tests/data-quality/` reads the YAML directly; the engines load it through their parameter stores |

`make samples` regenerates the three groups of sample files and the web fixtures in one go. The details of each
folder are in [`data/sample/README.md`](../../data/sample/README.md).

## Keeping fixtures current

- `python3 scripts/make_sample_tree_age.py --check` and `python3 scripts/make_sample_imports.py --check` exit with 1
  when a committed file no longer matches what the code produces. Their output is deterministic (a pinned clock, fixed
  seeds), so a diff means behaviour or data changed.
- `scripts/make_sample_responses.py` has no `--check`, and the files it writes carry the generation time, so a re-run
  changes them even when nothing else did. `tests/integration/test_contract_fixtures.py` guards the field names of six
  of them (`plot`, `analysis`, `carbon-estimate`, `policy-eligibility`, `market-scenario`, `regions`) against the live
  demo API. Regenerate after an intentional contract change, then run `npm run fixtures:demo` and commit both.
- The tree-age and imagery samples are not read by a test; they document the response shapes.

## Rules for adding a fixture

1. **Synthetic locations only.** Derive fixtures from the example farms or from obviously artificial geometry. Never
   commit a real boundary, a real point cloud or a recorded response for a real place. Do not put coordinates of a real
   plot into a test.
2. **Small.** Keep a file small: the largest committed sample, the LAZ point cloud, is under 1 MB. GeoTIFFs (`*.tif`)
   are ignored by `.gitignore`; generate rasters in the test instead of committing them.
3. **Generated, with the generator committed.** Write a script under `scripts/` with a fixed seed or a pinned clock, and
   give it a `--check` mode like `make_sample_imports.py`, so that a stale file is caught.
4. **Licensed.** A dataset fixture is covered by [`DATA_LICENSES.md`](../../docs/licensing/DATA_LICENSES.md). Name the
   dataset, version, acquisition date and licence next to it and keep the attribution string.
5. **No secrets.** Never commit an API key, token or request id. `make_sample_tree_age.py` blanks the Esri key and
   refuses output that still contains a `${...}` placeholder; gitleaks runs in CI.
6. **Do not paste the output of your own code as the expected value.** Take reference values from the source (a paper,
   a table, a hand calculation) and write the source and tolerance in the test
   ([testing guide](../../docs/developer-guide/testing.md)).

## Links

- [Tests overview](../README.md)
- [Sample data](../../data/sample/README.md)
- [Examples](../../examples/README.md)
- [Testing guide for developers](../../docs/developer-guide/testing.md)
