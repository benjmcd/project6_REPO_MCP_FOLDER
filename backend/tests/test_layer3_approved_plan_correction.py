from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
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
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3Session,
)
from app.services.layer3_approved_plan_correction import (
    APPROVED_PLAN_CANCEL_CONTEXT_KEY,
    APPROVED_PLAN_CANCEL_DECISION,
    APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE,
    APPROVED_PLAN_CANCEL_NEXT_STATE,
    APPROVED_PLAN_CANCEL_RESULT_SCHEMA_ID,
    APPROVED_PLAN_CANCEL_STATE_SCHEMA_ID,
    APPROVED_PLAN_CANCELLED_STATUS,
    approved_plan_cancel_from_session,
    cancel_approved_plan_without_replacement,
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


def _insert_approved_plan(
    db: Session,
    *,
    suffix: str,
    status: str = "approved",
    approved_by_operator: bool = True,
    source_preview_id: str = "preview-approved",
    source_preview_hash: str = "hash-approved",
) -> tuple[str, str, str]:
    session_id = f"session-{suffix}"
    analysis_set_id = f"analysis-set-{suffix}"
    analysis_plan_id = f"analysis-plan-{suffix}"
    db.add_all(
        [
            L3Session(
                session_id=session_id,
                selection_manifest_id=f"manifest-{suffix}",
                operator_context_json={},
                summary_json={
                    "gate_b_summary_v1": {
                        "approved": 1,
                        "denied": 0,
                        "isolated": 0,
                        "flagged": 0,
                    }
                },
            ),
            L3AnalysisSet(
                analysis_set_id=analysis_set_id,
                session_id=session_id,
                analysis_group_ids_json=["group-1"],
                analysis_unit_ids_json=["unit-1"],
                set_type="single_item",
                formation_basis_json={"source_preview_id": source_preview_id},
            ),
            L3AnalysisPlan(
                analysis_plan_id=analysis_plan_id,
                session_id=session_id,
                analysis_set_ids_json=[analysis_set_id],
                status=status,
                approved_by_operator=approved_by_operator,
                approved_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
                plan_json={
                    "source_preview_id": source_preview_id,
                    "source_preview_hash": source_preview_hash,
                    "analysis_set_ids": [analysis_set_id],
                },
            ),
        ]
    )
    db.commit()
    return session_id, analysis_plan_id, analysis_set_id


def _payload(
    *,
    request_id: str,
    session_id: str,
    analysis_plan_id: str,
    source_preview_id: str = "preview-approved",
    source_preview_hash: str = "hash-approved",
    **extra,
) -> dict:
    return {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "operator_decision": APPROVED_PLAN_CANCEL_DECISION,
        **extra,
    }


def _assert_no_downstream_artifacts(db: Session) -> None:
    assert db.query(L3PassRun).count() == 0
    assert db.query(AnalysisRun).count() == 0
    assert db.query(AnalysisArtifact).count() == 0
    assert db.query(L3OutputPackage).count() == 0
    assert db.query(L3ReconciliationRecord).count() == 0
    assert db.query(ConnectorRun).count() == 0


def test_cancel_approved_plan_without_replacement_updates_existing_plan_only_and_is_idempotent(db_session) -> None:
    session_id, analysis_plan_id, _ = _insert_approved_plan(db_session, suffix="success")
    payload = _payload(
        request_id="service-approved-plan-cancel",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        operator_note="Cancel before execution selection.",
    )

    result = cancel_approved_plan_without_replacement(db_session, payload)

    assert result["schema_id"] == APPROVED_PLAN_CANCEL_RESULT_SCHEMA_ID
    assert result["next_state"] == APPROVED_PLAN_CANCEL_NEXT_STATE
    assert result["approved_plan_cancelled"] is True
    assert result["approval_available"] is False
    assert result["execution_started"] is False
    assert result["replacement_plan_created"] is False
    assert result["plan_status"] == APPROVED_PLAN_CANCELLED_STATUS
    assert result["previous_plan_status"] == "approved"
    assert result["downstream_unavailable"] == list(APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE)
    assert result["authority_rail"]["persistence_mode"] == "approved_plan_cancel"
    assert result["approved_plan_cancel"]["schema_id"] == APPROVED_PLAN_CANCEL_STATE_SCHEMA_ID
    assert result["approved_plan_cancel"]["operator_note_recorded"] is True

    duplicate = cancel_approved_plan_without_replacement(db_session, payload)
    assert duplicate["approved_plan_cancel"]["cancellation_id"] == result["approved_plan_cancel"]["cancellation_id"]

    stored_session = db_session.get(L3Session, session_id)
    stored_plan = db_session.get(L3AnalysisPlan, analysis_plan_id)
    assert stored_session is not None
    assert stored_plan is not None
    assert db_session.query(L3AnalysisPlan).count() == 1
    assert stored_plan.status == APPROVED_PLAN_CANCELLED_STATUS
    assert stored_plan.plan_json[APPROVED_PLAN_CANCEL_CONTEXT_KEY]["cancellation_id"] == result["approved_plan_cancel"][
        "cancellation_id"
    ]
    assert approved_plan_cancel_from_session(stored_session) == stored_session.summary_json[
        APPROVED_PLAN_CANCEL_CONTEXT_KEY
    ]
    _assert_no_downstream_artifacts(db_session)


def test_cancel_approved_plan_without_replacement_rejects_non_admitted_fields_before_mutation(db_session) -> None:
    session_id, analysis_plan_id, _ = _insert_approved_plan(db_session, suffix="forbidden")

    with pytest.raises(Layer3WorkbenchError) as forbidden:
        cancel_approved_plan_without_replacement(
            db_session,
            _payload(
                request_id="service-approved-plan-cancel-forbidden",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                replacement_plan={"mode": "not-admitted"},
                approved_plan_supersession=True,
                provider_public_url="https://example.invalid/object",
            ),
        )

    assert forbidden.value.error_code == "approved_plan_correction_not_admitted"
    assert forbidden.value.blocked_fields == [
        "approved_plan_supersession",
        "provider_public_url",
        "replacement_plan",
    ]
    stored_session = db_session.get(L3Session, session_id)
    stored_plan = db_session.get(L3AnalysisPlan, analysis_plan_id)
    assert stored_session is not None
    assert stored_plan is not None
    assert APPROVED_PLAN_CANCEL_CONTEXT_KEY not in stored_session.summary_json
    assert APPROVED_PLAN_CANCEL_CONTEXT_KEY not in stored_plan.plan_json
    assert stored_plan.status == "approved"
    _assert_no_downstream_artifacts(db_session)


def test_cancel_approved_plan_without_replacement_prechecks_fail_closed_before_mutation(db_session) -> None:
    session_id, analysis_plan_id, analysis_set_id = _insert_approved_plan(db_session, suffix="prechecks")

    with pytest.raises(Layer3WorkbenchError) as stale_preview:
        cancel_approved_plan_without_replacement(
            db_session,
            _payload(
                request_id="service-approved-plan-cancel-stale-preview",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                source_preview_hash="stale-preview-hash",
            ),
        )
    assert stale_preview.value.error_code == "preview_mismatch"

    db_session.add(
        L3PassRun(
            pass_run_id="service-approved-plan-cancel-pass-run",
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            analysis_set_id=analysis_set_id,
            pass_type="single_item",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            input_payload_ref="memory://service-approved-plan-cancel/input",
            summary_json={"execution_started": False},
        )
    )
    db_session.commit()

    with pytest.raises(Layer3WorkbenchError) as pass_runs:
        cancel_approved_plan_without_replacement(
            db_session,
            _payload(
                request_id="service-approved-plan-cancel-pass-runs",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
            ),
        )
    assert pass_runs.value.error_code == "pass_runs_already_exist"

    stored_session = db_session.get(L3Session, session_id)
    stored_plan = db_session.get(L3AnalysisPlan, analysis_plan_id)
    assert stored_session is not None
    assert stored_plan is not None
    assert APPROVED_PLAN_CANCEL_CONTEXT_KEY not in stored_session.summary_json
    assert APPROVED_PLAN_CANCEL_CONTEXT_KEY not in stored_plan.plan_json
    assert stored_plan.status == "approved"
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(AnalysisArtifact).count() == 0
    assert db_session.query(L3OutputPackage).count() == 0
    assert db_session.query(L3ReconciliationRecord).count() == 0
    assert db_session.query(ConnectorRun).count() == 0


def test_approved_plan_cancel_from_session_requires_current_schema() -> None:
    valid = {
        "schema_id": APPROVED_PLAN_CANCEL_STATE_SCHEMA_ID,
        "state": APPROVED_PLAN_CANCEL_NEXT_STATE,
        "cancellation_id": "cancel-1",
    }
    assert approved_plan_cancel_from_session(
        L3Session(
            session_id="session-valid",
            selection_manifest_id="manifest-valid",
            summary_json={APPROVED_PLAN_CANCEL_CONTEXT_KEY: valid},
        )
    ) == valid
    assert (
        approved_plan_cancel_from_session(
            L3Session(session_id="session-missing", selection_manifest_id="manifest-missing", summary_json={})
        )
        is None
    )
    assert (
        approved_plan_cancel_from_session(
            L3Session(
                session_id="session-wrong-schema",
                selection_manifest_id="manifest-wrong-schema",
                summary_json={
                    APPROVED_PLAN_CANCEL_CONTEXT_KEY: {
                        **valid,
                        "schema_id": "layer3.approved_plan_cancel_state.v0",
                    }
                },
            )
        )
        is None
    )
    assert approved_plan_cancel_from_session(None) is None
