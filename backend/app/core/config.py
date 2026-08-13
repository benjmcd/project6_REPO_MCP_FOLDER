from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Literal
import urllib.parse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)

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


def _path_inside_repo_or_onedrive(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    for root in _local_application_roots():
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return any(_is_onedrive_path_part(part) for part in resolved.parts)


def _local_application_roots() -> tuple[Path, ...]:
    roots = [BACKEND_ROOT.resolve(strict=False)]
    parent = BACKEND_ROOT.parent.resolve(strict=False)
    parent_backend = (parent / "backend").resolve(strict=False)
    if parent_backend == BACKEND_ROOT.resolve(strict=False):
        roots.append(parent)
    return tuple(dict.fromkeys(roots))


def _is_onedrive_path_part(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized == "onedrive" or normalized.startswith("onedrive - ")


def _sqlite_database_path(database_url: str) -> Path | None:
    raw = str(database_url).strip()
    prefix = "sqlite:///"
    if not raw.startswith(prefix):
        return None

    raw_path = raw[len(prefix):].strip()
    if not raw_path or raw_path == ":memory:":
        return None
    if raw_path.startswith("file:"):
        parsed = urllib.parse.urlparse(raw_path)
        path_value = urllib.parse.unquote(parsed.path or "")
        if not path_value or path_value == ":memory:":
            return None
        raw_path = path_value

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = BACKEND_ROOT / candidate
    return candidate.resolve(strict=False)


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
    layer3_external_local_export_dir: str = Field(default="", alias="LAYER3_EXTERNAL_LOCAL_EXPORT_DIR")
    layer3_internal_webhook_url: str = Field(default="", alias="LAYER3_INTERNAL_WEBHOOK_URL")
    layer3_internal_webhook_display_name: str = Field(
        default="server-configured-internal-webhook",
        alias="LAYER3_INTERNAL_WEBHOOK_DISPLAY_NAME",
    )
    layer3_candidate_b_bundle_bridge_dir: str = Field(
        default="",
        alias="LAYER3_CANDIDATE_B_BUNDLE_BRIDGE_DIR",
    )
    layer3_candidate_b_runtime_bridge_dir: str = Field(
        default="",
        alias="LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR",
    )
    layer3_candidate_b_full_corpus_operator_workflow_dir: str = Field(
        default="",
        alias="LAYER3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR",
    )
    layer3_source_ingestion_dir: str = Field(default="", alias="LAYER3_SOURCE_INGESTION_DIR")
    layer3_sec_edgar_user_agent: str = Field(default="", alias="LAYER3_SEC_EDGAR_USER_AGENT")
    layer3_sec_edgar_live_network_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    )
    layer3_sec_edgar_rate_limit_per_second: int = Field(
        default=1,
        alias="LAYER3_SEC_EDGAR_RATE_LIMIT_PER_SECOND",
    )
    layer3_sec_edgar_max_live_requests_per_process: int = Field(
        default=10,
        alias="LAYER3_SEC_EDGAR_MAX_LIVE_REQUESTS_PER_PROCESS",
    )
    layer3_sec_edgar_max_bytes: int = Field(default=25_000_000, alias="LAYER3_SEC_EDGAR_MAX_BYTES")
    layer3_sec_edgar_timeout_seconds: int = Field(default=20, alias="LAYER3_SEC_EDGAR_TIMEOUT_SECONDS")
    layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(
        default=True,
        alias="LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED",
    )
    layer3_sec_edgar_arelle_internal_value_store_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    )
    layer3_sec_edgar_arelle_corpus_validation_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    )
    layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED",
    )
    layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    )
    layer3_sec_edgar_official_ticker_resolution_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_OFFICIAL_TICKER_RESOLUTION_ENABLED",
    )
    layer3_sec_xbrl_controlled_value_reveal_submit_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    )
    layer3_sec_xbrl_storage_root_hygiene_override_ack: bool = Field(
        default=False,
        alias="LAYER3_SEC_XBRL_STORAGE_ROOT_HYGIENE_OVERRIDE_ACK",
    )
    layer3_analysis_product_package_inventory_enabled: bool = Field(
        default=False,
        alias="LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED",
    )
    layer3_model_egress_enabled: bool = Field(
        default=False,
        alias="LAYER3_MODEL_EGRESS_ENABLED",
        description=(
            "Master off-switch for any model/agent egress from Layer 3 / Sublayer 3C. "
            "Must remain False until an explicit egress policy lane (18/19) is in place "
            "and an authorized EgressPolicy factory has been constructed.  "
            "Default: False (deny all model/agent egress)."
        ),
    )
    sec_xbrl_production_admission_evaluator_enabled: bool = Field(
        default=False,
        alias="SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
    )
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
    worldbank_api_base_url: str = Field(default="https://api.worldbank.org/v2", alias="WORLDBANK_API_BASE_URL")
    cftc_cot_api_base_url: str = Field(default="https://www.cftc.gov/dea/newcot", alias="CFTC_COT_API_BASE_URL")
    bls_api_base_url: str = Field(default="https://api.bls.gov/publicAPI/v1/timeseries/data", alias="BLS_API_BASE_URL")
    oecd_sdmx_api_base_url: str = Field(default="https://sdmx.oecd.org/public/rest/data", alias="OECD_SDMX_API_BASE_URL")
    connector_lease_ttl_seconds: int = Field(default=120, alias="CONNECTOR_LEASE_TTL_SECONDS")
    connector_submission_ttl_hours: int = Field(default=24, alias="CONNECTOR_SUBMISSION_TTL_HOURS")
    connector_max_redirects: int = Field(default=3, alias="CONNECTOR_MAX_REDIRECTS")
    connector_max_concurrent_runs: int = Field(default=1, alias="CONNECTOR_MAX_CONCURRENT_RUNS")
    connector_max_downloads_per_run: int = Field(default=1, alias="CONNECTOR_MAX_DOWNLOADS_PER_RUN")
    connector_per_host_fetch_limit: int = Field(default=2, alias="CONNECTOR_PER_HOST_FETCH_LIMIT")
    connector_live_egress_enabled: bool = Field(
        default=False,
        alias="CONNECTOR_LIVE_EGRESS_ENABLED",
    )
    connector_egress_arming_max_ttl_seconds: int = Field(
        default=86_400,
        gt=0,
        alias="CONNECTOR_EGRESS_ARMING_MAX_TTL_SECONDS",
    )
    connector_live_egress_exclusive_proof_mode: bool = Field(
        default=True,
        alias="CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
    )
    connector_campaign_definition_path: Path | None = Field(
        default=None,
        alias="CONNECTOR_CAMPAIGN_DEFINITION_PATH",
    )
    connector_campaign_definition_sha256: str | None = Field(
        default=None,
        alias="CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
    )
    connector_sciencebase_grant_path: Path | None = Field(
        default=None,
        alias="CONNECTOR_SCIENCEBASE_GRANT_PATH",
    )
    connector_sciencebase_grant_sha256: str | None = Field(
        default=None,
        alias="CONNECTOR_SCIENCEBASE_GRANT_SHA256",
    )
    connector_nrc_aps_grant_path: Path | None = Field(
        default=None,
        alias="CONNECTOR_NRC_APS_GRANT_PATH",
    )
    connector_nrc_aps_grant_sha256: str | None = Field(
        default=None,
        alias="CONNECTOR_NRC_APS_GRANT_SHA256",
    )
    connector_campaign_evidence_root: Path | None = Field(
        default=None,
        alias="CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
    )
    connector_campaign_evidence_index_path: Path | None = Field(
        default=None,
        alias="CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
    )
    connector_campaign_evidence_index_sha256: str | None = Field(
        default=None,
        alias="CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
    )
    layer3_route_authorization_mode: Literal["identity_presence", "role_enforcing"] = Field(
        default="identity_presence",
        alias="LAYER3_ROUTE_AUTHORIZATION_MODE",
    )
    proxy_roles_header: str = Field(default="X-Forwarded-Roles", alias="PROXY_ROLES_HEADER")
    layer3_owner_role_tokens: str = Field(default="owner", alias="LAYER3_OWNER_ROLE_TOKENS")
    layer3_auditor_role_tokens: str = Field(default="auditor", alias="LAYER3_AUDITOR_ROLE_TOKENS")
    layer3_connector_promotion_identity_enabled: bool = Field(
        default=False,
        alias="LAYER3_CONNECTOR_PROMOTION_IDENTITY_ENABLED",
    )

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

    @field_validator("layer3_route_authorization_mode", mode="before")
    @classmethod
    def _normalize_layer3_route_authorization_mode(cls, value: object) -> str:
        normalized = "identity_presence" if value is None else str(value).strip().lower()
        allowed_modes = {"identity_presence", "role_enforcing"}
        if normalized not in allowed_modes:
            allowed = ", ".join(sorted(allowed_modes))
            raise ValueError(f"LAYER3_ROUTE_AUTHORIZATION_MODE must be one of: {allowed}")
        return normalized

    def _armed_value_reveal_flags(self) -> list[str]:
        """Return names of value-reveal conjunction flags that are currently true.

        Used for warning emission in any deployment mode.  Includes all five flags
        from the value-reveal conjunction documented in .env.example.
        """
        checks = [
            ("LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED", self.layer3_sec_edgar_arelle_internal_value_store_enabled),
            ("LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED", self.layer3_sec_edgar_arelle_corpus_validation_enabled),
            ("LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED", self.layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized),
            ("LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED", self.layer3_sec_edgar_arelle_value_reveal_enabled),
            ("LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED", self.layer3_sec_xbrl_controlled_value_reveal_submit_enabled),
        ]
        return [name for name, armed in checks if armed]

    def _armed_value_reveal_flags_nonlocal_forbidden(self) -> list[str]:
        """Return names of value-reveal flags that must be false in nonlocal posture.

        Derived from _armed_value_reveal_flags() by filtering out
        LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED, which is
        intentionally excluded: it is a required authorization gate in nonlocal
        deployments and is already validated separately by _validate_deployment_profile.
        """
        _excluded = {"LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED"}
        return [name for name in self._armed_value_reveal_flags() if name not in _excluded]

    def _armed_raw_bearing_sec_flags(self) -> list[str]:
        checks = [
            ("LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED", self.layer3_sec_edgar_live_network_enabled),
            ("LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED", self.layer3_sec_edgar_arelle_internal_value_store_enabled),
            ("LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED", self.layer3_sec_edgar_arelle_corpus_validation_enabled),
            ("LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED", self.layer3_sec_edgar_arelle_value_reveal_enabled),
            ("LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED", self.layer3_sec_xbrl_controlled_value_reveal_submit_enabled),
        ]
        return [name for name, armed in checks if armed]

    def model_post_init(self, __context: object) -> None:
        if self.database_url.startswith("sqlite"):
            self.database_url = _normalize_sqlite_url(self.database_url)
        self.storage_dir = _normalize_storage_path(self.storage_dir)
        self._validate_raw_bearing_sec_storage_containment()
        self._validate_deployment_profile()
        armed = self._armed_value_reveal_flags()
        if armed:
            _logger.warning(
                "Value-reveal conjunction flag(s) armed: %s. "
                "Ensure this is intentional; these flags must stay false in nonlocal/production posture.",
                armed,
            )

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

    def _validate_raw_bearing_sec_storage_containment(self) -> None:
        armed = self._armed_raw_bearing_sec_flags()
        if not armed:
            return

        unsafe_surfaces: list[str] = []
        if self.storage_mount_enabled:
            unsafe_surfaces.append("STORAGE_EXPOSURE")
        if _path_inside_repo_or_onedrive(Path(self.storage_dir)):
            unsafe_surfaces.append("STORAGE_DIR")
        database_path = _sqlite_database_path(self.database_url)
        if database_path is not None and _path_inside_repo_or_onedrive(database_path):
            unsafe_surfaces.append("DATABASE_URL")
        if not unsafe_surfaces:
            return

        raise ValueError(
            "Raw-bearing SEC egress/value-reveal flag(s) cannot be armed while storage or database "
            "containment is unsafe. Armed flags: "
            + ", ".join(armed)
            + ". Unsafe surface(s): "
            + ", ".join(unsafe_surfaces)
        )

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
        if self.storage_exposure in {"enabled", "proxy_protected"}:
            raise ValueError("STORAGE_EXPOSURE must be auto or disabled when DEPLOYMENT_MODE=nonlocal")
        if (
            self.layer3_sec_edgar_arelle_fact_authority_cutover_enabled
            and not self.layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized
        ):
            raise ValueError(
                "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED=true is required "
                "when DEPLOYMENT_MODE=nonlocal and Arelle fact-authority cutover is enabled"
            )
        if self.database_url.startswith("sqlite"):
            raise ValueError("DATABASE_URL must not use sqlite when DEPLOYMENT_MODE=nonlocal")
        if (
            self.layer3_route_authorization_mode == "role_enforcing"
            and not self.proxy_roles_header.strip()
        ):
            raise ValueError(
                "PROXY_ROLES_HEADER is required when DEPLOYMENT_MODE=nonlocal and "
                "LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing"
            )
        armed = self._armed_value_reveal_flags_nonlocal_forbidden()
        if armed:
            raise ValueError(
                "Value-reveal conjunction flag(s) must be false when DEPLOYMENT_MODE=nonlocal: "
                + ", ".join(armed)
            )

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

    @property
    def layer3_local_outbox_dir(self) -> str:
        return str(Path(self.storage_dir) / "layer3-outbox")


settings = Settings(_env_file=None) if sys.flags.isolated else Settings()


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
        root / "layer3-outbox",
    )
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
