"""Tests for layer3_working_set service.

Uses an in-memory SQLite database matching the StaticPool pattern from
test_layer3_analysis_product_authoring.py.
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
    L3AnalysisSet,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
    L3WorkingSet,
)
from app.services.layer3_working_set import (
    Layer3WorkingSetError,
    Layer3WorkingSetResult,
    WorkingSetDraft,
    WorkingSetMemberDraft,
    create_working_set,
)
from app.services.layer3_sublayer_state import (
    serialize_working_set,
    session_working_sets,
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
    from datetime import datetime, timezone
    from app.models.models import (
        L3AnalysisGroup,
        L3AnalysisPlan,
        L3AnalysisUnit,
    )

    analysis_plan_id = "plan-ws-test"
    analysis_set_id = "set-ws-test"

    session_row = L3Session(
        session_id="session-ws-test",
        selection_manifest_id="manifest-ws-test",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id="snapshot-ws-test",
        session_id="session-ws-test",
        descriptor_id="descriptor-ws-test",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://ws-test",
        payload_hash="hash-ws-test",
        source_identity_json={"dataset_version_id": "dv-ws-test"},
        source_provenance_json={},
        load_summary_json={},
    )
    analysis_unit = L3AnalysisUnit(
        analysis_unit_id="unit-ws-test",
        session_id="session-ws-test",
        unit_kind="material_snapshot",
        analysis_modality="quantitative",
        member_snapshot_ids_json=["snapshot-ws-test"],
        member_ranges_json=[],
        must_remain_intact=True,
        typing_record_ids_json=[],
        unit_hash="unit-hash-ws-test",
        summary_json={},
    )
    analysis_group = L3AnalysisGroup(
        analysis_group_id="group-ws-test",
        session_id="session-ws-test",
        analysis_modality="quantitative",
        typing_basis_json={},
        analysis_unit_ids_json=["unit-ws-test"],
        status="formed",
    )
    analysis_set = L3AnalysisSet(
        analysis_set_id=analysis_set_id,
        session_id="session-ws-test",
        analysis_group_ids_json=["group-ws-test"],
        analysis_unit_ids_json=["unit-ws-test"],
        set_type="associated_cohort",
        formation_basis_json={},
    )
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=analysis_plan_id,
        session_id="session-ws-test",
        analysis_set_ids_json=[analysis_set_id],
        status="approved",
        approved_by_operator=True,
        approved_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    pass_run = L3PassRun(
        pass_run_id="pass-run-ws-test",
        session_id="session-ws-test",
        analysis_plan_id=analysis_plan_id,
        analysis_set_id=analysis_set_id,
        pass_type="associated_cohort",
        engine_family="wrapped_quantitative_analysis",
        status="completed",
        input_payload_ref="payload://input-ws",
        output_payload_ref="payload://output-ws",
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
# Happy path: create working set with 2 members
# ---------------------------------------------------------------------------


def test_happy_create_two_members(seeded_db) -> None:
    db = seeded_db
    draft = WorkingSetDraft(
        name="My Working Set",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
            WorkingSetMemberDraft(ref_kind="pass_run", ref_id="pass-run-ws-test"),
        ),
    )
    result = create_working_set(
        db,
        session_id="session-ws-test",
        client_request_id="req-ws-001",
        draft=draft,
    )
    db.commit()

    assert result.replayed is False
    ws = result.working_set
    assert ws.name == "My Working Set"
    assert ws.member_count == 2
    assert ws.basis_hash
    assert ws.working_set_id
    assert ws.session_id == "session-ws-test"
    # normalized members sorted by (ref_kind, ref_id)
    assert len(ws.member_refs_json) == 2
    ref_kinds = {m["ref_kind"] for m in ws.member_refs_json}
    assert ref_kinds == {"material_snapshot", "pass_run"}

    count = db.query(L3WorkingSet).count()
    assert count == 1


# ---------------------------------------------------------------------------
# Member validation failures
# ---------------------------------------------------------------------------


def test_create_working_set_with_prior_product_member(seeded_db) -> None:
    # Happy-path coverage for the prior_product member ref_kind (cite a product as scope).
    from app.services.layer3_analysis_product_authoring import (
        AnalysisProductDraft,
        AnalysisProductEvidenceDraft,
        create_analysis_product_draft,
    )

    db = seeded_db
    prior = create_analysis_product_draft(
        db,
        session_id="session-ws-test",
        client_request_id="ws-prior-prod",
        draft=AnalysisProductDraft(
            product_kind="finding",
            title="Prior finding",
            body="Body for the prior product.",
            evidence=(
                AnalysisProductEvidenceDraft(
                    ref_kind="material_snapshot",
                    ref_id="snapshot-ws-test",
                    evidence_role="observation",
                ),
            ),
        ),
    ).product
    db.commit()

    result = create_working_set(
        db,
        session_id="session-ws-test",
        client_request_id="ws-with-prior",
        draft=WorkingSetDraft(
            name="Scope citing prior product",
            members=(
                WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
                WorkingSetMemberDraft(ref_kind="prior_product", ref_id=prior.analysis_product_id),
            ),
        ),
    )

    assert result.replayed is False
    assert result.working_set.member_count == 2
    kinds = {member["ref_kind"] for member in result.working_set.member_refs_json}
    assert kinds == {"material_snapshot", "prior_product"}


def test_invalid_member_ref_kind_rejected(seeded_db) -> None:
    draft = WorkingSetDraft(
        name="Bad ref kind",
        members=(
            WorkingSetMemberDraft(ref_kind="unknown_table", ref_id="snapshot-ws-test"),
        ),
    )
    with pytest.raises(Layer3WorkingSetError) as exc_info:
        create_working_set(
            seeded_db,
            session_id="session-ws-test",
            client_request_id="req-bad-kind",
            draft=draft,
        )
    assert exc_info.value.error_code == "invalid_member_ref_kind"


def test_cross_session_member_rejected(seeded_db) -> None:
    """ref_id that does not exist in the session -> member_ref_not_found_in_session."""
    draft = WorkingSetDraft(
        name="Cross session member",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-other-session"),
        ),
    )
    with pytest.raises(Layer3WorkingSetError) as exc_info:
        create_working_set(
            seeded_db,
            session_id="session-ws-test",
            client_request_id="req-cross-session",
            draft=draft,
        )
    assert exc_info.value.error_code == "member_ref_not_found_in_session"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Session validation failures
# ---------------------------------------------------------------------------


def test_session_missing_returns_404(seeded_db) -> None:
    draft = WorkingSetDraft(
        name="WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
        ),
    )
    with pytest.raises(Layer3WorkingSetError) as exc_info:
        create_working_set(
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
    bad_session = L3Session(
        session_id=f"session-bad-{bad_status}",
        selection_manifest_id=f"manifest-bad-{bad_status}",
        status=bad_status,
        operator_context_json={},
        summary_json={},
    )
    db.add(bad_session)
    db.commit()

    draft = WorkingSetDraft(
        name="WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
        ),
    )
    with pytest.raises(Layer3WorkingSetError) as exc_info:
        create_working_set(
            db,
            session_id=f"session-bad-{bad_status}",
            client_request_id=f"req-bad-session-{bad_status}",
            draft=draft,
        )
    assert exc_info.value.error_code == "session_state_not_eligible"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Basis-hash stability: member reorder + dedup -> same basis
# ---------------------------------------------------------------------------


def test_basis_hash_stable_under_reorder_and_dedup(seeded_db) -> None:
    db = seeded_db
    # Draft A: snapshot first, then pass_run
    draft_a = WorkingSetDraft(
        name="Stable hash test",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
            WorkingSetMemberDraft(ref_kind="pass_run", ref_id="pass-run-ws-test"),
        ),
    )
    result_a = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-hash-a", draft=draft_a
    )
    db.commit()

    # Draft B: reversed order + a duplicate member -> same normalized set
    draft_b = WorkingSetDraft(
        name="Stable hash test",
        members=(
            WorkingSetMemberDraft(ref_kind="pass_run", ref_id="pass-run-ws-test"),
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),  # dup
        ),
    )
    result_b = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-hash-a", draft=draft_b
    )
    # Same client_request_id + same basis -> replay
    assert result_b.replayed is True
    assert result_b.working_set.working_set_id == result_a.working_set.working_set_id
    assert result_b.working_set.basis_hash == result_a.working_set.basis_hash
    assert db.query(L3WorkingSet).count() == 1


# ---------------------------------------------------------------------------
# Idempotency replay + conflict
# ---------------------------------------------------------------------------


def test_idempotency_replay(seeded_db) -> None:
    db = seeded_db
    draft = WorkingSetDraft(
        name="Idempotency WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
        ),
    )
    result1 = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-idem-ws-001", draft=draft
    )
    db.commit()

    result2 = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-idem-ws-001", draft=draft
    )
    assert result2.replayed is True
    assert result2.working_set.working_set_id == result1.working_set.working_set_id
    assert db.query(L3WorkingSet).count() == 1


def test_idempotency_conflict_different_members(seeded_db) -> None:
    db = seeded_db
    draft1 = WorkingSetDraft(
        name="Conflict WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
        ),
    )
    create_working_set(
        db, session_id="session-ws-test", client_request_id="req-conflict-ws-001", draft=draft1
    )
    db.commit()

    # Different members -> different basis_hash -> conflict
    draft2 = WorkingSetDraft(
        name="Conflict WS",
        members=(
            WorkingSetMemberDraft(ref_kind="pass_run", ref_id="pass-run-ws-test"),
        ),
    )
    with pytest.raises(Layer3WorkingSetError) as exc_info:
        create_working_set(
            db, session_id="session-ws-test", client_request_id="req-conflict-ws-001", draft=draft2
        )
    assert exc_info.value.error_code == "idempotency_conflict"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Immutability: new client_request_id -> new working_set, original unchanged
# ---------------------------------------------------------------------------


def test_immutability_new_request_id_creates_new_working_set(seeded_db) -> None:
    db = seeded_db
    draft1 = WorkingSetDraft(
        name="Original WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
        ),
    )
    result1 = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-immut-001", draft=draft1
    )
    db.commit()

    # Different members + different client_request_id -> new working set
    draft2 = WorkingSetDraft(
        name="New WS different members",
        members=(
            WorkingSetMemberDraft(ref_kind="pass_run", ref_id="pass-run-ws-test"),
        ),
    )
    result2 = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-immut-002", draft=draft2
    )
    db.commit()

    assert result2.replayed is False
    assert result2.working_set.working_set_id != result1.working_set.working_set_id
    assert result2.working_set.basis_hash != result1.working_set.basis_hash

    # Original is unchanged
    original = db.get(L3WorkingSet, result1.working_set.working_set_id)
    assert original is not None
    assert original.member_count == 1
    assert original.member_refs_json[0]["ref_kind"] == "material_snapshot"

    assert db.query(L3WorkingSet).count() == 2


# ---------------------------------------------------------------------------
# serialize_working_set / session_working_sets shape
# ---------------------------------------------------------------------------


def test_serialize_working_set_shape(seeded_db) -> None:
    db = seeded_db
    draft = WorkingSetDraft(
        name="Serialized WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
            WorkingSetMemberDraft(ref_kind="pass_run", ref_id="pass-run-ws-test"),
        ),
    )
    result = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-serial-001", draft=draft
    )
    db.commit()

    serialized = serialize_working_set(result.working_set)

    assert "working_set_id" in serialized
    assert serialized["name"] == "Serialized WS"
    assert serialized["basis_hash"]
    assert serialized["member_count"] == 2
    assert len(serialized["member_refs"]) == 2
    # Each member_ref has only ref_kind and ref_id
    for ref in serialized["member_refs"]:
        assert set(ref.keys()) == {"ref_kind", "ref_id"}
    assert serialized["created_at"] is not None
    # No raw payloads / summary_json / provenance_json exposed
    assert "summary_json" not in serialized
    assert "provenance_json" not in serialized
    assert "client_request_id" not in serialized


def test_session_working_sets_returns_list(seeded_db) -> None:
    db = seeded_db
    draft = WorkingSetDraft(
        name="Inventory WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
        ),
    )
    create_working_set(
        db, session_id="session-ws-test", client_request_id="req-inv-001", draft=draft
    )
    db.commit()

    result = session_working_sets(db, session_id="session-ws-test")
    assert len(result) == 1
    assert result[0]["name"] == "Inventory WS"
    assert result[0]["member_count"] == 1


# ---------------------------------------------------------------------------
# Linkage: product cites working_set as evidence
# ---------------------------------------------------------------------------


def test_product_can_cite_working_set_as_evidence(seeded_db) -> None:
    """Create a working set then create an analysis product with evidence ref_kind='working_set'."""
    db = seeded_db

    # Create a working set
    ws_draft = WorkingSetDraft(
        name="Linkage WS",
        members=(
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-ws-test"),
        ),
    )
    ws_result = create_working_set(
        db, session_id="session-ws-test", client_request_id="req-ws-link-001", draft=ws_draft
    )
    db.commit()

    ws_id = ws_result.working_set.working_set_id

    # Import authoring service
    from app.services.layer3_analysis_product_authoring import (
        AnalysisProductDraft,
        AnalysisProductEvidenceDraft,
        create_analysis_product_draft,
    )

    prod_draft = AnalysisProductDraft(
        product_kind="finding",
        title="Finding grounded on working set",
        body="This finding is grounded on a working set as context evidence.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="working_set",
                ref_id=ws_id,
                evidence_role="context",
            ),
        ),
    )
    prod_result = create_analysis_product_draft(
        db,
        session_id="session-ws-test",
        client_request_id="req-prod-link-001",
        draft=prod_draft,
    )
    db.commit()

    assert prod_result.replayed is False
    assert len(prod_result.evidence_links) == 1
    link = prod_result.evidence_links[0]
    assert link.ref_kind == "working_set"
    assert link.ref_id == ws_id
    assert link.evidence_role == "context"
