from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import L3SourceIntakeRecord


SOURCE_INTAKE_SCHEMA_ID = "layer3.source_intake_record.v1"
SOURCE_INTAKE_MODE = "operator_single_upload_source_intake"
SOURCE_INTAKE_SOURCE_GATE = "286_SOURCE_BREADTH_RUNTIME_ENTRY_FREEZE"
SOURCE_INTAKE_OPERATOR_DECISION = "record_operator_uploaded_source"
SOURCE_INTAKE_STATUS = "recorded"
SOURCE_INTAKE_SOURCE_FAMILY = "operator_uploaded_single_source"
SOURCE_INTAKE_STORAGE_SEGMENT = "layer3-source-intake"

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
    downstream_eligibility = record.downstream_eligibility_json or _downstream_eligibility()
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
            "define_later_freeze_before_material_preview_or_rag_use",
        ],
    }


def _downstream_eligibility() -> dict[str, bool]:
    return {
        "source_intake_recorded": True,
        "eligible_for_source_inventory": True,
        "eligible_for_material_preview": False,
        "material_preview_requires_later_freeze": True,
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
        "material_preview_enabled_for_operator_upload": False,
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
