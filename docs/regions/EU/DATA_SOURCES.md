# Data sources — European Union

Global datasets (ESA WorldCover, Sentinel-2, Open-Meteo, SoilGrids, OpenStreetMap) serve EU plots exactly as they serve
plots elsewhere. This page covers what is specific to the EU: the Copernicus data CarbonCreditBuy relies on, the sources
it
does not yet have, and what we deliberately do not use. Licenses are consolidated in
[`docs/licensing/DATA_LICENSES.md`](../../licensing/DATA_LICENSES.md), and every source's endpoint, key, cache and
failure behavior is in [FREE_APIS.md](../../data-sources/FREE_APIS.md).

**Status in version 0.1.** The EU region file names no source of crop statistics, and the repository has no adapter for
one ([`config/regions/EU.yaml`](../../../config/regions/EU.yaml)). India and the United States have crop-statistics
adapters that are built but not called yet. For every region, the lines of the "Other farm income" card are empty in
version 0.1.

## Copernicus Sentinel-2

The EU's Copernicus program is the source of the vegetation indices CarbonCreditBuy uses everywhere. Two catalogs are
available, chosen by `ATLAS_STAC_PROVIDER`:

| Option | Endpoint variable | Credentials | Notes |
| --- | --- | --- | --- |
| Earth Search (AWS), the default | `EARTH_SEARCH_STAC_URL` | None | Cloud-optimized files on AWS Open Data |
| Copernicus Data Space Ecosystem | `COPERNICUS_STAC_URL` | `COPERNICUS_TOKEN` for asset downloads; search is anonymous | Applies its own terms of use in addition to the Sentinel data terms |

Sentinel data are free, full and open under the Copernicus legal notice, and CarbonCreditBuy shows "Contains modified
Copernicus
Sentinel data [year]" wherever it displays values derived from them
([ATTRIBUTION.md](../../licensing/ATTRIBUTION.md)). Cloud cover varies by season and region, and the 36-month vegetation
cube shows how many pixels were valid in each month instead of hiding gaps
([change over time](../../user-guide/results-explained.md#change-over-time)). Details are in
[FREE_APIS.md](../../data-sources/FREE_APIS.md).

## Land cover, climate and soil

- ESA WorldCover 2021 is the land-cover baseline. It is a 2021 snapshot, so trees planted since then do not show as tree
  cover.
- Open-Meteo normals set the climate zone in live mode: the server classifies mean annual temperature, annual
  precipitation and elevation into an IPCC-style zone ([METHODOLOGIES.md](METHODOLOGIES.md)). Without them the region
  default, `cool_temperate_moist`, applies to every EU plot, and it will not suit the Mediterranean or the far north.
- SoilGrids is a global 250 m model of soil organic carbon. National soil inventories are more detailed and are not
  used.

## Place search

When the selected country is the European Union, the search box does not restrict Nominatim to one country, so results
can include places outside the EU. The public Nominatim instance allows one request per second and requires an
identifying `User-Agent`; a deployment with heavy use should self-host Nominatim or Photon
([mapping architecture](../../architecture/mapping-architecture.md)). Place names come from OpenStreetMap in the
language
the mappers used.

## Imagery for the map

The map's **Satellite** view loads raster tiles from a provider that the API recommends for the plot's country
(`GET /api/v1/imagery/providers?country=FR`, from
[`config/imagery/providers.yaml`](../../../config/imagery/providers.yaml)). Three member states have a verified national
orthophoto and use it by default. Every other member state starts with the global Sentinel-2 mosaic. A person can choose
another provider under **Settings**, **Map imagery**. Imagery is for viewing: CarbonCreditBuy does not analyze these
tiles. The
license, attribution and analysis rule of every provider are in
[MAP_LICENSES.md](../../licensing/MAP_LICENSES.md), and the research is in
[imagery-providers.md](../../research/imagery-providers.md).

| Provider (id) | Role | Resolution | License | Attribution to show | Key | Max zoom |
| --- | --- | --- | --- | --- | --- | --- |
| IGN France, BD ORTHO (`ign-france-orthophotos`) | Default for FR | 20 cm | Licence Ouverte 2.0 (Etalab) | Source : IGN - Institut national de l'information géographique et forestière - Licence Ouverte 2.0 | None | 19 |
| IGN Spain, PNOA (`ign-spain-pnoa`) | Default for ES | 25 to 50 cm | CC BY 4.0 scne.es | PNOA CC-BY 4.0 scne.es | None | 19 |
| PDOK Luchtfoto RGB (`pdok-luchtfoto`) | Default for NL | 8 cm (5 cm in places) | CC BY 4.0 | Beeldmateriaal Nederland (beeldmateriaal.nl), CC BY 4.0, via PDOK | None | 21 |
| EOX Sentinel-2 cloudless 2016 (`eox-s2cloudless-2016`) | Default for every other member state | 10 m, from 2016 | CC BY 4.0 | The EOxCloudless text in the config, which mentions Copernicus Sentinel data | None | 14 |
| Esri World Imagery (`esri-world-imagery`) | Optional, display only | Varies by place | Esri Master License Agreement (proprietary) | Esri, Vantor, Earthstar Geographics, and the GIS User Community | `ESRI_API_KEY` | 19 |

The EOX 2017 layer has the same terms as 2016. The EOX 2025 layer is CC BY-NC-SA 4.0 and only for clearly
non-commercial deployments. Esri's terms prohibit using its tiles as input to automated extraction, and whether a free
open-source deployment counts as commercial use is not confirmed, so the config keeps `review-terms`. CarbonCreditBuy
shows
the attribution text of whichever provider is on screen.

Notes and what is not confirmed, from the research of 2026-10-05:

- The 2016 mosaic does not show anything built or planted since. The free EOX endpoint is "as is" and rate limited, so a
  production deployment needs an agreement with EOX or its own mosaic.
- The national layers are mosaics of surveys from different dates. Their attribution strings were composed from the
  license requirements, because none of the three providers mandates an exact text; add the survey date when you know
  it.
- Not confirmed: coverage of the French overseas departments, of the Canary Islands, Ceuta and Melilla, and of the
  Caribbean Netherlands, and any fair-use limit for the Dutch service. The French tile service documents no rate limit.
- Other member states publish open orthophotos too. None has been researched; add one with the steps in
  [adding an integration](../../developer-guide/adding-an-integration.md#which-kind-of-integration-is-it).
- A web container behind the Docker image only loads tiles from hosts listed in `ATLAS_EXTRA_IMG_SRC`; the development
  server has no such list
  ([troubleshooting](../../developer-guide/troubleshooting.md#a-basemap-or-imagery-works-with-npm-run-dev-but-not-in-docker)).

## Eurostat (candidate, not integrated)

Eurostat publishes regional agricultural statistics, and the region file names "Eurostat and national statistics" as the
source for fruit, olive and nut yield. The licenses table lists Eurostat as optional and not yet integrated: its reuse
policy is generally CC BY 4.0, with the attribution "Source: Eurostat"
([Eurostat copyright policy](https://ec.europa.eu/eurostat/about-us/policies/copyright);
[DATA_LICENSES.md](../../licensing/DATA_LICENSES.md)). Before an adapter is written, TODO(verify): the dataset and its
license, the NUTS level that is available for each crop, and how codes map to CarbonCreditBuy. Eurostat and NUTS codes
reportedly use `EL` for Greece, while CarbonCreditBuy uses the ISO 3166-1 code `GR` (verify), so a lookup table is
needed.
Follow [adding an integration](../../developer-guide/adding-an-integration.md) and the "Data source" issue form
([`data_source.yml`](../../../.github/ISSUE_TEMPLATE/data_source.yml)).

## Other candidates

None has been researched for CarbonCreditBuy; the license, endpoint, coverage and privacy impact of each are
TODO(verify).

| Candidate | What it could add |
| --- | --- |
| Copernicus DEM GLO-30 | Terrain and an elevation cross-check; already listed as optional in [DATA_LICENSES.md](../../licensing/DATA_LICENSES.md) |
| CORINE Land Cover and the LUCAS survey | EU land-cover and land-use references to compare with WorldCover |
| Orthophotos of other member states | Display imagery with national open licenses, as for France, Spain and the Netherlands above |
| National soil and forest inventories | Country-specific references that could replace global estimates |

## What we do not use

Land-parcel and farmer registers kept for CAP payments, and any record tied to a person, are out of scope: the platform
needs no identity and must not become a reason to collect it ([farmer data](../../privacy/farmer-data.md)). An
organization that operates CarbonCreditBuy in the EU is responsible for its own data-protection obligations; the privacy
pages are not legal advice.

## Related pages

[README.md](README.md) · [PROGRAMS.md](PROGRAMS.md) · [METHODOLOGIES.md](METHODOLOGIES.md) ·
[FREE_APIS.md](../../data-sources/FREE_APIS.md)
