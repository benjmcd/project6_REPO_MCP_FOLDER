from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_sec_edgar_live_source_artifact as svc
from app.services.layer3_workbench_error import Layer3WorkbenchError


class _FakeSecEdgarClient:
    def __init__(self, results: list[svc.SecEdgarFetchResult]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, object]] = []

    def fetch_complete_submission_text(
        self,
        *,
        url: str,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
    ) -> svc.SecEdgarFetchResult:
        self.calls.append(
            {
                "url": url,
                "user_agent": user_agent,
                "timeout_seconds": timeout_seconds,
                "max_bytes": max_bytes,
            }
        )
        assert self.results
        return self.results.pop(0)


class _RecordingOpener:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def open(self, request: object, *, timeout: int) -> object:
        self.calls.append({"request": request, "timeout": timeout})
        raise AssertionError("SEC opener should not be reached")


@pytest.fixture(autouse=True)
def _isolated_sec_live_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "Layer3 Test contact@example.com")
    monkeypatch.setattr(settings, "layer3_sec_edgar_rate_limit_per_second", 10)
    monkeypatch.setattr(settings, "layer3_sec_edgar_max_bytes", 25_000_000)
    monkeypatch.setattr(settings, "layer3_sec_edgar_timeout_seconds", 20)
    monkeypatch.delenv("CI", raising=False)
    svc._reset_live_request_count_for_tests()
    yield
    svc._reset_live_request_count_for_tests()


def _payload(client_request_id: str = "sec-live-source-artifact-test-001", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "client_request_id": client_request_id,
        "acquisition_mode": svc.ACQUISITION_MODE,
        "operator_decision": svc.OPERATOR_DECISION,
        "cik_or_filer_ref": "0000320193",
        "accession_or_submission_id": "0000320193-24-000123",
        "form_type": "10-K",
        "filing_date": "2024-11-01",
        "operator_confirmation": True,
    }
    payload.update(overrides)
    return payload


def _success_result(content: bytes = b"<SEC-DOCUMENT>safe fixture</SEC-DOCUMENT>\n") -> svc.SecEdgarFetchResult:
    return svc.SecEdgarFetchResult(
        status_code=200,
        content=content,
        final_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123.txt",
    )


def _assert_blocked(exc_info: pytest.ExceptionInfo[Layer3WorkbenchError], error_code: str) -> None:
    assert exc_info.value.status == "blocked"
    assert exc_info.value.error_code == error_code


def test_acquire_flag_off_fails_closed_before_transport(monkeypatch) -> None:
    fake_client = _FakeSecEdgarClient([_success_result()])
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", False)

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.acquire_sec_edgar_text_table_live_source_artifact(_payload())

    _assert_blocked(exc_info, "sec_edgar_text_table_live_source_artifact_live_network_disabled")
    assert fake_client.calls == []


def test_real_http_client_ci_runtime_blocks_before_opener(monkeypatch) -> None:
    opener = _RecordingOpener()
    monkeypatch.setattr(svc, "_SEC_OPENER", opener)
    monkeypatch.setenv("CI", "true")

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.SecEdgarHttpClient().fetch_complete_submission_text(
            url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123.txt",
            user_agent="Layer3 Test contact@example.com",
            timeout_seconds=1,
            max_bytes=128,
        )

    _assert_blocked(exc_info, "sec_edgar_text_table_live_source_artifact_ci_network_disabled")
    assert opener.calls == []


def test_acquire_missing_user_agent_fails_closed_before_transport(monkeypatch) -> None:
    fake_client = _FakeSecEdgarClient([_success_result()])
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "")

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.acquire_sec_edgar_text_table_live_source_artifact(_payload())

    _assert_blocked(exc_info, "sec_edgar_text_table_live_source_artifact_user_agent_missing")
    assert fake_client.calls == []


@pytest.mark.parametrize(
    ("overrides", "error_code"),
    [
        ({"cik_or_filer_ref": "not-a-cik"}, "sec_edgar_text_table_live_source_artifact_cik_not_admitted"),
        (
            {"accession_or_submission_id": "not-an-accession"},
            "sec_edgar_text_table_live_source_artifact_accession_not_admitted",
        ),
    ],
)
def test_acquire_malformed_source_identity_fails_closed_before_transport(
    monkeypatch,
    overrides: dict[str, object],
    error_code: str,
) -> None:
    fake_client = _FakeSecEdgarClient([_success_result()])
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.acquire_sec_edgar_text_table_live_source_artifact(_payload(**overrides))

    _assert_blocked(exc_info, error_code)
    assert fake_client.calls == []


def test_retry_after_is_honored_with_bounded_sleep(monkeypatch) -> None:
    fake_client = _FakeSecEdgarClient(
        [
            svc.SecEdgarFetchResult(status_code=429, headers={"Retry-After": "2"}),
            _success_result(),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(svc, "SEC_EDGAR_SLEEP", sleeps.append)
    monkeypatch.setattr(svc, "_enforce_rate_limit", lambda: None)

    result = svc._fetch_with_retry(
        url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123.txt",
        user_agent="Layer3 Test contact@example.com",
        timeout_seconds=20,
        max_bytes=256,
    )

    assert result.status_code == 200
    assert len(fake_client.calls) == 2
    assert sleeps == [1.0]


def test_acquire_partial_download_fails_closed_without_receipt(tmp_path, monkeypatch) -> None:
    fake_client = _FakeSecEdgarClient(
        [
            svc.SecEdgarFetchResult(
                status_code=200,
                content=b"x" * 11,
                complete=False,
                final_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123.txt",
            )
        ]
    )
    monkeypatch.setattr(settings, "layer3_sec_edgar_max_bytes", 10)
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(svc, "_enforce_rate_limit", lambda: None)

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.acquire_sec_edgar_text_table_live_source_artifact(_payload("sec-live-partial-001"))

    _assert_blocked(exc_info, "sec_edgar_text_table_live_source_artifact_partial_download_blocked")
    assert fake_client.calls[0]["max_bytes"] == 10
    receipt_root = tmp_path / "storage" / svc.RECEIPT_DIR
    assert list((receipt_root / "receipts").glob("*.json")) == []
    assert list((receipt_root / "artifacts").glob("*.txt")) == []


def test_acquire_timeout_result_retries_then_fails_closed(monkeypatch) -> None:
    fake_client = _FakeSecEdgarClient(
        [
            svc.SecEdgarFetchResult(status_code=408, complete=False),
            svc.SecEdgarFetchResult(status_code=408, complete=False),
            svc.SecEdgarFetchResult(status_code=408, complete=False),
        ]
    )
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(svc, "SEC_EDGAR_SLEEP", lambda _seconds: None)
    monkeypatch.setattr(svc, "_enforce_rate_limit", lambda: None)

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.acquire_sec_edgar_text_table_live_source_artifact(_payload("sec-live-timeout-001"))

    _assert_blocked(exc_info, "sec_edgar_text_table_live_source_artifact_fetch_failed")
    assert len(fake_client.calls) == 3


def test_acquire_rejects_max_bytes_above_source_artifact_ceiling_before_transport(monkeypatch) -> None:
    fake_client = _FakeSecEdgarClient([_success_result()])
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(settings, "layer3_sec_edgar_max_bytes", 200_000_001)
    monkeypatch.setattr(svc, "_enforce_rate_limit", lambda: None)

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.acquire_sec_edgar_text_table_live_source_artifact(_payload("sec-live-max-bytes-001"))

    _assert_blocked(exc_info, "sec_edgar_text_table_live_source_artifact_max_bytes_not_admitted")
    assert fake_client.calls == []


def test_acquire_rejects_timeout_above_source_artifact_ceiling_before_transport(monkeypatch) -> None:
    fake_client = _FakeSecEdgarClient([_success_result()])
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(settings, "layer3_sec_edgar_timeout_seconds", 121)
    monkeypatch.setattr(svc, "_enforce_rate_limit", lambda: None)

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        svc.acquire_sec_edgar_text_table_live_source_artifact(_payload("sec-live-timeout-cap-001"))

    _assert_blocked(exc_info, "sec_edgar_text_table_live_source_artifact_timeout_seconds_not_admitted")
    assert fake_client.calls == []


def test_acquire_success_returns_redacted_hash_only_operator_surface(tmp_path, monkeypatch) -> None:
    raw_user_agent = "Layer3 Test contact@example.com"
    content = b"<SEC-DOCUMENT>PRIVATE-LIVE-FILING-VALUE</SEC-DOCUMENT>\n"
    fake_client = _FakeSecEdgarClient([_success_result(content)])
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", raw_user_agent)
    monkeypatch.setattr(svc, "SEC_EDGAR_CLIENT", fake_client)
    monkeypatch.setattr(svc, "_enforce_rate_limit", lambda: None)

    response = svc.acquire_sec_edgar_text_table_live_source_artifact(_payload("sec-live-redacted-001"))
    response_text = json.dumps(response, sort_keys=True)

    assert response["live_source_artifact_receipt_status"] == "available"
    assert response["source_artifact_receipt"]["content_sha256"]
    assert response["source_artifact_receipt"]["content_length"] == len(content)
    assert response["cache"]["network_request_made"] is True
    assert response["sec_request_policy"]["server_configured_user_agent_hash"]
    assert "https://www.sec.gov" not in response_text
    assert "0000320193-24-000123" not in response_text
    assert "0000320193" not in response_text
    assert raw_user_agent not in response_text
    assert "PRIVATE-LIVE-FILING-VALUE" not in response_text
    assert str(tmp_path) not in response_text

    receipt_root = tmp_path / "storage" / svc.RECEIPT_DIR
    receipt_files = list((receipt_root / "receipts").glob("*.json"))
    artifact_files = list((receipt_root / "artifacts").glob("*.txt"))
    assert len(receipt_files) == 1
    assert len(artifact_files) == 1
    receipt_text = receipt_files[0].read_text(encoding="utf-8")
    assert raw_user_agent not in receipt_text
    assert "https://www.sec.gov" not in receipt_text
    assert "0000320193-24-000123" not in receipt_text
    assert "PRIVATE-LIVE-FILING-VALUE" not in receipt_text
