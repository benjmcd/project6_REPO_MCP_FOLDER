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
from app.models.models import L3AnalysisPlan, L3PassRun, L3Session
from app.services import layer3_execution_selection as execution_selection
from app.services import layer3_workbench
from app.services.layer3_execution_state import EXECUTION_SELECTION_STATE_SCHEMA_ID
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_STATUS_SELECTED_NOT_STARTED,
    PASS_TYPE_SINGLE_ITEM,
    PLAN_STATUS_APPROVED,
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


def _session(session_id: str, summary_json: dict | None = None) -> L3Session:
    return L3Session(
        session_id=session_id,
        selection_manifest_id=f"manifest-{session_id}",
        operator_context_json={},
        summary_json=summary_json or {},
    )


def _approved_plan(session_id: str, plan_id: str = "plan-selection") -> L3AnalysisPlan:
    return L3AnalysisPlan(
        analysis_plan_id=plan_id,
        session_id=session_id,
        analysis_set_ids_json=["set-selection"],
        status=PLAN_STATUS_APPROVED,
        approved_by_operator=True,
        approved_at=datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc),
        plan_json={
            "source_preview_id": "preview-selection",
            "source_preview_hash": "hash-selection",
        },
    )


def _pass_run(
    session_id: str,
    plan_id: str,
    pass_run_id: str,
    *,
    status: str = PASS_STATUS_SELECTED_NOT_STARTED,
    summary_json: dict | None = None,
) -> L3PassRun:
    return L3PassRun(
        pass_run_id=pass_run_id,
        session_id=session_id,
        analysis_plan_id=plan_id,
        analysis_set_id="set-selection",
        pass_type=PASS_TYPE_SINGLE_ITEM,
        engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
        status=status,
        input_payload_ref=f"payload://{pass_run_id}/input",
        output_payload_ref=None,
        summary_json=summary_json or {},
    )


def test_execution_selection_summary_reports_available_approved_plan(db_session) -> None:
    session_id = "session-selection-available"
    db_session.add(_session(session_id))
    db_session.add(_approved_plan(session_id))
    db_session.commit()

    summary = execution_selection.execution_selection_summary(db_session, session_id=session_id)

    assert summary == layer3_workbench._execution_selection_summary(db_session, session_id=session_id)
    assert summary["available"] is True
    assert summary["selected"] is False
    assert summary["blocked_reason"] is None
    assert summary["analysis_plan_id"] == "plan-selection"
    assert summary["source_preview_id"] == "preview-selection"
    assert summary["source_preview_hash"] == "hash-selection"
    assert summary["downstream_unavailable"] == ["results", "package", "handoff"]


def test_execution_selection_summary_preserves_existing_selection_projection(db_session) -> None:
    session_id = "session-selection-existing"
    plan_id = "plan-selection-existing"
    selection_state = {
        "schema_id": EXECUTION_SELECTION_STATE_SCHEMA_ID,
        "state": "execution_selected_not_started",
        "analysis_plan_id": plan_id,
        "source_preview_id": "preview-existing",
        "source_preview_hash": "hash-existing",
        "selected_at": "2026-05-06T09:30:00Z",
        "pass_run_ids_json": ["pass-run-a", "pass-run-b"],
    }
    db_session.add(_session(session_id, {"execution_selection": selection_state}))
    db_session.add(_approved_plan(session_id, plan_id))
    db_session.add_all(
        [
            _pass_run(session_id, plan_id, "pass-run-a"),
            _pass_run(
                session_id,
                plan_id,
                "pass-run-b",
                status=PASS_STATUS_COMPLETED,
                summary_json={"analysis_run_id": "analysis-run-b"},
            ),
        ]
    )
    db_session.commit()

    summary = execution_selection.execution_selection_summary(db_session, session_id=session_id)

    assert summary == layer3_workbench._execution_selection_summary(db_session, session_id=session_id)
    assert summary["available"] is False
    assert summary["selected"] is True
    assert summary["blocked_reason"] == "execution_selection_already_exists"
    assert summary["pass_run_ids"] == ["pass-run-a", "pass-run-b"]
    assert summary["execution_started"] is True
    assert summary["analysis_run_ids"] == ["analysis-run-b"]
    assert summary["pass_run_statuses"]["pass-run-b"] == PASS_STATUS_COMPLETED


def test_execution_selection_summary_preserves_blocked_reasons(db_session) -> None:
    no_plan_session = "session-selection-no-plan"
    multiple_plan_session = "session-selection-multiple-plan"
    pass_runs_session = "session-selection-pass-runs"
    db_session.add_all(
        [
            _session(no_plan_session),
            _session(multiple_plan_session),
            _session(pass_runs_session),
            _approved_plan(multiple_plan_session, "plan-a"),
            _approved_plan(multiple_plan_session, "plan-b"),
            _approved_plan(pass_runs_session, "plan-pass-runs"),
            _pass_run(pass_runs_session, "plan-pass-runs", "pass-run-existing"),
        ]
    )
    db_session.commit()

    assert execution_selection.execution_selection_summary(
        db_session,
        session_id=no_plan_session,
    )["blocked_reason"] == "no_approved_plan"
    assert execution_selection.execution_selection_summary(
        db_session,
        session_id=multiple_plan_session,
    )["blocked_reason"] == "multiple_approved_plans"
    assert execution_selection.execution_selection_summary(
        db_session,
        session_id=pass_runs_session,
    )["blocked_reason"] == "pass_runs_already_exist"
