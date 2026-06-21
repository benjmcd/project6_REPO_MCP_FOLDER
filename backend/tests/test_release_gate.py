from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "release_readiness_check.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("release_readiness_check", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collect_ready_build_info_restores_temporary_environment(monkeypatch):
    runner = _load_runner()
    source_sha = "a" * 40

    monkeypatch.delenv("PROJECT6_SOURCE_SHA", raising=False)
    monkeypatch.delenv("DB_INIT_MODE", raising=False)
    monkeypatch.setattr(runner, "_current_git_sha", lambda _repo_root: source_sha)

    def ready():
        payload = {
            "status": "ready",
            "build": {
                "version": "0.2.0-rc1",
                "source_sha": os.environ.get("PROJECT6_SOURCE_SHA"),
            },
        }
        return SimpleNamespace(status_code=200, body=json.dumps(payload).encode("utf-8"))

    fake_main = SimpleNamespace(ready=ready, SessionLocal=None)
    monkeypatch.setattr(runner.importlib, "import_module", lambda name: fake_main)

    build_info = runner.collect_ready_build_info(REPO_ROOT)

    assert build_info["source_sha"] == source_sha
    assert "PROJECT6_SOURCE_SHA" not in os.environ
    assert "DB_INIT_MODE" not in os.environ
