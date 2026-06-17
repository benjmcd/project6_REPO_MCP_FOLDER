"""Tests for layer3_analysis_product_lineage service.

Uses an in-memory SQLite database mirroring the seeded_db fixture pattern from
test_layer3_analysis_product_replay.py.  Creates working sets and analysis
products via generate_analysis_product (deterministic) and
create_analysis_product_draft (human), then inspects lineage via
build_analysis_product_lineage.
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
    L3AnalysisProductReviewDecision,
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
from app.services.layer3_analysis_product_lineage import (
    _order_review_decisions,
    build_analysis_product_lineage,
)
from app.services.layer3_analysis_product_promotion import (
    AnalysisProductTransitionRequest,
    transition_analysis_product,
)
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
    """Seed an active_execution session with snapshot and pass_run."""
    analysis_plan_id = "plan-lin-test"
    analysis_set_id = "set-lin-test"

    session_row = L3Session(
        session_id="session-lin-test",
        selection_manifest_id="manifest-lin-test",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id="snapshot-lin-test",
        session_id="session-lin-test",
        descriptor_id="descriptor-lin-test",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://lin-test",
        payload_hash="hash-lin-test",
        source_identity_json={"dataset_version_id": "dv-lin-test"},
        source_provenance_json={},
        load_summary_json={},
    )
    analysis_unit = L3AnalysisUnit(
        analysis_unit_id="unit-lin-test",
        session_id="session-lin-test",
        unit_kind="material_snapshot",
        analysis_modality="quantitative",
        member_snapshot_ids_json=["snapshot-lin-test"],
        member_ranges_json=[],
        must_remain_intact=True,
        typing_record_ids_json=[],
        unit_hash="unit-hash-lin-test",
        summary_json={},
    )
    analysis_group = L3AnalysisGroup(
        analysis_group_id="group-lin-test",
        session_id="session-lin-test",
        analysis_modality="quantitative",
        typing_basis_json={},
        analysis_unit_ids_json=["unit-lin-test"],
        status="formed",
    )
    analysis_set = L3AnalysisSet(
        analysis_set_id=analysis_set_id,
        session_id="session-lin-test",
        analysis_group_ids_json=["group-lin-test"],
        analysis_unit_ids_json=["unit-lin-test"],
        set_type="associated_cohort",
        formation_basis_json={},
    )
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=analysis_plan_id,
        session_id="session-lin-test",
        analysis_set_ids_json=[analysis_set_id],
        status="approved",
        approved_by_operator=True,
        approved_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    pass_run = L3PassRun(
        pass_run_id="pass-run-lin-test",
        session_id="session-lin-test",
        analysis_plan_id=analysis_plan_id,
        analysis_set_id=analysis_set_id,
        pass_type="associated_cohort",
        engine_family="wrapped_quantitative_analysis",
        status="completed",
        input_payload_ref="payload://input-lin",
        output_payload_ref="payload://output-lin",
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
            WorkingSetMemberDraft(ref_kind="material_snapshot", ref_id="snapshot-lin-test"),
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
# Test 1: deterministic product lineage happy path
# ---------------------------------------------------------------------------


def test_lineage_deterministic_happy_path(seeded_db) -> None:
    """Deterministic product: all lineage fields populated correctly."""
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-lin-test",
        name="WS Lin HappyPath",
        client_request_id="req-ws-lin-hp-001",
    )
    gen = generate_analysis_product(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-hp-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    product_id = gen.product.analysis_product_id

    lineage = build_analysis_product_lineage(
        db,
        session_id="session-lin-test",
        analysis_product_id=product_id,
    )

    # Top-level keys
    assert lineage["schema_id"] == "layer3.analysis_product_lineage.v1"
    assert lineage["analysis_product_id"] == product_id

    # Product fields — bounded (no body, no title)
    prod = lineage["product"]
    assert prod["analysis_product_id"] == product_id
    assert prod["product_kind"] is not None
    assert prod["executor_type"] == "deterministic"
    assert prod["lifecycle_status"] == "draft"
    assert "is_non_evidentiary" in prod
    assert "basis_hash" in prod
    assert "spec_hash" in prod
    assert "created_at" in prod
    assert "body" not in prod
    assert "title" not in prod

    # Working set
    assert lineage["working_set_linked"] is True
    ws_out = lineage["working_set"]
    assert ws_out is not None
    assert ws_out["working_set_id"] == ws.working_set_id
    assert "basis_hash" in ws_out
    assert "member_count" in ws_out

    # Method provenance
    mp = lineage["method_provenance"]
    assert mp is not None
    assert mp["method_id"] == "working_set_composition_summary"
    assert mp["method_version"] is not None
    assert "input_basis_hash" in mp
    assert "param_hash" in mp
    # result_summary must NOT be present
    assert "result_summary" not in mp

    # Evidence refs include the working_set ref
    ev_refs = lineage["evidence_refs"]
    assert isinstance(ev_refs, list)
    assert any(r["ref_kind"] == "working_set" for r in ev_refs)
    assert lineage["evidence_refs_truncated"] is False

    # Review trail empty for a fresh draft
    assert lineage["review_trail"] == []

    # Package: fresh draft is not eligible
    pkg = lineage["package"]
    assert pkg["package_eligible_or_packaged"] is False
    assert pkg["lifecycle_status"] == "draft"
    assert isinstance(pkg["output_package_refs"], list)


# ---------------------------------------------------------------------------
# Test 2: review_trail order and completeness
# ---------------------------------------------------------------------------


def test_lineage_review_trail_order(seeded_db) -> None:
    """Promote through draft->proposed->validated->accepted; trail must be
    ordered created_at ASC and contain all decisions with correct statuses."""
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-lin-test",
        name="WS Lin Trail",
        client_request_id="req-ws-lin-trail-001",
    )
    gen = generate_analysis_product(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-trail-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    pid = gen.product.analysis_product_id
    sid = "session-lin-test"

    def _t(crid: str, intent: str, reason: str) -> None:
        transition_analysis_product(
            db,
            session_id=sid,
            analysis_product_id=pid,
            client_request_id=crid,
            request=AnalysisProductTransitionRequest(
                decision_intent=intent,
                decision_reason_code=reason,
            ),
        )
        db.commit()

    _t("lin-trail-step-1", "promote", "proposed_ready")    # draft -> proposed
    _t("lin-trail-step-2", "promote", "validation_passed")  # proposed -> validated
    _t("lin-trail-step-3", "accept", "grounded_accept")     # validated -> accepted

    lineage = build_analysis_product_lineage(
        db,
        session_id=sid,
        analysis_product_id=pid,
    )

    trail = lineage["review_trail"]
    assert len(trail) == 3

    # Ordered from_status progression
    assert trail[0]["from_status"] == "draft"
    assert trail[0]["to_status"] == "proposed"
    assert trail[1]["from_status"] == "proposed"
    assert trail[1]["to_status"] == "validated"
    assert trail[2]["from_status"] == "validated"
    assert trail[2]["to_status"] == "accepted"

    # Each entry has the required fields
    for entry in trail:
        assert "review_decision" in entry
        assert "decision_reason_code" in entry
        assert "from_status" in entry
        assert "to_status" in entry
        assert "created_at" in entry
        assert "operator_identity" in entry
        assert "successor_analysis_product_id" in entry

    # created_at values are in non-decreasing order
    timestamps = [e["created_at"] for e in trail if e["created_at"] is not None]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# Test 3: human product — method_provenance is None
# ---------------------------------------------------------------------------


def test_lineage_human_product_no_method_provenance(seeded_db) -> None:
    """Human-authored product must return method_provenance=None."""
    db = seeded_db
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Human finding for lineage test",
        body="Human-authored, no working set.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-lin-test",
                evidence_role="observation",
            ),
        ),
    )
    result = create_analysis_product_draft(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-human-001",
        draft=draft,
    )
    db.commit()
    product_id = result.product.analysis_product_id

    lineage = build_analysis_product_lineage(
        db,
        session_id="session-lin-test",
        analysis_product_id=product_id,
    )

    assert lineage["method_provenance"] is None
    assert lineage["product"]["executor_type"] == "human"


# ---------------------------------------------------------------------------
# Test 4: working_set_unlinked — evidence link deleted after generation
# ---------------------------------------------------------------------------


def test_lineage_working_set_unlinked(seeded_db) -> None:
    """Deleting the working_set evidence link yields working_set=None,
    working_set_linked=False; service still returns a normal dict (200-level)."""
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-lin-test",
        name="WS Lin Unlinked",
        client_request_id="req-ws-lin-unlinked-001",
    )
    gen = generate_analysis_product(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-unlinked-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    product_id = gen.product.analysis_product_id

    # Remove the working_set evidence link
    link = (
        db.query(L3AnalysisProductEvidenceLink)
        .filter(
            L3AnalysisProductEvidenceLink.analysis_product_id == product_id,
            L3AnalysisProductEvidenceLink.ref_kind == "working_set",
        )
        .one()
    )
    db.delete(link)
    db.commit()

    lineage = build_analysis_product_lineage(
        db,
        session_id="session-lin-test",
        analysis_product_id=product_id,
    )

    assert lineage["working_set"] is None
    assert lineage["working_set_linked"] is False
    assert lineage["analysis_product_id"] == product_id


# ---------------------------------------------------------------------------
# Test 5: product not found -> 404
# ---------------------------------------------------------------------------


def test_lineage_product_not_found(seeded_db) -> None:
    """Non-existent analysis_product_id raises error_code=analysis_product_not_found / 404."""
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        build_analysis_product_lineage(
            seeded_db,
            session_id="session-lin-test",
            analysis_product_id="nonexistent-product-id-lin",
        )

    assert exc_info.value.error_code == "analysis_product_not_found"
    assert exc_info.value.http_status == 404


# ---------------------------------------------------------------------------
# Test 6: cross-session -> 409
# ---------------------------------------------------------------------------


def test_lineage_cross_session(seeded_db) -> None:
    """Product in session A, queried with session B -> analysis_product_not_in_session / 409."""
    db = seeded_db

    other_session = L3Session(
        session_id="session-lin-other",
        selection_manifest_id="manifest-lin-other",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    db.add(other_session)
    db.commit()

    ws = _make_working_set(
        db,
        session_id="session-lin-test",
        name="WS Lin Cross",
        client_request_id="req-ws-lin-cross-001",
    )
    gen = generate_analysis_product(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-cross-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        build_analysis_product_lineage(
            db,
            session_id="session-lin-other",
            analysis_product_id=gen.product.analysis_product_id,
        )

    assert exc_info.value.error_code == "analysis_product_not_in_session"
    assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Test 7: package eligibility flag
# ---------------------------------------------------------------------------


def test_lineage_package_eligibility_flag(seeded_db) -> None:
    """Promote a product to package_eligible; package.package_eligible_or_packaged must be True."""
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-lin-test",
        name="WS Lin Pkg",
        client_request_id="req-ws-lin-pkg-001",
    )
    gen = generate_analysis_product(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-pkg-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    pid = gen.product.analysis_product_id
    sid = "session-lin-test"

    def _t(crid: str, intent: str, reason: str) -> None:
        transition_analysis_product(
            db,
            session_id=sid,
            analysis_product_id=pid,
            client_request_id=crid,
            request=AnalysisProductTransitionRequest(
                decision_intent=intent,
                decision_reason_code=reason,
            ),
        )
        db.commit()

    _t("lin-pkg-step-1", "promote", "proposed_ready")
    _t("lin-pkg-step-2", "promote", "validation_passed")
    _t("lin-pkg-step-3", "accept", "grounded_accept")
    _t("lin-pkg-step-4", "mark_package_eligible", "package_ready")

    lineage = build_analysis_product_lineage(db, session_id=sid, analysis_product_id=pid)

    pkg = lineage["package"]
    assert pkg["package_eligible_or_packaged"] is True
    assert pkg["lifecycle_status"] == "package_eligible"


# ---------------------------------------------------------------------------
# Route-level test (service layer, no HTTP client needed)
# Tests that the service response has the correct top-level keys and that
# no body/title/payload leaks into the lineage dict.
# ---------------------------------------------------------------------------


def test_lineage_response_bounded_no_body_leak(seeded_db) -> None:
    """Lineage dict must have all required keys and must NOT contain body/title."""
    db = seeded_db
    ws = _make_working_set(
        db,
        session_id="session-lin-test",
        name="WS Lin Bounded",
        client_request_id="req-ws-lin-bounded-001",
    )
    gen = generate_analysis_product(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-bounded-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_staleness_diagnostic",
    )
    db.commit()
    product_id = gen.product.analysis_product_id

    lineage = build_analysis_product_lineage(
        db,
        session_id="session-lin-test",
        analysis_product_id=product_id,
    )

    # Required top-level keys
    required_keys = {
        "schema_id",
        "analysis_product_id",
        "product",
        "working_set",
        "working_set_linked",
        "method_provenance",
        "evidence_refs",
        "evidence_refs_truncated",
        "review_trail",
        "package",
    }
    assert required_keys <= set(lineage.keys()), (
        f"Missing keys: {required_keys - set(lineage.keys())}"
    )

    # No raw body/title/payload in top-level or product sub-dict
    assert "body" not in lineage
    assert "title" not in lineage
    assert "payload_ref" not in lineage
    prod = lineage["product"]
    assert "body" not in prod
    assert "title" not in prod
    assert "payload_ref" not in prod

    # method_provenance present for deterministic (staleness_diagnostic is state-consuming)
    mp = lineage["method_provenance"]
    assert mp is not None
    assert mp["method_id"] == "working_set_staleness_diagnostic"
    # input_state_hash present for state-consuming methods
    assert "input_state_hash" in mp


# ---------------------------------------------------------------------------
# _order_review_decisions — chain linearizer unit tests (clock-independent)
# ---------------------------------------------------------------------------


def _mk_decision(did: str, frm: str, to: str, ts: datetime | None):
    """Build a transient (unpersisted) review-decision row carrying only the
    attributes the linearizer reads."""
    return L3AnalysisProductReviewDecision(
        analysis_product_review_decision_id=did,
        analysis_product_id="p",
        session_id="s",
        from_status=frm,
        to_status=to,
        review_decision="promote",
        decision_reason_code="proposed_ready",
        decision_basis_hash="h",
        decision_schema_id="x",
        product_basis_hash="h",
        client_request_id=did,
        created_at=ts,
    )


def _ids(rows) -> list[str]:
    return [r.analysis_product_review_decision_id for r in rows]


def test_order_review_decisions_empty_and_single() -> None:
    assert _order_review_decisions([]) == []
    only = _mk_decision("d1", "draft", "proposed", None)
    assert _ids(_order_review_decisions([only])) == ["d1"]


def test_order_review_decisions_linear_overrides_clock() -> None:
    """A clean promotion chain is returned draft-first even when created_at is
    reversed and UUID ids sort against insertion order."""
    base = datetime(2026, 6, 17, tzinfo=timezone.utc)
    # created_at deliberately REVERSED vs chain order; ids also reverse-sorted.
    d_accept = _mk_decision("d1-accept", "validated", "accepted", base)
    d_valid = _mk_decision("d2-valid", "proposed", "validated", base.replace(hour=1))
    d_prop = _mk_decision("d3-prop", "draft", "proposed", base.replace(hour=2))
    ordered = _order_review_decisions([d_accept, d_valid, d_prop])
    assert [r.from_status for r in ordered] == ["draft", "proposed", "validated"]
    assert [r.to_status for r in ordered] == ["proposed", "validated", "accepted"]


def test_order_review_decisions_revise_loop_keeps_all_once() -> None:
    """A revise loop (ambiguous head) must not drop, duplicate, or crash."""
    base = datetime(2026, 6, 17, tzinfo=timezone.utc)
    rows = [
        _mk_decision("a", "draft", "proposed", base),
        _mk_decision("b", "proposed", "draft", base.replace(minute=1)),
        _mk_decision("c", "draft", "proposed", base.replace(minute=2)),
        _mk_decision("d", "proposed", "validated", base.replace(minute=3)),
    ]
    ordered = _order_review_decisions(rows)
    assert sorted(_ids(ordered)) == ["a", "b", "c", "d"]
    assert len(ordered) == 4


def test_order_review_decisions_disconnected_chains_all_once() -> None:
    """Two disconnected sub-chains: every decision appears exactly once."""
    base = datetime(2026, 6, 17, tzinfo=timezone.utc)
    rows = [
        _mk_decision("y", "validated", "accepted", base.replace(minute=5)),
        _mk_decision("x", "proposed", "validated", base.replace(minute=4)),
        _mk_decision("n", "draft", "proposed", base.replace(minute=1)),
    ]
    ordered = _order_review_decisions(rows)
    assert sorted(_ids(ordered)) == ["n", "x", "y"]
    assert len(ordered) == 3


def test_lineage_api_cross_session_409(seeded_db) -> None:
    """build_analysis_product_lineage raises 409 when the product is in another session."""
    db = seeded_db
    other = L3Session(
        session_id="session-lin-other",
        selection_manifest_id="manifest-lin-other",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    db.add(other)
    db.commit()

    ws = _make_working_set(
        db, session_id="session-lin-test", name="WS Lin Cross", client_request_id="req-ws-lin-cross-001"
    )
    gen = generate_analysis_product(
        db,
        session_id="session-lin-test",
        client_request_id="req-lin-cross-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()

    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        build_analysis_product_lineage(
            db,
            session_id="session-lin-other",
            analysis_product_id=gen.product.analysis_product_id,
        )
    assert exc_info.value.error_code == "analysis_product_not_in_session"
    assert exc_info.value.http_status == 409
