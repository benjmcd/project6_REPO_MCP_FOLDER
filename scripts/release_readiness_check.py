from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, NamedTuple

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal CI envs.
    yaml = None


SCHEMA_ID = "project6.release_readiness.v1"
READY_BUILD_INFO_SOURCE = "/ready build_info"
SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$", re.IGNORECASE)


class CommandResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_subprocess(command: list[str], cwd: Path) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def _tail(text: str, limit: int = 2000) -> str:
    value = text.strip()
    if len(value) <= limit:
        return value
    return value[-limit:]


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text)
    else:
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} requires PyYAML for non-JSON YAML content") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return loaded


def _validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_id") != SCHEMA_ID:
        raise ValueError(f"manifest schema_id must be {SCHEMA_ID!r}")
    if manifest.get("build_identity", {}).get("source") != READY_BUILD_INFO_SOURCE:
        raise ValueError("build_identity.source must be /ready build_info")
    if manifest.get("owner_selected_profile_specific_gates") != []:
        raise ValueError("owner_selected_profile_specific_gates must stay empty until owner selection")
    gates = manifest.get("required_gates")
    if not isinstance(gates, list) or not gates:
        raise ValueError("required_gates must be a non-empty list")
    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError("each gate must be a mapping")
        if not gate.get("id"):
            raise ValueError("each gate needs an id")
        if gate.get("profile_scope") != "profile-neutral":
            raise ValueError(f"gate {gate.get('id')!r} must be profile-neutral")


def _current_git_sha(repo_root: Path) -> str:
    try:
        raw = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"
    if SOURCE_SHA_RE.fullmatch(raw):
        return raw.lower()
    return "unknown"


def collect_ready_build_info(repo_root: Path) -> dict[str, Any]:
    original_source_sha = os.environ.get("PROJECT6_SOURCE_SHA")
    original_db_init_mode = os.environ.get("DB_INIT_MODE")
    source_sha_was_present = "PROJECT6_SOURCE_SHA" in os.environ
    db_init_mode_was_present = "DB_INIT_MODE" in os.environ

    try:
        return _collect_ready_build_info(repo_root)
    finally:
        if source_sha_was_present:
            os.environ["PROJECT6_SOURCE_SHA"] = original_source_sha or ""
        else:
            os.environ.pop("PROJECT6_SOURCE_SHA", None)
        if db_init_mode_was_present:
            os.environ["DB_INIT_MODE"] = original_db_init_mode or ""
        else:
            os.environ.pop("DB_INIT_MODE", None)


def _collect_ready_build_info(repo_root: Path) -> dict[str, Any]:
    existing_sha = os.environ.get("PROJECT6_SOURCE_SHA", "").strip()
    if not SOURCE_SHA_RE.fullmatch(existing_sha):
        git_sha = _current_git_sha(repo_root)
        if git_sha != "unknown":
            os.environ["PROJECT6_SOURCE_SHA"] = git_sha
    os.environ.setdefault("DB_INIT_MODE", "none")

    backend_path = str(repo_root / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    importlib.invalidate_caches()
    main = importlib.import_module("main")

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, _statement: object) -> None:
            return None

    main.SessionLocal = lambda: Session()
    response = main.ready()
    payload = json.loads(response.body.decode("utf-8"))
    build = payload.get("build") or {}
    return {
        "source": READY_BUILD_INFO_SOURCE,
        "ready_status_code": response.status_code,
        "status": payload.get("status"),
        "version": build.get("version"),
        "source_sha": build.get("source_sha"),
    }


def _check_workflow_contains(gate: dict[str, Any], repo_root: Path) -> tuple[bool, str]:
    path_value = gate.get("path")
    if not path_value:
        return False, "missing workflow path"
    path = (repo_root / str(path_value)).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        return False, "workflow path escapes repo root"
    if not path.exists():
        return False, f"{path_value} does not exist"
    text = path.read_text(encoding="utf-8")
    missing = [token for token in gate.get("must_contain", []) if token not in text]
    if missing:
        return False, "missing tokens: " + ", ".join(missing)
    return True, ""


def _run_gate(
    gate: dict[str, Any],
    repo_root: Path,
    command_runner: Any,
) -> dict[str, Any]:
    gate_id = str(gate["id"])
    kind = str(gate.get("kind", ""))
    start = time.monotonic()
    base: dict[str, Any] = {"id": gate_id, "kind": kind, "profile_scope": gate.get("profile_scope")}

    if kind in {"command", "pytest"}:
        command = gate.get("command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            return {**base, "status": "fail", "error": "command must be a list of strings"}
        result = command_runner(command, repo_root)
        return {
            **base,
            "status": "pass" if result.returncode == 0 else "fail",
            "command": command,
            "returncode": result.returncode,
            "stdout_tail": _tail(result.stdout),
            "stderr_tail": _tail(result.stderr),
            "duration_seconds": round(time.monotonic() - start, 3),
        }

    if kind == "workflow_contains":
        ok, detail = _check_workflow_contains(gate, repo_root)
        return {
            **base,
            "status": "pass" if ok else "fail",
            "path": gate.get("path"),
            "detail": detail,
            "duration_seconds": round(time.monotonic() - start, 3),
        }

    return {**base, "status": "fail", "error": f"unsupported gate kind {kind!r}"}


def run_release_readiness(
    manifest_path: Path,
    *,
    repo_root: Path | None = None,
    command_runner: Any = run_subprocess,
    build_info_provider: Any = collect_ready_build_info,
) -> dict[str, Any]:
    root = (repo_root or default_repo_root()).resolve()
    manifest = _load_yaml(Path(manifest_path))
    _validate_manifest(manifest)

    build_identity = build_info_provider(root)
    gates = [_run_gate(gate, root, command_runner) for gate in manifest["required_gates"]]
    build_ok = (
        build_identity.get("version") == manifest.get("release", {}).get("version")
        and SOURCE_SHA_RE.fullmatch(str(build_identity.get("source_sha", ""))) is not None
        and build_identity.get("ready_status_code", 200) == 200
    )
    status = "pass" if build_ok and all(gate["status"] == "pass" for gate in gates) else "fail"
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "release": manifest["release"],
        "build_identity": build_identity,
        "build_identity_status": "pass" if build_ok else "fail",
        "owner_selected_profile_specific_gates": manifest["owner_selected_profile_specific_gates"],
        "gates": gates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the profile-neutral release readiness gates.")
    parser.add_argument(
        "--manifest",
        default=str(default_repo_root() / "config" / "release_readiness.yaml"),
        help="Path to the release readiness manifest.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root()),
        help="Repository root used for commands and static workflow checks.",
    )
    args = parser.parse_args(argv)

    try:
        report = run_release_readiness(Path(args.manifest), repo_root=Path(args.repo_root))
    except Exception as exc:
        report = {
            "schema_id": SCHEMA_ID,
            "status": "fail",
            "error": str(exc),
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
