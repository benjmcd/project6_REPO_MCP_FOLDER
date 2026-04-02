"""Focused API tests for the document trace routes.

These tests must fail closed when the audited runtime is missing.
They exercise GET /runs/{run_id}/documents and GET /runs/{run_id}/documents/{target_id}/trace
against the real audited runtime DB via FastAPI TestClient.

The dependency override is applied per-test via fixture to avoid collision
with other test modules that override get_db at module scope on the shared app singleton.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.api.deps import get_db
from app.models.models import ApsContentLinkage, ApsContentDocument
from app.schemas.review_nrc_aps import NrcApsReviewExtractedUnitsOut
from main import app
from review_nrc_aps_runtime_fixture import (
    discover_passed_runtimes,
    latest_passed_runtime,
    make_session,
    resolve_deduplicated_target_pair,
    resolve_target_for_accession,
)

RUNTIME = latest_passed_runtime()
RUN_ID = RUNTIME.run_id
DB_PATH = RUNTIME.db_path
MULTI_RUNTIME_RUN_IDS = [runtime.run_id for runtime in discover_passed_runtimes()[:3]]
TEXT_LIKE_UNIT_KINDS = {
    "text_block",
    "paragraph",
    "ocr_text",
    "pdf_native_span",
    "pdf_text_block",
    "pdf_paragraph",
}

_bootstrap_session = make_session(RUNTIME)
try:
    TARGET_ID, ACCESSION = resolve_target_for_accession(_bootstrap_session, RUN_ID)
    DEDUP_TARGET_ID_A, DEDUP_TARGET_ID_B = resolve_deduplicated_target_pair(_bootstrap_session, RUN_ID)

    pinned_linkage = (
        _bootstrap_session.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == RUN_ID,
            ApsContentLinkage.target_id == TARGET_ID,
        )
        .first()
    )
    assert pinned_linkage is not None and pinned_linkage.diagnostics_ref
    ordered_units = json.loads(Path(pinned_linkage.diagnostics_ref).read_text(encoding="utf-8")).get("ordered_units") or []
    EXPECTED_TOTAL_UNIT_COUNT = len(ordered_units)
    EXPECTED_PAGE3_UNIT_COUNT = len([unit for unit in ordered_units if unit.get("page_number") == 3])
    EXPECTED_UNIT_KIND_COUNTS = {}
    for unit in ordered_units:
        unit_kind = str(unit.get("unit_kind") or "").strip()
        if not unit_kind:
            continue
        EXPECTED_UNIT_KIND_COUNTS[unit_kind] = EXPECTED_UNIT_KIND_COUNTS.get(unit_kind, 0) + 1
    EXPECTED_UNIT_KIND_COUNTS = dict(sorted(EXPECTED_UNIT_KIND_COUNTS.items()))
    EXPECTED_VISUAL_DERIVATIVE_UNIT_COUNT = sum(
        count for unit_kind, count in EXPECTED_UNIT_KIND_COUNTS.items() if unit_kind not in TEXT_LIKE_UNIT_KINDS
    )
    pinned_doc = (
        _bootstrap_session.query(ApsContentDocument)
        .filter(ApsContentDocument.content_id == pinned_linkage.content_id)
        .first()
    )
    assert pinned_doc is not None
    EXPECTED_VISUAL_PAGE_REF_COUNT = len(json.loads(pinned_doc.visual_page_refs_json or "[]"))

    dedup_linkage_a = (
        _bootstrap_session.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == RUN_ID,
            ApsContentLinkage.target_id == DEDUP_TARGET_ID_A,
        )
        .first()
    )
    dedup_linkage_b = (
        _bootstrap_session.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == RUN_ID,
            ApsContentLinkage.target_id == DEDUP_TARGET_ID_B,
        )
        .first()
    )
    assert dedup_linkage_a is not None and dedup_linkage_a.diagnostics_ref
    assert dedup_linkage_b is not None and dedup_linkage_b.diagnostics_ref
    EXPECTED_DEDUP_UNIT_COUNT_A = len(
        json.loads(Path(dedup_linkage_a.diagnostics_ref).read_text(encoding="utf-8")).get("ordered_units") or []
    )
    EXPECTED_DEDUP_UNIT_COUNT_B = len(
        json.loads(Path(dedup_linkage_b.diagnostics_ref).read_text(encoding="utf-8")).get("ordered_units") or []
    )
finally:
    _bootstrap_session.close()


def _override_get_db():
    """Yield a real SQLAlchemy session against the audited runtime DB."""
    session = make_session(RUNTIME)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _apply_db_override():
    """Apply the real-DB override before each test and restore after."""
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override_get_db
    yield
    if previous is not None:
        app.dependency_overrides[get_db] = previous
    else:
        app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


# ---------------------------------------------------------------------------
# Document selector route tests
# ---------------------------------------------------------------------------

def test_api_document_selector_returns_200():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents")
    assert response.status_code == 200


def test_api_document_selector_returns_nonempty():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents")
    data = response.json()
    assert data["run_id"] == RUN_ID
    assert len(data["documents"]) > 0, "Selector must return non-empty target rows for the audited run"


def test_api_document_selector_pinned_target_present():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents")
    data = response.json()
    target = next((d for d in data["documents"] if d["target_id"] == TARGET_ID), None)
    assert target is not None, f"Pinned target {TARGET_ID} must appear in selector"
    assert target["accession_number"] == ACCESSION


def test_api_document_selector_document_type_semantics():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents")
    data = response.json()
    target = next((d for d in data["documents"] if d["target_id"] == TARGET_ID), None)
    assert target is not None
    assert target["document_type"] == "Exemption from NRC Requirements"


def test_api_document_selector_404_for_unknown_run():
    response = client.get("/api/v1/review/nrc-aps/runs/00000000-0000-0000-0000-000000000000/documents")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Trace manifest route tests
# ---------------------------------------------------------------------------

def test_api_trace_manifest_returns_200():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/trace")
    assert response.status_code == 200


def test_api_trace_manifest_content():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/trace")
    data = response.json()
    assert data["run_id"] == RUN_ID
    assert data["target_id"] == TARGET_ID
    assert data["identity"]["accession_number"] == ACCESSION
    assert data["identity"]["document_type"] == "Exemption from NRC Requirements"
    assert "sync_capabilities" in data
    assert data["summary"]["visual_page_ref_count"] == EXPECTED_VISUAL_PAGE_REF_COUNT
    assert data["summary"]["visual_derivative_unit_count"] == EXPECTED_VISUAL_DERIVATIVE_UNIT_COUNT
    assert data["trace_completeness"]["has_visual_derivatives"] is (
        EXPECTED_VISUAL_PAGE_REF_COUNT > 0 or EXPECTED_VISUAL_DERIVATIVE_UNIT_COUNT > 0
    )


def test_api_trace_manifest_source_endpoint_truthfulness():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/trace")
    data = response.json()
    assert data["source"]["source_endpoint"] is not None
    assert f"/runs/{RUN_ID}/documents/{TARGET_ID}/source" in data["source"]["source_endpoint"]


def test_api_document_source_stream_success():
    """Stream the document source successfully."""
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/source")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "filename*=utf-8''Dresden" in response.headers["content-disposition"]
    assert len(response.content) > 0


def test_api_document_source_404_for_unknown_target():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/00000000-0000-0000-0000-000000000000/source")
    assert response.status_code == 404 # resolve_source_blob_info raises KeyError -> 404


def test_api_document_source_400_for_cross_run_traversal(monkeypatch):
    """Simulate a targeted attack with a cross-run path."""
    from app.services.review_nrc_aps_document_trace import resolve_source_blob_info
    
    # Let's mock resolve_source_blob_info to raise ValueError representing a path outside allowed boundaries
    def mock_resolve(*args, **kwargs):
        raise ValueError("Requested blob path is outside allowed runtime boundaries")
    
    monkeypatch.setattr("app.api.review_nrc_aps.resolve_source_blob_info", mock_resolve)
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/source")
    assert response.status_code == 400
    assert "outside allowed runtime boundaries" in response.json()["detail"]


def test_api_trace_manifest_expected_endpoints():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/trace")
    data = response.json()
    
    allowed_endpoints = {"normalized_text", "indexed_chunks", "diagnostics", "extracted_units"}
    for tab in data["tabs"]:
        if tab["tab_id"] in allowed_endpoints and tab["available"]:
            assert tab["endpoint"] is not None, f"Tab '{tab['tab_id']}' should have an endpoint"
        else:
            assert tab["endpoint"] is None, f"Tab '{tab['tab_id']}' endpoint must be null"


def test_api_document_diagnostics_payload():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert data["target_id"] == TARGET_ID
    assert "available" in data
    assert data["visual_page_ref_count"] == EXPECTED_VISUAL_PAGE_REF_COUNT
    assert data["visual_derivative_unit_count"] == EXPECTED_VISUAL_DERIVATIVE_UNIT_COUNT
    assert data["unit_kind_counts"] == EXPECTED_UNIT_KIND_COUNTS


def test_api_document_normalized_text_payload():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/normalized-text")
    assert response.status_code == 200
    data = response.json()
    assert data["target_id"] == TARGET_ID
    assert "char_count" in data


def test_api_document_indexed_chunks_payload():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/indexed-chunks")
    assert response.status_code == 200
    data = response.json()
    assert data["target_id"] == TARGET_ID
    assert "chunk_count" in data
    assert isinstance(data["chunks"], list)


def test_api_trace_manifest_404_for_unknown_target():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/00000000-0000-0000-0000-000000000000/trace")
    assert response.status_code == 404


def test_api_phase4_routes_404_for_unknown_target():
    unknown_target = "00000000-0000-0000-0000-000000000000"
    for route in ["diagnostics", "normalized-text", "indexed-chunks"]:
        res = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{unknown_target}/{route}")
        assert res.status_code == 404, f"Route /{route} should return 404 for unknown target"


def test_api_phase4_routes_200_missingness_for_known_target_missing_layer(monkeypatch):
    """If target is known but payload layer is absent, return 200 with available=False."""
    # We patch ApsContentLinkage query to return a link with no diagnostics_ref etc.
    from app.services.review_nrc_aps_document_trace import compose_diagnostics_payload
    def mock_compose(*args, **kwargs):
        from app.schemas.review_nrc_aps import NrcApsReviewDiagnosticsOut
        return NrcApsReviewDiagnosticsOut(run_id=RUN_ID, target_id=TARGET_ID, available=False)
    
    monkeypatch.setattr("app.api.review_nrc_aps.compose_diagnostics_payload", mock_compose)
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == RUN_ID
    assert data["target_id"] == TARGET_ID
    assert data["available"] is False


def test_api_extracted_units_happy_path():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == RUN_ID
    assert data["target_id"] == TARGET_ID
    assert data["available"] is True
    assert data["reason_code"] is None
    assert data["source_precision"] == "unit"
    assert data["source_layer"] == "diagnostics_ordered_units"
    assert data["total_unit_count"] == EXPECTED_TOTAL_UNIT_COUNT
    assert len(data["units"]) == EXPECTED_TOTAL_UNIT_COUNT


def test_api_extracted_units_page_filter():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units?page_number=3")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["page_number"] == 3
    assert len(data["units"]) == EXPECTED_PAGE3_UNIT_COUNT
    assert all(unit["page_number"] == 3 for unit in data["units"])


def test_api_extracted_units_invalid_page_number():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units?page_number=0")
    assert response.status_code == 422

    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units?page_number=-5")
    assert response.status_code == 422


def test_api_extracted_units_unknown_target_404():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/00000000-0000-0000-0000-000000000000/extracted-units")
    assert response.status_code == 404


def test_api_extracted_units_known_target_missing_diagnostics_returns_explicit_missingness(monkeypatch):
    monkeypatch.setattr(
        "app.api.review_nrc_aps.compose_extracted_units_payload",
        lambda db, run_id, target_id, root, page_number=None: NrcApsReviewExtractedUnitsOut(
            run_id=run_id,
            target_id=target_id,
            available=False,
            reason_code="diagnostics_absent",
            source_precision="none",
            page_number=page_number,
            units=[],
        ),
    )

    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["reason_code"] == "diagnostics_absent"
    assert data["source_precision"] == "none"
    assert data["units"] == []


def test_api_extracted_units_no_retrieval_dependency():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True

    trace_response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/trace")
    trace_data = trace_response.json()
    assert trace_data["trace_completeness"]["retrieval_available"] is False


def test_api_extracted_units_remain_target_scoped_for_deduplicated_content():
    response_a = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{DEDUP_TARGET_ID_A}/extracted-units")
    response_b = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{DEDUP_TARGET_ID_B}/extracted-units")

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    data_a = response_a.json()
    data_b = response_b.json()
    assert data_a["target_id"] == DEDUP_TARGET_ID_A
    assert data_b["target_id"] == DEDUP_TARGET_ID_B
    assert data_a["total_unit_count"] == EXPECTED_DEDUP_UNIT_COUNT_A
    assert data_b["total_unit_count"] == EXPECTED_DEDUP_UNIT_COUNT_B
    assert EXPECTED_DEDUP_UNIT_COUNT_A == EXPECTED_DEDUP_UNIT_COUNT_B
    assert data_a["units"][0]["text"] == data_b["units"][0]["text"]
    assert data_a["units"][0]["unit_id"] != data_b["units"][0]["unit_id"]
    
# ---------------------------------------------------------------------------
# Regression: existing review routes must still work
# ---------------------------------------------------------------------------

def test_api_existing_overview_not_regressed():
    """The existing overview route must still return 200 for the audited run."""
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/overview")
    assert response.status_code == 200
    data = response.json()
    assert "tree" in data
    assert "run_projection" in data


@pytest.mark.parametrize("run_id", MULTI_RUNTIME_RUN_IDS)
def test_api_document_trace_routes_switch_across_multiple_runtime_dbs(run_id: str):
    selector_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/documents")
    assert selector_response.status_code == 200

    selector_data = selector_response.json()
    assert selector_data["run_id"] == run_id
    assert selector_data["documents"], f"Expected non-empty document selector for run {run_id}"

    target_id = selector_data["default_target_id"] or selector_data["documents"][0]["target_id"]
    assert target_id

    trace_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/trace")
    assert trace_response.status_code == 200
    trace_data = trace_response.json()
    assert trace_data["run_id"] == run_id
    assert trace_data["target_id"] == target_id
