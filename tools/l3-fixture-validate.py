from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD = (
    REPO_ROOT
    / "next_milestone_plans"
    / "Layer3_planning_docs"
    / "850_FIXTURE_VALIDATE_ONLY.md"
)
STRUCTURED_RECORD_HEADING = "## Structured Fixture Authority Record"
EXPECTED_STATES = ("pending", "selected", "frozen")
NULL_VALUES = {"null", "none"}
TRUE_VALUE = "true"
FALSE_VALUE = "false"
TOOL_STATUS_VALUES = {
    "pending",
    "selected",
    "deferred_absent_fixture_authority",
    "no_adopt_absent_fixture_authority",
}

FIXED_FIELDS = {
    "benchmark_fixture_authority_schema_id": (
        "layer3.sublayer3c_optional_tool_benchmark_fixture_authority.v1"
    ),
    "candidate_tools": "tabpfn,nrc_licensing_rag",
    "runtime_isolation_required": TRUE_VALUE,
    "default_dependency_allowed": FALSE_VALUE,
    "network_or_provider_call_allowed": FALSE_VALUE,
    "package_handoff_export_download_allowed": FALSE_VALUE,
    "runtime_behavior_change": FALSE_VALUE,
    "benchmark_execution_change": FALSE_VALUE,
    "fixture_materialization_change": FALSE_VALUE,
}

TOOL_STATUS_FIELDS = (
    "tabpfn_fixture_authority_status",
    "nrc_rag_fixture_authority_status",
)

TABPFN_FIELDS = (
    "tabpfn_fixture_authority",
    "tabpfn_source_authority",
    "tabpfn_fixture_kind",
    "tabpfn_target_column",
    "tabpfn_feature_columns",
    "tabpfn_task_type",
    "tabpfn_train_test_split",
    "tabpfn_leakage_checks",
    "tabpfn_row_count_band",
    "tabpfn_metric_family",
    "tabpfn_baseline_family",
    "tabpfn_no_adopt_threshold",
    "tabpfn_license_dependency_runtime_constraints",
)

NRC_RAG_FIELDS = (
    "nrc_rag_fixture_authority",
    "nrc_rag_query_set_authority",
    "nrc_rag_fixture_kind",
    "nrc_rag_query_ids",
    "nrc_rag_query_texts",
    "nrc_rag_answerability_labels",
    "nrc_rag_expected_source_identifiers",
    "nrc_rag_expected_source_spans",
    "nrc_rag_expected_refusal_behavior",
    "nrc_rag_citation_rubric",
    "nrc_rag_baseline_surface_set",
    "nrc_rag_no_adopt_threshold",
    "nrc_rag_dependency_provider_network_runtime_constraints",
)

SELECTION_FIELDS = TABPFN_FIELDS + NRC_RAG_FIELDS
CONTROL_FIELDS = ("selection_complete", "implementation_entry_freeze_written")
ALL_FIELDS = tuple(FIXED_FIELDS) + TOOL_STATUS_FIELDS + SELECTION_FIELDS + CONTROL_FIELDS


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    line: int | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "message": self.message,
        }
        if self.line is not None:
            payload["line"] = self.line
        return payload


@dataclass(frozen=True)
class ParsedRecord:
    values: dict[str, str]
    issues: tuple[ValidationIssue, ...]


def _extract_fenced_yaml_after_heading(text: str) -> tuple[str, list[ValidationIssue]]:
    heading_index = text.find(STRUCTURED_RECORD_HEADING)
    if heading_index < 0:
        return "", [
            ValidationIssue(
                "missing_heading",
                f"missing heading {STRUCTURED_RECORD_HEADING!r}",
            )
        ]

    section = text[heading_index:]
    heading_tail_index = len(STRUCTURED_RECORD_HEADING)
    next_heading = re.search(r"\r?\n##\s+", section[heading_tail_index:])
    if next_heading is not None:
        section = section[: heading_tail_index + next_heading.start()]

    fence_pattern = re.compile(r"```yaml\s*\r?\n(?P<body>.*?)\r?\n```", re.DOTALL)
    matches = list(fence_pattern.finditer(section))
    if len(matches) != 1:
        return "", [
            ValidationIssue(
                "missing_or_ambiguous_yaml_fence",
                "structured fixture authority section must contain exactly one fenced yaml block",
            )
        ]
    return matches[0].group("body").strip("\r\n"), []


def parse_structured_record(text: str) -> ParsedRecord:
    block, issues = _extract_fenced_yaml_after_heading(text)
    values: dict[str, str] = {}
    for line_number, line in enumerate(block.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            issues.append(
                ValidationIssue(
                    "malformed_mapping_line",
                    "structured fixture authority line is not a key/value mapping",
                    line_number,
                )
            )
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            issues.append(
                ValidationIssue(
                    "invalid_key",
                    f"structured fixture authority key {key!r} is not valid snake_case",
                    line_number,
                )
            )
            continue
        if key in values:
            issues.append(
                ValidationIssue(
                    "duplicate_key",
                    f"structured fixture authority key {key!r} is duplicated",
                    line_number,
                )
            )
            continue
        if value == "":
            issues.append(
                ValidationIssue(
                    "empty_value",
                    f"structured fixture authority key {key!r} has an empty value",
                    line_number,
                )
            )
            continue
        values[key] = value
    return ParsedRecord(values=values, issues=tuple(issues))


def _record_shape_issues(values: dict[str, str]) -> list[ValidationIssue]:
    expected_fields = set(ALL_FIELDS)
    issues: list[ValidationIssue] = []
    for field in ALL_FIELDS:
        if field not in values:
            issues.append(
                ValidationIssue(
                    "missing_required_key",
                    f"structured fixture authority record is missing required key {field!r}",
                )
            )
    for field in sorted(values):
        if field not in expected_fields:
            issues.append(
                ValidationIssue(
                    "unexpected_key",
                    f"structured fixture authority record has unexpected key {field!r}",
                )
            )
    return issues


def _normalized(value: str | None) -> str:
    return "" if value is None else value.strip().lower()


def _is_nullish(value: str | None) -> bool:
    return _normalized(value) in NULL_VALUES


def _is_filled(value: str | None) -> bool:
    return bool(value and value.strip() and _normalized(value) not in NULL_VALUES)


def _validate_fixed_fields(values: dict[str, str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field, expected in FIXED_FIELDS.items():
        if values.get(field) != expected:
            issues.append(
                ValidationIssue(
                    "fixed_field_mismatch",
                    f"{field} must be exactly {expected!r}",
                )
            )
    return issues


def _validate_tool_status_fields(values: dict[str, str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in TOOL_STATUS_FIELDS:
        if _normalized(values[field]) not in TOOL_STATUS_VALUES:
            issues.append(
                ValidationIssue(
                    "invalid_tool_fixture_authority_status",
                    (
                        f"{field} must be one of "
                        f"{', '.join(sorted(TOOL_STATUS_VALUES))}"
                    ),
                )
            )
    return issues


def _validate_tabpfn_selected_values(values: dict[str, str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if values["tabpfn_fixture_kind"] != "dataset_version_supervised_tabular_micro_fixture":
        issues.append(
            ValidationIssue(
                "invalid_tabpfn_fixture_kind",
                "tabpfn_fixture_kind must be dataset_version_supervised_tabular_micro_fixture",
            )
        )

    task_type = values["tabpfn_task_type"]
    metric_family = values["tabpfn_metric_family"]
    if task_type not in {"classification", "regression"}:
        issues.append(
            ValidationIssue(
                "invalid_tabpfn_task_type",
                "tabpfn_task_type must be classification or regression",
            )
        )
    elif task_type == "classification" and metric_family != "accuracy_or_auc":
        issues.append(
            ValidationIssue(
                "invalid_tabpfn_metric_family",
                "classification fixtures must use accuracy_or_auc",
            )
        )
    elif task_type == "regression" and metric_family != "mae_or_rmse":
        issues.append(
            ValidationIssue(
                "invalid_tabpfn_metric_family",
                "regression fixtures must use mae_or_rmse",
            )
        )
    return issues


def _validate_nrc_rag_selected_values(values: dict[str, str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if values["nrc_rag_fixture_kind"] != "regulatory_context_grounding_query_set":
        issues.append(
            ValidationIssue(
                "invalid_nrc_rag_fixture_kind",
                "nrc_rag_fixture_kind must be regulatory_context_grounding_query_set",
            )
        )
    return issues


def _validate_tool_selection_fields(
    values: dict[str, str],
    *,
    status: str,
    fields: tuple[str, ...],
    expected_state: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if status == "selected":
        for field in fields:
            if not _is_filled(values[field]):
                issues.append(
                    ValidationIssue(
                        f"{expected_state}_field_must_be_filled",
                        f"{expected_state} fixture authority field {field!r} must be filled",
                    )
                )
    else:
        for field in fields:
            if not _is_nullish(values[field]):
                issues.append(
                    ValidationIssue(
                        "nonselected_tool_field_must_be_null",
                        (
                            f"fixture authority field {field!r} must remain null "
                            f"unless its tool status is selected"
                        ),
                    )
                )
    return issues


def _tool_statuses(values: dict[str, str]) -> tuple[str, str]:
    return (
        _normalized(values["tabpfn_fixture_authority_status"]),
        _normalized(values["nrc_rag_fixture_authority_status"]),
    )


def validate_record(values: dict[str, str], expected_state: str) -> list[ValidationIssue]:
    if expected_state not in EXPECTED_STATES:
        raise ValueError(f"unsupported expected state: {expected_state}")

    issues = _record_shape_issues(values)
    if issues:
        return issues

    issues.extend(_validate_fixed_fields(values))
    issues.extend(_validate_tool_status_fields(values))
    selection_complete = _normalized(values["selection_complete"])
    freeze_written = _normalized(values["implementation_entry_freeze_written"])
    tabpfn_status, nrc_rag_status = _tool_statuses(values)
    selected_tool_count = sum(
        1 for status in (tabpfn_status, nrc_rag_status) if status == "selected"
    )
    any_pending_tool = any(status == "pending" for status in (tabpfn_status, nrc_rag_status))

    if selection_complete not in {TRUE_VALUE, FALSE_VALUE}:
        issues.append(
            ValidationIssue(
                "invalid_selection_complete",
                "selection_complete must be exactly true or false",
            )
        )
    if freeze_written not in {TRUE_VALUE, FALSE_VALUE}:
        issues.append(
            ValidationIssue(
                "invalid_implementation_entry_freeze_written",
                "implementation_entry_freeze_written must be exactly true or false",
            )
        )

    if expected_state == "pending":
        for field in TOOL_STATUS_FIELDS:
            if _normalized(values[field]) != "pending":
                issues.append(
                    ValidationIssue(
                        "pending_tool_status_must_be_pending",
                        f"pending fixture authority record must keep {field} pending",
                    )
                )
        for field in SELECTION_FIELDS:
            if not _is_nullish(values[field]):
                issues.append(
                    ValidationIssue(
                        "pending_field_must_be_null",
                        f"pending fixture authority field {field!r} must remain null",
                    )
                )
        if selection_complete != FALSE_VALUE:
            issues.append(
                ValidationIssue(
                    "pending_selection_complete_must_be_false",
                    "pending fixture authority record must keep selection_complete false",
                )
            )
        if freeze_written != FALSE_VALUE:
            issues.append(
                ValidationIssue(
                    "pending_freeze_written_must_be_false",
                    "pending fixture authority record must keep implementation_entry_freeze_written false",
                )
            )
    elif expected_state == "selected":
        if selected_tool_count == 0:
            issues.append(
                ValidationIssue(
                    "selected_record_requires_selected_tool",
                    "selected fixture authority record must select at least one tool",
                )
            )
        issues.extend(
            _validate_tool_selection_fields(
                values,
                status=tabpfn_status,
                fields=TABPFN_FIELDS,
                expected_state="selected",
            )
        )
        issues.extend(
            _validate_tool_selection_fields(
                values,
                status=nrc_rag_status,
                fields=NRC_RAG_FIELDS,
                expected_state="selected",
            )
        )
        expected_selection_complete = FALSE_VALUE if any_pending_tool else TRUE_VALUE
        if selection_complete != expected_selection_complete:
            issues.append(
                ValidationIssue(
                    "selected_selection_complete_mismatch",
                    (
                        "selected fixture authority record must set selection_complete "
                        f"{expected_selection_complete}"
                    ),
                )
            )
        if freeze_written != FALSE_VALUE:
            issues.append(
                ValidationIssue(
                    "selected_freeze_written_must_be_false",
                    "selected fixture authority record must keep implementation_entry_freeze_written false until a separate freeze lands",
                )
            )
        if tabpfn_status == "selected":
            issues.extend(_validate_tabpfn_selected_values(values))
        if nrc_rag_status == "selected":
            issues.extend(_validate_nrc_rag_selected_values(values))
    else:
        if selected_tool_count == 0:
            issues.append(
                ValidationIssue(
                    "frozen_record_requires_selected_tool",
                    "frozen fixture authority record must select at least one tool",
                )
            )
        if any_pending_tool:
            issues.append(
                ValidationIssue(
                    "frozen_tool_status_must_not_be_pending",
                    "frozen fixture authority record cannot leave a tool pending",
                )
            )
        issues.extend(
            _validate_tool_selection_fields(
                values,
                status=tabpfn_status,
                fields=TABPFN_FIELDS,
                expected_state="frozen",
            )
        )
        issues.extend(
            _validate_tool_selection_fields(
                values,
                status=nrc_rag_status,
                fields=NRC_RAG_FIELDS,
                expected_state="frozen",
            )
        )
        if selection_complete != TRUE_VALUE:
            issues.append(
                ValidationIssue(
                    "frozen_selection_complete_must_be_true",
                    "frozen fixture authority record must set selection_complete true",
                )
            )
        if freeze_written != TRUE_VALUE:
            issues.append(
                ValidationIssue(
                    "frozen_freeze_written_must_be_true",
                    "frozen fixture authority record must set implementation_entry_freeze_written true",
                )
            )
        if tabpfn_status == "selected":
            issues.extend(_validate_tabpfn_selected_values(values))
        if nrc_rag_status == "selected":
            issues.extend(_validate_nrc_rag_selected_values(values))
    return issues


def validate_text(text: str, expected_state: str) -> list[ValidationIssue]:
    parsed = parse_structured_record(text)
    return [*parsed.issues, *validate_record(parsed.values, expected_state)]


def _format_issue(issue: ValidationIssue) -> str:
    location = f" line {issue.line}" if issue.line is not None else ""
    return f"{issue.code}{location}: {issue.message}"


def _json_payload(path: Path, expected_state: str, issues: Iterable[ValidationIssue]) -> str:
    issue_list = list(issues)
    return json.dumps(
        {
            "path": path.as_posix(),
            "expected_state": expected_state,
            "valid": not issue_list,
            "issues": [issue.as_dict() for issue in issue_list],
        },
        indent=2,
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Layer 3 Sublayer 3C fixture-authority record."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_RECORD),
        help="Path to 850_FIXTURE_VALIDATE_ONLY.md or a candidate copy.",
    )
    parser.add_argument(
        "--expect",
        choices=EXPECTED_STATES,
        default="pending",
        help="Expected record state: pending, selected, or frozen.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable validation output.",
    )
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        issue = ValidationIssue("missing_file", f"file does not exist: {path}")
        print(_json_payload(path, args.expect, [issue]) if args.json else _format_issue(issue))
        return 1
    if path.stat().st_size == 0:
        issue = ValidationIssue("empty_file", f"file is empty: {path}")
        print(_json_payload(path, args.expect, [issue]) if args.json else _format_issue(issue))
        return 1

    text = path.read_text(encoding="utf-8")
    issues = validate_text(text, args.expect)
    if args.json:
        print(_json_payload(path, args.expect, issues))
    elif issues:
        print(f"Layer 3 fixture-authority validation: FAIL ({args.expect})")
        for issue in issues:
            print(f"- {_format_issue(issue)}")
    else:
        print(f"Layer 3 fixture-authority validation: PASS ({args.expect})")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
