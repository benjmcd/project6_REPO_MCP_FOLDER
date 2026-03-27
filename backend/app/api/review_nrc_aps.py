from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.review_nrc_aps import (
    NrcApsReviewRunSelectorOut,
    NrcApsReviewCanonicalGraphOut,
    NrcApsReviewOverviewOut,
    NrcApsReviewTreeOut,
    NrcApsReviewNodeDetailsOut,
    NrcApsReviewFileDetailsOut,
)
from app.services.review_nrc_aps_catalog import discover_candidate_runs
from app.services.review_nrc_aps_graph import build_canonical_graph
from app.services.review_nrc_aps_runtime import find_review_root_for_run, normalize_path
from app.services.review_nrc_aps_overview import compose_overview
from app.services.review_nrc_aps_tree import get_node_by_tree_id
from app.services.review_nrc_aps_details import get_node_details, get_file_details

router = APIRouter()

@router.get("/runs", response_model=NrcApsReviewRunSelectorOut)
def get_runs(db: Session = Depends(get_db)):
    """List reviewable runs and the default run id."""
    return discover_candidate_runs(db)

@router.get("/pipeline-definition", response_model=NrcApsReviewCanonicalGraphOut)
def get_pipeline_definition():
    """Return the frozen canonical graph shape."""
    return build_canonical_graph()

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
