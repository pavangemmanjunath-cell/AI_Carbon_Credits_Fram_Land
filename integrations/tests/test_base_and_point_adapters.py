from __future__ import annotations

import httpx
import pytest
from httpmock import json_response, make_client

from atlas_integrations import (
    ConfigurationError,
    MemoryTTLCache,
    NotFoundError,
    RateLimitedError,
    UpstreamDataError,
    UpstreamError,
)
from atlas_integrations.base import HttpAdapter, SourceProvenance, cache_key, demo_source
from atlas_integrations.census_geocoder import CensusGeocoderAdapter, DemoCensusGeocoderAdapter
from atlas_integrations.data_gov_in import DataGovInAdapter, DemoDataGovInAdapter
from atlas_integrations.open_meteo import DemoOpenMeteoAdapter, OpenMeteoAdapter
from atlas_integrations.soilgrids import DemoSoilGridsAdapter, SoilGridsAdapter
from atlas_integrations.usda_nass import DemoUsdaNassAdapter, UsdaNassAdapter

# --------------------------------------------------------------------------- base


def test_retry_once_on_5xx_then_success(recorder):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return json_response({"ok": True}) if calls["n"] > 1 else httpx.Response(503)

    adapter = HttpAdapter(client=make_client(handler, recorder), retry_backoff_s=0)
    assert adapter.get_json("https://example.test/x") == {"ok": True}
    assert calls["n"] == 2


def test_retry_on_transport_error_then_raise(recorder):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    adapter = HttpAdapter(client=make_client(handler, recorder), retry_backoff_s=0)
    with pytest.raises(UpstreamError) as excinfo:
        adapter.get_json("https://example.test/x", params={"lat": 13.29, "lon": 77.54})
    assert "13.29" not in str(excinfo.value) and "example.test" in str(excinfo.value)
    assert len(recorder.requests) == 2


@pytest.mark.parametrize(
    "status, error",
    [
        (404, NotFoundError),
        (429, RateLimitedError),
        (401, ConfigurationError),
        (418, UpstreamError),
    ],
)
def test_status_codes_map_to_typed_errors(status, error):
    adapter = HttpAdapter(client=make_client(lambda r: httpx.Response(status)), retry_backoff_s=0)
    with pytest.raises(error):
        adapter.get_json("https://example.test/x")


def test_non_json_payload_raises_data_error():
    adapter = HttpAdapter(client=make_client(lambda r: httpx.Response(200, content=b"<html>")))
    with pytest.raises(UpstreamDataError):
        adapter.get_json("https://example.test/x")


def test_cache_prevents_second_request(recorder):
    adapter = HttpAdapter(
        client=make_client(lambda r: json_response({"v": 1}), recorder), cache=MemoryTTLCache()
    )
    adapter.get_json("https://example.test/x", params={"a": 1})
    adapter.get_json("https://example.test/x", params={"a": 1})
    adapter.get_json("https://example.test/x", params={"a": 2})
    assert len(recorder.requests) == 2
    assert recorder.requests[0].headers["user-agent"].startswith("agricarbon-atlas")


def test_cache_key_is_stable_and_opaque():
    assert cache_key("a", {"lat": 1.0}) == cache_key("a", {"lat": 1.0})
    assert "lat" not in cache_key("a", {"lat": 1.0})


def test_memory_ttl_cache_expiry(monkeypatch):
    cache = MemoryTTLCache(max_items=2)
    cache.set("a", 1, ttl_s=100)
    cache.set("b", 2, ttl_s=100)
    cache.set("c", 3, ttl_s=100)  # evicts the oldest
    assert cache.get("a") is None and cache.get("c") == 3
    import atlas_integrations.base as base

    now = base.time.monotonic()
    monkeypatch.setattr(base.time, "monotonic", lambda: now + 1000)
    assert cache.get("c") is None


def test_provenance_records():
    src = SourceProvenance("x", "X data", "1", "CC BY 4.0", "© X", "https://x")
    data = src.to_dict()
    assert data["accessed_at"].endswith("Z") and data["license"] == "CC BY 4.0"
    demo = demo_source(src).to_dict()
    assert demo["id"] == "synthetic-demo" and "X data" in demo["name"]


# --------------------------------------------------------------------------- open-meteo


def test_open_meteo_normals_and_elevation(recorder):
    def handler(request: httpx.Request) -> httpx.Response:
        if "elevation" in request.url.path:
            return json_response({"elevation": [880.0]})
        assert request.url.params["daily"] == "temperature_2m_mean,precipitation_sum"
        assert request.url.params["start_date"] == "2020-01-01"
        days = 365 * 2
        return json_response(
            {
                "daily": {
                    "temperature_2m_mean": [24.0] * days + [None],
                    "precipitation_sum": [820.0 / 365] * days,
                }
            }
        )

    adapter = OpenMeteoAdapter(
        "https://archive.test/v1/archive",
        "https://api.test/v1/elevation",
        client=make_client(handler, recorder),
        start_year=2020,
        end_year=2021,
    )
    normals = adapter.fetch_climate_normals(13.29, 77.54)
    assert normals.mean_annual_temp_c == pytest.approx(24.0)
    assert normals.annual_precip_mm == pytest.approx(820.0, rel=1e-6)
    assert normals.elevation_m == 880.0
    assert normals.to_dict()["period"] == "2020-2021"
    assert normals.source["id"] == "open-meteo" and normals.source["license"] == "CC BY 4.0"


def test_open_meteo_malformed_payload():
    adapter = OpenMeteoAdapter(
        "https://a.test", "https://e.test", client=make_client(lambda r: json_response({"x": 1}))
    )
    with pytest.raises(UpstreamDataError):
        adapter.fetch_climate_normals(1, 1, with_elevation=False)


def test_demo_open_meteo_is_deterministic_and_regional():
    demo = DemoOpenMeteoAdapter()
    a = demo.fetch_climate_normals(13.29, 77.54)
    b = demo.fetch_climate_normals(13.29, 77.54)
    # identical values; only the access timestamp in the provenance may differ
    assert (a.mean_annual_temp_c, a.annual_precip_mm, a.elevation_m) == (
        b.mean_annual_temp_c,
        b.annual_precip_mm,
        b.elevation_m,
    )
    assert 23.5 < a.mean_annual_temp_c < 24.7 and 780 < a.annual_precip_mm < 860
    us = demo.fetch_climate_normals(32.6, -83.6)
    assert 17.0 < us.mean_annual_temp_c < 18.0 and us.annual_precip_mm > 1200
    assert a.source["id"] == "synthetic-demo"
    assert demo.fetch_climate_normals(-33.9, 151.2).mean_annual_temp_c < 20  # formula fallback


# --------------------------------------------------------------------------- soilgrids


def test_soilgrids_weighted_mean(recorder):
    payload = {
        "properties": {
            "layers": [
                {
                    "name": "soc",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 150}},
                        {"label": "5-15cm", "values": {"mean": 100}},
                        {"label": "15-30cm", "values": {"mean": 70}},
                    ],
                }
            ]
        }
    }
    adapter = SoilGridsAdapter(
        "https://rest.test/query", client=make_client(lambda r: json_response(payload), recorder)
    )
    result = adapter.fetch_soc_0_30(13.29, 77.54)
    expected = (150 * 5 + 100 * 10 + 70 * 15) / 30 / 10
    assert result.soc_0_30cm_g_per_kg == pytest.approx(expected)
    assert recorder.last.url.params.get_list("depth") == ["0-5cm", "5-15cm", "15-30cm"]
    assert recorder.last.url.params["property"] == "soc"
    assert result.to_dict() == {"soc_0_30cm_g_per_kg": round(expected, 2)}


def test_soilgrids_missing_depth_and_demo():
    payload = {
        "properties": {
            "layers": [{"name": "soc", "depths": [{"label": "0-5cm", "values": {"mean": None}}]}]
        }
    }
    adapter = SoilGridsAdapter(
        "https://rest.test/query", client=make_client(lambda r: json_response(payload))
    )
    assert adapter.fetch_soc_0_30(1, 1).soc_0_30cm_g_per_kg is None
    demo = DemoSoilGridsAdapter().fetch_soc_0_30(13.29, 77.54)
    assert 7 < demo.soc_0_30cm_g_per_kg < 12 and demo.source["id"] == "synthetic-demo"


# --------------------------------------------------------------------------- usda nass


def test_usda_nass_query_and_parsing(recorder):
    payload = {
        "data": [
            {
                "year": "2023",
                "commodity_desc": "PECANS",
                "statisticcat_desc": "PRODUCTION",
                "Value": "1,234,567",
                "unit_desc": "LB",
                "state_name": "GEORGIA",
                "county_name": "BIBB",
            },
            {
                "year": "2022",
                "commodity_desc": "PECANS",
                "statisticcat_desc": "PRODUCTION",
                "Value": "(D)",
                "unit_desc": "LB",
                "state_name": "GEORGIA",
                "county_name": "BIBB",
            },
        ]
    }
    adapter = UsdaNassAdapter(
        "https://nass.test/api_GET/",
        "KEY",
        client=make_client(lambda r: json_response(payload), recorder),
    )
    records = adapter.fetch_county_statistics("13", "21", "pecans", [2022, 2023])
    assert [r.year for r in records] == [2022, 2023]
    assert records[0].value is None and records[1].value == 1234567.0
    params = recorder.last.url.params
    assert (
        params["key"] == "KEY"
        and params["county_code"] == "021"
        and params["state_fips_code"] == "13"
    )
    assert params["commodity_desc"] == "PECANS" and params["year__GE"] == "2022"
    with pytest.raises(ConfigurationError):
        UsdaNassAdapter("https://nass.test", "")
    demo = DemoUsdaNassAdapter().fetch_county_statistics("13", "021", "PECANS", [2021, 2022])
    assert len(demo) == 2 and demo[0].unit == "LB"


# --------------------------------------------------------------------------- census


def test_census_geocoder_lookup(recorder):
    payload = {
        "result": {
            "geographies": {
                "Counties": [
                    {"STATE": "13", "COUNTY": "021", "NAME": "Bibb County", "BASENAME": "Bibb"}
                ],
                "States": [{"NAME": "Georgia", "STUSAB": "GA"}],
            }
        }
    }
    adapter = CensusGeocoderAdapter(
        "https://geo.test/coordinates",
        client=make_client(lambda r: json_response(payload), recorder),
    )
    result = adapter.lookup(32.6, -83.6)
    assert result.to_dict() == {
        "state_fips": "13",
        "county_fips": "021",
        "state_name": "Georgia",
        "state_abbr": "GA",
        "county_name": "Bibb County",
    }
    assert (
        recorder.last.url.params["x"] == "-83.6"
        and recorder.last.url.params["benchmark"] == "Public_AR_Current"
    )
    empty = CensusGeocoderAdapter(
        "https://geo.test",
        client=make_client(lambda r: json_response({"result": {"geographies": {}}})),
    )
    with pytest.raises(NotFoundError):
        empty.lookup(0, 0)
    assert DemoCensusGeocoderAdapter().lookup(32.6, -83.6).state_fips == "13"
    with pytest.raises(NotFoundError):
        DemoCensusGeocoderAdapter().lookup(13.29, 77.54)


# --------------------------------------------------------------------------- data.gov.in


def test_data_gov_in_filters_and_records(recorder):
    payload = {
        "total": 2,
        "records": [{"crop": "Mango", "production_": 100}, {"crop": "Mango", "production_": 120}],
    }
    adapter = DataGovInAdapter(
        "https://api.test/resource",
        "KEY",
        crop_resource_id="abc",
        client=make_client(lambda r: json_response(payload), recorder),
    )
    result = adapter.fetch_crop_production("Karnataka", "Bengaluru Rural", "Mango")
    assert result.total == 2 and len(result.records) == 2
    assert recorder.last.url.path.endswith("/resource/abc")
    params = recorder.last.url.params
    assert params["api-key"] == "KEY" and params["filters[state_name]"] == "Karnataka"
    assert (
        params["filters[district_name]"] == "Bengaluru Rural" and params["filters[crop]"] == "Mango"
    )
    with pytest.raises(ConfigurationError):
        DataGovInAdapter("https://api.test", "")
    no_resource = DataGovInAdapter(
        "https://api.test", "KEY", client=make_client(lambda r: json_response(payload))
    )
    with pytest.raises(ConfigurationError):
        no_resource.fetch_crop_production("Karnataka")
    demo = DemoDataGovInAdapter().fetch_crop_production("Karnataka", "Bengaluru Rural", "Mango")
    assert len(demo.records) == 5 and demo.source["id"] == "synthetic-demo"
