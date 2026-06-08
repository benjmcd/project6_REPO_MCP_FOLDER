"""Tests for layer3_analysis_product_generation service.

Uses an in-memory SQLite database mirroring the seeded_db fixture pattern from
test_layer3_working_set.py.  Creates working sets via create_working_set before
testing generation.
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
# Happy path
# ---------------------------------------------------------------------------


def test_generate_happy_path(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="My WS", client_request_id="req-ws-gen-001")

    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-gen-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    product = result.product
    # executor_type must be "deterministic"
    assert product.executor_type == "deterministic"
    # product_kind must be "summary"
    assert product.product_kind == "summary"
    # lifecycle must be "draft"
    assert product.lifecycle_status == "draft"
    # replayed is False on first call
    assert result.replayed is False
    # method fields
    assert result.method_id == "working_set_composition_summary"
    assert result.method_version == 1
    # exactly 1 evidence link, ref_kind="working_set"
    assert len(result.evidence_links) == 1
    link = result.evidence_links[0]
    assert link.ref_kind == "working_set"
    assert link.ref_id == ws.working_set_id
    assert link.evidence_role == "context"
    # reserved columns
    assert product.output_schema_validation_status == "validated"
    assert product.executor_identity == "working_set_composition_summary"
    # authoring_provenance has required keys
    prov = product.authoring_provenance_json
    assert prov["method_id"] == "working_set_composition_summary"
    assert "input_basis_hash" in prov
    assert prov["input_basis_hash"] == ws.basis_hash
    assert "param_hash" in prov
    assert "result_summary" in prov
    assert "validation" in prov


def test_generate_product_grounded_to_working_set(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS Grounded", client_request_id="req-ws-gen-002")

    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-gen-002",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    # Product is grounded (not non-evidentiary) and has the working_set evidence link
    assert result.product.is_non_evidentiary is False
    assert len(result.evidence_links) == 1
    assert result.evidence_links[0].ref_kind == "working_set"


# ---------------------------------------------------------------------------
# Idempotency: same client_request_id -> replayed, single product row
# ---------------------------------------------------------------------------


def test_generated_deterministic_product_promotes_through_lifecycle(seeded_db) -> None:
    # A machine-generated deterministic product is a normal draft: it promotes through
    # the executor-agnostic state machine, and the grounding gate at accept passes
    # because it carries a working_set evidence link.
    from app.services.layer3_analysis_product_promotion import (
        AnalysisProductTransitionRequest,
        transition_analysis_product,
    )

    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS", client_request_id="req-ws-promote")
    gen = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-gen-promote",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    pid = gen.product.analysis_product_id

    def _t(crid: str, intent: str, reason: str):
        r = transition_analysis_product(
            db,
            session_id="session-gen-test",
            analysis_product_id=pid,
            client_request_id=crid,
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()
        return r

    assert _t("d1", "promote", "proposed_ready").product.lifecycle_status == "proposed"
    assert _t("d2", "promote", "validation_passed").product.lifecycle_status == "validated"
    accepted = _t("d3", "accept", "grounded_accept")
    assert accepted.product.lifecycle_status == "accepted"
    assert accepted.decision.grounding_asserted is True


def test_generate_idempotency_same_request(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="Idem WS", client_request_id="req-ws-gen-003")

    result1 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-gen-idem",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    result2 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-gen-idem",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    assert result2.replayed is True
    assert result2.product.analysis_product_id == result1.product.analysis_product_id
    # Only one product row
    assert db.query(L3AnalysisProduct).count() == 1


# ---------------------------------------------------------------------------
# Error: unknown method_id -> 400
# ---------------------------------------------------------------------------


def test_generate_unknown_method_raises_400(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS Unknown Method", client_request_id="req-ws-gen-004")

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        generate_analysis_product(
            db,
            session_id="session-gen-test",
            client_request_id="req-gen-bad-method",
            working_set_id=ws.working_set_id,
            method_id="nonexistent_method",
        )
    assert exc_info.value.error_code == "unknown_method"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# Error: working_set_not_found -> 404
# ---------------------------------------------------------------------------


def test_generate_working_set_not_found_raises_404(seeded_db) -> None:
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        generate_analysis_product(
            seeded_db,
            session_id="session-gen-test",
            client_request_id="req-gen-nows",
            working_set_id="nonexistent-ws-id",
            method_id="working_set_composition_summary",
        )
    assert exc_info.value.error_code == "working_set_not_found"
    assert exc_info.value.http_status == 404


# ---------------------------------------------------------------------------
# Error: cross-session working set -> 409
# ---------------------------------------------------------------------------


def test_generate_cross_session_working_set_raises_409(seeded_db) -> None:
    db = seeded_db
    # Create a second session
    other_session = L3Session(
        session_id="session-gen-other",
        selection_manifest_id="manifest-gen-other",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    db.add(other_session)
    db.commit()

    # Create working set in first session
    ws = _make_working_set(db, session_id="session-gen-test", name="WS Cross Session", client_request_id="req-ws-gen-005")

    # Try to generate using the working set from the wrong session
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        generate_analysis_product(
            db,
            session_id="session-gen-other",
            client_request_id="req-gen-cross",
            working_set_id=ws.working_set_id,
            method_id="working_set_composition_summary",
        )
    assert exc_info.value.error_code == "working_set_not_in_session"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Authoring gate: executor_type="agent" still rejected
# ---------------------------------------------------------------------------


def test_authoring_still_rejects_agent_executor_type(seeded_db) -> None:
    """The relaxed gate allows 'deterministic' but still rejects 'agent'."""
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Agent attempt",
        body="This should be rejected.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-gen-test",
                evidence_role="observation",
            ),
        ),
        executor_type="agent",
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            seeded_db,
            session_id="session-gen-test",
            client_request_id="req-agent-rejected",
            draft=draft,
        )
    assert exc_info.value.error_code == "unsupported_executor_type"


def test_authoring_allows_deterministic_executor_type(seeded_db) -> None:
    """The relaxed gate now admits 'deterministic'."""
    db = seeded_db
    ws = _make_working_set(db, session_id="session-gen-test", name="WS Det Auth", client_request_id="req-ws-gen-006")

    draft = AnalysisProductDraft(
        product_kind="summary",
        title="Deterministic product",
        body="A deterministic product body for the test.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="working_set",
                ref_id=ws.working_set_id,
                evidence_role="context",
            ),
        ),
        executor_type="deterministic",
    )
    result = create_analysis_product_draft(
        db,
        session_id="session-gen-test",
        client_request_id="req-det-allowed",
        draft=draft,
    )
    db.commit()
    assert result.product.executor_type == "deterministic"
    assert result.replayed is False
