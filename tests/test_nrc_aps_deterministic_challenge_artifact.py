import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "tests"))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.db.session import Base  # noqa: E402
from app.models import ConnectorRun  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_artifact as challenge  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_artifact_contract as contract  # noqa: E402
from app.services import nrc_aps_deterministic_insight_artifact as insight  # noqa: E402
from app.services import nrc_aps_deterministic_insight_artifact_contract as insight_contract  # noqa: E402
from test_nrc_aps_deterministic_insight_artifact import (  # noqa: E402
    _patch_runtime_settings_all as _patch_runtime_settings_all_insight,
    _persisted_context_dossier,
    _seed_report_index_rows,
    _synthetic_context_packet,
)


def _persisted_insight(db, *, run_id: str) -> dict:
    seeded = _persisted_context_dossier(db, run_id=run_id)
    artifact = insight.assemble_deterministic_insight_artifact(
        db,
        request_payload={
            "context_dossier_ref": seeded["dossier"]["context_dossier_ref"],
            "persist_insight_artifact": True,
        },
    )
    return {"dossier": seeded["dossier"], "insight": artifact}


def _patch_runtime_settings_all(monkeypatch, tmp_path: Path) -> None:
    _patch_runtime_settings_all_insight(monkeypatch, tmp_path)

    class _Settings:
        connector_reports_dir = str(tmp_path)
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr(challenge, "settings", _Settings())


def test_persisted_deterministic_challenge_artifact_is_immutable_and_updates_run_refs(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)
        run_id = "run-challenge-service-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        seeded = _persisted_insight(db, run_id=run_id)
        source_insight = seeded["insight"]

        preview = challenge.assemble_deterministic_challenge_artifact(
            db,
            request_payload={
                "deterministic_insight_artifact_id": source_insight["deterministic_insight_artifact_id"],
                "persist_challenge_artifact": False,
            },
        )
        first = challenge.assemble_deterministic_challenge_artifact(
            db,
            request_payload={
                "deterministic_insight_artifact_id": source_insight["deterministic_insight_artifact_id"],
                "persist_challenge_artifact": True,
            },
        )
        second = challenge.assemble_deterministic_challenge_artifact(
            db,
            request_payload={
                "deterministic_insight_artifact_ref": source_insight["deterministic_insight_artifact_ref"],
                "persist_challenge_artifact": True,
            },
        )

        assert first["deterministic_challenge_artifact_id"] == second["deterministic_challenge_artifact_id"]
        assert first["deterministic_challenge_artifact_ref"] == second["deterministic_challenge_artifact_ref"]
        assert preview["deterministic_challenge_artifact_id"] == first["deterministic_challenge_artifact_id"]
        assert Path(first["deterministic_challenge_artifact_ref"]).exists()

        persisted = challenge.get_persisted_deterministic_challenge_artifact(
            deterministic_challenge_artifact_id=first["deterministic_challenge_artifact_id"]
        )
        assert persisted["persisted"] is True
        assert persisted["challenges"] == first["challenges"]

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_report_refs") or {})
        assert refs.get("aps_deterministic_challenge_artifacts") == [first["deterministic_challenge_artifact_ref"]]
        assert refs.get("aps_deterministic_challenge_artifact_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["deterministic_challenge_artifact_id"] == first["deterministic_challenge_artifact_id"]
    finally:
        db.close()
        engine.dispose()


def test_source_insight_not_found_invalid_and_ambiguous_behaviors(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)

        with pytest.raises(challenge.DeterministicChallengeArtifactError) as missing_exc:
            challenge.assemble_deterministic_challenge_artifact(
                db,
                request_payload={"deterministic_insight_artifact_id": "missing-insight", "persist_challenge_artifact": False},
            )
        assert missing_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_NOT_FOUND
        assert missing_exc.value.status_code == 404

        invalid_path = tmp_path / "invalid_insight.json"
        invalid_path.write_text("{}", encoding="utf-8")
        with pytest.raises(challenge.DeterministicChallengeArtifactError) as invalid_exc:
            challenge.assemble_deterministic_challenge_artifact(
                db,
                request_payload={"deterministic_insight_artifact_ref": str(invalid_path), "persist_challenge_artifact": False},
            )
        assert invalid_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_INVALID
        assert invalid_exc.value.status_code == 422

        run_a_payload = insight_contract.build_deterministic_insight_artifact_payload(
            {
                "schema_id": "aps.context_dossier.v1",
                "schema_version": 1,
                "generated_at_utc": "2026-03-12T00:00:00Z",
                "context_dossier_id": "dossier-shared-id",
                "context_dossier_checksum": "sum-a",
                "_context_dossier_ref": "C:/tmp/run-a-dossier.json",
                "composition_contract_id": "aps_context_dossier_manifest_v1",
                "dossier_mode": "manifest_only",
                "owner_run_id": "run-api-a",
                "projection_contract_id": "aps_context_packet_projection_v1",
                "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
                "objective": "normalize_persisted_source_for_downstream_consumption",
                "source_family": "evidence_report_export_package",
                "source_packet_count": 2,
                "ordered_source_packets_sha256": "ordered-a",
                "total_facts": 3,
                "total_caveats": 0,
                "total_constraints": 0,
                "total_unresolved_questions": 0,
                "source_packets": [
                    _synthetic_context_packet(run_id="run-api-a", packet_id="packet-1", packet_checksum="sum-1", packet_ref="C:/tmp/run-a-packet-1.json"),
                    _synthetic_context_packet(run_id="run-api-a", packet_id="packet-2", packet_checksum="sum-2", packet_ref="C:/tmp/run-a-packet-2.json"),
                ],
            },
            generated_at_utc="2026-03-12T00:00:00Z",
        )
        run_b_payload = insight_contract.build_deterministic_insight_artifact_payload(
            {
                "schema_id": "aps.context_dossier.v1",
                "schema_version": 1,
                "generated_at_utc": "2026-03-12T00:00:00Z",
                "context_dossier_id": "dossier-shared-id",
                "context_dossier_checksum": "sum-b",
                "_context_dossier_ref": "C:/tmp/run-b-dossier.json",
                "composition_contract_id": "aps_context_dossier_manifest_v1",
                "dossier_mode": "manifest_only",
                "owner_run_id": "run-api-b",
                "projection_contract_id": "aps_context_packet_projection_v1",
                "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
                "objective": "normalize_persisted_source_for_downstream_consumption",
                "source_family": "evidence_report_export_package",
                "source_packet_count": 2,
                "ordered_source_packets_sha256": "ordered-b",
                "total_facts": 3,
                "total_caveats": 0,
                "total_constraints": 0,
                "total_unresolved_questions": 0,
                "source_packets": [
                    _synthetic_context_packet(run_id="run-api-b", packet_id="packet-1", packet_checksum="sum-1", packet_ref="C:/tmp/run-b-packet-1.json"),
                    _synthetic_context_packet(run_id="run-api-b", packet_id="packet-2", packet_checksum="sum-2", packet_ref="C:/tmp/run-b-packet-2.json"),
                ],
            },
            generated_at_utc="2026-03-12T00:00:00Z",
        )
        assert run_a_payload["deterministic_insight_artifact_id"] == run_b_payload["deterministic_insight_artifact_id"]
        path_a = tmp_path / insight_contract.expected_deterministic_insight_artifact_file_name(
            scope="run_aaa",
            deterministic_insight_artifact_id=run_a_payload["deterministic_insight_artifact_id"],
        )
        path_b = tmp_path / insight_contract.expected_deterministic_insight_artifact_file_name(
            scope="run_zzz",
            deterministic_insight_artifact_id=run_b_payload["deterministic_insight_artifact_id"],
        )
        path_a.write_text(json.dumps(run_a_payload, indent=2, sort_keys=True), encoding="utf-8")
        path_b.write_text(json.dumps(run_b_payload, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(challenge.DeterministicChallengeArtifactError) as conflict_exc:
            challenge.assemble_deterministic_challenge_artifact(
                db,
                request_payload={
                    "deterministic_insight_artifact_id": run_a_payload["deterministic_insight_artifact_id"],
                    "persist_challenge_artifact": False,
                },
            )
        assert conflict_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_CONFLICT
        assert conflict_exc.value.status_code == 409
    finally:
        db.close()
        engine.dispose()


def test_persisted_deterministic_challenge_artifact_conflicts_on_drift_and_records_failure(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)
        run_id = "run-challenge-service-2"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        seeded = _persisted_insight(db, run_id=run_id)
        source_insight = seeded["insight"]
        artifact = challenge.assemble_deterministic_challenge_artifact(
            db,
            request_payload={
                "deterministic_insight_artifact_ref": source_insight["deterministic_insight_artifact_ref"],
                "persist_challenge_artifact": True,
            },
        )
        artifact_path = Path(artifact["deterministic_challenge_artifact_ref"])
        tampered = json.loads(artifact_path.read_text(encoding="utf-8"))
        tampered["challenges"][0]["message"] = "tampered message"
        tampered["deterministic_challenge_artifact_checksum"] = contract.compute_deterministic_challenge_artifact_checksum(tampered)
        artifact_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(challenge.DeterministicChallengeArtifactError) as conflict_exc:
            challenge.assemble_deterministic_challenge_artifact(
                db,
                request_payload={
                    "deterministic_insight_artifact_ref": source_insight["deterministic_insight_artifact_ref"],
                    "persist_challenge_artifact": True,
                },
            )
        assert conflict_exc.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert conflict_exc.value.status_code == 409

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_report_refs") or {})
        failure_refs = refs.get("aps_deterministic_challenge_artifact_failures") or []
        assert len(failure_refs) == 1
        failure_path = Path(failure_refs[0])
        assert failure_path.exists()
        failure_payload = json.loads(failure_path.read_text(encoding="utf-8"))
        assert failure_payload["schema_id"] == contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_FAILURE_SCHEMA_ID
        assert failure_payload["error_code"] == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert failure_payload["source_deterministic_insight_artifact"]["deterministic_insight_artifact_id"] == source_insight["deterministic_insight_artifact_id"]
    finally:
        db.close()
        engine.dispose()
