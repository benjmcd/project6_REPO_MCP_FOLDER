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
from app.services import nrc_aps_deterministic_challenge_artifact as aps_challenge_module
from app.services import (
    nrc_aps_deterministic_challenge_artifact_contract as aps_challenge_contract,
)
from app.services import (
    nrc_aps_deterministic_challenge_artifact_gate as aps_challenge_gate_module,
)
from app.services import nrc_aps_deterministic_insight_artifact as aps_insight_module
from app.services import (
    nrc_aps_deterministic_insight_artifact_contract as aps_insight_contract,
)
from app.services.layer3_aps_deterministic_challenge_artifact_handoff import (
    PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF,
    Layer3ApsDeterministicChallengeArtifactHandoffError,
    materialize_aps_deterministic_challenge_artifact_handoff,
)
from app.services.layer3_aps_deterministic_insight_artifact_handoff import (
    PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF,
    materialize_aps_deterministic_insight_artifact_handoff,
)
from test_layer3_aps_deterministic_insight_artifact_handoff import (
    _build_deterministic_insight_ready_session,
)
from test_layer3_aps_handoff import _make_session, _rows_by_kind


def _build_deterministic_challenge_ready_session(
    db,
    tmp_path: Path,
    *,
    run_id: str = "run-aps-deterministic-challenge-001",
) -> tuple[str, str, list[str], list[str]]:
    session_id, built_run_id, export_refs, context_packet_refs = (
        _build_deterministic_insight_ready_session(
            db,
            tmp_path,
            run_id=run_id,
        )
    )
    materialize_aps_deterministic_insight_artifact_handoff(db, session_id=session_id)
    db.commit()
    return session_id, built_run_id, export_refs, context_packet_refs


def _write_failure_artifact(
    *,
    owner_run_id: str,
    source_locator: str,
    error_code: str,
    source_payload: dict | None = None,
    raw_text: str | None = None,
) -> Path:
    failure_id = aps_challenge_contract.derive_failure_deterministic_challenge_artifact_id(
        source_locator=source_locator,
        error_code=error_code,
    )
    failure_path = aps_challenge_module.deterministic_challenge_failure_artifact_path(
        owner_run_id=owner_run_id,
        deterministic_challenge_artifact_id=failure_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_text is not None:
        failure_path.write_text(raw_text, encoding="utf-8")
        return failure_path

    source_summary = {
        "deterministic_insight_artifact_id": None,
        "deterministic_insight_artifact_checksum": None,
        "deterministic_insight_artifact_ref": None,
    }
    if isinstance(source_payload, dict) and source_payload:
        source_summary = {
            "deterministic_insight_artifact_id": (
                str(source_payload.get("deterministic_insight_artifact_id") or "").strip() or None
            ),
            "deterministic_insight_artifact_checksum": (
                str(source_payload.get("deterministic_insight_artifact_checksum") or "").strip()
                or None
            ),
            "deterministic_insight_artifact_ref": (
                str(
                    source_payload.get("_deterministic_insight_artifact_ref")
                    or source_payload.get("deterministic_insight_artifact_ref")
                    or ""
                ).strip()
                or None
            ),
        }

    failure_payload = {
        "schema_id": aps_challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_FAILURE_SCHEMA_ID,
        "schema_version": aps_challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION,
        "generated_at_utc": "2026-04-20T00:00:00Z",
        "deterministic_challenge_artifact_id": failure_id,
        **aps_challenge_contract.ruleset_identity_payload(),
        "challenge_mode": aps_challenge_contract.APS_DETERMINISTIC_CHALLENGE_MODE,
        "owner_run_id": owner_run_id,
        "source_request": {
            "deterministic_insight_artifact_id": None,
            "deterministic_insight_artifact_ref": None,
            "persist_challenge_artifact": False,
        },
        "source_deterministic_insight_artifact": source_summary,
        "error_code": error_code,
        "error_message": f"synthetic {error_code}",
    }
    failure_payload["deterministic_challenge_artifact_checksum"] = (
        aps_challenge_contract.compute_deterministic_challenge_artifact_checksum(
            failure_payload
        )
    )
    failure_path.write_text(json.dumps(failure_payload, sort_keys=True), encoding="utf-8")
    return failure_path


def test_materialize_aps_deterministic_challenge_handoff_emits_row_without_runtime_db_writes(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, _export_refs, _context_packet_refs = (
            _build_deterministic_challenge_ready_session(
                db,
                tmp_path,
            )
        )

        before_run = db.get(ConnectorRun, run_id)
        before_query_plan = json.loads(json.dumps(before_run.query_plan_json or {}, sort_keys=True))

        result = materialize_aps_deterministic_challenge_artifact_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        source_row = rows[PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF]
        handoff_row = rows[PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == source_row.status
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, artifact_path = (
            aps_challenge_module.load_persisted_deterministic_challenge_artifact(
                deterministic_challenge_artifact_ref=handoff_row.payload_ref
            )
        )
        assert artifact_path == Path(handoff_row.payload_ref)
        assert (
            loaded_payload["schema_id"]
            == aps_challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID
        )
        source_insight = dict(loaded_payload.get("source_deterministic_insight_artifact") or {})
        assert source_insight["owner_run_id"] == run_id
        assert (
            source_insight["schema_id"]
            == aps_insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID
        )

        gate_report = aps_challenge_gate_module.validate_deterministic_challenge_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_challenge_gate.json",
            require_runs=True,
        )
        assert gate_report["passed"] is True

        after_run = db.get(ConnectorRun, run_id)
        after_query_plan = json.loads(json.dumps(after_run.query_plan_json or {}, sort_keys=True))
        assert after_query_plan == before_query_plan
        assert not dict((after_run.query_plan_json or {})).get(
            "aps_deterministic_challenge_artifact_report_refs"
        )
        assert not list(
            (after_run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_summaries")
            or []
        )

        source_insight_payload, _insight_path = (
            aps_insight_module.load_persisted_deterministic_insight_artifact(
                deterministic_insight_artifact_ref=source_row.payload_ref
            )
        )
        assert handoff_row.summary_json["aps_target_family"] == "deterministic_challenge_artifact"
        assert (
            handoff_row.summary_json["aps_schema_id"]
            == aps_challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID
        )
        assert (
            handoff_row.summary_json["deterministic_challenge_artifact_id"]
            == loaded_payload["deterministic_challenge_artifact_id"]
        )
        assert handoff_row.summary_json["deterministic_challenge_artifact_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF
        ]
        assert handoff_row.summary_json["source_package_refs_json"] == {
            PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF: source_row.payload_ref
        }
        assert (
            handoff_row.summary_json["source_deterministic_insight_artifact_id"]
            == source_insight_payload["deterministic_insight_artifact_id"]
        )
        assert (
            handoff_row.summary_json["source_context_dossier_id"]
            == source_insight["source_context_dossier_id"]
        )
        assert handoff_row.summary_json["source_finding_counts"] == source_insight["finding_counts"]
        assert handoff_row.summary_json["challenge_counts"] == loaded_payload["challenge_counts"]
        assert (
            handoff_row.summary_json["disposition_counts"]
            == loaded_payload["disposition_counts"]
        )
        assert handoff_row.summary_json["handoff_status"]["runtime_db_writes_performed"] is False
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_deterministic_challenge_handoff_handles_non_path_safe_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps deterministic challenge:001"
        session_id, built_run_id, _export_refs, _context_packet_refs = (
            _build_deterministic_challenge_ready_session(
                db,
                tmp_path,
                run_id=run_id,
            )
        )
        assert built_run_id == run_id

        result = materialize_aps_deterministic_challenge_artifact_handoff(db, session_id=session_id)
        db.commit()

        gate_report = aps_challenge_gate_module.validate_deterministic_challenge_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_challenge_gate_non_path_safe.json",
            require_runs=True,
        )
        rows = _rows_by_kind(db)
        handoff_row = rows[PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF]
        loaded_payload, _artifact_path = (
            aps_challenge_module.load_persisted_deterministic_challenge_artifact(
                deterministic_challenge_artifact_ref=handoff_row.payload_ref
            )
        )

        assert gate_report["passed"] is True
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert loaded_payload["source_deterministic_insight_artifact"]["owner_run_id"] == run_id
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_challenge_gate_filters_scope_collisions_by_exact_owner_run_id(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "ab"
        foreign_run_id = "a/b"
        session_id, built_run_id, _export_refs, _context_packet_refs = (
            _build_deterministic_challenge_ready_session(
                db,
                tmp_path,
                run_id=run_id,
            )
        )
        assert built_run_id == run_id
        materialize_aps_deterministic_challenge_artifact_handoff(db, session_id=session_id)
        db.commit()

        _write_failure_artifact(
            owner_run_id=foreign_run_id,
            source_locator="foreign-scope-collision",
            error_code="foreign_scope_collision",
        )

        discovered_runs = aps_challenge_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert {str(row["run_id"]) for row in discovered_runs} == {run_id, foreign_run_id}

        gate_report = aps_challenge_gate_module.validate_deterministic_challenge_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_challenge_gate_scope_collision.json",
            require_runs=True,
        )

        assert gate_report["passed"] is True
        assert gate_report["checks"][0]["failure_refs"] == []
        assert len(gate_report["checks"][0]["deterministic_challenge_artifact_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_challenge_gate_handles_non_ascii_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        run_id = "run/aps deterministic challenge:\u00e901"
        failure_path = _write_failure_artifact(
            owner_run_id=run_id,
            source_locator="non-ascii-owner-run",
            error_code="non_ascii_owner_run",
        )

        discovered_runs = aps_challenge_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert [str(row["run_id"]) for row in discovered_runs] == [run_id]

        gate_report = aps_challenge_gate_module.validate_deterministic_challenge_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_challenge_gate_non_ascii.json",
            require_runs=True,
        )

        assert gate_report["passed"] is True
        assert gate_report["checked_runs"] == 1
        assert gate_report["checks"][0]["failure_refs"] == [str(failure_path)]
        assert gate_report["checks"][0]["reasons"] == []
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_challenge_gate_fails_closed_on_malformed_scoped_artifact(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/deterministic challenge:malformed"
        session_id, built_run_id, _export_refs, _context_packet_refs = (
            _build_deterministic_challenge_ready_session(
                db,
                tmp_path,
                run_id=run_id,
            )
        )
        assert built_run_id == run_id
        materialize_aps_deterministic_challenge_artifact_handoff(db, session_id=session_id)
        db.commit()

        malformed_failure_path = _write_failure_artifact(
            owner_run_id=run_id,
            source_locator="malformed-scoped-artifact",
            error_code="malformed_scoped_artifact",
            raw_text="{not-json",
        )

        gate_report = aps_challenge_gate_module.validate_deterministic_challenge_artifact_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "deterministic_challenge_gate_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        assert gate_report["checks"][0]["failure_refs"] == [str(malformed_failure_path)]
        assert (
            aps_challenge_contract.APS_GATE_FAILURE_FAILURE_SCHEMA
            in gate_report["checks"][0]["reasons"]
        )
        assert len(gate_report["checks"][0]["deterministic_challenge_artifact_refs"]) == 1
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_challenge_gate_discovers_malformed_scoped_artifact_without_explicit_run_ids(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        healthy_run_id = "run-aps-deterministic-challenge-healthy"
        session_id, built_run_id, _export_refs, _context_packet_refs = (
            _build_deterministic_challenge_ready_session(
                db,
                tmp_path,
                run_id=healthy_run_id,
            )
        )
        assert built_run_id == healthy_run_id
        materialize_aps_deterministic_challenge_artifact_handoff(db, session_id=session_id)
        db.commit()

        malformed_run_id = "run/aps deterministic challenge:mixed"
        malformed_failure_path = _write_failure_artifact(
            owner_run_id=malformed_run_id,
            source_locator="mixed-malformed-scoped-artifact",
            error_code="mixed_malformed_scoped_artifact",
            raw_text="{not-json",
        )

        discovered_runs = aps_challenge_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert len(discovered_runs) == 2

        gate_report = aps_challenge_gate_module.validate_deterministic_challenge_artifact_gate(
            run_ids=None,
            limit=10,
            report_path=tmp_path / "deterministic_challenge_gate_mixed_malformed_scope.json",
            require_runs=True,
        )

        assert gate_report["passed"] is False
        malformed_check = next(
            check for check in gate_report["checks"] if str(malformed_failure_path) in check["failure_refs"]
        )
        assert aps_challenge_contract.APS_GATE_FAILURE_FAILURE_SCHEMA in malformed_check["reasons"]
    finally:
        settings.storage_dir = original_storage_dir


def test_deterministic_challenge_gate_dedupes_raw_and_fallback_candidates_for_same_run(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        run_id = "run/aps deterministic challenge:dedupe"
        session_id, built_run_id, _export_refs, _context_packet_refs = (
            _build_deterministic_challenge_ready_session(
                db,
                tmp_path,
                run_id=run_id,
            )
        )
        assert built_run_id == run_id
        materialize_aps_deterministic_challenge_artifact_handoff(db, session_id=session_id)
        db.commit()

        malformed_failure_path = _write_failure_artifact(
            owner_run_id=run_id,
            source_locator="dedupe-malformed-scoped-artifact",
            error_code="dedupe_malformed_scoped_artifact",
            raw_text="{not-json",
        )

        discovered_runs = aps_challenge_gate_module._load_candidate_runs(run_ids=None, limit=10)
        assert [str(row["run_id"]) for row in discovered_runs] == [run_id]

        gate_report = aps_challenge_gate_module.validate_deterministic_challenge_artifact_gate(
            run_ids=None,
            limit=10,
            report_path=tmp_path / "deterministic_challenge_gate_dedupe_scope.json",
            require_runs=True,
        )

        assert gate_report["checked_runs"] == 1
        assert gate_report["failed_runs"] == 1
        assert gate_report["checks"][0]["run_id"] == run_id
        assert gate_report["checks"][0]["failure_refs"] == [str(malformed_failure_path)]
        assert (
            aps_challenge_contract.APS_GATE_FAILURE_FAILURE_SCHEMA
            in gate_report["checks"][0]["reasons"]
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_deterministic_challenge_handoff_fails_closed_without_insight_source(
    tmp_path: Path,
) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _run_id, _export_refs, _context_packet_refs = (
            _build_deterministic_insight_ready_session(
                db,
                tmp_path,
            )
        )

        with pytest.raises(
            Layer3ApsDeterministicChallengeArtifactHandoffError,
            match="missing the APS deterministic-insight handoff package",
        ):
            materialize_aps_deterministic_challenge_artifact_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.package_kind
                == PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF
            )
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
