# Software DOIs (Zenodo)

The repository is connected to Zenodo. Every GitHub Release is archived automatically and receives its own DOI.

| Identifier | DOI | Meaning |
|---|---|---|
| Version DOI, release `v1.1.1` | [10.5281/zenodo.23298816](https://doi.org/10.5281/zenodo.23298816) | Cites exactly that archived release |
| Version DOI, release `V_1.1` | [10.5281/zenodo.23298049](https://doi.org/10.5281/zenodo.23298049) | Cites exactly that archived release |
| Concept DOI | [10.5281/zenodo.23298048](https://doi.org/10.5281/zenodo.23298048) | Cites the software across all versions; resolves to the latest |

These are **software** DOIs. A journal or conference paper about the project will have its own, separate DOI; the
two are never interchanged.

## Releasing a new version

1. Finish the release checklist in [docs/reproducibility.md](../reproducibility.md#release-checklist) and update
   [CHANGELOG.md](../../CHANGELOG.md).
2. Create a GitHub Release with a semantic-version tag (for example `v1.1.1`). Zenodo archives it and issues a new
   version DOI under the same concept DOI.
3. Metadata comes from [`CITATION.cff`](../../CITATION.cff). The repository deliberately has no `.zenodo.json`:
   Zenodo prefers that file when it exists, and two metadata files drift apart.
4. After Zenodo shows the new record, put its version DOI in `CITATION.cff` (`doi:`, `version:`, `date-released:`,
   `identifiers:`) and in the README badge, then commit.
