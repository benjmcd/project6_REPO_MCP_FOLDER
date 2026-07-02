from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "rc3_sec_xbrl_offline_acceptance.py"
SUPPORT_MATRIX_PATH = REPO_ROOT / "config" / "support_matrix.yaml"
RELEASE_READINESS_PATH = REPO_ROOT / "config" / "release_readiness.yaml"


def _load_runner():
    spec = importlib.util.spec_from_file_location("rc3_sec_xbrl_offline_acceptance", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_rc3_support_matrix_declares_offline_simulation_honesty_ceiling() -> None:
    runner = _load_runner()
    matrix = _load_json(SUPPORT_MATRIX_PATH)
    by_id = {item["id"]: item for item in matrix["capabilities"]}

    assert matrix["profile"] == "local_expert"
    assert matrix["overlays"] == ["public_connectors", "sec_xbrl_offline"]
    assert matrix["pinned_false_flags"] == runner.PINNED_FALSE_FLAGS
    for token in runner.BOUNDARY_TOKENS:
        assert token in matrix["boundary_note"]

    for capability_id in runner.UNSUPPORTED_CAPABILITIES:
        assert by_id[capability_id]["status"] == "unsupported"
    for capability_id in runner.EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES:
        assert by_id[capability_id]["status"] == "experimental_default_off"
    for capability_id in runner.OFFLINE_SIMULATION_CAPABILITIES:
        assert by_id[capability_id]["status"] == "simulation"

    release_manifest = _load_json(RELEASE_READINESS_PATH)
    assert release_manifest["release"]["version"] == "0.3.0"
    assert release_manifest["release"]["milestone"] == "M-FINAL-030-SEC-XBRL-OFFLINE-ACCEPTANCE"
    assert release_manifest["owner_selected_profile_specific_gates"] == []


def test_rc3_acceptance_runner_reports_pass_with_injected_checks() -> None:
    runner = _load_runner()
    calls: list[tuple[str, ...]] = []

    def fake_command_runner(command: list[str], cwd: Path):
        calls.append(tuple(command))
        return runner.CommandResult(returncode=0, stdout="ok", stderr="")

    report = runner.run_rc3_acceptance(
        repo_root=REPO_ROOT,
        command_runner=fake_command_runner,
        build_info_provider=lambda _root: {
            "source": "/ready build_info",
            "ready_status_code": 200,
            "status": "ready",
            "version": "0.3.0",
            "source_sha": "a" * 40,
        },
    )

    assert report["schema_id"] == "project6.rc3_sec_xbrl_offline_acceptance.v1"
    assert report["verdict"] == "PASS"
    assert report["profile"] == {
        "base": "local_expert",
        "overlays": ["public_connectors", "sec_xbrl_offline"],
        "scope": "sec_xbrl offline/simulation only",
        "proof_level": "operator-workflow + local-deployment",
    }
    assert report["build_identity"]["version"] == "0.3.0"
    assert report["release_readiness_owner_selected_profile_specific_gates"] == []
    assert report["owner_signoff_required_before_merge"] is True

    criteria = {item["id"]: item for item in report["criteria"]}
    for criterion_id in [
        "build_identity_final_030",
        "build_identity_release_readiness_check",
        "support_matrix_rc3_offline_overlay_valid",
        "pr3_offline_loader_oracle_honesty",
        "pr4_offline_orchestrator_honesty",
        "companyfacts_stage_oracle_offline_honesty",
        "pr5_full_sec_xbrl_suite",
        "rc2_public_connector_acceptance_regression",
        "forbidden_surface_boundary",
    ]:
        assert criteria[criterion_id]["status"] == "pass"

    full_suite_command = criteria["pr5_full_sec_xbrl_suite"]["command"]
    full_suite_files = [
        part
        for part in full_suite_command
        if part.startswith("./backend/tests/test_sec_xbrl") and part.endswith(".py")
    ]
    tracked_sec_xbrl_files = [
        "./" + path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / "backend" / "tests").glob("test_sec_xbrl_*.py"))
    ]
    assert full_suite_files == tracked_sec_xbrl_files
    assert not any("*" in part for part in full_suite_command)

    connector_command = criteria["rc2_public_connector_acceptance_regression"]["command"]
    connector_tests = [
        part
        for part in connector_command
        if part.startswith("./tests/test_api.py::")
    ]
    assert len(connector_tests) == 24

    flat_calls = "\n".join(" ".join(command) for command in calls)
    for marker in [
        "release_readiness_check.py",
        "support_matrix_check.py",
        "test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py",
        "test_sec_xbrl_offline_evidence_loader.py",
        "test_sec_xbrl_offline_evidence_proof_capability.py",
        "test_sec_xbrl_e2e_offline_orchestrator.py",
        "test_sec_xbrl_value_reveal_operator_exercise_runner.py",
        "test_l17_sciencebase_download_negatives_are_bounded_and_observable",
        "test_connector_l20_sciencebase_active_lease_records_conflict",
        "test_sciencebase_csv_ingest_preserves_l11_source_fidelity",
        "test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis",
        "test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey",
    ]:
        assert marker in flat_calls


def test_rc3_acceptance_runner_fails_when_version_is_stale() -> None:
    runner = _load_runner()

    report = runner.run_rc3_acceptance(
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
            "version": "0.2.0-rc1",
            "source_sha": "b" * 40,
        },
    )

    assert report["verdict"] == "FAIL"
    assert any(
        item["id"] == "build_identity_final_030" and item["status"] == "fail"
        for item in report["criteria"]
    )


def test_rc3_acceptance_runner_fails_closed_when_full_suite_command_fails() -> None:
    runner = _load_runner()

    def fail_closed_command_runner(command: list[str], cwd: Path):
        if any("test_sec_xbrl_arelle_helper.py" in part for part in command):
            return runner.CommandResult(
                returncode=5,
                stdout="",
                stderr="no tests collected",
            )
        return runner.CommandResult(returncode=0, stdout="ok", stderr="")

    report = runner.run_rc3_acceptance(
        repo_root=REPO_ROOT,
        command_runner=fail_closed_command_runner,
        build_info_provider=lambda _root: {
            "source": "/ready build_info",
            "ready_status_code": 200,
            "status": "ready",
            "version": "0.3.0",
            "source_sha": "c" * 40,
        },
    )

    criteria = {item["id"]: item for item in report["criteria"]}
    assert report["verdict"] == "FAIL"
    assert criteria["pr5_full_sec_xbrl_suite"]["status"] == "fail"
    assert criteria["pr5_full_sec_xbrl_suite"]["returncode"] == 5
