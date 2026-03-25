import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_safeguard_gate  # noqa: E402
from app.services import nrc_aps_safeguards  # noqa: E402


def test_validate_safeguard_gate_fail_closed_and_pass(tmp_path: Path, monkeypatch):
    run_id = "22222222-2222-2222-2222-222222222222"

    class _Settings:
        connector_reports_dir = str(tmp_path)

    monkeypatch.setattr(nrc_aps_safeguard_gate, "settings", _Settings())
    monkeypatch.setattr(
        nrc_aps_safeguard_gate,
        "_load_candidate_runs",
        lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
    )

    fail_report = nrc_aps_safeguard_gate.validate_safeguard_gate(
        run_ids=[run_id],
        limit=1,
        report_path=tmp_path / "fail.json",
        require_runs=True,
    )
    assert fail_report["passed"] is False

    payload = {
        "schema_id": nrc_aps_safeguards.APS_SAFEGUARD_REPORT_SCHEMA_ID,
        "schema_version": nrc_aps_safeguards.APS_SAFEGUARD_REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "event_counts": {},
    }
    (tmp_path / f"{run_id}_aps_safeguard_v1.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    pass_report = nrc_aps_safeguard_gate.validate_safeguard_gate(
        run_ids=[run_id],
        limit=1,
        report_path=tmp_path / "pass.json",
        require_runs=True,
    )
    assert pass_report["passed"] is True

