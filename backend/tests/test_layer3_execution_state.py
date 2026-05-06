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
from app.models.models import L3PassRun, L3Session
from app.services import layer3_execution_state as execution_state
from app.services import layer3_workbench
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_STATUS_COMPLETED_WITH_WARNINGS,
    PASS_STATUS_FAILED,
    PASS_STATUS_RUNNING,
    PASS_STATUS_SELECTED_NOT_STARTED,
    PASS_TYPE_SINGLE_ITEM,
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


def _pass_run(
    pass_run_id: str,
    *,
    status: str = PASS_STATUS_SELECTED_NOT_STARTED,
    summary_json: dict | None = None,
    created_at: datetime | None = None,
) -> L3PassRun:
    return L3PassRun(
        pass_run_id=pass_run_id,
        session_id="session-execution-state",
        analysis_plan_id="plan-execution-state",
        analysis_set_id="set-execution-state",
        pass_type=PASS_TYPE_SINGLE_ITEM,
        engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
        status=status,
        input_payload_ref=f"payload://{pass_run_id}/input",
        output_payload_ref=None,
        summary_json=summary_json or {},
        created_at=created_at,
    )


def test_execution_selection_from_session_preserves_workbench_projection() -> None:
    selection = {
        "schema_id": execution_state.EXECUTION_SELECTION_STATE_SCHEMA_ID,
        "state": execution_state.EXECUTION_SELECTION_STATE,
        "pass_run_ids": ["pass-run-selected"],
    }
    session = L3Session(
        session_id="session-execution-state",
        selection_manifest_id="manifest-execution-state",
        operator_context_json={},
        summary_json={"execution_selection": selection},
    )

    assert execution_state.execution_selection_from_session(session) == selection
    assert layer3_workbench._execution_selection_from_session(session) == selection

    session.summary_json["execution_selection"] = {
        **selection,
        "schema_id": "wrong-schema",
    }
    assert execution_state.execution_selection_from_session(session) is None
    assert layer3_workbench._execution_selection_from_session(session) is None


def test_pass_run_projection_helpers_preserve_existing_state_semantics() -> None:
    selected = _pass_run("pass-run-selected")
    started_by_summary = _pass_run(
        "pass-run-summary-started",
        summary_json={"execution_started": True, "analysis_run_id": 123},
    )
    started_by_status = _pass_run("pass-run-running", status=PASS_STATUS_RUNNING)
    completed = _pass_run("pass-run-completed", status=PASS_STATUS_COMPLETED)
    warning = _pass_run("pass-run-warning", status=PASS_STATUS_COMPLETED_WITH_WARNINGS)
    failed = _pass_run("pass-run-failed", status=PASS_STATUS_FAILED)

    assert execution_state.pass_run_execution_started(selected) is False
    assert execution_state.pass_run_execution_started(started_by_summary) is True
    assert execution_state.pass_run_execution_started(started_by_status) is True
    assert execution_state.pass_run_analysis_run_id(started_by_summary) == "123"
    assert layer3_workbench._pass_run_analysis_run_id(started_by_summary) == "123"

    assert execution_state.execution_state_for_pass_runs([]) == execution_state.EXECUTION_SELECTION_STATE
    assert execution_state.execution_state_for_pass_runs([selected]) == execution_state.EXECUTION_SELECTION_STATE
    assert (
        execution_state.execution_state_for_pass_runs([completed, warning])
        == execution_state.EXECUTION_PASS_COMPLETED_STATE
    )
    assert execution_state.execution_state_for_pass_runs([failed]) == execution_state.EXECUTION_PASS_FAILED_STATE
    assert (
        execution_state.execution_state_for_pass_runs([failed, started_by_status])
        == execution_state.EXECUTION_PASS_RUNNING_STATE
    )
    assert (
        layer3_workbench._execution_state_for_pass_runs([completed, warning])
        == execution_state.EXECUTION_PASS_COMPLETED_STATE
    )


def test_analysis_execution_start_from_pass_run_preserves_workbench_projection() -> None:
    start_state = {
        "schema_id": execution_state.ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID,
        "state": execution_state.EXECUTION_PASS_RUNNING_STATE,
        "analysis_run_id": "analysis-run-execution-state",
    }
    pass_run = _pass_run(
        "pass-run-start-state",
        status=PASS_STATUS_RUNNING,
        summary_json={"analysis_execution_start": start_state},
    )

    assert execution_state.analysis_execution_start_from_pass_run(pass_run) == start_state
    assert layer3_workbench._analysis_execution_start_from_pass_run(pass_run) == start_state

    pass_run.summary_json["analysis_execution_start"] = {**start_state, "schema_id": "wrong-schema"}
    assert execution_state.analysis_execution_start_from_pass_run(pass_run) is None


def test_execution_selection_pass_runs_orders_by_creation_then_id(db_session) -> None:
    session = L3Session(
        session_id="session-execution-state",
        selection_manifest_id="manifest-execution-state",
        operator_context_json={},
        summary_json={},
    )
    earlier = datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc)
    later = datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc)
    db_session.add(session)
    db_session.add_all(
        [
            _pass_run("pass-run-c", created_at=later),
            _pass_run("pass-run-b", created_at=earlier),
            _pass_run("pass-run-a", created_at=earlier),
        ]
    )
    db_session.commit()

    pass_runs = execution_state.execution_selection_pass_runs(db_session, session_id=session.session_id)

    assert [pass_run.pass_run_id for pass_run in pass_runs] == ["pass-run-a", "pass-run-b", "pass-run-c"]
    delegated_pass_runs = layer3_workbench._execution_selection_pass_runs(
        db_session,
        session_id=session.session_id,
    )
    assert [pass_run.pass_run_id for pass_run in delegated_pass_runs] == [
        "pass-run-a",
        "pass-run-b",
        "pass-run-c",
    ]
