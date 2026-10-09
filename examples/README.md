# Examples

Three synthetic farms, one per supported region, with request bodies that
match the [API contract](../docs/architecture/api-contract.md) and a
`curl.sh` walkthrough from plot creation to report. None of them is a real
property; the polygons were generated to hit a target area near a chosen
coordinate and the tree counts are illustrative.

| Example | Region | Plot | Trees | Demo plot id |
|---|---|---|---|---|
| [india-mango-farm](india-mango-farm/) | `IN`, Karnataka | ≈ 2.13 ha near 13.29 N 77.54 E | 420 mango, planted 2023 | `PLT-DEMOIN` |
| [usa-agroforestry](usa-agroforestry/) | `US`, Georgia | ≈ 8 ha near 32.5 N 83.7 W | 1,200 pecan, planted 2021 | `PLT-DEMOUS` |
| [eu-carbon-farming](eu-carbon-farming/) | `ES` → `EU` rules, Andalusia | ≈ 5 ha near 37.6 N 4.8 W | 900 olive, planted 2020 | `PLT-DEMOEU` |

Each folder contains `plot.request.json`, `trees.request.json`,
`carbon-estimate.request.json`, `simulate.request.json`, a `README.md`
describing the scenario and what to look for in the responses, and
`curl.sh`.

```bash
make dev                                  # API on :8000, web on :5173
ATLAS_API=http://localhost:8000/api/v1 ./examples/india-mango-farm/curl.sh
```

The scripts create a new plot and use the returned `plot_id`; the demo ids
are the identifiers of the plots pre-seeded by the API in demo mode and are
listed for reference. In demo mode every provenance block is labelled
`synthetic-demo`. Everything the scripts print is a scenario estimate with
`certified: false`.

To add an example, copy a folder, change the polygon (keep it synthetic and
between 0.01 and 10 000 ha), update the README, and run
`.github/workflows/lint.yml`'s JSON check locally:
`python3 -c "import json,glob; [json.load(open(p)) for p in glob.glob('examples/**/*.json', recursive=True)]"`.
