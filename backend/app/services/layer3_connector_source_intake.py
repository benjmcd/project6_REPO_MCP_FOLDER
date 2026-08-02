from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import ConnectorRun, ConnectorRunTarget, L3ConnectorSourceIntakeRecord
from app.services.layer3_gate_b_state import (
    material_candidate_basis_from_preview as _gate_b_material_candidate_basis_from_preview,
    material_preview_hash as _gate_b_material_preview_hash,
)
from app.services.raw_storage_handles import (
    StableRawStorageError,
    hash_locked_raw_file,
)


CONNECTOR_SOURCE_INTAKE_SCHEMA_ID = "layer3.connector_source_intake_record.v1"
CONNECTOR_SOURCE_INTAKE_MODE = "connector_produced_source_intake"
CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION = "record_connector_produced_source"
CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY = "connector_produced_single_source"
STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS = "strict_sciencebase_connector_single_source"
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
CONNECTOR_ORIGIN_RECEIPT_HASH_KEY = "connector_origin_receipt_hash"
STRICT_SCIENCEBASE_SOURCE_LABEL = "ScienceBase MCS frozen raw artifact"
STRICT_SCIENCEBASE_SOURCE_DESCRIPTION = (
    "Strict Phase-A raw CSV artifact; no semantic ingestion."
)
STRICT_SCIENCEBASE_ITEM_ID = "63d1a3c6d34e06fef15006be"
STRICT_SCIENCEBASE_FILE_NAME = "mcs2023-germa_salient.csv"

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


def _normalise_gate_b_decision_basis_key(key: str) -> str:
    value = str(key).strip()
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", value)
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return value.replace("-", "_").casefold()


_CONNECTOR_SOURCE_INTAKE_GATE_B_FORBIDDEN_KEYS = {
    _normalise_gate_b_decision_basis_key(field)
    for field in _CONNECTOR_SOURCE_INTAKE_GATE_B_FORBIDDEN_FIELDS
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
    """Record connector-produced source intake under the current idempotency contract.

    The conflict axes are client_request_id and authority_basis_hash.
    connector_run_target_id is not unique; the same target may produce distinct
    records when a future caller supplies a distinct client_request_id and
    therefore a distinct authority_basis_hash.
    """
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
    if (
        _server_owned_strict_sciencebase_authority(
            db,
            connector_run_target_id=target_id,
        )
        is not None
    ):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_reserved_strict_lane",
            "Reserved strict ScienceBase targets require server-staged intake.",
            http_status=409,
            details={"connector_run_target_id": target_id},
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


def _stage_strict_sciencebase_source_intake(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
) -> L3ConnectorSourceIntakeRecord:
    """Stage one server-owned strict ScienceBase intake row without commit."""

    expected_item_id = "63d1a3c6d34e06fef15006be"
    expected_file_name = "mcs2023-germa_salient.csv"
    expected_artifact_key = (
        f"sciencebase:{expected_item_id}:{expected_file_name}"
    )
    if (
        run.connector_key != "sciencebase_mcs"
        or run.source_mode != "strict_live_egress"
        or run.status != "running"
        or target.connector_run_id != run.connector_run_id
        or target.sciencebase_item_id != expected_item_id
        or target.sciencebase_file_name != expected_file_name
        or target.sciencebase_item_url is not None
        or target.sciencebase_download_uri is not None
        or target.artifact_surface != "files"
        or target.source_artifact_key != expected_artifact_key
        or target.status != "downloaded"
        or target.public_read_confirmed is not True
    ):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_strict_authority_invalid",
            "Strict ScienceBase intake requires exact server-owned run and target authority.",
            http_status=409,
        )
    existing_count = (
        db.query(L3ConnectorSourceIntakeRecord)
        .filter(
            L3ConnectorSourceIntakeRecord.connector_run_id
            == run.connector_run_id,
            L3ConnectorSourceIntakeRecord.connector_run_target_id
            == target.connector_run_target_id,
        )
        .count()
    )
    if existing_count:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_strict_cardinality_conflict",
            "Strict ScienceBase intake already exists for this run and target.",
            http_status=409,
            details={
                "connector_run_id": run.connector_run_id,
                "connector_run_target_id": target.connector_run_target_id,
                "existing_count": existing_count,
            },
        )
    if not target.downloaded_sha256 or not target.raw_storage_ref:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_strict_raw_blob_missing",
            "Strict ScienceBase intake requires admitted raw hash and storage authority.",
            http_status=409,
        )
    storage_path = _storage_path_from_ref(target.raw_storage_ref)
    raw_root = Path(os.path.abspath(settings.connector_raw_dir))
    resolved_path = Path(os.path.abspath(storage_path))
    expected_hash = str(target.downloaded_sha256)
    if (
        not storage_path.is_file()
        or resolved_path.parent != raw_root / "sha256"
        or resolved_path.name != f"{expected_hash}.csv"
    ):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_strict_storage_ref_invalid",
            "Strict ScienceBase intake requires the canonical content-addressed raw path.",
            http_status=409,
        )
    content_size_bytes, content_sha256 = _hash_file(resolved_path)
    if (
        content_size_bytes <= 0
        or content_sha256 != expected_hash
    ):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_strict_hash_mismatch",
            "Strict ScienceBase intake raw bytes contradict target authority.",
            http_status=409,
        )

    values = _strict_sciencebase_intake_values(
        connector_key=run.connector_key,
        connector_run_id=run.connector_run_id,
        connector_run_target_id=target.connector_run_target_id,
        raw_storage_ref=str(resolved_path),
        freshness_timestamp=target.downloaded_at,
        content_size_bytes=content_size_bytes,
        content_sha256=content_sha256,
        connector_origin_receipt_hash=None,
    )
    record = L3ConnectorSourceIntakeRecord(**values)
    db.add(record)
    db.flush()
    return record


def _strict_sciencebase_intake_values(
    *,
    connector_key: str,
    connector_run_id: str,
    connector_run_target_id: str,
    raw_storage_ref: str,
    freshness_timestamp: datetime | None,
    content_size_bytes: int,
    content_sha256: str,
    connector_origin_receipt_hash: str | None,
) -> dict[str, Any]:
    """Build deterministic strict ScienceBase intake values without I/O."""

    client_request_id = (
        f"strict-sciencebase:{connector_run_id}:"
        f"{connector_run_target_id}"
    )
    receipt_hash: str | None = None
    if connector_origin_receipt_hash is not None:
        receipt_hash = str(connector_origin_receipt_hash)
        if not re.fullmatch(r"[0-9a-f]{64}", receipt_hash):
            raise ConnectorSourceIntakeError(
                "connector_source_intake_origin_projection_invalid",
                "Strict ScienceBase origin projection requires one canonical receipt hash.",
                http_status=409,
            )
    metadata = {
        "client_request_id": client_request_id,
        "source_family": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
        "connector_key": connector_key,
        "connector_run_id": connector_run_id,
        "connector_run_target_id": connector_run_target_id,
        "sciencebase_item_id": STRICT_SCIENCEBASE_ITEM_ID,
        "sciencebase_file_name": STRICT_SCIENCEBASE_FILE_NAME,
        "artifact_surface": "files",
        "media_type": "text/csv",
        "content_size_bytes": content_size_bytes,
        "content_sha256": content_sha256,
    }
    if receipt_hash is not None:
        metadata[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY] = receipt_hash
    metadata_hash = _stable_hash(metadata)
    authority_basis = {
        "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
        "mode": CONNECTOR_SOURCE_INTAKE_MODE,
        "operator_decision": CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION,
        "client_request_id": client_request_id,
        "metadata_hash": metadata_hash,
        "content_sha256": content_sha256,
        "source_gate": CONNECTOR_SOURCE_INTAKE_SOURCE_GATE,
    }
    if receipt_hash is not None:
        authority_basis["connector_run_target_id"] = (
            connector_run_target_id
        )
        authority_basis[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY] = receipt_hash
    authority_basis_hash = _stable_hash(authority_basis)
    provenance = {
        "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
        "mode": CONNECTOR_SOURCE_INTAKE_MODE,
        "operator_decision": CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION,
        "server_authority": SERVER_AUTHORITY,
        "source_gate": CONNECTOR_SOURCE_INTAKE_SOURCE_GATE,
        "connector_key": connector_key,
        "connector_run_id": connector_run_id,
        "connector_run_target_id": connector_run_target_id,
        "content_sha256": content_sha256,
        "metadata_hash": metadata_hash,
    }
    if receipt_hash is not None:
        provenance[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY] = receipt_hash
    return {
        "client_request_id": client_request_id,
        "operator_decision": CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION,
        "source_family": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
        "source_label": STRICT_SCIENCEBASE_SOURCE_LABEL,
        "source_description": STRICT_SCIENCEBASE_SOURCE_DESCRIPTION,
        "original_filename": STRICT_SCIENCEBASE_FILE_NAME,
        "media_type": "text/csv",
        "content_size_bytes": content_size_bytes,
        "content_sha256": content_sha256,
        "metadata_hash": metadata_hash,
        "authority_basis_hash": authority_basis_hash,
        "storage_ref": raw_storage_ref,
        "freshness_timestamp": freshness_timestamp,
        "provenance_json": provenance,
        "downstream_eligibility_json": _downstream_eligibility(),
        "summary_json": {
            "metadata": metadata,
            "authority_basis": authority_basis,
            "negative_invariants": _negative_invariants(),
        },
        "status": CONNECTOR_SOURCE_INTAKE_STATUS,
        "connector_key": connector_key,
        "connector_run_id": connector_run_id,
        "connector_run_target_id": connector_run_target_id,
    }


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
    origin_projection = _assert_record_admitted(
        db,
        record,
        context="preview",
    )
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
    gate_b_source_class = (
        STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
        if origin_projection is not None
        else CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
    )
    source_identity = _source_identity(record)
    if origin_projection is not None:
        source_identity[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY] = (
            origin_projection[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY]
        )
    source_provenance = {
        **(record.provenance_json or {}),
        "mode": CONNECTOR_SOURCE_INTAKE_GATE_B_MODE,
        "source_ref": source_ref,
    }
    payload = {
        "connector_source_intake_record_id": (
            record.connector_source_intake_record_id
        ),
        "source_class": gate_b_source_class,
        "content_sha256": record.content_sha256,
        "metadata_hash": record.metadata_hash,
        "authority_basis_hash": record.authority_basis_hash,
        "connector_key": record.connector_key,
        "connector_run_id": record.connector_run_id,
        "connector_run_target_id": record.connector_run_target_id,
        "bounded_preview_char_count": len(preview_text),
        "preview_truncated": truncated,
    }
    if origin_projection is not None:
        payload[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY] = (
            origin_projection[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY]
        )
    load_summary = {
        "loaded_records": 1,
        "failed_records": 0,
        "preview_material": True,
        "bounded_text_preview": True,
        "connector_source_intake_gate_b_material_admission": True,
    }
    material_candidate = {
        "candidate_id": f"{CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX}{record.connector_source_intake_record_id}",
        "source_class": gate_b_source_class,
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
        "payload": payload,
        "load_summary": load_summary,
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
) -> str:
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
    origin_projection = _assert_record_admitted(
        db,
        record,
        context="gate_b",
    )
    if origin_projection is not None:
        mismatched_surfaces = []
        for surface in (
            "source_identity",
            "source_provenance",
            "payload",
        ):
            surface_value = decision_basis.get(surface)
            if (
                not isinstance(surface_value, Mapping)
                or surface_value.get("connector_run_target_id")
                != origin_projection["connector_run_target_id"]
                or surface_value.get(CONNECTOR_ORIGIN_RECEIPT_HASH_KEY)
                != origin_projection[CONNECTOR_ORIGIN_RECEIPT_HASH_KEY]
            ):
                mismatched_surfaces.append(
                    f"candidate_decisions.decision_basis.{surface}"
                )
        if mismatched_surfaces:
            raise ConnectorSourceIntakeError(
                "connector_source_intake_gate_b_origin_projection_mismatch",
                "Gate B requires the exact strict ScienceBase origin projection on every candidate surface.",
                http_status=409,
                details={"blocked_fields": mismatched_surfaces},
            )
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
            "source_class": (
                STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
                if origin_projection is not None
                else CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
            ),
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
    canonical_candidate = connector_source_intake_material_preview(
        db,
        connector_source_intake_record_id=(
            record.connector_source_intake_record_id
        ),
    )["material_candidate"]
    expected_decision_basis = {
        key: canonical_candidate[key]
        for key in (
            "source_ref",
            "query_basis",
            "provenance_ref",
            "source_identity",
            "source_provenance",
            "payload",
            "load_summary",
        )
    }
    if "connector_target" in decision_basis:
        expected_decision_basis["connector_target"] = {
            "connector_run_target_id": (
                record.connector_run_target_id
            ),
            "connector_key": record.connector_key,
        }
    if dict(decision_basis) != expected_decision_basis:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_basis_mismatch",
            "Gate B requires the exact server-derived material-candidate basis.",
            http_status=409,
            details={
                "connector_source_intake_record_id": (
                    record.connector_source_intake_record_id
                ),
            },
        )
    return (
        STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
        if origin_projection is not None
        else CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
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
    raw_root = Path(os.path.abspath(settings.connector_raw_dir))
    candidate = Path(str(storage_ref or "").strip())
    if not candidate.is_absolute():
        candidate = raw_root / candidate
    candidate = Path(os.path.abspath(candidate))
    if candidate != raw_root and raw_root not in candidate.parents:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_storage_ref_not_admitted",
            "The connector source-intake storage reference resolves outside the connector raw storage segment.",
            details={"storage_ref": storage_ref},
        )
    return candidate


def _hash_file(path: Path) -> tuple[int, str]:
    try:
        size, digest, _ = hash_locked_raw_file(
            Path(settings.connector_raw_dir),
            path,
        )
    except StableRawStorageError as exc:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_raw_blob_changed",
            "The connector raw blob or its storage path changed during verification.",
            http_status=409,
        ) from exc
    return size, digest


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


def _server_owned_strict_sciencebase_authority(
    db: Session,
    *,
    connector_run_target_id: str,
) -> Mapping[str, Any] | None:
    target_id = str(connector_run_target_id or "").strip()
    if not target_id:
        return None
    statement = (
        select(
            ConnectorRun.connector_run_id.label("run_id"),
            ConnectorRun.connector_key.label("run_connector_key"),
            ConnectorRun.source_mode.label("run_source_mode"),
            ConnectorRun.status.label("run_status"),
            ConnectorRunTarget.connector_run_target_id.label("target_id"),
            ConnectorRunTarget.connector_run_id.label("target_run_id"),
            ConnectorRunTarget.sciencebase_item_id,
            ConnectorRunTarget.sciencebase_item_url,
            ConnectorRunTarget.sciencebase_file_name,
            ConnectorRunTarget.sciencebase_download_uri,
            ConnectorRunTarget.artifact_surface,
            ConnectorRunTarget.artifact_locator_type,
            ConnectorRunTarget.source_artifact_key,
            ConnectorRunTarget.status.label("target_status"),
            ConnectorRunTarget.public_read_confirmed,
            ConnectorRunTarget.source_reference_json,
        )
        .select_from(ConnectorRunTarget)
        .join(
            ConnectorRun,
            ConnectorRun.connector_run_id
            == ConnectorRunTarget.connector_run_id,
        )
        .where(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .limit(2)
    )
    with db.no_autoflush:
        rows = list(db.execute(statement).mappings().all())
    if len(rows) != 1:
        return None
    authority = rows[0]
    from app.services import layer3_origin_continuity as origin

    source_reference = authority["source_reference_json"]
    receipt_present = (
        isinstance(source_reference, Mapping)
        and origin.ORIGIN_RECEIPT_STORAGE_KEY in source_reference
    )
    reserved = (
        authority["run_connector_key"] == "sciencebase_mcs"
        and authority["run_source_mode"] == "strict_live_egress"
    ) or receipt_present
    if not reserved:
        return None
    expected_artifact_key = (
        f"sciencebase:{STRICT_SCIENCEBASE_ITEM_ID}:"
        f"{STRICT_SCIENCEBASE_FILE_NAME}"
    )
    if (
        authority["run_connector_key"] != "sciencebase_mcs"
        or authority["run_source_mode"] != "strict_live_egress"
        or authority["run_status"] not in {"running", "completed"}
        or authority["target_run_id"] != authority["run_id"]
        or authority["sciencebase_item_id"]
        != STRICT_SCIENCEBASE_ITEM_ID
        or authority["sciencebase_item_url"] is not None
        or authority["sciencebase_file_name"]
        != STRICT_SCIENCEBASE_FILE_NAME
        or authority["sciencebase_download_uri"] is not None
        or authority["artifact_surface"] != "files"
        or authority["artifact_locator_type"]
        != "downloadUri_hash_only"
        or authority["source_artifact_key"] != expected_artifact_key
        or authority["target_status"] != "downloaded"
        or authority["public_read_confirmed"] is not True
    ):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_reserved_authority_invalid",
            "Reserved ScienceBase authority contradicts its strict server-owned lane.",
            http_status=409,
            details={"connector_run_target_id": target_id},
        )
    return dict(authority)


def _assert_record_admitted(
    db: Session,
    record: L3ConnectorSourceIntakeRecord,
    *,
    context: str,
) -> dict[str, str] | None:
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
    authority = _server_owned_strict_sciencebase_authority(
        db,
        connector_run_target_id=str(
            record.connector_run_target_id or ""
        ),
    )
    strict_shape = _strict_sciencebase_record_shape(record)
    if authority is None:
        provenance = (
            record.provenance_json
            if isinstance(record.provenance_json, Mapping)
            else {}
        )
        summary = (
            record.summary_json
            if isinstance(record.summary_json, Mapping)
            else {}
        )
        metadata = summary.get("metadata")
        authority_basis = summary.get("authority_basis")
        projected_origin_signal = any(
            isinstance(surface, Mapping)
            and CONNECTOR_ORIGIN_RECEIPT_HASH_KEY in surface
            for surface in (
                provenance,
                metadata,
                authority_basis,
            )
        )
        if strict_shape != "generic" or projected_origin_signal:
            raise ConnectorSourceIntakeError(
                f"connector_source_intake_{context}_reserved_authority_invalid",
                "Reserved ScienceBase intake lacks its server-owned run-target authority.",
                http_status=409,
                details={
                    "connector_source_intake_record_id": (
                        record.connector_source_intake_record_id
                    ),
                },
            )
        with db.no_autoflush:
            generic_run = db.get(
                ConnectorRun,
                str(record.connector_run_id or ""),
            )
            generic_target = db.get(
                ConnectorRunTarget,
                str(record.connector_run_target_id or ""),
            )
        if (
            generic_run is None
            or generic_target is None
            or generic_target.connector_run_id
            != record.connector_run_id
            or generic_run.connector_key != record.connector_key
        ):
            raise ConnectorSourceIntakeError(
                f"connector_source_intake_{context}_record_not_admitted",
                "Connector source intake lacks matching server-owned run-target authority.",
                http_status=409,
                details={
                    "connector_source_intake_record_id": (
                        record.connector_source_intake_record_id
                    ),
                },
            )
        return None
    if (
        strict_shape != "strict"
        or record.connector_run_id != authority["run_id"]
        or record.connector_run_target_id != authority["target_id"]
        or record.connector_key != authority["run_connector_key"]
    ):
        raise ConnectorSourceIntakeError(
            f"connector_source_intake_{context}_strict_shape_invalid",
            "Reserved ScienceBase intake contradicts the frozen strict contract.",
            http_status=409,
            details={
                "connector_source_intake_record_id": (
                    record.connector_source_intake_record_id
                ),
            },
        )
    provenance = (
        record.provenance_json
        if isinstance(record.provenance_json, Mapping)
        else {}
    )
    summary = (
        record.summary_json
        if isinstance(record.summary_json, Mapping)
        else {}
    )
    metadata = summary.get("metadata")
    authority_basis = summary.get("authority_basis")
    metadata_receipt_hash = (
        metadata.get(CONNECTOR_ORIGIN_RECEIPT_HASH_KEY)
        if isinstance(metadata, Mapping)
        else None
    )
    authority_receipt_hash = (
        authority_basis.get(CONNECTOR_ORIGIN_RECEIPT_HASH_KEY)
        if isinstance(authority_basis, Mapping)
        else None
    )
    provenance_receipt_hash = provenance.get(
        CONNECTOR_ORIGIN_RECEIPT_HASH_KEY
    )
    authority_target_id = (
        authority_basis.get("connector_run_target_id")
        if isinstance(authority_basis, Mapping)
        else None
    )
    receipt_hash: str | None
    if (
        metadata_receipt_hash is None
        and authority_receipt_hash is None
        and provenance_receipt_hash is None
    ):
        receipt_hash = None
    elif (
        metadata_receipt_hash
        == authority_receipt_hash
        == provenance_receipt_hash
        and re.fullmatch(
            r"[0-9a-f]{64}",
            str(metadata_receipt_hash or ""),
        )
        and authority_target_id == record.connector_run_target_id
    ):
        receipt_hash = str(metadata_receipt_hash)
    else:
        receipt_hash = ""
    try:
        expected_values = _strict_sciencebase_intake_values(
            connector_key=str(record.connector_key),
            connector_run_id=str(record.connector_run_id),
            connector_run_target_id=str(record.connector_run_target_id),
            raw_storage_ref=str(record.storage_ref),
            freshness_timestamp=record.freshness_timestamp,
            content_size_bytes=int(record.content_size_bytes),
            content_sha256=str(record.content_sha256),
            connector_origin_receipt_hash=(
                receipt_hash if receipt_hash else None
            ),
        )
        values_match = all(
            getattr(record, field) == expected
            for field, expected in expected_values.items()
        )
    except (TypeError, ValueError, ConnectorSourceIntakeError):
        values_match = False
    if (
        not isinstance(metadata, Mapping)
        or not isinstance(authority_basis, Mapping)
        or not values_match
        or not receipt_hash
    ):
        raise ConnectorSourceIntakeError(
            f"connector_source_intake_{context}_origin_receipt_missing",
            "Strict ScienceBase intake requires one exact top-level target/hash projection.",
            http_status=409,
            details={
                "connector_source_intake_record_id": (
                    record.connector_source_intake_record_id
                ),
            },
        )
    from app.services import layer3_origin_continuity as origin

    try:
        canonical_projection = (
            origin.verified_connector_origin_projection(
                db,
                connector_run_target_id=str(
                    record.connector_run_target_id
                ),
            )
        )
    except origin.Layer3OriginContinuityError:
        raise ConnectorSourceIntakeError(
            f"connector_source_intake_{context}_origin_receipt_missing",
            "Strict ScienceBase intake lacks verified origin continuity.",
            http_status=409,
            details={
                "connector_source_intake_record_id": (
                    record.connector_source_intake_record_id
                ),
            },
        ) from None
    expected_projection = {
        "connector_run_target_id": str(
            record.connector_run_target_id
        ),
        "connector_origin_receipt_hash": receipt_hash,
    }
    if (
        set(canonical_projection) != set(expected_projection)
        or canonical_projection != expected_projection
    ):
        raise ConnectorSourceIntakeError(
            f"connector_source_intake_{context}_origin_receipt_missing",
            "Strict ScienceBase intake lacks verified origin continuity.",
            http_status=409,
            details={
                "connector_source_intake_record_id": (
                    record.connector_source_intake_record_id
                ),
            },
        )
    return canonical_projection


def _strict_sciencebase_record_shape(
    record: L3ConnectorSourceIntakeRecord,
) -> str:
    run_id = str(record.connector_run_id or "")
    target_id = str(record.connector_run_target_id or "")
    request_id = str(record.client_request_id or "")
    expected_request_id = (
        f"strict-sciencebase:{run_id}:{target_id}"
    )
    strict_signals = (
        request_id.startswith("strict-sciencebase:")
        or record.source_label == STRICT_SCIENCEBASE_SOURCE_LABEL
        or record.source_description
        == STRICT_SCIENCEBASE_SOURCE_DESCRIPTION
    )
    if not strict_signals:
        return "generic"
    if (
        record.connector_key != "sciencebase_mcs"
        or request_id != expected_request_id
        or record.source_label != STRICT_SCIENCEBASE_SOURCE_LABEL
        or record.source_description
        != STRICT_SCIENCEBASE_SOURCE_DESCRIPTION
        or record.original_filename != STRICT_SCIENCEBASE_FILE_NAME
    ):
        return "strict_invalid"
    return "strict"


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
            if _normalise_gate_b_decision_basis_key(key) in _CONNECTOR_SOURCE_INTAKE_GATE_B_FORBIDDEN_KEYS:
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
