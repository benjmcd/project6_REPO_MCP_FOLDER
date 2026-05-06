from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
PASS_ENTRY_MIGRATION = BACKEND / "alembic" / "versions" / "0014_layer3_pass_entry.py"

from app.db.session import Base
from app.models.models import (
    L3_ANALYSIS_PLAN_STATUS_APPROVED,
    L3_ANALYSIS_PLAN_STATUS_CANCELLED,
    L3_ANALYSIS_PLAN_STATUS_FORMED,
    L3_ANALYSIS_PLAN_STATUS_VALUES,
    L3_PASS_RUN_STATUS_COMPLETED,
    L3_PASS_RUN_STATUS_COMPLETED_WITH_WARNINGS,
    L3_PASS_RUN_STATUS_FAILED,
    L3_PASS_RUN_STATUS_PLANNED,
    L3_PASS_RUN_STATUS_RUNNING,
    L3_PASS_RUN_STATUS_SELECTED_NOT_STARTED,
    L3_PASS_RUN_STATUS_VALUES,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3PassRun,
    L3Session,
)
from app.services.layer3_approved_plan_correction import APPROVED_PLAN_APPROVED_STATUS, APPROVED_PLAN_CANCELLED_STATUS
from app.services.layer3_pass_entry import (
    PASS_STATUS_COMPLETED,
    PASS_STATUS_COMPLETED_WITH_WARNINGS,
    PASS_STATUS_FAILED,
    PASS_STATUS_PLANNED,
    PASS_STATUS_RUNNING,
    PASS_STATUS_SELECTED_NOT_STARTED,
    PLAN_STATUS_APPROVED,
    PLAN_STATUS_FORMED,
)


def test_layer3_plan_status_check_constraint_rejects_unknown_status():
    db = _make_session()
    try:
        db.add(L3Session(session_id="session-plan-status", selection_manifest_id="manifest-plan-status"))
        db.commit()

        db.add(
            L3AnalysisPlan(
                session_id="session-plan-status",
                analysis_set_ids_json=[],
                status="draft_created",
                approved_by_operator=False,
                plan_json={},
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()


def test_layer3_pass_run_status_check_constraint_rejects_unknown_status():
    db = _make_session()
    try:
        db.add(L3Session(session_id="session-pass-status", selection_manifest_id="manifest-pass-status"))
        db.add(
            L3AnalysisSet(
                analysis_set_id="set-pass-status",
                session_id="session-pass-status",
                analysis_unit_ids_json=[],
                set_type="single_item",
                formation_basis_json={},
            )
        )
        db.add(
            L3AnalysisPlan(
                analysis_plan_id="plan-pass-status",
                session_id="session-pass-status",
                analysis_set_ids_json=["set-pass-status"],
                status=L3_ANALYSIS_PLAN_STATUS_APPROVED,
                approved_by_operator=True,
                plan_json={},
            )
        )
        db.commit()

        db.add(
            L3PassRun(
                session_id="session-pass-status",
                analysis_plan_id="plan-pass-status",
                analysis_set_id="set-pass-status",
                pass_type="single_item",
                engine_family="wrapped_quantitative_analysis",
                status="waiting_room",
                input_payload_ref="memory://input",
                summary_json={},
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()


def test_layer3_plan_and_pass_status_defaults_and_vocabularies_are_model_owned():
    assert L3_ANALYSIS_PLAN_STATUS_VALUES == ("formed", "approved", "cancelled")
    assert L3_PASS_RUN_STATUS_VALUES == (
        "planned",
        "selected_not_started",
        "running",
        "completed",
        "completed_with_warnings",
        "failed",
    )

    db = _make_session()
    try:
        db.add(L3Session(session_id="session-default-plan", selection_manifest_id="manifest-default-plan"))
        db.add(
            L3AnalysisPlan(
                session_id="session-default-plan",
                analysis_set_ids_json=[],
                approved_by_operator=False,
                plan_json={},
            )
        )
        db.commit()

        plan = db.query(L3AnalysisPlan).one()
        assert plan.status == L3_ANALYSIS_PLAN_STATUS_FORMED

        db.add(
            L3AnalysisSet(
                analysis_set_id="set-planned-pass",
                session_id="session-default-plan",
                analysis_unit_ids_json=[],
                set_type="single_item",
                formation_basis_json={},
            )
        )
        db.add(
            L3PassRun(
                session_id="session-default-plan",
                analysis_plan_id=plan.analysis_plan_id,
                analysis_set_id="set-planned-pass",
                pass_type="single_item",
                engine_family="wrapped_quantitative_analysis",
                status=L3_PASS_RUN_STATUS_PLANNED,
                input_payload_ref="memory://input",
                summary_json={},
            )
        )
        db.commit()
    finally:
        db.close()


def test_layer3_plan_and_pass_status_vocabularies_match_owner_services():
    assert L3_ANALYSIS_PLAN_STATUS_VALUES == (
        PLAN_STATUS_FORMED,
        PLAN_STATUS_APPROVED,
        APPROVED_PLAN_CANCELLED_STATUS,
    )
    assert L3_ANALYSIS_PLAN_STATUS_FORMED == PLAN_STATUS_FORMED
    assert L3_ANALYSIS_PLAN_STATUS_APPROVED == PLAN_STATUS_APPROVED
    assert L3_ANALYSIS_PLAN_STATUS_APPROVED == APPROVED_PLAN_APPROVED_STATUS
    assert L3_ANALYSIS_PLAN_STATUS_CANCELLED == APPROVED_PLAN_CANCELLED_STATUS

    assert L3_PASS_RUN_STATUS_VALUES == (
        PASS_STATUS_PLANNED,
        PASS_STATUS_SELECTED_NOT_STARTED,
        PASS_STATUS_RUNNING,
        PASS_STATUS_COMPLETED,
        PASS_STATUS_COMPLETED_WITH_WARNINGS,
        PASS_STATUS_FAILED,
    )
    assert L3_PASS_RUN_STATUS_PLANNED == PASS_STATUS_PLANNED
    assert L3_PASS_RUN_STATUS_SELECTED_NOT_STARTED == PASS_STATUS_SELECTED_NOT_STARTED
    assert L3_PASS_RUN_STATUS_RUNNING == PASS_STATUS_RUNNING
    assert L3_PASS_RUN_STATUS_COMPLETED == PASS_STATUS_COMPLETED
    assert L3_PASS_RUN_STATUS_COMPLETED_WITH_WARNINGS == PASS_STATUS_COMPLETED_WITH_WARNINGS
    assert L3_PASS_RUN_STATUS_FAILED == PASS_STATUS_FAILED


def test_layer3_pass_entry_migration_defines_plan_and_pass_status_constraints(monkeypatch):
    spec = importlib.util.spec_from_file_location("layer3_pass_entry_migration", PASS_ENTRY_MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    created_tables = []

    def capture_create_table(name, *elements):
        created_tables.append((name, elements))

    monkeypatch.setattr(module, "create_table_idempotent", capture_create_table)
    module.upgrade()

    plan_constraint_sql = _constraint_sql(created_tables, "l3_analysis_plan", "ck_l3_analysis_plan_status")
    assert "status IN" in plan_constraint_sql
    for status in L3_ANALYSIS_PLAN_STATUS_VALUES:
        assert status in plan_constraint_sql

    pass_constraint_sql = _constraint_sql(created_tables, "l3_pass_run", "ck_l3_pass_run_status")
    assert "status IN" in pass_constraint_sql
    for status in L3_PASS_RUN_STATUS_VALUES:
        assert status in pass_constraint_sql


def _constraint_sql(created_tables, table_name: str, constraint_name: str) -> str:
    table_elements = next(elements for name, elements in created_tables if name == table_name)
    constraints = [element for element in table_elements if isinstance(element, CheckConstraint)]
    constraint = next(element for element in constraints if element.name == constraint_name)
    return str(constraint.sqltext)


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()
