from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _current_git_sha(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git rev-parse HEAD failed")
    source_sha = completed.stdout.strip().lower()
    if not SOURCE_SHA_RE.fullmatch(source_sha):
        raise ValueError(f"git rev-parse HEAD did not return a 40-char SHA: {source_sha!r}")
    return source_sha


def build_command(
    repo_root: Path,
    *,
    image_tag: str,
    docker_executable: str = "docker",
    source_sha: str | None = None,
) -> list[str]:
    selected_sha = (source_sha or _current_git_sha(repo_root)).strip().lower()
    if not SOURCE_SHA_RE.fullmatch(selected_sha):
        raise ValueError(f"PROJECT6_SOURCE_SHA must be a 40-char git SHA, got {selected_sha!r}")
    return [
        docker_executable,
        "build",
        "-f",
        "Dockerfile.app",
        "--build-arg",
        f"PROJECT6_SOURCE_SHA={selected_sha}",
        "-t",
        image_tag,
        ".",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Project6 application image with source identity baked in")
    parser.add_argument("--tag", default="method-aware-app:local", help="image tag to pass to docker build")
    parser.add_argument("--docker", default="docker", help="docker executable name or path")
    parser.add_argument("--source-sha", help="explicit 40-char source SHA; defaults to git rev-parse HEAD")
    parser.add_argument("--print-command", action="store_true", help="print the docker command without running it")
    args = parser.parse_args()

    repo_root = default_repo_root()
    command = build_command(
        repo_root,
        image_tag=args.tag,
        docker_executable=args.docker,
        source_sha=args.source_sha,
    )
    if args.print_command:
        print(subprocess.list2cmdline(command))
        return 0
    return subprocess.run(command, cwd=repo_root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
