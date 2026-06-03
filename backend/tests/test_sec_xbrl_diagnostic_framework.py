from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = ROOT / "diagnostics" / "assessment"


def test_framework_migrated_diagnostic_reports_remain_byte_stable(tmp_path: Path) -> None:
    checked = []
    for module_name, diagnostic_path, report_path in _framework_migrated_reports():
        diagnostic = _module_from_path(module_name, diagnostic_path)
        generated = _build_report(diagnostic)
        regenerated_path = tmp_path / report_path.name
        regenerated_path.write_text(json.dumps(generated, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        assert regenerated_path.read_bytes() == report_path.read_bytes(), report_path.relative_to(ROOT).as_posix()
        checked.append(report_path.relative_to(ROOT).as_posix())

    assert len(checked) >= 11
    assert checked == sorted(checked)
    assert "diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-default-on-runtime-report.json" in checked


def test_framework_matches_pilot_criterion_and_blocking_shapes() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )
    criteria = [
        framework.criterion("ready", passed=True, evidence={"count": 1}, blocked_reason="unused"),
        framework.criterion("blocked", passed=False, evidence={"count": 0}, blocked_reason="missing_evidence"),
    ]

    assert criteria == [
        {
            "criterion": "ready",
            "state": "passed",
            "blocked_reason": None,
            "evidence": {"count": 1},
        },
        {
            "criterion": "blocked",
            "state": "blocked",
            "blocked_reason": "missing_evidence",
            "evidence": {"count": 0},
        },
    ]
    assert framework.blocking_reasons(criteria) == [
        {
            "criterion": "blocked",
            "reason": "missing_evidence",
            "evidence": {"count": 0},
        }
    ]
    assert framework.decision(criteria[:1], ready="ready_decision", blocked="blocked_decision") == "ready_decision"
    assert framework.decision(criteria, ready="ready_decision", blocked="blocked_decision") == "blocked_decision"


def _module_from_path(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _build_report(diagnostic: ModuleType) -> dict:
    parameters = inspect.signature(diagnostic.build_report).parameters
    kwargs = {}
    if "source_root" in parameters:
        kwargs["source_root"] = ROOT
    if "report_paths" in parameters:
        kwargs["report_paths"] = {
            name: ROOT / path for name, path in diagnostic.DEFAULT_REQUIRED_REPORTS.items()
        }
    if "default_on_gate_report_path" in parameters:
        kwargs["default_on_gate_report_path"] = ROOT / diagnostic.DEFAULT_DEFAULT_ON_GATE_REPORT
    if "product_path_report_path" in parameters:
        kwargs["product_path_report_path"] = ROOT / diagnostic.DEFAULT_PRODUCT_PATH_REPORT
    if "real_product_runner_report_path" in parameters:
        kwargs["real_product_runner_report_path"] = ROOT / diagnostic.DEFAULT_REAL_PRODUCT_RUNNER_REPORT
    return diagnostic.build_report(**kwargs)


def _framework_migrated_reports() -> list[tuple[str, Path, Path]]:
    reports = []
    for diagnostic_path in sorted(ASSESSMENT.glob("sec-xbrl*.py")):
        if "sec_xbrl_diagnostic_framework" not in diagnostic_path.read_text(encoding="utf-8"):
            continue
        module_name = f"{diagnostic_path.stem.replace('-', '_')}_byte_stability"
        diagnostic = _module_from_path(module_name, diagnostic_path)
        report_path = ROOT / diagnostic.DEFAULT_OUTPUT
        assert report_path.exists(), diagnostic_path.relative_to(ROOT).as_posix()
        reports.append((module_name, diagnostic_path, report_path))
    return reports
