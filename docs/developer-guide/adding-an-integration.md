# Adding an integration

The application never calls a public service directly. Every external API or
dataset sits behind an adapter in
[`integrations/atlas_integrations/`](../../integrations/atlas_integrations/) that
states its source, license, attribution, rate limits, caching and failure
behavior, takes its endpoint from an environment variable, and has an offline
**demo twin** ([CLAUDE.md](../../CLAUDE.md) principles 5 and 6). This page
shows the steps, with a skeleton you can copy. The existing adapters are the
best reference: start with
[`soilgrids/adapter.py`](../../integrations/atlas_integrations/soilgrids/adapter.py)
(a plain JSON point query) and
[`nominatim/adapter.py`](../../integrations/atlas_integrations/nominatim/adapter.py)
(a source with strict usage rules).
[`integrations/README.md`](../../integrations/README.md) lists what exists, and
[`docs/data-sources/FREE_APIS.md`](../data-sources/FREE_APIS.md) lists every source with its terms.

## Which kind of integration is it?

| You want to add | Do this | Where |
| --- | --- | --- |
| An API or dataset that returns data for a place (climate, soil, land cover, statistics, geocoding) | An adapter with a demo twin: **this page** | `integrations/atlas_integrations/<name>/` |
| A satellite or aerial map layer for the web map | An entry in the imagery provider list. It is configuration, not an adapter: the API reports which providers are usable and under what license, and the browser loads the tiles | `config/imagery/providers.yaml`, then a row in [`MAP_LICENSES.md`](../licensing/MAP_LICENSES.md) and the [imagery research note](../research/imagery-providers.md) |
| A new file format for imports (GeoJSON, KML, CSV and LAS/LAZ exist) | A parser in the geo engine. Keep the raw file out of storage, parse XML with `defusedxml`, and respect the size limits | `packages/geo-engine/geo_engine/imports/` |
| Something an agent can ask for | A tool that calls an existing service. An agent never calls an adapter or computes a number itself | `apps/api/app/agents/tools.py` |
| A client of the API (like the QGIS plugin) | A separate deliverable that talks to the API only | `integrations/` or its own folder, with its own license review |

The rest of this page is about the first kind.

## 0. Check the source first

Open a "Data source proposal" issue (the form is
[`data_source.yml`](../../.github/ISSUE_TEMPLATE/data_source.yml)) before you write
code. The questions that decide whether the source can be used:

- **License and terms.** Can the data be fetched, cached and shown, and what
  attribution is required? A source whose terms cannot be documented is out of scope
  ([GOVERNANCE.md](../../GOVERNANCE.md)). Check the terms of the *derived output* too: a
  share-alike license affects what the Atlas can publish.
- **Rate limits and usage policy.** Quote the provider's published limit with a link.
  If you cannot find one, write `TODO(verify)`; never guess a number.
- **Authentication.** Free key or none. A paid source is not an option for the default
  setup.
- **Privacy.** Which coordinates would the provider see? Prefer the least precision the
  provider needs.

## 1. Licensing metadata

Add the row before the adapter, so the license question is answered once, in review:

1. A row in [`docs/licensing/DATA_LICENSES.md`](../licensing/DATA_LICENSES.md): source and
   URL, purpose, coverage, license with a link to the terms, the exact attribution text,
   whether results may be stored, and the date you checked.
2. The attribution text in [`docs/licensing/ATTRIBUTION.md`](../licensing/ATTRIBUTION.md)
   and an entry in `ATTRIBUTION_ITEMS` in `apps/api/app/services/regions.py`, which
   `GET /api/v1/attribution` serves to the interface and reports.
3. A row for the source in [`docs/data-sources/FREE_APIS.md`](../data-sources/FREE_APIS.md), with its
   endpoint variable, license, attribution, key requirement, rate limit or usage policy, adapter path and
   demo twin.
4. If the adapter needs a new Python or npm package, a row in
   [`docs/licensing/THIRD_PARTY.md`](../licensing/THIRD_PARTY.md) with its license, checked from the
   installed package metadata (`pip show <package>`), not from memory.

## 2. The package

```text
integrations/atlas_integrations/<name>/
    __init__.py     exports SOURCE, the live adapter, the demo twin and the result type
    adapter.py      SOURCE, result dataclass, live adapter, demo twin
    README.md       the seven items below (CLAUDE.md principle 6)
```

The README (or at least the module docstring) states: the source and endpoint variable,
the license and attribution, the rate limit, the cache policy, and how a failure
behaves. The adapters document
these in docstrings and in [`integrations/README.md`](../../integrations/README.md); a README per
adapter is still open work, and writing one is a good first contribution
([starter issues](../community/starter-issues.md)).

`adapter.py`, modeled on SoilGrids:

```python
"""<Service name> adapter: <what it returns for a point>.

Endpoint ``EXAMPLE_API_URL`` (<default URL>), parameters <...>.
License <license>; attribution "<exact text>".
Rate limit: <the provider's published limit, with a link; TODO(verify) if unknown>.
Cache: <ttl and why>. Failure: raises UpstreamError / NotFoundError / UpstreamDataError.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from atlas_integrations.base import (
    Cache,
    HttpAdapter,
    SourceProvenance,
    UpstreamDataError,
    demo_source,
)
from atlas_integrations.demo_support import region_for, unit_noise

SOURCE = SourceProvenance(
    id="example-source",
    name="<Dataset or service name>",
    version="<dataset version>",
    license="<license>",
    attribution="<exact attribution text>",
    url="<dataset home page>",
)


@dataclass(frozen=True)
class ExampleResult:
    value: float | None
    source: dict[str, Any]  # provenance of this observation

    def to_dict(self) -> dict[str, Any]:
        return {"value": None if self.value is None else round(self.value, 2)}


class ExampleAdapter(HttpAdapter):
    def __init__(self, url: str, cache: Cache | None = None, **kwargs: Any) -> None:
        super().__init__(cache=cache, cache_ttl_s=7 * 86_400.0, **kwargs)
        self.url = url  # injected from the environment, never a literal

    def fetch_value(self, lat: float, lon: float) -> ExampleResult:
        data = self.get_json(self.url, params={"lat": lat, "lon": lon})
        try:
            value = float(data["result"]["value"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamDataError("Example Service payload malformed") from exc
        return ExampleResult(value, SOURCE.to_dict(datetime.now(UTC)))

    @staticmethod
    def provenance() -> dict[str, Any]:
        return SOURCE.to_dict()


class DemoExampleAdapter:
    """Same methods, synthetic and deterministic, labeled `synthetic-demo`."""

    def fetch_value(self, lat: float, lon: float) -> ExampleResult:
        hint = region_for(lat, lon)
        base = 10.0 if hint else 8.0
        value = base + 2.0 * (unit_noise("example", round(lat, 2), round(lon, 2)) - 0.5)
        return ExampleResult(value, demo_source(SOURCE).to_dict(datetime.now(UTC)))

    @staticmethod
    def provenance() -> dict[str, Any]:
        return demo_source(SOURCE).to_dict()
```

`__init__.py`:

```python
from atlas_integrations.example_source.adapter import (
    SOURCE,
    DemoExampleAdapter,
    ExampleAdapter,
    ExampleResult,
)

__all__ = ["SOURCE", "DemoExampleAdapter", "ExampleAdapter", "ExampleResult"]
```

## 3. Rules every adapter follows

| Rule | How |
| --- | --- |
| Endpoint and keys from the environment | The constructor takes the URL and key as arguments; `ModeRouter` passes them from `Settings`. No URL literal in application code. `SOURCE.url` is the dataset's home page, not an endpoint |
| Typed errors | Extend `HttpAdapter`. It maps 404 to `NotFoundError`, 429 to `RateLimitedError`, 401 and 403 to `ConfigurationError`, other 4xx and 5xx to `UpstreamError`, and a non-JSON body to `UpstreamDataError`. Raise `UpstreamDataError` yourself when the JSON has an unexpected shape. Raise `ConfigurationError` when a required key or `User-Agent` is missing |
| Timeout and retry | `HttpAdapter` uses a 20 second timeout and retries once on a 5xx or a transport error. Do not add retry loops |
| Caching | Pass a `Cache` (the router shares one `MemoryTTLCache`) and set `cache_ttl_s` to how fast the data really changes. Build keys with `cache_key(...)`, a SHA-256 of the request identity, so coordinates are not readable keys |
| Rate limits | For a strict policy, throttle with a process-wide lock as `nominatim/adapter.py` does (`_Throttle` and `GEOCODER_MIN_INTERVAL_SECONDS`) and send the identifying `User-Agent` the policy asks for |
| Privacy | Error messages carry the host and status only, never the query. Never log coordinates. Send the provider the least precision it needs. In v0.1 the point adapters (`open_meteo`, `soilgrids`) pass the centroid at full precision; rounding it to the provider's native resolution is an open improvement |
| Optional heavy dependencies | Import `rasterio` or `pystac-client` inside the method and raise `DependencyMissingError` with an install hint (`pip install -e "integrations[live]"`), so demo mode and CI do not need them |
| Provenance on every result | Return the `SOURCE.to_dict(...)` of the observation (with the access time). Add `dataset_version`, scene ids or similar through `extra` when you have them |
| No invented values | If the provider returns nothing, return `None` or raise; never substitute a plausible number |

## 4. The demo twin

Demo mode and CI never touch the network, so every adapter needs a twin:

- Same method names and result types as the live adapter.
- Deterministic: derive pseudo-random values from the inputs with `unit_noise(...)` or
  `seed_from(...)` in `demo_support.py`, so two runs give the same answer.
- Plausible, not real. Use `region_for(lat, lon)` for a regional baseline.
- Labeled: `demo_source(SOURCE)` produces the `synthetic-demo` provenance. A demo value
  must never be presentable as an observation.

## 5. Wire it into the API

1. **Settings.** Add the fields to `Settings` in `apps/api/app/core/config.py`
   (`example_api_url` with the real default URL; `example_api_key` if needed) and a
   documented line to [`.env.example`](../../.env.example) and a row to the variable table in
   [setup](setup.md#environment-variables). Keep the three in step: today `.env.example` has lines
   that `Settings` does not read and settings that it does not list.
2. **Router.** Add a property to `ModeRouter` (`apps/api/app/services/adapters.py`):

   ```python
   @cached_property
   def example(self) -> Any:
       if self.settings.is_demo:
           return DemoExampleAdapter()
       return ExampleAdapter(self.settings.example_api_url, cache=self.cache)
   ```

   The existing keyed adapters (`usda_nass`, `data_gov_in`) fall back to the demo twin
   when the key is empty, which hides a misconfiguration behind synthetic data. For a new
   adapter prefer failing loudly in live mode (raise `ConfigurationError`).
3. **Service.** Call it from a service, never from a router or a component. Catch
   `AdapterError` (the services also catch `OSError` and `ValueError`), add a warning to
   `data_quality.warnings`, and return `None` for that block. Attach provenance with
   `base_provenance(self.router.mode, [dict(result.source)])`. See `_soil` in
   `apps/api/app/services/analysis.py`.
4. **Agents.** If an agent should talk about the new data, add a tool in
   `apps/api/app/agents/tools.py` that calls the **service** and returns a summary without coordinates.
   Agents never call adapters directly.
5. **Contract.** If the response gains a field, update
   [`docs/architecture/api-contract.md`](../architecture/api-contract.md), the schemas in
   `data/schemas/` and the web types in `apps/web/src/types/api.ts`, and refresh the demo
   fixtures.

## 6. Tests

Adapter tests never use the network. `integrations/tests/httpmock.py` provides
`make_client(handler, recorder)` (an `httpx.Client` over `httpx.MockTransport`) and
`json_response(payload, status)`, and `conftest.py` provides a `recorder` fixture. Add
`integrations/tests/test_<name>.py` with at least:

```python
import httpx
import pytest
from httpmock import json_response, make_client

from atlas_integrations import MemoryTTLCache, UpstreamDataError, UpstreamError
from atlas_integrations.example_source import DemoExampleAdapter, ExampleAdapter


def test_parses_the_value_and_records_provenance(recorder):
    adapter = ExampleAdapter(
        "https://example.test/api",
        client=make_client(lambda r: json_response({"result": {"value": 4.2}}), recorder),
    )
    result = adapter.fetch_value(13.29, 77.54)
    assert result.value == pytest.approx(4.2)
    assert result.source["license"]  # provenance is attached
    assert recorder.last.url.params["lat"] == "13.29"


def test_malformed_payload_is_a_data_error():
    adapter = ExampleAdapter(
        "https://example.test/api", client=make_client(lambda r: json_response({"x": 1}))
    )
    with pytest.raises(UpstreamDataError):
        adapter.fetch_value(13.29, 77.54)


def test_errors_never_contain_coordinates():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    adapter = ExampleAdapter(
        "https://example.test/api", client=make_client(down), retry_backoff_s=0
    )
    with pytest.raises(UpstreamError) as excinfo:
        adapter.fetch_value(13.29, 77.54)
    assert "13.29" not in str(excinfo.value)


def test_second_identical_call_is_served_from_the_cache(recorder):
    adapter = ExampleAdapter(
        "https://example.test/api",
        cache=MemoryTTLCache(),
        client=make_client(lambda r: json_response({"result": {"value": 1}}), recorder),
    )
    adapter.fetch_value(13.29, 77.54)
    adapter.fetch_value(13.29, 77.54)
    assert len(recorder.requests) == 1


def test_demo_twin_is_deterministic_and_labeled():
    first = DemoExampleAdapter().fetch_value(13.29, 77.54)
    assert first.value == DemoExampleAdapter().fetch_value(13.29, 77.54).value
    assert first.source["id"] == "synthetic-demo"
```

Also cover each status you handle specially (a 429, a missing key) and every branch of
your parser. Run `python3 -m pytest integrations -q`; the API tests in
`apps/api/tests/` exercise the router in demo mode.

## 7. Documentation

- `integrations/README.md`: a row in the adapter table (endpoint variable, credentials,
  license, cache).
- `docs/data-sources/FREE_APIS.md` and `docs/licensing/DATA_LICENSES.md`, as in step 1.
- The region's `DATA_SOURCES.md` page under `docs/regions/` if the source serves a
  region ([adding a region](adding-a-region.md)).

## Checklist for the pull request

- [ ] License row, attribution text and `ATTRIBUTION_ITEMS` entry added first
- [ ] `SOURCE` complete; `provenance()` on both the adapter and the twin
- [ ] Endpoint and key from `Settings` and `.env.example`; no URL literal in app code
- [ ] Typed errors; messages carry no coordinates or query text
- [ ] Cache with a justified TTL; rate-limit handling and the provider's limit quoted
- [ ] Demo twin: same API, deterministic, labeled `synthetic-demo`
- [ ] Router property, service call with a warning on failure, provenance attached
- [ ] Tests without network access (parse, malformed, errors, cache, demo)
- [ ] Docs updated (`FREE_APIS.md`, `DATA_LICENSES.md`, the variable table in setup); the PR description
      states the license and privacy impact

Next: [testing](testing.md) or [troubleshooting](troubleshooting.md).
