from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import local_profile_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "local_profile_acceptance.py"
RUNBOOK = ROOT / "docs" / "local-profile-ops.md"
ACCEPTANCE_TIMEOUT_SECONDS = 520


def test_local_profile_child_json_tolerates_dependency_stdout_warning(
    monkeypatch,
    tmp_path: Path,
) -> None:
    result = subprocess.CompletedProcess(
        args=[sys.executable],
        returncode=0,
        stdout='warning: dependency notice\n{"ok": true}\n',
        stderr="",
    )
    monkeypatch.setattr(acceptance.subprocess, "run", lambda *_args, **_kwargs: result)

    payload = acceptance._run_child(
        "seed",
        tmp_path / "local-profile.db",
        tmp_path / "storage",
    )

    assert payload == {"ok": True}


def test_local_profile_acceptance_script_proves_install_restart_and_restore(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--work-dir",
            str(tmp_path / "local-profile"),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=ACCEPTANCE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, (
        f"local profile acceptance failed with {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )

    payload = json.loads(result.stdout)
    assert payload["schema_id"] == "project6.local_profile_acceptance.v1"
    assert payload["profile"] == {
        "DEPLOYMENT_MODE": "local",
        "AUTH_OWNER": "none",
        "database": "sqlite",
        "proxy": "none",
    }
    assert payload["claims"] == {
        "install_run": "passed",
        "restart_survival": "passed",
        "backup_restore": "passed",
        "upgrade": "not_claimed",
    }
    assert payload["source_fidelity"]["content_hash"]
    assert payload["source_fidelity"]["source_row_count"] == 7
    assert payload["source_fidelity"]["dropped_row_count"] == 1
    assert payload["restored"]["analysis_run_id"] == payload["restart"]["analysis_run_id"]
    assert payload["restored"]["content_hash"] == payload["source_fidelity"]["content_hash"]
    assert payload["restored"]["dataframe_reads"]["raw_profile_count"] > 0
    assert payload["restored"]["dataframe_reads"]["transformed_profile_count"] > 0
    assert payload["artifact_hashes"]
    assert payload["backup"]["original_runtime_relocated"] is True


def test_local_profile_runbook_records_selected_l05_subcontracts() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for phrase in [
        "DEPLOYMENT_MODE=local",
        "AUTH_OWNER=none",
        "SQLite",
        "no proxy",
        "install/run",
        "restart-survival",
        "backup/restore",
        "UPGRADE: not claimed",
        "scripts/local_profile_acceptance.py",
    ]:
        assert phrase in text


def test_local_profile_acceptance_refuses_hidden_workstation_state(tmp_path: Path) -> None:
    work_dir = tmp_path / "local-profile"
    work_dir.mkdir()
    (work_dir / "stale.db").write_text("preexisting state", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--work-dir",
            str(work_dir),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "work directory must be empty" in result.stderr
