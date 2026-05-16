from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = (
    REPO_ROOT
    / "next_milestone_plans"
    / "Layer3_planning_docs"
    / "612_TARGET_SELECTION_INTAKE.md"
)
STRUCTURED_RECORD_HEADING = "## Structured Selection Record"
REQUIRED_FIELDS = (
    "target_identity",
    "target_owner",
    "target_class",
    "operator_purpose",
    "authority_source",
    "artifact_family",
    "credential_model",
    "destination_address_model",
    "side_effect_boundary",
    "idempotency_contract",
    "failure_lifecycle",
    "receipt_audit_contract",
    "exposure_security_posture",
    "operator_surface",
    "proof_architecture",
)
CONTROL_FIELDS = (
    "selection_complete",
    "implementation_entry_freeze_written",
)
EXPECTED_STATES = ("pending", "selected", "frozen")
NULL_VALUE = "null"
TRUE_VALUE = "true"
FALSE_VALUE = "false"


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
                "structured record section must contain exactly one fenced yaml block",
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
                    "structured record line is not a key/value mapping",
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
                    f"structured record key {key!r} is not valid snake_case",
                    line_number,
                )
            )
            continue
        if key in values:
            issues.append(
                ValidationIssue(
                    "duplicate_key",
                    f"structured record key {key!r} is duplicated",
                    line_number,
                )
            )
            continue
        if value == "":
            issues.append(
                ValidationIssue(
                    "empty_value",
                    f"structured record key {key!r} has an empty value",
                    line_number,
                )
            )
            continue
        values[key] = value
    return ParsedRecord(values=values, issues=tuple(issues))


def _record_shape_issues(values: dict[str, str]) -> list[ValidationIssue]:
    expected_fields = set(REQUIRED_FIELDS + CONTROL_FIELDS)
    issues: list[ValidationIssue] = []
    for field in REQUIRED_FIELDS + CONTROL_FIELDS:
        if field not in values:
            issues.append(
                ValidationIssue(
                    "missing_required_key",
                    f"structured record is missing required key {field!r}",
                )
            )
    for field in sorted(values):
        if field not in expected_fields:
            issues.append(
                ValidationIssue(
                    "unexpected_key",
                    f"structured record has unexpected key {field!r}",
                )
            )
    return issues


def _is_nullish(value: str | None) -> bool:
    return value is None or value.strip().lower() == NULL_VALUE


def _is_filled(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip().lower() != NULL_VALUE)


def validate_record(values: dict[str, str], expected_state: str) -> list[ValidationIssue]:
    if expected_state not in EXPECTED_STATES:
        raise ValueError(f"unsupported expected state: {expected_state}")

    issues = _record_shape_issues(values)
    if issues:
        return issues

    selection_complete = values["selection_complete"].strip().lower()
    freeze_written = values["implementation_entry_freeze_written"].strip().lower()

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
        for field in REQUIRED_FIELDS:
            if not _is_nullish(values[field]):
                issues.append(
                    ValidationIssue(
                        "pending_field_must_be_null",
                        f"pending intake field {field!r} must remain null",
                    )
                )
        if selection_complete != FALSE_VALUE:
            issues.append(
                ValidationIssue(
                    "pending_selection_complete_must_be_false",
                    "pending intake must keep selection_complete false",
                )
            )
        if freeze_written != FALSE_VALUE:
            issues.append(
                ValidationIssue(
                    "pending_freeze_written_must_be_false",
                    "pending intake must keep implementation_entry_freeze_written false",
                )
            )
    elif expected_state == "selected":
        for field in REQUIRED_FIELDS:
            if not _is_filled(values[field]):
                issues.append(
                    ValidationIssue(
                        "selected_field_must_be_filled",
                        f"selected intake field {field!r} must be filled",
                    )
                )
        if selection_complete != TRUE_VALUE:
            issues.append(
                ValidationIssue(
                    "selected_selection_complete_must_be_true",
                    "selected intake must set selection_complete true",
                )
            )
        if freeze_written != FALSE_VALUE:
            issues.append(
                ValidationIssue(
                    "selected_freeze_written_must_be_false",
                    "selected intake must keep implementation_entry_freeze_written false until the separate freeze lands",
                )
            )
    else:
        for field in REQUIRED_FIELDS:
            if not _is_filled(values[field]):
                issues.append(
                    ValidationIssue(
                        "frozen_field_must_be_filled",
                        f"frozen intake field {field!r} must be filled",
                    )
                )
        if selection_complete != TRUE_VALUE:
            issues.append(
                ValidationIssue(
                    "frozen_selection_complete_must_be_true",
                    "frozen intake must set selection_complete true",
                )
            )
        if freeze_written != TRUE_VALUE:
            issues.append(
                ValidationIssue(
                    "frozen_freeze_written_must_be_true",
                    "frozen intake must set implementation_entry_freeze_written true",
                )
            )
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
        description="Validate the Layer 3 target-selection structured intake record."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_INTAKE),
        help="Path to 612_TARGET_SELECTION_INTAKE.md or a candidate copy.",
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
        print(f"Layer 3 target-selection validation: FAIL ({args.expect})")
        for issue in issues:
            print(f"- {_format_issue(issue)}")
    else:
        print(f"Layer 3 target-selection validation: PASS ({args.expect})")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
