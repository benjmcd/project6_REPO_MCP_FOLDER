from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "rc1-local-expert-acceptance.md"
RUNNER_PATH = REPO_ROOT / "scripts" / "rc1_local_expert_acceptance.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "playwright.yml"
RELEASE_READINESS_PATH = REPO_ROOT / "config" / "release_readiness.yaml"
VERSION_PATH = REPO_ROOT / "backend" / "app" / "_version.py"
SMOKE_PATH = REPO_ROOT / "deploy" / "smoke.ps1"


def _load_runner():
    spec = importlib.util.spec_from_file_location("rc1_local_expert_acceptance", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rc1_acceptance_doc_records_profile_boundaries_and_proofs() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    required_phrases = [
        "base=local_expert",
        "overlays=none",
        "analytics-only",
        "operator-workflow + local-deployment",
        "not live-external",
        "not overlay",
        "not nonlocal",
        "connectors excluded",
        "SEC excluded",
        "agent/model egress excluded",
        "scripts/support_matrix_check.py",
        "tests/test_api.py::test_canonical_local_expert_journey_recovers_state_with_fresh_client",
        "unsupported_method",
        "content_hash",
        "source_row_count",
        "dropped_row_count",
        "backend/alembic/versions/0055_dataset_version_source_fidelity.py",
        "scripts/local_profile_acceptance.py",
        "backend/tests/test_release_local_profile_operational_acceptance.py",
        "scripts/build_app_image.py",
        "/ready BUILD_INFO.source_sha",
        "scripts/release_readiness_check.py",
        "backend/tests/test_deployment_profile_validation.py",
        "UPGRADE: not_claimed",
        "RC1 verdict: PASS",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_rc1_acceptance_runner_reports_profile_bounded_pass_with_injected_checks(monkeypatch) -> None:
    runner = _load_runner()
    calls: list[tuple[str, ...]] = []
    monkeypatch.setenv("PROJECT6_CI_BACKEND_LAYER3_API_RESULT", "success")

    def fake_command_runner(command: list[str], cwd: Path):
        calls.append(tuple(command))
        return runner.CommandResult(returncode=0, stdout="ok", stderr="")

    report = runner.run_rc1_acceptance(
        repo_root=REPO_ROOT,
        command_runner=fake_command_runner,
        build_info_provider=lambda _root: {
            "source": "/ready build_info",
            "ready_status_code": 200,
            "status": "ready",
            "version": "0.1.0-rc1",
            "source_sha": "a" * 40,
        },
    )

    assert report["schema_id"] == "project6.rc1_local_expert_acceptance.v1"
    assert report["verdict"] == "PASS"
    assert report["profile"] == {
        "base": "local_expert",
        "overlays": "none",
        "scope": "analytics-only",
        "proof_level": "operator-workflow + local-deployment",
    }
    assert report["build_identity"]["version"] == "0.1.0-rc1"
    assert report["build_identity"]["source_sha"] == "a" * 40
    assert report["release_readiness_owner_selected_profile_specific_gates"] == []
    assert report["upgrade"] == "not_claimed"
    assert "connectors" in report["excluded_surfaces"]
    assert "SEC" in report["excluded_surfaces"]
    assert "nonlocal" in report["excluded_surfaces"]

    criteria = {item["id"]: item for item in report["criteria"]}
    for criterion_id in [
        "support_matrix_valid",
        "canonical_analytics_journey",
        "csv_source_fidelity_recorded",
        "local_profile_operational_acceptance",
        "artifact_baked_build_identity",
        "profile_neutral_release_gates",
        "defaults_fail_closed",
    ]:
        assert criteria[criterion_id]["status"] == "pass"
    assert criteria["upgrade_subcontract"]["status"] == "not_claimed"
    assert criteria["local_profile_operational_acceptance"]["execution"] == "referenced_not_rerun"
    assert criteria["local_profile_operational_acceptance"]["ci_dependency"] == "backend-layer3-api"
    assert criteria["local_profile_operational_acceptance"]["ci_dependency_result"] == "success"

    assert ("python", "./scripts/support_matrix_check.py") in calls
    assert ("python", "./scripts/release_readiness_check.py") in calls
    flat_calls = "\n".join(" ".join(command) for command in calls)
    assert "test_canonical_local_expert_journey_recovers_state_with_fresh_client" in flat_calls
    assert "test_upload_counts_blank_csv_lines_as_dropped_source_rows" in flat_calls
    assert "test_release_local_profile_operational_acceptance.py" in flat_calls
    assert "--collect-only" in flat_calls
    assert "test_deployment_profile_validation.py" in flat_calls
    assert "test_app_image_build_script_passes_current_git_source_sha" in flat_calls
    assert "local_profile_acceptance.py" not in flat_calls


def test_rc1_acceptance_runner_cli_emits_json_with_injected_empty_runtime_fail_closed() -> None:
    runner = _load_runner()

    def fail_closed_command_runner(command: list[str], cwd: Path):
        if any(
            "test_canonical_local_expert_journey_recovers_state_with_fresh_client" in part
            for part in command
        ):
            return runner.CommandResult(returncode=5, stdout="", stderr="no tests collected")
        return runner.CommandResult(returncode=0, stdout="ok", stderr="")

    report = runner.run_rc1_acceptance(
        repo_root=REPO_ROOT,
        command_runner=fail_closed_command_runner,
        build_info_provider=lambda _root: {
            "source": "/ready build_info",
            "ready_status_code": 200,
            "status": "ready",
            "version": "0.1.0-rc1",
            "source_sha": "b" * 40,
        },
    )

    assert report["verdict"] == "FAIL"
    assert any(
        item["id"] == "canonical_analytics_journey" and item["status"] == "fail"
        for item in report["criteria"]
    )
    json.dumps(report)


def test_rc1_acceptance_runner_fails_when_ci_dependency_failed(monkeypatch) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PROJECT6_CI_BACKEND_LAYER3_API_RESULT", "failure")

    report = runner.run_rc1_acceptance(
        repo_root=REPO_ROOT,
        command_runner=lambda _command, _cwd: runner.CommandResult(
            returncode=0,
            stdout="ok",
            stderr="",
        ),
        build_info_provider=lambda _root: {
            "source": "/ready build_info",
            "ready_status_code": 200,
            "status": "ready",
            "version": "0.1.0-rc1",
            "source_sha": "c" * 40,
        },
    )

    criteria = {item["id"]: item for item in report["criteria"]}
    assert report["verdict"] == "FAIL"
    assert criteria["local_profile_operational_acceptance"]["status"] == "fail"
    assert criteria["local_profile_operational_acceptance"]["ci_dependency_status"] == "fail"


def test_rc1_historical_acceptance_remains_profile_neutral_after_current_bump() -> None:
    version_text = VERSION_PATH.read_text(encoding="utf-8")
    release_manifest = json.loads(RELEASE_READINESS_PATH.read_text(encoding="utf-8"))
    smoke_text = SMOKE_PATH.read_text(encoding="utf-8")
    old_version = "0.1.0-rc1-" + "foundation"

    assert 'VERSION = "0.3.0-rc1"' in version_text
    assert old_version not in version_text
    assert release_manifest["release"]["version"] == "0.3.0-rc1"
    assert release_manifest["owner_selected_profile_specific_gates"] == []
    assert "owner-selected profile-specific gates intentionally empty" in release_manifest[
        "profile_boundary_note"
    ]
    assert old_version not in smoke_text
    assert '"0.3.0-rc1"' in smoke_text


def test_rc1_acceptance_runner_is_preserved_but_not_current_release_gate_ci_hook() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Run RC3 SEC XBRL offline acceptance capstone" in workflow_text
    assert "PROJECT6_CI_BACKEND_LAYER3_API_RESULT: ${{ needs['backend-layer3-api'].result }}" in workflow_text
    assert "python ./scripts/rc3_sec_xbrl_offline_acceptance.py --json" in workflow_text
    assert "python ./scripts/rc1_local_expert_acceptance.py --json" not in workflow_text
    assert "python ./scripts/rc2_public_connectors_acceptance.py --json" not in workflow_text

    coverage_text = (REPO_ROOT / "backend" / "tests" / "test_ci_coverage_completeness.py").read_text(
        encoding="utf-8"
    )
    assert "rc3_sec_xbrl_offline_acceptance.py" in coverage_text
