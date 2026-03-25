from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    ApsDialectCapability,
    ApsSyncCursor,
    ConnectorPolicySnapshot,
    ConnectorRun,
    ConnectorRunCheckpoint,
    ConnectorRunSubmission,
    ConnectorRunTarget,
)
from app.services import nrc_aps_artifact_ingestion
from app.services import nrc_aps_content_index
from app.services import nrc_aps_contract
from app.services import nrc_aps_safeguards
from app.services import nrc_aps_sync_drift
from app.services.connectors_sciencebase import _finalize_run, _record_run_event
from app.services.sciencebase_connector.contracts import RETRYABLE_HTTP_STATUSES, RUN_TERMINAL_STATUSES, SubmissionConflictError
from app.services.sciencebase_connector.executor import ExecutorGuards, assert_lease_token, transition_target_state


NRC_EXECUTOR_GUARDS = ExecutorGuards(max_concurrent_runs=settings.connector_max_concurrent_runs)

APS_TOTAL_KEYS = ("count", "total", "Total", "totalHits", "total_hits", "TotalHits")
APS_RESULTS_KEYS = ("results", "Results", "documents", "Documents")
APS_TEXT_PATH_CANDIDATES = (
    ("document", "content"),
    ("content",),
    ("IndexedContent",),
    ("indexedContent",),
    ("DocumentText",),
    ("documentText",),
    ("DocumentContent",),
    ("documentContent",),
    ("Text",),
    ("text",),
)
APS_DEFAULT_ALLOWED_HOSTS = [
    "adams-api.nrc.gov",
    "adams-search.nrc.gov",
    "adams.nrc.gov",
    "nrc.gov",
    "www.nrc.gov",
]
APS_OPERATOR_MAP = {"eq": "equals", "gt": "ge", "lt": "le"}
APS_ALLOWED_RUN_MODES = {"metadata_only", "dry_run"}
APS_ALLOWED_REPORT_VERBOSITY = {"summary", "standard", "debug"}
APS_MAPPER_VERSION = "aps_mapper_v1"
APS_COMPILER_VERSION = "aps_compiler_v2"
APS_ALLOWED_WIRE_SHAPE_MODES = {"auto_probe", "guide_native", "shape_a", "shape_b", "draft_shape_a"}
APS_SHAPE_A_EXPRESSION_OPERATORS = {"ge", "gt", "le", "lt", "eq", "ne"}
APS_DEFAULT_DIALECT_PROBE_ORDER = ("shape_a", "guide_native", "shape_b")
APS_KNOWN_BAD_FORCED_DIALECTS = {"guide_native", "shape_b"}
APS_SYNC_WATERMARK_FIELD = "DateAddedTimestamp"
APS_SYNC_MODES = {"full_scan", "incremental", "reconciliation"}
APS_SYNC_BASELINE_ELIGIBLE_STATUSES = {"completed", "completed_with_errors"}
APS_DEFAULT_SYNC_OVERLAP_SECONDS = 259200
APS_DEFAULT_RECONCILIATION_LOOKBACK_DAYS = 30
APS_DEFAULT_RATE_LIMIT_RPS = 5.0
APS_RETRYABLE_THROTTLE_STATUSES = {429, 503}
APS_ARTIFACT_PIPELINE_MODES = {
    nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_OFF,
    nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_DOWNLOAD_ONLY,
    nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_HYDRATE_PROCESS,
}
APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE = nrc_aps_content_index.APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE
APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP = nrc_aps_content_index.APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP
APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK = nrc_aps_content_index.APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK


@dataclass
class ApsDownloadResult:
    content: bytes
    status_code: int
    final_url: str
    redirect_count: int
    etag: str | None
    last_modified: str | None
    content_type: str | None
    sha256: str
    headers: dict[str, Any]
    auth_required: bool


class ApsArtifactSizeLimitExceeded(RuntimeError):
    def __init__(
        self,
        *,
        max_file_bytes: int,
        bytes_received_before_abort: int,
        content_length_header: int | None,
        overrun_phase: str,
    ) -> None:
        self.max_file_bytes = int(max_file_bytes)
        self.bytes_received_before_abort = int(bytes_received_before_abort)
        self.content_length_header = int(content_length_header) if content_length_header is not None else None
        self.overrun_phase = str(overrun_phase or "stream")
        super().__init__(
            f"artifact_size_limit_exceeded:max={self.max_file_bytes}:received={self.bytes_received_before_abort}:phase={self.overrun_phase}"
        )


@dataclass(frozen=True)
class ApsLogicalQuery:
    text_query: str
    properties: list[dict[str, Any]]
    main_lib_filter: bool
    legacy_lib_filter: bool
    sort_field: str
    sort_direction: int
    include_content: bool | None
    requested_take: int | None
    identity_fingerprint: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _stable_json_hash(payload: dict[str, Any]) -> str:
    return nrc_aps_contract.stable_json_hash(payload)


def _parse_iso_datetime(value: Any) -> datetime | None:
    return nrc_aps_contract.parse_iso_datetime(value)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _subtract_overlap_from_iso(value: str | None, *, overlap_seconds: int) -> str | None:
    parsed = _parse_iso_datetime(value)
    if not parsed:
        return None
    return _iso_utc(parsed - timedelta(seconds=max(0, int(overlap_seconds))))


def _subscription_key_hash() -> str:
    raw = settings.nrc_adams_subscription_key or ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _aps_api_host() -> str:
    return (urlparse(settings.nrc_adams_api_base_url).hostname or "").lower() or "adams-api.nrc.gov"


def _normalize_wire_dialect(value: Any, *, default: str = "auto_probe") -> str:
    return nrc_aps_contract.normalize_wire_dialect(value, default=default)


def _logical_query_dict(logical_query: ApsLogicalQuery) -> dict[str, Any]:
    return nrc_aps_contract.logical_query_dict(logical_query)


def _build_logical_query(normalized_query_payload: dict[str, Any]) -> ApsLogicalQuery:
    return nrc_aps_contract.build_logical_query(normalized_query_payload)


def _logical_query_with_watermark(logical_query: ApsLogicalQuery, *, min_date_added_iso: str) -> ApsLogicalQuery:
    if not min_date_added_iso:
        return logical_query
    filtered = []
    for prop in logical_query.properties:
        if str(prop.get("name") or "").strip() == APS_SYNC_WATERMARK_FIELD:
            continue
        filtered.append(dict(prop))
    filtered.append({"name": APS_SYNC_WATERMARK_FIELD, "operator": "ge", "value": min_date_added_iso})
    patched_payload = {
        "searchCriteria": {
            "q": logical_query.text_query,
            "mainLibFilter": logical_query.main_lib_filter,
            "legacyLibFilter": logical_query.legacy_lib_filter,
            "properties": filtered,
        },
        "sort": logical_query.sort_field,
        "sortDirection": logical_query.sort_direction,
        "take": logical_query.requested_take,
        "content": logical_query.include_content,
    }
    return _build_logical_query(_strip_internal_fields(patched_payload))


def _compile_guide_native_payload(logical_query: ApsLogicalQuery, *, skip: int, take: int) -> dict[str, Any]:
    return nrc_aps_contract.compile_guide_native_payload(logical_query, skip=skip, take=take)


def _compile_shape_a_payload(logical_query: ApsLogicalQuery, *, skip: int, take: int) -> dict[str, Any]:
    return nrc_aps_contract.compile_shape_a_payload(logical_query, skip=skip, take=take)


def _compile_shape_b_payload(logical_query: ApsLogicalQuery, *, skip: int, take: int) -> dict[str, Any]:
    return nrc_aps_contract.compile_shape_b_payload(logical_query, skip=skip, take=take)


def _compile_dialect_payload(logical_query: ApsLogicalQuery, *, dialect: str, skip: int, take: int) -> dict[str, Any]:
    return nrc_aps_contract.compile_dialect_payload(logical_query, dialect=dialect, skip=skip, take=take)


@lru_cache(maxsize=1)
def _load_document_types_reference() -> set[str]:
    path = Path(__file__).resolve().parent / "nrc_adams_resources" / "document_types.json"
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    values = payload.get("document_types") if isinstance(payload, dict) else None
    if not isinstance(values, list):
        return set()
    return {str(item).strip() for item in values if str(item).strip()}


def _find_capability(
    db: Session,
    *,
    subscription_key_hash: str,
    api_host: str,
    dialect: str,
) -> ApsDialectCapability | None:
    return (
        db.query(ApsDialectCapability)
        .filter(
            and_(
                ApsDialectCapability.subscription_key_hash == subscription_key_hash,
                ApsDialectCapability.api_host == api_host,
                ApsDialectCapability.dialect == dialect,
            )
        )
        .first()
    )


def _upsert_capability_attempt(
    db: Session,
    *,
    subscription_key_hash: str,
    api_host: str,
    dialect: str,
    status_code: int,
    exchange_ref: str,
    parse_status: str,
    normalized_search: dict[str, Any],
    take_sent: int,
) -> None:
    now = _utcnow()
    capability = _find_capability(
        db,
        subscription_key_hash=subscription_key_hash,
        api_host=api_host,
        dialect=dialect,
    )
    if not capability:
        capability = ApsDialectCapability(
            subscription_key_hash=subscription_key_hash,
            api_host=api_host,
            dialect=dialect,
            observed_envelope_keys_json={},
            observed_count_keys_json=[],
            evidence_refs_json=[],
            notes_json={},
        )
        db.add(capability)
        db.flush()

    success = int(status_code) < 400
    capability.last_status = int(status_code)
    capability.updated_at = now
    if success:
        capability.success_count = int(capability.success_count or 0) + 1
        capability.last_success_at = now
        capability.cooldown_until = None
    else:
        capability.failure_count = int(capability.failure_count or 0) + 1
        capability.last_failure_at = now
        penalty_seconds = 0
        if int(status_code) in APS_RETRYABLE_THROTTLE_STATUSES:
            penalty_seconds = min(600, 30 * max(1, int(capability.failure_count)))
        elif 500 <= int(status_code) <= 599:
            penalty_seconds = min(300, 15 * max(1, int(capability.failure_count)))
        if penalty_seconds > 0:
            capability.cooldown_until = now + timedelta(seconds=penalty_seconds)

    schema_variant = str(normalized_search.get("schema_variant") or "unknown")
    envelope_counts = dict(capability.observed_envelope_keys_json or {})
    envelope_counts[schema_variant] = int(envelope_counts.get(schema_variant, 0)) + 1
    capability.observed_envelope_keys_json = envelope_counts

    count_keys = [str(item) for item in (capability.observed_count_keys_json or []) if str(item).strip()]
    raw_total_key = str(normalized_search.get("raw_total_key") or "").strip()
    if raw_total_key and raw_total_key not in count_keys:
        count_keys.append(raw_total_key)
    capability.observed_count_keys_json = count_keys

    if take_sent > 0:
        old_cap = int(capability.observed_page_cap or 0)
        capability.observed_page_cap = max(old_cap, int(take_sent))

    evidence = [str(item) for item in (capability.evidence_refs_json or []) if str(item).strip()]
    if exchange_ref and exchange_ref not in evidence:
        evidence.append(exchange_ref)
    capability.evidence_refs_json = evidence[-100:]

    capability.notes_json = {
        **(capability.notes_json or {}),
        "last_parse_status": parse_status,
        "last_results_key": normalized_search.get("results_key"),
    }
    db.flush()


def _preferred_dialect_order(
    db: Session,
    *,
    subscription_key_hash: str,
    api_host: str,
    forced_mode: str,
) -> list[str]:
    now = _utcnow()
    rows = (
        db.query(ApsDialectCapability)
        .filter(
            and_(
                ApsDialectCapability.subscription_key_hash == subscription_key_hash,
                ApsDialectCapability.api_host == api_host,
                ApsDialectCapability.success_count > 0,
            )
        )
        .all()
    )
    capability_rows = [
        {
            "dialect": row.dialect,
            "success_count": int(row.success_count or 0),
            "failure_count": int(row.failure_count or 0),
            "last_status": int(row.last_status or 0),
            "cooldown_until": _iso_utc(row.cooldown_until),
        }
        for row in rows
    ]
    return nrc_aps_contract.choose_dialect_order(
        forced_mode=forced_mode,
        capabilities=capability_rows,
        now=now,
    )


def _lint_submission_config(config: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    mode = _normalize_wire_dialect(config.get("wire_shape_mode"), default="auto_probe")
    if mode in APS_KNOWN_BAD_FORCED_DIALECTS and not bool(config.get("allow_known_bad_dialect", False)):
        raise SubmissionConflictError(
            f"wire_shape_mode={mode} is blocked by config lint; set allow_known_bad_dialect=true to override"
        )
    allowed_hosts = [str(item).strip().lower() for item in config.get("allowed_hosts", []) if str(item).strip()]
    if any(host in {"*", "*.*", "localhost"} for host in allowed_hosts):
        raise SubmissionConflictError("allowed_hosts contains unsafe wildcard/localhost entry")
    if int(config.get("max_run_bytes", 0)) < int(config.get("max_file_bytes", 0)):
        warnings.append("max_run_bytes increased to satisfy max_file_bytes floor")
    sync_mode = str(config.get("sync_mode", "full_scan")).strip().lower()
    if sync_mode not in APS_SYNC_MODES:
        raise SubmissionConflictError(f"sync_mode={sync_mode} is invalid")
    pipeline_mode = str(config.get("artifact_pipeline_mode") or "").strip().lower()
    if pipeline_mode not in APS_ARTIFACT_PIPELINE_MODES:
        raise SubmissionConflictError(f"artifact_pipeline_mode={pipeline_mode or 'unknown'} is invalid")
    if pipeline_mode == nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_OFF and bool(config.get("artifact_required_for_target_success")):
        warnings.append("artifact_required_for_target_success ignored when artifact_pipeline_mode=off")
    chunk_size_chars = _coerce_int(config.get("content_chunk_size_chars"), APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE)
    chunk_overlap_chars = _coerce_int(config.get("content_chunk_overlap_chars"), APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP)
    min_chunk_chars = _coerce_int(config.get("content_chunk_min_chars"), APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK)
    if chunk_size_chars <= 0:
        raise SubmissionConflictError("content_chunk_size_chars must be > 0")
    if chunk_overlap_chars < 0 or chunk_overlap_chars >= chunk_size_chars:
        raise SubmissionConflictError("content_chunk_overlap_chars must satisfy 0 <= overlap < chunk_size")
    if min_chunk_chars < 1 or min_chunk_chars > chunk_size_chars:
        raise SubmissionConflictError("content_chunk_min_chars must satisfy 1 <= min <= chunk_size")
    safeguard_lint = dict(config.get("safeguard_lint") or {})
    blocking_errors = [dict(item or {}) for item in safeguard_lint.get("blocking_errors", []) if isinstance(item, dict)]
    if blocking_errors:
        codes = [str(item.get("code") or "unknown_blocking_error") for item in blocking_errors]
        raise SubmissionConflictError(f"safeguard lint blocked configuration: {', '.join(codes)}")
    for item in [dict(entry or {}) for entry in safeguard_lint.get("warnings", []) if isinstance(entry, dict)]:
        message = str(item.get("message") or "").strip()
        if message:
            warnings.append(message)
    return warnings


def _safeguard_effective_config(config: dict[str, Any]) -> dict[str, Any]:
    policy = dict(config.get("safeguard_policy") or {})
    lint = dict(config.get("safeguard_lint") or {})
    return {
        "policy_schema_id": str(policy.get("schema_id") or nrc_aps_safeguards.APS_SAFEGUARD_POLICY_SCHEMA_ID),
        "policy_schema_version": int(policy.get("schema_version") or nrc_aps_safeguards.APS_SAFEGUARD_POLICY_SCHEMA_VERSION),
        "policy_hash": str(config.get("safeguard_policy_hash") or lint.get("policy_hash") or ""),
        "limiter": dict(policy.get("limiter") or {}),
        "timeouts": dict(policy.get("timeouts") or {}),
        "retry": dict(policy.get("retry") or {}),
        "lint_warning_count": len(list(lint.get("warnings") or [])),
        "lint_blocking_error_count": len(list(lint.get("blocking_errors") or [])),
    }

def _safe_filename(name: str) -> str:
    base = Path(name or "artifact").name.strip() or "artifact"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    cleaned = cleaned or "artifact"
    max_len = 120
    if len(cleaned) <= max_len:
        return cleaned
    suffix = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:12]
    ext = Path(cleaned).suffix
    stem = cleaned[: -len(ext)] if ext else cleaned
    budget = max_len - len(suffix) - (len(ext) if ext else 0) - 1
    budget = max(16, budget)
    return f"{stem[:budget]}_{suffix}{ext}"


def _fit_filename_for_path(base_dir: Path, prefix: str, safe_name: str, max_path_len: int = 240) -> str:
    candidate = safe_name
    base_abs = base_dir.resolve()
    prefix_path = base_abs / f"{prefix}_"
    full_path = base_abs / f"{prefix}_{candidate}"
    if len(str(full_path)) <= max_path_len:
        return candidate
    allowed_name_len = max_path_len - len(str(prefix_path))
    if allowed_name_len <= 0:
        return hashlib.sha1(candidate.encode("utf-8")).hexdigest()[:8]

    ext = Path(candidate).suffix
    stem = candidate[: -len(ext)] if ext else candidate
    suffix = hashlib.sha1(candidate.encode("utf-8")).hexdigest()[:10]
    sep = 1  # underscore between truncated stem and hash suffix
    budget = allowed_name_len - len(ext) - len(suffix) - sep
    if budget < 1:
        fallback = f"{suffix}{ext}"
        if len(fallback) <= allowed_name_len:
            return fallback
        return fallback[:allowed_name_len]

    fitted = f"{stem[:budget]}_{suffix}{ext}"
    if len(fitted) <= allowed_name_len:
        return fitted
    return fitted[:allowed_name_len]


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)


def _strip_internal_fields(obj: Any) -> Any:
    return nrc_aps_contract.strip_internal_fields(obj)


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_sort(raw_sort: Any, explicit_sort_direction: Any) -> tuple[str, int]:
    return nrc_aps_contract.parse_sort(raw_sort, explicit_sort_direction)


def _map_aps_filter(raw: Any) -> dict[str, Any] | None:
    return nrc_aps_contract.map_aps_filter(raw)


def _normalize_aps_query_payload(query_payload: dict[str, Any], mode: str) -> tuple[dict[str, Any], list[str]]:
    return nrc_aps_contract.normalize_aps_query_payload(query_payload, mode)


def _enum_mode(value: Any, default: str = "strict_builder") -> str:
    normalized = str(value or default).strip().lower()
    if normalized in {"strict_builder", "lenient_pass_through"}:
        return normalized
    return default


def _enum_wire_shape_mode(value: Any, default: str = "auto_probe") -> str:
    return _normalize_wire_dialect(value, default=default)


def _shape_a_expression_value(field: str, operator: str, value: Any) -> str:
    return nrc_aps_contract.shape_a_expression_value(field, operator, value)


def _guide_property_to_shape_a_filter(prop: dict[str, Any]) -> dict[str, Any] | None:
    return nrc_aps_contract.guide_property_to_shape_a_filter(prop)


def _guide_to_shape_a_payload(guide_payload: dict[str, Any]) -> dict[str, Any]:
    return nrc_aps_contract.guide_to_shape_a_payload(guide_payload)


def _build_wire_payload_candidates(
    logical_query: ApsLogicalQuery,
    *,
    dialect_order: list[str],
    skip: int,
    take: int,
) -> list[dict[str, Any]]:
    return nrc_aps_contract.build_wire_payload_candidates(
        logical_query,
        dialect_order=dialect_order,
        skip=skip,
        take=take,
    )


def _parse_json_response(response: requests.Response) -> tuple[dict[str, Any] | None, str]:
    return nrc_aps_contract.parse_json_response_text(response.text or "")


def _normalize_request_config(payload: dict[str, Any], submission_idempotency_key: str | None) -> dict[str, Any]:
    config = dict(payload or {})
    mode = _enum_mode(config.get("mode"), default="strict_builder")
    wire_shape_mode = _enum_wire_shape_mode(config.get("wire_shape_mode"), default="auto_probe")
    query_payload = config.get("query_payload")
    if not isinstance(query_payload, dict):
        query_payload = {}
    if not query_payload:
        if mode == "lenient_pass_through":
            control_keys = {
                "mode",
                "wire_shape_mode",
                "query_payload",
                "run_mode",
                "page_size",
                "max_items",
                "include_document_details",
                "artifact_pipeline_mode",
                "artifact_required_for_target_success",
                "download_artifacts",
                "probe_artifact_auth",
                "allowed_hosts",
                "fetch_policy_mode",
                "max_file_bytes",
                "max_run_bytes",
                "request_timeout_seconds",
                "connect_timeout_seconds",
                "read_timeout_seconds",
                "overall_deadline_seconds",
                "limiter_max_wait_seconds",
                "limiter_queue_poll_seconds",
                "runtime_process_count",
                "unsafe_allow_multi_process_limiter",
                "retry_max_attempts_per_request",
                "retry_max_attempts_per_scope",
                "retry_max_attempts_per_run",
                "retry_max_cumulative_sleep_seconds",
                "retry_base_backoff_seconds",
                "retry_max_backoff_seconds",
                "retry_jitter_mode",
                "retry_respect_retry_after",
                "max_redirects",
                "content_chunk_size_chars",
                "content_chunk_overlap_chars",
                "content_chunk_min_chars",
                "report_verbosity",
                "safeguard_policy",
                "client_request_id",
            }
            query_payload = {key: value for key, value in config.items() if key not in control_keys and value is not None}
        else:
            fallback_keys = ("q", "queryString", "filters", "anyFilters", "docketNumber", "searchCriteria", "sort", "sortDirection", "skip", "content", "take", "mainLibFilter", "legacyLibFilter")
            query_payload = {key: config.get(key) for key in fallback_keys if key in config and config.get(key) is not None}

    normalized_query_payload, mapper_warnings = _normalize_aps_query_payload(query_payload, mode=mode)
    logical_query = _build_logical_query(normalized_query_payload)
    default_take = max(1, min(_coerce_int(normalized_query_payload.get("take", config.get("page_size", 100)), 100), 100))
    traversal_defaults = {
        "initial_skip": max(0, _coerce_int(normalized_query_payload.get("skip", 0), 0)),
        "default_take": default_take,
    }

    raw_page_size = _coerce_int(config.get("page_size", 100), 100)
    page_size = max(1, min(raw_page_size, 100))
    if raw_page_size > 100:
        mapper_warnings.append("page_size clamped to 100 pending APS-V8 convergence")
    run_mode = str(config.get("run_mode", "metadata_only")).strip().lower() or "metadata_only"
    if run_mode not in APS_ALLOWED_RUN_MODES:
        run_mode = "metadata_only"
    raw_pipeline_mode = str(config.get("artifact_pipeline_mode") or "").strip().lower()
    if not raw_pipeline_mode:
        raw_pipeline_mode = (
            nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_DOWNLOAD_ONLY
            if bool(config.get("download_artifacts", True))
            else nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_OFF
        )
    artifact_pipeline_mode = nrc_aps_artifact_ingestion.normalize_pipeline_mode(raw_pipeline_mode)
    artifact_required_for_target_success = nrc_aps_artifact_ingestion.resolve_artifact_required_for_target_success(
        artifact_pipeline_mode,
        config.get("artifact_required_for_target_success"),
    )
    report_verbosity = str(config.get("report_verbosity", "standard")).strip().lower() or "standard"
    if report_verbosity not in APS_ALLOWED_REPORT_VERBOSITY:
        report_verbosity = "standard"
    sync_mode = str(config.get("sync_mode", "full_scan")).strip().lower() or "full_scan"
    if sync_mode not in APS_SYNC_MODES:
        sync_mode = "full_scan"

    allowed_hosts = [str(v).strip().lower() for v in config.get("allowed_hosts", []) if str(v).strip()]
    allowed_hosts = list(dict.fromkeys(APS_DEFAULT_ALLOWED_HOSTS + allowed_hosts))

    max_file_bytes = max(1024, _coerce_int(config.get("max_file_bytes", 64 * 1024 * 1024), 64 * 1024 * 1024))
    max_run_bytes = max(max_file_bytes, _coerce_int(config.get("max_run_bytes", 512 * 1024 * 1024), 512 * 1024 * 1024))
    safeguard_policy, safeguard_lint = nrc_aps_safeguards.ApsSafeguardPolicyLoader.load_from_config(
        config,
        max_concurrent_runs=int(settings.connector_max_concurrent_runs),
    )
    timeout_cfg = dict(safeguard_policy.get("timeouts") or {})
    limiter_cfg = dict(safeguard_policy.get("limiter") or {})
    normalized: dict[str, Any] = {
        "mode": mode,
        "wire_shape_mode": wire_shape_mode,
        "mapper_version": APS_MAPPER_VERSION,
        "compiler_version": APS_COMPILER_VERSION,
        "mapper_warnings": mapper_warnings,
        "query_payload_inbound": query_payload,
        "query_payload_normalized": normalized_query_payload,
        "logical_query": _logical_query_dict(logical_query),
        "logical_query_fingerprint": logical_query.identity_fingerprint,
        "traversal_defaults": traversal_defaults,
        "run_mode": run_mode,
        "artifact_pipeline_mode": artifact_pipeline_mode,
        "artifact_required_for_target_success": bool(artifact_required_for_target_success),
        "page_size": page_size,
        "max_items": max(0, _coerce_int(config.get("max_items", 0), 0)),
        "include_document_details": bool(config.get("include_document_details", True)),
        "download_artifacts": bool(artifact_pipeline_mode != nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_OFF),
        "probe_artifact_auth": bool(config.get("probe_artifact_auth", True)),
        "request_timeout_seconds": max(5, _coerce_int(config.get("request_timeout_seconds", timeout_cfg.get("read_timeout_seconds", 30)), 30)),
        "connect_timeout_seconds": max(1, _coerce_int(config.get("connect_timeout_seconds", timeout_cfg.get("connect_timeout_seconds", 10)), 10)),
        "read_timeout_seconds": max(1, _coerce_int(config.get("read_timeout_seconds", timeout_cfg.get("read_timeout_seconds", 30)), 30)),
        "overall_deadline_seconds": max(
            1,
            _coerce_int(config.get("overall_deadline_seconds", timeout_cfg.get("overall_deadline_seconds", 120)), 120),
        ),
        "max_file_bytes": max_file_bytes,
        "max_run_bytes": max_run_bytes,
        "max_redirects": max(0, _coerce_int(config.get("max_redirects", settings.connector_max_redirects), settings.connector_max_redirects)),
        "content_chunk_size_chars": _coerce_int(config.get("content_chunk_size_chars", APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE), APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE),
        "content_chunk_overlap_chars": _coerce_int(
            config.get("content_chunk_overlap_chars", APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP),
            APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP,
        ),
        "content_chunk_min_chars": _coerce_int(config.get("content_chunk_min_chars", APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK), APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK),
        "allowed_hosts": allowed_hosts,
        "fetch_policy_mode": str(config.get("fetch_policy_mode", "strict_public_safe") or "strict_public_safe"),
        "report_verbosity": report_verbosity,
        "sync_mode": sync_mode,
        "incremental_overlap_seconds": max(0, _coerce_int(config.get("incremental_overlap_seconds", APS_DEFAULT_SYNC_OVERLAP_SECONDS), APS_DEFAULT_SYNC_OVERLAP_SECONDS)),
        "reconciliation_lookback_days": max(1, _coerce_int(config.get("reconciliation_lookback_days", APS_DEFAULT_RECONCILIATION_LOOKBACK_DAYS), APS_DEFAULT_RECONCILIATION_LOOKBACK_DAYS)),
        "max_rps": max(0.1, float(config.get("max_rps", limiter_cfg.get("max_rps", APS_DEFAULT_RATE_LIMIT_RPS)) or APS_DEFAULT_RATE_LIMIT_RPS)),
        "limiter_max_wait_seconds": max(
            1.0,
            float(config.get("limiter_max_wait_seconds", limiter_cfg.get("max_wait_seconds", 10.0)) or 10.0),
        ),
        "limiter_queue_poll_seconds": max(
            0.01,
            float(config.get("limiter_queue_poll_seconds", limiter_cfg.get("queue_poll_seconds", 0.05)) or 0.05),
        ),
        "retry_max_attempts_per_request": max(
            1,
            _coerce_int(
                config.get(
                    "retry_max_attempts_per_request",
                    dict(safeguard_policy.get("retry") or {}).get("max_attempts_per_request", 4),
                ),
                4,
            ),
        ),
        "retry_max_attempts_per_scope": max(
            1,
            _coerce_int(
                config.get(
                    "retry_max_attempts_per_scope",
                    dict(safeguard_policy.get("retry") or {}).get("max_attempts_per_scope", 8),
                ),
                8,
            ),
        ),
        "retry_max_attempts_per_run": max(
            1,
            _coerce_int(
                config.get(
                    "retry_max_attempts_per_run",
                    dict(safeguard_policy.get("retry") or {}).get("max_attempts_per_run", 300),
                ),
                300,
            ),
        ),
        "retry_max_cumulative_sleep_seconds": max(
            0.0,
            float(
                config.get(
                    "retry_max_cumulative_sleep_seconds",
                    dict(safeguard_policy.get("retry") or {}).get("max_cumulative_sleep_seconds", 20.0),
                )
                or 20.0
            ),
        ),
        "retry_base_backoff_seconds": max(
            0.01,
            float(
                config.get(
                    "retry_base_backoff_seconds",
                    dict(safeguard_policy.get("retry") or {}).get("base_backoff_seconds", 0.4),
                )
                or 0.4
            ),
        ),
        "retry_max_backoff_seconds": max(
            0.01,
            float(
                config.get(
                    "retry_max_backoff_seconds",
                    dict(safeguard_policy.get("retry") or {}).get("max_backoff_seconds", 3.0),
                )
                or 3.0
            ),
        ),
        "retry_jitter_mode": str(
            config.get(
                "retry_jitter_mode",
                dict(safeguard_policy.get("retry") or {}).get("jitter_mode", "none"),
            )
            or "none"
        ).strip().lower(),
        "retry_respect_retry_after": bool(
            config.get(
                "retry_respect_retry_after",
                dict(safeguard_policy.get("retry") or {}).get("respect_retry_after", True),
            )
        ),
        "runtime_process_count": max(1, _coerce_int(config.get("runtime_process_count", limiter_cfg.get("runtime_process_count", 1)), 1)),
        "unsafe_allow_multi_process_limiter": bool(
            config.get(
                "unsafe_allow_multi_process_limiter",
                limiter_cfg.get("unsafe_allow_multi_process_limiter", False),
            )
        ),
        "allow_known_bad_dialect": bool(config.get("allow_known_bad_dialect", False)),
        "client_request_id": config.get("client_request_id"),
        "submission_idempotency_key": submission_idempotency_key or str(config.get("client_request_id") or "").strip() or None,
        "source_query_fingerprint": logical_query.identity_fingerprint,
        "subscription_key_hash": _subscription_key_hash() if settings.nrc_adams_subscription_key else None,
        "api_host": _aps_api_host(),
        "safeguard_policy": safeguard_policy,
        "safeguard_lint": safeguard_lint,
        "safeguard_policy_schema": safeguard_policy.get("schema_id"),
        "safeguard_policy_hash": safeguard_lint.get("policy_hash"),
    }
    lint_warnings = _lint_submission_config(normalized)
    normalized["lint_warnings"] = lint_warnings
    return normalized


def _extract_content_and_path(raw_payload: dict[str, Any]) -> tuple[str | None, str | None]:
    return nrc_aps_contract.extract_content_and_path(raw_payload)


def _first_total_value(payload: dict[str, Any]) -> tuple[int | None, str | None]:
    return nrc_aps_contract.first_total_value(payload)


def _normalize_document_projection(raw_doc: dict[str, Any]) -> dict[str, Any]:
    return nrc_aps_contract.normalize_document_projection(
        raw_doc,
        known_document_types=_load_document_types_reference(),
    )


def _normalize_search_response(payload: dict[str, Any]) -> dict[str, Any]:
    return nrc_aps_contract.normalize_search_response(
        payload,
        known_document_types=_load_document_types_reference(),
    )


def _normalize_document_response(payload: dict[str, Any]) -> dict[str, Any]:
    return nrc_aps_contract.normalize_document_response(
        payload,
        known_document_types=_load_document_types_reference(),
    )


def _is_allowed_host(hostname: str, allowed_patterns: list[str]) -> bool:
    host = hostname.lower()
    for pattern in allowed_patterns:
        pat = pattern.lower().strip()
        if not pat:
            continue
        if pat.startswith("*.") and host.endswith(pat[1:]):
            return True
        if host == pat:
            return True
    return False


def _precheck_download_url(url: str, allowed_hosts: list[str]) -> str | None:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if scheme != "https":
        return "scheme_not_allowed"
    if not host:
        return "missing_host"
    if not _is_allowed_host(host, allowed_hosts):
        return "host_not_allowed"
    return None


class NrcAdamsApsClient:
    def __init__(
        self,
        *,
        base_url: str,
        subscription_key: str,
        probe_artifact_auth: bool,
        safeguard_policy: dict[str, Any],
        safeguard_lint: dict[str, Any],
    ):
        self.base_url = base_url.rstrip("/")
        self.subscription_key = subscription_key
        self.probe_artifact_auth = probe_artifact_auth
        self.subscription_key_hash = hashlib.sha256(subscription_key.encode("utf-8")).hexdigest()
        self.api_host = (urlparse(self.base_url).hostname or "").lower() or "adams-api.nrc.gov"
        self.limiter_bucket_key = f"{self.subscription_key_hash}:{self.api_host}"
        self.safeguard_policy = dict(safeguard_policy or {})
        self.safeguard_lint = dict(safeguard_lint or {})
        self.max_rps = max(
            0.1,
            float(dict(self.safeguard_policy.get("limiter") or {}).get("max_rps", APS_DEFAULT_RATE_LIMIT_RPS) or APS_DEFAULT_RATE_LIMIT_RPS),
        )
        self.connect_timeout_seconds, self.read_timeout_seconds, self.overall_deadline_seconds = nrc_aps_safeguards.ApsTimeoutNormalizer.normalize(
            config={},
            policy=self.safeguard_policy,
        )
        self.safeguard_recorder = nrc_aps_safeguards.ApsSafeguardRecorder()
        self.request_executor = nrc_aps_safeguards.ApsRequestExecutor(
            policy=self.safeguard_policy,
            limiter=nrc_aps_safeguards.APS_LIMITER,
            recorder=self.safeguard_recorder,
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Ocp-Apim-Subscription-Key": self.subscription_key}

    def _remaining_deadline_seconds(self, started_monotonic: float) -> float:
        elapsed = max(0.0, time.monotonic() - started_monotonic)
        return max(0.0, float(self.overall_deadline_seconds) - elapsed)

    def _request_timeout_for_attempt(self, started_monotonic: float, *, for_download: bool = False) -> tuple[float, float]:
        remaining = self._remaining_deadline_seconds(started_monotonic)
        if remaining <= 0.0:
            raise requests.Timeout("overall_deadline_exceeded")
        connect_timeout = min(float(self.connect_timeout_seconds), remaining)
        read_timeout = min(float(self.read_timeout_seconds), remaining)
        if for_download:
            connect_timeout = min(connect_timeout, 10.0)
        return max(0.1, connect_timeout), max(0.1, read_timeout)

    def _request_with_safeguards(
        self,
        method: str,
        url: str,
        *,
        call_class: str,
        json_body: dict[str, Any] | None = None,
        explicit_scope: str | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        started_monotonic = time.monotonic()

        def _send() -> requests.Response:
            request_kwargs = dict(kwargs)
            request_kwargs["timeout"] = self._request_timeout_for_attempt(started_monotonic, for_download=(call_class == "download"))
            return requests.request(method, url, **request_kwargs)

        return self.request_executor.execute(
            method=method,
            url=url,
            call_class=call_class,
            bucket_key=self.limiter_bucket_key,
            request_callable=_send,
            json_body=json_body,
            explicit_scope=explicit_scope,
        )

    def search(self, payload: dict[str, Any], *, scope_key: str | None = None) -> requests.Response:
        return self._request_with_safeguards(
            "POST",
            f"{self.base_url}/aps/api/search",
            call_class="search",
            json_body=payload,
            explicit_scope=scope_key,
            json=payload,
            headers={**self._auth_headers(), "Content-Type": "application/json", "Accept": "application/json"},
        )

    def get_document(self, accession_number: str) -> requests.Response:
        return self._request_with_safeguards(
            "GET",
            f"{self.base_url}/aps/api/search/{accession_number}",
            call_class="document",
            explicit_scope=f"document:{accession_number}",
            headers={**self._auth_headers(), "Accept": "application/json"},
        )

    def download_artifact(self, url: str, *, max_redirects: int, max_file_bytes: int | None = None) -> ApsDownloadResult:
        attempts: list[tuple[dict[str, str], bool]] = []
        if self.probe_artifact_auth:
            attempts.append(({"Accept": "*/*"}, False))
        attempts.append(({**self._auth_headers(), "Accept": "*/*"}, True))

        last_exc: Exception | None = None
        for headers, auth_required in attempts:
            try:
                response = self._request_with_safeguards(
                    "GET",
                    url,
                    call_class="download",
                    explicit_scope=f"download:{url}:{int(auth_required)}",
                    stream=True,
                    allow_redirects=True,
                    headers=headers,
                )
                if len(response.history) > max_redirects:
                    raise RuntimeError("redirect_policy_violation")
                if response.status_code in {401, 403} and not auth_required and len(attempts) > 1:
                    continue
                response.raise_for_status()
                content_length_header: int | None = None
                try:
                    if response.headers.get("content-length"):
                        content_length_header = int(str(response.headers.get("content-length") or "").strip())
                except ValueError:
                    content_length_header = None
                limit = int(max_file_bytes or 0)
                if limit > 0 and content_length_header is not None and content_length_header > limit:
                    raise ApsArtifactSizeLimitExceeded(
                        max_file_bytes=limit,
                        bytes_received_before_abort=0,
                        content_length_header=content_length_header,
                        overrun_phase="preflight",
                    )
                hasher = hashlib.sha256()
                chunks: list[bytes] = []
                bytes_received = 0
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    if not chunk:
                        continue
                    bytes_received += len(chunk)
                    if limit > 0 and bytes_received > limit:
                        raise ApsArtifactSizeLimitExceeded(
                            max_file_bytes=limit,
                            bytes_received_before_abort=bytes_received,
                            content_length_header=content_length_header,
                            overrun_phase="stream",
                        )
                    chunks.append(chunk)
                    hasher.update(chunk)
                body = b"".join(chunks)
                return ApsDownloadResult(
                    content=body,
                    status_code=int(response.status_code),
                    final_url=str(response.url),
                    redirect_count=len(response.history),
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                    content_type=response.headers.get("content-type"),
                    sha256=hasher.hexdigest(),
                    headers=dict(response.headers),
                    auth_required=auth_required,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self.safeguard_recorder.record(
                    event_type="aps_download_attempt_failed",
                    reason_code="download_exception",
                    error_class=nrc_aps_safeguards.APS_CLASS_DOWNLOAD_FAILURE,
                    message=str(exc),
                    metrics={"url": url, "auth_required": auth_required},
                )
                continue
        raise last_exc or RuntimeError("artifact_download_failed")

    def record_parse_failure(
        self,
        *,
        parse_status: str,
        call_class: str,
        status_code: int,
        scope_key: str,
        exchange_ref: str | None,
    ) -> bool:
        decision = nrc_aps_safeguards.ApsFailureClassifier.classify_parse_status(parse_status)
        if not decision:
            return False
        self.safeguard_recorder.record(
            event_type="aps_terminal_contract_failure",
            reason_code="parse_failure_no_retry",
            error_class=decision.failure_class,
            metrics={
                "call_class": call_class,
                "status_code": int(status_code),
                "parse_status": parse_status,
                "scope_key": scope_key,
                "exchange_ref": exchange_ref,
            },
            dedupe_key=f"parse:{call_class}:{scope_key}:{parse_status}:{exchange_ref or ''}",
        )
        return True

    def safeguard_report_payload(self, *, run_id: str) -> dict[str, Any]:
        return self.safeguard_recorder.to_report(
            run_id=run_id,
            policy=self.safeguard_policy,
            lint=self.safeguard_lint,
        )


def get_nrc_adams_client(config: dict[str, Any]) -> NrcAdamsApsClient:
    if not settings.nrc_adams_subscription_key:
        raise SubmissionConflictError("NRC_ADAMS_APS_SUBSCRIPTION_KEY is not configured")
    safeguard_policy = dict(config.get("safeguard_policy") or {})
    if not safeguard_policy:
        safeguard_policy, safeguard_lint = nrc_aps_safeguards.ApsSafeguardPolicyLoader.load_from_config(
            config,
            max_concurrent_runs=int(settings.connector_max_concurrent_runs),
        )
    else:
        safeguard_lint = dict(config.get("safeguard_lint") or {})
    return NrcAdamsApsClient(
        base_url=settings.nrc_adams_api_base_url,
        subscription_key=settings.nrc_adams_subscription_key,
        probe_artifact_auth=bool(config.get("probe_artifact_auth", True)),
        safeguard_policy=safeguard_policy,
        safeguard_lint=safeguard_lint,
    )


def _get_sync_cursor(db: Session, *, source_query_fingerprint: str) -> ApsSyncCursor | None:
    if not source_query_fingerprint:
        return None
    return (
        db.query(ApsSyncCursor)
        .filter(
            and_(
                ApsSyncCursor.source_system == "nrc_adams_aps",
                ApsSyncCursor.logical_query_fingerprint == source_query_fingerprint,
            )
        )
        .first()
    )


def _resolve_runtime_logical_query(
    db: Session,
    *,
    base_logical_query: ApsLogicalQuery,
    config: dict[str, Any],
) -> tuple[ApsLogicalQuery, dict[str, Any]]:
    sync_mode = str(config.get("sync_mode", "full_scan")).strip().lower()
    overlap_seconds = int(config.get("incremental_overlap_seconds", APS_DEFAULT_SYNC_OVERLAP_SECONDS) or APS_DEFAULT_SYNC_OVERLAP_SECONDS)
    lookback_days = int(config.get("reconciliation_lookback_days", APS_DEFAULT_RECONCILIATION_LOOKBACK_DAYS) or APS_DEFAULT_RECONCILIATION_LOOKBACK_DAYS)
    source_query_fingerprint = str(config.get("source_query_fingerprint") or "")
    cursor = _get_sync_cursor(db, source_query_fingerprint=source_query_fingerprint)
    resolved = base_logical_query
    metadata: dict[str, Any] = {
        "sync_mode": sync_mode,
        "source_query_fingerprint": source_query_fingerprint,
        "cursor_last_watermark_iso": cursor.last_watermark_iso if cursor else None,
    }
    if sync_mode == "incremental" and cursor and cursor.last_watermark_iso:
        threshold = _subtract_overlap_from_iso(cursor.last_watermark_iso, overlap_seconds=overlap_seconds)
        if threshold:
            resolved = _logical_query_with_watermark(resolved, min_date_added_iso=threshold)
            metadata["effective_min_date_added"] = threshold
            metadata["overlap_seconds"] = overlap_seconds
    elif sync_mode == "reconciliation":
        threshold = _iso_utc(_utcnow() - timedelta(days=max(1, lookback_days)))
        if threshold:
            resolved = _logical_query_with_watermark(resolved, min_date_added_iso=threshold)
            metadata["effective_min_date_added"] = threshold
            metadata["reconciliation_lookback_days"] = lookback_days
    return resolved, metadata


def _logical_query_from_config(config: dict[str, Any]) -> ApsLogicalQuery:
    raw = dict(config.get("logical_query") or {})
    if raw:
        payload: dict[str, Any] = {
            "searchCriteria": {
                "q": str(raw.get("q") or ""),
                "mainLibFilter": bool(raw.get("mainLibFilter", True)),
                "legacyLibFilter": bool(raw.get("legacyLibFilter", False)),
                "properties": [dict(item or {}) for item in raw.get("properties", []) if isinstance(item, dict)],
            },
            "sort": str(raw.get("sort") or "DateAddedTimestamp"),
            "sortDirection": _coerce_int(raw.get("sortDirection", 1), 1),
        }
        if raw.get("content") is not None:
            payload["content"] = bool(raw.get("content"))
        if raw.get("take") is not None:
            payload["take"] = max(1, _coerce_int(raw.get("take"), 100))
        return _build_logical_query(payload)
    return _build_logical_query(dict(config.get("query_payload_normalized") or {}))


def _run_sync_mode(run: ConnectorRun) -> str:
    config = dict(run.request_config_json or {})
    value = str(config.get("sync_mode", "full_scan")).strip().lower()
    if value not in APS_SYNC_MODES:
        return "full_scan"
    return value


def _run_comparison_basis(run: ConnectorRun) -> dict[str, Any]:
    config = dict(run.request_config_json or {})
    query_plan = dict(run.query_plan_json or {})
    return nrc_aps_sync_drift.build_comparison_basis(
        connector_key=run.connector_key,
        source_system=run.source_system,
        source_query_fingerprint=run.source_query_fingerprint,
        run_mode=config.get("run_mode", "metadata_only"),
        comparison_contract_version=query_plan.get("aps_comparison_contract_version") or nrc_aps_sync_drift.APS_COMPARISON_CONTRACT_VERSION,
        projection_hash_contract=query_plan.get("aps_projection_hash_contract") or nrc_aps_sync_drift.APS_PROJECTION_HASH_CONTRACT,
    )


def _build_sync_drift_snapshot_for_run(run: ConnectorRun) -> dict[str, Any]:
    config = dict(run.request_config_json or {})
    query_plan = dict(run.query_plan_json or {})
    discovery_payload = nrc_aps_sync_drift.read_json_object(run.discovery_snapshot_ref)
    selection_payload = nrc_aps_sync_drift.read_json_object(run.selection_manifest_ref)
    metadata_payloads, metadata_refs = nrc_aps_sync_drift.collect_metadata_payloads(
        run_id=run.connector_run_id,
        manifests_dir=settings.connector_manifests_dir,
    )
    projection_hashes, projection_refs, projection_inputs = nrc_aps_sync_drift.build_projection_index(
        metadata_payloads=metadata_payloads,
        metadata_refs=metadata_refs,
    )
    return nrc_aps_sync_drift.build_snapshot(
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        source_system=run.source_system,
        source_query_fingerprint=str(run.source_query_fingerprint or ""),
        run_mode=str(config.get("run_mode", "metadata_only")),
        sync_mode=_run_sync_mode(run),
        comparison_contract_version=str(
            query_plan.get("aps_comparison_contract_version") or nrc_aps_sync_drift.APS_COMPARISON_CONTRACT_VERSION
        ),
        projection_hash_contract=str(
            query_plan.get("aps_projection_hash_contract") or nrc_aps_sync_drift.APS_PROJECTION_HASH_CONTRACT
        ),
        discovery_ref=run.discovery_snapshot_ref,
        selection_ref=run.selection_manifest_ref,
        discovery_payload=discovery_payload,
        selection_payload=selection_payload,
        projection_hashes=projection_hashes,
        projection_refs=projection_refs,
        projection_inputs=projection_inputs,
        max_observed_watermark=query_plan.get("aps_max_observed_watermark"),
        observed_schema_variants=dict(query_plan.get("aps_observed_schema_variants") or {}),
        dialect_order=[str(item) for item in (query_plan.get("aps_dialect_order") or []) if str(item).strip()],
    )


def _resolve_sync_drift_baseline(
    db: Session,
    *,
    current_run: ConnectorRun,
    current_snapshot: dict[str, Any],
) -> tuple[dict[str, Any] | None, str, dict[str, Any]]:
    sync_mode = str(current_snapshot.get("sync_mode") or "").strip().lower()
    source_query_fingerprint = str(current_snapshot.get("source_query_fingerprint") or "").strip()
    if sync_mode == "incremental":
        strict_mode = "incremental"
        strict_label = nrc_aps_sync_drift.APS_BASELINE_INCREMENTAL_STRICT
        fallback_label = nrc_aps_sync_drift.APS_BASELINE_INCREMENTAL_FALLBACK
    elif sync_mode == "reconciliation":
        strict_mode = "reconciliation"
        strict_label = nrc_aps_sync_drift.APS_BASELINE_RECON_STRICT
        fallback_label = nrc_aps_sync_drift.APS_BASELINE_RECON_FALLBACK
    else:
        return (
            None,
            nrc_aps_sync_drift.APS_BASELINE_NO_BASELINE,
            {"reason": "sync_mode_not_incremental_or_reconciliation", "sync_mode": sync_mode},
        )
    if not source_query_fingerprint:
        return (
            None,
            nrc_aps_sync_drift.APS_BASELINE_NO_BASELINE,
            {"reason": "missing_source_query_fingerprint"},
        )

    candidates = (
        db.query(ConnectorRun)
        .filter(
            and_(
                ConnectorRun.connector_key == "nrc_adams_aps",
                ConnectorRun.connector_run_id != current_run.connector_run_id,
                ConnectorRun.source_query_fingerprint == source_query_fingerprint,
                ConnectorRun.completed_at.isnot(None),
                ConnectorRun.status.in_(sorted(APS_SYNC_BASELINE_ELIGIBLE_STATUSES)),
            )
        )
        .order_by(ConnectorRun.completed_at.desc(), ConnectorRun.submitted_at.desc())
        .all()
    )
    if not candidates:
        return (
            None,
            nrc_aps_sync_drift.APS_BASELINE_NO_BASELINE,
            {"reason": "no_prior_completed_candidates"},
        )

    current_basis = dict(current_snapshot.get("comparison_basis") or {})
    rejected: list[dict[str, Any]] = []
    evaluated_ids: set[str] = set()

    def _find_match(label: str, *, strict_only: bool) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        for candidate in candidates:
            candidate_id = str(candidate.connector_run_id or "")
            if candidate_id in evaluated_ids:
                continue
            candidate_sync_mode = _run_sync_mode(candidate)
            if strict_only and candidate_sync_mode != strict_mode:
                continue
            baseline_snapshot = _build_sync_drift_snapshot_for_run(candidate)
            baseline_basis = dict(baseline_snapshot.get("comparison_basis") or _run_comparison_basis(candidate))
            comparable, failures = nrc_aps_sync_drift.are_runs_comparable(current_basis, baseline_basis)
            evaluated_ids.add(candidate_id)
            if comparable:
                return (
                    baseline_snapshot,
                    {
                        "baseline_resolution": label,
                        "baseline_run_id": candidate.connector_run_id,
                        "baseline_sync_mode": candidate_sync_mode,
                    },
                )
            rejected.append(
                {
                    "candidate_run_id": candidate.connector_run_id,
                    "candidate_sync_mode": candidate_sync_mode,
                    "comparability_failures": failures,
                }
            )
        return None, {}

    strict_snapshot, strict_meta = _find_match(strict_label, strict_only=True)
    if strict_snapshot:
        return strict_snapshot, strict_label, {"selected": strict_meta, "rejected": rejected}

    fallback_snapshot, fallback_meta = _find_match(fallback_label, strict_only=False)
    if fallback_snapshot:
        return fallback_snapshot, fallback_label, {"selected": fallback_meta, "rejected": rejected}

    return (
        None,
        nrc_aps_sync_drift.APS_BASELINE_NO_BASELINE,
        {"reason": "no_comparable_baseline", "rejected": rejected},
    )


def _append_error_summary_token(existing: str | None, *, token: str) -> str:
    base = str(existing or "").strip()
    if not base:
        return token
    if token in base:
        return base
    return f"{base}; {token}"


def _safeguard_report_path(run_id: str) -> Path:
    return Path(settings.connector_reports_dir) / f"{run_id}_aps_safeguard_v1.json"


def _persist_safeguard_report_artifact(
    db: Session,
    *,
    run: ConnectorRun,
    config: dict[str, Any],
    client: Any,
    run_error: Exception | None = None,
) -> str:
    if hasattr(client, "safeguard_report_payload"):
        payload = dict(client.safeguard_report_payload(run_id=run.connector_run_id))
    else:
        payload = {
            "schema_id": nrc_aps_safeguards.APS_SAFEGUARD_REPORT_SCHEMA_ID,
            "schema_version": nrc_aps_safeguards.APS_SAFEGUARD_REPORT_SCHEMA_VERSION,
            "run_id": run.connector_run_id,
            "policy_schema_id": str(config.get("safeguard_policy_schema") or nrc_aps_safeguards.APS_SAFEGUARD_POLICY_SCHEMA_ID),
            "policy_hash": str(config.get("safeguard_policy_hash") or ""),
            "lint_warning_count": len(list(dict(config.get("safeguard_lint") or {}).get("warnings") or [])),
            "lint_blocking_error_count": len(list(dict(config.get("safeguard_lint") or {}).get("blocking_errors") or [])),
            "event_counts": {},
            "events": [],
        }
    payload["status"] = str(run.status or "")
    payload["completed_at"] = _iso_utc(run.completed_at)
    payload["safeguard_effective_config"] = _safeguard_effective_config(config)
    if run_error is not None:
        payload["run_error"] = {"class": run_error.__class__.__name__, "message": str(run_error)}

    report_ref = nrc_aps_safeguards.write_json_atomic(_safeguard_report_path(run.connector_run_id), payload)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_safeguard_report_refs": {"aps_safeguard": report_ref},
        "aps_safeguard_summary": {
            "policy_schema_id": payload.get("policy_schema_id"),
            "policy_hash": payload.get("policy_hash"),
            "event_counts": dict(payload.get("event_counts") or {}),
            "lint_warning_count": payload.get("lint_warning_count"),
            "lint_blocking_error_count": payload.get("lint_blocking_error_count"),
        },
    }
    db.flush()
    return report_ref


def _emit_safeguard_events(
    db: Session,
    *,
    run: ConnectorRun,
    client: Any,
) -> int:
    recorder = getattr(client, "safeguard_recorder", None)
    if recorder is None or not hasattr(recorder, "events"):
        return 0
    emitted = 0
    for payload in recorder.events():
        dedupe_key = str(payload.get("dedupe_key") or "").strip()
        reason_code = str(payload.get("reason_code") or "").strip() or None
        if dedupe_key:
            reason_code = (reason_code or dedupe_key)[:255]
        _record_run_event(
            db,
            run=run,
            event_type=str(payload.get("event_type") or "aps_safeguard_event"),
            phase="safeguards",
            stage="runtime",
            status_after=run.status,
            reason_code=reason_code,
            error_class=str(payload.get("error_class") or "") or None,
            message=str(payload.get("message") or "") or None,
            metrics_json={**dict(payload.get("metrics") or {}), "dedupe_key": dedupe_key or None},
        )
        emitted += 1
    return emitted


def _target_artifact_report_path(run_id: str, target_id: str) -> Path:
    return nrc_aps_artifact_ingestion.target_artifact_path(
        run_id=run_id,
        target_id=target_id,
        reports_dir=settings.connector_reports_dir,
    )


def _artifact_ingestion_run_report_path(run_id: str) -> Path:
    return nrc_aps_artifact_ingestion.run_artifact_path(run_id=run_id, reports_dir=settings.connector_reports_dir)


def _artifact_ingestion_failure_report_path(run_id: str) -> Path:
    return nrc_aps_artifact_ingestion.failure_artifact_path(run_id=run_id, reports_dir=settings.connector_reports_dir)


def _content_units_report_path(run_id: str, target_id: str) -> Path:
    return nrc_aps_content_index.content_units_artifact_path(
        run_id=run_id,
        target_id=target_id,
        reports_dir=settings.connector_reports_dir,
    )


def _content_index_run_report_path(run_id: str) -> Path:
    return nrc_aps_content_index.run_artifact_path(run_id=run_id, reports_dir=settings.connector_reports_dir)


def _content_index_failure_report_path(run_id: str) -> Path:
    return nrc_aps_content_index.failure_artifact_path(run_id=run_id, reports_dir=settings.connector_reports_dir)


def _persist_artifact_ingestion_run_artifact(
    db: Session,
    *,
    run: ConnectorRun,
    config: dict[str, Any],
) -> str:
    target_rows = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunTarget.ordinal.asc())
        .all()
    )
    target_artifacts: list[dict[str, Any]] = []
    for target in target_rows:
        source_ref = dict(target.source_reference_json or {})
        ref = str(source_ref.get("aps_artifact_ingestion_ref") or "").strip()
        if not ref:
            continue
        path = Path(ref)
        sha = ""
        target_payload: dict[str, Any] = {}
        if path.exists():
            try:
                with path.open("rb") as handle:
                    digest = hashlib.sha256()
                    while True:
                        chunk = handle.read(65536)
                        if not chunk:
                            break
                        digest.update(chunk)
                sha = digest.hexdigest()
                target_payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(target_payload, dict):
                    target_payload = {}
            except OSError:
                sha = ""
            except ValueError:
                target_payload = {}
        target_artifacts.append(
            {
                "target_id": target.connector_run_target_id,
                "status": target.status,
                "ref": ref,
                "sha256": sha or None,
                "outcome_status": str(target_payload.get("outcome_status") or "").strip() or None,
                "failure": dict(target_payload.get("failure") or {}) if isinstance(target_payload.get("failure"), dict) else None,
            }
        )

    payload = nrc_aps_artifact_ingestion.build_run_artifact_payload(
        run_id=run.connector_run_id,
        run_status=str(run.status or ""),
        pipeline_mode=str(config.get("artifact_pipeline_mode") or ""),
        artifact_required_for_target_success=bool(config.get("artifact_required_for_target_success", False)),
        selected_targets=int(run.selected_count or 0),
        target_artifacts=target_artifacts,
    )
    report_ref = nrc_aps_artifact_ingestion.write_json_atomic(
        _artifact_ingestion_run_report_path(run.connector_run_id),
        payload,
    )
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_artifact_ingestion_report_refs": {
            "aps_artifact_ingestion": report_ref,
            "aps_artifact_ingestion_failure": None,
        },
        "aps_artifact_ingestion_summary": {
            "run_outcome": payload.get("run_outcome"),
            "pipeline_mode": payload.get("pipeline_mode"),
            "artifact_required_for_target_success": bool(payload.get("artifact_required_for_target_success", False)),
            "selected_targets": int(payload.get("selected_targets") or 0),
            "processed_targets": int(payload.get("processed_targets") or 0),
            "outcome_counts": dict(payload.get("outcome_counts") or {}),
            "failure_code_counts": dict(payload.get("failure_code_counts") or {}),
        },
    }
    db.flush()
    return report_ref


def _persist_content_index_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun,
    error: Exception,
    failures: list[dict[str, Any]] | None = None,
) -> str:
    failure_payload = nrc_aps_content_index.build_failure_artifact_payload(
        run_id=run.connector_run_id,
        run_status=str(run.status or ""),
        error_class=error.__class__.__name__,
        error_message=str(error),
        failures=failures or [],
    )
    failure_ref = nrc_aps_content_index.write_json_atomic(
        _content_index_failure_report_path(run.connector_run_id),
        failure_payload,
    )
    run.error_summary = _append_error_summary_token(
        run.error_summary,
        token="aps_content_indexing_failed",
    )
    if run.status not in {"failed", "cancelled"}:
        run.status = "completed_with_errors"
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_content_index_report_refs": {
            "aps_content_index": None,
            "aps_content_index_failure": failure_ref,
        },
        "aps_content_index_summary": {
            "artifact_generation_failed": True,
            "error_class": error.__class__.__name__,
            "error_message": str(error),
        },
    }
    _record_run_event(
        db,
        run=run,
        event_type="aps_content_index_artifact_failed",
        phase="finalizing",
        stage="reporting",
        status_after=run.status,
        error_class=error.__class__.__name__,
        message=str(error),
        metrics_json={"aps_content_index_failure_ref": failure_ref},
    )
    db.flush()
    return failure_ref


def _generate_content_index_artifacts(
    db: Session,
    *,
    run: ConnectorRun,
    config: dict[str, Any],
) -> dict[str, Any]:
    chunking_policy = nrc_aps_content_index.normalize_chunking_policy(config)
    target_rows = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunTarget.ordinal.asc())
        .all()
    )
    content_units_artifacts: list[dict[str, Any]] = []
    indexing_failures: list[dict[str, Any]] = []

    for target in target_rows:
        source_ref = dict(target.source_reference_json or {})
        target_artifact_ref = str(source_ref.get("aps_artifact_ingestion_ref") or "").strip()
        if not target_artifact_ref:
            continue
        target_artifact_payload = nrc_aps_sync_drift.read_json_object(target_artifact_ref)
        if not target_artifact_payload:
            indexing_failures.append(
                {
                    "target_id": target.connector_run_target_id,
                    "code": "content_units_target_artifact_unreadable",
                    "message": f"Unable to parse target artifact: {target_artifact_ref}",
                }
            )
            continue
        outcome_status = str(target_artifact_payload.get("outcome_status") or "").strip().lower()
        if outcome_status == "failed":
            continue

        source_metadata_ref = str(
            target_artifact_payload.get("source_metadata_ref")
            or source_ref.get("metadata_ref")
            or ""
        ).strip() or None
        try:
            content_units_payload = nrc_aps_content_index.build_content_units_payload_from_target_artifact(
                run_id=run.connector_run_id,
                target_id=target.connector_run_target_id,
                target_artifact_payload=target_artifact_payload,
                source_metadata_ref=source_metadata_ref,
                artifact_storage_dir=settings.artifact_storage_dir,
                chunking_policy=chunking_policy,
            )
        except Exception as exc:  # noqa: BLE001
            indexing_failures.append(
                {
                    "target_id": target.connector_run_target_id,
                    "code": "content_units_build_failed",
                    "error_class": exc.__class__.__name__,
                    "message": str(exc),
                }
            )
            continue

        content_units_ref = nrc_aps_content_index.write_json_atomic(
            _content_units_report_path(run.connector_run_id, target.connector_run_target_id),
            content_units_payload,
        )
        content_units_sha = hashlib.sha256(Path(content_units_ref).read_bytes()).hexdigest()
        content_units_payload = {
            **content_units_payload,
            "content_units_ref": content_units_ref,
        }

        content_units_artifact_row = {
            "target_id": target.connector_run_target_id,
            "status": target.status,
            "ref": content_units_ref,
            "sha256": content_units_sha,
            "content_id": str(content_units_payload.get("content_id") or ""),
            "content_status": str(content_units_payload.get("content_status") or ""),
            "chunk_count": int(content_units_payload.get("chunk_count") or 0),
        }
        content_units_artifacts.append(content_units_artifact_row)

        try:
            nrc_aps_content_index.upsert_content_units_payload(
                db,
                payload=content_units_payload,
            )
        except Exception as exc:  # noqa: BLE001
            indexing_failures.append(
                {
                    "target_id": target.connector_run_target_id,
                    "content_id": str(content_units_payload.get("content_id") or ""),
                    "code": "content_index_db_write_failed",
                    "error_class": exc.__class__.__name__,
                    "message": str(exc),
                    "content_units_ref": content_units_ref,
                }
            )
            continue

        target.source_reference_json = {
            **(target.source_reference_json or {}),
            "aps_content_units_ref": content_units_ref,
            "aps_content_id": str(content_units_payload.get("content_id") or ""),
            "aps_content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            "aps_chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        }
        db.flush()

    run_payload = nrc_aps_content_index.build_run_artifact_payload(
        run_id=run.connector_run_id,
        run_status=str(run.status or ""),
        selected_targets=int(run.selected_count or 0),
        content_units_artifacts=content_units_artifacts,
        indexing_failures=indexing_failures,
    )
    run_ref = nrc_aps_content_index.write_json_atomic(
        _content_index_run_report_path(run.connector_run_id),
        run_payload,
    )

    failure_ref: str | None = None
    if indexing_failures:
        failure_payload = nrc_aps_content_index.build_failure_artifact_payload(
            run_id=run.connector_run_id,
            run_status=str(run.status or ""),
            error_class="content_index_partial_failure",
            error_message="One or more content index updates failed",
            failures=indexing_failures,
        )
        failure_ref = nrc_aps_content_index.write_json_atomic(
            _content_index_failure_report_path(run.connector_run_id),
            failure_payload,
        )
        run.error_summary = _append_error_summary_token(
            run.error_summary,
            token="aps_content_indexing_failed",
        )
        if run.status not in {"failed", "cancelled"}:
            run.status = "completed_with_errors"

    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_content_index_report_refs": {
            "aps_content_index": run_ref,
            "aps_content_index_failure": failure_ref,
        },
        "aps_content_index_summary": {
            "run_outcome": run_payload.get("run_outcome"),
            "selected_targets": int(run_payload.get("selected_targets") or 0),
            "processed_targets": int(run_payload.get("processed_targets") or 0),
            "indexed_content_units": int(run_payload.get("indexed_content_units") or 0),
            "content_status_counts": dict(run_payload.get("content_status_counts") or {}),
            "indexing_failures_count": int(run_payload.get("indexing_failures_count") or 0),
            "indexing_failure_code_counts": dict(run_payload.get("indexing_failure_code_counts") or {}),
            "chunking_policy": chunking_policy,
        },
    }
    db.flush()
    return {
        "run_ref": run_ref,
        "failure_ref": failure_ref,
        "processed_targets": int(run_payload.get("processed_targets") or 0),
        "indexed_content_units": int(run_payload.get("indexed_content_units") or 0),
        "indexing_failures_count": int(run_payload.get("indexing_failures_count") or 0),
        "content_status_counts": dict(run_payload.get("content_status_counts") or {}),
        "indexing_failure_code_counts": dict(run_payload.get("indexing_failure_code_counts") or {}),
    }


def _persist_artifact_ingestion_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun,
    error: Exception,
) -> str:
    failure_payload = nrc_aps_artifact_ingestion.build_failure_artifact_payload(
        run_id=run.connector_run_id,
        run_status=str(run.status or ""),
        error_class=error.__class__.__name__,
        error_message=str(error),
    )
    failure_ref = nrc_aps_artifact_ingestion.write_json_atomic(
        _artifact_ingestion_failure_report_path(run.connector_run_id),
        failure_payload,
    )
    run.error_summary = _append_error_summary_token(
        run.error_summary,
        token="aps_artifact_ingestion_artifact_generation_failed",
    )
    if run.status not in {"failed", "cancelled"}:
        run.status = "completed_with_errors"
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_artifact_ingestion_report_refs": {
            "aps_artifact_ingestion": None,
            "aps_artifact_ingestion_failure": failure_ref,
        },
        "aps_artifact_ingestion_summary": {
            "artifact_generation_failed": True,
            "error_class": error.__class__.__name__,
            "error_message": str(error),
        },
    }
    _record_run_event(
        db,
        run=run,
        event_type="aps_artifact_ingestion_artifact_failed",
        phase="finalizing",
        stage="reporting",
        status_after=run.status,
        error_class=error.__class__.__name__,
        message=str(error),
        metrics_json={"aps_artifact_ingestion_failure_ref": failure_ref},
    )
    db.flush()
    return failure_ref


def _generate_sync_drift_artifacts(
    db: Session,
    *,
    run: ConnectorRun,
) -> dict[str, Any]:
    current_snapshot = _build_sync_drift_snapshot_for_run(run)
    baseline_snapshot, baseline_resolution, baseline_meta = _resolve_sync_drift_baseline(
        db,
        current_run=run,
        current_snapshot=current_snapshot,
    )
    if baseline_snapshot is None:
        baseline_resolution = nrc_aps_sync_drift.APS_BASELINE_NO_BASELINE
    delta_artifact, drift_artifact = nrc_aps_sync_drift.build_delta_and_drift_artifacts(
        current_snapshot=current_snapshot,
        baseline_snapshot=baseline_snapshot,
        baseline_resolution=baseline_resolution,
    )
    paths = nrc_aps_sync_drift.artifact_paths(run_id=run.connector_run_id, reports_dir=settings.connector_reports_dir)
    delta_ref = nrc_aps_sync_drift.write_json_deterministic(paths["aps_sync_delta"], delta_artifact)
    drift_ref = nrc_aps_sync_drift.write_json_deterministic(paths["aps_sync_drift"], drift_artifact)

    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_comparison_contract_version": nrc_aps_sync_drift.APS_COMPARISON_CONTRACT_VERSION,
        "aps_projection_hash_contract": nrc_aps_sync_drift.APS_PROJECTION_HASH_CONTRACT,
        "aps_sync_report_refs": {
            "aps_sync_delta": delta_ref,
            "aps_sync_drift": drift_ref,
            "aps_sync_drift_failure": None,
        },
        "aps_sync_drift_comparison": {
            "baseline_resolution": baseline_resolution,
            "baseline_run_id": baseline_snapshot.get("run_id") if baseline_snapshot else None,
            "comparison_status": drift_artifact.get("comparison_status"),
            "finding_counts": drift_artifact.get("finding_counts", {}),
            "selection_debug": baseline_meta,
        },
    }
    return {
        "delta_ref": delta_ref,
        "drift_ref": drift_ref,
        "baseline_resolution": baseline_resolution,
        "baseline_run_id": baseline_snapshot.get("run_id") if baseline_snapshot else None,
        "comparison_status": drift_artifact.get("comparison_status"),
        "finding_counts": drift_artifact.get("finding_counts", {}),
        "selection_debug": baseline_meta,
    }


def _persist_sync_drift_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun,
    error: Exception,
) -> str:
    config = dict(run.request_config_json or {})
    sync_mode = str(config.get("sync_mode", "full_scan")).strip().lower() or "full_scan"
    paths = nrc_aps_sync_drift.artifact_paths(run_id=run.connector_run_id, reports_dir=settings.connector_reports_dir)
    failure_payload = nrc_aps_sync_drift.build_failure_artifact(
        run_id=run.connector_run_id,
        source_query_fingerprint=str(run.source_query_fingerprint or ""),
        sync_mode=sync_mode,
        error_class=error.__class__.__name__,
        error_message=str(error),
    )
    failure_ref = nrc_aps_sync_drift.write_json_deterministic(paths["aps_sync_drift_failure"], failure_payload)
    run.error_summary = _append_error_summary_token(
        run.error_summary,
        token="aps_sync_drift_artifact_generation_failed",
    )
    if run.status not in {"failed", "cancelled"}:
        run.status = "completed_with_errors"
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_comparison_contract_version": nrc_aps_sync_drift.APS_COMPARISON_CONTRACT_VERSION,
        "aps_projection_hash_contract": nrc_aps_sync_drift.APS_PROJECTION_HASH_CONTRACT,
        "aps_sync_report_refs": {
            "aps_sync_delta": None,
            "aps_sync_drift": None,
            "aps_sync_drift_failure": failure_ref,
        },
        "aps_sync_drift_comparison": {
            "artifact_generation_failed": True,
            "error_class": error.__class__.__name__,
            "error_message": str(error),
        },
    }
    _record_run_event(
        db,
        run=run,
        event_type="aps_sync_drift_artifact_failed",
        phase="finalizing",
        stage="reporting",
        status_after=run.status,
        error_class=error.__class__.__name__,
        message=str(error),
        metrics_json={"aps_sync_drift_failure_ref": failure_ref},
    )
    return failure_ref


def _upsert_sync_cursor_after_run(
    db: Session,
    *,
    run: ConnectorRun,
    logical_query_fingerprint: str,
    overlap_seconds: int,
    reconciliation_lookback_days: int,
    max_observed_watermark: str | None,
    sync_metadata: dict[str, Any],
) -> None:
    if not logical_query_fingerprint:
        return
    cursor = _get_sync_cursor(db, source_query_fingerprint=logical_query_fingerprint)
    if not cursor:
        cursor = ApsSyncCursor(
            source_system="nrc_adams_aps",
            logical_query_fingerprint=logical_query_fingerprint,
            watermark_field=APS_SYNC_WATERMARK_FIELD,
        )
        db.add(cursor)
        db.flush()
    now = _utcnow()
    cursor.overlap_seconds = max(0, int(overlap_seconds))
    cursor.reconciliation_window_days = max(1, int(reconciliation_lookback_days))
    cursor.last_run_connector_id = run.connector_run_id
    cursor.last_run_completed_at = run.completed_at or now
    if str(sync_metadata.get("sync_mode") or "") == "reconciliation":
        cursor.last_reconciliation_at = now
    if max_observed_watermark:
        cursor.last_watermark_iso = max_observed_watermark
    cursor.metadata_json = {
        **(cursor.metadata_json or {}),
        **sync_metadata,
        "last_completed_status": run.status,
        "last_search_exhaustion_reason": run.search_exhaustion_reason,
    }
    cursor.updated_at = now
    db.flush()


def submit_nrc_adams_run(db: Session, *, payload: dict[str, Any], idempotency_key: str | None) -> tuple[ConnectorRun, bool]:
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
                    ConnectorRunSubmission.connector_key == "nrc_adams_aps",
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
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="pending",
        request_config_json=config,
        source_query_fingerprint=source_query_fingerprint,
        request_fingerprint=request_fingerprint,
        effective_search_params_json={},
        effective_filters_json=[],
        effective_sort=None,
        effective_order=None,
        effective_page_size=int(config.get("page_size", 100)),
        search_exhaustion_reason=None,
        submission_idempotency_key=submitted_key,
        adapter_dialect="nrc_adams_aps_rest_v1",
        api_generation="v1",
        sciencebase_normalization_version="n/a",
        submitted_at=now,
    )
    db.add(run)
    db.flush()

    if submitted_key:
        db.add(
            ConnectorRunSubmission(
                connector_key="nrc_adams_aps",
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
                "retryable": [
                    nrc_aps_safeguards.APS_CLASS_HTTP_429,
                    nrc_aps_safeguards.APS_CLASS_HTTP_5XX,
                    nrc_aps_safeguards.APS_CLASS_NETWORK,
                    nrc_aps_safeguards.APS_TIMEOUT_CONNECT,
                    nrc_aps_safeguards.APS_TIMEOUT_READ,
                    nrc_aps_safeguards.APS_TIMEOUT_DEADLINE,
                ],
                "terminal": [
                    nrc_aps_safeguards.APS_CLASS_JSON_MALFORMED,
                    nrc_aps_safeguards.APS_CLASS_HTTP_4XX,
                    nrc_aps_safeguards.APS_CLASS_AUTH,
                    "host_policy_violation",
                ],
                "orchestrator_only": ["lease_conflict"],
            },
        )
    )
    db.add(
        ConnectorRunCheckpoint(
            connector_run_id=run.connector_run_id,
            phase="planning",
            partition_cursor="0",
            page_offset=0,
            last_successful_stage="planning",
            payload_json={"state": "submitted"},
            checkpoint_written_at=_utcnow(),
        )
    )
    _record_run_event(
        db,
        run=run,
        event_type="run_submitted",
        phase="planning",
        status_after="pending",
        metrics_json={"connector_key": "nrc_adams_aps"},
    )
    db.commit()
    db.refresh(run)
    return run, True


def _assert_active_lease(run: ConnectorRun, lease_token: str | None) -> None:
    assert_lease_token(
        current_token=run.execution_lease_token,
        expected_token=lease_token,
        expires_at=run.execution_lease_expires_at,
    )


def _acquire_lease(db: Session, run: ConnectorRun) -> bool:
    now = _utcnow()
    owner = f"pid:{os.getpid()}"
    if run.execution_lease_expires_at and run.execution_lease_expires_at > now and run.execution_lease_owner not in (None, owner):
        return False
    run.execution_lease_owner = owner
    run.execution_lease_token = uuid.uuid4().hex
    run.execution_lease_expires_at = now + timedelta(seconds=settings.connector_lease_ttl_seconds)
    run.claimed_at = now
    run.heartbeat_at = now
    run.attempt_number = (run.attempt_number or 0) + 1
    run.started_at = run.started_at or now
    if run.status != "cancelling":
        run.status = "running"
    db.commit()
    return True


def _renew_lease(db: Session, run: ConnectorRun) -> None:
    run.execution_lease_expires_at = _utcnow() + timedelta(seconds=settings.connector_lease_ttl_seconds)
    run.heartbeat_at = _utcnow()
    db.commit()


def _release_lease(run: ConnectorRun) -> None:
    run.execution_lease_expires_at = _utcnow()


def _classify_http_exception(exc: Exception) -> tuple[str, bool]:
    decision = nrc_aps_safeguards.ApsFailureClassifier.classify_exception(exc)
    if decision.failure_class == "ok":
        return "ok", False
    if decision.failure_class == nrc_aps_safeguards.APS_CLASS_HTTP_5XX and isinstance(exc, requests.HTTPError):
        code = int(exc.response.status_code) if exc.response is not None else 0
        return decision.failure_class, bool(code in RETRYABLE_HTTP_STATUSES or code in APS_RETRYABLE_THROTTLE_STATUSES)
    return decision.failure_class, bool(decision.retryable)


def _classify_target_exception(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, RuntimeError) and "host_not_allowed" in str(exc):
        return "host_policy_violation", False
    if isinstance(exc, RuntimeError) and "document_response_parse_failed" in str(exc):
        return nrc_aps_safeguards.APS_CLASS_JSON_MALFORMED, False
    if isinstance(exc, RuntimeError) and (
        "artifact_download_failed" in str(exc)
        or "file_size_limit_exceeded" in str(exc)
        or "redirect_policy_violation" in str(exc)
        or "artifact_" in str(exc)
    ):
        return nrc_aps_safeguards.APS_CLASS_DOWNLOAD_FAILURE, False
    return _classify_http_exception(exc)


def _expected_discovery_ref(run_id: str) -> str:
    return str(Path(settings.connector_manifests_dir) / f"{run_id}_discovery.json")


def _expected_selection_ref(run_id: str) -> str:
    return str(Path(settings.connector_manifests_dir) / f"{run_id}_selection.json")


def _write_download_exchange(
    *,
    run_id: str,
    target_id: str,
    phase: str,
    payload: dict[str, Any],
) -> str:
    path = Path(settings.connector_snapshots_dir) / f"{run_id}_{target_id}_{phase}_download_exchange.json"
    return _write_json(path, payload)


def _write_target_ingestion_artifact(
    *,
    run_id: str,
    target_id: str,
    payload: dict[str, Any],
) -> str:
    report_path = _target_artifact_report_path(run_id, target_id)
    return nrc_aps_artifact_ingestion.write_json_atomic(report_path, payload)


def _build_artifact_base_evidence(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    metadata_ref: str,
) -> dict[str, Any]:
    source_ref = dict(target.source_reference_json or {})
    return {
        "discovery_ref": str(source_ref.get("search_exchange_ref") or _expected_discovery_ref(run.connector_run_id)),
        "selection_ref": str(source_ref.get("selection_ref") or _expected_selection_ref(run.connector_run_id)),
        "url_fields_checked": ["aps_normalized.url", "target.sciencebase_download_uri"],
    }


def _artifact_target_context(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    pipeline_mode: str,
    artifact_required_for_target_success: bool,
    metadata_ref: str,
) -> dict[str, Any]:
    return {
        "run_id": run.connector_run_id,
        "target_id": target.connector_run_target_id,
        "accession_number": target.sciencebase_item_id or None,
        "pipeline_mode": pipeline_mode,
        "artifact_required_for_target_success": bool(artifact_required_for_target_success),
        "source_metadata_ref": metadata_ref,
        "evidence": _build_artifact_base_evidence(run=run, target=target, metadata_ref=metadata_ref),
    }


def _emit_artifact_target_payload(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    payload: dict[str, Any],
) -> str:
    try:
        return _write_target_ingestion_artifact(
            run_id=run.connector_run_id,
            target_id=target.connector_run_target_id,
            payload=payload,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"{nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_WRITE_FAILED}:{exc.__class__.__name__}:{exc}"
        ) from exc


def _run_target_artifact_pipeline(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    client: NrcAdamsApsClient,
    config: dict[str, Any],
    normalized_document: dict[str, Any],
    metadata_ref: str,
) -> dict[str, Any]:
    mode = nrc_aps_artifact_ingestion.normalize_pipeline_mode(config.get("artifact_pipeline_mode"))
    required = nrc_aps_artifact_ingestion.resolve_artifact_required_for_target_success(
        mode,
        config.get("artifact_required_for_target_success"),
    )
    context = _artifact_target_context(
        run=run,
        target=target,
        pipeline_mode=mode,
        artifact_required_for_target_success=required,
        metadata_ref=metadata_ref,
    )
    if mode == nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_OFF:
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": False,
            "target_artifact_ref": None,
            "failure_code": None,
            "download_result": None,
            "blob_ref": None,
            "target_updates": {},
            "metrics": {"artifact_pipeline_mode": mode},
        }

    artifact_url = str(normalized_document.get("url") or target.sciencebase_download_uri or "").strip()
    if not artifact_url:
        availability_reason = "no_url_in_metadata"
        if required:
            failure_payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
                **context,
                outcome_status="failed",
                target_success=False,
                availability_reason=availability_reason,
                failure={
                    "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_URL_MISSING,
                    "stage": "download",
                    "message": "artifact URL missing in metadata",
                    "error_class": "artifact_url_missing",
                    "evidence": {
                        "url_fields_checked": list(context["evidence"].get("url_fields_checked") or []),
                        "availability_reason": availability_reason,
                    },
                },
            )
            target_ref = _emit_artifact_target_payload(run=run, target=target, payload=failure_payload)
            return {
                "mode": mode,
                "required": required,
                "should_fail_target": True,
                "target_artifact_ref": target_ref,
                "failure_code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_URL_MISSING,
                "download_result": None,
                "blob_ref": None,
                "target_updates": {},
                "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "failed"},
            }

        not_available_payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status=nrc_aps_artifact_ingestion.APS_ARTIFACT_OUTCOME_NOT_AVAILABLE,
            target_success=True,
            availability_reason=availability_reason,
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=not_available_payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": False,
            "target_artifact_ref": target_ref,
            "failure_code": None,
            "download_result": None,
            "blob_ref": None,
            "target_updates": {},
            "metrics": {
                "artifact_pipeline_mode": mode,
                "artifact_outcome_status": nrc_aps_artifact_ingestion.APS_ARTIFACT_OUTCOME_NOT_AVAILABLE,
            },
        }

    reason = _precheck_download_url(artifact_url, list(config.get("allowed_hosts", APS_DEFAULT_ALLOWED_HOSTS)))
    if reason:
        failure_payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status="failed",
            target_success=False,
            failure={
                "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_DOWNLOAD_FAILED,
                "stage": "download",
                "message": reason,
                "error_class": "download_precheck_failed",
                "evidence": {
                    "download_exchange_ref": None,
                    "attempt_count": 1,
                    "error_class": "download_precheck_failed",
                },
            },
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=failure_payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": bool(required),
            "target_artifact_ref": target_ref,
            "failure_code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_DOWNLOAD_FAILED if required else None,
            "download_result": None,
            "blob_ref": None,
            "target_updates": {},
            "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "failed"},
        }

    download_result: ApsDownloadResult | None = None
    download_exchange_ref: str | None = None
    try:
        download_result = client.download_artifact(
            artifact_url,
            max_redirects=int(config.get("max_redirects", settings.connector_max_redirects)),
            max_file_bytes=int(config.get("max_file_bytes", 64 * 1024 * 1024)),
        )
        download_exchange_ref = _write_download_exchange(
            run_id=run.connector_run_id,
            target_id=target.connector_run_target_id,
            phase="success",
            payload={
                "request_url": artifact_url,
                "status_code": int(download_result.status_code),
                "final_url": str(download_result.final_url),
                "content_type": str(download_result.content_type or ""),
                "bytes": len(download_result.content),
                "sha256": str(download_result.sha256),
            },
        )
    except ApsArtifactSizeLimitExceeded as size_exc:
        download_exchange_ref = _write_download_exchange(
            run_id=run.connector_run_id,
            target_id=target.connector_run_target_id,
            phase="size_limit",
            payload={
                "request_url": artifact_url,
                "error_class": size_exc.__class__.__name__,
                "error_message": str(size_exc),
                "max_file_bytes": size_exc.max_file_bytes,
                "bytes_received_before_abort": size_exc.bytes_received_before_abort,
                "content_length_header": size_exc.content_length_header,
                "overrun_phase": size_exc.overrun_phase,
            },
        )
        failure_payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status="failed",
            target_success=False,
            failure={
                "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_SIZE_LIMIT_EXCEEDED,
                "stage": "download",
                "message": str(size_exc),
                "error_class": size_exc.__class__.__name__,
                "evidence": {
                    "max_file_bytes": size_exc.max_file_bytes,
                    "bytes_received_before_abort": size_exc.bytes_received_before_abort,
                    "content_length_header": size_exc.content_length_header,
                    "overrun_phase": size_exc.overrun_phase,
                    "download_exchange_ref": download_exchange_ref,
                },
            },
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=failure_payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": bool(required),
            "target_artifact_ref": target_ref,
            "failure_code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_SIZE_LIMIT_EXCEEDED if required else None,
            "download_result": None,
            "blob_ref": None,
            "target_updates": {},
            "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "failed"},
        }
    except Exception as exc:  # noqa: BLE001
        download_exchange_ref = _write_download_exchange(
            run_id=run.connector_run_id,
            target_id=target.connector_run_target_id,
            phase="failed",
            payload={
                "request_url": artifact_url,
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        failure_payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status="failed",
            target_success=False,
            failure={
                "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_DOWNLOAD_FAILED,
                "stage": "download",
                "message": str(exc),
                "error_class": exc.__class__.__name__,
                "evidence": {
                    "download_exchange_ref": download_exchange_ref,
                    "attempt_count": 1,
                    "error_class": exc.__class__.__name__,
                    "http_status": getattr(getattr(exc, "response", None), "status_code", None),
                    "final_url": artifact_url,
                },
            },
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=failure_payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": bool(required),
            "target_artifact_ref": target_ref,
            "failure_code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_DOWNLOAD_FAILED if required else None,
            "download_result": None,
            "blob_ref": None,
            "target_updates": {},
            "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "failed"},
        }

    if download_result is None:
        raise RuntimeError("artifact_download_failed")

    run.consumed_bytes = int(run.consumed_bytes or 0) + len(download_result.content)
    if int(run.consumed_bytes or 0) > int(config.get("max_run_bytes", 512 * 1024 * 1024)):
        run.budget_exhausted = True
        raise RuntimeError("budget_exhausted_after_download")

    blob_info = nrc_aps_artifact_ingestion.write_blob_content_addressed(
        raw_root=settings.connector_raw_dir,
        content=download_result.content,
    )
    target_updates: dict[str, Any] = {
        "raw_storage_ref": str(blob_info.get("blob_ref") or ""),
        "downloaded_sha256": str(blob_info.get("blob_sha256") or download_result.sha256),
        "redirect_count": int(download_result.redirect_count),
        "etag": download_result.etag,
        "last_modified": download_result.last_modified,
        "downloaded_at": _utcnow(),
    }

    if mode == nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_DOWNLOAD_ONLY:
        payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status="downloaded",
            target_success=True,
            download={
                "url": artifact_url,
                "download_exchange_ref": download_exchange_ref,
                "content_type": str(download_result.content_type or ""),
                **blob_info,
            },
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": False,
            "target_artifact_ref": target_ref,
            "failure_code": None,
            "download_result": download_result,
            "blob_ref": blob_info.get("blob_ref"),
            "target_updates": target_updates,
            "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "downloaded"},
        }

    detected_content_type = nrc_aps_artifact_ingestion.normalize_content_type(download_result.content_type)
    if detected_content_type not in nrc_aps_artifact_ingestion.APS_SUPPORTED_CONTENT_TYPES:
        payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status="failed",
            target_success=False,
            download={
                "url": artifact_url,
                "download_exchange_ref": download_exchange_ref,
                "content_type": detected_content_type,
                **blob_info,
            },
            failure={
                "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE,
                "stage": "hydrate",
                "message": f"unsupported content type: {detected_content_type or 'unknown'}",
                "error_class": "unsupported_content_type",
                "evidence": {
                    "detected_content_type": detected_content_type,
                    "allowed_content_types": sorted(nrc_aps_artifact_ingestion.APS_SUPPORTED_CONTENT_TYPES),
                    "blob_ref": blob_info.get("blob_ref"),
                },
            },
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": bool(required),
            "target_artifact_ref": target_ref,
            "failure_code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE if required else None,
            "download_result": download_result,
            "blob_ref": blob_info.get("blob_ref"),
            "target_updates": target_updates,
            "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "failed"},
        }

    try:
        extraction = nrc_aps_artifact_ingestion.extract_and_normalize(
            content=download_result.content,
            content_type=detected_content_type,
        )
    except ValueError as exc:
        payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status="failed",
            target_success=False,
            download={
                "url": artifact_url,
                "download_exchange_ref": download_exchange_ref,
                "content_type": detected_content_type,
                **blob_info,
            },
            failure={
                "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_EXTRACTION_FAILED,
                "stage": "extract",
                "message": str(exc),
                "error_class": exc.__class__.__name__,
                "evidence": {
                    "blob_ref": blob_info.get("blob_ref"),
                    "extractor_id": (
                        nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_ID
                        if detected_content_type == "application/pdf"
                        else nrc_aps_artifact_ingestion.APS_TEXT_EXTRACTOR_ID
                    ),
                    "extractor_version": (
                        nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_VERSION
                        if detected_content_type == "application/pdf"
                        else nrc_aps_artifact_ingestion.APS_TEXT_EXTRACTOR_VERSION
                    ),
                    "error_class": exc.__class__.__name__,
                },
            },
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": bool(required),
            "target_artifact_ref": target_ref,
            "failure_code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_EXTRACTION_FAILED if required else None,
            "download_result": download_result,
            "blob_ref": blob_info.get("blob_ref"),
            "target_updates": target_updates,
            "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "failed"},
        }
    except Exception as exc:  # noqa: BLE001
        payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
            **context,
            outcome_status="failed",
            target_success=False,
            download={
                "url": artifact_url,
                "download_exchange_ref": download_exchange_ref,
                "content_type": detected_content_type,
                **blob_info,
            },
            failure={
                "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_NORMALIZATION_FAILED,
                "stage": "normalize",
                "message": str(exc),
                "error_class": exc.__class__.__name__,
                "evidence": {
                    "extractor_id": (
                        nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_ID
                        if detected_content_type == "application/pdf"
                        else nrc_aps_artifact_ingestion.APS_TEXT_EXTRACTOR_ID
                    ),
                    "extractor_version": (
                        nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_VERSION
                        if detected_content_type == "application/pdf"
                        else nrc_aps_artifact_ingestion.APS_TEXT_EXTRACTOR_VERSION
                    ),
                    "normalization_contract_id": nrc_aps_artifact_ingestion.APS_TEXT_NORMALIZATION_CONTRACT_ID,
                    "error_class": exc.__class__.__name__,
                },
            },
        )
        target_ref = _emit_artifact_target_payload(run=run, target=target, payload=payload)
        return {
            "mode": mode,
            "required": required,
            "should_fail_target": bool(required),
            "target_artifact_ref": target_ref,
            "failure_code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_NORMALIZATION_FAILED if required else None,
            "download_result": download_result,
            "blob_ref": blob_info.get("blob_ref"),
            "target_updates": target_updates,
            "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "failed"},
        }

    normalized_blob = _write_normalized_text_blob(text=str(extraction.get("normalized_text") or ""))
    target_updates["ingested_at"] = _utcnow()
    payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
        **context,
        outcome_status="processed",
        target_success=True,
        download={
            "url": artifact_url,
            "download_exchange_ref": download_exchange_ref,
            "content_type": detected_content_type,
            **blob_info,
        },
        extraction={
            "extractor_id": extraction.get("extractor_id"),
            "extractor_version": extraction.get("extractor_version"),
            "normalization_contract_id": extraction.get("normalization_contract_id"),
            "normalized_char_count": extraction.get("normalized_char_count"),
            "normalized_text_sha256": extraction.get("normalized_text_sha256"),
            "normalized_text_ref": normalized_blob.get("normalized_text_ref"),
        },
    )
    target_ref = _emit_artifact_target_payload(run=run, target=target, payload=payload)
    return {
        "mode": mode,
        "required": required,
        "should_fail_target": False,
        "target_artifact_ref": target_ref,
        "failure_code": None,
        "download_result": download_result,
        "blob_ref": blob_info.get("blob_ref"),
        "target_updates": target_updates,
        "metrics": {"artifact_pipeline_mode": mode, "artifact_outcome_status": "processed"},
    }


def _write_raw_blob(run: ConnectorRun, target: ConnectorRunTarget, content: bytes) -> str:
    stored = nrc_aps_artifact_ingestion.write_blob_content_addressed(
        raw_root=settings.connector_raw_dir,
        content=content,
    )
    return str(stored.get("blob_ref") or "")


def _write_normalized_text_blob(*, text: str) -> dict[str, Any]:
    content = str(text or "").encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    base = Path(settings.artifact_storage_dir) / "nrc_adams_aps" / "normalized_text" / digest[0:2] / digest[2:4]
    base.mkdir(parents=True, exist_ok=True)
    out = base / f"{digest}.txt"
    if not out.exists():
        temp = out.with_name(f".{out.name}.{uuid.uuid4().hex}.tmp")
        temp.write_bytes(content)
        os.replace(temp, out)
    return {
        "normalized_text_ref": str(out),
        "normalized_text_sha256": digest,
        "normalized_text_bytes": len(content),
    }


def _build_exchange_payload(
    *,
    request_id: str,
    endpoint: str,
    request_url: str,
    request_headers: dict[str, Any],
    request_body: Any,
    sent_at: datetime,
    response_status: int,
    response_headers: dict[str, Any],
    response_body_text: str,
    received_at: datetime,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key_hash = hashlib.sha256((settings.nrc_adams_subscription_key or "").encode("utf-8")).hexdigest() if settings.nrc_adams_subscription_key else None
    payload_hash = hashlib.sha256(
        json.dumps(request_body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return {
        "request_log": {
            "request_id": request_id,
            "endpoint": endpoint,
            "subscription_key_hash": key_hash,
            "payload_hash": payload_hash,
            "sent_at": sent_at.isoformat(),
            "request_url": request_url,
            "request_headers_subset": request_headers,
            "request_body": request_body,
        },
        "response_log": {
            "request_id": request_id,
            "status_code": response_status,
            "received_at": received_at.isoformat(),
            "response_headers": response_headers,
            "raw_body_text": response_body_text,
            "metadata": metadata or {},
        },
    }


def _create_target_for_hit(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    ordinal: int,
    hit: dict[str, Any],
    source_reference_json: dict[str, Any],
) -> ConnectorRunTarget:
    projection = dict(hit.get("projection") or {})
    accession = str(projection.get("accession_number") or "").strip()
    title = str(projection.get("document_title") or accession or "adams_document")
    artifact_url = str(projection.get("url") or "").strip() or None
    source_key = f"nrc_adams_aps::{accession}" if accession else f"nrc_adams_aps::{uuid.uuid4().hex}"

    target = ConnectorRunTarget(
        connector_run_id=run.connector_run_id,
        ordinal=ordinal,
        stable_release_key=accession or source_key,
        stable_release_identifier=f"adams_accession:{accession}" if accession else source_key,
        identifiers_json=[{"type": "AccessionNumber", "value": accession}] if accession else [],
        sciencebase_item_id=accession or None,
        sciencebase_item_url=f"{settings.nrc_adams_api_base_url.rstrip('/')}/aps/api/search/{accession}" if accession else None,
        sciencebase_file_name=title,
        sciencebase_download_uri=artifact_url,
        artifact_surface="files",
        selection_source="aps_results",
        selection_scope="search_hit",
        selection_match_basis="aps_query",
        artifact_locator_type="document.Url" if artifact_url else None,
        source_artifact_key=source_key,
        canonical_artifact_key=source_key,
        source_reference_json=source_reference_json,
        permission_snapshot_json={},
        access_level_summary="public_or_unknown",
        public_read_confirmed=False,
        fetch_policy_mode="strict_public_safe",
        status="discovered",
        discovered_at=_utcnow(),
        last_stage_transition_at=_utcnow(),
        retry_eligible=False,
    )
    db.add(target)
    db.flush()
    transition_target_state(
        db,
        run=run,
        target=target,
        status_after="selected",
        phase="target_creation",
        stage="target_creation",
        event_type="target_selected",
        created=True,
        operator_reason_code="selected_metadata_record",
        retry_eligible=False,
        target_updates={"selected_at": _utcnow()},
        assert_lease=_assert_active_lease,
        lease_token=lease_token,
    )
    return target


def _process_target_metadata(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    client: NrcAdamsApsClient,
    target: ConnectorRunTarget,
    hit: dict[str, Any],
    config: dict[str, Any],
) -> None:
    _assert_active_lease(run, lease_token)
    projection = dict(hit.get("projection") or {})
    normalized_document = {"source": "search_hit", **projection}
    request_exchange_refs: list[str] = []

    if bool(config.get("include_document_details", True)) and target.sciencebase_item_id:
        request_id = uuid.uuid4().hex
        sent_at = _utcnow()
        response = client.get_document(target.sciencebase_item_id)
        received_at = _utcnow()
        response_payload, parse_status = _parse_json_response(response)
        normalized_doc_payload = _normalize_document_response(response_payload or {})
        exchange = _build_exchange_payload(
            request_id=request_id,
            endpoint="GET /aps/api/search/{AccessionNumber}",
            request_url=str(response.request.url) if response.request else f"{settings.nrc_adams_api_base_url.rstrip('/')}/aps/api/search/{target.sciencebase_item_id}",
            request_headers={"Accept": "application/json"},
            request_body={},
            sent_at=sent_at,
            response_status=int(response.status_code),
            response_headers=dict(response.headers),
            response_body_text=response.text,
            received_at=received_at,
            metadata={
                "schema_variant": normalized_doc_payload.get("wrapper_variant"),
                "parse_status": parse_status,
            },
        )
        exchange_path = _write_json(
            Path(settings.connector_snapshots_dir) / f"{run.connector_run_id}_{request_id}_document_exchange.json",
            exchange,
        )
        request_exchange_refs.append(exchange_path)
        parse_failure = str(parse_status or "").strip().lower() in nrc_aps_safeguards.APS_PARSE_FAILURE_STATUSES
        if parse_failure and hasattr(client, "record_parse_failure"):
            client.record_parse_failure(
                parse_status=parse_status,
                call_class="document",
                status_code=int(response.status_code),
                scope_key=f"document:{target.sciencebase_item_id}",
                exchange_ref=exchange_path,
            )
        if int(response.status_code) >= 400:
            response.raise_for_status()
        if response_payload is None or parse_failure:
            raise RuntimeError(f"document_response_parse_failed:{parse_status}")
        normalized_document.update(normalized_doc_payload.get("projection") or {})

    run_mode = str(config.get("run_mode", "metadata_only"))
    if run_mode == "dry_run":
        transition_target_state(
            db,
            run=run,
            target=target,
            status_after="dry_run_skipped",
            phase="indexing",
            stage="indexing",
            event_type="target_dry_run_skipped",
            operator_reason_code="dry_run_metadata_only",
            retry_eligible=False,
            target_updates={
                "source_reference_json": {
                    **(target.source_reference_json or {}),
                    "aps_normalized": normalized_document,
                    "exchange_refs": request_exchange_refs,
                    "mapper_version": str(config.get("mapper_version", APS_MAPPER_VERSION)),
                },
                "error_stage": None,
                "error_message": None,
                "last_error_class": None,
            },
            assert_lease=_assert_active_lease,
            lease_token=lease_token,
        )
        return

    artifact_url = str(normalized_document.get("url") or target.sciencebase_download_uri or "").strip()
    artifact_payload = {
        "provider": "nrc_adams_aps",
        "accession_number": normalized_document.get("accession_number"),
        "document_title": normalized_document.get("document_title"),
        "document_type": normalized_document.get("document_type"),
        "document_date": normalized_document.get("document_date"),
        "date_added_timestamp": normalized_document.get("date_added_timestamp"),
        "url": artifact_url or None,
        "docket_number": normalized_document.get("docket_number"),
        "content_present": bool(normalized_document.get("content_present")),
        "content_source_path": normalized_document.get("content_source_path"),
        "retention_allowed": "unknown",
        "captured_at": _utcnow().isoformat(),
        "raw_exchange_refs": request_exchange_refs,
    }

    metadata_ref = _write_json(
        Path(settings.connector_manifests_dir) / f"{run.connector_run_id}_{target.connector_run_target_id}_aps_metadata.json",
        artifact_payload,
    )
    artifact_pipeline = _run_target_artifact_pipeline(
        run=run,
        target=target,
        client=client,
        config=config,
        normalized_document=normalized_document,
        metadata_ref=metadata_ref,
    )
    target_artifact_ref = str(artifact_pipeline.get("target_artifact_ref") or "").strip() or None
    if target_artifact_ref:
        target.source_reference_json = {
            **(target.source_reference_json or {}),
            "aps_artifact_ingestion_ref": target_artifact_ref,
            "aps_artifact_pipeline_mode": artifact_pipeline.get("mode"),
            "aps_artifact_required_for_target_success": bool(artifact_pipeline.get("required")),
            "aps_artifact_outcome_status": artifact_pipeline.get("metrics", {}).get("artifact_outcome_status"),
        }
        db.flush()
    if artifact_pipeline.get("should_fail_target"):
        failure_code = str(artifact_pipeline.get("failure_code") or "artifact_pipeline_failed")
        raise RuntimeError(failure_code)

    download_result = artifact_pipeline.get("download_result")
    if download_result:
        artifact_payload["sha256"] = download_result.sha256
        artifact_payload["bytes"] = len(download_result.content)
        artifact_payload["fetched_at"] = _utcnow().isoformat()
        artifact_payload["http_status"] = download_result.status_code
        artifact_payload["content_type"] = download_result.content_type
        artifact_payload["auth_required"] = download_result.auth_required

    if artifact_payload.get("sha256"):
        _write_json(
            Path(settings.connector_manifests_dir) / f"{run.connector_run_id}_{target.connector_run_target_id}_aps_metadata.json",
            artifact_payload,
        )
    updates: dict[str, Any] = {
        "sciencebase_file_name": str(normalized_document.get("document_title") or target.sciencebase_file_name or ""),
        "sciencebase_download_uri": artifact_url or target.sciencebase_download_uri,
        "source_reference_json": {
            **(target.source_reference_json or {}),
            "aps_normalized": normalized_document,
            "metadata_ref": metadata_ref,
            "exchange_refs": request_exchange_refs,
            "mapper_version": str(config.get("mapper_version", APS_MAPPER_VERSION)),
            "aps_artifact_ingestion_ref": target_artifact_ref,
            "aps_artifact_pipeline_mode": artifact_pipeline.get("mode"),
            "aps_artifact_required_for_target_success": bool(artifact_pipeline.get("required")),
            "aps_artifact_outcome_status": artifact_pipeline.get("metrics", {}).get("artifact_outcome_status"),
        },
        "error_stage": None,
        "error_message": None,
        "last_error_class": None,
    }
    updates.update(dict(artifact_pipeline.get("target_updates") or {}))

    transition_target_state(
        db,
        run=run,
        target=target,
        status_after="recommended",
        phase="indexing",
        stage="indexing",
        event_type="target_metadata_indexed",
        operator_reason_code="metadata_indexed",
        retry_eligible=False,
        target_updates=updates,
        metrics_json={
            "artifact_downloaded": bool(download_result),
            "artifact_bytes": len(download_result.content) if download_result else 0,
            "artifact_pipeline_mode": artifact_pipeline.get("mode"),
            "artifact_required_for_target_success": bool(artifact_pipeline.get("required")),
            "artifact_outcome_status": artifact_pipeline.get("metrics", {}).get("artifact_outcome_status"),
        },
        assert_lease=_assert_active_lease,
        lease_token=lease_token,
    )


def execute_nrc_adams_run(connector_run_id: str) -> None:
    db = SessionLocal()
    NRC_EXECUTOR_GUARDS.acquire_run_slot()
    client: Any | None = None
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
        lease_token = run.execution_lease_token
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
        client = get_nrc_adams_client(config)
        wire_shape_mode = _enum_wire_shape_mode(config.get("wire_shape_mode"), default="auto_probe")
        base_logical_query = _logical_query_from_config(config)
        runtime_logical_query, sync_runtime_meta = _resolve_runtime_logical_query(
            db,
            base_logical_query=base_logical_query,
            config=config,
        )
        traversal_defaults = dict(config.get("traversal_defaults") or {})
        skip = max(0, _coerce_int(traversal_defaults.get("initial_skip", 0), 0))
        page_size = max(1, min(_coerce_int(config.get("page_size", 100), 100), 100))
        effective_take = max(1, min(_coerce_int(traversal_defaults.get("default_take", page_size), page_size), 100))
        max_items = int(config.get("max_items", 0))
        subscription_key_hash = str(config.get("subscription_key_hash") or client.subscription_key_hash)
        api_host = str(config.get("api_host") or client.api_host)
        dialect_order = _preferred_dialect_order(
            db,
            subscription_key_hash=subscription_key_hash,
            api_host=api_host,
            forced_mode=wire_shape_mode,
        )
        wire_payload_candidates = _build_wire_payload_candidates(
            runtime_logical_query,
            dialect_order=dialect_order,
            skip=skip,
            take=effective_take,
        )

        run.effective_search_params_json = {
            "mode": config.get("mode"),
            "wire_shape_mode": wire_shape_mode,
            "wire_shape_candidates": [item.get("wire_shape") for item in wire_payload_candidates],
            "mapper_version": config.get("mapper_version"),
            "compiler_version": config.get("compiler_version", APS_COMPILER_VERSION),
            "logical_query": _logical_query_dict(runtime_logical_query),
            "mapper_warnings": config.get("mapper_warnings", []),
            "lint_warnings": config.get("lint_warnings", []),
            "sync_metadata": sync_runtime_meta,
            "safeguard_effective_config": _safeguard_effective_config(config),
        }
        run.effective_filters_json = [_strip_internal_fields(dict(item or {})) for item in runtime_logical_query.properties]
        run.effective_sort = runtime_logical_query.sort_field
        run.effective_order = "desc" if int(runtime_logical_query.sort_direction) == 1 else "asc"
        run.effective_page_size = page_size
        db.commit()

        _record_run_event(
            db,
            run=run,
            event_type="mapping_applied",
            phase="planning",
            status_after=run.status,
            metrics_json={
                "mapper_version": config.get("mapper_version"),
                "warnings": config.get("mapper_warnings", []),
                "lint_warnings": config.get("lint_warnings", []),
                "compiler_version": config.get("compiler_version", APS_COMPILER_VERSION),
                "safeguard_policy_hash": config.get("safeguard_policy_hash"),
            },
            commit=True,
        )
        observed_schema_variants: dict[str, int] = {}
        accession_seen: set[str] = set()
        search_exchange_refs: list[str] = []
        discovery_pages: list[dict[str, Any]] = []
        selection_targets: list[dict[str, Any]] = []
        ordinal = 0
        page_index = 0
        max_observed_watermark: datetime | None = None

        while True:
            db.refresh(run)
            _assert_active_lease(run, lease_token)
            if run.cancellation_requested_at:
                run.status = "cancelling"
                _record_run_event(
                    db,
                    run=run,
                    event_type="run_cancelling",
                    phase="finalizing",
                    status_after=run.status,
                )
                db.commit()
                break
            if max_items > 0 and len(accession_seen) >= max_items:
                run.search_exhaustion_reason = "max_items_cap"
                db.commit()
                break

            wire_payload_candidates = _build_wire_payload_candidates(
                runtime_logical_query,
                dialect_order=dialect_order,
                skip=skip,
                take=effective_take,
            )
            page_attempts: list[dict[str, Any]] = []
            selected_wire_shape = "unknown"
            selected_outbound_payload: dict[str, Any] | None = None
            selected_exchange_ref: str | None = None
            selected_schema_variant = "unknown"
            selected_normalized_search: dict[str, Any] | None = None

            for attempt_index, candidate in enumerate(wire_payload_candidates, start=1):
                outbound_payload = dict(candidate.get("payload") or {})
                wire_shape = str(candidate.get("wire_shape") or "unknown")
                take_sent = max(1, _coerce_int(outbound_payload.get("take", effective_take), effective_take))

                request_id = uuid.uuid4().hex
                sent_at = _utcnow()
                search_scope = f"search:{skip}:{wire_shape}:{take_sent}"
                try:
                    response = client.search(outbound_payload, scope_key=search_scope)
                except TypeError:
                    # Backward compatibility for test doubles that still expose search(payload) only.
                    response = client.search(outbound_payload)
                received_at = _utcnow()
                response_payload, parse_status = _parse_json_response(response)
                normalized_search = _normalize_search_response(response_payload or {})
                schema_variant = str(normalized_search.get("schema_variant") or "unknown")
                observed_schema_variants[schema_variant] = int(observed_schema_variants.get(schema_variant, 0)) + 1
                parse_failure = str(parse_status or "").strip().lower() in nrc_aps_safeguards.APS_PARSE_FAILURE_STATUSES

                exchange = _build_exchange_payload(
                    request_id=request_id,
                    endpoint="POST /aps/api/search",
                    request_url=str(response.request.url) if response.request else f"{settings.nrc_adams_api_base_url.rstrip('/')}/aps/api/search",
                    request_headers={"Content-Type": "application/json", "Accept": "application/json"},
                    request_body=outbound_payload,
                    sent_at=sent_at,
                    response_status=int(response.status_code),
                    response_headers=dict(response.headers),
                    response_body_text=response.text,
                    received_at=received_at,
                    metadata={
                        "wire_shape": wire_shape,
                        "attempt_index": attempt_index,
                        "parse_status": parse_status,
                        "schema_variant_observed": schema_variant,
                        "results_key_observed": normalized_search.get("results_key"),
                        "count_returned": normalized_search.get("count_returned"),
                        "total_hits": normalized_search.get("total_hits"),
                        "raw_total_key": normalized_search.get("raw_total_key"),
                    },
                )
                exchange_ref = _write_json(
                    Path(settings.connector_snapshots_dir) / f"{run.connector_run_id}_{request_id}_search_exchange.json",
                    exchange,
                )
                search_exchange_refs.append(exchange_ref)
                if parse_failure and hasattr(client, "record_parse_failure"):
                    client.record_parse_failure(
                        parse_status=parse_status,
                        call_class="search",
                        status_code=int(response.status_code),
                        scope_key=search_scope,
                        exchange_ref=exchange_ref,
                    )
                _upsert_capability_attempt(
                    db,
                    subscription_key_hash=subscription_key_hash,
                    api_host=api_host,
                    dialect=wire_shape,
                    status_code=int(response.status_code),
                    exchange_ref=exchange_ref,
                    parse_status=parse_status,
                    normalized_search=normalized_search,
                    take_sent=take_sent,
                )

                attempt_record = {
                    "attempt_index": attempt_index,
                    "wire_shape": wire_shape,
                    "status_code": int(response.status_code),
                    "parse_status": parse_status,
                    "parse_failure": parse_failure,
                    "schema_variant": schema_variant,
                    "results_key": normalized_search.get("results_key"),
                    "count_returned": normalized_search.get("count_returned"),
                    "total_hits": normalized_search.get("total_hits"),
                    "exchange_ref": exchange_ref,
                }
                page_attempts.append(attempt_record)

                if int(response.status_code) < 400 and not parse_failure:
                    selected_wire_shape = wire_shape
                    selected_outbound_payload = outbound_payload
                    selected_exchange_ref = exchange_ref
                    selected_schema_variant = schema_variant
                    selected_normalized_search = normalized_search
                    break

                if int(response.status_code) < 400 and parse_failure:
                    if attempt_index < len(wire_payload_candidates):
                        _record_run_event(
                            db,
                            run=run,
                            event_type="search_shape_fallback",
                            phase="planning",
                            stage="search",
                            status_after=run.status,
                            reason_code="parse_failure_no_retry",
                            message=f"wire_shape={wire_shape} parse_status={parse_status}",
                            metrics_json={
                                "attempt": attempt_index,
                                "wire_shape": wire_shape,
                                "status_code": int(response.status_code),
                                "parse_status": parse_status,
                            },
                            commit=True,
                        )
                        continue
                    raise RuntimeError(f"search_parse_failed:{parse_status}")

                if attempt_index < len(wire_payload_candidates):
                    _record_run_event(
                        db,
                        run=run,
                        event_type="search_shape_fallback",
                        phase="planning",
                        stage="search",
                        status_after=run.status,
                        message=f"wire_shape={wire_shape} status={response.status_code}",
                        metrics_json={"attempt": attempt_index, "wire_shape": wire_shape, "status_code": int(response.status_code)},
                        commit=True,
                    )
                    continue

                response.raise_for_status()

            if not selected_normalized_search or not selected_outbound_payload or not selected_exchange_ref:
                raise RuntimeError("search_response_not_selected")

            hits = list(selected_normalized_search.get("hits") or [])
            run.adapter_dialect = selected_wire_shape
            run.page_count_completed = int(run.page_count_completed or 0) + 1
            run.last_offset_committed = skip
            run.next_page_available = bool(hits)
            db.commit()
            discovery_pages.append(
                {
                    "offset": skip,
                    "take": int(selected_outbound_payload.get("take") or page_size),
                    "wire_shape": selected_wire_shape,
                    "schema_variant": selected_schema_variant,
                    "results_key": selected_normalized_search.get("results_key"),
                    "count_returned": len(hits),
                    "total_hits": selected_normalized_search.get("total_hits"),
                    "exchange_ref": selected_exchange_ref,
                    "attempts": page_attempts,
                }
            )

            if not hits:
                run.search_exhaustion_reason = run.search_exhaustion_reason or "no_more_pages"
                db.commit()
                break

            for hit in hits:
                projection = dict(hit.get("projection") or {})
                watermark = _parse_iso_datetime(projection.get("date_added_timestamp"))
                if watermark and (max_observed_watermark is None or watermark > max_observed_watermark):
                    max_observed_watermark = watermark
                accession = str(projection.get("accession_number") or "").strip()
                if not accession or accession in accession_seen:
                    continue
                accession_seen.add(accession)
                ordinal += 1
                target = _create_target_for_hit(
                    db,
                    run=run,
                    lease_token=lease_token,
                    ordinal=ordinal,
                    hit=hit,
                    source_reference_json={
                        "search_exchange_ref": selected_exchange_ref,
                        "selection_ref": _expected_selection_ref(run.connector_run_id),
                        "schema_variant_observed": selected_schema_variant,
                        "wire_shape_observed": selected_wire_shape,
                        "provider": "nrc_adams_aps",
                    },
                )
                selection_targets.append(
                    {
                        "target_id": target.connector_run_target_id,
                        "item_id": target.sciencebase_item_id,
                        "name": target.sciencebase_file_name,
                        "surface": target.artifact_surface,
                        "status": target.status,
                        "reason": target.operator_reason_code,
                        "source_artifact_key": target.source_artifact_key,
                        "canonical_artifact_key": target.canonical_artifact_key,
                    }
                )
                try:
                    _process_target_metadata(
                        db,
                        run=run,
                        lease_token=lease_token,
                        client=client,
                        target=target,
                        hit=hit,
                        config=config,
                    )
                except Exception as exc:  # noqa: BLE001
                    error_class, retryable = _classify_target_exception(exc)
                    transition_target_state(
                        db,
                        run=run,
                        target=target,
                        status_after="download_failed",
                        phase="indexing",
                        stage="indexing",
                        event_type="target_indexing_failed",
                        operator_reason_code="metadata_indexing_failed",
                        error_class=error_class,
                        message=str(exc),
                        retry_eligible=retryable,
                        target_updates={
                            "error_stage": "indexing",
                            "error_message": str(exc),
                            "last_error_class": error_class,
                        },
                        assert_lease=_assert_active_lease,
                        lease_token=lease_token,
                    )
                _renew_lease(db, run)
                lease_token = run.execution_lease_token
                if max_items > 0 and len(accession_seen) >= max_items:
                    run.search_exhaustion_reason = "max_items_cap"
                    db.commit()
                    break

            if max_items > 0 and len(accession_seen) >= max_items:
                break

            skip += int(selected_outbound_payload.get("take") or page_size)
            page_index += 1
            run.partition_count_completed = page_index
            db.commit()

        run.discovery_snapshot_ref = _write_json(
            Path(settings.connector_manifests_dir) / f"{run.connector_run_id}_discovery.json",
            {
                "provider": "nrc_adams_aps",
                "logical_query": _logical_query_dict(runtime_logical_query),
                "logical_query_fingerprint": runtime_logical_query.identity_fingerprint,
                "page_size": page_size,
                "take": effective_take,
                "max_items": max_items,
                "search_exhaustion_reason": run.search_exhaustion_reason,
                "sync_metadata": sync_runtime_meta,
                "search_exchange_refs": search_exchange_refs,
                "pages": discovery_pages,
            },
        )
        run.selection_manifest_ref = _write_json(
            Path(settings.connector_manifests_dir) / f"{run.connector_run_id}_selection.json",
            {
                "provider": "nrc_adams_aps",
                "candidate_count": len(selection_targets),
                "selected_count": len(selection_targets),
                "targets": selection_targets,
            },
        )
        run.query_plan_json = {
            **(run.query_plan_json or {}),
            "aps_mapper_version": config.get("mapper_version"),
            "aps_compiler_version": config.get("compiler_version", APS_COMPILER_VERSION),
            "aps_comparison_contract_version": nrc_aps_sync_drift.APS_COMPARISON_CONTRACT_VERSION,
            "aps_projection_hash_contract": nrc_aps_sync_drift.APS_PROJECTION_HASH_CONTRACT,
            "aps_mapper_warnings": config.get("mapper_warnings", []),
            "aps_lint_warnings": config.get("lint_warnings", []),
            "aps_safeguard_policy_schema": config.get("safeguard_policy_schema"),
            "aps_safeguard_policy_hash": config.get("safeguard_policy_hash"),
            "aps_safeguard_effective_config": _safeguard_effective_config(config),
            "aps_wire_shape_mode": wire_shape_mode,
            "aps_dialect_order": dialect_order,
            "aps_observed_schema_variants": observed_schema_variants,
            "aps_sync_mode": config.get("sync_mode", "full_scan"),
            "aps_sync_metadata": sync_runtime_meta,
            "aps_logical_query_fingerprint": runtime_logical_query.identity_fingerprint,
            "aps_max_observed_watermark": _iso_utc(max_observed_watermark),
            "aps_artifact_pipeline_mode": config.get("artifact_pipeline_mode"),
            "aps_artifact_required_for_target_success": bool(config.get("artifact_required_for_target_success", False)),
            "aps_text_normalization_contract_id": nrc_aps_artifact_ingestion.APS_TEXT_NORMALIZATION_CONTRACT_ID,
            "aps_content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            "aps_chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            "aps_content_chunking_policy": {
                "chunk_size_chars": int(config.get("content_chunk_size_chars") or APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE),
                "chunk_overlap_chars": int(config.get("content_chunk_overlap_chars") or APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP),
                "min_chunk_chars": int(config.get("content_chunk_min_chars") or APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK),
            },
            "checkpoint": {
                "target_ordinal_completed": ordinal,
                "updated_at": _utcnow().isoformat(),
            },
        }
        db.commit()

        _finalize_run(db, run)
        artifact_ingestion_summary: dict[str, Any] | None = None
        try:
            artifact_run_ref = _persist_artifact_ingestion_run_artifact(
                db,
                run=run,
                config=config,
            )
            artifact_ingestion_summary = {
                "artifact_run_ref": artifact_run_ref,
                "pipeline_mode": config.get("artifact_pipeline_mode"),
            }
            _record_run_event(
                db,
                run=run,
                event_type="aps_artifact_ingestion_artifacts_generated",
                phase="finalizing",
                stage="reporting",
                status_after=run.status,
                metrics_json={
                    "aps_artifact_ingestion_ref": artifact_run_ref,
                    "pipeline_mode": config.get("artifact_pipeline_mode"),
                    "selected_targets": int(run.selected_count or 0),
                },
            )
        except Exception as artifact_exc:  # noqa: BLE001
            failure_ref = _persist_artifact_ingestion_failure_artifact(
                db,
                run=run,
                error=artifact_exc,
            )
            artifact_ingestion_summary = {
                "artifact_generation_failed": True,
                "failure_ref": failure_ref,
            }

        content_index_summary: dict[str, Any] | None = None
        if run.status in {"completed", "completed_with_errors"}:
            try:
                content_index_summary = _generate_content_index_artifacts(
                    db,
                    run=run,
                    config=config,
                )
                _record_run_event(
                    db,
                    run=run,
                    event_type="aps_content_index_artifacts_generated",
                    phase="finalizing",
                    stage="reporting",
                    status_after=run.status,
                    metrics_json={
                        "aps_content_index_ref": content_index_summary.get("run_ref"),
                        "aps_content_index_failure_ref": content_index_summary.get("failure_ref"),
                        "processed_targets": content_index_summary.get("processed_targets"),
                        "indexed_content_units": content_index_summary.get("indexed_content_units"),
                        "indexing_failures_count": content_index_summary.get("indexing_failures_count"),
                    },
                )
            except Exception as content_index_exc:  # noqa: BLE001
                failure_ref = _persist_content_index_failure_artifact(
                    db,
                    run=run,
                    error=content_index_exc,
                )
                content_index_summary = {
                    "artifact_generation_failed": True,
                    "failure_ref": failure_ref,
                }

        sync_drift_summary: dict[str, Any] | None = None
        if run.status in APS_SYNC_BASELINE_ELIGIBLE_STATUSES:
            try:
                sync_drift_summary = _generate_sync_drift_artifacts(db, run=run)
                _record_run_event(
                    db,
                    run=run,
                    event_type="aps_sync_drift_artifacts_generated",
                    phase="finalizing",
                    stage="reporting",
                    status_after=run.status,
                    metrics_json={
                        "baseline_resolution": sync_drift_summary.get("baseline_resolution"),
                        "baseline_run_id": sync_drift_summary.get("baseline_run_id"),
                        "comparison_status": sync_drift_summary.get("comparison_status"),
                        "finding_counts": sync_drift_summary.get("finding_counts", {}),
                    },
                )
            except Exception as artifact_exc:  # noqa: BLE001
                failure_ref = _persist_sync_drift_failure_artifact(
                    db,
                    run=run,
                    error=artifact_exc,
                )
                sync_drift_summary = {
                    "artifact_generation_failed": True,
                    "failure_ref": failure_ref,
                }

        _upsert_sync_cursor_after_run(
            db,
            run=run,
            logical_query_fingerprint=str(config.get("source_query_fingerprint") or ""),
            overlap_seconds=int(config.get("incremental_overlap_seconds", APS_DEFAULT_SYNC_OVERLAP_SECONDS) or APS_DEFAULT_SYNC_OVERLAP_SECONDS),
            reconciliation_lookback_days=int(config.get("reconciliation_lookback_days", APS_DEFAULT_RECONCILIATION_LOOKBACK_DAYS) or APS_DEFAULT_RECONCILIATION_LOOKBACK_DAYS),
            max_observed_watermark=_iso_utc(max_observed_watermark),
            sync_metadata={
                **sync_runtime_meta,
                "dialect_order": dialect_order,
                "observed_schema_variants": observed_schema_variants,
                "run_mode": config.get("run_mode"),
                "artifact_ingestion_summary": artifact_ingestion_summary or {},
                "content_index_summary": content_index_summary or {},
                "sync_drift_summary": sync_drift_summary or {},
            },
        )
        safeguard_events_emitted = 0
        safeguard_report_ref: str | None = None
        try:
            if client is not None:
                safeguard_events_emitted = _emit_safeguard_events(db, run=run, client=client)
            safeguard_report_ref = _persist_safeguard_report_artifact(
                db,
                run=run,
                config=config,
                client=client or {},
            )
        except Exception as safeguard_exc:  # noqa: BLE001
            run.error_summary = _append_error_summary_token(
                run.error_summary,
                token="aps_safeguard_artifact_generation_failed",
            )
            if run.status not in {"failed", "cancelled"}:
                run.status = "completed_with_errors"
            _record_run_event(
                db,
                run=run,
                event_type="aps_safeguard_artifact_failed",
                phase="finalizing",
                stage="reporting",
                status_after=run.status,
                error_class=safeguard_exc.__class__.__name__,
                message=str(safeguard_exc),
            )
        db.commit()
        _record_run_event(
            db,
            run=run,
            event_type="run_finalized",
            phase="finalizing",
            status_after=run.status,
            metrics_json={
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "aps_safeguard_report_ref": safeguard_report_ref,
                "aps_safeguard_events_emitted": safeguard_events_emitted,
                "aps_artifact_ingestion_report_ref": dict((run.query_plan_json or {}).get("aps_artifact_ingestion_report_refs") or {}).get("aps_artifact_ingestion"),
                "aps_artifact_ingestion_failure_ref": dict((run.query_plan_json or {}).get("aps_artifact_ingestion_report_refs") or {}).get("aps_artifact_ingestion_failure"),
                "aps_content_index_report_ref": dict((run.query_plan_json or {}).get("aps_content_index_report_refs") or {}).get("aps_content_index"),
                "aps_content_index_failure_ref": dict((run.query_plan_json or {}).get("aps_content_index_report_refs") or {}).get("aps_content_index_failure"),
            },
            commit=True,
        )
    except Exception as exc:  # noqa: BLE001
        run = db.get(ConnectorRun, connector_run_id)
        if run:
            run.status = "failed"
            if "lease_conflict" in str(exc):
                run.error_summary = "lease_conflict"
                error_class = "lease_conflict"
            else:
                run.error_summary = f"orchestrator_internal_error: {exc}"
                error_class = "orchestrator_internal_error"
            run.completed_at = _utcnow()
            _release_lease(run)
            _record_run_event(
                db,
                run=run,
                event_type="run_failed",
                phase="finalizing",
                status_after=run.status,
                error_class=error_class,
                message=str(exc),
            )
            config = dict(run.request_config_json or {})
            try:
                if client is not None:
                    _emit_safeguard_events(db, run=run, client=client)
                _persist_safeguard_report_artifact(
                    db,
                    run=run,
                    config=config,
                    client=client or {},
                    run_error=exc,
                )
            except Exception as safeguard_exc:  # noqa: BLE001
                run.error_summary = _append_error_summary_token(
                    run.error_summary,
                    token="aps_safeguard_artifact_generation_failed",
                )
                _record_run_event(
                    db,
                    run=run,
                    event_type="aps_safeguard_artifact_failed",
                    phase="finalizing",
                    stage="reporting",
                    status_after=run.status,
                    error_class=safeguard_exc.__class__.__name__,
                    message=str(safeguard_exc),
                )
            db.commit()
    finally:
        NRC_EXECUTOR_GUARDS.release_run_slot()
        db.close()
