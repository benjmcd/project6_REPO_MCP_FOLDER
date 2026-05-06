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
from app.models.models import L3AnalysisPlan, L3Session
from app.services import layer3_plan_flow_state as state
from app.services import layer3_workbench
from app.services.layer3_plan_revision_state import (
    PLAN_REVISION_RECOVERY_STATE,
    plan_revision_control_record,
)


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


def test_latest_analysis_plan_preserves_workbench_ordering(db_session) -> None:
    session = L3Session(
        session_id="session-plan-flow-state",
        selection_manifest_id="manifest-plan-flow-state",
        operator_context_json={},
        summary_json={},
    )
    earlier = L3AnalysisPlan(
        analysis_plan_id="plan-earlier",
        session_id=session.session_id,
        analysis_set_ids_json=[],
        status="formed",
        approved_by_operator=False,
        created_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    latest_b = L3AnalysisPlan(
        analysis_plan_id="plan-b",
        session_id=session.session_id,
        analysis_set_ids_json=[],
        status="approved",
        approved_by_operator=True,
        created_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    latest_a = L3AnalysisPlan(
        analysis_plan_id="plan-a",
        session_id=session.session_id,
        analysis_set_ids_json=[],
        status="approved",
        approved_by_operator=True,
        created_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    db_session.add_all([session, earlier, latest_b, latest_a])
    db_session.commit()

    assert (
        state.latest_analysis_plan(db_session, session_id=session.session_id).analysis_plan_id
        == "plan-a"
    )
    assert (
        layer3_workbench._latest_analysis_plan(db_session, session_id=session.session_id).analysis_plan_id
        == "plan-a"
    )


def test_plan_revision_control_for_session_filters_recovery_state(db_session) -> None:
    active_control = plan_revision_control_record(
        source_preview_id="preview-active",
        source_preview_hash="hash-active",
        operator_decision="request_revision",
        operator_note="Needs review.",
        created_at="2026-05-05T00:00:00Z",
    )
    recovered_control = {
        **active_control,
        "source_preview_id": "preview-recovered",
        "recovery_state": PLAN_REVISION_RECOVERY_STATE,
    }
    db_session.add_all(
        [
            L3Session(
                session_id="session-active-revision",
                selection_manifest_id="manifest-active-revision",
                operator_context_json={},
                summary_json={"plan_revision_control": active_control},
            ),
            L3Session(
                session_id="session-recovered-revision",
                selection_manifest_id="manifest-recovered-revision",
                operator_context_json={},
                summary_json={"plan_revision_control": recovered_control},
            ),
        ]
    )
    db_session.commit()

    assert (
        state.plan_revision_control_for_session(
            db_session,
            session_id="session-active-revision",
        )
        == active_control
    )
    assert (
        layer3_workbench._plan_revision_control(
            db_session,
            session_id="session-active-revision",
        )
        == active_control
    )
    assert (
        state.plan_revision_control_for_session(
            db_session,
            session_id="session-recovered-revision",
        )
        is None
    )
