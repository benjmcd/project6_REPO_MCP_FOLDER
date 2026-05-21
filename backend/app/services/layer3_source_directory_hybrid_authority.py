from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models import L3MaterialSnapshot
from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.layer3_source_directory_text_index import source_directory_material_text_index
from app.services.layer3_source_directory_vector_index import source_directory_material_embedding_vector_index

SCHEMA_ID = "layer3.source_directory_hybrid_authority_prepare.v1"
MODE = "source_directory_hybrid_authority_generation_operator_bridge"
SOURCE_CLASS = "server_configured_directory_file"

DEFAULT_QUERY_TEXT = "BETA alpha alpha"
DEFAULT_ANALYSIS_QUESTION = "What does the alpha beta evidence support?"
DEFAULT_ANALYSIS_FOCUS = "rendered source-directory scan to hybrid handoff delivery proof"

_AUTHORITY_FIELDS = (
    "material_snapshot_id",
    "source_ingestion_batch_id",
    "source_ingestion_file_id",
    "content_sha256",
    "file_identity_hash",
    "authority_basis_hash",
    "payload_hash",
)

_ALLOWED_FIELDS = {
    "analysis_focus",
    "analysis_question",
    "client_request_id",
    "limit",
    "material_snapshot_id",
    "offset",
    "query_text",
    "session_id",
    "top_k",
}

_FORBIDDEN_FIELDS = {
    "absolute_path",
    "browser_state",
    "connector_destination",
    "destination_id",
    "destination_url",
    "embedding_index_authority_hash",
    "file_bytes",
    "frontend_state",
    "headers",
    "index_authority_hash",
    "local_file_path",
    "package_payload",
    "payload_ref",
    "provider_url",
    "public_url",
    "raw_headers",
    "raw_package_payload",
    "raw_payload",
    "raw_payload_path",
    "raw_target_url",
    "signed_url",
    "target_url",
    "token",
    "webhook_destination",
}


class SourceDirectoryHybridAuthorityError(Exception):
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
            "request_id": "source-directory-hybrid-authority-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_hybrid_authority_prepare(db: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    session_id = _required(fields, "session_id")
    snapshot = _load_source_directory_snapshot(
        db,
        session_id=session_id,
        material_snapshot_id=str(fields.get("material_snapshot_id") or "").strip() or None,
    )
    snapshot_info = _snapshot_info(snapshot)
    text_index = source_directory_material_text_index(
        db,
        {
            "client_request_id": f"{request_id}-text-index",
            **snapshot_info,
        },
    )
    vector_index = source_directory_material_embedding_vector_index(
        db,
        {
            "client_request_id": f"{request_id}-vector-index",
            **snapshot_info,
            "index_authority_hash": text_index["index_authority_hash"],
        },
    )
    authority_payload = {
        **snapshot_info,
        "index_authority_hash": text_index["index_authority_hash"],
        "embedding_index_authority_hash": vector_index["embedding_index_authority_hash"],
        "query_text": _optional_text(fields, "query_text", DEFAULT_QUERY_TEXT),
        "analysis_question": _optional_text(fields, "analysis_question", DEFAULT_ANALYSIS_QUESTION),
        "analysis_focus": _optional_text(fields, "analysis_focus", DEFAULT_ANALYSIS_FOCUS),
        "limit": _optional_int(fields, "limit", 2, minimum=1, maximum=50),
        "offset": _optional_int(fields, "offset", 0, minimum=0),
        "top_k": _optional_int(fields, "top_k", 2, minimum=1, maximum=20),
    }
    authority_hash = _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "mode": MODE,
            "session_id": session_id,
            "authority_payload": authority_payload,
        }
    )
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "mode": MODE,
        "session_id": session_id,
        "material_snapshot_id": authority_payload["material_snapshot_id"],
        "source_ingestion_batch_id": authority_payload["source_ingestion_batch_id"],
        "source_ingestion_file_id": authority_payload["source_ingestion_file_id"],
        "index_authority_hash": authority_payload["index_authority_hash"],
        "embedding_index_authority_hash": authority_payload["embedding_index_authority_hash"],
        "authority_prepare_hash": authority_hash,
        "authority_payload": authority_payload,
        "redaction_guards": {
            "absolute_path_exposed": False,
            "raw_payload_ref_exposed": False,
            "file_bytes_exposed": False,
            "provider_url_enabled": False,
            "connector_destination_enabled": False,
            "webhook_destination_enabled": False,
            "package_payload_exposed": False,
            "frontend_durable_authority_enabled": False,
        },
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [
            "submit_source_directory_hybrid_middle_lifecycle_from_server_authority",
            "inspect_source_directory_hybrid_delivery_status_before_delivery",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_forbidden_field_not_admitted",
            "The source-directory hybrid authority prepare request includes browser or downstream authority fields.",
            http_status=409,
            details={"blocked_fields": forbidden},
        )
    unknown = sorted(set(fields) - _ALLOWED_FIELDS)
    if unknown:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_unknown_field",
            "The source-directory hybrid authority prepare request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    return fields


def _load_source_directory_snapshot(
    db: Session,
    *,
    session_id: str,
    material_snapshot_id: str | None,
) -> L3MaterialSnapshot:
    query = db.query(L3MaterialSnapshot).filter(
        L3MaterialSnapshot.session_id == session_id,
        L3MaterialSnapshot.source_shape == SOURCE_CLASS,
    )
    if material_snapshot_id:
        query = query.filter(L3MaterialSnapshot.material_snapshot_id == material_snapshot_id)
    snapshots = query.order_by(L3MaterialSnapshot.material_snapshot_id.asc()).all()
    if not snapshots:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_material_snapshot_not_found",
            "No admitted source-directory material snapshot exists for the requested session.",
            http_status=404,
            details={"session_id": session_id, "material_snapshot_id": material_snapshot_id},
        )
    if len(snapshots) > 1:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_material_snapshot_ambiguous",
            "Multiple source-directory material snapshots exist for the session; material_snapshot_id is required.",
            http_status=409,
            details={
                "session_id": session_id,
                "material_snapshot_ids": [snapshot.material_snapshot_id for snapshot in snapshots],
            },
        )
    return snapshots[0]


def _snapshot_info(snapshot: L3MaterialSnapshot) -> dict[str, str]:
    identity = dict(snapshot.source_identity_json or {})
    values = {
        "material_snapshot_id": snapshot.material_snapshot_id,
        "source_ingestion_batch_id": identity.get("source_ingestion_batch_id"),
        "source_ingestion_file_id": identity.get("source_ingestion_file_id"),
        "content_sha256": identity.get("content_sha256"),
        "file_identity_hash": identity.get("file_identity_hash"),
        "authority_basis_hash": identity.get("authority_basis_hash"),
        "payload_hash": snapshot.payload_hash,
    }
    missing = [key for key in _AUTHORITY_FIELDS if not str(values.get(key) or "").strip()]
    if missing:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_material_snapshot_missing_authority",
            "The source-directory material snapshot is missing authority fields required for hybrid authority.",
            http_status=409,
            details={"material_snapshot_id": snapshot.material_snapshot_id, "blocked_fields": missing},
        )
    return {key: str(values[key]) for key in _AUTHORITY_FIELDS}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_required_field_missing",
            "A required source-directory hybrid authority prepare field is missing or empty.",
            details={"field": key},
        )
    return value


def _optional_text(fields: Mapping[str, Any], key: str, default: str) -> str:
    value = str(fields.get(key) or "").strip()
    return value or default


def _optional_int(
    fields: Mapping[str, Any],
    key: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    value = fields.get(key)
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_integer_field_invalid",
            "A source-directory hybrid authority integer field is invalid.",
            details={"field": key},
        ) from exc
    if minimum is not None and number < minimum:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_integer_field_out_of_range",
            "A source-directory hybrid authority integer field is below the admitted range.",
            details={"field": key, "minimum": minimum},
        )
    if maximum is not None and number > maximum:
        raise SourceDirectoryHybridAuthorityError(
            "source_directory_hybrid_authority_integer_field_out_of_range",
            "A source-directory hybrid authority integer field is above the admitted range.",
            details={"field": key, "maximum": maximum},
        )
    return number


def _negative_invariants() -> dict[str, bool]:
    return {
        "absolute_path_exposed": False,
        "raw_payload_ref_exposed": False,
        "file_bytes_exposed": False,
        "source_index_rows_written": False,
        "embedding_vector_rows_written": False,
        "vector_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "provider_private_signed_url_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat()
