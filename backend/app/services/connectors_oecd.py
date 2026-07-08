from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

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
    FetchPolicyBlockedError,
    RUN_TERMINAL_STATUSES,
    SubmissionConflictError,
)
from app.services.sciencebase_connector.executor import ExecutorGuards


CONNECTOR_KEY = "oecd_sdmx"
SOURCE_SYSTEM = "oecd_sdmx"
ALLOWED_HOST = "sdmx.oecd.org"
FORMAT = "csvfilewithlabels"
DEFAULT_MAX_ROWS = 5000
MAX_MAX_ROWS = 10000
DEFAULT_MAX_RESPONSE_BYTES = 2_000_000
MAX_RESPONSE_BYTES = 5_000_000
API_ACCESS_DATE = "2026-07-08"
ATTRIBUTION = "Organisation for Economic Co-operation and Development SDMX API"
TERMS_URL = "https://www.oecd.org/en/about/terms-conditions.html"
RESTRICTED_PARAMETER_URL = "https://www.oecd.org/en/data/insights/data-explainers/2026/03/Restricted-API-parameter.html"
PHASE0_DOC_URLS = [
    "https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html",
    "https://gitlab.algobank.oecd.org/public-documentation/dotstat-migration/-/raw/main/OECD_Data_API_documentation.pdf",
]
ANONYMOUS_TIER_BASIS = "Registration in no way impacts the application of these Terms"
OPERATOR_RESIDUALS = (
    "OECD allows a maximum of 60 data downloads per hour across runs; "
    "operator-responsible OECD 60 data downloads/hour compliance across runs and "
    "egress from non-VPN, non-anonymized sources remain outside this per-run code budget. "
    "Traffic originating from VPNs or anonymized sources is not allowed."
)
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
SUMMARY_SCHEMA_ID = "oecd_sdmx.summary.v1"
SELECTION_SCHEMA_ID = "oecd_sdmx.selection_manifest.v1"
ROWS_SCHEMA_ID = "oecd_sdmx.rows.v1"
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_.@+-]{1,128}$")
DIMENSION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.@+*-]{1,256}$")
OECD_EXECUTOR_GUARDS = ExecutorGuards(max_concurrent_runs=settings.connector_max_concurrent_runs)


class OecdSdmxSchemaValidationError(ValueError):
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
        out = default
    if minimum is not None:
        out = max(minimum, out)
    if maximum is not None:
        out = min(maximum, out)
    return out


def _coerce_float(value: Any, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        out = float(value)
    except Exception:
        out = default
    if minimum is not None:
        out = max(minimum, out)
    if maximum is not None:
        out = min(maximum, out)
    return out


def _clean_identifier(value: Any, field_name: str, default: str) -> str:
    text = _clean_string(value) or default
    if not IDENTIFIER_PATTERN.fullmatch(text):
        raise OecdSdmxSchemaValidationError(f"invalid_{field_name}")
    return text


def _clean_dimension_key(value: Any) -> str:
    text = _clean_string(value) or ".M.LI...AA...H"
    if not DIMENSION_KEY_PATTERN.fullmatch(text):
        raise OecdSdmxSchemaValidationError("invalid_dimension_key")
    return text


def _logical_query_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "agency": config.get("agency"),
        "dataflow": config.get("dataflow"),
        "dimension_key": config.get("dimension_key"),
        "start_period": config.get("start_period"),
        "end_period": config.get("end_period"),
        "lastNObservations": config.get("lastNObservations"),
    }


def _normalize_request_config(payload: dict[str, Any], submission_idempotency_key: str | None) -> dict[str, Any]:
    config = dict(payload)
    config["agency"] = _clean_identifier(config.get("agency"), "agency", "OECD.SDD.STES")
    config["dataflow"] = _clean_identifier(config.get("dataflow"), "dataflow", "DSD_STES@DF_CLI")
    config["dimension_key"] = _clean_dimension_key(config.get("dimension_key"))
    config["start_period"] = _clean_string(config.get("start_period"))
    config["end_period"] = _clean_string(config.get("end_period"))
    last_n = config.get("lastNObservations", config.get("last_n_observations"))
    config["lastNObservations"] = _coerce_int(last_n, 0, minimum=0) or None
    config["max_requests"] = _coerce_int(config.get("max_requests"), 6)
    if int(config["max_requests"]) < 1 or int(config["max_requests"]) > 30:
        raise OecdSdmxSchemaValidationError("oecd_request_budget_out_of_range")
    config["max_rows"] = _coerce_int(config.get("max_rows"), DEFAULT_MAX_ROWS, minimum=1, maximum=MAX_MAX_ROWS)
    config["max_response_bytes"] = _coerce_int(
        config.get("max_response_bytes"),
        DEFAULT_MAX_RESPONSE_BYTES,
        minimum=1,
        maximum=MAX_RESPONSE_BYTES,
    )
    config["run_mode"] = str(config.get("run_mode", "metadata_only")).strip().lower()
    if config["run_mode"] not in {"metadata_only", "dry_run"}:
        config["run_mode"] = "metadata_only"
    config["request_timeout_seconds"] = _coerce_int(config.get("request_timeout_seconds"), 30, minimum=5, maximum=120)
    config["retry_max_attempts_per_request"] = _coerce_int(config.get("retry_max_attempts_per_request"), 4, minimum=1, maximum=8)
    config["retry_base_backoff_seconds"] = _coerce_float(config.get("retry_base_backoff_seconds"), 0.4, minimum=0.0, maximum=10.0)
    config["retry_max_backoff_seconds"] = _coerce_float(config.get("retry_max_backoff_seconds"), 3.0, minimum=float(config["retry_base_backoff_seconds"]), maximum=60.0)
    config["retry_respect_retry_after"] = bool(config.get("retry_respect_retry_after", True))
    config["max_rps"] = _coerce_float(config.get("max_rps"), 2.0)
    if float(config["max_rps"]) <= 0 or float(config["max_rps"]) > 2.0:
        raise OecdSdmxSchemaValidationError("oecd_max_rps_out_of_range")
    config["report_verbosity"] = str(config.get("report_verbosity", "standard")).strip().lower()
    if config["report_verbosity"] not in {"summary", "standard", "debug"}:
        config["report_verbosity"] = "standard"
    config["client_request_id"] = _clean_string(config.get("client_request_id"))
    config["submission_idempotency_key"] = submission_idempotency_key or config["client_request_id"]
    config["allowed_hosts"] = [ALLOWED_HOST]
    config["format"] = FORMAT
    config["fetch_policy_summary"] = {
        "mode": "official_api_only",
        "surface_policy": "metadata_only",
        "external_fetch_policy": "oecd_sdmx_official_only",
        "allowed_hosts": [ALLOWED_HOST],
    }
    config["source_query_fingerprint"] = _stable_json_hash(_logical_query_from_config(config))
    return config


def _oecd_fetch_policy(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "strict_public_safe",
        "external_fetch_policy": "oecd_sdmx_official_only",
        "allowed_schemes": ["https"],
        "allowed_hosts": [ALLOWED_HOST],
        "max_redirects": int(config.get("max_redirects", settings.connector_max_redirects)),
    }


def _precheck_oecd_url(url: str, policy: dict[str, Any]) -> tuple[str | None, str | None]:
    original_resolver = _sciencebase_helpers._resolve_host_ip
    try:
        _sciencebase_helpers._resolve_host_ip = _resolve_host_ip
        return _precheck_download_url(url, policy)
    finally:
        _sciencebase_helpers._resolve_host_ip = original_resolver


def _http_status_from_exception(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    try:
        return int(getattr(response, "status_code", None))
    except Exception:
        return None


def _classify_oecd_exception(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, OecdSdmxSchemaValidationError):
        return str(exc) or "schema_validation_failed", False
    if isinstance(exc, FetchPolicyBlockedError):
        return exc.reason or "fetch_policy_blocked", False
    status_code = _http_status_from_exception(exc)
    if status_code == 413:
        return "restricted_parameter_413", False
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
        delay = self._interval - (now - self._last_call)
        if delay > 0:
            time.sleep(delay)
            self.total_sleep_seconds += delay
            now = time.monotonic()
        self._last_call = now


class OecdSdmxClient:
    def __init__(self, *, base_url: str):
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != ALLOWED_HOST:
            raise OecdSdmxSchemaValidationError("inadmissible_oecd_sdmx_base_url")
        if parsed.path.rstrip("/") != "/public/rest/data":
            raise OecdSdmxSchemaValidationError("inadmissible_oecd_sdmx_base_url")
        if parsed.query or parsed.fragment:
            raise OecdSdmxSchemaValidationError("inadmissible_oecd_sdmx_base_url")
        self.session = requests.Session()

    @property
    def auth_mode(self) -> str:
        return "anonymous"

    def fetch_csv(
        self,
        *,
        agency: str,
        dataflow: str,
        dimension_key: str,
        start_period: str | None,
        end_period: str | None,
        last_n_observations: int | None,
        timeout_seconds: int,
        max_redirects: int,
        max_requests_budget: int,
        retry_max_attempts_per_request: int,
        retry_base_backoff_seconds: float,
        retry_max_backoff_seconds: float,
        retry_respect_retry_after: bool,
        rate_limiter: _RateLimiter,
        retry_counters: dict[str, Any],
        format: str = FORMAT,
    ) -> str:
        if format != FORMAT:
            raise OecdSdmxSchemaValidationError("unsupported_oecd_sdmx_format")
        url = f"{self.base_url}/{agency},{dataflow}/{dimension_key}"
        params: dict[str, Any] = {"dimensionAtObservation": "AllDimensions", "format": FORMAT}
        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period
        if last_n_observations is not None:
            params["lastNObservations"] = int(last_n_observations)
        last_exc: Exception | None = None
        for attempt in range(1, retry_max_attempts_per_request + 1):
            if int(retry_counters.get("requests_total", 0)) >= max_requests_budget:
                raise OecdSdmxSchemaValidationError("request_budget_exhausted")
            try:
                response = self._get_with_validated_redirects(
                    url=url,
                    params=params,
                    timeout_seconds=timeout_seconds,
                    max_redirects=max_redirects,
                    max_requests_budget=max_requests_budget,
                    max_response_bytes=int(retry_counters.get("max_response_bytes", DEFAULT_MAX_RESPONSE_BYTES)),
                    rate_limiter=rate_limiter,
                    retry_counters=retry_counters,
                )
                final_host = (urlparse(str(response.url)).hostname or "").lower()
                if final_host != ALLOWED_HOST:
                    raise FetchPolicyBlockedError("host_not_allowed")
                if int(response.status_code) == 413:
                    retry_counters["last_error_class"] = "restricted_parameter_413"
                    raise OecdSdmxSchemaValidationError("restricted_parameter_413")
                if response.status_code in RETRYABLE_HTTP_STATUSES and attempt < retry_max_attempts_per_request:
                    retry_counters["retries_total"] = int(retry_counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    if retry_respect_retry_after:
                        try:
                            wait_seconds = min(retry_max_backoff_seconds, max(wait_seconds, float(response.headers.get("Retry-After") or "")))
                        except Exception:
                            pass
                    time.sleep(wait_seconds)
                    retry_counters["retry_sleep_seconds"] = float(retry_counters.get("retry_sleep_seconds", 0.0)) + wait_seconds
                    continue
                response.raise_for_status()
                if len(getattr(response, "content", b"") or b"") > int(retry_counters.get("max_response_bytes", DEFAULT_MAX_RESPONSE_BYTES)):
                    raise OecdSdmxSchemaValidationError("response_too_large")
                return response.text
            except Exception as exc:
                last_exc = exc
                error_class, retryable = _classify_oecd_exception(exc)
                retry_counters["last_error_class"] = error_class
                if retryable and attempt < retry_max_attempts_per_request:
                    retry_counters["retries_total"] = int(retry_counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    time.sleep(wait_seconds)
                    retry_counters["retry_sleep_seconds"] = float(retry_counters.get("retry_sleep_seconds", 0.0)) + wait_seconds
                    continue
                raise
        if last_exc:
            raise last_exc
        raise OecdSdmxSchemaValidationError("request_failed")

    def _get_with_validated_redirects(
        self,
        *,
        url: str,
        params: dict[str, Any],
        timeout_seconds: int,
        max_redirects: int,
        max_requests_budget: int,
        max_response_bytes: int,
        rate_limiter: _RateLimiter,
        retry_counters: dict[str, Any],
    ) -> requests.Response:
        policy = _oecd_fetch_policy({"max_redirects": max_redirects})
        current_url = url
        current_params: dict[str, Any] | None = params
        redirects_followed = 0
        while True:
            if int(retry_counters.get("requests_total", 0)) >= max_requests_budget:
                raise OecdSdmxSchemaValidationError("request_budget_exhausted")
            resolved_ip, reason = _precheck_oecd_url(current_url, policy)
            retry_counters["resolved_ip"] = resolved_ip
            if reason:
                raise FetchPolicyBlockedError(reason)
            rate_limiter.wait()
            retry_counters["requests_total"] = int(retry_counters.get("requests_total", 0)) + 1
            response = self.session.get(current_url, params=current_params, timeout=timeout_seconds, allow_redirects=False)
            if len(getattr(response, "content", b"") or b"") > max_response_bytes:
                raise OecdSdmxSchemaValidationError("response_too_large")
            if int(getattr(response, "status_code", 0)) not in {301, 302, 303, 307, 308}:
                return response
            if redirects_followed >= max_redirects:
                raise FetchPolicyBlockedError("redirect_policy_violation")
            location = str(response.headers.get("Location") or "").strip()
            if not location:
                raise FetchPolicyBlockedError("redirect_policy_violation")
            next_url = urljoin(str(getattr(response, "url", current_url) or current_url), location)
            _resolved_ip, next_reason = _precheck_oecd_url(next_url, policy)
            if next_reason:
                raise FetchPolicyBlockedError(next_reason)
            if (urlparse(next_url).hostname or "").lower() != ALLOWED_HOST:
                raise FetchPolicyBlockedError("host_not_allowed")
            current_url = next_url
            current_params = None
            redirects_followed += 1
            retry_counters["redirects_total"] = int(retry_counters.get("redirects_total", 0)) + 1


def get_oecd_client(config: dict[str, Any]) -> OecdSdmxClient:
    return OecdSdmxClient(base_url=settings.oecd_sdmx_api_base_url)


def _client_auth_mode(client: Any) -> str:
    return str(getattr(client, "auth_mode", "anonymous") or "anonymous")


def _common_request_kwargs(config: dict[str, Any], rate_limiter: _RateLimiter, retry_counters: dict[str, Any]) -> dict[str, Any]:
    retry_counters["max_response_bytes"] = int(config.get("max_response_bytes", DEFAULT_MAX_RESPONSE_BYTES))
    return {
        "timeout_seconds": int(config.get("request_timeout_seconds", 30)),
        "max_redirects": int(config.get("max_redirects", settings.connector_max_redirects)),
        "max_requests_budget": int(config.get("max_requests", 6)),
        "retry_max_attempts_per_request": int(config.get("retry_max_attempts_per_request", 4)),
        "retry_base_backoff_seconds": float(config.get("retry_base_backoff_seconds", 0.4)),
        "retry_max_backoff_seconds": float(config.get("retry_max_backoff_seconds", 3.0)),
        "retry_respect_retry_after": bool(config.get("retry_respect_retry_after", True)),
        "rate_limiter": rate_limiter,
        "retry_counters": retry_counters,
        "format": FORMAT,
    }


def _summary_report_path(run_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_oecd_sdmx_summary_v1.json"


def _selection_manifest_path(run_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_oecd_sdmx_selection_manifest_v1.json"


def submit_oecd_sdmx_run(db: Session, *, payload: dict[str, Any], idempotency_key: str | None) -> tuple[ConnectorRun, bool]:
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
        source_mode="public_api",
        status="pending",
        request_config_json=config,
        source_query_fingerprint=str(config.get("source_query_fingerprint") or ""),
        request_fingerprint=request_fingerprint,
        effective_search_params_json={},
        effective_filters_json=[],
        effective_sort="sdmx_time_period",
        effective_order="desc",
        effective_page_size=1,
        submission_idempotency_key=submitted_key,
        adapter_dialect="oecd_sdmx_csv_v1",
        api_generation="sdmx_rest_v1",
        sciencebase_normalization_version="n/a",
        submitted_at=now,
    )
    db.add(run)
    db.flush()
    if submitted_key:
        db.add(ConnectorRunSubmission(connector_key=CONNECTOR_KEY, submission_idempotency_key=submitted_key, request_fingerprint=request_fingerprint, connector_run_id=run.connector_run_id, expires_at=now + timedelta(hours=settings.connector_submission_ttl_hours)))
    db.add(ConnectorPolicySnapshot(connector_run_id=run.connector_run_id, policy_json=config, retry_matrix_json={"retryable_http_statuses": sorted(RETRYABLE_HTTP_STATUSES), "terminal_http_statuses": [413], "retry_max_attempts_per_request": int(config.get("retry_max_attempts_per_request", 4)), "max_requests": int(config.get("max_requests", 6))}))
    _record_run_event(db, run=run, event_type="run_submitted", phase="planning", status_after="pending", metrics_json={"connector_key": CONNECTOR_KEY, "auth_mode": "anonymous"})
    db.commit()
    db.refresh(run)
    return run, True


def _request_accounting_from_run(run: ConnectorRun) -> dict[str, Any]:
    stored = dict((run.query_plan_json or {}).get("oecd_sdmx_request_accounting") or {})
    return {
        "requests_total": int(stored.get("requests_total", 0)),
        "retries_total": int(stored.get("retries_total", 0)),
        "retry_sleep_seconds": float(stored.get("retry_sleep_seconds", 0.0)),
        "last_error_class": stored.get("last_error_class"),
        "resolved_ip": stored.get("resolved_ip"),
    }


def _record_request_accounting(run: ConnectorRun, retry_counters: dict[str, Any]) -> None:
    plan = dict(run.query_plan_json or {})
    plan["oecd_sdmx_request_accounting"] = {
        "requests_total": int(retry_counters.get("requests_total", 0)),
        "retries_total": int(retry_counters.get("retries_total", 0)),
        "retry_sleep_seconds": float(retry_counters.get("retry_sleep_seconds", 0.0)),
        "last_error_class": retry_counters.get("last_error_class"),
        "resolved_ip": retry_counters.get("resolved_ip"),
    }
    run.query_plan_json = plan


def _rows_artifact_path(run_id: str, target_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_{target_id}_oecd_sdmx_rows_v1.json"


def _write_rows_artifact(run: ConnectorRun, target: ConnectorRunTarget, rows: list[dict[str, Any]]) -> str:
    return _write_json(_rows_artifact_path(run.connector_run_id, target.connector_run_target_id), {"schema_id": ROWS_SCHEMA_ID, "schema_version": 1, "connector_run_id": run.connector_run_id, "target_id": target.connector_run_target_id, "rows": rows})


def _rows_from_ref(ref: str | None) -> list[dict[str, Any]]:
    if not ref:
        return []
    try:
        payload = json.loads(Path(ref).read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = payload.get("rows") if isinstance(payload, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _rows_for_target(target: ConnectorRunTarget, rows_by_target: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = rows_by_target.get(target.connector_run_target_id)
    if rows is not None:
        return rows
    source_ref = dict(target.source_reference_json or {})
    return _rows_from_ref(source_ref.get("row_artifact_ref"))


def _query_url(config: dict[str, Any]) -> str:
    params: dict[str, Any] = {"dimensionAtObservation": "AllDimensions", "format": FORMAT}
    if config.get("start_period"):
        params["startPeriod"] = config["start_period"]
    if config.get("end_period"):
        params["endPeriod"] = config["end_period"]
    if config.get("lastNObservations") is not None:
        params["lastNObservations"] = int(config["lastNObservations"])
    return (
        f"{settings.oecd_sdmx_api_base_url.rstrip('/')}/{config['agency']},{config['dataflow']}/{config['dimension_key']}"
        f"?{urlencode(params)}"
    )


def _target_for_request(*, run: ConnectorRun, config: dict[str, Any]) -> ConnectorRunTarget:
    now = _utcnow()
    artifact_key = f"oecd_sdmx:{config['agency']}:{config['dataflow']}:{_stable_json_hash(_logical_query_from_config(config))[:16]}"
    target_status = "dry_run_skipped" if str(config.get("run_mode", "metadata_only")) == "dry_run" else "selected"
    source_ref = {
        "source_system": SOURCE_SYSTEM,
        "agency": config.get("agency"),
        "dataflow": config.get("dataflow"),
        "dimension_key": config.get("dimension_key"),
        "start_period": config.get("start_period"),
        "end_period": config.get("end_period"),
        "lastNObservations": config.get("lastNObservations"),
        "runtime_host": ALLOWED_HOST,
        "runtime_base_url": settings.oecd_sdmx_api_base_url,
        "format": FORMAT,
        "phase0_doc_urls": PHASE0_DOC_URLS,
        "api_access_date": API_ACCESS_DATE,
        "terms_url": TERMS_URL,
        "restricted_parameter_url": RESTRICTED_PARAMETER_URL,
        "anonymous_tier_basis": ANONYMOUS_TIER_BASIS,
        "operator_residuals": OPERATOR_RESIDUALS,
        "code_enforced_caps": {"max_requests_per_run": int(config.get("max_requests", 6)), "max_rps": 2.0},
    }
    return ConnectorRunTarget(
        connector_run_id=run.connector_run_id,
        ordinal=1,
        stable_release_key=artifact_key,
        stable_release_identifier=artifact_key,
        identifiers_json=[{"type": "oecd_agency", "value": str(config.get("agency"))}, {"type": "oecd_dataflow", "value": str(config.get("dataflow"))}],
        sciencebase_item_id=f"{config.get('agency')}:{config.get('dataflow')}",
        sciencebase_item_url=_query_url(config),
        sciencebase_file_name=f"OECD SDMX {config.get('dataflow')}",
        sciencebase_download_uri=_query_url(config),
        artifact_surface="sdmx_csv_observations",
        selection_source=SOURCE_SYSTEM,
        selection_scope="metadata_query",
        selection_match_basis="sdmx_dataflow_dimension_key",
        artifact_locator_type="api_url",
        source_artifact_key=artifact_key,
        canonical_artifact_key=artifact_key,
        source_reference_json=source_ref,
        permission_snapshot_json={"access": "public", "auth_mode": "anonymous", "attribution": ATTRIBUTION, "terms_url": TERMS_URL},
        access_level_summary="public_api",
        public_read_confirmed=True,
        status=target_status,
        retry_eligible=False,
        discovered_at=now,
        selected_at=now,
        recommended_at=now if target_status == "dry_run_skipped" else None,
        last_stage_transition_at=now,
        operator_reason_code="dry_run_oecd_sdmx_query_selected" if target_status == "dry_run_skipped" else "oecd_sdmx_query_selected",
    )


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace(",", ""))
    except Exception as exc:
        raise OecdSdmxSchemaValidationError("schema_validation_failed") from exc


def _parse_sdmx_csv(payload: str, *, max_rows: int) -> tuple[list[dict[str, Any]], int]:
    text = payload.strip()
    if not text:
        raise OecdSdmxSchemaValidationError("empty_dataset")
    try:
        reader = csv.DictReader(text.splitlines())
        headers = [str(name or "").strip() for name in (reader.fieldnames or [])]
        header_set = set(headers)
        if not ({"DATAFLOW", "TIME_PERIOD", "OBS_VALUE"} <= header_set or {"STRUCTURE", "TIME_PERIOD", "OBS_VALUE"} <= header_set):
            raise OecdSdmxSchemaValidationError("schema_validation_failed")
        rows: list[dict[str, Any]] = []
        source_row_count = 0
        for raw in reader:
            if not any(_clean_string(value) for value in raw.values()):
                continue
            source_row_count += 1
            obs_raw = _clean_string(raw.get("OBS_VALUE"))
            if obs_raw is None:
                continue
            dataflow = _clean_string(raw.get("DATAFLOW") or raw.get("STRUCTURE"))
            time_period = _clean_string(raw.get("TIME_PERIOD"))
            if not dataflow or not time_period:
                raise OecdSdmxSchemaValidationError("schema_validation_failed")
            if len(rows) >= max_rows:
                raise OecdSdmxSchemaValidationError("row_limit_exceeded")
            rows.append(
                {
                    "dataflow": dataflow,
                    "time_period": time_period,
                    "obs_value": _parse_float(obs_raw),
                    "obs_value_text": obs_raw,
                    "ref_area": _clean_string(raw.get("REF_AREA")),
                    "frequency": _clean_string(raw.get("FREQ")),
                    "measure": _clean_string(raw.get("MEASURE")),
                    "adjustment": _clean_string(raw.get("ADJUSTMENT")),
                    "unit_measure": _clean_string(raw.get("UNIT_MEASURE")),
                    "unit_mult": _clean_string(raw.get("UNIT_MULT")),
                    "obs_status": _clean_string(raw.get("OBS_STATUS")),
                    "reference_area": _clean_string(raw.get("Reference area")),
                }
            )
    except OecdSdmxSchemaValidationError:
        raise
    except Exception as exc:
        raise OecdSdmxSchemaValidationError("schema_validation_failed") from exc
    if source_row_count == 0:
        raise OecdSdmxSchemaValidationError("empty_dataset")
    if not rows:
        raise OecdSdmxSchemaValidationError("empty_after_normalization")
    return rows, source_row_count


def _resolve_dataset_id(db: Session, logical_dataset_key: str) -> str | None:
    existing = db.query(DatasetExternalIdentity).filter(and_(DatasetExternalIdentity.source_system == SOURCE_SYSTEM, DatasetExternalIdentity.logical_dataset_key == logical_dataset_key)).first()
    return existing.dataset_id if existing else None


def _persist_dataset_identity(db: Session, dataset_id: str, logical_dataset_key: str, metadata_json: dict[str, Any]) -> None:
    existing = db.query(DatasetExternalIdentity).filter(and_(DatasetExternalIdentity.source_system == SOURCE_SYSTEM, DatasetExternalIdentity.logical_dataset_key == logical_dataset_key)).first()
    if existing:
        return
    db.add(DatasetExternalIdentity(dataset_id=dataset_id, source_system=SOURCE_SYSTEM, logical_dataset_key=logical_dataset_key, metadata_json=metadata_json))
    db.flush()


def _ensure_metadata_provenance(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    rows: list[dict[str, Any]],
    source_row_count: int,
    retry_counters: dict[str, Any],
) -> None:
    if target.status != "recommended":
        return
    logical_dataset_key = target.stable_release_key or f"oecd_sdmx:{target.connector_run_target_id}"
    if not target.dataset_id:
        dataset_id = _resolve_dataset_id(db, logical_dataset_key)
        if not dataset_id:
            dataset = Dataset(name=f"OECD SDMX {target.sciencebase_item_id or target.ordinal}", description=f"{ATTRIBUTION}; rows retained only in connector reports", domain_pack="public_connectors", frequency_hint="mixed", time_column="time_period")
            db.add(dataset)
            db.flush()
            dataset_id = dataset.dataset_id
            _persist_dataset_identity(db, dataset_id=dataset_id, logical_dataset_key=logical_dataset_key, metadata_json={"source_system": SOURCE_SYSTEM, "stable_release_key": target.stable_release_key, "source_artifact_key": target.source_artifact_key, "identifiers": target.identifiers_json or []})
        target.dataset_id = dataset_id
    if not target.dataset_version_id:
        dropped_row_count = max(source_row_count - len(rows), 0)
        content_payload = {"source_system": SOURCE_SYSTEM, "source_artifact_key": target.source_artifact_key, "row_count": len(rows), "source_row_count": source_row_count, "dropped_row_count": dropped_row_count, "row_hashes": [_stable_json_hash({"row": row}) for row in rows]}
        version = DatasetVersion(dataset_id=target.dataset_id, version_label=f"oecd_sdmx_{str(target.sciencebase_item_id or target.ordinal).replace(':', '_')[:80]}_{run.connector_run_id[:8]}", version_type="source_metadata", status="ready", storage_ref=target.source_artifact_key, row_count=len(rows), content_hash=_stable_json_hash(content_payload), source_row_count=source_row_count, dropped_row_count=dropped_row_count, notes=f"connector_run_id={run.connector_run_id}; source_artifact_key={target.source_artifact_key}")
        db.add(version)
        db.flush()
        target.dataset_version_id = version.dataset_version_id
    existing = db.query(DatasetSourceProvenance).filter(and_(DatasetSourceProvenance.dataset_version_id == target.dataset_version_id, DatasetSourceProvenance.connector_run_id == run.connector_run_id, DatasetSourceProvenance.source_system == SOURCE_SYSTEM)).first()
    if existing:
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
            fetch_policy_mode="oecd_sdmx_official_only",
            retrieved_http_json={"api_base_url": settings.oecd_sdmx_api_base_url, "allowed_hosts": [ALLOWED_HOST], "format": FORMAT, "phase0_doc_urls": PHASE0_DOC_URLS, "api_access_date": API_ACCESS_DATE, "terms_url": TERMS_URL, "restricted_parameter_url": RESTRICTED_PARAMETER_URL, "anonymous_tier_basis": ANONYMOUS_TIER_BASIS, "operator_residuals": OPERATOR_RESIDUALS, "requests_total": int(retry_counters.get("requests_total", 0)), "resolved_ip": retry_counters.get("resolved_ip"), "source_row_count": source_row_count, "normalized_row_count": len(rows), "dropped_row_count": max(source_row_count - len(rows), 0)},
            discovered_at=target.discovered_at,
            downloaded_at=target.downloaded_at,
        )
    )
    db.flush()


def _process_target(db: Session, *, run: ConnectorRun, target: ConnectorRunTarget, client: Any, config: dict[str, Any], rate_limiter: _RateLimiter, retry_counters: dict[str, Any]) -> list[dict[str, Any]]:
    if target.status == "dry_run_skipped":
        return []
    target.attempt_count = int(target.attempt_count or 0) + 1
    target.last_attempt_at = _utcnow()
    target.last_stage_transition_at = _utcnow()
    db.commit()
    try:
        if int(retry_counters.get("requests_total", 0)) >= int(config.get("max_requests", 6)):
            raise OecdSdmxSchemaValidationError("request_budget_exhausted")
        payload = client.fetch_csv(agency=str(config.get("agency")), dataflow=str(config.get("dataflow")), dimension_key=str(config.get("dimension_key")), start_period=config.get("start_period"), end_period=config.get("end_period"), last_n_observations=config.get("lastNObservations"), **_common_request_kwargs(config, rate_limiter, retry_counters))
        rows, source_row_count = _parse_sdmx_csv(payload, max_rows=int(config.get("max_rows", DEFAULT_MAX_ROWS)))
        row_artifact_ref = _write_rows_artifact(run, target, rows)
        target.status = "recommended"
        target.recommended_at = _utcnow()
        target.downloaded_at = _utcnow()
        target.error_stage = None
        target.error_message = None
        target.last_error_class = None
        target.retry_eligible = False
        target.operator_reason_code = "observations_recorded"
        target.last_stage_transition_at = _utcnow()
        source_ref = dict(target.source_reference_json or {})
        source_ref.update({"source_row_count": source_row_count, "normalized_row_count": len(rows), "format": FORMAT, "row_artifact_ref": row_artifact_ref})
        target.source_reference_json = source_ref
        _record_request_accounting(run, retry_counters)
        _ensure_metadata_provenance(db, run=run, target=target, rows=rows, source_row_count=source_row_count, retry_counters=retry_counters)
        _record_run_event(db, run=run, target=target, event_type="target_rows_recorded", phase="selection", status_after="recommended", reason_code="observations_recorded")
        db.commit()
        return rows
    except Exception as exc:
        error_class, retryable = _classify_oecd_exception(exc)
        blocked = isinstance(exc, FetchPolicyBlockedError)
        target.status = "blocked_by_fetch_policy" if blocked else "download_failed"
        target.error_stage = "requesting" if blocked else "metadata_validation"
        target.error_message = str(exc)
        target.last_error_class = error_class
        target.retry_eligible = retryable
        target.last_stage_transition_at = _utcnow()
        target.operator_reason_code = error_class
        if blocked:
            target.blocked_reason = error_class
        _record_request_accounting(run, retry_counters)
        _record_run_event(db, run=run, target=target, event_type="target_blocked_by_fetch_policy" if blocked else "target_failed_closed", phase="selection", status_after=target.status, error_class=error_class, message=str(exc), reason_code=error_class)
        db.commit()
        return []


def _write_selection_manifest(db: Session, *, run: ConnectorRun, rows_by_target: dict[str, list[dict[str, Any]]]) -> None:
    targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).order_by(ConnectorRunTarget.ordinal.asc()).all()
    payloads = [{"target_id": t.connector_run_target_id, "ordinal": int(t.ordinal or 0), "dataflow": (t.source_reference_json or {}).get("dataflow"), "dimension_key": (t.source_reference_json or {}).get("dimension_key"), "status": t.status, "last_error_class": t.last_error_class, "source_artifact_key": t.source_artifact_key, "rows": _rows_for_target(t, rows_by_target)} for t in targets]
    run.page_count_completed = len([item for item in payloads if item["status"] in {"recommended", "dry_run_skipped"}])
    run.last_offset_committed = len(payloads)
    run.search_exhaustion_reason = "query_processed" if run.page_count_completed else "error"
    run.selection_manifest_ref = _write_json(_selection_manifest_path(run.connector_run_id), {"schema_id": SELECTION_SCHEMA_ID, "schema_version": 1, "connector_run_id": run.connector_run_id, "targets": payloads})
    db.commit()


def _write_summary(db: Session, *, run: ConnectorRun, config: dict[str, Any], client: Any, retry_counters: dict[str, Any], rows_by_target: dict[str, list[dict[str, Any]]]) -> None:
    targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).order_by(ConnectorRunTarget.ordinal.asc()).all()
    rows = [row for target in targets for row in _rows_for_target(target, rows_by_target)]
    summary = {
        "schema_id": SUMMARY_SCHEMA_ID,
        "schema_version": 1,
        "generated_at_utc": _utcnow().isoformat(),
        "connector_run_id": run.connector_run_id,
        "connector_key": run.connector_key,
        "status": run.status,
        "api_base_url": settings.oecd_sdmx_api_base_url,
        "runtime_host": ALLOWED_HOST,
        "auth_mode": _client_auth_mode(client),
        "request": {**_logical_query_from_config(config), "run_mode": str(config.get("run_mode", "metadata_only")), "format": FORMAT},
        "phase0_doc_urls": PHASE0_DOC_URLS,
        "api_access_date": API_ACCESS_DATE,
        "attribution": ATTRIBUTION,
        "terms_url": TERMS_URL,
        "restricted_parameter_url": RESTRICTED_PARAMETER_URL,
        "anonymous_tier_basis": ANONYMOUS_TIER_BASIS,
        "operator_residuals": OPERATOR_RESIDUALS,
        "rows": rows,
        "totals": {"discovered_count": int(run.discovered_count or 0), "recommended_count": int(run.recommended_count or 0), "failed_count": int(run.failed_count or 0), "blocked_by_fetch_policy_count": int(run.blocked_by_fetch_policy_count or 0), "row_count": len(rows)},
        "targets": [{"ordinal": int(t.ordinal or 0), "dataflow": (t.source_reference_json or {}).get("dataflow"), "dimension_key": (t.source_reference_json or {}).get("dimension_key"), "status": t.status, "last_error_class": t.last_error_class, "source_artifact_key": t.source_artifact_key} for t in targets],
        "retry_summary": {"requests_total": int(retry_counters.get("requests_total", 0)), "retries_total": int(retry_counters.get("retries_total", 0)), "retry_sleep_seconds": round(float(retry_counters.get("retry_sleep_seconds", 0.0)), 4), "rate_limiter_sleep_seconds": round(float(retry_counters.get("rate_limiter_sleep_seconds", 0.0)), 4), "last_error_class": retry_counters.get("last_error_class")},
    }
    summary_ref = _write_json(_summary_report_path(run.connector_run_id), summary)
    run.query_plan_json = {**(run.query_plan_json or {}), "connector_report_refs": {"oecd_sdmx_summary": summary_ref}}
    db.commit()


def _target_needs_processing(target: ConnectorRunTarget) -> bool:
    return target.status == "selected" or (target.status == "download_failed" and bool(target.retry_eligible))


def execute_oecd_sdmx_run(connector_run_id: str) -> None:
    db = SessionLocal()
    try:
        OECD_EXECUTOR_GUARDS.acquire_run_slot()
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
            client = get_oecd_client(config)
            run.effective_search_params_json = {"base_url": settings.oecd_sdmx_api_base_url, "runtime_host": ALLOWED_HOST, "auth_mode": _client_auth_mode(client), "logical_query": _logical_query_from_config(config), "format": FORMAT}
            run.effective_filters_json = [{"field": key, "value": value} for key, value in _logical_query_from_config(config).items()]
            run.effective_sort = "sdmx_time_period"
            run.effective_order = "desc"
            run.effective_page_size = 1
            db.commit()
            retry_counters: dict[str, Any] = _request_accounting_from_run(run)
            rows_by_target: dict[str, list[dict[str, Any]]] = {}
            rate_limiter = _RateLimiter(float(config.get("max_rps", 2.0)))
            targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).order_by(ConnectorRunTarget.ordinal.asc()).all()
            processed_any = False
            cancelled = False
            if not targets:
                if _cooperate_with_cancel_request(db, run, phase="discovery"):
                    cancelled = True
                else:
                    target = _target_for_request(run=run, config=config)
                    db.add(target)
                    db.flush()
                    _record_run_event(db, run=run, target=target, event_type="target_created", phase="selection", status_after=target.status, reason_code=target.operator_reason_code)
                    db.commit()
                    targets = [target]
            if not cancelled:
                for target in targets:
                    if not _target_needs_processing(target):
                        continue
                    if _cooperate_with_cancel_request(db, run, phase="selection"):
                        cancelled = True
                        break
                    rows = _process_target(db, run=run, target=target, client=client, config=config, rate_limiter=rate_limiter, retry_counters=retry_counters)
                    processed_any = True
                    if rows:
                        rows_by_target[target.connector_run_target_id] = rows
                    _renew_lease(db, run)
            if processed_any or not run.selection_manifest_ref:
                _write_selection_manifest(db, run=run, rows_by_target=rows_by_target)
            retry_counters["rate_limiter_sleep_seconds"] = rate_limiter.total_sleep_seconds
            _record_request_accounting(run, retry_counters)
            _finalize_run(db, run)
            _write_summary(db, run=run, config=config, client=client, retry_counters=retry_counters, rows_by_target=rows_by_target)
            _record_run_event(db, run=run, event_type="run_finalized", phase="finalizing", status_after=run.status, metrics_json={"connector_key": CONNECTOR_KEY}, commit=True)
        finally:
            OECD_EXECUTOR_GUARDS.release_run_slot()
    except Exception as exc:
        run = db.get(ConnectorRun, connector_run_id)
        if run:
            error_class, _retryable = _classify_oecd_exception(exc)
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
