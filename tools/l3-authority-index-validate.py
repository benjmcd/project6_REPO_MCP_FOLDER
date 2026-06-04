from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "next_milestone_plans" / "authority-index.json"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ONLOOK_RE = re.compile(r"onlook", re.IGNORECASE)
ALLOWED_INDEX_SCOPES = {"intentionally_scoped"}
ALLOWED_FRESHNESS = {
    "active_process_policy",
    "current_closeout",
    "current_lane_front_door",
    "current_status_doc",
    "snapshot_guardrail",
    "snapshot_manifest",
}
REQUIRED_TOP_LEVEL = {
    "artifact_version",
    "artifact_name",
    "index_scope",
    "non_exhaustive_reason",
    "onlook_policy",
    "last_verified",
    "authority_order",
    "lanes",
}
REQUIRED_LAST_VERIFIED = {
    "remote",
    "commit",
    "verified_at_utc",
    "verification_summary",
    "commands",
}
REQUIRED_LANE = {
    "lane_id",
    "lane_name",
    "lane_scope",
    "current_state",
    "source_of_truth",
    "current_truth_order",
    "known_limits",
    "next_decision",
}
REQUIRED_SOURCE = {
    "path",
    "kind",
    "authority",
    "freshness",
    "required_terms",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def _issue(issues: list[ValidationIssue], code: str, message: str) -> None:
    issues.append(ValidationIssue(code, message))


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_is_nonempty_string(item) for item in value)


def _reject_unknown_keys(
    value: dict[str, Any],
    *,
    allowed: set[str],
    label: str,
    issues: list[ValidationIssue],
) -> None:
    for key in sorted(set(value) - allowed):
        _issue(issues, "unsupported_field", f"{label} has unsupported field {key!r}")


def _contains_onlook_text(value: Any) -> bool:
    if isinstance(value, str):
        return ONLOOK_RE.search(value) is not None
    if isinstance(value, list):
        return any(_contains_onlook_text(item) for item in value)
    return False


def _is_safe_repo_path(path_value: str) -> bool:
    path = Path(path_value)
    return not path.is_absolute() and ".." not in path.parts and path_value.strip() == path_value


def _read_json(path: Path) -> tuple[dict[str, Any] | None, list[ValidationIssue]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [ValidationIssue("index_missing", f"index file does not exist: {path}")]
    except json.JSONDecodeError as exc:
        return None, [ValidationIssue("invalid_json", f"invalid JSON: {exc}")]
    if not isinstance(payload, dict):
        return None, [ValidationIssue("invalid_root", "index root must be a JSON object")]
    return payload, []


def validate_payload(payload: dict[str, Any], *, root: Path = ROOT) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _reject_unknown_keys(payload, allowed=REQUIRED_TOP_LEVEL, label="index", issues=issues)
    missing_top = REQUIRED_TOP_LEVEL - set(payload)
    for key in sorted(missing_top):
        _issue(issues, "missing_top_level_key", f"missing top-level key {key!r}")

    if payload.get("artifact_version") != 1:
        _issue(issues, "invalid_artifact_version", "artifact_version must be 1")
    if payload.get("index_scope") not in ALLOWED_INDEX_SCOPES:
        _issue(issues, "invalid_index_scope", "index_scope must be intentionally_scoped")
    if payload.get("onlook_policy") != "excluded":
        _issue(issues, "invalid_onlook_policy", "onlook_policy must be excluded")
    if not _is_nonempty_string(payload.get("non_exhaustive_reason")):
        _issue(
            issues,
            "missing_non_exhaustive_reason",
            "intentionally scoped index must explain non-exhaustive scope",
        )
    if not _is_string_list(payload.get("authority_order")):
        _issue(issues, "invalid_authority_order", "authority_order must be a non-empty string list")

    last_verified = payload.get("last_verified")
    if not isinstance(last_verified, dict):
        _issue(issues, "invalid_last_verified", "last_verified must be an object")
    else:
        _reject_unknown_keys(
            last_verified,
            allowed=REQUIRED_LAST_VERIFIED,
            label="last_verified",
            issues=issues,
        )
        for key in sorted(REQUIRED_LAST_VERIFIED - set(last_verified)):
            _issue(issues, "missing_last_verified_key", f"last_verified missing {key!r}")
        if last_verified.get("remote") != "project6-origin/main":
            _issue(issues, "invalid_remote", "last_verified.remote must be project6-origin/main")
        commit = last_verified.get("commit")
        if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
            _issue(issues, "invalid_commit", "last_verified.commit must be a 40-character hex SHA")
        verified_at = last_verified.get("verified_at_utc")
        if not isinstance(verified_at, str) or UTC_RE.fullmatch(verified_at) is None:
            _issue(issues, "invalid_verified_at", "verified_at_utc must be an ISO UTC timestamp")
        if not _is_nonempty_string(last_verified.get("verification_summary")):
            _issue(issues, "missing_verification_summary", "verification_summary must be present")
        if not _is_string_list(last_verified.get("commands")):
            _issue(issues, "invalid_verification_commands", "commands must be a non-empty string list")

    lanes = payload.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        _issue(issues, "invalid_lanes", "lanes must be a non-empty list")
        return issues

    lane_ids: set[str] = set()
    for lane_index, lane in enumerate(lanes):
        lane_label = f"lanes[{lane_index}]"
        if not isinstance(lane, dict):
            _issue(issues, "invalid_lane", f"{lane_label} must be an object")
            continue
        _reject_unknown_keys(lane, allowed=REQUIRED_LANE, label=lane_label, issues=issues)
        for key in sorted(REQUIRED_LANE - set(lane)):
            _issue(issues, "missing_lane_key", f"{lane_label} missing {key!r}")
        lane_id = lane.get("lane_id")
        if not _is_nonempty_string(lane_id):
            _issue(issues, "invalid_lane_id", f"{lane_label}.lane_id must be a non-empty string")
        elif lane_id in lane_ids:
            _issue(issues, "duplicate_lane_id", f"duplicate lane_id {lane_id!r}")
        else:
            lane_ids.add(lane_id)
        for key in ("lane_name", "lane_scope", "current_state", "next_decision"):
            if key in lane and not _is_nonempty_string(lane[key]):
                _issue(issues, "invalid_lane_string", f"{lane_label}.{key} must be non-empty")
            if key in lane and _contains_onlook_text(lane[key]):
                _issue(issues, "onlook_lane_metadata", f"{lane_label}.{key} must not reference Onlook")
        for key in ("current_truth_order", "known_limits"):
            if key in lane and not _is_string_list(lane[key]):
                _issue(issues, "invalid_lane_list", f"{lane_label}.{key} must be a non-empty string list")
            if key in lane and _contains_onlook_text(lane[key]):
                _issue(issues, "onlook_lane_metadata", f"{lane_label}.{key} must not reference Onlook")
        sources = lane.get("source_of_truth")
        if not isinstance(sources, list) or not sources:
            _issue(issues, "invalid_source_of_truth", f"{lane_label}.source_of_truth must be non-empty")
            continue
        for source_index, source in enumerate(sources):
            source_label = f"{lane_label}.source_of_truth[{source_index}]"
            _validate_source(source, source_label, root, issues)

    return issues


def _validate_source(
    source: Any,
    source_label: str,
    root: Path,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(source, dict):
        _issue(issues, "invalid_source", f"{source_label} must be an object")
        return
    _reject_unknown_keys(source, allowed=REQUIRED_SOURCE, label=source_label, issues=issues)
    for key in sorted(REQUIRED_SOURCE - set(source)):
        _issue(issues, "missing_source_key", f"{source_label} missing {key!r}")
    path_value = source.get("path")
    if not _is_nonempty_string(path_value):
        _issue(issues, "invalid_source_path", f"{source_label}.path must be non-empty")
        return
    if ONLOOK_RE.search(path_value):
        _issue(issues, "onlook_path", f"{source_label}.path must not reference Onlook")
    if not _is_safe_repo_path(path_value):
        _issue(issues, "unsafe_source_path", f"{source_label}.path must be a safe relative path")
        return
    full_path = root / path_value
    if not full_path.exists():
        _issue(issues, "missing_source_path", f"{source_label}.path does not exist: {path_value}")
        return

    for key in ("kind", "authority"):
        if key in source and not _is_nonempty_string(source[key]):
            _issue(issues, "invalid_source_string", f"{source_label}.{key} must be non-empty")
    freshness = source.get("freshness")
    if freshness not in ALLOWED_FRESHNESS:
        _issue(issues, "invalid_freshness", f"{source_label}.freshness has unsupported value")
    terms = source.get("required_terms")
    if not _is_string_list(terms):
        _issue(issues, "invalid_required_terms", f"{source_label}.required_terms must be non-empty")
        return

    text = full_path.read_text(encoding="utf-8-sig")
    for term in terms:
        if ONLOOK_RE.search(term):
            _issue(issues, "onlook_required_term", f"{source_label}.required_terms must not reference Onlook")
        if term not in text:
            _issue(
                issues,
                "missing_required_term",
                f"{source_label}.required_terms entry {term!r} was not found in {path_value}",
            )


def validate_index(index_path: Path = DEFAULT_INDEX, *, root: Path = ROOT) -> list[ValidationIssue]:
    payload, issues = _read_json(index_path)
    if payload is None:
        return issues
    return issues + validate_payload(payload, root=root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Project6 roadmap authority index.")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--json", action="store_true", help="emit machine-readable issue output")
    args = parser.parse_args(argv)

    issues = validate_index(args.index)
    if args.json:
        print(json.dumps([issue.as_dict() for issue in issues], indent=2, sort_keys=True))
    elif issues:
        print("Layer 3 authority index validation: FAIL")
        for issue in issues:
            print(f"- {issue.code}: {issue.message}")
    else:
        print("Layer 3 authority index validation: PASS")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
