from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun
from app.services import nrc_aps_evidence_bundle_contract as contract
from app.services import nrc_aps_safeguards
from app.services.nrc_aps_content_index import _deserialize_visual_page_refs, _resolve_diagnostics_ref


class EvidenceBundleError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = str(code or contract.APS_RUNTIME_FAILURE_INTERNAL)
        self.message = str(message or "")
        self.status_code = int(status_code)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_scope_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return "".join(ch for ch in raw if ch.isalnum() or ch in {"_", "-", "."}) or "unknown"


def bundle_artifact_path(*, run_id: str, bundle_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_bundle_file_name(scope=scope, bundle_id=bundle_id)


def bundle_failure_artifact_path(*, run_id: str, bundle_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(scope=scope, bundle_id=bundle_id)


def find_bundle_artifact_by_id(*, bundle_id: str, reports_dir: str | Path) -> Path | None:
    candidates = sorted(Path(reports_dir).glob("*_aps_evidence_bundle_v2.json"), key=lambda path: path.name)
    for candidate in candidates:
        payload = _read_json(candidate)
        if str(payload.get("bundle_id") or "").strip() == str(bundle_id or "").strip():
            return candidate
    return None


def _resolve_bundle_artifact_path(*, bundle_id: str | None = None, bundle_ref: str | Path | None = None) -> Path:
    normalized_bundle_id = str(bundle_id or "").strip()
    normalized_bundle_ref = str(bundle_ref or "").strip()
    if bool(normalized_bundle_id) == bool(normalized_bundle_ref):
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "exactly one of bundle_id or bundle_ref is required", status_code=400)
    if normalized_bundle_ref:
        candidate_path = Path(normalized_bundle_ref)
    else:
        candidate_path = find_bundle_artifact_by_id(bundle_id=normalized_bundle_id, reports_dir=settings.connector_reports_dir)
        if candidate_path is None:
            raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "bundle not found", status_code=404)
    if not candidate_path.exists():
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "bundle not found", status_code=404)
    return candidate_path


def resolve_persisted_bundle_artifact_path(
    *,
    bundle_id: str | None = None,
    bundle_ref: str | Path | None = None,
) -> Path:
    return _resolve_bundle_artifact_path(bundle_id=bundle_id, bundle_ref=bundle_ref)


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def read_persisted_bundle_artifact_json(path: str | Path | None) -> dict[str, Any]:
    return _read_json(path)


def _validate_persisted_bundle_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID:
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_INTERNAL, "bundle schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_INTERNAL, "bundle schema version mismatch", status_code=500)
    checksum = str(payload.get("bundle_checksum") or "").strip()
    checksum_payload = dict(payload)
    checksum_payload.pop("bundle_checksum", None)
    expected_checksum = contract.compute_bundle_checksum(checksum_payload)
    if not checksum or checksum != expected_checksum:
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, "bundle checksum mismatch", status_code=500)
    mode = str(payload.get("mode") or contract.APS_MODE_BROWSE)
    results = [dict(item or {}) for item in (payload.get("results") or []) if isinstance(item, dict)]
    if not contract.is_ordering_deterministic(results, mode=mode):
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_ORDERING_VIOLATION, "persisted ordering drift", status_code=500)
    for item in results:
        if not contract.validate_snippet_bounds(item):
            raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_SNIPPET_BOUNDS, "persisted snippet bounds invalid", status_code=500)
    return payload


def load_persisted_bundle_artifact(
    *,
    bundle_id: str | None = None,
    bundle_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_bundle_artifact_path(bundle_id=bundle_id, bundle_ref=bundle_ref)
    payload = _read_json(candidate_path)
    if not payload:
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_INTERNAL, "bundle artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_bundle_payload(payload)
    validated_payload["_bundle_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _db_fingerprint() -> str:
    return hashlib.sha256(str(settings.database_url).encode("utf-8")).hexdigest()


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _serialize_index_row(*, linkage: ApsContentLinkage, document: ApsContentDocument, chunk: ApsContentChunk) -> dict[str, Any]:
    document_updated = _iso_or_none(getattr(document, "updated_at", None))
    chunk_updated = _iso_or_none(getattr(chunk, "updated_at", None))
    return {
        "content_id": str(linkage.content_id or ""),
        "chunk_id": str(chunk.chunk_id or ""),
        "content_contract_id": str(linkage.content_contract_id or ""),
        "chunking_contract_id": str(linkage.chunking_contract_id or ""),
        "normalization_contract_id": str(document.normalization_contract_id or contract.APS_NORMALIZATION_CONTRACT_ID),
        "chunk_ordinal": int(chunk.chunk_ordinal or 0),
        "start_char": int(chunk.start_char or 0),
        "end_char": int(chunk.end_char or 0),
        "chunk_text": str(chunk.chunk_text or ""),
        "chunk_text_sha256": str(chunk.chunk_text_sha256 or ""),
        "run_id": str(linkage.run_id or ""),
        "target_id": str(linkage.target_id or ""),
        "accession_number": str(linkage.accession_number or "").strip() or None,
        "content_units_ref": str(linkage.content_units_ref or "").strip() or None,
        "normalized_text_ref": str(linkage.normalized_text_ref or "").strip() or None,
        "blob_ref": str(linkage.blob_ref or "").strip() or None,
        "download_exchange_ref": str(linkage.download_exchange_ref or "").strip() or None,
        "discovery_ref": str(linkage.discovery_ref or "").strip() or None,
        "selection_ref": str(linkage.selection_ref or "").strip() or None,
        "normalized_text_sha256": str(linkage.normalized_text_sha256 or document.normalized_text_sha256 or "").strip() or None,
        "blob_sha256": str(linkage.blob_sha256 or "").strip() or None,
        "page_start": int(chunk.page_start) if chunk.page_start is not None else None,
        "page_end": int(chunk.page_end) if chunk.page_end is not None else None,
        "unit_kind": str(chunk.unit_kind or "").strip() or None,
        "quality_status": str(chunk.quality_status or document.quality_status or "").strip() or None,
        "visual_page_refs": _deserialize_visual_page_refs(document.visual_page_refs_json),
        "document_class": str(document.document_class or "").strip() or None,
        "media_type": str(document.media_type or "").strip() or None,
        "page_count": int(document.page_count or 0),
        "diagnostics_ref": _resolve_diagnostics_ref(linkage, document),
        "document_updated_at_utc": document_updated,
        "chunk_updated_at_utc": chunk_updated,
    }


def _index_signature(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "content_id": item.get("content_id"),
        "chunk_id": item.get("chunk_id"),
        "run_id": item.get("run_id"),
        "target_id": item.get("target_id"),
        "content_contract_id": item.get("content_contract_id"),
        "chunking_contract_id": item.get("chunking_contract_id"),
        "normalization_contract_id": item.get("normalization_contract_id"),
        "chunk_ordinal": item.get("chunk_ordinal"),
        "start_char": item.get("start_char"),
        "end_char": item.get("end_char"),
        "chunk_text_sha256": item.get("chunk_text_sha256"),
        "normalized_text_sha256": item.get("normalized_text_sha256"),
        "blob_sha256": item.get("blob_sha256"),
        "page_start": item.get("page_start"),
        "page_end": item.get("page_end"),
        "unit_kind": item.get("unit_kind"),
        "quality_status": item.get("quality_status"),
        "content_units_ref": item.get("content_units_ref"),
        "normalized_text_ref": item.get("normalized_text_ref"),
        "blob_ref": item.get("blob_ref"),
        "download_exchange_ref": item.get("download_exchange_ref"),
        "discovery_ref": item.get("discovery_ref"),
        "selection_ref": item.get("selection_ref"),
        "visual_page_refs": item.get("visual_page_refs", []),
        "diagnostics_ref": item.get("diagnostics_ref"),
    }


def _apply_structural_filters(query, normalized_request: dict[str, Any]):
    filters = dict(normalized_request.get("filters") or {})
    accession_numbers = [str(item) for item in (filters.get("accession_numbers") or []) if str(item).strip()]
    if accession_numbers:
        query = query.filter(ApsContentLinkage.accession_number.in_(accession_numbers))
    content_ids = [str(item) for item in (filters.get("content_ids") or []) if str(item).strip()]
    if content_ids:
        query = query.filter(ApsContentLinkage.content_id.in_(content_ids))
    target_ids = [str(item) for item in (filters.get("target_ids") or []) if str(item).strip()]
    if target_ids:
        query = query.filter(ApsContentLinkage.target_id.in_(target_ids))

    content_contract_id = str(filters.get("content_contract_id") or "").strip()
    if content_contract_id:
        if content_contract_id != contract.APS_CONTENT_CONTRACT_ID:
            raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_UNKNOWN_CONTRACT_ID, "unknown content_contract_id", status_code=422)
        query = query.filter(ApsContentLinkage.content_contract_id == content_contract_id)

    chunking_contract_id = str(filters.get("chunking_contract_id") or "").strip()
    if chunking_contract_id:
        if chunking_contract_id != contract.APS_CHUNKING_CONTRACT_ID:
            raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_UNKNOWN_CONTRACT_ID, "unknown chunking_contract_id", status_code=422)
        query = query.filter(ApsContentLinkage.chunking_contract_id == chunking_contract_id)

    normalization_contract_id = str(filters.get("normalization_contract_id") or "").strip()
    if normalization_contract_id:
        if normalization_contract_id != contract.APS_NORMALIZATION_CONTRACT_ID:
            raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_UNKNOWN_CONTRACT_ID, "unknown normalization_contract_id", status_code=422)
        query = query.filter(ApsContentDocument.normalization_contract_id == normalization_contract_id)

    return query


def _snapshot_max_updated(items: list[dict[str, Any]]) -> str | None:
    candidates: list[str] = []
    for item in items:
        doc_updated = str(item.get("document_updated_at_utc") or "").strip()
        chunk_updated = str(item.get("chunk_updated_at_utc") or "").strip()
        if doc_updated:
            candidates.append(doc_updated)
        if chunk_updated:
            candidates.append(chunk_updated)
    return max(candidates) if candidates else None


def _validated_items_for_mode(*, base_items: list[dict[str, Any]], normalized_request: dict[str, Any]) -> list[dict[str, Any]]:
    mode = str(normalized_request.get("mode") or contract.APS_MODE_BROWSE)
    query_tokens = list(normalized_request.get("query_tokens") or [])
    results: list[dict[str, Any]] = []
    for row in base_items:
        missing = contract.missing_provenance_fields(row)
        if missing:
            raise EvidenceBundleError(
                contract.APS_RUNTIME_FAILURE_PROVENANCE_MISSING,
                f"missing required provenance fields: {', '.join(sorted(missing))}",
                status_code=422,
            )
        unresolved = contract.unresolvable_provenance_fields(row)
        if unresolved:
            raise EvidenceBundleError(
                contract.APS_RUNTIME_FAILURE_PROVENANCE_UNRESOLVABLE,
                f"unresolvable provenance fields: {', '.join(sorted(unresolved))}",
                status_code=422,
            )
        if not contract.validate_known_contract_ids(row):
            raise EvidenceBundleError(
                contract.APS_RUNTIME_FAILURE_UNKNOWN_CONTRACT_ID,
                "unknown contract id in content index row",
                status_code=422,
            )

        payload = dict(row)
        frequencies = contract.token_frequencies(str(payload.get("chunk_text") or ""))
        if mode == contract.APS_MODE_QUERY:
            if any(int(frequencies.get(token, 0)) <= 0 for token in query_tokens):
                continue
            payload["matched_unique_query_terms"] = len(query_tokens)
            payload["summed_term_frequency"] = sum(int(frequencies.get(token, 0)) for token in query_tokens)
        else:
            payload["matched_unique_query_terms"] = 0
            payload["summed_term_frequency"] = 0
        payload["chunk_length"] = len(str(payload.get("chunk_text") or ""))
        snippet = contract.build_snippet(
            chunk_text=str(payload.get("chunk_text") or ""),
            mode=mode,
            query_tokens=query_tokens,
        )
        payload.update(snippet)
        payload["group_id"] = contract.group_id_for_item(payload)
        if not contract.validate_snippet_bounds(payload):
            raise EvidenceBundleError(
                contract.APS_RUNTIME_FAILURE_SNIPPET_BOUNDS,
                f"snippet bounds violation for chunk_id={payload.get('chunk_id')}",
                status_code=500,
            )
        results.append(payload)
    ordered = contract.ordered_items(results, mode=mode)
    if not contract.is_ordering_deterministic(ordered, mode=mode):
        raise EvidenceBundleError(
            contract.APS_RUNTIME_FAILURE_ORDERING_VIOLATION,
            "ordering contract violation",
            status_code=500,
        )
    return ordered


def _persist_or_validate_bundle(*, artifact_path: Path, payload: dict[str, Any]) -> str:
    if artifact_path.exists():
        existing_payload = _read_json(artifact_path)
        existing_checksum = str(existing_payload.get("bundle_checksum") or "").strip()
        expected_checksum = str(payload.get("bundle_checksum") or "").strip()
        existing_bundle_id = str(existing_payload.get("bundle_id") or "").strip()
        expected_bundle_id = str(payload.get("bundle_id") or "").strip()
        if (
            existing_payload
            and existing_checksum
            and expected_checksum
            and existing_checksum == expected_checksum
            and existing_bundle_id == expected_bundle_id
        ):
            return str(artifact_path)
        if existing_payload and existing_bundle_id and existing_bundle_id == expected_bundle_id:
            return str(artifact_path)
        raise EvidenceBundleError(
            contract.APS_RUNTIME_FAILURE_WRITE_FAILED,
            "existing persisted bundle conflicts with immutable checksum",
            status_code=500,
        )
    return nrc_aps_safeguards.write_json_atomic(artifact_path, payload)


def _persist_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun,
    normalized_request: dict[str, Any],
    error_code: str,
    error_message: str,
) -> str:
    request_identity = contract.request_identity_hash(normalized_request)
    failure_bundle_id = contract.derive_failure_bundle_id(request_identity_hash_value=request_identity)
    failure_payload = {
        "schema_id": contract.APS_EVIDENCE_BUNDLE_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "bundle_id": failure_bundle_id,
        "run_id": str(run.connector_run_id),
        "request_contract_id": contract.APS_EVIDENCE_REQUEST_NORM_CONTRACT_ID,
        "request_identity_hash": request_identity,
        "mode": str(normalized_request.get("mode") or ""),
        "query": normalized_request.get("query"),
        "query_tokens": list(normalized_request.get("query_tokens") or []),
        "normalized_request": contract.request_identity_payload(normalized_request),
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["bundle_checksum"] = contract.compute_bundle_checksum(failure_payload)
    failure_path = bundle_failure_artifact_path(
        run_id=run.connector_run_id,
        bundle_id=failure_bundle_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_bundle_report_refs") or {})
    failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_bundle_failures") or []) if str(item).strip()]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_evidence_bundle_report_refs": {
            "aps_evidence_bundles": [str(item).strip() for item in list(existing_refs.get("aps_evidence_bundles") or []) if str(item).strip()],
            "aps_evidence_bundle_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def _append_bundle_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_bundle_id = str(entry.get("bundle_id") or "").strip()
    incoming_request_identity = str(entry.get("request_identity_hash") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_identity = (
            str(item.get("bundle_id") or "").strip() == incoming_bundle_id
            and str(item.get("request_identity_hash") or "").strip() == incoming_request_identity
        )
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_identity or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("bundle_id") or ""), str(item.get("ref") or "")))
    return kept


def _with_pagination(
    *,
    payload: dict[str, Any],
    limit: int,
    offset: int,
) -> dict[str, Any]:
    items = [dict(item or {}) for item in (payload.get("results") or []) if isinstance(item, dict)]
    mode = str(payload.get("mode") or contract.APS_MODE_BROWSE)
    paged_items = items[offset : offset + limit]
    groups = contract.grouped_page(paged_items, mode=mode)
    return {
        "schema_id": str(payload.get("schema_id") or contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION),
        "bundle_id": str(payload.get("bundle_id") or ""),
        "bundle_checksum": str(payload.get("bundle_checksum") or ""),
        "bundle_ref": str(payload.get("_bundle_ref") or "") or None,
        "mode": mode,
        "query": payload.get("query"),
        "query_tokens": list(payload.get("query_tokens") or []),
        "request_identity_hash": str(payload.get("request_identity_hash") or ""),
        "snapshot": dict(payload.get("snapshot") or {}),
        "total_hits": int(payload.get("total_hits") or 0),
        "total_groups": int(payload.get("total_groups") or 0),
        "limit": int(limit),
        "offset": int(offset),
        "items": paged_items,
        "groups": groups,
        "persisted": bool(payload.get("_persisted", False)),
    }


def assemble_evidence_bundle(
    db: Session,
    *,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        status_code = 422 if code in {contract.APS_RUNTIME_FAILURE_INVALID_QUERY, contract.APS_RUNTIME_FAILURE_INVALID_REQUEST} else 400
        raise EvidenceBundleError(code, f"invalid request: {code}", status_code=status_code) from None

    persist_bundle = bool(normalized_request.get("persist_bundle", False))
    run_id = str(normalized_request.get("run_id") or "")
    run = db.get(ConnectorRun, run_id)
    if not run:
        raise EvidenceBundleError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "connector run not found", status_code=404)

    try:
        snapshot_started = _utc_iso()
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
            .filter(ApsContentLinkage.run_id == run_id)
        )
        query = _apply_structural_filters(query, normalized_request)
        base_rows = [_serialize_index_row(linkage=row[0], document=row[1], chunk=row[2]) for row in query.all()]
        ordered_items = _validated_items_for_mode(base_items=base_rows, normalized_request=normalized_request)
        for row in ordered_items:
            row.pop("chunk_length", None)

        index_max_updated = _snapshot_max_updated(ordered_items)
        index_state_payload = {
            "rows": [_index_signature(item) for item in ordered_items],
            "row_count": len(ordered_items),
            "index_max_updated_at_utc": index_max_updated,
        }
        index_state_hash = contract.stable_hash(index_state_payload)
        request_identity = contract.request_identity_hash(normalized_request)
        bundle_id = contract.derive_bundle_id(
            request_identity_hash_value=request_identity,
            index_state_hash=index_state_hash,
        )
        snapshot_completed = _utc_iso()

        bundle_payload = {
            "schema_id": contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID,
            "schema_version": contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "generated_at_utc": snapshot_completed,
            "request_contract_id": contract.APS_EVIDENCE_REQUEST_NORM_CONTRACT_ID,
            "ranking_contract_id": contract.APS_EVIDENCE_RANKING_CONTRACT_ID,
            "snippet_contract_id": contract.APS_EVIDENCE_SNIPPET_CONTRACT_ID,
            "snapshot_contract_id": contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID,
            "bundle_id": bundle_id,
            "request_identity_hash": request_identity,
            "mode": str(normalized_request.get("mode") or ""),
            "run_id": run_id,
            "query": normalized_request.get("query"),
            "query_tokens": list(normalized_request.get("query_tokens") or []),
            "normalized_request": contract.request_identity_payload(normalized_request),
            "snapshot": {
                "snapshot_contract_id": contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID,
                "snapshot_started_at_utc": snapshot_started,
                "snapshot_completed_at_utc": snapshot_completed,
                "index_state_hash": index_state_hash,
                "index_row_count": len(ordered_items),
                "index_max_updated_at_utc": index_max_updated,
                "db_fingerprint": _db_fingerprint(),
                "read_scope": {
                    "run_id": run_id,
                    "filters": dict(normalized_request.get("filters") or {}),
                },
            },
            "total_hits": len(ordered_items),
            "total_groups": contract.total_group_count(ordered_items),
            "results": ordered_items,
        }
        bundle_payload["bundle_checksum"] = contract.compute_bundle_checksum(bundle_payload)

        if persist_bundle:
            if len(ordered_items) > contract.APS_MAX_BUNDLE_CHUNKS:
                raise EvidenceBundleError(
                    contract.APS_RUNTIME_FAILURE_SIZE_LIMIT,
                    f"bundle chunk count exceeds cap ({contract.APS_MAX_BUNDLE_CHUNKS})",
                    status_code=422,
                )
            if len(contract.canonical_json_bytes(bundle_payload)) > contract.APS_MAX_BUNDLE_BYTES:
                raise EvidenceBundleError(
                    contract.APS_RUNTIME_FAILURE_SIZE_LIMIT,
                    f"bundle byte size exceeds cap ({contract.APS_MAX_BUNDLE_BYTES})",
                    status_code=422,
                )
            bundle_path = bundle_artifact_path(
                run_id=run_id,
                bundle_id=bundle_id,
                reports_dir=settings.connector_reports_dir,
            )
            bundle_ref = _persist_or_validate_bundle(artifact_path=bundle_path, payload=bundle_payload)
            persisted_payload = _read_json(bundle_ref)
            if persisted_payload:
                bundle_payload = persisted_payload
            existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_bundle_report_refs") or {})
            bundle_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_bundles") or []) if str(item).strip()]
            if bundle_ref not in bundle_refs:
                bundle_refs.append(bundle_ref)
            failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_bundle_failures") or []) if str(item).strip()]
            summaries = _append_bundle_summary(
                (run.query_plan_json or {}).get("aps_evidence_bundle_summaries"),
                {
                    "bundle_id": bundle_id,
                    "request_identity_hash": request_identity,
                    "mode": str(normalized_request.get("mode") or ""),
                    "total_hits": len(ordered_items),
                    "total_groups": contract.total_group_count(ordered_items),
                    "ref": bundle_ref,
                    "snapshot": dict(bundle_payload.get("snapshot") or {}),
                },
            )
            run.query_plan_json = {
                **(run.query_plan_json or {}),
                "aps_evidence_bundle_report_refs": {
                    "aps_evidence_bundles": bundle_refs,
                    "aps_evidence_bundle_failures": failure_refs,
                },
                "aps_evidence_bundle_summaries": summaries,
            }
            db.commit()
            bundle_payload["_bundle_ref"] = bundle_ref
            bundle_payload["_persisted"] = True
        else:
            bundle_payload["_bundle_ref"] = None
            bundle_payload["_persisted"] = False

        return _with_pagination(
            payload=bundle_payload,
            limit=int(normalized_request.get("limit") or 0),
            offset=int(normalized_request.get("offset") or 0),
        )
    except EvidenceBundleError as exc:
        if persist_bundle:
            _persist_failure_artifact(
                db,
                run=run,
                normalized_request=normalized_request,
                error_code=exc.code,
                error_message=exc.message,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_bundle:
            _persist_failure_artifact(
                db,
                run=run,
                normalized_request=normalized_request,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise EvidenceBundleError(
            contract.APS_RUNTIME_FAILURE_INTERNAL,
            str(exc),
            status_code=500,
        ) from exc


def get_persisted_bundle_page(
    *,
    bundle_id: str,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_bundle_artifact(bundle_id=bundle_id)
    mode = str(payload.get("mode") or contract.APS_MODE_BROWSE)
    resolved_limit, resolved_offset = contract.resolve_limit_offset(
        mode=mode,
        limit_value=limit,
        offset_value=offset,
    )
    return _with_pagination(payload=payload, limit=resolved_limit, offset=resolved_offset)
