from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import (
    AnalysisRun,
    L3AnalysisGroup,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3TypingRecord,
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
from app.services.layer3_typing_entry import Layer3TypingEntryError, materialize_typing_entry


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def _build_gatec_ready_session(db, tmp_path: Path) -> str:
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": "dv-100"},
                "selection_basis": {"selection_id": "sel-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": "run-qual-001", "target_id": "target-qual-001"},
                "selection_basis": {"selection_id": "sel-qual"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="gatec-typing-entry-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c"},
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
                source_identity={"dataset_version_id": "dv-100"},
                source_provenance={"dataset_id": "ds-100", "storage_ref": "datasets/dv-100.json"},
                payload={"rows": [{"x": 1, "y": 2}]},
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
                source_identity={"content_id": "doc-001"},
                source_provenance={"linkage_ref": "aps/linkage/doc-001"},
                payload={"content": "qualitative document one"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": "doc-002"},
                source_provenance={"linkage_ref": "aps/linkage/doc-002"},
                payload={"content": "qualitative document two"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    return session.session_id


def _build_unsupported_shape_session(db, tmp_path: Path) -> str:
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_x",
                "descriptor_type": "opaque_blob",
                "selector_payload": {"blob_id": "blob-001"},
                "selection_basis": {"selection_id": "sel-unsupported"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_x": ["opaque_blob"]},
        commit_reason="gatec-typing-entry-unsupported-shape",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c"},
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
                source_shape="opaque_blob",
                source_identity={"blob_id": "blob-001"},
                source_provenance={"blob_ref": "opaque/blob-001"},
                payload={"content": "unsupported"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    return session.session_id


def _build_source_intake_gatec_ready_session(db, tmp_path: Path) -> str:
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_source_intake",
                "descriptor_type": SOURCE_INTAKE_GATE_B_SOURCE_CLASS,
                "selector_payload": {
                    "candidate_id": "mat-source_intake_record-src-intake-001",
                    "source_ref": "source_intake:src-intake-001",
                    "source_intake_record_id": "src-intake-001",
                },
                "selection_basis": {
                    "selection_id": "sel-source-intake",
                    "gate_b_decision": "approved",
                },
                "expansion_reason": "gate_b_approved_material",
            }
        ],
        source_plane_hints={"source_classes": [SOURCE_INTAKE_GATE_B_SOURCE_CLASS]},
        commit_reason="gatec-source-intake-typing-entry-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c", "gate_b_summary_v1": {"approved": 1}},
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
                    "candidate_id": "mat-source_intake_record-src-intake-001",
                    "source_class": SOURCE_INTAKE_GATE_B_SOURCE_CLASS,
                    "source_intake_record_id": "src-intake-001",
                    "content_sha256": "a" * 64,
                    "metadata_hash": "b" * 64,
                },
                source_provenance={
                    "source_ref": "source_intake:src-intake-001",
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
    db.commit()
    return session.session_id


def _build_unfinalized_session(db, tmp_path: Path) -> str:
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": "dv-unfinalized"},
                "selection_basis": {"selection_id": "sel-unfinalized"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="gatec-typing-entry-unfinalized-session",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_c"},
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
                source_identity={"dataset_version_id": "dv-unfinalized"},
                source_provenance={"dataset_id": "ds-unfinalized", "storage_ref": "datasets/dv-unfinalized.json"},
                payload={"rows": [{"x": 1, "y": 2}]},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    db.commit()
    return session.session_id


def test_gatec_typing_entry_materializes_quant_single_item_and_qual_associated_cohort(tmp_path):
    db = _make_session()
    session_id = _build_gatec_ready_session(db, tmp_path)

    result = materialize_typing_entry(db, session_id=session_id)
    db.commit()

    stored_typing_records = (
        db.query(L3TypingRecord)
        .order_by(L3TypingRecord.chosen_modality.asc(), L3TypingRecord.material_snapshot_id.asc())
        .all()
    )
    stored_units = (
        db.query(L3AnalysisUnit)
        .order_by(L3AnalysisUnit.analysis_modality.asc(), L3AnalysisUnit.analysis_unit_id.asc())
        .all()
    )
    stored_groups = (
        db.query(L3AnalysisGroup)
        .order_by(L3AnalysisGroup.analysis_modality.asc(), L3AnalysisGroup.analysis_group_id.asc())
        .all()
    )
    stored_sets = (
        db.query(L3AnalysisSet)
        .order_by(L3AnalysisSet.set_type.asc(), L3AnalysisSet.analysis_set_id.asc())
        .all()
    )

    assert len(result.typing_records) == 3
    assert len(result.analysis_units) == 3
    assert len(result.analysis_groups) == 2
    assert len(result.analysis_sets) == 2

    assert len(stored_typing_records) == 3
    assert [record.chosen_modality for record in stored_typing_records] == [
        "qualitative",
        "qualitative",
        "quantitative",
    ]
    assert all(record.overridden_by_operator is False for record in stored_typing_records)
    assert all(record.override_reason is None for record in stored_typing_records)

    qualitative_records = [record for record in stored_typing_records if record.chosen_modality == "qualitative"]
    quantitative_record = next(record for record in stored_typing_records if record.chosen_modality == "quantitative")

    assert all(record.candidate_modalities_json == ["qualitative"] for record in qualitative_records)
    assert quantitative_record.candidate_modalities_json == ["quantitative"]
    assert quantitative_record.typing_basis_json["planning_shape_family"] == "tabular_numeric"
    assert all(record.typing_basis_json["planning_shape_family"] == "document_chunks" for record in qualitative_records)

    assert len(stored_units) == 3
    assert all(unit.unit_kind == "atomic" for unit in stored_units)
    assert all(unit.must_remain_intact is False for unit in stored_units)
    assert all(len(unit.member_snapshot_ids_json) == 1 for unit in stored_units)
    assert all(len(unit.typing_record_ids_json) == 1 for unit in stored_units)
    for unit in stored_units:
        assert unit.member_ranges_json == [{"material_snapshot_id": unit.member_snapshot_ids_json[0], "scope": "full"}]

    quantitative_group = next(group for group in stored_groups if group.analysis_modality == "quantitative")
    qualitative_group = next(group for group in stored_groups if group.analysis_modality == "qualitative")

    assert quantitative_group.typing_basis_json["group_basis"] == "singleton"
    assert len(quantitative_group.analysis_unit_ids_json) == 1
    assert qualitative_group.typing_basis_json["group_basis"] == "same_descriptor"
    assert len(qualitative_group.analysis_unit_ids_json) == 2

    single_item_set = next(analysis_set for analysis_set in stored_sets if analysis_set.set_type == "single_item")
    associated_cohort_set = next(
        analysis_set for analysis_set in stored_sets if analysis_set.set_type == "associated_cohort"
    )

    assert single_item_set.analysis_unit_ids_json == quantitative_group.analysis_unit_ids_json
    assert single_item_set.formation_basis_json["group_basis"] == "singleton"
    assert associated_cohort_set.analysis_unit_ids_json == qualitative_group.analysis_unit_ids_json
    assert associated_cohort_set.formation_basis_json["group_basis"] == "same_descriptor"
    assert associated_cohort_set.formation_basis_json["analysis_modality"] == "qualitative"

    assert db.query(AnalysisRun).count() == 0


def test_gatec_typing_entry_fails_closed_on_unsupported_shape(tmp_path):
    db = _make_session()
    session_id = _build_unsupported_shape_session(db, tmp_path)

    with pytest.raises(Layer3TypingEntryError, match="unsupported source_shape 'opaque_blob'"):
        materialize_typing_entry(db, session_id=session_id)

    assert db.query(L3TypingRecord).count() == 0
    assert db.query(L3AnalysisUnit).count() == 0
    assert db.query(L3AnalysisGroup).count() == 0
    assert db.query(L3AnalysisSet).count() == 0
    assert db.query(AnalysisRun).count() == 0


def test_gatec_typing_entry_materializes_source_intake_as_qualitative_document_chunks(tmp_path):
    db = _make_session()
    session_id = _build_source_intake_gatec_ready_session(db, tmp_path)

    result = materialize_typing_entry(db, session_id=session_id)
    db.commit()

    typing_record = db.query(L3TypingRecord).one()
    analysis_unit = db.query(L3AnalysisUnit).one()
    analysis_group = db.query(L3AnalysisGroup).one()
    analysis_set = db.query(L3AnalysisSet).one()
    snapshot = db.get(L3MaterialSnapshot, typing_record.material_snapshot_id)

    assert len(result.typing_records) == 1
    assert len(result.analysis_units) == 1
    assert len(result.analysis_groups) == 1
    assert len(result.analysis_sets) == 1

    assert snapshot is not None
    assert snapshot.source_shape == SOURCE_INTAKE_GATE_B_SOURCE_CLASS
    assert snapshot.source_identity_json["source_intake_record_id"] == "src-intake-001"

    assert typing_record.candidate_modalities_json == ["qualitative"]
    assert typing_record.chosen_modality == "qualitative"
    assert typing_record.typing_basis_json["source_shape"] == SOURCE_INTAKE_GATE_B_SOURCE_CLASS
    assert typing_record.typing_basis_json["planning_shape_family"] == "document_chunks"
    assert typing_record.typing_basis_json["confidence_basis"] == "frozen_source_intake_text_document_default"
    assert typing_record.overridden_by_operator is False
    assert typing_record.override_reason is None

    assert analysis_unit.unit_kind == "atomic"
    assert analysis_unit.analysis_modality == "qualitative"
    assert analysis_unit.member_snapshot_ids_json == [snapshot.material_snapshot_id]
    assert analysis_unit.typing_record_ids_json == [typing_record.typing_record_id]
    assert analysis_unit.must_remain_intact is False

    assert analysis_group.analysis_modality == "qualitative"
    assert analysis_group.typing_basis_json["group_basis"] == "singleton"
    assert analysis_set.set_type == "single_item"
    assert analysis_set.formation_basis_json["analysis_modality"] == "qualitative"
    assert analysis_set.formation_basis_json["group_basis"] == "singleton"

    assert db.query(AnalysisRun).count() == 0


def test_gatec_typing_entry_source_intake_duplicate_commit_fails_closed(tmp_path):
    db = _make_session()
    session_id = _build_source_intake_gatec_ready_session(db, tmp_path)

    materialize_typing_entry(db, session_id=session_id)
    db.commit()

    with pytest.raises(Layer3TypingEntryError, match="already has typing records"):
        materialize_typing_entry(db, session_id=session_id)

    assert db.query(L3TypingRecord).count() == 1
    assert db.query(L3AnalysisUnit).count() == 1
    assert db.query(L3AnalysisGroup).count() == 1
    assert db.query(L3AnalysisSet).count() == 1
    assert db.query(AnalysisRun).count() == 0


def test_gatec_typing_entry_requires_finalized_session(tmp_path):
    db = _make_session()
    session_id = _build_unfinalized_session(db, tmp_path)

    with pytest.raises(Layer3TypingEntryError, match="must be finalized before Gate C typing entry"):
        materialize_typing_entry(db, session_id=session_id)

    assert db.query(L3TypingRecord).count() == 0
    assert db.query(L3AnalysisUnit).count() == 0
    assert db.query(L3AnalysisGroup).count() == 0
    assert db.query(L3AnalysisSet).count() == 0
    assert db.query(AnalysisRun).count() == 0
