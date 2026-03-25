from __future__ import annotations

import hashlib
import json
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import ConnectorPolicySnapshot, ConnectorRun, ConnectorRunSubmission, ConnectorRunTarget
from app.services.connectors_sciencebase import (
    _acquire_lease,
    _finalize_run,
    _record_run_event,
    _release_lease,
    _renew_lease,
    _to_utc_naive,
    _utcnow,
    _write_json,
)
from app.services.sciencebase_connector.contracts import RUN_TERMINAL_STATUSES, SubmissionConflictError
from app.services.sciencebase_connector.executor import ExecutorGuards


SENATE_LDA_EXECUTOR_GUARDS = ExecutorGuards(max_concurrent_runs=settings.connector_max_concurrent_runs)
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
SUMMARY_SCHEMA_ID = "senate_lda.summary.v1"
DISCOVERY_SCHEMA_ID = "senate_lda.discovery_snapshot.v1"
SELECTION_SCHEMA_ID = "senate_lda.selection_manifest.v1"


def _stable_json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _clean_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _logical_query_from_config(config: dict[str, Any]) -> dict[str, Any]:
    logical_query: dict[str, Any] = {}
    for key in (
        "filing_uuid",
        "filing_year",
        "filing_period",
        "filing_type",
        "registrant_name",
        "client_name",
        "lobbyist_name",
        "filing_specific_lobbying_issues",
        "filing_dt_posted_after",
        "filing_dt_posted_before",
        "ordering",
    ):
        value = config.get(key)
        if value in (None, "", [], {}):
            continue
        logical_query[key] = value
    return logical_query


def _normalize_request_config(payload: dict[str, Any], submission_idempotency_key: str | None) -> dict[str, Any]:
    config = dict(payload)
    config["filing_uuid"] = _clean_string(config.get("filing_uuid"))
    config["filing_year"] = _coerce_int(config.get("filing_year"), 0, minimum=0) or None
    config["filing_period"] = _clean_string(config.get("filing_period"))
    config["filing_type"] = _clean_string(config.get("filing_type"))
    config["registrant_name"] = _clean_string(config.get("registrant_name"))
    config["client_name"] = _clean_string(config.get("client_name"))
    config["lobbyist_name"] = _clean_string(config.get("lobbyist_name"))
    config["filing_specific_lobbying_issues"] = _clean_string(config.get("filing_specific_lobbying_issues"))
    config["filing_dt_posted_after"] = _clean_string(config.get("filing_dt_posted_after"))
    config["filing_dt_posted_before"] = _clean_string(config.get("filing_dt_posted_before"))
    config["ordering"] = _clean_string(config.get("ordering")) or "-dt_posted"
    config["page_size"] = _coerce_int(config.get("page_size"), 25, minimum=1, maximum=25)
    config["max_items"] = _coerce_int(config.get("max_items"), 0, minimum=0)
    config["run_mode"] = str(config.get("run_mode", "metadata_only")).strip().lower()
    if config["run_mode"] not in {"metadata_only", "dry_run"}:
        config["run_mode"] = "metadata_only"
    config["include_filing_detail"] = bool(config.get("include_filing_detail", False))
    config["request_timeout_seconds"] = _coerce_int(config.get("request_timeout_seconds"), 30, minimum=5, maximum=120)
    config["retry_max_attempts_per_request"] = _coerce_int(
        config.get("retry_max_attempts_per_request"),
        4,
        minimum=1,
        maximum=8,
    )
    config["retry_base_backoff_seconds"] = _coerce_float(
        config.get("retry_base_backoff_seconds"),
        0.4,
        minimum=0.0,
        maximum=10.0,
    )
    config["retry_max_backoff_seconds"] = _coerce_float(
        config.get("retry_max_backoff_seconds"),
        3.0,
        minimum=config["retry_base_backoff_seconds"],
        maximum=60.0,
    )
    config["retry_respect_retry_after"] = bool(config.get("retry_respect_retry_after", True))
    config["max_rps"] = _coerce_float(config.get("max_rps"), 2.0, minimum=0.1, maximum=20.0)
    config["report_verbosity"] = str(config.get("report_verbosity", "standard")).strip().lower()
    if config["report_verbosity"] not in {"summary", "standard", "debug"}:
        config["report_verbosity"] = "standard"
    config["client_request_id"] = _clean_string(config.get("client_request_id"))
    config["submission_idempotency_key"] = submission_idempotency_key or config["client_request_id"]
    config["allowed_hosts"] = ["lda.senate.gov"]
    config["fetch_policy_summary"] = {
        "mode": "official_api_only",
        "surface_policy": "metadata_only",
        "external_fetch_policy": "senate_lda_official_only",
        "allowed_hosts": ["lda.senate.gov"],
    }
    config["source_query_fingerprint"] = _stable_json_hash(_logical_query_from_config(config))
    return config


def _classify_request_exception(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, requests.Timeout):
        return "transport_timeout", True
    if isinstance(exc, requests.ConnectionError):
        return "transport_connection_error", True
    if isinstance(exc, requests.HTTPError):
        response = getattr(exc, "response", None)
        status_code = int(response.status_code) if response is not None else 0
        if status_code in RETRYABLE_HTTP_STATUSES:
            return f"http_{status_code}", True
        return f"http_{status_code or 0}", False
    return exc.__class__.__name__.lower(), False


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


class SenateLdaClient:
    def __init__(self, *, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = str(api_key or "").strip() or None
        self.session = requests.Session()

    @property
    def auth_mode(self) -> str:
        return "token" if self.api_key else "anonymous"

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Token {self.api_key}"}

    def _request_json(
        self,
        *,
        path: str,
        params: dict[str, Any] | None,
        timeout_seconds: int,
        retry_max_attempts_per_request: int,
        retry_base_backoff_seconds: float,
        retry_max_backoff_seconds: float,
        retry_respect_retry_after: bool,
        rate_limiter: _RateLimiter,
        retry_counters: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(1, retry_max_attempts_per_request + 1):
            rate_limiter.wait()
            retry_counters["requests_total"] = int(retry_counters.get("requests_total", 0)) + 1
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=self._headers(),
                    timeout=timeout_seconds,
                )
                if response.status_code in RETRYABLE_HTTP_STATUSES and attempt < retry_max_attempts_per_request:
                    retry_counters["retries_total"] = int(retry_counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    if retry_respect_retry_after:
                        retry_after_raw = str(response.headers.get("Retry-After") or "").strip()
                        try:
                            wait_seconds = min(retry_max_backoff_seconds, max(wait_seconds, float(retry_after_raw)))
                        except Exception:
                            pass
                    time.sleep(wait_seconds)
                    retry_counters["retry_sleep_seconds"] = float(retry_counters.get("retry_sleep_seconds", 0.0)) + float(wait_seconds)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_exc = exc
                error_class, retryable = _classify_request_exception(exc)
                if retryable and attempt < retry_max_attempts_per_request:
                    retry_counters["retries_total"] = int(retry_counters.get("retries_total", 0)) + 1
                    wait_seconds = min(retry_max_backoff_seconds, retry_base_backoff_seconds * (2 ** (attempt - 1)))
                    time.sleep(wait_seconds)
                    retry_counters["retry_sleep_seconds"] = float(retry_counters.get("retry_sleep_seconds", 0.0)) + float(wait_seconds)
                    continue
                retry_counters["last_error_class"] = error_class
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("senate_lda_request_failed_without_exception")

    def list_filings(
        self,
        *,
        params: dict[str, Any],
        timeout_seconds: int,
        retry_max_attempts_per_request: int,
        retry_base_backoff_seconds: float,
        retry_max_backoff_seconds: float,
        retry_respect_retry_after: bool,
        rate_limiter: _RateLimiter,
        retry_counters: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request_json(
            path="/filings/",
            params=params,
            timeout_seconds=timeout_seconds,
            retry_max_attempts_per_request=retry_max_attempts_per_request,
            retry_base_backoff_seconds=retry_base_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_respect_retry_after=retry_respect_retry_after,
            rate_limiter=rate_limiter,
            retry_counters=retry_counters,
        )

    def get_filing_detail(
        self,
        *,
        filing_uuid: str,
        timeout_seconds: int,
        retry_max_attempts_per_request: int,
        retry_base_backoff_seconds: float,
        retry_max_backoff_seconds: float,
        retry_respect_retry_after: bool,
        rate_limiter: _RateLimiter,
        retry_counters: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request_json(
            path=f"/filings/{filing_uuid}/",
            params=None,
            timeout_seconds=timeout_seconds,
            retry_max_attempts_per_request=retry_max_attempts_per_request,
            retry_base_backoff_seconds=retry_base_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_respect_retry_after=retry_respect_retry_after,
            rate_limiter=rate_limiter,
            retry_counters=retry_counters,
        )


def get_senate_lda_client(config: dict[str, Any]) -> SenateLdaClient:
    return SenateLdaClient(
        base_url=settings.senate_lda_api_base_url,
        api_key=settings.senate_lda_api_key,
    )


def _registrant_name(item: dict[str, Any]) -> str | None:
    raw = item.get("registrant")
    if isinstance(raw, dict):
        return _clean_string(raw.get("name"))
    return None


def _client_name(item: dict[str, Any]) -> str | None:
    raw = item.get("client")
    if isinstance(raw, dict):
        return _clean_string(raw.get("name"))
    return None


def _client_auth_mode(client: Any) -> str:
    return str(getattr(client, "auth_mode", "anonymous") or "anonymous")


def _build_target_display_name(item: dict[str, Any]) -> str:
    filing_type = _clean_string(item.get("filing_type")) or "filing"
    filing_year = _clean_string(item.get("filing_year")) or "unknown_year"
    client_name = _client_name(item) or _registrant_name(item) or "unknown_party"
    return f"{filing_type}_{filing_year}_{client_name}".replace("/", "_")


def _normalize_filing_record(item: dict[str, Any], *, page_ref: str | None = None, detail_ref: str | None = None) -> dict[str, Any]:
    filing_uuid = _clean_string(item.get("filing_uuid")) or "unknown-filing"
    detail_url = _clean_string(item.get("url")) or f"{settings.senate_lda_api_base_url.rstrip('/')}/filings/{filing_uuid}/"
    document_url = _clean_string(item.get("filing_document_url"))
    return {
        "filing_uuid": filing_uuid,
        "stable_release_key": f"senate_lda:filing:{filing_uuid}",
        "stable_release_identifier": f"filing_uuid:{filing_uuid}",
        "sciencebase_item_id": filing_uuid,
        "sciencebase_item_url": detail_url,
        "sciencebase_file_name": _build_target_display_name(item),
        "sciencebase_download_uri": document_url,
        "artifact_surface": "filings",
        "artifact_locator_type": "filing_document_url" if document_url else "api_url",
        "source_artifact_key": document_url or detail_url,
        "canonical_artifact_key": document_url or detail_url,
        "selection_source": "filings",
        "selection_scope": "search_hit",
        "selection_match_basis": "metadata_query",
        "source_reference_json": {
            "source_system": "senate_lda",
            "list_ref": page_ref,
            "detail_ref": detail_ref,
            "detail_url": detail_url,
            "api_url": detail_url,
            "document_url": document_url,
            "document_content_type": _clean_string(item.get("filing_document_content_type")),
            "filing_type": _clean_string(item.get("filing_type")),
            "filing_year": item.get("filing_year"),
            "filing_period": _clean_string(item.get("filing_period")),
            "dt_posted": _clean_string(item.get("dt_posted")),
            "registrant_name": _registrant_name(item),
            "client_name": _client_name(item),
        },
        "identifiers_json": [{"type": "filing_uuid", "value": filing_uuid}],
    }


def _build_list_params(config: dict[str, Any], *, page: int) -> dict[str, Any]:
    params: dict[str, Any] = {
        "page": page,
        "page_size": int(config.get("page_size", 25)),
        "ordering": str(config.get("ordering", "-dt_posted")),
    }
    for key in (
        "filing_uuid",
        "filing_year",
        "filing_period",
        "filing_type",
        "registrant_name",
        "client_name",
        "lobbyist_name",
        "filing_specific_lobbying_issues",
        "filing_dt_posted_after",
        "filing_dt_posted_before",
    ):
        value = config.get(key)
        if value not in (None, "", [], {}):
            params[key] = value
    return params


def submit_senate_lda_run(db: Session, *, payload: dict[str, Any], idempotency_key: str | None) -> tuple[ConnectorRun, bool]:
    submitted_key = (idempotency_key or payload.get("client_request_id") or "").strip() or None
    config = _normalize_request_config(payload, submitted_key)
    request_fingerprint = _stable_json_hash(config)
    source_query_fingerprint = str(config.get("source_query_fingerprint") or "")
    now = _utcnow()

    if submitted_key:
        existing_submission = (
            db.query(ConnectorRunSubmission)
            .filter(
                and_(
                    ConnectorRunSubmission.connector_key == "senate_lda",
                    ConnectorRunSubmission.submission_idempotency_key == submitted_key,
                )
            )
            .first()
        )
        expires_at = _to_utc_naive(existing_submission.expires_at) if existing_submission else None
        now_naive = _to_utc_naive(now)
        if existing_submission and (expires_at is None or (now_naive is not None and expires_at > now_naive)):
            if existing_submission.request_fingerprint != request_fingerprint:
                raise SubmissionConflictError("idempotency key reused with different payload")
            existing_run = db.get(ConnectorRun, existing_submission.connector_run_id)
            if existing_run:
                return existing_run, False

    active_run_count = (
        db.query(ConnectorRun)
        .filter(ConnectorRun.status.in_(["pending", "running", "cancelling"]))
        .count()
    )
    if active_run_count >= int(settings.connector_max_concurrent_runs):
        raise SubmissionConflictError("active run concurrency limit reached")

    run = ConnectorRun(
        connector_key="senate_lda",
        source_system="senate_lda",
        source_mode="public_api",
        status="pending",
        request_config_json=config,
        source_query_fingerprint=source_query_fingerprint,
        request_fingerprint=request_fingerprint,
        effective_search_params_json={},
        effective_filters_json=[],
        effective_sort=str(config.get("ordering", "-dt_posted")),
        effective_order="desc" if str(config.get("ordering", "")).startswith("-") else "asc",
        effective_page_size=int(config.get("page_size", 25)),
        search_exhaustion_reason=None,
        submission_idempotency_key=submitted_key,
        adapter_dialect="senate_lda_rest_v1",
        api_generation="v1",
        sciencebase_normalization_version="n/a",
        submitted_at=now,
    )
    db.add(run)
    db.flush()

    if submitted_key:
        db.add(
            ConnectorRunSubmission(
                connector_key="senate_lda",
                submission_idempotency_key=submitted_key,
                request_fingerprint=request_fingerprint,
                connector_run_id=run.connector_run_id,
                expires_at=now + timedelta(hours=settings.connector_submission_ttl_hours),
            )
        )

    db.add(
        ConnectorPolicySnapshot(
            connector_run_id=run.connector_run_id,
            policy_json=config,
            retry_matrix_json={
                "retryable_http_statuses": sorted(RETRYABLE_HTTP_STATUSES),
                "retry_max_attempts_per_request": int(config.get("retry_max_attempts_per_request", 4)),
            },
        )
    )

    _record_run_event(
        db,
        run=run,
        event_type="run_submitted",
        phase="planning",
        status_after="pending",
        metrics_json={
            "connector_key": run.connector_key,
            "auth_mode": "token" if settings.senate_lda_api_key else "anonymous",
        },
    )
    db.commit()
    db.refresh(run)
    return run, True


def _discovery_snapshot_path(run_id: str) -> Path:
    return Path(settings.connector_snapshots_dir) / f"{run_id}_senate_lda_discovery_snapshot_v1.json"


def _selection_manifest_path(run_id: str) -> Path:
    return Path(settings.connector_manifests_dir) / f"{run_id}_senate_lda_selection_manifest_v1.json"


def _summary_report_path(run_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_senate_lda_summary_v1.json"


def _page_snapshot_path(run_id: str, page_number: int) -> Path:
    return Path(settings.connector_snapshots_dir) / f"{run_id}_senate_lda_page_{page_number:04d}.json"


def _detail_snapshot_path(run_id: str, filing_uuid: str) -> Path:
    return Path(settings.connector_snapshots_dir) / f"{run_id}_senate_lda_detail_{filing_uuid}.json"


def _create_targets_from_discovery(
    db: Session,
    *,
    run: ConnectorRun,
    discovered_records: list[dict[str, Any]],
    run_mode: str,
    include_filing_detail: bool,
) -> None:
    now = _utcnow()
    for ordinal, record in enumerate(discovered_records, start=1):
        normalized = _normalize_filing_record(record, page_ref=record.get("_page_ref"))
        target_status = "selected"
        operator_reason_code = "metadata_selected"
        recommended_at = None
        if run_mode == "dry_run":
            target_status = "dry_run_skipped"
            operator_reason_code = "dry_run_metadata_only"
        elif not include_filing_detail:
            target_status = "recommended"
            operator_reason_code = "metadata_recorded"
            recommended_at = now
        target = ConnectorRunTarget(
            connector_run_id=run.connector_run_id,
            ordinal=ordinal,
            stable_release_key=normalized["stable_release_key"],
            stable_release_identifier=normalized["stable_release_identifier"],
            identifiers_json=normalized["identifiers_json"],
            sciencebase_item_id=normalized["sciencebase_item_id"],
            sciencebase_item_url=normalized["sciencebase_item_url"],
            sciencebase_file_name=normalized["sciencebase_file_name"],
            sciencebase_download_uri=normalized["sciencebase_download_uri"],
            artifact_surface=normalized["artifact_surface"],
            selection_source=normalized["selection_source"],
            selection_scope=normalized["selection_scope"],
            selection_match_basis=normalized["selection_match_basis"],
            artifact_locator_type=normalized["artifact_locator_type"],
            source_artifact_key=normalized["source_artifact_key"],
            canonical_artifact_key=normalized["canonical_artifact_key"],
            source_reference_json=normalized["source_reference_json"],
            permission_snapshot_json={},
            access_level_summary="public_api",
            public_read_confirmed=True,
            status=target_status,
            retry_eligible=False,
            discovered_at=now,
            selected_at=now,
            recommended_at=recommended_at,
            last_stage_transition_at=now,
            operator_reason_code=operator_reason_code,
        )
        db.add(target)
        _record_run_event(
            db,
            run=run,
            target=target,
            event_type="target_created",
            phase="selection",
            status_after=target_status,
            reason_code=operator_reason_code,
        )
    db.commit()


def _hydrate_detail_targets(
    db: Session,
    *,
    run: ConnectorRun,
    client: SenateLdaClient,
    config: dict[str, Any],
    rate_limiter: _RateLimiter,
    retry_counters: dict[str, Any],
) -> None:
    targets = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunTarget.ordinal.asc())
        .all()
    )
    for target in targets:
        if run.cancellation_requested_at:
            run.status = "cancelling"
            db.commit()
            break
        if target.status == "download_failed" and not bool(target.retry_eligible):
            continue
        if target.status not in {"selected", "download_failed"}:
            continue
        filing_uuid = str(target.sciencebase_item_id or "").strip()
        if not filing_uuid:
            continue
        target.attempt_count = int(target.attempt_count or 0) + 1
        target.last_attempt_at = _utcnow()
        target.last_stage_transition_at = _utcnow()
        db.commit()
        try:
            detail_payload = client.get_filing_detail(
                filing_uuid=filing_uuid,
                timeout_seconds=int(config.get("request_timeout_seconds", 30)),
                retry_max_attempts_per_request=int(config.get("retry_max_attempts_per_request", 4)),
                retry_base_backoff_seconds=float(config.get("retry_base_backoff_seconds", 0.4)),
                retry_max_backoff_seconds=float(config.get("retry_max_backoff_seconds", 3.0)),
                retry_respect_retry_after=bool(config.get("retry_respect_retry_after", True)),
                rate_limiter=rate_limiter,
                retry_counters=retry_counters,
            )
            detail_ref = _write_json(
                _detail_snapshot_path(run.connector_run_id, filing_uuid),
                {
                    "schema_id": "senate_lda.filing_detail_snapshot.v1",
                    "schema_version": 1,
                    "connector_run_id": run.connector_run_id,
                    "filing_uuid": filing_uuid,
                    "payload": detail_payload,
                },
            )
            normalized = _normalize_filing_record(detail_payload, detail_ref=detail_ref)
            source_ref = dict(target.source_reference_json or {})
            source_ref.update(normalized["source_reference_json"])
            target.sciencebase_item_url = normalized["sciencebase_item_url"]
            target.sciencebase_download_uri = normalized["sciencebase_download_uri"]
            target.source_artifact_key = normalized["source_artifact_key"]
            target.canonical_artifact_key = normalized["canonical_artifact_key"]
            target.source_reference_json = source_ref
            target.status = "recommended"
            target.error_stage = None
            target.error_message = None
            target.last_error_class = None
            target.retry_eligible = False
            target.recommended_at = _utcnow()
            target.last_stage_transition_at = _utcnow()
            target.operator_reason_code = "detail_hydrated"
            _record_run_event(
                db,
                run=run,
                target=target,
                event_type="target_detail_hydrated",
                phase="hydrating_detail",
                status_before="selected",
                status_after="recommended",
                reason_code="detail_hydrated",
            )
            db.commit()
        except Exception as exc:
            error_class, retryable = _classify_request_exception(exc)
            target.status = "download_failed"
            target.error_stage = "detail_hydration"
            target.error_message = str(exc)
            target.last_error_class = error_class
            target.retry_eligible = retryable
            target.last_stage_transition_at = _utcnow()
            target.operator_reason_code = "detail_hydration_failed"
            _record_run_event(
                db,
                run=run,
                target=target,
                event_type="target_detail_hydration_failed",
                phase="hydrating_detail",
                status_before="selected",
                status_after="download_failed",
                error_class=error_class,
                message=str(exc),
                reason_code="detail_hydration_failed",
            )
            db.commit()
        _renew_lease(db, run)


def _write_senate_lda_summary(
    db: Session,
    *,
    run: ConnectorRun,
    config: dict[str, Any],
    client: SenateLdaClient,
    page_refs: list[str],
    retry_counters: dict[str, Any],
) -> None:
    targets = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunTarget.ordinal.asc())
        .all()
    )
    summary = {
        "schema_id": SUMMARY_SCHEMA_ID,
        "schema_version": 1,
        "generated_at_utc": _utcnow().isoformat(),
        "connector_run_id": run.connector_run_id,
        "connector_key": run.connector_key,
        "status": run.status,
        "api_base_url": settings.senate_lda_api_base_url,
        "auth_mode": _client_auth_mode(client),
        "request": {
            "logical_query": _logical_query_from_config(config),
            "page_size": int(config.get("page_size", 25)),
            "max_items": int(config.get("max_items", 0)),
            "run_mode": str(config.get("run_mode", "metadata_only")),
            "include_filing_detail": bool(config.get("include_filing_detail", False)),
        },
        "discovery": {
            "page_count_completed": int(run.page_count_completed or 0),
            "next_page_available": bool(run.next_page_available),
            "search_exhaustion_reason": run.search_exhaustion_reason,
            "page_refs": page_refs,
        },
        "totals": {
            "discovered_count": int(run.discovered_count or 0),
            "selected_count": int(run.selected_count or 0),
            "recommended_count": int(run.recommended_count or 0),
            "failed_count": int(run.failed_count or 0),
        },
        "targets": [
            {
                "ordinal": int(target.ordinal or 0),
                "filing_uuid": target.sciencebase_item_id,
                "filing_name": target.sciencebase_file_name,
                "status": target.status,
                "detail_ref": dict(target.source_reference_json or {}).get("detail_ref"),
                "document_url": target.sciencebase_download_uri,
                "last_error_class": target.last_error_class,
            }
            for target in targets
        ],
        "retry_summary": {
            "requests_total": int(retry_counters.get("requests_total", 0)),
            "retries_total": int(retry_counters.get("retries_total", 0)),
            "retry_sleep_seconds": round(float(retry_counters.get("retry_sleep_seconds", 0.0)), 4),
            "rate_limiter_sleep_seconds": round(float(retry_counters.get("rate_limiter_sleep_seconds", 0.0)), 4),
            "last_error_class": retry_counters.get("last_error_class"),
        },
    }
    summary_ref = _write_json(_summary_report_path(run.connector_run_id), summary)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "connector_report_refs": {"senate_lda_summary": summary_ref},
    }
    db.commit()


def execute_senate_lda_run(connector_run_id: str) -> None:
    db = SessionLocal()
    SENATE_LDA_EXECUTOR_GUARDS.acquire_run_slot()
    try:
        run = db.get(ConnectorRun, connector_run_id)
        if not run:
            return
        if run.status in RUN_TERMINAL_STATUSES:
            return
        if not _acquire_lease(db, run):
            run.error_summary = "lease_conflict"
            _record_run_event(
                db,
                run=run,
                event_type="lease_conflict",
                phase="planning",
                status_after=run.status,
                error_class="lease_conflict",
            )
            db.commit()
            return
        _record_run_event(
            db,
            run=run,
            event_type="lease_acquired",
            phase="planning",
            status_after=run.status,
            metrics_json={"lease_owner": run.execution_lease_owner},
            commit=True,
        )

        config = dict(run.request_config_json or {})
        client = get_senate_lda_client(config)
        run.effective_search_params_json = {
            "base_url": settings.senate_lda_api_base_url,
            "auth_mode": _client_auth_mode(client),
            "logical_query": _logical_query_from_config(config),
        }
        run.effective_filters_json = [{"field": key, "value": value} for key, value in _logical_query_from_config(config).items()]
        run.effective_sort = str(config.get("ordering", "-dt_posted"))
        run.effective_order = "desc" if str(config.get("ordering", "")).startswith("-") else "asc"
        run.effective_page_size = int(config.get("page_size", 25))
        db.commit()

        retry_counters: dict[str, Any] = {}
        rate_limiter = _RateLimiter(float(config.get("max_rps", 2.0)))
        page_refs: list[str] = []

        target_count = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).count()
        if target_count == 0:
            _record_run_event(
                db,
                run=run,
                event_type="discovery_started",
                phase="discovery",
                status_after=run.status,
            )
            discovered_records: list[dict[str, Any]] = []
            page_number = 1
            max_items = int(config.get("max_items", 0))
            while True:
                if run.cancellation_requested_at:
                    run.status = "cancelling"
                    db.commit()
                    break
                payload = client.list_filings(
                    params=_build_list_params(config, page=page_number),
                    timeout_seconds=int(config.get("request_timeout_seconds", 30)),
                    retry_max_attempts_per_request=int(config.get("retry_max_attempts_per_request", 4)),
                    retry_base_backoff_seconds=float(config.get("retry_base_backoff_seconds", 0.4)),
                    retry_max_backoff_seconds=float(config.get("retry_max_backoff_seconds", 3.0)),
                    retry_respect_retry_after=bool(config.get("retry_respect_retry_after", True)),
                    rate_limiter=rate_limiter,
                    retry_counters=retry_counters,
                )
                page_ref = _write_json(
                    _page_snapshot_path(run.connector_run_id, page_number),
                    {
                        "schema_id": "senate_lda.page_snapshot.v1",
                        "schema_version": 1,
                        "connector_run_id": run.connector_run_id,
                        "page_number": page_number,
                        "params": _build_list_params(config, page=page_number),
                        "payload": payload,
                    },
                )
                page_refs.append(page_ref)
                results = [item for item in (payload.get("results") or []) if isinstance(item, dict)]
                for item in results:
                    if max_items and len(discovered_records) >= max_items:
                        break
                    normalized_item = dict(item)
                    normalized_item["_page_ref"] = page_ref
                    discovered_records.append(normalized_item)
                run.page_count_completed = int(page_number)
                run.last_offset_committed = len(discovered_records)
                next_url = str(payload.get("next") or "").strip()
                max_items_reached = bool(max_items and len(discovered_records) >= max_items)
                run.next_page_available = bool(next_url) and not max_items_reached
                run.search_exhaustion_reason = "max_items_reached" if max_items_reached else ("next_page_absent" if not next_url else None)
                db.commit()
                _record_run_event(
                    db,
                    run=run,
                    event_type="discovery_page_fetched",
                    phase="discovery",
                    status_after=run.status,
                    metrics_json={"page_number": page_number, "result_count": len(results)},
                )
                if max_items_reached or not next_url or not results:
                    break
                page_number += 1
                _renew_lease(db, run)

            discovery_snapshot = {
                "schema_id": DISCOVERY_SCHEMA_ID,
                "schema_version": 1,
                "generated_at_utc": _utcnow().isoformat(),
                "connector_run_id": run.connector_run_id,
                "logical_query": _logical_query_from_config(config),
                "page_refs": page_refs,
                "page_count_completed": int(run.page_count_completed or 0),
                "search_exhaustion_reason": run.search_exhaustion_reason,
                "discovered_records": [
                    {
                        "filing_uuid": item.get("filing_uuid"),
                        "filing_type": item.get("filing_type"),
                        "filing_year": item.get("filing_year"),
                        "filing_period": item.get("filing_period"),
                        "dt_posted": item.get("dt_posted"),
                        "registrant_name": _registrant_name(item),
                        "client_name": _client_name(item),
                        "detail_url": item.get("url"),
                        "filing_document_url": item.get("filing_document_url"),
                        "page_ref": item.get("_page_ref"),
                    }
                    for item in discovered_records
                ],
            }
            run.discovery_snapshot_ref = _write_json(_discovery_snapshot_path(run.connector_run_id), discovery_snapshot)
            db.commit()
            _create_targets_from_discovery(
                db,
                run=run,
                discovered_records=discovered_records,
                run_mode=str(config.get("run_mode", "metadata_only")),
                include_filing_detail=bool(config.get("include_filing_detail", False)),
            )
            targets = (
                db.query(ConnectorRunTarget)
                .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
                .order_by(ConnectorRunTarget.ordinal.asc())
                .all()
            )
            run.selection_manifest_ref = _write_json(
                _selection_manifest_path(run.connector_run_id),
                {
                    "schema_id": SELECTION_SCHEMA_ID,
                    "schema_version": 1,
                    "generated_at_utc": _utcnow().isoformat(),
                    "connector_run_id": run.connector_run_id,
                    "target_count": len(targets),
                    "targets": [
                        {
                            "ordinal": int(target.ordinal or 0),
                            "filing_uuid": target.sciencebase_item_id,
                            "status": target.status,
                            "detail_url": dict(target.source_reference_json or {}).get("detail_url"),
                            "document_url": target.sciencebase_download_uri,
                        }
                        for target in targets
                    ],
                },
            )
            db.commit()

        if (
            str(config.get("run_mode", "metadata_only")) != "dry_run"
            and bool(config.get("include_filing_detail", False))
            and run.status != "cancelling"
        ):
            _hydrate_detail_targets(
                db,
                run=run,
                client=client,
                config=config,
                rate_limiter=rate_limiter,
                retry_counters=retry_counters,
            )

        retry_counters["rate_limiter_sleep_seconds"] = rate_limiter.total_sleep_seconds
        _finalize_run(db, run)
        _write_senate_lda_summary(
            db,
            run=run,
            config=config,
            client=client,
            page_refs=page_refs,
            retry_counters=retry_counters,
        )
        _record_run_event(
            db,
            run=run,
            event_type="run_finalized",
            phase="finalizing",
            status_after=run.status,
            metrics_json={"completed_at": run.completed_at.isoformat() if run.completed_at else None},
            commit=True,
        )
    except Exception as exc:
        run = db.get(ConnectorRun, connector_run_id)
        if run:
            run.status = "failed"
            run.error_summary = f"orchestrator_internal_error: {exc}"
            run.completed_at = _utcnow()
            _release_lease(run)
            _record_run_event(
                db,
                run=run,
                event_type="run_failed",
                phase="finalizing",
                status_after=run.status,
                error_class="orchestrator_internal_error",
                message=str(exc),
            )
            db.commit()
    finally:
        SENATE_LDA_EXECUTOR_GUARDS.release_run_slot()
        db.close()
