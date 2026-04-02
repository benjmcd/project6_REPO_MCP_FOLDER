"""Focused API tests for the document trace routes.

These tests must fail closed when the audited runtime is missing.
They exercise GET /runs/{run_id}/documents and GET /runs/{run_id}/documents/{target_id}/trace
against the real audited runtime DB via FastAPI TestClient.

The dependency override is applied per-test via fixture to avoid collision
with other test modules that override get_db at module scope on the shared app singleton.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm.session import Session as OrmSession

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.api.deps import get_db
import app.services.review_nrc_aps_document_trace as trace_service
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

PASSED_RUNTIMES = discover_passed_runtimes()
RUNTIMES_BY_RUN_ID = {runtime.run_id: runtime for runtime in PASSED_RUNTIMES}

RUNTIME = latest_passed_runtime()
RUN_ID = RUNTIME.run_id
DB_PATH = RUNTIME.db_path
MULTI_RUNTIME_RUN_IDS = [runtime.run_id for runtime in PASSED_RUNTIMES[:3]]

RUN_A_ID = "6a3dadd8-625a-4465-9b20-df05b39b8fc6"
RUN_B_ID = "282ae183-0f73-4e73-ba6e-f124c56d957d"

RUN_A_POSITIVE_TARGET_ID = "54a334ee-e2eb-43ea-9648-fba7d11ef59e"
RUN_A_MIXED_TARGET_ID = "7287ce0a-710e-43e2-afe0-454ae4a32116"
RUN_A_NEGATIVE_TARGET_ID = "4044136b-586f-419c-88c7-5d2c5b79ccef"
RUN_B_POSITIVE_TARGET_ID = "fc7d00dc-d4e7-4da6-ace1-83babbc0a324"

assert RUN_A_ID in RUNTIMES_BY_RUN_ID, f"Required representative run missing from test runtimes: {RUN_A_ID}"
assert RUN_B_ID in RUNTIMES_BY_RUN_ID, f"Required representative run missing from test runtimes: {RUN_B_ID}"
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
    VISUAL_TARGET_ID, VISUAL_ACCESSION = resolve_target_for_accession(_bootstrap_session, RUN_ID, accession_number="LOCALAPS00020")
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

    visual_linkage = (
        _bootstrap_session.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == RUN_ID,
            ApsContentLinkage.target_id == VISUAL_TARGET_ID,
        )
        .first()
    )
    assert visual_linkage is not None and visual_linkage.diagnostics_ref
    visual_ordered_units = json.loads(Path(visual_linkage.diagnostics_ref).read_text(encoding="utf-8")).get("ordered_units") or []
    visual_doc = (
        _bootstrap_session.query(ApsContentDocument)
        .filter(ApsContentDocument.content_id == visual_linkage.content_id)
        .first()
    )
    assert visual_doc is not None
    EXPECTED_VISUAL_ARTIFACT_REFS = json.loads(visual_doc.visual_page_refs_json or "[]")
    EXPECTED_VISUAL_ARTIFACT_PAGE2_COUNT = len([item for item in EXPECTED_VISUAL_ARTIFACT_REFS if item.get("page_number") == 2])
    EXPECTED_VISUAL_ARTIFACT_PAGE2_SHA256 = str(EXPECTED_VISUAL_ARTIFACT_REFS[0].get("visual_artifact_sha256"))
    EXPECTED_VISUAL_UNIT_PAGE3_KINDS = sorted({
        str(unit.get("unit_kind") or "").strip()
        for unit in visual_ordered_units
        if unit.get("page_number") == 3 and str(unit.get("unit_kind") or "").strip() in {"pdf_table", "ocr_image_supplement"}
    })

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


def _resolve_runtime_artifact_path(runtime_root: Path, artifact_ref: str | None) -> Path | None:
    if not artifact_ref:
        return None
    raw_path = Path(artifact_ref)
    return (runtime_root / raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()


def _resolve_target_runtime_artifact_paths(run_id: str, target_id: str) -> tuple[Path | None, Path | None]:
    runtime = RUNTIMES_BY_RUN_ID[run_id]
    session = make_session(runtime)
    try:
        linkage = (
            session.query(ApsContentLinkage)
            .filter(
                ApsContentLinkage.run_id == run_id,
                ApsContentLinkage.target_id == target_id,
            )
            .first()
        )
    finally:
        session.close()
    assert linkage is not None, f"Expected linkage for representative target {target_id} in run {run_id}"
    diagnostics_path = _resolve_runtime_artifact_path(runtime.runtime_dir, linkage.diagnostics_ref)
    normalized_text_path = _resolve_runtime_artifact_path(runtime.runtime_dir, linkage.normalized_text_ref)
    return diagnostics_path, normalized_text_path


def _normalized_path_key(path_value: str | Path) -> str:
    try:
        return str(Path(path_value).resolve()).lower()
    except Exception:
        return str(path_value).lower()


@contextmanager
def _instrument_document_trace_route_backend(run_id: str, target_id: str):
    diagnostics_path, normalized_text_path = _resolve_target_runtime_artifact_paths(run_id, target_id)
    diagnostics_key = _normalized_path_key(diagnostics_path) if diagnostics_path is not None else None
    normalized_text_key = _normalized_path_key(normalized_text_path) if normalized_text_path is not None else None

    counters = {
        "query_total": 0,
        "query_by_model": Counter(),
        "diagnostics_loader_calls": 0,
        "diagnostics_file_reads": 0,
        "normalized_text_reads": 0,
    }
    tracked_model_names = {"ConnectorRunTarget", "ApsContentLinkage", "ApsContentDocument", "ApsContentChunk"}

    original_query = OrmSession.query
    original_load_diagnostics = trace_service._load_diagnostics_json
    original_read_text = Path.read_text

    def wrapped_query(self, *entities, **kwargs):  # noqa: ANN001
        if entities:
            first = entities[0]
            model_name = getattr(first, "__name__", None)
            if model_name in tracked_model_names:
                counters["query_total"] += 1
                counters["query_by_model"][model_name] += 1
        return original_query(self, *entities, **kwargs)

    def wrapped_load_diagnostics(lnk, root):  # noqa: ANN001
        counters["diagnostics_loader_calls"] += 1
        return original_load_diagnostics(lnk, root)

    def wrapped_read_text(path_obj, *args, **kwargs):  # noqa: ANN001
        resolved_key = _normalized_path_key(path_obj)
        if diagnostics_key and resolved_key == diagnostics_key:
            counters["diagnostics_file_reads"] += 1
        if normalized_text_key and resolved_key == normalized_text_key:
            counters["normalized_text_reads"] += 1
        return original_read_text(path_obj, *args, **kwargs)

    OrmSession.query = wrapped_query
    trace_service._load_diagnostics_json = wrapped_load_diagnostics
    Path.read_text = wrapped_read_text
    try:
        yield counters
    finally:
        OrmSession.query = original_query
        trace_service._load_diagnostics_json = original_load_diagnostics
        Path.read_text = original_read_text


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
        lambda db, run_id, target_id, root, storage_root=None, page_number=None: NrcApsReviewExtractedUnitsOut(
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


def test_api_extracted_units_expose_visual_artifacts_for_positive_document():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{VISUAL_TARGET_ID}/extracted-units?page_number=2")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["visual_artifacts"]) == EXPECTED_VISUAL_ARTIFACT_PAGE2_COUNT
    artifact = payload["visual_artifacts"][0]
    assert artifact["page_number"] == 2
    assert artifact["status"] == "preserved"
    assert artifact["format"] == "png"
    assert artifact["media_type"] == "image/png"
    assert artifact["sha256"] == EXPECTED_VISUAL_ARTIFACT_PAGE2_SHA256
    assert artifact["endpoint"].endswith(f"/visual-artifacts/{artifact['artifact_id']}")


def test_api_extracted_units_page3_preserves_visual_derived_unit_kinds():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{VISUAL_TARGET_ID}/extracted-units?page_number=3")
    assert response.status_code == 200
    payload = response.json()
    actual_kinds = sorted({unit["unit_kind"] for unit in payload["units"] if unit.get("unit_kind") in {"pdf_table", "ocr_image_supplement"}})
    assert actual_kinds == EXPECTED_VISUAL_UNIT_PAGE3_KINDS


def test_api_visual_artifact_stream_success():
    extracted_units = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/documents/{VISUAL_TARGET_ID}/extracted-units?page_number=2").json()
    artifact = extracted_units["visual_artifacts"][0]
    response = client.get(artifact["endpoint"])
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")


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


def test_api_route_level_document_trace_backend_data_path_audit() -> None:
    base = f"/api/v1/review/nrc-aps/runs/{RUN_A_ID}/documents/{RUN_A_POSITIVE_TARGET_ID}"
    route_expectations = [
        (
            "trace",
            f"{base}/trace",
            {
                "query_total": 2,
                "chunk_queries": 1,
                "diagnostics_loader_calls": 1,
                "diagnostics_file_reads": 1,
                "normalized_text_reads": 0,
            },
        ),
        (
            "diagnostics",
            f"{base}/diagnostics",
            {
                "query_total": 1,
                "chunk_queries": 0,
                "diagnostics_loader_calls": 1,
                "diagnostics_file_reads": 1,
                "normalized_text_reads": 0,
            },
        ),
        (
            "normalized_text",
            f"{base}/normalized-text",
            {
                "query_total": 1,
                "chunk_queries": 0,
                "diagnostics_loader_calls": 1,
                "diagnostics_file_reads": 1,
                "normalized_text_reads": 1,
            },
        ),
        (
            "indexed_chunks",
            f"{base}/indexed-chunks",
            {
                "query_total": 2,
                "chunk_queries": 1,
                "diagnostics_loader_calls": 0,
                "diagnostics_file_reads": 0,
                "normalized_text_reads": 0,
            },
        ),
        (
            "extracted_units_all",
            f"{base}/extracted-units",
            {
                "query_total": 1,
                "chunk_queries": 0,
                "diagnostics_loader_calls": 1,
                "diagnostics_file_reads": 1,
                "normalized_text_reads": 0,
            },
        ),
        (
            "extracted_units_page2",
            f"{base}/extracted-units?page_number=2",
            {
                "query_total": 1,
                "chunk_queries": 0,
                "diagnostics_loader_calls": 1,
                "diagnostics_file_reads": 1,
                "normalized_text_reads": 0,
            },
        ),
        (
            "extracted_units_page3",
            f"{base}/extracted-units?page_number=3",
            {
                "query_total": 1,
                "chunk_queries": 0,
                "diagnostics_loader_calls": 1,
                "diagnostics_file_reads": 1,
                "normalized_text_reads": 0,
            },
        ),
    ]

    for route_label, route_path, expected in route_expectations:
        with _instrument_document_trace_route_backend(RUN_A_ID, RUN_A_POSITIVE_TARGET_ID) as counters:
            response = client.get(route_path)

        assert response.status_code == 200, f"Route {route_label} should return 200 in representative run A positive case"
        assert counters["query_total"] == expected["query_total"], f"Unexpected query count for route {route_label}"
        assert counters["query_by_model"]["ConnectorRunTarget"] == 1, f"Route {route_label} must resolve one target context query"
        assert counters["query_by_model"].get("ApsContentChunk", 0) == expected["chunk_queries"], (
            f"Unexpected chunk query count for route {route_label}"
        )
        assert counters["diagnostics_loader_calls"] == expected["diagnostics_loader_calls"], (
            f"Unexpected diagnostics loader count for route {route_label}"
        )
        assert counters["diagnostics_file_reads"] == expected["diagnostics_file_reads"], (
            f"Unexpected diagnostics file read count for route {route_label}"
        )
        assert counters["normalized_text_reads"] == expected["normalized_text_reads"], (
            f"Unexpected normalized-text read count for route {route_label}"
        )


def test_api_session_level_document_trace_backend_data_path_audit() -> None:
    base = f"/api/v1/review/nrc-aps/runs/{RUN_A_ID}/documents/{RUN_A_POSITIVE_TARGET_ID}"
    flow = [
        f"{base}/trace",
        f"{base}/extracted-units",
        f"{base}/diagnostics",
        f"{base}/normalized-text",
        f"{base}/indexed-chunks",
    ]

    with _instrument_document_trace_route_backend(RUN_A_ID, RUN_A_POSITIVE_TARGET_ID) as counters:
        statuses = [client.get(route_path).status_code for route_path in flow]

    assert statuses == [200, 200, 200, 200, 200]
    assert counters["query_total"] == 7
    assert counters["query_by_model"]["ConnectorRunTarget"] == 5
    assert counters["query_by_model"].get("ApsContentChunk", 0) == 2
    assert counters["diagnostics_loader_calls"] == 4
    assert counters["diagnostics_file_reads"] == 4
    assert counters["normalized_text_reads"] == 1


def test_api_representative_run_a_positive_visual_behavior_preserved() -> None:
    base = f"/api/v1/review/nrc-aps/runs/{RUN_A_ID}/documents/{RUN_A_POSITIVE_TARGET_ID}"
    page2_payload = client.get(f"{base}/extracted-units?page_number=2").json()
    page3_payload = client.get(f"{base}/extracted-units?page_number=3").json()

    assert page2_payload["available"] is True
    assert len(page2_payload["visual_artifacts"]) > 0
    assert all(item["page_number"] == 2 for item in page2_payload["visual_artifacts"])
    assert all(item["status"] == "preserved" for item in page2_payload["visual_artifacts"])

    assert page3_payload["available"] is True
    assert page3_payload["visual_artifacts"] == []
    page3_visual_kinds = {
        unit["unit_kind"]
        for unit in page3_payload["units"]
        if unit.get("unit_kind") in {"pdf_table", "ocr_image_supplement"}
    }
    assert page3_visual_kinds == {"pdf_table", "ocr_image_supplement"}


def test_api_representative_run_a_mixed_behavior_preserved() -> None:
    base = f"/api/v1/review/nrc-aps/runs/{RUN_A_ID}/documents/{RUN_A_MIXED_TARGET_ID}"
    diagnostics_payload = client.get(f"{base}/diagnostics").json()
    extracted_payload = client.get(f"{base}/extracted-units").json()

    assert diagnostics_payload["available"] is True
    assert diagnostics_payload["visual_derivative_unit_count"] > 0
    assert extracted_payload["available"] is True
    assert extracted_payload["visual_artifacts"] == []


def test_api_representative_run_a_negative_behavior_preserved() -> None:
    base = f"/api/v1/review/nrc-aps/runs/{RUN_A_ID}/documents/{RUN_A_NEGATIVE_TARGET_ID}"
    diagnostics_payload = client.get(f"{base}/diagnostics").json()
    extracted_payload = client.get(f"{base}/extracted-units").json()

    assert diagnostics_payload["available"] is True
    assert diagnostics_payload["visual_derivative_unit_count"] == 0
    assert extracted_payload["available"] is True
    assert extracted_payload["visual_artifacts"] == []
    assert not any(
        unit.get("unit_kind") in {"pdf_table", "ocr_image_supplement"}
        for unit in extracted_payload["units"]
    )


def test_api_representative_run_b_positive_matches_run_a_positive() -> None:
    run_a_base = f"/api/v1/review/nrc-aps/runs/{RUN_A_ID}/documents/{RUN_A_POSITIVE_TARGET_ID}"
    run_b_base = f"/api/v1/review/nrc-aps/runs/{RUN_B_ID}/documents/{RUN_B_POSITIVE_TARGET_ID}"

    run_a_trace = client.get(f"{run_a_base}/trace").json()
    run_b_trace = client.get(f"{run_b_base}/trace").json()
    run_a_page2 = client.get(f"{run_a_base}/extracted-units?page_number=2").json()
    run_b_page2 = client.get(f"{run_b_base}/extracted-units?page_number=2").json()
    run_a_page3 = client.get(f"{run_a_base}/extracted-units?page_number=3").json()
    run_b_page3 = client.get(f"{run_b_base}/extracted-units?page_number=3").json()

    assert run_a_trace["summary"]["visual_page_ref_count"] == run_b_trace["summary"]["visual_page_ref_count"]
    assert run_a_trace["summary"]["visual_derivative_unit_count"] == run_b_trace["summary"]["visual_derivative_unit_count"]
    assert len(run_a_page2["visual_artifacts"]) == len(run_b_page2["visual_artifacts"])
    assert all(item["page_number"] == 2 for item in run_b_page2["visual_artifacts"])
    assert run_a_page3["visual_artifacts"] == run_b_page3["visual_artifacts"] == []

    run_a_page3_kinds = sorted(
        {
            unit["unit_kind"]
            for unit in run_a_page3["units"]
            if unit.get("unit_kind") in {"pdf_table", "ocr_image_supplement"}
        }
    )
    run_b_page3_kinds = sorted(
        {
            unit["unit_kind"]
            for unit in run_b_page3["units"]
            if unit.get("unit_kind") in {"pdf_table", "ocr_image_supplement"}
        }
    )
    assert run_a_page3_kinds == run_b_page3_kinds
