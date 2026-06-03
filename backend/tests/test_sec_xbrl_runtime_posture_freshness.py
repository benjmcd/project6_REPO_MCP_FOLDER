from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

import pytest


ROOT = Path(__file__).resolve().parents[2]
POSTURE_PATH = ROOT / "diagnostics" / "assessment" / "sec_xbrl_runtime_posture.py"
REPORTS = (
    "diagnostics/assessment/sec-xbrl-canonical-projection-report.json",
    "diagnostics/assessment/sec-xbrl-canonical-comparability-report.json",
    "diagnostics/assessment/sec-xbrl-canonical-coverage-breadth-report.json",
    "diagnostics/assessment/sec-xbrl-canonical-retained-coherence-report.json",
    "diagnostics/assessment/sec-xbrl-canonical-statement-organization-report.json",
    "diagnostics/assessment/sec-xbrl-multi-period-projection-report.json",
    "diagnostics/assessment/sec-xbrl-sector-family-coverage-report.json",
    "diagnostics/assessment/sec-xbrl-statement-assembly-report.json",
)


def _posture_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_runtime_posture", POSTURE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_predecessor_reports_match_live_runtime_posture() -> None:
    posture_module = _posture_module()
    posture = posture_module.committed_runtime_posture(source_root=ROOT)
    expected_evidence = posture_module.runtime_posture_criterion_evidence(posture)
    expected_passed = posture_module.runtime_posture_criterion_passed(posture)

    checked = []
    for report_path in REPORTS:
        report = json.loads((ROOT / report_path).read_text(encoding="utf-8-sig"))
        criterion = _committed_runtime_criterion(report)
        _assert_runtime_posture_criterion_current(
            report_path=report_path,
            criterion=criterion,
            expected_evidence=expected_evidence,
            expected_passed=expected_passed,
        )
        checked.append(report_path)

    assert checked == list(REPORTS)


def test_runtime_posture_guard_rejects_stale_report_evidence() -> None:
    posture_module = _posture_module()
    posture = posture_module.committed_runtime_posture(source_root=ROOT)
    expected_evidence = posture_module.runtime_posture_criterion_evidence(posture)
    expected_passed = posture_module.runtime_posture_criterion_passed(posture)
    stale_evidence = dict(expected_evidence)
    stale_evidence["config_defaults_off"] = not stale_evidence["config_defaults_off"]
    stale = {
        "criterion": "committed_runtime_defaults_remain_off",
        "state": "passed" if expected_passed else "blocked",
        "evidence": stale_evidence,
    }

    with pytest.raises(AssertionError):
        _assert_runtime_posture_criterion_current(
            report_path="synthetic-stale-report.json",
            criterion=stale,
            expected_evidence=expected_evidence,
            expected_passed=expected_passed,
        )


def _committed_runtime_criterion(report: Mapping[str, Any]) -> Mapping[str, Any]:
    criteria = report.get("criteria")
    assert isinstance(criteria, list)
    matches = [item for item in criteria if item.get("criterion") == "committed_runtime_defaults_remain_off"]
    assert len(matches) == 1
    return matches[0]


def _assert_runtime_posture_criterion_current(
    *,
    report_path: str,
    criterion: Mapping[str, Any],
    expected_evidence: Mapping[str, bool],
    expected_passed: bool,
) -> None:
    assert criterion.get("evidence") == dict(expected_evidence), report_path
    assert criterion.get("state") == ("passed" if expected_passed else "blocked"), report_path
    if expected_passed:
        assert criterion.get("blocked_reason") is None, report_path
    else:
        assert criterion.get("blocked_reason"), report_path
