from __future__ import annotations

import hashlib
import json
import os
import sys
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
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3Session,
    VariableDefinition,
    VariableProfile,
)
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    Layer3PackageEntryError,
    materialize_package_entry,
)
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


def _seed_timeseries_dataset_version(
    db,
    tmp_path: Path,
    *,
    dataset_id: str,
    dataset_version_id: str,
    measure_name: str = "value",
    values: list[float] | None = None,
) -> None:
    dataset = Dataset(
        dataset_id=dataset_id,
        name=f"Dataset {dataset_id}",
        description="Gate D package-entry proof dataset",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="v1",
        version_type="baseline",
        status="ready",
        notes="gated-package-entry-proof",
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

    frame = pd.DataFrame(
        {
            "observed_at": pd.date_range("2020-01-01", periods=24, freq="MS", tz="UTC"),
            measure_name: values or [100 + index for index in range(24)],
        }
    )
    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    frame.to_csv(csv_path, index=False)
    version.storage_ref = str(csv_path)
    version.row_count = len(frame)
    db.flush()


def _build_quant_ready_session(db, tmp_path: Path) -> str:
    dataset_version_id = "dv-pack-001"
    _seed_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id="ds-pack-001",
        dataset_version_id=dataset_version_id,
    )

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-pack-quant"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="gated-package-entry-quant-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_d_package"},
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
                source_provenance={
                    "dataset_id": "ds-pack-001",
                    "storage_ref": str(tmp_path / "datasets" / f"{dataset_version_id}.csv"),
                },
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id


def _build_mixed_ready_session(db, tmp_path: Path) -> str:
    dataset_version_id = "dv-pack-002"
    _seed_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id="ds-pack-002",
        dataset_version_id=dataset_version_id,
    )

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-pack-mixed-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": "run-pack-qual-001", "target_id": "target-pack-qual-001"},
                "selection_basis": {"selection_id": "sel-pack-mixed-qual"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="gated-package-entry-mixed-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_d_package"},
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
                source_provenance={
                    "dataset_id": "ds-pack-002",
                    "storage_ref": str(tmp_path / "datasets" / f"{dataset_version_id}.csv"),
                },
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
                source_identity={"content_id": "doc-pack-001"},
                source_provenance={"linkage_ref": "aps/linkage/doc-pack-001"},
                payload={"content": "qualitative package companion"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": "doc-pack-002"},
                source_provenance={"linkage_ref": "aps/linkage/doc-pack-002"},
                payload={"content": "qualitative package companion two"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id


def _package_rows_by_kind(db) -> dict[str, L3OutputPackage]:
    return {
        row.package_kind: row
        for row in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
    }


def _load_payload(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_gated_package_entry_emits_canonical_user_and_review_packages(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id = _build_quant_ready_session(db, tmp_path)
        materialize_pass_entry(db, session_id=session_id)
        db.commit()

        result = materialize_package_entry(db, session_id=session_id)
        db.commit()

        stored_reconciliation = db.query(L3ReconciliationRecord).one()
        rows = _package_rows_by_kind(db)

        assert result.reconciliation_record.reconciliation_record_id == stored_reconciliation.reconciliation_record_id
        assert set(rows) == {
            PACKAGE_KIND_CANONICAL_INTERNAL,
            PACKAGE_KIND_USER_FACING,
            PACKAGE_KIND_REVIEW_FACING,
        }
        assert len(result.output_packages) == 3

        canonical_row = rows[PACKAGE_KIND_CANONICAL_INTERNAL]
        user_row = rows[PACKAGE_KIND_USER_FACING]
        review_row = rows[PACKAGE_KIND_REVIEW_FACING]
        assert canonical_row.status in {"package_complete", "package_complete_with_warnings"}
        assert user_row.status == canonical_row.status
        assert review_row.status == canonical_row.status

        for row in rows.values():
            payload_path = Path(row.payload_ref)
            assert payload_path.exists()
            assert payload_path.parent == (Path(tmp_path) / "artifacts" / "layer3")
            assert hashlib.sha256(payload_path.read_bytes()).hexdigest() == row.payload_hash
            assert row.summary_json["package_kind"] == row.package_kind

        canonical_payload = _load_payload(canonical_row.payload_ref)
        user_payload = _load_payload(user_row.payload_ref)
        review_payload = _load_payload(review_row.payload_ref)

        assert set(canonical_payload) == {
            "package_header",
            "selection_and_source_summary",
            "typing_and_set_summary",
            "pass_summary",
            "findings",
            "contradictions",
            "caveats",
            "consumer_projection_summary",
            "handoff_status",
        }
        assert canonical_payload["package_header"]["package_kind"] == "canonical_internal"
        assert canonical_payload["selection_and_source_summary"]["material_snapshot_count"] == 1
        assert canonical_payload["pass_summary"]["analysis_plan_id"] == stored_reconciliation.summary_json["analysis_plan_id"]
        assert canonical_payload["consumer_projection_summary"]["derived_package_kinds_json"] == [
            "user_facing",
            "review_facing",
        ]
        assert canonical_payload["handoff_status"]["aps_handoff_admitted"] is False

        assert user_payload["package_header"]["canonical_package_key"] == canonical_payload["package_header"]["package_key"]
        assert review_payload["package_header"]["canonical_package_key"] == canonical_payload["package_header"]["package_key"]
        assert review_payload["trace_payload_refs_json"] == sorted(review_payload["trace_payload_refs_json"])
        assert stored_reconciliation.summary_json["accepted_pass_run_ids_json"]
    finally:
        settings.storage_dir = original_storage_dir


def test_gated_package_entry_marks_excluded_inventory_as_warning_packages(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id = _build_mixed_ready_session(db, tmp_path)
        materialize_pass_entry(db, session_id=session_id)
        db.commit()

        result = materialize_package_entry(db, session_id=session_id)
        db.commit()

        rows = _package_rows_by_kind(db)
        canonical_payload = _load_payload(rows[PACKAGE_KIND_CANONICAL_INTERNAL].payload_ref)
        user_payload = _load_payload(rows[PACKAGE_KIND_USER_FACING].payload_ref)
        review_payload = _load_payload(rows[PACKAGE_KIND_REVIEW_FACING].payload_ref)

        assert result.reconciliation_record.status == "reconciled_with_warnings"
        assert result.reconciliation_record.summary_json["excluded_set_count"] == 1
        assert all(row.status == "package_complete_with_warnings" for row in rows.values())
        assert any(caveat["caveat_type"] == "excluded_analysis_set" for caveat in canonical_payload["caveats"])
        assert user_payload["provisional_or_warning_summary"]["excluded_set_count"] == 1
        assert user_payload["provisional_or_warning_summary"]["is_provisional"] is True
        assert len(review_payload["warning_failure_inventory"]["excluded_sets_json"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_gated_package_entry_emits_review_only_packages_for_failed_pass_provenance(tmp_path, monkeypatch):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id = _build_quant_ready_session(db, tmp_path)

        def _boom(*args, **kwargs):
            raise RuntimeError("analysis exploded")

        monkeypatch.setattr(layer3_pass_entry_module, "run_analysis", _boom)

        with pytest.raises(Layer3PassEntryError, match="analysis exploded"):
            layer3_pass_entry_module.materialize_pass_entry(db, session_id=session_id)
        db.rollback()

        session = db.get(L3Session, session_id)
        assert session.status == "failed"
        assert db.query(AnalysisRun).count() == 0

        result = materialize_package_entry(db, session_id=session_id)
        db.commit()

        rows = _package_rows_by_kind(db)
        canonical_payload = _load_payload(rows[PACKAGE_KIND_CANONICAL_INTERNAL].payload_ref)
        review_payload = _load_payload(rows[PACKAGE_KIND_REVIEW_FACING].payload_ref)

        assert result.reconciliation_record.status == "review_only"
        assert all(row.status == "package_review_only" for row in rows.values())
        assert any(caveat["caveat_type"] == "pass_failure" for caveat in canonical_payload["caveats"])
        assert len(review_payload["warning_failure_inventory"]["failed_pass_run_ids_json"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_gated_package_entry_fails_closed_on_missing_completed_pass_output_ref(tmp_path):
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id = _build_quant_ready_session(db, tmp_path)
        materialize_pass_entry(db, session_id=session_id)
        db.commit()

        stored_pass = db.query(L3PassRun).one()
        stored_pass.output_payload_ref = None
        db.commit()

        with pytest.raises(Layer3PackageEntryError, match="output payload ref is missing"):
            materialize_package_entry(db, session_id=session_id)

        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        settings.storage_dir = original_storage_dir
