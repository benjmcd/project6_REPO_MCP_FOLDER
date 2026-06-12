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
    _stored_decision_basis_hash,
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
    # package_eligible is no longer a terminal state; non-supersede intents fail
    # at the transition-lookup step with transition_not_allowed, not product_terminal.
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
    assert exc_info.value.error_code == "transition_not_allowed"
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


# ---------------------------------------------------------------------------
# Supersession: happy paths
# ---------------------------------------------------------------------------


def _walk_to_accepted(db, pid: str, sid: str, prefix: str) -> None:
    """Drive a product from draft -> accepted."""
    for step, (intent, reason) in enumerate([
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
        ("accept", "grounded_accept"),
    ]):
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id=f"{prefix}-walk-{step}",
            request=AnalysisProductTransitionRequest(decision_intent=intent, decision_reason_code=reason),
        )
        db.commit()


def _walk_to_package_eligible(db, pid: str, sid: str, prefix: str) -> None:
    """Drive a product from draft -> package_eligible."""
    _walk_to_accepted(db, pid, sid, prefix)
    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id=f"{prefix}-walk-pe",
        request=AnalysisProductTransitionRequest(
            decision_intent="mark_package_eligible",
            decision_reason_code="package_ready",
        ),
    )
    db.commit()


def test_accepted_to_superseded_stale_basis(seeded_db) -> None:
    """accepted -> superseded with stale_basis reason (no successor provenance required)."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-stale-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-stale")

    result = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="sup-stale-final",
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="stale_basis",
            decision_notes="This analysis is based on outdated data.",
        ),
    )
    db.commit()
    assert result.replayed is False
    assert result.product.lifecycle_status == "superseded"
    assert result.decision.from_status == "accepted"
    assert result.decision.to_status == "superseded"
    assert result.decision.review_decision == "supersede"
    assert result.decision.decision_reason_code == "stale_basis"
    assert result.decision.decision_notes_present is True


def test_package_eligible_to_superseded_with_successor(seeded_db) -> None:
    """package_eligible -> superseded with superseded_by_successor, recording provenance."""
    db = seeded_db
    sid = "session-promo-test"

    # Product to be superseded
    product = _make_grounded_product(db, client_request_id="req-sup-pe-001")
    pid = product.analysis_product_id
    _walk_to_package_eligible(db, pid, sid, "sup-pe")

    # Successor product (just needs to exist in the session)
    successor = _make_grounded_product(db, client_request_id="req-sup-succ-001")
    succ_id = successor.analysis_product_id

    result = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="sup-pe-final",
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="superseded_by_successor",
            decision_notes="Replaced by a more complete analysis.",
            decision_provenance={"successor_analysis_product_id": succ_id},
        ),
    )
    db.commit()
    assert result.product.lifecycle_status == "superseded"
    assert result.decision.decision_reason_code == "superseded_by_successor"
    assert result.decision.decision_provenance_json.get("successor_analysis_product_id") == succ_id


def test_packaged_to_superseded(seeded_db) -> None:
    """packaged -> superseded via a direct-DB-constructed product row (no API path produces packaged)."""
    db = seeded_db
    sid = "session-promo-test"

    # Directly insert a product at lifecycle_status="packaged"
    from app.services.layer3_utils import stable_hash
    packaged_product = L3AnalysisProduct(
        analysis_product_id="ap-packaged-direct-001",
        session_id=sid,
        product_kind="finding",
        executor_type="human",
        lifecycle_status="packaged",
        title="Directly-packaged product",
        body="Created directly in DB for supersession test.",
        is_non_evidentiary=False,
        basis_hash=stable_hash({"seed": "packaged-direct"}),
        spec_hash=stable_hash({"spec": "packaged-direct"}),
        client_request_id="req-packaged-direct-001",
        authoring_provenance_json={},
        summary_json={},
    )
    db.add(packaged_product)
    db.commit()

    result = transition_analysis_product(
        db, session_id=sid, analysis_product_id="ap-packaged-direct-001",
        client_request_id="sup-packaged-final",
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="stale_basis",
            decision_notes="Packaged product is now superseded.",
        ),
    )
    db.commit()
    assert result.product.lifecycle_status == "superseded"
    assert result.decision.from_status == "packaged"
    assert result.decision.to_status == "superseded"


# ---------------------------------------------------------------------------
# Supersession: terminal state
# ---------------------------------------------------------------------------


def test_superseded_is_terminal(seeded_db) -> None:
    """Any further transition from superseded -> product_terminal."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-term-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-term")

    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="sup-term-supersede",
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="stale_basis",
            decision_notes="Now superseded.",
        ),
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-term-after",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="stale_basis",
                decision_notes="Trying to supersede again.",
            ),
        )
    assert exc_info.value.error_code == "product_terminal"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Supersession: validation failures
# ---------------------------------------------------------------------------


def test_supersede_notes_required(seeded_db) -> None:
    """supersede without notes -> decision_notes_required."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-nonotes-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-nonotes")

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-nonotes-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="stale_basis",
                decision_notes=None,
            ),
        )
    assert exc_info.value.error_code == "decision_notes_required"


def test_supersede_reason_mismatch(seeded_db) -> None:
    """supersede with a reason code belonging to another intent -> decision_reason_mismatch."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-mismatch-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-mismatch-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="proposed_ready",  # belongs to promote
                decision_notes="Notes here.",
            ),
        )
    assert exc_info.value.error_code == "decision_reason_mismatch"


def test_supersede_successor_required_when_reason_is_successor(seeded_db) -> None:
    """superseded_by_successor without providing successor_analysis_product_id -> supersede_successor_required."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-reqd-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-reqd")

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-reqd-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="superseded_by_successor",
                decision_notes="Should fail — no successor provided.",
                decision_provenance=None,
            ),
        )
    assert exc_info.value.error_code == "supersede_successor_required"
    assert exc_info.value.http_status == 409


def test_supersede_successor_not_found(seeded_db) -> None:
    """Referencing a non-existent successor -> supersede_successor_not_found (404-style)."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-nf-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-nf")

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-nf-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="superseded_by_successor",
                decision_notes="Successor does not exist.",
                decision_provenance={"successor_analysis_product_id": "nonexistent-succ-id"},
            ),
        )
    assert exc_info.value.error_code == "supersede_successor_not_found"
    assert exc_info.value.http_status == 404


def test_supersede_successor_self(seeded_db) -> None:
    """Referencing itself as successor -> supersede_successor_self."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-self-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-self")

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-self-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="superseded_by_successor",
                decision_notes="Self-reference attempt.",
                decision_provenance={"successor_analysis_product_id": pid},
            ),
        )
    assert exc_info.value.error_code == "supersede_successor_self"
    assert exc_info.value.http_status == 409


def test_supersede_successor_not_in_session(seeded_db) -> None:
    """Referencing a successor in a different session -> supersede_successor_not_in_session."""
    db = seeded_db
    sid = "session-promo-test"

    # Product to supersede
    product = _make_grounded_product(db, client_request_id="req-sup-nis-001")
    pid = product.analysis_product_id
    _walk_to_accepted(db, pid, sid, "sup-nis")

    # Successor in a different session — create the second session first
    from app.services.layer3_utils import stable_hash
    other_session = L3Session(
        session_id="session-other-sup-test",
        selection_manifest_id="manifest-other-sup-test",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    db.add(other_session)
    db.commit()

    other_product = L3AnalysisProduct(
        analysis_product_id="ap-other-session-succ-001",
        session_id="session-other-sup-test",
        product_kind="finding",
        executor_type="human",
        lifecycle_status="draft",
        title="Successor in other session",
        body="In a different session.",
        is_non_evidentiary=False,
        basis_hash=stable_hash({"seed": "other-session-succ"}),
        spec_hash=stable_hash({"spec": "other-session-succ"}),
        client_request_id="req-other-session-succ-001",
        authoring_provenance_json={},
        summary_json={},
    )
    db.add(other_product)
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-nis-attempt",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="superseded_by_successor",
                decision_notes="Successor is in another session.",
                decision_provenance={"successor_analysis_product_id": "ap-other-session-succ-001"},
            ),
        )
    assert exc_info.value.error_code == "supersede_successor_not_in_session"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Supersession: idempotency
# ---------------------------------------------------------------------------


def test_supersede_idempotent_replay(seeded_db) -> None:
    """Same client_request_id with same successor -> replayed=True."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-idem-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-idem")

    successor = _make_grounded_product(db, client_request_id="req-sup-idem-succ-001")
    succ_id = successor.analysis_product_id

    r1 = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="sup-idem-req",
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="superseded_by_successor",
            decision_notes="First supersession.",
            decision_provenance={"successor_analysis_product_id": succ_id},
        ),
    )
    db.commit()
    assert r1.replayed is False

    r2 = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="sup-idem-req",  # same request id
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="superseded_by_successor",
            decision_notes="First supersession.",
            decision_provenance={"successor_analysis_product_id": succ_id},
        ),
    )
    assert r2.replayed is True
    assert r2.decision.analysis_product_review_decision_id == r1.decision.analysis_product_review_decision_id


def test_supersede_idempotency_conflict_different_successor(seeded_db) -> None:
    """Same client_request_id but different successor -> idempotency_conflict (hash-folding proof)."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-conf-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-conf")

    successor1 = _make_grounded_product(db, client_request_id="req-sup-conf-succ1-001")
    succ1_id = successor1.analysis_product_id
    successor2 = _make_grounded_product(db, client_request_id="req-sup-conf-succ2-001")
    succ2_id = successor2.analysis_product_id

    transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="sup-conf-req",
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="superseded_by_successor",
            decision_notes="Original supersession.",
            decision_provenance={"successor_analysis_product_id": succ1_id},
        ),
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-conf-req",  # same request id
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="superseded_by_successor",
                decision_notes="Original supersession.",
                decision_provenance={"successor_analysis_product_id": succ2_id},  # different successor
            ),
        )
    assert exc_info.value.error_code == "idempotency_conflict"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Supersession: grounding NOT required
# ---------------------------------------------------------------------------


def test_supersede_does_not_require_grounding(seeded_db) -> None:
    """Grounding is not asserted for supersede transitions.

    An accepted product already has evidence (required to reach accepted), but
    we verify grounding_asserted is False on the supersede decision row.
    """
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-noground-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-noground")

    result = transition_analysis_product(
        db, session_id=sid, analysis_product_id=pid,
        client_request_id="sup-noground-final",
        request=AnalysisProductTransitionRequest(
            decision_intent="supersede",
            decision_reason_code="stale_basis",
            decision_notes="Superseding without grounding check.",
        ),
    )
    db.commit()
    assert result.decision.grounding_asserted is False


# ---------------------------------------------------------------------------
# FIX 3: _normalize_successor_id rejects non-str types
# ---------------------------------------------------------------------------


def test_supersede_successor_invalid_type_int(seeded_db) -> None:
    """supersede with an int successor id raises supersede_successor_invalid_type (409)."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="req-sup-invtype-001")
    pid = product.analysis_product_id
    sid = "session-promo-test"
    _walk_to_accepted(db, pid, sid, "sup-invtype")

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        transition_analysis_product(
            db, session_id=sid, analysis_product_id=pid,
            client_request_id="sup-invtype-req",
            request=AnalysisProductTransitionRequest(
                decision_intent="supersede",
                decision_reason_code="superseded_by_successor",
                decision_notes="Successor is an int, not a string.",
                decision_provenance={"successor_analysis_product_id": 5},
            ),
        )
    assert exc_info.value.error_code == "supersede_successor_invalid_type"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# FIX 5: _stored_decision_basis_hash folds successor into the hash
# ---------------------------------------------------------------------------


def test_stored_decision_basis_hash_differs_by_successor() -> None:
    """_stored_decision_basis_hash produces distinct values for distinct successors
    and equal values when successors match — no DB required."""
    from datetime import datetime, timezone

    def _make_row(successor_id: str) -> L3AnalysisProductReviewDecision:
        return L3AnalysisProductReviewDecision(
            analysis_product_review_decision_id=f"dec-hash-test-{successor_id}",
            analysis_product_id="prod-hash-test",
            session_id="session-hash-test",
            from_status="accepted",
            to_status="superseded",
            review_decision="supersede",
            decision_reason_code="superseded_by_successor",
            decision_status="recorded",
            decision_basis_hash="placeholder",
            decision_schema_id="layer3.analysis_product_promotion.v1",
            product_basis_hash="basis-hash-test",
            grounding_asserted=False,
            decision_notes_present=True,
            decision_notes_hash="notes-hash-test",
            client_request_id=f"crid-hash-test-{successor_id}",
            decision_provenance_json={"successor_analysis_product_id": successor_id},
            decision_summary_json={},
        )

    row_a = _make_row("succ-aaa")
    row_b = _make_row("succ-bbb")
    row_a2 = _make_row("succ-aaa")

    hash_a = _stored_decision_basis_hash(row_a)
    hash_b = _stored_decision_basis_hash(row_b)
    hash_a2 = _stored_decision_basis_hash(row_a2)

    assert hash_a != hash_b, "different successors must produce different basis hashes"
    assert hash_a == hash_a2, "identical successors must produce equal basis hashes"
