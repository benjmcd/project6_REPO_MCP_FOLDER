from __future__ import annotations

import importlib.util
from io import StringIO
import json
from pathlib import Path
import sqlite3

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "dual_live_initialize.py"
RUN_ID = "11111111-1111-4111-8111-111111111111"


def _tool_module():
    spec = importlib.util.spec_from_file_location("dual_live_initialize", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reservation_store_command_initializes_fresh_root_before_prepare(
    tmp_path: Path,
) -> None:
    tool = _tool_module()
    stdout = StringIO()
    root = tmp_path.resolve()

    code = tool.main(
        [
            "reservation-store",
            "--canonical-root",
            str(root),
            "--connector-run-id",
            RUN_ID,
        ],
        stdout=stdout,
    )

    assert code == 0
    assert stdout.getvalue() == f"INITIALIZED: {root / 'reservation.db'}\n"
    with sqlite3.connect(root / "reservation.db") as connection:
        assert connection.execute(
            "SELECT connector_run_id FROM connector_run"
        ).fetchone() == (RUN_ID,)


def test_authority_envelope_command_inserts_retired_sentinel_create_once(
    tmp_path: Path,
) -> None:
    tool = _tool_module()
    output = tmp_path / "authority.json"
    args = [
        "authority-envelope",
        "--output",
        str(output),
        "--campaign-id",
        "campaign-test",
        "--canonical-root",
        str(tmp_path.resolve()),
        "--connector-run-id",
        RUN_ID,
        "--source-commit",
        "1" * 40,
        "--interpreter-identity",
        "sha256:" + "2" * 64,
        "--authorization-digest",
        "sha256:" + "3" * 64,
        "--grant-digest",
        "sha256:" + "4" * 64,
    ]

    assert tool.main(args, stdout=StringIO()) == 0
    document = json.loads(output.read_bytes())
    assert document["wrapper_start_token_ref"] == "retired:sciencebase-live-v2"
    original = output.read_bytes()
    stderr = StringIO()
    assert tool.main(args, stdout=StringIO(), stderr=stderr) == 2
    assert stderr.getvalue() == "HOLD: authority_envelope_exists\n"
    assert output.read_bytes() == original


def test_initializer_has_no_live_runtime_or_effect_surface() -> None:
    source = TOOL.read_text(encoding="utf-8")

    assert "DUAL_LIVE_RUNTIME_ENABLED" not in source
    assert "prepare_dual_live_runtime" not in source
    assert "run_prepared_runtime" not in source
    assert "requests" not in source
    assert "wrapper-start-token" not in source


def test_project6_forwards_distinct_dual_live_initializer_action() -> None:
    script = (REPO_ROOT / "project6.ps1").read_text(encoding="utf-8-sig")

    assert '"initialize-dual-live"' in script.splitlines()[2]
    assert (
        '$DualLiveInitializePath = Join-Path $RepoRoot "tools\\dual_live_initialize.py"'
        in script
    )
    assert "& py \"-$PythonVersion\" $DualLiveInitializePath @ActionArgs" in script
