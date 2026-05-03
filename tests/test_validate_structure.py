from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import validate_structure


def test_root_surface_fails_unknown_top_level() -> None:
    issues = validate_structure.check_root_surface(["backend/main.py", "surprise/file.txt"])

    assert [issue.code for issue in issues] == ["UNKNOWN_ROOT_ENTRY"]
    assert issues[0].path == "surprise"


def test_json_syntax_reports_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{bad", encoding="utf-8")
    (tmp_path / "good.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

    issues = validate_structure.check_json_syntax(tmp_path, ["bad.json", "good.json"])

    assert [issue.code for issue in issues] == ["JSON_INVALID"]
    assert issues[0].severity == "error"


def test_local_path_refs_are_warnings(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("Use C:\\Users\\benny\\repo for old evidence.\n", encoding="utf-8")

    issues = validate_structure.scan_local_path_refs(tmp_path, ["doc.md"])

    assert [issue.code for issue in issues] == ["LOCAL_PATH_REF"]
    assert issues[0].severity == "warning"
    assert issues[0].line == 1


def test_codesight_freshness_warns_when_marker_missing(tmp_path: Path) -> None:
    (tmp_path / ".codesight").mkdir()

    issues = validate_structure.check_codesight_freshness(tmp_path)

    assert [issue.code for issue in issues] == ["CODESIGHT_FRESHNESS_MISSING"]
    assert issues[0].severity == "warning"


def test_codesight_freshness_accepts_complete_marker(tmp_path: Path) -> None:
    codesight = tmp_path / ".codesight"
    codesight.mkdir()
    (codesight / "freshness.json").write_text(
        json.dumps(
            {
                "source_commit": "abc123",
                "generated_at": "2026-05-03T00:00:00Z",
                "command": "generate-codesight",
            }
        ),
        encoding="utf-8",
    )

    assert validate_structure.check_codesight_freshness(tmp_path) == []
