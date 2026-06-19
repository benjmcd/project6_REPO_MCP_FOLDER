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
    # product_kind must be "metric" (composition emits quantitative counts)
    assert product.product_kind == "metric"
    # lifecycle must be "draft"
    assert product.lifecycle_status == "draft"
    # replayed is False on first call
    assert result.replayed is False
    # method fields
    assert result.method_id == "working_set_composition_summary"
    assert result.method_version == 2
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


def test_generate_idempotent_replay_survives_spec_change(seeded_db, monkeypatch) -> None:
    """A duplicate generate with the same client_request_id replays the existing
    deterministic product even if the method spec (product_kind / version) changed
    between calls — e.g. a taxonomy/version bump across a deploy — instead of
    raising idempotency_conflict.  The (method, working_set) inputs match, so it
    is the same logical generation request."""
    import dataclasses

    from app.services import layer3_deterministic_methods as dm

    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS SpecChange", client_request_id="req-ws-specchg"
    )
    first = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-gen-specchg",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    assert first.replayed is False
    original_id = first.product.analysis_product_id
    original_kind = first.product.product_kind

    # Simulate a later deploy that changes the composition spec (kind + version).
    orig_spec = dm.DETERMINISTIC_METHODS["working_set_composition_summary"]
    changed_spec = dataclasses.replace(
        orig_spec, product_kind="summary", version=orig_spec.version + 1
    )
    monkeypatch.setitem(dm.DETERMINISTIC_METHODS, "working_set_composition_summary", changed_spec)

    # Retry the SAME client_request_id -> must replay the existing product (no 409).
    second = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-gen-specchg",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    assert second.replayed is True
    assert second.product.analysis_product_id == original_id
    # The replayed product keeps its ORIGINAL kind — proves replay, not a rebuild.
    assert second.product.product_kind == original_kind
    # Still exactly one composition product row.
    count = (
        db.query(L3AnalysisProduct)
        .filter(L3AnalysisProduct.executor_identity == "working_set_composition_summary")
        .count()
    )
    assert count == 1


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


# ===========================================================================
# New methods: working_set_member_state_profile
# ===========================================================================


def test_generate_member_state_profile_happy_path(seeded_db) -> None:
    """Happy path: product_kind=summary, executor_identity, evidence link, lifecycle draft."""
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS Profile", client_request_id="req-ws-profile-001"
    )
    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-profile-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_member_state_profile",
    )
    db.commit()

    product = result.product
    assert product.executor_type == "deterministic"
    assert product.product_kind == "summary"
    assert product.lifecycle_status == "draft"
    assert result.replayed is False
    assert result.method_id == "working_set_member_state_profile"
    assert result.method_version == 1
    # Evidence link
    assert len(result.evidence_links) == 1
    link = result.evidence_links[0]
    assert link.ref_kind == "working_set"
    assert link.ref_id == ws.working_set_id
    assert link.evidence_role == "context"
    # Reserved columns
    assert product.output_schema_validation_status == "validated"
    assert product.executor_identity == "working_set_member_state_profile"
    # Provenance: state-consuming sentinel + input_state_hash present
    prov = product.authoring_provenance_json
    assert prov["method_id"] == "working_set_member_state_profile"
    assert prov["validation"] == "function_purity_recomputed_match"
    assert "input_state_hash" in prov
    assert "input_basis_hash" in prov
    assert "param_hash" in prov
    assert "result_summary" in prov


def test_generate_member_state_profile_input_state_hash_absent_for_composition_summary(seeded_db) -> None:
    """Composition summary (state-free) must NOT have input_state_hash in provenance (R2)."""
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS NoHash", client_request_id="req-ws-nohash-001"
    )
    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-nohash-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    prov = result.product.authoring_provenance_json
    assert "input_state_hash" not in prov
    assert prov["validation"] == "deterministic_recomputed_match"


def test_generate_member_state_profile_idempotent_replay(seeded_db) -> None:
    """Same client_request_id for member_state_profile -> replayed, single product row."""
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS Profile Idem", client_request_id="req-ws-profile-002"
    )
    r1 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-profile-idem",
        working_set_id=ws.working_set_id,
        method_id="working_set_member_state_profile",
    )
    db.commit()
    r2 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-profile-idem",
        working_set_id=ws.working_set_id,
        method_id="working_set_member_state_profile",
    )
    db.commit()
    assert r2.replayed is True
    assert r2.product.analysis_product_id == r1.product.analysis_product_id
    # Count only state-profile products to avoid cross-test interference
    count = (
        db.query(L3AnalysisProduct)
        .filter(L3AnalysisProduct.executor_identity == "working_set_member_state_profile")
        .count()
    )
    assert count == 1


# ===========================================================================
# New methods: working_set_staleness_diagnostic
# ===========================================================================


def test_generate_staleness_diagnostic_happy_path(seeded_db) -> None:
    """Happy path: product_kind=diagnostic, executor_identity, evidence link, lifecycle draft."""
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS Diagnostic", client_request_id="req-ws-diag-001"
    )
    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-diag-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()

    product = result.product
    assert product.executor_type == "deterministic"
    assert product.product_kind == "diagnostic"
    assert product.lifecycle_status == "draft"
    assert result.replayed is False
    assert result.method_id == "working_set_staleness_diagnostic"
    assert result.method_version == 1
    # Evidence link
    assert len(result.evidence_links) == 1
    link = result.evidence_links[0]
    assert link.ref_kind == "working_set"
    assert link.ref_id == ws.working_set_id
    # Reserved columns
    assert product.output_schema_validation_status == "validated"
    assert product.executor_identity == "working_set_staleness_diagnostic"
    # Provenance: state-consuming sentinel + input_state_hash present
    prov = product.authoring_provenance_json
    assert prov["method_id"] == "working_set_staleness_diagnostic"
    assert prov["validation"] == "function_purity_recomputed_match"
    assert "input_state_hash" in prov


def test_generate_staleness_diagnostic_idempotent_replay(seeded_db) -> None:
    db = seeded_db
    ws = _make_working_set(
        db, session_id="session-gen-test", name="WS Diag Idem", client_request_id="req-ws-diag-002"
    )
    r1 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-diag-idem",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()
    r2 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-diag-idem",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()
    assert r2.replayed is True
    assert r2.product.analysis_product_id == r1.product.analysis_product_id


# ===========================================================================
# R2 mutation test: different state -> different input_state_hash, same basis_hash
# ===========================================================================


def test_r2_mutation_different_state_different_input_state_hash(seeded_db) -> None:
    """Generate, mutate a member's state, generate again with new client_request_id.

    Proves: different input_state_hash, same input_basis_hash (lineage honesty).
    """
    db = seeded_db

    # Create a prior_product member in session-gen-test so it's reachable
    prior_product_row = L3AnalysisProduct(
        analysis_product_id="pp-mutation-test",
        session_id="session-gen-test",
        product_kind="summary",
        executor_type="human",
        lifecycle_status="draft",
        title="Mutation test product",
        body="Body text here.",
        is_non_evidentiary=False,
        basis_hash="basis-pp-mutation",
        spec_hash="spec-pp-mutation",
        client_request_id="req-pp-mutation-seed",
        authoring_provenance_json={},
        summary_json={},
    )
    db.add(prior_product_row)
    db.commit()

    # Working set includes the prior_product member
    from app.services.layer3_working_set import WorkingSetDraft, WorkingSetMemberDraft, create_working_set

    draft = WorkingSetDraft(
        name="WS Mutation",
        members=(
            WorkingSetMemberDraft(ref_kind="prior_product", ref_id="pp-mutation-test"),
        ),
    )
    ws_result = create_working_set(
        db,
        session_id="session-gen-test",
        client_request_id="req-ws-mutation-001",
        draft=draft,
    )
    db.commit()
    ws = ws_result.working_set

    # --- First generation (draft state) ---
    gen1 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-mutation-gen-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()
    hash1 = gen1.product.authoring_provenance_json["input_state_hash"]
    basis_hash1 = gen1.product.authoring_provenance_json["input_basis_hash"]

    # --- Mutate the prior_product lifecycle_status to "superseded" ---
    prior_product_row.lifecycle_status = "superseded"
    db.commit()

    # --- Second generation with a NEW client_request_id ---
    gen2 = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-mutation-gen-002",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()
    hash2 = gen2.product.authoring_provenance_json["input_state_hash"]
    basis_hash2 = gen2.product.authoring_provenance_json["input_basis_hash"]

    # input_state_hash must differ (member state changed)
    assert hash1 != hash2, "input_state_hash must differ after state mutation"
    # input_basis_hash must be identical (same working set identity)
    assert basis_hash1 == basis_hash2, "input_basis_hash must be identical (same working set)"


# ===========================================================================
# R3 session-scoping test: ref_id exists only in another session -> resolved:false
# ===========================================================================


def test_r3_cross_session_member_resolved_false(seeded_db) -> None:
    """A member ref_id existing only in another session -> resolved:false, no 500.

    The staleness diagnostic must surface it as unresolved, not crash.
    """
    db = seeded_db

    # Create a second session
    other_session = L3Session(
        session_id="session-gen-other-r3",
        selection_manifest_id="manifest-gen-other-r3",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    db.add(other_session)
    db.commit()

    # Create a snapshot in the OTHER session only
    other_snap = L3MaterialSnapshot(
        material_snapshot_id="snapshot-other-session-r3",
        session_id="session-gen-other-r3",
        descriptor_id="descriptor-gen-test",  # descriptor exists
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://other-r3",
        payload_hash="hash-other-r3",
        source_identity_json={},
        source_provenance_json={},
        load_summary_json={},
    )
    db.add(other_snap)
    db.commit()

    # Build working set in session-gen-test referencing the OTHER session's snapshot.
    # We must bypass create_working_set's membership check since the snapshot is in a
    # different session. Insert the working set row directly.
    from app.models.models import L3WorkingSet
    from app.services.layer3_utils import stable_hash

    cross_ws_id = "ws-cross-session-r3"
    members = [{"ref_kind": "material_snapshot", "ref_id": "snapshot-other-session-r3"}]
    ws_row = L3WorkingSet(
        working_set_id=cross_ws_id,
        session_id="session-gen-test",
        name="Cross Session WS",
        member_refs_json=members,
        member_count=1,
        basis_hash=stable_hash({"members": members}),
        client_request_id="req-ws-cross-r3",
        provenance_json={},
        summary_json={"member_count": 1, "by_ref_kind": {"material_snapshot": 1}},
    )
    db.add(ws_row)
    db.commit()

    # Generate using staleness diagnostic — must NOT raise, must surface unresolved
    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-cross-r3-diag",
        working_set_id=cross_ws_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()

    prov = result.product.authoring_provenance_json
    result_summary = prov["result_summary"]
    # The cross-session member must appear as unresolved
    assert result_summary["unresolved_members"]["count"] == 1
    assert "snapshot-other-session-r3" in result_summary["unresolved_members"]["members"]
    # Product should still be created (no 500)
    assert result.product.lifecycle_status == "draft"


# ===========================================================================
# Method input authority: unsupported ref_kind -> 400 unsupported_member_kinds
# ===========================================================================


def test_generate_unsupported_member_kind_raises_400(seeded_db) -> None:
    """A working set containing ref_kind='custom_unknown_type' -> Layer3AnalysisProductError 400.

    Inserts the L3WorkingSet row directly (bypassing create_working_set membership
    validation) to carry an unsupported ref_kind, mirroring the test_r3_cross_session_member_resolved_false
    direct-insert pattern.
    """
    db = seeded_db

    from app.models.models import L3WorkingSet
    from app.services.layer3_utils import stable_hash

    bad_ws_id = "ws-bad-kind-test"
    members = [{"ref_kind": "custom_unknown_type", "ref_id": "ref-bad-kind-001"}]
    ws_row = L3WorkingSet(
        working_set_id=bad_ws_id,
        session_id="session-gen-test",
        name="Bad Kind WS",
        member_refs_json=members,
        member_count=1,
        basis_hash=stable_hash({"members": members}),
        client_request_id="req-ws-bad-kind-001",
        provenance_json={},
        summary_json={"member_count": 1, "by_ref_kind": {"custom_unknown_type": 1}},
    )
    db.add(ws_row)
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        generate_analysis_product(
            db,
            session_id="session-gen-test",
            client_request_id="req-bad-kind-gen-001",
            working_set_id=bad_ws_id,
            method_id="working_set_composition_summary",
        )

    err = exc_info.value
    assert err.error_code == "unsupported_member_kinds"
    assert err.http_status == 400
    assert "custom_unknown_type" in str(err)


# ===========================================================================
# Lane 8 — confidence_level + limitations in authoring_provenance_json
# ===========================================================================


def test_generate_composition_summary_provenance_has_confidence_high(seeded_db) -> None:
    """composition_summary (state-free) -> provenance has confidence_level=='high' and limitations==[]."""
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-gen-test",
        name="WS Conf High",
        client_request_id="req-ws-conf-high-001",
    )
    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-conf-high-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    prov = result.product.authoring_provenance_json
    assert prov["confidence_level"] == "high"
    assert prov["limitations"] == []
    # Quality signals live in provenance ONLY, never in result_summary — otherwise
    # they would change the replay-verify result hash. Guard against that leak.
    assert "confidence_level" not in prov["result_summary"]
    assert "limitations" not in prov["result_summary"]


def test_generate_staleness_diagnostic_clean_provenance_confidence_high(seeded_db) -> None:
    """staleness_diagnostic over a clean working set -> provenance confidence_level=='high', limitations==[]."""
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-gen-test",
        name="WS Clean Conf",
        client_request_id="req-ws-clean-conf-001",
    )
    # The seeded_db has a material_snapshot member only — no superseded/failed/unresolved,
    # so staleness_diagnostic result is clean.
    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-clean-conf-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()
    prov = result.product.authoring_provenance_json
    assert prov["confidence_level"] == "high"
    assert prov["limitations"] == []


def test_generate_staleness_diagnostic_superseded_provenance_confidence_low(seeded_db) -> None:
    """staleness_diagnostic over a working set with a superseded prior_product member
    -> provenance confidence_level=='low' and limitations contains the superseded entry.

    Setup mirrors test_r2_mutation_different_state_different_input_state_hash: create a
    prior_product, supersede it directly, then build a working set containing it.
    """
    db = seeded_db

    # Create a prior_product member already in 'superseded' state.
    prior_product_row = L3AnalysisProduct(
        analysis_product_id="pp-conf-low-test",
        session_id="session-gen-test",
        product_kind="summary",
        executor_type="human",
        lifecycle_status="superseded",
        title="Low confidence test product",
        body="Body here.",
        is_non_evidentiary=False,
        basis_hash="basis-conf-low",
        spec_hash="spec-conf-low",
        client_request_id="req-pp-conf-low-seed",
        authoring_provenance_json={},
        summary_json={},
    )
    db.add(prior_product_row)
    db.commit()

    from app.services.layer3_working_set import WorkingSetDraft, WorkingSetMemberDraft, create_working_set

    draft = WorkingSetDraft(
        name="WS Superseded Conf",
        members=(
            WorkingSetMemberDraft(ref_kind="prior_product", ref_id="pp-conf-low-test"),
        ),
    )
    ws_result = create_working_set(
        db,
        session_id="session-gen-test",
        client_request_id="req-ws-conf-low-001",
        draft=draft,
    )
    db.commit()
    ws = ws_result.working_set

    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-conf-low-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()

    prov = result.product.authoring_provenance_json
    assert prov["confidence_level"] == "low", (
        f"Expected confidence_level='low' for superseded member; got {prov['confidence_level']!r}"
    )
    lims = prov["limitations"]
    assert any("superseded" in lim for lim in lims), (
        f"Expected a 'superseded prior product(s)' limitation; got {lims!r}"
    )
    # Limitations must contain counts only — no ref_ids
    for lim in lims:
        assert "pp-conf-low-test" not in lim, (
            f"ref_id leaked into limitation string: {lim!r}"
        )


def test_generate_member_state_profile_unresolved_provenance_confidence_medium(seeded_db) -> None:
    """member_state_profile over a working set referencing a cross-session (unresolvable) member
    -> provenance confidence_level=='medium' and limitations contains the unresolved count.

    Uses the cross-session pattern from test_r3_cross_session_member_resolved_false.
    """
    db = seeded_db

    other_session = L3Session(
        session_id="session-gen-other-conf",
        selection_manifest_id="manifest-gen-other-conf",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    db.add(other_session)
    db.commit()

    other_snap = L3MaterialSnapshot(
        material_snapshot_id="snapshot-other-conf",
        session_id="session-gen-other-conf",
        descriptor_id="descriptor-gen-test",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://other-conf",
        payload_hash="hash-other-conf",
        source_identity_json={},
        source_provenance_json={},
        load_summary_json={},
    )
    db.add(other_snap)
    db.commit()

    from app.models.models import L3WorkingSet
    from app.services.layer3_utils import stable_hash

    cross_ws_id = "ws-cross-conf-medium"
    members = [{"ref_kind": "material_snapshot", "ref_id": "snapshot-other-conf"}]
    ws_row = L3WorkingSet(
        working_set_id=cross_ws_id,
        session_id="session-gen-test",
        name="Cross Session Conf WS",
        member_refs_json=members,
        member_count=1,
        basis_hash=stable_hash({"members": members}),
        client_request_id="req-ws-cross-conf",
        provenance_json={},
        summary_json={"member_count": 1, "by_ref_kind": {"material_snapshot": 1}},
    )
    db.add(ws_row)
    db.commit()

    result = generate_analysis_product(
        db,
        session_id="session-gen-test",
        client_request_id="req-conf-medium-001",
        working_set_id=cross_ws_id,
        method_id="working_set_member_state_profile",
    )
    db.commit()

    prov = result.product.authoring_provenance_json
    assert prov["confidence_level"] == "medium", (
        f"Expected confidence_level='medium' for unresolvable member; got {prov['confidence_level']!r}"
    )
    lims = prov["limitations"]
    assert any("unresolved" in lim for lim in lims), (
        f"Expected an 'unresolved member(s)' limitation; got {lims!r}"
    )
    # Limitations must be bounded — no raw ref_ids
    for lim in lims:
        assert "snapshot-other-conf" not in lim, (
            f"ref_id leaked into limitation string: {lim!r}"
        )
