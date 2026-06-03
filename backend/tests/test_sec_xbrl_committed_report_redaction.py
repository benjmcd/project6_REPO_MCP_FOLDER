from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_REDACTION_PATH = ROOT / "diagnostics" / "assessment" / "sec_xbrl_report_redaction.py"


def _report_redaction_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_report_redaction", REPORT_REDACTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_sec_xbrl_reports_do_not_carry_residual_magnitude_keys() -> None:
    redaction = _report_redaction_module()
    reports = sorted((ROOT / "diagnostics" / "assessment").glob("sec-xbrl*report.json"))

    findings: list[str] = []
    for report in reports:
        payload = json.loads(report.read_text(encoding="utf-8-sig"))
        findings.extend(
            f"{report.relative_to(ROOT)}::{path}"
            for path in _residual_magnitude_key_paths(payload, redaction.RESIDUAL_MAGNITUDE_KEYS)
        )

    assert reports
    assert findings == []


def _residual_magnitude_key_paths(value: Any, keys: set[str] | frozenset[str], path: str = "$") -> list[str]:
    if isinstance(value, dict):
        findings: list[str] = []
        for key, item in value.items():
            key_text = str(key)
            if key_text in keys:
                findings.append(f"{path}.{key_text}")
            findings.extend(_residual_magnitude_key_paths(item, keys, f"{path}.{key_text}"))
        return findings
    if isinstance(value, list):
        findings = []
        for index, item in enumerate(value):
            findings.extend(_residual_magnitude_key_paths(item, keys, f"{path}[{index}]"))
        return findings
    return []
