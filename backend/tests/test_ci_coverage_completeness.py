from __future__ import annotations

from fnmatch import fnmatch
import json
from pathlib import Path
import re
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_TESTS_ROOT = REPO_ROOT / "backend" / "tests"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "playwright.yml"
RELEASE_READINESS_MANIFEST_PATH = REPO_ROOT / "config" / "release_readiness.yaml"

BACKEND_SHARD_PATTERNS = (
    "test_admission_evaluator_*.py",
    "test_aps_retrieval_*.py",
    "test_backend_config.py",
    "test_ci_coverage_completeness.py",
    "test_deployment_profile_*.py",
    "test_diagnostics_ref_*.py",
    "test_dual_live_sciencebase_producer.py",
    "test_egress_effect_boundary.py",
    "test_sciencebase_live_readiness.py",
    "test_sciencebase_spent_marker.py",
    "test_honesty_*.py",
    "test_legacy_api_*.py",
    "test_layer3_*.py",
    "test_market_*.py",
    "test_analyst_*.py",
    "test_nrc_aps_*.py",
    "test_pre_body_*.py",
    "test_review_browser_*.py",
    "test_review_nrc_aps_candidate_b_trace_*.py",
    "test_review_nrc_aps_document_trace_page.py",
    "test_review_nrc_aps_gate_reports.py",
    "test_review_nrc_aps_operator_identity*.py",
    "test_review_nrc_aps_page.py",
    "test_review_nrc_aps_workbench_compare_*.py",
    "test_release_*.py",
    "test_sec_refs.py",
    "test_sec_xbrl_*.py",
    "test_support_matrix.py",
    "test_visual_artifact_*.py",
)

RUNTIME_REQUIRED_REASON = (
    "requires-prebuilt-nrc-aps-local-corpus-runtime: tests depend on an existing "
    "storage_test_runtime/lc_e2e run database and storage tree; fresh CI does "
    "not generate runtime artifacts in validate-only backend shards"
)

EXCLUDED_BACKEND_TESTS = {
    "test_review_nrc_aps_api.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_catalog.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_details.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_document_trace_api.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_document_trace_service.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_graph.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_runtime_db.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_tree.py": RUNTIME_REQUIRED_REASON,
}

EXPECTED_RELEASE_GATE_COVERAGE = {
    "deployment_profile_fail_closed_validation": {
        "kind": "command",
        "test_path": "backend/tests/test_deployment_profile_validation.py",
    },
    "ci_coverage_completeness": {
        "kind": "command",
        "test_path": "backend/tests/test_ci_coverage_completeness.py",
    },
    "backend_migrations_postgres_golden_path": {
        "kind": "workflow_contains",
        "job_id": "backend-migrations-postgres",
    },
    "backend_coverage_floor": {
        "kind": "workflow_contains",
        "job_id": "backend-coverage",
    },
    "release_lock_install": {
        "kind": "workflow_contains",
        "job_id": "release-lock-install",
    },
}

RELEASE_GATE_AGGREGATED_JOBS = (
    "release-lock-install",
    "backend-layer3-api",
    "backend-coverage",
    "backend-migrations-postgres",
    "sec-xbrl-arelle-provisioning",
    "root-tests",
    "nrc-aps-ocr",
    "dual-live-windows-boundary",
    "test",
)


def _backend_test_files() -> list[str]:
    return sorted(path.name for path in BACKEND_TESTS_ROOT.glob("test_*.py") if path.is_file())


def _covered_by_backend_shard(file_name: str) -> bool:
    return any(fnmatch(file_name, pattern) for pattern in BACKEND_SHARD_PATTERNS)


def _workflow_backend_patterns() -> tuple[str, ...]:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"patterns = \(\s*(?P<body>.*?)\s*\)\s*files = sorted",
        workflow_text,
        flags=re.DOTALL,
    )
    assert match is not None, "Could not locate backend shard patterns tuple in playwright.yml"
    return tuple(re.findall(r'"([^"]+\.py)"', match.group("body")))


def _workflow_job_ids() -> set[str]:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", workflow_text, flags=re.MULTILINE))


def _workflow_job_block(job_id: str) -> str:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    match = re.search(
        rf"^  {re.escape(job_id)}:\s*$\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\s*$|\Z)",
        workflow_text,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert match is not None, f"Could not locate workflow job {job_id!r}"
    return match.group("body")


def _workflow_job_needs(job_id: str) -> tuple[str, ...]:
    job_block = _workflow_job_block(job_id)
    match = re.search(
        r"^    needs:\s*\n(?P<body>(?:      - [A-Za-z0-9_-]+\s*\n)+)",
        job_block,
        flags=re.MULTILINE,
    )
    assert match is not None, f"Could not locate workflow needs for job {job_id!r}"
    return tuple(
        re.findall(r"^      - ([A-Za-z0-9_-]+)\s*$", match.group("body"), flags=re.MULTILINE)
    )


def _release_readiness_manifest() -> dict:
    return json.loads(RELEASE_READINESS_MANIFEST_PATH.read_text(encoding="utf-8"))


def _collect_pytest_nodeids(relative_path: str) -> list[str]:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", relative_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    nodeids = [
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if "::" in line
    ]
    assert nodeids, f"{relative_path} collected no pytest node ids"
    return nodeids


def test_backend_test_files_are_ci_covered_or_allowlisted() -> None:
    all_files = _backend_test_files()
    assert all_files, "backend/tests/test_*.py inventory is empty"

    missing_allowlist_entries = [
        file_name for file_name in EXCLUDED_BACKEND_TESTS if file_name not in all_files
    ]
    assert missing_allowlist_entries == []

    covered = {file_name for file_name in all_files if _covered_by_backend_shard(file_name)}
    excluded = set(EXCLUDED_BACKEND_TESTS)
    uncovered = sorted(set(all_files) - covered - excluded)
    assert uncovered == []


def test_backend_test_allowlist_is_concrete_and_not_shadow_covered() -> None:
    for file_name, reason in EXCLUDED_BACKEND_TESTS.items():
        assert reason.startswith("requires-"), file_name
        assert "runtime" in reason, file_name
        assert not _covered_by_backend_shard(file_name), file_name


def test_backend_shard_pattern_mirror_matches_workflow() -> None:
    workflow_patterns = _workflow_backend_patterns()
    assert workflow_patterns == BACKEND_SHARD_PATTERNS
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    for pattern in BACKEND_SHARD_PATTERNS:
        assert f'"{pattern}"' in workflow_text


def test_release_readiness_manifest_gates_map_to_ci_jobs_or_collected_tests() -> None:
    manifest = _release_readiness_manifest()
    gates_by_id = {gate["id"]: gate for gate in manifest["required_gates"]}
    assert set(gates_by_id) == set(EXPECTED_RELEASE_GATE_COVERAGE)

    workflow_jobs = _workflow_job_ids()
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    for gate_id, expected in EXPECTED_RELEASE_GATE_COVERAGE.items():
        gate = gates_by_id[gate_id]
        assert gate["kind"] == expected["kind"], gate_id

        if expected["kind"] == "command":
            relative_path = expected["test_path"]
            file_name = Path(relative_path).name
            command_parts = [str(part).lstrip("./").replace("\\", "/") for part in gate["command"]]
            assert (REPO_ROOT / relative_path).exists(), gate_id
            assert relative_path in command_parts, gate_id
            assert _covered_by_backend_shard(file_name), gate_id
            nodeids = _collect_pytest_nodeids(relative_path)
            assert any(nodeid.startswith(f"{relative_path}::") for nodeid in nodeids), gate_id
            continue

        job_id = expected["job_id"]
        assert job_id in workflow_jobs, gate_id
        assert job_id in gate["must_contain"], gate_id
        for token in gate["must_contain"]:
            assert token in workflow_text, f"{gate_id} missing workflow token {token!r}"


def test_release_gate_job_runs_manifest_runner_after_manifest_ci_jobs() -> None:
    workflow_jobs = _workflow_job_ids()
    assert "release-gate" in workflow_jobs

    gate_block = _workflow_job_block("release-gate")
    assert "if: ${{ always() }}" in gate_block
    assert "python ./scripts/release_readiness_check.py" in gate_block
    assert "python ./scripts/rc3_sec_xbrl_offline_acceptance.py --json" in gate_block
    assert set(_workflow_job_needs("release-gate")) == set(RELEASE_GATE_AGGREGATED_JOBS)
    assert gate_block.index("python ./scripts/release_readiness_check.py") < gate_block.index(
        "python ./scripts/rc3_sec_xbrl_offline_acceptance.py --json"
    )
    for job_id in RELEASE_GATE_AGGREGATED_JOBS:
        assert job_id in gate_block
        assert f"needs['{job_id}'].result" in gate_block


def test_backend_coverage_comment_matches_enforced_floor() -> None:
    coverage_block = _workflow_job_block("backend-coverage")
    assert "--cov-fail-under=90" in coverage_block
    assert "Coverage floor is set to 90%" in coverage_block
    assert "30%" not in coverage_block


def test_dual_live_windows_boundary_job_is_required_and_exact() -> None:
    block = _workflow_job_block("dual-live-windows-boundary")

    for token in (
        "runs-on: windows-2025", 'python-version: "3.12"',
        "https://www.python.org/ftp/python/3.12.6/python-3.12.6-embed-amd64.zip",
        "a86a2e28870967745d255cc597d1e4d19ae79e65e927cdc324baa0256202231c",
        "CreateAppContainerProfile", "DeriveAppContainerSidFromAppContainerName",
        "DeleteAppContainerProfile", "PROJECT6_B0_BUNDLE_BINDING",
        "Deny B0 bundle before Package SID grant", "Grant exact protected B0 bundle ACL",
        "Teardown disposable B0 profile and closure", "if: ${{ always() }}",
        "/inheritance:r", "(RX)", "tools/dual_live_run.py",
        "backend/app/services/dual_live_windows_boundary.py",
        "backend/app/services/dual_live_worker_bundle.py",
        "backend/app/services/dual_live_effect_guard.py",
        "backend/app/services/dual_live_sciencebase_producer.py",
        "backend/app/services/connector_egress_contract.py", "-m pytest",
        'mode="sciencebase"', "LocalBrokerTransport", "sciencebase-proof.py",
        "from app.services.dual_live_effect_guard import",
        "$env:PYTHONPATH = (Join-Path $Repo 'backend')",
        "$brokerPassword = 'P6!b0Ci9xQ2#'",
        "-RedirectStandardError $profileStderr",
        "creation failed (exit $($created.ExitCode))",
        "$env:TEMP = $stateRoot", "$env:TEMP = $state.state_root",
        "campaign_root = $stateRoot",
        "[Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)",
        "$brokerProfileRoot = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)",
        "$userDataRoot = Join-Path $brokerProfileRoot 'AppData\\Local'",
        "New-Item -ItemType Directory -Path $userDataRoot -Force",
        'LookupPrivilegeValue(null, "SeRestorePrivilege"',
        "[P6RestorePrivilege]::Enable()", "Exact bundle owner assignment failed",
        "DriveType -ne [IO.DriveType]::Fixed", "FileAttributes]::ReparsePoint",
        "[StringComparer]::Ordinal",
        "$hr -notin @(0, -2147023728)",
        "PROJECT6_B0_PROVISIONING_ROOT", "partial B0 root removal failed",
        "$teardownFailures", "broker account removal failed",
    ):
        assert token in block
    for test_path in (
        "./backend/tests/test_egress_effect_boundary.py",
        "./backend/tests/test_dual_live_sciencebase_producer.py",
        "./backend/tests/test_sciencebase_live_readiness.py",
        "./backend/tests/test_sciencebase_spent_marker.py",
        "./tests/test_dual_live_effect_guard.py",
        "./tests/test_dual_live_worker_bundle.py",
        "./tests/test_dual_live_runtime.py",
        "./tests/test_sciencebase_no_signature_rehearsal.py",
    ):
        assert test_path in block

    assert block.index("Deny B0 bundle before Package SID grant") < block.index(
        "Grant exact protected B0 bundle ACL"
    ) < block.index("Prove B0 AppContainer and effect boundary")
    assert block.index("profile_created = $true") < block.index(
        "$created = Start-Process powershell.exe"
    )
    assert "[uint32]$hr" not in block
    assert block.index('"PROJECT6_B0_STATE=$statePath"') < block.index(
        "New-Item -ItemType Directory"
    )
    assert block.index("git config --global core.longpaths true") < block.index(
        "actions/checkout@v6"
    )

    release_block = _workflow_job_block("release-gate")
    assert "dual-live-windows-boundary" in _workflow_job_needs("release-gate")
    assert "needs['dual-live-windows-boundary'].result" in release_block
