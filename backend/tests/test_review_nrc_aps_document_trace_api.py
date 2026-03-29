"""Focused API tests for the document trace routes.

These tests must fail closed when the audited runtime is missing.
They exercise GET /runs/{run_id}/documents and GET /runs/{run_id}/documents/{target_id}/trace
against the real audited runtime DB via FastAPI TestClient.

The dependency override is applied per-test via fixture to avoid collision
with other test modules that override get_db at module scope on the shared app singleton.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.deps import get_db
from main import app

RUN_ID = "5cd56147-4b5b-4278-8b32-79b9b1b34db5"
TARGET_ID = "fd00ab2b-aa52-4c2a-9899-0c36786f8870"
ACCESSION = "LOCALAPS00001"

DB_PATH = Path(__file__).resolve().parents[1] / "app" / "storage_test_runtime" / "lc_e2e" / "20260328_150207" / "lc.db"

# Fail closed: if the audited runtime DB is missing, fail immediately at import time
assert DB_PATH.exists(), f"Audited runtime DB not found at {DB_PATH}. API tests cannot run."


def _override_get_db():
    """Yield a real SQLAlchemy session against the audited runtime DB."""
    engine = create_engine(f"sqlite:///{DB_PATH}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
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


# ---------------------------------------------------------------------------
# Phase 6 Extracted Units API Tests
# ---------------------------------------------------------------------------

def test_api_extracted_units_happy_path():
    """GET /extracted-units for pinned target must return diagnostics-backed units."""
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["source_precision"] == "unit"
    assert data["source_layer"] == "diagnostics_ordered_units"
    assert data["total_unit_count"] == 543
    assert len(data["units"]) == 543


def test_api_extracted_units_page_filter():
    """page_number query param must filter to only matching units."""
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units?page_number=2")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["page_number"] == 2
    assert all(u["page_number"] == 2 for u in data["units"])
    assert len(data["units"]) == 26  # page 2 has 26 units


def test_api_extracted_units_invalid_page_number():
    """Negative page_number must return 422."""
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units?page_number=0")
    assert response.status_code == 422

    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units?page_number=-1")
    assert response.status_code == 422


def test_api_extracted_units_unknown_target_404():
    """Unknown target must return 404."""
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/00000000-0000-0000-0000-000000000000/extracted-units")
    assert response.status_code == 404


def test_api_extracted_units_no_retrieval_dependency():
    """Verify extracted units work without retrieval dependency.
    The audited runtime has zero retrieval rows — extracted units must still work."""
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/extracted-units")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    # Also verify trace completeness confirms no retrieval
    trace_resp = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{TARGET_ID}/trace")
    trace_data = trace_resp.json()
    assert trace_data["trace_completeness"]["retrieval_available"] is False
