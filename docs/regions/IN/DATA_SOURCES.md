# Data sources — India

Global datasets (ESA WorldCover, Sentinel-2, Open-Meteo, SoilGrids,
OpenStreetMap) serve Indian plots exactly as elsewhere; this page covers
the India-specific sources, how to obtain access, and what we deliberately
do not use. Licenses are consolidated in
[../../licensing/DATA_LICENSES.md](../../licensing/DATA_LICENSES.md).

## data.gov.in — district crop production

The Open Government Data platform publishes agricultural statistics from
the Ministry of Agriculture and Farmers Welfare under the Government Open
Data License – India (GODL,
<https://data.gov.in/government-open-data-license-india>). The Atlas uses
the district-wise, season-wise crop production dataset to populate the
"other farm income" context (area, production and derived yield for the
plot's district and crop).

| Item | Detail |
|---|---|
| Access | REST API, `https://api.data.gov.in/resource/{resource_id}` with `api-key`, `format=json`, `limit`, `offset` and `filters[field]=value` parameters |
| Key | Free; register at <https://data.gov.in/> and generate an API key; set `DATA_GOV_IN_API_KEY` |
| Resource id | `DATA_GOV_IN_CROP_RESOURCE_ID` — the `.env.example` value points at a district-wise crop production resource and is marked *verify*: resource ids change when datasets are republished, and several versions exist (older series ending 2014–15, newer series by year). Confirm the id on the dataset page before deploying |
| Fields (typical) | `state_name`, `district_name`, `crop_year`, `season`, `crop`, `area_` (hectares), `production_` (tonnes, or other units for some crops such as coconut in nuts) |
| Rate limits | Not published precisely; the adapter uses a conservative interval and caches by (state, district, crop, year) |
| Caveats | District names must be normalized (spelling, renamed and bifurcated districts); units differ by crop; yields derived from area and production are district averages, not farm values |
| Attribution | "Source: data.gov.in — Ministry of Agriculture and Farmers Welfare, Government of India" |

Other data.gov.in resources that may be added later through the same
adapter: horticulture area and production (National Horticulture Board),
agricultural market prices (Agmarknet, <https://agmarknet.gov.in/>), and
rainfall statistics (IMD).

## Bhuvan (NRSC / ISRO)

Bhuvan (<https://bhuvan.nrsc.gov.in/>) provides thematic geospatial
services for India, including land use / land cover at 1:250,000 and
1:50,000 scales, wasteland atlases and some high-resolution imagery.
Access to many layers requires registration and, for APIs, a token; terms
are layer-specific. The Atlas does not integrate Bhuvan in v0.1; a
contributor adding it must document the layer's terms in the data-source
issue template and respect that Bhuvan imagery is not generally licensed
for redistribution. Bhuvan's wasteland and LULC layers are relevant to
the Green Credit Programme's "degraded land" question
([GREEN_CREDIT.md](GREEN_CREDIT.md)).

## Forest Survey of India

The India State of Forest Report (<https://fsi.nic.in/>) gives district
forest-cover statistics every two years; useful as context for tree-cover
shares from WorldCover but not integrated.

## State portals

| State | Portal | Relevance | Status |
|---|---|---|---|
| Karnataka | Karnataka Forest Department (<https://aranya.gov.in/>) — Krishi Aranya Protsaha Yojane details and nursery locations | Incentive screening ([INCENTIVES.md](INCENTIVES.md)) | referenced |
| Karnataka | FRUITS farmer registration, Bhoomi land records | Identity and land records — **not used**: privacy; the Atlas never asks for survey numbers or farmer ids | excluded by design |
| All states | Soil Health Card portal (<https://soilhealth.dac.gov.in/>) | Farmer-held soil test results could replace SoilGrids context if the farmer enters them | planned as user input, not integration |
| All states | State horticulture mission pages (MIDH) | Orchard establishment subsidies | referenced in incentives |

## Geocoding in India

Nominatim's coverage of village names and transliterations varies; the
geocoder adapter sends `country=IN` to narrow results and returns state
and district from the result's address fields. Deployments expecting
heavy use should self-host Nominatim or Photon
([../../architecture/mapping-architecture.md](../../architecture/mapping-architecture.md)).
Survey of India and state cadastral maps are not integrated.

## Earth observation specifics

- Sentinel-2 tiles over India are available from both Earth Search (AWS)
  and the Copernicus Data Space; monsoon cloud cover (June–September)
  means the monthly composites frequently have low `valid_share` in those
  months, which the cube and the trend statement expose rather than hide.
- WorldCover 2021 is the land-cover baseline; its "Tree cover" class
  includes orchards and plantations above the canopy threshold, so an
  established mango orchard appears as tree cover while a young one
  appears as cropland or grassland.

## What we do not use

Land-record systems (Bhoomi, Dharani, Mee Bhoomi), Aadhaar-linked farmer
registries and PM-KISAN data are deliberately out of scope: the platform
needs no identity and must not become a reason to collect it
([../../privacy/farmer-data.md](../../privacy/farmer-data.md)).
