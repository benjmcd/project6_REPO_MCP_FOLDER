from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import random
import re
import socket
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    ConnectorArtifactAlias,
    ConnectorPolicySnapshot,
    ConnectorRun,
    ConnectorRunCheckpoint,
    ConnectorRunEvent,
    ConnectorRunPartitionCursor,
    ConnectorRunSubmission,
    ConnectorRunTarget,
    DatasetExternalIdentity,
    DatasetSourceProvenance,
)
from app.services.sciencebase_connector.executor import ExecutorGuards, assert_lease_token, transition_target_state
from app.services.sciencebase_connector.contracts import (
    ARTIFACT_DEDUP_POLICIES,
    DEFAULT_ALLOWED_HOST_PATTERNS,
    ERROR_TAXONOMY,
    PHASES,
    RECONCILIATION_STATUSES,
    RETRYABLE_HTTP_STATUSES,
    RUN_MODES,
    RUN_TERMINAL_STATUSES,
    SCOPE_MODES,
    SEARCH_EXHAUSTION_REASONS,
    SURFACE_PRECEDENCE,
    TARGET_TERMINAL_STATUSES,
    ArtifactCandidate,
    ConditionalFetchMetadata,
    DownloadResult,
    FetchPolicyBlockedError,
    ResolvedTargetPlan,
    RunNotFoundError,
    SearchPageNormalized,
    StageResult,
    SubmissionConflictError,
    enum_value as contract_enum_value,
)
from app.services.sciencebase_connector.planner import (
    build_mcs_query as planner_build_mcs_query,
    build_query_fingerprint as planner_build_query_fingerprint,
    stable_json_hash as planner_stable_json_hash,
)
from app.services.sciencebase_connector.reporting import report_refs as build_report_refs
from app.services.sciencebase_connector.reconciliation import is_reconciliation_terminal
from app.services.sciencebase_connector.serialization import serialize_run_event
from app.services.ingest import ingest_csv_bytes_to_dataset
from app.services.profiling import profile_dataset_version
from app.services.transforms import recommend_transformations


EXECUTOR_GUARDS = ExecutorGuards(max_concurrent_runs=settings.connector_max_concurrent_runs)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _safe_filename(name: str) -> str:
    base = Path(name or "artifact").name.strip() or "artifact"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)


def _normalize_extension(ext: str) -> str:
    out = ext.strip().lower()
    if not out:
        return out
    return out if out.startswith(".") else f".{out}"


def _stable_json_hash(payload: dict[str, Any]) -> str:
    return planner_stable_json_hash(payload)


def _normalize_url_for_key(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""
    scheme = (parsed.scheme or "").lower()
    return f"{scheme}://{host}{path}?{query}"


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


def _resolve_host_ip(hostname: str) -> str | None:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except Exception:
        return None
    for info in infos:
        ip = info[4][0]
        if ip:
            return ip
    return None


def _is_blocked_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return bool(
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
        or addr.is_reserved
    )


def _build_fetch_policy(config: dict[str, Any]) -> dict[str, Any]:
    extra_hosts = [h.strip() for h in config.get("allowed_hosts", []) if str(h).strip()]
    allowed_hosts = list(dict.fromkeys(DEFAULT_ALLOWED_HOST_PATTERNS + extra_hosts))
    external_policy = str(config.get("external_fetch_policy", "sciencebase_only"))
    if external_policy == "allowlisted_external":
        allowed_hosts = list(dict.fromkeys(allowed_hosts + extra_hosts))
    elif external_policy in {"sciencebase_only", "all_https_denied_by_default"}:
        allowed_hosts = ["sciencebase.gov", "www.sciencebase.gov"]
    return {
        "mode": config.get("fetch_policy_mode", "strict_public_safe"),
        "external_fetch_policy": external_policy,
        "allowed_schemes": ["https"],
        "allowed_hosts": allowed_hosts,
        "max_redirects": int(config.get("max_redirects", settings.connector_max_redirects)),
    }


def _precheck_download_url(url: str, policy: dict[str, Any]) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if scheme not in policy["allowed_schemes"]:
        return None, "scheme_not_allowed"
    if not host:
        return None, "missing_host"
    if not _is_allowed_host(host, policy["allowed_hosts"]):
        return None, "host_not_allowed"
    resolved_ip = _resolve_host_ip(host)
    if resolved_ip and _is_blocked_ip(resolved_ip):
        return resolved_ip, "resolved_private_or_blocked_ip"
    return resolved_ip, None


def _surface_enabled(surface: str, surface_policy: str) -> bool:
    if surface_policy == "files_only":
        return surface == "files"
    if surface_policy == "files_and_distribution":
        return surface in {"files", "distributionLinks"}
    if surface_policy == "all_supported":
        return surface in {"files", "distributionLinks", "webLinks"}
    return surface == "files"


def _classify_download_exception(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, FetchPolicyBlockedError):
        if "redirect" in exc.reason:
            return "redirect_policy_violation", False
        return "host_policy_violation", False
    if isinstance(exc, requests.Timeout):
        return "transport_timeout", True
    if isinstance(exc, requests.ConnectionError):
        return "transport_timeout", True
    if isinstance(exc, requests.HTTPError):
        code = int(exc.response.status_code) if exc.response is not None else 0
        if 500 <= code <= 599:
            return "http_5xx", code in RETRYABLE_HTTP_STATUSES
        return "http_4xx", False
    return "orchestrator_internal_error", False


def _classify_stage_exception(stage: str) -> tuple[str, bool]:
    if stage == "ingest":
        return "ingest_failed", False
    if stage == "profile":
        return "profile_failed", False
    if stage == "recommend":
        return "recommend_failed", False
    return "orchestrator_internal_error", False


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)

def _extract_doi(item: dict[str, Any]) -> str | None:
    identifiers = item.get("identifiers") or []
    for raw in identifiers:
        if not isinstance(raw, dict):
            continue
        id_type = str(raw.get("type") or "").lower()
        value = str(raw.get("key") or raw.get("id") or raw.get("value") or "").strip()
        if "doi" in id_type and value:
            return value
        if value.lower().startswith("10."):
            return value
    citation = str(item.get("citation") or "")
    match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", citation)
    if match:
        return match.group(1)
    return None


def _extract_stable_release_identifier(item: dict[str, Any]) -> str:
    doi = _extract_doi(item)
    if doi:
        return f"doi:{doi.lower()}"
    identifiers = item.get("identifiers") or []
    for raw in identifiers:
        if not isinstance(raw, dict):
            continue
        value = str(raw.get("id") or raw.get("key") or raw.get("value") or "").strip()
        if value:
            return f"identifier:{value}"
    return f"sciencebase:{item.get('id', 'unknown')}"


def _extract_stable_release_key(item: dict[str, Any]) -> str:
    return _extract_stable_release_identifier(item)


def _build_query_fingerprint(config: dict[str, Any]) -> str:
    return planner_build_query_fingerprint(config)


class ScienceBaseAdapter:
    def __init__(self, *, base_url: str, timeout_seconds: int):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search_page(
        self,
        *,
        q: str,
        filters: list[str],
        offset: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> SearchPageNormalized:
        params: list[tuple[str, Any]] = [
            ("q", q),
            ("format", "json"),
            ("max", page_size),
            ("offset", offset),
            ("sort", sort),
            ("order", order),
        ]
        for f in filters:
            params.append(("filter", f))
        response = requests.get(f"{self.base_url}/items", params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        return SearchPageNormalized(
            items=[item for item in (payload.get("items") or []) if isinstance(item, dict)],
            offset=offset,
            page_size=page_size,
            total=payload.get("total"),
            nextlink=payload.get("nextlink"),
            prevlink=payload.get("prevlink"),
            raw_query_metadata={"params": params, "keys": sorted(payload.keys())},
        )

    def hydrate_item(self, item_id: str) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/item/{item_id}", params={"format": "json"}, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def extract_artifacts(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in item.get("files") or []:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "unnamed")
            download_uri = str(raw.get("downloadUri") or raw.get("url") or "").strip()
            if not download_uri:
                continue
            checksum = raw.get("checksum")
            checksum_type: str | None = None
            checksum_value: str | None = None
            if isinstance(checksum, dict):
                checksum_type = str(checksum.get("type") or checksum.get("algorithm") or "").strip() or None
                checksum_value = str(checksum.get("value") or checksum.get("checksum") or "").strip() or None
            elif isinstance(checksum, str) and checksum.strip():
                checksum_value = checksum.strip()
            out.append(
                {
                    "surface": "files",
                    "name": name,
                    "url": download_uri,
                    "locator_type": "downloadUri" if raw.get("downloadUri") else "url",
                    "checksum_type": checksum_type,
                    "checksum_value": checksum_value,
                    "source_reference": raw,
                }
            )
        for raw in item.get("distributionLinks") or []:
            if not isinstance(raw, dict):
                continue
            url = str(raw.get("uri") or raw.get("url") or "").strip()
            if not url:
                continue
            name = str(raw.get("title") or raw.get("type") or Path(urlparse(url).path).name or "distribution_link")
            out.append(
                {
                    "surface": "distributionLinks",
                    "name": name,
                    "url": url,
                    "locator_type": "distributionLink",
                    "checksum_type": None,
                    "checksum_value": None,
                    "source_reference": raw,
                }
            )
        for raw in item.get("webLinks") or []:
            if not isinstance(raw, dict):
                continue
            url = str(raw.get("uri") or raw.get("url") or "").strip()
            if not url:
                continue
            name = str(raw.get("title") or raw.get("type") or Path(urlparse(url).path).name or "web_link")
            out.append(
                {
                    "surface": "webLinks",
                    "name": name,
                    "url": url,
                    "locator_type": "webLink",
                    "checksum_type": None,
                    "checksum_value": None,
                    "source_reference": raw,
                }
            )
        return out

    def download_artifact(
        self,
        *,
        url: str,
        timeout_seconds: int,
        max_redirects: int,
        headers: dict[str, str] | None = None,
    ) -> DownloadResult:
        response = requests.get(url, stream=True, timeout=(10, timeout_seconds), allow_redirects=True, headers=headers or {})
        if len(response.history) > max_redirects:
            raise FetchPolicyBlockedError("redirect_policy_violation")
        if response.status_code != 304:
            response.raise_for_status()
        hasher = hashlib.sha256()
        chunks: list[bytes] = []
        if response.status_code != 304:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if not chunk:
                    continue
                chunks.append(chunk)
                hasher.update(chunk)
        body = b"".join(chunks)
        final_url = str(response.url)
        final_host = (urlparse(final_url).hostname or "").lower()
        resolved_ip = _resolve_host_ip(final_host) if final_host else None
        return DownloadResult(
            content=body,
            status_code=int(response.status_code),
            final_url=final_url,
            redirect_count=len(response.history),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            content_type=response.headers.get("content-type"),
            sha256=hasher.hexdigest() if response.status_code != 304 else "",
            headers=dict(response.headers),
            resolved_ip=resolved_ip,
        )


def get_sciencebase_adapter(config: dict[str, Any]) -> ScienceBaseAdapter:
    timeout_seconds = int(config.get("request_timeout_seconds", 30))
    return ScienceBaseAdapter(base_url=settings.sciencebase_api_base_url, timeout_seconds=timeout_seconds)


def _build_mcs_query(payload: dict[str, Any]) -> str:
    return planner_build_mcs_query(payload)


def _enum_value(value: Any, *, allowed: set[str], default: str) -> str:
    return contract_enum_value(value, allowed=allowed, default=default)


def _normalize_request_config(connector_key: str, payload: dict[str, Any], submission_idempotency_key: str | None) -> dict[str, Any]:
    config = dict(payload)
    config["scope_mode"] = _enum_value(value=config.get("scope_mode", "keyword_search"), allowed=SCOPE_MODES, default="keyword_search")
    config["scope_values"] = [str(v).strip() for v in config.get("scope_values", []) if str(v).strip()]
    config["run_mode"] = _enum_value(value=config.get("run_mode", "one_shot_import"), allowed=RUN_MODES, default="one_shot_import")
    config["surface_policy"] = config.get("surface_policy", "files_only")
    config["external_fetch_policy"] = config.get("external_fetch_policy", "sciencebase_only")
    config["reconciliation_enabled"] = bool(config.get("reconciliation_enabled", False)) or config["run_mode"] == "recurring_sync"
    config["resume_behavior"] = _enum_value(
        value=config.get("resume_behavior", "resume_if_exists"),
        allowed={"resume_if_exists", "fail_if_running", "force_new_run"},
        default="resume_if_exists",
    )
    config["partition_strategy"] = _enum_value(
        value=config.get("partition_strategy", "none"),
        allowed={"none", "auto_date_split", "configured_slices"},
        default="none",
    )
    config["configured_slices"] = list(config.get("configured_slices", []))
    config["ordering_strategy"] = _enum_value(
        value=config.get("ordering_strategy", "item_id"),
        allowed={"item_id", "doi_then_item_id", "explicit_sort"},
        default="item_id",
    )
    config["checkpoint_frequency"] = _enum_value(
        value=config.get("checkpoint_frequency", "per_target"),
        allowed={"per_page", "per_target", "per_stage"},
        default="per_target",
    )
    config["artifact_dedup_policy"] = _enum_value(
        value=config.get("artifact_dedup_policy", "by_checksum"),
        allowed=ARTIFACT_DEDUP_POLICIES,
        default="by_checksum",
    )
    config["report_verbosity"] = _enum_value(
        value=config.get("report_verbosity", "standard"),
        allowed={"summary", "standard", "debug"},
        default="standard",
    )
    config["conditional_request_policy"] = config.get("conditional_request_policy", "etag_then_last_modified")
    config["submission_idempotency_key"] = submission_idempotency_key or config.get("client_request_id")

    if connector_key == "sciencebase_mcs":
        config["mcs_release_mode"] = _enum_value(
            value=config.get("mcs_release_mode", "annual_release"),
            allowed={"annual_release", "commodity_sheet_release"},
            default="annual_release",
        )
        config["commodity_keywords"] = [str(v).strip() for v in config.get("commodity_keywords", []) if str(v).strip()]
        if config["mcs_release_mode"] == "commodity_sheet_release" and not config["commodity_keywords"]:
            raise SubmissionConflictError("commodity_keywords required for mcs commodity_sheet_release mode")
        config["q"] = _build_mcs_query(config)
        filters = list(config.get("filters", []))
        if "systemType=Data Release" not in filters:
            filters.append("systemType=Data Release")
        config["filters"] = filters

    if config["scope_mode"] in {"folder_children", "folder_descendants"} and len(config["scope_values"]) != 1:
        raise SubmissionConflictError("scope_values must contain exactly one folder id for folder scope modes")
    if config["scope_mode"] in {"explicit_item_ids", "explicit_dois"} and not config["scope_values"]:
        raise SubmissionConflictError("scope_values must be non-empty for explicit scope modes")

    config["allowed_extensions"] = sorted({_normalize_extension(ext) for ext in config.get("allowed_extensions", [".csv"]) if _normalize_extension(ext)})
    config["selection_mode"] = config.get("selection_mode", "first_n")
    config["sort"] = config.get("sort", "title")
    config["order"] = config.get("order", "asc")
    config["page_size"] = max(5, min(int(config.get("page_size", 100)), 1000))
    config["page_size"] = config["page_size"] - (config["page_size"] % 5)
    if config["page_size"] <= 0:
        config["page_size"] = 5
    config["max_items"] = max(0, int(config.get("max_items", 0)))
    config["max_files"] = max(0, int(config.get("max_files", 0)))
    config["seed"] = int(config.get("seed", 0))
    config["max_file_bytes"] = max(1024, int(config.get("max_file_bytes", 64 * 1024 * 1024)))
    config["max_run_bytes"] = max(config["max_file_bytes"], int(config.get("max_run_bytes", 512 * 1024 * 1024)))
    config["max_concurrent_downloads_per_run"] = max(
        1,
        int(config.get("max_concurrent_downloads_per_run", settings.connector_max_downloads_per_run)),
    )
    config["per_host_fetch_limit"] = max(1, int(config.get("per_host_fetch_limit", settings.connector_per_host_fetch_limit)))
    config["request_timeout_seconds"] = max(5, int(config.get("request_timeout_seconds", 30)))
    config["max_redirects"] = max(0, int(config.get("max_redirects", settings.connector_max_redirects)))
    if config.get("run_mode") != "recurring_sync":
        config["reconciliation_enabled"] = bool(config.get("reconciliation_enabled", False))
    if config.get("run_mode") == "recurring_sync":
        config["reconciliation_enabled"] = True
    return config


def submit_connector_run(db: Session, *, connector_key: str, payload: dict[str, Any], idempotency_key: str | None) -> tuple[ConnectorRun, bool]:
    submitted_key = (idempotency_key or payload.get("client_request_id") or "").strip() or None
    config = _normalize_request_config(connector_key, payload, submitted_key)
    request_fingerprint = _stable_json_hash(config)
    source_query_fingerprint = _build_query_fingerprint(config)
    now = _utcnow()

    if submitted_key:
        existing_submission = (
            db.query(ConnectorRunSubmission)
            .filter(
                and_(
                    ConnectorRunSubmission.connector_key == connector_key,
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
            if not existing_run:
                raise RunNotFoundError("idempotent submission points to missing run")
            return existing_run, False
    else:
        resume_behavior = str(config.get("resume_behavior", "resume_if_exists"))
        active_run = (
            db.query(ConnectorRun)
            .filter(
                and_(
                    ConnectorRun.connector_key == connector_key,
                    ConnectorRun.request_fingerprint == request_fingerprint,
                    ConnectorRun.status.in_(["pending", "running", "cancelling"]),
                )
            )
            .order_by(ConnectorRun.submitted_at.desc())
            .first()
        )
        if active_run and resume_behavior == "resume_if_exists":
            return active_run, False
        if active_run and resume_behavior == "fail_if_running":
            raise SubmissionConflictError("equivalent run already active")
    active_run_count = (
        db.query(ConnectorRun)
        .filter(ConnectorRun.status.in_(["pending", "running", "cancelling"]))
        .count()
    )
    if active_run_count >= int(settings.connector_max_concurrent_runs):
        raise SubmissionConflictError("active run concurrency limit reached")

    run = ConnectorRun(
        connector_key=connector_key,
        source_system="sciencebase",
        source_mode="public_api",
        status="pending",
        request_config_json=config,
        source_query_fingerprint=source_query_fingerprint,
        request_fingerprint=request_fingerprint,
        effective_search_params_json={},
        effective_filters_json=[],
        effective_sort=str(config.get("sort", "title")),
        effective_order=str(config.get("order", "asc")),
        effective_page_size=int(config.get("page_size", 100)),
        search_exhaustion_reason=None,
        submission_idempotency_key=submitted_key,
        adapter_dialect="sciencebase_rest_v1",
        api_generation="v1",
        sciencebase_normalization_version="1.3.3",
        submitted_at=now,
    )
    db.add(run)
    db.flush()

    if submitted_key:
        db.add(
            ConnectorRunSubmission(
                connector_key=connector_key,
                submission_idempotency_key=submitted_key,
                request_fingerprint=request_fingerprint,
                connector_run_id=run.connector_run_id,
                expires_at=now + timedelta(hours=settings.connector_submission_ttl_hours),
            )
        )

    retry_matrix = {
        "retryable": ["transport_timeout", "http_5xx"],
        "terminal": ["http_4xx", "host_policy_violation", "redirect_policy_violation", "unsupported_artifact_surface", "parse_failed", "profile_failed", "recommend_failed"],
        "orchestrator_only": ["lease_conflict"],
    }
    db.add(ConnectorPolicySnapshot(connector_run_id=run.connector_run_id, policy_json=config, retry_matrix_json=retry_matrix))
    db.add(
        ConnectorRunCheckpoint(
            connector_run_id=run.connector_run_id,
            phase="planning",
            partition_cursor="0",
            page_offset=0,
            last_successful_stage="planning",
            payload_json={"state": "submitted"},
        )
    )
    _record_run_event(
        db,
        run=run,
        event_type="run_submitted",
        phase="planning",
        status_after="pending",
        metrics_json={"connector_key": connector_key},
    )

    db.commit()
    db.refresh(run)
    return run, True


def request_cancel_run(db: Session, connector_run_id: str) -> ConnectorRun:
    run = db.get(ConnectorRun, connector_run_id)
    if not run:
        raise RunNotFoundError("connector run not found")
    if run.status in RUN_TERMINAL_STATUSES:
        return run
    prior_status = run.status
    run.cancellation_requested_at = _utcnow()
    run.status = "cancelling"
    _record_run_event(
        db,
        run=run,
        event_type="run_cancel_requested",
        phase="finalizing",
        status_before=prior_status,
        status_after="cancelling",
    )
    db.commit()
    db.refresh(run)
    return run


def request_resume_run(db: Session, connector_run_id: str) -> ConnectorRun:
    run = db.get(ConnectorRun, connector_run_id)
    if not run:
        raise RunNotFoundError("connector run not found")
    if run.status == "running":
        return run
    if run.status == "cancelling":
        return run
    prior_status = run.status
    run.status = "pending"
    run.cancellation_requested_at = None
    run.resume_count = (run.resume_count or 0) + 1
    _record_run_event(
        db,
        run=run,
        event_type="run_resume_requested",
        phase="planning",
        status_before=prior_status,
        status_after="pending",
        metrics_json={"resume_count": int(run.resume_count or 0)},
    )
    db.commit()
    db.refresh(run)
    return run

def _record_checkpoint(
    db: Session,
    *,
    run: ConnectorRun,
    phase: str,
    partition_cursor: str | None = None,
    page_offset: int | None = None,
    last_item_id: str | None = None,
    last_target_id: str | None = None,
    last_successful_stage: str | None = None,
    payload_json: dict[str, Any] | None = None,
) -> None:
    db.add(
        ConnectorRunCheckpoint(
            connector_run_id=run.connector_run_id,
            phase=phase,
            partition_cursor=partition_cursor,
            page_offset=page_offset,
            last_item_id=last_item_id,
            last_target_id=last_target_id,
            last_successful_stage=last_successful_stage,
            payload_json=payload_json or {},
            checkpoint_written_at=_utcnow(),
        )
    )
    db.commit()


def _checkpoint_frequency(config: dict[str, Any] | None) -> str:
    value = str((config or {}).get("checkpoint_frequency", "per_target")).strip().lower()
    if value in {"per_page", "per_target", "per_stage"}:
        return value
    return "per_target"


def _should_record_checkpoint(config: dict[str, Any] | None, granularity: str) -> bool:
    freq = _checkpoint_frequency(config)
    if granularity in {"phase", "page"}:
        return True
    if granularity == "target":
        return freq in {"per_target", "per_stage"}
    if granularity == "stage":
        return freq == "per_stage"
    return True


def _maybe_record_checkpoint(
    db: Session,
    *,
    run: ConnectorRun,
    config: dict[str, Any] | None,
    granularity: str,
    phase: str,
    partition_cursor: str | None = None,
    page_offset: int | None = None,
    last_item_id: str | None = None,
    last_target_id: str | None = None,
    last_successful_stage: str | None = None,
    payload_json: dict[str, Any] | None = None,
) -> None:
    if not _should_record_checkpoint(config, granularity):
        return
    _record_checkpoint(
        db,
        run=run,
        phase=phase,
        partition_cursor=partition_cursor,
        page_offset=page_offset,
        last_item_id=last_item_id,
        last_target_id=last_target_id,
        last_successful_stage=last_successful_stage,
        payload_json=payload_json,
    )


def _record_stage_checkpoint(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    config: dict[str, Any],
    phase: str,
) -> None:
    _maybe_record_checkpoint(
        db,
        run=run,
        config=config,
        granularity="stage",
        phase=phase,
        partition_cursor="0",
        page_offset=0,
        last_item_id=target.sciencebase_item_id,
        last_target_id=target.connector_run_target_id,
        last_successful_stage=target.status,
        payload_json={
            "stage": phase,
            "target_status": target.status,
            "target_ordinal": target.ordinal,
        },
    )


def _record_run_event(
    db: Session,
    *,
    run: ConnectorRun,
    event_type: str,
    phase: str | None = None,
    stage: str | None = None,
    target: ConnectorRunTarget | None = None,
    status_before: str | None = None,
    status_after: str | None = None,
    reason_code: str | None = None,
    error_class: str | None = None,
    message: str | None = None,
    metrics_json: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    db.add(
        ConnectorRunEvent(
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id if target else None,
            phase=phase,
            stage=stage,
            event_type=event_type,
            status_before=status_before,
            status_after=status_after,
            reason_code=reason_code,
            error_class=error_class,
            message=message,
            metrics_json=metrics_json or {},
            created_at=_utcnow(),
        )
    )
    if commit:
        db.commit()


def _update_run_stage_aggregates(run: ConnectorRun, *, metrics_json: dict[str, Any] | None = None) -> None:
    metrics = dict(metrics_json or {})
    duration_ms_raw = metrics.get("duration_ms")
    bytes_raw = metrics.get("bytes")

    query_plan = dict(run.query_plan_json or {})
    telemetry = dict(query_plan.get("telemetry") or {})
    latency_total_ms = int(telemetry.get("stage_latency_total_ms", 0) or 0)
    latency_samples = int(telemetry.get("stage_latency_samples", 0) or 0)
    bytes_skipped = int(telemetry.get("bytes_skipped_due_to_unchanged_detection", 0) or 0)

    if duration_ms_raw is not None:
        try:
            latency_total_ms += int(float(duration_ms_raw))
            latency_samples += 1
        except (TypeError, ValueError):
            pass

    if bytes_raw is not None:
        try:
            bytes_skipped += int(bytes_raw)
        except (TypeError, ValueError):
            pass

    telemetry["stage_latency_total_ms"] = latency_total_ms
    telemetry["stage_latency_samples"] = latency_samples
    telemetry["bytes_skipped_due_to_unchanged_detection"] = bytes_skipped
    query_plan["telemetry"] = telemetry
    run.query_plan_json = query_plan


def _transition_target_atomic(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    lease_token: str | None,
    status_after: str,
    phase: str,
    stage: str,
    event_type: str,
    operator_reason_code: str | None = None,
    error_class: str | None = None,
    message: str | None = None,
    retry_eligible: bool | None = None,
    target_updates: dict[str, Any] | None = None,
    stage_attempt: dict[str, Any] | None = None,
    metrics_json: dict[str, Any] | None = None,
    created: bool = False,
    status_before_override: str | None = None,
) -> None:
    if stage_attempt and stage_attempt.get("metrics_json"):
        _update_run_stage_aggregates(run, metrics_json=stage_attempt.get("metrics_json"))
    if event_type == "target_skipped_unchanged":
        _update_run_stage_aggregates(run, metrics_json={"bytes": (metrics_json or {}).get("bytes", 0)})
    transition_target_state(
        db,
        run=run,
        target=target,
        status_after=status_after,
        phase=phase,
        stage=stage,
        event_type=event_type,
        status_before_override=status_before_override,
        created=created,
        operator_reason_code=operator_reason_code,
        error_class=error_class,
        message=message,
        retry_eligible=retry_eligible,
        target_updates=target_updates,
        stage_attempt=stage_attempt,
        metrics_json=metrics_json,
        assert_lease=_assert_active_lease,
        lease_token=lease_token,
    )


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


def _target_terminal_for_processing(target: ConnectorRunTarget) -> bool:
    if target.status in TARGET_TERMINAL_STATUSES:
        return True
    if target.status in {"download_failed", "ingest_failed", "profile_failed", "recommend_failed"} and not target.retry_eligible:
        return True
    return False


def _extension_allowed(name: str, allowed_extensions: list[str]) -> bool:
    ext = Path(name).suffix.lower()
    return ext in allowed_extensions


def _normalize_item_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    contacts = item.get("contacts") or []
    contact_names = []
    for c in contacts:
        if isinstance(c, dict):
            contact_names.append(c.get("name") or c.get("person") or c.get("email"))
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "summary": item.get("summary"),
        "citation": item.get("citation"),
        "identifiers": item.get("identifiers"),
        "systemTypes": item.get("systemTypes"),
        "tags": item.get("tags"),
        "dates": item.get("dates"),
        "permissions": item.get("permissions"),
        "parentId": item.get("parentId"),
        "hasChildren": item.get("hasChildren"),
        "contacts_summary": [str(v) for v in contact_names if v],
        "files": item.get("files"),
        "distributionLinks": item.get("distributionLinks"),
        "webLinks": item.get("webLinks"),
    }


def _permission_summary(item: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
    raw = item.get("permissions")
    if isinstance(raw, dict):
        text = json.dumps(raw).lower()
        if "public" in text and "read" in text:
            return raw, "public_read", True
        return raw, "restricted_or_unknown", False
    if isinstance(raw, list):
        text = json.dumps(raw).lower()
        if "public" in text and "read" in text:
            return {"permissions": raw}, "public_read", True
        return {"permissions": raw}, "restricted_or_unknown", False
    # ScienceBase public items often have no explicit permissions in payload.
    return {}, "public_read_assumed", True


def _selection_scope_from_config(config: dict[str, Any]) -> str:
    scope_mode = str(config.get("scope_mode", "keyword_search"))
    if scope_mode in {"explicit_item_ids", "explicit_dois"}:
        return "explicit_item"
    return "search_hit"


def _selection_match_basis_from_config(config: dict[str, Any]) -> str:
    scope_mode = str(config.get("scope_mode", "keyword_search"))
    if scope_mode == "explicit_dois":
        return "doi_scope"
    if scope_mode in {"folder_children", "folder_descendants"}:
        return "folder_scope"
    if scope_mode == "explicit_item_ids":
        return "content_type"
    return "keyword_scope"


def _resolve_scope_filters(config: dict[str, Any]) -> list[str]:
    filters = [str(f) for f in config.get("filters", [])]
    scope_mode = str(config.get("scope_mode", "keyword_search"))
    scope_values = [str(v).strip() for v in config.get("scope_values", []) if str(v).strip()]
    if scope_mode == "folder_children" and scope_values:
        filters.append(f"parentId={scope_values[0]}")
    elif scope_mode == "folder_descendants" and scope_values:
        filters.append(f"ancestors={scope_values[0]}")
    return filters


def _extract_item_id(value: Any) -> str | None:
    if isinstance(value, dict):
        raw = value.get("id")
    else:
        raw = value
    item_id = str(raw or "").strip()
    return item_id or None


def _resolve_scope_items(
    adapter: ScienceBaseAdapter,
    *,
    config: dict[str, Any],
    page_size: int,
    sort: str,
    order: str,
) -> list[dict[str, Any]]:
    scope_mode = str(config.get("scope_mode", "keyword_search"))
    scope_values = [str(v).strip() for v in config.get("scope_values", []) if str(v).strip()]
    if scope_mode == "explicit_item_ids":
        return [{"id": item_id} for item_id in scope_values]
    if scope_mode == "explicit_dois":
        resolved: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        base_filters = [str(f) for f in config.get("filters", [])]
        for doi in scope_values:
            page = adapter.search_page(
                q=doi,
                filters=list(base_filters) + [f"identifiers={doi}"],
                offset=0,
                page_size=page_size,
                sort=sort,
                order=order,
            )
            for item in page.items:
                item_id = _extract_item_id(item)
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                resolved.append({"id": item_id})
        return resolved
    return []


def _upsert_partition_cursor(
    db: Session,
    *,
    run: ConnectorRun,
    partition_id: str,
    partition_type: str,
    partition_bounds_json: dict[str, Any],
    last_offset: int | None,
    last_item_sort_key: str | None,
    last_page_link: str | None,
    partition_exhausted: bool,
) -> None:
    cursor = (
        db.query(ConnectorRunPartitionCursor)
        .filter(
            and_(
                ConnectorRunPartitionCursor.connector_run_id == run.connector_run_id,
                ConnectorRunPartitionCursor.partition_id == partition_id,
            )
        )
        .first()
    )
    if not cursor:
        cursor = ConnectorRunPartitionCursor(
            connector_run_id=run.connector_run_id,
            partition_id=partition_id,
            partition_type=partition_type,
        )
        db.add(cursor)
    cursor.partition_bounds_json = partition_bounds_json
    cursor.last_offset = last_offset
    cursor.last_item_sort_key = last_item_sort_key
    cursor.last_page_link = last_page_link
    cursor.partition_exhausted = partition_exhausted
    cursor.updated_at = _utcnow()
    db.commit()


def _build_canonical_key(
    stable_release_key: str,
    name: str,
    checksum_value: str | None,
    url: str,
    surface: str,
    dedup_policy: str,
) -> str:
    normalized_name = _safe_filename(name).lower()
    policy = _enum_value(value=dedup_policy, allowed=ARTIFACT_DEDUP_POLICIES, default="by_checksum")
    if policy == "by_resolved_url":
        discriminator = _normalize_url_for_key(url)
    elif policy == "by_name_plus_surface":
        discriminator = f"{normalized_name}::{surface.lower()}"
    else:
        discriminator = checksum_value.strip().lower() if checksum_value else _normalize_url_for_key(url)
    return f"{stable_release_key}::{normalized_name}::{discriminator}"


def _build_query_partitions(config: dict[str, Any]) -> list[dict[str, Any]]:
    resolved_filters = _resolve_scope_filters(config)
    base = {
        "label": "p0",
        "q": str(config.get("q") or "Mineral Commodity Summaries"),
        "filters": resolved_filters,
    }
    strategy = str(config.get("partition_strategy", "none"))
    if strategy == "configured_slices":
        configured = config.get("configured_slices") or []
        partitions: list[dict[str, Any]] = []
        for idx, raw in enumerate(configured):
            if not isinstance(raw, dict):
                continue
            partitions.append(
                {
                    "label": str(raw.get("label") or f"slice_{idx}"),
                    "q": str(raw.get("q") or base["q"]),
                    "filters": [str(f) for f in raw.get("filters", base["filters"])],
                }
            )
        return partitions or [base]
    if strategy == "auto_date_split":
        years = sorted({int(y) for y in config.get("years", []) if str(y).strip().isdigit()})
        if not years:
            return [base]
        return [
            {
                "label": f"year_{year}",
                "q": base["q"],
                "filters": list(base["filters"]) + [f"dateRange={year}-01-01,{year}-12-31"],
            }
            for year in years
        ]
    return [base]


def _order_discovered_items(items: list[dict[str, Any]], ordering_strategy: str) -> list[dict[str, Any]]:
    if ordering_strategy == "explicit_sort":
        return list(items)
    return sorted(items, key=lambda x: str(x.get("id") or ""))


def _order_candidates(candidates: list[ArtifactCandidate], ordering_strategy: str) -> list[ArtifactCandidate]:
    if ordering_strategy == "doi_then_item_id":
        return sorted(
            candidates,
            key=lambda c: (
                0 if c.stable_release_identifier.startswith("doi:") else 1,
                c.stable_release_identifier,
                c.sciencebase_item_id,
                SURFACE_PRECEDENCE.get(c.artifact_surface, 99),
                c.sciencebase_file_name.lower(),
                c.sciencebase_download_uri,
            ),
        )
    if ordering_strategy == "explicit_sort":
        return sorted(
            candidates,
            key=lambda c: (
                SURFACE_PRECEDENCE.get(c.artifact_surface, 99),
                c.sciencebase_file_name.lower(),
                c.sciencebase_download_uri,
            ),
        )
    return sorted(
        candidates,
        key=lambda c: (
            c.sciencebase_item_id,
            SURFACE_PRECEDENCE.get(c.artifact_surface, 99),
            c.sciencebase_file_name.lower(),
            c.sciencebase_download_uri,
        ),
    )


def _load_discovery_resume_state(
    db: Session,
    run: ConnectorRun,
    partitions: list[dict[str, Any]],
    page_size: int,
) -> tuple[list[dict[str, Any]], int, int]:
    checkpoints = (
        db.query(ConnectorRunCheckpoint)
        .filter(
            and_(
                ConnectorRunCheckpoint.connector_run_id == run.connector_run_id,
                ConnectorRunCheckpoint.phase == "discovery",
            )
        )
        .order_by(ConnectorRunCheckpoint.checkpoint_written_at.asc())
        .all()
    )
    if not checkpoints:
        return [], 0, 0

    recovered_item_ids: list[str] = []
    seen_ids: set[str] = set()
    latest_cursor_label: str | None = None
    latest_cursor_offset: int | None = None

    for checkpoint in checkpoints:
        payload = checkpoint.payload_json or {}
        page_item_ids = payload.get("page_item_ids")
        if isinstance(page_item_ids, list):
            for raw_id in page_item_ids:
                item_id = str(raw_id or "").strip()
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                recovered_item_ids.append(item_id)
        if checkpoint.partition_cursor is not None and checkpoint.page_offset is not None:
            latest_cursor_label = str(checkpoint.partition_cursor)
            latest_cursor_offset = int(checkpoint.page_offset or 0)

    latest_partition_cursor = (
        db.query(ConnectorRunPartitionCursor)
        .filter(ConnectorRunPartitionCursor.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunPartitionCursor.updated_at.desc())
        .first()
    )
    if latest_partition_cursor:
        latest_cursor_label = latest_partition_cursor.partition_id
        latest_cursor_offset = int(latest_partition_cursor.last_offset or 0)

    if latest_cursor_label is None or latest_cursor_offset is None:
        return [{"id": item_id} for item_id in recovered_item_ids], 0, 0

    partition_to_index = {
        str(partition.get("label") or f"p{idx}"): idx
        for idx, partition in enumerate(partitions)
    }
    start_partition_idx = partition_to_index.get(str(latest_cursor_label), 0)
    start_offset = int(latest_cursor_offset) + page_size

    # If we cannot reconstruct prior page item ids, fallback to full replay.
    if start_offset > 0 and not recovered_item_ids:
        return [], 0, 0

    return [{"id": item_id} for item_id in recovered_item_ids], start_partition_idx, start_offset


def _resolve_resume_target_ordinal(db: Session, run: ConnectorRun) -> int:
    checkpoint = (run.query_plan_json or {}).get("checkpoint", {})
    raw_ordinal = checkpoint.get("target_ordinal_completed")
    try:
        ordinal = int(raw_ordinal or 0)
    except (TypeError, ValueError):
        ordinal = 0
    if ordinal > 0:
        return ordinal

    latest = (
        db.query(ConnectorRunCheckpoint)
        .filter(ConnectorRunCheckpoint.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunCheckpoint.checkpoint_written_at.desc())
        .first()
    )
    if not latest or not latest.last_target_id:
        return 0
    target = db.get(ConnectorRunTarget, latest.last_target_id)
    return int(target.ordinal or 0) if target else 0


def _discover_targets(db: Session, run: ConnectorRun, adapter: ScienceBaseAdapter) -> None:
    config = dict(run.request_config_json or {})
    fetch_policy = _build_fetch_policy(config)
    page_size = int(config.get("page_size", 100))
    sort = str(config.get("sort", "title"))
    order = str(config.get("order", "asc"))
    max_items = int(config.get("max_items", 0))
    max_files = int(config.get("max_files", 0))
    ordering_strategy = str(config.get("ordering_strategy", "item_id"))
    dedup_policy = str(config.get("artifact_dedup_policy", "by_checksum"))
    scope_mode = str(config.get("scope_mode", "keyword_search"))
    resolved_filters = _resolve_scope_filters(config)

    partitions = _build_query_partitions(config)
    discovered_items: list[dict[str, Any]]
    resume_partition_idx = 0
    resume_offset = 0
    if scope_mode in {"explicit_item_ids", "explicit_dois"}:
        discovered_items = _resolve_scope_items(
            adapter,
            config=config,
            page_size=page_size,
            sort=sort,
            order=order,
        )
        partitions = []
    else:
        discovered_items, resume_partition_idx, resume_offset = _load_discovery_resume_state(
            db,
            run,
            partitions,
            page_size,
        )
    resume_start_offset = resume_offset
    discovery_records: list[dict[str, Any]] = []
    page_offsets: list[int] = []
    nextlinks: list[str] = []
    prevlinks: list[str] = []
    offset = 0
    search_exhaustion_reason = "no_more_pages"
    page_count_completed = 0
    partition_count_completed = 0
    last_offset_committed: int | None = None
    next_page_available = False

    run.effective_search_params_json = {
        "scope_mode": scope_mode,
        "scope_values": [str(v) for v in config.get("scope_values", [])],
        "q": str(config.get("q") or ""),
        "sort": sort,
        "order": order,
        "page_size": page_size,
    }
    run.effective_filters_json = resolved_filters
    run.effective_sort = sort
    run.effective_order = order
    run.effective_page_size = page_size
    db.commit()

    _maybe_record_checkpoint(
        db,
        run=run,
        config=config,
        granularity="phase",
        phase="discovery",
        partition_cursor="0",
        page_offset=0,
        last_successful_stage="discovery",
    )

    if scope_mode not in {"explicit_item_ids", "explicit_dois"}:
        for partition_idx, partition in enumerate(partitions):
            if partition_idx < resume_partition_idx:
                continue
            partition_label = str(partition.get("label") or f"p{partition_idx}")
            partition_q = str(partition.get("q") or config.get("q") or "Mineral Commodity Summaries")
            partition_filters = [str(f) for f in partition.get("filters", [])]
            offset = resume_offset if partition_idx == resume_partition_idx else 0
            while True:
                db.refresh(run)
                if run.cancellation_requested_at:
                    search_exhaustion_reason = "cancelled"
                    break
                page = adapter.search_page(
                    q=partition_q,
                    filters=partition_filters,
                    offset=offset,
                    page_size=page_size,
                    sort=sort,
                    order=order,
                )
                page_count_completed += 1
                last_offset_committed = offset
                next_page_available = bool(page.nextlink)
                if not page.items:
                    _upsert_partition_cursor(
                        db,
                        run=run,
                        partition_id=partition_label,
                        partition_type="query_partition",
                        partition_bounds_json={"q": partition_q, "filters": partition_filters},
                        last_offset=offset,
                        last_item_sort_key=None,
                        last_page_link=page.nextlink,
                        partition_exhausted=True,
                    )
                    break

                discovered_items.extend(page.items)
                discovery_records.append(
                    {
                        "partition": partition_label,
                        "offset": offset,
                        "count": len(page.items),
                        "first_item_id": str(page.items[0].get("id") or ""),
                        "last_item_id": str(page.items[-1].get("id") or ""),
                    }
                )
                page_offsets.append(offset)
                if page.nextlink:
                    nextlinks.append(page.nextlink)
                if page.prevlink:
                    prevlinks.append(page.prevlink)
                _upsert_partition_cursor(
                    db,
                    run=run,
                    partition_id=partition_label,
                    partition_type="query_partition",
                    partition_bounds_json={"q": partition_q, "filters": partition_filters},
                    last_offset=offset,
                    last_item_sort_key=str(page.items[-1].get("id") or ""),
                    last_page_link=page.nextlink,
                    partition_exhausted=not bool(page.nextlink),
                )
                _maybe_record_checkpoint(
                    db,
                    run=run,
                    config=config,
                    granularity="page",
                    phase="discovery",
                    partition_cursor=partition_label,
                    page_offset=offset,
                    last_item_id=str(page.items[-1].get("id") or ""),
                    last_successful_stage="discovery",
                    payload_json={
                        "page_items": len(page.items),
                        "partition": partition_label,
                        "page_item_ids": [str(item.get("id") or "") for item in page.items if str(item.get("id") or "").strip()],
                    },
                )
                if max_items > 0 and len(discovered_items) >= max_items:
                    search_exhaustion_reason = "max_items_cap"
                    break
                offset += page_size
            partition_count_completed += 1
            resume_offset = 0
            if search_exhaustion_reason in {"cancelled", "max_items_cap"}:
                break

    discovered_items = _order_discovered_items(discovered_items, ordering_strategy=ordering_strategy)
    deduped_items: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    for item in discovered_items:
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in seen_item_ids:
            continue
        seen_item_ids.add(item_id)
        deduped_items.append(item)
    discovered_items = deduped_items
    if max_items > 0:
        discovered_items = discovered_items[:max_items]

    run.search_exhaustion_reason = (
        search_exhaustion_reason if search_exhaustion_reason in SEARCH_EXHAUSTION_REASONS else "error"
    )
    run.page_count_completed = page_count_completed
    run.partition_count_completed = partition_count_completed
    run.next_page_available = bool(next_page_available)
    run.last_offset_committed = last_offset_committed
    db.commit()

    _maybe_record_checkpoint(
        db,
        run=run,
        config=config,
        granularity="phase",
        phase="hydration",
        partition_cursor="0",
        page_offset=offset,
        last_successful_stage="hydration",
    )

    candidates: list[ArtifactCandidate] = []
    for item in discovered_items:
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        try:
            hydrated = adapter.hydrate_item(item_id)
        except Exception:
            continue
        stable_release_key = _extract_stable_release_key(hydrated)
        stable_release_identifier = _extract_stable_release_identifier(hydrated)
        identifiers_json = hydrated.get("identifiers") if isinstance(hydrated.get("identifiers"), list) else []
        permission_snapshot_json, access_level_summary, public_read_confirmed = _permission_summary(hydrated)
        sciencebase_item_url = f"{settings.sciencebase_api_base_url.rstrip('/')}/item/{item_id}"

        raw_snap_path = Path(settings.connector_snapshots_dir) / f"{run.connector_run_id}_{item_id}_raw.json"
        normalized_snap_path = Path(settings.connector_snapshots_dir) / f"{run.connector_run_id}_{item_id}_normalized.json"
        _write_json(raw_snap_path, hydrated if isinstance(hydrated, dict) else {"raw": hydrated})
        _write_json(normalized_snap_path, _normalize_item_snapshot(hydrated if isinstance(hydrated, dict) else {}))

        for artifact in adapter.extract_artifacts(hydrated):
            name = str(artifact.get("name") or "artifact")
            url = str(artifact.get("url") or "").strip()
            surface = str(artifact.get("surface") or "files")
            locator_type = str(artifact.get("locator_type") or "url")
            if not url:
                continue
            raw_source_artifact_key = f"{stable_release_key}::{surface}::{_safe_filename(name).lower()}"
            canonical_key = _build_canonical_key(
                stable_release_key,
                name,
                artifact.get("checksum_value"),
                url,
                surface,
                dedup_policy,
            )
            source_artifact_key = canonical_key
            candidates.append(
                ArtifactCandidate(
                    stable_release_key=stable_release_key,
                    stable_release_identifier=stable_release_identifier,
                    identifiers_json=identifiers_json,
                    sciencebase_item_id=item_id,
                    sciencebase_item_url=sciencebase_item_url,
                    artifact_surface=surface,
                    artifact_locator_type=locator_type,
                    sciencebase_file_name=name,
                    sciencebase_download_uri=url,
                    remote_checksum_type=artifact.get("checksum_type"),
                    remote_checksum_value=artifact.get("checksum_value"),
                    source_reference_json={
                        "surface": surface,
                        "item_snapshot_ref": str(raw_snap_path),
                        "normalized_snapshot_ref": str(normalized_snap_path),
                        "raw_source_artifact_key": raw_source_artifact_key,
                        "raw": artifact.get("source_reference") or {},
                    },
                    canonical_artifact_key=canonical_key,
                    source_artifact_key=source_artifact_key,
                    dedup_hint=canonical_key,
                    permission_snapshot_json=permission_snapshot_json,
                    access_level_summary=access_level_summary,
                    public_read_confirmed=public_read_confirmed,
                )
            )

    candidates = _order_candidates(candidates, ordering_strategy=ordering_strategy)

    selected_indexes = list(range(len(candidates)))
    if max_files > 0 and len(selected_indexes) > max_files:
        if str(config.get("selection_mode", "first_n")) == "sample":
            rng = random.Random(int(config.get("seed", 0)))
            selected_indexes = sorted(rng.sample(selected_indexes, max_files))
        else:
            selected_indexes = selected_indexes[:max_files]
        if str(run.search_exhaustion_reason or "no_more_pages") == "no_more_pages":
            run.search_exhaustion_reason = "max_files_cap"
    selected_index_set = set(selected_indexes)

    surface_policy = str(config.get("surface_policy", "files_only"))
    allowed_extensions = [str(ext).lower() for ext in config.get("allowed_extensions", [".csv"])]

    winner_by_key: dict[str, int] = {}
    duplicates: set[int] = set()
    for i, cand in enumerate(candidates):
        existing_idx = winner_by_key.get(cand.canonical_artifact_key)
        if existing_idx is None:
            winner_by_key[cand.canonical_artifact_key] = i
            continue
        old = candidates[existing_idx]
        if SURFACE_PRECEDENCE.get(cand.artifact_surface, 99) < SURFACE_PRECEDENCE.get(old.artifact_surface, 99):
            duplicates.add(existing_idx)
            winner_by_key[cand.canonical_artifact_key] = i
        else:
            duplicates.add(i)

    created: list[ConnectorRunTarget] = []
    selection_scope = _selection_scope_from_config(config)
    selection_match_basis = _selection_match_basis_from_config(config)
    for i, cand in enumerate(candidates):
        plan = ResolvedTargetPlan(
            target_status="selected",
            operator_reason_code="selected_csv_files_surface",
            selection_reason_code="selected_csv_files_surface",
            ignore_reason_code=None,
            dedup_reason_code=None,
            blocked_reason=None,
        )
        if i in duplicates:
            plan.target_status = "collapsed_duplicate"
            plan.operator_reason_code = "deduped_same_checksum"
            plan.selection_reason_code = None
            plan.dedup_reason_code = "deduped_same_checksum"
        elif i not in selected_index_set:
            plan.target_status = "ignored_by_policy"
            plan.operator_reason_code = "ignored_selection_cap"
            plan.selection_reason_code = None
            plan.ignore_reason_code = "ignored_selection_cap"
        elif not _surface_enabled(cand.artifact_surface, surface_policy):
            plan.target_status = "unsupported_artifact_surface"
            plan.operator_reason_code = "ignored_external_webLink_policy"
            plan.selection_reason_code = None
            plan.ignore_reason_code = "ignored_external_webLink_policy"
        elif not _extension_allowed(cand.sciencebase_file_name, allowed_extensions):
            plan.target_status = "ignored_by_policy"
            plan.operator_reason_code = "ignored_non_tabular_extension"
            plan.selection_reason_code = None
            plan.ignore_reason_code = "ignored_non_tabular_extension"
        else:
            resolved_ip, blocked_reason = _precheck_download_url(cand.sciencebase_download_uri, fetch_policy)
            if blocked_reason:
                plan.target_status = "blocked_by_fetch_policy"
                plan.operator_reason_code = "host_policy_violation"
                plan.selection_reason_code = None
                plan.blocked_reason = blocked_reason

        target = ConnectorRunTarget(
            connector_run_id=run.connector_run_id,
            ordinal=len(created) + 1,
            stable_release_key=cand.stable_release_key,
            stable_release_identifier=cand.stable_release_identifier,
            identifiers_json=cand.identifiers_json,
            sciencebase_item_id=cand.sciencebase_item_id,
            sciencebase_item_url=cand.sciencebase_item_url,
            sciencebase_file_name=cand.sciencebase_file_name,
            sciencebase_download_uri=cand.sciencebase_download_uri,
            artifact_surface=cand.artifact_surface,
            selection_source=cand.artifact_surface,
            selection_scope=selection_scope,
            selection_match_basis=selection_match_basis,
            artifact_locator_type=cand.artifact_locator_type,
            source_artifact_key=cand.source_artifact_key,
            canonical_artifact_key=cand.canonical_artifact_key,
            remote_checksum_type=cand.remote_checksum_type,
            remote_checksum_value=cand.remote_checksum_value,
            source_reference_json=cand.source_reference_json,
            permission_snapshot_json=cand.permission_snapshot_json,
            access_level_summary=cand.access_level_summary,
            public_read_confirmed=cand.public_read_confirmed,
            fetch_policy_mode=fetch_policy["mode"],
            status="discovered",
            blocked_reason=plan.blocked_reason,
            operator_reason_code=None,
            selection_reason_code=None,
            ignore_reason_code=None,
            dedup_reason_code=None,
            discovered_at=_utcnow(),
            selected_at=None,
            last_stage_transition_at=_utcnow(),
            retry_eligible=False,
        )
        created.append(target)
        db.add(target)
        db.flush()
        update_payload: dict[str, Any] = {
            "selection_reason_code": plan.selection_reason_code,
            "ignore_reason_code": plan.ignore_reason_code,
            "dedup_reason_code": plan.dedup_reason_code,
            "blocked_reason": plan.blocked_reason,
            "selected_at": _utcnow() if plan.target_status == "selected" else None,
            "error_stage": None,
            "error_message": None,
            "last_error_class": None,
        }
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=run.execution_lease_token,
            status_after=plan.target_status,
            phase="target_creation",
            stage="target_creation",
            event_type=f"target_{plan.target_status}",
            operator_reason_code=plan.operator_reason_code,
            retry_eligible=False,
            target_updates=update_payload,
            created=True,
        )

    winners = [created[idx] for idx in selected_indexes if idx < len(created) and idx not in duplicates]
    winner_map = {w.canonical_artifact_key: w for w in winners if w.canonical_artifact_key}
    for i, target in enumerate(created):
        if i not in duplicates:
            continue
        winner = winner_map.get(target.canonical_artifact_key)
        if not winner:
            continue
        db.add(
            ConnectorArtifactAlias(
                connector_run_target_id=winner.connector_run_target_id,
                alias_surface=target.artifact_surface,
                alias_name=target.sciencebase_file_name,
                alias_url=target.sciencebase_download_uri,
                alias_checksum_type=target.remote_checksum_type,
                alias_checksum_value=target.remote_checksum_value,
                alias_json=target.source_reference_json,
            )
        )

    discovery_payload = {
        "query": str(config.get("q") or "Mineral Commodity Summaries"),
        "filters": resolved_filters,
        "partitions": partitions,
        "resume_partition_index": resume_partition_idx,
        "resume_start_offset": resume_start_offset,
        "partition_strategy": str(config.get("partition_strategy", "none")),
        "ordering_strategy": ordering_strategy,
        "page_size": page_size,
        "scope_mode": scope_mode,
        "scope_values": [str(v) for v in config.get("scope_values", [])],
        "effective_sort": sort,
        "effective_order": order,
        "offsets": page_offsets,
        "nextlinks": nextlinks,
        "prevlinks": prevlinks,
        "search_exhaustion_reason": run.search_exhaustion_reason,
        "pages": discovery_records,
        "discovered_item_ids": [str(item.get("id")) for item in discovered_items],
    }
    run.discovery_snapshot_ref = _write_json(Path(settings.connector_manifests_dir) / f"{run.connector_run_id}_discovery.json", discovery_payload)
    run.selection_manifest_ref = _write_json(
        Path(settings.connector_manifests_dir) / f"{run.connector_run_id}_selection.json",
        {
            "candidate_count": len(candidates),
            "selected_count": len([t for t in created if t.status == "selected"]),
            "targets": [
                {
                    "target_id": t.connector_run_target_id,
                    "item_id": t.sciencebase_item_id,
                    "name": t.sciencebase_file_name,
                    "surface": t.artifact_surface,
                    "status": t.status,
                    "reason": t.operator_reason_code,
                    "source_artifact_key": t.source_artifact_key,
                    "canonical_artifact_key": t.canonical_artifact_key,
                }
                for t in created
            ],
        },
    )
    run.query_plan_json = {
        "q": str(config.get("q") or "Mineral Commodity Summaries"),
        "filters": resolved_filters,
        "sort": sort,
        "order": order,
        "page_size": page_size,
        "partition_strategy": str(config.get("partition_strategy", "none")),
        "partitions": partitions,
        "ordering_strategy": ordering_strategy,
        "checkpoint": {"target_ordinal_completed": 0},
    }
    if str(run.search_exhaustion_reason or "") not in SEARCH_EXHAUSTION_REASONS:
        run.search_exhaustion_reason = "error"
    db.commit()

    _maybe_record_checkpoint(
        db,
        run=run,
        config=config,
        granularity="phase",
        phase="target_creation",
        partition_cursor="0",
        page_offset=offset,
        last_successful_stage="target_creation",
        payload_json={"targets": len(created)},
    )


def _apply_reconciliation_targets(db: Session, run: ConnectorRun, config: dict[str, Any]) -> None:
    if not bool(config.get("reconciliation_enabled", False)):
        return
    if str(config.get("run_mode", "one_shot_import")) != "recurring_sync":
        return

    current_keys = {
        str(key)
        for (key,) in db.query(ConnectorRunTarget.source_artifact_key)
        .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
        .all()
        if str(key or "").strip()
    }

    prior_sources = (
        db.query(DatasetSourceProvenance)
        .filter(
            and_(
                DatasetSourceProvenance.source_system == "sciencebase",
                DatasetSourceProvenance.source_artifact_key.is_not(None),
            )
        )
        .order_by(DatasetSourceProvenance.created_at.desc())
        .all()
    )
    latest_by_key: dict[str, DatasetSourceProvenance] = {}
    for row in prior_sources:
        key = str(row.source_artifact_key or "").strip()
        if not key or key in latest_by_key:
            continue
        latest_by_key[key] = row

    missing_keys = [key for key in sorted(latest_by_key.keys()) if key not in current_keys]
    if not missing_keys:
        return

    last_ordinal = (
        db.query(ConnectorRunTarget.ordinal)
        .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunTarget.ordinal.desc())
        .first()
    )
    ordinal = int(last_ordinal[0]) if last_ordinal else 0

    now = _utcnow()
    for key in missing_keys:
        prior = latest_by_key[key]
        ordinal += 1
        target = ConnectorRunTarget(
            connector_run_id=run.connector_run_id,
            ordinal=ordinal,
            stable_release_key=key.split("::")[0] if "::" in key else key,
            stable_release_identifier=None,
            identifiers_json=[],
            sciencebase_item_id=prior.sciencebase_item_id,
            sciencebase_item_url=prior.sciencebase_item_url,
            sciencebase_file_name=prior.sciencebase_file_name,
            sciencebase_download_uri=prior.sciencebase_download_uri,
            artifact_surface=prior.artifact_surface or "files",
            selection_source=prior.artifact_surface or "files",
            selection_scope="search_hit",
            selection_match_basis="keyword_scope",
            artifact_locator_type=prior.artifact_locator_type,
            source_artifact_key=key,
            canonical_artifact_key=key,
            remote_checksum_type=prior.remote_checksum_type,
            remote_checksum_value=prior.remote_checksum_value,
            source_reference_json=prior.source_reference_json or {},
            permission_snapshot_json={},
            access_level_summary="unknown",
            public_read_confirmed=False,
            status="discovered",
            operator_reason_code=None,
            reconciliation_reason_code=None,
            discovered_at=now,
            last_stage_transition_at=now,
            retry_eligible=False,
        )
        db.add(target)
        db.flush()
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=run.execution_lease_token,
            status_after="missing_upstream",
            phase="reconciliation",
            stage="reconciliation",
            event_type="target_missing_upstream",
            operator_reason_code="missing_upstream",
            retry_eligible=False,
            target_updates={
                "reconciliation_reason_code": "missing_upstream",
                "selection_reason_code": None,
                "ignore_reason_code": None,
                "dedup_reason_code": None,
                "error_stage": None,
                "error_message": None,
                "last_error_class": None,
            },
            created=True,
        )

    db.commit()


def _resolve_dataset_id(db: Session, logical_dataset_key: str) -> str | None:
    existing = (
        db.query(DatasetExternalIdentity)
        .filter(
            and_(
                DatasetExternalIdentity.source_system == "sciencebase",
                DatasetExternalIdentity.logical_dataset_key == logical_dataset_key,
            )
        )
        .first()
    )
    return existing.dataset_id if existing else None


def _persist_dataset_identity(db: Session, dataset_id: str, logical_dataset_key: str, metadata_json: dict[str, Any]) -> None:
    existing = (
        db.query(DatasetExternalIdentity)
        .filter(
            and_(
                DatasetExternalIdentity.source_system == "sciencebase",
                DatasetExternalIdentity.logical_dataset_key == logical_dataset_key,
            )
        )
        .first()
    )
    if existing:
        return
    db.add(
        DatasetExternalIdentity(
            dataset_id=dataset_id,
            source_system="sciencebase",
            logical_dataset_key=logical_dataset_key,
            metadata_json=metadata_json,
        )
    )
    db.flush()


def _latest_provenance(db: Session, source_artifact_key: str) -> DatasetSourceProvenance | None:
    return (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.source_artifact_key == source_artifact_key)
        .order_by(DatasetSourceProvenance.created_at.desc())
        .first()
    )


def _is_unchanged(target: ConnectorRunTarget, prior: DatasetSourceProvenance | None) -> bool:
    if not prior:
        return False
    if (
        target.remote_checksum_value
        and prior.remote_checksum_value
        and str(target.remote_checksum_value).strip() == str(prior.remote_checksum_value).strip()
        and (target.remote_checksum_type or "").lower() == (prior.remote_checksum_type or "").lower()
    ):
        return True
    if target.downloaded_sha256 and prior.downloaded_sha256 and target.downloaded_sha256 == prior.downloaded_sha256:
        return True
    return False


def _write_raw_blob(run: ConnectorRun, target: ConnectorRunTarget, content: bytes) -> str:
    out_dir = Path(settings.connector_raw_dir) / run.connector_run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(target.sciencebase_file_name or "artifact.csv")
    out = out_dir / f"{target.connector_run_target_id}_{safe_name}"
    out.write_bytes(content)
    return str(out)


def _download_target(
    adapter: ScienceBaseAdapter,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    config: dict[str, Any],
    conditional_headers: dict[str, str] | None = None,
) -> DownloadResult:
    fetch_policy = _build_fetch_policy(config)
    resolved_ip, reason = _precheck_download_url(target.sciencebase_download_uri or "", fetch_policy)
    target.resolved_ip = resolved_ip
    if reason:
        raise FetchPolicyBlockedError(reason)
    host_gate = ExecutorGuards.acquire_host_slot(
        target.sciencebase_download_uri or "",
        int(config.get("per_host_fetch_limit", settings.connector_per_host_fetch_limit)),
    )
    try:
        result = adapter.download_artifact(
            url=target.sciencebase_download_uri or "",
            timeout_seconds=int(config.get("request_timeout_seconds", 30)),
            max_redirects=int(config.get("max_redirects", settings.connector_max_redirects)),
            headers=conditional_headers,
        )
    finally:
        host_gate.release()
    resolved_ip_2, reason_2 = _precheck_download_url(result.final_url, fetch_policy)
    target.resolved_ip = resolved_ip_2 or target.resolved_ip
    if reason_2:
        raise FetchPolicyBlockedError(reason_2)
    if result.status_code != 304 and len(result.content) > int(config.get("max_file_bytes", 64 * 1024 * 1024)):
        raise FetchPolicyBlockedError("file_size_limit_exceeded")
    return result


def _run_target_pipeline(
    db: Session,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    adapter: ScienceBaseAdapter,
    config: dict[str, Any],
    lease_token: str | None,
) -> None:
    if _target_terminal_for_processing(target):
        return
    _assert_active_lease(run, lease_token)
    run_mode = str(config.get("run_mode", "one_shot_import"))
    max_run_bytes = int(config.get("max_run_bytes", 512 * 1024 * 1024))

    if bool(run.budget_exhausted) or int(run.consumed_bytes or 0) >= max_run_bytes:
        run.budget_exhausted = True
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="budget_blocked",
            phase="downloading",
            stage="downloading",
            event_type="target_budget_blocked",
            operator_reason_code="budget_exhausted",
            retry_eligible=False,
            target_updates={
                "versioning_reason_code": "budget_exhausted_before_start",
                "error_stage": None,
                "error_message": None,
                "last_error_class": None,
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="downloading")
        return

    if run_mode == "dry_run":
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="dry_run_skipped",
            phase="downloading",
            stage="downloading",
            event_type="target_dry_run_skipped",
            operator_reason_code="dry_run_no_download",
            retry_eligible=False,
            target_updates={
                "error_stage": None,
                "error_message": None,
                "last_error_class": None,
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="downloading")
        return

    started = _utcnow()
    target.attempt_count = (target.attempt_count or 0) + 1
    target.last_attempt_at = started
    _assert_active_lease(run, lease_token)
    db.commit()

    prior = _latest_provenance(db, target.source_artifact_key or "")
    conditional_headers: dict[str, str] = {}
    if run_mode == "recurring_sync":
        policy = str(config.get("conditional_request_policy", "etag_then_last_modified"))
        if policy in {"etag_then_last_modified", "etag_only"} and prior and prior.etag:
            conditional_headers["If-None-Match"] = str(prior.etag)
        if (
            not conditional_headers
            and policy in {"etag_then_last_modified", "last_modified_only"}
            and prior
            and prior.last_modified
        ):
            conditional_headers["If-Modified-Since"] = str(prior.last_modified)

    stage_start = time.time()
    download_gate = threading.BoundedSemaphore(max(1, int(config.get("max_concurrent_downloads_per_run", 1))))
    download_gate.acquire()
    try:
        download = _download_target(adapter, run, target, config, conditional_headers=conditional_headers or None)
    except Exception as exc:
        error_class, retryable = _classify_download_exception(exc)
        if isinstance(exc, FetchPolicyBlockedError):
            status_after = "blocked_by_fetch_policy"
            reason_code = "ignored_external_webLink_policy"
            retry = False
            event_type = "target_blocked_by_fetch_policy"
        else:
            status_after = "download_failed"
            reason_code = "transport_or_http_failure"
            retry = retryable
            event_type = "target_download_failed"
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after=status_after,
            phase="downloading",
            stage="downloading",
            event_type=event_type,
            operator_reason_code=reason_code,
            error_class=error_class,
            message=str(exc),
            retry_eligible=retry,
            target_updates={
                "error_stage": "downloading",
                "error_message": str(exc),
                "last_error_class": error_class,
            },
            stage_attempt={
                "stage": "downloading",
                "started_at": started,
                "status": status_after,
                "error_class": error_class,
                "error_message": str(exc),
                "retryable": retry,
                "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000)},
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="downloading")
        return
    finally:
        download_gate.release()

    if download.status_code == 304:
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="not_modified_remote",
            phase="downloading",
            stage="downloading",
            event_type="target_not_modified_remote",
            operator_reason_code="not_modified_remote_conditional_304",
            error_class="conditional_fetch_miss",
            retry_eligible=False,
            target_updates={
                "versioning_reason_code": "not_modified_remote_conditional_304",
                "error_stage": None,
                "error_message": None,
                "last_error_class": None,
                "etag": download.etag,
                "last_modified": download.last_modified,
            },
            stage_attempt={
                "stage": "downloading",
                "started_at": started,
                "status": "not_modified_remote",
                "error_class": "conditional_fetch_miss",
                "error_message": None,
                "retryable": False,
                "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000), "http_status": 304},
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="downloading")
        return

    downloaded_at = _utcnow()
    raw_storage_ref = _write_raw_blob(run, target, download.content)
    run.consumed_bytes = int(run.consumed_bytes or 0) + len(download.content)
    if int(run.consumed_bytes or 0) > max_run_bytes:
        run.budget_exhausted = True
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="budget_blocked",
            phase="downloading",
            stage="downloading",
            event_type="target_budget_blocked",
            operator_reason_code="budget_exhausted",
            retry_eligible=False,
            target_updates={
                "downloaded_at": downloaded_at,
                "redirect_count": download.redirect_count,
                "etag": download.etag,
                "last_modified": download.last_modified,
                "downloaded_sha256": download.sha256,
                "raw_storage_ref": raw_storage_ref,
                "versioning_reason_code": "budget_exhausted_after_download",
                "error_stage": None,
                "error_message": None,
                "last_error_class": None,
            },
            metrics_json={"consumed_bytes": int(run.consumed_bytes or 0), "max_run_bytes": max_run_bytes},
            stage_attempt={
                "stage": "downloading",
                "started_at": started,
                "status": "budget_blocked",
                "error_class": None,
                "error_message": None,
                "retryable": False,
                "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000), "bytes": len(download.content)},
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="downloading")
        return

    _transition_target_atomic(
        db,
        run=run,
        target=target,
        lease_token=lease_token,
        status_after="downloaded",
        phase="downloading",
        stage="downloading",
        event_type="target_downloaded",
        operator_reason_code="downloaded_successfully",
        retry_eligible=False,
        target_updates={
            "downloaded_at": downloaded_at,
            "redirect_count": download.redirect_count,
            "etag": download.etag,
            "last_modified": download.last_modified,
            "downloaded_sha256": download.sha256,
            "raw_storage_ref": raw_storage_ref,
            "error_stage": None,
            "error_message": None,
            "last_error_class": None,
        },
        metrics_json={"bytes": len(download.content)},
        stage_attempt={
            "stage": "downloading",
            "started_at": started,
            "status": "downloaded",
            "error_class": None,
            "error_message": None,
            "retryable": False,
            "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000), "bytes": len(download.content)},
        },
    )
    _record_stage_checkpoint(db, run=run, target=target, config=config, phase="downloading")

    if _is_unchanged(target, prior):
        if conditional_headers:
            unchanged_reason = "skipped_unchanged_after_conditional_revalidate"
        else:
            unchanged_reason = "skipped_unchanged_remote_checksum_match"
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="skipped_unchanged",
            phase="downloading",
            stage="downloading",
            event_type="target_skipped_unchanged",
            operator_reason_code=unchanged_reason,
            retry_eligible=False,
            target_updates={
                "versioning_reason_code": unchanged_reason,
                "error_stage": None,
                "error_message": None,
                "last_error_class": None,
            },
            metrics_json={"bytes": len(download.content)},
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="downloading")
        return

    logical_dataset_key = f"{target.stable_release_key or target.sciencebase_item_id or 'unknown'}::{Path(target.sciencebase_file_name or 'artifact').stem.lower()}"
    existing_dataset_id = _resolve_dataset_id(db, logical_dataset_key)

    ingest_start = _utcnow()
    stage_start = time.time()
    try:
        ingest_result = ingest_csv_bytes_to_dataset(
            db,
            filename=target.sciencebase_file_name or "artifact.csv",
            content=download.content,
            name=Path(target.sciencebase_file_name or "artifact.csv").stem,
            description=target.sciencebase_item_url,
            domain_pack=str(config.get("domain_pack") or "macro_energy_commodities"),
            primary_time_column=config.get("primary_time_column"),
            dataset_id=existing_dataset_id,
            source_name="sciencebase_public_connector",
            source_category="api_connector",
            source_notes=f"connector_run_id={run.connector_run_id}; source_artifact_key={target.source_artifact_key}; artifact_surface={target.artifact_surface}",
        )
    except Exception as exc:
        error_class, retryable = _classify_stage_exception("ingest")
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="ingest_failed",
            phase="ingesting",
            stage="ingesting",
            event_type="target_ingest_failed",
            operator_reason_code="ingest_failed",
            error_class=error_class,
            message=str(exc),
            retry_eligible=retryable,
            target_updates={
                "error_stage": "ingesting",
                "error_message": str(exc),
                "last_error_class": error_class,
            },
            stage_attempt={
                "stage": "ingesting",
                "started_at": ingest_start,
                "status": "ingest_failed",
                "error_class": error_class,
                "error_message": str(exc),
                "retryable": retryable,
                "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000)},
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="ingesting")
        return

    dataset_id = str(ingest_result["dataset_id"])
    dataset_version_id = str(ingest_result["dataset_version_id"])
    _persist_dataset_identity(
        db,
        dataset_id=dataset_id,
        logical_dataset_key=logical_dataset_key,
        metadata_json={
            "stable_release_key": target.stable_release_key,
            "sciencebase_item_id": target.sciencebase_item_id,
            "source_artifact_key": target.source_artifact_key,
        },
    )
    _transition_target_atomic(
        db,
        run=run,
        target=target,
        lease_token=lease_token,
        status_after="ingested",
        phase="ingesting",
        stage="ingesting",
        event_type="target_ingested",
        operator_reason_code="ingested_successfully",
        retry_eligible=False,
        target_updates={
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "ingested_at": _utcnow(),
            "versioning_reason_code": "new_version_checksum_changed",
            "error_stage": None,
            "error_message": None,
            "last_error_class": None,
        },
        stage_attempt={
            "stage": "ingesting",
            "started_at": ingest_start,
            "status": "ingested",
            "error_class": None,
            "error_message": None,
            "retryable": False,
            "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000)},
        },
    )
    _record_stage_checkpoint(db, run=run, target=target, config=config, phase="ingesting")

    profile_start = _utcnow()
    stage_start = time.time()
    try:
        profile_dataset_version(
            db,
            target.dataset_version_id,
            detect_seasonality=bool(config.get("detect_seasonality", True)),
            detect_stationarity=bool(config.get("detect_stationarity", True)),
        )
    except Exception as exc:
        error_class, retryable = _classify_stage_exception("profile")
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="profile_failed",
            phase="profiling",
            stage="profiling",
            event_type="target_profile_failed",
            operator_reason_code="profile_failed",
            error_class=error_class,
            message=str(exc),
            retry_eligible=retryable,
            target_updates={
                "error_stage": "profiling",
                "error_message": str(exc),
                "last_error_class": error_class,
            },
            stage_attempt={
                "stage": "profiling",
                "started_at": profile_start,
                "status": "profile_failed",
                "error_class": error_class,
                "error_message": str(exc),
                "retryable": retryable,
                "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000)},
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="profiling")
        return

    _transition_target_atomic(
        db,
        run=run,
        target=target,
        lease_token=lease_token,
        status_after="profiled",
        phase="profiling",
        stage="profiling",
        event_type="target_profiled",
        operator_reason_code="profiled_successfully",
        retry_eligible=False,
        target_updates={
            "profiled_at": _utcnow(),
            "error_stage": None,
            "error_message": None,
            "last_error_class": None,
        },
        stage_attempt={
            "stage": "profiling",
            "started_at": profile_start,
            "status": "profiled",
            "error_class": None,
            "error_message": None,
            "retryable": False,
            "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000)},
        },
    )
    _record_stage_checkpoint(db, run=run, target=target, config=config, phase="profiling")

    recommend_start = _utcnow()
    stage_start = time.time()
    try:
        recommend_transformations(db, target.dataset_version_id)
    except Exception as exc:
        error_class, retryable = _classify_stage_exception("recommend")
        _transition_target_atomic(
            db,
            run=run,
            target=target,
            lease_token=lease_token,
            status_after="recommend_failed",
            phase="recommending",
            stage="recommending",
            event_type="target_recommend_failed",
            operator_reason_code="recommend_failed",
            error_class=error_class,
            message=str(exc),
            retry_eligible=retryable,
            target_updates={
                "error_stage": "recommending",
                "error_message": str(exc),
                "last_error_class": error_class,
            },
            stage_attempt={
                "stage": "recommending",
                "started_at": recommend_start,
                "status": "recommend_failed",
                "error_class": error_class,
                "error_message": str(exc),
                "retryable": retryable,
                "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000)},
            },
        )
        _record_stage_checkpoint(db, run=run, target=target, config=config, phase="recommending")
        return

    db.add(
        DatasetSourceProvenance(
            dataset_version_id=target.dataset_version_id,
            connector_run_id=run.connector_run_id,
            source_system="sciencebase",
            source_mode="public_api",
            source_artifact_key=target.source_artifact_key or "",
            sciencebase_item_id=target.sciencebase_item_id,
            sciencebase_item_url=target.sciencebase_item_url,
            sciencebase_file_name=target.sciencebase_file_name,
            sciencebase_download_uri=target.sciencebase_download_uri,
            artifact_surface=target.artifact_surface,
            artifact_locator_type=target.artifact_locator_type,
            remote_checksum_type=target.remote_checksum_type,
            remote_checksum_value=target.remote_checksum_value,
            downloaded_sha256=target.downloaded_sha256,
            raw_storage_ref=target.raw_storage_ref,
            source_query_fingerprint=run.source_query_fingerprint,
            source_reference_json=target.source_reference_json or {},
            fetch_policy_mode=target.fetch_policy_mode,
            resolved_ip=target.resolved_ip,
            redirect_count=target.redirect_count,
            blocked_reason=target.blocked_reason,
            etag=target.etag,
            last_modified=target.last_modified,
            retrieved_http_json={
                "status_code": download.status_code,
                "content_type": download.content_type,
                "headers": download.headers,
            },
            discovered_at=target.discovered_at,
            downloaded_at=target.downloaded_at,
        )
    )
    _transition_target_atomic(
        db,
        run=run,
        target=target,
        lease_token=lease_token,
        status_after="recommended",
        phase="recommending",
        stage="recommending",
        event_type="target_recommended",
        operator_reason_code="recommended_successfully",
        retry_eligible=False,
        target_updates={
            "recommended_at": _utcnow(),
            "error_stage": None,
            "error_message": None,
            "last_error_class": None,
        },
        stage_attempt={
            "stage": "recommending",
            "started_at": recommend_start,
            "status": "recommended",
            "error_class": None,
            "error_message": None,
            "retryable": False,
            "metrics_json": {"duration_ms": int((time.time() - stage_start) * 1000)},
        },
    )
    _record_stage_checkpoint(db, run=run, target=target, config=config, phase="recommending")

def _recompute_run_totals(db: Session, run: ConnectorRun) -> dict[str, int]:
    targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).all()
    statuses = [t.status for t in targets]
    run.discovered_count = len(targets)
    run.selected_count = len(
        [
            s
            for s in statuses
            if s
            in {
                "selected",
                "downloaded",
                "ingested",
                "profiled",
                "recommended",
                "skipped_unchanged",
                "not_modified_remote",
                "dry_run_skipped",
            }
        ]
    )
    run.ignored_count = len([s for s in statuses if s in {"ignored_by_policy", "unsupported_artifact_surface"}])
    run.collapsed_duplicate_count = statuses.count("collapsed_duplicate")
    run.deduped_within_run_count = run.collapsed_duplicate_count
    run.blocked_by_fetch_policy_count = statuses.count("blocked_by_fetch_policy")
    run.skipped_unchanged_count = statuses.count("skipped_unchanged")
    run.not_modified_count = statuses.count("not_modified_remote")
    run.reconciliation_only_count = len([s for s in statuses if is_reconciliation_terminal(s)])
    run.budget_blocked_count = statuses.count("budget_blocked")
    run.downloaded_count = len(
        [
            s
            for s in statuses
            if s in {"downloaded", "ingested", "profiled", "recommended", "skipped_unchanged", "not_modified_remote"}
        ]
    )
    run.ingested_count = len([s for s in statuses if s in {"ingested", "profiled", "recommended"}])
    run.profiled_count = len([s for s in statuses if s in {"profiled", "recommended"}])
    run.recommended_count = statuses.count("recommended")
    run.failed_count = len([s for s in statuses if s in {"download_failed", "ingest_failed", "profile_failed", "recommend_failed"}])
    run.consumed_bytes = 0
    for target in targets:
        if target.raw_storage_ref and Path(target.raw_storage_ref).exists():
            run.consumed_bytes += int(Path(target.raw_storage_ref).stat().st_size)
    run.budget_exhausted = run.budget_exhausted or run.budget_blocked_count > 0

    policy_counts: dict[str, int] = {}
    for target in targets:
        if target.status not in {"ignored_by_policy", "unsupported_artifact_surface", "blocked_by_fetch_policy"}:
            continue
        reason = str(target.operator_reason_code or "unknown")
        policy_counts[reason] = int(policy_counts.get(reason, 0)) + 1
    run.policy_skipped_count_by_reason_json = policy_counts

    retryable_target_count = len([t for t in targets if t.retry_eligible])
    terminal_target_count = len(
        [
            t
            for t in targets
            if t.status in TARGET_TERMINAL_STATUSES
            or (t.status in {"download_failed", "ingest_failed", "profile_failed", "recommend_failed"} and not t.retry_eligible)
        ]
    )
    nonterminal_target_count = len(targets) - terminal_target_count
    run.retryable_target_count = retryable_target_count
    run.terminal_target_count = terminal_target_count
    run.nonterminal_target_count = nonterminal_target_count
    db.commit()
    return {
        "retryable_target_count": retryable_target_count,
        "terminal_target_count": terminal_target_count,
        "nonterminal_target_count": nonterminal_target_count,
    }


def _finalize_run(db: Session, run: ConnectorRun) -> None:
    counts = _recompute_run_totals(db, run)
    now = _utcnow()
    if run.status == "cancelling" or run.cancellation_requested_at:
        run.status = "cancelled"
        run.cancelled_at = now
        run.error_summary = "cancelled_by_operator"
    elif run.failed_count > 0 or run.blocked_by_fetch_policy_count > 0 or run.budget_blocked_count > 0:
        run.status = "completed_with_errors"
    else:
        run.status = "completed"
    run.completed_at = now
    _release_lease(run)

    targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).order_by(ConnectorRunTarget.ordinal.asc()).all()
    run_summary = {
        "connector_run_id": run.connector_run_id,
        "status": run.status,
        "connector_key": run.connector_key,
        "totals": {
            "discovered": run.discovered_count,
            "selected": run.selected_count,
            "ignored": run.ignored_count,
            "collapsed_duplicate": run.collapsed_duplicate_count,
            "deduped_within_run": run.deduped_within_run_count,
            "blocked_by_fetch_policy": run.blocked_by_fetch_policy_count,
            "skipped_unchanged": run.skipped_unchanged_count,
            "not_modified_remote": run.not_modified_count,
            "reconciliation_only": run.reconciliation_only_count,
            "budget_blocked": run.budget_blocked_count,
            "downloaded": run.downloaded_count,
            "ingested": run.ingested_count,
            "profiled": run.profiled_count,
            "recommended": run.recommended_count,
            "failed": run.failed_count,
            **counts,
        },
        "effective_search_envelope": {
            "params": run.effective_search_params_json or {},
            "filters": run.effective_filters_json or [],
            "sort": run.effective_sort,
            "order": run.effective_order,
            "page_size": run.effective_page_size,
            "search_exhaustion_reason": run.search_exhaustion_reason,
        },
    }
    report_verbosity = str((run.request_config_json or {}).get("report_verbosity", "standard"))
    run.report_ref = _write_json(Path(settings.connector_reports_dir) / f"{run.connector_run_id}_run_summary.json", run_summary)

    failures_csv = Path(settings.connector_reports_dir) / f"{run.connector_run_id}_targets_failures.csv"
    selected_csv = Path(settings.connector_reports_dir) / f"{run.connector_run_id}_targets_selected.csv"
    versioning_csv = Path(settings.connector_reports_dir) / f"{run.connector_run_id}_versioning_decisions.csv"
    event_log = Path(settings.connector_reports_dir) / f"{run.connector_run_id}_event_log.ndjson"

    failures_lines = ["target_id,status,error_class,error_stage,error_message,reason_code"]
    selected_lines = ["target_id,status,item_id,file_name,surface,source_artifact_key,canonical_artifact_key"]
    versioning_lines = ["target_id,status,versioning_reason_code,dataset_id,dataset_version_id"]
    event_lines: list[str] = []

    for t in targets:
        if t.status in {"download_failed", "ingest_failed", "profile_failed", "recommend_failed", "blocked_by_fetch_policy", "budget_blocked"}:
            failures_lines.append(
                f"{t.connector_run_target_id},{t.status},{t.last_error_class or ''},{t.error_stage or ''},{(t.error_message or '').replace(',', ';')},{t.operator_reason_code or ''}"
            )
        if t.status in {"selected", "downloaded", "ingested", "profiled", "recommended", "skipped_unchanged", "not_modified_remote", "dry_run_skipped"}:
            selected_lines.append(
                f"{t.connector_run_target_id},{t.status},{t.sciencebase_item_id or ''},{(t.sciencebase_file_name or '').replace(',', ';')},{t.artifact_surface},{t.source_artifact_key or ''},{t.canonical_artifact_key or ''}"
            )
        versioning_lines.append(
            f"{t.connector_run_target_id},{t.status},{t.versioning_reason_code or ''},{t.dataset_id or ''},{t.dataset_version_id or ''}"
        )
        event_lines.append(
            json.dumps(
                {
                    "event": "target_state",
                    "target_id": t.connector_run_target_id,
                    "status": t.status,
                    "reason_code": t.operator_reason_code,
                    "ts": (t.last_stage_transition_at or _utcnow()).isoformat(),
                }
            )
        )

    if report_verbosity in {"standard", "debug"}:
        failures_csv.write_text("\n".join(failures_lines), encoding="utf-8")
        selected_csv.write_text("\n".join(selected_lines), encoding="utf-8")
        versioning_csv.write_text("\n".join(versioning_lines), encoding="utf-8")

    if report_verbosity == "debug":
        event_log.write_text("\n".join(event_lines), encoding="utf-8")
        _write_json(
            Path(settings.connector_reports_dir) / f"{run.connector_run_id}_checkpoint_history.json",
            {
                "checkpoints": [
                    {
                        "phase": c.phase,
                        "partition_cursor": c.partition_cursor,
                        "page_offset": c.page_offset,
                        "last_item_id": c.last_item_id,
                        "last_target_id": c.last_target_id,
                        "last_successful_stage": c.last_successful_stage,
                        "checkpoint_written_at": c.checkpoint_written_at.isoformat() if c.checkpoint_written_at else None,
                    }
                    for c in db.query(ConnectorRunCheckpoint)
                    .filter(ConnectorRunCheckpoint.connector_run_id == run.connector_run_id)
                    .order_by(ConnectorRunCheckpoint.checkpoint_written_at.asc())
                    .all()
                ]
            },
        )
        _write_json(
            Path(settings.connector_reports_dir) / f"{run.connector_run_id}_artifact_dedup_report.json",
            {
                "collapsed_duplicate_count": run.collapsed_duplicate_count,
                "aliases": [
                    {
                        "target_id": t.connector_run_target_id,
                        "canonical_artifact_key": t.canonical_artifact_key,
                        "alias_count": len(t.aliases),
                    }
                    for t in targets
                    if t.aliases
                ],
            },
        )

    db.commit()


def execute_connector_run(connector_run_id: str) -> None:
    db = SessionLocal()
    EXECUTOR_GUARDS.acquire_run_slot()
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
        adapter = get_sciencebase_adapter(config)

        existing_target_count = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run.connector_run_id).count()
        if existing_target_count == 0:
            _discover_targets(db, run, adapter)
            _apply_reconciliation_targets(db, run, config)
            _record_run_event(
                db,
                run=run,
                event_type="targets_discovered",
                phase="target_creation",
                status_after=run.status,
                metrics_json={"discovered_count": int(run.discovered_count or 0)},
                commit=True,
            )

        targets = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
            .order_by(ConnectorRunTarget.ordinal.asc())
            .all()
        )
        resume_target_ordinal = _resolve_resume_target_ordinal(db, run)
        targets_to_process = targets
        if resume_target_ordinal > 0:
            has_nonterminal_before_cursor = any(
                not _target_terminal_for_processing(item)
                for item in targets
                if int(item.ordinal or 0) <= resume_target_ordinal
            )
            if not has_nonterminal_before_cursor:
                targets_to_process = [item for item in targets if int(item.ordinal or 0) > resume_target_ordinal]

        _maybe_record_checkpoint(
            db,
            run=run,
            config=config,
            granularity="phase",
            phase="downloading",
            partition_cursor="0",
            page_offset=0,
            last_successful_stage="downloading",
            payload_json={"resume_target_ordinal": resume_target_ordinal},
        )
        for target in targets_to_process:
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
            if run.budget_exhausted and target.status == "selected":
                _transition_target_atomic(
                    db,
                    run=run,
                    target=target,
                    lease_token=lease_token,
                    status_after="budget_blocked",
                    phase="downloading",
                    stage="downloading",
                    event_type="target_budget_blocked",
                    operator_reason_code="budget_exhausted",
                    retry_eligible=False,
                    target_updates={
                        "versioning_reason_code": "budget_exhausted_before_start",
                        "error_stage": None,
                        "error_message": None,
                        "last_error_class": None,
                    },
                )
                _maybe_record_checkpoint(
                    db,
                    run=run,
                    config=config,
                    granularity="target",
                    phase="downloading",
                    partition_cursor="0",
                    page_offset=0,
                    last_item_id=target.sciencebase_item_id,
                    last_target_id=target.connector_run_target_id,
                    last_successful_stage=target.status,
                    payload_json={"target_status": target.status},
                )
                continue
            _run_target_pipeline(db, run, target, adapter, config, lease_token)
            _assert_active_lease(run, lease_token)
            run.query_plan_json = {
                **(run.query_plan_json or {}),
                "checkpoint": {
                    "target_ordinal_completed": target.ordinal,
                    "last_stage": target.status,
                    "updated_at": _utcnow().isoformat(),
                },
            }
            db.commit()
            _maybe_record_checkpoint(
                db,
                run=run,
                config=config,
                granularity="target",
                phase="downloading" if target.status in {"downloaded", "download_failed", "blocked_by_fetch_policy"} else "recommending",
                partition_cursor="0",
                page_offset=0,
                last_item_id=target.sciencebase_item_id,
                last_target_id=target.connector_run_target_id,
                last_successful_stage=target.status,
                payload_json={"target_status": target.status},
            )
            _renew_lease(db, run)
            lease_token = run.execution_lease_token

        if run.budget_exhausted and not run.search_exhaustion_reason:
            run.search_exhaustion_reason = "budget_exhausted"
            db.commit()

        _maybe_record_checkpoint(
            db,
            run=run,
            config=config,
            granularity="phase",
            phase="finalizing",
            partition_cursor="0",
            page_offset=0,
            last_successful_stage="finalizing",
        )
        _finalize_run(db, run)
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
            db.commit()
    finally:
        EXECUTOR_GUARDS.release_run_slot()
        db.close()


def serialize_connector_target(target: ConnectorRunTarget) -> dict[str, Any]:
    return {
        "connector_run_target_id": target.connector_run_target_id,
        "ordinal": target.ordinal,
        "sciencebase_item_id": target.sciencebase_item_id,
        "sciencebase_file_name": target.sciencebase_file_name,
        "artifact_surface": target.artifact_surface,
        "selection_source": target.selection_source,
        "selection_scope": target.selection_scope,
        "selection_match_basis": target.selection_match_basis,
        "artifact_locator_type": target.artifact_locator_type,
        "stable_release_key": target.stable_release_key,
        "source_artifact_key": target.source_artifact_key,
        "attempt_count": target.attempt_count,
        "retry_eligible": target.retry_eligible,
        "last_error_class": target.last_error_class,
        "last_error_message": target.error_message,
        "last_stage_transition_at": target.last_stage_transition_at,
        "operator_reason_code": target.operator_reason_code,
        "status": target.status,
        "error_stage": target.error_stage,
        "error_message": target.error_message,
        "dataset_id": target.dataset_id,
        "dataset_version_id": target.dataset_version_id,
        "canonical_artifact_key": target.canonical_artifact_key,
        "blocked_reason": target.blocked_reason,
        "redirect_count": target.redirect_count,
        "access_level_summary": target.access_level_summary,
        "public_read_confirmed": bool(target.public_read_confirmed),
    }


def _connector_report_refs_for_run(run: ConnectorRun) -> dict[str, Any]:
    return {
        **build_report_refs(run.connector_run_id),
        **dict((run.query_plan_json or {}).get("connector_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_sync_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_safeguard_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_artifact_ingestion_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_content_index_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_evidence_bundle_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_evidence_citation_pack_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_evidence_report_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_evidence_report_export_package_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_context_packet_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_context_dossier_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_deterministic_insight_artifact_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_report_refs") or {}),
        **dict((run.query_plan_json or {}).get("aps_deterministic_challenge_review_packet_report_refs") or {}),
        "run_summary": run.report_ref or build_report_refs(run.connector_run_id)["run_summary"],
    }


def _connector_report_status(report_refs: dict[str, Any]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for name, path in report_refs.items():
        if not path:
            out[name] = False
            continue
        out[name] = Path(str(path)).exists()
    return out


def serialize_connector_run(db: Session, run: ConnectorRun) -> dict[str, Any]:
    latest_checkpoint = (
        db.query(ConnectorRunCheckpoint)
        .filter(ConnectorRunCheckpoint.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunCheckpoint.checkpoint_written_at.desc())
        .first()
    )
    latest_partition_cursor = (
        db.query(ConnectorRunPartitionCursor)
        .filter(ConnectorRunPartitionCursor.connector_run_id == run.connector_run_id)
        .order_by(ConnectorRunPartitionCursor.updated_at.desc())
        .first()
    )
    config = dict(run.request_config_json or {})
    surface_counts: dict[str, int] = {}
    surfaces = (
        db.query(ConnectorRunTarget.artifact_surface)
        .filter(ConnectorRunTarget.connector_run_id == run.connector_run_id)
        .distinct()
        .all()
    )
    for row in sorted({str(item[0] or "").strip() for item in surfaces if str(item[0] or "").strip()}):
        surface = row
        count = (
            db.query(ConnectorRunTarget)
            .filter(
                and_(
                    ConnectorRunTarget.connector_run_id == run.connector_run_id,
                    ConnectorRunTarget.artifact_surface == surface,
                )
            )
            .count()
        )
        surface_counts[surface] = int(count)

    telemetry = dict((run.query_plan_json or {}).get("telemetry") or {})
    latency_total_ms = int(telemetry.get("stage_latency_total_ms", 0) or 0)
    latency_samples = int(telemetry.get("stage_latency_samples", 0) or 0)
    bytes_downloaded = int(run.consumed_bytes or 0)
    bytes_skipped_due_unchanged = int(telemetry.get("bytes_skipped_due_to_unchanged_detection", 0) or 0)

    end_time = run.completed_at or _utcnow()
    if run.started_at and end_time > run.started_at:
        elapsed_hours = max((end_time - run.started_at).total_seconds() / 3600.0, 1e-9)
    else:
        elapsed_hours = 0.0
    processed_targets = max(int(run.discovered_count or 0) - int(run.nonterminal_target_count or 0), 0)
    targets_per_hour = float(processed_targets / elapsed_hours) if elapsed_hours > 0 else 0.0
    average_stage_latency_ms = float(latency_total_ms / latency_samples) if latency_samples > 0 else 0.0
    retryable_target_count = int(run.retryable_target_count or 0)
    terminal_target_count = int(run.terminal_target_count or 0)
    nonterminal_target_count = int(run.nonterminal_target_count or 0)

    fetch_policy_summary = dict(config.get("fetch_policy_summary") or {})
    if not fetch_policy_summary:
        fetch_policy_summary = {
            "mode": config.get("fetch_policy_mode", "strict_public_safe"),
            "surface_policy": config.get("surface_policy", "files_only"),
            "external_fetch_policy": config.get("external_fetch_policy", "sciencebase_only"),
            "allowed_hosts": list(dict.fromkeys(DEFAULT_ALLOWED_HOST_PATTERNS + [str(h) for h in config.get("allowed_hosts", [])])),
        }
    report_refs = _connector_report_refs_for_run(run)

    return {
        "connector_run_id": run.connector_run_id,
        "connector_key": run.connector_key,
        "source_system": run.source_system,
        "source_mode": run.source_mode,
        "status": run.status,
        "submitted_at": run.submitted_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "run_mode": config.get("run_mode", "one_shot_import"),
        "search_exhaustion_reason": run.search_exhaustion_reason,
        "submission_idempotency_key": run.submission_idempotency_key,
        "request_fingerprint": run.request_fingerprint,
        "source_query_fingerprint": run.source_query_fingerprint,
        "effective_search_envelope": {
            "params": run.effective_search_params_json or {},
            "filters": run.effective_filters_json or [],
            "sort": run.effective_sort,
            "order": run.effective_order,
            "page_size": run.effective_page_size,
        },
        "page_count_completed": int(run.page_count_completed or 0),
        "partition_count_completed": int(run.partition_count_completed or 0),
        "next_page_available": bool(run.next_page_available),
        "last_offset_committed": run.last_offset_committed,
        "lease_state": {
            "claimed": bool(run.execution_lease_owner),
            "lease_owner": run.execution_lease_owner,
            "lease_expires_at": run.execution_lease_expires_at,
            "lease_token_redacted_summary": (run.execution_lease_token or "")[:8],
        },
        "checkpoint_summary": {
            "current_partition": (latest_partition_cursor.partition_id if latest_partition_cursor else (latest_checkpoint.partition_cursor if latest_checkpoint else None)),
            "current_page": (latest_partition_cursor.last_offset if latest_partition_cursor else (latest_checkpoint.page_offset if latest_checkpoint else None)),
            "last_completed_target_ordinal": (run.query_plan_json or {}).get("checkpoint", {}).get("target_ordinal_completed"),
            "last_committed_stage": latest_checkpoint.last_successful_stage if latest_checkpoint else None,
        },
        "cancellation_state": {
            "requested": bool(run.cancellation_requested_at),
            "requested_at": run.cancellation_requested_at,
            "cancelled_at": run.cancelled_at,
        },
        "resume_eligibility": run.status in {"failed", "completed_with_errors", "cancelled", "pending"},
        "retryable_target_count": retryable_target_count,
        "terminal_target_count": terminal_target_count,
        "nonterminal_target_count": nonterminal_target_count,
        "current_phase": latest_checkpoint.phase if latest_checkpoint else "planning",
        "artifact_surface_counts": surface_counts,
        "partition_progress": {
            "strategy": config.get("partition_strategy", "none"),
            "page_size": config.get("page_size", 100),
            "next_page_available": bool(run.next_page_available),
            "last_offset_committed": run.last_offset_committed,
        },
        "throughput_summary": {
            "bytes_downloaded": bytes_downloaded,
            "bytes_skipped_due_to_unchanged_detection": bytes_skipped_due_unchanged,
            "targets_per_hour": round(targets_per_hour, 4),
            "average_stage_latency_ms": round(average_stage_latency_ms, 2),
        },
        "collapsed_duplicate_count": run.collapsed_duplicate_count,
        "deduped_within_run_count": run.deduped_within_run_count,
        "blocked_by_fetch_policy_count": run.blocked_by_fetch_policy_count,
        "not_modified_count": run.not_modified_count,
        "reconciliation_only_count": run.reconciliation_only_count,
        "budget_blocked_count": run.budget_blocked_count,
        "policy_skipped_count_by_reason_json": run.policy_skipped_count_by_reason_json or {},
        "discovered_count": run.discovered_count,
        "selected_count": run.selected_count,
        "ignored_count": run.ignored_count,
        "skipped_unchanged_count": run.skipped_unchanged_count,
        "downloaded_count": run.downloaded_count,
        "ingested_count": run.ingested_count,
        "profiled_count": run.profiled_count,
        "recommended_count": run.recommended_count,
        "failed_count": run.failed_count,
        "error_summary": run.error_summary,
        "reconciliation_summary": {
            "enabled": bool(config.get("reconciliation_enabled", False)),
            "terminal_statuses": sorted(RECONCILIATION_STATUSES),
            "count": int(run.reconciliation_only_count or 0),
        },
        "budget_summary": {
            "max_run_bytes": int(config.get("max_run_bytes", 512 * 1024 * 1024)),
            "consumed_bytes": int(run.consumed_bytes or 0),
            "budget_exhausted": bool(run.budget_exhausted),
            "budget_blocked_count": int(run.budget_blocked_count or 0),
        },
        "fetch_policy_summary": fetch_policy_summary,
        "dedupe_summary": {
            "collapsed_duplicate_count": run.collapsed_duplicate_count,
            "deduped_within_run_count": run.deduped_within_run_count,
        },
        "report_refs": report_refs,
        "manifest_refs": {
            "discovery_snapshot_ref": run.discovery_snapshot_ref,
            "selection_manifest_ref": run.selection_manifest_ref,
        },
    }


def list_connector_run_events(
    db: Session,
    *,
    connector_run_id: str,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    query = db.query(ConnectorRunEvent).filter(ConnectorRunEvent.connector_run_id == connector_run_id)
    total = query.count()
    items = query.order_by(ConnectorRunEvent.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "connector_run_id": connector_run_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [serialize_run_event(item) for item in items],
    }


def serialize_connector_run_reports(run: ConnectorRun) -> dict[str, Any]:
    report_refs = _connector_report_refs_for_run(run)
    return {
        "connector_run_id": run.connector_run_id,
        "reports": report_refs,
        "report_status": _connector_report_status(report_refs),
    }

