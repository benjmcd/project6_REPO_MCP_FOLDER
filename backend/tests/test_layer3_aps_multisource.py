from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS_DIR))

from app.core.config import settings
from app.models.models import ConnectorRun, L3MaterialSnapshot, L3OutputPackage
from app.services.layer3_aps_multisource import (
    APS_MULTISOURCE_GROUPING_CONTRACT_ID,
    APS_MULTISOURCE_SCHEMA_ID,
    PACKAGE_KIND_APS_MULTISOURCE_ADMISSION,
    Layer3ApsMultisourceError,
    materialize_aps_multisource_admission,
)
from app.services.layer3_package_entry import PACKAGE_KIND_CANONICAL_INTERNAL, materialize_package_entry
from app.services.layer3_pass_entry import materialize_pass_entry
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import materialize_typing_entry
from test_layer3_aps_handoff import (
    _make_session,
    _rows_by_kind,
    _seed_aps_content_fixture,
    _seed_timeseries_dataset_version,
)


def _build_multisource_packaged_session(
    db,
    tmp_path: Path,
    *,
    run_id: str = "run-aps-multi-001",
) -> tuple[str, str, str, tuple[str, str]]:
    dataset_version_id = "dv-aps-multi-001"
    target_id = "target-aps-multi-001"
    content_ids = ("content-aps-multi-001", "content-aps-multi-002")

    _seed_timeseries_dataset_version(db, tmp_path, dataset_version_id=dataset_version_id)
    for artifact_suffix, content_id in enumerate(content_ids, start=1):
        _seed_aps_content_fixture(
            db,
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_id,
            artifact_suffix=str(artifact_suffix),
        )

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-aps-multi-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": "sel-aps-multi-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="gated-aps-multisource-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_d_aps_multisource"},
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
                    "dataset_id": f"ds-{dataset_version_id}",
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
                source_identity={
                    "run_id": run_id,
                    "target_id": target_id,
                    "content_id": content_ids[0],
                },
                source_provenance={"linkage_ref": f"aps/linkage/{content_ids[0]}"},
                payload={"content": "aps multisource companion one"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={
                    "run_id": run_id,
                    "target_id": target_id,
                    "content_id": content_ids[1],
                },
                source_provenance={"linkage_ref": f"aps/linkage/{content_ids[1]}"},
                payload={"content": "aps multisource companion two"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    materialize_pass_entry(db, session_id=session.session_id)
    db.commit()
    materialize_package_entry(db, session_id=session.session_id)
    db.commit()

    return session.session_id, run_id, target_id, content_ids


def _aps_snapshots(db) -> list[L3MaterialSnapshot]:
    return (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.source_shape == "aps_content_document")
        .order_by(L3MaterialSnapshot.material_snapshot_id.asc())
        .all()
    )


def test_materialize_aps_multisource_admission_emits_grouped_row_without_runtime_db_writes(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, target_id, content_ids = _build_multisource_packaged_session(db, tmp_path)

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        canonical_row = rows[PACKAGE_KIND_CANONICAL_INTERNAL]
        admission_row = rows[PACKAGE_KIND_APS_MULTISOURCE_ADMISSION]
        assert result.output_package.output_package_id == admission_row.output_package_id
        assert admission_row.status == canonical_row.status
        assert hashlib.sha256(Path(admission_row.payload_ref).read_bytes()).hexdigest() == admission_row.payload_hash

        payload = json.loads(Path(admission_row.payload_ref).read_text(encoding="utf-8"))
        assert payload["schema_id"] == APS_MULTISOURCE_SCHEMA_ID
        assert payload["grouping_contract_id"] == APS_MULTISOURCE_GROUPING_CONTRACT_ID
        assert payload["source_gate"] == "14_GATED_APS_MULTISOURCE_FREEZE"
        assert payload["admitted_group_count"] == 1
        assert payload["admitted_source_count"] == 2
        assert payload["owner_run_ids_json"] == [run_id]
        admitted_group = payload["admitted_groups"][0]
        assert admitted_group["owner_run_id"] == run_id
        assert admitted_group["source_count"] == 2
        assert {
            (row["target_id"], row["content_id"])
            for row in admitted_group["sources"]
        } == {
            (target_id, content_ids[0]),
            (target_id, content_ids[1]),
        }

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan

        assert admission_row.summary_json["aps_target_family"] == "multisource_admission"
        assert admission_row.summary_json["grouping_contract_id"] == APS_MULTISOURCE_GROUPING_CONTRACT_ID
        assert admission_row.summary_json["source_package_kinds_json"] == [PACKAGE_KIND_CANONICAL_INTERNAL]
        assert admission_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_CANONICAL_INTERNAL: canonical_row.payload_ref
        }
        assert admission_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_multisource_admission_fails_closed_on_single_source_session(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_id = _build_multisource_packaged_session(db, tmp_path)

        snapshots = _aps_snapshots(db)
        db.delete(snapshots[-1])
        db.commit()

        with pytest.raises(
            Layer3ApsMultisourceError,
            match="does not contain an APS same-run multisource group",
        ):
            materialize_aps_multisource_admission(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_MULTISOURCE_ADMISSION)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_multisource_admission_fails_closed_on_duplicate_source_identity(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_ids = _build_multisource_packaged_session(db, tmp_path)

        snapshots = _aps_snapshots(db)
        duplicate_identity = json.loads(json.dumps(snapshots[0].source_identity_json or {}, sort_keys=True))
        snapshots[1].source_identity_json = duplicate_identity
        db.commit()

        with pytest.raises(
            Layer3ApsMultisourceError,
            match="duplicate APS source identity",
        ):
            materialize_aps_multisource_admission(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_MULTISOURCE_ADMISSION)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_multisource_admission_fails_closed_on_cross_run_grouping(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, _target_id, _content_ids = _build_multisource_packaged_session(db, tmp_path)

        snapshots = _aps_snapshots(db)
        altered_identity = json.loads(json.dumps(snapshots[1].source_identity_json or {}, sort_keys=True))
        altered_identity["run_id"] = f"{run_id}-other"
        snapshots[1].source_identity_json = altered_identity
        db.commit()

        with pytest.raises(
            Layer3ApsMultisourceError,
            match="spans multiple APS run ids",
        ):
            materialize_aps_multisource_admission(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_MULTISOURCE_ADMISSION)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
