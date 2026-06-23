from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMOKE_PATH = ROOT / "diagnostics" / "assessment" / "sec-live-smoke.py"
EVIDENCE_PATH = ROOT / "diagnostics" / "assessment" / "sec-live-smoke-evidence.py"
PROJECT_WRAPPER_PATH = ROOT / "project6.ps1"


class _FakeSecClient:
    def __init__(self, module, content: bytes) -> None:
        self.module = module
        self.content = bytes(content)
        self.calls: list[dict[str, object]] = []

    def fetch_complete_submission_text(
        self,
        *,
        url: str,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
    ):
        self.calls.append(
            {
                "url_seen": bool(url),
                "user_agent_seen": bool(user_agent),
                "timeout_seconds": timeout_seconds,
                "max_bytes": max_bytes,
            }
        )
        return self.module._service_module().SecEdgarFetchResult(
            status_code=200,
            content=self.content,
            headers={},
            final_url=(
                "https://www.sec.gov/Archives/edgar/data/320193/"
                "000032019324000123/0000320193-24-000123.txt"
            ),
            complete=True,
        )


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _smoke_module():
    return _module(SMOKE_PATH, "sec_live_smoke")


def _evidence_module():
    return _module(EVIDENCE_PATH, "sec_live_smoke_evidence")


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


def _evidence_env(smoke_env: dict[str, str]) -> dict[str, str]:
    return {
        "STORAGE_EXPOSURE": "disabled",
        "STORAGE_DIR": smoke_env["STORAGE_DIR"],
    }


def _private_report_path(tmp_path: Path) -> Path:
    private_dir = tmp_path / "private"
    private_dir.mkdir()
    return private_dir / "smoke-report.json"


def _write_report(path: Path, report: dict) -> None:
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _live_shaped_report(report: dict) -> dict:
    copied = json.loads(json.dumps(report))
    copied["operator_evidence"]["transport_kind"] = "live_http"
    copied["execution_effects"]["real_sec_network_request_performed"] = True
    return copied


def _smoke_report(tmp_path: Path) -> tuple[dict, dict[str, str], object]:
    smoke = _smoke_module()
    env = _ready_env(tmp_path)
    fake_client = _FakeSecClient(
        smoke,
        (
            b"SEC-LIVE-SMOKE-RAW-CONTENT\n"
            b"CIK: 0000320193\n"
            b"ACCESSION: 0000320193-24-000123\n"
        ),
    )
    report = smoke.build_report(
        source_root=ROOT,
        env=env,
        execute_live=True,
        sec_client=fake_client,
        sleep=lambda _seconds: None,
    )
    assert report["decision"] == "sec_live_source_artifact_smoke_executed"
    assert len(fake_client.calls) == 1
    return report, env, fake_client


def _receipt_and_artifact_files(storage: Path) -> tuple[list[Path], list[Path]]:
    return sorted(storage.rglob("receipts/*.json")), sorted(storage.rglob("artifacts/*.txt"))


def test_sec_live_smoke_evidence_verifies_private_report_against_retained_storage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    evidence = _evidence_module()
    smoke_report, env, _fake_client = _smoke_report(tmp_path)
    smoke_report = _live_shaped_report(smoke_report)
    report_path = _private_report_path(tmp_path)
    _write_report(report_path, smoke_report)
    receipts_before, artifacts_before = _receipt_and_artifact_files(Path(env["STORAGE_DIR"]))
    svc = evidence._service_module()

    def _unexpected_acquire(_request):
        raise AssertionError("evidence verifier must not acquire source artifacts")

    monkeypatch.setattr(svc, "acquire_sec_edgar_text_table_live_source_artifact", _unexpected_acquire)

    report = evidence.build_report(
        source_root=ROOT,
        report_path=report_path,
        env=_evidence_env(env),
    )
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "sec_live_source_artifact_smoke_evidence_verified"
    assert all(item["state"] == "passed" for item in report["criteria"])
    assert report["transport"]["live_transport_proven"] is True
    assert report["execution_effects"]["validate_only"] is True
    assert report["execution_effects"]["sec_network_request_performed"] is False
    assert report["execution_effects"]["source_artifact_or_receipt_created"] is False
    assert report["execution_effects"]["retained_status_reread_performed"] is True
    assert report["retained_status"]["status_matches_report"] is True
    assert all(report["hash_shapes"].values())
    assert not any(report["redaction"].values())
    assert "0000320193-24-000123" not in serialized
    assert "0000320193" not in serialized
    assert "Project6 Operator contact@example.test" not in serialized
    assert str(tmp_path) not in serialized
    assert "https://www.sec.gov" not in serialized
    assert "SEC-LIVE-SMOKE-RAW-CONTENT" not in serialized
    assert _receipt_and_artifact_files(Path(env["STORAGE_DIR"])) == (receipts_before, artifacts_before)


def test_sec_live_smoke_evidence_blocks_fake_transport_report_by_default(tmp_path: Path) -> None:
    evidence = _evidence_module()
    smoke_report, env, _fake_client = _smoke_report(tmp_path)
    report_path = _private_report_path(tmp_path)
    _write_report(report_path, smoke_report)

    report = evidence.build_report(
        source_root=ROOT,
        report_path=report_path,
        env=_evidence_env(env),
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_evidence_blocked"
    assert report["transport"]["transport_kind"] == "fake_client"
    assert report["transport"]["live_transport_proven"] is False
    assert any(
        item["blocked_reason"] == "sec_live_smoke_evidence_live_transport_not_proven"
        for item in report["blocking_reasons"]
    )


def test_sec_live_smoke_evidence_blocks_missing_private_report(tmp_path: Path) -> None:
    evidence = _evidence_module()
    env = _ready_env(tmp_path)

    report = evidence.build_report(
        source_root=ROOT,
        report_path=tmp_path / "missing" / "smoke-report.json",
        env=_evidence_env(env),
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_evidence_blocked"
    assert any(
        item["blocked_reason"] == "sec_live_smoke_evidence_report_missing_invalid_or_not_private"
        for item in report["blocking_reasons"]
    )
    assert report["execution_effects"]["sec_network_request_performed"] is False
    assert report["execution_effects"]["source_artifact_or_receipt_created"] is False


def test_sec_live_smoke_evidence_blocks_wrong_retained_storage(tmp_path: Path) -> None:
    evidence = _evidence_module()
    smoke_report, _env, _fake_client = _smoke_report(tmp_path)
    smoke_report = _live_shaped_report(smoke_report)
    report_path = _private_report_path(tmp_path)
    _write_report(report_path, smoke_report)
    wrong_storage = tmp_path / "wrong-storage"
    wrong_storage.mkdir()

    report = evidence.build_report(
        source_root=ROOT,
        report_path=report_path,
        env={"STORAGE_EXPOSURE": "disabled", "STORAGE_DIR": str(wrong_storage)},
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_evidence_blocked"
    assert report["retained_status"]["status_matches_report"] is False
    assert report["retained_status"]["error_code"]
    assert any(
        item["blocked_reason"] == "sec_live_smoke_evidence_retained_status_mismatch"
        for item in report["blocking_reasons"]
    )


def test_sec_live_smoke_evidence_blocks_malformed_hash_shape(tmp_path: Path) -> None:
    evidence = _evidence_module()
    smoke_report, env, _fake_client = _smoke_report(tmp_path)
    smoke_report = _live_shaped_report(smoke_report)
    smoke_report["operator_evidence"]["content_sha256"] = "not-a-sha256"
    report_path = _private_report_path(tmp_path)
    _write_report(report_path, smoke_report)

    report = evidence.build_report(
        source_root=ROOT,
        report_path=report_path,
        env=_evidence_env(env),
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_evidence_blocked"
    assert report["hash_shapes"]["content_sha256"] is False
    assert any(
        item["blocked_reason"] == "sec_live_smoke_evidence_report_hash_shape_invalid"
        for item in report["blocking_reasons"]
    )


def test_sec_live_smoke_evidence_blocks_smoke_redaction_flag_leak(tmp_path: Path) -> None:
    evidence = _evidence_module()
    smoke_report, env, _fake_client = _smoke_report(tmp_path)
    smoke_report = _live_shaped_report(smoke_report)
    smoke_report["redaction"]["raw_sec_url_returned"] = True
    report_path = _private_report_path(tmp_path)
    _write_report(report_path, smoke_report)

    report = evidence.build_report(
        source_root=ROOT,
        report_path=report_path,
        env=_evidence_env(env),
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_evidence_blocked"
    assert report["redaction"]["smoke_report_redaction_flag_leak"] is True
    assert any(
        item["blocked_reason"] == "sec_live_smoke_evidence_raw_authority_leak"
        for item in report["blocking_reasons"]
    )


def test_sec_live_smoke_evidence_blocks_raw_cik_like_value_under_unexpected_key(
    tmp_path: Path,
) -> None:
    evidence = _evidence_module()
    smoke_report, env, _fake_client = _smoke_report(tmp_path)
    smoke_report = _live_shaped_report(smoke_report)
    smoke_report["operator_evidence"]["unexpected_raw_identity"] = "CIK 0000320193"
    report_path = _private_report_path(tmp_path)
    _write_report(report_path, smoke_report)

    report = evidence.build_report(
        source_root=ROOT,
        report_path=report_path,
        env=_evidence_env(env),
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_evidence_blocked"
    assert report["redaction"]["raw_cik_like_returned"] is True
    assert any(
        item["blocked_reason"] == "sec_live_smoke_evidence_raw_authority_leak"
        for item in report["blocking_reasons"]
    )


def test_sec_live_smoke_evidence_cli_no_report_skips_output_write(
    tmp_path: Path,
    monkeypatch,
) -> None:
    evidence = _evidence_module()
    smoke_report, env, _fake_client = _smoke_report(tmp_path)
    smoke_report = _live_shaped_report(smoke_report)
    report_path = _private_report_path(tmp_path)
    _write_report(report_path, smoke_report)
    output = tmp_path / "evidence-output.json"
    for key, value in _evidence_env(env).items():
        monkeypatch.setenv(key, value)

    assert evidence.main(["--report", str(report_path), "--output", str(output), "--no-report"]) == 0

    assert not output.exists()


def test_sec_live_smoke_evidence_project_wrapper_uses_artifact_free_action() -> None:
    wrapper = PROJECT_WRAPPER_PATH.read_text(encoding="utf-8")

    assert '"validate-sec-live-smoke-evidence"' in wrapper
    assert (
        '$SecLiveSmokeEvidencePath = Join-Path $RepoRoot '
        '"diagnostics\\assessment\\sec-live-smoke-evidence.py"'
    ) in wrapper
    assert '@($SecLiveSmokeEvidencePath, "--no-report") + $ActionArgs' in wrapper
    assert '& py "-$PythonVersion" @smokeEvidenceArgs' in wrapper
    assert "exit $LASTEXITCODE" in wrapper
