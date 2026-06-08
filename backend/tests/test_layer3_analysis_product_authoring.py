"""Tests for layer3_analysis_product_authoring service.

Uses an in-memory SQLite database matching the StaticPool pattern from the
existing layer3 service test suite.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import (
    L3AnalysisProduct,
    L3AnalysisProductEvidenceLink,
    L3AnalysisSet,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
)
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    Layer3AnalysisProductError,
    create_analysis_product_draft,
)
from app.services.layer3_sublayer_state import (
    serialize_analysis_product,
    session_analyst_products,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def seeded_db(db_session):
    """Seed an active_execution session with one material_snapshot and one pass_run."""
    analysis_plan_id = "plan-aprod-test"
    analysis_set_id = "set-aprod-test"

    session_row = L3Session(
        session_id="session-aprod-test",
        selection_manifest_id="manifest-aprod-test",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id="snapshot-aprod-test",
        session_id="session-aprod-test",
        descriptor_id="descriptor-aprod-test",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://aprod-test",
        payload_hash="hash-aprod-test",
        source_identity_json={"dataset_version_id": "dv-aprod-test"},
        source_provenance_json={},
        load_summary_json={},
    )
    # Minimal L3AnalysisSet required for prior_product evidence test
    from app.models.models import L3AnalysisPlan, L3AnalysisUnit, L3AnalysisGroup

    analysis_unit = L3AnalysisUnit(
        analysis_unit_id="unit-aprod-test",
        session_id="session-aprod-test",
        unit_kind="material_snapshot",
        analysis_modality="quantitative",
        member_snapshot_ids_json=["snapshot-aprod-test"],
        member_ranges_json=[],
        must_remain_intact=True,
        typing_record_ids_json=[],
        unit_hash="unit-hash-aprod-test",
        summary_json={},
    )
    analysis_group = L3AnalysisGroup(
        analysis_group_id="group-aprod-test",
        session_id="session-aprod-test",
        analysis_modality="quantitative",
        typing_basis_json={},
        analysis_unit_ids_json=["unit-aprod-test"],
        status="formed",
    )
    analysis_set = L3AnalysisSet(
        analysis_set_id=analysis_set_id,
        session_id="session-aprod-test",
        analysis_group_ids_json=["group-aprod-test"],
        analysis_unit_ids_json=["unit-aprod-test"],
        set_type="associated_cohort",
        formation_basis_json={},
    )
    from datetime import datetime, timezone
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=analysis_plan_id,
        session_id="session-aprod-test",
        analysis_set_ids_json=[analysis_set_id],
        status="approved",
        approved_by_operator=True,
        approved_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    pass_run = L3PassRun(
        pass_run_id="pass-run-aprod-test",
        session_id="session-aprod-test",
        analysis_plan_id=analysis_plan_id,
        analysis_set_id=analysis_set_id,
        pass_type="associated_cohort",
        engine_family="wrapped_quantitative_analysis",
        status="completed",
        input_payload_ref="payload://input-aprod",
        output_payload_ref="payload://output-aprod",
        summary_json={},
    )
    db_session.add_all(
        [
            session_row,
            snapshot,
            analysis_unit,
            analysis_group,
            analysis_set,
            analysis_plan,
            pass_run,
        ]
    )
    db_session.commit()
    return db_session


# ---------------------------------------------------------------------------
# Happy path: grounded finding
# ---------------------------------------------------------------------------


def test_happy_grounded_finding(seeded_db) -> None:
    db = seeded_db
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Test finding",
        body="This is the body of the finding with sufficient detail.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    result = create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-finding-001",
        draft=draft,
    )
    db.commit()

    assert result.replayed is False
    product = result.product
    assert product.product_kind == "finding"
    assert product.lifecycle_status == "draft"
    assert product.executor_type == "human"
    assert product.is_non_evidentiary is False
    assert product.basis_hash
    assert product.spec_hash
    assert len(result.evidence_links) == 1
    link = result.evidence_links[0]
    assert link.ref_kind == "material_snapshot"
    assert link.ref_id == "snapshot-aprod-test"
    assert link.evidence_role == "observation"

    # DB has exactly 1 product row
    count = db.query(L3AnalysisProduct).count()
    assert count == 1


# ---------------------------------------------------------------------------
# serialize_analysis_product and session_analyst_products
# ---------------------------------------------------------------------------


def test_serialize_analysis_product_shape(seeded_db) -> None:
    db = seeded_db
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Serialized finding",
        body="Body for serialization test.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    result = create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-serialize-001",
        draft=draft,
    )
    db.commit()

    serialized = serialize_analysis_product(result.product, list(result.evidence_links))

    assert "analysis_product_id" in serialized
    assert serialized["product_kind"] == "finding"
    assert serialized["title"] == "Serialized finding"
    # body must NOT be present
    assert "body" not in serialized
    assert serialized["grounded"] is True
    assert serialized["is_non_evidentiary"] is False
    assert serialized["evidence_count"] == 1
    assert serialized["by_evidence_role"] == {"observation": 1}
    assert len(serialized["evidence_refs"]) == 1
    assert serialized["evidence_refs"][0]["ref_kind"] == "material_snapshot"
    assert serialized["basis_hash"]
    assert serialized["spec_hash"]
    assert serialized["created_at"] is not None


def test_session_analyst_products_returns_list(seeded_db) -> None:
    db = seeded_db
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Inventory finding",
        body="Body for inventory test.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-inventory-001",
        draft=draft,
    )
    db.commit()

    products = session_analyst_products(db, session_id="session-aprod-test")
    assert len(products) == 1
    assert products[0]["product_kind"] == "finding"
    assert "body" not in products[0]
    assert products[0]["grounded"] is True


# ---------------------------------------------------------------------------
# Non-evidentiary analyst_note
# ---------------------------------------------------------------------------


def test_happy_non_evidentiary_analyst_note(seeded_db) -> None:
    db = seeded_db
    draft = AnalysisProductDraft(
        product_kind="analyst_note",
        title="Background context note",
        body="This is a non-evidentiary analyst note. No evidence links.",
        evidence=(),
        is_non_evidentiary=True,
    )
    result = create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-note-001",
        draft=draft,
    )
    db.commit()

    assert result.replayed is False
    assert result.product.is_non_evidentiary is True
    assert result.product.lifecycle_status == "draft"
    serialized = serialize_analysis_product(result.product, list(result.evidence_links))
    assert serialized["grounded"] is False
    assert serialized["is_non_evidentiary"] is True
    assert serialized["evidence_count"] == 0


# ---------------------------------------------------------------------------
# Fail-closed: invalid inputs
# ---------------------------------------------------------------------------


def test_invalid_product_kind(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="bogus_kind",
        title="Title",
        body="Body text here.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-invalid-kind",
            draft=draft,
        )
    assert exc_info.value.error_code == "invalid_product_kind"


def test_empty_title_rejected(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="   ",
        body="Non-empty body text.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-empty-title",
            draft=draft,
        )
    assert exc_info.value.error_code == "invalid_title"


def test_empty_body_rejected(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Valid title",
        body="   ",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-empty-body",
            draft=draft,
        )
    assert exc_info.value.error_code == "invalid_body"


def test_title_too_long_rejected(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="A" * 257,
        body="Valid body text.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-long-title",
            draft=draft,
        )
    assert exc_info.value.error_code == "invalid_title"


def test_finding_with_no_evidence_rejected(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Finding with no evidence",
        body="No evidence provided but finding kind requires it.",
        evidence=(),
        is_non_evidentiary=False,
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-no-evidence",
            draft=draft,
        )
    assert exc_info.value.error_code == "missing_evidence"


def test_non_evidentiary_on_finding_rejected(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Non-evidentiary finding",
        body="Should be rejected.",
        evidence=(),
        is_non_evidentiary=True,
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-ne-finding",
            draft=draft,
        )
    assert exc_info.value.error_code == "non_evidentiary_kind_not_allowed"


def test_non_evidentiary_note_with_evidence_rejected(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="analyst_note",
        title="Non-evidentiary note with evidence",
        body="Should be rejected because evidence is provided.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
        is_non_evidentiary=True,
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-ne-with-ev",
            draft=draft,
        )
    assert exc_info.value.error_code == "non_evidentiary_with_evidence"


def test_invalid_evidence_ref_kind_rejected(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Finding with bad ref_kind",
        body="Body text.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="unknown_table",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-bad-ref-kind",
            draft=draft,
        )
    assert exc_info.value.error_code == "invalid_evidence_ref_kind"


def test_evidence_ref_not_in_session_rejected(seeded_db) -> None:
    """ref_id points to a snapshot that does not exist in the session."""
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Finding with foreign snapshot",
        body="Body text.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-does-not-exist",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-aprod-test",
            client_request_id="req-foreign-snapshot",
            draft=draft,
        )
    assert exc_info.value.error_code == "evidence_ref_not_found_in_session"
    assert exc_info.value.http_status == 409


def test_session_missing_returns_404(seeded_db) -> None:
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Finding",
        body="Body text.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="nonexistent-session",
            client_request_id="req-missing-session",
            draft=draft,
        )
    assert exc_info.value.error_code == "session_not_found"
    assert exc_info.value.http_status == 404


@pytest.mark.parametrize("bad_status", ["active_loading", "failed"])
def test_session_ineligible_status_rejected(seeded_db, bad_status) -> None:
    db = seeded_db
    # Insert a second session with ineligible status
    bad_session = L3Session(
        session_id=f"session-bad-status-{bad_status}",
        selection_manifest_id=f"manifest-bad-{bad_status}",
        status=bad_status,
        operator_context_json={},
        summary_json={},
    )
    db.add(bad_session)
    db.commit()

    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Finding",
        body="Body text.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            db,
            session_id=f"session-bad-status-{bad_status}",
            client_request_id=f"req-bad-session-{bad_status}",
            draft=draft,
        )
    assert exc_info.value.error_code == "session_state_not_authoring_eligible"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotency_same_draft_returns_replayed(seeded_db) -> None:
    db = seeded_db
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Idempotency finding",
        body="Identical body for idempotency.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    result1 = create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-idem-001",
        draft=draft,
    )
    db.commit()

    result2 = create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-idem-001",
        draft=draft,
    )
    # Only one row in DB
    count = db.query(L3AnalysisProduct).count()
    assert count == 1
    assert result2.replayed is True
    assert result2.product.analysis_product_id == result1.product.analysis_product_id


def test_idempotency_different_body_raises_conflict(seeded_db) -> None:
    db = seeded_db
    draft1 = AnalysisProductDraft(
        product_kind="finding",
        title="Conflict finding",
        body="First version of the body.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-conflict-001",
        draft=draft1,
    )
    db.commit()

    draft2 = AnalysisProductDraft(
        product_kind="finding",
        title="Conflict finding",
        body="DIFFERENT body — should trigger conflict.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            db,
            session_id="session-aprod-test",
            client_request_id="req-conflict-001",
            draft=draft2,
        )
    assert exc_info.value.error_code == "idempotency_conflict"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# prior_product evidence: product B cites product A
# ---------------------------------------------------------------------------


def test_basis_hash_stable_across_reordered_duplicate_evidence(seeded_db) -> None:
    # Two evidence links to the same snapshot+role but different locators: the basis
    # hash must be order-independent, so a reordered replay is recognized as identical.
    db = seeded_db
    ev_a = AnalysisProductEvidenceDraft(
        ref_kind="material_snapshot", ref_id="snapshot-aprod-test",
        evidence_role="observation", locator={"row": 1},
    )
    ev_b = AnalysisProductEvidenceDraft(
        ref_kind="material_snapshot", ref_id="snapshot-aprod-test",
        evidence_role="observation", locator={"row": 2},
    )
    result1 = create_analysis_product_draft(
        db, session_id="session-aprod-test", client_request_id="req-dup-ev",
        draft=AnalysisProductDraft(product_kind="finding", title="Dup ev", body="Body.", evidence=(ev_a, ev_b)),
    )
    db.commit()

    result2 = create_analysis_product_draft(
        db, session_id="session-aprod-test", client_request_id="req-dup-ev",
        draft=AnalysisProductDraft(product_kind="finding", title="Dup ev", body="Body.", evidence=(ev_b, ev_a)),
    )
    assert result2.replayed is True
    assert result2.product.analysis_product_id == result1.product.analysis_product_id
    assert db.query(L3AnalysisProduct).count() == 1


def test_prior_product_evidence(seeded_db) -> None:
    db = seeded_db
    # Author product A (grounded finding)
    draft_a = AnalysisProductDraft(
        product_kind="finding",
        title="Product A",
        body="First product, grounded on a snapshot.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-aprod-test",
                evidence_role="observation",
            ),
        ),
    )
    result_a = create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-prior-a",
        draft=draft_a,
    )
    db.commit()

    # Author product B citing product A as prior_product
    draft_b = AnalysisProductDraft(
        product_kind="insight",
        title="Product B citing A",
        body="Derived insight building on prior finding A.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="prior_product",
                ref_id=result_a.product.analysis_product_id,
                evidence_role="interpretation",
            ),
        ),
    )
    result_b = create_analysis_product_draft(
        db,
        session_id="session-aprod-test",
        client_request_id="req-prior-b",
        draft=draft_b,
    )
    db.commit()

    assert result_b.replayed is False
    assert len(result_b.evidence_links) == 1
    assert result_b.evidence_links[0].ref_kind == "prior_product"
    assert result_b.evidence_links[0].ref_id == result_a.product.analysis_product_id
    # Two products total
    assert db.query(L3AnalysisProduct).count() == 2
