"""
Tier-1 persistence contract for the analyst structuring layer.

The document bridge **only** enumerates retrieved material through SQLAlchemy against the
same database URL as the rest of the app (PostgreSQL or SQLite per ``settings.database_url``).
Those rows are written by the existing connector + NRC APS ingestion / indexing / retrieval
pipelines — not by ad-hoc file scans.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.config import settings

MaterialSource = Literal["content_index", "retrieval_plane"]


def database_kind_label() -> str:
    """Kind derived from ``settings.database_url`` (process default / API server)."""
    url = (settings.database_url or "").lower()
    if "postgresql" in url or "postgres" in url:
        return "postgresql"
    if url.startswith("sqlite"):
        return "sqlite"
    return "other"


def database_kind_from_session(db: Session | None) -> str | None:
    """Kind derived from the engine bound to this session (authoritative for a given request)."""
    if db is None:
        return None
    try:
        url = str(db.get_bind().url).lower()
    except Exception:
        return None
    if "postgresql" in url or "postgres" in url:
        return "postgresql"
    if url.startswith("sqlite"):
        return "sqlite"
    return "other"


def tier1_data_plane_metadata(*, material_source: MaterialSource, db: Session | None = None) -> dict[str, Any]:
    """
    Read-only observability: where rows come from in the Tier1 ORM model.

    *content_index* — rows produced after chunking + linkage persistence (``list_content_units_for_run``).
    *retrieval_plane* — materialized ``aps_retrieval_chunk_v1`` scope (``list_content_units_for_run`` on retrieval read path).
    """
    common = (
        "connector_run",
        "connector_run_target",
    )
    if material_source == "content_index":
        tables = (
            *common,
            "aps_content_linkage",
            "aps_content_document",
            "aps_content_chunk",
        )
        note = (
            "Chunk text and linkage are read from Tier1 tables populated by NRC APS "
            "document processing, artifact ingestion, and content indexing (same path as "
            "GET /api/v1/connectors/runs/{id}/content-units)."
        )
    else:
        tables = (
            *common,
            "aps_retrieval_chunk_v1",
        )
        note = (
            "Rows are enumerated from the materialized retrieval plane table. Optional JSON "
            "artifact reads may enrich fields but do not replace DB-backed enumeration."
        )

    session_kind = database_kind_from_session(db)
    return {
        "database_kind": session_kind or database_kind_label(),
        "database_kind_source": "session_engine" if session_kind else "settings_default",
        "persistence": "tier1_sqlalchemy_session",
        "material_source": material_source,
        "tables": list(tables),
        "lineage_note": note,
    }
