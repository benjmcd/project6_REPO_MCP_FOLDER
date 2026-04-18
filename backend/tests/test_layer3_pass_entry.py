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
    AnalysisRun,
    Dataset,
    DatasetVersion,
    L3AnalysisPlan,
    L3PassRun,
    L3Session,
    VariableDefinition,
    VariableProfile,
)
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services.dataframe_io import load_version_dataframe
from app.services.layer3_pass_entry import Layer3PassEntryError, materialize_pass_entry
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
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


def test_gatec_pass_entry_excludes_unsupported_recommended_method_and_fails_closed(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, phase1a_status, phase1a_completed_at = _build_non_timeseries_quant_ready_session(db, tmp_path)

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
