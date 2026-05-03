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
