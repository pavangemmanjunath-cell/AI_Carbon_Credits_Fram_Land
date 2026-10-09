# Data retention

Retention is a privacy control, not a storage-cost decision: every day a
boundary sits in a cache is a day it can leak. This page states the
defaults the software applies, what deletion covers, how export works and
what a deployer must decide for themselves.

## Defaults by data class

| Data | Default retention | Configurable by | Rationale |
|---|---|---|---|
| Plots, inventories, estimates (repository) | Until the owner deletes them; in-memory repository: until process restart | `ATLAS_REPOSITORY`; deployer's own policy | Users expect to return to their plots |
| Analyses (latest per plot) | Replaced on re-analysis; deleted with the plot | — | Only the latest is needed; history is in provenance |
| Cached upstream responses (WorldCover windows, Sentinel-2 band windows, STAC results, Open-Meteo, SoilGrids, geocoder) | 30 days from last access, or dataset-version change, whichever is first | `ATLAS_CACHE_TTL_DAYS` (planned), bucket lifecycle rules | Raster windows equal the plot bounding box and are therefore location data |
| Cubes | Regenerated from cache; same TTL | as above | |
| Reports (`ATLAS_REPORTS_DIR` or bucket) | 30 days; owner may download and re-generate at any time | `ATLAS_REPORTS_TTL_DAYS` (planned), lifecycle rules | A report can contain the boundary if the owner chose to include it |
| API access logs | 14 days | Edge/API logging configuration | Operational debugging; contain plot ids and IPs, never coordinates |
| Application logs | 14 days | Logging configuration | Same |
| Rate-limit and session state | Minutes to hours | `ATLAS_RATE_LIMIT`, deployment | Transient |
| Database backups | Deployer-defined; recommended ≤ 35 days | Deployer | Deleted plots persist in backups until the backup expires; say so in the notice |
| Demo-mode data | Process lifetime | — | Synthetic, pre-seeded plots `PLT-DEMOIN`, `PLT-DEMOUS`, `PLT-DEMOEU` |

Values marked *planned* are the agreed defaults the implementation
targets; until the variables exist, deployers enforce them with bucket
lifecycle rules and a cron job over `ATLAS_CACHE_DIR` and
`ATLAS_REPORTS_DIR`.

## Deletion

`DELETE /plots/{plot_id}` (owner only) removes, synchronously or through a
queued job that completes within 24 hours:

1. the plot record, including geometry and centroids;
2. all inventories, estimates, analyses and policy/market results for the
   plot;
3. report files and their metadata;
4. cache entries keyed by the plot's bounding box or centroid, including
   cubes;
5. search indexes or materialized views, if a deployment adds them.

Deletion is logged as an event with the plot id and timestamp (no
coordinates) so that it can be evidenced. Backups are not rewritten;
instead, restoring a backup replays the deletion log before the service
comes back, and the backup retention window is disclosed to users.
Deleting the last plot of an API key does not delete the key; key
lifecycle is the deployer's concern.

## Export

Owners can export everything stored about a plot as a single JSON bundle
(`GET /plots/{plot_id}/export`, planned for Phase 11; until then, the
individual `GET` endpoints provide the same data). The bundle contains
the plot with geometry, inventories, the latest analysis, all estimates
with provenance, policy screenings, market scenarios, report metadata and
a `schema_version`. It is produced on demand, delivered over the
authenticated session and never stored server-side. Reports in HTML,
Markdown, JSON and (optionally) PDF are the human-readable export.

## Anonymized aggregates

A deployment may keep **aggregate** statistics after deletion (for example
"plots analyzed per district per month", "median NDVI trend by species")
provided that no cell contains fewer than five plots and no exact geometry
or plot id is retained. Such aggregates are not personal data under the
project's own rules; whether they are under local law is for the deployer
to determine.

## Research use

Field or inventory data contributed to validation studies is stored
outside the production system, under written consent, with its own
retention stated in the consent form, and is never committed to the
repository ([../../research/README.md](../../research/README.md)).

## Checklist for deployers

- Set lifecycle rules on the cache and reports buckets to the defaults
  above or stricter.
- Configure log retention and verify that logs contain no coordinates
  (run the redaction test against production logging configuration).
- Document backup retention and the deletion-replay procedure.
- Publish the retention table in your privacy notice
  ([farmer-data.md](farmer-data.md)).
- Test `DELETE /plots/{id}` end to end, including cache removal, before
  going live.
