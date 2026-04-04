from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"
DEFAULT_DATABASE_PATH = BACKEND_ROOT / "method_aware.db"
DEFAULT_STORAGE_PATH = BACKEND_ROOT / "app" / "storage"


def _sqlite_url_for_path(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


DEFAULT_DATABASE_URL = _sqlite_url_for_path(DEFAULT_DATABASE_PATH)
DB_INIT_MODES = {"migrate", "create_all", "none"}


def _normalize_sqlite_url(value: str) -> str:
    raw = str(value).strip()
    prefix = "sqlite:///"
    if not raw.startswith(prefix):
        return raw

    raw_path = raw[len(prefix):].strip()
    if not raw_path or raw_path == ".":
        return DEFAULT_DATABASE_URL
    if raw_path == ":memory:" or raw_path.startswith("file:"):
        return raw

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = BACKEND_ROOT / candidate
    return _sqlite_url_for_path(candidate)


def _normalize_storage_path(value: str | Path) -> str:
    raw = str(value).strip()
    candidate = DEFAULT_STORAGE_PATH if not raw else Path(raw)
    if not candidate.is_absolute():
        candidate = BACKEND_ROOT / candidate
    return str(candidate.resolve())


class Settings(BaseSettings):
    app_name: str = "Method-Aware Framework"
    api_prefix: str = "/api/v1"
    db_init_mode: Literal["migrate", "create_all", "none"] = Field(default="migrate", alias="DB_INIT_MODE")
    database_url: str = Field(default=DEFAULT_DATABASE_URL, alias="DATABASE_URL")
    storage_dir: str = Field(default=str(DEFAULT_STORAGE_PATH.resolve()), alias="STORAGE_DIR")
    max_upload_mb: int = Field(default=64, alias="MAX_UPLOAD_MB")
    sciencebase_api_base_url: str = Field(default="https://www.sciencebase.gov/catalog", alias="SCIENCEBASE_API_BASE_URL")
    nrc_adams_api_base_url: str = Field(default="https://adams-api.nrc.gov", alias="NRC_ADAMS_APS_API_BASE_URL")
    nrc_adams_subscription_key: str = Field(default="", alias="NRC_ADAMS_APS_SUBSCRIPTION_KEY")
    senate_lda_api_base_url: str = Field(default="https://lda.senate.gov/api/v1", alias="SENATE_LDA_API_BASE_URL")
    senate_lda_api_key: str = Field(default="", alias="SENATE_LDA_API_KEY")
    connector_lease_ttl_seconds: int = Field(default=120, alias="CONNECTOR_LEASE_TTL_SECONDS")
    connector_submission_ttl_hours: int = Field(default=24, alias="CONNECTOR_SUBMISSION_TTL_HOURS")
    connector_max_redirects: int = Field(default=3, alias="CONNECTOR_MAX_REDIRECTS")
    connector_max_concurrent_runs: int = Field(default=2, alias="CONNECTOR_MAX_CONCURRENT_RUNS")
    connector_max_downloads_per_run: int = Field(default=1, alias="CONNECTOR_MAX_DOWNLOADS_PER_RUN")
    connector_per_host_fetch_limit: int = Field(default=2, alias="CONNECTOR_PER_HOST_FETCH_LIMIT")

    model_config = SettingsConfigDict(env_file=str(BACKEND_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    @field_validator("db_init_mode", mode="before")
    @classmethod
    def _normalize_db_init_mode(cls, value: object) -> str:
        normalized = "migrate" if value is None else str(value).strip().lower()
        if normalized not in DB_INIT_MODES:
            allowed = ", ".join(sorted(DB_INIT_MODES))
            raise ValueError(f"DB_INIT_MODE must be one of: {allowed}")
        return normalized

    def model_post_init(self, __context: object) -> None:
        if self.database_url.startswith("sqlite"):
            self.database_url = _normalize_sqlite_url(self.database_url)
        self.storage_dir = _normalize_storage_path(self.storage_dir)

    @property
    def raw_storage_dir(self) -> str:
        return str(Path(self.storage_dir) / "raw")

    @property
    def artifact_storage_dir(self) -> str:
        return str(Path(self.storage_dir) / "artifacts")

    @property
    def dataset_storage_dir(self) -> str:
        return str(Path(self.storage_dir) / "datasets")

    @property
    def connector_storage_dir(self) -> str:
        return str(Path(self.storage_dir) / "connectors")

    @property
    def connector_reports_dir(self) -> str:
        return str(Path(self.connector_storage_dir) / "reports")

    @property
    def connector_manifests_dir(self) -> str:
        return str(Path(self.connector_storage_dir) / "manifests")

    @property
    def connector_snapshots_dir(self) -> str:
        return str(Path(self.connector_storage_dir) / "snapshots")

    @property
    def connector_raw_dir(self) -> str:
        return str(Path(self.connector_storage_dir) / "raw")


settings = Settings()


def bootstrap_storage_tree(storage_dir: str | Path | None = None) -> None:
    root = Path(settings.storage_dir if storage_dir is None else _normalize_storage_path(storage_dir))
    paths = (
        root,
        root / "raw",
        root / "artifacts",
        root / "datasets",
        root / "connectors",
        root / "connectors" / "reports",
        root / "connectors" / "manifests",
        root / "connectors" / "snapshots",
        root / "connectors" / "raw",
    )
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
