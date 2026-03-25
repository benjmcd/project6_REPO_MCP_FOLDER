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
from app.services import nrc_aps_context_dossier  # noqa: E402
from app.services import nrc_aps_context_dossier_contract as contract  # noqa: E402
from app.services import nrc_aps_context_dossier_gate  # noqa: E402
from app.services import nrc_aps_context_packet  # noqa: E402
from test_nrc_aps_context_dossier import _patch_runtime_settings, _persisted_artifacts, _seed_report_index_rows  # noqa: E402


def test_context_dossier_gate_pass_and_fail_on_counter_drift(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings(monkeypatch, tmp_path)

        class _GateSettings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_context_dossier_gate, "settings", _GateSettings())
        monkeypatch.setattr(
            nrc_aps_context_dossier_gate,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": "run-context-dossier-gate-1"}],
        )

        run_id = "run-context-dossier-gate-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        export_a = _persisted_artifacts(db, run_id=run_id, query="alpha")["export"]
        export_b = _persisted_artifacts(db, run_id=run_id, query="delta")["export"]
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

        pass_report = nrc_aps_context_dossier_gate.validate_context_dossier_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "pass_report.json",
            require_runs=True,
        )
        assert pass_report["passed"] is True

        dossier_path = Path(dossier["context_dossier_ref"])
        tampered = json.loads(dossier_path.read_text(encoding="utf-8"))
        tampered["total_constraints"] = 999
        tampered["context_dossier_checksum"] = contract.compute_context_dossier_checksum(tampered)
        dossier_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8-sig")

        fail_report = nrc_aps_context_dossier_gate.validate_context_dossier_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "fail_report.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_COUNTERS in reasons or contract.APS_GATE_FAILURE_DERIVATION_DRIFT in reasons
    finally:
        db.close()
        engine.dispose()


def test_context_dossier_gate_allow_empty_behavior(monkeypatch, tmp_path: Path):
    class _Settings:
        connector_reports_dir = str(tmp_path)
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr(nrc_aps_context_dossier_gate, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_context_dossier_gate, "_load_candidate_runs", lambda run_ids, limit: [])

    fail_closed = nrc_aps_context_dossier_gate.validate_context_dossier_gate(
        run_ids=None,
        limit=5,
        report_path=tmp_path / "empty_fail_closed.json",
        require_runs=True,
    )
    assert fail_closed["passed"] is False
    assert fail_closed["no_runs_failure"] is True

    allow_empty = nrc_aps_context_dossier_gate.validate_context_dossier_gate(
        run_ids=None,
        limit=5,
        report_path=tmp_path / "empty_allow.json",
        require_runs=False,
    )
    assert allow_empty["passed"] is True
