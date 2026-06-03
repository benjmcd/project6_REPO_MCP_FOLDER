from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = ROOT / "diagnostics" / "assessment"
PILOT_REPORTS = (
    (
        "sec_xbrl_canonical_projection_byte_stability",
        ASSESSMENT / "sec-xbrl-canonical-projection.py",
        ASSESSMENT / "sec-xbrl-canonical-projection-report.json",
    ),
    (
        "sec_xbrl_canonical_comparability_byte_stability",
        ASSESSMENT / "sec-xbrl-canonical-comparability.py",
        ASSESSMENT / "sec-xbrl-canonical-comparability-report.json",
    ),
    (
        "sec_xbrl_statement_assembly_byte_stability",
        ASSESSMENT / "sec-xbrl-statement-assembly.py",
        ASSESSMENT / "sec-xbrl-statement-assembly-report.json",
    ),
)


def test_pilot_diagnostic_reports_remain_byte_stable(tmp_path: Path) -> None:
    checked = []
    for module_name, diagnostic_path, report_path in PILOT_REPORTS:
        diagnostic = _module_from_path(module_name, diagnostic_path)
        generated = diagnostic.build_report(source_root=ROOT)
        regenerated_path = tmp_path / report_path.name
        regenerated_path.write_text(json.dumps(generated, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        assert regenerated_path.read_bytes() == report_path.read_bytes(), report_path.relative_to(ROOT).as_posix()
        checked.append(report_path.relative_to(ROOT).as_posix())

    assert checked == [
        "diagnostics/assessment/sec-xbrl-canonical-projection-report.json",
        "diagnostics/assessment/sec-xbrl-canonical-comparability-report.json",
        "diagnostics/assessment/sec-xbrl-statement-assembly-report.json",
    ]


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
