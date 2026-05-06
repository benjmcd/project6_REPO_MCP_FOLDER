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
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
    L3TypingRecord,
)
from app.services import layer3_sublayer_state as sublayer_state
from app.services import layer3_workbench
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_TYPE_ASSOCIATED_COHORT,
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


def test_snapshot_projection_reports_unsupported_shape_without_side_effects() -> None:
    snapshot = L3MaterialSnapshot(
        material_snapshot_id="snapshot-unsupported",
        session_id="session-sublayer-unsupported",
        descriptor_id="descriptor-unsupported",
        source_plane="runtime",
        source_shape="unsupported-shape",
        payload_ref="payload://unsupported",
        payload_hash="hash-unsupported",
        source_identity_json={},
        source_provenance_json={},
        load_summary_json={},
    )

    projection, unsupported = sublayer_state.snapshot_projection(snapshot)

    assert projection is None
    assert unsupported == {
        "material_snapshot_id": "snapshot-unsupported",
        "owner_service_source_shape": "unsupported-shape",
        "reason": "unsupported_typing_shape",
    }
    assert layer3_workbench._snapshot_projection(snapshot) == (projection, unsupported)


def test_session_sublayer_visualization_state_preserves_workbench_projection(db_session) -> None:
    session_id = "session-sublayer-state"
    snapshot_id = "snapshot-sublayer-state"
    typing_record_id = "typing-sublayer-state"
    unit_id = "unit-sublayer-state"
    group_id = "group-sublayer-state"
    set_id = "set-sublayer-state"
    plan_id = "plan-sublayer-state"
    pass_run_id = "pass-run-sublayer-state"
    db_session.add_all(
        [
            L3Session(
                session_id=session_id,
                selection_manifest_id="manifest-sublayer-state",
                operator_context_json={},
                summary_json={},
            ),
            L3MaterialSnapshot(
                material_snapshot_id=snapshot_id,
                session_id=session_id,
                descriptor_id="descriptor-sublayer-state",
                source_plane="runtime",
                source_shape="dataset_version",
                payload_ref="payload://dataset-version",
                payload_hash="hash-dataset-version",
                source_identity_json={"dataset_version_id": "dv-sublayer-state"},
                source_provenance_json={},
                load_summary_json={"row_count": 10},
            ),
            L3TypingRecord(
                typing_record_id=typing_record_id,
                session_id=session_id,
                material_snapshot_id=snapshot_id,
                candidate_modalities_json=["quantitative"],
                chosen_modality="quantitative",
                typing_basis_json={
                    "source_shape": "dataset_version",
                    "planning_shape_family": "tabular_numeric",
                },
                confidence=1.0,
            ),
            L3AnalysisUnit(
                analysis_unit_id=unit_id,
                session_id=session_id,
                unit_kind="material_snapshot",
                analysis_modality="quantitative",
                member_snapshot_ids_json=[snapshot_id],
                member_ranges_json=[],
                must_remain_intact=True,
                typing_record_ids_json=[typing_record_id],
                unit_hash="unit-hash-sublayer-state",
                summary_json={},
            ),
            L3AnalysisGroup(
                analysis_group_id=group_id,
                session_id=session_id,
                analysis_modality="quantitative",
                typing_basis_json={"basis": "test"},
                analysis_unit_ids_json=[unit_id],
                status="formed",
            ),
            L3AnalysisSet(
                analysis_set_id=set_id,
                session_id=session_id,
                analysis_group_ids_json=[group_id],
                analysis_unit_ids_json=[unit_id],
                set_type="associated_cohort",
                formation_basis_json={"analysis_modality": "quantitative"},
            ),
            L3AnalysisPlan(
                analysis_plan_id=plan_id,
                session_id=session_id,
                analysis_set_ids_json=[set_id],
                status=PLAN_STATUS_APPROVED,
                approved_by_operator=True,
                approved_at=datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc),
                plan_json={
                    "approval_only": False,
                    "execution_started": True,
                    "approved_sets_json": [{"analysis_set_id": set_id}],
                    "planned_passes_json": [{"pass_run_id": pass_run_id}],
                    "source_preview_id": "preview-sublayer-state",
                    "source_preview_hash": "hash-preview-sublayer-state",
                },
            ),
            L3PassRun(
                pass_run_id=pass_run_id,
                session_id=session_id,
                analysis_plan_id=plan_id,
                analysis_set_id=set_id,
                pass_type=PASS_TYPE_ASSOCIATED_COHORT,
                engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
                status=PASS_STATUS_COMPLETED,
                input_payload_ref="payload://input",
                output_payload_ref="payload://output",
                summary_json={
                    "analysis_run_id": "analysis-run-sublayer-state",
                    "selected_method_name": "decomposition",
                    "pass_scope": "quant_associated_cohort",
                },
            ),
        ]
    )
    db_session.commit()

    state = sublayer_state.session_sublayer_visualization_state(db_session, session_id=session_id)

    assert state == layer3_workbench._session_sublayer_visualization_state(
        db_session,
        session_id=session_id,
    )
    assert state["schema_id"] == sublayer_state.SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID
    assert state["authority_source"] == "read_only_persisted_layer3_rows"
    assert state["no_side_effects"] is True
    assert state["material_objects"][0]["source_identity"]["dataset_version_id"] == "dv-sublayer-state"
    assert state["typing_records"][0]["payload_hash"] == "hash-dataset-version"
    assert state["analysis_units"][0]["analysis_unit_id"] == unit_id
    assert state["analysis_sets"][0]["member_snapshot_ids"] == [snapshot_id]
    assert state["latest_plan"]["analysis_plan_id"] == plan_id
    assert state["latest_plan"]["planned_passes"] == [{"pass_run_id": pass_run_id}]
    assert state["pass_runs"][0]["analysis_run_id"] == "analysis-run-sublayer-state"
