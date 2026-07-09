from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import ConnectorRun, ConnectorRunTarget, L3ConnectorSourceIntakeRecord
from app.services.layer3_gate_b_state import (
    material_candidate_basis_from_preview as _gate_b_material_candidate_basis_from_preview,
    material_preview_hash as _gate_b_material_preview_hash,
)


CONNECTOR_SOURCE_INTAKE_SCHEMA_ID = "layer3.connector_source_intake_record.v1"
CONNECTOR_SOURCE_INTAKE_MODE = "connector_produced_source_intake"
CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION = "record_connector_produced_source"
CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY = "connector_produced_single_source"
CONNECTOR_SOURCE_INTAKE_STATUS = "recorded"
CONNECTOR_SOURCE_INTAKE_STORAGE_SEGMENT = "layer3-connector-source-intake"
CONNECTOR_SOURCE_INTAKE_INVENTORY_SCHEMA_ID = "layer3.connector_source_intake_inventory.v1"
CONNECTOR_SOURCE_INTAKE_INVENTORY_MODE = "connector_source_intake_inventory_read_only"
CONNECTOR_SOURCE_INTAKE_INVENTORY_DEFAULT_LIMIT = 50
CONNECTOR_SOURCE_INTAKE_INVENTORY_MAX_LIMIT = 100
CONNECTOR_SOURCE_INTAKE_PREVIEW_SCHEMA_ID = "layer3.connector_source_intake_material_preview.v1"
CONNECTOR_SOURCE_INTAKE_PREVIEW_MODE = "connector_source_intake_material_preview_read_only"
CONNECTOR_SOURCE_INTAKE_PREVIEW_MAX_CHARS = 4000
CONNECTOR_SOURCE_INTAKE_GATE_B_MODE = "connector_source_intake_gate_b_material_admission"
CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX = "mat-connector_source_intake_record-"
CONNECTOR_SOURCE_INTAKE_QUERY_BASIS = "connector_produced_source_intake"
CONNECTOR_SOURCE_INTAKE_SOURCE_GATE = "1366_SOURCE_ARTIFACT_ADMISSION_MAP_PHASE_3"

SERVER_AUTHORITY = (
    "Layer 3 connector source intake record owns connector-produced source "
    "identity, bytes/metadata hash, provenance, storage pointer, and downstream eligibility."
)

_CLIENT_REQUEST_RE = re.compile(r"^[A-Za-z0-9._:-]{1,255}$")
_LABEL_MAX_CHARS = 255
_DESCRIPTION_MAX_CHARS = 2000

_CONNECTOR_SOURCE_INTAKE_GATE_B_FORBIDDEN_FIELDS = {
    "absolute_path",
    "auth_policy",
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
    "raw_storage_ref",
    "storage_ref",
    "blob_ref",
    "vector_index",
    "web_connector",
}


class ConnectorSourceIntakeError(Exception):
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
            "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "connector-source-intake-error",
            "server_time": _server_time(),
            "mode": CONNECTOR_SOURCE_INTAKE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_connector_produced_source_intake(
    db: Session,
    *,
    client_request_id: str,
    connector_key: str,
    connector_run_id: str,
    connector_run_target_id: str,
    source_label: str,
    source_description: str | None = None,
    media_type: str | None = None,
    freshness_timestamp: datetime | str | None = None,
) -> dict[str, Any]:
    request_id = _normalise_required(client_request_id, "client_request_id")
    if not _CLIENT_REQUEST_RE.match(request_id):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_invalid_client_request_id",
            "client_request_id must be 1-255 characters using letters, numbers, dot, dash, underscore, or colon.",
            details={"client_request_id": request_id},
        )
    key = _normalise_required(connector_key, "connector_key")
    run_id = _normalise_required(connector_run_id, "connector_run_id")
    target_id = _normalise_required(connector_run_target_id, "connector_run_target_id")
    label = _normalise_required(source_label, "source_label")
    if len(label) > _LABEL_MAX_CHARS:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_label_too_long",
            "source_label must be 255 characters or fewer.",
            details={"source_label_length": len(label)},
        )
    description = str(source_description).strip() if source_description is not None else None
    if description is not None and len(description) > _DESCRIPTION_MAX_CHARS:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_description_too_long",
            "source_description must be 2000 characters or fewer.",
            details={"source_description_length": len(description)},
        )
    if media_type is None or not str(media_type).strip():
        raise ConnectorSourceIntakeError(
            "connector_source_intake_media_type_required",
            "Connector source intake requires an explicit text/csv media_type.",
            details={"media_type": media_type},
        )
    effective_media_type = str(media_type).strip()
    if len(effective_media_type) > 128:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_media_type_too_long",
            "media type must be 128 characters or fewer.",
            details={"media_type_length": len(effective_media_type)},
        )
    if not _is_csv_media_type(effective_media_type):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_media_type_not_admitted",
            "Only text/csv connector-produced source intake is admitted in this pilot.",
            details={"media_type": effective_media_type},
        )
    parsed_freshness = _parse_freshness_timestamp(freshness_timestamp)

    run = db.get(ConnectorRun, run_id)
    if run is None or run.connector_key != key:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_run_not_found",
            "No connector run exists for the requested connector source intake.",
            http_status=404,
            details={"connector_key": key, "connector_run_id": run_id},
        )
    target = db.get(ConnectorRunTarget, target_id)
    if target is None or target.connector_run_id != run_id:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_target_not_found",
            "No connector run target exists for the requested connector source intake.",
            http_status=404,
            details={"connector_run_id": run_id, "connector_run_target_id": target_id},
        )
    if target.status != "downloaded":
        raise ConnectorSourceIntakeError(
            "connector_source_intake_target_not_downloaded",
            "Connector source intake can only mint envelopes from downloaded raw blobs.",
            http_status=409,
            details={"connector_run_target_id": target_id, "status": target.status},
        )
    if target.public_read_confirmed is not True:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_public_read_not_confirmed",
            "Connector source intake requires public_read_confirmed before raw blob persistence.",
            http_status=409,
            details={
                "connector_run_target_id": target_id,
                "public_read_confirmed": bool(target.public_read_confirmed),
            },
        )

    original_filename = str(target.sciencebase_file_name or "").strip()
    if not original_filename or len(original_filename) > 255:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_unusable_file_name",
            "sciencebase_file_name must be present and 255 characters or fewer before connector source intake persists.",
            http_status=409,
            details={
                "connector_run_target_id": target_id,
                "sciencebase_file_name_length": len(original_filename),
            },
        )
    if not target.downloaded_sha256 or not target.raw_storage_ref:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_raw_blob_missing",
            "Connector run target must have downloaded_sha256 and raw_storage_ref before connector source intake persists.",
            http_status=409,
            details={"connector_run_target_id": target_id},
        )

    storage_path = _storage_path_from_ref(target.raw_storage_ref)
    if not storage_path.exists() or not storage_path.is_file():
        raise ConnectorSourceIntakeError(
            "connector_source_intake_raw_blob_missing",
            "The connector raw blob is not available for connector source intake.",
            http_status=404,
            details={"connector_run_target_id": target_id},
        )
    content_size_bytes, content_sha256 = _hash_file(storage_path)
    if content_size_bytes <= 0:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_raw_blob_empty",
            "Connector source intake rejects zero-byte raw blobs before persistence.",
            http_status=409,
            details={"connector_run_target_id": target_id, "content_size_bytes": content_size_bytes},
        )
    if content_sha256 != target.downloaded_sha256:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_hash_mismatch",
            "The connector raw blob hash does not match downloaded_sha256.",
            http_status=409,
            details={"connector_run_target_id": target_id},
        )

    metadata = {
        "client_request_id": request_id,
        "source_family": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
        "connector_key": key,
        "connector_run_id": run_id,
        "connector_run_target_id": target_id,
        "sciencebase_item_id": target.sciencebase_item_id,
        "sciencebase_download_uri": target.sciencebase_download_uri,
        "sciencebase_file_name": original_filename,
        "media_type": effective_media_type,
        "content_size_bytes": content_size_bytes,
        "content_sha256": content_sha256,
        "freshness_timestamp": _iso_or_none(parsed_freshness),
    }
    metadata_hash = _stable_hash(metadata)
    authority_basis = {
        "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
        "mode": CONNECTOR_SOURCE_INTAKE_MODE,
        "operator_decision": CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION,
        "client_request_id": request_id,
        "metadata_hash": metadata_hash,
        "content_sha256": content_sha256,
        "source_gate": CONNECTOR_SOURCE_INTAKE_SOURCE_GATE,
    }
    authority_basis_hash = _stable_hash(authority_basis)
    if _existing_record(db, request_id, authority_basis_hash) is not None:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_idempotency_conflict",
            "The connector source-intake idempotency key or authority basis conflicts with an existing record.",
            http_status=409,
            details={"client_request_id": request_id},
        )

    downstream_eligibility = _downstream_eligibility()
    provenance = {
        "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
        "mode": CONNECTOR_SOURCE_INTAKE_MODE,
        "operator_decision": CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION,
        "server_authority": SERVER_AUTHORITY,
        "source_gate": CONNECTOR_SOURCE_INTAKE_SOURCE_GATE,
        "connector_key": key,
        "connector_run_id": run_id,
        "connector_run_target_id": target_id,
        "content_sha256": content_sha256,
        "metadata_hash": metadata_hash,
        "freshness_timestamp": _iso_or_none(parsed_freshness),
    }
    record = L3ConnectorSourceIntakeRecord(
        client_request_id=request_id,
        operator_decision=CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION,
        source_family=CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
        source_label=label,
        source_description=description,
        original_filename=original_filename,
        media_type=effective_media_type,
        content_size_bytes=content_size_bytes,
        content_sha256=content_sha256,
        metadata_hash=metadata_hash,
        authority_basis_hash=authority_basis_hash,
        storage_ref=str(target.raw_storage_ref),
        freshness_timestamp=parsed_freshness,
        provenance_json=provenance,
        downstream_eligibility_json=downstream_eligibility,
        summary_json={
            "metadata": metadata,
            "authority_basis": authority_basis,
            "negative_invariants": _negative_invariants(),
        },
        status=CONNECTOR_SOURCE_INTAKE_STATUS,
        connector_key=key,
        connector_run_id=run_id,
        connector_run_target_id=target_id,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _existing_record(db, request_id, authority_basis_hash) is not None:
            raise ConnectorSourceIntakeError(
                "connector_source_intake_idempotency_conflict",
                "The connector source-intake idempotency key or authority basis conflicts with an existing record.",
                http_status=409,
                details={"client_request_id": request_id},
            ) from exc
        raise ConnectorSourceIntakeError(
            "connector_source_intake_record_conflict",
            "The connector source-intake record conflicts with an existing persisted authority row.",
            http_status=409,
            details={"client_request_id": request_id},
        ) from exc
    db.refresh(record)
    return _record_response(record)


def connector_source_intake_inventory(
    db: Session,
    *,
    limit: int = CONNECTOR_SOURCE_INTAKE_INVENTORY_DEFAULT_LIMIT,
    source_family: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    try:
        normalized_limit = int(limit)
    except (TypeError, ValueError) as exc:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_inventory_limit_invalid",
            "connector source-intake inventory limit must be an integer from 1 through 100.",
            details={"limit": limit},
        ) from exc
    if normalized_limit < 1 or normalized_limit > CONNECTOR_SOURCE_INTAKE_INVENTORY_MAX_LIMIT:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_inventory_limit_invalid",
            "connector source-intake inventory limit must be an integer from 1 through 100.",
            details={"limit": normalized_limit},
        )
    normalized_source_family = (source_family or CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY).strip()
    if normalized_source_family != CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_inventory_source_family_not_admitted",
            "connector source-intake inventory is limited to the approved connector-produced source family.",
            details={"received_source_family": normalized_source_family},
        )
    normalized_status = (status or CONNECTOR_SOURCE_INTAKE_STATUS).strip()
    if normalized_status != CONNECTOR_SOURCE_INTAKE_STATUS:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_inventory_status_not_admitted",
            "connector source-intake inventory is limited to recorded intake rows.",
            details={"received_status": normalized_status},
        )
    records = (
        db.query(L3ConnectorSourceIntakeRecord)
        .filter(L3ConnectorSourceIntakeRecord.source_family == normalized_source_family)
        .filter(L3ConnectorSourceIntakeRecord.status == normalized_status)
        .order_by(
            L3ConnectorSourceIntakeRecord.created_at.desc(),
            L3ConnectorSourceIntakeRecord.connector_source_intake_record_id.desc(),
        )
        .limit(normalized_limit)
        .all()
    )
    return {
        "schema_id": CONNECTOR_SOURCE_INTAKE_INVENTORY_SCHEMA_ID,
        "schema_version": 1,
        "request_id": "connector-source-intake-inventory",
        "server_time": _server_time(),
        "mode": CONNECTOR_SOURCE_INTAKE_INVENTORY_MODE,
        "status": "available",
        "message": "Layer 3 connector source intake inventory returned safe record metadata only.",
        "source_family": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
        "inventory_count": len(records),
        "limit": normalized_limit,
        "records": [_inventory_record_response(record) for record in records],
        "downstream_eligibility": _downstream_eligibility(),
        "negative_invariants": _negative_invariants(),
    }


def connector_source_intake_material_preview(
    db: Session,
    *,
    connector_source_intake_record_id: str,
    max_chars: int = CONNECTOR_SOURCE_INTAKE_PREVIEW_MAX_CHARS,
) -> dict[str, Any]:
    record_id = _normalise_required(
        connector_source_intake_record_id,
        "connector_source_intake_record_id",
    )
    try:
        normalized_max_chars = int(max_chars)
    except (TypeError, ValueError) as exc:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_preview_max_chars_invalid",
            "connector source-intake material preview max_chars must be an integer from 1 through 4000.",
            details={"max_chars": max_chars},
        ) from exc
    if normalized_max_chars < 1 or normalized_max_chars > CONNECTOR_SOURCE_INTAKE_PREVIEW_MAX_CHARS:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_preview_max_chars_invalid",
            "connector source-intake material preview max_chars must be an integer from 1 through 4000.",
            details={"max_chars": normalized_max_chars},
        )
    record = db.get(L3ConnectorSourceIntakeRecord, record_id)
    if record is None:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_preview_record_not_found",
            "No connector source-intake record exists for the requested preview.",
            http_status=404,
            details={"connector_source_intake_record_id": record_id},
    )
    _assert_record_admitted(record, context="preview")
    media_type = _normalise_media_type(record.media_type)
    if not _is_csv_media_type(media_type):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_preview_media_type_not_admitted",
            "Only bounded text/csv connector-produced source material preview is admitted.",
            details={"media_type": record.media_type},
        )
    storage_path = _storage_path_from_ref(record.storage_ref)
    if not storage_path.exists() or not storage_path.is_file():
        raise ConnectorSourceIntakeError(
            "connector_source_intake_preview_storage_missing",
            "The connector source-intake storage object is not available for preview.",
            http_status=404,
            details={"connector_source_intake_record_id": record.connector_source_intake_record_id},
        )
    preview_text, decoded_char_count, content_sha256 = _preview_text_and_hash(storage_path, normalized_max_chars)
    if content_sha256 != record.content_sha256:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_preview_hash_mismatch",
            "The connector source-intake storage object hash does not match the persisted authority row.",
            http_status=409,
            details={"connector_source_intake_record_id": record.connector_source_intake_record_id},
        )
    truncated = decoded_char_count > normalized_max_chars
    material_preview_id = _stable_hash(
        {
            "mode": CONNECTOR_SOURCE_INTAKE_PREVIEW_MODE,
            "connector_source_intake_record_id": record.connector_source_intake_record_id,
            "content_sha256": record.content_sha256,
            "max_chars": normalized_max_chars,
        }
    )[:36]
    source_ref = f"connector_source_intake_record:{record.connector_source_intake_record_id}"
    source_identity = _source_identity(record)
    source_provenance = {
        **(record.provenance_json or {}),
        "mode": CONNECTOR_SOURCE_INTAKE_GATE_B_MODE,
        "source_ref": source_ref,
    }
    material_candidate = {
        "candidate_id": f"{CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX}{record.connector_source_intake_record_id}",
        "source_class": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
        "source_ref": source_ref,
        "query_basis": CONNECTOR_SOURCE_INTAKE_QUERY_BASIS,
        "provenance_ref": (
            f"connector_source_intake_record:{record.connector_source_intake_record_id}:metadata:{record.metadata_hash}"
        ),
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
        "source_identity": source_identity,
        "source_provenance": source_provenance,
        "payload": {
            "connector_source_intake_record_id": record.connector_source_intake_record_id,
            "source_class": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
            "authority_basis_hash": record.authority_basis_hash,
            "connector_key": record.connector_key,
            "connector_run_id": record.connector_run_id,
            "connector_run_target_id": record.connector_run_target_id,
            "bounded_preview_char_count": len(preview_text),
            "preview_truncated": truncated,
        },
        "load_summary": {
            "loaded_records": 1,
            "failed_records": 0,
            "preview_material": True,
            "bounded_text_preview": True,
            "connector_source_intake_gate_b_material_admission": True,
        },
        "current_decision_state": "candidate",
    }
    material_preview_hash = _gate_b_material_preview_hash(
        [_gate_b_material_candidate_basis_from_preview(material_candidate)]
    )
    return {
        "schema_id": CONNECTOR_SOURCE_INTAKE_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "request_id": record.client_request_id,
        "server_time": _server_time(),
        "mode": CONNECTOR_SOURCE_INTAKE_PREVIEW_MODE,
        "status": "available",
        "message": "Layer 3 connector source-intake material preview returned bounded text from one connector raw blob.",
        "connector_source_intake_record_id": record.connector_source_intake_record_id,
        "material_preview_id": material_preview_id,
        "material_preview_hash": material_preview_hash,
        "material_candidate": material_candidate,
        "partial_retrieval": truncated,
        "downstream_eligibility": _downstream_eligibility(),
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [
            "submit_connector_source_intake_material_candidate_to_gate_b_decision",
            "define_later_freeze_before_media_widening_rag_connector_package_or_rendered_source_controls",
        ],
    }


def validate_connector_intake_gate_b_decision_basis(
    db: Session,
    *,
    candidate_id: str,
    decision_basis: Mapping[str, Any],
) -> None:
    blocked_fields = _gate_b_forbidden_decision_basis_fields(decision_basis)
    if blocked_fields:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_forbidden_field_not_admitted",
            "The connector source-intake Gate B decision basis includes a field from a deferred or forbidden runtime mode.",
            details={"blocked_fields": blocked_fields},
        )
    record_id = _connector_source_intake_record_id_from_candidate(candidate_id)
    if not record_id:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_candidate_id_not_admitted",
            "The Gate B material candidate is not an admitted connector source-intake record candidate.",
            details={"blocked_fields": ["candidate_decisions.candidate_id"]},
        )
    record = db.get(L3ConnectorSourceIntakeRecord, record_id)
    if record is None:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_record_not_found",
            "No connector source-intake authority row exists for the Gate B material candidate.",
            http_status=404,
            details={"connector_source_intake_record_id": record_id},
        )
    _assert_record_admitted(record, context="gate_b")
    media_type = _normalise_media_type(record.media_type)
    if not _is_csv_media_type(media_type):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_media_type_not_admitted",
            "Only bounded text/csv connector-produced source material is admitted for Gate B material selection.",
            details={"blocked_fields": ["candidate_decisions.decision_basis.media_type"]},
        )
    storage_path = _storage_path_from_ref(record.storage_ref)
    if not storage_path.exists() or not storage_path.is_file():
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_storage_missing",
            "The connector source-intake storage object is not available for Gate B material selection.",
            http_status=404,
            details={"connector_source_intake_record_id": record.connector_source_intake_record_id},
        )
    _, _, content_sha256 = _preview_text_and_hash(storage_path, 1)
    if content_sha256 != record.content_sha256:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_hash_mismatch",
            "The connector source-intake storage object hash does not match the persisted authority row.",
            http_status=409,
            details={"connector_source_intake_record_id": record.connector_source_intake_record_id},
        )
    expected_source_ref = f"connector_source_intake_record:{record.connector_source_intake_record_id}"
    if str(decision_basis.get("source_ref") or "").strip() != expected_source_ref:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_source_ref_mismatch",
            "The Gate B decision basis source_ref does not match the connector source-intake authority row.",
            http_status=409,
            details={"blocked_fields": ["candidate_decisions.decision_basis.source_ref"]},
        )
    if str(decision_basis.get("query_basis") or "").strip() != CONNECTOR_SOURCE_INTAKE_QUERY_BASIS:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_query_basis_mismatch",
            "The Gate B decision basis query_basis does not match the connector source-intake material preview.",
            http_status=409,
            details={"blocked_fields": ["candidate_decisions.decision_basis.query_basis"]},
        )
    expected_provenance_ref = (
        f"connector_source_intake_record:{record.connector_source_intake_record_id}:metadata:{record.metadata_hash}"
    )
    if str(decision_basis.get("provenance_ref") or "").strip() != expected_provenance_ref:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_provenance_ref_mismatch",
            "The Gate B decision basis provenance_ref does not match the connector source-intake authority row.",
            http_status=409,
            details={"blocked_fields": ["candidate_decisions.decision_basis.provenance_ref"]},
        )
    source_identity = decision_basis.get("source_identity")
    if not isinstance(source_identity, Mapping):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_source_identity_missing",
            "The Gate B decision basis must include source_identity from the connector source-intake material preview.",
            details={"blocked_fields": ["candidate_decisions.decision_basis.source_identity"]},
        )
    _assert_gate_b_basis_matches_record(
        source_identity,
        record,
        fields={
            "connector_source_intake_record_id": record.connector_source_intake_record_id,
            "source_family": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
        },
        field_prefix="candidate_decisions.decision_basis.source_identity",
        code="connector_source_intake_gate_b_source_identity_mismatch",
        message="The Gate B decision basis source_identity does not match the connector source-intake authority row.",
    )
    payload = decision_basis.get("payload")
    if not isinstance(payload, Mapping):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_payload_missing",
            "The Gate B decision basis must include the connector source-intake material preview payload.",
            details={"blocked_fields": ["candidate_decisions.decision_basis.payload"]},
        )
    _assert_gate_b_basis_matches_record(
        payload,
        record,
        fields={
            "connector_source_intake_record_id": record.connector_source_intake_record_id,
            "source_class": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
            "content_sha256": record.content_sha256,
            "metadata_hash": record.metadata_hash,
            "authority_basis_hash": record.authority_basis_hash,
            "connector_key": record.connector_key,
            "connector_run_id": record.connector_run_id,
            "connector_run_target_id": record.connector_run_target_id,
        },
        field_prefix="candidate_decisions.decision_basis.payload",
        code="connector_source_intake_gate_b_payload_mismatch",
        message="The Gate B decision basis payload does not match the connector source-intake authority row.",
    )


def _normalise_required(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_required_field_missing",
            "A required connector source-intake field is missing or empty.",
            details={"field": field},
        )
    return text


def _parse_freshness_timestamp(raw_value: datetime | str | None) -> datetime | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        parsed = raw_value
    else:
        try:
            parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ConnectorSourceIntakeError(
                "connector_source_intake_invalid_freshness_timestamp",
                "freshness_timestamp must be an ISO-8601 datetime.",
                details={"freshness_timestamp": raw_value},
            ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _storage_path_from_ref(storage_ref: str) -> Path:
    raw_root = Path(settings.connector_raw_dir).resolve()
    candidate = Path(str(storage_ref or "").strip())
    if not candidate.is_absolute():
        candidate = raw_root / candidate
    resolved = candidate.resolve()
    if resolved != raw_root and raw_root not in resolved.parents:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_storage_ref_not_admitted",
            "The connector source-intake storage reference resolves outside the connector raw storage segment.",
            details={"storage_ref": storage_ref},
        )
    return candidate


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


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


def _is_csv_media_type(media_type: str | None) -> bool:
    return _normalise_media_type(media_type) == "text/csv"


def _normalise_media_type(media_type: str | None) -> str:
    return str(media_type or "").split(";", 1)[0].strip().lower()


def _existing_record(
    db: Session,
    client_request_id: str,
    authority_basis_hash: str,
) -> L3ConnectorSourceIntakeRecord | None:
    return (
        db.query(L3ConnectorSourceIntakeRecord)
        .filter(
            or_(
                L3ConnectorSourceIntakeRecord.client_request_id == client_request_id,
                L3ConnectorSourceIntakeRecord.authority_basis_hash == authority_basis_hash,
            )
        )
        .one_or_none()
    )


def _record_response(record: L3ConnectorSourceIntakeRecord) -> dict[str, Any]:
    return {
        "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": record.client_request_id,
        "server_time": _server_time(),
        "mode": CONNECTOR_SOURCE_INTAKE_MODE,
        "status": record.status,
        "connector_source_intake_record_id": record.connector_source_intake_record_id,
        "source_family": record.source_family,
        "connector_key": record.connector_key,
        "connector_run_id": record.connector_run_id,
        "connector_run_target_id": record.connector_run_target_id,
        "content_sha256": record.content_sha256,
        "metadata_hash": record.metadata_hash,
        "authority_basis_hash": record.authority_basis_hash,
        "downstream_eligibility": record.downstream_eligibility_json,
        "negative_invariants": _negative_invariants(),
    }


def _inventory_record_response(record: L3ConnectorSourceIntakeRecord) -> dict[str, Any]:
    return {
        "connector_source_intake_record_id": record.connector_source_intake_record_id,
        "client_request_id": record.client_request_id,
        "source_family": record.source_family,
        "source_label": record.source_label,
        "source_description": (record.source_description or "")[:512],
        "original_filename": record.original_filename,
        "media_type": record.media_type,
        "content_size_bytes": record.content_size_bytes,
        "content_sha256": record.content_sha256,
        "metadata_hash": record.metadata_hash,
        "authority_basis_hash": record.authority_basis_hash,
        "connector_key": record.connector_key,
        "connector_run_id": record.connector_run_id,
        "connector_run_target_id": record.connector_run_target_id,
        "status": record.status,
        "created_at": _iso_or_none(record.created_at),
        "source_identity": _source_identity(record),
        "preview_eligible": _is_csv_media_type(record.media_type),
    }


def _source_identity(record: L3ConnectorSourceIntakeRecord) -> dict[str, Any]:
    return {
        "connector_source_intake_record_id": record.connector_source_intake_record_id,
        "source_family": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
        "content_sha256": record.content_sha256,
        "metadata_hash": record.metadata_hash,
        "connector_key": record.connector_key,
        "connector_run_id": record.connector_run_id,
        "connector_run_target_id": record.connector_run_target_id,
    }


def _downstream_eligibility() -> dict[str, Any]:
    return {
        "gate_b_material_admission_enabled": True,
        "gate_b_mode": CONNECTOR_SOURCE_INTAKE_GATE_B_MODE,
        "csv_only_pilot": True,
        "media_type_widening_deferred": True,
        "support_matrix_capability_added": False,
        "new_http_route_added": False,
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "operator_source_intake_table_modified": False,
        "generic_source_classes_widened": False,
        "support_matrix_changed": False,
        "new_http_route_added": False,
        "media_type_gate_widened": False,
        "absolute_path_exposed": False,
    }


def _assert_record_admitted(record: L3ConnectorSourceIntakeRecord, *, context: str) -> None:
    if (
        record.status != CONNECTOR_SOURCE_INTAKE_STATUS
        or record.source_family != CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
    ):
        raise ConnectorSourceIntakeError(
            f"connector_source_intake_{context}_record_not_admitted",
            "Only recorded connector-produced single-source rows are admitted.",
            http_status=409,
            details={
                "connector_source_intake_record_id": record.connector_source_intake_record_id,
                "status": record.status,
                "source_family": record.source_family,
            },
        )


def _connector_source_intake_record_id_from_candidate(candidate_id: str) -> str | None:
    value = str(candidate_id or "").strip()
    if not value.startswith(CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX):
        return None
    record_id = value[len(CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX) :].strip()
    return record_id or None


def _gate_b_forbidden_decision_basis_fields(
    value: Any,
    prefix: str = "candidate_decisions.decision_basis",
) -> list[str]:
    blocked: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, nested_value in value.items():
            key = str(raw_key)
            field_path = f"{prefix}.{key}"
            if key in _CONNECTOR_SOURCE_INTAKE_GATE_B_FORBIDDEN_FIELDS:
                blocked.append(field_path)
            blocked.extend(_gate_b_forbidden_decision_basis_fields(nested_value, field_path))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            blocked.extend(_gate_b_forbidden_decision_basis_fields(nested_value, f"{prefix}.{index}"))
    return sorted(set(blocked))


def _assert_gate_b_basis_matches_record(
    value: Mapping[str, Any],
    record: L3ConnectorSourceIntakeRecord,
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
        raise ConnectorSourceIntakeError(
            code,
            message,
            http_status=409,
            details={
                "connector_source_intake_record_id": record.connector_source_intake_record_id,
                "blocked_fields": mismatched_fields,
            },
        )


def _stable_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
