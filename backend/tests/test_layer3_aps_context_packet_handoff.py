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
from app.models.models import ConnectorRun, L3OutputPackage
from app.services import nrc_aps_context_packet as aps_context_module
from app.services import nrc_aps_context_packet_contract as aps_context_contract
from app.services import nrc_aps_context_packet_gate as aps_context_gate_module
from app.services import nrc_aps_evidence_report_export as aps_report_export_module
from app.services import nrc_aps_evidence_report_export_contract as aps_report_export_contract
from app.services.layer3_aps_citation_handoff import materialize_aps_citation_handoff
from app.services.layer3_aps_context_packet_handoff import (
    PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF,
    Layer3ApsContextPacketHandoffError,
    materialize_aps_context_packet_handoff,
)
from app.services.layer3_aps_handoff import materialize_aps_handoff
from app.services.layer3_aps_report_export_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF,
    materialize_aps_report_export_handoff,
)
from app.services.layer3_aps_report_handoff import materialize_aps_report_handoff
from test_layer3_aps_handoff import _build_packaged_session, _make_session, _rows_by_kind


def test_materialize_aps_context_packet_handoff_emits_row_without_runtime_db_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
        )
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_context_packet_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF]
        handoff_row = rows[PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, packet_path = aps_context_module.load_persisted_context_packet_artifact(
            context_packet_ref=handoff_row.payload_ref
        )
        assert packet_path == Path(handoff_row.payload_ref)
        assert loaded_payload["schema_id"] == aps_context_contract.APS_CONTEXT_PACKET_SCHEMA_ID
        assert loaded_payload["source_family"] == aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT
        assert loaded_payload["source_descriptor"]["source_ref"] == source_row.payload_ref
        assert loaded_payload["source_descriptor"]["source_id"] == result.context_packet_payload["source_descriptor"]["source_id"]
        assert loaded_payload["source_descriptor"]["owner_run_id"] == run_id
        assert loaded_payload["facts"][0]["fact_type"] == "export_summary"

        monkeypatch.setattr(
            aps_context_gate_module,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
        )
        gate_report = aps_context_gate_module.validate_context_packet_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "context_packet_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get("aps_context_packet_report_refs")
        assert not list((after_run.query_plan_json or {}).get("aps_context_packet_summaries") or [])

        assert handoff_row.summary_json["aps_target_family"] == "context_packet"
        assert handoff_row.summary_json["aps_schema_id"] == aps_context_contract.APS_CONTEXT_PACKET_SCHEMA_ID
        assert handoff_row.summary_json["context_packet_id"] == loaded_payload["context_packet_id"]
        assert handoff_row.summary_json["context_packet_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF: source_row.payload_ref
        }
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
        assert (
            handoff_row.summary_json["handoff_status"]["source_family"]
            == aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_packet_handoff_fails_closed_on_missing_source_export_ref(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
        )
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF)
            .one()
        )
        source_row.payload_ref = str(tmp_path / "missing-evidence-report-export.json")
        db.commit()

        with pytest.raises(
            Layer3ApsContextPacketHandoffError,
            match="payload ref does not exist",
        ):
            materialize_aps_context_packet_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_packet_handoff_fails_closed_on_incompatible_source_export_provenance(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
        )
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF)
            .one()
        )
        source_summary = dict(source_row.summary_json or {})
        source_summary["aps_schema_id"] = "aps.evidence_report_export.v999"
        source_row.summary_json = source_summary
        db.commit()

        with pytest.raises(
            Layer3ApsContextPacketHandoffError,
            match="incompatible APS schema provenance",
        ):
            materialize_aps_context_packet_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_packet_handoff_fails_closed_on_malformed_source_export(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
        )
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF)
            .one()
        )
        tampered = json.loads(Path(source_row.payload_ref).read_text(encoding="utf-8"))
        tampered["schema_id"] = "aps.evidence_report_export.v999"
        tampered["evidence_report_export_checksum"] = (
            aps_report_export_contract.compute_evidence_report_export_checksum(tampered)
        )
        Path(source_row.payload_ref).write_text(
            json.dumps(tampered, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        with pytest.raises(
            Layer3ApsContextPacketHandoffError,
            match="evidence report export schema mismatch",
        ):
            materialize_aps_context_packet_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
