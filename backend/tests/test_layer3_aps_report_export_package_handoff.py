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
from app.services import nrc_aps_evidence_citation_pack_contract as aps_citation_contract
from app.services import nrc_aps_evidence_report as aps_report_module
from app.services import nrc_aps_evidence_report_contract as aps_report_contract
from app.services import nrc_aps_evidence_report_export as aps_report_export_module
from app.services import nrc_aps_evidence_report_export_contract as aps_report_export_contract
from app.services import nrc_aps_evidence_report_export_package as aps_package_module
from app.services import nrc_aps_evidence_report_export_package_contract as aps_package_contract
from app.services import nrc_aps_evidence_report_export_package_gate as aps_package_gate_module
from app.services.layer3_aps_multisource import (
    PACKAGE_KIND_APS_MULTISOURCE_ADMISSION,
    materialize_aps_multisource_admission,
)
from app.services.layer3_aps_report_export_package_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF,
    Layer3ApsReportExportPackageHandoffError,
    materialize_aps_report_export_package_handoff,
)
from test_layer3_aps_handoff import _make_session, _rows_by_kind
from test_layer3_aps_multisource import _build_multisource_packaged_session


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _persist_single_source_export_fixture(
    tmp_path: Path,
    *,
    run_id: str,
    target_id: str,
    content_id: str,
    variant: str,
) -> str:
    citation_pack_id = f"citation-pack-{content_id}-{variant}"
    citation_pack_checksum = hashlib.sha256(
        f"{citation_pack_id}:{run_id}:{target_id}:{content_id}".encode("utf-8")
    ).hexdigest()
    citation = {
        "citation_id": f"citation-{content_id}-{variant}",
        "citation_label": f"[{variant}] {content_id}",
        "citation_ordinal": 1,
        "group_id": f"group-{content_id}-{variant}",
        "accession_number": f"ML-{variant}-{content_id}",
        "content_id": content_id,
        "run_id": run_id,
        "target_id": target_id,
        "content_contract_id": "aps.content_document.v2",
        "chunking_contract_id": "aps.chunking.v2",
        "chunk_id": f"{content_id}-chunk-1",
        "chunk_ordinal": 0,
        "start_char": 0,
        "end_char": 32,
        "snippet_text": f"snippet for {content_id} ({variant})",
        "snippet_start_char": 0,
        "snippet_end_char": 32,
        "highlight_spans": [],
    }
    citation_pack_payload = {
        "schema_id": aps_citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
        "schema_version": aps_citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
        "citation_pack_id": citation_pack_id,
        "citation_pack_checksum": citation_pack_checksum,
        "derivation_contract_id": aps_citation_contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
        "total_citations": 1,
        "total_groups": 1,
        "source_bundle": {
            "schema_id": "aps.evidence_bundle.v2",
            "schema_version": 2,
            "bundle_id": f"bundle-{content_id}-{variant}",
            "bundle_checksum": hashlib.sha256(
                f"bundle:{content_id}:{variant}".encode("utf-8")
            ).hexdigest(),
            "bundle_ref": str(tmp_path / "aps" / f"bundle-{content_id}-{variant}.json"),
            "run_id": run_id,
            "target_id": target_id,
        },
        "citations": [citation],
    }
    source_citation_pack = aps_report_contract.source_citation_pack_summary_payload(citation_pack_payload)
    sections = aps_report_contract.build_sections_from_citation_pack(citation_pack_payload)
    report_payload = {
        "schema_id": aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID,
        "schema_version": aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "evidence_report_id": aps_report_contract.derive_evidence_report_id(
            citation_pack_id=citation_pack_id,
            citation_pack_checksum=citation_pack_checksum,
        ),
        "assembly_contract_id": aps_report_contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
        "sectioning_contract_id": aps_report_contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
        "source_citation_pack": source_citation_pack,
        "total_sections": len(sections),
        "total_citations": int(source_citation_pack.get("total_citations") or 0),
        "total_groups": int(source_citation_pack.get("total_groups") or 0),
        "sections": sections,
    }
    report_payload["evidence_report_checksum"] = aps_report_contract.compute_evidence_report_checksum(
        report_payload
    )
    report_path = aps_report_module.evidence_report_artifact_path(
        run_id=run_id,
        evidence_report_id=str(report_payload.get("evidence_report_id") or ""),
        reports_dir=settings.connector_reports_dir,
    )
    report_payload, _report_ref = aps_report_module._persist_or_validate_evidence_report(
        artifact_path=report_path,
        payload=report_payload,
    )

    export_payload = aps_report_export_contract.build_evidence_report_export_payload(
        report_payload,
        generated_at_utc=_utc_iso(),
    )
    export_path = aps_report_export_module.evidence_report_export_artifact_path(
        run_id=run_id,
        evidence_report_export_id=str(export_payload.get("evidence_report_export_id") or ""),
        reports_dir=settings.connector_reports_dir,
    )
    export_payload, export_ref = aps_report_export_module._persist_or_validate_evidence_report_export(
        artifact_path=export_path,
        payload=export_payload,
    )
    return export_ref


def test_materialize_aps_report_export_package_handoff_emits_row_without_runtime_db_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, target_id, content_ids = _build_multisource_packaged_session(db, tmp_path)
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        export_refs = [
            _persist_single_source_export_fixture(
                tmp_path,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
                variant=f"v{index}",
            )
            for index, content_id in enumerate(content_ids, start=1)
        ]

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_report_export_package_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_MULTISOURCE_ADMISSION]
        handoff_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, package_path = aps_package_module.load_persisted_evidence_report_export_package_artifact(
            evidence_report_export_package_ref=handoff_row.payload_ref
        )
        assert package_path == Path(handoff_row.payload_ref)
        assert (
            loaded_payload["schema_id"]
            == aps_package_contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID
        )
        assert loaded_payload["owner_run_id"] == run_id
        assert loaded_payload["source_export_count"] == 2
        assert {
            entry["evidence_report_export_ref"] for entry in loaded_payload["source_exports"]
        } == set(export_refs)

        monkeypatch.setattr(
            aps_package_gate_module,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
        )
        gate_report = aps_package_gate_module.validate_evidence_report_export_package_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_package_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get("aps_evidence_report_export_package_report_refs")
        assert not list((after_run.query_plan_json or {}).get("aps_evidence_report_export_package_summaries") or [])

        assert handoff_row.summary_json["aps_target_family"] == "evidence_report_export_package"
        assert (
            handoff_row.summary_json["aps_schema_id"]
            == aps_package_contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID
        )
        assert (
            handoff_row.summary_json["evidence_report_export_package_id"]
            == loaded_payload["evidence_report_export_package_id"]
        )
        assert handoff_row.summary_json["evidence_report_export_package_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_MULTISOURCE_ADMISSION
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_MULTISOURCE_ADMISSION: source_row.payload_ref
        }
        assert set(handoff_row.summary_json["source_export_refs_json"]) == set(export_refs)
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_package_handoff_handles_non_path_safe_run_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps export package:001"
        session_id, built_run_id, target_id, content_ids = _build_multisource_packaged_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        export_refs = [
            _persist_single_source_export_fixture(
                tmp_path,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
                variant=f"safe-{index}",
            )
            for index, content_id in enumerate(content_ids, start=1)
        ]

        result = materialize_aps_report_export_package_handoff(db, session_id=session_id)
        db.commit()

        monkeypatch.setattr(
            aps_package_gate_module,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
        )
        gate_report = aps_package_gate_module.validate_evidence_report_export_package_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_package_gate_non_path_safe.json",
            require_runs=True,
        )
        rows = _rows_by_kind(db)
        handoff_row = rows[PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF]
        loaded_payload, _package_path = aps_package_module.load_persisted_evidence_report_export_package_artifact(
            evidence_report_export_package_ref=handoff_row.payload_ref
        )

        assert gate_report["passed"] is True
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert loaded_payload["owner_run_id"] == run_id
        assert {
            entry["evidence_report_export_ref"] for entry in loaded_payload["source_exports"]
        } == set(export_refs)
    finally:
        settings.storage_dir = original_storage_dir


def test_evidence_report_export_package_gate_filters_scope_collisions_by_exact_owner_run_id(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "ab"
        foreign_run_id = "a/b"
        session_id, built_run_id, target_id, content_ids = _build_multisource_packaged_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        for index, content_id in enumerate(content_ids, start=1):
            _persist_single_source_export_fixture(
                tmp_path,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
                variant=f"collision-{index}",
            )

        materialize_aps_report_export_package_handoff(db, session_id=session_id)
        db.commit()

        foreign_failure_id = aps_package_contract.derive_failure_package_id(
            source_locator="foreign-scope-collision",
            error_code="foreign_scope_collision",
        )
        foreign_failure_payload = {
            "schema_id": "aps.evidence_report_export_package_failure.v999",
            "schema_version": aps_package_contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION,
            "generated_at_utc": "2026-04-20T00:00:00Z",
            "evidence_report_export_package_id": foreign_failure_id,
            "owner_run_id": foreign_run_id,
            "composition_contract_id": aps_package_contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID,
            "package_mode": aps_package_contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE,
            "source_request": {
                "evidence_report_export_ids": None,
                "evidence_report_export_refs": None,
                "persist_package": False,
            },
            "error_code": "foreign_scope_collision",
            "error_message": "foreign package artifact under same sanitized scope",
        }
        foreign_failure_payload["evidence_report_export_package_checksum"] = aps_package_contract.compute_evidence_report_export_package_checksum(
            foreign_failure_payload
        )
        foreign_failure_path = aps_package_module.evidence_report_export_package_failure_artifact_path(
            owner_run_id=foreign_run_id,
            evidence_report_export_package_id=foreign_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        foreign_failure_path.parent.mkdir(parents=True, exist_ok=True)
        foreign_failure_path.write_text(
            json.dumps(foreign_failure_payload, sort_keys=True),
            encoding="utf-8",
        )

        discovered_runs = aps_package_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert {str(row["run_id"]) for row in discovered_runs} == {run_id, foreign_run_id}

        gate_report = aps_package_gate_module.validate_evidence_report_export_package_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_package_gate_scope_collision.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True
        assert gate_report["checks"][0]["failure_refs"] == []
        assert len(gate_report["checks"][0]["evidence_report_export_package_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_evidence_report_export_package_gate_fails_closed_on_malformed_scoped_artifact(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps export package:malformed"
        session_id, built_run_id, target_id, content_ids = _build_multisource_packaged_session(
            db,
            tmp_path,
            run_id=run_id,
        )
        assert built_run_id == run_id
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        for index, content_id in enumerate(content_ids, start=1):
            _persist_single_source_export_fixture(
                tmp_path,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
                variant=index,
            )
        materialize_aps_report_export_package_handoff(db, session_id=session_id)
        db.commit()

        malformed_failure_id = aps_package_contract.derive_failure_package_id(
            source_locator="malformed-scoped-artifact",
            error_code="malformed_scoped_artifact",
        )
        malformed_failure_path = aps_package_module.evidence_report_export_package_failure_artifact_path(
            owner_run_id=run_id,
            evidence_report_export_package_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        gate_report = aps_package_gate_module.validate_evidence_report_export_package_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "evidence_report_export_package_gate_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        assert gate_report["checks"][0]["failure_refs"] == [str(malformed_failure_path)]
        assert aps_package_contract.APS_GATE_FAILURE_FAILURE_SCHEMA in gate_report["checks"][0]["reasons"]
        assert len(gate_report["checks"][0]["evidence_report_export_package_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_evidence_report_export_package_gate_discovers_malformed_scoped_artifact_without_explicit_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        healthy_run_id = "run-aps-export-package-healthy"
        session_id, built_run_id, target_id, content_ids = _build_multisource_packaged_session(
            db,
            tmp_path,
            run_id=healthy_run_id,
        )
        assert built_run_id == healthy_run_id
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()
        for index, content_id in enumerate(content_ids, start=1):
            _persist_single_source_export_fixture(
                tmp_path,
                run_id=healthy_run_id,
                target_id=target_id,
                content_id=content_id,
                variant=f"healthy-{index}",
            )
        materialize_aps_report_export_package_handoff(db, session_id=session_id)
        db.commit()

        malformed_run_id = "run/aps export package:mixed"
        malformed_failure_id = aps_package_contract.derive_failure_package_id(
            source_locator="mixed-malformed-scoped-artifact",
            error_code="mixed_malformed_scoped_artifact",
        )
        malformed_failure_path = aps_package_module.evidence_report_export_package_failure_artifact_path(
            owner_run_id=malformed_run_id,
            evidence_report_export_package_id=malformed_failure_id,
            reports_dir=settings.connector_reports_dir,
        )
        malformed_failure_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_failure_path.write_text("{not-json", encoding="utf-8")

        discovered_runs = aps_package_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert len(discovered_runs) == 2

        gate_report = aps_package_gate_module.validate_evidence_report_export_package_gate(
            run_ids=None,
            limit=10,
            report_path=tmp_path / "evidence_report_export_package_gate_mixed_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        malformed_check = next(
            check for check in gate_report["checks"] if str(malformed_failure_path) in check["failure_refs"]
        )
        assert aps_package_contract.APS_GATE_FAILURE_FAILURE_SCHEMA in malformed_check["reasons"]
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_package_handoff_fails_closed_without_multisource_package(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _target_id, _content_ids = _build_multisource_packaged_session(db, tmp_path)

        with pytest.raises(
            Layer3ApsReportExportPackageHandoffError,
            match="missing the APS multisource admission package",
        ):
            materialize_aps_report_export_package_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.package_kind
                == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF
            )
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_package_handoff_fails_closed_on_missing_matched_export(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, target_id, content_ids = _build_multisource_packaged_session(db, tmp_path)
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        _persist_single_source_export_fixture(
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_ids[0],
            variant="only-one",
        )

        with pytest.raises(
            Layer3ApsReportExportPackageHandoffError,
            match="could not resolve a persisted export",
        ):
            materialize_aps_report_export_package_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.package_kind
                == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF
            )
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_report_export_package_handoff_fails_closed_on_duplicate_export_match(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, target_id, content_ids = _build_multisource_packaged_session(db, tmp_path)
        materialize_aps_multisource_admission(db, session_id=session_id)
        db.commit()

        _persist_single_source_export_fixture(
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_ids[0],
            variant="dup-a",
        )
        _persist_single_source_export_fixture(
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_ids[0],
            variant="dup-b",
        )
        _persist_single_source_export_fixture(
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_ids[1],
            variant="ok",
        )

        with pytest.raises(
            Layer3ApsReportExportPackageHandoffError,
            match="multiple persisted exports for admitted source identity",
        ):
            materialize_aps_report_export_package_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.package_kind
                == PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF
            )
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
