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
from app.services import nrc_aps_context_dossier  # noqa: E402
from app.services import nrc_aps_context_dossier_contract as dossier_contract  # noqa: E402
from app.services import nrc_aps_context_packet  # noqa: E402
from app.services import nrc_aps_deterministic_insight_artifact as insight  # noqa: E402
from app.services import nrc_aps_deterministic_insight_artifact_contract as contract  # noqa: E402
from test_nrc_aps_context_dossier import _patch_runtime_settings, _persisted_artifacts, _seed_report_index_rows  # noqa: E402


def _patch_runtime_settings_all(monkeypatch, tmp_path: Path) -> None:
    _patch_runtime_settings(monkeypatch, tmp_path)

    class _Settings:
        connector_reports_dir = str(tmp_path)
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr(insight, "settings", _Settings())


def _persisted_context_dossier(db, *, run_id: str, query_a: str = "alpha", query_b: str = "delta") -> dict:
    export_a = _persisted_artifacts(db, run_id=run_id, query=query_a)["export"]
    export_b = _persisted_artifacts(db, run_id=run_id, query=query_b)["export"]
    packet_a = nrc_aps_context_packet.assemble_context_packet(
        db,
        request_payload={"evidence_report_export_id": export_a["evidence_report_export_id"], "persist_context_packet": True},
    )
    packet_b = nrc_aps_context_packet.assemble_context_packet(
        db,
        request_payload={"evidence_report_export_id": export_b["evidence_report_export_id"], "persist_context_packet": True},
    )
    dossier = nrc_aps_context_dossier.assemble_context_dossier(
        db,
        request_payload={
            "context_packet_refs": [packet_a["context_packet_ref"], packet_b["context_packet_ref"]],
            "persist_dossier": True,
        },
    )
    return {"packet_a": packet_a, "packet_b": packet_b, "dossier": dossier}


def _synthetic_context_packet(*, run_id: str, packet_id: str, packet_checksum: str, packet_ref: str) -> dict:
    return {
        "schema_id": "aps.context_packet.v1",
        "schema_version": 1,
        "generated_at_utc": "2026-03-12T00:00:00Z",
        "context_packet_id": packet_id,
        "context_packet_checksum": packet_checksum,
        "_context_packet_ref": packet_ref,
        "projection_contract_id": "aps_context_packet_projection_v1",
        "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
        "source_family": "evidence_report_export_package",
        "source_descriptor": {
            "source_id": f"source-{packet_id}",
            "source_checksum": f"source-sum-{packet_id}",
            "owner_run_id": run_id,
        },
        "objective": "normalize_persisted_source_for_downstream_consumption",
        "total_facts": 3,
        "total_caveats": 0,
        "total_constraints": 0,
        "total_unresolved_questions": 0,
    }


def test_persisted_deterministic_insight_artifact_is_immutable_and_updates_run_refs(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)
        run_id = "run-insight-service-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        seeded = _persisted_context_dossier(db, run_id=run_id)
        dossier = seeded["dossier"]

        preview = insight.assemble_deterministic_insight_artifact(
            db,
            request_payload={"context_dossier_id": dossier["context_dossier_id"], "persist_insight_artifact": False},
        )
        first = insight.assemble_deterministic_insight_artifact(
            db,
            request_payload={"context_dossier_id": dossier["context_dossier_id"], "persist_insight_artifact": True},
        )
        second = insight.assemble_deterministic_insight_artifact(
            db,
            request_payload={"context_dossier_ref": dossier["context_dossier_ref"], "persist_insight_artifact": True},
        )

        assert first["deterministic_insight_artifact_id"] == second["deterministic_insight_artifact_id"]
        assert first["deterministic_insight_artifact_ref"] == second["deterministic_insight_artifact_ref"]
        assert first["deterministic_insight_artifact_checksum"] == second["deterministic_insight_artifact_checksum"]
        assert preview["deterministic_insight_artifact_id"] == first["deterministic_insight_artifact_id"]
        assert Path(first["deterministic_insight_artifact_ref"]).exists()
        assert first["source_context_dossier"]["context_dossier_id"] == dossier["context_dossier_id"]

        persisted = insight.get_persisted_deterministic_insight_artifact(
            deterministic_insight_artifact_id=first["deterministic_insight_artifact_id"]
        )
        assert persisted["persisted"] is True
        assert persisted["findings"] == first["findings"]

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_deterministic_insight_artifact_report_refs") or {})
        assert refs.get("aps_deterministic_insight_artifacts") == [first["deterministic_insight_artifact_ref"]]
        assert refs.get("aps_deterministic_insight_artifact_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_deterministic_insight_artifact_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["deterministic_insight_artifact_id"] == first["deterministic_insight_artifact_id"]
    finally:
        db.close()
        engine.dispose()


def test_source_dossier_not_found_invalid_and_ambiguous_behaviors(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)

        with pytest.raises(insight.DeterministicInsightArtifactError) as missing_exc:
            insight.assemble_deterministic_insight_artifact(
                db,
                request_payload={"context_dossier_id": "missing-dossier", "persist_insight_artifact": False},
            )
        assert missing_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_NOT_FOUND
        assert missing_exc.value.status_code == 404

        run_id = "run-insight-service-2"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        dossier = _persisted_context_dossier(db, run_id=run_id)["dossier"]
        dossier_path = Path(dossier["context_dossier_ref"])
        tampered = json.loads(dossier_path.read_text(encoding="utf-8"))
        tampered["schema_id"] = "aps.context_dossier.v999"
        tampered["context_dossier_checksum"] = dossier_contract.compute_context_dossier_checksum(tampered)
        dossier_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(insight.DeterministicInsightArtifactError) as invalid_exc:
            insight.assemble_deterministic_insight_artifact(
                db,
                request_payload={"context_dossier_ref": str(dossier_path), "persist_insight_artifact": False},
            )
        assert invalid_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_INVALID
        assert invalid_exc.value.status_code == 422

        run_a = dossier_contract.build_context_dossier_payload(
            [
                _synthetic_context_packet(run_id="run-a", packet_id="packet-1", packet_checksum="sum-1", packet_ref="C:/tmp/a-1.json"),
                _synthetic_context_packet(run_id="run-a", packet_id="packet-2", packet_checksum="sum-2", packet_ref="C:/tmp/a-2.json"),
            ],
            generated_at_utc="2026-03-12T00:00:00Z",
        )
        run_b = dossier_contract.build_context_dossier_payload(
            [
                _synthetic_context_packet(run_id="run-b", packet_id="packet-1", packet_checksum="sum-1", packet_ref="C:/tmp/b-1.json"),
                _synthetic_context_packet(run_id="run-b", packet_id="packet-2", packet_checksum="sum-2", packet_ref="C:/tmp/b-2.json"),
            ],
            generated_at_utc="2026-03-12T00:00:00Z",
        )
        dossier_id = run_a["context_dossier_id"]
        assert dossier_id == run_b["context_dossier_id"]
        path_a = tmp_path / dossier_contract.expected_context_dossier_file_name(scope="run_aaa", context_dossier_id=dossier_id)
        path_b = tmp_path / dossier_contract.expected_context_dossier_file_name(scope="run_zzz", context_dossier_id=dossier_id)
        path_a.write_text(json.dumps(run_a, indent=2, sort_keys=True), encoding="utf-8")
        path_b.write_text(json.dumps(run_b, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(insight.DeterministicInsightArtifactError) as conflict_exc:
            insight.assemble_deterministic_insight_artifact(
                db,
                request_payload={"context_dossier_id": dossier_id, "persist_insight_artifact": False},
            )
        assert conflict_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_CONFLICT
        assert conflict_exc.value.status_code == 409
    finally:
        db.close()
        engine.dispose()


def test_run_scoped_persistence_prevents_collisions_and_id_only_get_fails_closed(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    class _Settings:
        connector_reports_dir = str(tmp_path)
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr(insight, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_context_dossier, "settings", _Settings())

    run_a = dossier_contract.build_context_dossier_payload(
        [
            _synthetic_context_packet(run_id="run-scope-a", packet_id="packet-1", packet_checksum="sum-1", packet_ref="C:/tmp/run-a-1.json"),
            _synthetic_context_packet(run_id="run-scope-a", packet_id="packet-2", packet_checksum="sum-2", packet_ref="C:/tmp/run-a-2.json"),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    run_b = dossier_contract.build_context_dossier_payload(
        [
            _synthetic_context_packet(run_id="run-scope-b", packet_id="packet-1", packet_checksum="sum-1", packet_ref="C:/tmp/run-b-1.json"),
            _synthetic_context_packet(run_id="run-scope-b", packet_id="packet-2", packet_checksum="sum-2", packet_ref="C:/tmp/run-b-2.json"),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    dossier_id = run_a["context_dossier_id"]
    path_a = tmp_path / dossier_contract.expected_context_dossier_file_name(scope="run_run-scope-a", context_dossier_id=dossier_id)
    path_b = tmp_path / dossier_contract.expected_context_dossier_file_name(scope="run_run-scope-b", context_dossier_id=dossier_id)
    path_a.write_text(json.dumps(run_a, indent=2, sort_keys=True), encoding="utf-8")
    path_b.write_text(json.dumps(run_b, indent=2, sort_keys=True), encoding="utf-8")

    try:
        artifact_a = insight.assemble_deterministic_insight_artifact(
            db,
            request_payload={"context_dossier_ref": str(path_a), "persist_insight_artifact": False},
        )
        artifact_b = insight.assemble_deterministic_insight_artifact(
            db,
            request_payload={"context_dossier_ref": str(path_b), "persist_insight_artifact": False},
        )
        assert artifact_a["deterministic_insight_artifact_id"] == artifact_b["deterministic_insight_artifact_id"]
        assert artifact_a["deterministic_insight_artifact_checksum"] != artifact_b["deterministic_insight_artifact_checksum"]

        persisted_a = contract.build_deterministic_insight_artifact_payload(run_a, generated_at_utc="2026-03-12T00:00:00Z")
        persisted_b = contract.build_deterministic_insight_artifact_payload(run_b, generated_at_utc="2026-03-12T00:00:00Z")
        insight_path_a = tmp_path / contract.expected_deterministic_insight_artifact_file_name(
            scope="run_run-scope-a",
            deterministic_insight_artifact_id=persisted_a["deterministic_insight_artifact_id"],
        )
        insight_path_b = tmp_path / contract.expected_deterministic_insight_artifact_file_name(
            scope="run_run-scope-b",
            deterministic_insight_artifact_id=persisted_b["deterministic_insight_artifact_id"],
        )
        insight_path_a.write_text(json.dumps(persisted_a, indent=2, sort_keys=True), encoding="utf-8")
        insight_path_b.write_text(json.dumps(persisted_b, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(insight.DeterministicInsightArtifactError) as exc_info:
            insight.get_persisted_deterministic_insight_artifact(
                deterministic_insight_artifact_id=persisted_a["deterministic_insight_artifact_id"]
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert exc_info.value.status_code == 409
    finally:
        db.close()
        engine.dispose()


def test_conflict_on_drifted_persisted_artifact_and_failure_artifact_only_when_persist_true(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)
        run_id = "run-insight-service-3"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        dossier = _persisted_context_dossier(db, run_id=run_id)["dossier"]

        preview = insight.assemble_deterministic_insight_artifact(
            db,
            request_payload={"context_dossier_ref": dossier["context_dossier_ref"], "persist_insight_artifact": False},
        )
        assert preview["persisted"] is False
        assert list(tmp_path.glob(f"run_{run_id}_*_aps_deterministic_insight_artifact_failure_v1.json")) == []

        persisted = insight.assemble_deterministic_insight_artifact(
            db,
            request_payload={"context_dossier_ref": dossier["context_dossier_ref"], "persist_insight_artifact": True},
        )
        artifact_path = Path(persisted["deterministic_insight_artifact_ref"])
        tampered = json.loads(artifact_path.read_text(encoding="utf-8"))
        tampered["findings"][0]["message"] = "tampered"
        tampered["deterministic_insight_artifact_checksum"] = contract.compute_deterministic_insight_artifact_checksum(tampered)
        artifact_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(insight.DeterministicInsightArtifactError) as exc_info:
            insight.assemble_deterministic_insight_artifact(
                db,
                request_payload={"context_dossier_ref": dossier["context_dossier_ref"], "persist_insight_artifact": True},
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert exc_info.value.status_code == 409
        failure_paths = sorted(tmp_path.glob(f"run_{run_id}_*_aps_deterministic_insight_artifact_failure_v1.json"))
        assert len(failure_paths) == 1
        failure_payload = json.loads(failure_paths[0].read_text(encoding="utf-8"))
        assert failure_payload["error_code"] == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert failure_payload["source_request"]["persist_insight_artifact"] is True
    finally:
        db.close()
        engine.dispose()
