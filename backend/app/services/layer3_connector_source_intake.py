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

ADOPTED_EXTERNAL_SOURCE_INTAKE_MODE = "adopted_external_source_intake"
ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION = "record_adopted_external_source"
ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY = "adopted_external_single_source"
ADOPTED_EXTERNAL_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX = (
    "mat-adopted_source_intake_record-"
)
ADOPTED_EXTERNAL_SOURCE_INTAKE_QUERY_BASIS = "adopted_external_source_intake"
ADOPTED_EXTERNAL_CONNECTOR_KEY = "sciencebase_adopted_external"
ADOPTED_EXTERNAL_SOURCE_MODE = "adopted_external_artifact"
ADOPTED_EXTERNAL_ITEM_ID = "63d1a3c6d34e06fef15006be"
ADOPTED_EXTERNAL_DOI = "10.5066/P9WCYUI6"
ADOPTED_EXTERNAL_FILENAME = "mcs2023-germa_salient.csv"
ADOPTED_EXTERNAL_DOWNLOAD_URI = (
    "https://www.sciencebase.gov/catalog/file/get/"
    "63d1a3c6d34e06fef15006be?f=__disk__7e%2F49%2Fe8%2F"
    "7e49e8a4a53eb2219837f97defb22a25a286cdbc"
)
ADOPTED_EXTERNAL_ACQUIRED_AT = "2026-08-30T17:05:58.459Z"
ADOPTED_EXTERNAL_ACQUISITION_GIT_REF = "codex/sb-instrument-acq@b8839048"
ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH = (
    "acquisitions/20260830T170556947Z/acquisition-record.json"
)
ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256 = (
    "d49762e1e588841d76583c9dfb59a60fc3634c8d8324ca1c535014db1fc06f1d"
)
ADOPTED_EXTERNAL_ARTIFACT_SHA256 = (
    "c8eacb7b8df0aa12b45eeb383d79d5cf95d7e002dfed7c07736e5aad3dca930c"
)
ADOPTED_EXTERNAL_ARTIFACT_BYTES = 510

SERVER_AUTHORITY = (
    "Layer 3 connector source intake record owns connector-produced source "
    "identity, bytes/metadata hash, provenance, storage pointer, and downstream eligibility."
)

ADOPTED_EXTERNAL_SERVER_AUTHORITY = (
    "Layer 3 adopted external source intake record owns the hash-bound adoption "
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


def adopted_external_provenance() -> dict[str, str]:
    return {
        "instrument": "standalone-curl",
        "method": "single unauthenticated HTTPS GET",
        "doi": ADOPTED_EXTERNAL_DOI,
        "acquisition_git_ref": ADOPTED_EXTERNAL_ACQUISITION_GIT_REF,
        "acquisition_record_path": ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH,
        "acquisition_record_sha256": ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256,
        "artifact_sha256": ADOPTED_EXTERNAL_ARTIFACT_SHA256,
        "acquired_at": ADOPTED_EXTERNAL_ACQUIRED_AT,
    }


def _adopted_external_request_basis(
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "source_family": ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY,
        "operator_decision": ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION,
        "connector_key": ADOPTED_EXTERNAL_CONNECTOR_KEY,
        "source_mode": ADOPTED_EXTERNAL_SOURCE_MODE,
        "artifact_surface": ADOPTED_EXTERNAL_SOURCE_MODE,
        "sciencebase_item_id": ADOPTED_EXTERNAL_ITEM_ID,
        "sciencebase_file_name": ADOPTED_EXTERNAL_FILENAME,
        "sciencebase_download_uri": ADOPTED_EXTERNAL_DOWNLOAD_URI,
        "adoption_provenance": _json_copy(provenance),
    }


def _adopted_external_permission_snapshot() -> dict[str, Any]:
    return {
        "license": "CC0-1.0",
        "license_source": "asserted",
        "public_read_confirmed": True,
        "public_read_evidence_source": (
            "standalone-instrument acquisition record, not this run"
        ),
        "acquisition_record_path": ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH,
        "acquisition_record_sha256": ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256,
    }


def validate_adopted_external_carrier(
    run: ConnectorRun,
    target: ConnectorRunTarget,
    *,
    adoption_provenance: Mapping[str, Any],
) -> None:
    expected_provenance = adopted_external_provenance()
    if dict(adoption_provenance) != expected_provenance:
        raise ConnectorSourceIntakeError(
            "adopted_external_source_intake_provenance_not_admitted",
            "The adoption provenance does not match the owner-authorized acquisition record.",
            http_status=409,
        )
    expected_request_basis = _adopted_external_request_basis(expected_provenance)
    expected_source_reference = {
        "doi": ADOPTED_EXTERNAL_DOI,
        "acquisition_git_ref": ADOPTED_EXTERNAL_ACQUISITION_GIT_REF,
        "acquisition_record_path": ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH,
        "acquisition_record_sha256": ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256,
    }
    carrier_matches = bool(
        run.connector_key == ADOPTED_EXTERNAL_CONNECTOR_KEY
        and run.source_system == "sciencebase"
        and run.source_mode == ADOPTED_EXTERNAL_SOURCE_MODE
        and run.status == "completed"
        and (run.request_config_json or {}) == expected_request_basis
        and run.discovered_count == 1
        and run.selected_count == 1
        and run.downloaded_count == 1
        and run.terminal_target_count == 1
        and run.consumed_bytes == ADOPTED_EXTERNAL_ARTIFACT_BYTES
        and target.connector_run_id == run.connector_run_id
        and target.ordinal == 1
        and target.sciencebase_item_id == ADOPTED_EXTERNAL_ITEM_ID
        and target.sciencebase_file_name == ADOPTED_EXTERNAL_FILENAME
        and target.sciencebase_download_uri == ADOPTED_EXTERNAL_DOWNLOAD_URI
        and target.artifact_surface == ADOPTED_EXTERNAL_SOURCE_MODE
        and target.artifact_locator_type == "adopted_storage_ref"
        and target.downloaded_sha256 == ADOPTED_EXTERNAL_ARTIFACT_SHA256
        and (target.source_reference_json or {}) == expected_source_reference
        and (target.permission_snapshot_json or {})
        == _adopted_external_permission_snapshot()
        and target.public_read_confirmed is True
        and target.status == "downloaded"
    )
    if not carrier_matches:
        raise ConnectorSourceIntakeError(
            "adopted_external_source_intake_carrier_not_admitted",
            "The carrier rows do not truthfully describe the owner-authorized adopted artifact.",
            http_status=409,
        )


def record_adopted_external_source_intake(
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
    adoption_provenance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Adopt the one owner-authorized external artifact without asserting a fetch."""
    if not settings.layer3_adopted_external_source_intake_enabled:
        raise ConnectorSourceIntakeError(
            "adopted_external_source_intake_unavailable",
            "Adopted external source intake is not enabled.",
            http_status=409,
        )
    if not isinstance(adoption_provenance, Mapping):
        raise ConnectorSourceIntakeError(
            "adopted_external_source_intake_provenance_required",
            "A validated adoption provenance mapping is required.",
        )

    request_id = _normalise_required(client_request_id, "client_request_id")
    if not _CLIENT_REQUEST_RE.match(request_id):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_invalid_client_request_id",
            "client_request_id must be 1-255 characters using letters, numbers, dot, dash, underscore, or colon.",
            details={"client_request_id": request_id},
        )
    key = _normalise_required(connector_key, "connector_key")
    run_id = _normalise_required(connector_run_id, "connector_run_id")
    target_id = _normalise_required(
        connector_run_target_id, "connector_run_target_id"
    )
    label = _normalise_required(source_label, "source_label")
    if len(label) > _LABEL_MAX_CHARS:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_label_too_long",
            "source_label must be 255 characters or fewer.",
        )
    description = (
        str(source_description).strip() if source_description is not None else None
    )
    if description is not None and len(description) > _DESCRIPTION_MAX_CHARS:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_description_too_long",
            "source_description must be 2000 characters or fewer.",
        )
    effective_media_type = str(media_type or "").strip()
    if not effective_media_type:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_media_type_required",
            "Adopted external source intake requires an explicit text/csv media_type.",
        )
    if len(effective_media_type) > 128:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_media_type_too_long",
            "media type must be 128 characters or fewer.",
        )
    if not _is_csv_media_type(effective_media_type):
        raise ConnectorSourceIntakeError(
            "connector_source_intake_media_type_not_admitted",
            "Only text/csv adopted external source intake is admitted.",
        )
    parsed_freshness = _parse_freshness_timestamp(freshness_timestamp)
    if parsed_freshness != _parse_freshness_timestamp(ADOPTED_EXTERNAL_ACQUIRED_AT):
        raise ConnectorSourceIntakeError(
            "adopted_external_source_intake_freshness_mismatch",
            "freshness_timestamp must match the acquisition record download completion time.",
            http_status=409,
        )

    run = db.get(ConnectorRun, run_id)
    if run is None or run.connector_key != key:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_run_not_found",
            "No carrier run exists for the requested adopted external source intake.",
            http_status=404,
        )
    target = db.get(ConnectorRunTarget, target_id)
    if target is None or target.connector_run_id != run_id:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_target_not_found",
            "No carrier target exists for the requested adopted external source intake.",
            http_status=404,
        )
    validated_provenance = _json_copy(adoption_provenance)
    validate_adopted_external_carrier(
        run,
        target,
        adoption_provenance=validated_provenance,
    )
    if not target.raw_storage_ref:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_raw_blob_missing",
            "The adopted external carrier target has no storage reference.",
            http_status=409,
        )
    storage_path = _storage_path_from_ref(target.raw_storage_ref)
    if not storage_path.is_file():
        raise ConnectorSourceIntakeError(
            "connector_source_intake_raw_blob_missing",
            "The adopted external artifact is not available in connector raw storage.",
            http_status=404,
        )
    content_size_bytes, content_sha256 = _hash_file(storage_path)
    if (
        content_size_bytes != ADOPTED_EXTERNAL_ARTIFACT_BYTES
        or content_sha256 != ADOPTED_EXTERNAL_ARTIFACT_SHA256
        or content_sha256 != target.downloaded_sha256
    ):
        raise ConnectorSourceIntakeError(
            "adopted_external_source_intake_hash_mismatch",
            "The adopted external artifact bytes do not match the authorized artifact hash.",
            http_status=409,
        )

    metadata = {
        "client_request_id": request_id,
        "source_family": ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY,
        "connector_key": key,
        "connector_run_id": run_id,
        "connector_run_target_id": target_id,
        "sciencebase_item_id": target.sciencebase_item_id,
        "sciencebase_download_uri": target.sciencebase_download_uri,
        "sciencebase_file_name": ADOPTED_EXTERNAL_FILENAME,
        "media_type": effective_media_type,
        "content_size_bytes": content_size_bytes,
        "content_sha256": content_sha256,
        "freshness_timestamp": _iso_or_none(parsed_freshness),
        "adoption_provenance": validated_provenance,
    }
    metadata_hash = _stable_hash(metadata)
    authority_basis = {
        "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
        "mode": ADOPTED_EXTERNAL_SOURCE_INTAKE_MODE,
        "operator_decision": ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION,
        "client_request_id": request_id,
        "metadata_hash": metadata_hash,
        "content_sha256": content_sha256,
        "source_gate": CONNECTOR_SOURCE_INTAKE_SOURCE_GATE,
        "adoption_provenance": _json_copy(validated_provenance),
    }
    authority_basis_hash = _stable_hash(authority_basis)
    if _existing_record(db, request_id, authority_basis_hash) is not None:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_idempotency_conflict",
            "The adopted external intake idempotency key or authority basis conflicts with an existing record.",
            http_status=409,
        )

    provenance = {
        "schema_id": CONNECTOR_SOURCE_INTAKE_SCHEMA_ID,
        "mode": ADOPTED_EXTERNAL_SOURCE_INTAKE_MODE,
        "operator_decision": ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION,
        "server_authority": ADOPTED_EXTERNAL_SERVER_AUTHORITY,
        "source_gate": CONNECTOR_SOURCE_INTAKE_SOURCE_GATE,
        "connector_key": key,
        "connector_run_id": run_id,
        "connector_run_target_id": target_id,
        "content_sha256": content_sha256,
        "metadata_hash": metadata_hash,
        "freshness_timestamp": _iso_or_none(parsed_freshness),
        "adoption_provenance": _json_copy(validated_provenance),
    }
    record = L3ConnectorSourceIntakeRecord(
        client_request_id=request_id,
        operator_decision=ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION,
        source_family=ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY,
        source_label=label,
        source_description=description,
        original_filename=ADOPTED_EXTERNAL_FILENAME,
        media_type=effective_media_type,
        content_size_bytes=content_size_bytes,
        content_sha256=content_sha256,
        metadata_hash=metadata_hash,
        authority_basis_hash=authority_basis_hash,
        storage_ref=str(target.raw_storage_ref),
        freshness_timestamp=parsed_freshness,
        provenance_json=provenance,
        downstream_eligibility_json=_downstream_eligibility(),
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
                "The adopted external intake idempotency key or authority basis conflicts with an existing record.",
                http_status=409,
            ) from exc
        raise ConnectorSourceIntakeError(
            "connector_source_intake_record_conflict",
            "The adopted external intake conflicts with an existing authority row.",
            http_status=409,
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
    if normalized_source_family not in _admitted_source_families():
        raise ConnectorSourceIntakeError(
            "connector_source_intake_inventory_source_family_not_admitted",
            "connector source-intake inventory is limited to an enabled admitted source family.",
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
        "message": _inventory_message(normalized_source_family),
        "source_family": normalized_source_family,
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
        "mode": _gate_b_provenance_mode(record),
        "source_ref": source_ref,
    }
    material_candidate = {
        "candidate_id": f"{_candidate_prefix(record)}{record.connector_source_intake_record_id}",
        "source_class": record.source_family,
        "source_ref": source_ref,
        "query_basis": _query_basis(record),
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
            "source_class": record.source_family,
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
        "message": _preview_message(record),
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
    expected_candidate_id = f"{_candidate_prefix(record)}{record_id}"
    if str(candidate_id or "").strip() != expected_candidate_id:
        raise ConnectorSourceIntakeError(
            "connector_source_intake_gate_b_candidate_family_mismatch",
            "The Gate B material candidate prefix does not match the source-intake authority row family.",
            http_status=409,
            details={"blocked_fields": ["candidate_decisions.candidate_id"]},
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
    if str(decision_basis.get("query_basis") or "").strip() != _query_basis(record):
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
            "source_family": record.source_family,
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
            "source_class": record.source_family,
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
    if record.source_family == ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY:
        expected_source_provenance = {
            **_json_copy(record.provenance_json or {}),
            "mode": _gate_b_provenance_mode(record),
            "source_ref": expected_source_ref,
        }
        provided_source_provenance = decision_basis.get("source_provenance")
        if (
            not isinstance(provided_source_provenance, Mapping)
            or _json_copy(provided_source_provenance) != expected_source_provenance
        ):
            raise ConnectorSourceIntakeError(
                "connector_source_intake_gate_b_source_provenance_mismatch",
                "The Gate B decision basis source_provenance does not match the adopted external intake authority row.",
                http_status=409,
                details={
                    "blocked_fields": [
                        "candidate_decisions.decision_basis.source_provenance"
                    ]
                },
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


def _json_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(dict(value), sort_keys=True, default=str))


def _admitted_source_families() -> set[str]:
    families = {CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY}
    if settings.layer3_adopted_external_source_intake_enabled:
        families.add(ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY)
    return families


def _is_adopted_external_record(record: L3ConnectorSourceIntakeRecord) -> bool:
    return record.source_family == ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY


def _candidate_prefix(record: L3ConnectorSourceIntakeRecord) -> str:
    if _is_adopted_external_record(record):
        return ADOPTED_EXTERNAL_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX
    return CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX


def _query_basis(record: L3ConnectorSourceIntakeRecord) -> str:
    if _is_adopted_external_record(record):
        return ADOPTED_EXTERNAL_SOURCE_INTAKE_QUERY_BASIS
    return CONNECTOR_SOURCE_INTAKE_QUERY_BASIS


def _intake_mode(record: L3ConnectorSourceIntakeRecord) -> str:
    if _is_adopted_external_record(record):
        return ADOPTED_EXTERNAL_SOURCE_INTAKE_MODE
    return CONNECTOR_SOURCE_INTAKE_MODE


def _gate_b_provenance_mode(record: L3ConnectorSourceIntakeRecord) -> str:
    if _is_adopted_external_record(record):
        return ADOPTED_EXTERNAL_SOURCE_INTAKE_MODE
    return CONNECTOR_SOURCE_INTAKE_GATE_B_MODE


def _inventory_message(source_family: str) -> str:
    if source_family == ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY:
        return "Layer 3 adopted external source intake inventory returned safe record metadata only."
    return "Layer 3 connector source intake inventory returned safe record metadata only."


def _preview_message(record: L3ConnectorSourceIntakeRecord) -> str:
    if _is_adopted_external_record(record):
        return "Layer 3 adopted external source-intake material preview returned bounded text from one adopted artifact."
    return "Layer 3 connector source-intake material preview returned bounded text from one connector raw blob."


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
        "mode": _intake_mode(record),
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
        "source_family": record.source_family,
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
        or record.source_family not in _admitted_source_families()
    ):
        message = "Only recorded connector-produced single-source rows are admitted."
        if settings.layer3_adopted_external_source_intake_enabled:
            message = "Only recorded connector or adopted-external single-source rows are admitted."
        raise ConnectorSourceIntakeError(
            f"connector_source_intake_{context}_record_not_admitted",
            message,
            http_status=409,
            details={
                "connector_source_intake_record_id": record.connector_source_intake_record_id,
                "status": record.status,
                "source_family": record.source_family,
            },
        )


def _connector_source_intake_record_id_from_candidate(candidate_id: str) -> str | None:
    value = str(candidate_id or "").strip()
    for prefix in (
        CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX,
        ADOPTED_EXTERNAL_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX,
    ):
        if value.startswith(prefix):
            record_id = value[len(prefix) :].strip()
            return record_id or None
    return None


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
