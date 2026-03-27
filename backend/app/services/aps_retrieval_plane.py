from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ApsRetrievalChunk
from app.services import aps_retrieval_plane_contract as contract


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _latest_source_timestamp(*values: datetime | None) -> datetime:
    normalized = [_normalize_dt(value) for value in values if value is not None]
    return max(normalized) if normalized else _utc_now()


def _row_identity_tuple_from_orm(row: ApsRetrievalChunk) -> tuple[Any, ...]:
    return tuple(getattr(row, field) for field in contract.APS_RETRIEVAL_IDENTITY_FIELDS)


def _serialize_retrieval_row(row: ApsRetrievalChunk) -> dict[str, Any]:
    return {field: getattr(row, field) for field in contract.APS_RETRIEVAL_PERSISTED_FIELDS}


def _resolve_quality_status(*, document: ApsContentDocument, chunk: ApsContentChunk) -> str | None:
    return contract.normalize_optional_string(chunk.quality_status) or contract.normalize_optional_string(document.quality_status)


def _resolve_diagnostics_ref(*, linkage: ApsContentLinkage) -> str | None:
    return contract.normalize_optional_string(linkage.diagnostics_ref)


def fetch_canonical_rows_for_run(
    db: Session,
    *,
    run_id: str,
) -> list[tuple[ApsContentLinkage, ApsContentDocument, ApsContentChunk]]:
    normalized_run_id = contract.normalize_optional_string(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")
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
        .filter(ApsContentLinkage.run_id == normalized_run_id)
        .order_by(
            ApsContentLinkage.content_id.asc(),
            ApsContentChunk.chunk_ordinal.asc(),
            ApsContentLinkage.target_id.asc(),
            ApsContentChunk.chunk_id.asc(),
        )
    )
    return list(query.all())


def build_expected_retrieval_row(
    *,
    linkage: ApsContentLinkage,
    document: ApsContentDocument,
    chunk: ApsContentChunk,
) -> dict[str, Any]:
    payload = {
        "retrieval_contract_id": contract.APS_RETRIEVAL_CONTRACT_ID,
        "run_id": str(linkage.run_id or ""),
        "target_id": str(linkage.target_id or ""),
        "content_id": str(linkage.content_id or ""),
        "chunk_id": str(chunk.chunk_id or ""),
        "content_contract_id": str(linkage.content_contract_id or ""),
        "chunking_contract_id": str(linkage.chunking_contract_id or ""),
        "normalization_contract_id": contract.normalize_optional_string(document.normalization_contract_id),
        "accession_number": contract.normalize_optional_string(linkage.accession_number),
        "chunk_ordinal": int(chunk.chunk_ordinal or 0),
        "start_char": int(chunk.start_char or 0),
        "end_char": int(chunk.end_char or 0),
        "page_start": int(chunk.page_start) if chunk.page_start is not None else None,
        "page_end": int(chunk.page_end) if chunk.page_end is not None else None,
        "chunk_text": str(chunk.chunk_text or ""),
        "chunk_text_sha256": str(chunk.chunk_text_sha256 or ""),
        "search_text": str(chunk.chunk_text or ""),
        "content_status": str(document.content_status or ""),
        "quality_status": _resolve_quality_status(document=document, chunk=chunk),
        "document_class": contract.normalize_optional_string(document.document_class),
        "media_type": contract.normalize_optional_string(document.media_type),
        "page_count": int(document.page_count or 0),
        "content_units_ref": contract.normalize_optional_string(linkage.content_units_ref),
        "normalized_text_ref": contract.normalize_optional_string(linkage.normalized_text_ref),
        "blob_ref": contract.normalize_optional_string(linkage.blob_ref),
        "download_exchange_ref": contract.normalize_optional_string(linkage.download_exchange_ref),
        "discovery_ref": contract.normalize_optional_string(linkage.discovery_ref),
        "selection_ref": contract.normalize_optional_string(linkage.selection_ref),
        "diagnostics_ref": _resolve_diagnostics_ref(linkage=linkage),
        "visual_page_refs_json": contract.canonicalize_visual_page_refs(document.visual_page_refs_json),
        "source_updated_at": _latest_source_timestamp(
            document.updated_at,
            chunk.updated_at,
            getattr(linkage, "created_at", None),
            getattr(document, "created_at", None),
            getattr(chunk, "created_at", None),
        ),
    }
    payload["aps_retrieval_chunk_id"] = contract.derive_retrieval_chunk_id(payload)
    payload["source_signature_sha256"] = contract.compute_source_signature(payload)
    return payload


def list_retrieval_rows_for_run(db: Session, *, run_id: str) -> list[dict[str, Any]]:
    normalized_run_id = contract.normalize_optional_string(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")
    rows = (
        db.query(ApsRetrievalChunk)
        .filter(ApsRetrievalChunk.run_id == normalized_run_id)
        .order_by(
            ApsRetrievalChunk.content_id.asc(),
            ApsRetrievalChunk.chunk_ordinal.asc(),
            ApsRetrievalChunk.target_id.asc(),
            ApsRetrievalChunk.chunk_id.asc(),
        )
        .all()
    )
    return [_serialize_retrieval_row(row) for row in rows]


def rebuild_retrieval_plane_for_run(
    db: Session,
    *,
    run_id: str,
    rebuilt_at: datetime | None = None,
) -> dict[str, Any]:
    normalized_run_id = contract.normalize_optional_string(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")
    effective_rebuilt_at = _normalize_dt(rebuilt_at) or _utc_now()
    canonical_rows = fetch_canonical_rows_for_run(db, run_id=normalized_run_id)
    existing_rows = db.query(ApsRetrievalChunk).filter(ApsRetrievalChunk.run_id == normalized_run_id).all()
    existing_by_key = {_row_identity_tuple_from_orm(row): row for row in existing_rows}

    expected_keys: set[tuple[Any, ...]] = set()
    inserted = 0
    updated = 0
    unchanged = 0

    for linkage, document, chunk in canonical_rows:
        expected = build_expected_retrieval_row(linkage=linkage, document=document, chunk=chunk)
        key = contract.row_identity_tuple(expected)
        expected_keys.add(key)
        existing = existing_by_key.get(key)
        if (
            existing is not None
            and existing.source_signature_sha256 == expected["source_signature_sha256"]
            and _normalize_dt(existing.source_updated_at) == _normalize_dt(expected["source_updated_at"])
        ):
            unchanged += 1
            continue

        payload = dict(expected)
        payload["rebuilt_at"] = effective_rebuilt_at
        if existing is None:
            db.add(ApsRetrievalChunk(**payload))
            inserted += 1
        else:
            for field, value in payload.items():
                setattr(existing, field, value)
            updated += 1

    deleted = 0
    for row in existing_rows:
        if _row_identity_tuple_from_orm(row) in expected_keys:
            continue
        db.delete(row)
        deleted += 1

    db.flush()
    return {
        "run_id": normalized_run_id,
        "retrieval_contract_id": contract.APS_RETRIEVAL_CONTRACT_ID,
        "canonical_row_count": len(canonical_rows),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "deleted": deleted,
    }
