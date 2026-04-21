from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import review_nrc_aps_gate_reports as gate_reports


def _write_summary(runtime_root: Path, *, run_id: str) -> None:
    payload = {
        "schema_id": "aps.local_corpus_e2e_summary.v1",
        "schema_version": 1,
        "run_id": run_id,
        "passed": True,
        "database_path": "lc.db",
        "storage_dir": "storage",
        "submission": {"submitted_at": "2026-04-21T00:00:00Z"},
        "run_detail": {"completed_at": "2026-04-21T00:05:00Z"},
        "gate_results": {},
    }
    (runtime_root / "local_corpus_e2e_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_run_gate_reports_for_run_records_all_gate_results(monkeypatch, tmp_path):
    database_path = tmp_path / "lc.db"
    database_path.write_text("", encoding="utf-8")
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    report_dir = tmp_path / "gate_reports"

    calls: list[dict[str, object]] = []

    def fake_run(command, cwd, env, capture_output, text):
        del cwd, capture_output, text
        report_path = Path(command[command.index("--report") + 1])
        gate_name = report_path.stem
        passed = gate_name != "context_dossier"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps({"passed": passed, "checked_runs": 1}), encoding="utf-8")
        calls.append(
            {
                "command": list(command),
                "database_url": str(env.get("DATABASE_URL") or ""),
                "storage_dir": str(env.get("STORAGE_DIR") or ""),
                "db_init_mode": str(env.get("DB_INIT_MODE") or ""),
            }
        )
        return subprocess.CompletedProcess(command, 0 if passed else 1, stdout=f"{gate_name}\n", stderr="" if passed else "failed\n")

    monkeypatch.setattr(gate_reports.subprocess, "run", fake_run)

    result = gate_reports.run_gate_reports_for_run(
        run_id="run-123",
        report_dir=report_dir,
        database_path=database_path,
        storage_dir=storage_dir,
        python_executable=sys.executable,
    )

    assert len(calls) == len(gate_reports.GATE_REPORT_SPECS)
    assert result["passed"] is False
    assert result["gate_results"]["artifact_ingestion"]["passed"] is True
    assert result["gate_results"]["context_dossier"]["passed"] is False
    assert all(Path(str(item["report_path"])).parent == report_dir.resolve() for item in result["gate_results"].values())
    assert all(str(item["database_url"]).startswith("sqlite:///") for item in calls)
    assert all(str(item["storage_dir"]) == str(storage_dir.resolve()) for item in calls)
    assert all(str(item["db_init_mode"]) == "none" for item in calls)


def test_refresh_review_gate_reports_updates_summary_from_explicit_review_root(monkeypatch, tmp_path):
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    (runtime_root / "lc.db").write_text("", encoding="utf-8")
    (runtime_root / "storage").mkdir()
    _write_summary(runtime_root, run_id="run-123")

    fake_gate_results = {
        "artifact_ingestion": {
            "script": "nrc_aps_artifact_ingestion_gate.py",
            "report_path": str((runtime_root / "gate_reports" / "artifact_ingestion.json").resolve()),
            "passed": True,
            "checked_runs": 1,
            "stdout": "",
            "stderr": "",
        }
    }

    def fake_run_gate_reports_for_run(**kwargs):
        assert kwargs["run_id"] == "run-123"
        assert Path(str(kwargs["report_dir"])).resolve() == (runtime_root / "gate_reports").resolve()
        return {
            "run_id": "run-123",
            "report_dir": str((runtime_root / "gate_reports").resolve()),
            "passed": True,
            "gate_results": fake_gate_results,
        }

    monkeypatch.setattr(gate_reports, "run_gate_reports_for_run", fake_run_gate_reports_for_run)

    result = gate_reports.refresh_review_gate_reports(run_id="run-123", review_root=runtime_root)
    updated_summary = json.loads((runtime_root / "local_corpus_e2e_summary.json").read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert result["review_root"] == str(runtime_root.resolve())
    assert updated_summary["gate_results"] == fake_gate_results


def test_refresh_review_gate_reports_fails_closed_on_run_mismatch(tmp_path):
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    (runtime_root / "lc.db").write_text("", encoding="utf-8")
    (runtime_root / "storage").mkdir()
    _write_summary(runtime_root, run_id="run-abc")

    with pytest.raises(ValueError, match="does not match requested run_id"):
        gate_reports.refresh_review_gate_reports(run_id="run-xyz", review_root=runtime_root)


def test_local_corpus_e2e_help_bootstraps_backend_imports():
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "run_nrc_aps_local_corpus_e2e.py"), "--help"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
