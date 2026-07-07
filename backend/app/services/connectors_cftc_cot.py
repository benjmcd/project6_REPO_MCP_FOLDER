from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    ConnectorPolicySnapshot,
    ConnectorRun,
    ConnectorRunSubmission,
    ConnectorRunTarget,
    Dataset,
    DatasetExternalIdentity,
    DatasetSourceProvenance,
    DatasetVersion,
)
from app.services import connectors_sciencebase as _sciencebase_helpers
from app.services.connectors_sciencebase import (
    _acquire_lease,
    _classify_download_exception,
    _cooperate_with_cancel_request,
    _finalize_run,
    _precheck_download_url,
    _record_run_event,
    _release_lease,
    _renew_lease,
    _resolve_host_ip,
    _to_utc_naive,
    _utcnow,
    _write_json,
)
from app.services.sciencebase_connector.contracts import (
    DownloadResult,
    FetchPolicyBlockedError,
    RUN_TERMINAL_STATUSES,
    SubmissionConflictError,
)
from app.services.sciencebase_connector.executor import ExecutorGuards


CONNECTOR_KEY = "cftc_cot"
SOURCE_SYSTEM = "cftc_cot"
ALLOWED_HOST = "www.cftc.gov"
CFTC_COT_INDEX_URL = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"
PHASE0_DOC_URLS = [
    CFTC_COT_INDEX_URL,
    "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm",
    "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/cotvariableslegacy.html",
    "https://www.cftc.gov/MarketReports/CommitmentsofTraders/DisaggregatedExplanatoryNotes/index.htm",
    "https://www.cftc.gov/MarketReports/CommitmentsofTraders/AbouttheCOTReports/cot_about",
]
REPORT_VARIANT_FILES = {
    "legacy_futures_only": "deafut.txt",
    "legacy_combined": "deacom.txt",
}
ATTRIBUTION = "U.S. Commodity Futures Trading Commission Commitments of Traders"
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
SUMMARY_SCHEMA_ID = "cftc_cot.summary.v1"
SELECTION_SCHEMA_ID = "cftc_cot.selection_manifest.v1"
CFTC_COT_EXECUTOR_GUARDS = ExecutorGuards(max_concurrent_runs=settings.connector_max_concurrent_runs)

LEGACY_COT_FIELDS = [
    "Market_and_Exchange_Names",
    "As_of_Date_In_Form_YYMMDD",
    "As_of_Date_Form_YYYY-MM-DD",
    "CFTC_Contract_Market_Code",
    "CFTC_Market_Code",
    "CFTC_Region_Code",
    "CFTC_Commodity_Code",
    "Open_Interest_All",
    "Noncommercial_Positions_Long_All",
    "Noncommercial_Positions_Short_All",
    "Noncommercial_Positions_Spreading_All",
    "Commercial_Positions_Long_All",
    "Commercial_Positions_Short_All",
    "Total_Reportable_Positions_Long_All",
    "Total_Reportable_Positions_Short_All",
    "Nonreportable_Positions_Long_All",
    "Nonreportable_Positions_Short_All",
]
NUMERIC_FIELDS = LEGACY_COT_FIELDS[7:]


class CftcCotSchemaValidationError(ValueError):
    pass


def _stable_json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _clean_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _coerce_int(value: Any, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        out = int(value)
    except Exception:
        out = int(default)
    if minimum is not None:
        out = max(minimum, out)
    if maximum is not None:
        out = min(maximum, out)
    return out


def _coerce_float(value: Any, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        out = float(value)
    except Exception:
        out = float(default)
    if minimum is not None:
        out = max(minimum, out)
    if maximum is not None:
        out = min(maximum, out)
    return out


def _logical_query_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_variant": config.get("report_variant"),
        "market_name_contains": config.get("market_name_contains"),
        "exchange_name_contains": config.get("exchange_name_contains"),
        "max_rows": int(config.get("max_rows", 1000)),
    }


def _normalize_request_config(payload: dict[str, Any], submission_idempotency_key: str | None) -> dict[str, Any]:
    config = dict(payload)
    config["report_variant"] = str(config.get("report_variant") or "legacy_futures_only").strip()
    if config["report_variant"] not in REPORT_VARIANT_FILES:
        config["report_variant"] = "legacy_futures_only"
    config["market_name_contains"] = _clean_string(config.get("market_name_contains"))
    config["exchange_name_contains"] = _clean_string(config.get("exchange_name_contains"))
    config["max_rows"] = _coerce_int(config.get("max_rows"), 1000, minimum=1, maximum=5000)
    config["max_file_bytes"] = _coerce_int(config.get("max_file_bytes"), 8 * 1024 * 1024, minimum=1, maximum=8 * 1024 * 1024)
    config["run_mode"] = str(config.get("run_mode", "metadata_only")).strip().lower()
    if config["run_mode"] not in {"metadata_only", "dry_run"}:
        config["run_mode"] = "metadata_only"
    config["request_timeout_seconds"] = _coerce_int(config.get("request_timeout_seconds"), 30, minimum=5, maximum=120)
    config["retry_max_attempts_per_request"] = _coerce_int(config.get("retry_max_attempts_per_request"), 4, minimum=1, maximum=8)
    config["retry_base_backoff_seconds"] = _coerce_float(config.get("retry_base_backoff_seconds"), 0.4, minimum=0.0, maximum=10.0)
    config["retry_max_backoff_seconds"] = _coerce_float(config.get("retry_max_backoff_seconds"), 3.0, minimum=float(config["retry_base_backoff_seconds"]), maximum=60.0)
    config["retry_respect_retry_after"] = bool(config.get("retry_respect_retry_after", True))
    config["max_rps"] = _coerce_float(config.get("max_rps"), 2.0, minimum=0.1, maximum=2.0)
    config["report_verbosity"] = str(config.get("report_verbosity", "standard")).strip().lower()
    if config["report_verbosity"] not in {"summary", "standard", "debug"}:
        config["report_verbosity"] = "standard"
    config["client_request_id"] = _clean_string(config.get("client_request_id"))
    config["submission_idempotency_key"] = submission_idempotency_key or config["client_request_id"]
    config["allowed_hosts"] = [ALLOWED_HOST]
    config["fetch_policy_summary"] = {
        "mode": "official_file_only",
        "surface_policy": "public_report_rows",
        "external_fetch_policy": "cftc_cot_official_only",
        "allowed_hosts": [ALLOWED_HOST],
    }
    config["source_query_fingerprint"] = _stable_json_hash(_logical_query_from_config(config))
    return config


def _cftc_fetch_policy(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "strict_public_safe",
        "external_fetch_policy": "cftc_cot_official_only",
        "allowed_schemes": ["https"],
        "allowed_hosts": [ALLOWED_HOST],
        "max_redirects": int(config.get("max_redirects", settings.connector_max_redirects)),
    }


def _precheck_cftc_download_url(url: str, policy: dict[str, Any]) -> tuple[str | None, str | None]:
    original_resolver = _sciencebase_helpers._resolve_host_ip
    try:
        _sciencebase_helpers._resolve_host_ip = _resolve_host_ip
        return _precheck_download_url(url, policy)
    finally:
        _sciencebase_helpers._resolve_host_ip = original_resolver


def _classify_cftc_exception(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, CftcCotSchemaValidationError):
        return str(exc) or "schema_validation_failed", False
    if isinstance(exc, FetchPolicyBlockedError):
        return exc.reason or "fetch_policy_blocked", False
    return _classify_download_exception(exc)


class _RateLimiter:
    def __init__(self, max_rps: float):
        self._interval = 0.0 if max_rps <= 0 else 1.0 / max_rps
        self._last_call = 0.0
        self.total_sleep_seconds = 0.0

    def wait(self) -> None:
        if self._interval <= 0:
            return
        now = time.monotonic()
        wait_seconds = self._interval - (now - self._last_call)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
            self.total_sleep_seconds += wait_seconds
        self._last_call = time.monotonic()


class CftcCotClient:
    def __init__(self, *, base_url: str):
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != ALLOWED_HOST:
            raise CftcCotSchemaValidationError("inadmissible_cftc_cot_base_url")
        self.session = requests.Session()

    @property
    def auth_mode(self) -> str:
        return "anonymous"

    def report_url(self, report_variant: str) -> str:
        filename = REPORT_VARIANT_FILES[report_variant]
        return f"{self.base_url}/{filename}"

    def download_artifact(
        self,
        *,
        url: str,
        timeout_seconds: int,
        max_redirects: int,
        headers: dict[str, str] | None = None,
        rate_limiter: _RateLimiter | None = None,
        retry_counters: dict[str, Any] | None = None,
        retry_max_attempts_per_request: int = 4,
        retry_base_backoff_seconds: float = 0.4,
        retry_max_backoff_seconds: float = 3.0,
        retry_respect_retry_after: bool = True,
    ) -> DownloadResult:
        counters = retry_counters if retry_counters is not None else {}
        last_exc: Exception | None = None
        for attempt in range(1, retry_max_attempts_per_request + 1):
            if rate_limiter is not None:
                rate_limiter.wait()
            counters["requests_total"] = int(counters.get("requests_total", 0)) + 1
            try:
                response = self.session.get(url, stream=True, timeout=(10, timeout_seconds), allow_redirects=True, headers=headers or {})
                if len(response.history) > max_redirects:
                    raise FetchPolicyBlockedError("redirect_policy_violation")
                final_host = (urlparse(str(response.url)).hostname or "").lower()
                if final_host != ALLOWED_HOST:
                    raise FetchPolicyBlockedError("host_not_allowed")
                if response.status_code in RETRYABLE_HTTP_STATUSES and attempt < retry_max_attempts_per_request:
                    counters["retries_total"] = int(counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    if retry_respect_retry_after:
                        try:
                            wait_seconds = min(retry_max_backoff_seconds, max(wait_seconds, float(response.headers.get("Retry-After") or "")))
                        except Exception:
                            pass
                    time.sleep(wait_seconds)
                    counters["retry_sleep_seconds"] = float(counters.get("retry_sleep_seconds", 0.0)) + float(wait_seconds)
                    continue
                response.raise_for_status()
                hasher = hashlib.sha256()
                chunks: list[bytes] = []
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    hasher.update(chunk)
                body = b"".join(chunks)
                final_url = str(response.url)
                resolved_ip = _resolve_host_ip(final_host) if final_host else None
                return DownloadResult(
                    content=body,
                    status_code=int(response.status_code),
                    final_url=final_url,
                    redirect_count=len(response.history),
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                    content_type=response.headers.get("content-type"),
                    sha256=hasher.hexdigest(),
                    headers=dict(response.headers),
                    resolved_ip=resolved_ip,
                )
            except Exception as exc:
                last_exc = exc
                error_class, retryable = _classify_cftc_exception(exc)
                if retryable and attempt < retry_max_attempts_per_request:
                    counters["retries_total"] = int(counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    time.sleep(wait_seconds)
                    counters["retry_sleep_seconds"] = float(counters.get("retry_sleep_seconds", 0.0)) + float(wait_seconds)
                    continue
                counters["last_error_class"] = error_class
                raise
        raise last_exc or RuntimeError("cftc_cot_download_failed_without_exception")


def get_cftc_cot_client(config: dict[str, Any]) -> CftcCotClient:
    return CftcCotClient(base_url=settings.cftc_cot_api_base_url)


def _download_cftc_file(
    client: Any,
    target: ConnectorRunTarget,
    config: dict[str, Any],
    rate_limiter: _RateLimiter,
    retry_counters: dict[str, Any],
) -> DownloadResult:
    fetch_policy = _cftc_fetch_policy(config)
    resolved_ip, reason = _precheck_cftc_download_url(target.sciencebase_download_uri or "", fetch_policy)
    target.resolved_ip = resolved_ip
    if reason:
        raise FetchPolicyBlockedError(reason)
    host_gate = ExecutorGuards.acquire_host_slot(target.sciencebase_download_uri or "", int(settings.connector_per_host_fetch_limit))
    try:
        result = client.download_artifact(
            url=target.sciencebase_download_uri or "",
            timeout_seconds=int(config.get("request_timeout_seconds", 30)),
            max_redirects=int(config.get("max_redirects", settings.connector_max_redirects)),
            headers=None,
            rate_limiter=rate_limiter,
            retry_counters=retry_counters,
            retry_max_attempts_per_request=int(config.get("retry_max_attempts_per_request", 4)),
            retry_base_backoff_seconds=float(config.get("retry_base_backoff_seconds", 0.4)),
            retry_max_backoff_seconds=float(config.get("retry_max_backoff_seconds", 3.0)),
            retry_respect_retry_after=bool(config.get("retry_respect_retry_after", True)),
        )
    finally:
        host_gate.release()
    resolved_ip_2, reason_2 = _precheck_cftc_download_url(result.final_url, fetch_policy)
    target.resolved_ip = resolved_ip_2 or result.resolved_ip or target.resolved_ip
    target.redirect_count = int(result.redirect_count or 0)
    if reason_2:
        raise FetchPolicyBlockedError(reason_2)
    if len(result.content) > int(config.get("max_file_bytes", 8 * 1024 * 1024)):
        raise FetchPolicyBlockedError("file_size_limit_exceeded")
    return result


def _to_int(value: Any) -> int | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    return int(float(text))


def _normalize_row(raw: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    if None in raw:
        raise CftcCotSchemaValidationError("row_shape_mismatch")
    market = _clean_string(raw.get("Market_and_Exchange_Names"))
    report_date = _clean_string(raw.get("As_of_Date_Form_YYYY-MM-DD"))
    yymmdd = _clean_string(raw.get("As_of_Date_In_Form_YYMMDD"))
    contract_code = _clean_string(raw.get("CFTC_Contract_Market_Code"))
    market_code = _clean_string(raw.get("CFTC_Market_Code"))
    region_code = _clean_string(raw.get("CFTC_Region_Code"))
    commodity_code = _clean_string(raw.get("CFTC_Commodity_Code"))
    if not all([market, report_date, yymmdd, contract_code, market_code, region_code, commodity_code]):
        raise CftcCotSchemaValidationError("missing_required_cot_field")
    market_filter = _clean_string(config.get("market_name_contains"))
    exchange_filter = _clean_string(config.get("exchange_name_contains"))
    market_lower = market.lower()
    if market_filter and market_filter.lower() not in market_lower:
        return None
    if exchange_filter and exchange_filter.lower() not in market_lower:
        return None
    numeric = {field: _to_int(raw.get(field)) for field in NUMERIC_FIELDS}
    if all(value is None for value in numeric.values()):
        return None
    return {
        "market_and_exchange": market,
        "report_date_yymmdd": yymmdd,
        "report_date": report_date,
        "contract_market_code": contract_code,
        "market_code": market_code,
        "region_code": region_code,
        "commodity_code": commodity_code,
        "open_interest_all": numeric["Open_Interest_All"],
        "noncommercial_long_all": numeric["Noncommercial_Positions_Long_All"],
        "noncommercial_short_all": numeric["Noncommercial_Positions_Short_All"],
        "noncommercial_spreading_all": numeric["Noncommercial_Positions_Spreading_All"],
        "commercial_long_all": numeric["Commercial_Positions_Long_All"],
        "commercial_short_all": numeric["Commercial_Positions_Short_All"],
        "total_reportable_long_all": numeric["Total_Reportable_Positions_Long_All"],
        "total_reportable_short_all": numeric["Total_Reportable_Positions_Short_All"],
        "nonreportable_long_all": numeric["Nonreportable_Positions_Long_All"],
        "nonreportable_short_all": numeric["Nonreportable_Positions_Short_All"],
    }


def _parse_legacy_cot_rows(content: bytes, config: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CftcCotSchemaValidationError("cot_decode_failed") from exc
    reader = csv.DictReader(StringIO(text))
    header = [str(name or "").strip() for name in (reader.fieldnames or [])]
    if header[: len(LEGACY_COT_FIELDS)] != LEGACY_COT_FIELDS:
        raise CftcCotSchemaValidationError("unrecognized_cot_header")
    rows: list[dict[str, Any]] = []
    source_row_count = 0
    for raw in reader:
        source_row_count += 1
        normalized = _normalize_row(raw, config)
        if normalized is None:
            continue
        rows.append(normalized)
        if len(rows) >= int(config.get("max_rows", 1000)):
            break
    if source_row_count == 0:
        raise CftcCotSchemaValidationError("empty_report")
    if not rows:
        raise CftcCotSchemaValidationError("empty_after_normalization")
    return rows, source_row_count


def _summary_report_path(run_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_cftc_cot_summary_v1.json"


def _selection_manifest_path(run_id: str) -> Path:
    return Path(settings.connector_manifests_dir) / f"{run_id}_cftc_cot_selection_manifest_v1.json"


def _report_url_for_variant(report_variant: str) -> str:
    return f"{settings.cftc_cot_api_base_url.rstrip('/')}/{REPORT_VARIANT_FILES[report_variant]}"


def submit_cftc_cot_run(db: Session, *, payload: dict[str, Any], idempotency_key: str | None) -> tuple[ConnectorRun, bool]:
    submitted_key = (idempotency_key or payload.get("client_request_id") or "").strip() or None
    config = _normalize_request_config(payload, submitted_key)
    request_fingerprint = _stable_json_hash(config)
    now = _utcnow()
    if submitted_key:
        existing_submission = db.query(ConnectorRunSubmission).filter(and_(ConnectorRunSubmission.connector_key == CONNECTOR_KEY, ConnectorRunSubmission.submission_idempotency_key == submitted_key)).first()
        expires_at = _to_utc_naive(existing_submission.expires_at) if existing_submission else None
        now_naive = _to_utc_naive(now)
        if existing_submission and (expires_at is None or (now_naive is not None and expires_at > now_naive)):
            if existing_submission.request_fingerprint != request_fingerprint:
                raise SubmissionConflictError("idempotency key reused with different payload")
            existing_run = db.get(ConnectorRun, existing_submission.connector_run_id)
            if existing_run:
                return existing_run, False
    if db.query(ConnectorRun).filter(ConnectorRun.status.in_(["pending", "running", "cancelling"])).count() >= int(settings.connector_max_concurrent_runs):
        raise SubmissionConflictError("active run concurrency limit reached")
    run = ConnectorRun(
        connector_key=CONNECTOR_KEY,
        source_system=SOURCE_SYSTEM,
        source_mode="public_file",
        status="pending",
        request_config_json=config,
        source_query_fingerprint=str(config.get("source_query_fingerprint") or ""),
        request_fingerprint=request_fingerprint,
        effective_search_params_json={},
        effective_filters_json=[],
        effective_sort="report_date",
        effective_order="desc",
        effective_page_size=int(config.get("max_rows", 1000)),
        submission_idempotency_key=submitted_key,
        adapter_dialect="cftc_cot_legacy_text",
        api_generation="current_legacy_long_form",
        sciencebase_normalization_version="n/a",
        submitted_at=now,
    )
    db.add(run)
    db.flush()
    if submitted_key:
        db.add(ConnectorRunSubmission(connector_key=CONNECTOR_KEY, submission_idempotency_key=submitted_key, request_fingerprint=request_fingerprint, connector_run_id=run.connector_run_id, expires_at=now + timedelta(hours=settings.connector_submission_ttl_hours)))
    db.add(ConnectorPolicySnapshot(connector_run_id=run.connector_run_id, policy_json=config, retry_matrix_json={"retryable_http_statuses": sorted(RETRYABLE_HTTP_STATUSES), "retry_max_attempts_per_request": int(config.get("retry_max_attempts_per_request", 4))}))
    _record_run_event(db, run=run, event_type="run_submitted", phase="planning", status_after="pending", metrics_json={"connector_key": CONNECTOR_KEY, "auth_mode": "anonymous"})
    db.commit()
    db.refresh(run)
    return run, True


def _client_auth_mode(client: Any) -> str:
    return str(getattr(client, "auth_mode", "anonymous") or "anonymous")


def _client_report_url(client: Any, report_variant: str) -> str:
    if hasattr(client, "report_url"):
        return str(client.report_url(report_variant))
    return _report_url_for_variant(report_variant)


def _target_for_report(*, run: ConnectorRun, config: dict[str, Any], report_url: str) -> ConnectorRunTarget:
    now = _utcnow()
    variant = str(config.get("report_variant", "legacy_futures_only"))
    artifact_key = f"cftc_cot:{variant}:current"
    target_status = "dry_run_skipped" if str(config.get("run_mode", "metadata_only")) == "dry_run" else "selected"
    source_ref = {
        "source_system": SOURCE_SYSTEM,
        "report_variant": variant,
        "report_url": report_url,
        "cftc_cot_index_url": CFTC_COT_INDEX_URL,
        "phase0_format_pin": "official_cftc_doc_pages",
        "phase0_doc_urls": PHASE0_DOC_URLS,
        "historical_patterns_provenance_only": [
            "https://www.cftc.gov/files/dea/history/deacot{YYYY}.zip",
            "https://www.cftc.gov/files/dea/history/deahistfo{YYYY}.zip",
        ],
        "current_file_url_unverified_until_live_pilot": report_url,
    }
    return ConnectorRunTarget(
        connector_run_id=run.connector_run_id,
        ordinal=1,
        stable_release_key=artifact_key,
        stable_release_identifier=artifact_key,
        identifiers_json=[{"type": "cftc_cot_report_variant", "value": variant}],
        sciencebase_item_id=variant,
        sciencebase_item_url=CFTC_COT_INDEX_URL,
        sciencebase_file_name=REPORT_VARIANT_FILES[variant],
        sciencebase_download_uri=report_url,
        artifact_surface="current_legacy_long_form_report",
        selection_source=SOURCE_SYSTEM,
        selection_scope="current_report_file",
        selection_match_basis="report_variant",
        artifact_locator_type="https_text_file",
        source_artifact_key=artifact_key,
        canonical_artifact_key=artifact_key,
        source_reference_json=source_ref,
        permission_snapshot_json={"access": "public", "auth_mode": "anonymous", "attribution": ATTRIBUTION},
        access_level_summary="public_file",
        public_read_confirmed=True,
        status=target_status,
        retry_eligible=False,
        discovered_at=now,
        selected_at=now,
        recommended_at=now if target_status == "dry_run_skipped" else None,
        last_stage_transition_at=now,
        operator_reason_code="dry_run_report_file_selected" if target_status == "dry_run_skipped" else "report_file_selected",
    )


def _resolve_dataset_id(db: Session, logical_dataset_key: str) -> str | None:
    existing = db.query(DatasetExternalIdentity).filter(and_(DatasetExternalIdentity.source_system == SOURCE_SYSTEM, DatasetExternalIdentity.logical_dataset_key == logical_dataset_key)).first()
    return existing.dataset_id if existing else None


def _persist_dataset_identity(db: Session, dataset_id: str, logical_dataset_key: str, metadata_json: dict[str, Any]) -> None:
    existing = db.query(DatasetExternalIdentity).filter(and_(DatasetExternalIdentity.source_system == SOURCE_SYSTEM, DatasetExternalIdentity.logical_dataset_key == logical_dataset_key)).first()
    if existing:
        return
    db.add(DatasetExternalIdentity(dataset_id=dataset_id, source_system=SOURCE_SYSTEM, logical_dataset_key=logical_dataset_key, metadata_json=metadata_json))
    db.flush()


def _ensure_cftc_metadata_provenance(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    rows: list[dict[str, Any]],
    result: DownloadResult,
) -> None:
    if target.status != "recommended":
        return
    logical_dataset_key = target.stable_release_key or f"cftc_cot:{target.sciencebase_item_id or target.connector_run_target_id}"
    if not target.dataset_id:
        dataset_id = _resolve_dataset_id(db, logical_dataset_key)
        if not dataset_id:
            dataset = Dataset(
                name=f"CFTC COT {target.sciencebase_item_id or 'current'}",
                description=f"{ATTRIBUTION}; rows retained only in connector reports",
                domain_pack="public_connectors",
                frequency_hint="weekly",
                time_column="report_date",
            )
            db.add(dataset)
            db.flush()
            dataset_id = dataset.dataset_id
            _persist_dataset_identity(
                db,
                dataset_id=dataset_id,
                logical_dataset_key=logical_dataset_key,
                metadata_json={
                    "source_system": SOURCE_SYSTEM,
                    "stable_release_key": target.stable_release_key,
                    "source_artifact_key": target.source_artifact_key,
                    "identifiers": target.identifiers_json or [],
                },
            )
        target.dataset_id = dataset_id
    if not target.dataset_version_id:
        content_payload = {
            "source_system": SOURCE_SYSTEM,
            "source_artifact_key": target.source_artifact_key,
            "downloaded_sha256": result.sha256,
            "row_count": len(rows),
            "row_hashes": [_stable_json_hash({"row": row}) for row in rows],
        }
        version = DatasetVersion(
            dataset_id=target.dataset_id,
            version_label=f"cftc_cot_{str(target.sciencebase_item_id or target.ordinal).replace(':', '_')[:80]}_{run.connector_run_id[:8]}",
            version_type="source_metadata",
            status="ready",
            storage_ref=target.source_artifact_key,
            row_count=len(rows),
            content_hash=_stable_json_hash(content_payload),
            source_row_count=len(rows),
            dropped_row_count=0,
            notes=f"connector_run_id={run.connector_run_id}; source_artifact_key={target.source_artifact_key}",
        )
        db.add(version)
        db.flush()
        target.dataset_version_id = version.dataset_version_id
    existing_provenance = db.query(DatasetSourceProvenance).filter(and_(DatasetSourceProvenance.dataset_version_id == target.dataset_version_id, DatasetSourceProvenance.connector_run_id == run.connector_run_id, DatasetSourceProvenance.source_system == SOURCE_SYSTEM)).first()
    if existing_provenance:
        return
    db.add(
        DatasetSourceProvenance(
            dataset_version_id=target.dataset_version_id,
            connector_run_id=run.connector_run_id,
            source_system=SOURCE_SYSTEM,
            source_mode="metadata_only",
            source_artifact_key=target.source_artifact_key or target.stable_release_key or "",
            sciencebase_item_id=target.sciencebase_item_id,
            sciencebase_item_url=target.sciencebase_item_url,
            sciencebase_file_name=target.sciencebase_file_name,
            artifact_surface=target.artifact_surface,
            artifact_locator_type=target.artifact_locator_type,
            source_query_fingerprint=run.source_query_fingerprint,
            source_reference_json=target.source_reference_json or {},
            fetch_policy_mode="cftc_cot_official_only",
            retrieved_http_json={
                "api_base_url": settings.cftc_cot_api_base_url,
                "report_url": target.sciencebase_download_uri,
                "final_url": result.final_url,
                "allowed_hosts": [ALLOWED_HOST],
                "sha256": result.sha256,
                "etag": result.etag,
                "last_modified": result.last_modified,
                "content_type": result.content_type,
                "redirect_count": result.redirect_count,
                "phase0_doc_urls": PHASE0_DOC_URLS,
            },
            discovered_at=target.discovered_at,
            downloaded_at=target.downloaded_at,
        )
    )
    db.flush()


def _process_current_report(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    client: Any,
    config: dict[str, Any],
    rate_limiter: _RateLimiter,
    retry_counters: dict[str, Any],
) -> list[dict[str, Any]]:
    if target.status == "dry_run_skipped":
        return []
    target.attempt_count = int(target.attempt_count or 0) + 1
    target.last_attempt_at = _utcnow()
    target.last_stage_transition_at = _utcnow()
    db.commit()
    try:
        result = _download_cftc_file(client, target, config, rate_limiter, retry_counters)
        target.downloaded_sha256 = result.sha256
        target.etag = result.etag
        target.last_modified = result.last_modified
        target.downloaded_at = _utcnow()
        rows, source_row_count = _parse_legacy_cot_rows(result.content, config)
        target.status = "recommended"
        target.recommended_at = _utcnow()
        target.error_stage = None
        target.error_message = None
        target.last_error_class = None
        target.retry_eligible = False
        target.operator_reason_code = "report_rows_recorded"
        target.last_stage_transition_at = _utcnow()
        source_ref = dict(target.source_reference_json or {})
        source_ref.update(
            {
                "source_row_count": source_row_count,
                "normalized_row_count": len(rows),
                "content_sha256": result.sha256,
                "final_url": result.final_url,
                "redirect_count": result.redirect_count,
            }
        )
        target.source_reference_json = source_ref
        _ensure_cftc_metadata_provenance(db, run=run, target=target, rows=rows, result=result)
        _record_run_event(db, run=run, target=target, event_type="target_rows_recorded", phase="selection", status_after="recommended", reason_code="report_rows_recorded")
        db.commit()
        return rows
    except Exception as exc:
        error_class, retryable = _classify_cftc_exception(exc)
        blocked = isinstance(exc, FetchPolicyBlockedError)
        target.status = "blocked_by_fetch_policy" if blocked else "download_failed"
        target.error_stage = "downloading" if blocked else "format_validation"
        target.error_message = str(exc)
        target.last_error_class = error_class
        target.retry_eligible = retryable
        target.last_stage_transition_at = _utcnow()
        target.operator_reason_code = error_class
        if blocked:
            target.blocked_reason = error_class
        _record_run_event(
            db,
            run=run,
            target=target,
            event_type="target_blocked_by_fetch_policy" if blocked else "target_failed_closed",
            phase="selection",
            status_after=target.status,
            error_class=error_class,
            message=str(exc),
            reason_code=error_class,
        )
        db.commit()
        return []


def _write_selection_manifest(db: Session, *, run: ConnectorRun, rows_by_target: dict[str, list[dict[str, Any]]]) -> None:
    targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).order_by(ConnectorRunTarget.ordinal.asc()).all()
    target_payloads = [
        {
            "target_id": target.connector_run_target_id,
            "ordinal": int(target.ordinal or 0),
            "report_variant": target.sciencebase_item_id,
            "status": target.status,
            "last_error_class": target.last_error_class,
            "source_artifact_key": target.source_artifact_key,
            "rows": rows_by_target.get(target.connector_run_target_id, []),
        }
        for target in targets
    ]
    run.page_count_completed = len([item for item in target_payloads if item["status"] in {"recommended", "dry_run_skipped"}])
    run.last_offset_committed = len(target_payloads)
    run.search_exhaustion_reason = "report_processed" if run.page_count_completed else "error"
    run.selection_manifest_ref = _write_json(
        _selection_manifest_path(run.connector_run_id),
        {
            "schema_id": SELECTION_SCHEMA_ID,
            "schema_version": 1,
            "connector_run_id": run.connector_run_id,
            "targets": target_payloads,
        },
    )
    db.commit()


def _write_summary(
    db: Session,
    *,
    run: ConnectorRun,
    config: dict[str, Any],
    client: Any,
    retry_counters: dict[str, Any],
    rows_by_target: dict[str, list[dict[str, Any]]],
) -> None:
    targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).order_by(ConnectorRunTarget.ordinal.asc()).all()
    rows: list[dict[str, Any]] = []
    for target_rows in rows_by_target.values():
        rows.extend(target_rows)
    summary = {
        "schema_id": SUMMARY_SCHEMA_ID,
        "schema_version": 1,
        "generated_at_utc": _utcnow().isoformat(),
        "connector_run_id": run.connector_run_id,
        "connector_key": run.connector_key,
        "status": run.status,
        "api_base_url": settings.cftc_cot_api_base_url,
        "auth_mode": _client_auth_mode(client),
        "report_variant": str(config.get("report_variant", "legacy_futures_only")),
        "phase0_doc_urls": PHASE0_DOC_URLS,
        "rows": rows,
        "totals": {
            "discovered_count": int(run.discovered_count or 0),
            "recommended_count": int(run.recommended_count or 0),
            "failed_count": int(run.failed_count or 0),
            "blocked_by_fetch_policy_count": int(run.blocked_by_fetch_policy_count or 0),
            "row_count": len(rows),
        },
        "targets": [
            {
                "ordinal": int(target.ordinal or 0),
                "report_variant": target.sciencebase_item_id,
                "status": target.status,
                "last_error_class": target.last_error_class,
                "source_artifact_key": target.source_artifact_key,
            }
            for target in targets
        ],
        "attribution": ATTRIBUTION,
        "retry_summary": {
            "requests_total": int(retry_counters.get("requests_total", 0)),
            "retries_total": int(retry_counters.get("retries_total", 0)),
            "retry_sleep_seconds": round(float(retry_counters.get("retry_sleep_seconds", 0.0)), 4),
            "rate_limiter_sleep_seconds": round(float(retry_counters.get("rate_limiter_sleep_seconds", 0.0)), 4),
            "last_error_class": retry_counters.get("last_error_class"),
        },
    }
    summary_ref = _write_json(_summary_report_path(run.connector_run_id), summary)
    run.query_plan_json = {**(run.query_plan_json or {}), "connector_report_refs": {"cftc_cot_summary": summary_ref}}
    db.commit()


def execute_cftc_cot_run(connector_run_id: str) -> None:
    db = SessionLocal()
    try:
        CFTC_COT_EXECUTOR_GUARDS.acquire_run_slot()
        try:
            run = db.get(ConnectorRun, connector_run_id)
            if not run or run.status in RUN_TERMINAL_STATUSES:
                return
            if not _acquire_lease(db, run):
                run.error_summary = "lease_conflict"
                _record_run_event(db, run=run, event_type="lease_conflict", phase="planning", status_after=run.status, error_class="lease_conflict")
                db.commit()
                return
            config = dict(run.request_config_json or {})
            client = get_cftc_cot_client(config)
            report_url = _client_report_url(client, str(config.get("report_variant", "legacy_futures_only")))
            run.effective_search_params_json = {
                "base_url": settings.cftc_cot_api_base_url,
                "auth_mode": _client_auth_mode(client),
                "logical_query": _logical_query_from_config(config),
                "report_url": report_url,
            }
            run.effective_filters_json = [{"field": key, "value": value} for key, value in _logical_query_from_config(config).items()]
            run.effective_sort = "report_date"
            run.effective_order = "desc"
            run.effective_page_size = int(config.get("max_rows", 1000))
            db.commit()

            retry_counters: dict[str, Any] = {}
            rows_by_target: dict[str, list[dict[str, Any]]] = {}
            rate_limiter = _RateLimiter(float(config.get("max_rps", 2.0)))
            target_count = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).count()
            if target_count == 0 or not run.selection_manifest_ref:
                if _cooperate_with_cancel_request(db, run, phase="discovery"):
                    return
                target = _target_for_report(run=run, config=config, report_url=report_url)
                db.add(target)
                db.flush()
                _record_run_event(db, run=run, target=target, event_type="target_created", phase="selection", status_after=target.status, reason_code=target.operator_reason_code)
                db.commit()
                rows = _process_current_report(db, run=run, target=target, client=client, config=config, rate_limiter=rate_limiter, retry_counters=retry_counters)
                if rows:
                    rows_by_target[target.connector_run_target_id] = rows
                _renew_lease(db, run)
                _write_selection_manifest(db, run=run, rows_by_target=rows_by_target)

            retry_counters["rate_limiter_sleep_seconds"] = rate_limiter.total_sleep_seconds
            _finalize_run(db, run)
            _write_summary(db, run=run, config=config, client=client, retry_counters=retry_counters, rows_by_target=rows_by_target)
            _record_run_event(db, run=run, event_type="run_finalized", phase="finalizing", status_after=run.status, metrics_json={"connector_key": CONNECTOR_KEY}, commit=True)
        finally:
            CFTC_COT_EXECUTOR_GUARDS.release_run_slot()
    except Exception as exc:
        run = db.get(ConnectorRun, connector_run_id)
        if run:
            error_class, _retryable = _classify_cftc_exception(exc)
            run.status = "failed"
            run.search_exhaustion_reason = error_class
            run.error_summary = f"{error_class}: {exc}"
            run.completed_at = _utcnow()
            _release_lease(run)
            _record_run_event(db, run=run, event_type="run_failed", phase="failed", status_after="failed", error_class=error_class, message=str(exc))
            db.commit()
        else:
            raise
    finally:
        db.close()
