from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import (
    L3Descriptor,
    L3MaterialSnapshot,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
)
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def test_layer3_session_entry_happy_path(tmp_path):
    db = _make_session()
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": "dv-001"},
                "selection_basis": {"selection_id": "sel-plane-a"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": "run-aps-001", "target_id": "target-aps-001", "content_id": "cid-001"},
                "selection_basis": {"selection_id": "sel-plane-b"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="phase1a-proof-happy-path",
        entry_route_context={"entrypoint": "test_harness"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_b"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)

    event_a, snapshots_a = record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": "dv-001"},
                source_provenance={"dataset_id": "ds-001", "storage_ref": "datasets/dv-001.json"},
                payload={"rows": [{"region": "west", "value": 12}]},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    event_b, snapshots_b = record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"run_id": "run-aps-001", "target_id": "target-aps-001", "content_id": "cid-001"},
                source_provenance={"linkage_ref": "aps/linkage/cid-001"},
                payload={"content": "phase-1a document material"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()

    stored_session = db.query(L3Session).one()
    stored_manifest = db.query(L3SelectionManifest).one()
    stored_descriptors = db.query(L3Descriptor).order_by(L3Descriptor.source_plane).all()
    stored_events = db.query(L3RetrievalEvent).order_by(L3RetrievalEvent.outcome).all()
    stored_snapshots = db.query(L3MaterialSnapshot).order_by(L3MaterialSnapshot.source_plane).all()

    assert stored_session.status == "completed"
    assert stored_session.selection_manifest_id == stored_manifest.selection_manifest_id
    assert len(stored_manifest.selection_hash) == 64
    assert stored_manifest.commit_reason == "phase1a-proof-happy-path"
    assert stored_session.summary_json["loaded_snapshot_count"] == 2
    assert stored_session.summary_json["source_planes"] == ["plane_a", "plane_b"]
    assert stored_session.summary_json["warning_reasons"] == []

    assert [descriptor.status for descriptor in stored_descriptors] == ["resolved_loaded", "resolved_loaded"]
    assert {descriptor.source_plane for descriptor in stored_descriptors} == {"plane_a", "plane_b"}

    assert {event.outcome for event in stored_events} == {"loaded"}
    for event in (event_a, event_b):
        assert event.event_payload_json["failed_items"] == []
        assert event.event_payload_json["why"] == "loaded"

    assert len(stored_snapshots) == 2
    assert {snapshot.source_plane for snapshot in stored_snapshots} == {"plane_a", "plane_b"}
    for snapshot in stored_snapshots:
        payload_path = Path(snapshot.payload_ref)
        assert payload_path.exists()
        assert hashlib.sha256(payload_path.read_bytes()).hexdigest() == snapshot.payload_hash

    assert snapshots_a[0].material_snapshot_id in event_a.material_snapshot_ids_json
    assert snapshots_b[0].material_snapshot_id in event_b.material_snapshot_ids_json


def test_layer3_session_entry_partial_feed_preserves_explicit_failure_lineage(tmp_path):
    db = _make_session()
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": "dv-002"},
                "selection_basis": {"selection_id": "sel-plane-a"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": "run-aps-002", "target_id": "target-aps-002", "content_id": "cid-404"},
                "selection_basis": {"selection_id": "sel-plane-b"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="phase1a-proof-partial-feed",
        entry_route_context={"entrypoint": "test_harness"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_b"},
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
                source_identity={"dataset_version_id": "dv-002"},
                source_provenance={"dataset_id": "ds-002", "storage_ref": "datasets/dv-002.json"},
                payload={"rows": [{"region": "central", "value": 7}]},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    partial_event, partial_snapshots = record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="empty",
        reason_code="no_match",
        loaded_materials=[],
        failed_items=[
            {
                "source_plane": "plane_b",
                "selector_payload": {"run_id": "run-aps-002", "target_id": "target-aps-002", "content_id": "cid-404"},
                "why": "no_match",
            }
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()

    stored_session = db.query(L3Session).one()
    stored_descriptors = db.query(L3Descriptor).order_by(L3Descriptor.source_plane).all()
    stored_events = db.query(L3RetrievalEvent).order_by(L3RetrievalEvent.reason_code).all()
    stored_snapshots = db.query(L3MaterialSnapshot).all()

    assert stored_session.status == "completed_with_warnings"
    assert stored_session.summary_json["loaded_snapshot_count"] == 1
    assert stored_session.summary_json["warning_reasons"] == ["no_match"]
    assert stored_session.summary_json["source_planes"] == ["plane_a", "plane_b"]

    assert [descriptor.status for descriptor in stored_descriptors] == ["resolved_loaded", "resolved_empty"]
    assert {descriptor.source_plane for descriptor in stored_descriptors} == {"plane_a", "plane_b"}

    assert len(stored_events) == 2
    assert partial_event.material_snapshot_ids_json == []
    assert partial_snapshots == []
    assert partial_event.event_payload_json["loaded_items"] == []
    assert partial_event.event_payload_json["failed_items"] == [
        {
            "source_plane": "plane_b",
            "selector_payload": {"run_id": "run-aps-002", "target_id": "target-aps-002", "content_id": "cid-404"},
            "why": "no_match",
        }
    ]
    assert partial_event.event_payload_json["why"] == "no_match"

    assert len(stored_snapshots) == 1
    payload_path = Path(stored_snapshots[0].payload_ref)
    assert payload_path.exists()
    stored_payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert stored_payload == {"rows": [{"region": "central", "value": 7}]}
