from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "tools" / "resolve-review-runtime.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def _write_runtime(root: Path, name: str, *, run_id: str, passed: bool = True) -> None:
    run_root = root / "lc_e2e" / name
    run_root.mkdir(parents=True)
    (run_root / "lc.db").write_text("", encoding="utf-8")
    (run_root / "local_corpus_e2e_summary.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "passed": passed,
                "completed_at_utc": "2026-05-03T01:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def _run_resolver(script: str) -> str:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not available")
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-Command", script],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def test_runtime_resolver_prefers_shared_repo_root_for_worktrees(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    lane_root = repo_root / "worktrees" / "lane-a"
    shared_root = repo_root / "backend" / "app" / "storage_test_runtime"
    local_root = lane_root / "backend" / "app" / "storage_test_runtime"
    lane_root.mkdir(parents=True)
    _write_runtime(shared_root, "shared-run", run_id="shared-run")
    _write_runtime(local_root, "local-run", run_id="local-run")

    script = f"""
. '{RESOLVER}'
$state = Resolve-ReviewRuntimeState -LaneRoot '{lane_root}'
$state.Source
$state.RunId
$state.RuntimeRoot
"""

    output = _run_resolver(script).splitlines()

    assert output[0] == "shared-repo-root"
    assert output[1] == "shared-run"
    assert Path(output[2]).resolve() == shared_root.resolve()


def test_runtime_resolver_keeps_explicit_root_authoritative(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    lane_root = repo_root / "worktrees" / "lane-a"
    shared_root = repo_root / "backend" / "app" / "storage_test_runtime"
    explicit_root = tmp_path / "explicit-runtime"
    lane_root.mkdir(parents=True)
    _write_runtime(shared_root, "shared-run", run_id="shared-run")
    _write_runtime(explicit_root, "explicit-run", run_id="explicit-run")

    script = f"""
. '{RESOLVER}'
$state = Resolve-ReviewRuntimeState -LaneRoot '{lane_root}' -RuntimeRoot '{explicit_root}'
$state.Source
$state.RunId
$state.RuntimeRoot
"""

    output = _run_resolver(script).splitlines()

    assert output[0] == "explicit"
    assert output[1] == "explicit-run"
    assert Path(output[2]).resolve() == explicit_root.resolve()


def test_runtime_resolver_does_not_default_to_legacy_pr45_path() -> None:
    assert "pr45-postmerge-audit" not in RESOLVER.read_text(encoding="utf-8")
