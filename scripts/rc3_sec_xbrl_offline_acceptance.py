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


SCHEMA_ID = "project6.rc3_sec_xbrl_offline_acceptance.v1"
EXPECTED_VERSION = "0.3.0-rc1"
SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$", re.IGNORECASE)

PROFILE = {
    "base": "local_expert",
    "overlays": ["public_connectors", "sec_xbrl_offline"],
    "scope": "sec_xbrl offline/simulation only",
    "proof_level": "operator-workflow + local-deployment",
}

EXCLUDED_SURFACES = [
    "live SEC egress",
    "value-reveal default-on",
    "Arelle network resolution",
    "source acquisition",
    "model/agent egress",
    "nonlocal deployment",
    "keyed connectors",
    "high availability",
    "real provider delivery",
]

PINNED_FALSE_FLAGS = [
    "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "LAYER3_MODEL_EGRESS_ENABLED",
    "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
    "LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED",
]

BOUNDARY_TOKENS = [
    "live SEC egress explicit default-off",
    "no value-reveal default-on",
    "no agent egress",
    "no nonlocal",
]

UNSUPPORTED_CAPABILITIES = {
    "real_provider_delivery",
    "model_agent_egress",
    "nonlocal_multi_trust_multi_identity",
    "high_availability",
    "keyed_connectors",
    "signed_reference_export",
}

EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES = {
    "sec_live_network_egress",
    "sec_value_reveal",
    "sec_controlled_value_reveal_submit",
    "arelle_internal_value_store",
    "arelle_corpus_validation",
    "sec_xbrl_production_admission_evaluator",
}

FORBIDDEN_SUPPORTED_CAPABILITIES = (
    UNSUPPORTED_CAPABILITIES | EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES
)

OFFLINE_SIMULATION_CAPABILITIES = {
    "layer3_sec_xbrl_offline_evidence_loader",
    "layer3_sec_xbrl_offline_companyfacts_stage",
    "layer3_sec_xbrl_offline_companyfacts_oracle_packet",
    "layer3_sec_xbrl_e2e_offline_orchestrator",
    "layer3_sec_xbrl_offline_evidence_proof_capability",
}

SEC_XBRL_TEST_FILES = [
    "./backend/tests/test_sec_xbrl_arelle_helper.py",
    "./backend/tests/test_sec_xbrl_arelle_provisioning.py",
    "./backend/tests/test_sec_xbrl_auth_binding_receipt.py",
    "./backend/tests/test_sec_xbrl_auth_owner_binding_strategy.py",
    "./backend/tests/test_sec_xbrl_broader_corpus_reliability_gate.py",
    "./backend/tests/test_sec_xbrl_canonical_comparability.py",
    "./backend/tests/test_sec_xbrl_canonical_coverage_breadth.py",
    "./backend/tests/test_sec_xbrl_canonical_projection.py",
    "./backend/tests/test_sec_xbrl_canonical_retained_coherence.py",
    "./backend/tests/test_sec_xbrl_canonical_statement_organization.py",
    "./backend/tests/test_sec_xbrl_committed_report_redaction.py",
    "./backend/tests/test_sec_xbrl_default_on_admission_restatement.py",
    "./backend/tests/test_sec_xbrl_default_on_admission_review.py",
    "./backend/tests/test_sec_xbrl_default_on_gate.py",
    "./backend/tests/test_sec_xbrl_default_on_runtime.py",
    "./backend/tests/test_sec_xbrl_default_posture_decision.py",
    "./backend/tests/test_sec_xbrl_diagnostic_framework.py",
    "./backend/tests/test_sec_xbrl_e2e_guard.py",
    "./backend/tests/test_sec_xbrl_e2e_integration.py",
    "./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py",
    "./backend/tests/test_sec_xbrl_h6_quarantine.py",
    "./backend/tests/test_sec_xbrl_in_app_auth_policy_validation.py",
    "./backend/tests/test_sec_xbrl_measure_companyfacts.py",
    "./backend/tests/test_sec_xbrl_multi_filing_evidence_authority_gate.py",
    "./backend/tests/test_sec_xbrl_multi_period_projection.py",
    "./backend/tests/test_sec_xbrl_nonlocal_admission_disposition.py",
    "./backend/tests/test_sec_xbrl_nonlocal_production_readiness_gate.py",
    "./backend/tests/test_sec_xbrl_offline_evidence_loader.py",
    "./backend/tests/test_sec_xbrl_offline_evidence_proof_capability.py",
    "./backend/tests/test_sec_xbrl_operator_review_workflow.py",
    "./backend/tests/test_sec_xbrl_operator_runbook_matrix_selection.py",
    "./backend/tests/test_sec_xbrl_projection_persistence.py",
    "./backend/tests/test_sec_xbrl_proxy_identity_readonly_projection.py",
    "./backend/tests/test_sec_xbrl_public_authority_guard.py",
    "./backend/tests/test_sec_xbrl_real_corpus_product_runner.py",
    "./backend/tests/test_sec_xbrl_report_leak_guard.py",
    "./backend/tests/test_sec_xbrl_role_cap.py",
    "./backend/tests/test_sec_xbrl_route_level_auth_enforcement.py",
    "./backend/tests/test_sec_xbrl_runtime_posture.py",
    "./backend/tests/test_sec_xbrl_runtime_posture_freshness.py",
    "./backend/tests/test_sec_xbrl_runtime_posture_operator_identity.py",
    "./backend/tests/test_sec_xbrl_s1_proof_snapshots_consistent.py",
    "./backend/tests/test_sec_xbrl_sector_family_coverage.py",
    "./backend/tests/test_sec_xbrl_sidecar.py",
    "./backend/tests/test_sec_xbrl_statement_assembly.py",
    "./backend/tests/test_sec_xbrl_statement_packet_persistence.py",
    "./backend/tests/test_sec_xbrl_stratified_matrix_readiness_decision.py",
    "./backend/tests/test_sec_xbrl_stratified_real_filing_validation_matrix_preflight.py",
    "./backend/tests/test_sec_xbrl_value_reveal_authority_provisioning_preflight.py",
    "./backend/tests/test_sec_xbrl_value_reveal_guard_contracts.py",
    "./backend/tests/test_sec_xbrl_value_reveal_operator_exercise.py",
    "./backend/tests/test_sec_xbrl_value_reveal_operator_exercise_runner.py",
]

COMPANYFACTS_OFFLINE_TEST_FILES = [
    "./backend/tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py",
]

RC2_PUBLIC_CONNECTOR_REGRESSION_TESTS = [
    "./tests/test_api.py::test_sciencebase_download_429_retryable_sets_backoff",
    "./tests/test_api.py::test_senate_lda_dedupes_duplicate_filings_and_records_provenance",
    "./tests/test_api.py::test_l17_sciencebase_download_negatives_are_bounded_and_observable",
    "./tests/test_api.py::test_l17_sciencebase_additive_schema_is_tolerated",
    "./tests/test_api.py::test_l17_sciencebase_malformed_schema_is_rejected_explicitly",
    "./tests/test_api.py::test_l17_sciencebase_partial_page_is_degraded_not_complete",
    "./tests/test_api.py::test_l17_senate_lda_detail_errors_are_terminal_or_retryable",
    "./tests/test_api.py::test_l17_senate_lda_missing_required_schema_is_rejected_explicitly",
    "./tests/test_api.py::test_l17_senate_lda_partial_page_is_degraded_not_complete",
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
    "./tests/test_api.py::test_sciencebase_csv_ingest_preserves_l11_source_fidelity",
    "./tests/test_api.py::test_connector_cross_surface_dedupe_prefers_files",
    "./tests/test_api.py::test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis",
    "./tests/test_api.py::test_public_connector_journey_network_unreachable_is_degraded",
    "./tests/test_api.py::test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey",
]

COMMAND_CHECKS = [
    {
        "id": "build_identity_release_readiness_check",
        "title": "Release readiness validates RC3 build identity and profile-neutral gates",
        "evidence": ["scripts/release_readiness_check.py", "config/release_readiness.yaml"],
        "command": ["python", "./scripts/release_readiness_check.py"],
    },
    {
        "id": "support_matrix_rc3_offline_overlay_valid",
        "title": "Support matrix validates the RC3 offline overlay",
        "evidence": ["scripts/support_matrix_check.py", "config/support_matrix.yaml"],
        "command": ["python", "./scripts/support_matrix_check.py"],
    },
    {
        "id": "pr3_offline_loader_oracle_honesty",
        "title": "PR-3 loader and proof honesty controls stay green",
        "evidence": [
            "backend/tests/test_sec_xbrl_offline_evidence_loader.py",
            "backend/tests/test_sec_xbrl_offline_evidence_proof_capability.py",
        ],
        "command": [
            "python",
            "-m",
            "pytest",
            "./backend/tests/test_sec_xbrl_offline_evidence_loader.py",
            "./backend/tests/test_sec_xbrl_offline_evidence_proof_capability.py",
            "-q",
        ],
    },
    {
        "id": "pr4_offline_orchestrator_honesty",
        "title": "PR-4 orchestrator honesty controls stay green",
        "evidence": ["backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py"],
        "command": [
            "python",
            "-m",
            "pytest",
            "./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py",
            "-q",
        ],
    },
    {
        "id": "companyfacts_stage_oracle_offline_honesty",
        "title": "Companyfacts stage and oracle offline simulation tests stay green",
        "evidence": COMPANYFACTS_OFFLINE_TEST_FILES,
        "command": ["python", "-m", "pytest", *COMPANYFACTS_OFFLINE_TEST_FILES, "-q"],
    },
    {
        "id": "pr5_full_sec_xbrl_suite",
        "title": "Full SEC XBRL suite stays green",
        "evidence": SEC_XBRL_TEST_FILES,
        "command": ["python", "-m", "pytest", *SEC_XBRL_TEST_FILES, "-q"],
    },
    {
        "id": "rc2_public_connector_acceptance_regression",
        "title": "Full RC2 public connector acceptance checks still pass under RC3 profile",
        "evidence": RC2_PUBLIC_CONNECTOR_REGRESSION_TESTS,
        "command": ["python", "-m", "pytest", *RC2_PUBLIC_CONNECTOR_REGRESSION_TESTS, "-q"],
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
        "id": "build_identity_bumped_to_rc3",
        "title": "Release identity is bumped to RC3",
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
            errors.append("support matrix overlays are not ['public_connectors', 'sec_xbrl_offline']")
        if matrix.get("pinned_false_flags") != PINNED_FALSE_FLAGS:
            errors.append("pinned_false_flags must match the selected local_expert pin set")
        for capability_id in sorted(UNSUPPORTED_CAPABILITIES):
            if by_id.get(capability_id, {}).get("status") != "unsupported":
                errors.append(f"{capability_id} must remain unsupported")
        for capability_id in sorted(EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES):
            if by_id.get(capability_id, {}).get("status") != "experimental_default_off":
                errors.append(f"{capability_id} must remain experimental_default_off")
        for capability_id in sorted(OFFLINE_SIMULATION_CAPABILITIES):
            if by_id.get(capability_id, {}).get("status") != "simulation":
                errors.append(f"{capability_id} must remain simulation-only")
        boundary_note = str(matrix.get("boundary_note") or "")
        for token in BOUNDARY_TOKENS:
            if token not in boundary_note:
                errors.append(f"boundary_note missing {token!r}")
    except Exception as exc:
        errors.append(str(exc))

    return {
        "id": "forbidden_surface_boundary",
        "title": "SEC XBRL offline overlay stays simulation-only and bounded",
        "status": "pass" if not errors else "fail",
        "execution": "inspected",
        "evidence": ["config/support_matrix.yaml"],
        "excluded_surfaces": EXCLUDED_SURFACES,
        "forbidden_supported_capabilities": sorted(FORBIDDEN_SUPPORTED_CAPABILITIES),
        "offline_simulation_capabilities": sorted(OFFLINE_SIMULATION_CAPABILITIES),
        "pinned_false_flags": PINNED_FALSE_FLAGS,
        "boundary_tokens": BOUNDARY_TOKENS,
        "errors": errors,
    }


def run_rc3_acceptance(
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
    parser = argparse.ArgumentParser(description="Run the RC3 SEC XBRL offline acceptance capstone.")
    parser.add_argument("--json", action="store_true", help="emit the structured JSON acceptance report")
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root()),
        help="Repository root used for checks and identity collection.",
    )
    args = parser.parse_args(argv)

    report = run_rc3_acceptance(repo_root=Path(args.repo_root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
