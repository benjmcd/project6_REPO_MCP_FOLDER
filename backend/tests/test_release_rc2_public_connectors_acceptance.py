from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "rc2-public-connectors-acceptance.md"
RUNNER_PATH = REPO_ROOT / "scripts" / "rc2_public_connectors_acceptance.py"
SUPPORT_MATRIX_PATH = REPO_ROOT / "config" / "support_matrix.yaml"
RELEASE_READINESS_PATH = REPO_ROOT / "config" / "release_readiness.yaml"
VERSION_PATH = REPO_ROOT / "backend" / "app" / "_version.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("rc2_public_connectors_acceptance", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_rc2_public_connectors_doc_records_honest_acceptance_ceiling() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    required_phrases = [
        "base=local_expert",
        "overlays=[\"public_connectors\"]",
        "operator-workflow + local-deployment",
        "public/anonymous connectors only",
        "ScienceBase public/MCS",
        "Senate LDA anonymous",
        "No SEC",
        "No OCR",
        "No model/agent egress",
        "No nonlocal deployment",
        "No keyed connector",
        "No high availability",
        "No real provider delivery",
        "PR-1",
        "PR-2",
        "PR-3",
        "PR-4",
        "PR-5",
        "RC2 verdict: PASS",
        "OWNER sign-off required before merge",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_rc2_support_matrix_selects_public_connectors_overlay_only() -> None:
    matrix = _load_json(SUPPORT_MATRIX_PATH)
    by_id = {item["id"]: item for item in matrix["capabilities"]}

    assert matrix["profile"] == "local_expert"
    assert matrix["overlays"] == ["public_connectors"]
    assert "public_connectors overlay" in matrix["boundary_note"]
    assert "operator-workflow + local-deployment" in matrix["boundary_note"]
    assert "No SEC" in matrix["boundary_note"]

    for connector_id in (
        "sciencebase_public_connector_slice",
        "senate_lda_anonymous_connector_slice",
        "connector_run_observability",
    ):
        assert by_id[connector_id]["status"] == "supported"
        evidence = by_id[connector_id]["evidence"]
        for marker in ("PR-1", "PR-2", "PR-3", "PR-4", "PR-5"):
            assert marker in evidence

    for excluded_id in (
        "sec_live_network_egress",
        "real_provider_delivery",
        "model_agent_egress",
        "nonlocal_multi_trust_multi_identity",
        "high_availability",
        "keyed_connectors",
        "signed_reference_export",
    ):
        assert by_id[excluded_id]["status"] == "unsupported"


def test_rc2_version_bump_keeps_release_owner_gates_empty() -> None:
    version_text = VERSION_PATH.read_text(encoding="utf-8")
    release_manifest = _load_json(RELEASE_READINESS_PATH)

    assert 'VERSION = "0.2.0-rc1"' in version_text
    assert release_manifest["release"]["version"] == "0.2.0-rc1"
    assert release_manifest["owner_selected_profile_specific_gates"] == []
    assert "profile-neutral" in release_manifest["release"]["scope"]


def test_rc2_acceptance_runner_reports_public_connector_pass_with_injected_checks(monkeypatch) -> None:
    runner = _load_runner()
    calls: list[tuple[str, ...]] = []
    monkeypatch.setenv("PROJECT6_CI_BACKEND_LAYER3_API_RESULT", "success")

    def fake_command_runner(command: list[str], cwd: Path):
        calls.append(tuple(command))
        return runner.CommandResult(returncode=0, stdout="ok", stderr="")

    report = runner.run_rc2_acceptance(
        repo_root=REPO_ROOT,
        command_runner=fake_command_runner,
        build_info_provider=lambda _root: {
            "source": "/ready build_info",
            "ready_status_code": 200,
            "status": "ready",
            "version": "0.2.0-rc1",
            "source_sha": "a" * 40,
        },
    )

    assert report["schema_id"] == "project6.rc2_public_connectors_acceptance.v1"
    assert report["verdict"] == "PASS"
    assert report["profile"] == {
        "base": "local_expert",
        "overlays": ["public_connectors"],
        "scope": "public/anonymous connectors only",
        "proof_level": "operator-workflow + local-deployment",
    }
    assert report["build_identity"]["version"] == "0.2.0-rc1"
    assert report["release_readiness_owner_selected_profile_specific_gates"] == []
    assert report["owner_signoff_required_before_merge"] is True

    criteria = {item["id"]: item for item in report["criteria"]}
    for criterion_id in [
        "support_matrix_public_connectors_overlay_valid",
        "pr1_correctness_regressions",
        "pr2_l17_negative_cases",
        "pr3_l20_lifecycle_postures",
        "pr4_l11_source_fidelity",
        "pr5_canonical_connector_journey",
        "forbidden_surface_boundary",
    ]:
        assert criteria[criterion_id]["status"] == "pass"

    flat_calls = "\n".join(" ".join(command) for command in calls)
    for test_name in [
        "test_sciencebase_download_429_retryable_sets_backoff",
        "test_l17_sciencebase_download_negatives_are_bounded_and_observable",
        "test_connector_l20_sciencebase_active_lease_records_conflict",
        "test_sciencebase_csv_ingest_preserves_l11_source_fidelity",
        "test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis",
        "test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey",
    ]:
        assert test_name in flat_calls


def test_rc2_acceptance_runner_fails_when_version_is_stale() -> None:
    runner = _load_runner()

    report = runner.run_rc2_acceptance(
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
            "source_sha": "b" * 40,
        },
    )

    assert report["verdict"] == "FAIL"
    assert any(
        item["id"] == "version_bumped_to_rc2" and item["status"] == "fail"
        for item in report["criteria"]
    )
