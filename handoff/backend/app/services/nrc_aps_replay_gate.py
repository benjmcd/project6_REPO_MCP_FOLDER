from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from app.services.nrc_aps_contract import (
    choose_dialect_order,
    compile_dialect_payload,
    infer_wire_dialect_from_request,
    normalize_document_response,
    normalize_search_response,
    normalize_wire_dialect,
    parse_iso_datetime,
    parse_json_response_text,
    payload_shape_hash,
    request_to_logical_query,
    status_class,
    strip_internal_fields,
    stable_json_hash,
)
from app.services.nrc_aps_replay_models import ReplayCase, ReplayCorpusIndex, ReplayExpected, ReplayRunReport


REPLAY_SCHEMA_VERSION = 1
REPLAY_TOOL_VERSION = "nrc_aps_replay_gate_v1"
APS_PROVIDER_KEY = "nrc_adams_aps"
DEFAULT_MAX_BODY_CHARS = 120_000

DEFAULT_SOURCE_ROOT = Path("backend/app/storage_test/connectors")
DEFAULT_CORPUS_DIR = Path("tests/fixtures/nrc_aps_replay/v1")
DEFAULT_VALIDATION_REPORT = Path("tests/reports/nrc_aps_replay_validation_report.json")
DEFAULT_DIFF_REPORT = Path("tests/reports/nrc_aps_replay_corpus_diff.json")
DEFAULT_OVERRIDE_FILE = Path("tests/fixtures/nrc_aps_replay/overrides.json")

REDACTED_REQUEST_ID = "<redacted:request_id>"
REDACTED_TIMESTAMP = "<redacted:timestamp>"
TRUNCATED_MARKER = "\n...[TRUNCATED_FOR_REPLAY_CORPUS]"


class ReplayGateError(RuntimeError):
    """Raised when build/validate/check operations fail."""


@dataclass(frozen=True)
class SourceRunContext:
    source_root: Path
    discovery_manifest_path: Path
    run_id: str
    manifest_payload: dict[str, Any]
    search_exchange_paths: list[Path]
    document_exchange_paths: list[Path]


@dataclass(frozen=True)
class ExchangeRecord:
    endpoint: str
    request_url: str
    request_body: dict[str, Any]
    request_headers_subset: dict[str, Any]
    request_id: str
    sent_at: str
    response_status: int
    response_headers: dict[str, Any]
    response_body_text: str
    received_at: str
    metadata: dict[str, Any]


class ReplayProviderAdapter(Protocol):
    provider_key: str

    def collect_run_contexts(self, source_root: Path) -> list[SourceRunContext]:
        ...


class NrcApsReplayAdapter:
    provider_key = APS_PROVIDER_KEY

    def collect_run_contexts(self, source_root: Path) -> list[SourceRunContext]:
        resolved_root = _resolve_connector_root(source_root)
        manifests_dir = resolved_root / "manifests"
        snapshots_dir = resolved_root / "snapshots"
        if not manifests_dir.exists():
            raise ReplayGateError(f"Manifest directory not found: {manifests_dir}")
        if not snapshots_dir.exists():
            raise ReplayGateError(f"Snapshot directory not found: {snapshots_dir}")

        contexts: list[SourceRunContext] = []
        for manifest_path in sorted(manifests_dir.glob("*_discovery.json"), key=lambda path: path.name):
            payload = _load_json(manifest_path)
            if not self._supports_manifest(payload):
                continue
            run_id = manifest_path.name.rsplit("_discovery.json", 1)[0]
            search_paths = self._collect_search_paths(payload, resolved_root=resolved_root)
            if not search_paths:
                search_paths = sorted(
                    snapshots_dir.glob(f"{run_id}_*_search_exchange.json"),
                    key=lambda path: path.name,
                )
            document_paths = sorted(
                snapshots_dir.glob(f"{run_id}_*_document_exchange.json"),
                key=lambda path: path.name,
            )
            contexts.append(
                SourceRunContext(
                    source_root=resolved_root,
                    discovery_manifest_path=manifest_path,
                    run_id=run_id,
                    manifest_payload=payload,
                    search_exchange_paths=search_paths,
                    document_exchange_paths=document_paths,
                )
            )
        return contexts

    def _supports_manifest(self, payload: dict[str, Any]) -> bool:
        provider = str(payload.get("provider") or "").strip().lower()
        if provider == self.provider_key:
            return True
        has_refs = isinstance(payload.get("search_exchange_refs"), list)
        has_query_shape = ("logical_query" in payload) or ("query_payload_normalized" in payload)
        return bool(has_refs and has_query_shape)

    def _collect_search_paths(self, payload: dict[str, Any], *, resolved_root: Path) -> list[Path]:
        snapshots_dir = resolved_root / "snapshots"
        refs: list[str] = []
        for value in payload.get("search_exchange_refs", []) if isinstance(payload.get("search_exchange_refs"), list) else []:
            refs.append(str(value))
        for page in payload.get("pages", []) if isinstance(payload.get("pages"), list) else []:
            if isinstance(page, dict) and page.get("exchange_ref"):
                refs.append(str(page.get("exchange_ref")))
            for attempt in page.get("attempts", []) if isinstance(page, dict) and isinstance(page.get("attempts"), list) else []:
                if isinstance(attempt, dict) and attempt.get("exchange_ref"):
                    refs.append(str(attempt.get("exchange_ref")))

        resolved: list[Path] = []
        seen: set[str] = set()
        for raw_ref in refs:
            candidate = _resolve_snapshot_ref(raw_ref, resolved_root=resolved_root, snapshots_dir=snapshots_dir)
            if not candidate:
                continue
            key = str(candidate.resolve())
            if key in seen:
                continue
            seen.add(key)
            resolved.append(candidate)
        return sorted(resolved, key=lambda path: path.name)


def _resolve_connector_root(source_root: Path) -> Path:
    root = Path(source_root).resolve()
    if (root / "manifests").exists() and (root / "snapshots").exists():
        return root
    if (root / "connectors" / "manifests").exists() and (root / "connectors" / "snapshots").exists():
        return (root / "connectors").resolve()
    raise ReplayGateError(
        f"Source root must contain manifests/snapshots, or connectors/manifests+snapshots: {root}"
    )


def _resolve_snapshot_ref(raw_ref: str, *, resolved_root: Path, snapshots_dir: Path) -> Path | None:
    if not raw_ref:
        return None
    direct = Path(raw_ref)
    if direct.exists():
        return direct.resolve()
    if not direct.is_absolute():
        relative = (resolved_root / direct).resolve()
        if relative.exists():
            return relative
    by_name = snapshots_dir / Path(raw_ref).name
    if by_name.exists():
        return by_name.resolve()
    return None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReplayGateError(f"JSON file not found: {path}") from exc
    except (OSError, ValueError) as exc:
        raise ReplayGateError(f"Invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReplayGateError(f"JSON payload must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
    path.write_text(serialized + "\n", encoding="utf-8")


def _stable_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _load_exchange_record(path: Path) -> ExchangeRecord:
    payload = _load_json(path)
    request_log = payload.get("request_log")
    response_log = payload.get("response_log")
    if not isinstance(request_log, dict) or not isinstance(response_log, dict):
        raise ReplayGateError(f"Exchange snapshot missing request_log/response_log: {path}")

    endpoint = str(request_log.get("endpoint") or "").strip()
    if not endpoint:
        raise ReplayGateError(f"Exchange snapshot missing request endpoint: {path}")
    request_body = request_log.get("request_body")
    if request_body is None:
        request_body = {}
    if not isinstance(request_body, dict):
        raise ReplayGateError(f"Exchange request_body must be object: {path}")

    status_code = response_log.get("status_code")
    try:
        response_status = int(status_code)
    except (TypeError, ValueError) as exc:
        raise ReplayGateError(f"Exchange response status must be int: {path}") from exc

    raw_body_text = response_log.get("raw_body_text")
    if raw_body_text is None:
        raw_body_text = ""
    if not isinstance(raw_body_text, str):
        raw_body_text = str(raw_body_text)

    request_headers_subset = request_log.get("request_headers_subset")
    if not isinstance(request_headers_subset, dict):
        request_headers_subset = {}
    response_headers = response_log.get("response_headers")
    if not isinstance(response_headers, dict):
        response_headers = {}
    metadata = response_log.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    return ExchangeRecord(
        endpoint=endpoint,
        request_url=str(request_log.get("request_url") or ""),
        request_body=request_body,
        request_headers_subset=request_headers_subset,
        request_id=str(request_log.get("request_id") or ""),
        sent_at=str(request_log.get("sent_at") or ""),
        response_status=response_status,
        response_headers=response_headers,
        response_body_text=raw_body_text,
        received_at=str(response_log.get("received_at") or ""),
        metadata=metadata,
    )


def _truncate_text(text: str, *, max_chars: int) -> tuple[str, dict[str, Any]]:
    if len(text) <= max_chars:
        return text, {"response_body_truncated": False}
    trimmed = text[:max_chars] + TRUNCATED_MARKER
    return trimmed, {
        "response_body_truncated": True,
        "response_body_original_length": len(text),
        "response_body_kept_length": len(trimmed),
    }


def _normalize_headers_subset(headers: dict[str, Any]) -> dict[str, Any]:
    keep = {"content-type", "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"}
    out: dict[str, Any] = {}
    for key, value in headers.items():
        normalized_key = str(key or "").strip().lower()
        if not normalized_key or normalized_key not in keep:
            continue
        out[normalized_key] = str(value)
    return out


def _endpoint_path(endpoint: str, request_url: str) -> str:
    endpoint_value = str(endpoint or "").strip()
    if " " in endpoint_value:
        return endpoint_value.split(" ", 1)[1].strip()
    if request_url:
        url_value = str(request_url).strip()
        if "://" in url_value:
            slash_index = url_value.find("/", url_value.find("://") + 3)
            if slash_index >= 0:
                return url_value[slash_index:]
    return endpoint_value


def _compute_signature(
    *,
    case_type: str,
    endpoint: str,
    dialect: str,
    case_status_class: str,
    envelope_variant: str,
    request_body: dict[str, Any],
) -> str:
    signature_payload = {
        "case_type": case_type,
        "endpoint": endpoint,
        "dialect": dialect,
        "status_class": case_status_class,
        "envelope_variant": envelope_variant,
        "payload_shape_hash": payload_shape_hash(request_body),
    }
    return stable_json_hash(signature_payload)


def _logical_roundtrip_hash(request_body: dict[str, Any], *, dialect: str) -> str | None:
    try:
        logical_query = request_to_logical_query(request_body)
        skip = int(request_body.get("skip", 0))
        take = int(request_body.get("take", 100))
        compiled = compile_dialect_payload(logical_query, dialect=dialect, skip=skip, take=take)
        return payload_shape_hash(compiled)
    except Exception:  # noqa: BLE001
        return None


def _build_search_case(
    *,
    context: SourceRunContext,
    snapshot_path: Path,
    record: ExchangeRecord,
    max_body_chars: int,
) -> ReplayCase:
    request_body = strip_internal_fields(dict(record.request_body or {}))
    parse_payload, parse_status = parse_json_response_text(record.response_body_text)
    normalized = normalize_search_response(parse_payload or {}) if parse_payload is not None else {
        "schema_variant": "unknown",
        "results_key": None,
        "raw_total_key": None,
        "count_returned": 0,
        "total_hits": None,
        "hits": [],
    }
    accessions = [
        str(hit.get("projection", {}).get("accession_number") or "").strip()
        for hit in normalized.get("hits", [])
        if isinstance(hit, dict)
    ]
    accessions = [item for item in accessions if item]
    projection_keys: list[str] = []
    raw_hits = normalized.get("hits")
    first_hit = raw_hits[0] if isinstance(raw_hits, list) and raw_hits else None
    if isinstance(first_hit, dict):
        projection = first_hit.get("projection")
        if isinstance(projection, dict):
            projection_keys = sorted([str(key) for key in projection.keys()])

    dialect_raw = str(record.metadata.get("wire_shape") or infer_wire_dialect_from_request(request_body))
    dialect = normalize_wire_dialect(dialect_raw, default=infer_wire_dialect_from_request(request_body))
    case_status_class = status_class(record.response_status)
    envelope_variant = str(normalized.get("schema_variant") or parse_status or "unknown")
    signature = _compute_signature(
        case_type="search",
        endpoint=record.endpoint,
        dialect=dialect,
        case_status_class=case_status_class,
        envelope_variant=envelope_variant,
        request_body=request_body,
    )
    truncated_body, trunc_meta = _truncate_text(record.response_body_text, max_chars=max_body_chars)
    roundtrip_hash = _logical_roundtrip_hash(request_body, dialect=dialect)

    expected = ReplayExpected(
        parse_status=parse_status,
        status_class=case_status_class,
        schema_variant=str(normalized.get("schema_variant") or "unknown"),
        results_key=(str(normalized.get("results_key")) if normalized.get("results_key") is not None else None),
        raw_total_key=(str(normalized.get("raw_total_key")) if normalized.get("raw_total_key") is not None else None),
        count_returned=int(normalized.get("count_returned") or 0),
        total_hits=(int(normalized.get("total_hits")) if normalized.get("total_hits") is not None else None),
        accession_numbers=accessions,
        projection_keys=projection_keys,
        roundtrip_payload_hash=roundtrip_hash,
    )
    metadata = {
        "provider": APS_PROVIDER_KEY,
        "source_manifest": context.discovery_manifest_path.name,
        "source_snapshot": snapshot_path.name,
        "request_id": REDACTED_REQUEST_ID if record.request_id else None,
        "request_sent_at": REDACTED_TIMESTAMP if record.sent_at else None,
        "response_received_at": REDACTED_TIMESTAMP if record.received_at else None,
        "request_path": _endpoint_path(record.endpoint, record.request_url),
        "dialect_observed_raw": dialect_raw,
        "dialect_observed": dialect,
        "response_headers_subset": _normalize_headers_subset(record.response_headers),
        "response_metadata_observed": dict(record.metadata or {}),
        "evidence_id": f"{context.run_id}:{snapshot_path.name}",
        **trunc_meta,
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}
    return ReplayCase(
        case_id="",
        case_type="search",
        signature=signature,
        endpoint=record.endpoint,
        dialect=dialect,
        request_body=request_body,
        response_status=int(record.response_status),
        response_body_text=truncated_body,
        response_headers=_normalize_headers_subset(record.response_headers),
        metadata=metadata,
        expected=expected,
        source_run_id=context.run_id,
        source_snapshot=snapshot_path.name,
        evidence_refs=[
            f"run:{context.run_id}",
            f"manifest:{context.discovery_manifest_path.name}",
            f"snapshot:{snapshot_path.name}",
        ],
        synthetic=False,
    )


def _build_document_case(
    *,
    context: SourceRunContext,
    snapshot_path: Path,
    record: ExchangeRecord,
    max_body_chars: int,
) -> ReplayCase:
    request_body = strip_internal_fields(dict(record.request_body or {}))
    parse_payload, parse_status = parse_json_response_text(record.response_body_text)
    normalized = normalize_document_response(parse_payload or {}) if parse_payload is not None else {
        "wrapper_variant": "unknown",
        "projection": {},
    }
    projection = normalized.get("projection")
    if not isinstance(projection, dict):
        projection = {}
    projection_keys = sorted([str(key) for key in projection.keys()])
    accession = str(projection.get("accession_number") or "").strip()
    case_status_class = status_class(record.response_status)
    envelope_variant = str(normalized.get("wrapper_variant") or parse_status or "unknown")
    signature = _compute_signature(
        case_type="document",
        endpoint=record.endpoint,
        dialect="document",
        case_status_class=case_status_class,
        envelope_variant=envelope_variant,
        request_body=request_body,
    )
    truncated_body, trunc_meta = _truncate_text(record.response_body_text, max_chars=max_body_chars)
    expected = ReplayExpected(
        parse_status=parse_status,
        status_class=case_status_class,
        wrapper_variant=str(normalized.get("wrapper_variant") or "unknown"),
        accession_numbers=([accession] if accession else []),
        projection_keys=projection_keys,
    )
    metadata = {
        "provider": APS_PROVIDER_KEY,
        "source_manifest": context.discovery_manifest_path.name,
        "source_snapshot": snapshot_path.name,
        "request_id": REDACTED_REQUEST_ID if record.request_id else None,
        "request_sent_at": REDACTED_TIMESTAMP if record.sent_at else None,
        "response_received_at": REDACTED_TIMESTAMP if record.received_at else None,
        "request_path": _endpoint_path(record.endpoint, record.request_url),
        "response_headers_subset": _normalize_headers_subset(record.response_headers),
        "response_metadata_observed": dict(record.metadata or {}),
        "evidence_id": f"{context.run_id}:{snapshot_path.name}",
        **trunc_meta,
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}
    return ReplayCase(
        case_id="",
        case_type="document",
        signature=signature,
        endpoint=record.endpoint,
        dialect="document",
        request_body=request_body,
        response_status=int(record.response_status),
        response_body_text=truncated_body,
        response_headers=_normalize_headers_subset(record.response_headers),
        metadata=metadata,
        expected=expected,
        source_run_id=context.run_id,
        source_snapshot=snapshot_path.name,
        evidence_refs=[
            f"run:{context.run_id}",
            f"manifest:{context.discovery_manifest_path.name}",
            f"snapshot:{snapshot_path.name}",
        ],
        synthetic=False,
    )


def _build_synthetic_search_case(
    *,
    case_name: str,
    dialect: str,
    request_body: dict[str, Any],
    response_status: int,
    response_body_text: str,
) -> ReplayCase:
    normalized_dialect = normalize_wire_dialect(dialect, default=dialect)
    parse_payload, parse_status = parse_json_response_text(response_body_text)
    normalized = normalize_search_response(parse_payload or {}) if parse_payload is not None else {
        "schema_variant": "unknown",
        "results_key": None,
        "raw_total_key": None,
        "count_returned": 0,
        "total_hits": None,
        "hits": [],
    }
    accessions = [
        str(hit.get("projection", {}).get("accession_number") or "").strip()
        for hit in normalized.get("hits", [])
        if isinstance(hit, dict)
    ]
    accessions = [item for item in accessions if item]
    projection_keys: list[str] = []
    raw_hits = normalized.get("hits")
    first_hit = raw_hits[0] if isinstance(raw_hits, list) and raw_hits else None
    if isinstance(first_hit, dict):
        projection = first_hit.get("projection")
        if isinstance(projection, dict):
            projection_keys = sorted([str(key) for key in projection.keys()])

    case_status_class = status_class(response_status)
    endpoint = "POST /aps/api/search"
    signature = _compute_signature(
        case_type="search",
        endpoint=endpoint,
        dialect=normalized_dialect,
        case_status_class=case_status_class,
        envelope_variant=str(normalized.get("schema_variant") or parse_status or "unknown"),
        request_body=request_body,
    )
    expected = ReplayExpected(
        parse_status=parse_status,
        status_class=case_status_class,
        schema_variant=str(normalized.get("schema_variant") or "unknown"),
        results_key=(str(normalized.get("results_key")) if normalized.get("results_key") is not None else None),
        raw_total_key=(str(normalized.get("raw_total_key")) if normalized.get("raw_total_key") is not None else None),
        count_returned=int(normalized.get("count_returned") or 0),
        total_hits=(int(normalized.get("total_hits")) if normalized.get("total_hits") is not None else None),
        accession_numbers=accessions,
        projection_keys=projection_keys,
        roundtrip_payload_hash=_logical_roundtrip_hash(request_body, dialect=normalized_dialect),
    )
    return ReplayCase(
        case_id="",
        case_type="search",
        signature=signature,
        endpoint=endpoint,
        dialect=normalized_dialect,
        request_body=strip_internal_fields(request_body),
        response_status=response_status,
        response_body_text=response_body_text,
        response_headers={"content-type": "application/json"},
        metadata={
            "provider": APS_PROVIDER_KEY,
            "source_manifest": "synthetic",
            "source_snapshot": f"synthetic_{case_name}.json",
            "evidence_id": f"synthetic:{case_name}",
        },
        expected=expected,
        source_run_id="synthetic",
        source_snapshot=f"synthetic_{case_name}.json",
        evidence_refs=[f"synthetic:{case_name}"],
        synthetic=True,
    )


def _build_synthetic_negotiator_case(
    *,
    case_name: str,
    forced_mode: str,
    capabilities: list[dict[str, Any]],
    now_utc: str,
) -> ReplayCase:
    now = parse_iso_datetime(now_utc)
    dialect_order = choose_dialect_order(forced_mode=forced_mode, capabilities=capabilities, now=now)
    request_body = {"case": case_name}
    signature = _compute_signature(
        case_type="negotiator",
        endpoint="internal://dialect-negotiator",
        dialect="auto_probe",
        case_status_class="success",
        envelope_variant="dialect_order",
        request_body=request_body,
    )
    return ReplayCase(
        case_id="",
        case_type="negotiator",
        signature=signature,
        endpoint="internal://dialect-negotiator",
        dialect="auto_probe",
        request_body=request_body,
        response_status=200,
        response_body_text="{}",
        response_headers={},
        metadata={
            "forced_mode": forced_mode,
            "capabilities": capabilities,
            "now_utc": now_utc,
            "provider": APS_PROVIDER_KEY,
            "source_manifest": "synthetic",
            "source_snapshot": f"synthetic_{case_name}.json",
            "evidence_id": f"synthetic:{case_name}",
        },
        expected=ReplayExpected(
            parse_status="synthetic",
            status_class="success",
            dialect_order=dialect_order,
        ),
        source_run_id="synthetic",
        source_snapshot=f"synthetic_{case_name}.json",
        evidence_refs=[f"synthetic:{case_name}"],
        synthetic=True,
    )


def _build_synthetic_cases() -> list[ReplayCase]:
    base_shape_a_request = {
        "q": "__synthetic_shape_a_success__",
        "filters": [],
        "anyFilters": [],
        "mainLibFilter": True,
        "legacyLibFilter": False,
        "sort": "DateAddedTimestamp",
        "sortDirection": 1,
        "skip": 0,
        "take": 10,
    }
    base_guide_request = {
        "searchCriteria": {
            "q": "__synthetic_guide_failure__",
            "mainLibFilter": True,
            "legacyLibFilter": False,
            "properties": [],
        },
        "sort": "DateAddedTimestamp",
        "sortDirection": 1,
        "skip": 0,
        "take": 10,
    }
    base_shape_b_request = {
        "queryString": "__synthetic_shape_b_failure__",
        "docketNumber": "05000000",
        "filters": [],
        "sort": "-DateAddedTimestamp",
        "skip": 0,
        "take": 10,
    }
    cases = [
        _build_synthetic_search_case(
            case_name="shape_a_success_results",
            dialect="shape_a",
            request_body=base_shape_a_request,
            response_status=200,
            response_body_text=(
                '{"count":1,"results":[{"document":{"AccessionNumber":"MLSYN000001","DocumentTitle":"Synthetic"}}]}'
            ),
        ),
        _build_synthetic_search_case(
            case_name="guide_native_failure",
            dialect="guide_native",
            request_body=base_guide_request,
            response_status=500,
            response_body_text="{}",
        ),
        _build_synthetic_search_case(
            case_name="shape_b_failure",
            dialect="shape_b",
            request_body=base_shape_b_request,
            response_status=500,
            response_body_text="{}",
        ),
        _build_synthetic_search_case(
            case_name="documents_envelope_success",
            dialect="shape_a",
            request_body={
                **base_shape_a_request,
                "q": "__synthetic_documents_envelope__",
            },
            response_status=200,
            response_body_text=(
                '{"total":1,"documents":[{"AccessionNumber":"MLSYN000002","DocumentTitle":"Synthetic Document"}]}'
            ),
        ),
        _build_synthetic_search_case(
            case_name="parse_empty_body",
            dialect="shape_a",
            request_body={
                **base_shape_a_request,
                "q": "__synthetic_parse_empty__",
            },
            response_status=200,
            response_body_text="",
        ),
        _build_synthetic_search_case(
            case_name="parse_invalid_json",
            dialect="shape_a",
            request_body={
                **base_shape_a_request,
                "q": "__synthetic_parse_invalid__",
            },
            response_status=200,
            response_body_text="{",
        ),
        _build_synthetic_search_case(
            case_name="parse_non_dict_json",
            dialect="shape_a",
            request_body={
                **base_shape_a_request,
                "q": "__synthetic_parse_non_dict__",
            },
            response_status=200,
            response_body_text="[]",
        ),
        _build_synthetic_negotiator_case(
            case_name="negotiator_forced_shape_b",
            forced_mode="shape_b",
            capabilities=[],
            now_utc="2026-01-01T00:00:00Z",
        ),
        _build_synthetic_negotiator_case(
            case_name="negotiator_capability_preferred",
            forced_mode="auto_probe",
            capabilities=[
                {
                    "dialect": "guide_native",
                    "success_count": 8,
                    "failure_count": 1,
                    "last_status": 200,
                    "cooldown_until": None,
                },
                {
                    "dialect": "shape_a",
                    "success_count": 2,
                    "failure_count": 0,
                    "last_status": 200,
                    "cooldown_until": None,
                },
            ],
            now_utc="2026-01-01T00:00:00Z",
        ),
        _build_synthetic_negotiator_case(
            case_name="negotiator_cooldown_fallback",
            forced_mode="auto_probe",
            capabilities=[
                {
                    "dialect": "guide_native",
                    "success_count": 6,
                    "failure_count": 0,
                    "last_status": 200,
                    "cooldown_until": "2099-01-01T00:00:00Z",
                },
                {
                    "dialect": "shape_a",
                    "success_count": 2,
                    "failure_count": 0,
                    "last_status": 200,
                    "cooldown_until": None,
                },
            ],
            now_utc="2026-01-01T00:00:00Z",
        ),
    ]
    return cases


def _dedupe_cases(cases: list[ReplayCase]) -> list[ReplayCase]:
    selected: dict[str, ReplayCase] = {}
    for case in sorted(
        cases,
        key=lambda row: (
            row.signature,
            1 if row.synthetic else 0,
            str(row.source_snapshot or ""),
            row.case_type,
            row.dialect,
        ),
    ):
        if case.signature not in selected:
            selected[case.signature] = case

    out: list[ReplayCase] = []
    for case in sorted(selected.values(), key=lambda row: (row.case_type, row.signature)):
        case_id = f"{case.case_type}_{case.signature}"
        out.append(
            ReplayCase(
                case_id=case_id,
                case_type=case.case_type,
                signature=case.signature,
                endpoint=case.endpoint,
                dialect=case.dialect,
                request_body=case.request_body,
                response_status=case.response_status,
                response_body_text=case.response_body_text,
                response_headers=case.response_headers,
                metadata=case.metadata,
                expected=case.expected,
                source_run_id=case.source_run_id,
                source_snapshot=case.source_snapshot,
                evidence_refs=case.evidence_refs,
                synthetic=case.synthetic,
            )
        )
    return out


def _compute_coverage(cases: list[ReplayCase]) -> dict[str, int]:
    coverage: dict[str, int] = {}

    def bump(key: str) -> None:
        coverage[key] = int(coverage.get(key, 0)) + 1

    for case in cases:
        bump(f"case_type.{case.case_type}")
        bump(f"dialect.{case.dialect}")
        bump(f"status_class.{case.expected.status_class}")
        bump(f"parse_status.{case.expected.parse_status}")
        if case.expected.schema_variant:
            bump(f"schema_variant.{case.expected.schema_variant}")
        if case.expected.wrapper_variant:
            bump(f"wrapper_variant.{case.expected.wrapper_variant}")
        if case.expected.results_key:
            bump(f"results_key.{case.expected.results_key}")
    return dict(sorted(coverage.items(), key=lambda item: item[0]))


def _validate_minimum_coverage(cases: list[ReplayCase]) -> None:
    def has_case(predicate: Any) -> bool:
        return any(bool(predicate(case)) for case in cases)

    required_checks = {
        "guide_native_failure": lambda case: (
            case.case_type == "search"
            and case.dialect == "guide_native"
            and case.expected.status_class == "server_error"
        ),
        "shape_a_success": lambda case: (
            case.case_type == "search"
            and case.dialect == "shape_a"
            and case.expected.status_class == "success"
        ),
        "shape_b_failure": lambda case: (
            case.case_type == "search"
            and case.dialect == "shape_b"
            and case.expected.status_class == "server_error"
        ),
        "parse_empty_body": lambda case: case.expected.parse_status == "empty_body",
        "parse_invalid_json": lambda case: case.expected.parse_status == "invalid_json",
        "parse_non_dict_json": lambda case: case.expected.parse_status == "non_dict_json",
        "results_envelope": lambda case: case.expected.results_key == "results",
        "documents_envelope": lambda case: case.expected.results_key == "documents",
        "negotiator_case": lambda case: case.case_type == "negotiator",
    }
    missing = [name for name, predicate in required_checks.items() if not has_case(predicate)]
    if missing:
        raise ReplayGateError(
            "Replay corpus is missing required coverage cases: " + ", ".join(sorted(missing))
        )


def _collect_cases(
    *,
    source_roots: list[Path],
    max_body_chars: int,
) -> tuple[list[ReplayCase], list[SourceRunContext]]:
    adapter: ReplayProviderAdapter = NrcApsReplayAdapter()
    contexts: list[SourceRunContext] = []
    cases: list[ReplayCase] = []

    for source_root in source_roots:
        contexts.extend(adapter.collect_run_contexts(source_root))

    for context in sorted(contexts, key=lambda row: row.discovery_manifest_path.name):
        for snapshot_path in context.search_exchange_paths:
            record = _load_exchange_record(snapshot_path)
            if record.endpoint.upper().startswith("GET "):
                continue
            cases.append(
                _build_search_case(
                    context=context,
                    snapshot_path=snapshot_path,
                    record=record,
                    max_body_chars=max_body_chars,
                )
            )
        for snapshot_path in context.document_exchange_paths:
            record = _load_exchange_record(snapshot_path)
            cases.append(
                _build_document_case(
                    context=context,
                    snapshot_path=snapshot_path,
                    record=record,
                    max_body_chars=max_body_chars,
                )
            )

    cases.extend(_build_synthetic_cases())
    deduped = _dedupe_cases(cases)
    _validate_minimum_coverage(deduped)
    return deduped, contexts


def _snapshot_dir_fingerprint(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for file_path in sorted(path.rglob("*"), key=lambda row: str(row)):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(path).as_posix()
        out[rel] = _stable_file_hash(file_path)
    return out


def _dir_diff(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    added = sorted(after_keys - before_keys)
    removed = sorted(before_keys - after_keys)
    changed = sorted(
        key
        for key in sorted(before_keys & after_keys)
        if before.get(key) != after.get(key)
    )
    return {
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "added_files": added,
        "removed_files": removed,
        "changed_files": changed,
    }


def _coverage_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, dict[str, int]]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    out: dict[str, dict[str, int]] = {}
    for key in keys:
        left = int(before.get(key, 0))
        right = int(after.get(key, 0))
        if left == right:
            continue
        out[key] = {"before": left, "after": right}
    return out


def _build_index(
    *,
    cases: list[ReplayCase],
    source_roots: list[Path],
    contexts: list[SourceRunContext],
) -> ReplayCorpusIndex:
    coverage = _compute_coverage(cases)
    source_run_ids = sorted({context.run_id for context in contexts})
    source_manifest_names = sorted({context.discovery_manifest_path.name for context in contexts})
    source_fingerprint = stable_json_hash(
        {
            "source_roots": [str(Path(root).resolve()) for root in source_roots],
            "source_run_ids": source_run_ids,
            "source_manifests": source_manifest_names,
            "case_signatures": [case.signature for case in cases],
            "schema_version": REPLAY_SCHEMA_VERSION,
        }
    )
    return ReplayCorpusIndex(
        schema_version=REPLAY_SCHEMA_VERSION,
        tool_version=REPLAY_TOOL_VERSION,
        source_roots=[str(Path(root).resolve()) for root in source_roots],
        source_run_ids=source_run_ids,
        case_count=len(cases),
        case_files=[],
        case_checksums={},
        source_fingerprint=source_fingerprint,
        coverage=coverage,
        generated_at=f"source_fingerprint:{source_fingerprint[:16]}",
        source_manifest_count=len(source_manifest_names),
        diff_summary_file=None,
    )


def _write_corpus(
    *,
    out_dir: Path,
    cases: list[ReplayCase],
    index: ReplayCorpusIndex,
) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    cases_dir = out_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    case_files: list[str] = []
    case_checksums: dict[str, str] = {}
    for case in cases:
        file_name = f"{case.case_id}.json"
        rel_path = f"cases/{file_name}"
        file_path = out_dir / rel_path
        payload = case.to_dict()
        _write_json(file_path, payload)
        case_files.append(rel_path)
        case_checksums[rel_path] = stable_json_hash(payload)

    index.case_files = sorted(case_files)
    index.case_checksums = {key: case_checksums[key] for key in sorted(case_checksums.keys())}
    _write_json(out_dir / "index.json", index.to_dict())


def build_replay_corpus(
    *,
    source_roots: list[Path],
    out_dir: Path,
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS,
    diff_report_path: Path | None = None,
) -> dict[str, Any]:
    roots = [Path(root).resolve() for root in source_roots]
    prior_fingerprint = _snapshot_dir_fingerprint(out_dir) if out_dir.exists() else {}
    prior_coverage: dict[str, int] = {}
    prior_index_path = out_dir / "index.json"
    if prior_index_path.exists():
        prior_index_payload = _load_json(prior_index_path)
        prior_coverage = {
            str(key): int(value) for key, value in dict(prior_index_payload.get("coverage") or {}).items()
        }

    cases, contexts = _collect_cases(source_roots=roots, max_body_chars=max_body_chars)
    index = _build_index(cases=cases, source_roots=roots, contexts=contexts)

    temp_parent = out_dir.parent
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nrc_aps_replay_build_", dir=str(temp_parent)) as temp_dir_str:
        temp_dir = Path(temp_dir_str) / "v1"
        _write_corpus(out_dir=temp_dir, cases=cases, index=index)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        shutil.move(str(temp_dir), str(out_dir))

    new_fingerprint = _snapshot_dir_fingerprint(out_dir)
    file_diff = _dir_diff(prior_fingerprint, new_fingerprint)
    coverage_delta = _coverage_delta(prior_coverage, index.coverage)
    diff_summary = {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "tool_version": REPLAY_TOOL_VERSION,
        "out_dir": str(out_dir.resolve()),
        "file_diff": file_diff,
        "coverage_delta": coverage_delta,
        "case_count": len(cases),
        "source_run_count": len(index.source_run_ids),
        "source_manifest_count": index.source_manifest_count,
        "source_fingerprint": index.source_fingerprint,
    }
    if diff_report_path is not None:
        _write_json(diff_report_path.resolve(), diff_summary)
    return diff_summary


def _load_override_map(override_path: Path | None) -> dict[str, dict[str, Any]]:
    if override_path is None:
        return {}
    path = Path(override_path)
    if not path.exists():
        return {}

    payload = _load_json(path)
    overrides = payload.get("overrides")
    if not isinstance(overrides, list):
        raise ReplayGateError(f"Override file must contain an 'overrides' list: {path}")

    out: dict[str, dict[str, Any]] = {}
    today = date.today()
    for raw in overrides:
        if not isinstance(raw, dict):
            raise ReplayGateError(f"Override entry must be object: {path}")
        case_id = str(raw.get("case_id") or "").strip()
        reason = str(raw.get("reason") or "").strip()
        expires_on_raw = str(raw.get("expires_on") or "").strip()
        ignore_paths = [str(item).strip() for item in raw.get("ignore_paths", []) if str(item).strip()]
        if not case_id or not reason or not expires_on_raw or not ignore_paths:
            raise ReplayGateError(
                f"Override entries require case_id, reason, expires_on, and ignore_paths: {path}"
            )
        try:
            expires_on = date.fromisoformat(expires_on_raw)
        except ValueError as exc:
            raise ReplayGateError(f"Override expires_on must be YYYY-MM-DD: {path}: {case_id}") from exc
        if expires_on < today:
            raise ReplayGateError(f"Override expired for case_id={case_id} on {expires_on_raw}")
        out[case_id] = {
            "reason": reason,
            "expires_on": expires_on_raw,
            "ignore_paths": set(ignore_paths),
        }
    return out


def _append_mismatch(
    *,
    case: ReplayCase,
    field_path: str,
    expected_value: Any,
    actual_value: Any,
    failures: list[dict[str, Any]],
    warnings: list[str],
    overrides: dict[str, dict[str, Any]],
    overrides_counter: dict[str, int],
) -> None:
    override = overrides.get(case.case_id)
    if override and field_path in set(override.get("ignore_paths", set())):
        overrides_counter["count"] = int(overrides_counter.get("count", 0)) + 1
        warnings.append(
            f"override applied case_id={case.case_id} field={field_path} "
            f"reason={override.get('reason')} expires_on={override.get('expires_on')}"
        )
        return
    failures.append(
        {
            "case_id": case.case_id,
            "case_type": case.case_type,
            "field": field_path,
            "expected": expected_value,
            "actual": actual_value,
            "source_run_id": case.source_run_id,
            "source_snapshot": case.source_snapshot,
        }
    )


def _validate_no_opaque_failure(
    *,
    case: ReplayCase,
    computed_status_class: str,
    computed_parse_status: str,
    failures: list[dict[str, Any]],
    warnings: list[str],
    overrides: dict[str, dict[str, Any]],
    overrides_counter: dict[str, int],
) -> None:
    is_failure = computed_status_class != "success" or computed_parse_status != "ok"
    if not is_failure:
        return
    if not case.evidence_refs:
        _append_mismatch(
            case=case,
            field_path="evidence_refs",
            expected_value="non-empty evidence refs",
            actual_value=case.evidence_refs,
            failures=failures,
            warnings=warnings,
            overrides=overrides,
            overrides_counter=overrides_counter,
        )
    evidence_id = str(case.metadata.get("evidence_id") or "").strip()
    if not evidence_id:
        _append_mismatch(
            case=case,
            field_path="metadata.evidence_id",
            expected_value="traceable evidence identifier",
            actual_value=evidence_id,
            failures=failures,
            warnings=warnings,
            overrides=overrides,
            overrides_counter=overrides_counter,
        )


def _compare_value(
    *,
    case: ReplayCase,
    field_path: str,
    expected_value: Any,
    actual_value: Any,
    failures: list[dict[str, Any]],
    warnings: list[str],
    overrides: dict[str, dict[str, Any]],
    overrides_counter: dict[str, int],
) -> None:
    if expected_value == actual_value:
        return
    _append_mismatch(
        case=case,
        field_path=field_path,
        expected_value=expected_value,
        actual_value=actual_value,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )


def _validate_search_case(
    *,
    case: ReplayCase,
    failures: list[dict[str, Any]],
    warnings: list[str],
    overrides: dict[str, dict[str, Any]],
    overrides_counter: dict[str, int],
) -> None:
    parsed_payload, parse_status = parse_json_response_text(case.response_body_text)
    computed_status_class = status_class(case.response_status)
    _compare_value(
        case=case,
        field_path="expected.parse_status",
        expected_value=case.expected.parse_status,
        actual_value=parse_status,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.status_class",
        expected_value=case.expected.status_class,
        actual_value=computed_status_class,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )

    normalized = normalize_search_response(parsed_payload or {}) if parsed_payload is not None else {
        "schema_variant": "unknown",
        "results_key": None,
        "raw_total_key": None,
        "count_returned": 0,
        "total_hits": None,
        "hits": [],
    }
    _compare_value(
        case=case,
        field_path="expected.schema_variant",
        expected_value=case.expected.schema_variant,
        actual_value=str(normalized.get("schema_variant") or "unknown"),
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.results_key",
        expected_value=case.expected.results_key,
        actual_value=(str(normalized.get("results_key")) if normalized.get("results_key") is not None else None),
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.raw_total_key",
        expected_value=case.expected.raw_total_key,
        actual_value=(str(normalized.get("raw_total_key")) if normalized.get("raw_total_key") is not None else None),
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.count_returned",
        expected_value=case.expected.count_returned,
        actual_value=int(normalized.get("count_returned") or 0),
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.total_hits",
        expected_value=case.expected.total_hits,
        actual_value=(int(normalized.get("total_hits")) if normalized.get("total_hits") is not None else None),
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )

    accessions = [
        str(hit.get("projection", {}).get("accession_number") or "").strip()
        for hit in normalized.get("hits", [])
        if isinstance(hit, dict)
    ]
    accessions = [item for item in accessions if item]
    _compare_value(
        case=case,
        field_path="expected.accession_numbers",
        expected_value=case.expected.accession_numbers,
        actual_value=accessions,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )

    projection_keys: list[str] = []
    raw_hits = normalized.get("hits")
    first_hit = raw_hits[0] if isinstance(raw_hits, list) and raw_hits else None
    if isinstance(first_hit, dict):
        projection = first_hit.get("projection")
        if isinstance(projection, dict):
            projection_keys = sorted([str(key) for key in projection.keys()])
    _compare_value(
        case=case,
        field_path="expected.projection_keys",
        expected_value=case.expected.projection_keys,
        actual_value=projection_keys,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )

    if case.expected.roundtrip_payload_hash:
        try:
            logical_query = request_to_logical_query(case.request_body)
            skip = int(case.request_body.get("skip", 0))
            take = int(case.request_body.get("take", 100))
            compiled = compile_dialect_payload(
                logical_query,
                dialect=normalize_wire_dialect(case.dialect, default=case.dialect),
                skip=skip,
                take=take,
            )
            roundtrip_hash = payload_shape_hash(compiled)
        except Exception as exc:  # noqa: BLE001
            roundtrip_hash = f"error:{exc}"
        _compare_value(
            case=case,
            field_path="expected.roundtrip_payload_hash",
            expected_value=case.expected.roundtrip_payload_hash,
            actual_value=roundtrip_hash,
            failures=failures,
            warnings=warnings,
            overrides=overrides,
            overrides_counter=overrides_counter,
        )

    expected_signature = _compute_signature(
        case_type="search",
        endpoint=case.endpoint,
        dialect=case.dialect,
        case_status_class=case.expected.status_class,
        envelope_variant=str(case.expected.schema_variant or case.expected.parse_status or "unknown"),
        request_body=case.request_body,
    )
    _compare_value(
        case=case,
        field_path="signature",
        expected_value=expected_signature,
        actual_value=case.signature,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _validate_no_opaque_failure(
        case=case,
        computed_status_class=computed_status_class,
        computed_parse_status=parse_status,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )


def _validate_document_case(
    *,
    case: ReplayCase,
    failures: list[dict[str, Any]],
    warnings: list[str],
    overrides: dict[str, dict[str, Any]],
    overrides_counter: dict[str, int],
) -> None:
    parsed_payload, parse_status = parse_json_response_text(case.response_body_text)
    computed_status_class = status_class(case.response_status)
    _compare_value(
        case=case,
        field_path="expected.parse_status",
        expected_value=case.expected.parse_status,
        actual_value=parse_status,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.status_class",
        expected_value=case.expected.status_class,
        actual_value=computed_status_class,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    normalized = normalize_document_response(parsed_payload or {}) if parsed_payload is not None else {
        "wrapper_variant": "unknown",
        "projection": {},
    }
    projection = normalized.get("projection")
    if not isinstance(projection, dict):
        projection = {}
    projection_keys = sorted([str(key) for key in projection.keys()])
    accession = str(projection.get("accession_number") or "").strip()

    _compare_value(
        case=case,
        field_path="expected.wrapper_variant",
        expected_value=case.expected.wrapper_variant,
        actual_value=str(normalized.get("wrapper_variant") or "unknown"),
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.accession_numbers",
        expected_value=case.expected.accession_numbers,
        actual_value=([accession] if accession else []),
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.projection_keys",
        expected_value=case.expected.projection_keys,
        actual_value=projection_keys,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )

    expected_signature = _compute_signature(
        case_type="document",
        endpoint=case.endpoint,
        dialect=case.dialect,
        case_status_class=case.expected.status_class,
        envelope_variant=str(case.expected.wrapper_variant or case.expected.parse_status or "unknown"),
        request_body=case.request_body,
    )
    _compare_value(
        case=case,
        field_path="signature",
        expected_value=expected_signature,
        actual_value=case.signature,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _validate_no_opaque_failure(
        case=case,
        computed_status_class=computed_status_class,
        computed_parse_status=parse_status,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )


def _validate_negotiator_case(
    *,
    case: ReplayCase,
    failures: list[dict[str, Any]],
    warnings: list[str],
    overrides: dict[str, dict[str, Any]],
    overrides_counter: dict[str, int],
) -> None:
    forced_mode = str(case.metadata.get("forced_mode") or "auto_probe")
    capabilities = case.metadata.get("capabilities")
    now = parse_iso_datetime(case.metadata.get("now_utc"))
    if not isinstance(capabilities, list):
        capabilities = []
    dialect_order = choose_dialect_order(forced_mode=forced_mode, capabilities=capabilities, now=now)
    _compare_value(
        case=case,
        field_path="expected.dialect_order",
        expected_value=case.expected.dialect_order,
        actual_value=dialect_order,
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.parse_status",
        expected_value=case.expected.parse_status,
        actual_value="synthetic",
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )
    _compare_value(
        case=case,
        field_path="expected.status_class",
        expected_value=case.expected.status_class,
        actual_value="success",
        failures=failures,
        warnings=warnings,
        overrides=overrides,
        overrides_counter=overrides_counter,
    )


def validate_replay_corpus(
    *,
    corpus_dir: Path,
    report_path: Path,
    override_path: Path | None = None,
) -> ReplayRunReport:
    corpus_root = Path(corpus_dir).resolve()
    index_path = corpus_root / "index.json"
    if not index_path.exists():
        raise ReplayGateError(f"Replay index missing: {index_path}")

    index = ReplayCorpusIndex.from_dict(_load_json(index_path))
    if int(index.schema_version) != REPLAY_SCHEMA_VERSION:
        raise ReplayGateError(
            f"Unsupported replay corpus schema: {index.schema_version}; expected {REPLAY_SCHEMA_VERSION}"
        )

    overrides = _load_override_map(override_path)
    overrides_counter = {"count": 0}
    cases: list[ReplayCase] = []
    for rel_case_path in index.case_files:
        case_path = corpus_root / rel_case_path
        if not case_path.exists():
            raise ReplayGateError(f"Missing replay case file listed in index: {case_path}")
        case_payload = _load_json(case_path)
        cases.append(ReplayCase.from_dict(case_payload))

    failures: list[dict[str, Any]] = []
    warnings: list[str] = []
    for case in cases:
        if case.case_type == "search":
            _validate_search_case(
                case=case,
                failures=failures,
                warnings=warnings,
                overrides=overrides,
                overrides_counter=overrides_counter,
            )
        elif case.case_type == "document":
            _validate_document_case(
                case=case,
                failures=failures,
                warnings=warnings,
                overrides=overrides,
                overrides_counter=overrides_counter,
            )
        elif case.case_type == "negotiator":
            _validate_negotiator_case(
                case=case,
                failures=failures,
                warnings=warnings,
                overrides=overrides,
                overrides_counter=overrides_counter,
            )
        else:
            failures.append(
                {
                    "case_id": case.case_id,
                    "case_type": case.case_type,
                    "field": "case_type",
                    "expected": "search|document|negotiator",
                    "actual": case.case_type,
                    "source_run_id": case.source_run_id,
                    "source_snapshot": case.source_snapshot,
                }
            )

    report = ReplayRunReport(
        schema_version=REPLAY_SCHEMA_VERSION,
        corpus_path=str(corpus_root),
        passed=(len(failures) == 0),
        total_cases=len(cases),
        failed_cases=len(failures),
        warning_count=len(warnings),
        failures=failures,
        warnings=warnings,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        overrides_applied=int(overrides_counter.get("count", 0)),
    )
    _write_json(report_path.resolve(), report.to_dict())
    return report


def check_replay_corpus(
    *,
    source_roots: list[Path],
    corpus_dir: Path,
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS,
    diff_report_path: Path | None = None,
) -> dict[str, Any]:
    corpus_root = Path(corpus_dir).resolve()
    if not corpus_root.exists():
        raise ReplayGateError(f"Replay corpus directory not found: {corpus_root}")

    baseline_fingerprint = _snapshot_dir_fingerprint(corpus_root)
    with tempfile.TemporaryDirectory(prefix="nrc_aps_replay_check_") as temp_dir_str:
        temp_root = Path(temp_dir_str) / "v1"
        build_replay_corpus(
            source_roots=source_roots,
            out_dir=temp_root,
            max_body_chars=max_body_chars,
            diff_report_path=None,
        )
        current_fingerprint = _snapshot_dir_fingerprint(temp_root)

    file_diff = _dir_diff(baseline_fingerprint, current_fingerprint)
    passed = (
        int(file_diff.get("added_count", 0)) == 0
        and int(file_diff.get("removed_count", 0)) == 0
        and int(file_diff.get("changed_count", 0)) == 0
    )
    summary = {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "tool_version": REPLAY_TOOL_VERSION,
        "corpus_dir": str(corpus_root),
        "passed": passed,
        "file_diff": file_diff,
    }
    if diff_report_path is not None:
        _write_json(diff_report_path.resolve(), summary)
    return summary


def _parse_source_roots(values: list[str] | None) -> list[Path]:
    if not values:
        return [DEFAULT_SOURCE_ROOT.resolve()]
    out: list[Path] = []
    seen: set[str] = set()
    for raw in values:
        root = Path(raw).resolve()
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        out.append(root)
    return out


def _print_build_summary(summary: dict[str, Any]) -> None:
    file_diff = dict(summary.get("file_diff") or {})
    print(
        "Replay corpus build complete:"
        f" cases={summary.get('case_count')} source_runs={summary.get('source_run_count')}"
        f" manifests={summary.get('source_manifest_count')}"
    )
    print(
        "Diff summary:"
        f" added={file_diff.get('added_count', 0)}"
        f" removed={file_diff.get('removed_count', 0)}"
        f" changed={file_diff.get('changed_count', 0)}"
    )


def _print_validation_summary(report: ReplayRunReport, report_path: Path) -> None:
    status = "PASS" if report.passed else "FAIL"
    print(
        f"Replay validation {status}: total_cases={report.total_cases} "
        f"failed={report.failed_cases} warnings={report.warning_count} "
        f"overrides_applied={report.overrides_applied}"
    )
    print(f"Validation report: {report_path.resolve()}")
    if report.failed_cases:
        for failure in report.failures[:20]:
            print(
                f"- case_id={failure.get('case_id')} field={failure.get('field')} "
                f"expected={failure.get('expected')} actual={failure.get('actual')}"
            )
        if report.failed_cases > 20:
            print(f"... plus {report.failed_cases - 20} additional failures")


def _print_check_summary(summary: dict[str, Any], diff_report_path: Path | None) -> None:
    file_diff = dict(summary.get("file_diff") or {})
    status = "PASS" if bool(summary.get("passed")) else "FAIL"
    print(
        f"Replay corpus check {status}: added={file_diff.get('added_count', 0)} "
        f"removed={file_diff.get('removed_count', 0)} changed={file_diff.get('changed_count', 0)}"
    )
    if diff_report_path is not None:
        print(f"Diff report: {diff_report_path.resolve()}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NRC APS replay corpus build/validate/check gate.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_cmd = subparsers.add_parser("build", help="Build deterministic NRC APS replay corpus.")
    build_cmd.add_argument("--source-root", action="append", default=None)
    build_cmd.add_argument("--out", default=str(DEFAULT_CORPUS_DIR))
    build_cmd.add_argument("--max-body-chars", type=int, default=DEFAULT_MAX_BODY_CHARS)
    build_cmd.add_argument("--diff-report", default=str(DEFAULT_DIFF_REPORT))

    validate_cmd = subparsers.add_parser("validate", help="Validate replay corpus against pure contract logic.")
    validate_cmd.add_argument("--corpus", default=str(DEFAULT_CORPUS_DIR))
    validate_cmd.add_argument("--report", default=str(DEFAULT_VALIDATION_REPORT))
    validate_cmd.add_argument("--override", default=str(DEFAULT_OVERRIDE_FILE))

    check_cmd = subparsers.add_parser("check", help="Fail if regenerated corpus differs from checked-in corpus.")
    check_cmd.add_argument("--source-root", action="append", default=None)
    check_cmd.add_argument("--corpus", default=str(DEFAULT_CORPUS_DIR))
    check_cmd.add_argument("--max-body-chars", type=int, default=DEFAULT_MAX_BODY_CHARS)
    check_cmd.add_argument("--diff-report", default=str(DEFAULT_DIFF_REPORT))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            source_roots = _parse_source_roots(args.source_root)
            summary = build_replay_corpus(
                source_roots=source_roots,
                out_dir=Path(args.out).resolve(),
                max_body_chars=max(1, int(args.max_body_chars)),
                diff_report_path=(Path(args.diff_report).resolve() if args.diff_report else None),
            )
            _print_build_summary(summary)
            return 0

        if args.command == "validate":
            override_path: Path | None = Path(args.override).resolve() if args.override else None
            report = validate_replay_corpus(
                corpus_dir=Path(args.corpus).resolve(),
                report_path=Path(args.report).resolve(),
                override_path=override_path,
            )
            _print_validation_summary(report, Path(args.report))
            return 0 if report.passed else 1

        if args.command == "check":
            source_roots = _parse_source_roots(args.source_root)
            summary = check_replay_corpus(
                source_roots=source_roots,
                corpus_dir=Path(args.corpus).resolve(),
                max_body_chars=max(1, int(args.max_body_chars)),
                diff_report_path=(Path(args.diff_report).resolve() if args.diff_report else None),
            )
            _print_check_summary(summary, Path(args.diff_report).resolve() if args.diff_report else None)
            return 0 if bool(summary.get("passed")) else 1
    except ReplayGateError as exc:
        print(f"NRC APS replay gate error: {exc}")
        return 2

    parser.print_help()
    return 2
