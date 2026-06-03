from __future__ import annotations

import ast
import importlib.util
import inspect
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = ROOT / "diagnostics" / "assessment"

RUNTIME_BOUND_FRAMEWORK_REPORTS = {
    "diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json": (
        "historical offline product report import stores non-portable report-path and storage markers"
    ),
    "diagnostics/assessment/sec-xbrl-value-reveal-authority-provisioning-preflight-report.json": (
        "historical operator-exercise summary is bound to committed runtime inventory shape"
    ),
    "diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-run-report.json": (
        "historical configured-storage marker is derived from a local absolute runtime path"
    ),
}


def test_framework_migrated_diagnostic_reports_remain_byte_stable(tmp_path: Path) -> None:
    checked = []
    runtime_bound = []
    for module_name, diagnostic_path, report_path in _framework_migrated_reports():
        report_relative_path = report_path.relative_to(ROOT).as_posix()
        if report_relative_path in RUNTIME_BOUND_FRAMEWORK_REPORTS:
            runtime_bound.append(report_relative_path)
            continue

        diagnostic = _module_from_path(module_name, diagnostic_path)
        generated = _build_report(diagnostic)
        regenerated_path = tmp_path / report_path.name
        regenerated_path.write_text(json.dumps(generated, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        assert regenerated_path.read_bytes() == report_path.read_bytes(), report_relative_path
        checked.append(report_relative_path)

    assert len(checked) >= 22
    assert checked == sorted(checked)
    assert runtime_bound == sorted(RUNTIME_BOUND_FRAMEWORK_REPORTS)
    assert "diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-default-on-runtime-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-auth-owner-binding-strategy-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-default-on-gate-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-default-posture-decision-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-stratified-matrix-readiness-decision-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-multi-period-projection-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-statement-assembly-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-canonical-retained-coherence-report.json" in checked
    assert "diagnostics/assessment/sec-xbrl-canonical-statement-organization-report.json" in checked


def test_framework_runtime_bound_reports_are_explicitly_declared() -> None:
    migrated_reports = {
        report_path.relative_to(ROOT).as_posix()
        for _, _, report_path in _framework_migrated_reports()
    }

    assert set(RUNTIME_BOUND_FRAMEWORK_REPORTS).issubset(migrated_reports)
    for report_relative_path, reason in RUNTIME_BOUND_FRAMEWORK_REPORTS.items():
        assert reason
        report = json.loads((ROOT / report_relative_path).read_text(encoding="utf-8"))
        non_goals = report.get("non_goals_preserved", {})
        redaction = report.get("redaction", {})
        assert report.get("schema_id")
        assert report.get("target")
        assert non_goals.get("raw_values_committed", redaction.get("raw_values_committed")) is False
        assert (
            non_goals.get("raw_identity_committed", redaction.get("raw_identity_committed")) is False
            or redaction.get("identity_hash_only") is True
        )


def test_framework_rollout_has_no_local_criterion_or_blocking_helpers() -> None:
    local_helpers = []
    for diagnostic_path in sorted(ASSESSMENT.glob("sec-xbrl*.py")):
        tree = ast.parse(diagnostic_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in {"_criterion", "_blocking_reasons"}:
                local_helpers.append(f"{diagnostic_path.relative_to(ROOT).as_posix()}::{node.name}")

    assert local_helpers == []


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
    explicit_path_lists = {
        "value_report_paths": ("DEFAULT_VALUE_REPORT", "DEFAULT_EXPANDED_VALUE_REPORT"),
    }
    explicit_path_maps = {
        "report_paths": "DEFAULT_REQUIRED_REPORTS",
    }

    for name, parameter in parameters.items():
        if name == "source_root":
            kwargs[name] = ROOT
            continue

        if name in explicit_path_lists:
            kwargs[name] = [ROOT / getattr(diagnostic, constant) for constant in explicit_path_lists[name]]
            continue

        if name in explicit_path_maps:
            kwargs[name] = {
                key: ROOT / value for key, value in getattr(diagnostic, explicit_path_maps[name]).items()
            }
            continue

        if name.endswith("_path"):
            constant_base = name[: -len("_path")].upper()
            candidates = (f"DEFAULT_{constant_base}", constant_base)
            for constant in candidates:
                if hasattr(diagnostic, constant):
                    kwargs[name] = ROOT / getattr(diagnostic, constant)
                    break
            else:
                if parameter.default is inspect.Parameter.empty:
                    raise AssertionError(
                        f"{diagnostic.__name__}.build_report requires unsupported path parameter {name!r}"
                    )
            continue

        if parameter.default is inspect.Parameter.empty:
            raise AssertionError(f"{diagnostic.__name__}.build_report requires unsupported parameter {name!r}")

    return diagnostic.build_report(**kwargs)

def _framework_migrated_reports() -> list[tuple[str, Path, Path]]:
    reports = []
    for diagnostic_path in sorted(ASSESSMENT.glob("sec-xbrl*.py")):
        text = diagnostic_path.read_text(encoding="utf-8")
        if "sec_xbrl_diagnostic_framework" not in text:
            continue
        module_name = f"{diagnostic_path.stem.replace('-', '_')}_byte_stability"
        report_path = ROOT / _static_default_output(diagnostic_path, text)
        assert report_path.exists(), diagnostic_path.relative_to(ROOT).as_posix()
        reports.append((module_name, diagnostic_path, report_path))
    return reports


def _static_default_output(diagnostic_path: Path, text: str) -> Path:
    tree = ast.parse(text)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "DEFAULT_OUTPUT" for target in node.targets):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "Path"
            and value.args
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
        ):
            return Path(value.args[0].value)
        break

    raise AssertionError(f"{diagnostic_path.relative_to(ROOT).as_posix()} has no static DEFAULT_OUTPUT Path")
