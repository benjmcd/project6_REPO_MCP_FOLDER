"""Tests for layer3_analysis_product_replay service.

Uses an in-memory SQLite database mirroring the seeded_db fixture pattern from
test_layer3_analysis_product_generation.py.  Creates working sets and analysis
products via generate_analysis_product, then verifies reproducibility via
verify_analysis_product_replay.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
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
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisProduct,
    L3AnalysisProductEvidenceLink,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
    L3WorkingSet,
)
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    Layer3AnalysisProductError,
    create_analysis_product_draft,
)
from app.services.layer3_analysis_product_generation import generate_analysis_product
from app.services.layer3_analysis_product_replay import verify_analysis_product_replay
from app.services.layer3_working_set import (
    WorkingSetDraft,
    WorkingSetMemberDraft,
    create_working_set,
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
    """Seed an active_execution session with snapshot and pass_run (mirrors working_set test pattern)."""
    analysis_plan_id = "plan-gen-test"
    analysis_set_id = "set-gen-test"

    session_row = L3Session(
        session_id="session-gen-test",
        selection_manifest_id="manifest-gen-test",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id="snapshot-gen-test",
        session_id="session-gen-test",
        descriptor_id="descriptor-gen-test",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://gen-test",
        payload_hash="hash-gen-test",
        source_identity_json={"dataset_version_id": "dv-gen-test"},
        source_provenance_json={},
        load_summary_json={},
    )
    analysis_unit = L3AnalysisUnit(
        analysis_unit_id="unit-gen-test",
        session_id="session-gen-test",
        unit_kind="material_snapshot",
        analysis_modality="quantitative",
        member_snapshot_ids_json=["snapshot-gen-test"],
        member_ranges_json=[],
        must_remain_intact=True,
        typing_record_ids_json=[],
        unit_hash="unit-hash-gen-test",
        summary_json={},
    )
    analysis_group = L3AnalysisGroup(
        analysis_group_id="group-gen-test",
        session_id="session-gen-test",
        analysis_modality="quantitative",
        typing_basis_json={},
        analysis_unit_ids_json=["unit-gen-test"],
        status="formed",
    )
    analysis_set = L3AnalysisSet(
        analysis_set_id=analysis_set_id,
        session_id="session-gen-test",
        analysis_group_ids_json=["group-gen-test"],
        analysis_unit_ids_json=["unit-gen-test"],
        set_type="associated_cohort",
        formation_basis_json={},
    )
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=analysis_plan_id,
        session_id="session-gen-test",
        analysis_set_ids_json=[analysis_set_id],
        status="approved",
        approved_by_operator=True,
        approved_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    pass_run = L3PassRun(
        pass_run_id="pass-run-gen-test",
        session_id="session-gen-test",
        analysis_plan_id=analysis_plan_id,
        analysis_set_id=analysis_set_id,
        pass_type="associated_cohort",
        engine_family="wrapped_quantitative_analysis",
        status="completed",
        input_payload_ref="payload://input-gen",
        output_payload_ref="payload://output-gen",
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


def _make_working_set(db, *, session_id: str, name: str, client_request_id: str) -> L3WorkingSet:
    """Helper: create a working set with one material_snapshot member."""
    draft = WorkingSetDraft(
        name=name,
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-gen-test"),
        ),
    )
    result = create_working_set(
        db,
        session_id=session_id,
        client_request_id=client_request_id,
        draft=draft,
    )
    db.commit()
    return result.working_set


# ---------------------------------------------------------------------------
# Happy path: state-free method (working_set_composition_summary)
# ---------------------------------------------------------------------------


def test_replay_reproduced_state_free(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS SF", client_request_id="req-ws-replay-sf-001")

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-sf-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=gen.product.analysis_product_id,
    )

    assert result.reproduced is True
    assert result.classification == "reproduced"
    assert result.input_state_match is None  # state-free
    assert result.method_present is True
    assert result.method_version_match is True
    assert result.input_basis_match is True
    assert result.result_match is True
    assert result.result_summary_hash_current is not None
    assert result.result_summary_hash_recorded == result.result_summary_hash_current


# ---------------------------------------------------------------------------
# Happy path: state-consuming method (working_set_staleness_diagnostic)
# ---------------------------------------------------------------------------


def test_replay_reproduced_state_consuming(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS SC", client_request_id="req-ws-replay-sc-001")

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-sc-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=gen.product.analysis_product_id,
    )

    assert result.reproduced is True
    assert result.classification == "reproduced"
    assert result.input_state_match is True
    assert result.method_present is True
    assert result.method_version_match is True
    assert result.input_basis_match is True
    assert result.result_match is True


# ---------------------------------------------------------------------------
# input_state_drift: mutate a member's lifecycle_status after generation
# ---------------------------------------------------------------------------


def test_replay_input_state_drift(seeded_db) -> None:
    db = seeded_db

    # Create a prior_product member so staleness_diagnostic will track its state
    prior_product_row = L3AnalysisProduct(
        analysis_product_id="pp-replay-drift-test",
        session_id="session-gen-test",
        product_kind="summary",
        executor_type="human",
        lifecycle_status="draft",
        title="Drift test product",
        body="Body text for drift test.",
        is_non_evidentiary=False,
        basis_hash="basis-pp-replay-drift",
        spec_hash="spec-pp-replay-drift",
        client_request_id="req-pp-replay-drift-seed",
        authoring_provenance_json={},
        summary_json={},
    )
    db.add(prior_product_row)
    db.commit()

    draft = WorkingSetDraft(
        name="WS Drift",
        members=(
            WorkingSetMemberDraft(ref_kind="prior_product", ref_id="pp-replay-drift-test"),
        ),
    )
    ws_result = create_working_set(
        db,
        session_id="session-gen-test",
        client_request_id="req-ws-replay-drift-001",
        draft=draft,
    )
    db.commit()
    ws = ws_result.working_set

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-drift-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()
    product_id = gen.product.analysis_product_id

    # Mutate the prior_product's lifecycle_status to "superseded"
    prior_product_row.lifecycle_status = "superseded"
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product_id,
    )

    assert result.reproduced is False
    assert result.classification == "input_state_drift"
    assert result.input_basis_match is True
    assert result.input_state_match is False


# ---------------------------------------------------------------------------
# result_mismatch: tamper stored result_summary in provenance
# ---------------------------------------------------------------------------


def test_replay_result_mismatch(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS RM", client_request_id="req-ws-replay-rm-001")

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-rm-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product = gen.product
    # Mutate via a fresh dict assignment so SQLAlchemy detects the JSON change
    tampered = dict(product.authoring_provenance_json)
    tampered["result_summary"] = {"tampered": True}
    product.authoring_provenance_json = tampered
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product.analysis_product_id,
    )

    assert result.reproduced is False
    assert result.classification == "result_mismatch"
    assert result.result_match is False
    assert result.method_version_match is True
    assert result.input_basis_match is True


# ---------------------------------------------------------------------------
# method_version_changed: tamper stored method_version to 999
# ---------------------------------------------------------------------------


def test_replay_method_version_changed(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS MVC", client_request_id="req-ws-replay-mvc-001")

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-mvc-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product = gen.product
    tampered = dict(product.authoring_provenance_json)
    tampered["method_version"] = 999
    product.authoring_provenance_json = tampered
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product.analysis_product_id,
    )

    assert result.reproduced is False
    assert result.classification == "method_version_changed"
    assert result.method_version_match is False


def test_replay_v1_composition_product_reports_method_version_changed(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-gen-test",
        name="WS MVC V1",
        client_request_id="req-ws-replay-mvc-v1-001",
    )

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-mvc-v1-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product = gen.product
    product.product_kind = "summary"
    prior_provenance = dict(product.authoring_provenance_json)
    prior_provenance["method_version"] = 1
    product.authoring_provenance_json = prior_provenance
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product.analysis_product_id,
    )

    assert result.reproduced is False
    assert result.classification == "method_version_changed"
    assert result.method_version_recorded == 1
    assert result.method_version_current == 2
    assert result.method_version_match is False


# ---------------------------------------------------------------------------
# method_removed: tamper stored method_id to an unknown value
# ---------------------------------------------------------------------------


def test_replay_method_removed(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS MR", client_request_id="req-ws-replay-mr-001")

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-mr-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product = gen.product
    tampered = dict(product.authoring_provenance_json)
    tampered["method_id"] = "removed_method"
    product.authoring_provenance_json = tampered
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product.analysis_product_id,
    )

    assert result.reproduced is False
    assert result.classification == "method_removed"
    assert result.method_present is False


# ---------------------------------------------------------------------------
# input_basis_drift: tamper working_set.basis_hash
# ---------------------------------------------------------------------------


def test_replay_input_basis_drift(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS IBD", client_request_id="req-ws-replay-ibd-001")

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-ibd-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product_id = gen.product.analysis_product_id

    # Tamper the working set's basis_hash
    ws.basis_hash = "tampered-basis-hash"
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product_id,
    )

    assert result.reproduced is False
    assert result.classification == "input_basis_drift"
    assert result.input_basis_match is False


# ---------------------------------------------------------------------------
# working_set_missing: delete the working set row after generation
# ---------------------------------------------------------------------------


def test_replay_working_set_missing(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS WSM", client_request_id="req-ws-replay-wsm-001")

    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-wsm-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product_id = gen.product.analysis_product_id

    # Delete the working set row
    db.delete(ws)
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product_id,
    )

    assert result.reproduced is False
    assert result.classification == "working_set_missing"


# ---------------------------------------------------------------------------
# Reject non-deterministic (human) products
# ---------------------------------------------------------------------------


def test_replay_rejects_human_product(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS Human", client_request_id="req-ws-replay-h-001")

    # Create a human product via create_analysis_product_draft
    draft = AnalysisProductDraft(
        product_kind="summary",
        title="Human product",
        body="A human-authored product body for replay test.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="working_set",
                ref_id=ws.working_set_id,
                evidence_role="context",
            ),
        ),
        executor_type="human",
    )
    authoring_result = create_analysis_product_draft(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-h-001",
        draft=draft,
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        verify_analysis_product_replay(
            db,
            session_id="session-gen-test",
            analysis_product_id=authoring_result.product.analysis_product_id,
        )

    assert exc_info.value.error_code == "not_deterministic_product"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# product_not_found: non-existent product id -> 404
# ---------------------------------------------------------------------------


def test_replay_product_not_found(seeded_db) -> None:
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        verify_analysis_product_replay(
            seeded_db,
            session_id="session-gen-test",
            analysis_product_id="nonexistent-product-id",
        )

    assert exc_info.value.error_code == "analysis_product_not_found"
    assert exc_info.value.http_status == 404


# ---------------------------------------------------------------------------
# cross_session: product in session A, verify with session B -> 409
# ---------------------------------------------------------------------------


def test_replay_cross_session(seeded_db) -> None:
    db = seeded_db

    # Create second session
    other_session = L3Session(
        session_id="session-replay-other",
        selection_manifest_id="manifest-replay-other",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    db.add(other_session)
    db.commit()

    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS Cross", client_request_id="req-ws-replay-cross-001"
    )
    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-cross-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        verify_analysis_product_replay(
            db,
            session_id="session-replay-other",
            analysis_product_id=gen.product.analysis_product_id,
        )

    assert exc_info.value.error_code == "analysis_product_not_in_session"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# read_only: verify does not mutate any rows or create new rows
# ---------------------------------------------------------------------------


def test_replay_is_read_only(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS RO", client_request_id="req-ws-replay-ro-001"
    )
    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-ro-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product = gen.product
    prov_before = dict(product.authoring_provenance_json)
    status_before = product.lifecycle_status
    count_before = db.query(L3AnalysisProduct).count()

    verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product.analysis_product_id,
    )

    # Re-query to confirm no mutation
    db.expire_all()
    product_after = db.query(L3AnalysisProduct).filter(
        L3AnalysisProduct.analysis_product_id == product.analysis_product_id
    ).one()
    assert product_after.authoring_provenance_json == prov_before
    assert product_after.lifecycle_status == status_before
    assert db.query(L3AnalysisProduct).count() == count_before


# ---------------------------------------------------------------------------
# working_set_unlinked: deterministic product with no working_set evidence link
# ---------------------------------------------------------------------------


def test_replay_working_set_unlinked(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS Unlinked", client_request_id="req-ws-replay-unlinked-001"
    )
    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-unlinked-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    product_id = gen.product.analysis_product_id

    # Remove the working_set evidence link so the chain cannot be resolved.
    db.query(L3AnalysisProductEvidenceLink).filter(
        L3AnalysisProductEvidenceLink.analysis_product_id == product_id
    ).delete()
    db.commit()
    db.expire_all()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product_id,
    )

    assert result.reproduced is False
    assert result.classification == "working_set_unlinked"
    # Cannot recompute without the working set link.
    assert result.input_basis_match is None
    assert result.input_basis_hash_current is None
    assert result.result_match is None


# ---------------------------------------------------------------------------
# provenance_incomplete: deterministic product missing method_id in provenance
# ---------------------------------------------------------------------------


def test_replay_provenance_incomplete(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS ProvInc", client_request_id="req-ws-replay-provinc-001"
    )
    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-provinc-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product = gen.product
    tampered = dict(product.authoring_provenance_json)
    tampered.pop("method_id", None)
    product.authoring_provenance_json = tampered
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        verify_analysis_product_replay(
            db,
            session_id="session-gen-test",
            analysis_product_id=product.analysis_product_id,
        )

    assert exc_info.value.error_code == "provenance_incomplete"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Honesty lock: a state-consuming product whose provenance is missing the
# recorded input_state_hash must NOT be reported as reproduced — the verifier
# cannot confirm the member-state basis, so it fails closed as input_state_drift.
# ---------------------------------------------------------------------------


def test_replay_state_consuming_missing_recorded_state_hash_not_reproduced(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS MissStateHash", client_request_id="req-ws-replay-msh-001"
    )
    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-msh-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",  # state-consuming
    )
    db.commit()

    product = gen.product
    # Sanity: generation recorded an input_state_hash for a state-consuming method.
    assert "input_state_hash" in product.authoring_provenance_json
    tampered = dict(product.authoring_provenance_json)
    tampered.pop("input_state_hash", None)
    product.authoring_provenance_json = tampered
    db.commit()

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product.analysis_product_id,
    )

    assert result.reproduced is False
    assert result.input_state_match is False
    assert result.classification == "input_state_drift"
    assert result.input_state_hash_recorded is None
    assert result.input_state_hash_current is not None


# ---------------------------------------------------------------------------
# recompute_error: an unexpected failure during recompute is surfaced, not raised
# ---------------------------------------------------------------------------


def test_replay_recompute_error(seeded_db, monkeypatch) -> None:
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS Recompute", client_request_id="req-ws-replay-rce-001"
    )
    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-replay-rce-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    product_id = gen.product.analysis_product_id

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated method failure")

    # Patch run_method as imported into the replay service module namespace.
    monkeypatch.setattr(
        "app.services.layer3_analysis_product_replay.run_method", _boom
    )

    result = verify_analysis_product_replay(
        db,
        session_id="session-gen-test",
        analysis_product_id=product_id,
    )

    assert result.reproduced is False
    assert result.classification == "recompute_error"
    assert result.result_match is None
