from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "playwright.yml"


def test_release_lock_is_hash_pinned_and_keeps_ranges_as_source_of_truth() -> None:
    range_text = (BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8")
    lock_path = BACKEND_ROOT / "requirements.lock.txt"

    assert "uvicorn>=" in range_text
    assert lock_path.exists(), "PR1 must add a derived release lock, not replace ranges"

    lock_text = lock_path.read_text(encoding="utf-8")
    assert "source-file: backend/requirements.txt" in lock_text
    assert "--require-hashes" in lock_text
    assert "fastapi==0.137.2" in lock_text
    assert "--hash=sha256:" in lock_text

    requirement_lines = [
        line.strip()
        for line in lock_text.splitlines()
        if re.match(r"^[A-Za-z0-9_.-]+(?:\[.*\])?==", line.strip())
    ]
    assert requirement_lines
    assert all(">=" not in line for line in requirement_lines)
    assert all("--hash=sha256:" in line or line.endswith("\\") for line in requirement_lines)


def test_dockerfile_uses_digest_pinned_python312_release_base_and_lock() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile.app").read_text(encoding="utf-8")

    assert re.search(r"^FROM python:3\.12-slim@sha256:[0-9a-f]{64}$", dockerfile, re.MULTILINE)
    assert "requirements.lock.txt" in dockerfile
    assert "pip install --no-cache-dir --require-hashes -r requirements.lock.txt" in dockerfile


def test_fastapi_and_ready_expose_bounded_release_identity(monkeypatch) -> None:
    os.environ.setdefault("DB_INIT_MODE", "none")
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    main = importlib.import_module("main")

    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

        def execute(self, _statement):
            return None

    monkeypatch.setattr(main, "SessionLocal", lambda: _Session())

    assert main.app.version == main.BUILD_INFO["version"]
    response = main.ready()
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["build"] == {
        "version": main.BUILD_INFO["version"],
        "source_sha": main.BUILD_INFO["source_sha"],
    }
    assert set(payload["build"]) == {"version", "source_sha"}


def test_release_identity_ci_job_is_collected() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "release-lock-install" in workflow_text
    assert "backend/requirements.lock.txt" in workflow_text
    assert "pip install --require-hashes -r ./backend/requirements.lock.txt" in workflow_text
    assert "test_release_identity.py" in workflow_text
