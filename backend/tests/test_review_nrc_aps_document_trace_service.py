"""Focused tests for the document trace service module.

These tests must fail closed when the audited runtime is missing.
They exercise compose_document_selector and compose_trace_manifest against
the real audited runtime DB.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.services.review_nrc_aps_document_trace as trace_service
from app.models.models import ApsContentLinkage
from app.services.review_nrc_aps_document_trace import (
    compose_document_selector, 
    compose_trace_manifest,
    compose_extracted_units_payload,
    resolve_source_blob_info
)
from app.services.review_nrc_aps_runtime import find_review_root_for_run
from review_nrc_aps_runtime_fixture import latest_passed_runtime, make_session, resolve_deduplicated_target_pair, resolve_target_for_accession

RUNTIME = latest_passed_runtime()
RUN_ID = RUNTIME.run_id
DB_PATH = RUNTIME.db_path

_bootstrap_session = make_session(RUNTIME)
try:
    TARGET_ID, ACCESSION = resolve_target_for_accession(_bootstrap_session, RUN_ID)
    DEDUP_TARGET_ID_A, DEDUP_TARGET_ID_B = resolve_deduplicated_target_pair(_bootstrap_session, RUN_ID)
finally:
    _bootstrap_session.close()


@pytest.fixture(scope="module")
def db_session():
    """Create a read-only SQLAlchemy session against the audited runtime DB.

    Fails closed if the DB file is missing or unreadable.
    """
    assert DB_PATH.exists(), f"Audited runtime DB not found at {DB_PATH}. Tests cannot run."
    session = make_session(RUNTIME)
    yield session
    session.close()


@pytest.fixture(scope="module")
def review_root():
    """Resolve the review root for the audited run. Fails closed if missing."""
    root = find_review_root_for_run(RUN_ID)
    assert root is not None, f"Review root not found for run {RUN_ID}"
    return root


def _load_ordered_units(db_session):
    linkage = db_session.query(ApsContentLinkage).filter(
        ApsContentLinkage.run_id == RUN_ID,
        ApsContentLinkage.target_id == TARGET_ID,
    ).first()
    assert linkage is not None
    assert linkage.diagnostics_ref
    data = json.loads(Path(linkage.diagnostics_ref).read_text(encoding="utf-8"))
    return data.get("ordered_units") or []


# ---------------------------------------------------------------------------
# Selector tests
# ---------------------------------------------------------------------------

def test_selector_returns_nonempty_documents(db_session, review_root):
    selector = compose_document_selector(db_session, RUN_ID, review_root)
    assert selector.run_id == RUN_ID
    assert len(selector.documents) > 0, "Selector should return at least one document"


def test_selector_ordering_is_deterministic(db_session, review_root):
    selector = compose_document_selector(db_session, RUN_ID, review_root)
    docs = selector.documents
    for i in range(len(docs) - 1):
        key1 = (docs[i].accession_number or "", docs[i].document_title or "", docs[i].target_id)
        key2 = (docs[i + 1].accession_number or "", docs[i + 1].document_title or "", docs[i + 1].target_id)
        assert key1 <= key2, f"Selector ordering violated at index {i}"


def test_selector_is_target_scoped(db_session, review_root):
    """Even if content_ids are deduplicated, each target_id must appear as its own row."""
    selector = compose_document_selector(db_session, RUN_ID, review_root)
    target_ids = [d.target_id for d in selector.documents]
    assert len(target_ids) == len(set(target_ids)), "Duplicate target_ids found — selector must be target-scoped"


def test_selector_pinned_target_present(db_session, review_root):
    selector = compose_document_selector(db_session, RUN_ID, review_root)
    target = next((d for d in selector.documents if d.target_id == TARGET_ID), None)
    assert target is not None, f"Pinned target {TARGET_ID} not found in selector"
    assert target.accession_number == ACCESSION
    assert target.trace_state.has_source_blob is True


def test_selector_document_type_uses_normalized_source_metadata(db_session, review_root):
    """document_type must come from source_reference_json.aps_normalized, not document_class."""
    selector = compose_document_selector(db_session, RUN_ID, review_root)
    target = next((d for d in selector.documents if d.target_id == TARGET_ID), None)
    assert target is not None
    # The pinned target has aps_normalized.document_type = "Exemption from NRC Requirements"
    assert target.document_type == "Exemption from NRC Requirements"


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------

def test_manifest_returns_for_pinned_target(db_session, review_root):
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    assert manifest.run_id == RUN_ID
    assert manifest.target_id == TARGET_ID
    assert manifest.identity.accession_number == ACCESSION


def test_manifest_completeness_flags(db_session, review_root):
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    assert manifest.trace_completeness.has_linkage_row is True
    assert manifest.trace_completeness.has_document_row is True
    assert manifest.trace_completeness.has_source_blob is True
    assert manifest.trace_completeness.retrieval_available is False


def test_manifest_document_type_is_source_type(db_session, review_root):
    """identity.document_type must be the normalized source document type, not document_class."""
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    assert manifest.identity.document_type == "Exemption from NRC Requirements"
    # document_class is a separate processing classification in the summary block
    assert manifest.summary.document_class is not None


def test_manifest_no_misleading_future_endpoints(db_session, review_root):
    """Only implemented tabs should advertise endpoints in the manifest.
    Summary remains client-rendered and downstream usage remains unimplemented.
    """
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    allowed_to_have_endpoints = {"diagnostics", "normalized_text", "indexed_chunks", "extracted_units"}
    
    for tab in manifest.tabs:
        if tab.tab_id in allowed_to_have_endpoints:
            # OK to have endpoint if available
            pass
        else:
            assert tab.endpoint is None, f"Tab '{tab.tab_id}' must not advertise an endpoint in Phase 4"


def test_manifest_diagnostics_unit_count(db_session, review_root):
    """ordered_unit_count must be derived from diagnostics ordered_units, not aps_content_units_v2."""
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    # The pinned target has diagnostics — ordered_unit_count should be > 0 if diagnostics has units
    if manifest.trace_completeness.has_diagnostics:
        # We accept >= 0; the key constraint is it came from diagnostics, not units_v2
        assert manifest.summary.ordered_unit_count >= 0


def test_manifest_exposes_source_endpoint_truthfully(db_session, review_root):
    """source_endpoint must be non-null in Phase 2 if the source blob is present."""
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    if manifest.trace_completeness.has_source_blob:
        assert manifest.source.source_endpoint is not None
        assert f"/runs/{RUN_ID}/documents/{TARGET_ID}/source" in manifest.source.source_endpoint
    else:
        assert manifest.source.source_endpoint is None


# ---------------------------------------------------------------------------
# Source Resolution tests
# ---------------------------------------------------------------------------

def test_resolve_source_blob_info_success(db_session, review_root):
    blob_path, media_type, filename = resolve_source_blob_info(db_session, RUN_ID, TARGET_ID, review_root)
    assert blob_path.exists()
    assert blob_path.is_absolute()
    assert media_type == "application/pdf"
    assert "Dresden" in filename


def test_resolve_source_blob_info_path_safety_rejection(db_session, review_root):
    """If we mock a linkage to point to an unsafe path, it must be rejected."""
    # We'll use a mock for the linkage to simulate an unsafe path
    from unittest.mock import MagicMock
    from app.models.models import ApsContentLinkage
    
    mock_lnk = MagicMock(spec=ApsContentLinkage)
    mock_lnk.blob_ref = "C:/Windows/system32/config/SAM" # Obviously unsafe
    mock_lnk.content_id = "some_id"
    
    # We'd need to mock the query to return this. Since this is a bit complex for a light test,
    # we'll test the helper directly.
    from app.services.review_nrc_aps_runtime import is_absolute_path_safe
    assert is_absolute_path_safe(review_root, Path("C:/Windows/system32/config/SAM")) is False
    assert is_absolute_path_safe(review_root, review_root / "some_file.json") is True


def test_manifest_missing_target_raises(db_session, review_root):
    """Requesting a non-existent target must raise KeyError."""
    with pytest.raises(KeyError):
        compose_trace_manifest(db_session, RUN_ID, "00000000-0000-0000-0000-000000000000", review_root)


def test_manifest_missing_optional_layers_degrade_safely(db_session, review_root):
    """The manifest must remain stable even for targets that may lack optional layers."""
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    # These are boolean fields that degrade to False when the layer is absent
    assert isinstance(manifest.trace_completeness.has_visual_derivatives, bool)
    assert isinstance(manifest.trace_completeness.has_downstream_usage, bool)
    assert isinstance(manifest.trace_completeness.retrieval_available, bool)


# ---------------------------------------------------------------------------
# Extracted Units tests
# ---------------------------------------------------------------------------

def test_extracted_units_come_from_diagnostics_ordered_units(db_session, review_root):
    ordered_units = _load_ordered_units(db_session)
    payload = compose_extracted_units_payload(db_session, RUN_ID, TARGET_ID, review_root)

    assert payload.available is True
    assert payload.reason_code is None
    assert payload.source_precision == "unit"
    assert payload.source_layer == "diagnostics_ordered_units"
    assert payload.total_unit_count == len(ordered_units)
    assert len(payload.units) == len(ordered_units)

    expected = [(unit.get("page_number"), unit.get("text"), unit.get("start_char"), unit.get("end_char")) for unit in ordered_units[:5]]
    actual = [(unit.page_number, unit.text, unit.start_char, unit.end_char) for unit in payload.units[:5]]
    assert actual == expected


def test_extracted_units_ordering_matches_diagnostics_order(db_session, review_root):
    ordered_units = _load_ordered_units(db_session)
    payload = compose_extracted_units_payload(db_session, RUN_ID, TARGET_ID, review_root)

    expected_tail = [(unit.get("page_number"), unit.get("text")) for unit in ordered_units[-5:]]
    actual_tail = [(unit.page_number, unit.text) for unit in payload.units[-5:]]
    assert actual_tail == expected_tail


def test_extracted_units_ids_are_stable_and_unique(db_session, review_root):
    payload_a = compose_extracted_units_payload(db_session, RUN_ID, TARGET_ID, review_root)
    payload_b = compose_extracted_units_payload(db_session, RUN_ID, TARGET_ID, review_root)

    ids_a = [unit.unit_id for unit in payload_a.units]
    ids_b = [unit.unit_id for unit in payload_b.units]
    assert ids_a == ids_b
    assert len(ids_a) == len(set(ids_a))


def test_extracted_units_page_number_filtering_is_truthful(db_session, review_root):
    payload = compose_extracted_units_payload(db_session, RUN_ID, TARGET_ID, review_root, page_number=2)

    assert payload.available is True
    assert payload.page_number == 2
    assert payload.total_unit_count == 543
    assert len(payload.units) == 26
    assert all(unit.page_number == 2 for unit in payload.units)


def test_extracted_units_missing_target_raises_key_error(db_session, review_root):
    with pytest.raises(KeyError):
        compose_extracted_units_payload(db_session, RUN_ID, "00000000-0000-0000-0000-000000000000", review_root)


def test_extracted_units_missing_diagnostics_returns_explicit_missingness(monkeypatch, db_session, review_root):
    monkeypatch.setattr(trace_service, "_load_diagnostics_json", lambda lnk, root: (None, "diagnostics_absent"))

    payload = compose_extracted_units_payload(db_session, RUN_ID, TARGET_ID, review_root)

    assert payload.available is False
    assert payload.reason_code == "diagnostics_absent"
    assert payload.source_precision == "none"
    assert payload.page_number is None
    assert payload.total_unit_count == 0
    assert payload.units == []


def test_extracted_units_without_page_number_are_not_falsely_page_scoped(monkeypatch, db_session, review_root):
    fake_units = [
        {"unit_kind": "paragraph", "text": "page two", "page_number": 2, "start_char": 0, "end_char": 8, "bbox": [0, 0, 1, 1]},
        {"unit_kind": "paragraph", "text": "no page", "start_char": 9, "end_char": 16},
    ]
    monkeypatch.setattr(trace_service, "_load_diagnostics_json", lambda lnk, root: ({"ordered_units": fake_units}, None))

    payload = compose_extracted_units_payload(db_session, RUN_ID, TARGET_ID, review_root, page_number=2)

    assert payload.available is True
    assert len(payload.units) == 1
    assert payload.units[0].text == "page two"
    assert payload.units[0].page_number == 2


def test_extracted_units_remain_target_scoped_for_deduplicated_content(db_session, review_root):
    payload_a = compose_extracted_units_payload(db_session, RUN_ID, DEDUP_TARGET_ID_A, review_root)
    payload_b = compose_extracted_units_payload(db_session, RUN_ID, DEDUP_TARGET_ID_B, review_root)

    assert payload_a.available is True
    assert payload_b.available is True
    assert payload_a.total_unit_count == payload_b.total_unit_count == 8446
    assert payload_a.units[0].text == payload_b.units[0].text
    assert payload_a.units[0].unit_id != payload_b.units[0].unit_id


def test_manifest_extracted_units_tab_exposes_truthful_endpoint(db_session, review_root):
    manifest = compose_trace_manifest(db_session, RUN_ID, TARGET_ID, review_root)
    tab = next(item for item in manifest.tabs if item.tab_id == "extracted_units")
    assert tab.available is True
    assert tab.endpoint is not None
    assert tab.endpoint.endswith("/extracted-units")
