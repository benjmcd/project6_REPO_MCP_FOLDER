from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = (
    ROOT
    / "diagnostics"
    / "assessment"
    / "sec-xbrl-value-reveal-authority-provisioning-preflight.py"
)


def _preflight_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_value_reveal_authority_provisioning_preflight", PREFLIGHT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_report(tmp_path: Path) -> Path:
    path = tmp_path / "run-report.json"
    path.write_text(
        json.dumps(
            {
                "decision": "value_reveal_operator_exercise_blocked_missing_authority",
                "ready_to_run_operator_exercise": False,
                "redacted_inventory": {"sidecar_receipt_count": 0, "bridge_receipt_count": 0},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_sec_xbrl_value_reveal_authority_provisioning_preflight_requires_grant_or_environment(
    tmp_path: Path,
) -> None:
    module = _preflight_module()

    report = module.build_report(source_root=ROOT, run_report_path=_run_report(tmp_path), env={})
    blockers = {item["blocked_reason"] for item in report["blocking_reasons"]}

    assert report["decision"] == "authority_provisioning_preflight_requires_explicit_grant_or_environment"
    assert "authority_provisioning_preflight_live_network_env_missing" in blockers
    assert "authority_provisioning_preflight_user_agent_env_missing" in blockers
    assert "authority_provisioning_preflight_arelle_environment_missing" in blockers
    assert report["operator_exercise_run_report_summary"]["decision"] == (
        "value_reveal_operator_exercise_blocked_missing_authority"
    )
    assert report["non_goals_preserved"]["sec_network_fetch_performed"] is False
    assert report["non_goals_preserved"]["arelle_subprocess_invoked"] is False
    assert report["non_goals_preserved"]["raw_values_committed"] is False
    assert report["next_slice"] == "sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1"


def test_sec_xbrl_value_reveal_authority_provisioning_preflight_rejects_nonexistent_arelle_paths(
    tmp_path: Path,
) -> None:
    module = _preflight_module()

    missing_python = tmp_path / "missing-python.exe"
    missing_taxonomy = tmp_path / "missing-taxonomy.zip"
    missing_cache = tmp_path / "missing-cache"
    report = module.build_report(
        source_root=ROOT,
        run_report_path=_run_report(tmp_path),
        env={
            "SEC_XBRL_ARELLE_PYTHON": str(missing_python),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(missing_taxonomy),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(missing_cache),
            "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED": "true",
            "LAYER3_SEC_EDGAR_USER_AGENT": "redacted operator test agent",
        },
    )
    blockers = {item["blocked_reason"] for item in report["blocking_reasons"]}

    arelle = report["arelle_environment_preflight"]
    assert report["decision"] == "authority_provisioning_preflight_requires_explicit_grant_or_environment"
    assert "authority_provisioning_preflight_live_network_env_missing" not in blockers
    assert "authority_provisioning_preflight_user_agent_env_missing" not in blockers
    assert "authority_provisioning_preflight_arelle_environment_missing" in blockers
    assert arelle["python_present"] is True
    assert arelle["python_exists"] is False
    assert arelle["taxonomy_packages_present"] is True
    assert arelle["taxonomy_package_existing_count"] == 0
    assert arelle["taxonomy_packages_all_exist"] is False
    assert arelle["cache_dir_present"] is True
    assert arelle["cache_dir_exists"] is False


def test_sec_xbrl_value_reveal_authority_provisioning_preflight_admits_existing_arelle_paths_after_grant(
    tmp_path: Path,
) -> None:
    module = _preflight_module()

    arelle_python = tmp_path / "python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    report = module.build_report(
        source_root=ROOT,
        run_report_path=_run_report(tmp_path),
        env={
            "SEC_XBRL_ARELLE_PYTHON": str(arelle_python),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(taxonomy_package),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(cache_dir),
            "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED": "true",
            "LAYER3_SEC_EDGAR_USER_AGENT": "redacted operator test agent",
        },
    )

    assert report["decision"] == "authority_provisioning_preflight_ready_for_explicit_granted_run"
    assert report["arelle_environment_preflight"]["python_exists"] is True
    assert report["arelle_environment_preflight"]["taxonomy_packages_all_exist"] is True
    assert report["arelle_environment_preflight"]["cache_dir_exists"] is True
    assert report["required_next_action"] == "run_authority_provisioning_with_explicit_operator_grant"
