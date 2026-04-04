"""
Bridge **Backend — Document Processing & Storage** outputs into the
**Backend — Data Structuring & Processing** (integrate → validate → insight) chain.

**Data source (Tier-1 database):** All enumerated units are read through a SQLAlchemy
``Session`` bound to ``settings.database_url`` (PostgreSQL or SQLite),
using the same ORM tables the ingestion / extraction / indexing layers persist after processing
connector runs. There is no parallel “file corpus” feed: chunk text and linkage come from
``aps_content_chunk`` / ``aps_content_linkage`` (content index path) or
``aps_retrieval_chunk_v1`` (retrieval plane path), matching
``GET /api/v1/connectors/runs/{id}/content-units`` and the retrieval-plane operator list.

Entry points:
``nrc_aps_content_index.list_content_units_for_run`` (indexed units) or
``aps_retrieval_plane_read.list_content_units_for_run`` (materialized retrieval scope).

This module shapes and sequences in-memory structures; it does not substitute for retrieval.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models import ConnectorRun
from app.services import analyst_insight_db_source
from app.services import aps_retrieval_plane_read
from app.services import nrc_aps_content_index
from app.services.market_data_integration import build_integrated_dataset
from app.services.market_data_validation import validate_market_rows
from app.services.market_insight_ai import MarketInsight, process_market_insights

MaterialSource = Literal["content_index", "retrieval_plane"]

_TEXT_PREVIEW_CHARS = 480


def _safe_source_name(target_id: str) -> str:
    raw = str(target_id or "").strip() or "unknown_target"
    return f"target_{raw}"


def slim_content_unit(item: dict[str, Any]) -> dict[str, Any]:
    """Strip heavy text but keep lineage fields for integration and audit."""
    text = str(item.get("chunk_text") or "")
    preview = text[:_TEXT_PREVIEW_CHARS]
    return {
        "layer": "document_processing_storage",
        "content_id": item.get("content_id"),
        "chunk_id": item.get("chunk_id"),
        "target_id": item.get("target_id"),
        "run_id": item.get("run_id"),
        "accession_number": item.get("accession_number"),
        "chunk_ordinal": item.get("chunk_ordinal"),
        "page_start": item.get("page_start"),
        "page_end": item.get("page_end"),
        "chunk_text_sha256": item.get("chunk_text_sha256"),
        "quality_status": item.get("quality_status"),
        "unit_kind": item.get("unit_kind"),
        "chunk_text_preview": preview,
        "chunk_text_len": len(text),
    }


def group_by_target(slim_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """One named source per connector target (NRC APS target_id)."""
    sources: dict[str, list[dict[str, Any]]] = {}
    for row in slim_rows:
        name = _safe_source_name(str(row.get("target_id") or ""))
        sources.setdefault(name, []).append(row)
    return sources


def infer_default_link_keys(slim_rows: list[dict[str, Any]]) -> list[str]:
    """Prefer accession + page when present; else document + chunk ordinal."""
    if not slim_rows:
        return ["content_id", "chunk_ordinal"]
    acc_ok = all(str(r.get("accession_number") or "").strip() for r in slim_rows)
    pg_ok = all(r.get("page_start") is not None for r in slim_rows)
    if acc_ok and pg_ok:
        return ["accession_number", "page_start"]
    return ["content_id", "chunk_ordinal"]


def admissibility_from_validation(validated: dict[str, Any]) -> dict[str, Any]:
    """Map validation output to coarse admissibility states (epistemic gate)."""
    missing = validated.get("missing_field_issues") or []
    outliers = validated.get("outliers") or []
    row_count = int(validated.get("row_count") or 0)
    if row_count == 0:
        return {
            "state": "rejected",
            "reason": "no_rows_after_materialization",
        }
    if missing:
        state = "quarantined" if len(missing) > row_count // 2 else "validated_with_warnings"
    elif outliers:
        state = "validated_with_warnings"
    else:
        state = "validated"
    return {
        "state": state,
        "missing_field_issue_count": len(missing),
        "outlier_count": len(outliers),
    }


def fetch_retrieved_items(
    db: Session,
    *,
    run_id: str,
    limit: int,
    offset: int,
    material_source: MaterialSource,
) -> dict[str, Any]:
    """
    Load a page of content units from Tier1 tables (same DB the ingestion pipeline writes).

    This is a thin delegate to the canonical list implementations used elsewhere in the API.
    """
    if material_source == "content_index":
        return nrc_aps_content_index.list_content_units_for_run(
            db, run_id=run_id, limit=limit, offset=offset
        )
    return aps_retrieval_plane_read.list_content_units_for_run(
        db, run_id=run_id, limit=limit, offset=offset
    )


def run_pipeline_from_document_storage(
    db: Session,
    *,
    connector_run_id: str,
    material_source: MaterialSource = "content_index",
    limit: int = 50,
    offset: int = 0,
    link_keys: list[str] | None = None,
    validation_options: dict[str, Any] | None = None,
    skip_insight_if_rejected: bool = True,
) -> dict[str, Any]:
    """
    End-to-end: retrieved units → integrated packet → validated packet → packaged insights.

    Insight stage receives validation summaries plus integrated *signals* derived from the
    same material (deterministic). If ``skip_insight_if_rejected`` and admissibility is
    ``rejected`` (no rows / unusable window), insights are omitted with a recorded reason.
    Quarantined or warning-bearing packets may still produce insights when rules fire.
    """
    run = db.get(ConnectorRun, connector_run_id)
    if not run:
        raise ValueError("connector_run_not_found")

    try:
        page = fetch_retrieved_items(
            db,
            run_id=connector_run_id,
            limit=limit,
            offset=offset,
            material_source=material_source,
        )
    except aps_retrieval_plane_read.RetrievalPlaneReadError:
        raise
    except ValueError as exc:
        if str(exc) == "run_id_required":
            raise ValueError("connector_run_id_invalid") from exc
        raise

    items: list[dict[str, Any]] = list(page.get("items") or [])
    slim = [slim_content_unit(dict(i)) for i in items]
    sources = group_by_target(slim)
    keys = list(link_keys) if link_keys else infer_default_link_keys(slim)
    integrated = build_integrated_dataset(sources, keys)

    default_vo: dict[str, Any] = {
        "required_fields": ["content_id", "target_id"],
        "numeric_columns": ["chunk_ordinal", "chunk_text_len"],
        "outlier_method": "none",
        "check_key_consistency": True,
    }
    vo_keys = {
        "required_fields",
        "numeric_columns",
        "outlier_method",
        "zscore_threshold",
        "iqr_multiplier",
        "normalize_columns",
        "check_key_consistency",
    }
    merged_vo = {**default_vo, **{k: v for k, v in (validation_options or {}).items() if k in vo_keys}}
    validated = validate_market_rows(slim, **merged_vo)
    admissibility = admissibility_from_validation(validated)

    insight_payload: dict[str, Any] = {
        "validation_summary": {
            "valid_count": max(
                0,
                int(validated.get("row_count") or 0) - len(validated.get("missing_field_issues") or []),
            ),
            "invalid_count": len(validated.get("missing_field_issues") or []),
            "failed_count": 0,
            "pass_rate": _pass_rate(validated),
        },
        "integrated": {
            "signals_by_category": _quality_histogram(slim),
            "signal_trajectory": _chunk_ordinal_series(slim),
            "source_names": list(sources.keys()),
        },
    }

    insights: list[MarketInsight] | list[dict[str, Any]] = []
    insight_skipped_reason: str | None = None

    blocked = skip_insight_if_rejected and admissibility.get("state") == "rejected"
    if blocked:
        insight_skipped_reason = (
            "insight_stage_skipped: admissibility rejected — no analysis-ready rows in window"
        )
    elif not slim:
        insight_skipped_reason = "insight_stage_skipped: no_retrieved_units_in_window"
    else:
        insights = process_market_insights(insight_payload)

    return {
        "tier1_data_plane": analyst_insight_db_source.tier1_data_plane_metadata(
            material_source=material_source,
            db=db,
        ),
        "validation_options_resolved": merged_vo,
        "link_keys_resolved": keys,
        "document_storage": {
            "connector_run_id": connector_run_id,
            "connector_key": run.connector_key,
            "material_source": material_source,
            "retrieved_total_reported": int(page.get("total") or 0),
            "window_limit": int(page.get("limit") or limit),
            "window_offset": int(page.get("offset") or offset),
            "units_in_window": len(items),
            "lineage_note": (
                "Tier1 indexed units: aps_content_linkage + aps_content_document + aps_content_chunk "
                if material_source == "content_index"
                else "Tier1 materialized retrieval plane: aps_retrieval_chunk_v1"
            ),
        },
        "integrated_analytical_packet": integrated,
        "validated_analytical_packet": validated,
        "admissibility": admissibility,
        "insight_input_payload": insight_payload,
        "packaged_insights": [i.model_dump() for i in insights] if insights else [],
        "insight_skipped_reason": insight_skipped_reason,
    }


def _pass_rate(validated: dict[str, Any]) -> float:
    rc = int(validated.get("row_count") or 0)
    if rc <= 0:
        return 0.0
    bad = len(validated.get("missing_field_issues") or [])
    return max(0.0, (rc - bad) / rc)


def _quality_histogram(slim: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in slim:
        q = str(r.get("quality_status") or "unknown")
        out[q] = out.get(q, 0) + 1
    return out


def _chunk_ordinal_series(slim: list[dict[str, Any]]) -> list[float]:
    vals = sorted(int(r.get("chunk_ordinal") or 0) for r in slim)
    return [float(x) for x in vals[:32]]
