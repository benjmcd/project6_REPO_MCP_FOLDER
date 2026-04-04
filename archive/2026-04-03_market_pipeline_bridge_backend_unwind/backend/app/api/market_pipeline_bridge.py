"""HTTP entrypoints linking document storage / retrieval to the analyst insight pipeline."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import analyst_insight_document_bridge
from app.services.aps_retrieval_plane_read import RetrievalPlaneReadError

router = APIRouter(tags=["market-pipeline"])


class DocumentStoragePipelineIn(BaseModel):
    """Request body for running the structuring layer on stored/retrieved units."""

    material_source: Literal["content_index", "retrieval_plane"] = Field(
        default="content_index",
        description=(
            "`content_index`: ApsContentChunk linkage (post indexing). "
            "`retrieval_plane`: materialized ApsRetrievalChunk scope."
        ),
    )
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    link_keys: list[str] | None = Field(
        default=None,
        description="Composite join keys for integration; default is inferred from material.",
    )
    validation_options: dict[str, Any] | None = Field(
        default=None,
        description="Forwarded to validate_market_rows (subset of kwargs only).",
    )
    skip_insight_if_rejected: bool = Field(
        default=True,
        description="If true, omit heuristic insights when admissibility is rejected.",
    )


@router.post("/market-pipeline/from-document-storage/{connector_run_id}")
def run_pipeline_from_document_storage(
    connector_run_id: str,
    body: DocumentStoragePipelineIn | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Chain **document processing & storage** outputs into integrate → validate → insight.

    Enumerates units from the Tier1 database (PostgreSQL or SQLite per deployment) using the
    same SQLAlchemy-backed list implementations as
    ``GET /api/v1/connectors/runs/{id}/content-units`` (content index) or the retrieval-plane
    operator list when ``material_source=retrieval_plane``. Rows are those persisted by ingestion,
    extraction, and indexing — not a separate file corpus.
    """
    payload = body or DocumentStoragePipelineIn()
    try:
        return analyst_insight_document_bridge.run_pipeline_from_document_storage(
            db,
            connector_run_id=connector_run_id,
            material_source=payload.material_source,
            limit=payload.limit,
            offset=payload.offset,
            link_keys=payload.link_keys,
            validation_options=payload.validation_options,
            skip_insight_if_rejected=payload.skip_insight_if_rejected,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "connector_run_not_found":
            raise HTTPException(status_code=404, detail="connector run not found") from exc
        if code == "connector_run_id_invalid":
            raise HTTPException(status_code=400, detail="invalid connector_run_id") from exc
        raise HTTPException(status_code=400, detail=code) from exc
    except RetrievalPlaneReadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
