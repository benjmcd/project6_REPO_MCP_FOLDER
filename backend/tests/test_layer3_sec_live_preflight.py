from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = ROOT / "diagnostics" / "assessment" / "sec-live-preflight.py"


def _preflight_module():
    spec = importlib.util.spec_from_file_location("sec_live_preflight", PREFLIGHT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ready_env(tmp_path: Path) -> dict[str, str]:
    storage = tmp_path / "storage"
    storage.mkdir()
    return {
        "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED": "true",
        "LAYER3_SEC_EDGAR_USER_AGENT": "Project6 Operator contact@example.test",
        "STORAGE_EXPOSURE": "disabled",
        "STORAGE_DIR": str(storage),
        "DATABASE_URL": "sqlite:///:memory:",
        "LAYER3_SEC_EDGAR_SMOKE_CIK": "0000320193",
        "LAYER3_SEC_EDGAR_SMOKE_ACCESSION": "0000320193-24-000123",
        "LAYER3_SEC_EDGAR_SMOKE_FORM_TYPE": "10-K",
        "LAYER3_SEC_EDGAR_SMOKE_FILING_DATE": "2024-11-01",
        "LAYER3_SEC_EDGAR_SMOKE_OPERATOR_CONFIRMATION": "true",
    }


def test_sec_live_preflight_blocks_without_operator_environment() -> None:
    module = _preflight_module()

    report = module.build_report(source_root=ROOT, env={})
    blockers = {item["blocked_reason"] for item in report["blocking_reasons"]}

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert "sec_live_preflight_live_network_not_explicitly_enabled" in blockers
    assert "sec_live_preflight_user_agent_missing" in blockers
    assert "sec_live_preflight_storage_missing_or_unsafe" in blockers
    assert "sec_live_preflight_database_missing_or_unsafe" in blockers
    assert "sec_live_preflight_smoke_request_missing_or_invalid" in blockers
    assert report["non_goals_preserved"]["sec_network_fetch_performed"] is False
    assert report["non_goals_preserved"]["source_artifact_created"] is False
    assert report["non_goals_preserved"]["arelle_subprocess_invoked"] is False
    assert report["next_slice"] == "execute_operator_configured_manual_live_sec_source_artifact_smoke"


def test_sec_live_preflight_ready_with_redacted_isolated_environment(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)

    report = module.build_report(source_root=ROOT, env=env)
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_ready"
    assert report["blocking_reasons"] == []
    assert report["runtime_preflight"]["storage"]["storage_dir_inside_repo_or_onedrive"] is False
    assert report["runtime_preflight"]["database"]["sqlite_memory"] is True
    assert report["smoke_request_preflight"]["request_ready"] is True
    assert report["smoke_request_preflight"]["source_identity_marker"]
    assert env["LAYER3_SEC_EDGAR_USER_AGENT"] not in serialized
    assert env["STORAGE_DIR"] not in serialized
    assert env["LAYER3_SEC_EDGAR_SMOKE_CIK"] not in serialized
    assert env["LAYER3_SEC_EDGAR_SMOKE_ACCESSION"] not in serialized
    assert report["runtime_preflight"]["user_agent"]["raw_value_returned"] is False
    assert report["runtime_preflight"]["storage"]["raw_path_returned"] is False
    assert report["smoke_request_preflight"]["raw_identity_returned"] is False


def test_sec_live_preflight_blocks_repo_storage_and_exposed_storage_mount(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["STORAGE_DIR"] = str(ROOT)
    env["STORAGE_EXPOSURE"] = "auto"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["storage"]["storage_dir_inside_repo_or_onedrive"] is True
    assert report["runtime_preflight"]["storage"]["storage_exposure_disabled"] is False
    assert any(
        item["blocked_reason"] == "sec_live_preflight_storage_missing_or_unsafe"
        for item in report["blocking_reasons"]
    )


def test_sec_live_preflight_blocks_repo_sqlite_database(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["DATABASE_URL"] = "sqlite:///" + (ROOT / "backend" / "method_aware.db").as_posix()

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["database"]["sqlite_path_inside_repo_or_onedrive"] is True
    assert any(
        item["blocked_reason"] == "sec_live_preflight_database_missing_or_unsafe"
        for item in report["blocking_reasons"]
    )


def test_sec_live_preflight_blocks_invalid_smoke_request_identity(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["LAYER3_SEC_EDGAR_SMOKE_ACCESSION"] = "not-an-accession"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["smoke_request_preflight"]["accession_shape_valid"] is False
    assert any(
        item["blocked_reason"] == "sec_live_preflight_smoke_request_missing_or_invalid"
        for item in report["blocking_reasons"]
    )
    assert "not-an-accession" not in json.dumps(report, sort_keys=True)


def test_sec_live_preflight_blocks_ci_runtime(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["CI"] = "true"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["ci"]["ci_active"] is True
    assert any(
        item["blocked_reason"] == "sec_live_preflight_ci_runtime_active"
        for item in report["blocking_reasons"]
    )


def test_sec_live_preflight_blocks_invalid_rate_controls(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["LAYER3_SEC_EDGAR_RATE_LIMIT_PER_SECOND"] = "11"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["limits"]["rate_limit_admitted"] is False
    assert any(
        item["blocked_reason"] == "sec_live_preflight_rate_or_size_controls_invalid"
        for item in report["blocking_reasons"]
    )
