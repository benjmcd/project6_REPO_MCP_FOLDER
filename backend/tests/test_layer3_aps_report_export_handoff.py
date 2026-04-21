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
from app.services import nrc_aps_evidence_report as aps_report_module
from app.services import nrc_aps_evidence_report_contract as aps_report_contract
from app.services import nrc_aps_evidence_report_export as aps_report_export_module
from app.services import nrc_aps_evidence_report_export_contract as aps_report_export_contract
from app.services import nrc_aps_evidence_report_export_gate as aps_report_export_gate_module
from app.services.layer3_aps_citation_handoff import materialize_aps_citation_handoff
from app.services.layer3_aps_handoff import materialize_aps_handoff
from app.services.layer3_aps_report_export_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF,
    Layer3ApsReportExportHandoffError,
    materialize_aps_report_export_handoff,
)
from app.services.layer3_aps_report_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF,
    materialize_aps_report_handoff,
)
from test_layer3_aps_handoff import _build_packaged_session, _make_session, _rows_by_kind


def test_materialize_aps_report_export_handoff_emits_row_without_runtime_db_writes(
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

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF]
        handoff_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, export_path = aps_report_export_module.load_persisted_evidence_report_export_artifact(
            evidence_report_export_ref=handoff_row.payload_ref
        )
        assert export_path == Path(handoff_row.payload_ref)
        assert (
            loaded_payload["schema_id"]
            == aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID
        )
        assert loaded_payload["source_evidence_report"]["evidence_report_ref"] == source_row.payload_ref
        assert loaded_payload["source_evidence_report"]["schema_id"] == aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID
        assert loaded_payload["source_evidence_report"]["source_citation_pack"]["source_bundle"]["run_id"] == run_id
        assert loaded_payload["rendered_markdown"].startswith(
            "# NRC ADAMS APS Evidence Report Export\n"
        )

        monkeypatch.setattr(
            aps_report_export_gate_module,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
        )
        gate_report = aps_report_export_gate_module.validate_evidence_report_export_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get("aps_evidence_report_export_report_refs")
        assert not list((after_run.query_plan_json or {}).get("aps_evidence_report_export_summaries") or [])

        assert handoff_row.summary_json["aps_target_family"] == "evidence_report_export"
        assert (
            handoff_row.summary_json["aps_schema_id"]
            == aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID
        )
        assert (
            handoff_row.summary_json["evidence_report_export_id"]
            == loaded_payload["evidence_report_export_id"]
        )
        assert handoff_row.summary_json["evidence_report_export_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF: source_row.payload_ref
        }
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_handoff_handles_non_path_safe_run_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps export:001"
        session_id, built_run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()

        result = materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        monkeypatch.setattr(
            aps_report_export_gate_module,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
        )
        gate_report = aps_report_export_gate_module.validate_evidence_report_export_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_gate_non_path_safe.json",
            require_runs=True,
        )
        rows = _rows_by_kind(db)
        handoff_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF]
        loaded_payload, _export_path = aps_report_export_module.load_persisted_evidence_report_export_artifact(
            evidence_report_export_ref=handoff_row.payload_ref
        )

        assert gate_report["passed"] is True
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert loaded_payload["source_evidence_report"]["source_citation_pack"]["source_bundle"]["run_id"] == run_id
    finally:
        settings.storage_dir = original_storage_dir


def test_evidence_report_export_gate_filters_scope_collisions_by_exact_run_id(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "ab"
        foreign_run_id = "a/b"
        session_id, built_run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        foreign_failure_id = aps_report_export_contract.derive_failure_export_id(
            source_locator="foreign-scope-collision",
            error_code="foreign_scope_collision",
        )
        foreign_failure_payload = {
            "schema_id": "aps.evidence_report_export_failure.v999",
            "schema_version": aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION,
            "generated_at_utc": "2026-04-20T00:00:00Z",
            "evidence_report_export_id": foreign_failure_id,
            "run_id": foreign_run_id,
            "render_contract_id": aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID,
            "template_contract_id": aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID,
            "format_id": aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID,
            "source_request": {
                "evidence_report_id": None,
                "evidence_report_ref": None,
                "persist_export": False,
            },
            "source_evidence_report": {
                "evidence_report_id": None,
                "evidence_report_checksum": None,
                "evidence_report_ref": None,
            },
            "error_code": "foreign_scope_collision",
            "error_message": "foreign artifact under same sanitized scope",
        }
        foreign_failure_payload["evidence_report_export_checksum"] = aps_report_export_contract.compute_evidence_report_export_checksum(
            foreign_failure_payload
        )
        foreign_failure_path = aps_report_export_module.evidence_report_export_failure_artifact_path(
            run_id=foreign_run_id,
            evidence_report_export_id=foreign_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        foreign_failure_path.parent.mkdir(parents=True, exist_ok=True)
        foreign_failure_path.write_text(
            json.dumps(foreign_failure_payload, sort_keys=True),
            encoding="utf-8",
        )

        discovered_runs = aps_report_export_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert {str(row["run_id"]) for row in discovered_runs} == {run_id, foreign_run_id}

        gate_report = aps_report_export_gate_module.validate_evidence_report_export_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_gate_scope_collision.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True
        assert gate_report["checks"][0]["failure_refs"] == []
        assert len(gate_report["checks"][0]["evidence_report_export_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_evidence_report_export_gate_fails_closed_on_malformed_scoped_artifact(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps export:malformed"
        session_id, built_run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        malformed_failure_id = aps_report_export_contract.derive_failure_export_id(
            source_locator="malformed-scoped-artifact",
            error_code="malformed_scoped_artifact",
        )
        malformed_failure_path = aps_report_export_module.evidence_report_export_failure_artifact_path(
            run_id=run_id,
            evidence_report_export_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        gate_report = aps_report_export_gate_module.validate_evidence_report_export_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_gate_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        assert gate_report["checks"][0]["failure_refs"] == [str(malformed_failure_path)]
        assert aps_report_export_contract.APS_GATE_FAILURE_FAILURE_SCHEMA in gate_report["checks"][0]["reasons"]
        assert len(gate_report["checks"][0]["evidence_report_export_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_evidence_report_export_gate_discovers_malformed_scoped_artifact_without_explicit_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        healthy_run_id = "run-aps-export-healthy"
        session_id, built_run_id, _target_id, _content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
            run_id=healthy_run_id,
        )
        assert built_run_id == healthy_run_id
        materialize_aps_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_citation_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_handoff(db, session_id=session_id)
        db.commit()
        materialize_aps_report_export_handoff(db, session_id=session_id)
        db.commit()

        malformed_run_id = "run/aps export:mixed"
        malformed_failure_id = aps_report_export_contract.derive_failure_export_id(
            source_locator="mixed-malformed-scoped-artifact",
            error_code="mixed_malformed_scoped_artifact",
        )
        malformed_failure_path = aps_report_export_module.evidence_report_export_failure_artifact_path(
            run_id=malformed_run_id,
            evidence_report_export_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        discovered_runs = aps_report_export_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert len(discovered_runs) == 2

        gate_report = aps_report_export_gate_module.validate_evidence_report_export_gate(
            run_ids=None,
            limit=10,
            report_path=tmp_path / "evidence_report_export_gate_mixed_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        malformed_check = next(
            check for check in gate_report["checks"] if str(malformed_failure_path) in check["failure_refs"]
        )
        assert aps_report_export_contract.APS_GATE_FAILURE_FAILURE_SCHEMA in malformed_check["reasons"]
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_handoff_fails_closed_on_missing_source_report_ref(
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

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF)
            .one()
        )
        source_row.payload_ref = str(tmp_path / "missing-evidence-report.json")
        db.commit()

        with pytest.raises(
            Layer3ApsReportExportHandoffError,
            match="payload ref does not exist",
        ):
            materialize_aps_report_export_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_handoff_fails_closed_on_incompatible_source_report_provenance(
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

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF)
            .one()
        )
        source_summary = dict(source_row.summary_json or {})
        source_summary["aps_schema_id"] = "aps.evidence_report.v999"
        source_row.summary_json = source_summary
        db.commit()

        with pytest.raises(
            Layer3ApsReportExportHandoffError,
            match="incompatible APS schema provenance",
        ):
            materialize_aps_report_export_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_handoff_fails_closed_on_malformed_source_report(
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

        source_row = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF)
            .one()
        )
        tampered = json.loads(Path(source_row.payload_ref).read_text(encoding="utf-8"))
        tampered["schema_id"] = "aps.evidence_report.v999"
        tampered["evidence_report_checksum"] = aps_report_contract.compute_evidence_report_checksum(
            tampered
        )
        Path(source_row.payload_ref).write_text(
            json.dumps(tampered, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        with pytest.raises(
            Layer3ApsReportExportHandoffError,
            match="evidence report schema mismatch",
        ):
            materialize_aps_report_export_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
