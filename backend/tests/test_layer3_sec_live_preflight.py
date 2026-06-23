from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = ROOT / "diagnostics" / "assessment" / "sec-live-preflight.py"
PROJECT_WRAPPER_PATH = ROOT / "project6.ps1"


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
        "LAYER3_SEC_EDGAR_RATE_LIMIT_PER_SECOND": "1",
        "LAYER3_SEC_EDGAR_MAX_LIVE_REQUESTS_PER_PROCESS": "10",
        "LAYER3_SEC_EDGAR_MAX_BYTES": "25000000",
        "LAYER3_SEC_EDGAR_TIMEOUT_SECONDS": "20",
        "LAYER3_SEC_EDGAR_SMOKE_CIK": "0000320193",
        "LAYER3_SEC_EDGAR_SMOKE_ACCESSION": "0000320193-24-000123",
        "LAYER3_SEC_EDGAR_SMOKE_FORM_TYPE": "10-K",
        "LAYER3_SEC_EDGAR_SMOKE_FILING_DATE": "2024-11-01",
        "LAYER3_SEC_EDGAR_SMOKE_OPERATOR_CONFIRMATION": "true",
    }


def _clear_operator_env(module, monkeypatch) -> None:
    for key in [
        module.LIVE_ENABLED_ENV,
        module.USER_AGENT_ENV,
        module.RATE_ENV,
        module.MAX_REQUESTS_ENV,
        module.MAX_BYTES_ENV,
        module.TIMEOUT_ENV,
        module.STORAGE_ENV,
        module.STORAGE_EXPOSURE_ENV,
        module.DATABASE_ENV,
        module.CI_ENV,
        module.SMOKE_CIK_ENV,
        module.SMOKE_ACCESSION_ENV,
        module.SMOKE_FORM_ENV,
        module.SMOKE_DATE_ENV,
        module.SMOKE_CONFIRM_ENV,
    ]:
        monkeypatch.delenv(key, raising=False)


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
    assert report["runtime_preflight"]["storage"]["storage_dir_writable_non_mutating_check"] is True
    assert report["runtime_preflight"]["database"]["sqlite_memory"] is True
    assert report["runtime_preflight"]["limits"]["rate_limit_present"] is True
    assert report["runtime_preflight"]["limits"]["max_live_requests_present"] is True
    assert report["runtime_preflight"]["limits"]["max_bytes_present"] is True
    assert report["runtime_preflight"]["limits"]["timeout_seconds_present"] is True
    assert report["runtime_preflight"]["limits"]["max_bytes_admitted"] is True
    assert report["runtime_preflight"]["limits"]["timeout_seconds_admitted"] is True
    assert report["smoke_request_preflight"]["request_ready"] is True
    assert report["smoke_request_preflight"]["matching_existing_receipt_found"] is False
    assert report["smoke_request_preflight"]["source_identity_marker"]
    assert env["LAYER3_SEC_EDGAR_USER_AGENT"] not in serialized
    assert env["STORAGE_DIR"] not in serialized
    assert env["LAYER3_SEC_EDGAR_SMOKE_CIK"] not in serialized
    assert env["LAYER3_SEC_EDGAR_SMOKE_ACCESSION"] not in serialized
    assert report["runtime_preflight"]["user_agent"]["raw_value_returned"] is False
    assert report["runtime_preflight"]["storage"]["raw_path_returned"] is False
    assert report["smoke_request_preflight"]["raw_identity_returned"] is False


def test_sec_live_preflight_normalizes_relative_storage_and_sqlite_under_backend() -> None:
    module = _preflight_module()

    assert module._normalise_storage_dir(ROOT, "relative-storage") == (
        ROOT / "backend" / "relative-storage"
    ).resolve()
    assert module._sqlite_database_path("sqlite:///relative.db", source_root=ROOT) == (
        ROOT / "backend" / "relative.db"
    ).resolve()


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


def test_sec_live_preflight_blocks_unwritable_storage_check(tmp_path: Path, monkeypatch) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    monkeypatch.setattr(module.os, "access", lambda path, mode: False)

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["storage"]["storage_dir_writable_non_mutating_check"] is False
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


def test_sec_live_preflight_blocks_malformed_database_url(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["DATABASE_URL"] = "not-a-database-url"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["database"]["external_scheme_admitted"] is False
    assert report["runtime_preflight"]["database"]["external_url_valid"] is False
    assert report["runtime_preflight"]["database"]["database_safe_for_live_sec"] is False
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


def test_sec_live_preflight_blocks_invalid_calendar_date(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["LAYER3_SEC_EDGAR_SMOKE_FILING_DATE"] = "2024-99-99"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["smoke_request_preflight"]["filing_date_shape_valid"] is False
    assert report["smoke_request_preflight"]["request_ready"] is False
    assert any(
        item["blocked_reason"] == "sec_live_preflight_smoke_request_missing_or_invalid"
        for item in report["blocking_reasons"]
    )


def test_sec_live_preflight_blocks_matching_existing_receipt(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    source_identity_hash = module._source_identity_hash(
        cik="320193",
        accession=env["LAYER3_SEC_EDGAR_SMOKE_ACCESSION"],
        form=env["LAYER3_SEC_EDGAR_SMOKE_FORM_TYPE"],
        filing_date=env["LAYER3_SEC_EDGAR_SMOKE_FILING_DATE"],
    )
    receipt_dir = Path(env["STORAGE_DIR"]) / module.RECEIPT_DIR / "receipts"
    receipt_dir.mkdir(parents=True)
    receipt_path = receipt_dir / f"{module.RECEIPT_PREFIX}-{'a' * 24}-{'b' * 24}.json"
    receipt_path.write_text(json.dumps({"source_identity_hash": source_identity_hash}), encoding="utf-8")

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["smoke_request_preflight"]["matching_existing_receipt_found"] is True
    assert report["smoke_request_preflight"]["request_ready"] is False
    assert any(
        item["blocked_reason"] == "sec_live_preflight_smoke_request_missing_or_invalid"
        for item in report["blocking_reasons"]
    )


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
    env["LAYER3_SEC_EDGAR_MAX_LIVE_REQUESTS_PER_PROCESS"] = "0"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["limits"]["rate_limit_admitted"] is False
    assert report["runtime_preflight"]["limits"]["max_live_requests_admitted"] is False
    assert any(
        item["blocked_reason"] == "sec_live_preflight_rate_or_size_controls_invalid"
        for item in report["blocking_reasons"]
    )


def test_sec_live_preflight_cli_no_report_skips_report_write_and_fails_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _preflight_module()
    _clear_operator_env(module, monkeypatch)
    output = tmp_path / "preflight-report.json"

    assert module.main(["--output", str(output), "--no-report"]) == 1

    assert not output.exists()


def test_sec_live_preflight_cli_writes_report_when_not_suppressed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _preflight_module()
    _clear_operator_env(module, monkeypatch)
    output = tmp_path / "preflight-report.json"

    assert module.main(["--output", str(output)]) == 1

    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"


def test_sec_live_preflight_cli_ready_no_report_exits_zero_without_writing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _preflight_module()
    _clear_operator_env(module, monkeypatch)
    for key, value in _ready_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    output = tmp_path / "preflight-report.json"

    assert module.main(["--output", str(output), "--no-report"]) == 0

    assert not output.exists()


def test_sec_live_preflight_project_wrapper_uses_artifact_free_action() -> None:
    wrapper = PROJECT_WRAPPER_PATH.read_text(encoding="utf-8")

    assert '"validate-sec-live-preflight"' in wrapper
    assert '$SecLivePreflightPath = Join-Path $RepoRoot "diagnostics\\assessment\\sec-live-preflight.py"' in wrapper
    assert '@($SecLivePreflightPath, "--no-report") + $ActionArgs' in wrapper
    assert '& py "-$PythonVersion" @preflightArgs' in wrapper
    assert "exit $LASTEXITCODE" in wrapper


def test_sec_live_preflight_blocks_missing_explicit_rate_size_timeout_controls(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    for key in [
        "LAYER3_SEC_EDGAR_RATE_LIMIT_PER_SECOND",
        "LAYER3_SEC_EDGAR_MAX_LIVE_REQUESTS_PER_PROCESS",
        "LAYER3_SEC_EDGAR_MAX_BYTES",
        "LAYER3_SEC_EDGAR_TIMEOUT_SECONDS",
    ]:
        del env[key]

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["limits"]["rate_limit_present"] is False
    assert report["runtime_preflight"]["limits"]["max_live_requests_present"] is False
    assert report["runtime_preflight"]["limits"]["max_bytes_present"] is False
    assert report["runtime_preflight"]["limits"]["timeout_seconds_present"] is False
    assert all(
        report["runtime_preflight"]["limits"][key] is True
        for key in [
            "rate_limit_admitted",
            "max_live_requests_admitted",
            "max_bytes_admitted",
            "timeout_seconds_admitted",
        ]
    )
    assert any(
        item["blocked_reason"] == "sec_live_preflight_rate_or_size_controls_invalid"
        for item in report["blocking_reasons"]
    )


def test_sec_live_preflight_blocks_invalid_size_or_timeout_controls(tmp_path: Path) -> None:
    module = _preflight_module()
    env = _ready_env(tmp_path)
    env["LAYER3_SEC_EDGAR_MAX_BYTES"] = "25000001"
    env["LAYER3_SEC_EDGAR_TIMEOUT_SECONDS"] = "121"

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_preflight_blocked"
    assert report["runtime_preflight"]["limits"]["max_bytes_admitted"] is False
    assert report["runtime_preflight"]["limits"]["timeout_seconds_admitted"] is False
    assert any(
        item["blocked_reason"] == "sec_live_preflight_rate_or_size_controls_invalid"
        for item in report["blocking_reasons"]
    )
