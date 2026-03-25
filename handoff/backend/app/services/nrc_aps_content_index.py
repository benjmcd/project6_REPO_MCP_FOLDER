from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage
from app.services import nrc_aps_artifact_ingestion
from app.services import nrc_aps_document_processing
from app.services import nrc_aps_safeguards


APS_CONTENT_UNITS_SCHEMA_ID = "aps.content_units.v2"
APS_CONTENT_INDEX_RUN_SCHEMA_ID = "aps.content_index_run.v1"
APS_CONTENT_INDEX_FAILURE_SCHEMA_ID = "aps.content_index_failure.v1"
APS_CONTENT_INDEX_GATE_SCHEMA_ID = "aps.content_index_gate.v1"
APS_CONTENT_INDEX_SCHEMA_VERSION = 1

APS_CONTENT_CONTRACT_ID = "aps_content_units_v2"
APS_CHUNKING_CONTRACT_ID = "aps_chunking_v2"
APS_NORMALIZATION_CONTRACT_ID = nrc_aps_artifact_ingestion.APS_TEXT_NORMALIZATION_CONTRACT_ID

APS_CONTENT_STATUS_INDEXED = "indexed"
APS_CONTENT_STATUS_EMPTY_NORMALIZED_TEXT = "empty_normalized_text"
APS_CONTENT_STATUS_ARTIFACT_NOT_AVAILABLE = nrc_aps_artifact_ingestion.APS_ARTIFACT_OUTCOME_NOT_AVAILABLE
APS_CONTENT_STATUS_LOW_QUALITY_TEXT = "low_quality_text"
APS_CONTENT_STATUS_UNUSABLE_TEXT = "unusable_text"

APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE = 1000
APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP = 200
APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK = 50

APS_CONTENT_INDEX_GATE_FAILURE_MISSING_REF = "missing_content_units_ref"
APS_CONTENT_INDEX_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_content_units_ref"
APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH = "content_units_schema_mismatch"
APS_CONTENT_INDEX_GATE_FAILURE_UNKNOWN_CONTRACT_ID = "unknown_contract_id"
APS_CONTENT_INDEX_GATE_FAILURE_DB_DOCUMENT_MISSING = "artifact_db_document_missing"
APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_COUNT_MISMATCH = "artifact_db_chunk_count_mismatch"
APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_MISSING = "artifact_db_chunk_missing"
APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_FIELD_MISMATCH = "artifact_db_chunk_field_mismatch"
APS_CONTENT_INDEX_GATE_FAILURE_DB_LINKAGE_MISSING = "artifact_db_linkage_missing"
APS_CONTENT_INDEX_GATE_FAILURE_CHECKSUM_MISMATCH = "checksum_mismatch"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def _file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_object(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> str:
    return nrc_aps_safeguards.write_json_atomic(path, payload)


def normalize_chunking_policy(config: dict[str, Any]) -> dict[str, int]:
    chunk_size_chars = _safe_int(config.get("content_chunk_size_chars"), APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE)
    chunk_overlap_chars = _safe_int(config.get("content_chunk_overlap_chars"), APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP)
    min_chunk_chars = _safe_int(config.get("content_chunk_min_chars"), APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK)
    if chunk_size_chars <= 0:
        raise ValueError("content_chunk_size_chars must be > 0")
    if chunk_overlap_chars < 0 or chunk_overlap_chars >= chunk_size_chars:
        raise ValueError("content_chunk_overlap_chars must satisfy 0 <= overlap < chunk_size")
    if min_chunk_chars < 1 or min_chunk_chars > chunk_size_chars:
        raise ValueError("content_chunk_min_chars must satisfy 1 <= min <= chunk_size")
    return {
        "chunk_size_chars": chunk_size_chars,
        "chunk_overlap_chars": chunk_overlap_chars,
        "min_chunk_chars": min_chunk_chars,
    }


def normalize_query_tokens(value: Any) -> list[str]:
    normalized = unicodedata.normalize("NFC", str(value or "")).lower()
    chars = [char if char.isalnum() else " " for char in normalized]
    collapsed = " ".join("".join(chars).split())
    if not collapsed:
        return []
    return collapsed.split(" ")


def _token_frequencies(text: str) -> Counter[str]:
    return Counter(normalize_query_tokens(text))


def _chunk_id(
    *,
    content_id: str,
    chunk_ordinal: int,
    start_char: int,
    end_char: int,
    chunk_text_sha256: str,
) -> str:
    return _stable_hash(
        {
            "content_id": content_id,
            "chunking_contract_id": APS_CHUNKING_CONTRACT_ID,
            "chunk_ordinal": int(chunk_ordinal),
            "start_char": int(start_char),
            "end_char": int(end_char),
            "chunk_text_sha256": str(chunk_text_sha256 or ""),
        }
    )


def _content_id(
    *,
    normalized_text_sha256: str | None,
    accession_number: str | None,
    content_status: str,
    availability_reason: str | None,
) -> str:
    identity_hint = str(normalized_text_sha256 or "").strip()
    if not identity_hint:
        identity_hint = f"{str(accession_number or '').strip()}::{str(availability_reason or content_status)}"
    return _stable_hash(
        {
            "content_contract_id": APS_CONTENT_CONTRACT_ID,
            "chunking_contract_id": APS_CHUNKING_CONTRACT_ID,
            "identity_hint": identity_hint,
        }
    )


def chunk_document_units(
    *,
    ordered_units: list[dict[str, Any]],
    chunk_size_chars: int,
    chunk_overlap_chars: int,
    min_chunk_chars: int,
) -> list[dict[str, Any]]:
    units = [dict(item or {}) for item in ordered_units if isinstance(item, dict) and str(item.get("text") or "").strip()]
    if not units:
        return []
    chunks: list[dict[str, Any]] = []
    buffer: list[dict[str, Any]] = []
    ordinal = 0
    for unit in units:
        buffer.append(unit)
        buffer_text = "\n".join(str(item.get("text") or "").strip() for item in buffer if str(item.get("text") or "").strip())
        if len(buffer_text) < int(chunk_size_chars):
            continue
        candidate = _build_chunk_from_units(buffer, chunk_ordinal=ordinal)
        if len(str(candidate.get("chunk_text") or "")) >= int(min_chunk_chars) and not _chunk_matches_last(
            candidate=candidate,
            chunks=chunks,
        ):
            chunks.append(candidate)
            ordinal += 1
        buffer = _carry_overlap_units(buffer, overlap_chars=int(chunk_overlap_chars))
    if buffer:
        candidate = _build_chunk_from_units(buffer, chunk_ordinal=ordinal)
        if len(str(candidate.get("chunk_text") or "")) >= int(min_chunk_chars) and not _chunk_matches_last(
            candidate=candidate,
            chunks=chunks,
        ):
            chunks.append(candidate)
    return chunks


def _write_normalized_text_blob(*, artifact_storage_dir: str | Path, text: str) -> dict[str, Any]:
    content = str(text or "").encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    base = Path(artifact_storage_dir) / "nrc_adams_aps" / "normalized_text" / digest[0:2] / digest[2:4]
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
        "normalized_char_count": len(str(text or "")),
    }


def _load_processed_document(
    *,
    run_id: str,
    target_id: str,
    target_artifact_payload: dict[str, Any],
    artifact_storage_dir: str | Path,
) -> dict[str, Any]:
    extraction = dict(target_artifact_payload.get("extraction") or {})
    download = dict(target_artifact_payload.get("download") or {})
    normalized_ref = str(extraction.get("normalized_text_ref") or "").strip()
    diagnostics_ref = str(extraction.get("diagnostics_ref") or "").strip()
    normalization_contract_id = str(extraction.get("normalization_contract_id") or "").strip() or APS_NORMALIZATION_CONTRACT_ID
    diagnostics_payload = _read_json_object(diagnostics_ref)
    if normalized_ref:
        candidate = Path(normalized_ref)
        if candidate.exists():
            try:
                text = candidate.read_text(encoding="utf-8")
                return {
                    "normalized_text": text,
                    "normalized_text_ref": str(candidate),
                    "normalized_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "normalization_contract_id": normalization_contract_id,
                    "ordered_units": [dict(item or {}) for item in (diagnostics_payload.get("ordered_units") or []) if isinstance(item, dict)],
                    "page_count": int(diagnostics_payload.get("page_count") or extraction.get("page_count") or 0),
                    "quality_status": str(diagnostics_payload.get("quality_status") or extraction.get("quality_status") or ""),
                    "document_class": str(diagnostics_payload.get("document_class") or extraction.get("document_class") or ""),
                    "effective_content_type": str(
                        diagnostics_payload.get("effective_content_type") or extraction.get("effective_content_type") or ""
                    ),
                    "diagnostics_ref": diagnostics_ref or None,
                }
            except OSError:
                pass

    blob_ref = str(download.get("blob_ref") or "").strip()
    if not blob_ref:
        raise RuntimeError("content_blob_ref_missing")
    blob_path = Path(blob_ref)
    if not blob_path.exists():
        raise RuntimeError("content_blob_ref_unresolvable")
    content_type = str(download.get("content_type") or "")
    content = blob_path.read_bytes()
    extracted = nrc_aps_artifact_ingestion.extract_and_normalize(content=content, content_type=content_type)
    normalized_text = str(extracted.get("normalized_text") or "")
    normalized_blob = _write_normalized_text_blob(artifact_storage_dir=artifact_storage_dir, text=normalized_text)
    diagnostics_payload = _build_processing_diagnostics_payload(
        run_id=run_id,
        target_id=target_id,
        target_artifact_payload=target_artifact_payload,
        processed=extracted,
    )
    diagnostics_blob = nrc_aps_artifact_ingestion.write_processing_diagnostics(
        artifact_storage_dir=artifact_storage_dir,
        run_id=run_id,
        target_id=target_id,
        payload=diagnostics_payload,
    )
    return {
        "normalized_text": normalized_text,
        "normalized_text_ref": str(normalized_blob.get("normalized_text_ref") or ""),
        "normalized_text_sha256": str(normalized_blob.get("normalized_text_sha256") or ""),
        "normalization_contract_id": str(extracted.get("normalization_contract_id") or APS_NORMALIZATION_CONTRACT_ID),
        "ordered_units": [dict(item or {}) for item in (extracted.get("ordered_units") or []) if isinstance(item, dict)],
        "page_count": int(extracted.get("page_count") or 0),
        "quality_status": str(extracted.get("quality_status") or ""),
        "document_class": str(extracted.get("document_class") or ""),
        "effective_content_type": str(extracted.get("effective_content_type") or ""),
        "diagnostics_ref": str(diagnostics_blob.get("diagnostics_ref") or "") or None,
    }


def _build_chunk_from_units(units: list[dict[str, Any]], *, chunk_ordinal: int) -> dict[str, Any]:
    chunk_text = "\n".join(str(item.get("text") or "").strip() for item in units if str(item.get("text") or "").strip())
    start_char = int(units[0].get("start_char") or 0)
    end_char = int(units[-1].get("end_char") or start_char + len(chunk_text))
    page_numbers = [int(item.get("page_number") or 0) for item in units if int(item.get("page_number") or 0) > 0]
    chunk_sha = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
    unit_kinds = sorted(list(dict.fromkeys(str(item.get("unit_kind") or "").strip() for item in units if str(item.get("unit_kind") or "").strip())))
    return {
        "chunk_ordinal": int(chunk_ordinal),
        "start_char": start_char,
        "end_char": end_char,
        "chunk_text": chunk_text,
        "chunk_text_sha256": chunk_sha,
        "page_start": min(page_numbers) if page_numbers else None,
        "page_end": max(page_numbers) if page_numbers else None,
        "unit_kind": unit_kinds[0] if len(unit_kinds) == 1 else "mixed_units",
    }


def _chunk_matches_last(*, candidate: dict[str, Any], chunks: list[dict[str, Any]]) -> bool:
    if not chunks:
        return False
    previous = chunks[-1]
    comparable_keys = (
        "start_char",
        "end_char",
        "chunk_text_sha256",
        "page_start",
        "page_end",
        "unit_kind",
    )
    return all(previous.get(key) == candidate.get(key) for key in comparable_keys)


def _build_processing_diagnostics_payload(
    *,
    run_id: str,
    target_id: str,
    target_artifact_payload: dict[str, Any],
    processed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": "aps.document_processing_diagnostics.v1",
        "schema_version": 1,
        "run_id": str(run_id),
        "target_id": str(target_id),
        "accession_number": target_artifact_payload.get("accession_number"),
        "declared_content_type": processed.get("declared_content_type"),
        "sniffed_content_type": processed.get("sniffed_content_type"),
        "effective_content_type": processed.get("effective_content_type"),
        "media_detection_contract_id": processed.get("media_detection_contract_id"),
        "media_detection_status": processed.get("media_detection_status"),
        "media_detection_reason": processed.get("media_detection_reason"),
        "signature_basis": processed.get("signature_basis"),
        "document_processing_contract_id": processed.get("document_processing_contract_id"),
        "extractor_family": processed.get("extractor_family"),
        "extractor_id": processed.get("extractor_id"),
        "extractor_version": processed.get("extractor_version"),
        "document_class": processed.get("document_class"),
        "quality_status": processed.get("quality_status"),
        "quality_metrics": processed.get("quality_metrics"),
        "degradation_codes": processed.get("degradation_codes"),
        "page_count": processed.get("page_count"),
        "page_summaries": processed.get("page_summaries"),
        "ordered_units": processed.get("ordered_units"),
    }


def _carry_overlap_units(units: list[dict[str, Any]], *, overlap_chars: int) -> list[dict[str, Any]]:
    if overlap_chars <= 0:
        return []
    carried: list[dict[str, Any]] = []
    consumed = 0
    for unit in reversed(units):
        text = str(unit.get("text") or "").strip()
        if not text:
            continue
        carried.insert(0, unit)
        consumed += len(text) + 1
        if consumed >= int(overlap_chars):
            break
    return carried


def content_units_artifact_path(*, run_id: str, target_id: str, reports_dir: str | Path) -> Path:
    safe_run = _safe_path_token(run_id)
    safe_target = _safe_path_token(target_id)
    return Path(reports_dir) / f"{safe_run}_{safe_target}_aps_content_units_v2.json"


def run_artifact_path(*, run_id: str, reports_dir: str | Path) -> Path:
    safe_run = _safe_path_token(run_id)
    return Path(reports_dir) / f"{safe_run}_aps_content_index_run_v1.json"


def failure_artifact_path(*, run_id: str, reports_dir: str | Path) -> Path:
    safe_run = _safe_path_token(run_id)
    return Path(reports_dir) / f"{safe_run}_aps_content_index_failure_v1.json"


def artifact_paths(*, run_id: str, reports_dir: str | Path) -> dict[str, str]:
    return {
        "aps_content_index": str(run_artifact_path(run_id=run_id, reports_dir=reports_dir)),
        "aps_content_index_failure": str(failure_artifact_path(run_id=run_id, reports_dir=reports_dir)),
    }


def build_content_units_payload_from_target_artifact(
    *,
    run_id: str,
    target_id: str,
    target_artifact_payload: dict[str, Any],
    source_metadata_ref: str | None,
    artifact_storage_dir: str | Path,
    chunking_policy: dict[str, int],
) -> dict[str, Any]:
    pipeline_mode = nrc_aps_artifact_ingestion.normalize_pipeline_mode(target_artifact_payload.get("pipeline_mode"))
    artifact_outcome_status = str(target_artifact_payload.get("outcome_status") or "").strip().lower()
    accession_number = str(target_artifact_payload.get("accession_number") or "").strip() or None
    evidence = dict(target_artifact_payload.get("evidence") or {})
    download = dict(target_artifact_payload.get("download") or {})
    extraction = dict(target_artifact_payload.get("extraction") or {})

    content_status = APS_CONTENT_STATUS_INDEXED
    availability_reason = str(target_artifact_payload.get("availability_reason") or "").strip() or None
    normalized_text = ""
    normalized_text_ref: str | None = None
    normalized_text_sha256: str | None = None
    normalization_contract_id: str | None = None
    quality_status = str(extraction.get("quality_status") or "")
    document_class = str(extraction.get("document_class") or "")
    effective_content_type = str(extraction.get("effective_content_type") or "")
    diagnostics_ref = str(extraction.get("diagnostics_ref") or "").strip() or None
    page_count = int(extraction.get("page_count") or 0)
    ordered_units: list[dict[str, Any]] = []
    if artifact_outcome_status == APS_CONTENT_STATUS_ARTIFACT_NOT_AVAILABLE:
        content_status = APS_CONTENT_STATUS_ARTIFACT_NOT_AVAILABLE
    else:
        processed = _load_processed_document(
            run_id=run_id,
            target_id=target_id,
            target_artifact_payload=target_artifact_payload,
            artifact_storage_dir=artifact_storage_dir,
        )
        normalized_text = str(processed.get("normalized_text") or "")
        normalized_text_ref = str(processed.get("normalized_text_ref") or "") or None
        normalized_text_sha256 = str(processed.get("normalized_text_sha256") or "") or None
        normalization_contract_id = str(processed.get("normalization_contract_id") or "") or None
        quality_status = str(processed.get("quality_status") or quality_status)
        document_class = str(processed.get("document_class") or document_class)
        effective_content_type = str(processed.get("effective_content_type") or effective_content_type)
        diagnostics_ref = str(processed.get("diagnostics_ref") or diagnostics_ref or "") or None
        page_count = int(processed.get("page_count") or page_count)
        ordered_units = [dict(item or {}) for item in (processed.get("ordered_units") or []) if isinstance(item, dict)]
        if len(normalized_text) == 0:
            content_status = APS_CONTENT_STATUS_EMPTY_NORMALIZED_TEXT
        elif quality_status in {
            nrc_aps_document_processing.APS_QUALITY_STATUS_WEAK,
            nrc_aps_document_processing.APS_QUALITY_STATUS_UNUSABLE,
        }:
            content_status = (
                APS_CONTENT_STATUS_LOW_QUALITY_TEXT
                if quality_status == nrc_aps_document_processing.APS_QUALITY_STATUS_WEAK
                else APS_CONTENT_STATUS_UNUSABLE_TEXT
            )

    content_id = _content_id(
        normalized_text_sha256=normalized_text_sha256,
        accession_number=accession_number,
        content_status=content_status,
        availability_reason=availability_reason,
    )
    chunks: list[dict[str, Any]] = []
    if len(normalized_text) > 0 and content_status == APS_CONTENT_STATUS_INDEXED:
        base_chunks = chunk_document_units(
            ordered_units=ordered_units or [
                {
                    "page_number": 1,
                    "unit_kind": "text_block",
                    "text": normalized_text,
                    "start_char": 0,
                    "end_char": len(normalized_text),
                }
            ],
            chunk_size_chars=int(chunking_policy["chunk_size_chars"]),
            chunk_overlap_chars=int(chunking_policy["chunk_overlap_chars"]),
            min_chunk_chars=int(chunking_policy["min_chunk_chars"]),
        )
        chunks = [
            {
                **item,
                "chunk_id": _chunk_id(
                    content_id=content_id,
                    chunk_ordinal=int(item["chunk_ordinal"]),
                    start_char=int(item["start_char"]),
                    end_char=int(item["end_char"]),
                    chunk_text_sha256=str(item["chunk_text_sha256"]),
                ),
            }
            for item in base_chunks
        ]

    payload = {
        "schema_id": APS_CONTENT_UNITS_SCHEMA_ID,
        "schema_version": APS_CONTENT_INDEX_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": str(run_id),
        "target_id": str(target_id),
        "accession_number": accession_number,
        "pipeline_mode": pipeline_mode,
        "artifact_outcome_status": artifact_outcome_status,
        "content_contract_id": APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": normalization_contract_id,
        "content_id": content_id,
        "content_status": content_status,
        "chunk_size_chars": int(chunking_policy["chunk_size_chars"]),
        "chunk_overlap_chars": int(chunking_policy["chunk_overlap_chars"]),
        "min_chunk_chars": int(chunking_policy["min_chunk_chars"]),
        "normalized_char_count": len(normalized_text),
        "normalized_text_ref": normalized_text_ref,
        "normalized_text_sha256": normalized_text_sha256,
        "effective_content_type": effective_content_type or None,
        "document_class": document_class or None,
        "quality_status": quality_status or None,
        "page_count": int(page_count),
        "diagnostics_ref": diagnostics_ref,
        "source_metadata_ref": str(source_metadata_ref or "").strip() or None,
        "blob_ref": str(download.get("blob_ref") or "").strip() or None,
        "blob_sha256": str(download.get("blob_sha256") or "").strip() or None,
        "download_exchange_ref": str(download.get("download_exchange_ref") or "").strip() or None,
        "discovery_ref": str(evidence.get("discovery_ref") or "").strip() or None,
        "selection_ref": str(evidence.get("selection_ref") or "").strip() or None,
        "availability_reason": availability_reason,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    payload["payload_sha256"] = _stable_hash(payload)
    return payload


def build_run_artifact_payload(
    *,
    run_id: str,
    run_status: str,
    selected_targets: int,
    content_units_artifacts: list[dict[str, Any]],
    indexing_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = [dict(item or {}) for item in content_units_artifacts if isinstance(item, dict)]
    failure_rows = [dict(item or {}) for item in indexing_failures if isinstance(item, dict)]
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("content_status") or "unknown").strip() or "unknown"
        status_counts[status] = int(status_counts.get(status, 0)) + 1
    failure_counts: dict[str, int] = {}
    for row in failure_rows:
        code = str(row.get("code") or "content_index_failure").strip()
        failure_counts[code] = int(failure_counts.get(code, 0)) + 1
    payload = {
        "schema_id": APS_CONTENT_INDEX_RUN_SCHEMA_ID,
        "schema_version": APS_CONTENT_INDEX_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": str(run_id or ""),
        "run_status": str(run_status or ""),
        "run_outcome": "no_targets_selected" if int(selected_targets) == 0 else "targets_processed",
        "selected_targets": int(selected_targets),
        "processed_targets": len(rows),
        "indexed_content_units": len(rows),
        "content_status_counts": status_counts,
        "indexing_failures_count": len(failure_rows),
        "indexing_failure_code_counts": failure_counts,
        "content_units_artifacts": rows,
        "indexing_failures": failure_rows,
    }
    payload["payload_sha256"] = _stable_hash(payload)
    return payload


def build_failure_artifact_payload(
    *,
    run_id: str,
    run_status: str,
    error_class: str,
    error_message: str,
    failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_id": APS_CONTENT_INDEX_FAILURE_SCHEMA_ID,
        "schema_version": APS_CONTENT_INDEX_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": str(run_id or ""),
        "run_status": str(run_status or ""),
        "error_class": str(error_class or "runtime_error"),
        "error_message": str(error_message or ""),
        "failures": [dict(item or {}) for item in (failures or []) if isinstance(item, dict)],
    }
    payload["payload_sha256"] = _stable_hash(payload)
    return payload


def upsert_content_units_payload(db: Session, *, payload: dict[str, Any]) -> None:
    content_id = str(payload.get("content_id") or "").strip()
    content_contract_id = str(payload.get("content_contract_id") or "").strip()
    chunking_contract_id = str(payload.get("chunking_contract_id") or "").strip()
    if not content_id:
        raise ValueError("content_id_missing")
    if content_contract_id != APS_CONTENT_CONTRACT_ID or chunking_contract_id != APS_CHUNKING_CONTRACT_ID:
        raise ValueError("unknown_contract_id")

    with db.begin_nested():
        doc = (
            db.query(ApsContentDocument)
            .filter(
                and_(
                    ApsContentDocument.content_id == content_id,
                    ApsContentDocument.content_contract_id == content_contract_id,
                    ApsContentDocument.chunking_contract_id == chunking_contract_id,
                )
            )
            .first()
        )
        if not doc:
            doc = ApsContentDocument(
                content_id=content_id,
                content_contract_id=content_contract_id,
                chunking_contract_id=chunking_contract_id,
            )
            db.add(doc)
            db.flush()
        doc.normalization_contract_id = str(payload.get("normalization_contract_id") or "") or None
        doc.normalized_text_sha256 = str(payload.get("normalized_text_sha256") or "") or None
        doc.normalized_char_count = int(payload.get("normalized_char_count") or 0)
        doc.chunk_count = int(payload.get("chunk_count") or 0)
        doc.content_status = str(payload.get("content_status") or "")
        doc.media_type = str(payload.get("effective_content_type") or "").strip() or None
        doc.document_class = str(payload.get("document_class") or "").strip() or None
        doc.quality_status = str(payload.get("quality_status") or "").strip() or None
        doc.page_count = int(payload.get("page_count") or 0)
        doc.diagnostics_ref = None
        doc.updated_at = datetime.now(timezone.utc)
        db.flush()

        incoming_chunks = [dict(item or {}) for item in (payload.get("chunks") or []) if isinstance(item, dict)]
        existing_chunks = (
            db.query(ApsContentChunk)
            .filter(
                and_(
                    ApsContentChunk.content_id == content_id,
                    ApsContentChunk.content_contract_id == content_contract_id,
                    ApsContentChunk.chunking_contract_id == chunking_contract_id,
                )
            )
            .all()
        )
        existing_by_id = {str(item.chunk_id): item for item in existing_chunks}
        incoming_ids = {str(item.get("chunk_id") or "") for item in incoming_chunks}
        for existing_id, row in existing_by_id.items():
            if existing_id and existing_id not in incoming_ids:
                db.delete(row)
        for chunk in incoming_chunks:
            chunk_id = str(chunk.get("chunk_id") or "").strip()
            if not chunk_id:
                raise ValueError("chunk_id_missing")
            row = existing_by_id.get(chunk_id)
            if not row:
                row = ApsContentChunk(
                    content_id=content_id,
                    chunk_id=chunk_id,
                    content_contract_id=content_contract_id,
                    chunking_contract_id=chunking_contract_id,
                )
                db.add(row)
            row.chunk_ordinal = int(chunk.get("chunk_ordinal") or 0)
            row.start_char = int(chunk.get("start_char") or 0)
            row.end_char = int(chunk.get("end_char") or 0)
            row.chunk_text = str(chunk.get("chunk_text") or "")
            row.chunk_text_sha256 = str(chunk.get("chunk_text_sha256") or "")
            row.page_start = int(chunk.get("page_start")) if chunk.get("page_start") is not None else None
            row.page_end = int(chunk.get("page_end")) if chunk.get("page_end") is not None else None
            row.unit_kind = str(chunk.get("unit_kind") or "").strip() or None
            row.quality_status = str(payload.get("quality_status") or "").strip() or None
            row.updated_at = datetime.now(timezone.utc)
        db.flush()

        linkage = (
            db.query(ApsContentLinkage)
            .filter(
                and_(
                    ApsContentLinkage.content_id == content_id,
                    ApsContentLinkage.run_id == str(payload.get("run_id") or ""),
                    ApsContentLinkage.target_id == str(payload.get("target_id") or ""),
                    ApsContentLinkage.content_contract_id == content_contract_id,
                    ApsContentLinkage.chunking_contract_id == chunking_contract_id,
                )
            )
            .first()
        )
        if not linkage:
            linkage = ApsContentLinkage(
                content_id=content_id,
                run_id=str(payload.get("run_id") or ""),
                target_id=str(payload.get("target_id") or ""),
                content_contract_id=content_contract_id,
                chunking_contract_id=chunking_contract_id,
            )
            db.add(linkage)
        linkage.accession_number = str(payload.get("accession_number") or "").strip() or None
        linkage.content_units_ref = str(payload.get("content_units_ref") or "").strip() or None
        linkage.normalized_text_ref = str(payload.get("normalized_text_ref") or "").strip() or None
        linkage.normalized_text_sha256 = str(payload.get("normalized_text_sha256") or "").strip() or None
        linkage.blob_ref = str(payload.get("blob_ref") or "").strip() or None
        linkage.blob_sha256 = str(payload.get("blob_sha256") or "").strip() or None
        linkage.download_exchange_ref = str(payload.get("download_exchange_ref") or "").strip() or None
        linkage.discovery_ref = str(payload.get("discovery_ref") or "").strip() or None
        linkage.selection_ref = str(payload.get("selection_ref") or "").strip() or None
        linkage.diagnostics_ref = str(payload.get("diagnostics_ref") or "").strip() or None
        db.flush()


def _serialize_index_row(
    *,
    linkage: ApsContentLinkage,
    document: ApsContentDocument,
    chunk: ApsContentChunk,
) -> dict[str, Any]:
    return {
        "content_id": linkage.content_id,
        "chunk_id": chunk.chunk_id,
        "content_contract_id": linkage.content_contract_id,
        "chunking_contract_id": linkage.chunking_contract_id,
        "chunk_ordinal": int(chunk.chunk_ordinal or 0),
        "start_char": int(chunk.start_char or 0),
        "end_char": int(chunk.end_char or 0),
        "chunk_text": str(chunk.chunk_text or ""),
        "chunk_text_sha256": str(chunk.chunk_text_sha256 or ""),
        "page_start": int(chunk.page_start or 0) if chunk.page_start is not None else None,
        "page_end": int(chunk.page_end or 0) if chunk.page_end is not None else None,
        "unit_kind": str(chunk.unit_kind or "").strip() or None,
        "quality_status": str(chunk.quality_status or document.quality_status or "").strip() or None,
        "run_id": linkage.run_id,
        "target_id": linkage.target_id,
        "accession_number": linkage.accession_number,
        "content_units_ref": linkage.content_units_ref,
        "normalized_text_ref": linkage.normalized_text_ref,
        "diagnostics_ref": str(linkage.diagnostics_ref or "").strip() or None,
        "blob_ref": linkage.blob_ref,
        "download_exchange_ref": linkage.download_exchange_ref,
        "discovery_ref": linkage.discovery_ref,
        "selection_ref": linkage.selection_ref,
        "normalized_text_sha256": linkage.normalized_text_sha256 or document.normalized_text_sha256,
        "blob_sha256": linkage.blob_sha256,
        "effective_content_type": str(document.media_type or "").strip() or None,
        "document_class": str(document.document_class or "").strip() or None,
        "page_count": int(document.page_count or 0),
    }


def list_content_units_for_run(
    db: Session,
    *,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    query = (
        db.query(ApsContentLinkage, ApsContentDocument, ApsContentChunk)
        .join(
            ApsContentDocument,
            and_(
                ApsContentDocument.content_id == ApsContentLinkage.content_id,
                ApsContentDocument.content_contract_id == ApsContentLinkage.content_contract_id,
                ApsContentDocument.chunking_contract_id == ApsContentLinkage.chunking_contract_id,
            ),
        )
        .join(
            ApsContentChunk,
            and_(
                ApsContentChunk.content_id == ApsContentLinkage.content_id,
                ApsContentChunk.content_contract_id == ApsContentLinkage.content_contract_id,
                ApsContentChunk.chunking_contract_id == ApsContentLinkage.chunking_contract_id,
            ),
        )
        .filter(ApsContentLinkage.run_id == str(run_id or ""))
    )
    total = query.count()
    rows = (
        query.order_by(
            ApsContentLinkage.content_id.asc(),
            ApsContentChunk.chunk_ordinal.asc(),
            ApsContentLinkage.target_id.asc(),
        )
        .offset(int(offset))
        .limit(int(limit))
        .all()
    )
    items = [_serialize_index_row(linkage=row[0], document=row[1], chunk=row[2]) for row in rows]
    return {
        "connector_run_id": str(run_id or ""),
        "total": int(total),
        "limit": int(limit),
        "offset": int(offset),
        "items": items,
    }


def search_content_units(
    db: Session,
    *,
    query_text: str,
    run_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    query_tokens = normalize_query_tokens(query_text)
    if not query_tokens:
        raise ValueError("empty_query")
    unique_tokens = sorted(list(dict.fromkeys(query_tokens)))

    base_query = (
        db.query(ApsContentLinkage, ApsContentDocument, ApsContentChunk)
        .join(
            ApsContentDocument,
            and_(
                ApsContentDocument.content_id == ApsContentLinkage.content_id,
                ApsContentDocument.content_contract_id == ApsContentLinkage.content_contract_id,
                ApsContentDocument.chunking_contract_id == ApsContentLinkage.chunking_contract_id,
            ),
        )
        .join(
            ApsContentChunk,
            and_(
                ApsContentChunk.content_id == ApsContentLinkage.content_id,
                ApsContentChunk.content_contract_id == ApsContentLinkage.content_contract_id,
                ApsContentChunk.chunking_contract_id == ApsContentLinkage.chunking_contract_id,
            ),
        )
    )
    if str(run_id or "").strip():
        base_query = base_query.filter(ApsContentLinkage.run_id == str(run_id).strip())

    ranked_rows: list[dict[str, Any]] = []
    for linkage, document, chunk in base_query.all():
        chunk_text = str(chunk.chunk_text or "")
        frequencies = _token_frequencies(chunk_text)
        if any(int(frequencies.get(token, 0)) <= 0 for token in unique_tokens):
            continue
        matched_unique_count = len(unique_tokens)
        summed_term_frequency = sum(int(frequencies.get(token, 0)) for token in unique_tokens)
        serialized = _serialize_index_row(linkage=linkage, document=document, chunk=chunk)
        serialized["matched_unique_query_terms"] = matched_unique_count
        serialized["summed_term_frequency"] = summed_term_frequency
        serialized["chunk_length"] = len(chunk_text)
        ranked_rows.append(serialized)

    ranked_rows.sort(
        key=lambda row: (
            -int(row.get("matched_unique_query_terms") or 0),
            -int(row.get("summed_term_frequency") or 0),
            int(row.get("chunk_length") or 0),
            str(row.get("content_id") or ""),
            int(row.get("chunk_ordinal") or 0),
            str(row.get("run_id") or ""),
            str(row.get("target_id") or ""),
        )
    )
    total = len(ranked_rows)
    paged = ranked_rows[int(offset) : int(offset) + int(limit)]
    for row in paged:
        row.pop("chunk_length", None)

    return {
        "query": str(query_text or ""),
        "query_tokens": unique_tokens,
        "total": int(total),
        "limit": int(limit),
        "offset": int(offset),
        "items": paged,
    }


def validate_content_index_artifact_presence(
    *,
    run_rows: list[dict[str, Any]],
    reports_dir: str | Path,
    db: Session,
) -> dict[str, Any]:
    base = Path(reports_dir)
    checks: list[dict[str, Any]] = []
    for row in run_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        run_path = run_artifact_path(run_id=run_id, reports_dir=base)
        failure_path = failure_artifact_path(run_id=run_id, reports_dir=base)
        reasons: list[str] = []
        run_payload: dict[str, Any] | None = None

        if not run_path.exists() and not failure_path.exists():
            reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_MISSING_REF)

        if run_path.exists():
            try:
                parsed = json.loads(run_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                parsed = None
            if not isinstance(parsed, dict):
                reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)
            else:
                run_payload = parsed
                if str(parsed.get("schema_id") or "") != APS_CONTENT_INDEX_RUN_SCHEMA_ID:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)
                if int(parsed.get("schema_version") or 0) != APS_CONTENT_INDEX_SCHEMA_VERSION:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)

        if failure_path.exists():
            failure_payload = _read_json_object(failure_path)
            if not failure_payload:
                reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)
            else:
                if str(failure_payload.get("schema_id") or "") != APS_CONTENT_INDEX_FAILURE_SCHEMA_ID:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)
                if int(failure_payload.get("schema_version") or 0) != APS_CONTENT_INDEX_SCHEMA_VERSION:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)

        if run_payload:
            artifact_rows = [
                dict(item or {})
                for item in (run_payload.get("content_units_artifacts") or [])
                if isinstance(item, dict)
            ]
            for artifact_row in artifact_rows:
                ref = str(artifact_row.get("ref") or "").strip()
                if not ref:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_MISSING_REF)
                    continue
                path = Path(ref)
                if not path.exists():
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_UNRESOLVABLE_REF)
                    continue
                declared_sha = str(artifact_row.get("sha256") or "").strip()
                if declared_sha and declared_sha != _file_sha256(path):
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_CHECKSUM_MISMATCH)
                payload = _read_json_object(path)
                if not payload:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)
                    continue
                if str(payload.get("schema_id") or "") != APS_CONTENT_UNITS_SCHEMA_ID:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)
                if int(payload.get("schema_version") or 0) != APS_CONTENT_INDEX_SCHEMA_VERSION:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_SCHEMA_MISMATCH)
                if str(payload.get("content_contract_id") or "") != APS_CONTENT_CONTRACT_ID:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_UNKNOWN_CONTRACT_ID)
                if str(payload.get("chunking_contract_id") or "") != APS_CHUNKING_CONTRACT_ID:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_UNKNOWN_CONTRACT_ID)

                content_id = str(payload.get("content_id") or "")
                content_contract_id = str(payload.get("content_contract_id") or "")
                chunking_contract_id = str(payload.get("chunking_contract_id") or "")
                document = (
                    db.query(ApsContentDocument)
                    .filter(
                        and_(
                            ApsContentDocument.content_id == content_id,
                            ApsContentDocument.content_contract_id == content_contract_id,
                            ApsContentDocument.chunking_contract_id == chunking_contract_id,
                        )
                    )
                    .first()
                )
                if not document:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_DB_DOCUMENT_MISSING)
                    continue
                if str(payload.get("normalized_text_sha256") or "") and str(document.normalized_text_sha256 or "") != str(
                    payload.get("normalized_text_sha256") or ""
                ):
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_CHECKSUM_MISMATCH)
                if (
                    str(document.content_status or "") != str(payload.get("content_status") or "")
                    or str(document.media_type or "") != str(payload.get("effective_content_type") or "")
                    or str(document.document_class or "") != str(payload.get("document_class") or "")
                    or str(document.quality_status or "") != str(payload.get("quality_status") or "")
                    or int(document.page_count or 0) != int(payload.get("page_count") or 0)
                ):
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_FIELD_MISMATCH)

                chunk_rows = (
                    db.query(ApsContentChunk)
                    .filter(
                        and_(
                            ApsContentChunk.content_id == content_id,
                            ApsContentChunk.content_contract_id == content_contract_id,
                            ApsContentChunk.chunking_contract_id == chunking_contract_id,
                        )
                    )
                    .all()
                )
                chunk_by_id = {str(item.chunk_id): item for item in chunk_rows}
                artifact_chunks = [dict(item or {}) for item in (payload.get("chunks") or []) if isinstance(item, dict)]
                if len(chunk_rows) != int(payload.get("chunk_count") or 0):
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_COUNT_MISMATCH)
                for artifact_chunk in artifact_chunks:
                    chunk_id = str(artifact_chunk.get("chunk_id") or "").strip()
                    chunk_row = chunk_by_id.get(chunk_id)
                    if not chunk_row:
                        reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_MISSING)
                        continue
                    if (
                        int(chunk_row.chunk_ordinal or 0) != int(artifact_chunk.get("chunk_ordinal") or 0)
                        or int(chunk_row.start_char or 0) != int(artifact_chunk.get("start_char") or 0)
                        or int(chunk_row.end_char or 0) != int(artifact_chunk.get("end_char") or 0)
                        or str(chunk_row.chunk_text_sha256 or "") != str(artifact_chunk.get("chunk_text_sha256") or "")
                        or (int(chunk_row.page_start or 0) if chunk_row.page_start is not None else None)
                        != (int(artifact_chunk.get("page_start") or 0) if artifact_chunk.get("page_start") is not None else None)
                        or (int(chunk_row.page_end or 0) if chunk_row.page_end is not None else None)
                        != (int(artifact_chunk.get("page_end") or 0) if artifact_chunk.get("page_end") is not None else None)
                        or str(chunk_row.unit_kind or "") != str(artifact_chunk.get("unit_kind") or "")
                        or str(chunk_row.quality_status or "") != str(payload.get("quality_status") or "")
                    ):
                        reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_FIELD_MISMATCH)

                linkage = (
                    db.query(ApsContentLinkage)
                    .filter(
                        and_(
                            ApsContentLinkage.content_id == content_id,
                            ApsContentLinkage.run_id == str(payload.get("run_id") or ""),
                            ApsContentLinkage.target_id == str(payload.get("target_id") or ""),
                            ApsContentLinkage.content_contract_id == content_contract_id,
                            ApsContentLinkage.chunking_contract_id == chunking_contract_id,
                        )
                    )
                    .first()
                )
                if not linkage:
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_DB_LINKAGE_MISSING)
                elif (
                    str(linkage.content_units_ref or "") != str(path)
                    or str(linkage.normalized_text_ref or "") != str(payload.get("normalized_text_ref") or "")
                    or str(linkage.normalized_text_sha256 or "") != str(payload.get("normalized_text_sha256") or "")
                    or str(linkage.blob_ref or "") != str(payload.get("blob_ref") or "")
                    or str(linkage.blob_sha256 or "") != str(payload.get("blob_sha256") or "")
                    or str(linkage.download_exchange_ref or "") != str(payload.get("download_exchange_ref") or "")
                    or str(linkage.discovery_ref or "") != str(payload.get("discovery_ref") or "")
                    or str(linkage.selection_ref or "") != str(payload.get("selection_ref") or "")
                    or str(linkage.diagnostics_ref or "") != str(payload.get("diagnostics_ref") or "")
                ):
                    reasons.append(APS_CONTENT_INDEX_GATE_FAILURE_DB_CHUNK_FIELD_MISMATCH)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "run_artifact_ref": str(run_path),
                "run_artifact_exists": run_path.exists(),
                "failure_artifact_ref": str(failure_path),
                "failure_artifact_exists": failure_path.exists(),
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    return {
        "schema_id": APS_CONTENT_INDEX_GATE_SCHEMA_ID,
        "schema_version": APS_CONTENT_INDEX_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "passed": passed,
        "checked_runs": len(checks),
        "failed_runs": len([item for item in checks if not bool(item.get("passed"))]),
        "checks": checks,
    }
