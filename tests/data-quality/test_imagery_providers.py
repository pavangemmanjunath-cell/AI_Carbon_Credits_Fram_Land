"""Data-quality gates on ``config/imagery/providers.yaml``.

Imagery is licensed content: a provider with a missing licence, an empty attribution or a key
written into its URL must never ship (CLAUDE.md principles 5 and 6). These tests also keep the
"display only" promise honest: imagery whose terms bar automated analysis (Esri World Imagery) can
never be marked ``analysis_allowed: true``, and no provider reaches production while its terms are
still ``pending``.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
PROVIDERS_PATH = CONFIG / "imagery" / "providers.yaml"
RAW = yaml.safe_load(PROVIDERS_PATH.read_text(encoding="utf-8"))
PROVIDERS = RAW["providers"]
PROVIDER_IDS = [provider["id"] for provider in PROVIDERS]
BY_ID = {provider["id"]: provider for provider in PROVIDERS}
DEFAULTS = RAW["default_by_country"]

REQUIRED_FIELDS = {
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
    "commercial_use",
    "analysis_allowed",
    "open_data",
    "verification_status",
    "sources",
    "notes",
}
KINDS = {"xyz"}
COMMERCIAL_USE = {"allowed", "not-allowed", "review-terms"}
ANALYSIS_ALLOWED = {True, False, "review-terms"}
VERIFICATION_STATUSES = {"verified", "pending"}
COVERAGE_TYPES = {"global", "countries"}
PLACEHOLDER = re.compile(r"\$\{([^}]*)\}")
KEY_NAME = re.compile(r"^[A-Z][A-Z0-9_]*_(?:KEY|TOKEN)$")
SECRET_PARAMETERS = {
    "key",
    "apikey",
    "api_key",
    "token",
    "access_token",
    "authkey",
    "sig",
    "signature",
}
ESRI = "esri-world-imagery"


def region_countries() -> list[str]:
    """Every country the MVP supports: IN, US and the EU member states."""
    countries = ["IN", "US"]
    eu = yaml.safe_load((CONFIG / "regions" / "EU.yaml").read_text(encoding="utf-8"))
    return countries + [str(code) for code in eu["member_states"]]


def as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def covers(provider: dict, country: str) -> bool:
    coverage = provider["coverage"]
    return coverage["type"] == "global" or country in coverage.get("countries", [])


@pytest.fixture(params=PROVIDERS, ids=PROVIDER_IDS)
def provider(request):
    return request.param


# ---------------------------------------------------------------------------- whole file
def test_file_header_is_complete():
    assert str(RAW["version"]).strip()
    assert as_date(RAW["updated"]) <= date.today()
    assert str(RAW["notes"]).strip()
    assert len(PROVIDERS) >= 5


def test_provider_ids_are_unique_slugs():
    assert len(PROVIDER_IDS) == len(set(PROVIDER_IDS))
    assert all(
        re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", provider_id) for provider_id in PROVIDER_IDS
    )


def test_no_http_links_and_no_literal_key_anywhere_in_the_file():
    text = PROVIDERS_PATH.read_text(encoding="utf-8")
    assert "http://" not in text
    # a key is only ever a ${NAME} placeholder substituted at run time (principle 6)
    for url in re.findall(r'url: "([^"]+)"', text):
        for name, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
            if name.lower() in SECRET_PARAMETERS:
                assert PLACEHOLDER.fullmatch(value), f"literal secret in {name}= of {url[:60]}"


# ------------------------------------------------------------------------------ per provider
def test_provider_has_every_field_and_no_unknown_ones(provider):
    assert REQUIRED_FIELDS <= set(provider), sorted(REQUIRED_FIELDS - set(provider))
    # the API serves a fixed set of fields, so a misspelt key would silently disappear
    assert set(provider) <= REQUIRED_FIELDS, sorted(set(provider) - REQUIRED_FIELDS)


def test_provider_uses_the_documented_vocabulary(provider):
    assert provider["kind"] in KINDS
    assert provider["commercial_use"] in COMMERCIAL_USE
    assert provider["analysis_allowed"] in ANALYSIS_ALLOWED
    assert provider["verification_status"] in VERIFICATION_STATUSES
    for flag in ("requires_key", "open_data"):
        assert isinstance(provider[flag], bool), flag
    # ``1 == True`` in Python, so check the type as well as the value
    analysis = provider["analysis_allowed"]
    assert isinstance(analysis, bool) or analysis == "review-terms"


def test_tile_size_and_zoom_are_sane(provider):
    assert provider["tile_size"] in (256, 512)
    assert isinstance(provider["max_zoom"], int) and 8 <= provider["max_zoom"] <= 23


def test_coverage_is_global_or_a_list_of_iso_countries(provider):
    coverage = provider["coverage"]
    assert coverage["type"] in COVERAGE_TYPES
    if coverage["type"] == "global":
        assert set(coverage) == {"type"}
    else:
        countries = coverage["countries"]
        assert countries and len(countries) == len(set(countries))
        assert all(isinstance(c, str) and re.fullmatch(r"[A-Z]{2}", c) for c in countries)


def test_tile_url_is_https_xyz_and_names_its_key_by_placeholder(provider):
    url = provider["url"]
    assert url.startswith("https://") and " " not in url
    for token in ("{z}", "{x}", "{y}"):
        assert url.count(token) == 1, f"{token} must appear exactly once"
    names = PLACEHOLDER.findall(url)
    assert all(KEY_NAME.match(name) for name in names), names
    assert len(names) == len(set(names))
    # ``requires_key`` is what the web app shows; it must agree with the URL
    assert provider["requires_key"] is bool(names)
    # tile placeholders use single braces; nothing else may be left unresolved at the file level
    leftover = PLACEHOLDER.sub("", url).replace("{z}", "").replace("{x}", "").replace("{y}", "")
    assert "{" not in leftover and "}" not in leftover


def test_licence_and_attribution_are_present(provider):
    for field in ("name", "resolution", "license", "attribution", "notes"):
        assert isinstance(provider[field], str) and provider[field].strip(), field
    assert "${" not in provider["attribution"] and "${" not in provider["license"]
    assert provider["license_url"].startswith("https://") and " " not in provider["license_url"]


def test_sources_are_https_links(provider):
    sources = provider["sources"]
    assert isinstance(sources, list) and sources, "a provider without a source is not allowed"
    assert len(sources) == len(set(sources))
    for link in sources:
        assert isinstance(link, str) and link.startswith("https://") and " " not in link, link


def test_the_licence_url_is_among_the_sources_or_a_standard_licence_page(provider):
    standard = ("https://creativecommons.org/", "https://www.data.gouv.fr/pages/legal/licences/")
    link = provider["license_url"]
    assert link in provider["sources"] or link.startswith(standard), link


def test_what_is_not_confirmed_is_said_in_the_notes(provider):
    if provider["verification_status"] == "pending":
        assert "not confirmed" in provider["notes"].lower(), "say what is still unconfirmed"


# ---------------------------------------------------------------------- licence invariants
def test_open_data_providers_allow_commercial_use_and_analysis(provider):
    if provider["open_data"]:
        assert provider["commercial_use"] == "allowed"
        assert provider["analysis_allowed"] is True


def test_analysis_is_only_allowed_on_openly_licensed_imagery(provider):
    if provider["analysis_allowed"] is True:
        assert provider["open_data"] is True
        assert provider["commercial_use"] == "allowed"
        assert provider["verification_status"] == "verified"


def test_proprietary_or_non_commercial_imagery_is_display_only(provider):
    if provider["requires_key"] or provider["commercial_use"] == "not-allowed":
        assert provider["analysis_allowed"] is not True
        assert provider["open_data"] is False


def test_esri_world_imagery_stays_display_only():
    esri = BY_ID[ESRI]
    assert esri["analysis_allowed"] is False
    assert esri["open_data"] is False
    assert esri["requires_key"] is True
    assert esri["commercial_use"] != "allowed"
    assert "ESRI_API_KEY" in esri["url"]
    assert "Esri" in esri["attribution"]


def test_the_non_commercial_eox_mosaic_is_not_open_data():
    eox = BY_ID["eox-s2cloudless-2025"]
    assert "NC" in eox["license"]
    assert eox["commercial_use"] == "not-allowed" and eox["open_data"] is False
    assert eox["analysis_allowed"] is not True


# ----------------------------------------------------------------------- default_by_country
def test_default_by_country_names_existing_providers():
    assert "default" in DEFAULTS
    for key, provider_id in DEFAULTS.items():
        assert isinstance(key, str), f"{key!r}: quote codes YAML reads as booleans (e.g. NO)"
        assert key == "default" or re.fullmatch(r"[A-Z]{2}", key), key
        assert provider_id in BY_ID, f"{key} -> {provider_id} is not a provider id"


def test_every_default_is_keyless_open_and_covers_its_country():
    """A default is shown to everyone without setup, so it must work for them and be analysable."""
    for key, provider_id in DEFAULTS.items():
        chosen = BY_ID[provider_id]
        assert chosen["requires_key"] is False, key
        assert chosen["open_data"] is True and chosen["analysis_allowed"] is True, key
        assert chosen["verification_status"] == "verified", key
        if key == "default":
            assert chosen["coverage"]["type"] == "global"
        else:
            assert covers(chosen, key), f"{provider_id} does not cover {key}"


@pytest.mark.parametrize("country", region_countries())
def test_every_supported_country_gets_a_covering_recommendation(country):
    provider_id = DEFAULTS.get(country, DEFAULTS["default"])
    assert covers(BY_ID[provider_id], country), f"{provider_id} does not cover {country}"


def test_the_global_default_is_not_the_licensed_esri_service():
    assert DEFAULTS["default"] != ESRI
    assert ESRI not in DEFAULTS.values(), "a licensed, key-bound service is never a default"


def test_every_provider_is_reachable_from_some_country_or_is_global():
    """A country-specific provider that covers nobody we support is dead configuration."""
    supported = set(region_countries())
    for entry in PROVIDERS:
        if entry["coverage"]["type"] == "countries":
            assert set(entry["coverage"]["countries"]) & supported, entry["id"]


# ------------------------------------------------------------------------ production gate
@pytest.mark.skipif(
    os.environ.get("ATLAS_ENV", "").lower() != "production", reason="production gate"
)
def test_production_ships_no_provider_whose_terms_are_unconfirmed():
    """Principle 10: ``pending`` data fails the production-mode data-quality run."""
    pending = [entry["id"] for entry in PROVIDERS if entry["verification_status"] != "verified"]
    assert not pending, f"confirm the licence from the provider's own terms first: {pending}"
