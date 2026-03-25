from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import nrc_aps_document_processing
from app.services import nrc_aps_media_detection
from app.services import nrc_aps_safeguards


APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID = "aps.artifact_ingestion_target.v1"
APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID = "aps.artifact_ingestion_run.v1"
APS_ARTIFACT_INGESTION_FAILURE_SCHEMA_ID = "aps.artifact_ingestion_failure.v1"
APS_ARTIFACT_INGESTION_SCHEMA_VERSION = 1

APS_ARTIFACT_INGESTION_GATE_SCHEMA_ID = "aps.artifact_ingestion_gate.v1"
APS_ARTIFACT_INGESTION_GATE_SCHEMA_VERSION = 1

APS_PIPELINE_MODE_OFF = "off"
APS_PIPELINE_MODE_DOWNLOAD_ONLY = "download_only"
APS_PIPELINE_MODE_HYDRATE_PROCESS = "hydrate_process"
APS_PIPELINE_MODES = {
    APS_PIPELINE_MODE_OFF,
    APS_PIPELINE_MODE_DOWNLOAD_ONLY,
    APS_PIPELINE_MODE_HYDRATE_PROCESS,
}

APS_ARTIFACT_OUTCOME_NOT_AVAILABLE = "artifact_not_available"

APS_FAILURE_ARTIFACT_URL_MISSING = "artifact_url_missing"
APS_FAILURE_ARTIFACT_DOWNLOAD_FAILED = "artifact_download_failed"
APS_FAILURE_ARTIFACT_SIZE_LIMIT_EXCEEDED = "artifact_size_limit_exceeded"
APS_FAILURE_ARTIFACT_HYDRATION_FAILED = "artifact_hydration_failed"
APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE = "artifact_unsupported_media_type"
APS_FAILURE_ARTIFACT_EXTRACTION_FAILED = "artifact_extraction_failed"
APS_FAILURE_ARTIFACT_NORMALIZATION_FAILED = "artifact_normalization_failed"
APS_FAILURE_ARTIFACT_WRITE_FAILED = "artifact_write_failed"
APS_FAILURE_ARTIFACT_PARTIAL_CORRUPTION = "artifact_ingestion_partial_corruption"

APS_FAILURE_CODES = {
    APS_FAILURE_ARTIFACT_URL_MISSING,
    APS_FAILURE_ARTIFACT_DOWNLOAD_FAILED,
    APS_FAILURE_ARTIFACT_SIZE_LIMIT_EXCEEDED,
    APS_FAILURE_ARTIFACT_HYDRATION_FAILED,
    APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE,
    APS_FAILURE_ARTIFACT_EXTRACTION_FAILED,
    APS_FAILURE_ARTIFACT_NORMALIZATION_FAILED,
    APS_FAILURE_ARTIFACT_WRITE_FAILED,
    APS_FAILURE_ARTIFACT_PARTIAL_CORRUPTION,
}

APS_TEXT_NORMALIZATION_CONTRACT_ID = nrc_aps_document_processing.APS_TEXT_NORMALIZATION_CONTRACT_ID

APS_PDF_EXTRACTOR_ID = nrc_aps_document_processing.APS_PDF_EXTRACTOR_ID
APS_PDF_EXTRACTOR_VERSION = nrc_aps_document_processing.APS_PDF_EXTRACTOR_VERSION
APS_TEXT_EXTRACTOR_ID = nrc_aps_document_processing.APS_TEXT_EXTRACTOR_ID
APS_TEXT_EXTRACTOR_VERSION = nrc_aps_document_processing.APS_TEXT_EXTRACTOR_VERSION

APS_SUPPORTED_CONTENT_TYPES = nrc_aps_media_detection.APS_SUPPORTED_CONTENT_TYPES

APS_GATE_FAILURE_MISSING_REF = "missing_required_artifact_ref"
APS_GATE_FAILURE_SCHEMA_ID = "schema_id_mismatch"
APS_GATE_FAILURE_SCHEMA_VERSION = "schema_version_mismatch"
APS_GATE_FAILURE_INVALID_FAILURE_CODE = "invalid_failure_code"
APS_GATE_FAILURE_MISSING_EVIDENCE = "missing_required_evidence"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_ref"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_STATUS = "status_semantics_mismatch"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


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


def _path_get(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for piece in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(piece)
    return current


def normalize_pipeline_mode(value: Any, *, default: str = APS_PIPELINE_MODE_DOWNLOAD_ONLY) -> str:
    mode = str(value or "").strip().lower()
    if mode in APS_PIPELINE_MODES:
        return mode
    return default


def resolve_artifact_required_for_target_success(mode: str, configured_value: Any) -> bool:
    if str(mode or "").strip().lower() == APS_PIPELINE_MODE_OFF:
        return False
    if configured_value is None:
        return str(mode or "").strip().lower() == APS_PIPELINE_MODE_HYDRATE_PROCESS
    return bool(configured_value)


def is_failure_code(value: Any) -> bool:
    return str(value or "").strip() in APS_FAILURE_CODES


def is_artifact_not_available(value: Any) -> bool:
    return str(value or "").strip() == APS_ARTIFACT_OUTCOME_NOT_AVAILABLE


def normalize_content_type(value: Any) -> str:
    return nrc_aps_media_detection.normalize_content_type(value)


def normalization_contract_id() -> str:
    return APS_TEXT_NORMALIZATION_CONTRACT_ID


def processing_config_from_run_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    incoming = dict(config or {})
    return nrc_aps_document_processing.default_processing_config(
        {
            "content_sniff_bytes": incoming.get("content_sniff_bytes", 4096),
            "content_parse_max_pages": incoming.get("content_parse_max_pages", 500),
            "content_parse_timeout_seconds": incoming.get("content_parse_timeout_seconds", 30),
            "ocr_enabled": incoming.get("ocr_enabled", True),
            "ocr_max_pages": incoming.get("ocr_max_pages", 50),
            "ocr_render_dpi": incoming.get("ocr_render_dpi", 300),
            "ocr_language": incoming.get("ocr_language", "eng"),
            "ocr_timeout_seconds": incoming.get("ocr_timeout_seconds", 120),
            "content_min_searchable_chars": incoming.get("content_min_searchable_chars", 200),
            "content_min_searchable_tokens": incoming.get("content_min_searchable_tokens", 30),
            "document_type": incoming.get("document_type"),
            "file_path": incoming.get("file_path") or incoming.get("source_file_path"),
            "pdf_path": incoming.get("pdf_path") or incoming.get("source_file_path"),
        }
    )


def detect_media_type(*, content: bytes, content_type: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
    processing_config = processing_config_from_run_config(config)
    return nrc_aps_media_detection.detect_media_type(
        content,
        declared_content_type=content_type,
        sniff_bytes=int(processing_config["content_sniff_bytes"]),
    )


def extract_and_normalize(*, content: bytes, content_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    processed = nrc_aps_document_processing.process_document(
        content=content,
        declared_content_type=content_type,
        config=processing_config_from_run_config(config),
    )
    return {
        "content_type": str(processed.get("effective_content_type") or normalize_content_type(content_type)),
        **processed,
    }


def blob_relative_path(*, sha256: str) -> str:
    digest = str(sha256 or "").strip().lower()
    if len(digest) < 4:
        raise ValueError("sha256 required for blob path")
    return str(Path("nrc_adams_aps") / "blobs" / "sha256" / digest[0:2] / digest[2:4] / f"{digest}.bin")


def write_blob_content_addressed(*, raw_root: str | Path, content: bytes) -> dict[str, Any]:
    digest = hashlib.sha256(content).hexdigest()
    rel = blob_relative_path(sha256=digest)
    absolute = Path(raw_root) / rel
    absolute.parent.mkdir(parents=True, exist_ok=True)
    if not absolute.exists():
        temp = absolute.with_name(f".{absolute.name}.{uuid.uuid4().hex}.tmp")
        temp.write_bytes(content)
        os.replace(temp, absolute)
    return {
        "blob_ref": str(absolute),
        "blob_rel_ref": rel.replace("\\", "/"),
        "blob_sha256": digest,
        "blob_bytes": len(content),
        "blob_storage_layout": "nrc_aps_blob_sha256_v1",
    }


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> str:
    return nrc_aps_safeguards.write_json_atomic(path, payload)


def diagnostics_relative_path(*, run_id: str, target_id: str) -> str:
    safe_run = _safe_path_token(run_id)
    safe_target = _safe_path_token(target_id)
    return str(Path("nrc_adams_aps") / "diagnostics" / f"{safe_run}_{safe_target}_document_processing_v1.json")


def write_processing_diagnostics(
    *,
    artifact_storage_dir: str | Path,
    run_id: str,
    target_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    rel = diagnostics_relative_path(run_id=run_id, target_id=target_id)
    absolute = Path(artifact_storage_dir) / rel
    absolute.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(absolute, payload)
    return {
        "diagnostics_ref": str(absolute),
        "diagnostics_rel_ref": rel.replace("\\", "/"),
        "diagnostics_sha256": _file_sha256(absolute),
    }


def target_artifact_path(*, run_id: str, target_id: str, reports_dir: str | Path) -> Path:
    safe_run = _safe_path_token(run_id)
    safe_target = _safe_path_token(target_id)
    return Path(reports_dir) / f"{safe_run}_{safe_target}_aps_artifact_ingestion_target_v1.json"


def run_artifact_path(*, run_id: str, reports_dir: str | Path) -> Path:
    safe_run = _safe_path_token(run_id)
    return Path(reports_dir) / f"{safe_run}_aps_artifact_ingestion_run_v1.json"


def failure_artifact_path(*, run_id: str, reports_dir: str | Path) -> Path:
    safe_run = _safe_path_token(run_id)
    return Path(reports_dir) / f"{safe_run}_aps_artifact_ingestion_failure_v1.json"


def artifact_paths(*, run_id: str, reports_dir: str | Path) -> dict[str, str]:
    return {
        "aps_artifact_ingestion": str(run_artifact_path(run_id=run_id, reports_dir=reports_dir)),
        "aps_artifact_ingestion_failure": str(failure_artifact_path(run_id=run_id, reports_dir=reports_dir)),
    }


def build_target_artifact_payload(
    *,
    run_id: str,
    target_id: str,
    accession_number: str | None,
    pipeline_mode: str,
    artifact_required_for_target_success: bool,
    outcome_status: str,
    target_success: bool,
    evidence: dict[str, Any],
    source_metadata_ref: str | None,
    failure: dict[str, Any] | None = None,
    download: dict[str, Any] | None = None,
    extraction: dict[str, Any] | None = None,
    availability_reason: str | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_id": APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID,
        "schema_version": APS_ARTIFACT_INGESTION_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": str(run_id or ""),
        "target_id": str(target_id or ""),
        "accession_number": str(accession_number or "").strip() or None,
        "pipeline_mode": normalize_pipeline_mode(pipeline_mode),
        "artifact_required_for_target_success": bool(artifact_required_for_target_success),
        "outcome_status": str(outcome_status or "").strip(),
        "target_success": bool(target_success),
        "source_metadata_ref": str(source_metadata_ref or "") or None,
        "evidence": dict(evidence or {}),
    }
    if availability_reason:
        payload["availability_reason"] = str(availability_reason).strip()
    if download:
        payload["download"] = dict(download)
    if extraction:
        payload["extraction"] = dict(extraction)
        payload["normalization_contract_id"] = str(extraction.get("normalization_contract_id") or "")
    if failure:
        payload["failure"] = dict(failure)
    payload["payload_sha256"] = _stable_hash(payload)
    return payload


def build_run_artifact_payload(
    *,
    run_id: str,
    run_status: str,
    pipeline_mode: str,
    artifact_required_for_target_success: bool,
    selected_targets: int,
    target_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    target_rows = [dict(item or {}) for item in target_artifacts if isinstance(item, dict)]
    outcome_counts: dict[str, int] = {}
    failure_code_counts: dict[str, int] = {}
    for row in target_rows:
        status = str(row.get("outcome_status") or "").strip() or "unknown"
        outcome_counts[status] = int(outcome_counts.get(status, 0)) + 1
        failure = dict(row.get("failure") or {})
        code = str(failure.get("code") or "").strip()
        if code:
            failure_code_counts[code] = int(failure_code_counts.get(code, 0)) + 1
    if int(selected_targets) == 0:
        run_outcome = "no_targets_selected"
    else:
        run_outcome = "targets_processed"
    payload = {
        "schema_id": APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID,
        "schema_version": APS_ARTIFACT_INGESTION_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": str(run_id or ""),
        "run_status": str(run_status or ""),
        "pipeline_mode": normalize_pipeline_mode(pipeline_mode),
        "artifact_required_for_target_success": bool(artifact_required_for_target_success),
        "run_outcome": run_outcome,
        "selected_targets": int(selected_targets),
        "processed_targets": len(target_rows),
        "outcome_counts": outcome_counts,
        "failure_code_counts": failure_code_counts,
        "target_artifacts": target_rows,
    }
    payload["payload_sha256"] = _stable_hash(payload)
    return payload


def build_failure_artifact_payload(
    *,
    run_id: str,
    run_status: str,
    error_class: str,
    error_message: str,
) -> dict[str, Any]:
    payload = {
        "schema_id": APS_ARTIFACT_INGESTION_FAILURE_SCHEMA_ID,
        "schema_version": APS_ARTIFACT_INGESTION_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": str(run_id or ""),
        "run_status": str(run_status or ""),
        "error_class": str(error_class or "runtime_error"),
        "error_message": str(error_message or ""),
    }
    payload["payload_sha256"] = _stable_hash(payload)
    return payload


def _required_failure_evidence_paths(code: str) -> list[str]:
    common = [
        "run_id",
        "target_id",
        "pipeline_mode",
        "source_metadata_ref",
        "evidence.discovery_ref",
        "evidence.selection_ref",
    ]
    by_code = {
        APS_FAILURE_ARTIFACT_URL_MISSING: [
            "failure.evidence.url_fields_checked",
            "failure.evidence.availability_reason",
        ],
        APS_FAILURE_ARTIFACT_DOWNLOAD_FAILED: [
            "failure.evidence.download_exchange_ref",
            "failure.evidence.attempt_count",
            "failure.evidence.error_class",
        ],
        APS_FAILURE_ARTIFACT_SIZE_LIMIT_EXCEEDED: [
            "failure.evidence.max_file_bytes",
            "failure.evidence.bytes_received_before_abort",
            "failure.evidence.overrun_phase",
            "failure.evidence.download_exchange_ref",
        ],
        APS_FAILURE_ARTIFACT_HYDRATION_FAILED: [
            "failure.evidence.download_exchange_ref",
            "failure.evidence.error_class",
        ],
        APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE: [
            "failure.evidence.declared_content_type",
            "failure.evidence.sniffed_content_type",
            "failure.evidence.detected_content_type",
            "failure.evidence.media_detection_status",
            "failure.evidence.allowed_content_types",
            "failure.evidence.blob_ref",
        ],
        APS_FAILURE_ARTIFACT_EXTRACTION_FAILED: [
            "failure.evidence.blob_ref",
            "failure.evidence.declared_content_type",
            "failure.evidence.sniffed_content_type",
            "failure.evidence.detected_content_type",
            "failure.evidence.media_detection_status",
            "failure.evidence.extractor_id",
            "failure.evidence.extractor_version",
            "failure.evidence.error_class",
        ],
        APS_FAILURE_ARTIFACT_NORMALIZATION_FAILED: [
            "failure.evidence.extractor_id",
            "failure.evidence.extractor_version",
            "failure.evidence.normalization_contract_id",
            "failure.evidence.error_class",
        ],
        APS_FAILURE_ARTIFACT_WRITE_FAILED: [
            "failure.evidence.artifact_kind",
            "failure.evidence.intended_output_path",
            "failure.evidence.error_class",
        ],
        APS_FAILURE_ARTIFACT_PARTIAL_CORRUPTION: [
            "failure.evidence.corrupted_ref",
            "failure.evidence.validation_failures",
        ],
    }
    return common + by_code.get(code, [])


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def validate_target_artifact_payload(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if str(payload.get("schema_id") or "") != APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID:
        reasons.append(APS_GATE_FAILURE_SCHEMA_ID)
    if int(payload.get("schema_version") or 0) != APS_ARTIFACT_INGESTION_SCHEMA_VERSION:
        reasons.append(APS_GATE_FAILURE_SCHEMA_VERSION)

    outcome = str(payload.get("outcome_status") or "").strip()
    if outcome == APS_ARTIFACT_OUTCOME_NOT_AVAILABLE:
        for required in (
            "run_id",
            "target_id",
            "pipeline_mode",
            "source_metadata_ref",
            "evidence.discovery_ref",
            "evidence.selection_ref",
            "evidence.url_fields_checked",
            "availability_reason",
        ):
            if _is_missing(_path_get(payload, required)):
                reasons.append(APS_GATE_FAILURE_MISSING_EVIDENCE)
                break

    failure = dict(payload.get("failure") or {})
    if failure:
        code = str(failure.get("code") or "").strip()
        if code not in APS_FAILURE_CODES:
            reasons.append(APS_GATE_FAILURE_INVALID_FAILURE_CODE)
        else:
            for path in _required_failure_evidence_paths(code):
                if _is_missing(_path_get(payload, path)):
                    reasons.append(APS_GATE_FAILURE_MISSING_EVIDENCE)
                    break
            if code == APS_FAILURE_ARTIFACT_NORMALIZATION_FAILED:
                contract = str(_path_get(payload, "failure.evidence.normalization_contract_id") or "")
                if contract != APS_TEXT_NORMALIZATION_CONTRACT_ID:
                    reasons.append(APS_GATE_FAILURE_MISSING_EVIDENCE)

    if str(payload.get("pipeline_mode") or "") == APS_PIPELINE_MODE_HYDRATE_PROCESS and not failure:
        if outcome not in {APS_ARTIFACT_OUTCOME_NOT_AVAILABLE, "processed"}:
            reasons.append(APS_GATE_FAILURE_STATUS)
        if outcome == "processed":
            contract = str(payload.get("normalization_contract_id") or "")
            if contract != APS_TEXT_NORMALIZATION_CONTRACT_ID:
                reasons.append(APS_GATE_FAILURE_MISSING_EVIDENCE)
            for required in (
                "extraction.declared_content_type",
                "extraction.sniffed_content_type",
                "extraction.effective_content_type",
                "extraction.media_detection_contract_id",
                "extraction.media_detection_status",
                "extraction.document_processing_contract_id",
                "extraction.document_class",
                "extraction.extractor_id",
                "extraction.extractor_version",
                "extraction.normalized_text_ref",
                "extraction.normalized_text_sha256",
                "extraction.quality_status",
                "extraction.page_count",
                "extraction.diagnostics_ref",
            ):
                if _is_missing(_path_get(payload, required)):
                    reasons.append(APS_GATE_FAILURE_MISSING_EVIDENCE)
                    break
    return sorted(list(dict.fromkeys(reasons)))


def validate_artifact_ingestion_artifact_presence(*, run_rows: list[dict[str, Any]], reports_dir: str | Path) -> dict[str, Any]:
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
            reasons.append(APS_GATE_FAILURE_MISSING_REF)

        if run_path.exists():
            try:
                parsed = json.loads(run_path.read_text(encoding="utf-8"))
                if not isinstance(parsed, dict):
                    reasons.append(APS_GATE_FAILURE_SCHEMA_ID)
                else:
                    run_payload = parsed
                    if str(parsed.get("schema_id") or "") != APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID:
                        reasons.append(APS_GATE_FAILURE_SCHEMA_ID)
                    if int(parsed.get("schema_version") or 0) != APS_ARTIFACT_INGESTION_SCHEMA_VERSION:
                        reasons.append(APS_GATE_FAILURE_SCHEMA_VERSION)
                    selected_targets = int(parsed.get("selected_targets") or 0)
                    run_outcome = str(parsed.get("run_outcome") or "").strip()
                    if selected_targets == 0 and run_outcome != "no_targets_selected":
                        reasons.append(APS_GATE_FAILURE_STATUS)
            except (OSError, ValueError):
                reasons.append(APS_GATE_FAILURE_SCHEMA_ID)

        if failure_path.exists():
            try:
                parsed_failure = json.loads(failure_path.read_text(encoding="utf-8"))
                if not isinstance(parsed_failure, dict):
                    reasons.append(APS_GATE_FAILURE_SCHEMA_ID)
                else:
                    if str(parsed_failure.get("schema_id") or "") != APS_ARTIFACT_INGESTION_FAILURE_SCHEMA_ID:
                        reasons.append(APS_GATE_FAILURE_SCHEMA_ID)
                    if int(parsed_failure.get("schema_version") or 0) != APS_ARTIFACT_INGESTION_SCHEMA_VERSION:
                        reasons.append(APS_GATE_FAILURE_SCHEMA_VERSION)
            except (OSError, ValueError):
                reasons.append(APS_GATE_FAILURE_SCHEMA_ID)

        if run_payload:
            for target_row in [dict(item or {}) for item in (run_payload.get("target_artifacts") or []) if isinstance(item, dict)]:
                target_ref = str(target_row.get("ref") or "").strip()
                if not target_ref:
                    reasons.append(APS_GATE_FAILURE_MISSING_REF)
                    continue
                target_path = Path(target_ref)
                if not target_path.exists():
                    reasons.append(APS_GATE_FAILURE_UNRESOLVABLE_REF)
                    continue
                declared_sha = str(target_row.get("sha256") or "").strip()
                if declared_sha and declared_sha != _file_sha256(target_path):
                    reasons.append(APS_GATE_FAILURE_CHECKSUM)
                try:
                    target_payload = json.loads(target_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    reasons.append(APS_GATE_FAILURE_SCHEMA_ID)
                    continue
                if not isinstance(target_payload, dict):
                    reasons.append(APS_GATE_FAILURE_SCHEMA_ID)
                    continue
                reasons.extend(validate_target_artifact_payload(target_payload))

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
        "schema_id": APS_ARTIFACT_INGESTION_GATE_SCHEMA_ID,
        "schema_version": APS_ARTIFACT_INGESTION_GATE_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "passed": passed,
        "checked_runs": len(checks),
        "failed_runs": len([item for item in checks if not bool(item.get("passed"))]),
        "checks": checks,
    }

