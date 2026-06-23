from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMOKE_PATH = ROOT / "diagnostics" / "assessment" / "sec-live-smoke.py"


class _FakeSecClient:
    def __init__(self, module, content: bytes, statuses: tuple[int, ...] = (200,)) -> None:
        self.module = module
        self.content = bytes(content)
        self.statuses = statuses
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
        index = min(len(self.calls) - 1, len(self.statuses) - 1)
        status_code = self.statuses[index]
        return self.module._service_module().SecEdgarFetchResult(
            status_code=status_code,
            content=self.content,
            headers={"Retry-After": "0.2"} if status_code != 200 else {},
            final_url=(
                "https://www.sec.gov/Archives/edgar/data/320193/"
                "000032019324000123/0000320193-24-000123.txt"
            ),
            complete=True,
        )


def _smoke_module():
    spec = importlib.util.spec_from_file_location("sec_live_smoke", SMOKE_PATH)
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


def _receipt_and_artifact_files(storage: Path) -> tuple[list[Path], list[Path]]:
    return sorted(storage.rglob("receipts/*.json")), sorted(storage.rglob("artifacts/*.txt"))


def test_sec_live_smoke_default_dry_run_does_not_execute_or_write_artifacts(tmp_path: Path) -> None:
    module = _smoke_module()
    env = _ready_env(tmp_path)

    report = module.build_report(source_root=ROOT, env=env)

    assert report["decision"] == "sec_live_source_artifact_smoke_execution_not_requested"
    assert report["preflight"]["ready"] is True
    assert report["execution_plan"]["execute_live_default"] is False
    assert report["execution_plan"]["execute_live_flag_required"] == "--execute-live"
    assert report["execution_effects"]["network_request_made"] is False
    assert report["execution_effects"]["source_artifact_or_receipt_created"] is False
    receipts, artifacts = _receipt_and_artifact_files(Path(env["STORAGE_DIR"]))
    assert receipts == []
    assert artifacts == []


def test_sec_live_smoke_blocks_before_execution_when_preflight_not_ready(tmp_path: Path) -> None:
    module = _smoke_module()

    report = module.build_report(source_root=ROOT, env={}, execute_live=True)

    assert report["decision"] == "sec_live_source_artifact_smoke_blocked"
    assert any(
        item["blocked_reason"] == "sec_live_smoke_preflight_not_ready"
        for item in report["blocking_reasons"]
    )
    assert not list(tmp_path.rglob("*.json"))


def test_sec_live_smoke_execute_live_with_fake_transport_returns_redacted_hash_only_evidence(
    tmp_path: Path,
) -> None:
    module = _smoke_module()
    env = _ready_env(tmp_path)
    raw_content = (
        b"SEC-LIVE-SMOKE-RAW-CONTENT\n"
        b"CIK: 0000320193\n"
        b"ACCESSION: 0000320193-24-000123\n"
    )
    fake_client = _FakeSecClient(module, raw_content)

    report = module.build_report(
        source_root=ROOT,
        env=env,
        execute_live=True,
        sec_client=fake_client,
        sleep=lambda _seconds: None,
    )
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "sec_live_source_artifact_smoke_executed"
    assert all(item["state"] == "passed" for item in report["criteria"])
    assert report["execution_effects"]["network_request_made"] is True
    assert report["execution_effects"]["real_sec_network_request_performed"] is False
    assert report["execution_effects"]["source_artifact_or_receipt_created"] is True
    assert report["operator_evidence"]["transport_kind"] == "fake_client"
    assert report["operator_evidence"]["cache"]["cache_status"] == "miss"
    assert report["operator_evidence"]["cache"]["network_request_made"] is True
    assert report["operator_evidence"]["cache"]["transport_call_count"] == 1
    assert report["operator_evidence"]["status_returned"] is True
    assert report["operator_evidence"]["live_source_artifact_receipt_hash"]
    assert report["operator_evidence"]["source_artifact_receipt_hash"]
    assert report["operator_evidence"]["source_artifact_ref_hash"]
    assert fake_client.calls and len(fake_client.calls) == 1
    assert report["redaction"] == {
        "raw_cik_returned": False,
        "raw_accession_returned": False,
        "raw_user_agent_returned": False,
        "raw_storage_path_returned": False,
        "raw_sec_url_returned": False,
        "artifact_bytes_returned": False,
    }
    assert "0000320193-24-000123" not in serialized
    assert "0000320193" not in serialized
    assert "320193" not in serialized
    assert "Project6 Operator contact@example.test" not in serialized
    assert str(tmp_path) not in serialized
    assert "https://www.sec.gov" not in serialized
    assert "SEC-LIVE-SMOKE-RAW-CONTENT" not in serialized

    receipts, artifacts = _receipt_and_artifact_files(Path(env["STORAGE_DIR"]))
    assert len(receipts) == 1
    assert len(artifacts) == 1
    assert artifacts[0].read_bytes() == raw_content
    receipt_text = receipts[0].read_text(encoding="utf-8")
    assert "0000320193-24-000123" not in receipt_text
    assert "https://www.sec.gov" not in receipt_text
    assert str(tmp_path) not in receipt_text
    assert "SEC-LIVE-SMOKE-RAW-CONTENT" not in receipt_text


def test_sec_live_smoke_execute_live_blocks_multiple_fetch_attempts(tmp_path: Path) -> None:
    module = _smoke_module()
    env = _ready_env(tmp_path)
    env["LAYER3_SEC_EDGAR_RATE_LIMIT_PER_SECOND"] = "10"
    fake_client = _FakeSecClient(module, b"retry then success", statuses=(503, 200))

    report = module.build_report(
        source_root=ROOT,
        env=env,
        execute_live=True,
        sec_client=fake_client,
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_blocked"
    assert report["operator_evidence"]["cache"]["transport_call_count"] == 2
    assert any(
        item["blocked_reason"] == "sec_live_smoke_not_a_fresh_network_miss"
        for item in report["blocking_reasons"]
    )


def test_sec_live_smoke_preserves_created_artifact_evidence_after_status_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _smoke_module()
    svc = module._service_module()
    env = _ready_env(tmp_path)
    fake_client = _FakeSecClient(module, b"status failure after acquire")

    def _fail_status(_receipt_id: str):
        raise svc.Layer3WorkbenchError(
            error_code="forced_status_failure",
            message="forced status failure",
            http_status=409,
        )

    monkeypatch.setattr(svc, "inspect_sec_edgar_text_table_live_source_artifact_status", _fail_status)

    report = module.build_report(
        source_root=ROOT,
        env=env,
        execute_live=True,
        sec_client=fake_client,
        sleep=lambda _seconds: None,
    )

    assert report["decision"] == "sec_live_source_artifact_smoke_blocked"
    assert report["execution_effects"]["source_artifact_or_receipt_created"] is True
    assert report["execution_effects"]["status_reread_performed"] is False
    assert report["service_error"]["error_code"] == "forced_status_failure"


def test_sec_live_smoke_redaction_does_not_false_positive_short_cik() -> None:
    module = _smoke_module()
    preflight = module._preflight_module()
    env = {
        preflight.SMOKE_CIK_ENV: "1",
        preflight.SMOKE_ACCESSION_ENV: "0000000001-24-000001",
        preflight.USER_AGENT_ENV: "Project6 Operator contact@example.test",
        preflight.STORAGE_ENV: "C:/private/sec-smoke",
    }

    result = module._redaction_result(
        report_parts=[
            {
                "schema_id": "diagnostics.sec_live_source_artifact_operator_smoke.v1",
                "hash_like_value": "1" * 64,
            }
        ],
        preflight_module=preflight,
        env=env,
    )

    assert result["raw_cik_returned"] is False


def test_sec_live_smoke_execute_live_requires_explicit_private_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _smoke_module()
    for key, value in _ready_env(tmp_path).items():
        monkeypatch.setenv(key, value)

    assert module.main(["--execute-live"]) == 1
    assert module.main(["--execute-live", "--output", str(ROOT / "sec-live-smoke-report.json")]) == 1


def test_sec_live_smoke_cli_no_report_skips_report_write_and_fails_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _smoke_module()
    for key, value in _ready_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    output = tmp_path / "smoke-report.json"

    assert module.main(["--output", str(output), "--no-report"]) == 1

    assert not output.exists()
