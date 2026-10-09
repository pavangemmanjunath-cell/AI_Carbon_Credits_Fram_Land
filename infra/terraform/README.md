# Reference infrastructure layout (Terraform)

This directory documents a **reference** deployment of AgriCarbon Atlas on
any cloud that offers S3-compatible object storage and container hosting. It
contains no secrets and, at the moment, no `.tf` files: the layout below is
the agreed shape so that a contributor can write modules for a specific
provider (AWS, Cloudflare R2 + Fly.io, Hetzner + MinIO, Azure with an S3
gateway, …) without re-deciding the architecture. Demo mode needs none of
this; `docker compose up` is enough
([getting-started.md](../../docs/user-guide/getting-started.md)).

## What needs to exist

| Component | Purpose | Notes |
|---|---|---|
| Object bucket `agricarbon-atlas-tiles` | Protomaps PMTiles basemap, optional terrain and satellite mosaics | Public read, HTTP Range requests, CORS exposing `ETag` and `Content-Range`; served through a CDN with a long cache. ODbL attribution is mandatory for OSM-derived tiles ([MAP_LICENSES.md](../../docs/licensing/MAP_LICENSES.md)). |
| Object bucket `agricarbon-atlas-cache` | Cached WorldCover clips, Sentinel-2 band windows, SoilGrids and Open-Meteo responses | **Private.** Clips are bounded by plot bounding boxes and therefore reveal location; treat as personal data ([data-retention.md](../../docs/privacy/data-retention.md)). |
| Object bucket `agricarbon-atlas-reports` | Rendered reports (HTML/PDF) | Private; expiring pre-signed URLs only. |
| Container service `api` | `infra/docker/Dockerfile.api`, port 8000 | Non-root (uid 10001). Environment from a secret store, never from a committed file. Horizontal scaling is safe when `ATLAS_REPOSITORY=postgres`. |
| Container service `web` | `infra/docker/Dockerfile.web`, port 8080 | Stateless. Set `ATLAS_API_ORIGIN` and `ATLAS_BASEMAP_ORIGINS` so the CSP matches the deployment. |
| PostgreSQL 16 + PostGIS 3.4 | Plot, inventory and estimate repository | Encrypted at rest; daily backups with a retention that matches the privacy policy; `DATABASE_URL` from the secret store. |
| Secret store | `ATLAS_API_KEYS`, `DATABASE_URL`, `S3_*`, `USDA_NASS_API_KEY`, `DATA_GOV_IN_API_KEY`, `COPERNICUS_TOKEN`, optional `LLM_API_KEY` | Rotate on leak; CI never has production secrets. |
| Edge / load balancer | TLS termination, HSTS, rate limiting in addition to the API's 60 req/min | Forward `X-Forwarded-For` only if the API is configured to trust it. |
| Observability | Logs, metrics, uptime check on `/api/v1/health` | Logs must never contain coordinates; use the structured logger's redaction and test it ([threat-model.md](../../docs/privacy/threat-model.md)). |

## Proposed module layout

```text
infra/terraform/
├── README.md                 ← this file
├── modules/
│   ├── object-storage/       # buckets, CORS, lifecycle rules, CDN origin
│   ├── container-service/    # api + web services, health checks, autoscaling
│   ├── database/             # PostgreSQL + PostGIS, backups, network rules
│   └── secrets/              # secret definitions (values injected out of band)
└── environments/
    ├── staging/              # small instances, demo or live mode, short retention
    └── production/           # live mode, ATLAS_ALLOW_PENDING_PARAMETERS=false
```

Each environment holds a `terraform.tfvars.example` with placeholder values
and **no** real identifiers. State is stored remotely with locking; never
commit `terraform.tfstate`.

## Environment variables per service

The API reads the variables in [`.env.example`](../../.env.example).
Production must set `ATLAS_ENV=production`, `ATLAS_MODE=live`,
`ATLAS_ALLOW_PENDING_PARAMETERS=false`, a non-empty `ATLAS_API_KEYS`,
`ATLAS_CORS_ORIGINS` limited to the web origin, and a `NOMINATIM_USER_AGENT`
with a working contact address (required by the Nominatim usage policy,
<https://operations.osmfoundation.org/policies/nominatim/>). Heavy
geocoding traffic should go to a self-hosted Nominatim or Photon instance
rather than the public servers.

The web image is built once per environment because `VITE_*` values are
compiled into the bundle; pass them as build arguments in the CI/CD
pipeline, not in Terraform.

## Bucket CORS for PMTiles

PMTiles are read with `fetch()` and HTTP Range requests from the browser.
The tiles bucket (or the CDN in front of it) must return:

```text
Access-Control-Allow-Origin: https://atlas.example.org
Access-Control-Allow-Methods: GET, HEAD
Access-Control-Allow-Headers: Range, If-Match, If-None-Match
Access-Control-Expose-Headers: ETag, Content-Range, Content-Length, Accept-Ranges
Access-Control-Max-Age: 86400
```

See the Protomaps deployment notes
(<https://docs.protomaps.com/pmtiles/cloud-storage>) for provider-specific
settings.

## Privacy and retention in infrastructure terms

- Lifecycle rules on `agricarbon-atlas-cache` and `agricarbon-atlas-reports`
  implement the defaults in
  [data-retention.md](../../docs/privacy/data-retention.md).
- Database backups inherit deletion obligations: document the backup
  retention window in the deployment's privacy notice.
- Access logs at the edge contain IP addresses and request paths; request
  paths carry plot identifiers but never coordinates, by API design.

## Cost expectations (order of magnitude)

A regional Protomaps basemap for one country is typically a few hundred MB
to a few GB; serving it from object storage behind a CDN costs far less
than hosted tile APIs at the same volume and avoids third-party usage
policies. Sentinel-2 reads from public COG archives (Earth Search on AWS
`us-west-2`) are free of egress charges for the data provider but incur
compute time in the API; cache aggressively.
