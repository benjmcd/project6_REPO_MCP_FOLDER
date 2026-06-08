"""Tests for layer3_analysis_product_promotion service.

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
    L3AnalysisProductReviewDecision,
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
from app.services.layer3_analysis_product_promotion import (
    AnalysisProductTransitionRequest,
    Layer3AnalysisProductPromotionResult,
    transition_analysis_product,
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
    analysis_plan_id = "plan-promo-test"
    analysis_set_id = "set-promo-test"

    session_row = L3Session(
        session_id="session-promo-test",
        selection_manifest_id="manifest-promo-test",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id="snapshot-promo-test",
        session_id="session-promo-test",
        descriptor_id="descriptor-promo-test",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://promo-test",
        payload_hash="hash-promo-test",
        source_identity_json={"dataset_version_id": "dv-promo-test"},
        source_provenance_json={},
        load_summary_json={},
    )
    from app.models.models import L3AnalysisPlan, L3AnalysisUnit, L3AnalysisGroup
    from datetime import datetime, timezone

    analysis_unit = L3AnalysisUnit(
        analysis_unit_id="unit-promo-test",
        session_id="session-promo-test",
        unit_kind="material_snapshot",
        analysis_modality="quantitative",
        member_snapshot_ids_json=["snapshot-promo-test"],
        member_ranges_json=[],
        must_remain_intact=True,
        typing_record_ids_json=[],
        unit_hash="unit-hash-promo-test",
        summary_json={},
    )
    analysis_group = L3AnalysisGroup(
        analysis_group_id="group-promo-test",
        session_id="session-promo-test",
        analysis_modality="quantitative",
        typing_basis_json={},
        analysis_unit_ids_json=["unit-promo-test"],
        status="formed",
    )
    analysis_set = L3AnalysisSet(
        analysis_set_id=analysis_set_id,
        session_id="session-promo-test",
        analysis_group_ids_json=["group-promo-test"],
        analysis_unit_ids_json=["unit-promo-test"],
        set_type="associated_cohort",
        formation_basis_json={},
    )
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=analysis_plan_id,
        session_id="session-promo-test",
        analysis_set_ids_json=[analysis_set_id],
        status="approved",
        approved_by_operator=True,
        approved_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    pass_run = L3PassRun(
        pass_run_id="pass-run-promo-test",
        session_id="session-promo-test",
        analysis_plan_id=analysis_plan_id,
        analysis_set_id=analysis_set_id,
        pass_type="associated_cohort",
        engine_family="wrapped_quantitative_analysis",
        status="completed",
        input_payload_ref="payload://input-promo",
        output_payload_ref="payload://output-promo",
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


def _make_grounded_product(db, *, client_request_id: str = "req-grounded-001") -> L3AnalysisProduct:
    """Author a grounded finding product and return the product row."""
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Grounded finding for promotion tests",
        body="This finding cites a material snapshot and is fully grounded.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-promo-test",
                evidence_role="observation",
            ),
        ),
    )
    result = create_analysis_product_draft(
        db,
        session_id="session-promo-test",
        client_request_id=client_request_id,
        draft=draft,
    )
    db.commit()
    return result.product


def _make_non_evidentiary_product(db, *, client_request_id: str = "req-note-001") -> L3AnalysisProduct:
    """Author a non-evidentiary analyst_note and return the product row."""
    draft = AnalysisProductDraft(
        product_kind="analyst_note",
        title="Non-evidentiary note for promotion tests",
        body="This is a background note with no evidence links.",
        evidence=(),
        is_non_evidentiary=True,
    )
    result = create_analysis_product_draft(
        db,
        session_id="session-promo-test",
        client_request_id=client_request_id,
        draft=draft,
    )
    db.commit()
    return result.product


# ---------------------------------------------------------------------------
# State machine: happy path walk draft->proposed->validated->accepted->package_eligible
# ---------------------------------------------------------------------------


def test_full_happy_path_walk(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db)
    pid = product.analysis_product_id
    sid = "session-promo-test"

    # draft -> proposed
    r1 = transition_analysis_product(
        db,
        session_id=sid,
        analysis_product_id=pid,
        client_request_id="walk-step-1",
        request=AnalysisProductTransitionRequest(
            decision_intent="promote",
            decision_reason_code="proposed_ready",
        ),
    )
    db.commit()
    assert r1.replayed is False
    assert r1.product.lifecycle_status == "proposed"
    assert r1.decision.from_status == "draft"
    assert r1.decision.to_status == "proposed"
    assert db.query(L3AnalysisProductReviewDecision).filter_by(analysis_product_id=pid).count() == 1

    # proposed -> validated
    r2 = transition_analysis_product(
        db,
        session_id=sid,
        analysis_product_id=pid,
        client_request_id="walk-step-2",
        request=AnalysisProductTransitionRequest(
            decision_intent="promote",
            decision_reason_code="validation_passed",
        ),
    )
    db.commit()
    assert r2.product.lifecycle_status == "validated"
    assert db.query(L3AnalysisProductReviewDecision).filter_by(analysis_product_id=pid).count() == 2

    # validated -> accepted
    r3 = transition_analysis_product(
        db,
        session_id=sid,
        analysis_product_id=pid,
        client_request_id="walk-step-3",
        request=AnalysisProductTransitionRequest(
            decision_intent="accept",
            decision_reason_code="grounded_accept",
        ),
    )
    db.commit()
    assert r3.product.lifecycle_status == "accepted"
    assert r3.decision.grounding_asserted is True
    assert db.query(L3AnalysisProductReviewDecision).filter_by(analysis_product_id=pid).count() == 3

    # accepted -> package_eligible
    r4 = transition_analysis_product(
        db,
        session_id=sid,
        analysis_product_id=pid,
        client_request_id="walk-step-4",
        request=AnalysisProductTransitionRequest(
            decision_intent="mark_package_eligible",
            decision_reason_code="package_ready",
        ),
    )
    db.commit()
    assert r4.product.lifecycle_status == "package_eligible"
    assert r4.decision.grounding_asserted is True
    assert db.query(L3AnalysisProductReviewDecision).filter_by(analysis_product_id=pid).count() == 4


# ---------------------------------------------------------------------------
# Forbidden transitions
# ---------------------------------------------------------------------------


def test_revise_then_repromote_loop_does_not_collide(seeded_db) -> None:
    # Regression: identical transitions legitimately recur on the revise->re-promote
    # loop (draft->proposed->draft->proposed). decision_basis_hash must NOT be globally
    # unique, or the second promote raises IntegrityError -> unhandled 500.
    db = seeded_db
    product = _make_grounded_product(db)
    pid = product.analysis_product_id
    sid = "session-promo-test"

    def _promote(crid: str):
        return transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid, client_request_id=crid,
            request=AnalysisProductTransitionRequest(
                decision_intent="promote", decision_reason_code="proposed_ready"
            ),
        )

    _promote("loop-1")
    db.commit()  # draft -> proposed
    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid, client_request_id="loop-revise",
        request=AnalysisProductTransitionRequest(
            decision_intent="revise", decision_reason_code="revision_requested",
            decision_notes="needs more support",
        ),
    )
    db.commit()  # proposed -> draft
    r3 = _promote("loop-2")
    db.commit()  # draft -> proposed AGAIN (byte-identical basis tuple to the first promote)

    assert r3.replayed is False
    assert r3.product.lifecycle_status == "proposed"
    assert (
        db.query(L3AnalysisProductReviewDecision)
        .filter_by(analysis_product_id=pid)
        .count()
        == 3
    )


def test_skip_transition_draft_to_validated_rejected(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-skip-001")
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db,
            session_id="session-promo-test",
            analysis_product_id=product.analysis_product_id,
            client_request_id="skip-draft-validated",
            request=AnalysisProductTransitionRequest(
                decision_intent="accept",
                decision_reason_code="grounded_accept",
            ),
        )
    assert exc_info.value.error_code == "transition_not_allowed"
    assert exc_info.value.http_status == 409


def test_accepted_to_draft_not_allowed(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-acc-draft-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    # Walk to accepted
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
        ("accept", "grounded_accept"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"acc-draft-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db,
            session_id=sid,
            analysis_product_id=pid,
            client_request_id="acc-to-draft-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="revise",
                decision_reason_code="revision_requested",
                decision_notes="Needs revision",
            ),
        )
    assert exc_info.value.error_code == "transition_not_allowed"


def test_terminal_package_eligible_blocks_further_transitions(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-terminal-pe-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
        ("accept", "grounded_accept"),
        ("mark_package_eligible", "package_ready"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"pe-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="pe-after-terminal",
            request=AnalysisProductTransitionRequest(
                decision_intent="promote",
                decision_reason_code="proposed_ready",
            ),
        )
    assert exc_info.value.error_code == "product_terminal"
    assert exc_info.value.http_status == 409


def test_terminal_rejected_blocks_further_transitions(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-terminal-rej-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    # draft -> proposed
    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="rej-walk-1",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="proposed_ready"),
    )
    db.commit()
    # proposed -> rejected
    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="rej-walk-2",
        request=AnalysisProductTransitionRequest(
            decision_intent="reject",
            decision_reason_code="operator_rejected",
            decision_notes="Operator rejected this product.",
        ),
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="rej-after-terminal",
            request=AnalysisProductTransitionRequest(
                decision_intent="promote",
                decision_reason_code="proposed_ready",
            ),
        )
    assert exc_info.value.error_code == "product_terminal"


def test_self_promote_wrong_state(seeded_db) -> None:
    """A second promote on 'validated' state should be transition_not_allowed."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-self-promo-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    # Walk to validated
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"self-promo-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()

    # validated -> promote is not in ALLOWED_TRANSITIONS
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="self-promo-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="promote",
                decision_reason_code="proposed_ready",
            ),
        )
    assert exc_info.value.error_code == "transition_not_allowed"


# ---------------------------------------------------------------------------
# Grounding gate at acceptance
# ---------------------------------------------------------------------------


def test_non_evidentiary_product_cannot_be_accepted(seeded_db) -> None:
    db = seeded_db
    product = _make_non_evidentiary_product(db, client_request_id="req-ne-accept-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    # draft -> proposed (allowed for non-evidentiary)
    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="ne-accept-walk-1",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="proposed_ready"),
    )
    db.commit()
    # proposed -> validated
    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="ne-accept-walk-2",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="validation_passed"),
    )
    db.commit()
    # validated -> accept: MUST fail because non-evidentiary
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="ne-accept-attempt",
            request=AnalysisProductTransitionRequest(decision_intent="accept", decision_reason_code="grounded_accept"),
        )
    assert exc_info.value.error_code == "non_evidentiary_not_acceptable"
    assert exc_info.value.http_status == 409


def test_grounded_finding_accepts_fine_with_grounding_asserted(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-grounded-accept-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"grounded-accept-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()

    result = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="grounded-accept-final",
        request=AnalysisProductTransitionRequest(decision_intent="accept", decision_reason_code="grounded_accept"),
    )
    db.commit()
    assert result.product.lifecycle_status == "accepted"
    assert result.decision.grounding_asserted is True


# ---------------------------------------------------------------------------
# Reject path
# ---------------------------------------------------------------------------


def test_validated_to_reject_with_notes(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-reject-notes-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"reject-notes-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()

    result = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="reject-with-notes",
        request=AnalysisProductTransitionRequest(
            decision_intent="reject",
            decision_reason_code="evidence_gap",
            decision_notes="The evidence does not support the conclusion.",
        ),
    )
    db.commit()
    assert result.product.lifecycle_status == "rejected"
    assert result.decision.decision_notes_present is True
    assert result.decision.decision_notes_hash is not None


def test_reject_without_notes_raises_decision_notes_required(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-reject-no-notes-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"reject-no-notes-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="reject-no-notes",
            request=AnalysisProductTransitionRequest(
                decision_intent="reject",
                decision_reason_code="evidence_gap",
                decision_notes=None,
            ),
        )
    assert exc_info.value.error_code == "decision_notes_required"


def test_reject_with_wrong_reason_code_raises_mismatch(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-reject-wrong-reason-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="rwr-walk-1",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="proposed_ready"),
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="reject-wrong-reason",
            request=AnalysisProductTransitionRequest(
                decision_intent="reject",
                decision_reason_code="proposed_ready",  # wrong: belongs to promote
                decision_notes="Notes provided.",
            ),
        )
    assert exc_info.value.error_code == "decision_reason_mismatch"


# ---------------------------------------------------------------------------
# Revise (back-transition)
# ---------------------------------------------------------------------------


def test_validated_to_revise_returns_to_draft(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-revise-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"revise-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()

    result = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="revise-back-to-draft",
        request=AnalysisProductTransitionRequest(
            decision_intent="revise",
            decision_reason_code="revision_requested",
            decision_notes="Please revise the body of this finding.",
        ),
    )
    db.commit()
    assert result.product.lifecycle_status == "draft"
    assert result.decision.from_status == "validated"
    assert result.decision.to_status == "draft"
    # Three transitions total: walk 2 + revise 1
    assert db.query(L3AnalysisProductReviewDecision).filter_by(analysis_product_id=pid).count() == 3


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotency_same_request_returns_replayed(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-idem-promote-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"

    r1 = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="idem-promote-req",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="proposed_ready"),
    )
    db.commit()
    assert r1.replayed is False

    r2 = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="idem-promote-req",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="proposed_ready"),
    )
    assert r2.replayed is True
    assert r2.decision.analysis_product_review_decision_id == r1.decision.analysis_product_review_decision_id
    # Still only one decision row
    assert db.query(L3AnalysisProductReviewDecision).filter_by(analysis_product_id=pid).count() == 1


def test_idempotency_conflict_different_transition(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-idem-conflict-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"

    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="conflict-req-id",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="proposed_ready"),
    )
    db.commit()

    # Same client_request_id but different reason code -> different basis hash
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="conflict-req-id",
            request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="validation_passed"),
        )
    assert exc_info.value.error_code == "idempotency_conflict"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Audit append: multiple decisions per product
# ---------------------------------------------------------------------------


def test_audit_append_three_decisions_ordered(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-audit-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"

    steps = [
        ("promote", "proposed_ready", None),
        ("promote", "validation_passed", None),
        ("revise", "revision_requested", "Needs more detail"),
    ]
    for i, (intent, reason, notes) in enumerate(steps):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"audit-step-{i}",
            request=AnalysisProductTransitionRequest(
                decision_intent=intent,
                decision_reason_code=reason,
                decision_notes=notes,
            ),
        )
        db.commit()

    decisions = (
        db.query(L3AnalysisProductReviewDecision)
        .filter_by(analysis_product_id=pid)
        .order_by(L3AnalysisProductReviewDecision.created_at.asc())
        .all()
    )
    assert len(decisions) == 3
    assert decisions[0].to_status == "proposed"
    assert decisions[1].to_status == "validated"
    assert decisions[2].to_status == "draft"

    # Product status reflects latest transition
    db.refresh(product)
    assert product.lifecycle_status == "draft"


# ---------------------------------------------------------------------------
# Input validation: invalid decision_intent / reason_code
# ---------------------------------------------------------------------------


def test_invalid_decision_intent_raises(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-bad-intent-001")
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db,
            session_id="session-promo-test",
            analysis_product_id=product.analysis_product_id,
            client_request_id="bad-intent-req",
            request=AnalysisProductTransitionRequest(
                decision_intent="fly_away",
                decision_reason_code="proposed_ready",
            ),
        )
    assert exc_info.value.error_code == "invalid_decision_intent"


def test_invalid_reason_code_raises(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-bad-reason-001")
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db,
            session_id="session-promo-test",
            analysis_product_id=product.analysis_product_id,
            client_request_id="bad-reason-req",
            request=AnalysisProductTransitionRequest(
                decision_intent="promote",
                decision_reason_code="not_a_real_reason",
            ),
        )
    assert exc_info.value.error_code == "invalid_decision_reason_code"


def test_product_not_found_raises_404(seeded_db) -> None:
    db = seeded_db
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db,
            session_id="session-promo-test",
            analysis_product_id="nonexistent-product-id",
            client_request_id="not-found-req",
            request=AnalysisProductTransitionRequest(
                decision_intent="promote",
                decision_reason_code="proposed_ready",
            ),
        )
    assert exc_info.value.error_code == "product_not_found"
    assert exc_info.value.http_status == 404


def test_product_not_in_session_raises_409(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-wrong-session-001")
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db,
            session_id="wrong-session-id",
            analysis_product_id=product.analysis_product_id,
            client_request_id="wrong-session-req",
            request=AnalysisProductTransitionRequest(
                decision_intent="promote",
                decision_reason_code="proposed_ready",
            ),
        )
    assert exc_info.value.error_code == "product_not_in_session"
    assert exc_info.value.http_status == 409
