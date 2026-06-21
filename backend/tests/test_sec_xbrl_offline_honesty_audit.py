from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "scripts" / "sec_xbrl_offline_honesty_audit.py"
MATRIX_PATH = ROOT / "config" / "support_matrix.yaml"


def _audit_module() -> Any:
    spec = importlib.util.spec_from_file_location("sec_xbrl_offline_honesty_audit", AUDIT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_offline_honesty_audit_reports_clean_pass(capsys) -> None:
    module = _audit_module()

    report = module.build_report(repo_root=ROOT)
    assert report["schema_id"] == module.REPORT_SCHEMA_ID
    assert report["status"] == "pass"
    assert report["errors"] == []
    assert {item["status"] for item in report["criteria"]} == {"pass"}

    assert module.main(["--repo-root", str(ROOT), "--matrix", str(MATRIX_PATH)]) == 0
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["status"] == "pass"


def test_sec_xbrl_offline_honesty_audit_fails_closed_on_synthetic_status_upgrade(tmp_path) -> None:
    module = _audit_module()
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    for capability in matrix["capabilities"]:
        if capability["id"] == "sec_live_network_egress":
            capability["status"] = "supported"
            break
    else:
        raise AssertionError("sec_live_network_egress capability missing from support matrix")

    mutated = tmp_path / "support_matrix.yaml"
    mutated.write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")

    report = module.build_report(matrix_path=mutated, repo_root=ROOT)
    assert report["status"] == "fail"
    assert any("sec_live_network_egress must be unsupported" in error for error in report["errors"])

    assert module.main(["--repo-root", str(ROOT), "--matrix", str(mutated)]) == 1
