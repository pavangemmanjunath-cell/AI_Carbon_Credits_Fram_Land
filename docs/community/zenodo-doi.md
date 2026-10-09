# Getting a DOI for a release (Zenodo)

1. Sign in at <https://zenodo.org> with GitHub, open *Profile → GitHub* and press *Sync now*.
2. Switch the repository **on**.
3. Keep `CITATION.cff` and `.zenodo.json` current (Zenodo prefers `.zenodo.json` when both exist).
4. On GitHub create a Release (for example `v0.2.0`). Zenodo archives it and issues a DOI such as `10.5281/zenodo.xxxxxxx`.
5. Add the DOI to the README and to `CITATION.cff` (`doi:`), then commit.
