from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ALLOWED_ROOT_ENTRIES = {
    ".gitattributes",
    ".github",
    ".gitignore",
    ".gitmodules",
    ".omc",
    ".project6_api_stderr.log",
    ".project6_api_stdout.log",
    ".vscode",
    "_external",
    "_forensic_exports",
    "2026-03-28_review_ui_hardening_and_cleanup_plan.md",
    "AGENTS.md",
    "BREAK_REFINEMENT_SUMMARY.md",
    "DECOMP_BREAK_PATCH_SUMMARY.md",
    "Dockerfile",
    "METHOD_AWARE_FRAMEWORK_CHANGELOG.md",
    "POST_REVIEW_PATCH_SUMMARY.md",
    "PRIMARY_INVESTIGATION_FILE_LATEST_SESSION.json",
    "README.md",
    "REPO_INDEX.md",
    "SCIENCEBASE_PILOT_RUNBOOK.md",
    "app",
    "archive",
    "backend",
    "chatgpt_project6_repo_creation.json",
    "corpus_closure.log",
    "corpus_diagnostics.py",
    "corpus_diagnostics_final.log",
    "corpus_diagnostics_patch.log",
    "corpus_diagnostics_patch2.log",
    "corpus_diagnostics_v2.log",
    "corpus_verify.log",
    "data_actual",
    "data_demo",
    "docs",
    "e2e",
    "frontend_UI_plans",
    "handoff",
    "mcp_current_filestates",
    "next_milestone_plans",
    "onlook-ui",
    "package-lock.json",
    "package.json",
    "patches",
    "plans",
    "playwright.config.js",
    "postreview_eval.py",
    "project6.ps1",
    "run_context_packet_single_export.py",
    "run_full_export.py",
    "session-2132a83d-b486-4995-ac98-5fd922420f8d.json",
    "session_extracted",
    "session_temp",
    "sessionhistory2_parsed.md",
    "sessionhistory3_parsed.md",
    "sessionhistory_extracted",
    "sessionhistoryfiles.zip",
    "setup_logs",
    "temp_extract",
    "temp_session.json",
    "tests",
    "tmp",
    "tools",
}

TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/](?:Users|Temp)[\\/]|/Users/|/home/|file:///)")
OVERSIZED_FILE_BYTES = 500_000


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    path: str
    message: str
    line: int | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }
        if self.line is not None:
            payload["line"] = self.line
        return payload


def git_ls_files(repo_root: Path) -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], cwd=repo_root, text=True)
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def check_root_surface(files: Iterable[str]) -> list[Issue]:
    seen_roots = sorted({path.split("/", 1)[0] for path in files if path})
    return [
        Issue(
            code="UNKNOWN_ROOT_ENTRY",
            severity="error",
            path=root,
            message="tracked top-level entry is not declared in the root surface allowlist",
        )
        for root in seen_roots
        if root not in ALLOWED_ROOT_ENTRIES
    ]


def check_json_syntax(repo_root: Path, files: Iterable[str]) -> list[Issue]:
    issues: list[Issue] = []
    for rel_path in files:
        if not rel_path.lower().endswith(".json"):
            continue
        path = repo_root / rel_path
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            issues.append(
                Issue(
                    code="JSON_INVALID",
                    severity="error",
                    path=rel_path,
                    message=f"tracked JSON could not be parsed: {type(exc).__name__}: {exc}",
                )
            )
    return issues


def scan_local_path_refs(repo_root: Path, files: Iterable[str]) -> list[Issue]:
    issues: list[Issue] = []
    for rel_path in files:
        suffix = Path(rel_path).suffix.lower()
        if suffix not in TEXT_EXTENSIONS:
            continue
        path = repo_root / rel_path
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(text.splitlines(), start=1):
            if LOCAL_PATH_RE.search(line):
                issues.append(
                    Issue(
                        code="LOCAL_PATH_REF",
                        severity="warning",
                        path=rel_path,
                        line=index,
                        message="tracked text contains a local absolute path or file URI",
                    )
                )
                break
    return issues


def check_oversized_files(repo_root: Path, files: Iterable[str]) -> list[Issue]:
    issues: list[Issue] = []
    for rel_path in files:
        path = repo_root / rel_path
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > OVERSIZED_FILE_BYTES:
            issues.append(
                Issue(
                    code="OVERSIZED_TRACKED_FILE",
                    severity="warning",
                    path=rel_path,
                    message=f"tracked file is {size} bytes; consider splitting or classifying it",
                )
            )
    return issues


def check_codesight_freshness(repo_root: Path) -> list[Issue]:
    codesight = repo_root / ".codesight"
    if not codesight.exists():
        return []
    marker = codesight / "freshness.json"
    if not marker.exists():
        return [
            Issue(
                code="CODESIGHT_FRESHNESS_MISSING",
                severity="warning",
                path=".codesight",
                message="local generated navigation exists without .codesight/freshness.json",
            )
        ]
    try:
        payload = json.loads(marker.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        return [
            Issue(
                code="CODESIGHT_FRESHNESS_INVALID",
                severity="warning",
                path=".codesight/freshness.json",
                message=f"freshness marker could not be parsed: {type(exc).__name__}: {exc}",
            )
        ]
    missing = [key for key in ("source_commit", "generated_at", "command") if not payload.get(key)]
    if missing:
        return [
            Issue(
                code="CODESIGHT_FRESHNESS_INCOMPLETE",
                severity="warning",
                path=".codesight/freshness.json",
                message=f"freshness marker is missing required field(s): {', '.join(missing)}",
            )
        ]
    return []


def run_checks(repo_root: Path) -> list[Issue]:
    files = git_ls_files(repo_root)
    issues: list[Issue] = []
    issues.extend(check_root_surface(files))
    issues.extend(check_json_syntax(repo_root, files))
    issues.extend(scan_local_path_refs(repo_root, files))
    issues.extend(check_oversized_files(repo_root, files))
    issues.extend(check_codesight_freshness(repo_root))
    return issues


def _format_text(issues: list[Issue]) -> str:
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    lines = [
        "structure validation:",
        f"  errors: {len(errors)}",
        f"  warnings: {len(warnings)}",
    ]
    for issue in issues[:50]:
        location = issue.path if issue.line is None else f"{issue.path}:{issue.line}"
        lines.append(f"  [{issue.severity}] {issue.code} {location} - {issue.message}")
    if len(issues) > 50:
        lines.append(f"  ... {len(issues) - 50} more issue(s) omitted from text output")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate non-mutating Project6 structural harness invariants.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    issues = run_checks(repo_root)
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    payload = {
        "passed": not errors and not (args.strict and warnings),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": [issue.as_dict() for issue in issues],
    }
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(_format_text(issues))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
