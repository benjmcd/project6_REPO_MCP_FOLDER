from __future__ import annotations

import ast
import importlib.util
import inspect
import json
from pathlib import Path
import re
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
    assert "diagnostics/assessment/sec-xbrl-sector-family-coverage-report.json" in checked


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


def test_resolved_fact_redaction_diagnostics_use_shared_binding_without_local_wrapper() -> None:
    targets = (
        ASSESSMENT / "sec-xbrl-canonical-retained-coherence.py",
        ASSESSMENT / "sec-xbrl-canonical-statement-organization.py",
    )

    for diagnostic_path in targets:
        text = diagnostic_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        local_wrappers = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_redaction_scan_payload"
        ]

        assert "diagnostic_resolved_fact_redaction_scan_payload" in text
        assert local_wrappers == [], diagnostic_path.relative_to(ROOT).as_posix()


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


def test_framework_report_envelope_preserves_shared_validate_only_shape() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_envelope_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )

    report = framework.report_envelope(
        schema_id="diagnostics.example.v1",
        target="example_target_v1",
        next_slice="example_next_slice_v1",
        decision="example_ready",
        source_mode="redacted_reference_summary",
        live_network_used=False,
        non_goals_preserved={"production_readiness_claimed": False},
    )

    assert report == {
        "schema_id": "diagnostics.example.v1",
        "target": "example_target_v1",
        "next_slice": "example_next_slice_v1",
        "decision": "example_ready",
        "source_mode": "redacted_reference_summary",
        "validate_only": True,
        "live_network_used": False,
        "non_goals_preserved": {"production_readiness_claimed": False},
    }


def test_framework_reference_identity_residuals_preserve_redacted_fixture_shape() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_residual_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )

    residuals = framework.reference_identity_residuals()

    assert residuals == [
        {
            "identity_id": "current_assets_plus_noncurrent_assets_equals_total_assets",
            "source_mode": "redacted_reference_summary",
            "residual_abs": "0",
            "relative_magnitude": "0E+2",
            "within_tolerance": True,
        },
        {
            "identity_id": "total_liabilities_plus_equity_equals_total_assets",
            "source_mode": "redacted_reference_summary",
            "residual_abs": "0",
            "relative_magnitude": "0E+2",
            "within_tolerance": True,
        },
        {
            "identity_id": "derived_total_liabilities_equals_assets_minus_equity_and_split",
            "source_mode": "redacted_reference_summary",
            "residual_abs": "0",
            "relative_magnitude": "0E+2",
            "within_tolerance": True,
        },
        {
            "identity_id": "revenue_minus_cost_of_sales_equals_gross_profit",
            "source_mode": "redacted_reference_summary",
            "residual_abs": "0",
            "relative_magnitude": "0E+2",
            "within_tolerance": True,
        },
        {
            "identity_id": "current_liabilities_plus_noncurrent_liabilities_equals_total_liabilities",
            "source_mode": "redacted_reference_summary",
            "residual_abs": "0",
            "relative_magnitude": "0E+2",
            "within_tolerance": True,
        },
    ]


def test_framework_mark_residual_magnitudes_redacted_preserves_summary_mutation() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_residual_marker_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )
    report = {
        "summary": {
            "statement_identity_residuals_committed_as_magnitudes_only": True,
            "other": "kept",
        }
    }

    framework.mark_residual_magnitudes_redacted(report)

    assert report == {
        "summary": {
            "other": "kept",
            "statement_identity_residual_magnitudes_redacted": True,
        }
    }


def test_framework_report_header_preserves_minimal_report_shape() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_header_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )

    report = framework.report_header(
        schema_id="diagnostics.example_header.v1",
        target="example_header_target_v1",
        next_slice="example_header_next_slice_v1",
        decision="example_header_ready",
        headline="Header-only diagnostic.",
        non_goals_preserved={"raw_values_committed": False},
    )

    assert report == {
        "schema_id": "diagnostics.example_header.v1",
        "target": "example_header_target_v1",
        "next_slice": "example_header_next_slice_v1",
        "decision": "example_header_ready",
        "headline": "Header-only diagnostic.",
        "non_goals_preserved": {"raw_values_committed": False},
    }


def test_framework_nonlocal_redaction_hit_classes_keep_custom_ref_policy() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_redaction_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )

    hits = framework.redaction_hit_classes(
        "operator@example.com 0000000000-00-000000",
        {"payload": [{"nested": {"raw_value": "redacted"}}], "owner_ref": "raw-owner"},
        regexes={
            "raw_operator_email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
            "raw_accession": re.compile(r"\b\d{10}-\d{2}-\d{6}\b"),
        },
        raw_keys={"payload", "raw_value"},
        authority_ref_invalid=lambda value: isinstance(value, dict) and value.get("owner_ref") == "raw-owner",
    )

    assert hits == [
        "raw_operator_email",
        "raw_accession",
        "raw_or_unreduced_authority_ref",
        "raw_or_local_authority_key",
        "raw_or_local_authority_key",
    ]


def test_framework_redacted_ref_preserves_nonlocal_ref_policy() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_redacted_ref_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )
    ref_pattern = re.compile(r"[a-z]+-ref-[a-z]+")
    forbidden_regexes = (
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        re.compile(r"\b\d{10}-\d{2}-\d{6}\b"),
        re.compile(r"[A-Za-z]:[\\/]"),
    )

    assert framework.redacted_ref(
        "owner-ref-alpha",
        ref_pattern=ref_pattern,
        forbidden_regexes=forbidden_regexes,
    ) is True
    assert framework.redacted_ref("", ref_pattern=ref_pattern, forbidden_regexes=forbidden_regexes) is False
    assert framework.redacted_ref(
        "owner@example.com",
        ref_pattern=ref_pattern,
        forbidden_regexes=forbidden_regexes,
    ) is False
    assert framework.redacted_ref(
        "0000000000-00-000000",
        ref_pattern=ref_pattern,
        forbidden_regexes=forbidden_regexes,
    ) is False
    assert framework.redacted_ref(
        "C:/Users/benny/raw.json",
        ref_pattern=ref_pattern,
        forbidden_regexes=forbidden_regexes,
    ) is False
    assert framework.redacted_ref(
        {"owner_ref": "owner-ref-alpha"},
        ref_pattern=ref_pattern,
        forbidden_regexes=forbidden_regexes,
    ) is False


def test_framework_text_redaction_scan_preserves_named_flags() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_text_redaction_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )

    scan = framework.text_redaction_scan(
        ["safe", "issuer@example.com", "0000000000-00-000000"],
        regexes={
            "raw_operator_contact_found": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
            "raw_accession_found": re.compile(r"\b\d{10}-\d{2}-\d{6}\b"),
            "raw_local_path_found": re.compile(r"[A-Za-z]:\\"),
        },
    )

    assert scan == {
        "passed": False,
        "raw_operator_contact_found": True,
        "raw_accession_found": True,
        "raw_local_path_found": False,
    }


def test_framework_raw_identity_hits_for_row_preserves_nested_paths_and_kinds() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_raw_identity_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )

    hits = framework.raw_identity_hits_for_row(
        {
            "safe": "redacted",
            "rows": [
                {"download_url": "https://sec.gov/Archives/edgar/data/example"},
                {"cik": 123456},
            ],
        },
        identity_kinds_for_value=lambda *, field_path, value: (
            ["url"]
            if "url" in field_path and "sec.gov" in value
            else ["cik"]
            if field_path.endswith("cik")
            else []
        ),
    )

    assert hits == [
        {"field": "rows[0].download_url", "kinds": ["url"]},
        {"field": "rows[1].cik", "kinds": ["cik"]},
    ]


def test_framework_label_contains_raw_identity_preserves_token_allowlist() -> None:
    framework = _module_from_path(
        "sec_xbrl_diagnostic_framework_label_identity_unit",
        ASSESSMENT / "sec_xbrl_diagnostic_framework.py",
    )

    assert framework.label_contains_raw_identity(
        "matrix 0000000000-00-000000",
        regexes=(re.compile(r"\b\d{10}-\d{2}-\d{6}\b"),),
    ) is True
    assert framework.label_contains_raw_identity(
        "matrix issuer ACME",
        regexes=(),
        token_pattern=re.compile(r"[A-Za-z][A-Za-z0-9]*"),
        admitted_tokens={"ACME"},
    ) is True
    assert framework.label_contains_raw_identity(
        "matrix issuer redacted",
        regexes=(),
        token_pattern=re.compile(r"[A-Za-z][A-Za-z0-9]*"),
        admitted_tokens={"ACME"},
    ) is False


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
