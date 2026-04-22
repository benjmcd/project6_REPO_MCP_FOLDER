from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace


os.environ["DB_INIT_MODE"] = "none"
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from tools import nrc_ui_launch  # noqa: E402


def test_selection_storage_root_prefers_shared_repo_root_for_worktree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    lane_root = repo_root / "worktrees" / "lane-a"
    shared_storage_root = repo_root / "backend" / "app" / "storage_test_runtime"
    lane_root.mkdir(parents=True)
    shared_storage_root.mkdir(parents=True)

    selected = nrc_ui_launch._selection_storage_root(lane_root)

    assert selected == shared_storage_root.resolve()


def test_command_serve_uses_selection_storage_root_for_env(monkeypatch) -> None:
    captured: dict[str, object] = {}
    selected = nrc_ui_launch.LaunchCandidate(
        run_id="run-123",
        display_label="run-123 | demo",
        review_root=Path("C:/demo/storage_test_runtime/lc_e2e/run-123"),
        runtime_root=Path("C:/demo/storage_test_runtime"),
        database_path=Path("C:/demo/storage_test_runtime/lc_e2e/run-123/lc.db"),
        storage_dir=Path("C:/demo/storage_test_runtime/lc_e2e/run-123/storage"),
        selection_storage_root=Path("C:/shared/storage_test_runtime"),
        completed_at="2026-04-21T01:00:00Z",
        submitted_at="2026-04-21T00:00:00Z",
    )

    monkeypatch.setattr(
        nrc_ui_launch,
        "_select_candidate",
        lambda repo_root, *, run_id, latest: selected,
    )

    def fake_run(args, *, cwd, env, check):
        captured["args"] = list(args)
        captured["cwd"] = cwd
        captured["env"] = dict(env)
        captured["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(nrc_ui_launch.subprocess, "run", fake_run)

    exit_code = nrc_ui_launch.command_serve(
        SimpleNamespace(run_id="", latest=True, host="127.0.0.1", port=8098)
    )

    assert exit_code == 0
    assert captured["cwd"] == str(nrc_ui_launch.REPO_ROOT)
    assert captured["check"] is False
    assert captured["env"]["DATABASE_URL"] == "sqlite:///C:/demo/storage_test_runtime/lc_e2e/run-123/lc.db"
    assert captured["env"]["STORAGE_DIR"] == "C:\\shared\\storage_test_runtime"
    assert captured["env"]["DB_INIT_MODE"] == "none"


def test_command_verify_fails_when_default_run_mismatches(monkeypatch) -> None:
    expected = nrc_ui_launch.LaunchCandidate(
        run_id="run-expected",
        display_label="run-expected | demo",
        review_root=Path("C:/demo/storage_test_runtime/lc_e2e/run-expected"),
        runtime_root=Path("C:/demo/storage_test_runtime"),
        database_path=Path("C:/demo/storage_test_runtime/lc_e2e/run-expected/lc.db"),
        storage_dir=Path("C:/demo/storage_test_runtime/lc_e2e/run-expected/storage"),
        selection_storage_root=Path("C:/demo/storage_test_runtime"),
        completed_at="2026-04-21T01:00:00Z",
        submitted_at="2026-04-21T00:00:00Z",
    )

    monkeypatch.setattr(
        nrc_ui_launch,
        "_select_candidate",
        lambda repo_root, *, run_id, latest: expected,
    )

    def fake_read_json(url: str) -> dict:
        if url.endswith("/health"):
            return {"status": "ok"}
        return {
            "default_run_id": "run-other",
            "runs": [{"run_id": "run-expected"}, {"run_id": "run-other"}],
        }

    monkeypatch.setattr(nrc_ui_launch, "_read_json", fake_read_json)

    exit_code = nrc_ui_launch.command_verify(
        SimpleNamespace(run_id="", latest=True, host="127.0.0.1", port=8098)
    )

    assert exit_code == 1
