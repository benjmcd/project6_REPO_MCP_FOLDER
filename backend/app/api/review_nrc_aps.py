from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

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
    NrcApsWorkbenchCompareSourcesOut,
    NrcApsWorkbenchCompareTargetsOut,
    NrcApsWorkbenchCompareManifestOut,
    NrcApsWorkbenchCompareTabOut,
    NrcApsCandidateBTraceManifestOut,
)
from fastapi.responses import FileResponse, PlainTextResponse
from app.services.review_nrc_aps_catalog import discover_candidate_runs
from app.services.review_nrc_aps_runtime import find_review_root_for_run, normalize_path
from app.services.review_nrc_aps_runtime_db import runtime_db_session_for_run
from app.services.review_nrc_aps_overview import compose_overview, compose_pipeline_definition
from app.services.review_nrc_aps_tree import get_node_by_tree_id
from app.services.review_nrc_aps_details import get_node_details, get_file_details, get_file_preview
from app.services.review_nrc_aps_document_trace import (
    compose_document_selector, 
    compose_trace_manifest,
    resolve_source_blob_info,
    resolve_visual_artifact_info,
    compose_diagnostics_payload,
    compose_normalized_text_payload,
    compose_indexed_chunks_payload,
    compose_extracted_units_payload,
)
from app.services.review_nrc_aps_workbench_compare import (
    compose_workbench_compare_manifest,
    compose_workbench_compare_tab,
    compose_workbench_compare_targets,
    discover_workbench_compare_sources,
)
from app.services.review_nrc_aps_candidate_b_trace import (
    compose_candidate_b_trace_manifest,
    load_candidate_b_trace_raw_json,
    load_candidate_b_trace_raw_markdown,
    resolve_candidate_b_trace_annotated_pdf_info,
)

router = APIRouter()


def _get_review_root_or_404(run_id: str):
    root = find_review_root_for_run(run_id)
    if not root:
        raise HTTPException(status_code=404, detail="Review root not found for run")
    return root


def _raise_workbench_compare_http_error(exc: Exception) -> None:
    detail = str(exc)
    if detail in {
        "candidate_b_bundle_id_missing",
        "candidate_b_bundle_id_invalid",
        "candidate_b_source_kind_invalid",
        "candidate_b_run_id_missing",
        "unsupported_tab",
    }:
        raise HTTPException(status_code=400, detail=detail)
    if detail in {
        "candidate_b_bundle_unavailable",
        "candidate_b_opendataloader_pdf_run_not_found",
        "fixture_id_not_comparable",
    }:
        raise HTTPException(status_code=404, detail=detail)
    raise HTTPException(status_code=400, detail=detail)


def _raise_candidate_b_trace_http_error(exc: Exception) -> None:
    detail = str(exc)
    if detail in {
        "candidate_b_bundle_id_missing",
        "candidate_b_bundle_id_invalid",
        "candidate_b_raw_root_missing",
        "candidate_b_raw_root_invalid",
        "candidate_b_compare_payload_invalid",
        "candidate_b_bundle_payload_invalid",
        "candidate_b_annotated_pdf_invalid",
        "candidate_b_raw_json_invalid",
        "candidate_b_raw_markdown_invalid",
    }:
        raise HTTPException(status_code=400, detail=detail)
    if detail in {
        "candidate_b_bundle_unavailable",
        "candidate_b_fixture_unavailable",
        "annotated_pdf_unavailable",
        "candidate_b_raw_json_unavailable",
        "candidate_b_raw_markdown_unavailable",
    }:
        raise HTTPException(status_code=404, detail=detail)
    raise HTTPException(status_code=400, detail=detail)


@router.get("/runs", response_model=NrcApsReviewRunSelectorOut)
def get_runs():
    """List reviewable runs and the default run id."""
    return discover_candidate_runs()


@router.get("/workbench-compare/sources", response_model=NrcApsWorkbenchCompareSourcesOut)
def get_workbench_compare_sources():
    """List compare-eligible baseline/Candidate A runs and Candidate B sources."""
    try:
        return discover_workbench_compare_sources()
    except ValueError as exc:
        _raise_workbench_compare_http_error(exc)


@router.get("/workbench-compare/targets", response_model=NrcApsWorkbenchCompareTargetsOut)
def get_workbench_compare_targets(
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_source_kind: str = Query("bundle"),
    candidate_b_bundle_id: str | None = None,
    candidate_b_run_id: str | None = None,
):
    """Return the strict three-way target set for the selected compare sources."""
    try:
        return compose_workbench_compare_targets(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_source_kind=candidate_b_source_kind,
            candidate_b_bundle_id=candidate_b_bundle_id,
            candidate_b_run_id=candidate_b_run_id,
        )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        _raise_workbench_compare_http_error(exc)


@router.get("/workbench-compare/targets/{fixture_id}/manifest", response_model=NrcApsWorkbenchCompareManifestOut)
def get_workbench_compare_manifest(
    fixture_id: str,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_source_kind: str = Query("bundle"),
    candidate_b_bundle_id: str | None = None,
    candidate_b_run_id: str | None = None,
):
    """Return the shared compare manifest for one selected fixture."""
    try:
        return compose_workbench_compare_manifest(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_source_kind=candidate_b_source_kind,
            candidate_b_bundle_id=candidate_b_bundle_id,
            candidate_b_run_id=candidate_b_run_id,
            fixture_id=fixture_id,
        )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        _raise_workbench_compare_http_error(exc)


@router.get("/workbench-compare/targets/{fixture_id}/tabs/{tab_id}", response_model=NrcApsWorkbenchCompareTabOut)
def get_workbench_compare_tab(
    fixture_id: str,
    tab_id: str,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_source_kind: str = Query("bundle"),
    candidate_b_bundle_id: str | None = None,
    candidate_b_run_id: str | None = None,
):
    """Return one compare tab payload for the selected fixture."""
    try:
        return compose_workbench_compare_tab(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_source_kind=candidate_b_source_kind,
            candidate_b_bundle_id=candidate_b_bundle_id,
            candidate_b_run_id=candidate_b_run_id,
            fixture_id=fixture_id,
            tab_id=tab_id,
        )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        _raise_workbench_compare_http_error(exc)


@router.get("/candidate-b-trace/manifest", response_model=NrcApsCandidateBTraceManifestOut)
def get_candidate_b_trace_manifest(
    candidate_b_bundle_id: str,
    fixture_id: str,
):
    """Return the Candidate B Trace manifest for one validated bundle-backed fixture."""
    try:
        return compose_candidate_b_trace_manifest(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
        )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        _raise_candidate_b_trace_http_error(exc)


@router.get("/candidate-b-trace/annotated-pdf")
def get_candidate_b_trace_annotated_pdf(
    candidate_b_bundle_id: str,
    fixture_id: str,
):
    """Stream the validated annotated PDF for one bundle-backed fixture."""
    try:
        pdf_path, media_type, filename = resolve_candidate_b_trace_annotated_pdf_info(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
        )
        return FileResponse(
            path=pdf_path,
            media_type=media_type,
            filename=filename,
            content_disposition_type="inline",
        )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        _raise_candidate_b_trace_http_error(exc)


@router.get("/candidate-b-trace/raw-json")
def get_candidate_b_trace_raw_json(
    candidate_b_bundle_id: str,
    fixture_id: str,
):
    """Return the validated raw JSON payload for one bundle-backed fixture."""
    try:
        return load_candidate_b_trace_raw_json(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
        )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        _raise_candidate_b_trace_http_error(exc)


@router.get("/candidate-b-trace/raw-markdown")
def get_candidate_b_trace_raw_markdown(
    candidate_b_bundle_id: str,
    fixture_id: str,
):
    """Return the validated raw Markdown payload for one bundle-backed fixture."""
    try:
        markdown_text = load_candidate_b_trace_raw_markdown(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
        )
        return PlainTextResponse(markdown_text)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        _raise_candidate_b_trace_http_error(exc)

@router.get("/pipeline-definition", response_model=NrcApsReviewPipelineDefinitionOut)
def get_pipeline_definition(run_id: str):
    """Return the canonical graph plus the conceptual pipeline projection."""
    root = _get_review_root_or_404(run_id)
    return compose_pipeline_definition(run_id, root)

@router.get("/runs/{run_id}/overview", response_model=NrcApsReviewOverviewOut)
def get_run_overview(run_id: str):
    """Return the combined graph mapping and tree for a specific run."""
    root = _get_review_root_or_404(run_id)
    return compose_overview(run_id, root)

@router.get("/runs/{run_id}/tree", response_model=NrcApsReviewTreeOut)
def get_run_tree(run_id: str):
    """Return the strict filesystem tree."""
    root = _get_review_root_or_404(run_id)
    return compose_overview(run_id, root).tree

@router.get("/runs/{run_id}/nodes/{node_id}", response_model=NrcApsReviewNodeDetailsOut)
def get_node_details_route(run_id: str, node_id: str):
    """Return details and metadata for a specific canonical node."""
    root = _get_review_root_or_404(run_id)
    try:
        return get_node_details(run_id, root, node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/runs/{run_id}/files/{tree_id}", response_model=NrcApsReviewFileDetailsOut)
def get_file_details_route(run_id: str, tree_id: str):
    """Return details and metadata for a specific tree file."""
    root = _get_review_root_or_404(run_id)

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
    root = _get_review_root_or_404(run_id)

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
def get_run_documents(run_id: str):
    """Return the document selector for a specific run."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            return compose_document_selector(db, run_id, binding.review_root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/trace", response_model=NrcApsReviewTraceManifestOut)
def get_document_trace(run_id: str, target_id: str):
    """Return the trace manifest for a specific document target."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            return compose_trace_manifest(db, run_id, target_id, binding.review_root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/source")
def get_document_source(run_id: str, target_id: str):
    """Stream the original source document for a target."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            blob_path, media_type, filename = resolve_source_blob_info(db, run_id, target_id, binding.review_root)
        
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


@router.get("/runs/{run_id}/documents/{target_id}/visual-artifacts/{artifact_id}")
def get_document_visual_artifact(run_id: str, target_id: str, artifact_id: str):
    """Stream a preserved visual artifact for a target."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            artifact_path, media_type, filename = resolve_visual_artifact_info(
                db,
                run_id,
                target_id,
                binding.storage_dir,
                artifact_id,
            )

        return FileResponse(
            path=artifact_path,
            media_type=media_type,
            filename=filename,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/diagnostics", response_model=NrcApsReviewDiagnosticsOut)
def get_document_diagnostics(run_id: str, target_id: str):
    """Return the structured diagnostics payload for a trackable target."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            return compose_diagnostics_payload(db, run_id, target_id, binding.review_root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/normalized-text", response_model=NrcApsReviewNormalizedTextOut)
def get_document_normalized_text(run_id: str, target_id: str):
    """Return the normalized text payload for a trackable target."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            return compose_normalized_text_payload(db, run_id, target_id, binding.review_root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/indexed-chunks", response_model=NrcApsReviewIndexedChunksOut)
def get_document_indexed_chunks(run_id: str, target_id: str):
    """Return the indexed chunks payload for a trackable target."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            return compose_indexed_chunks_payload(db, run_id, target_id, binding.review_root)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/documents/{target_id}/extracted-units", response_model=NrcApsReviewExtractedUnitsOut)
def get_document_extracted_units(
    run_id: str,
    target_id: str,
    page_number: int | None = Query(default=None, ge=1),
):
    """Return diagnostics-backed extracted units for a target, optionally filtered to one page."""
    try:
        with runtime_db_session_for_run(run_id) as (binding, db):
            return compose_extracted_units_payload(
                db,
                run_id,
                target_id,
                binding.review_root,
                storage_root=binding.storage_dir,
                page_number=page_number,
            )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
