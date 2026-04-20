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
from app.services import nrc_aps_evidence_citation_pack_contract as aps_citation_contract
from app.services import nrc_aps_evidence_report as aps_report_module
from app.services import nrc_aps_evidence_report_contract as aps_report_contract
from app.services import nrc_aps_evidence_report_gate as aps_report_gate_module
from app.services.layer3_aps_citation_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF,
    materialize_aps_citation_handoff,
)
from app.services.layer3_aps_handoff import materialize_aps_handoff
from app.services.layer3_aps_report_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF,
    Layer3ApsReportHandoffError,
    materialize_aps_report_handoff,
)
from test_layer3_aps_handoff import _build_packaged_session, _make_session, _rows_by_kind


def test_materialize_aps_report_handoff_emits_row_without_runtime_db_writes(
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

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF]
        handoff_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, report_path = aps_report_module.load_persisted_evidence_report_artifact(
            evidence_report_ref=handoff_row.payload_ref
        )
        assert report_path == Path(handoff_row.payload_ref)
        assert loaded_payload["schema_id"] == aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID
        assert loaded_payload["source_citation_pack"]["citation_pack_ref"] == source_row.payload_ref
        assert loaded_payload["source_citation_pack"]["source_bundle"]["run_id"] == run_id
        assert loaded_payload["total_sections"] >= 1
        assert loaded_payload["total_citations"] >= 1

        monkeypatch.setattr(
            aps_report_gate_module,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
        )
        gate_report = aps_report_gate_module.validate_evidence_report_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get("aps_evidence_report_report_refs")
        assert not list((after_run.query_plan_json or {}).get("aps_evidence_report_summaries") or [])

        assert handoff_row.summary_json["aps_target_family"] == "evidence_report"
        assert handoff_row.summary_json["aps_schema_id"] == aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID
        assert handoff_row.summary_json["evidence_report_id"] == loaded_payload["evidence_report_id"]
        assert handoff_row.summary_json["evidence_report_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF: source_row.payload_ref
        }
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_handoff_fails_closed_on_missing_source_citation_pack_ref(
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

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF)
            .one()
        )
        source_row.payload_ref = str(tmp_path / "missing-citation-pack.json")
        db.commit()

        with pytest.raises(
            Layer3ApsReportHandoffError,
            match="payload ref does not exist",
        ):
            materialize_aps_report_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_handoff_fails_closed_on_malformed_source_citation_pack(
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

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF)
            .one()
        )
        tampered = json.loads(Path(source_row.payload_ref).read_text(encoding="utf-8"))
        tampered["schema_id"] = "aps.evidence_citation_pack.v999"
        tampered["citation_pack_checksum"] = aps_citation_contract.compute_citation_pack_checksum(tampered)
        Path(source_row.payload_ref).write_text(
            json.dumps(tampered, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        with pytest.raises(
            Layer3ApsReportHandoffError,
            match="citation pack schema mismatch",
        ):
            materialize_aps_report_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
