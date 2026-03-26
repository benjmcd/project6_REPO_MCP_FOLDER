import json
import os
import sys
from pathlib import Path

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
from app.services import nrc_aps_deterministic_challenge_review_packet as review_packet  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_review_packet_contract as contract  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_review_packet_gate as gate  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_artifact as challenge  # noqa: E402
from test_nrc_aps_context_dossier import _seed_report_index_rows  # noqa: E402
from test_nrc_aps_deterministic_challenge_review_packet import _patch_runtime_settings_all, _persisted_challenge  # noqa: E402


def test_review_packet_gate_pass_and_fail_on_bucket_drift(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)

        class _GateSettings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(gate, "settings", _GateSettings())
        monkeypatch.setattr(review_packet, "settings", _GateSettings())
        monkeypatch.setattr(challenge, "settings", _GateSettings())
        monkeypatch.setattr(gate, "_load_candidate_runs", lambda run_ids, limit: [{"run_id": "run-review-gate-1"}])

        run_id = "run-review-gate-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        source_challenge = _persisted_challenge(db, run_id=run_id)["challenge"]
        packet = review_packet.assemble_deterministic_challenge_review_packet(
            db,
            request_payload={
                "deterministic_challenge_artifact_ref": source_challenge["deterministic_challenge_artifact_ref"],
                "persist_review_packet": True,
            },
        )

        pass_report = gate.validate_deterministic_challenge_review_packet_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "pass_report.json",
            require_runs=True,
        )
        assert pass_report["passed"] is True

        artifact_path = Path(packet["deterministic_challenge_review_packet_ref"])
        tampered = json.loads(artifact_path.read_text(encoding="utf-8"))
        tampered["blockers"].append(tampered["blockers"][0] if tampered["blockers"] else {"challenge_id": "fake", "check_id": "fake", "check_version": 1, "category": "fake", "severity": "critical", "disposition": "block", "matched_finding_count": 0, "source_finding_ids": [], "message": "fake", "evidence_pointers": []})
        tampered["blocker_count"] = len(tampered["blockers"])
        tampered["total_challenges"] = tampered["blocker_count"] + tampered["review_item_count"] + tampered["acknowledgement_count"]
        tampered["deterministic_challenge_review_packet_checksum"] = contract.compute_deterministic_challenge_review_packet_checksum(tampered)
        artifact_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        fail_report = gate.validate_deterministic_challenge_review_packet_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "fail_report.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_BLOCKERS in reasons or contract.APS_GATE_FAILURE_DERIVATION_DRIFT in reasons
    finally:
        db.close()
        engine.dispose()


def test_review_packet_gate_catches_source_summary_drift_and_allow_empty(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)

        class _GateSettings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(gate, "settings", _GateSettings())
        monkeypatch.setattr(review_packet, "settings", _GateSettings())
        monkeypatch.setattr(challenge, "settings", _GateSettings())
        monkeypatch.setattr(gate, "_load_candidate_runs", lambda run_ids, limit: [{"run_id": "run-review-gate-2"}])

        run_id = "run-review-gate-2"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        source_challenge = _persisted_challenge(db, run_id=run_id)["challenge"]
        packet = review_packet.assemble_deterministic_challenge_review_packet(
            db,
            request_payload={
                "deterministic_challenge_artifact_ref": source_challenge["deterministic_challenge_artifact_ref"],
                "persist_review_packet": True,
            },
        )

        artifact_path = Path(packet["deterministic_challenge_review_packet_ref"])
        tampered = json.loads(artifact_path.read_text(encoding="utf-8"))
        tampered["source_deterministic_challenge_artifact"]["total_challenges"] = 999
        tampered["deterministic_challenge_review_packet_checksum"] = contract.compute_deterministic_challenge_review_packet_checksum(tampered)
        artifact_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        fail_report = gate.validate_deterministic_challenge_review_packet_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "source_summary_drift.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        assert contract.APS_GATE_FAILURE_SOURCE_CHALLENGE_SUMMARY in fail_report["checks"][0]["reasons"]

        monkeypatch.setattr(gate, "_load_candidate_runs", lambda run_ids, limit: [])
        fail_closed = gate.validate_deterministic_challenge_review_packet_gate(
            run_ids=None,
            limit=5,
            report_path=tmp_path / "empty_fail_closed.json",
            require_runs=True,
        )
        assert fail_closed["passed"] is False
        assert fail_closed["no_runs_failure"] is True

        allow_empty = gate.validate_deterministic_challenge_review_packet_gate(
            run_ids=None,
            limit=5,
            report_path=tmp_path / "empty_allow.json",
            require_runs=False,
        )
        assert allow_empty["passed"] is True
    finally:
        db.close()
        engine.dispose()


def test_review_packet_gate_catches_checksum_drift(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)

        class _GateSettings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(gate, "settings", _GateSettings())
        monkeypatch.setattr(review_packet, "settings", _GateSettings())
        monkeypatch.setattr(challenge, "settings", _GateSettings())
        monkeypatch.setattr(gate, "_load_candidate_runs", lambda run_ids, limit: [{"run_id": "run-review-gate-3"}])

        run_id = "run-review-gate-3"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        source_challenge = _persisted_challenge(db, run_id=run_id)["challenge"]
        packet = review_packet.assemble_deterministic_challenge_review_packet(
            db,
            request_payload={
                "deterministic_challenge_artifact_ref": source_challenge["deterministic_challenge_artifact_ref"],
                "persist_review_packet": True,
            },
        )

        artifact_path = Path(packet["deterministic_challenge_review_packet_ref"])
        tampered = json.loads(artifact_path.read_text(encoding="utf-8"))
        tampered["deterministic_challenge_review_packet_checksum"] = "bad-checksum"
        artifact_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        fail_report = gate.validate_deterministic_challenge_review_packet_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "checksum_drift.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_CHECKSUM in reasons or contract.APS_GATE_FAILURE_ARTIFACT_SCHEMA in reasons
    finally:
        db.close()
        engine.dispose()
