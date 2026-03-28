from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ApsRetrievalChunk
from app.services import nrc_aps_content_index


RETRIEVAL_NOT_MATERIALIZED_CODE = "retrieval_not_materialized"
RETRIEVAL_NOT_MATERIALIZED_MESSAGE = "retrieval plane is not materialized for the requested scope"


class RetrievalPlaneReadError(RuntimeError):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = int(status_code)
        self.code = str(code)
        self.message = str(message)

    def to_detail(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
        }


def _normalize_run_id(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _deserialize_visual_page_refs(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    normalized = str(raw or "").strip()
    if not normalized:
        return []
    try:
        parsed = json.loads(normalized)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [dict(item) for item in parsed if isinstance(item, dict)]


def _load_content_units_artifact(
    *,
    ref: str | None,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    normalized_ref = str(ref or "").strip()
    if not normalized_ref:
        return {}
    cached = cache.get(normalized_ref)
    if cached is not None:
        return cached

    payload: dict[str, Any] = {}
    chunks_by_id: dict[str, dict[str, Any]] = {}
    path = Path(normalized_ref)
    if path.exists():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            payload = parsed
            chunks_by_id = {
                str(item.get("chunk_id") or "").strip(): dict(item)
                for item in (parsed.get("chunks") or [])
                if isinstance(item, dict) and str(item.get("chunk_id") or "").strip()
            }

    snapshot = {
        "payload": payload,
        "chunks_by_id": chunks_by_id,
    }
    cache[normalized_ref] = snapshot
    return snapshot


def _canonical_row_count_for_run(db: Session, *, run_id: str) -> int:
    normalized_run_id = _normalize_run_id(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")
    return int(
        db.query(ApsContentLinkage)
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
        .count()
    )


def _retrieval_row_count_for_run(db: Session, *, run_id: str) -> int:
    normalized_run_id = _normalize_run_id(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")
    return int(db.query(ApsRetrievalChunk).filter(ApsRetrievalChunk.run_id == normalized_run_id).count())


def _ensure_run_scope_is_materialized(db: Session, *, run_id: str) -> int:
    canonical_count = _canonical_row_count_for_run(db, run_id=run_id)
    retrieval_count = _retrieval_row_count_for_run(db, run_id=run_id)
    if canonical_count == retrieval_count:
        return retrieval_count
    raise RetrievalPlaneReadError(
        status_code=409,
        code=RETRIEVAL_NOT_MATERIALIZED_CODE,
        message=RETRIEVAL_NOT_MATERIALIZED_MESSAGE,
    )


def _serialize_retrieval_row(
    *,
    row: ApsRetrievalChunk,
    artifact_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    artifact_snapshot = _load_content_units_artifact(ref=row.content_units_ref, cache=artifact_cache)
    artifact_payload = dict(artifact_snapshot.get("payload") or {})
    chunk_payload = dict((artifact_snapshot.get("chunks_by_id") or {}).get(str(row.chunk_id or "").strip()) or {})
    effective_content_type = str(artifact_payload.get("effective_content_type") or row.media_type or "").strip() or None
    visual_page_refs = _deserialize_visual_page_refs(
        artifact_payload.get("visual_page_refs") if "visual_page_refs" in artifact_payload else row.visual_page_refs_json
    )
    return {
        "content_id": str(row.content_id or ""),
        "chunk_id": str(row.chunk_id or ""),
        "content_contract_id": str(row.content_contract_id or ""),
        "chunking_contract_id": str(row.chunking_contract_id or ""),
        "chunk_ordinal": int(row.chunk_ordinal or 0),
        "start_char": int(row.start_char or 0),
        "end_char": int(row.end_char or 0),
        "chunk_text": str(row.chunk_text or ""),
        "chunk_text_sha256": str(row.chunk_text_sha256 or ""),
        "page_start": int(row.page_start) if row.page_start is not None else None,
        "page_end": int(row.page_end) if row.page_end is not None else None,
        "unit_kind": str(chunk_payload.get("unit_kind") or "").strip() or None,
        "quality_status": str(row.quality_status or artifact_payload.get("quality_status") or "").strip() or None,
        "run_id": str(row.run_id or ""),
        "target_id": str(row.target_id or ""),
        "accession_number": str(row.accession_number or "").strip() or None,
        "content_units_ref": str(row.content_units_ref or "").strip() or None,
        "normalized_text_ref": str(row.normalized_text_ref or "").strip() or None,
        "diagnostics_ref": str(row.diagnostics_ref or "").strip() or None,
        "blob_ref": str(row.blob_ref or "").strip() or None,
        "download_exchange_ref": str(row.download_exchange_ref or "").strip() or None,
        "discovery_ref": str(row.discovery_ref or "").strip() or None,
        "selection_ref": str(row.selection_ref or "").strip() or None,
        "normalized_text_sha256": str(artifact_payload.get("normalized_text_sha256") or "").strip() or None,
        "blob_sha256": str(artifact_payload.get("blob_sha256") or "").strip() or None,
        "effective_content_type": effective_content_type,
        "document_class": str(row.document_class or artifact_payload.get("document_class") or "").strip() or None,
        "page_count": int(row.page_count or 0),
        "visual_page_refs": visual_page_refs,
    }


def list_content_units_for_run(
    db: Session,
    *,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    normalized_run_id = _normalize_run_id(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")
    retrieval_count = _ensure_run_scope_is_materialized(db, run_id=normalized_run_id)
    rows = (
        db.query(ApsRetrievalChunk)
        .filter(ApsRetrievalChunk.run_id == normalized_run_id)
        .order_by(
            ApsRetrievalChunk.content_id.asc(),
            ApsRetrievalChunk.chunk_ordinal.asc(),
            ApsRetrievalChunk.target_id.asc(),
        )
        .offset(int(offset))
        .limit(int(limit))
        .all()
    )
    artifact_cache: dict[str, dict[str, Any]] = {}
    items = [_serialize_retrieval_row(row=row, artifact_cache=artifact_cache) for row in rows]
    return {
        "connector_run_id": normalized_run_id,
        "total": retrieval_count,
        "limit": int(limit),
        "offset": int(offset),
        "items": items,
    }


def search_content_units(
    db: Session,
    *,
    query_text: str,
    run_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    query_tokens = nrc_aps_content_index.normalize_query_tokens(query_text)
    if not query_tokens:
        raise ValueError("empty_query")
    unique_tokens = sorted(list(dict.fromkeys(query_tokens)))
    normalized_run_id = _normalize_run_id(run_id)
    if normalized_run_id:
        _ensure_run_scope_is_materialized(db, run_id=normalized_run_id)

    base_query = db.query(ApsRetrievalChunk)
    if normalized_run_id:
        base_query = base_query.filter(ApsRetrievalChunk.run_id == normalized_run_id)
    rows = base_query.all()
    artifact_cache: dict[str, dict[str, Any]] = {}
    ranked_rows: list[dict[str, Any]] = []

    # Omitting run_id remains schema-compatible in Phase1B, but fail-closed proof stays run-scoped.
    for row in rows:
        search_text = str(row.search_text or "")
        frequencies = Counter(nrc_aps_content_index.normalize_query_tokens(search_text))
        if any(int(frequencies.get(token, 0)) <= 0 for token in unique_tokens):
            continue
        serialized = _serialize_retrieval_row(row=row, artifact_cache=artifact_cache)
        serialized["matched_unique_query_terms"] = len(unique_tokens)
        serialized["summed_term_frequency"] = sum(int(frequencies.get(token, 0)) for token in unique_tokens)
        serialized["chunk_length"] = len(search_text)
        ranked_rows.append(serialized)

    ranked_rows.sort(
        key=lambda row: (
            -int(row.get("matched_unique_query_terms") or 0),
            -int(row.get("summed_term_frequency") or 0),
            int(row.get("chunk_length") or 0),
            str(row.get("content_id") or ""),
            int(row.get("chunk_ordinal") or 0),
            str(row.get("run_id") or ""),
            str(row.get("target_id") or ""),
        )
    )
    total = len(ranked_rows)
    paged = ranked_rows[int(offset) : int(offset) + int(limit)]
    for row in paged:
        row.pop("chunk_length", None)
    return {
        "query": str(query_text or ""),
        "query_tokens": unique_tokens,
        "total": total,
        "limit": int(limit),
        "offset": int(offset),
        "items": paged,
    }
