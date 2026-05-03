from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_GLOBS = (
    ".project6_api_*.log",
    "corpus*.log",
    "setup_logs/*.log",
    "tests/reports/*.log",
    "test-results/**/*.log",
    "playwright-report/**/*.log",
)


@dataclass(frozen=True)
class LogSummary:
    path: str
    size_bytes: int
    modified_utc: str
    lines: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "modified_utc": self.modified_utc,
            "lines": self.lines,
        }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _safe_relative(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"path is outside repo root: {path}") from exc


def _candidate_paths(root: Path, extra_paths: Iterable[str]) -> list[Path]:
    paths: set[Path] = set()
    for pattern in DEFAULT_GLOBS:
        paths.update(path for path in root.glob(pattern) if path.is_file())
    for value in extra_paths:
        rel_path = _safe_relative(root, root.joinpath(value))
        path = root / rel_path
        if path.is_file():
            paths.add(path)
    return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)


def _read_tail(path: Path, limit: int, contains: str | None) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    if contains:
        lines = [line for line in lines if contains in line]
    return lines[-limit:] if limit > 0 else []


def inspect_logs(root: Path, extra_paths: Iterable[str], tail: int, contains: str | None) -> list[LogSummary]:
    summaries: list[LogSummary] = []
    for path in _candidate_paths(root, extra_paths):
        stat = path.stat()
        rel_path = path.resolve().relative_to(root).as_posix()
        lines = _read_tail(path, tail, contains)
        if contains and not lines:
            continue
        summaries.append(
            LogSummary(
                path=rel_path,
                size_bytes=stat.st_size,
                modified_utc=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                lines=lines,
            )
        )
    return summaries


def _format_text(summaries: list[LogSummary]) -> str:
    if not summaries:
        return "harness logs: none found"
    lines = ["harness logs:"]
    for summary in summaries:
        lines.append(f"- {summary.path} ({summary.size_bytes} bytes, modified {summary.modified_utc})")
        for line in summary.lines:
            lines.append(f"  {line}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect local harness logs without creating artifacts.")
    parser.add_argument("--path", action="append", default=[], help="Additional repo-relative log file to inspect.")
    parser.add_argument("--contains", help="Only show tail lines containing this exact text.")
    parser.add_argument("--tail", type=int, default=40, help="Lines to show per log after filtering.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    args = parser.parse_args(argv)

    root = _repo_root()
    summaries = inspect_logs(root, args.path, args.tail, args.contains)
    if args.format == "json":
        print(json.dumps([summary.as_dict() for summary in summaries], indent=2, sort_keys=True))
    else:
        print(_format_text(summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
