"""Imagery provider endpoint: GET /imagery/providers (demo mode, no network)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import ProblemError
from app.main import create_app
from app.services.imagery import ImageryService
from app.services.registry import service

API = "/api/v1"
ROOT = Path(__file__).resolve().parents[3]
FILE = yaml.safe_load((ROOT / "config" / "imagery" / "providers.yaml").read_text(encoding="utf-8"))
CONTRACT_FIELDS = {
    "id",
    "name",
    "kind",
    "url",
    "tile_size",
    "max_zoom",
    "coverage",
    "resolution",
    "license",
    "license_url",
    "attribution",
    "requires_key",
    "available",
    "unavailable_reason",
    "commercial_use",
    "analysis_allowed",
    "open_data",
    "verification_status",
}
SECRET = "test-esri-key-0123456789"


@contextmanager
def make_client(**settings) -> Iterator[TestClient]:
    base = {
        "ATLAS_MODE": "demo",
        "ATLAS_RATE_LIMIT_ENABLED": False,
        "ATLAS_API_KEYS": "",
        "ESRI_API_KEY": "",
    }
    app = create_app(Settings(**{**base, **settings}))  # type: ignore[arg-type]
    with TestClient(app) as test_client:
        yield test_client


def providers(client, country=None):
    params = {"country": country} if country else {}
    response = client.get(f"{API}/imagery/providers", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def by_id(body):
    return {p["id"]: p for p in body["providers"]}


@pytest.fixture(scope="module")
def keyless() -> Iterator[TestClient]:
    with make_client() as test_client:
        yield test_client


# ------------------------------------------------------------------------- the contract
def test_every_provider_has_the_contract_fields(keyless):
    body = providers(keyless, "IN")
    assert set(body) >= {"recommended", "providers", "notes"}
    assert isinstance(body["notes"], str) and "analysis" in body["notes"]
    assert {p["id"] for p in body["providers"]} == {p["id"] for p in FILE["providers"]}
    for provider in body["providers"]:
        assert CONTRACT_FIELDS <= set(provider), provider["id"]
        assert provider["license"].strip() and provider["attribution"].strip()
        assert provider["license_url"].startswith("https://")
        assert provider["kind"] == "xyz" and provider["tile_size"] == 256
        assert isinstance(provider["available"], bool)
        assert isinstance(provider["max_zoom"], int) and provider["max_zoom"] > 0
        assert provider["coverage"]["type"] in {"global", "countries"}


def test_provider_values_are_passed_through_from_the_file(keyless):
    served = by_id(providers(keyless))
    for entry in FILE["providers"]:
        provider = served[entry["id"]]
        for field in ("name", "license", "attribution", "commercial_use", "analysis_allowed"):
            assert provider[field] == entry[field], (entry["id"], field)
        assert provider["coverage"] == entry["coverage"]
        assert provider["verification_status"] == entry["verification_status"]


def test_display_only_and_non_open_providers_are_marked_for_the_user(keyless):
    served = by_id(providers(keyless))
    esri = served["esri-world-imagery"]
    assert esri["analysis_allowed"] is False and esri["requires_key"] is True
    assert esri["open_data"] is False
    newest = served["eox-s2cloudless-2025"]
    assert newest["commercial_use"] == "not-allowed" and newest["open_data"] is False
    assert newest["analysis_allowed"] == "review-terms"
    for provider_id in ("eox-s2cloudless-2016", "usgs-imagery-only", "ign-france-orthophotos"):
        assert served[provider_id]["analysis_allowed"] is True
        assert served[provider_id]["open_data"] is True


# ------------------------------------------------------------------------------ recommendation
@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("IN", "eox-s2cloudless-2016"),
        ("US", "usgs-imagery-only"),
        ("FR", "ign-france-orthophotos"),
        ("ES", "ign-spain-pnoa"),
        ("NL", "pdok-luchtfoto"),
        ("DE", "eox-s2cloudless-2016"),  # no national entry → the file's default
        ("ZZ", "eox-s2cloudless-2016"),
        (None, "eox-s2cloudless-2016"),
    ],
)
def test_recommended_follows_default_by_country(keyless, country, expected):
    assert providers(keyless, country)["recommended"] == expected
    defaults = FILE["default_by_country"]
    assert expected == (defaults.get(country) or defaults["default"])  # the file is the source


def test_recommended_is_always_available_and_listed(keyless):
    for country in (None, "IN", "US", "FR", "ES", "NL", "DE", "ZZ"):
        body = providers(keyless, country)
        recommended = by_id(body)[body["recommended"]]
        assert recommended["available"] is True and recommended["unavailable_reason"] is None


def test_country_is_case_insensitive_and_validated(keyless):
    assert providers(keyless, "us")["recommended"] == "usgs-imagery-only"
    assert providers(keyless, "us")["country"] == "US"
    for bad in ("INDIA", "I", "1"):
        response = keyless.get(f"{API}/imagery/providers", params={"country": bad})
        assert response.status_code == 422, bad
        assert response.json()["type"].endswith("validation-error")


# ----------------------------------------------------------------------------------- ordering
def test_providers_covering_the_country_are_listed_first(keyless):
    for country in ("IN", "US", "FR", "ES", "NL", "DE"):
        body = providers(keyless, country)
        flags = [p["covers_country"] for p in body["providers"]]
        assert flags == sorted(flags, reverse=True), country  # all True before any False
        covering = {p["id"] for p in body["providers"] if p["covers_country"]}
        for entry in FILE["providers"]:
            coverage = entry["coverage"]
            expected = coverage["type"] == "global" or country in coverage.get("countries", [])
            assert (entry["id"] in covering) == expected, (country, entry["id"])


def test_country_providers_cover_only_their_country(keyless):
    assert by_id(providers(keyless, "FR"))["ign-france-orthophotos"]["covers_country"] is True
    assert by_id(providers(keyless, "FR"))["usgs-imagery-only"]["covers_country"] is False
    assert by_id(providers(keyless, "US"))["usgs-imagery-only"]["covers_country"] is True
    india = by_id(providers(keyless, "IN"))
    assert india["usgs-imagery-only"]["covers_country"] is False
    assert india["eox-s2cloudless-2016"]["covers_country"] is True


def test_without_a_country_the_file_order_is_kept(keyless):
    body = providers(keyless)
    assert [p["id"] for p in body["providers"]] == [p["id"] for p in FILE["providers"]]
    assert all(p["covers_country"] is None for p in body["providers"])


def test_the_eu_region_covers_providers_of_its_member_states(keyless):
    served = by_id(providers(keyless, "EU"))
    for provider_id in ("ign-france-orthophotos", "ign-spain-pnoa", "pdok-luchtfoto"):
        assert served[provider_id]["covers_country"] is True
    assert served["usgs-imagery-only"]["covers_country"] is False


# ------------------------------------------------------------------------------------ the key
def test_missing_key_means_unavailable_without_a_url(keyless):
    for country in (None, "IN", "US", "FR"):
        body = providers(keyless, country)
        esri = by_id(body)["esri-world-imagery"]
        assert esri["available"] is False
        assert esri["unavailable_reason"] == "Set ESRI_API_KEY to enable"
        assert esri["url"] is None
        assert body["recommended"] != "esri-world-imagery"


def test_no_response_ever_contains_an_unsubstituted_placeholder(keyless):
    for country in (None, "IN", "US", "FR", "ES", "NL", "DE", "EU", "ZZ"):
        text = keyless.get(
            f"{API}/imagery/providers", params={"country": country} if country else {}
        )
        assert "${" not in text.text, country
    with make_client(ESRI_API_KEY=SECRET) as keyed:
        assert "${" not in keyed.get(f"{API}/imagery/providers").text


def test_available_providers_have_complete_tile_urls(keyless):
    for provider in providers(keyless, "US")["providers"]:
        if provider["available"]:
            assert provider["url"].startswith("https://")
            assert provider["unavailable_reason"] is None
            for placeholder in ("{z}", "{x}", "{y}"):
                assert placeholder in provider["url"], provider["id"]


def test_a_key_in_settings_enables_esri_and_is_substituted():
    with make_client(ESRI_API_KEY=SECRET) as keyed:
        body = providers(keyed, "IN")
        esri = by_id(body)["esri-world-imagery"]
        assert esri["available"] is True and esri["unavailable_reason"] is None
        assert esri["url"].endswith(f"?token={SECRET}")
        assert "{z}/{y}/{x}" in esri["url"]  # tile placeholders stay for MapLibre
        assert body["recommended"] == "eox-s2cloudless-2016"  # a key does not change the default


def test_the_key_is_url_encoded():
    with make_client(ESRI_API_KEY="a b&c=d") as keyed:
        url = by_id(providers(keyed))["esri-world-imagery"]["url"]
    assert url.endswith("?token=a%20b%26c%3Dd")


def test_the_key_never_reaches_the_logs():
    records: list[str] = []

    class Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(f"{record.getMessage()} {record.__dict__}")

    handler = Collect(level=logging.DEBUG)
    root = logging.getLogger()
    with make_client(ESRI_API_KEY=SECRET, ATLAS_LOG_LEVEL="debug") as keyed:
        root.addHandler(handler)
        previous = root.level
        root.setLevel(logging.DEBUG)
        try:
            providers(keyed, "IN")
            providers(keyed)
        finally:
            root.removeHandler(handler)
            root.setLevel(previous)
    assert records, "the request was expected to be logged"
    assert not any(SECRET in line for line in records)


def test_the_service_is_cached_in_the_context(keyless):
    context = keyless.app.state.context
    first = service(context, "imagery", lambda: ImageryService(context))
    assert service(context, "imagery", lambda: ImageryService(context)) is first


def test_openapi_lists_the_endpoint(keyless):
    spec = keyless.get(f"{API}/openapi.json").json()
    operation = spec["paths"][f"{API}/imagery/providers"]["get"]
    assert operation["tags"] == ["imagery"]


# -------------------------------------------------------- substitution rules (unit, fake config)
def fake_provider(provider_id, url, *, requires_key, coverage=None, open_data=False):
    return {
        "id": provider_id,
        "name": provider_id,
        "kind": "xyz",
        "tile_size": 256,
        "max_zoom": 10,
        "coverage": coverage or {"type": "global"},
        "resolution": "10 m",
        "license": "CC BY 4.0",
        "license_url": "https://example.org/license",
        "attribution": provider_id,
        "requires_key": requires_key,
        "commercial_use": "allowed",
        "analysis_allowed": True,
        "open_data": open_data,
        "verification_status": "verified",
        "url": url,
    }


PROVIDERS_YAML = yaml.safe_dump(
    {
        "version": "9.9.9",
        "updated": "2026-10-05",
        "notes": "Test notes.",
        "default_by_country": {"default": "keyed-global", "XX": "keyed-local"},
        "providers": [
            fake_provider(
                "keyed-global",
                "https://tiles.example.org/{z}/{x}/{y}?key=${MAPTILER_KEY}",
                requires_key=True,
            ),
            fake_provider(
                "keyed-local",
                "https://local.example.org/{z}/{x}/{y}?key=${LOCAL_TILES_TOKEN}",
                requires_key=True,
                coverage={"type": "countries", "countries": ["XX"]},
            ),
            fake_provider(
                "open",
                "https://open.example.org/{z}/{x}/{y}.jpg",
                requires_key=False,
                open_data=True,
            ),
            fake_provider(
                "leaky",
                "https://leak.example.org/{z}/{x}/{y}?k=${LLM_API_KEY}&m=${lower_case}",
                requires_key=True,
            ),
        ],
    }
)


def build_service(tmp_path: Path, text: str = PROVIDERS_YAML, **settings) -> ImageryService:
    (tmp_path / "imagery").mkdir(exist_ok=True)
    (tmp_path / "imagery" / "providers.yaml").write_text(text, encoding="utf-8")
    base = {"ATLAS_CONFIG_DIR": str(tmp_path), "ESRI_API_KEY": ""}
    ctx = SimpleNamespace(
        settings=Settings(**{**base, **settings}),  # type: ignore[arg-type]
        regions=SimpleNamespace(regions={}),
    )
    return ImageryService(ctx)  # type: ignore[arg-type]


def test_other_key_variables_come_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("MAPTILER_KEY", raising=False)
    monkeypatch.delenv("LOCAL_TILES_TOKEN", raising=False)
    imagery = build_service(tmp_path)
    missing = by_id(imagery.providers("XX"))
    assert missing["keyed-global"]["available"] is False
    assert missing["keyed-global"]["unavailable_reason"] == "Set MAPTILER_KEY to enable"
    assert missing["keyed-global"]["url"] is None

    monkeypatch.setenv("MAPTILER_KEY", "mt-123")
    monkeypatch.setenv("LOCAL_TILES_TOKEN", "lt-456")
    served = by_id(imagery.providers("XX"))
    assert served["keyed-global"]["url"] == "https://tiles.example.org/{z}/{x}/{y}?key=mt-123"
    assert served["keyed-local"]["url"] == "https://local.example.org/{z}/{x}/{y}?key=lt-456"
    assert served["open"]["url"] == "https://open.example.org/{z}/{x}/{y}.jpg"


def test_variables_the_app_uses_elsewhere_are_never_substituted(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "super-secret-llm-key")
    monkeypatch.setenv("lower_case", "nope")
    body = build_service(tmp_path).providers()
    leaky = by_id(body)["leaky"]
    assert leaky["available"] is False and leaky["url"] is None
    assert "LLM_API_KEY" in leaky["unavailable_reason"]
    assert "super-secret-llm-key" not in str(body) and "nope" not in str(body)


def test_recommended_falls_back_to_the_first_available_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("MAPTILER_KEY", raising=False)
    monkeypatch.delenv("LOCAL_TILES_TOKEN", raising=False)
    imagery = build_service(tmp_path)
    # keyed-local is XX's default but its key is missing → first available that covers XX
    assert imagery.providers("XX")["recommended"] == "open"
    assert imagery.providers()["recommended"] == "open"  # keyed-global is the default, unavailable
    monkeypatch.setenv("MAPTILER_KEY", "mt-123")
    assert imagery.providers()["recommended"] == "keyed-global"
    monkeypatch.setenv("LOCAL_TILES_TOKEN", "lt-456")
    assert imagery.providers("XX")["recommended"] == "keyed-local"


def test_a_missing_or_broken_file_is_a_clean_server_error(tmp_path):
    ctx = SimpleNamespace(settings=Settings(ATLAS_CONFIG_DIR=str(tmp_path)), regions=None)  # type: ignore[call-arg]
    with pytest.raises(ProblemError) as excinfo:
        ImageryService(ctx)  # type: ignore[arg-type]
    assert excinfo.value.status == 500
    assert str(tmp_path) not in excinfo.value.detail  # no server paths in the response

    with pytest.raises(ProblemError):
        build_service(tmp_path, "providers: not-a-list\n")
