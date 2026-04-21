from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
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
from app.services import nrc_aps_context_dossier_contract as aps_dossier_contract
from app.services import nrc_aps_context_dossier_gate as aps_dossier_gate_module
from app.services import nrc_aps_context_packet as aps_context_module
from app.services import nrc_aps_context_packet_contract as aps_context_contract
from app.services import nrc_aps_evidence_report_export as aps_export_module
from app.services import nrc_aps_evidence_report_export_package as aps_export_package_module
from app.services.layer3_aps_context_dossier_handoff import (
    PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF,
    Layer3ApsContextDossierHandoffError,
    materialize_aps_context_dossier_handoff,
)
from app.services.layer3_aps_context_packet_package_handoff import (
    PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF,
    materialize_aps_context_packet_package_handoff,
)
from app.services.layer3_aps_report_export_package_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF,
)
from test_layer3_aps_context_packet_package_handoff import _build_package_context_ready_session
from test_layer3_aps_handoff import _make_session, _rows_by_kind


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _persist_export_context_packet_fixture(*, export_ref: str) -> str:
    export_payload, _export_path = aps_export_module.load_persisted_evidence_report_export_artifact(
        evidence_report_export_ref=export_ref
    )
    context_packet_payload = aps_context_contract.build_context_packet_payload(
        source_family=aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
        source_payload=export_payload,
        generated_at_utc=_utc_iso(),
    )
    owner_run_id = str(dict(context_packet_payload.get("source_descriptor") or {}).get("owner_run_id") or "").strip()
    artifact_path = aps_context_module.context_packet_artifact_path(
        owner_run_id=owner_run_id,
        context_packet_id=str(context_packet_payload.get("context_packet_id") or ""),
        reports_dir=settings.connector_reports_dir,
    )
    _validated_payload, context_packet_ref = aps_context_module._persist_or_validate_context_packet(
        artifact_path=artifact_path,
        payload=context_packet_payload,
    )
    return context_packet_ref


def _build_context_dossier_ready_session(
    db,
    tmp_path: Path,
    *,
    run_id: str = "run-aps-dossier-001",
    export_context_packet_count: int = 2,
) -> tuple[str, str, list[str], list[str]]:
    session_id, built_run_id, _target_id, _content_ids = _build_package_context_ready_session(
        db,
        tmp_path,
        run_id=run_id,
    )
    materialize_aps_context_packet_package_handoff(db, session_id=session_id)
    db.commit()

    rows = _rows_by_kind(db)
    export_package_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF]
    export_package_payload, _package_path = aps_export_package_module.load_persisted_evidence_report_export_package_artifact(
        evidence_report_export_package_ref=export_package_row.payload_ref
    )
    source_exports = [dict(item or {}) for item in list(export_package_payload.get("source_exports") or []) if isinstance(item, dict)]
    source_exports.sort(key=lambda item: int(item.get("export_ordinal") or 0))
    export_refs = [str(item.get("evidence_report_export_ref") or "") for item in source_exports]
    context_packet_refs = [
        _persist_export_context_packet_fixture(export_ref=export_ref)
        for export_ref in export_refs[:export_context_packet_count]
    ]
    return session_id, built_run_id, export_refs, context_packet_refs


def test_materialize_aps_context_dossier_handoff_emits_row_without_runtime_db_writes(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, export_refs, context_packet_refs = _build_context_dossier_ready_session(db, tmp_path)

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_context_dossier_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF]
        handoff_row = rows[PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, dossier_path = aps_dossier_module.load_persisted_context_dossier_artifact(
            context_dossier_ref=handoff_row.payload_ref
        )
        assert dossier_path == Path(handoff_row.payload_ref)
        assert loaded_payload["schema_id"] == aps_dossier_contract.APS_CONTEXT_DOSSIER_SCHEMA_ID
        assert loaded_payload["owner_run_id"] == run_id
        assert loaded_payload["source_family"] == aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT
        assert loaded_payload["source_packet_count"] == 2
        assert {
            entry["context_packet_ref"] for entry in loaded_payload["source_packets"]
        } == set(context_packet_refs)

        gate_report = aps_dossier_gate_module.validate_context_dossier_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "context_dossier_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get("aps_context_dossier_report_refs")
        assert not list((after_run.query_plan_json or {}).get("aps_context_dossier_summaries") or [])

        assert handoff_row.summary_json["aps_target_family"] == "context_dossier"
        assert handoff_row.summary_json["aps_schema_id"] == aps_dossier_contract.APS_CONTEXT_DOSSIER_SCHEMA_ID
        assert handoff_row.summary_json["context_dossier_id"] == loaded_payload["context_dossier_id"]
        assert handoff_row.summary_json["context_dossier_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF: source_row.payload_ref
        }
        assert set(handoff_row.summary_json["source_export_refs_json"]) == set(export_refs)
        assert set(handoff_row.summary_json["source_context_packet_refs_json"]) == set(context_packet_refs)
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
        assert handoff_row.summary_json["handoff_status"]["package_context_used_as_provenance_only"] is True
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_dossier_handoff_handles_non_path_safe_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps dossier:001"
        session_id, built_run_id, _export_refs, context_packet_refs = _build_context_dossier_ready_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id

        result = materialize_aps_context_dossier_handoff(db, session_id=session_id)
        db.commit()

        gate_report = aps_dossier_gate_module.validate_context_dossier_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "context_dossier_gate_non_path_safe.json",
            require_runs=True,
        )
        rows = _rows_by_kind(db)
        handoff_row = rows[PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF]
        loaded_payload, _dossier_path = aps_dossier_module.load_persisted_context_dossier_artifact(
            context_dossier_ref=handoff_row.payload_ref
        )

        assert gate_report["passed"] is True
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert loaded_payload["owner_run_id"] == run_id
        assert {
            entry["context_packet_ref"] for entry in loaded_payload["source_packets"]
        } == set(context_packet_refs)
    finally:
        settings.storage_dir = original_storage_dir


def test_context_dossier_gate_filters_scope_collisions_by_exact_owner_run_id(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "ab"
        foreign_run_id = "a/b"
        session_id, built_run_id, _export_refs, _context_packet_refs = _build_context_dossier_ready_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_context_dossier_handoff(db, session_id=session_id)
        db.commit()

        foreign_failure_id = aps_dossier_contract.derive_failure_context_dossier_id(
            source_locator="foreign-scope-collision",
            error_code="foreign_scope_collision",
        )
        foreign_failure_path = aps_dossier_module.context_dossier_failure_artifact_path(
            owner_run_id=foreign_run_id,
            context_dossier_id=foreign_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        foreign_failure_path.parent.mkdir(parents=True, exist_ok=True)
        foreign_failure_payload = {
            "schema_id": aps_dossier_contract.APS_CONTEXT_DOSSIER_FAILURE_SCHEMA_ID,
            "schema_version": aps_dossier_contract.APS_CONTEXT_DOSSIER_SCHEMA_VERSION,
            "generated_at_utc": "2026-04-20T00:00:00Z",
            "context_dossier_id": foreign_failure_id,
            "owner_run_id": foreign_run_id,
            "composition_contract_id": aps_dossier_contract.APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID,
            "dossier_mode": aps_dossier_contract.APS_CONTEXT_DOSSIER_MODE,
            "source_request": {
                "context_packet_ids": None,
                "context_packet_refs": None,
                "persist_dossier": False,
            },
            "source_packets": [],
            "error_code": "foreign_scope_collision",
            "error_message": "foreign dossier artifact under neighboring sanitized scope",
        }
        foreign_failure_payload["context_dossier_checksum"] = aps_dossier_contract.compute_context_dossier_checksum(
            foreign_failure_payload
        )
        foreign_failure_path.write_text(
            json.dumps(foreign_failure_payload, sort_keys=True),
            encoding="utf-8",
        )

        discovered_runs = aps_dossier_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert {str(row["run_id"]) for row in discovered_runs} == {run_id, foreign_run_id}

        gate_report = aps_dossier_gate_module.validate_context_dossier_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "context_dossier_gate_scope_collision.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True
        assert gate_report["checks"][0]["failure_refs"] == []
        assert len(gate_report["checks"][0]["context_dossier_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_dossier_handoff_fails_closed_without_package_context_source(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_ids = _build_package_context_ready_session(db, tmp_path)

        with pytest.raises(
            Layer3ApsContextDossierHandoffError,
            match="missing the APS package-derived context handoff package",
        ):
            materialize_aps_context_dossier_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_context_dossier_handoff_fails_closed_on_missing_export_context_packet(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _export_refs, _context_packet_refs = _build_context_dossier_ready_session(
            db,
            tmp_path,
            export_context_packet_count=1,
        )

        with pytest.raises(
            Layer3ApsContextDossierHandoffError,
            match="could not resolve a persisted export-derived context packet",
        ):
            materialize_aps_context_dossier_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
