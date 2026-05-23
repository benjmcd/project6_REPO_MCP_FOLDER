from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models import L3MaterialSnapshot, L3SourceDirectoryIngestionBatch, L3SourceDirectoryIngestionFile
from app.services.layer3_source_directory_ingestion import (
    ALLOWED_EXTENSIONS,
    MAX_RELATIVE_PATH_SEGMENTS,
    MODE as INGESTION_MODE,
    SOURCE_FAMILY,
    STATUS_RECORDED,
    SourceDirectoryIngestionError,
    resolve_batch_source_root,
    _stable_hash,
)

SCHEMA_ID = "layer3.source_directory_text_index.v1"
MODE = "source_directory_material_deterministic_text_index_authority"
SOURCE_CLASS = "server_configured_directory_file"
INDEX_CONTRACT_ID = "source_directory_material_deterministic_text_index_authority"
INDEX_MODE = "deterministic_text_segments"
SEGMENTATION_VERSION = "line-window-v1"
MAX_SEGMENT_CHARS = 1600
MAX_SEGMENT_LINES = 40

_FORBIDDEN_FIELDS = {
    "absolute_path",
    "connector_target",
    "destination",
    "embedding_model",
    "embedding_options",
    "file_bytes",
    "frontend_state",
    "glob",
    "local_path",
    "package_payload",
    "path",
    "provider_model",
    "provider_url",
    "public_url",
    "rag_index",
    "recursive",
    "retrieval_query",
    "retrieval_query_text",
    "url",
    "vector_index",
    "web_connector",
}


class SourceDirectoryTextIndexError(Exception):
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
            "request_id": "source-directory-text-index-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_text_index(db: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    material_snapshot_id = _required(fields, "material_snapshot_id")

    snapshot, batch, file_record = _load_authority(db, material_snapshot_id=material_snapshot_id, fields=fields)
    _assert_payload_authority(snapshot)
    live_file = _read_live_file(batch, file_record)
    _assert_live_file_matches_authority(file_record, live_file)

    identity_basis = _index_identity_basis(snapshot, batch, file_record)
    segments = _build_segments(live_file["text"], identity_basis=identity_basis)
    index_authority_hash = _stable_hash(
        {
            **identity_basis,
            "segment_count": len(segments),
            "segment_hashes": [item["segment_hash"] for item in segments],
        }
    )
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": "available",
        "message": "Layer 3 source-directory material deterministic text index returned stable text segments.",
        "index_contract_id": INDEX_CONTRACT_ID,
        "index_mode": INDEX_MODE,
        "segmentation_version": SEGMENTATION_VERSION,
        "index_authority_hash": index_authority_hash,
        "source_ingestion_batch_id": batch.source_ingestion_batch_id,
        "source_ingestion_file_id": file_record.source_ingestion_file_id,
        "material_snapshot_id": snapshot.material_snapshot_id,
        "source_shape": SOURCE_CLASS,
        "content_sha256": file_record.content_sha256,
        "file_identity_hash": file_record.file_identity_hash,
        "authority_basis_hash": file_record.authority_basis_hash,
        "payload_hash": snapshot.payload_hash,
        "segment_count": len(segments),
        "segments": segments,
        "source_index_rows_written": False,
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [
            "use_deterministic_text_segments_as_source_index_authority",
            "freeze_later_before_vector_embedding_retrieval_or_qualitative_hybrid_runtime",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_forbidden_field_not_admitted",
            "The deterministic text index request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    allowed = {
        "client_request_id",
        "material_snapshot_id",
        "source_ingestion_batch_id",
        "source_ingestion_file_id",
        "content_sha256",
        "file_identity_hash",
        "authority_basis_hash",
        "payload_hash",
    }
    unknown = sorted(set(fields) - allowed)
    if unknown:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_unknown_field",
            "The deterministic text index request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    return fields


def _load_authority(
    db: Session,
    *,
    material_snapshot_id: str,
    fields: Mapping[str, Any],
) -> tuple[L3MaterialSnapshot, L3SourceDirectoryIngestionBatch, L3SourceDirectoryIngestionFile]:
    snapshot = db.get(L3MaterialSnapshot, material_snapshot_id)
    if snapshot is None:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_material_snapshot_not_found",
            "No material snapshot exists for the requested deterministic text index.",
            http_status=404,
            details={"material_snapshot_id": material_snapshot_id},
        )
    if snapshot.source_shape != SOURCE_CLASS:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_source_shape_not_admitted",
            "Only server-configured source-directory file material snapshots are admitted.",
            http_status=409,
            details={"material_snapshot_id": material_snapshot_id, "source_shape": snapshot.source_shape},
        )
    identity = snapshot.source_identity_json or {}
    source_ingestion_batch_id = _identity_value(identity, "source_ingestion_batch_id")
    source_ingestion_file_id = _identity_value(identity, "source_ingestion_file_id")
    batch = db.get(L3SourceDirectoryIngestionBatch, source_ingestion_batch_id)
    file_record = db.get(L3SourceDirectoryIngestionFile, source_ingestion_file_id)
    if batch is None:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_batch_not_found",
            "No source-directory batch authority exists for the requested material snapshot.",
            http_status=404,
            details={"source_ingestion_batch_id": source_ingestion_batch_id},
        )
    if file_record is None:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_file_not_found",
            "No source-directory file authority exists for the requested material snapshot.",
            http_status=404,
            details={"source_ingestion_file_id": source_ingestion_file_id},
        )
    if file_record.source_ingestion_batch_id != batch.source_ingestion_batch_id:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_file_batch_mismatch",
            "The source-directory file is not owned by the snapshot batch authority.",
            http_status=409,
            details={"source_ingestion_batch_id": source_ingestion_batch_id, "source_ingestion_file_id": source_ingestion_file_id},
        )
    if batch.status != STATUS_RECORDED or batch.source_family != SOURCE_FAMILY or batch.ingestion_mode != INGESTION_MODE:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_batch_not_admitted",
            "Only recorded server-configured source-directory ingestion batches are admitted.",
            http_status=409,
            details={"source_ingestion_batch_id": source_ingestion_batch_id},
        )
    if file_record.status != STATUS_RECORDED or file_record.extension not in ALLOWED_EXTENSIONS:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_file_not_admitted",
            "Only recorded admitted source-directory text/table files are admitted.",
            http_status=409,
            details={"source_ingestion_file_id": source_ingestion_file_id, "extension": file_record.extension},
        )
    _assert_expected_fields(
        fields,
        expected={
            "source_ingestion_batch_id": batch.source_ingestion_batch_id,
            "source_ingestion_file_id": file_record.source_ingestion_file_id,
            "content_sha256": file_record.content_sha256,
            "file_identity_hash": file_record.file_identity_hash,
            "authority_basis_hash": file_record.authority_basis_hash,
            "payload_hash": snapshot.payload_hash,
        },
        code="source_directory_text_index_stale_request_authority",
    )
    _assert_expected_fields(
        identity,
        expected={
            "source_ingestion_batch_id": batch.source_ingestion_batch_id,
            "source_ingestion_file_id": file_record.source_ingestion_file_id,
            "source_class": SOURCE_CLASS,
            "content_sha256": file_record.content_sha256,
            "file_identity_hash": file_record.file_identity_hash,
            "authority_basis_hash": file_record.authority_basis_hash,
        },
        code="source_directory_text_index_material_identity_mismatch",
    )
    return snapshot, batch, file_record


def _assert_payload_authority(snapshot: L3MaterialSnapshot) -> None:
    payload_ref = str(snapshot.payload_ref or "").strip()
    if not payload_ref:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_payload_ref_missing",
            "The material snapshot has no payload ref to verify.",
            http_status=409,
            details={"material_snapshot_id": snapshot.material_snapshot_id},
        )
    path = Path(payload_ref)
    try:
        payload_bytes = path.read_bytes()
    except OSError as exc:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_payload_unreadable",
            "The material snapshot payload cannot be read for authority verification.",
            http_status=409,
            details={"material_snapshot_id": snapshot.material_snapshot_id},
        ) from exc
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    if payload_hash != snapshot.payload_hash:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_payload_hash_mismatch",
            "The material snapshot payload hash no longer matches persisted authority.",
            http_status=409,
            details={"material_snapshot_id": snapshot.material_snapshot_id, "blocked_fields": ["payload_hash"]},
        )


def _read_live_file(
    batch: L3SourceDirectoryIngestionBatch,
    file_record: L3SourceDirectoryIngestionFile,
) -> dict[str, Any]:
    try:
        root = resolve_batch_source_root(batch)
    except SourceDirectoryIngestionError as exc:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_config_unavailable",
            "The persisted source-directory root is not available for deterministic text indexing.",
            http_status=exc.http_status,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id, **exc.details},
        ) from exc
    relative = PurePosixPath(file_record.relative_name)
    if (
        relative.is_absolute()
        or not relative.parts
        or len(relative.parts) > MAX_RELATIVE_PATH_SEGMENTS
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_relative_name_not_admitted",
            "The persisted source-directory file name is outside the admitted relative-path shape.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        )
    resolved_root = root.resolve()
    resolved_path = (root / Path(*relative.parts)).resolve()
    if resolved_root not in resolved_path.parents:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_path_not_admitted",
            "The persisted source-directory file resolves outside the configured server-owned root.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        )
    try:
        before = resolved_path.stat()
        data = resolved_path.read_bytes()
        after = resolved_path.stat()
    except OSError as exc:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_file_unreadable",
            "The source-directory file could not be read for deterministic text indexing.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        ) from exc
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_file_changed_during_read",
            "The source-directory file changed while deterministic text indexing was reading it.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id},
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_text_decode_failed",
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
        "text": text.replace("\r\n", "\n").replace("\r", "\n"),
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
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_file_identity_mismatch",
            "The live source-directory file no longer matches the persisted file authority.",
            http_status=409,
            details={"source_ingestion_file_id": file_record.source_ingestion_file_id, "blocked_fields": mismatches},
        )


def _index_identity_basis(
    snapshot: L3MaterialSnapshot,
    batch: L3SourceDirectoryIngestionBatch,
    file_record: L3SourceDirectoryIngestionFile,
) -> dict[str, Any]:
    return {
        "source_ingestion_batch_id": batch.source_ingestion_batch_id,
        "source_ingestion_file_id": file_record.source_ingestion_file_id,
        "material_snapshot_id": snapshot.material_snapshot_id,
        "content_sha256": file_record.content_sha256,
        "file_identity_hash": file_record.file_identity_hash,
        "authority_basis_hash": file_record.authority_basis_hash,
        "payload_hash": snapshot.payload_hash,
        "index_contract_id": INDEX_CONTRACT_ID,
        "index_mode": INDEX_MODE,
        "segmentation_version": SEGMENTATION_VERSION,
    }


def _build_segments(text: str, *, identity_basis: Mapping[str, Any]) -> list[dict[str, Any]]:
    if text == "":
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_empty_material",
            "The source-directory material has no text available for deterministic indexing.",
            http_status=409,
            details={"material_snapshot_id": identity_basis.get("material_snapshot_id")},
        )
    segments: list[dict[str, Any]] = []
    current_parts: list[str] = []
    current_line_start = 1
    current_char_start = 0
    current_line_count = 0
    current_char_count = 0
    char_pos = 0

    for line_number, line in enumerate(text.splitlines(keepends=True) or [text], start=1):
        if len(line) > MAX_SEGMENT_CHARS:
            if current_parts:
                _append_segment(
                    segments,
                    parts=current_parts,
                    line_start=current_line_start,
                    line_end=line_number - 1,
                    char_start=current_char_start,
                    identity_basis=identity_basis,
                )
                current_parts = []
                current_line_count = 0
                current_char_count = 0
            for offset in range(0, len(line), MAX_SEGMENT_CHARS):
                chunk = line[offset : offset + MAX_SEGMENT_CHARS]
                _append_segment(
                    segments,
                    parts=[chunk],
                    line_start=line_number,
                    line_end=line_number,
                    char_start=char_pos + offset,
                    identity_basis=identity_basis,
                )
            char_pos += len(line)
            current_line_start = line_number + 1
            current_char_start = char_pos
            continue
        if current_parts and (
            current_char_count + len(line) > MAX_SEGMENT_CHARS or current_line_count >= MAX_SEGMENT_LINES
        ):
            _append_segment(
                segments,
                parts=current_parts,
                line_start=current_line_start,
                line_end=line_number - 1,
                char_start=current_char_start,
                identity_basis=identity_basis,
            )
            current_parts = []
            current_line_start = line_number
            current_char_start = char_pos
            current_line_count = 0
            current_char_count = 0
        current_parts.append(line)
        current_line_count += 1
        current_char_count += len(line)
        char_pos += len(line)

    if current_parts:
        _append_segment(
            segments,
            parts=current_parts,
            line_start=current_line_start,
            line_end=current_line_start + current_line_count - 1,
            char_start=current_char_start,
            identity_basis=identity_basis,
        )
    return segments


def _append_segment(
    segments: list[dict[str, Any]],
    *,
    parts: list[str],
    line_start: int,
    line_end: int,
    char_start: int,
    identity_basis: Mapping[str, Any],
) -> None:
    segment_text = "".join(parts)
    segment_hash = hashlib.sha256(segment_text.encode("utf-8")).hexdigest()
    sequence = len(segments) + 1
    char_end = char_start + len(segment_text)
    segment_basis = {
        **dict(identity_basis),
        "segment_sequence": sequence,
        "line_start": line_start,
        "line_end": line_end,
        "char_start": char_start,
        "char_end": char_end,
        "segment_hash": segment_hash,
    }
    segments.append(
        {
            "segment_id": f"sdtxt-{_stable_hash(segment_basis)[:32]}",
            "segment_sequence": sequence,
            "line_start": line_start,
            "line_end": line_end,
            "char_start": char_start,
            "char_end": char_end,
            "segment_hash": segment_hash,
            "text": segment_text,
        }
    )


def _identity_value(identity: Mapping[str, Any], field: str) -> str:
    value = str(identity.get(field) or "").strip()
    if not value:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_material_identity_missing",
            "The material snapshot is missing source-directory identity required for deterministic text indexing.",
            http_status=409,
            details={"field": field},
        )
    return value


def _assert_expected_fields(fields: Mapping[str, Any], *, expected: Mapping[str, Any], code: str) -> None:
    mismatches = [
        field
        for field, expected_value in expected.items()
        if field in fields and str(fields.get(field) or "").strip() != str(expected_value)
    ]
    if mismatches:
        raise SourceDirectoryTextIndexError(
            code,
            "The deterministic text index authority request does not match current source-directory authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryTextIndexError(
            "source_directory_text_index_required_field_missing",
            "A required deterministic text index field is missing or empty.",
            details={"field": key},
        )
    return value


def _negative_invariants() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "route_admitted": False,
        "vector_index_enabled": False,
        "embedding_generation_enabled": False,
        "retrieval_query_enabled": False,
        "qualitative_hybrid_runtime_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "package_construction_enabled": False,
        "package_mutation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "network_egress_enabled": False,
    }


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
