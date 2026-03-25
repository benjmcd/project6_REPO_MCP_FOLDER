import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_artifact_ingestion  # noqa: E402
from app.services import nrc_aps_artifact_ingestion_gate  # noqa: E402


def test_validate_artifact_ingestion_gate_fail_closed_and_pass(tmp_path: Path, monkeypatch):
    run_id = "44444444-4444-4444-4444-444444444444"

    class _Settings:
        connector_reports_dir = str(tmp_path)

    monkeypatch.setattr(nrc_aps_artifact_ingestion_gate, "settings", _Settings())
    monkeypatch.setattr(
        nrc_aps_artifact_ingestion_gate,
        "_load_candidate_runs",
        lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
    )

    fail_report = nrc_aps_artifact_ingestion_gate.validate_artifact_ingestion_gate(
        run_ids=[run_id],
        limit=1,
        report_path=tmp_path / "fail.json",
        require_runs=True,
    )
    assert fail_report["passed"] is False

    target_payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
        run_id=run_id,
        target_id="target-1",
        accession_number="MLTEST",
        pipeline_mode="download_only",
        artifact_required_for_target_success=False,
        outcome_status=nrc_aps_artifact_ingestion.APS_ARTIFACT_OUTCOME_NOT_AVAILABLE,
        target_success=True,
        source_metadata_ref="/tmp/meta.json",
        evidence={
            "discovery_ref": "/tmp/discovery.json",
            "selection_ref": "/tmp/selection.json",
            "url_fields_checked": ["aps_normalized.url", "target.sciencebase_download_uri"],
        },
        availability_reason="no_url_in_metadata",
    )
    target_ref = nrc_aps_artifact_ingestion.target_artifact_path(
        run_id=run_id,
        target_id="target-1",
        reports_dir=tmp_path,
    )
    nrc_aps_artifact_ingestion.write_json_atomic(target_ref, target_payload)
    target_sha = hashlib.sha256(target_ref.read_bytes()).hexdigest()

    run_payload = nrc_aps_artifact_ingestion.build_run_artifact_payload(
        run_id=run_id,
        run_status="completed",
        pipeline_mode="download_only",
        artifact_required_for_target_success=False,
        selected_targets=1,
        target_artifacts=[{"target_id": "target-1", "status": "recommended", "ref": str(target_ref), "sha256": target_sha}],
    )
    run_ref = nrc_aps_artifact_ingestion.run_artifact_path(run_id=run_id, reports_dir=tmp_path)
    run_ref.write_text(json.dumps(run_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pass_report = nrc_aps_artifact_ingestion_gate.validate_artifact_ingestion_gate(
        run_ids=[run_id],
        limit=1,
        report_path=tmp_path / "pass.json",
        require_runs=True,
    )
    assert pass_report["passed"] is True
