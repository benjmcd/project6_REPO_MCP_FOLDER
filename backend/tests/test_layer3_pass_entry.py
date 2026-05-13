from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.db.session import Base
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    Dataset,
    DatasetVersion,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3OutputPackage,
    L3PassRun,
    L3Session,
    VariableDefinition,
    VariableProfile,
)
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services.dataframe_io import load_version_dataframe
from app.services.layer3_pass_entry import (
    Layer3PassEntryError,
    approve_pass_entry_plan,
    execute_selected_pass_run,
    materialize_pass_entry,
    preview_pass_entry,
)
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_source_boundary import SOURCE_INTAKE_GATE_B_SOURCE_CLASS
from app.services.layer3_typing_entry import materialize_typing_entry


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def _utc_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def _utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _seed_dataset_version(db, tmp_path: Path, *, dataset_id: str, dataset_version_id: str) -> None:
    _seed_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )


def _seed_timeseries_dataset_version(
    db,
    tmp_path: Path,
    *,
    dataset_id: str,
    dataset_version_id: str,
    start: str = "2020-01-01",
    periods: int = 24,
    freq: str = "MS",
    measure_name: str = "value",
    values: list[float] | None = None,
) -> None:
    dataset = Dataset(
        dataset_id=dataset_id,
        name=f"Dataset {dataset_id}",
        description="Gate C pass-entry proof dataset",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="v1",
        version_type="baseline",
        status="ready",
        notes="gatec-pass-entry-proof",
    )
    observed_at = VariableDefinition(
        variable_id=f"var-time-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_name="observed_at",
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id=f"var-value-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_name=measure_name,
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    value_profile = VariableProfile(
        variable_profile_id=f"profile-value-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_id=value.variable_id,
        seasonality_flag=True,
        stationarity_hint="likely_stationary",
        summary_json={},
    )
    db.add_all([dataset, version, observed_at, value, value_profile])
    db.flush()

    series_values = values or [100 + ((index % 12) * 2) + (index // 12) for index in range(periods)]
    frame = pd.DataFrame(
        {
            "observed_at": pd.date_range(start, periods=periods, freq=freq, tz="UTC"),
            measure_name: series_values,
        }
    )
    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    frame.to_csv(csv_path, index=False)
    version.storage_ref = str(csv_path)
    version.row_count = len(frame)
    db.flush()


def _seed_non_timeseries_dataset_version(db, tmp_path: Path, *, dataset_id: str, dataset_version_id: str) -> None:
    dataset = Dataset(
        dataset_id=dataset_id,
        name=f"Dataset {dataset_id}",
        description="Gate C unsupported-method proof dataset",
        frequency_hint="MS",
        time_column=None,
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="v1",
        version_type="baseline",
        status="ready",
        notes="gatec-pass-entry-unsupported-method-proof",
    )
    category = VariableDefinition(
        variable_id=f"var-category-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_name="category",
        dtype="string",
        role="dimension",
        is_numeric=False,
        is_time_index=False,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id=f"var-value-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_name="value",
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    value_profile = VariableProfile(
        variable_profile_id=f"profile-value-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_id=value.variable_id,
        seasonality_flag=False,
        stationarity_hint="likely_stationary",
        summary_json={},
    )
    db.add_all([dataset, version, category, value, value_profile])
    db.flush()

    frame = pd.DataFrame(
        {
            "category": ["alpha", "beta", "gamma"],
            "value": [1.0, 2.5, 3.5],
        }
    )
    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    frame.to_csv(csv_path, index=False)
    version.storage_ref = str(csv_path)
    version.row_count = len(frame)
    db.flush()


def _build_quant_ready_session(db, tmp_path: Path) -> tuple[str, str, datetime]:
    dataset_version_id = "dv-pass-001"
    _seed_dataset_version(db, tmp_path, dataset_id="ds-pass-001", dataset_version_id=dataset_version_id)

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-pass-quant"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="gatec-pass-entry-quant-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c_pass"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": "ds-pass-001", "storage_ref": str(tmp_path / "datasets" / f"{dataset_version_id}.csv")},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    phase1a_status = session.status
    phase1a_completed_at = session.completed_at
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id, phase1a_status, phase1a_completed_at


def _build_quant_cohort_ready_session(
    db,
    tmp_path: Path,
    *,
    second_start: str = "2020-01-01",
    requested_method_name: str | None = None,
) -> tuple[str, str, datetime]:
    _seed_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id="ds-cohort-001",
        dataset_version_id="dv-cohort-001",
        values=[50 + index for index in range(24)],
    )
    _seed_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id="ds-cohort-002",
        dataset_version_id="dv-cohort-002",
        start=second_start,
        values=[150 + (index * 2) for index in range(24)],
    )

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"selection_group": "sel-pass-cohort"},
                "selection_basis": {"selection_id": "sel-pass-cohort"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="gatec-pass-entry-cohort-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c_pass"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": "dv-cohort-001"},
                source_provenance={
                    "dataset_id": "ds-cohort-001",
                    "storage_ref": str(tmp_path / "datasets" / "dv-cohort-001.csv"),
                },
                payload={"dataset_version_id": "dv-cohort-001"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": "dv-cohort-002"},
                source_provenance={
                    "dataset_id": "ds-cohort-002",
                    "storage_ref": str(tmp_path / "datasets" / "dv-cohort-002.csv"),
                },
                payload={"dataset_version_id": "dv-cohort-002"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    phase1a_status = session.status
    phase1a_completed_at = session.completed_at
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    if requested_method_name is not None:
        associated_set = (
            db.query(L3AnalysisSet)
            .filter(
                L3AnalysisSet.session_id == session.session_id,
                L3AnalysisSet.set_type == "associated_cohort",
            )
            .one()
        )
        associated_set.formation_basis_json = {
            **associated_set.formation_basis_json,
            "requested_method_name": requested_method_name,
        }
    db.commit()
    return session.session_id, phase1a_status, phase1a_completed_at


def _build_mixed_ready_session(db, tmp_path: Path) -> tuple[str, str, datetime]:
    dataset_version_id = "dv-pass-002"
    _seed_dataset_version(db, tmp_path, dataset_id="ds-pass-002", dataset_version_id=dataset_version_id)

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-pass-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": "run-qual-001", "target_id": "target-qual-001"},
                "selection_basis": {"selection_id": "sel-pass-qual"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="gatec-pass-entry-mixed-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c_pass"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": "ds-pass-002", "storage_ref": str(tmp_path / "datasets" / f"{dataset_version_id}.csv")},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": "doc-pass-001"},
                source_provenance={"linkage_ref": "aps/linkage/doc-pass-001"},
                payload={"content": "qualitative document one"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": "doc-pass-002"},
                source_provenance={"linkage_ref": "aps/linkage/doc-pass-002"},
                payload={"content": "qualitative document two"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    phase1a_status = session.status
    phase1a_completed_at = session.completed_at
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id, phase1a_status, phase1a_completed_at


def _build_qual_only_ready_session(db, tmp_path: Path) -> tuple[str, str, datetime]:
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": "run-qual-only-001", "target_id": "target-qual-only-001"},
                "selection_basis": {"selection_id": "sel-pass-qual-only"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_b": ["aps_content_document"]},
        commit_reason="gatec-pass-entry-qual-only-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c_pass"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": "doc-qual-only-001"},
                source_provenance={"linkage_ref": "aps/linkage/doc-qual-only-001"},
                payload={"content": "qualitative one"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": "doc-qual-only-002"},
                source_provenance={"linkage_ref": "aps/linkage/doc-qual-only-002"},
                payload={"content": "qualitative two"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    phase1a_status = session.status
    phase1a_completed_at = session.completed_at
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id, phase1a_status, phase1a_completed_at


def _build_source_intake_plan_preview_session(db, tmp_path: Path) -> tuple[str, str, datetime]:
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_source_intake",
                "descriptor_type": SOURCE_INTAKE_GATE_B_SOURCE_CLASS,
                "selector_payload": {
                    "candidate_id": "mat-source_intake_record-src-intake-plan-001",
                    "source_ref": "source_intake_record:src-intake-plan-001",
                    "source_intake_record_id": "src-intake-plan-001",
                },
                "selection_basis": {
                    "selection_id": "sel-source-intake-plan",
                    "gate_b_decision": "approved",
                },
                "expansion_reason": "gate_b_approved_material",
            }
        ],
        source_plane_hints={"source_classes": [SOURCE_INTAKE_GATE_B_SOURCE_CLASS]},
        commit_reason="source-intake-plan-preview-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "source_intake_plan_preview"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="gate_b_approved_preview_material",
        loaded_materials=[
            SnapshotMaterial(
                source_shape=SOURCE_INTAKE_GATE_B_SOURCE_CLASS,
                source_identity={
                    "candidate_id": "mat-source_intake_record-src-intake-plan-001",
                    "source_class": SOURCE_INTAKE_GATE_B_SOURCE_CLASS,
                    "source_intake_record_id": "src-intake-plan-001",
                    "content_sha256": "a" * 64,
                    "metadata_hash": "b" * 64,
                },
                source_provenance={
                    "source_ref": "source_intake_record:src-intake-plan-001",
                    "query_basis": "operator_uploaded_source_intake",
                    "provenance_ref": "layer3-source-intake",
                },
                payload={"text_preview": "operator uploaded source-intake text"},
                load_summary={"loaded_records": 1, "failed_records": 0, "preview_material": True},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    phase1a_status = session.status
    phase1a_completed_at = session.completed_at
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id, phase1a_status, phase1a_completed_at


def _build_non_timeseries_quant_ready_session(db, tmp_path: Path) -> tuple[str, str, datetime]:
    dataset_version_id = "dv-pass-003"
    _seed_non_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id="ds-pass-003",
        dataset_version_id=dataset_version_id,
    )

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-pass-unsupported-method"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="gatec-pass-entry-unsupported-method-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c_pass"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": "ds-pass-003", "storage_ref": str(tmp_path / "datasets" / f"{dataset_version_id}.csv")},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    phase1a_status = session.status
    phase1a_completed_at = session.completed_at
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id, phase1a_status, phase1a_completed_at


def test_gatec_pass_entry_preview_is_read_only_for_quantitative_single_item(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_ready_session(db, tmp_path)

        preview = preview_pass_entry(db, session_id=session_id)

        assert preview.session_id == session_id
        assert len(preview.admitted_sets) == 1
        assert preview.admitted_sets[0]["readiness"] == "admitted"
        assert preview.admitted_sets[0]["analysis_modality"] == "quantitative"
        assert preview.planned_passes[0]["pass_type"] == "single_item"
        assert preview.planned_passes[0]["pass_scope"] == "quantitative_single_item_dataset_version"
        assert preview.planned_passes[0]["execution_status"] == "not_started"
        assert preview.owner_service_basis["mode"] == "read_only_preview"
        assert preview.owner_service_basis["preview_hash_schema_id"] == "layer3.plan_preview_hash.v1"
        assert preview.owner_plan_payload["plan_version"] == "gatec_pass_entry_v1"

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_preview_reports_exclusions_without_materializing(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_mixed_ready_session(db, tmp_path)

        preview = preview_pass_entry(db, session_id=session_id)

        assert len(preview.admitted_sets) == 1
        assert len(preview.excluded_sets) == 1
        assert preview.excluded_sets[0]["reason_code"] == "cohort_not_quantitative"
        assert preview.warnings[0]["reason_code"] == "partial_plan_preview"
        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_preview_admits_source_intake_without_materializing_downstream(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_source_intake_plan_preview_session(db, tmp_path)

        preview = preview_pass_entry(db, session_id=session_id)
        repeated_preview = preview_pass_entry(db, session_id=session_id)

        assert preview.preview_hash == repeated_preview.preview_hash
        assert len(preview.admitted_sets) == 1
        assert preview.excluded_sets == ()
        assert preview.admitted_sets[0]["readiness"] == "admitted"
        assert preview.admitted_sets[0]["analysis_modality"] == "qualitative"
        assert preview.admitted_sets[0]["source_summary"]["source_classes"] == [SOURCE_INTAKE_GATE_B_SOURCE_CLASS]

        planned_pass = preview.planned_passes[0]
        assert planned_pass["pass_type"] == "single_item"
        assert planned_pass["pass_scope"] == "qualitative_single_item_operator_uploaded_source"
        assert planned_pass["engine_family"] == "source_intake_qualitative_preview"
        assert planned_pass["selected_method_name"] == "operator_uploaded_source_review_preview"
        assert preview.owner_plan_payload["formation_reason"] == "source_intake_qualitative_plan_preview"
        assert preview.owner_plan_payload["source_gate"] == "299_SOURCE_INTAKE_PLAN_PREVIEW_BOUNDARY_FREEZE"
        owner_planned_pass = preview.owner_plan_payload["planned_passes_json"][0]
        assert owner_planned_pass["source_gate"] == "299_SOURCE_INTAKE_PLAN_PREVIEW_BOUNDARY_FREEZE"
        assert owner_planned_pass["source_intake_record_id"] == "src-intake-plan-001"
        assert owner_planned_pass["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_source_intake_plan_approval_remains_blocked(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_source_intake_plan_preview_session(db, tmp_path)

        preview = preview_pass_entry(db, session_id=session_id)
        with pytest.raises(Layer3PassEntryError, match="source-intake plan approval is not admitted"):
            approve_pass_entry_plan(
                db,
                session_id=session_id,
                preview_hash=preview.preview_hash,
                source_preview_id="source-intake-plan-preview",
            )

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_approves_plan_without_execution(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_ready_session(db, tmp_path)

        preview = preview_pass_entry(db, session_id=session_id)
        result = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview.preview_hash,
            source_preview_id="plan-preview-test",
        )
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        session = db.get(L3Session, session_id)

        assert result.analysis_plan.analysis_plan_id == stored_plan.analysis_plan_id
        assert result.source_preview_hash == preview.preview_hash
        assert result.approved_sets[0]["readiness"] == "approved"
        assert result.planned_passes[0]["execution_status"] == "not_started"
        assert result.owner_service_basis["mode"] == "operator_approved_plan_only"
        assert stored_plan.status == "approved"
        assert stored_plan.approved_by_operator is True
        assert stored_plan.approved_at is not None
        assert stored_plan.plan_json["approval_only"] is True
        assert stored_plan.plan_json["execution_started"] is False
        assert stored_plan.plan_json["source_preview_id"] == "plan-preview-test"
        assert stored_plan.plan_json["source_preview_hash"] == preview.preview_hash
        assert stored_plan.plan_json["approved_sets_json"][0]["readiness"] == "approved"
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert session.summary_json["plan_approval"]["analysis_plan_id"] == stored_plan.analysis_plan_id
        assert session.summary_json["plan_approval"]["approval_only"] is True
        assert session.summary_json["plan_approval"]["execution_started"] is False
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_approval_rejects_stale_preview_hash(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_ready_session(db, tmp_path)

        with pytest.raises(Layer3PassEntryError, match="preview hash mismatch"):
            approve_pass_entry_plan(
                db,
                session_id=session_id,
                preview_hash="stale-preview-hash",
                source_preview_id="plan-preview-test",
            )

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_executes_quantitative_single_item_and_preserves_loading_closure(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_ready_session(db, tmp_path)

        result = materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        session = db.get(L3Session, session_id)

        assert result.analysis_plan.analysis_plan_id == stored_plan.analysis_plan_id
        assert len(result.pass_runs) == 1
        assert result.pass_runs[0].pass_run_id == stored_pass.pass_run_id

        assert stored_plan.analysis_set_ids_json == [stored_pass.analysis_set_id]
        assert stored_plan.status == "formed"
        assert stored_plan.approved_by_operator is False
        assert stored_plan.approved_at is None
        assert stored_plan.plan_json["plan_version"] == "gatec_pass_entry_v1"
        assert len(stored_plan.plan_json["planned_passes_json"]) == 1
        assert stored_plan.plan_json["excluded_sets_json"] == []

        assert stored_pass.pass_type == "single_item"
        assert stored_pass.engine_family == "wrapped_quantitative_analysis"
        assert stored_pass.status in {"completed", "completed_with_warnings"}
        assert stored_pass.input_payload_ref
        assert stored_pass.output_payload_ref
        assert Path(stored_pass.output_payload_ref).exists()
        assert Path(stored_pass.output_payload_ref).parent == (Path(tmp_path) / "artifacts" / "layer3")
        assert stored_pass.summary_json["dataset_version_id"] == "dv-pass-001"
        assert stored_pass.summary_json["selected_method_name"] == "decomposition"
        assert stored_pass.summary_json["analysis_run_id"]
        assert stored_pass.summary_json["pass_scope"] == "quantitative_single_item_dataset_version"

        assert db.query(AnalysisRun).count() == 1

        preserved = session.summary_json["phase1a_loading_closure"]
        assert preserved["status"] == phase1a_status
        assert preserved["completed_at"] == _utc_isoformat(phase1a_completed_at)
        assert session.summary_json["pass_entry"]["analysis_plan_id"] == stored_plan.analysis_plan_id
        assert session.summary_json["pass_entry"]["excluded_set_count"] == 0
        assert session.status == "completed"
        assert session.completed_at is not None
        assert _utc_datetime(session.completed_at) > _utc_datetime(phase1a_completed_at)
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_excludes_qualitative_sets_but_runs_quantitative_single_item(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_mixed_ready_session(db, tmp_path)

        result = materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        session = db.get(L3Session, session_id)

        assert len(result.pass_runs) == 1
        assert len(stored_plan.analysis_set_ids_json) == 1
        assert len(stored_plan.plan_json["planned_passes_json"]) == 1
        assert len(stored_plan.plan_json["excluded_sets_json"]) == 1
        excluded = stored_plan.plan_json["excluded_sets_json"][0]
        assert excluded["reason_code"] == "cohort_not_quantitative"
        assert excluded["analysis_modality"] == "qualitative"
        assert excluded["set_type"] == "associated_cohort"
        assert stored_plan.plan_json["source_gate"] == "06_GATEC_PASS_FREEZE"

        assert stored_pass.summary_json["dataset_version_id"] == "dv-pass-002"
        assert stored_pass.summary_json["analysis_run_id"]
        assert db.query(AnalysisRun).count() == 1

        preserved = session.summary_json["phase1a_loading_closure"]
        assert preserved["status"] == phase1a_status
        assert preserved["completed_at"] == _utc_isoformat(phase1a_completed_at)
        assert session.summary_json["pass_entry"]["excluded_set_count"] == 1
        assert session.status == "completed_with_warnings"
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_executes_quantitative_associated_cohort_with_shaped_manifest(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_cohort_ready_session(db, tmp_path)

        result = materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        session = db.get(L3Session, session_id)

        assert result.analysis_plan.analysis_plan_id == stored_plan.analysis_plan_id
        assert len(result.pass_runs) == 1
        assert stored_plan.plan_json["source_gate"] == "07_GATEC_COHORT_FREEZE"
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        assert planned_pass["set_type"] == "associated_cohort"
        assert planned_pass["pass_type"] == "associated_cohort"
        assert planned_pass["pass_scope"] == "quantitative_associated_cohort_dataset_version"
        assert planned_pass["selected_method_name"] == "cross_correlation"
        assert planned_pass["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]

        assert stored_pass.pass_type == "associated_cohort"
        assert stored_pass.status in {"completed", "completed_with_warnings"}
        assert stored_pass.input_payload_ref
        assert Path(stored_pass.input_payload_ref).exists()
        assert Path(stored_pass.input_payload_ref).parent == (Path(tmp_path) / "artifacts" / "layer3")
        assert stored_pass.summary_json["pass_scope"] == "quantitative_associated_cohort_dataset_version"
        assert stored_pass.summary_json["selected_method_name"] == "cross_correlation"
        assert stored_pass.summary_json["analysis_run_id"]
        assert stored_pass.summary_json["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]
        assert len(stored_pass.summary_json["column_map_json"]) == 2

        input_manifest = json.loads(Path(stored_pass.input_payload_ref).read_text(encoding="utf-8"))
        assert input_manifest["analysis_set_id"] == stored_pass.analysis_set_id
        assert input_manifest["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]
        assert input_manifest["time_column"] == "observed_at"
        assert input_manifest["row_count"] == 24
        assert input_manifest["column_map_json"] == stored_pass.summary_json["column_map_json"]
        assert all(entry["source_variable_name"] == "value" for entry in input_manifest["column_map_json"])

        derived_dataset_version_id = stored_pass.summary_json["derived_dataset_version_id"]
        assert derived_dataset_version_id == input_manifest["derived_dataset_version_id"]
        derived_version = db.get(DatasetVersion, derived_dataset_version_id)
        assert derived_version is not None
        assert derived_version.storage_ref
        assert Path(derived_version.storage_ref).exists()

        derived_frame = load_version_dataframe(db, derived_dataset_version_id)
        derived_column_names = [entry["column_name"] for entry in stored_pass.summary_json["column_map_json"]]
        assert derived_frame.columns.tolist() == ["observed_at", *derived_column_names]
        assert len(derived_frame) == 24

        assert db.query(DatasetVersion).count() == 3
        assert db.query(AnalysisRun).count() == 1

        preserved = session.summary_json["phase1a_loading_closure"]
        assert preserved["status"] == phase1a_status
        assert preserved["completed_at"] == _utc_isoformat(phase1a_completed_at)
        assert session.summary_json["pass_entry"]["analysis_plan_id"] == stored_plan.analysis_plan_id
        assert session.summary_json["pass_entry"]["excluded_set_count"] == 0
        assert session.summary_json["pass_entry"]["source_gate"] == "07_GATEC_COHORT_FREEZE"
        assert session.status in {"completed", "completed_with_warnings"}
        assert session.completed_at is not None
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_executes_explicit_descriptive_summary_associated_cohort(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            requested_method_name="descriptive_summary",
        )

        result = materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        session = db.get(L3Session, session_id)

        assert result.analysis_plan.analysis_plan_id == stored_plan.analysis_plan_id
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        assert planned_pass["set_type"] == "associated_cohort"
        assert planned_pass["pass_type"] == "associated_cohort"
        assert planned_pass["pass_scope"] == "quantitative_associated_cohort_dataset_version"
        assert planned_pass["selected_method_name"] == "descriptive_summary"
        assert planned_pass["source_gate"] == "78_COHORT_FREEZE"
        assert planned_pass["cohort_shape"] == "aligned_wide_table"
        assert planned_pass["requested_method_name"] == "descriptive_summary"
        assert (
            planned_pass["requested_method_source"]
            == "analysis_set.formation_basis_json.requested_method_name"
        )
        assert stored_plan.plan_json["source_gate"] == "78_COHORT_FREEZE"

        assert stored_pass.pass_type == "associated_cohort"
        assert stored_pass.status in {"completed", "completed_with_warnings"}
        assert stored_pass.summary_json["selected_method_name"] == "descriptive_summary"
        assert stored_pass.summary_json["source_gate"] == "78_COHORT_FREEZE"
        assert stored_pass.summary_json["cohort_shape"] == "aligned_wide_table"
        assert stored_pass.summary_json["requested_method_name"] == "descriptive_summary"
        assert (
            stored_pass.summary_json["requested_method_source"]
            == "analysis_set.formation_basis_json.requested_method_name"
        )
        assert stored_pass.summary_json["artifact_types_json"] == ["descriptive_summary_result"]
        assert stored_pass.summary_json["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]
        assert all(entry["source_variable_name"] == "value" for entry in stored_pass.summary_json["column_map_json"])

        input_manifest = json.loads(Path(stored_pass.input_payload_ref).read_text(encoding="utf-8"))
        assert input_manifest["source_gate"] == "78_COHORT_FREEZE"
        assert input_manifest["selected_method_name"] == "descriptive_summary"
        assert input_manifest["cohort_shape"] == "aligned_wide_table"
        assert input_manifest["requested_method_name"] == "descriptive_summary"
        assert all(entry["source_variable_name"] == "value" for entry in input_manifest["column_map_json"])

        output_manifest = json.loads(Path(stored_pass.output_payload_ref).read_text(encoding="utf-8"))
        assert output_manifest["source_gate"] == "78_COHORT_FREEZE"
        assert output_manifest["selected_method_name"] == "descriptive_summary"
        assert output_manifest["artifact_types_json"] == ["descriptive_summary_result"]
        assert output_manifest["cohort_shape"] == "aligned_wide_table"
        assert output_manifest["requested_method_name"] == "descriptive_summary"
        assert all(entry["source_variable_name"] == "value" for entry in output_manifest["column_map_json"])

        analysis_run = db.query(AnalysisRun).one()
        assert analysis_run.method_name == "descriptive_summary"
        assert db.query(DatasetVersion).count() == 3
        preserved = session.summary_json["phase1a_loading_closure"]
        assert preserved["status"] == phase1a_status
        assert preserved["completed_at"] == _utc_isoformat(phase1a_completed_at)
        assert session.summary_json["pass_entry"]["source_gate"] == "78_COHORT_FREEZE"
        assert session.summary_json["pass_entry"]["excluded_set_count"] == 0
        assert session.status in {"completed", "completed_with_warnings"}
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_preserves_cross_correlation_for_non_descriptive_cohort_request(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _, _ = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            requested_method_name="cross_correlation",
        )

        materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        assert planned_pass["selected_method_name"] == "cross_correlation"
        assert planned_pass["source_gate"] == "07_GATEC_COHORT_FREEZE"
        assert "requested_method_name" not in planned_pass
        assert stored_pass.summary_json["selected_method_name"] == "cross_correlation"
        assert stored_pass.summary_json["source_gate"] == "07_GATEC_COHORT_FREEZE"
        assert "requested_method_name" not in stored_pass.summary_json
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_preserves_cross_correlation_for_malformed_descriptive_cohort_request(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _, _ = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            requested_method_name=" descriptive_summary ",
        )

        materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        assert planned_pass["selected_method_name"] == "cross_correlation"
        assert planned_pass["source_gate"] == "07_GATEC_COHORT_FREEZE"
        assert "requested_method_name" not in planned_pass
        assert stored_pass.summary_json["selected_method_name"] == "cross_correlation"
        assert stored_pass.summary_json["source_gate"] == "07_GATEC_COHORT_FREEZE"
        assert "requested_method_name" not in stored_pass.summary_json
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_selected_pass_execution_runs_descriptive_summary_associated_cohort(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _, _ = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            requested_method_name="descriptive_summary",
        )

        preview = preview_pass_entry(db, session_id=session_id)
        approval = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview.preview_hash,
            source_preview_id="cohort-selected-pass-preview",
        )
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        pass_run = L3PassRun(
            pass_run_id="pass-run-cohort-selected",
            session_id=session_id,
            analysis_plan_id=approval.analysis_plan.analysis_plan_id,
            analysis_set_id=planned_pass["analysis_set_id"],
            pass_type="associated_cohort",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            started_at=None,
            completed_at=None,
            input_payload_ref="selected-cohort-input-ref",
            output_payload_ref=None,
            summary_json={
                "schema_id": "layer3.pass_run_shell_summary.v1",
                "analysis_plan_id": approval.analysis_plan.analysis_plan_id,
                "source_preview_id": "cohort-selected-pass-preview",
                "source_preview_hash": preview.preview_hash,
                "planned_pass": dict(planned_pass),
                "execution_started": False,
                "analysis_run_id": None,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(pass_run)
        db.flush()

        result = execute_selected_pass_run(
            db,
            pass_run=pass_run,
            planned_pass=planned_pass,
            client_request_id="cohort-selected-start",
        )
        db.commit()

        stored_pass = db.get(L3PassRun, pass_run.pass_run_id)
        assert result.execution_started is True
        assert result.selected_method_name == "descriptive_summary"
        assert result.dataset_version_id
        assert result.analysis_run_id
        assert stored_pass.status in {"completed", "completed_with_warnings"}
        assert stored_pass.pass_type == "associated_cohort"
        assert stored_pass.input_payload_ref
        assert Path(stored_pass.input_payload_ref).exists()
        assert stored_pass.summary_json["pass_scope"] == "quantitative_associated_cohort_dataset_version"
        assert stored_pass.summary_json["selected_method_name"] == "descriptive_summary"
        assert stored_pass.summary_json["requested_method_name"] == "descriptive_summary"
        assert (
            stored_pass.summary_json["requested_method_source"]
            == "analysis_set.formation_basis_json.requested_method_name"
        )
        assert stored_pass.summary_json["cohort_shape"] == "aligned_wide_table"
        assert stored_pass.summary_json["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]
        assert len(stored_pass.summary_json["column_map_json"]) == 2
        assert stored_pass.summary_json["analysis_execution_start"]["client_request_id"] == "cohort-selected-start"

        input_manifest = json.loads(Path(stored_pass.input_payload_ref).read_text(encoding="utf-8"))
        assert input_manifest["selected_method_name"] == "descriptive_summary"
        assert input_manifest["requested_method_name"] == "descriptive_summary"
        assert input_manifest["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]

        output_manifest = json.loads(Path(stored_pass.output_payload_ref).read_text(encoding="utf-8"))
        assert output_manifest["selected_method_name"] == "descriptive_summary"
        assert output_manifest["artifact_types_json"] == ["descriptive_summary_result"]
        assert output_manifest["requested_method_name"] == "descriptive_summary"
        assert db.query(AnalysisRun).one().method_name == "descriptive_summary"
        assert db.query(DatasetVersion).count() == 3
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_selected_pass_execution_rejects_malformed_cohort_method_metadata(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _, _ = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            requested_method_name="descriptive_summary",
        )

        preview = preview_pass_entry(db, session_id=session_id)
        approval = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview.preview_hash,
            source_preview_id="cohort-selected-pass-preview",
        )
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        planned_pass = dict(stored_plan.plan_json["planned_passes_json"][0])
        planned_pass["requested_method_name"] = " descriptive_summary "
        pass_run = L3PassRun(
            pass_run_id="pass-run-cohort-selected-malformed",
            session_id=session_id,
            analysis_plan_id=approval.analysis_plan.analysis_plan_id,
            analysis_set_id=planned_pass["analysis_set_id"],
            pass_type="associated_cohort",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            started_at=None,
            completed_at=None,
            input_payload_ref="layer3://execution-selection/pass-run-cohort-selected-malformed/input",
            output_payload_ref=None,
            summary_json={
                "schema_id": "layer3.pass_run_shell_summary.v1",
                "analysis_plan_id": approval.analysis_plan.analysis_plan_id,
                "source_preview_id": "cohort-selected-pass-preview",
                "source_preview_hash": preview.preview_hash,
                "planned_pass": dict(planned_pass),
                "execution_started": False,
                "analysis_run_id": None,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(pass_run)
        db.flush()

        with pytest.raises(Layer3PassEntryError, match="method-source rejection"):
            execute_selected_pass_run(
                db,
                pass_run=pass_run,
                planned_pass=planned_pass,
                client_request_id="cohort-selected-start-malformed",
            )

        assert db.query(AnalysisRun).count() == 0
        stored_pass = db.get(L3PassRun, pass_run.pass_run_id)
        assert stored_pass.status == "selected_not_started"
        assert stored_pass.output_payload_ref is None
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_selected_cohort_failure_does_not_record_rolled_back_dataset(tmp_path, monkeypatch):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _, _ = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            requested_method_name="descriptive_summary",
        )

        preview = preview_pass_entry(db, session_id=session_id)
        approval = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview.preview_hash,
            source_preview_id="cohort-selected-pass-preview",
        )
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        pass_run = L3PassRun(
            pass_run_id="pass-run-cohort-selected-analysis-fails",
            session_id=session_id,
            analysis_plan_id=approval.analysis_plan.analysis_plan_id,
            analysis_set_id=planned_pass["analysis_set_id"],
            pass_type="associated_cohort",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            started_at=None,
            completed_at=None,
            input_payload_ref="layer3://execution-selection/pass-run-cohort-selected-analysis-fails/input",
            output_payload_ref=None,
            summary_json={
                "schema_id": "layer3.pass_run_shell_summary.v1",
                "analysis_plan_id": approval.analysis_plan.analysis_plan_id,
                "source_preview_id": "cohort-selected-pass-preview",
                "source_preview_hash": preview.preview_hash,
                "planned_pass": dict(planned_pass),
                "execution_started": False,
                "analysis_run_id": None,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(pass_run)
        db.flush()
        pass_run_id = pass_run.pass_run_id
        original_input_payload_ref = pass_run.input_payload_ref
        db.commit()

        def _explode(*args, **kwargs):
            raise RuntimeError("analysis exploded")

        monkeypatch.setattr(layer3_pass_entry_module, "run_analysis", _explode)

        result = execute_selected_pass_run(
            db,
            pass_run=pass_run,
            planned_pass=planned_pass,
            client_request_id="cohort-selected-start-fails",
        )
        db.commit()

        stored_pass = db.get(L3PassRun, pass_run_id)
        assert result.status == "failed"
        assert result.dataset_version_id is None
        assert result.analysis_run_id is None
        assert stored_pass.status == "failed"
        assert stored_pass.input_payload_ref == original_input_payload_ref
        assert "dataset_version_id" not in stored_pass.summary_json
        assert "derived_dataset_version_id" not in stored_pass.summary_json
        assert stored_pass.summary_json["requested_method_name"] == "descriptive_summary"
        assert stored_pass.summary_json["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]
        assert db.query(AnalysisRun).count() == 0
        assert db.query(DatasetVersion).count() == 2
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_fails_closed_on_cohort_time_alignment_empty(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            second_start="2030-01-01",
        )

        with pytest.raises(Layer3PassEntryError, match="has no admissible analysis sets"):
            materialize_pass_entry(db, session_id=session_id)

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(DatasetVersion).count() == 2
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_fails_closed_on_unsupported_cohort_recommended_method(tmp_path, monkeypatch):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_cohort_ready_session(db, tmp_path)

        def _unsupported(*args, **kwargs):
            raise Layer3PassEntryError("shaped cohort recommended unsupported Gate C method 'descriptive_summary'")

        monkeypatch.setattr(layer3_pass_entry_module, "_choose_cohort_method_name_or_raise", _unsupported)

        with pytest.raises(Layer3PassEntryError, match="has no admissible analysis sets"):
            layer3_pass_entry_module.materialize_pass_entry(db, session_id=session_id)

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(DatasetVersion).count() == 2
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_fails_closed_without_admissible_sets(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_qual_only_ready_session(db, tmp_path)

        with pytest.raises(Layer3PassEntryError, match="has no admissible analysis sets"):
            materialize_pass_entry(db, session_id=session_id)

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_marks_session_failed_when_wrapped_analysis_errors(tmp_path, monkeypatch):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_ready_session(db, tmp_path)

        def _boom(*args, **kwargs):
            raise RuntimeError("analysis exploded")

        monkeypatch.setattr(layer3_pass_entry_module, "run_analysis", _boom)

        with pytest.raises(Layer3PassEntryError, match="analysis exploded"):
            layer3_pass_entry_module.materialize_pass_entry(db, session_id=session_id)
        db.rollback()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        session = db.get(L3Session, session_id)

        assert stored_pass.status == "failed"
        assert stored_pass.completed_at is not None
        assert stored_pass.output_payload_ref is None
        assert stored_pass.summary_json["error"] == "analysis exploded"
        assert db.query(AnalysisRun).count() == 0

        preserved = session.summary_json["phase1a_loading_closure"]
        assert preserved["status"] == phase1a_status
        assert preserved["completed_at"] == _utc_isoformat(phase1a_completed_at)
        assert session.status == "failed"
        assert session.completed_at is not None
        assert session.summary_json["pass_entry"]["analysis_plan_id"] == stored_plan.analysis_plan_id
        assert session.summary_json["pass_entry"]["pass_run_ids_json"] == [stored_pass.pass_run_id]
        assert "analysis exploded" in session.summary_json["pass_entry"]["failure_reason"]
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_executes_descriptive_summary_single_item_without_widening_scope(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_non_timeseries_quant_ready_session(db, tmp_path)

        result = materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        stored_pass = db.query(L3PassRun).one()
        session = db.get(L3Session, session_id)

        assert result.analysis_plan.analysis_plan_id == stored_plan.analysis_plan_id
        assert len(result.pass_runs) == 1
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        assert planned_pass["pass_type"] == "single_item"
        assert planned_pass["pass_scope"] == "quantitative_single_item_dataset_version"
        assert planned_pass["selected_method_name"] == "descriptive_summary"
        assert planned_pass["dataset_version_id"] == "dv-pass-003"
        assert stored_plan.plan_json["source_gate"] == "06_GATEC_PASS_FREEZE"
        assert stored_plan.plan_json["excluded_sets_json"] == []

        assert stored_pass.pass_type == "single_item"
        assert stored_pass.engine_family == "wrapped_quantitative_analysis"
        assert stored_pass.status in {"completed", "completed_with_warnings"}
        assert stored_pass.input_payload_ref
        assert stored_pass.output_payload_ref
        assert Path(stored_pass.output_payload_ref).exists()
        assert stored_pass.summary_json["dataset_version_id"] == "dv-pass-003"
        assert stored_pass.summary_json["selected_method_name"] == "descriptive_summary"
        assert stored_pass.summary_json["pass_scope"] == "quantitative_single_item_dataset_version"
        assert stored_pass.summary_json["analysis_run_id"]
        assert stored_pass.summary_json["artifact_types_json"] == ["descriptive_summary_result"]

        output_manifest = json.loads(Path(stored_pass.output_payload_ref).read_text(encoding="utf-8"))
        assert output_manifest["selected_method_name"] == "descriptive_summary"
        assert output_manifest["artifact_types_json"] == ["descriptive_summary_result"]
        assert "source_dataset_version_ids_json" not in output_manifest
        assert "column_map_json" not in output_manifest

        analysis_run = db.query(AnalysisRun).one()
        assert analysis_run.method_name == "descriptive_summary"
        preserved = session.summary_json["phase1a_loading_closure"]
        assert preserved["status"] == phase1a_status
        assert preserved["completed_at"] == _utc_isoformat(phase1a_completed_at)
        assert session.summary_json["pass_entry"]["excluded_set_count"] == 0
        assert session.status in {"completed", "completed_with_warnings"}
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_selected_pass_execution_runs_descriptive_summary(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_non_timeseries_quant_ready_session(db, tmp_path)

        preview = preview_pass_entry(db, session_id=session_id)
        approval = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview.preview_hash,
            source_preview_id="descriptive-plan-preview",
        )
        db.commit()

        stored_plan = db.query(L3AnalysisPlan).one()
        planned_pass = stored_plan.plan_json["planned_passes_json"][0]
        pass_run = L3PassRun(
            pass_run_id="pass-run-descriptive-selected",
            session_id=session_id,
            analysis_plan_id=stored_plan.analysis_plan_id,
            analysis_set_id=planned_pass["analysis_set_id"],
            pass_type="single_item",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            started_at=None,
            completed_at=None,
            input_payload_ref="selected-pass-input-ref",
            output_payload_ref=None,
            summary_json={
                "dataset_version_id": "dv-pass-003",
                "selected_method_name": "descriptive_summary",
                "analysis_run_id": None,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(pass_run)
        db.flush()

        result = execute_selected_pass_run(
            db,
            pass_run=pass_run,
            planned_pass=planned_pass,
            client_request_id="descriptive-selected-start",
        )
        db.commit()

        stored_pass = db.get(L3PassRun, pass_run.pass_run_id)
        session = db.get(L3Session, session_id)

        assert approval.analysis_plan.analysis_plan_id == stored_plan.analysis_plan_id
        assert result.execution_started is True
        assert result.selected_method_name == "descriptive_summary"
        assert result.dataset_version_id == "dv-pass-003"
        assert result.analysis_run_id
        assert result.output_payload_ref
        assert stored_pass.status in {"completed", "completed_with_warnings"}
        assert stored_pass.summary_json["selected_method_name"] == "descriptive_summary"
        assert stored_pass.summary_json["artifact_types_json"] == ["descriptive_summary_result"]
        assert stored_pass.summary_json["analysis_execution_start"]["client_request_id"] == "descriptive-selected-start"

        output_manifest = json.loads(Path(stored_pass.output_payload_ref).read_text(encoding="utf-8"))
        assert output_manifest["selected_method_name"] == "descriptive_summary"
        assert output_manifest["artifact_types_json"] == ["descriptive_summary_result"]
        assert db.query(AnalysisRun).one().method_name == "descriptive_summary"
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
    finally:
        settings.storage_dir = original_storage_dir


def test_gatec_pass_entry_excludes_unknown_recommended_method_and_fails_closed(tmp_path, monkeypatch):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_quant_ready_session(db, tmp_path)

        def _unsupported(*args, **kwargs):
            return {"recommended_sequence": ["unsupported_quant_method"]}

        monkeypatch.setattr(layer3_pass_entry_module, "recommend_analysis", _unsupported)

        with pytest.raises(Layer3PassEntryError, match="has no admissible analysis sets"):
            materialize_pass_entry(db, session_id=session_id)

        session = db.get(L3Session, session_id)
        assert session.status == phase1a_status
        assert _utc_isoformat(session.completed_at) == _utc_isoformat(phase1a_completed_at)
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        settings.storage_dir = original_storage_dir
