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
from app.services.layer3_aps_context_packet_package_handoff import (
    PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF,
    Layer3ApsContextPacketPackageHandoffError,
    materialize_aps_context_packet_package_handoff,
)
from app.services.layer3_aps_multisource import materialize_aps_multisource_admission
from app.services.layer3_aps_report_export_package_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF,
    materialize_aps_report_export_package_handoff,
)
from test_layer3_aps_handoff import _make_session, _rows_by_kind
from test_layer3_aps_multisource import _build_multisource_packaged_session
from test_layer3_aps_report_export_package_handoff import _persist_single_source_export_fixture


def _build_package_context_ready_session(
    db,
    tmp_path: Path,
    *,
    run_id: str = "run-aps-pkgctx-001",
) -> tuple[str, str, str, tuple[str, str]]:
    session_id, built_run_id, target_id, content_ids = _build_multisource_packaged_session(
        db,
        tmp_path,
        run_id=run_id,
    )
    materialize_aps_multisource_admission(db, session_id=session_id)
    db.commit()

    for index, content_id in enumerate(content_ids, start=1):
        _persist_single_source_export_fixture(
            tmp_path,
            run_id=built_run_id,
            target_id=target_id,
            content_id=content_id,
            variant=f"pkgctx-{index}",
        )

    materialize_aps_report_export_package_handoff(db, session_id=session_id)
    db.commit()
    return session_id, built_run_id, target_id, content_ids


def test_materialize_aps_context_packet_package_handoff_emits_row_without_runtime_db_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, _target_id, _content_ids = _build_package_context_ready_session(db, tmp_path)

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_context_packet_package_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF]
        handoff_row = rows[PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, packet_path = aps_context_module.load_persisted_context_packet_artifact(
            context_packet_ref=handoff_row.payload_ref
        )
        assert packet_path == Path(handoff_row.payload_ref)
        assert loaded_payload["schema_id"] == aps_context_contract.APS_CONTEXT_PACKET_SCHEMA_ID
        assert loaded_payload["source_family"] == aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE
        assert loaded_payload["source_descriptor"]["source_ref"] == source_row.payload_ref
        assert loaded_payload["source_descriptor"]["source_id"] == result.context_packet_payload["source_descriptor"]["source_id"]
        assert loaded_payload["source_descriptor"]["owner_run_id"] == run_id
        assert loaded_payload["facts"][0]["fact_type"] == "package_summary"

        monkeypatch.setattr(
            aps_context_gate_module,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
        )
        gate_report = aps_context_gate_module.validate_context_packet_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "context_packet_package_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get("aps_context_packet_report_refs")
        assert not list((after_run.query_plan_json or {}).get("aps_context_packet_summaries") or [])

        assert handoff_row.summary_json["aps_target_family"] == "context_packet_package"
        assert handoff_row.summary_json["aps_schema_id"] == aps_context_contract.APS_CONTEXT_PACKET_SCHEMA_ID
        assert handoff_row.summary_json["context_packet_id"] == loaded_payload["context_packet_id"]
        assert handoff_row.summary_json["context_packet_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF: source_row.payload_ref
        }
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
        assert (
            handoff_row.summary_json["handoff_status"]["source_family"]
            == aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_context_packet_gate_discovers_malformed_scoped_artifact_without_explicit_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        healthy_run_id = "run-aps-context-healthy"
        session_id, built_run_id, _target_id, _content_ids = _build_package_context_ready_session(
            db,
            tmp_path,
            run_id=healthy_run_id,
        )
        assert built_run_id == healthy_run_id
        materialize_aps_context_packet_package_handoff(db, session_id=session_id)
        db.commit()

        malformed_run_id = "run/aps context:mixed"
        malformed_failure_id = aps_context_contract.derive_failure_context_packet_id(
            source_locator="mixed-malformed-scoped-artifact",
            error_code="mixed_malformed_scoped_artifact",
        )
        malformed_failure_path = aps_context_module.context_packet_failure_artifact_path(
            owner_run_id=malformed_run_id,
            context_packet_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        discovered_runs = aps_context_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert len(discovered_runs) == 2

        gate_report = aps_context_gate_module.validate_context_packet_gate(
            run_ids=None,
            limit=10,
            report_path=tmp_path / "context_packet_gate_mixed_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        malformed_check = next(
            check for check in gate_report["checks"] if str(malformed_failure_path) in check["failure_refs"]
        )
        assert aps_context_contract.APS_GATE_FAILURE_FAILURE_SCHEMA in malformed_check["reasons"]
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_packet_package_handoff_fails_closed_without_export_package_source(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_ids = _build_multisource_packaged_session(db, tmp_path)
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        with pytest.raises(
            Layer3ApsContextPacketPackageHandoffError,
            match="missing the APS evidence-report-export-package handoff package",
        ):
            materialize_aps_context_packet_package_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_packet_package_handoff_fails_closed_on_missing_source_package_ref(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_ids = _build_package_context_ready_session(db, tmp_path)

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF)
            .one()
        )
        source_row.payload_ref = str(tmp_path / "missing-evidence-report-export-package.json")
        db.commit()

        with pytest.raises(
            Layer3ApsContextPacketPackageHandoffError,
            match="payload ref does not exist",
        ):
            materialize_aps_context_packet_package_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_packet_package_handoff_fails_closed_on_incompatible_source_package_provenance(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_ids = _build_package_context_ready_session(db, tmp_path)

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF)
            .one()
        )
        source_summary = dict(source_row.summary_json or {})
        source_summary["aps_schema_id"] = "aps.evidence_report_export_package.v999"
        source_row.summary_json = source_summary
        db.commit()

        with pytest.raises(
            Layer3ApsContextPacketPackageHandoffError,
            match="incompatible APS schema provenance",
        ):
            materialize_aps_context_packet_package_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
