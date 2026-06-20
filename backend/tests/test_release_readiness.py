from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "config" / "release_readiness.yaml"
RUNNER_PATH = REPO_ROOT / "scripts" / "release_readiness_check.py"
SMOKE_PATH = REPO_ROOT / "deploy" / "smoke.ps1"

EXPECTED_PROFILE_NEUTRAL_GATES = [
    "deployment_profile_fail_closed_validation",
    "ci_coverage_completeness",
    "backend_migrations_postgres_golden_path",
    "backend_coverage_floor",
    "release_lock_install",
]


def _load_runner():
    spec = importlib.util.spec_from_file_location("release_readiness_check", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_readiness_manifest_is_profile_neutral_and_maps_existing_gates():
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    runner = _load_runner()
    original_yaml = runner.yaml
    try:
        runner.yaml = None
        assert runner._load_yaml(MANIFEST_PATH) == manifest
    finally:
        runner.yaml = original_yaml

    assert manifest["schema_id"] == "project6.release_readiness.v1"
    assert manifest["release"]["milestone"] == "M-L02-RELEASE-ACCEPTANCE"
    assert manifest["release"]["version"] == "0.1.0-rc1-foundation"
    assert manifest["build_identity"]["source"] == "/ready build_info"
    assert manifest["owner_selected_profile_specific_gates"] == []
    assert "owner-selected profile-specific gates intentionally empty" in manifest[
        "profile_boundary_note"
    ]

    gate_ids = [gate["id"] for gate in manifest["required_gates"]]
    assert gate_ids == EXPECTED_PROFILE_NEUTRAL_GATES
    assert all(gate["profile_scope"] == "profile-neutral" for gate in manifest["required_gates"])

    workflow_text = (REPO_ROOT / ".github" / "workflows" / "playwright.yml").read_text(
        encoding="utf-8"
    )
    gate_text = json.dumps(manifest["required_gates"], sort_keys=True)

    assert (REPO_ROOT / "backend" / "tests" / "test_deployment_profile_validation.py").exists()
    assert (REPO_ROOT / "backend" / "tests" / "test_ci_coverage_completeness.py").exists()
    assert "backend-migrations-postgres" in workflow_text
    assert "tests/test_layer3_migrations.py" in workflow_text
    assert "tests/test_layer3_3c_golden_path.py" in workflow_text
    assert "--cov-fail-under=90" in workflow_text
    assert "release-lock-install" in workflow_text
    assert "pip install --require-hashes -r ./backend/requirements.lock.txt" in workflow_text
    assert "test_release_identity.py" in workflow_text
    assert "selected_profile" not in gate_text
    assert "LAYER3_DEPLOYMENT_PROFILE" not in gate_text


def test_release_readiness_runner_reports_pass_and_fail_paths(tmp_path):
    runner = _load_runner()
    source_sha = "64d2d0f90f78bd5ce38a4b43a137d0f8566556c9"

    def write_manifest(command_name: str) -> Path:
        manifest_path = tmp_path / f"{command_name}.yaml"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_id": "project6.release_readiness.v1",
                    "release": {
                        "milestone": "M-L02-RELEASE-ACCEPTANCE",
                        "version": "0.1.0-rc1-foundation",
                    },
                    "build_identity": {"source": "/ready build_info"},
                    "owner_selected_profile_specific_gates": [],
                    "required_gates": [
                        {
                            "id": "command_gate",
                            "kind": "command",
                            "profile_scope": "profile-neutral",
                            "command": [command_name],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return manifest_path

    def fake_command_runner(command, cwd):
        assert Path(cwd) == REPO_ROOT
        if command == ["fail-command"]:
            return runner.CommandResult(returncode=7, stdout="partial output", stderr="gate failed")
        return runner.CommandResult(returncode=0, stdout="gate ok", stderr="")

    build_info_provider = lambda repo_root: {
        "version": "0.1.0-rc1-foundation",
        "source_sha": source_sha,
        "source": "/ready build_info",
    }

    pass_report = runner.run_release_readiness(
        write_manifest("pass-command"),
        repo_root=REPO_ROOT,
        command_runner=fake_command_runner,
        build_info_provider=build_info_provider,
    )
    assert pass_report["status"] == "pass"
    assert pass_report["build_identity"]["version"] == "0.1.0-rc1-foundation"
    assert pass_report["build_identity"]["source_sha"] == source_sha
    assert pass_report["gates"][0]["status"] == "pass"

    fail_report = runner.run_release_readiness(
        write_manifest("fail-command"),
        repo_root=REPO_ROOT,
        command_runner=fake_command_runner,
        build_info_provider=build_info_provider,
    )
    assert fail_report["status"] == "fail"
    assert fail_report["gates"][0]["status"] == "fail"
    assert fail_report["gates"][0]["returncode"] == 7
    assert fail_report["gates"][0]["stderr_tail"] == "gate failed"


def test_deploy_smoke_records_build_identity_and_extends_profile_neutral_probe():
    smoke_text = SMOKE_PATH.read_text(encoding="utf-8")

    required_markers = [
        "PROJECT6_SOURCE_SHA",
        "$ReadyBuildInfo",
        "release-identity",
        "/api/v1/layer3/gate-c/preview",
        "/api/v1/layer3/plan/preview",
        "/api/v1/layer3/plan/approve",
        "/api/v1/layer3/execution/select",
        "/api/v1/layer3/execution/start",
        "/api/v1/layer3/execution/result/review",
        "/api/v1/layer3/analysis-product/",
        "/api/v1/layer3/package/review/preview",
    ]
    for marker in required_markers:
        assert marker in smoke_text

    assert "profile-boundary" in smoke_text
    assert "selected profile" in smoke_text
