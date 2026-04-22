from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.review_nrc_aps_catalog import discover_candidate_runs  # noqa: E402
from app.services.review_nrc_aps_runtime import resolve_runtime_binding_for_run  # noqa: E402


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8098


@dataclass(frozen=True)
class LaunchCandidate:
    run_id: str
    display_label: str
    review_root: Path
    runtime_root: Path
    database_path: Path
    storage_dir: Path
    selection_storage_root: Path
    completed_at: str | None
    submitted_at: str | None


def _shared_repo_storage_root(repo_root: Path) -> Path | None:
    for ancestor in repo_root.parents:
        if ancestor.name != "worktrees":
            continue
        candidate = ancestor.parent / "backend" / "app" / "storage_test_runtime"
        try:
            return candidate.resolve()
        except OSError:
            return None
    return None


def _local_storage_roots(repo_root: Path) -> list[Path]:
    return [
        (repo_root / "backend" / "app" / "storage_test_runtime").resolve(),
        (repo_root / "backend" / "storage_test_runtime").resolve(),
    ]


def _selection_storage_root(repo_root: Path) -> Path | None:
    shared_root = _shared_repo_storage_root(repo_root)
    if shared_root is not None and shared_root.exists():
        return shared_root

    for candidate in _local_storage_roots(repo_root):
        if candidate.exists():
            return candidate
    return None


@contextmanager
def _override_storage_dir(storage_root: Path | None) -> Iterator[None]:
    previous_setting = settings.storage_dir
    had_env = "STORAGE_DIR" in os.environ
    previous_env = os.environ.get("STORAGE_DIR")
    try:
        if storage_root is not None:
            resolved = str(storage_root.resolve())
            os.environ["STORAGE_DIR"] = resolved
            settings.storage_dir = resolved
        yield
    finally:
        settings.storage_dir = previous_setting
        if had_env and previous_env is not None:
            os.environ["STORAGE_DIR"] = previous_env
        else:
            os.environ.pop("STORAGE_DIR", None)


def _discover_launch_candidates(repo_root: Path) -> tuple[str | None, list[LaunchCandidate]]:
    selected_storage_root = _selection_storage_root(repo_root)
    with _override_storage_dir(selected_storage_root):
        selector = discover_candidate_runs()
        candidates: list[LaunchCandidate] = []
        for item in selector.runs:
            if not item.reviewable:
                continue
            binding = resolve_runtime_binding_for_run(run_id=item.run_id)
            if binding.database_path is None or binding.storage_dir is None:
                continue
            runtime_root = binding.review_root.parent.parent.resolve()
            candidates.append(
                LaunchCandidate(
                    run_id=item.run_id,
                    display_label=item.display_label,
                    review_root=binding.review_root.resolve(),
                    runtime_root=runtime_root,
                    database_path=binding.database_path.resolve(),
                    storage_dir=binding.storage_dir.resolve(),
                    selection_storage_root=(selected_storage_root or runtime_root).resolve(),
                    completed_at=item.completed_at,
                    submitted_at=item.submitted_at,
                )
            )

    by_run_id = {candidate.run_id: candidate for candidate in candidates}
    default_run_id = selector.default_run_id if selector.default_run_id in by_run_id else None
    ordered = [by_run_id[item.run_id] for item in selector.runs if item.run_id in by_run_id]
    return default_run_id, ordered


def _select_candidate(repo_root: Path, *, run_id: str | None, latest: bool) -> LaunchCandidate:
    default_run_id, candidates = _discover_launch_candidates(repo_root)
    if not candidates:
        raise RuntimeError(
            "No reviewable summary-backed runtime was found. "
            "Create or restore one first, then rerun this command."
        )

    by_run_id = {candidate.run_id: candidate for candidate in candidates}
    if run_id:
        selected = by_run_id.get(run_id)
        if selected is None:
            raise RuntimeError(f"Requested run_id is not launchable from this checkout: {run_id}")
        return selected

    if latest:
        if default_run_id is None:
            raise RuntimeError("No default reviewable run could be determined from the discovered runtimes.")
        return by_run_id[default_run_id]

    return candidates[0]


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _read_json(url: str) -> dict:
    with urlopen(url, timeout=10) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _print_candidate(candidate: LaunchCandidate, *, mark_default: bool) -> None:
    if mark_default:
        print("selected=true")
    print(f"run_id={candidate.run_id}")
    print(f"display_label={candidate.display_label}")
    print(f"review_root={candidate.review_root}")
    print(f"runtime_root={candidate.runtime_root}")
    print(f"selection_storage_root={candidate.selection_storage_root}")
    print(f"database={candidate.database_path}")
    print(f"storage={candidate.storage_dir}")
    print(f"completed_at={candidate.completed_at or ''}")
    print(f"submitted_at={candidate.submitted_at or ''}")
    print("---")


def command_discover(args: argparse.Namespace) -> int:
    default_run_id, candidates = _discover_launch_candidates(REPO_ROOT)
    if not candidates:
        print(
            "No reviewable summary-backed runtime was found. "
            "Create or restore one first, then rerun this command.",
            file=sys.stderr,
        )
        return 1

    print(f"default_run_id={default_run_id or ''}")
    print(f"candidate_count={len(candidates)}")
    print("---")
    for candidate in candidates:
        _print_candidate(candidate, mark_default=(candidate.run_id == default_run_id))
    return 0


def command_urls(args: argparse.Namespace) -> int:
    base_url = _base_url(args.host, args.port)
    print(f"review={base_url}/review/nrc-aps")
    print(f"document_trace={base_url}/review/nrc-aps/document-trace")
    print(f"workbench_compare={base_url}/review/nrc-aps/workbench-compare")
    print(
        "candidate_b_trace_template="
        f"{base_url}/review/nrc-aps/candidate-b-trace"
        "?candidate_b_bundle_id=<BUNDLE_ID>&fixture_id=<FIXTURE_ID>"
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    expected = _select_candidate(REPO_ROOT, run_id=args.run_id, latest=args.latest)
    base_url = _base_url(args.host, args.port)

    try:
        health = _read_json(f"{base_url}/health")
        runs = _read_json(f"{base_url}/api/v1/review/nrc-aps/runs")
    except HTTPError as exc:
        print(f"HTTP error while verifying launch surface: {exc}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Connection error while verifying launch surface: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Unexpected non-JSON response while verifying launch surface: {exc}", file=sys.stderr)
        return 1

    discovered_run_ids = [str(item.get("run_id") or "") for item in runs.get("runs", [])]
    default_run_id = str(runs.get("default_run_id") or "").strip()

    if str(health.get("status") or "").strip().lower() != "ok":
        print(f"Health endpoint did not report ok: {health}", file=sys.stderr)
        return 1
    if expected.run_id not in discovered_run_ids:
        print(
            f"Expected run_id {expected.run_id} was not present in /runs. "
            f"Discovered: {discovered_run_ids}",
            file=sys.stderr,
        )
        return 1
    if default_run_id != expected.run_id:
        print(
            f"Default run mismatch. expected={expected.run_id} actual={default_run_id}",
            file=sys.stderr,
        )
        return 1

    print(f"health_status={health.get('status')}")
    print(f"expected_run_id={expected.run_id}")
    print(f"default_run_id={default_run_id}")
    print(f"run_count={len(discovered_run_ids)}")
    return 0


def command_serve(args: argparse.Namespace) -> int:
    selected = _select_candidate(REPO_ROOT, run_id=args.run_id, latest=args.latest)

    env = os.environ.copy()
    env["DB_INIT_MODE"] = "none"
    env["DATABASE_URL"] = f"sqlite:///{selected.database_path.as_posix()}"
    env["STORAGE_DIR"] = str(selected.selection_storage_root)

    print(f"run_id={selected.run_id}")
    print(f"review_root={selected.review_root}")
    print(f"runtime_root={selected.runtime_root}")
    print(f"selection_storage_root={selected.selection_storage_root}")
    print(f"database={selected.database_path}")
    print(f"storage={selected.storage_dir}")
    print(f"base_url={_base_url(args.host, args.port)}")
    print("db_init_mode=none")
    print("---")
    print("Starting uvicorn. Keep this terminal open while using the UI.")
    sys.stdout.flush()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--app-dir",
            "./backend",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Shell-neutral helper for launching and verifying the NRC APS UI surfaces.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="List reviewable runtimes and show the default selection.")
    discover_parser.set_defaults(func=command_discover)

    serve_parser = subparsers.add_parser("serve", help="Launch uvicorn against the selected review runtime.")
    serve_parser.add_argument("--run-id", default="", help="Launch a specific discovered run_id.")
    serve_parser.add_argument("--latest", action="store_true", help="Launch the latest reviewable discovered run.")
    serve_parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind. Default: {DEFAULT_HOST}")
    serve_parser.add_argument("--port", default=DEFAULT_PORT, type=int, help=f"Port to bind. Default: {DEFAULT_PORT}")
    serve_parser.set_defaults(func=command_serve)

    verify_parser = subparsers.add_parser("verify", help="Verify the launched UI/API surface against the selected run.")
    verify_parser.add_argument("--run-id", default="", help="Expect a specific discovered run_id.")
    verify_parser.add_argument("--latest", action="store_true", help="Expect the current latest reviewable discovered run.")
    verify_parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to verify. Default: {DEFAULT_HOST}")
    verify_parser.add_argument("--port", default=DEFAULT_PORT, type=int, help=f"Port to verify. Default: {DEFAULT_PORT}")
    verify_parser.set_defaults(func=command_verify)

    urls_parser = subparsers.add_parser("urls", help="Print the shipped UI URLs for the chosen host and port.")
    urls_parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to print. Default: {DEFAULT_HOST}")
    urls_parser.add_argument("--port", default=DEFAULT_PORT, type=int, help=f"Port to print. Default: {DEFAULT_PORT}")
    urls_parser.set_defaults(func=command_urls)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
