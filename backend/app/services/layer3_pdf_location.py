from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import ApsContentChunk, ApsContentDocument, L3PassRun


PDF_LOCATION_PROJECTION_SCHEMA_ID = "layer3.pdf_location_projection.v1"
PDF_LOCATION_AUTHORITY_CONTRACT = "aps_content_document_chunk_page_refs_and_citation_highlight_spans"
PDF_LOCATION_USE_CASE = "pdf_location_from_aps_content_document_citation"
PDF_LOCATION_NEXT_ACTION = "implement_read_only_pdf_location_projection_from_existing_authority"
SOURCE_SHAPE_APS_CONTENT_DOCUMENT = "aps_content_document"
CITATION_HIGHLIGHT_AUTHORITY = "citations[].highlight_spans"
_ADMITTED_PASS_STATUSES = {"completed", "completed_with_warnings"}
_FORBIDDEN_RUNTIME = (
    "raw_pdf_blob_streaming",
    "pdf_byte_download",
    "provider_or_object_store_url_exposure",
    "browser_owned_authoritative_pdf_location",
    "new_source_family_runtime",
    "local_upload",
    "local_directory_ingestion",
    "arbitrary_local_path_input",
    "rag_vector_retrieval",
    "connector_destination_dispatch",
    "package_mutation",
    "auth_security_behavior_change",
    "full_durable_mockup_activation",
    "frontend_only_durable_authority",
)


def unavailable_pdf_location_projection(
    reason: str,
    *,
    session_id: str | None = None,
    pass_run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_id": PDF_LOCATION_PROJECTION_SCHEMA_ID,
        "schema_version": 1,
        "available": False,
        "state": "unavailable",
        "blocked_reason": reason,
        "named_runtime_use_case": PDF_LOCATION_USE_CASE,
        "selected_source_family": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        "server_authority_contract": PDF_LOCATION_AUTHORITY_CONTRACT,
        "next_allowed_action": PDF_LOCATION_NEXT_ACTION,
        "session_id": session_id,
        "pass_run_id": pass_run_id,
        "location_items": [],
        "visual_page_refs": [],
        "no_side_effects": True,
        "forbidden_runtime": list(_FORBIDDEN_RUNTIME),
    }


def pdf_location_projection_for_session(db: Session, *, session_id: str) -> dict[str, Any]:
    pass_runs = (
        db.query(L3PassRun)
        .filter(L3PassRun.session_id == session_id)
        .filter(L3PassRun.output_payload_ref.isnot(None))
        .order_by(L3PassRun.completed_at.desc(), L3PassRun.started_at.desc(), L3PassRun.pass_run_id.desc())
        .all()
    )
    last_unavailable: dict[str, Any] | None = None
    for pass_run in pass_runs:
        projection = pdf_location_projection_for_pass_run(db, pass_run=pass_run)
        if projection.get("available") is True:
            return projection
        last_unavailable = projection
    if last_unavailable is not None:
        return last_unavailable
    return unavailable_pdf_location_projection(
        "pdf_location_no_completed_aps_content_document_output",
        session_id=session_id,
    )


def pdf_location_projection_for_pass_run(db: Session, *, pass_run: L3PassRun) -> dict[str, Any]:
    if str(pass_run.status or "") not in _ADMITTED_PASS_STATUSES:
        return unavailable_pdf_location_projection(
            "pdf_location_pass_run_not_completed",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )
    payload, error = _read_output_payload(pass_run)
    if error is not None:
        return unavailable_pdf_location_projection(
            error,
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )
    assert payload is not None
    payload_identity_error = _payload_identity_error(payload, pass_run)
    if payload_identity_error is not None:
        return unavailable_pdf_location_projection(
            payload_identity_error,
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )
    document_identity = payload.get("document_identity")
    if not isinstance(document_identity, dict):
        return unavailable_pdf_location_projection(
            "pdf_location_document_identity_missing",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )
    if str(payload.get("source_shape") or "").strip() != SOURCE_SHAPE_APS_CONTENT_DOCUMENT:
        return unavailable_pdf_location_projection(
            "pdf_location_source_shape_not_aps_content_document",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )

    content_id = _string(document_identity.get("content_id"))
    content_contract_id = _string(document_identity.get("content_contract_id"))
    chunking_contract_id = _string(document_identity.get("chunking_contract_id"))
    if not content_id or not content_contract_id or not chunking_contract_id:
        return unavailable_pdf_location_projection(
            "pdf_location_document_authority_incomplete",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )

    document = (
        db.query(ApsContentDocument)
        .filter(ApsContentDocument.content_id == content_id)
        .filter(ApsContentDocument.content_contract_id == content_contract_id)
        .filter(ApsContentDocument.chunking_contract_id == chunking_contract_id)
        .one_or_none()
    )
    if document is None:
        return unavailable_pdf_location_projection(
            "pdf_location_document_authority_missing",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )
    if _string(document.media_type).lower() != "application/pdf":
        return unavailable_pdf_location_projection(
            "pdf_location_document_not_pdf",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )
    visual_page_refs = _visual_page_refs(document.visual_page_refs_json)
    if not visual_page_refs:
        return unavailable_pdf_location_projection(
            "pdf_location_visual_page_authority_missing",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )

    chunk_ids = _ordered_chunk_ids(payload)
    if not chunk_ids:
        return unavailable_pdf_location_projection(
            "pdf_location_chunk_authority_missing",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )
    chunks = (
        db.query(ApsContentChunk)
        .filter(ApsContentChunk.content_id == content_id)
        .filter(ApsContentChunk.content_contract_id == content_contract_id)
        .filter(ApsContentChunk.chunking_contract_id == chunking_contract_id)
        .filter(ApsContentChunk.chunk_id.in_(chunk_ids))
        .all()
    )
    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    if any(chunk_id not in chunks_by_id for chunk_id in chunk_ids):
        return unavailable_pdf_location_projection(
            "pdf_location_chunk_authority_missing",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )

    output_items_by_chunk = _output_items_by_chunk(payload)
    payload_chunk_hashes = _payload_chunk_hashes(payload)
    for chunk_id in chunk_ids:
        expected_hash = payload_chunk_hashes.get(chunk_id)
        if not expected_hash:
            return unavailable_pdf_location_projection(
                "pdf_location_chunk_hash_authority_missing",
                session_id=pass_run.session_id,
                pass_run_id=pass_run.pass_run_id,
            )
        if _string(chunks_by_id[chunk_id].chunk_text_sha256) != expected_hash:
            return unavailable_pdf_location_projection(
                "pdf_location_chunk_hash_mismatch",
                session_id=pass_run.session_id,
                pass_run_id=pass_run.pass_run_id,
            )

    location_items: list[dict[str, Any]] = []
    for chunk_id in chunk_ids:
        chunk = chunks_by_id[chunk_id]
        if chunk.page_start is None or chunk.page_end is None:
            return unavailable_pdf_location_projection(
                "pdf_location_page_authority_missing",
                session_id=pass_run.session_id,
                pass_run_id=pass_run.pass_run_id,
            )
        output_item = output_items_by_chunk.get(chunk_id, {})
        highlight_spans = _highlight_spans(output_item)
        if not highlight_spans:
            return unavailable_pdf_location_projection(
                "pdf_location_highlight_authority_missing",
                session_id=pass_run.session_id,
                pass_run_id=pass_run.pass_run_id,
            )
        location_items.append(
            {
                "item_ref": _string(output_item.get("item_ref")) or f"chunk:{chunk.chunk_id}",
                "content_id": content_id,
                "chunk_id": chunk.chunk_id,
                "chunk_ordinal": chunk.chunk_ordinal,
                "page_start": int(chunk.page_start),
                "page_end": int(chunk.page_end),
                "page_label": _page_label(chunk.page_start, chunk.page_end),
                "chunk_text_sha256": chunk.chunk_text_sha256,
                "highlight_spans": highlight_spans,
                "bounded_text_preview": _bounded_preview(chunk.chunk_text),
                "authority_source": "ApsContentChunk.page_start/ApsContentChunk.page_end",
                "trace": {
                    "session_id": pass_run.session_id,
                    "analysis_plan_id": pass_run.analysis_plan_id,
                    "pass_run_id": pass_run.pass_run_id,
                    "material_snapshot_id": payload.get("material_snapshot_id"),
                    "analysis_unit_id": payload.get("analysis_unit_id"),
                    "content_id": content_id,
                    "chunk_id": chunk.chunk_id,
                    "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
                },
            }
        )
    if not location_items:
        return unavailable_pdf_location_projection(
            "pdf_location_page_authority_missing",
            session_id=pass_run.session_id,
            pass_run_id=pass_run.pass_run_id,
        )

    return {
        "schema_id": PDF_LOCATION_PROJECTION_SCHEMA_ID,
        "schema_version": 1,
        "available": True,
        "state": "available",
        "blocked_reason": None,
        "named_runtime_use_case": PDF_LOCATION_USE_CASE,
        "selected_source_family": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        "server_authority_contract": PDF_LOCATION_AUTHORITY_CONTRACT,
        "next_allowed_action": PDF_LOCATION_NEXT_ACTION,
        "session_id": pass_run.session_id,
        "pass_run_id": pass_run.pass_run_id,
        "analysis_plan_id": pass_run.analysis_plan_id,
        "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        "authority_source": "read_only_aps_content_document_chunk_page_refs",
        "citation_highlight_authority": CITATION_HIGHLIGHT_AUTHORITY,
        "document_identity": {
            "content_id": document.content_id,
            "content_contract_id": document.content_contract_id,
            "chunking_contract_id": document.chunking_contract_id,
            "normalization_contract_id": document.normalization_contract_id,
            "content_status": document.content_status,
            "media_type": document.media_type,
            "document_class": document.document_class,
            "quality_status": document.quality_status,
            "page_count": document.page_count,
            "visual_page_ref_count": len(visual_page_refs),
        },
        "visual_page_refs": visual_page_refs,
        "location_items": location_items,
        "no_side_effects": True,
        "forbidden_runtime": list(_FORBIDDEN_RUNTIME),
    }


def _read_output_payload(pass_run: L3PassRun) -> tuple[dict[str, Any] | None, str | None]:
    output_ref = _string(pass_run.output_payload_ref)
    if not output_ref:
        return None, "pdf_location_output_payload_ref_missing"
    output_path = Path(output_ref)
    if not output_path.exists() or not output_path.is_file():
        return None, "pdf_location_output_payload_missing"
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "pdf_location_output_payload_unreadable"
    if not isinstance(payload, dict):
        return None, "pdf_location_output_payload_malformed"
    return payload, None


def _payload_identity_error(payload: dict[str, Any], pass_run: L3PassRun) -> str | None:
    expected_values = {
        "session_id": pass_run.session_id,
        "analysis_plan_id": pass_run.analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
    }
    for key, expected in expected_values.items():
        if _string(payload.get(key)) != _string(expected):
            return f"pdf_location_payload_{key}_mismatch"
    return None


def _ordered_chunk_ids(payload: dict[str, Any]) -> list[str]:
    chunk_ids: list[str] = []
    output_items = payload.get("output_items_json")
    if isinstance(output_items, list):
        for item in output_items:
            if isinstance(item, dict):
                chunk_id = _string(item.get("chunk_id"))
                if chunk_id and chunk_id not in chunk_ids:
                    chunk_ids.append(chunk_id)
    chunk_summary = payload.get("chunk_summary")
    summary_ids = chunk_summary.get("chunk_ids") if isinstance(chunk_summary, dict) else None
    if isinstance(summary_ids, list):
        for raw_chunk_id in summary_ids:
            chunk_id = _string(raw_chunk_id)
            if chunk_id and chunk_id not in chunk_ids:
                chunk_ids.append(chunk_id)
    return chunk_ids


def _payload_chunk_hashes(payload: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    output_items = payload.get("output_items_json")
    if isinstance(output_items, list):
        for item in output_items:
            if not isinstance(item, dict):
                continue
            _record_payload_chunk_hash(
                hashes,
                item.get("chunk_id"),
                item.get("chunk_text_sha256") or item.get("chunk_hash") or item.get("chunk_sha256"),
            )

    chunk_summary = payload.get("chunk_summary")
    if isinstance(chunk_summary, dict):
        summary_hashes = chunk_summary.get("chunk_hashes")
        if isinstance(summary_hashes, dict):
            for chunk_id, chunk_hash in summary_hashes.items():
                _record_payload_chunk_hash(hashes, chunk_id, chunk_hash)
        elif isinstance(summary_hashes, list):
            for item in summary_hashes:
                if isinstance(item, dict):
                    _record_payload_chunk_hash(
                        hashes,
                        item.get("chunk_id"),
                        item.get("chunk_text_sha256") or item.get("chunk_hash") or item.get("sha256"),
                    )
    return hashes


def _record_payload_chunk_hash(hashes: dict[str, str], raw_chunk_id: Any, raw_hash: Any) -> None:
    chunk_id = _string(raw_chunk_id)
    chunk_hash = _string(raw_hash)
    if chunk_id and chunk_hash and chunk_id not in hashes:
        hashes[chunk_id] = chunk_hash


def _output_items_by_chunk(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output_items = payload.get("output_items_json")
    if not isinstance(output_items, list):
        return {}
    by_chunk: dict[str, dict[str, Any]] = {}
    for item in output_items:
        if not isinstance(item, dict):
            continue
        chunk_id = _string(item.get("chunk_id"))
        if chunk_id and chunk_id not in by_chunk:
            by_chunk[chunk_id] = item
    return by_chunk


def _highlight_spans(output_item: dict[str, Any]) -> list[dict[str, Any]]:
    spans = output_item.get("highlight_spans")
    if not isinstance(spans, list):
        return []
    safe_spans: list[dict[str, Any]] = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        safe_spans.append(
            {
                "start": _safe_int(span.get("start")),
                "end": _safe_int(span.get("end")),
                "source": _string(span.get("source")) or CITATION_HIGHLIGHT_AUTHORITY,
            }
        )
    return safe_spans


def _visual_page_refs(raw_value: str | None) -> list[dict[str, Any]]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    refs: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        page_number = _safe_int(item.get("page_number"))
        if page_number is None:
            continue
        refs.append(
            {
                "page_number": page_number,
                "status": _string(item.get("status")) or "preserved",
            }
        )
    return refs


def _page_label(page_start: int, page_end: int) -> str:
    if page_start == page_end:
        return f"p. {page_start}"
    return f"pp. {page_start}-{page_end}"


def _bounded_preview(text: str, *, limit: int = 160) -> str:
    collapsed = " ".join(_string(text).split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string(value: Any) -> str:
    return str(value or "").strip()
