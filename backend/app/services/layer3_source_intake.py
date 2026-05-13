from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import L3SourceIntakeRecord
from app.services.layer3_gate_b_state import (
    material_candidate_basis_from_preview as _gate_b_material_candidate_basis_from_preview,
    material_preview_hash as _gate_b_material_preview_hash,
)


SOURCE_INTAKE_SCHEMA_ID = "layer3.source_intake_record.v1"
SOURCE_INTAKE_MODE = "operator_single_upload_source_intake"
SOURCE_INTAKE_SOURCE_GATE = "286_SOURCE_BREADTH_RUNTIME_ENTRY_FREEZE"
SOURCE_INTAKE_OPERATOR_DECISION = "record_operator_uploaded_source"
SOURCE_INTAKE_STATUS = "recorded"
SOURCE_INTAKE_SOURCE_FAMILY = "operator_uploaded_single_source"
SOURCE_INTAKE_STORAGE_SEGMENT = "layer3-source-intake"
SOURCE_INTAKE_INVENTORY_SCHEMA_ID = "layer3.source_intake_inventory.v1"
SOURCE_INTAKE_INVENTORY_MODE = "operator_source_intake_inventory_read_only"
SOURCE_INTAKE_INVENTORY_DEFAULT_LIMIT = 50
SOURCE_INTAKE_INVENTORY_MAX_LIMIT = 100
SOURCE_INTAKE_DESCRIPTION_MAX_CHARS = 2000
SOURCE_INTAKE_INVENTORY_DESCRIPTION_MAX_CHARS = 512
SOURCE_INTAKE_PREVIEW_SCHEMA_ID = "layer3.source_intake_material_preview.v1"
SOURCE_INTAKE_PREVIEW_MODE = "operator_source_intake_material_preview_read_only"
SOURCE_INTAKE_PREVIEW_MAX_CHARS = 4000
SOURCE_INTAKE_GATE_B_MODE = "source_intake_gate_b_material_admission"
SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX = "mat-source_intake_record-"

SERVER_AUTHORITY = (
    "Layer 3 source intake record owns source identity, bytes/metadata hash, "
    "provenance, freshness, storage pointer, and downstream eligibility."
)

_CLIENT_REQUEST_RE = re.compile(r"^[A-Za-z0-9._:-]{1,255}$")
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

_ALLOWED_FIELDS = {
    "client_request_id",
    "operator_decision",
    "source_label",
    "source_description",
    "source_family",
    "freshness_timestamp",
    "declared_media_type",
}

_FORBIDDEN_FIELDS = {
    "auth_context",
    "browser_durable_authority",
    "connector_key",
    "connector_run_id",
    "destination_url",
    "local_directory",
    "local_path",
    "local_upload",
    "package_payload",
    "provider_url",
    "public_url",
    "rag_plan",
    "rag_vector_index",
    "runtime_db_query",
    "runtime_db_write",
    "schema_widening",
    "signed_url",
    "source_expansion",
    "source_upload",
    "vector_plan",
    "web_connector",
}


class SourceIntakeError(Exception):
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
            "schema_id": SOURCE_INTAKE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-intake-error",
            "server_time": _server_time(),
            "mode": SOURCE_INTAKE_MODE,
            "status": "blocked",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


def normalise_source_intake_form_items(form_items: Iterable[tuple[Any, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {}
    duplicate_fields: set[str] = set()
    file_part_count = 0
    for raw_key, value in form_items:
        key = str(raw_key)
        if key == "file":
            file_part_count += 1
            continue
        if value is None:
            continue
        if key in fields:
            duplicate_fields.add(key)
            continue
        fields[key] = str(value).strip()
    if file_part_count > 1:
        raise SourceIntakeError(
            "source_intake_duplicate_file_field",
            "The source-intake upload includes duplicate file fields and is ambiguous.",
            details={"duplicate_file_fields": ["file"], "file_part_count": file_part_count},
        )
    if duplicate_fields:
        raise SourceIntakeError(
            "source_intake_duplicate_field",
            "The source-intake upload includes duplicate form fields and is ambiguous.",
            details={"duplicate_fields": sorted(duplicate_fields)},
        )
    return _normalise_fields(fields)


def record_operator_upload_source_intake(
    db: Session,
    *,
    file_bytes: bytes,
    original_filename: str | None,
    media_type: str | None,
    form_fields: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_fields(form_fields)
    client_request_id = _required(fields, "client_request_id")
    if not _CLIENT_REQUEST_RE.match(client_request_id):
        raise SourceIntakeError(
            "source_intake_invalid_client_request_id",
            "client_request_id must be 1-255 characters using letters, numbers, dot, dash, underscore, or colon.",
            details={"client_request_id": client_request_id},
        )

    operator_decision = _required(fields, "operator_decision")
    if operator_decision != SOURCE_INTAKE_OPERATOR_DECISION:
        raise SourceIntakeError(
            "source_intake_operator_decision_not_admitted",
            "operator_decision is not admitted for the Layer 3 source-intake runtime slice.",
            details={
                "expected_operator_decision": SOURCE_INTAKE_OPERATOR_DECISION,
                "received_operator_decision": operator_decision,
            },
        )

    source_family = fields.get("source_family") or SOURCE_INTAKE_SOURCE_FAMILY
    if source_family != SOURCE_INTAKE_SOURCE_FAMILY:
        raise SourceIntakeError(
            "source_intake_family_not_admitted",
            "Only the approved operator-uploaded single-source family is admitted.",
            details={
                "expected_source_family": SOURCE_INTAKE_SOURCE_FAMILY,
                "received_source_family": source_family,
            },
        )

    source_label = _required(fields, "source_label")
    if len(source_label) > 255:
        raise SourceIntakeError(
            "source_intake_label_too_long",
            "source_label must be 255 characters or fewer.",
            details={"source_label_length": len(source_label)},
        )

    source_description = fields.get("source_description") or None
    if source_description is not None and len(source_description) > SOURCE_INTAKE_DESCRIPTION_MAX_CHARS:
        raise SourceIntakeError(
            "source_intake_description_too_long",
            "source_description must be 2000 characters or fewer.",
            details={
                "source_description_length": len(source_description),
                "max_chars": SOURCE_INTAKE_DESCRIPTION_MAX_CHARS,
            },
        )
    declared_media_type = fields.get("declared_media_type") or None
    effective_media_type = declared_media_type or media_type or "application/octet-stream"
    if len(effective_media_type) > 128:
        raise SourceIntakeError(
            "source_intake_media_type_too_long",
            "media type must be 128 characters or fewer.",
            details={"media_type_length": len(effective_media_type)},
        )

    if not file_bytes:
        raise SourceIntakeError(
            "source_intake_empty_file",
            "The source-intake upload must include non-empty file bytes.",
        )
    max_bytes = int(settings.max_upload_mb) * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise SourceIntakeError(
            "source_intake_file_too_large",
            "The source-intake upload exceeds the configured maximum upload size.",
            details={"max_upload_mb": settings.max_upload_mb, "received_bytes": len(file_bytes)},
        )

    freshness_timestamp = _parse_freshness_timestamp(fields.get("freshness_timestamp"))
    safe_filename = _safe_filename(original_filename)
    content_sha256 = hashlib.sha256(file_bytes).hexdigest()
    metadata = _metadata_payload(
        client_request_id=client_request_id,
        source_family=source_family,
        source_label=source_label,
        source_description=source_description,
        original_filename=safe_filename,
        media_type=effective_media_type,
        content_size_bytes=len(file_bytes),
        content_sha256=content_sha256,
        freshness_timestamp=freshness_timestamp,
    )
    metadata_hash = _stable_hash(metadata)
    authority_basis = {
        "schema_id": SOURCE_INTAKE_SCHEMA_ID,
        "mode": SOURCE_INTAKE_MODE,
        "operator_decision": operator_decision,
        "client_request_id": client_request_id,
        "metadata_hash": metadata_hash,
        "content_sha256": content_sha256,
        "source_gate": SOURCE_INTAKE_SOURCE_GATE,
    }
    authority_basis_hash = _stable_hash(authority_basis)

    existing = _existing_record(db, client_request_id, authority_basis_hash)
    if existing is not None:
        _ensure_idempotent_match(
            existing,
            content_sha256=content_sha256,
            authority_basis_hash=authority_basis_hash,
            client_request_id=client_request_id,
        )
        return _record_response(existing, response_status="already_recorded")

    storage_ref = _write_content_addressed_file(file_bytes, content_sha256, safe_filename)
    downstream_eligibility = _downstream_eligibility()
    provenance = {
        "schema_id": SOURCE_INTAKE_SCHEMA_ID,
        "mode": SOURCE_INTAKE_MODE,
        "operator_decision": operator_decision,
        "server_authority": SERVER_AUTHORITY,
        "source_gate": SOURCE_INTAKE_SOURCE_GATE,
        "content_sha256": content_sha256,
        "metadata_hash": metadata_hash,
        "freshness_timestamp": _iso_or_none(freshness_timestamp),
    }

    record = L3SourceIntakeRecord(
        client_request_id=client_request_id,
        operator_decision=operator_decision,
        source_family=source_family,
        source_label=source_label,
        source_description=source_description,
        original_filename=safe_filename,
        media_type=effective_media_type,
        content_size_bytes=len(file_bytes),
        content_sha256=content_sha256,
        metadata_hash=metadata_hash,
        authority_basis_hash=authority_basis_hash,
        storage_ref=storage_ref,
        freshness_timestamp=freshness_timestamp,
        provenance_json=provenance,
        downstream_eligibility_json=downstream_eligibility,
        summary_json={
            "metadata": metadata,
            "authority_basis": authority_basis,
            "negative_invariants": _negative_invariants(),
        },
        status=SOURCE_INTAKE_STATUS,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_after_race = _existing_record(db, client_request_id, authority_basis_hash)
        if existing_after_race is not None:
            _ensure_idempotent_match(
                existing_after_race,
                content_sha256=content_sha256,
                authority_basis_hash=authority_basis_hash,
                client_request_id=client_request_id,
            )
            return _record_response(existing_after_race, response_status="already_recorded")
        raise SourceIntakeError(
            "source_intake_record_conflict",
            "The source-intake record conflicts with an existing persisted authority row.",
            http_status=409,
            details={"client_request_id": client_request_id},
        ) from exc
    db.refresh(record)
    return _record_response(record)


def source_intake_inventory(
    db: Session,
    *,
    limit: int = SOURCE_INTAKE_INVENTORY_DEFAULT_LIMIT,
    source_family: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    try:
        normalized_limit = int(limit)
    except (TypeError, ValueError) as exc:
        raise SourceIntakeError(
            "source_intake_inventory_limit_invalid",
            "source-intake inventory limit must be an integer from 1 through 100.",
            details={"limit": limit},
        ) from exc
    if normalized_limit < 1 or normalized_limit > SOURCE_INTAKE_INVENTORY_MAX_LIMIT:
        raise SourceIntakeError(
            "source_intake_inventory_limit_invalid",
            "source-intake inventory limit must be an integer from 1 through 100.",
            details={
                "limit": normalized_limit,
                "max_limit": SOURCE_INTAKE_INVENTORY_MAX_LIMIT,
            },
        )

    normalized_source_family = (source_family or SOURCE_INTAKE_SOURCE_FAMILY).strip()
    if normalized_source_family != SOURCE_INTAKE_SOURCE_FAMILY:
        raise SourceIntakeError(
            "source_intake_inventory_source_family_not_admitted",
            "source-intake inventory is limited to the approved operator-uploaded single-source family.",
            details={
                "expected_source_family": SOURCE_INTAKE_SOURCE_FAMILY,
                "received_source_family": normalized_source_family,
            },
        )

    normalized_status = (status or SOURCE_INTAKE_STATUS).strip()
    if normalized_status != SOURCE_INTAKE_STATUS:
        raise SourceIntakeError(
            "source_intake_inventory_status_not_admitted",
            "source-intake inventory is limited to recorded intake rows.",
            details={
                "expected_status": SOURCE_INTAKE_STATUS,
                "received_status": normalized_status,
            },
        )

    records = (
        db.query(L3SourceIntakeRecord)
        .filter(L3SourceIntakeRecord.source_family == normalized_source_family)
        .filter(L3SourceIntakeRecord.status == normalized_status)
        .order_by(
            L3SourceIntakeRecord.created_at.desc(),
            L3SourceIntakeRecord.source_intake_record_id.desc(),
        )
        .limit(normalized_limit)
        .all()
    )

    return {
        "schema_id": SOURCE_INTAKE_INVENTORY_SCHEMA_ID,
        "schema_version": 1,
        "request_id": "source-intake-inventory",
        "server_time": _server_time(),
        "mode": SOURCE_INTAKE_INVENTORY_MODE,
        "status": "available",
        "message": "Layer 3 source intake inventory returned safe record metadata only.",
        "source_gate": {
            "canonical_source_of_truth": "L3SourceIntakeRecord",
            "source_gate": SOURCE_INTAKE_SOURCE_GATE,
            "writer_route": "POST /api/v1/layer3/source/intake/upload",
            "read_route": "GET /api/v1/layer3/source/intake/inventory",
            "no_file_bytes_returned": True,
            "absolute_path_exposed": False,
            "material_preview_enabled": False,
        },
        "source_intake_inventory_mode": SOURCE_INTAKE_INVENTORY_MODE,
        "source_family": SOURCE_INTAKE_SOURCE_FAMILY,
        "inventory_count": len(records),
        "limit": normalized_limit,
        "filters": {
            "source_family": normalized_source_family,
            "status": normalized_status,
        },
        "records": [_inventory_record_response(record) for record in records],
        "downstream_eligibility": _downstream_eligibility(),
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [
            "use_record_metadata_for_source_inventory_only",
            "use_bounded_preview_for_operator_review_only",
            "define_later_freeze_before_rag_connector_package_or_rendered_source_controls",
        ],
    }


def source_intake_material_preview(
    db: Session,
    *,
    source_intake_record_id: str,
    max_chars: int = SOURCE_INTAKE_PREVIEW_MAX_CHARS,
) -> dict[str, Any]:
    record_id = str(source_intake_record_id or "").strip()
    if not record_id:
        raise SourceIntakeError(
            "source_intake_preview_record_id_required",
            "source_intake_record_id is required for operator-uploaded material preview.",
            details={"field": "source_intake_record_id"},
        )
    try:
        normalized_max_chars = int(max_chars)
    except (TypeError, ValueError) as exc:
        raise SourceIntakeError(
            "source_intake_preview_max_chars_invalid",
            "source-intake material preview max_chars must be an integer from 1 through 4000.",
            details={"max_chars": max_chars},
        ) from exc
    if normalized_max_chars < 1 or normalized_max_chars > SOURCE_INTAKE_PREVIEW_MAX_CHARS:
        raise SourceIntakeError(
            "source_intake_preview_max_chars_invalid",
            "source-intake material preview max_chars must be an integer from 1 through 4000.",
            details={
                "max_chars": normalized_max_chars,
                "max_allowed_chars": SOURCE_INTAKE_PREVIEW_MAX_CHARS,
            },
        )

    record = (
        db.query(L3SourceIntakeRecord)
        .filter(L3SourceIntakeRecord.source_intake_record_id == record_id)
        .one_or_none()
    )
    if record is None:
        raise SourceIntakeError(
            "source_intake_preview_record_not_found",
            "No source-intake record exists for the requested preview.",
            http_status=404,
            details={"source_intake_record_id": record_id},
        )
    if record.status != SOURCE_INTAKE_STATUS or record.source_family != SOURCE_INTAKE_SOURCE_FAMILY:
        raise SourceIntakeError(
            "source_intake_preview_record_not_admitted",
            "Only recorded operator-uploaded single-source rows are admitted for material preview.",
            details={
                "status": record.status,
                "source_family": record.source_family,
            },
        )

    media_type = _normalise_media_type(record.media_type)
    if not _is_text_preview_media_type(media_type):
        raise SourceIntakeError(
            "source_intake_preview_media_type_not_admitted",
            "Only bounded text-like operator-uploaded source material preview is admitted.",
            details={"media_type": record.media_type},
        )

    storage_path = _storage_path_from_ref(record.storage_ref)
    if not storage_path.exists() or not storage_path.is_file():
        raise SourceIntakeError(
            "source_intake_preview_storage_missing",
            "The source-intake storage object is not available for preview.",
            http_status=404,
            details={"storage_ref": record.storage_ref},
        )
    preview_text, decoded_char_count, content_sha256 = _preview_text_and_hash(
        storage_path,
        normalized_max_chars,
    )
    if content_sha256 != record.content_sha256:
        raise SourceIntakeError(
            "source_intake_preview_hash_mismatch",
            "The source-intake storage object hash does not match the persisted authority row.",
            http_status=409,
            details={"source_intake_record_id": record.source_intake_record_id},
        )

    truncated = decoded_char_count > normalized_max_chars
    material_preview_id = _stable_hash(
        {
            "mode": SOURCE_INTAKE_PREVIEW_MODE,
            "source_intake_record_id": record.source_intake_record_id,
            "content_sha256": record.content_sha256,
            "max_chars": normalized_max_chars,
        }
    )[:36]
    source_ref = f"source_intake_record:{record.source_intake_record_id}"
    source_identity = {
        **_inventory_record_response(record)["source_identity"],
        "source_intake_record_id": record.source_intake_record_id,
    }
    source_provenance = {
        **(record.provenance_json or {}),
        "mode": SOURCE_INTAKE_GATE_B_MODE,
        "source_ref": source_ref,
    }
    material_candidate = {
        "candidate_id": f"{SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX}{record.source_intake_record_id}",
        "source_class": SOURCE_INTAKE_SOURCE_FAMILY,
        "source_ref": source_ref,
        "query_basis": "operator_uploaded_source_intake",
        "provenance_ref": f"source_intake_record:{record.source_intake_record_id}:metadata:{record.metadata_hash}",
        "source_label": record.source_label,
        "media_type": record.media_type,
        "content_size_bytes": record.content_size_bytes,
        "content_sha256": record.content_sha256,
        "metadata_hash": record.metadata_hash,
        "authority_basis_hash": record.authority_basis_hash,
        "preview_text": preview_text,
        "preview_char_count": len(preview_text),
        "preview_truncated": truncated,
        "preview_encoding": "utf-8-replace",
        "storage_pointer": {
            "storage_ref": record.storage_ref,
            "storage_authority": "server_raw_storage",
            "content_addressed": True,
            "absolute_path_exposed": False,
        },
        "source_identity": source_identity,
        "source_provenance": source_provenance,
        "payload": {
            "source_intake_record_id": record.source_intake_record_id,
            "source_class": SOURCE_INTAKE_SOURCE_FAMILY,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
            "authority_basis_hash": record.authority_basis_hash,
            "bounded_preview_char_count": len(preview_text),
            "preview_truncated": truncated,
        },
        "load_summary": {
            "loaded_records": 1,
            "failed_records": 0,
            "preview_material": True,
            "bounded_text_preview": True,
            "source_intake_gate_b_material_admission": True,
        },
        "current_decision_state": "candidate",
    }
    material_preview_hash = _gate_b_material_preview_hash(
        [_gate_b_material_candidate_basis_from_preview(material_candidate)]
    )
    return {
        "schema_id": SOURCE_INTAKE_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "request_id": record.client_request_id,
        "server_time": _server_time(),
        "mode": SOURCE_INTAKE_PREVIEW_MODE,
        "status": "available",
        "message": "Layer 3 source-intake material preview returned bounded text from one server-owned intake record.",
        "source_gate": {
            "canonical_source_of_truth": "L3SourceIntakeRecord",
            "source_gate": "288_SOURCE_INTAKE_MATERIAL_PREVIEW_FREEZE",
            "writer_route": "POST /api/v1/layer3/source/intake/upload",
            "inventory_route": "GET /api/v1/layer3/source/intake/inventory",
            "preview_route": "GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview",
            "gate_b_material_admission_route": "POST /api/v1/layer3/gate-b/decision",
            "absolute_path_exposed": False,
            "bounded_text_preview": True,
            "rag_vector_index_enabled": False,
            "web_connector_enabled": False,
            "package_construction_enabled": False,
        },
        "source_intake_preview_mode": SOURCE_INTAKE_PREVIEW_MODE,
        "source_intake_record_id": record.source_intake_record_id,
        "material_preview_id": material_preview_id,
        "material_preview_hash": material_preview_hash,
        "material_candidate": material_candidate,
        "partial_retrieval": truncated,
        "downstream_eligibility": _downstream_eligibility(),
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [
            "submit_source_intake_material_candidate_to_gate_b_decision",
            "define_later_freeze_before_rag_connector_package_or_rendered_source_controls",
        ],
    }


_SOURCE_INTAKE_GATE_B_FORBIDDEN_FIELDS = {
    "absolute_path",
    "auth_policy",
    "connector_target",
    "destination",
    "directory_path",
    "execution_mode",
    "file",
    "file_bytes",
    "frontend_state",
    "local_path",
    "package_payload",
    "provider_url",
    "public_url",
    "rag_index",
    "vector_index",
    "web_connector",
}


def validate_source_intake_gate_b_decision_basis(
    db: Session,
    *,
    candidate_id: str,
    decision_basis: Mapping[str, Any],
) -> None:
    blocked_fields = _gate_b_forbidden_decision_basis_fields(decision_basis)
    if blocked_fields:
        raise SourceIntakeError(
            "source_intake_gate_b_forbidden_field_not_admitted",
            "The source-intake Gate B decision basis includes a field from a deferred or forbidden runtime mode.",
            details={"blocked_fields": blocked_fields},
        )

    record_id = _source_intake_record_id_from_candidate(candidate_id)
    if not record_id:
        raise SourceIntakeError(
            "source_intake_gate_b_candidate_id_not_admitted",
            "The Gate B material candidate is not an admitted source-intake record candidate.",
            details={"blocked_fields": ["candidate_decisions.candidate_id"]},
        )

    record = db.get(L3SourceIntakeRecord, record_id)
    if record is None:
        raise SourceIntakeError(
            "source_intake_gate_b_record_not_found",
            "No source-intake authority row exists for the Gate B material candidate.",
            http_status=404,
            details={"source_intake_record_id": record_id},
        )
    if record.status != SOURCE_INTAKE_STATUS or record.source_family != SOURCE_INTAKE_SOURCE_FAMILY:
        raise SourceIntakeError(
            "source_intake_gate_b_record_not_admitted",
            "Only recorded operator-uploaded single-source rows are admitted for Gate B material selection.",
            http_status=409,
            details={
                "source_intake_record_id": record.source_intake_record_id,
                "status": record.status,
                "source_family": record.source_family,
                "blocked_fields": ["candidate_decisions.decision_basis.source_intake_record_id"],
            },
        )
    media_type = _normalise_media_type(record.media_type)
    if not _is_text_preview_media_type(media_type):
        raise SourceIntakeError(
            "source_intake_gate_b_media_type_not_admitted",
            "Only bounded text-like operator-uploaded source material is admitted for Gate B material selection.",
            details={
                "source_intake_record_id": record.source_intake_record_id,
                "media_type": record.media_type,
                "blocked_fields": ["candidate_decisions.decision_basis.media_type"],
            },
        )

    storage_path = _storage_path_from_ref(record.storage_ref)
    if not storage_path.exists() or not storage_path.is_file():
        raise SourceIntakeError(
            "source_intake_gate_b_storage_missing",
            "The source-intake storage object is not available for Gate B material selection.",
            http_status=404,
            details={"source_intake_record_id": record.source_intake_record_id, "storage_ref": record.storage_ref},
        )
    _, _, content_sha256 = _preview_text_and_hash(storage_path, 1)
    if content_sha256 != record.content_sha256:
        raise SourceIntakeError(
            "source_intake_gate_b_hash_mismatch",
            "The source-intake storage object hash does not match the persisted authority row.",
            http_status=409,
            details={"source_intake_record_id": record.source_intake_record_id},
        )

    expected_source_ref = f"source_intake_record:{record.source_intake_record_id}"
    source_ref = str(decision_basis.get("source_ref") or "").strip()
    if source_ref != expected_source_ref:
        raise SourceIntakeError(
            "source_intake_gate_b_source_ref_mismatch",
            "The Gate B decision basis source_ref does not match the source-intake authority row.",
            http_status=409,
            details={
                "expected_source_ref": expected_source_ref,
                "received_source_ref": source_ref,
                "blocked_fields": ["candidate_decisions.decision_basis.source_ref"],
            },
        )
    if str(decision_basis.get("query_basis") or "").strip() != "operator_uploaded_source_intake":
        raise SourceIntakeError(
            "source_intake_gate_b_query_basis_mismatch",
            "The Gate B decision basis query_basis does not match the source-intake material preview.",
            http_status=409,
            details={"blocked_fields": ["candidate_decisions.decision_basis.query_basis"]},
        )
    expected_provenance_ref = f"source_intake_record:{record.source_intake_record_id}:metadata:{record.metadata_hash}"
    if str(decision_basis.get("provenance_ref") or "").strip() != expected_provenance_ref:
        raise SourceIntakeError(
            "source_intake_gate_b_provenance_ref_mismatch",
            "The Gate B decision basis provenance_ref does not match the source-intake authority row.",
            http_status=409,
            details={"blocked_fields": ["candidate_decisions.decision_basis.provenance_ref"]},
        )

    source_identity = decision_basis.get("source_identity")
    if not isinstance(source_identity, Mapping):
        raise SourceIntakeError(
            "source_intake_gate_b_source_identity_missing",
            "The Gate B decision basis must include source_identity from the source-intake material preview.",
            details={"blocked_fields": ["candidate_decisions.decision_basis.source_identity"]},
        )
    _assert_gate_b_basis_matches_record(
        source_identity,
        record,
        fields={
            "source_intake_record_id": record.source_intake_record_id,
            "source_family": SOURCE_INTAKE_SOURCE_FAMILY,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
        },
        field_prefix="candidate_decisions.decision_basis.source_identity",
        code="source_intake_gate_b_source_identity_mismatch",
        message="The Gate B decision basis source_identity does not match the source-intake authority row.",
    )

    payload = decision_basis.get("payload")
    if not isinstance(payload, Mapping):
        raise SourceIntakeError(
            "source_intake_gate_b_payload_missing",
            "The Gate B decision basis must include the source-intake material preview payload.",
            details={"blocked_fields": ["candidate_decisions.decision_basis.payload"]},
        )
    _assert_gate_b_basis_matches_record(
        payload,
        record,
        fields={
            "source_intake_record_id": record.source_intake_record_id,
            "source_class": SOURCE_INTAKE_SOURCE_FAMILY,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
            "authority_basis_hash": record.authority_basis_hash,
        },
        field_prefix="candidate_decisions.decision_basis.payload",
        code="source_intake_gate_b_payload_mismatch",
        message="The Gate B decision basis payload does not match the source-intake authority row.",
    )


def _source_intake_record_id_from_candidate(candidate_id: str) -> str | None:
    value = str(candidate_id or "").strip()
    if not value.startswith(SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX):
        return None
    record_id = value[len(SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX) :].strip()
    return record_id or None


def _gate_b_forbidden_decision_basis_fields(value: Any, prefix: str = "candidate_decisions.decision_basis") -> list[str]:
    blocked: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, nested_value in value.items():
            key = str(raw_key)
            field_path = f"{prefix}.{key}"
            if key in _SOURCE_INTAKE_GATE_B_FORBIDDEN_FIELDS:
                blocked.append(field_path)
            blocked.extend(_gate_b_forbidden_decision_basis_fields(nested_value, field_path))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            blocked.extend(_gate_b_forbidden_decision_basis_fields(nested_value, f"{prefix}.{index}"))
    return sorted(set(blocked))


def _assert_gate_b_basis_matches_record(
    value: Mapping[str, Any],
    record: L3SourceIntakeRecord,
    *,
    fields: Mapping[str, Any],
    field_prefix: str,
    code: str,
    message: str,
) -> None:
    mismatched_fields = [
        f"{field_prefix}.{key}"
        for key, expected in fields.items()
        if str(value.get(key) or "") != str(expected)
    ]
    if mismatched_fields:
        raise SourceIntakeError(
            code,
            message,
            http_status=409,
            details={
                "source_intake_record_id": record.source_intake_record_id,
                "blocked_fields": mismatched_fields,
            },
        )


def _normalise_fields(form_fields: Mapping[str, Any]) -> dict[str, str]:
    fields = {
        str(key): str(value).strip()
        for key, value in form_fields.items()
        if key != "file" and value is not None
    }
    blocked = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if blocked:
        raise SourceIntakeError(
            "source_intake_forbidden_field",
            "The source-intake upload includes a field that belongs to a deferred or forbidden source mode.",
            details={"forbidden_fields": blocked},
        )
    unknown = sorted(set(fields) - _ALLOWED_FIELDS)
    if unknown:
        raise SourceIntakeError(
            "source_intake_unknown_field",
            "The source-intake upload contract is intentionally scoped and rejects undeclared fields.",
            details={"unknown_fields": unknown},
        )
    return fields


def _required(fields: Mapping[str, str], key: str) -> str:
    value = fields.get(key, "").strip()
    if not value:
        raise SourceIntakeError(
            "source_intake_required_field_missing",
            "A required source-intake form field is missing or empty.",
            details={"field": key},
        )
    return value


def _parse_freshness_timestamp(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceIntakeError(
            "source_intake_invalid_freshness_timestamp",
            "freshness_timestamp must be an ISO-8601 datetime.",
            details={"freshness_timestamp": raw_value},
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_filename(filename: str | None) -> str:
    candidate = (filename or "source.bin").strip().replace("\\", "/").split("/")[-1]
    candidate = _SAFE_FILENAME_RE.sub("_", candidate).strip("._")
    if not candidate:
        candidate = "source.bin"
    return candidate[:160]


def _metadata_payload(
    *,
    client_request_id: str,
    source_family: str,
    source_label: str,
    source_description: str | None,
    original_filename: str,
    media_type: str,
    content_size_bytes: int,
    content_sha256: str,
    freshness_timestamp: datetime | None,
) -> dict[str, Any]:
    return {
        "client_request_id": client_request_id,
        "source_family": source_family,
        "source_label": source_label,
        "source_description": source_description,
        "original_filename": original_filename,
        "media_type": media_type,
        "content_size_bytes": content_size_bytes,
        "content_sha256": content_sha256,
        "freshness_timestamp": _iso_or_none(freshness_timestamp),
    }


def _write_content_addressed_file(file_bytes: bytes, content_sha256: str, safe_filename: str) -> str:
    storage_dir = Path(settings.raw_storage_dir) / SOURCE_INTAKE_STORAGE_SEGMENT
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{content_sha256[:16]}_{safe_filename}"
    storage_path = storage_dir / storage_name
    if not storage_path.exists():
        storage_path.write_bytes(file_bytes)
    raw_root_name = Path(settings.raw_storage_dir).name
    return f"{raw_root_name}/{SOURCE_INTAKE_STORAGE_SEGMENT}/{storage_name}"


def _storage_path_from_ref(storage_ref: str) -> Path:
    ref = PurePosixPath(str(storage_ref or "").strip())
    parts = ref.parts
    raw_root = Path(settings.raw_storage_dir)
    if len(parts) != 3 or parts[0] != raw_root.name or parts[1] != SOURCE_INTAKE_STORAGE_SEGMENT:
        raise SourceIntakeError(
            "source_intake_preview_storage_ref_not_admitted",
            "The source-intake storage reference is outside the admitted server-owned raw storage segment.",
            details={"storage_ref": storage_ref},
        )
    storage_path = raw_root / SOURCE_INTAKE_STORAGE_SEGMENT / parts[2]
    resolved_root = (raw_root / SOURCE_INTAKE_STORAGE_SEGMENT).resolve()
    resolved_path = storage_path.resolve()
    if resolved_root not in resolved_path.parents:
        raise SourceIntakeError(
            "source_intake_preview_storage_ref_not_admitted",
            "The source-intake storage reference resolves outside the admitted server-owned raw storage segment.",
            details={"storage_ref": storage_ref},
        )
    return storage_path


def _is_text_preview_media_type(media_type: str) -> bool:
    if media_type.startswith("text/"):
        return True
    return media_type in {"application/json", "application/xml", "application/x-ndjson"}


def _normalise_media_type(media_type: str | None) -> str:
    return str(media_type or "").split(";", 1)[0].strip().lower()


def _preview_text_and_hash(storage_path: Path, max_chars: int) -> tuple[str, int, str]:
    digest = hashlib.sha256()
    preview_parts: list[str] = []
    decoded_char_count = 0
    with storage_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            decoded_chunk = chunk.decode("utf-8", errors="replace")
            decoded_char_count += len(decoded_chunk)
            remaining = max_chars - sum(len(part) for part in preview_parts)
            if remaining > 0:
                preview_parts.append(decoded_chunk[:remaining])
    return "".join(preview_parts), decoded_char_count, digest.hexdigest()


def _existing_record(
    db: Session,
    client_request_id: str,
    authority_basis_hash: str,
) -> L3SourceIntakeRecord | None:
    return (
        db.query(L3SourceIntakeRecord)
        .filter(
            (L3SourceIntakeRecord.client_request_id == client_request_id)
            | (L3SourceIntakeRecord.authority_basis_hash == authority_basis_hash)
        )
        .one_or_none()
    )


def _ensure_idempotent_match(
    record: L3SourceIntakeRecord,
    *,
    content_sha256: str,
    authority_basis_hash: str,
    client_request_id: str,
) -> None:
    if (
        record.content_sha256 != content_sha256
        or record.authority_basis_hash != authority_basis_hash
        or record.client_request_id != client_request_id
    ):
        raise SourceIntakeError(
            "source_intake_idempotency_conflict",
            "The source-intake idempotency key or authority basis conflicts with an existing record.",
            http_status=409,
            details={
                "client_request_id": client_request_id,
                "existing_source_intake_record_id": record.source_intake_record_id,
            },
        )


def _record_response(
    record: L3SourceIntakeRecord,
    *,
    response_status: str | None = None,
) -> dict[str, Any]:
    downstream_eligibility = _response_downstream_eligibility(record.downstream_eligibility_json)
    negative_invariants = _negative_invariants()
    return {
        "schema_id": SOURCE_INTAKE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": record.client_request_id,
        "server_time": _server_time(),
        "mode": SOURCE_INTAKE_MODE,
        "status": response_status or record.status,
        "message": "Layer 3 source intake record persisted without broad source expansion.",
        "source_gate": SOURCE_INTAKE_SOURCE_GATE,
        "source_intake_record_id": record.source_intake_record_id,
        "source_intake_mode": SOURCE_INTAKE_MODE,
        "source_family": record.source_family,
        "source_label": record.source_label,
        "source_identity": {
            "source_family": record.source_family,
            "source_label": record.source_label,
            "original_filename": record.original_filename,
            "content_size_bytes": record.content_size_bytes,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
        },
        "source_provenance": record.provenance_json or {},
        "storage_pointer": {
            "storage_ref": record.storage_ref,
            "storage_authority": "server_raw_storage",
            "content_addressed": True,
            "absolute_path_exposed": False,
        },
        "content_sha256": record.content_sha256,
        "metadata_hash": record.metadata_hash,
        "authority_basis_hash": record.authority_basis_hash,
        "downstream_eligibility": downstream_eligibility,
        "negative_invariants": negative_invariants,
        "next_allowed_actions": [
            "treat_source_intake_record_as_inventory_authority",
            "use_bounded_preview_for_operator_review_only",
            "define_later_freeze_before_rag_connector_package_or_rendered_source_controls",
        ],
    }


def _inventory_record_response(record: L3SourceIntakeRecord) -> dict[str, Any]:
    source_description = _bounded_inventory_description(record.source_description)
    return {
        "source_intake_record_id": record.source_intake_record_id,
        "client_request_id": record.client_request_id,
        "status": record.status,
        "source_intake_mode": SOURCE_INTAKE_MODE,
        "source_family": record.source_family,
        "source_label": record.source_label,
        "source_description": source_description,
        "source_description_truncated": (
            record.source_description is not None
            and len(record.source_description) > SOURCE_INTAKE_INVENTORY_DESCRIPTION_MAX_CHARS
        ),
        "original_filename": record.original_filename,
        "media_type": record.media_type,
        "content_sha256": record.content_sha256,
        "content_size_bytes": record.content_size_bytes,
        "metadata_hash": record.metadata_hash,
        "authority_basis_hash": record.authority_basis_hash,
        "source_identity": {
            "source_family": record.source_family,
            "source_label": record.source_label,
            "original_filename": record.original_filename,
            "content_size_bytes": record.content_size_bytes,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
        },
        "source_provenance": record.provenance_json or {},
        "storage_pointer": {
            "storage_ref": record.storage_ref,
            "storage_authority": "server_raw_storage",
            "content_addressed": True,
            "absolute_path_exposed": False,
        },
        "downstream_eligibility": _response_downstream_eligibility(record.downstream_eligibility_json),
        "freshness_timestamp": _iso_or_none(record.freshness_timestamp),
        "created_at": _iso_or_none(record.created_at),
        "updated_at": _iso_or_none(record.updated_at),
    }


def _bounded_inventory_description(source_description: str | None) -> str | None:
    if source_description is None:
        return None
    if len(source_description) <= SOURCE_INTAKE_INVENTORY_DESCRIPTION_MAX_CHARS:
        return source_description
    return source_description[:SOURCE_INTAKE_INVENTORY_DESCRIPTION_MAX_CHARS]


def _response_downstream_eligibility(stored: Mapping[str, Any] | None) -> dict[str, bool]:
    eligibility = dict(_downstream_eligibility())
    if stored:
        for key in (
            "source_intake_recorded",
            "eligible_for_source_inventory",
            "eligible_for_gate_b_material_admission",
            "eligible_for_rag_vector_index",
            "eligible_for_web_connector",
            "eligible_for_unbounded_runtime_db",
        ):
            if key in stored:
                eligibility[key] = bool(stored[key])
    eligibility["eligible_for_material_preview"] = True
    eligibility["material_preview_requires_later_freeze"] = False
    eligibility["eligible_for_gate_b_material_admission"] = True
    eligibility["gate_b_material_admission_requires_later_freeze"] = False
    return eligibility


def _downstream_eligibility() -> dict[str, bool]:
    return {
        "source_intake_recorded": True,
        "eligible_for_source_inventory": True,
        "eligible_for_material_preview": True,
        "material_preview_requires_later_freeze": False,
        "eligible_for_gate_b_material_admission": True,
        "gate_b_material_admission_requires_later_freeze": False,
        "eligible_for_rag_vector_index": False,
        "eligible_for_web_connector": False,
        "eligible_for_unbounded_runtime_db": False,
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "broad_file_upload_enabled": False,
        "local_directory_enabled": False,
        "web_connector_enabled": False,
        "rag_vector_index_enabled": False,
        "runtime_db_write_enabled": False,
        "unbounded_material_preview_enabled_for_operator_upload": False,
    }


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
