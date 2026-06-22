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
from support_matrix_constants import UNSUPPORTED_CAPABILITIES


SCHEMA_ID = "project6.rc2_public_connectors_acceptance.v1"
EXPECTED_VERSION = "0.2.0-rc1"
SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$", re.IGNORECASE)

PROFILE = {
    "base": "local_expert",
    "overlays": ["public_connectors"],
    "scope": "public/anonymous connectors only",
    "proof_level": "operator-workflow + local-deployment",
}

EXCLUDED_SURFACES = [
    "SEC",
    "OCR",
    "model/agent egress",
    "nonlocal deployment",
    "keyed connectors",
    "high availability",
    "real provider delivery",
]

FORBIDDEN_SUPPORTED_CAPABILITIES = UNSUPPORTED_CAPABILITIES | {"sec_live_network_egress"}

COMMAND_CHECKS = [
    {
        "id": "support_matrix_public_connectors_overlay_valid",
        "title": "Support matrix validates the public_connectors overlay",
        "evidence": ["scripts/support_matrix_check.py", "config/support_matrix.yaml"],
        "command": ["python", "./scripts/support_matrix_check.py"],
    },
    {
        "id": "pr1_correctness_regressions",
        "title": "PR-1 connector correctness regressions stay green",
        "evidence": [
            "tests/test_api.py::test_sciencebase_download_429_retryable_sets_backoff",
            "tests/test_api.py::test_senate_lda_dedupes_duplicate_filings_and_records_provenance",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./tests/test_api.py::test_sciencebase_download_429_retryable_sets_backoff",
            "./tests/test_api.py::test_senate_lda_dedupes_duplicate_filings_and_records_provenance",
            "-q",
        ],
    },
    {
        "id": "pr2_l17_negative_cases",
        "title": "PR-2 L17 negative and schema cases stay bounded",
        "evidence": [
            "tests/test_api.py::test_l17_sciencebase_download_negatives_are_bounded_and_observable",
            "tests/test_api.py::test_l17_sciencebase_additive_schema_is_tolerated",
            "tests/test_api.py::test_l17_sciencebase_malformed_schema_is_rejected_explicitly",
            "tests/test_api.py::test_l17_sciencebase_partial_page_is_degraded_not_complete",
            "tests/test_api.py::test_l17_senate_lda_detail_errors_are_terminal_or_retryable",
            "tests/test_api.py::test_l17_senate_lda_missing_required_schema_is_rejected_explicitly",
            "tests/test_api.py::test_l17_senate_lda_partial_page_is_degraded_not_complete",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./tests/test_api.py::test_l17_sciencebase_download_negatives_are_bounded_and_observable",
            "./tests/test_api.py::test_l17_sciencebase_additive_schema_is_tolerated",
            "./tests/test_api.py::test_l17_sciencebase_malformed_schema_is_rejected_explicitly",
            "./tests/test_api.py::test_l17_sciencebase_partial_page_is_degraded_not_complete",
            "./tests/test_api.py::test_l17_senate_lda_detail_errors_are_terminal_or_retryable",
            "./tests/test_api.py::test_l17_senate_lda_missing_required_schema_is_rejected_explicitly",
            "./tests/test_api.py::test_l17_senate_lda_partial_page_is_degraded_not_complete",
            "-q",
        ],
    },
    {
        "id": "pr3_l20_lifecycle_postures",
        "title": "PR-3 L20 lifecycle and resume postures stay green",
        "evidence": [
            "tests/test_api.py::test_connector_l20_terminal_resume_is_noop_for_public_connectors",
            "tests/test_api.py::test_connector_l20_expired_running_lease_resume_requeues_public_connectors",
            "tests/test_api.py::test_connector_l20_sciencebase_active_lease_records_conflict",
            "tests/test_api.py::test_connector_l20_sciencebase_cancel_mid_target_stops_before_partial_authority",
            "tests/test_api.py::test_connector_resume_reuses_discovery_checkpoint_cursor",
            "tests/test_api.py::test_connector_resume_target_cursor_keeps_retryable_prior_targets",
            "tests/test_api.py::test_senate_lda_connector_resume_uses_senate_executor",
            "tests/test_api.py::test_senate_lda_l20_active_lease_records_conflict",
            "tests/test_api.py::test_senate_lda_l20_cancel_mid_page_stops_before_partial_authority",
            "tests/test_api.py::test_senate_lda_l20_resume_after_target_creation_crash_does_not_duplicate_targets",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./tests/test_api.py::test_connector_l20_terminal_resume_is_noop_for_public_connectors",
            "./tests/test_api.py::test_connector_l20_expired_running_lease_resume_requeues_public_connectors",
            "./tests/test_api.py::test_connector_l20_sciencebase_active_lease_records_conflict",
            "./tests/test_api.py::test_connector_l20_sciencebase_cancel_mid_target_stops_before_partial_authority",
            "./tests/test_api.py::test_connector_resume_reuses_discovery_checkpoint_cursor",
            "./tests/test_api.py::test_connector_resume_target_cursor_keeps_retryable_prior_targets",
            "./tests/test_api.py::test_senate_lda_connector_resume_uses_senate_executor",
            "./tests/test_api.py::test_senate_lda_l20_active_lease_records_conflict",
            "./tests/test_api.py::test_senate_lda_l20_cancel_mid_page_stops_before_partial_authority",
            "./tests/test_api.py::test_senate_lda_l20_resume_after_target_creation_crash_does_not_duplicate_targets",
            "-q",
        ],
    },
    {
        "id": "pr4_l11_source_fidelity",
        "title": "PR-4 L11 connector source fidelity stays green",
        "evidence": [
            "tests/test_api.py::test_sciencebase_csv_ingest_preserves_l11_source_fidelity",
            "tests/test_api.py::test_connector_cross_surface_dedupe_prefers_files",
            "tests/test_api.py::test_senate_lda_dedupes_duplicate_filings_and_records_provenance",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./tests/test_api.py::test_sciencebase_csv_ingest_preserves_l11_source_fidelity",
            "./tests/test_api.py::test_connector_cross_surface_dedupe_prefers_files",
            "./tests/test_api.py::test_senate_lda_dedupes_duplicate_filings_and_records_provenance",
            "-q",
        ],
    },
    {
        "id": "pr5_canonical_connector_journey",
        "title": "PR-5 canonical connector journey stays green",
        "evidence": [
            "tests/test_api.py::test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis",
            "tests/test_api.py::test_public_connector_journey_network_unreachable_is_degraded",
            "tests/test_api.py::test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./tests/test_api.py::test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis",
            "./tests/test_api.py::test_public_connector_journey_network_unreachable_is_degraded",
            "./tests/test_api.py::test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey",
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


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return loaded


def _release_owner_gates(repo_root: Path) -> list[Any] | None:
    try:
        manifest = _load_json(repo_root / "config" / "release_readiness.yaml")
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


def _version_criterion(build_identity: dict[str, Any]) -> dict[str, Any]:
    status = _build_identity_status(build_identity)
    return {
        "id": "version_bumped_to_rc2",
        "title": "Release identity is bumped to RC2",
        "status": status,
        "execution": "inspected",
        "evidence": ["backend/app/_version.py", "config/release_readiness.yaml"],
        "expected_version": EXPECTED_VERSION,
        "observed_version": build_identity.get("version"),
        "observed_source_sha": build_identity.get("source_sha"),
    }


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


def _forbidden_surface_boundary_criterion(repo_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        matrix = _load_json(repo_root / "config" / "support_matrix.yaml")
        capabilities = matrix.get("capabilities")
        if not isinstance(capabilities, list):
            raise ValueError("capabilities must be a list")
        by_id = {item.get("id"): item for item in capabilities if isinstance(item, dict)}
        if matrix.get("profile") != PROFILE["base"]:
            errors.append("support matrix profile is not local_expert")
        if matrix.get("overlays") != PROFILE["overlays"]:
            errors.append("support matrix overlays are not ['public_connectors']")
        for capability_id in sorted(FORBIDDEN_SUPPORTED_CAPABILITIES):
            if by_id.get(capability_id, {}).get("status") != "unsupported":
                errors.append(f"{capability_id} must remain unsupported")
        if by_id.get("ocr_external_engine", {}).get("status") != "experimental_default_off":
            errors.append("ocr_external_engine must remain experimental_default_off")
        boundary_note = str(matrix.get("boundary_note") or "")
        for token in ("No SEC", "OCR", "model/agent egress", "nonlocal", "keyed connector", "HA"):
            if token not in boundary_note:
                errors.append(f"boundary_note missing {token!r}")
    except Exception as exc:
        errors.append(str(exc))

    return {
        "id": "forbidden_surface_boundary",
        "title": "Public connector overlay does not claim forbidden surfaces",
        "status": "pass" if not errors else "fail",
        "execution": "inspected",
        "evidence": ["config/support_matrix.yaml", "docs/rc2-public-connectors-acceptance.md"],
        "excluded_surfaces": EXCLUDED_SURFACES,
        "errors": errors,
    }


def run_rc2_acceptance(
    *,
    repo_root: Path | None = None,
    command_runner: Any = run_subprocess,
    build_info_provider: Any = release_readiness_check.collect_ready_build_info,
) -> dict[str, Any]:
    root = (repo_root or default_repo_root()).resolve()
    build_identity = build_info_provider(root)
    owner_gates = _release_owner_gates(root)

    criteria = [_version_criterion(build_identity)]
    criteria.extend(
        _command_criterion(check, repo_root=root, command_runner=command_runner)
        for check in COMMAND_CHECKS
    )
    criteria.append(_forbidden_surface_boundary_criterion(root))

    owner_gate_status = "pass" if owner_gates == [] else "fail"
    criteria_ok = all(item["status"] == "pass" for item in criteria)
    verdict = "PASS" if owner_gate_status == "pass" and criteria_ok else "FAIL"

    return {
        "schema_id": SCHEMA_ID,
        "verdict": verdict,
        "profile": PROFILE,
        "build_identity": build_identity,
        "build_identity_status": _build_identity_status(build_identity),
        "release_readiness_owner_selected_profile_specific_gates": owner_gates,
        "release_readiness_owner_gate_status": owner_gate_status,
        "excluded_surfaces": EXCLUDED_SURFACES,
        "owner_signoff_required_before_merge": True,
        "criteria": criteria,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the RC2 public connectors acceptance capstone.")
    parser.add_argument("--json", action="store_true", help="emit the structured JSON acceptance report")
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root()),
        help="Repository root used for checks and identity collection.",
    )
    args = parser.parse_args(argv)

    report = run_rc2_acceptance(repo_root=Path(args.repo_root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
