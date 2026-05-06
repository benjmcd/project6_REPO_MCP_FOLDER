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
from app.models.models import L3AnalysisPlan, L3AnalysisSet, L3MaterialSnapshot, L3Session, L3TypingRecord
from app.services import layer3_plan_flow_readiness as readiness
from app.services import layer3_workbench
from app.services.layer3_approved_plan_correction import APPROVED_PLAN_CANCELLED_STATUS
from app.services.layer3_plan_revision_state import plan_revision_control_record


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


def _seed_session_ready_for_plan(db_session, *, session_id: str) -> None:
    db_session.add_all(
        [
            L3Session(
                session_id=session_id,
                selection_manifest_id=f"manifest-{session_id}",
                operator_context_json={},
                summary_json={},
            ),
            L3MaterialSnapshot(
                material_snapshot_id=f"snapshot-{session_id}",
                session_id=session_id,
                descriptor_id=f"descriptor-{session_id}",
                source_plane="test",
                source_shape="table",
                payload_ref=f"payload://{session_id}",
                payload_hash=f"hash-{session_id}",
                source_identity_json={},
                source_provenance_json={},
                load_summary_json={},
            ),
            L3TypingRecord(
                typing_record_id=f"typing-{session_id}",
                session_id=session_id,
                material_snapshot_id=f"snapshot-{session_id}",
                candidate_modalities_json=["quantitative"],
                chosen_modality="quantitative",
                typing_basis_json={},
                confidence=1.0,
            ),
            L3AnalysisSet(
                analysis_set_id=f"set-{session_id}",
                session_id=session_id,
                analysis_group_ids_json=[],
                analysis_unit_ids_json=[],
                set_type="associated_cohort",
                formation_basis_json={},
            ),
        ]
    )


def test_plan_preview_readiness_blocks_cancelled_plan_and_workbench_delegates(db_session) -> None:
    session_id = "session-plan-flow-readiness-cancelled"
    _seed_session_ready_for_plan(db_session, session_id=session_id)
    db_session.add(
        L3AnalysisPlan(
            analysis_plan_id="plan-cancelled-readiness",
            session_id=session_id,
            analysis_set_ids_json=[f"set-{session_id}"],
            status=APPROVED_PLAN_CANCELLED_STATUS,
            approved_by_operator=True,
            created_at=datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc),
            plan_json={},
        )
    )
    db_session.commit()

    expected = readiness.plan_preview_readiness(db_session, session_id=session_id)

    assert expected["blocked_reason"] == "approved_plan_cancelled"
    assert expected["available"] is False
    assert layer3_workbench._plan_preview_readiness(db_session, session_id=session_id) == expected


def test_plan_approval_summary_clones_cancel_state_and_workbench_delegates(db_session) -> None:
    session_id = "session-plan-flow-approval-cancelled"
    _seed_session_ready_for_plan(db_session, session_id=session_id)
    cancellation = {
        "schema_id": "layer3.approved_plan_cancel.v1",
        "decision": "cancel_without_replacement",
    }
    db_session.add(
        L3AnalysisPlan(
            analysis_plan_id="plan-cancelled-summary",
            session_id=session_id,
            analysis_set_ids_json=[f"set-{session_id}"],
            status=APPROVED_PLAN_CANCELLED_STATUS,
            approved_by_operator=True,
            approved_at=datetime(2026, 5, 6, 8, 30, tzinfo=timezone.utc),
            created_at=datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc),
            plan_json={
                "approved_plan_cancel": cancellation,
                "excluded_sets_json": [{"analysis_set_id": "excluded"}],
                "planned_passes_json": [{"pass_id": "pass-1"}],
            },
        )
    )
    db_session.commit()

    summary = readiness.plan_approval_summary(db_session, session_id=session_id)
    delegated = layer3_workbench._plan_approval_summary(db_session, session_id=session_id)

    assert summary == delegated
    assert summary["blocked_reason"] == "approved_plan_cancelled"
    assert summary["approved_plan_cancel"] == cancellation
    assert summary["approved_plan_cancel"] is not cancellation


def test_plan_revision_summary_uses_control_record_and_workbench_delegates(db_session) -> None:
    control = plan_revision_control_record(
        source_preview_id="preview-readiness",
        source_preview_hash="hash-readiness",
        operator_decision="request_revision",
        operator_note="Needs a sharper plan.",
        created_at="2026-05-06T08:00:00Z",
    )
    session = L3Session(
        session_id="session-plan-flow-revision-summary",
        selection_manifest_id="manifest-plan-flow-revision-summary",
        operator_context_json={},
        summary_json={"plan_revision_control": control},
    )
    db_session.add(session)
    db_session.commit()

    summary = readiness.plan_revision_summary(db_session, session_id=session.session_id)

    assert summary == layer3_workbench._plan_revision_summary(db_session, session_id=session.session_id)
    assert summary["available"] is False
    assert summary["state"] == "plan_revision_requested"
    assert summary["source_preview_id"] == "preview-readiness"
