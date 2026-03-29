from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.review_nrc_aps import (
    NrcApsReviewRunSelectorOut,
    NrcApsReviewPipelineDefinitionOut,
    NrcApsReviewOverviewOut,
    NrcApsReviewTreeOut,
    NrcApsReviewNodeDetailsOut,
    NrcApsReviewFileDetailsOut,
    NrcApsReviewFilePreviewOut,
    NrcApsReviewDocumentSelectorOut,
    NrcApsReviewTraceManifestOut,
    NrcApsReviewDiagnosticsOut,
    NrcApsReviewNormalizedTextOut,
    NrcApsReviewIndexedChunksOut,
    NrcApsReviewExtractedUnitsOut,
)
from fastapi.responses import FileResponse
from app.services.review_nrc_aps_catalog import discover_candidate_runs
from app.services.review_nrc_aps_runtime import find_review_root_for_run, normalize_path
from app.services.review_nrc_aps_overview import compose_overview, compose_pipeline_definition
from app.services.review_nrc_aps_tree import get_node_by_tree_id
from app.services.review_nrc_aps_details import get_node_details, get_file_details, get_file_preview
from app.services.review_nrc_aps_document_trace import (
    compose_document_selector, 
    compose_trace_manifest,
    resolve_source_blob_info,
    compose_diagnostics_payload,
    compose_normalized_text_payload,
    compose_indexed_chunks_payload,
    compose_extracted_units_payload,
)

router = APIRouter()

@router.get("/runs", response_model=NrcApsReviewRunSelectorOut)
def get_runs(db: Session = Depends(get_db)):
    """List reviewable runs and the default run id."""
    return discover_candidate_runs(db)

@router.get("/pipeline-definition", response_model=NrcApsReviewPipelineDefinitionOut)
def get_pipeline_definition(run_id: str):
    """Return the canonical graph plus the conceptual pipeline projection."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    return compose_pipeline_definition(run_id, root)

@router.get("/runs/{run_id}/overview", response_model=NrcApsReviewOverviewOut)
def get_run_overview(run_id: str):
    """Return the combined graph mapping and tree for a specific run."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    return compose_overview(run_id, root)

@router.get("/runs/{run_id}/tree", response_model=NrcApsReviewTreeOut)
def get_run_tree(run_id: str):
    """Return the strict filesystem tree."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    return compose_overview(run_id, root).tree

@router.get("/runs/{run_id}/nodes/{node_id}", response_model=NrcApsReviewNodeDetailsOut)
def get_node_details_route(run_id: str, node_id: str):
    """Return details and metadata for a specific canonical node."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    try:
        return get_node_details(run_id, root, node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/runs/{run_id}/files/{tree_id}", response_model=NrcApsReviewFileDetailsOut)
def get_file_details_route(run_id: str, tree_id: str):
    """Return details and metadata for a specific tree file."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")

    tree = compose_overview(run_id, root).tree
    node = get_node_by_tree_id(tree.root, tree_id)
    if not node:
        raise HTTPException(status_code=404, detail="Tree id not found")

    file_path = root / node.path
    try:
        normalize_path(root, node.path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside review root")

    try:
        return get_file_details(run_id, root, tree_id, file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}/files/{tree_id}/preview", response_model=NrcApsReviewFilePreviewOut)
def get_file_preview_route(run_id: str, tree_id: str):
    """Return safe JSON/text preview content for a specific tree file."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")

    tree = compose_overview(run_id, root).tree
    node = get_node_by_tree_id(tree.root, tree_id)
    if not node:
        raise HTTPException(status_code=404, detail="Tree id not found")

    file_path = root / node.path
    try:
        normalize_path(root, node.path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside review root")

    try:
        return get_file_preview(run_id, root, tree_id, file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))


@router.get("/runs/{run_id}/documents", response_model=NrcApsReviewDocumentSelectorOut)
def get_run_documents(run_id: str, db: Session = Depends(get_db)):
    """Return the document selector for a specific run."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    return compose_document_selector(db, run_id, root)


@router.get("/runs/{run_id}/documents/{target_id}/trace", response_model=NrcApsReviewTraceManifestOut)
def get_document_trace(run_id: str, target_id: str, db: Session = Depends(get_db)):
    """Return the trace manifest for a specific document target."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    try:
        return compose_trace_manifest(db, run_id, target_id, root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/source")
def get_document_source(run_id: str, target_id: str, db: Session = Depends(get_db)):
    """Stream the original source document for a target."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
        
    try:
        blob_path, media_type, filename = resolve_source_blob_info(db, run_id, target_id, root)
        
        # We use FileResponse for efficient streaming
        return FileResponse(
            path=blob_path,
            media_type=media_type,
            filename=filename
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # Business/safety error
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/diagnostics", response_model=NrcApsReviewDiagnosticsOut)
def get_document_diagnostics(run_id: str, target_id: str, db: Session = Depends(get_db)):
    """Return the structured diagnostics payload for a trackable target."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    try:
        return compose_diagnostics_payload(db, run_id, target_id, root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/normalized-text", response_model=NrcApsReviewNormalizedTextOut)
def get_document_normalized_text(run_id: str, target_id: str, db: Session = Depends(get_db)):
    """Return the normalized text payload for a trackable target."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    try:
        return compose_normalized_text_payload(db, run_id, target_id, root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/indexed-chunks", response_model=NrcApsReviewIndexedChunksOut)
def get_document_indexed_chunks(run_id: str, target_id: str, db: Session = Depends(get_db)):
    """Return the indexed chunks payload for a trackable target."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    try:
        return compose_indexed_chunks_payload(db, run_id, target_id, root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/extracted-units", response_model=NrcApsReviewExtractedUnitsOut)
def get_document_extracted_units(
    run_id: str,
    target_id: str,
    page_number: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Return diagnostics-backed extracted units for a target, optionally filtered to one page."""
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    try:
        return compose_extracted_units_payload(db, run_id, target_id, root, page_number=page_number)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
