# Research

The `research/` tree holds the scientific work around AgriCarbon Atlas:
notebooks that validate inputs and models, experiments that compare
alternatives, the validation protocol that gates releases, and publication
drafts. It is kept in the main repository so that every number in a paper
can be traced to a commit of the engine and of `config/`.

The platform's scientific stance is modest by design. The carbon engine
applies published Tier 1 defaults (IPCC 2006, Vol. 4) and a pantropical
allometric model (Chave et al. 2014) to user-reported inventories; it does
not invent growth curves, and it reports ranges rather than points. Research
here serves to (a) check that the implementation reproduces the sources,
(b) quantify how far the defaults are from field or reference-tool values
for the crops and regions we support, and (c) tighten the uncertainty
where evidence allows.

| Folder | Content | Status |
|---|---|---|
| [notebooks/](notebooks/README.md) | Jupyter notebooks: NDVI validation, allometry comparison, uncertainty propagation | planned |
| [experiments/](experiments/README.md) | Reproducible experiment runs with configs and results tables | planned |
| [validation/](validation/README.md) | Validation protocol and acceptance criteria against COMET-Farm and field data | protocol written |
| [publications/](publications/paper-outline.md) | Paper outline and drafts | outline written |

## Principles

- **Reproducible.** Each notebook or experiment pins the repository commit,
  the `config/` versions and the dataset versions it used. Results tables
  are committed as CSV next to the code that produced them.
- **Synthetic or consented data.** Field data from real farms is used only
  with written consent and is stored outside the repository; the
  repository holds aggregated results and synthetic cases. Plot geometry
  is never committed.
- **Sources before conclusions.** A notebook that proposes a parameter
  change ends with the exact table cell or equation and a link, in the
  format `config/` expects (`source`, `unit`, `verification_status`).
- **Negative results count.** If a Tier 1 default is 40 % off COMET-Farm
  for pecan, that is a result to publish and to surface in the UI's
  confidence grading, not a reason to tune parameters quietly.

## Environment

Research dependencies (Jupyter, pandas, matplotlib, scikit-learn) are
intentionally not in the root `requirements.txt`. Create a separate
environment:

```bash
python3 -m venv .venv-research && . .venv-research/bin/activate
pip install -r requirements.txt -e packages/carbon-engine -e packages/geo-engine
pip install jupyterlab pandas matplotlib scipy
```

## Contributing research

Open an issue with the `research` label describing the question, the data
and the expected output. Review of research contributions focuses on
reproducibility and on the correctness of citations; see
[CONTRIBUTING.md](../CONTRIBUTING.md).
