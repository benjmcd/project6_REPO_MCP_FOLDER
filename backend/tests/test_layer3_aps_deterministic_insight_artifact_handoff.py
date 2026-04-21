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
from app.services import nrc_aps_context_dossier as aps_dossier_module
from app.services import nrc_aps_context_packet_contract as aps_context_contract
from app.services import nrc_aps_deterministic_insight_artifact as aps_insight_module
from app.services import nrc_aps_deterministic_insight_artifact_contract as aps_insight_contract
from app.services import nrc_aps_deterministic_insight_artifact_gate as aps_insight_gate_module
from app.services.layer3_aps_context_dossier_handoff import (
    PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF,
    materialize_aps_context_dossier_handoff,
)
from app.services.layer3_aps_deterministic_insight_artifact_handoff import (
    PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF,
    Layer3ApsDeterministicInsightArtifactHandoffError,
    materialize_aps_deterministic_insight_artifact_handoff,
)
from test_layer3_aps_context_dossier_handoff import _build_context_dossier_ready_session
from test_layer3_aps_handoff import _make_session, _rows_by_kind


def _build_deterministic_insight_ready_session(
    db,
    tmp_path: Path,
    *,
    run_id: str = "run-aps-deterministic-001",
) -> tuple[str, str, list[str], list[str]]:
    session_id, built_run_id, export_refs, context_packet_refs = _build_context_dossier_ready_session(
        db,
        tmp_path,
        run_id=run_id,
    )
    materialize_aps_context_dossier_handoff(db, session_id=session_id)
    db.commit()
    return session_id, built_run_id, export_refs, context_packet_refs


def test_materialize_aps_deterministic_insight_handoff_emits_row_without_runtime_db_writes(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, _export_refs, _context_packet_refs = _build_deterministic_insight_ready_session(
            db,
            tmp_path,
        )

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF]
        handoff_row = rows[PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, artifact_path = aps_insight_module.load_persisted_deterministic_insight_artifact(
            deterministic_insight_artifact_ref=handoff_row.payload_ref
        )
        assert artifact_path == Path(handoff_row.payload_ref)
        assert (
            loaded_payload["schema_id"]
            == aps_insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID
        )
        assert loaded_payload["source_context_dossier"]["owner_run_id"] == run_id
        assert (
            loaded_payload["source_context_dossier"]["source_family"]
            == aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT
        )
        assert loaded_payload["source_context_dossier"]["source_packet_count"] == 2

        gate_report = aps_insight_gate_module.validate_deterministic_insight_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_insight_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get("aps_deterministic_insight_artifact_report_refs")
        assert not list((after_run.query_plan_json or {}).get("aps_deterministic_insight_artifact_summaries") or [])

        source_dossier_payload, _dossier_path = aps_dossier_module.load_persisted_context_dossier_artifact(
            context_dossier_ref=source_row.payload_ref
        )
        assert handoff_row.summary_json["aps_target_family"] == "deterministic_insight_artifact"
        assert (
            handoff_row.summary_json["aps_schema_id"]
            == aps_insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID
        )
        assert (
            handoff_row.summary_json["deterministic_insight_artifact_id"]
            == loaded_payload["deterministic_insight_artifact_id"]
        )
        assert handoff_row.summary_json["deterministic_insight_artifact_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF: source_row.payload_ref
        }
        assert (
            handoff_row.summary_json["source_context_dossier_id"]
            == source_dossier_payload["context_dossier_id"]
        )
        assert (
            handoff_row.summary_json["source_context_dossier_ref"]
            == source_row.payload_ref
        )
        assert (
            handoff_row.summary_json["ordered_source_packets_sha256"]
            == source_dossier_payload["ordered_source_packets_sha256"]
        )
        assert handoff_row.summary_json["finding_counts"] == loaded_payload["finding_counts"]
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_deterministic_insight_handoff_handles_non_path_safe_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps deterministic:001"
        session_id, built_run_id, _export_refs, _context_packet_refs = _build_deterministic_insight_ready_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id

        result = materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)
        db.commit()

        gate_report = aps_insight_gate_module.validate_deterministic_insight_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_insight_gate_non_path_safe.json",
            require_runs=True,
        )
        rows = _rows_by_kind(db)
        handoff_row = rows[PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF]
        loaded_payload, _artifact_path = aps_insight_module.load_persisted_deterministic_insight_artifact(
            deterministic_insight_artifact_ref=handoff_row.payload_ref
        )

        assert gate_report["passed"] is True
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert loaded_payload["source_context_dossier"]["owner_run_id"] == run_id
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_insight_gate_filters_scope_collisions_by_exact_owner_run_id(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "ab"
        foreign_run_id = "a/b"
        session_id, built_run_id, _export_refs, _context_packet_refs = _build_deterministic_insight_ready_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)
        db.commit()

        foreign_failure_id = aps_insight_contract.derive_failure_deterministic_insight_artifact_id(
            source_locator="foreign-scope-collision",
            error_code="foreign_scope_collision",
        )
        foreign_failure_path = aps_insight_module.deterministic_insight_failure_artifact_path(
            owner_run_id=foreign_run_id,
            deterministic_insight_artifact_id=foreign_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        foreign_failure_path.parent.mkdir(parents=True, exist_ok=True)
        foreign_failure_payload = {
            "schema_id": aps_insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_FAILURE_SCHEMA_ID,
            "schema_version": aps_insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION,
            "generated_at_utc": "2026-04-20T00:00:00Z",
            "deterministic_insight_artifact_id": foreign_failure_id,
            **aps_insight_contract.ruleset_identity_payload(),
            "insight_mode": aps_insight_contract.APS_DETERMINISTIC_INSIGHT_MODE,
            "owner_run_id": foreign_run_id,
            "source_request": {
                "context_dossier_id": None,
                "context_dossier_ref": None,
                "persist_insight_artifact": False,
            },
            "source_context_dossier": {},
            "error_code": "foreign_scope_collision",
            "error_message": "foreign deterministic insight artifact under neighboring sanitized scope",
        }
        foreign_failure_payload["deterministic_insight_artifact_checksum"] = (
            aps_insight_contract.compute_deterministic_insight_artifact_checksum(
                foreign_failure_payload
            )
        )
        foreign_failure_path.write_text(
            json.dumps(foreign_failure_payload, sort_keys=True),
            encoding="utf-8",
        )

        discovered_runs = aps_insight_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert {str(row["run_id"]) for row in discovered_runs} == {run_id, foreign_run_id}

        gate_report = aps_insight_gate_module.validate_deterministic_insight_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_insight_gate_scope_collision.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True
        assert gate_report["checks"][0]["failure_refs"] == []
        assert len(gate_report["checks"][0]["deterministic_insight_artifact_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_insight_gate_fails_closed_on_malformed_scoped_artifact(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/deterministic insight:malformed"
        session_id, built_run_id, _export_refs, _context_packet_refs = _build_deterministic_insight_ready_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)
        db.commit()

        malformed_failure_id = aps_insight_contract.derive_failure_deterministic_insight_artifact_id(
            source_locator="malformed-scoped-artifact",
            error_code="malformed_scoped_artifact",
        )
        malformed_failure_path = aps_insight_module.deterministic_insight_failure_artifact_path(
            owner_run_id=run_id,
            deterministic_insight_artifact_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        gate_report = aps_insight_gate_module.validate_deterministic_insight_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_insight_gate_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        assert gate_report["checks"][0]["failure_refs"] == [str(malformed_failure_path)]
        assert (
            aps_insight_contract.APS_GATE_FAILURE_FAILURE_SCHEMA
            in gate_report["checks"][0]["reasons"]
        )
        assert len(gate_report["checks"][0]["deterministic_insight_artifact_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_insight_gate_discovers_malformed_scoped_artifact_without_explicit_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        healthy_run_id = "run-aps-deterministic-healthy"
        session_id, built_run_id, _export_refs, _context_packet_refs = _build_deterministic_insight_ready_session(
            db,
            tmp_path,
            run_id=healthy_run_id,
        )
        assert built_run_id == healthy_run_id
        materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)
        db.commit()

        malformed_run_id = "run/aps deterministic:mixed"
        malformed_failure_id = aps_insight_contract.derive_failure_deterministic_insight_artifact_id(
            source_locator="mixed-malformed-scoped-artifact",
            error_code="mixed_malformed_scoped_artifact",
        )
        malformed_failure_path = aps_insight_module.deterministic_insight_failure_artifact_path(
            owner_run_id=malformed_run_id,
            deterministic_insight_artifact_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        discovered_runs = aps_insight_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert len(discovered_runs) == 2

        gate_report = aps_insight_gate_module.validate_deterministic_insight_artifact_gate(
            run_ids=None,
            limit=10,
            report_path=tmp_path / "deterministic_insight_gate_mixed_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        malformed_check = next(
            check for check in gate_report["checks"] if str(malformed_failure_path) in check["failure_refs"]
        )
        assert aps_insight_contract.APS_GATE_FAILURE_FAILURE_SCHEMA in malformed_check["reasons"]
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_insight_gate_dedupes_raw_and_fallback_candidates_for_same_run(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps deterministic:dedupe"
        session_id, built_run_id, _export_refs, _context_packet_refs = _build_deterministic_insight_ready_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)
        db.commit()

        malformed_failure_id = aps_insight_contract.derive_failure_deterministic_insight_artifact_id(
            source_locator="dedupe-malformed-scoped-artifact",
            error_code="dedupe_malformed_scoped_artifact",
        )
        malformed_failure_path = aps_insight_module.deterministic_insight_failure_artifact_path(
            owner_run_id=run_id,
            deterministic_insight_artifact_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        discovered_runs = aps_insight_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert [str(row["run_id"]) for row in discovered_runs] == [run_id]

        gate_report = aps_insight_gate_module.validate_deterministic_insight_artifact_gate(
            run_ids=None,
            limit=10,
            report_path=tmp_path / "deterministic_insight_gate_dedupe_scope.json",
            require_runs=True,
        )

        assert gate_report["checked_runs"] == 1
        assert gate_report["failed_runs"] == 1
        assert gate_report["checks"][0]["run_id"] == run_id
        assert gate_report["checks"][0]["failure_refs"] == [str(malformed_failure_path)]
        assert (
            aps_insight_contract.APS_GATE_FAILURE_FAILURE_SCHEMA
            in gate_report["checks"][0]["reasons"]
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_deterministic_insight_handoff_fails_closed_without_context_dossier_source(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _export_refs, _context_packet_refs = _build_context_dossier_ready_session(
            db,
            tmp_path,
        )

        with pytest.raises(
            Layer3ApsDeterministicInsightArtifactHandoffError,
            match="missing the APS context-dossier handoff package",
        ):
            materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.package_kind
                == PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF
            )
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
