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
DEPLOYMENT_MODES = {"local", "nonlocal"}
AUTH_OWNERS = {"none", "proxy"}
STORAGE_EXPOSURE_MODES = {"auto", "enabled", "disabled", "proxy_protected"}


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


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


class Settings(BaseSettings):
    app_name: str = "Method-Aware Framework"
    api_prefix: str = "/api/v1"
    deployment_mode: Literal["local", "nonlocal"] = Field(default="local", alias="DEPLOYMENT_MODE")
    db_init_mode: Literal["migrate", "create_all", "none"] = Field(default="migrate", alias="DB_INIT_MODE")
    database_url: str = Field(default=DEFAULT_DATABASE_URL, alias="DATABASE_URL")
    storage_dir: str = Field(default=str(DEFAULT_STORAGE_PATH.resolve()), alias="STORAGE_DIR")
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
    cors_allow_credentials: bool | None = Field(default=None, alias="CORS_ALLOW_CREDENTIALS")
    auth_owner: Literal["none", "proxy"] = Field(default="none", alias="AUTH_OWNER")
    proxy_identity_header: str = Field(default="X-Forwarded-User", alias="PROXY_IDENTITY_HEADER")
    proxy_email_header: str = Field(default="X-Forwarded-Email", alias="PROXY_EMAIL_HEADER")
    proxy_groups_header: str = Field(default="X-Forwarded-Groups", alias="PROXY_GROUPS_HEADER")
    trusted_proxy_mode: bool = Field(default=False, alias="TRUSTED_PROXY_MODE")
    storage_exposure: Literal["auto", "enabled", "disabled", "proxy_protected"] = Field(
        default="auto",
        alias="STORAGE_EXPOSURE",
    )
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

    @field_validator("deployment_mode", mode="before")
    @classmethod
    def _normalize_deployment_mode(cls, value: object) -> str:
        normalized = "local" if value is None else str(value).strip().lower()
        if normalized not in DEPLOYMENT_MODES:
            allowed = ", ".join(sorted(DEPLOYMENT_MODES))
            raise ValueError(f"DEPLOYMENT_MODE must be one of: {allowed}")
        return normalized

    @field_validator("db_init_mode", mode="before")
    @classmethod
    def _normalize_db_init_mode(cls, value: object) -> str:
        normalized = "migrate" if value is None else str(value).strip().lower()
        if normalized not in DB_INIT_MODES:
            allowed = ", ".join(sorted(DB_INIT_MODES))
            raise ValueError(f"DB_INIT_MODE must be one of: {allowed}")
        return normalized

    @field_validator("auth_owner", mode="before")
    @classmethod
    def _normalize_auth_owner(cls, value: object) -> str:
        normalized = "none" if value is None else str(value).strip().lower()
        if normalized not in AUTH_OWNERS:
            allowed = ", ".join(sorted(AUTH_OWNERS))
            raise ValueError(f"AUTH_OWNER must be one of: {allowed}")
        return normalized

    @field_validator("storage_exposure", mode="before")
    @classmethod
    def _normalize_storage_exposure(cls, value: object) -> str:
        normalized = "auto" if value is None else str(value).strip().lower()
        if normalized not in STORAGE_EXPOSURE_MODES:
            allowed = ", ".join(sorted(STORAGE_EXPOSURE_MODES))
            raise ValueError(f"STORAGE_EXPOSURE must be one of: {allowed}")
        return normalized

    def model_post_init(self, __context: object) -> None:
        if self.database_url.startswith("sqlite"):
            self.database_url = _normalize_sqlite_url(self.database_url)
        self.storage_dir = _normalize_storage_path(self.storage_dir)
        self._validate_deployment_profile()

    @property
    def allowed_origin_list(self) -> list[str]:
        origins = _split_csv(self.allowed_origins)
        return origins or ["*"]

    @property
    def cors_allow_credentials_enabled(self) -> bool:
        if self.cors_allow_credentials is None:
            return self.deployment_mode == "local"
        return self.cors_allow_credentials

    @property
    def storage_mount_enabled(self) -> bool:
        if self.storage_exposure == "disabled":
            return False
        if self.storage_exposure == "auto":
            return self.deployment_mode == "local"
        return True

    def _validate_deployment_profile(self) -> None:
        if self.deployment_mode != "nonlocal":
            return

        origins = self.allowed_origin_list
        if not origins or "*" in origins or any("*" in origin for origin in origins):
            raise ValueError("ALLOWED_ORIGINS must use explicit origins when DEPLOYMENT_MODE=nonlocal")
        if any(not origin.lower().startswith("https://") for origin in origins):
            raise ValueError("ALLOWED_ORIGINS must use HTTPS origins when DEPLOYMENT_MODE=nonlocal")
        if self.auth_owner != "proxy":
            raise ValueError("AUTH_OWNER=proxy is required when DEPLOYMENT_MODE=nonlocal")
        if not self.trusted_proxy_mode:
            raise ValueError("TRUSTED_PROXY_MODE=true is required when DEPLOYMENT_MODE=nonlocal")
        if not self.proxy_identity_header.strip():
            raise ValueError("PROXY_IDENTITY_HEADER is required when DEPLOYMENT_MODE=nonlocal")
        if self.storage_exposure == "enabled":
            raise ValueError("STORAGE_EXPOSURE=enabled is not allowed when DEPLOYMENT_MODE=nonlocal")

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
