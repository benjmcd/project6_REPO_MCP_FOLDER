from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage
from app.services import aps_retrieval_plane_read
from app.services import nrc_aps_content_index
from app.services import nrc_aps_sync_drift


APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_ID = "aps.retrieval_cutover_proof.v1"
APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_VERSION = 1

APS_RETRIEVAL_CUTOVER_VERDICT_MATCH = "match"
APS_RETRIEVAL_CUTOVER_VERDICT_PAYLOAD_MISMATCH = "payload_mismatch"
APS_RETRIEVAL_CUTOVER_VERDICT_ORDER_MISMATCH = "order_mismatch"
APS_RETRIEVAL_CUTOVER_VERDICT_EMPTY_RUNTIME = "empty_runtime"
APS_RETRIEVAL_CUTOVER_VERDICT_RETRIEVAL_NOT_MATERIALIZED = "retrieval_not_materialized"

DEFAULT_LIST_LIMIT = 5000
DEFAULT_SEARCH_LIMIT = 5000


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_run_id(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


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


def _derive_search_query_from_canonical_run(db: Session, *, run_id: str) -> str | None:
    normalized_run_id = _normalize_run_id(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")
    rows = (
        db.query(ApsContentChunk.chunk_text)
        .join(
            ApsContentLinkage,
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
        .all()
    )
    unique_tokens: list[str] = []
    seen: set[str] = set()
    for (chunk_text,) in rows:
        for token in nrc_aps_content_index.normalize_query_tokens(chunk_text):
            if token in seen:
                continue
            seen.add(token)
            unique_tokens.append(token)
            if len(unique_tokens) >= 2:
                return " ".join(unique_tokens)
    if unique_tokens:
        return " ".join(unique_tokens)
    return None


def _stable_item_key(item: dict[str, Any]) -> str:
    return json.dumps(dict(item or {}), sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _compare_payloads(*, canonical_payload: dict[str, Any], retrieval_payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if canonical_payload == retrieval_payload:
        return APS_RETRIEVAL_CUTOVER_VERDICT_MATCH, {
            "reason": "payloads_equal",
            "mismatch_fields": [],
        }

    canonical_items = [dict(item or {}) for item in (canonical_payload.get("items") or []) if isinstance(item, dict)]
    retrieval_items = [dict(item or {}) for item in (retrieval_payload.get("items") or []) if isinstance(item, dict)]
    canonical_without_items = dict(canonical_payload)
    retrieval_without_items = dict(retrieval_payload)
    canonical_without_items["items"] = []
    retrieval_without_items["items"] = []

    if canonical_without_items == retrieval_without_items:
        canonical_counter = Counter(_stable_item_key(item) for item in canonical_items)
        retrieval_counter = Counter(_stable_item_key(item) for item in retrieval_items)
        if canonical_counter == retrieval_counter:
            return APS_RETRIEVAL_CUTOVER_VERDICT_ORDER_MISMATCH, {
                "reason": "same_items_different_order",
                "mismatch_fields": [],
            }

    mismatch_fields = sorted(
        [
            key
            for key in set(canonical_payload.keys()) | set(retrieval_payload.keys())
            if canonical_payload.get(key) != retrieval_payload.get(key)
        ]
    )
    return APS_RETRIEVAL_CUTOVER_VERDICT_PAYLOAD_MISMATCH, {
        "reason": "payload_values_differ",
        "mismatch_fields": mismatch_fields,
    }


def _build_check(
    *,
    surface: str,
    verdict: str,
    canonical_payload: dict[str, Any] | None,
    retrieval_payload: dict[str, Any] | None,
    detail: dict[str, Any],
) -> dict[str, Any]:
    return {
        "surface": surface,
        "verdict": verdict,
        "canonical_total": int((canonical_payload or {}).get("total") or 0),
        "retrieval_total": int((retrieval_payload or {}).get("total") or 0),
        "detail": dict(detail or {}),
    }


def validate_retrieval_cutover_for_run(
    db: Session,
    *,
    run_id: str,
    query_text: str | None = None,
) -> dict[str, Any]:
    normalized_run_id = _normalize_run_id(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")

    canonical_row_count = _canonical_row_count_for_run(db, run_id=normalized_run_id)
    if canonical_row_count <= 0:
        empty_check = _build_check(
            surface="content_units",
            verdict=APS_RETRIEVAL_CUTOVER_VERDICT_EMPTY_RUNTIME,
            canonical_payload=None,
            retrieval_payload=None,
            detail={"reason": "no_canonical_rows_for_run"},
        )
        return {
            "schema_id": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_ID,
            "schema_version": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_VERSION,
            "generated_at_utc": _utc_iso(),
            "run_id": normalized_run_id,
            "query_text": None,
            "passed": False,
            "overall_verdict": APS_RETRIEVAL_CUTOVER_VERDICT_EMPTY_RUNTIME,
            "checks": [
                empty_check,
                dict(empty_check, surface="content_search"),
            ],
        }

    effective_query_text = str(query_text or "").strip() or _derive_search_query_from_canonical_run(db, run_id=normalized_run_id)
    if not effective_query_text:
        mismatch_check = _build_check(
            surface="content_search",
            verdict=APS_RETRIEVAL_CUTOVER_VERDICT_PAYLOAD_MISMATCH,
            canonical_payload=None,
            retrieval_payload=None,
            detail={"reason": "unable_to_derive_run_scoped_search_query"},
        )
        return {
            "schema_id": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_ID,
            "schema_version": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_VERSION,
            "generated_at_utc": _utc_iso(),
            "run_id": normalized_run_id,
            "query_text": None,
            "passed": False,
            "overall_verdict": APS_RETRIEVAL_CUTOVER_VERDICT_PAYLOAD_MISMATCH,
            "checks": [
                _build_check(
                    surface="content_units",
                    verdict=APS_RETRIEVAL_CUTOVER_VERDICT_MATCH,
                    canonical_payload={"total": canonical_row_count},
                    retrieval_payload={"total": canonical_row_count},
                    detail={"reason": "units_not_evaluated_due_to_search_query_derivation_failure"},
                ),
                mismatch_check,
            ],
        }

    canonical_list = nrc_aps_content_index.list_content_units_for_run(
        db,
        run_id=normalized_run_id,
        limit=DEFAULT_LIST_LIMIT,
        offset=0,
    )
    canonical_search = nrc_aps_content_index.search_content_units(
        db,
        query_text=effective_query_text,
        run_id=normalized_run_id,
        limit=DEFAULT_SEARCH_LIMIT,
        offset=0,
    )

    try:
        retrieval_list = aps_retrieval_plane_read.list_content_units_for_run(
            db,
            run_id=normalized_run_id,
            limit=DEFAULT_LIST_LIMIT,
            offset=0,
        )
        retrieval_search = aps_retrieval_plane_read.search_content_units(
            db,
            query_text=effective_query_text,
            run_id=normalized_run_id,
            limit=DEFAULT_SEARCH_LIMIT,
            offset=0,
        )
    except aps_retrieval_plane_read.RetrievalPlaneReadError as exc:
        checks = [
            _build_check(
                surface="content_units",
                verdict=APS_RETRIEVAL_CUTOVER_VERDICT_RETRIEVAL_NOT_MATERIALIZED,
                canonical_payload=canonical_list,
                retrieval_payload=None,
                detail={"code": exc.code, "message": exc.message},
            ),
            _build_check(
                surface="content_search",
                verdict=APS_RETRIEVAL_CUTOVER_VERDICT_RETRIEVAL_NOT_MATERIALIZED,
                canonical_payload=canonical_search,
                retrieval_payload=None,
                detail={"code": exc.code, "message": exc.message},
            ),
        ]
        return {
            "schema_id": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_ID,
            "schema_version": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_VERSION,
            "generated_at_utc": _utc_iso(),
            "run_id": normalized_run_id,
            "query_text": effective_query_text,
            "passed": False,
            "overall_verdict": APS_RETRIEVAL_CUTOVER_VERDICT_RETRIEVAL_NOT_MATERIALIZED,
            "checks": checks,
        }

    list_verdict, list_detail = _compare_payloads(canonical_payload=canonical_list, retrieval_payload=retrieval_list)
    search_verdict, search_detail = _compare_payloads(canonical_payload=canonical_search, retrieval_payload=retrieval_search)
    checks = [
        _build_check(
            surface="content_units",
            verdict=list_verdict,
            canonical_payload=canonical_list,
            retrieval_payload=retrieval_list,
            detail=list_detail,
        ),
        _build_check(
            surface="content_search",
            verdict=search_verdict,
            canonical_payload=canonical_search,
            retrieval_payload=retrieval_search,
            detail=search_detail,
        ),
    ]

    verdict_priority = [
        APS_RETRIEVAL_CUTOVER_VERDICT_RETRIEVAL_NOT_MATERIALIZED,
        APS_RETRIEVAL_CUTOVER_VERDICT_EMPTY_RUNTIME,
        APS_RETRIEVAL_CUTOVER_VERDICT_PAYLOAD_MISMATCH,
        APS_RETRIEVAL_CUTOVER_VERDICT_ORDER_MISMATCH,
        APS_RETRIEVAL_CUTOVER_VERDICT_MATCH,
    ]
    observed_verdicts = {str(check.get("verdict") or "") for check in checks}
    overall_verdict = APS_RETRIEVAL_CUTOVER_VERDICT_MATCH
    for candidate in verdict_priority:
        if candidate in observed_verdicts:
            overall_verdict = candidate
            break

    return {
        "schema_id": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_ID,
        "schema_version": APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": normalized_run_id,
        "query_text": effective_query_text,
        "passed": overall_verdict == APS_RETRIEVAL_CUTOVER_VERDICT_MATCH,
        "overall_verdict": overall_verdict,
        "checks": checks,
    }


def run_retrieval_cutover_gate(
    *,
    run_id: str,
    query_text: str | None = None,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        report = validate_retrieval_cutover_for_run(db, run_id=run_id, query_text=query_text)
    finally:
        db.close()
    return report


def write_retrieval_cutover_report(report: dict[str, Any], *, report_path: str | Path) -> str:
    return nrc_aps_sync_drift.write_json_deterministic(report_path, report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate NRC APS retrieval cutover proof for one run scope.")
    parser.add_argument("--run-id", required=True, help="Run id to validate.")
    parser.add_argument(
        "--query",
        default="",
        help="Optional explicit run-scoped search query. When omitted, a deterministic query is derived from canonical chunk text.",
    )
    args = parser.parse_args(argv)
    report = run_retrieval_cutover_gate(
        run_id=str(args.run_id or ""),
        query_text=str(args.query or "").strip() or None,
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
