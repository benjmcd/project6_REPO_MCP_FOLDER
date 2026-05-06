from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    ConnectorRun,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3Descriptor,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
)
from app.services.layer3_plan_revision_recovery import (
    PLAN_REVISION_RECOVERY_DOWNSTREAM_UNAVAILABLE,
    PLAN_REVISION_RECOVERY_NEXT_STATE,
    PLAN_REVISION_RECOVERY_PREVIEW_MARKER_SCHEMA_ID,
    PLAN_REVISION_RECOVERY_RESULT_SCHEMA_ID,
    plan_revision_recovery_preview_marker,
    recover_plan_revision_for_preview_refresh,
)
from app.services.layer3_plan_revision_state import (
    PLAN_REVISION_CONTROL_CONTEXT_KEY,
    PLAN_REVISION_RECOVERY_CONTEXT_KEY,
    PLAN_REVISION_RECOVERY_DECISION,
    PLAN_REVISION_RECOVERY_SCHEMA_ID,
    PLAN_REVISION_RECOVERY_STATE,
    plan_revision_control_record,
    plan_revision_recovery_from_session,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError


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


def _insert_recoverable_session(
    db: Session,
    *,
    suffix: str,
    operator_decision: str = "request_revision",
    source_preview_id: str = "preview-revision",
    source_preview_hash: str = "hash-revision",
    include_gate_c: bool = True,
) -> tuple[str, str, str]:
    session_id = f"session-{suffix}"
    analysis_set_id = f"analysis-set-{suffix}"
    descriptor_id = f"descriptor-{suffix}"
    material_snapshot_id = f"material-snapshot-{suffix}"
    selection_manifest_id = f"manifest-{suffix}"
    control = plan_revision_control_record(
        source_preview_id=source_preview_id,
        source_preview_hash=source_preview_hash,
        operator_decision=operator_decision,
        operator_note="Needs revised plan authority.",
        created_at="2026-05-05T00:00:00Z",
    )
    rows = [
        L3Session(
            session_id=session_id,
            selection_manifest_id=selection_manifest_id,
            operator_context_json={},
            summary_json={
                "gate_b_summary_v1": {
                    "approved": 1,
                    "denied": 0,
                    "isolated": 0,
                    "flagged": 0,
                },
                PLAN_REVISION_CONTROL_CONTEXT_KEY: control,
            },
        ),
        L3SelectionManifest(
            selection_manifest_id=selection_manifest_id,
            session_id=session_id,
            manifest_json={"source_preview_id": source_preview_id},
            source_plane_hints_json={"source_plane": "nrc_aps"},
            selection_hash=f"selection-hash-{suffix}",
            commit_reason="plan revision recovery service proof fixture",
        ),
        L3Descriptor(
            descriptor_id=descriptor_id,
            session_id=session_id,
            selection_manifest_id=selection_manifest_id,
            source_plane="nrc_aps",
            descriptor_type="document",
            selector_payload_json={"source_preview_id": source_preview_id},
            selection_basis_json={"source_preview_hash": source_preview_hash},
            expansion_reason="plan revision recovery service proof fixture",
            descriptor_hash=f"descriptor-hash-{suffix}",
        ),
        L3MaterialSnapshot(
            material_snapshot_id=material_snapshot_id,
            session_id=session_id,
            descriptor_id=descriptor_id,
            source_plane="nrc_aps",
            source_shape="document",
            payload_ref=f"memory://{material_snapshot_id}",
            payload_hash=f"payload-hash-{suffix}",
            source_identity_json={"source_preview_id": source_preview_id},
            source_provenance_json={"source_preview_hash": source_preview_hash},
            load_summary_json={"fixture": "plan_revision_recovery"},
        ),
    ]
    if include_gate_c:
        rows.extend(
            [
                L3TypingRecord(
                    typing_record_id=f"typing-{suffix}",
                    session_id=session_id,
                    material_snapshot_id=material_snapshot_id,
                    candidate_modalities_json=["quantitative"],
                    chosen_modality="quantitative",
                    typing_basis_json={"source_preview_id": source_preview_id},
                    confidence=0.9,
                ),
                L3AnalysisSet(
                    analysis_set_id=analysis_set_id,
                    session_id=session_id,
                    analysis_group_ids_json=["group-1"],
                    analysis_unit_ids_json=["unit-1"],
                    set_type="single_item",
                    formation_basis_json={"source_preview_id": source_preview_id},
                ),
            ]
        )
    db.add_all(rows)
    db.commit()
    return session_id, analysis_set_id, material_snapshot_id


def _payload(
    *,
    request_id: str,
    session_id: str,
    source_revision_state: str = "plan_revision_requested",
    source_preview_id: str = "preview-revision",
    source_preview_hash: str = "hash-revision",
    **extra,
) -> dict:
    return {
        "client_request_id": request_id,
        "session_id": session_id,
        "source_revision_state": source_revision_state,
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "operator_decision": PLAN_REVISION_RECOVERY_DECISION,
        **extra,
    }


def _assert_no_recovery_downstream_artifacts(db: Session) -> None:
    assert db.query(L3AnalysisPlan).count() == 0
    assert db.query(L3PassRun).count() == 0
    assert db.query(AnalysisRun).count() == 0
    assert db.query(AnalysisArtifact).count() == 0
    assert db.query(L3OutputPackage).count() == 0
    assert db.query(L3ReconciliationRecord).count() == 0
    assert db.query(ConnectorRun).count() == 0


def _owner_authority_row_counts(db: Session, *, session_id: str) -> dict[str, int]:
    return {
        "sessions": db.query(L3Session).filter(L3Session.session_id == session_id).count(),
        "selection_manifests": db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == session_id)
        .count(),
        "descriptors": db.query(L3Descriptor).filter(L3Descriptor.session_id == session_id).count(),
        "material_snapshots": db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == session_id)
        .count(),
        "typing_records": db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count(),
        "analysis_sets": db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count(),
    }


def test_recover_plan_revision_for_preview_refresh_records_summary_state_only_and_is_idempotent(db_session) -> None:
    session_id, _, _ = _insert_recoverable_session(db_session, suffix="success")
    payload = _payload(
        request_id="service-plan-recovery",
        session_id=session_id,
        operator_note="Return to server preview refresh only.",
    )
    owner_counts = _owner_authority_row_counts(db_session, session_id=session_id)

    result = recover_plan_revision_for_preview_refresh(db_session, payload)

    assert result["schema_id"] == PLAN_REVISION_RECOVERY_RESULT_SCHEMA_ID
    assert result["source_revision_state"] == "plan_revision_requested"
    assert result["next_state"] == PLAN_REVISION_RECOVERY_NEXT_STATE
    assert result["preview_refresh_required"] is True
    assert result["approval_available"] is False
    assert result["execution_started"] is False
    assert result["recovery_lifecycle_only"] is True
    assert result["operator_note_recorded"] is True
    assert result["downstream_unavailable"] == list(PLAN_REVISION_RECOVERY_DOWNSTREAM_UNAVAILABLE)
    assert result["authority_rail"]["persistence_mode"] == "plan_revision_recovery"
    assert result["plan_revision_recovery"]["schema_id"] == PLAN_REVISION_RECOVERY_SCHEMA_ID
    assert result["plan_revision_recovery"]["state"] == PLAN_REVISION_RECOVERY_STATE

    duplicate = recover_plan_revision_for_preview_refresh(db_session, payload)
    assert duplicate["plan_revision_recovery"]["recovery_id"] == result["plan_revision_recovery"]["recovery_id"]
    assert _owner_authority_row_counts(db_session, session_id=session_id) == owner_counts

    stored_session = db_session.get(L3Session, session_id)
    assert stored_session is not None
    assert stored_session.summary_json[PLAN_REVISION_CONTROL_CONTEXT_KEY]["recovery_state"] == (
        PLAN_REVISION_RECOVERY_STATE
    )
    assert plan_revision_recovery_from_session(stored_session) == stored_session.summary_json[
        PLAN_REVISION_RECOVERY_CONTEXT_KEY
    ]
    marker = plan_revision_recovery_preview_marker(result["plan_revision_recovery"])
    assert marker is not None
    assert marker["schema_id"] == PLAN_REVISION_RECOVERY_PREVIEW_MARKER_SCHEMA_ID
    assert marker["preview_refresh_required"] is True
    _assert_no_recovery_downstream_artifacts(db_session)


def test_recover_plan_revision_for_preview_refresh_rejects_non_admitted_fields_before_mutation(db_session) -> None:
    session_id, _, _ = _insert_recoverable_session(db_session, suffix="forbidden")

    with pytest.raises(Layer3WorkbenchError) as forbidden:
        recover_plan_revision_for_preview_refresh(
            db_session,
            _payload(
                request_id="service-plan-recovery-forbidden",
                session_id=session_id,
                execute=True,
                provider_public_url="https://example.invalid/object",
            ),
        )

    assert forbidden.value.error_code == "execution_not_admitted"
    assert forbidden.value.blocked_fields == ["execute", "provider_public_url"]
    stored_session = db_session.get(L3Session, session_id)
    assert stored_session is not None
    assert PLAN_REVISION_RECOVERY_CONTEXT_KEY not in stored_session.summary_json
    assert PLAN_REVISION_CONTROL_CONTEXT_KEY in stored_session.summary_json
    _assert_no_recovery_downstream_artifacts(db_session)


def test_recover_plan_revision_for_preview_refresh_prechecks_fail_closed_before_mutation(db_session) -> None:
    session_id, _, _ = _insert_recoverable_session(db_session, suffix="prechecks")

    with pytest.raises(Layer3WorkbenchError) as state_mismatch:
        recover_plan_revision_for_preview_refresh(
            db_session,
            _payload(
                request_id="service-plan-recovery-state-mismatch",
                session_id=session_id,
                source_revision_state="plan_rejected",
            ),
        )
    assert state_mismatch.value.error_code == "plan_revision_state_mismatch"

    with pytest.raises(Layer3WorkbenchError) as preview_mismatch:
        recover_plan_revision_for_preview_refresh(
            db_session,
            _payload(
                request_id="service-plan-recovery-preview-mismatch",
                session_id=session_id,
                source_preview_hash="stale-preview-hash",
            ),
        )
    assert preview_mismatch.value.error_code == "preview_mismatch"

    stored_session = db_session.get(L3Session, session_id)
    assert stored_session is not None
    assert PLAN_REVISION_RECOVERY_CONTEXT_KEY not in stored_session.summary_json
    _assert_no_recovery_downstream_artifacts(db_session)


def test_recover_plan_revision_for_preview_refresh_blocks_plan_and_pass_run_state_without_recovery_mutation(
    db_session,
) -> None:
    plan_session_id, plan_analysis_set_id, _ = _insert_recoverable_session(db_session, suffix="plan-blocked")
    db_session.add(
        L3AnalysisPlan(
            analysis_plan_id="service-plan-recovery-approved-plan",
            session_id=plan_session_id,
            analysis_set_ids_json=[plan_analysis_set_id],
            status="approved",
            approved_by_operator=True,
            plan_json={"approval_only": True, "execution_started": False},
        )
    )
    db_session.commit()

    with pytest.raises(Layer3WorkbenchError) as plan_blocked:
        recover_plan_revision_for_preview_refresh(
            db_session,
            _payload(request_id="service-plan-recovery-approved-plan", session_id=plan_session_id),
        )
    assert plan_blocked.value.error_code == "plan_already_approved"

    pass_session_id, pass_analysis_set_id, _ = _insert_recoverable_session(db_session, suffix="pass-blocked")
    db_session.add(
        L3AnalysisPlan(
            analysis_plan_id="service-plan-recovery-pass-plan",
            session_id=pass_session_id,
            analysis_set_ids_json=[pass_analysis_set_id],
            status="approved",
            approved_by_operator=True,
            plan_json={"approval_only": True, "execution_started": False},
        )
    )
    db_session.add(
        L3PassRun(
            pass_run_id="service-plan-recovery-pass-run",
            session_id=pass_session_id,
            analysis_plan_id="service-plan-recovery-pass-plan",
            analysis_set_id=pass_analysis_set_id,
            pass_type="single_item",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            input_payload_ref="memory://service-plan-recovery-pass-run/input",
            summary_json={"execution_started": False},
        )
    )
    db_session.commit()

    with pytest.raises(Layer3WorkbenchError) as pass_blocked:
        recover_plan_revision_for_preview_refresh(
            db_session,
            _payload(request_id="service-plan-recovery-pass-runs", session_id=pass_session_id),
        )
    assert pass_blocked.value.error_code == "pass_runs_already_exist"

    for session_id in (plan_session_id, pass_session_id):
        stored_session = db_session.get(L3Session, session_id)
        assert stored_session is not None
        assert PLAN_REVISION_RECOVERY_CONTEXT_KEY not in stored_session.summary_json
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(AnalysisArtifact).count() == 0
    assert db_session.query(L3OutputPackage).count() == 0
    assert db_session.query(L3ReconciliationRecord).count() == 0
    assert db_session.query(ConnectorRun).count() == 0


def test_plan_revision_recovery_preview_marker_requires_recovery_state() -> None:
    recovery = {
        "schema_id": PLAN_REVISION_RECOVERY_SCHEMA_ID,
        "state": PLAN_REVISION_RECOVERY_STATE,
        "recovery_id": "recovery-1",
        "client_request_id": "request-1",
        "source_revision_state": "plan_revision_requested",
        "source_preview_id": "preview-revision",
        "source_preview_hash": "hash-revision",
        "created_at": "2026-05-05T00:00:00Z",
    }

    assert plan_revision_recovery_preview_marker(recovery) == {
        "schema_id": PLAN_REVISION_RECOVERY_PREVIEW_MARKER_SCHEMA_ID,
        "recovery_id": "recovery-1",
        "client_request_id": "request-1",
        "source_revision_state": "plan_revision_requested",
        "source_preview_id": "preview-revision",
        "source_preview_hash": "hash-revision",
        "preview_refresh_required": True,
        "approval_available": False,
        "created_at": "2026-05-05T00:00:00Z",
    }
    assert plan_revision_recovery_preview_marker({**recovery, "state": "plan_revision_requested"}) is None
    assert plan_revision_recovery_preview_marker(None) is None
