"""Runtime settings — every external endpoint and limit comes from the environment.

See ``.env.example`` at the repository root for the documented list.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config" / "species" / "species.yaml").is_file():
            return parent
    return here.parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # runtime
    atlas_env: str = Field("development", alias="ATLAS_ENV")
    atlas_mode: str = Field("demo", alias="ATLAS_MODE")  # demo | live
    atlas_log_level: str = Field("info", alias="ATLAS_LOG_LEVEL")
    atlas_api_host: str = Field("0.0.0.0", alias="ATLAS_API_HOST")
    atlas_api_port: int = Field(8000, alias="ATLAS_API_PORT")
    atlas_cors_origins: str = Field(
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,http://localhost:8080",
        alias="ATLAS_CORS_ORIGINS",
    )
    atlas_api_keys: str = Field("", alias="ATLAS_API_KEYS")
    atlas_rate_limit: str = Field("60/minute", alias="ATLAS_RATE_LIMIT")
    atlas_rate_limit_enabled: bool = Field(True, alias="ATLAS_RATE_LIMIT_ENABLED")
    atlas_max_plot_vertices: int = Field(500, alias="ATLAS_MAX_PLOT_VERTICES")
    atlas_max_plot_area_ha: float = Field(10_000.0, alias="ATLAS_MAX_PLOT_AREA_HA")
    atlas_max_body_bytes: int = Field(1_000_000, alias="ATLAS_MAX_BODY_BYTES")
    atlas_allow_pending_parameters: bool = Field(True, alias="ATLAS_ALLOW_PENDING_PARAMETERS")
    atlas_cache_dir: str = Field(".cache", alias="ATLAS_CACHE_DIR")
    atlas_reports_dir: str = Field(".reports", alias="ATLAS_REPORTS_DIR")
    atlas_config_dir: str | None = Field(None, alias="ATLAS_CONFIG_DIR")
    atlas_seed_demo: bool = Field(True, alias="ATLAS_SEED_DEMO")

    # storage
    atlas_repository: str = Field("memory", alias="ATLAS_REPOSITORY")  # memory | postgres
    database_url: str = Field("postgresql://atlas:atlas@localhost:5432/atlas", alias="DATABASE_URL")

    # earth observation
    atlas_stac_provider: str = Field("earth-search", alias="ATLAS_STAC_PROVIDER")
    earth_search_stac_url: str = Field(
        "https://earth-search.aws.element84.com/v1", alias="EARTH_SEARCH_STAC_URL"
    )
    copernicus_stac_url: str = Field(
        "https://stac.dataspace.copernicus.eu/v1", alias="COPERNICUS_STAC_URL"
    )
    copernicus_token: str = Field("", alias="COPERNICUS_TOKEN")
    esa_worldcover_base_url: str = Field(
        "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map",
        alias="ESA_WORLDCOVER_BASE_URL",
    )
    esa_worldcover_version: str = Field("v200", alias="ESA_WORLDCOVER_VERSION")
    open_meteo_archive_url: str = Field(
        "https://archive-api.open-meteo.com/v1/archive", alias="OPEN_METEO_ARCHIVE_URL"
    )
    open_meteo_elevation_url: str = Field(
        "https://api.open-meteo.com/v1/elevation", alias="OPEN_METEO_ELEVATION_URL"
    )
    soilgrids_url: str = Field(
        "https://rest.isric.org/soilgrids/v2.0/properties/query", alias="SOILGRIDS_URL"
    )
    max_cloud_cover_pct: float = Field(20.0, alias="MAX_CLOUD_COVER_PCT")

    # geocoding
    atlas_geocoder: str = Field("nominatim", alias="ATLAS_GEOCODER")  # nominatim | photon
    nominatim_url: str = Field("https://nominatim.openstreetmap.org", alias="NOMINATIM_URL")
    nominatim_user_agent: str = Field("", alias="NOMINATIM_USER_AGENT")
    photon_url: str = Field("https://photon.komoot.io", alias="PHOTON_URL")
    geocoder_min_interval_seconds: float = Field(1.0, alias="GEOCODER_MIN_INTERVAL_SECONDS")

    # regional statistics
    usda_nass_api_url: str = Field(
        "https://quickstats.nass.usda.gov/api/api_GET/", alias="USDA_NASS_API_URL"
    )
    usda_nass_api_key: str = Field("", alias="USDA_NASS_API_KEY")
    census_geocoder_url: str = Field(
        "https://geocoding.geo.census.gov/geocoder/geographies/coordinates",
        alias="CENSUS_GEOCODER_URL",
    )
    data_gov_in_api_url: str = Field(
        "https://api.data.gov.in/resource", alias="DATA_GOV_IN_API_URL"
    )
    data_gov_in_api_key: str = Field("", alias="DATA_GOV_IN_API_KEY")
    data_gov_in_crop_resource_id: str = Field(
        "35be999b-0208-4354-b557-f6ca9a5355de", alias="DATA_GOV_IN_CROP_RESOURCE_ID"
    )

    # explanation
    atlas_explain_provider: str = Field("template", alias="ATLAS_EXPLAIN_PROVIDER")

    # imports (GeoJSON / KML / CSV / point clouds)
    atlas_max_upload_mb: int = Field(50, alias="ATLAS_MAX_UPLOAD_MB")

    # map imagery (display). Keys are substituted into provider URLs at run time.
    esri_api_key: str = Field("", alias="ESRI_API_KEY")

    # agentic framework: deterministic templates by default; an LLM is optional and
    # only rewrites narration from redacted facts (never numbers, never coordinates).
    atlas_agent_reasoner: str = Field("template", alias="ATLAS_AGENT_REASONER")  # template | llm
    llm_api_base_url: str = Field("", alias="LLM_API_BASE_URL")  # OpenAI-compatible endpoint
    llm_api_key: str = Field("", alias="LLM_API_KEY")
    llm_model: str = Field("", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(20.0, alias="LLM_TIMEOUT_SECONDS")

    @field_validator("atlas_mode")
    @classmethod
    def _mode(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {"demo", "live"}:
            raise ValueError("ATLAS_MODE must be 'demo' or 'live'")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.atlas_cors_origins.split(",") if o.strip()]

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.atlas_api_keys.split(",") if k.strip()}

    @property
    def max_upload_bytes(self) -> int:
        return max(1, self.atlas_max_upload_mb) * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        return (
            self.atlas_agent_reasoner.lower() == "llm"
            and bool(self.llm_api_base_url)
            and bool(self.llm_model)
        )

    @property
    def is_demo(self) -> bool:
        return self.atlas_mode == "demo"

    @property
    def is_production(self) -> bool:
        return self.atlas_env.lower() == "production"

    @property
    def repo_root(self) -> Path:
        return _repo_root()

    @property
    def config_dir(self) -> Path:
        if self.atlas_config_dir:
            return Path(self.atlas_config_dir)
        return self.repo_root / "config"

    @property
    def sample_dir(self) -> Path:
        return self.repo_root / "data" / "sample"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
