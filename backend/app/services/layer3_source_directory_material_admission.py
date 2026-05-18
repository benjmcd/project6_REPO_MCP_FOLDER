from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import PurePosixPath
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models import L3SourceDirectoryIngestionBatch, L3SourceDirectoryIngestionFile
from app.services.layer3_gate_b_state import material_candidate_basis_from_preview, material_preview_hash
from app.services.layer3_source_directory_ingestion import (
    ALLOWED_EXTENSIONS,
    CONFIG_AUTHORITY,
    MODE as INGESTION_MODE,
    SCHEMA_ID as INGESTION_SCHEMA_ID,
    SOURCE_FAMILY,
    STATUS_RECORDED,
    SourceDirectoryIngestionError,
    _configured_root,
    _negative_invariants as _ingestion_negative_invariants,
    _source_root_ref,
    _stable_hash,
)

SCHEMA_ID = "layer3.source_directory_material_preview.v1"
MODE = "source_directory_ingestion_gate_b_material_admission"
SOURCE_CLASS = "server_configured_directory_file"
GATE_B_CANDIDATE_PREFIX = "mat-server_configured_directory_file-"
PREVIEW_MAX_CHARS = 4000
_FORBIDDEN_DECISION_BASIS_FIELDS = {
    "absolute_path",
    "auth_policy",
    "connector_target",
    "destination",
    "directory",
    "directory_path",
    "execution_mode",
    "file",
    "file_bytes",
    "frontend_state",
    "glob",
    "local_path",
    "package_payload",
    "path",
    "provider_url",
    "public_url",
    "rag_index",
    "recursive",
    "url",
    "vector_index",
    "web_connector",
}


class SourceDirectoryMaterialAdmissionError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-material-admission-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_preview(db: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_preview_payload(payload)
    request_id = _required(fields, "client_request_id")
    batch_id = _required(fields, "source_ingestion_batch_id")
    file_id = _required(fields, "source_ingestion_file_id")
    expected_file_identity_hash = _required(fields, "file_identity_hash")
    expected_authority_basis_hash = _required(fields, "authority_basis_hash")
    max_chars = _normalise_max_chars(fields.get("max_chars"))

    batch, file_record = _load_authority(db, batch_id=batch_id, file_id=file_id)
    _assert_expected_hashes(
        file_record,
        expected_file_identity_hash=expected_file_identity_hash,
        expected_authority_basis_hash=expected_authority_basis_hash,
    )
    live_file = _read_live_file(file_record, max_chars=max_chars)
    _assert_live_file_matches_authority(file_record, live_file)

    source_ref = f"source_directory_ingestion_file:{file_record.source_ingestion_file_id}"
    provenance_ref = _provenance_ref(batch, file_record)
    source_identity = _source_identity(batch, file_record)
    source_provenance = _source_provenance(batch, file_record, source_ref=source_ref)
    truncated = live_file["decoded_char_count"] > max_chars
    material_candidate = {
        "candidate_id": f"{GATE_B_CANDIDATE_PREFIX}{file_record.source_ingestion_file_id}",
        "source_class": SOURCE_CLASS,
        "source_ref": source_ref,
        "query_basis": MODE,
        "provenance_ref": provenance_ref,
        "source_label": file_record.relative_name,
        "media_type": file_record.media_type,
        "content_size_bytes": file_record.content_size_bytes,
        "content_sha256": file_record.content_sha256,
        "file_identity_hash": file_record.file_identity_hash,
        "authority_basis_hash": file_record.authority_basis_hash,
        "preview_text": live_file["preview_text"],
        "preview_char_count": len(live_file["preview_text"]),
        "preview_truncated": truncated,
        "preview_encoding": "utf-8",
        "source_identity": source_identity,
        "source_provenance": source_provenance,
        "payload": {
            "source_ingestion_batch_id": batch.source_ingestion_batch_id,
            "source_ingestion_file_id": file_record.source_ingestion_file_id,
            "source_class": SOURCE_CLASS,
            "content_sha256": file_record.content_sha256,
            "file_identity_hash": file_record.file_identity_hash,
            "authority_basis_hash": file_record.authority_basis_hash,
            "bounded_preview_char_count": len(live_file["preview_text"]),
            "preview_truncated": truncated,
        },
        "load_summary": {
            "loaded_records": 1,
            "failed_records": 0,
            "preview_material": True,
            "bounded_text_preview": True,
            "source_directory_gate_b_material_admission": True,
        },
        "current_decision_state": "candidate",
    }
    preview_hash = material_preview_hash([material_candidate_basis_from_preview(material_candidate)])
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": "available",
        "message": "Layer 3 source-directory material preview returned bounded text from one persisted file authority.",
        "source_gate": {
            "canonical_source_of_truth": "L3SourceDirectoryIngestionFile",
            "batch_authority": "L3SourceDirectoryIngestionBatch",
            "source_gate": "746_SOURCE_DIRECTORY_INGESTION_DOWNSTREAM_MATERIAL_AUTHORITY_FREEZE",
            "writer_route": "POST /api/v1/layer3/source/ingestion/server-configured-directory/scan",
            "status_route": (
                "GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}"
            ),
            "preview_route": "POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
            "gate_b_material_admission_route": "POST /api/v1/layer3/gate-b/decision",
            "absolute_path_exposed": False,
            "bounded_text_preview": True,
            "rag_vector_index_enabled": False,
            "web_connector_enabled": False,
            "package_construction_enabled": False,
        },
        "source_directory_preview_mode": MODE,
        "source_ingestion_batch_id": batch.source_ingestion_batch_id,
        "source_ingestion_file_id": file_record.source_ingestion_file_id,
        "material_preview_id": _stable_hash(
            {
                "mode": MODE,
                "source_ingestion_batch_id": batch.source_ingestion_batch_id,
                "source_ingestion_file_id": file_record.source_ingestion_file_id,
                "file_identity_hash": file_record.file_identity_hash,
                "max_chars": max_chars,
            }
        )[:36],
        "material_preview_hash": preview_hash,
        "material_candidate": material_candidate,
        "partial_retrieval": truncated,
        "downstream_eligibility": _downstream_eligibility(),
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [
            "submit_source_directory_material_candidate_to_gate_b_decision",
            "define_later_freeze_before_rag_connector_package_or_rendered_source_controls",
        ],
    }


def validate_source_directory_gate_b_decision_basis(
    db: Session,
    *,
    candidate_id: str,
    decision_basis: Mapping[str, Any],
) -> None:
    blocked_fields = _forbidden_decision_basis_fields(decision_basis)
    if blocked_fields:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_gate_b_forbidden_field_not_admitted",
            "The source-directory Gate B decision basis includes a field from a deferred or forbidden runtime mode.",
            details={"blocked_fields": blocked_fields},
        )
    file_id = _source_ingestion_file_id_from_candidate(candidate_id)
    if not file_id:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_gate_b_candidate_id_not_admitted",
            "The Gate B material candidate is not an admitted source-directory file candidate.",
            details={"blocked_fields": ["candidate_decisions.candidate_id"]},
        )
    payload = decision_basis.get("payload") if isinstance(decision_basis.get("payload"), Mapping) else {}
    batch_id = str(payload.get("source_ingestion_batch_id") or "").strip()
    if not batch_id:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_gate_b_batch_id_missing",
            "The Gate B decision basis must include the source directory ingestion batch id.",
            details={"blocked_fields": ["candidate_decisions.decision_basis.payload.source_ingestion_batch_id"]},
        )
    batch, file_record = _load_authority(db, batch_id=batch_id, file_id=file_id)

    expected_source_ref = f"source_directory_ingestion_file:{file_id}"
    _assert_scalar(decision_basis, "source_ref", expected_source_ref, "source_directory_gate_b_source_ref_mismatch")
    _assert_scalar(decision_basis, "query_basis", MODE, "source_directory_gate_b_query_basis_mismatch")
    _assert_scalar(decision_basis, "provenance_ref", _provenance_ref(batch, file_record), "source_directory_gate_b_provenance_ref_mismatch")
    _assert_mapping_fields(
        decision_basis.get("source_identity"),
        fields=_source_identity(batch, file_record),
        field_prefix="candidate_decisions.decision_basis.source_identity",
        code="source_directory_gate_b_source_identity_mismatch",
    )
    _assert_mapping_fields(
        payload,
        fields={
            "source_ingestion_batch_id": batch.source_ingestion_batch_id,
            "source_ingestion_file_id": file_record.source_ingestion_file_id,
            "source_class": SOURCE_CLASS,
            "content_sha256": file_record.content_sha256,
            "file_identity_hash": file_record.file_identity_hash,
            "authority_basis_hash": file_record.authority_basis_hash,
        },
        field_prefix="candidate_decisions.decision_basis.payload",
        code="source_directory_gate_b_payload_mismatch",
    )
    _assert_live_file_matches_authority(file_record, _read_live_file(file_record, max_chars=1))


def _normalise_preview_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    allowed = {
        "client_request_id",
        "source_ingestion_batch_id",
        "source_ingestion_file_id",
        "file_identity_hash",
        "authority_basis_hash",
        "max_chars",
        "actor",
    }
    unknown = sorted(set(fields) - allowed)
    if unknown:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_preview_unknown_field",
            "The source-directory material preview request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    return fields


def _load_authority(
    db: Session,
    *,
    batch_id: str,
    file_id: str,
) -> tuple[L3SourceDirectoryIngestionBatch, L3SourceDirectoryIngestionFile]:
    batch = db.get(L3SourceDirectoryIngestionBatch, batch_id)
    file_record = db.get(L3SourceDirectoryIngestionFile, file_id)
    if batch is None:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_batch_not_found",
            "No source directory ingestion batch exists for the requested material preview.",
            http_status=404,
            details={"source_ingestion_batch_id": batch_id},
        )
    if file_record is None:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_file_not_found",
            "No source directory ingestion file exists for the requested material preview.",
            http_status=404,
            details={"source_ingestion_file_id": file_id},
        )
    if file_record.source_ingestion_batch_id != batch.source_ingestion_batch_id:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_file_batch_mismatch",
            "The requested source directory file is not owned by the requested ingestion batch.",
            http_status=409,
            details={"source_ingestion_batch_id": batch_id, "source_ingestion_file_id": file_id},
        )
    if batch.status != STATUS_RECORDED or batch.source_family != SOURCE_FAMILY or batch.ingestion_mode != INGESTION_MODE:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_batch_not_admitted",
            "Only recorded server-configured source-directory ingestion batches are admitted.",
            http_status=409,
            details={"source_ingestion_batch_id": batch_id},
        )
    if file_record.status != STATUS_RECORDED or file_record.extension not in ALLOWED_EXTENSIONS:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_file_not_admitted",
            "Only recorded admitted source-directory text/table files are admitted.",
            http_status=409,
            details={"source_ingestion_file_id": file_id, "extension": file_record.extension},
        )
    return batch, file_record


def _assert_expected_hashes(
    file_record: L3SourceDirectoryIngestionFile,
    *,
    expected_file_identity_hash: str,
    expected_authority_basis_hash: str,
) -> None:
    mismatches = []
    if expected_file_identity_hash != file_record.file_identity_hash:
        mismatches.append("file_identity_hash")
    if expected_authority_basis_hash != file_record.authority_basis_hash:
        mismatches.append("authority_basis_hash")
    if mismatches:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_preview_stale_authority",
            "The requested source-directory material preview does not match current persisted file authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _read_live_file(file_record: L3SourceDirectoryIngestionFile, *, max_chars: int) -> dict[str, Any]:
    try:
        root = _configured_root()
    except SourceDirectoryIngestionError as exc:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_config_unavailable",
            "The configured source-directory root is not available for material preview.",
            http_status=exc.http_status,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id, **exc.details},
        ) from exc
    relative = PurePosixPath(file_record.relative_name)
    if len(relative.parts) != 1 or relative.name != file_record.relative_name:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_relative_name_not_admitted",
            "The persisted source-directory file name is outside the admitted direct-child shape.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        )
    resolved_root = root.resolve()
    resolved_path = (root / file_record.relative_name).resolve()
    if resolved_root not in resolved_path.parents:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_path_not_admitted",
            "The persisted source-directory file resolves outside the configured server-owned root.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        )
    try:
        path_available = resolved_path.exists() and resolved_path.is_file()
    except OSError as exc:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_file_unreadable",
            "The source-directory file could not be inspected for material preview.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        ) from exc
    if not path_available:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_file_missing",
            "The source-directory file is not available for material preview.",
            http_status=404,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        )
    try:
        before = resolved_path.stat()
        data = resolved_path.read_bytes()
        after = resolved_path.stat()
    except OSError as exc:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_file_unreadable",
            "The source-directory file could not be read for material preview.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        ) from exc
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_file_changed_during_read",
            "The source-directory file changed while material preview was reading it.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_text_decode_failed",
            "The source-directory file no longer decodes as UTF-8 text.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        ) from exc
    content_sha256 = hashlib.sha256(data).hexdigest()
    file_identity_hash = _stable_hash(
        {
            "relative_name": file_record.relative_name,
            "extension": file_record.extension,
            "content_size_bytes": after.st_size,
            "mtime_ns": after.st_mtime_ns,
            "content_sha256": content_sha256,
        }
    )
    return {
        "preview_text": text[:max_chars],
        "decoded_char_count": len(text),
        "content_sha256": content_sha256,
        "content_size_bytes": after.st_size,
        "mtime_ns": after.st_mtime_ns,
        "file_identity_hash": file_identity_hash,
    }


def _assert_live_file_matches_authority(file_record: L3SourceDirectoryIngestionFile, live_file: Mapping[str, Any]) -> None:
    mismatches = [
        field
        for field, expected in {
            "content_sha256": file_record.content_sha256,
            "content_size_bytes": file_record.content_size_bytes,
            "mtime_ns": file_record.mtime_ns,
            "file_identity_hash": file_record.file_identity_hash,
        }.items()
        if str(live_file.get(field) or "") != str(expected)
    ]
    if mismatches:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_preview_file_identity_mismatch",
            "The live source-directory file no longer matches the persisted file authority.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id, "blocked_fields": mismatches},
        )


def _source_identity(
    batch: L3SourceDirectoryIngestionBatch,
    file_record: L3SourceDirectoryIngestionFile,
) -> dict[str, Any]:
    return {
        "source_ingestion_batch_id": batch.source_ingestion_batch_id,
        "source_ingestion_file_id": file_record.source_ingestion_file_id,
        "source_family": SOURCE_FAMILY,
        "source_class": SOURCE_CLASS,
        "relative_name": file_record.relative_name,
        "extension": file_record.extension,
        "media_type": file_record.media_type,
        "content_size_bytes": file_record.content_size_bytes,
        "content_sha256": file_record.content_sha256,
        "file_identity_hash": file_record.file_identity_hash,
        "authority_basis_hash": file_record.authority_basis_hash,
    }


def _source_provenance(
    batch: L3SourceDirectoryIngestionBatch,
    file_record: L3SourceDirectoryIngestionFile,
    *,
    source_ref: str,
) -> dict[str, Any]:
    return {
        "schema_id": INGESTION_SCHEMA_ID,
        "mode": MODE,
        "source_ref": source_ref,
        "config_authority": CONFIG_AUTHORITY,
        "source_root_ref": _source_root_ref(),
        "source_root_absolute_path_exposed": False,
        "direct_child_only": True,
        "source_ingestion_batch_id": batch.source_ingestion_batch_id,
        "source_ingestion_file_id": file_record.source_ingestion_file_id,
        "directory_fingerprint_hash": batch.directory_fingerprint_hash,
        "batch_authority_basis_hash": batch.authority_basis_hash,
        "file_authority_basis_hash": file_record.authority_basis_hash,
    }


def _provenance_ref(batch: L3SourceDirectoryIngestionBatch, file_record: L3SourceDirectoryIngestionFile) -> str:
    return (
        f"source_directory_ingestion_batch:{batch.source_ingestion_batch_id}"
        f":file:{file_record.source_ingestion_file_id}:authority:{file_record.authority_basis_hash}"
    )


def _normalise_max_chars(raw_value: Any) -> int:
    if raw_value is None:
        return PREVIEW_MAX_CHARS
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_preview_max_chars_invalid",
            "source-directory material preview max_chars must be an integer from 1 through 4000.",
            details={"max_chars": raw_value},
        ) from exc
    if value < 1 or value > PREVIEW_MAX_CHARS:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_preview_max_chars_invalid",
            "source-directory material preview max_chars must be an integer from 1 through 4000.",
            details={"max_chars": value, "max_allowed_chars": PREVIEW_MAX_CHARS},
        )
    return value


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryMaterialAdmissionError(
            "source_directory_material_preview_required_field_missing",
            "A required source-directory material preview field is missing or empty.",
            details={"field": key},
        )
    return value


def _source_ingestion_file_id_from_candidate(candidate_id: str) -> str | None:
    value = str(candidate_id or "").strip()
    if not value.startswith(GATE_B_CANDIDATE_PREFIX):
        return None
    file_id = value[len(GATE_B_CANDIDATE_PREFIX) :].strip()
    return file_id or None


def _forbidden_decision_basis_fields(value: Any, prefix: str = "candidate_decisions.decision_basis") -> list[str]:
    blocked: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, nested_value in value.items():
            key = str(raw_key)
            field_path = f"{prefix}.{key}"
            if key in _FORBIDDEN_DECISION_BASIS_FIELDS:
                blocked.append(field_path)
            blocked.extend(_forbidden_decision_basis_fields(nested_value, field_path))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            blocked.extend(_forbidden_decision_basis_fields(nested_value, f"{prefix}.{index}"))
    return sorted(set(blocked))


def _assert_scalar(decision_basis: Mapping[str, Any], field: str, expected: str, code: str) -> None:
    if str(decision_basis.get(field) or "").strip() != expected:
        raise SourceDirectoryMaterialAdmissionError(
            code,
            "The Gate B decision basis does not match the source-directory material preview.",
            http_status=409,
            details={"blocked_fields": [f"candidate_decisions.decision_basis.{field}"]},
        )


def _assert_mapping_fields(
    value: Any,
    *,
    fields: Mapping[str, Any],
    field_prefix: str,
    code: str,
) -> None:
    if not isinstance(value, Mapping):
        raise SourceDirectoryMaterialAdmissionError(
            code,
            "The Gate B decision basis is missing source-directory authority fields.",
            details={"blocked_fields": [field_prefix]},
        )
    mismatches = [f"{field_prefix}.{key}" for key, expected in fields.items() if str(value.get(key) or "") != str(expected)]
    if mismatches:
        raise SourceDirectoryMaterialAdmissionError(
            code,
            "The Gate B decision basis does not match the source-directory authority row.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _downstream_eligibility() -> dict[str, bool]:
    return {
        "source_directory_ingestion_recorded": True,
        "eligible_for_material_preview": True,
        "eligible_for_gate_b_material_admission": True,
        "eligible_for_rag_vector_index": False,
        "eligible_for_web_connector": False,
        "eligible_for_package_construction": False,
        "eligible_for_frontend_durable_authority": False,
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        **_ingestion_negative_invariants(),
        "material_preview_writes_source_rows": False,
        "gate_b_material_admission_writes_package_rows": False,
        "rag_vector_index_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
    }


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
