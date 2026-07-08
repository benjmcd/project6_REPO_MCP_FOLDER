from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import timedelta
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
    FetchPolicyBlockedError,
    RUN_TERMINAL_STATUSES,
    SubmissionConflictError,
)
from app.services.sciencebase_connector.executor import ExecutorGuards


CONNECTOR_KEY = "bls_v1"
SOURCE_SYSTEM = "bls_v1"
ALLOWED_HOST = "api.bls.gov"
BLS_SIGNATURE_URL = "https://www.bls.gov/developers/api_signature.htm"
BLS_TERMS_URL = "https://www.bls.gov/developers/termsOfService.htm"
PHASE0_DOC_URLS = [BLS_SIGNATURE_URL, BLS_TERMS_URL]
API_ACCESS_DATE = "2026-07-08"
ATTRIBUTION = "U.S. Bureau of Labor Statistics Public Data API v1"
BLS_NO_VOUCH_DISCLAIMER = "BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov."
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
SUMMARY_SCHEMA_ID = "bls_v1.summary.v1"
SELECTION_SCHEMA_ID = "bls_v1.selection_manifest.v1"
ROWS_SCHEMA_ID = "bls_v1.rows.v1"
BLS_SERIES_ID_PATTERN = re.compile(r"^[A-Z0-9]{1,64}$")
BLS_EXECUTOR_GUARDS = ExecutorGuards(max_concurrent_runs=settings.connector_max_concurrent_runs)


class BlsSchemaValidationError(ValueError):
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


def _clean_series_ids(value: Any) -> list[str]:
    raw = value if isinstance(value, list) else ([value] if value not in (None, "") else ["LAUCN040010000000005"])
    out = []
    for item in raw:
        text = _clean_string(item)
        if text:
            out.append(text.upper())
    deduped = list(dict.fromkeys(out))
    if not deduped:
        raise BlsSchemaValidationError("bls_series_ids_required")
    if len(deduped) > 25:
        raise BlsSchemaValidationError("bls_series_limit_exceeded")
    if any(not BLS_SERIES_ID_PATTERN.fullmatch(series_id) for series_id in deduped):
        raise BlsSchemaValidationError("bls_series_id_invalid")
    return deduped


def _optional_year(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        year = int(value)
    except Exception as exc:
        raise BlsSchemaValidationError(f"bls_{field_name}_invalid") from exc
    if year < 1900 or year > 9999:
        raise BlsSchemaValidationError(f"bls_{field_name}_out_of_range")
    return year


def _logical_query_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "series_ids": list(config.get("series_ids") or []),
        "start_year": config.get("start_year"),
        "end_year": config.get("end_year"),
        "max_requests": int(config.get("max_requests", 10)),
    }


def _normalize_request_config(payload: dict[str, Any], submission_idempotency_key: str | None) -> dict[str, Any]:
    config = dict(payload)
    config["series_ids"] = _clean_series_ids(config.get("series_ids"))
    config["start_year"] = _optional_year(config.get("start_year"), "start_year")
    config["end_year"] = _optional_year(config.get("end_year"), "end_year")
    if (config["start_year"] is None) != (config["end_year"] is None):
        raise BlsSchemaValidationError("bls_year_range_requires_start_and_end")
    if config["start_year"] is not None:
        if int(config["start_year"]) > int(config["end_year"]):
            raise BlsSchemaValidationError("bls_start_year_after_end_year")
        if int(config["end_year"]) - int(config["start_year"]) > 9:
            raise BlsSchemaValidationError("bls_year_span_exceeds_10")
    config["max_requests"] = _coerce_int(config.get("max_requests"), 10)
    if int(config["max_requests"]) < 1 or int(config["max_requests"]) > 25:
        raise BlsSchemaValidationError("bls_request_budget_out_of_range")
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
        raise BlsSchemaValidationError("bls_max_rps_out_of_range")
    config["report_verbosity"] = str(config.get("report_verbosity", "standard")).strip().lower()
    if config["report_verbosity"] not in {"summary", "standard", "debug"}:
        config["report_verbosity"] = "standard"
    config["client_request_id"] = _clean_string(config.get("client_request_id"))
    config["submission_idempotency_key"] = submission_idempotency_key or config["client_request_id"]
    config["allowed_hosts"] = [ALLOWED_HOST]
    config["fetch_policy_summary"] = {"mode": "official_api_only", "surface_policy": "metadata_only", "external_fetch_policy": "bls_v1_official_only", "allowed_hosts": [ALLOWED_HOST]}
    config["source_query_fingerprint"] = _stable_json_hash(_logical_query_from_config(config))
    return config


def _bls_fetch_policy(config: dict[str, Any]) -> dict[str, Any]:
    return {"mode": "strict_public_safe", "external_fetch_policy": "bls_v1_official_only", "allowed_schemes": ["https"], "allowed_hosts": [ALLOWED_HOST], "max_redirects": int(config.get("max_redirects", settings.connector_max_redirects))}


def _precheck_bls_url(url: str, policy: dict[str, Any]) -> tuple[str | None, str | None]:
    original_resolver = _sciencebase_helpers._resolve_host_ip
    try:
        _sciencebase_helpers._resolve_host_ip = _resolve_host_ip
        return _precheck_download_url(url, policy)
    finally:
        _sciencebase_helpers._resolve_host_ip = original_resolver


def _classify_bls_exception(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, BlsSchemaValidationError):
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


class BlsV1Client:
    def __init__(self, *, base_url: str):
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != ALLOWED_HOST:
            raise BlsSchemaValidationError("inadmissible_bls_base_url")
        if parsed.path.rstrip("/") != "/publicAPI/v1/timeseries/data":
            raise BlsSchemaValidationError("inadmissible_bls_base_url")
        if parsed.query or parsed.fragment:
            raise BlsSchemaValidationError("inadmissible_bls_base_url")
        self.session = requests.Session()

    @property
    def auth_mode(self) -> str:
        return "anonymous"

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        json_body: dict[str, Any] | None,
        timeout_seconds: int,
        max_redirects: int,
        max_requests_budget: int,
        retry_max_attempts_per_request: int,
        retry_base_backoff_seconds: float,
        retry_max_backoff_seconds: float,
        retry_respect_retry_after: bool,
        rate_limiter: _RateLimiter,
        retry_counters: dict[str, Any],
    ) -> Any:
        url = f"{self.base_url}{path}"
        resolved_ip, reason = _precheck_bls_url(url, _bls_fetch_policy({"max_redirects": max_redirects}))
        if reason:
            raise FetchPolicyBlockedError(reason)
        last_exc: Exception | None = None
        for attempt in range(1, retry_max_attempts_per_request + 1):
            if int(retry_counters.get("requests_total", 0)) >= max_requests_budget:
                raise BlsSchemaValidationError("request_budget_exhausted")
            rate_limiter.wait()
            retry_counters["requests_total"] = int(retry_counters.get("requests_total", 0)) + 1
            try:
                if method == "GET":
                    response = self.session.get(url, timeout=timeout_seconds, allow_redirects=True)
                    if len(response.history) > max_redirects:
                        raise FetchPolicyBlockedError("redirect_policy_violation")
                    final_host = (urlparse(str(response.url)).hostname or "").lower()
                    if final_host != ALLOWED_HOST:
                        raise FetchPolicyBlockedError("host_not_allowed")
                elif method == "POST":
                    response = self.session.post(url, json=json_body or {}, timeout=timeout_seconds, allow_redirects=False)
                    if 300 <= int(response.status_code) < 400:
                        raise FetchPolicyBlockedError("redirect_policy_violation")
                    final_host = (urlparse(str(response.url or url)).hostname or "").lower()
                    if final_host != ALLOWED_HOST:
                        raise FetchPolicyBlockedError("host_not_allowed")
                else:
                    raise BlsSchemaValidationError("unsupported_bls_http_method")
                if response.status_code in RETRYABLE_HTTP_STATUSES and attempt < retry_max_attempts_per_request:
                    retry_counters["retries_total"] = int(retry_counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    if retry_respect_retry_after:
                        try:
                            wait_seconds = min(retry_max_backoff_seconds, max(wait_seconds, float(response.headers.get("Retry-After") or "")))
                        except Exception:
                            pass
                    time.sleep(wait_seconds)
                    retry_counters["retry_sleep_seconds"] = float(retry_counters.get("retry_sleep_seconds", 0.0)) + float(wait_seconds)
                    continue
                response.raise_for_status()
                retry_counters["resolved_ip"] = resolved_ip
                return response.json()
            except Exception as exc:
                last_exc = exc
                error_class, retryable = _classify_bls_exception(exc)
                if retryable and attempt < retry_max_attempts_per_request:
                    retry_counters["retries_total"] = int(retry_counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    time.sleep(wait_seconds)
                    retry_counters["retry_sleep_seconds"] = float(retry_counters.get("retry_sleep_seconds", 0.0)) + float(wait_seconds)
                    continue
                retry_counters["last_error_class"] = error_class
                raise
        raise last_exc or RuntimeError("bls_request_failed_without_exception")

    def fetch_series(self, *, series_ids: list[str], start_year: int | None, end_year: int | None, **kwargs: Any) -> Any:
        if len(series_ids) == 1 and start_year is None and end_year is None:
            return self._request_json(method="GET", path=f"/{series_ids[0]}", json_body=None, **kwargs)
        body: dict[str, Any] = {"seriesid": series_ids}
        if start_year is not None and end_year is not None:
            body.update({"startyear": str(start_year), "endyear": str(end_year)})
        return self._request_json(method="POST", path="", json_body=body, **kwargs)


def get_bls_client(config: dict[str, Any]) -> BlsV1Client:
    return BlsV1Client(base_url=settings.bls_api_base_url)


def _common_request_kwargs(config: dict[str, Any], rate_limiter: _RateLimiter, retry_counters: dict[str, Any]) -> dict[str, Any]:
    return {
        "timeout_seconds": int(config.get("request_timeout_seconds", 30)),
        "max_redirects": int(config.get("max_redirects", settings.connector_max_redirects)),
        "max_requests_budget": int(config.get("max_requests", 10)),
        "retry_max_attempts_per_request": int(config.get("retry_max_attempts_per_request", 4)),
        "retry_base_backoff_seconds": float(config.get("retry_base_backoff_seconds", 0.4)),
        "retry_max_backoff_seconds": float(config.get("retry_max_backoff_seconds", 3.0)),
        "retry_respect_retry_after": bool(config.get("retry_respect_retry_after", True)),
        "rate_limiter": rate_limiter,
        "retry_counters": retry_counters,
    }


def _summary_report_path(run_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_bls_summary_v1.json"


def _selection_manifest_path(run_id: str) -> Path:
    return Path(settings.connector_manifests_dir) / f"{run_id}_bls_selection_manifest_v1.json"


def submit_bls_run(db: Session, *, payload: dict[str, Any], idempotency_key: str | None) -> tuple[ConnectorRun, bool]:
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
        effective_sort="series_year_period",
        effective_order="desc",
        effective_page_size=len(config.get("series_ids") or []),
        submission_idempotency_key=submitted_key,
        adapter_dialect="bls_public_api_v1",
        api_generation="v1",
        sciencebase_normalization_version="n/a",
        submitted_at=now,
    )
    db.add(run)
    db.flush()
    if submitted_key:
        db.add(ConnectorRunSubmission(connector_key=CONNECTOR_KEY, submission_idempotency_key=submitted_key, request_fingerprint=request_fingerprint, connector_run_id=run.connector_run_id, expires_at=now + timedelta(hours=settings.connector_submission_ttl_hours)))
    db.add(ConnectorPolicySnapshot(connector_run_id=run.connector_run_id, policy_json=config, retry_matrix_json={"retryable_http_statuses": sorted(RETRYABLE_HTTP_STATUSES), "retry_max_attempts_per_request": int(config.get("retry_max_attempts_per_request", 4)), "max_requests": int(config.get("max_requests", 10))}))
    _record_run_event(db, run=run, event_type="run_submitted", phase="planning", status_after="pending", metrics_json={"connector_key": CONNECTOR_KEY, "auth_mode": "anonymous"})
    db.commit()
    db.refresh(run)
    return run, True


def _client_auth_mode(client: Any) -> str:
    return str(getattr(client, "auth_mode", "anonymous") or "anonymous")


def _request_method(config: dict[str, Any]) -> str:
    return "GET" if len(config.get("series_ids") or []) == 1 and config.get("start_year") is None and config.get("end_year") is None else "POST"


def _series_digest(series_ids: list[str]) -> str:
    return _stable_json_hash({"series_ids": series_ids})[:16]


def _series_key_fragment(series_ids: list[str]) -> str:
    joined = ",".join(series_ids)
    if len(joined) <= 160:
        return joined
    return f"{len(series_ids)}series-{_series_digest(series_ids)}"


def _series_display_value(series_ids: list[str]) -> str:
    joined = ";".join(series_ids)
    if len(joined) <= 200:
        return joined
    return f"{len(series_ids)} BLS series sha256:{_series_digest(series_ids)}"


def _request_accounting_from_run(run: ConnectorRun) -> dict[str, Any]:
    stored = dict((run.query_plan_json or {}).get("bls_request_accounting") or {})
    return {
        "requests_total": int(stored.get("requests_total", 0)),
        "retries_total": int(stored.get("retries_total", 0)),
        "retry_sleep_seconds": float(stored.get("retry_sleep_seconds", 0.0)),
        "last_error_class": stored.get("last_error_class"),
    }


def _record_request_accounting(run: ConnectorRun, retry_counters: dict[str, Any]) -> None:
    plan = dict(run.query_plan_json or {})
    plan["bls_request_accounting"] = {
        "requests_total": int(retry_counters.get("requests_total", 0)),
        "retries_total": int(retry_counters.get("retries_total", 0)),
        "retry_sleep_seconds": float(retry_counters.get("retry_sleep_seconds", 0.0)),
        "last_error_class": retry_counters.get("last_error_class"),
    }
    run.query_plan_json = plan


def _rows_artifact_path(run_id: str, target_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_{target_id}_bls_rows_v1.json"


def _write_rows_artifact(run: ConnectorRun, target: ConnectorRunTarget, rows: list[dict[str, Any]]) -> str:
    return _write_json(
        _rows_artifact_path(run.connector_run_id, target.connector_run_target_id),
        {"schema_id": ROWS_SCHEMA_ID, "schema_version": 1, "connector_run_id": run.connector_run_id, "target_id": target.connector_run_target_id, "rows": rows},
    )


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


def _target_for_request(*, run: ConnectorRun, config: dict[str, Any]) -> ConnectorRunTarget:
    now = _utcnow()
    series_ids = list(config.get("series_ids") or [])
    year_part = f"{config.get('start_year')}-{config.get('end_year')}" if config.get("start_year") is not None else "latest3"
    artifact_key = f"bls_v1:{_series_key_fragment(series_ids)}:{year_part}"
    series_display = _series_display_value(series_ids)
    method = _request_method(config)
    target_status = "dry_run_skipped" if str(config.get("run_mode", "metadata_only")) == "dry_run" else "selected"
    source_ref = {
        "source_system": SOURCE_SYSTEM,
        "series_ids": series_ids,
        "start_year": config.get("start_year"),
        "end_year": config.get("end_year"),
        "request_method": method,
        "runtime_host": ALLOWED_HOST,
        "runtime_base_url": settings.bls_api_base_url,
        "phase0_endpoint_pin": "official_bls_v1_signature_and_terms_pages",
        "phase0_doc_urls": PHASE0_DOC_URLS,
        "api_access_date": API_ACCESS_DATE,
        "terms_of_service_url": BLS_TERMS_URL,
        "no_vouch_disclaimer": BLS_NO_VOUCH_DISCLAIMER,
        "operator_daily_cap_residual": "BLS v1 25-queries-per-day compliance is operator responsibility across runs; this connector enforces only the per-run request budget.",
        "code_enforced_caps": {"series_per_query": 25, "year_span_inclusive": 10, "max_rps": 2.0, "max_requests_per_run": int(config.get("max_requests", 10))},
    }
    return ConnectorRunTarget(
        connector_run_id=run.connector_run_id,
        ordinal=1,
        stable_release_key=artifact_key,
        stable_release_identifier=artifact_key,
        identifiers_json=[{"type": "bls_series_id", "value": series_id} for series_id in series_ids],
        sciencebase_item_id=series_display,
        sciencebase_item_url=settings.bls_api_base_url,
        sciencebase_file_name=f"BLS API v1 {len(series_ids)} series {year_part}",
        sciencebase_download_uri=settings.bls_api_base_url if method == "POST" else f"{settings.bls_api_base_url.rstrip('/')}/{series_ids[0]}",
        artifact_surface="timeseries_observations",
        selection_source=SOURCE_SYSTEM,
        selection_scope="metadata_query",
        selection_match_basis="series_year_period",
        artifact_locator_type="api_url",
        source_artifact_key=artifact_key,
        canonical_artifact_key=artifact_key,
        source_reference_json=source_ref,
        permission_snapshot_json={"access": "public", "auth_mode": "anonymous", "attribution": ATTRIBUTION, "terms_of_service_url": BLS_TERMS_URL, "no_vouch_disclaimer": BLS_NO_VOUCH_DISCLAIMER},
        access_level_summary="public_api",
        public_read_confirmed=True,
        status=target_status,
        retry_eligible=False,
        discovered_at=now,
        selected_at=now,
        recommended_at=now if target_status == "dry_run_skipped" else None,
        last_stage_transition_at=now,
        operator_reason_code="dry_run_bls_query_selected" if target_status == "dry_run_skipped" else "bls_query_selected",
    )


def _normalize_observation(raw: dict[str, Any], *, series_id: str) -> dict[str, Any] | None:
    year = _clean_string(raw.get("year"))
    period = _clean_string(raw.get("period"))
    period_name = _clean_string(raw.get("periodName"))
    value = _clean_string(raw.get("value"))
    if not year or not period or not period_name:
        raise BlsSchemaValidationError("missing_required_observation_field")
    if value is None:
        return None
    footnotes = []
    for item in raw.get("footnotes") or []:
        if isinstance(item, dict):
            code = _clean_string(item.get("code"))
            text = _clean_string(item.get("text"))
            if code or text:
                footnotes.append({"code": code, "text": text})
    try:
        value_numeric = float(value.replace(",", ""))
    except Exception:
        value_numeric = None
    return {"series_id": series_id, "year": year, "period": period, "period_name": period_name, "value": value, "value_numeric": value_numeric, "footnotes": footnotes}


def _parse_bls_response(payload: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict):
        raise BlsSchemaValidationError("malformed_bls_envelope")
    status = _clean_string(payload.get("status"))
    if status != "REQUEST_SUCCEEDED":
        raise BlsSchemaValidationError(f"bls_status_{(status or 'missing').lower()}")
    results = payload.get("Results")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise BlsSchemaValidationError("malformed_bls_results")
    series = results[0].get("series")
    if not isinstance(series, list) or not series:
        raise BlsSchemaValidationError("empty_series")
    rows: list[dict[str, Any]] = []
    source_row_count = 0
    for series_item in series:
        if not isinstance(series_item, dict):
            raise BlsSchemaValidationError("malformed_bls_series")
        series_id = _clean_string(series_item.get("seriesID"))
        data = series_item.get("data")
        if not series_id or not isinstance(data, list) or not data:
            raise BlsSchemaValidationError("empty_series")
        for raw in data:
            if not isinstance(raw, dict):
                raise BlsSchemaValidationError("malformed_bls_observation")
            source_row_count += 1
            normalized = _normalize_observation(raw, series_id=series_id)
            if normalized is not None:
                rows.append(normalized)
    if source_row_count == 0:
        raise BlsSchemaValidationError("empty_series")
    if not rows:
        raise BlsSchemaValidationError("empty_after_normalization")
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


def _ensure_metadata_provenance(db: Session, *, run: ConnectorRun, target: ConnectorRunTarget, rows: list[dict[str, Any]], retry_counters: dict[str, Any]) -> None:
    if target.status != "recommended":
        return
    logical_dataset_key = target.stable_release_key or f"bls_v1:{target.connector_run_target_id}"
    if not target.dataset_id:
        dataset_id = _resolve_dataset_id(db, logical_dataset_key)
        if not dataset_id:
            dataset = Dataset(name=f"BLS API v1 {target.sciencebase_item_id or target.ordinal}", description=f"{ATTRIBUTION}; {BLS_NO_VOUCH_DISCLAIMER}", domain_pack="public_connectors", frequency_hint="monthly_or_annual", time_column="year_period")
            db.add(dataset)
            db.flush()
            dataset_id = dataset.dataset_id
            _persist_dataset_identity(db, dataset_id=dataset_id, logical_dataset_key=logical_dataset_key, metadata_json={"source_system": SOURCE_SYSTEM, "stable_release_key": target.stable_release_key, "source_artifact_key": target.source_artifact_key, "identifiers": target.identifiers_json or []})
        target.dataset_id = dataset_id
    if not target.dataset_version_id:
        content_payload = {"source_system": SOURCE_SYSTEM, "source_artifact_key": target.source_artifact_key, "row_count": len(rows), "row_hashes": [_stable_json_hash({"row": row}) for row in rows]}
        version = DatasetVersion(dataset_id=target.dataset_id, version_label=f"bls_v1_{str(target.sciencebase_item_id or target.ordinal).replace(';', '_')[:80]}_{run.connector_run_id[:8]}", version_type="source_metadata", status="ready", storage_ref=target.source_artifact_key, row_count=len(rows), content_hash=_stable_json_hash(content_payload), source_row_count=len(rows), dropped_row_count=0, notes=f"connector_run_id={run.connector_run_id}; source_artifact_key={target.source_artifact_key}")
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
            fetch_policy_mode="bls_v1_official_only",
            retrieved_http_json={"api_base_url": settings.bls_api_base_url, "allowed_hosts": [ALLOWED_HOST], "phase0_doc_urls": PHASE0_DOC_URLS, "api_access_date": API_ACCESS_DATE, "terms_of_service_url": BLS_TERMS_URL, "no_vouch_disclaimer": BLS_NO_VOUCH_DISCLAIMER, "requests_total": int(retry_counters.get("requests_total", 0)), "resolved_ip": retry_counters.get("resolved_ip")},
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
        if int(retry_counters.get("requests_total", 0)) >= int(config.get("max_requests", 10)):
            raise BlsSchemaValidationError("request_budget_exhausted")
        payload = client.fetch_series(series_ids=list(config.get("series_ids") or []), start_year=config.get("start_year"), end_year=config.get("end_year"), **_common_request_kwargs(config, rate_limiter, retry_counters))
        rows, source_row_count = _parse_bls_response(payload)
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
        source_ref.update({"source_row_count": source_row_count, "normalized_row_count": len(rows), "request_method": _request_method(config), "row_artifact_ref": row_artifact_ref})
        target.source_reference_json = source_ref
        _record_request_accounting(run, retry_counters)
        _ensure_metadata_provenance(db, run=run, target=target, rows=rows, retry_counters=retry_counters)
        _record_run_event(db, run=run, target=target, event_type="target_rows_recorded", phase="selection", status_after="recommended", reason_code="observations_recorded")
        db.commit()
        return rows
    except Exception as exc:
        error_class, retryable = _classify_bls_exception(exc)
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
    payloads = [{"target_id": t.connector_run_target_id, "ordinal": int(t.ordinal or 0), "series_ids": (t.source_reference_json or {}).get("series_ids", []), "status": t.status, "last_error_class": t.last_error_class, "source_artifact_key": t.source_artifact_key, "rows": _rows_for_target(t, rows_by_target)} for t in targets]
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
        "api_base_url": settings.bls_api_base_url,
        "runtime_host": ALLOWED_HOST,
        "auth_mode": _client_auth_mode(client),
        "request": {**_logical_query_from_config(config), "method": _request_method(config), "run_mode": str(config.get("run_mode", "metadata_only"))},
        "phase0_doc_urls": PHASE0_DOC_URLS,
        "api_access_date": API_ACCESS_DATE,
        "attribution": ATTRIBUTION,
        "terms_of_service_url": BLS_TERMS_URL,
        "no_vouch_disclaimer": BLS_NO_VOUCH_DISCLAIMER,
        "operator_daily_cap_residual": "BLS v1 25-queries-per-day compliance is operator responsibility across runs; no durable cross-run counter is claimed.",
        "rows": rows,
        "totals": {"discovered_count": int(run.discovered_count or 0), "recommended_count": int(run.recommended_count or 0), "failed_count": int(run.failed_count or 0), "blocked_by_fetch_policy_count": int(run.blocked_by_fetch_policy_count or 0), "row_count": len(rows)},
        "targets": [{"ordinal": int(t.ordinal or 0), "series_ids": (t.source_reference_json or {}).get("series_ids", []), "status": t.status, "last_error_class": t.last_error_class, "source_artifact_key": t.source_artifact_key} for t in targets],
        "retry_summary": {"requests_total": int(retry_counters.get("requests_total", 0)), "retries_total": int(retry_counters.get("retries_total", 0)), "retry_sleep_seconds": round(float(retry_counters.get("retry_sleep_seconds", 0.0)), 4), "rate_limiter_sleep_seconds": round(float(retry_counters.get("rate_limiter_sleep_seconds", 0.0)), 4), "last_error_class": retry_counters.get("last_error_class")},
    }
    summary_ref = _write_json(_summary_report_path(run.connector_run_id), summary)
    run.query_plan_json = {**(run.query_plan_json or {}), "connector_report_refs": {"bls_summary": summary_ref}}
    db.commit()


def _target_needs_processing(target: ConnectorRunTarget) -> bool:
    return target.status == "selected" or (target.status == "download_failed" and bool(target.retry_eligible))


def execute_bls_run(connector_run_id: str) -> None:
    db = SessionLocal()
    try:
        BLS_EXECUTOR_GUARDS.acquire_run_slot()
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
            client = get_bls_client(config)
            run.effective_search_params_json = {"base_url": settings.bls_api_base_url, "runtime_host": ALLOWED_HOST, "auth_mode": _client_auth_mode(client), "logical_query": _logical_query_from_config(config), "request_method": _request_method(config)}
            run.effective_filters_json = [{"field": key, "value": value} for key, value in _logical_query_from_config(config).items()]
            run.effective_sort = "series_year_period"
            run.effective_order = "desc"
            run.effective_page_size = len(config.get("series_ids") or [])
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
            BLS_EXECUTOR_GUARDS.release_run_slot()
    except Exception as exc:
        run = db.get(ConnectorRun, connector_run_id)
        if run:
            error_class, _retryable = _classify_bls_exception(exc)
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
