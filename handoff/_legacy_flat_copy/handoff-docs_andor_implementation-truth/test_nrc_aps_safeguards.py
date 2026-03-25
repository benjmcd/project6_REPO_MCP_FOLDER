import json
import sys
from pathlib import Path

import pytest
import requests


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_safeguards  # noqa: E402


def _response(status_code: int, *, retry_after: str | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = b"{}"  # noqa: SLF001
    response.headers = {}
    if retry_after is not None:
        response.headers["retry-after"] = retry_after
    return response


def test_policy_loader_blocks_multi_process_without_override():
    _policy, lint = nrc_aps_safeguards.ApsSafeguardPolicyLoader.load_from_config(
        {"runtime_process_count": 2, "unsafe_allow_multi_process_limiter": False},
        max_concurrent_runs=2,
    )
    codes = {str(item.get("code") or "") for item in lint["blocking_errors"]}
    assert "multi_process_limiter_unsafe" in codes


def test_policy_loader_normalizes_retry_budgets():
    policy, lint = nrc_aps_safeguards.ApsSafeguardPolicyLoader.load_from_config(
        {
            "retry_max_attempts_per_request": 5,
            "retry_max_attempts_per_scope": 2,
            "retry_max_attempts_per_run": 3,
        },
        max_concurrent_runs=1,
    )
    retry_policy = policy["retry"]
    assert retry_policy["max_attempts_per_scope"] == 5
    assert retry_policy["max_attempts_per_run"] == 5
    warning_codes = {str(item.get("code") or "") for item in lint["warnings"]}
    assert "retry_scope_budget_normalized" in warning_codes
    assert "retry_run_budget_normalized" in warning_codes


def test_failure_classifier_matrix_core_cases():
    assert nrc_aps_safeguards.ApsFailureClassifier.classify_status(429).failure_class == nrc_aps_safeguards.APS_CLASS_HTTP_429
    assert nrc_aps_safeguards.ApsFailureClassifier.classify_status(500).failure_class == nrc_aps_safeguards.APS_CLASS_HTTP_5XX
    assert nrc_aps_safeguards.ApsFailureClassifier.classify_status(401).failure_class == nrc_aps_safeguards.APS_CLASS_AUTH
    assert nrc_aps_safeguards.ApsFailureClassifier.classify_status(422).failure_class == nrc_aps_safeguards.APS_CLASS_HTTP_4XX
    parse_decision = nrc_aps_safeguards.ApsFailureClassifier.classify_parse_status("invalid_json")
    assert parse_decision is not None
    assert parse_decision.failure_class == nrc_aps_safeguards.APS_CLASS_JSON_MALFORMED


def test_limiter_bounded_wait_failure():
    limiter = nrc_aps_safeguards.ApsLimiterService()
    first = limiter.acquire(
        bucket_key="bucket-1",
        rate_per_second=0.1,
        max_wait_seconds=0.01,
        queue_poll_seconds=0.005,
    )
    assert first.granted is True

    second = limiter.acquire(
        bucket_key="bucket-1",
        rate_per_second=0.1,
        max_wait_seconds=0.01,
        queue_poll_seconds=0.005,
    )
    assert second.granted is False
    assert second.failure_class == nrc_aps_safeguards.APS_CLASS_LIMITER_WAIT


def test_request_executor_retries_429_then_success():
    policy = {
        "schema_id": nrc_aps_safeguards.APS_SAFEGUARD_POLICY_SCHEMA_ID,
        "schema_version": 1,
        "limiter": {
            "max_rps": 100.0,
            "max_wait_seconds": 1.0,
            "queue_poll_seconds": 0.001,
            "auth_cooldown_seconds": 1.0,
        },
        "timeouts": {"connect_timeout_seconds": 1.0, "read_timeout_seconds": 1.0, "overall_deadline_seconds": 5.0},
        "retry": {
            "max_attempts_per_request": 3,
            "max_attempts_per_scope": 3,
            "max_attempts_per_run": 10,
            "max_cumulative_sleep_seconds": 5.0,
            "base_backoff_seconds": 0.01,
            "max_backoff_seconds": 0.05,
            "jitter_mode": "none",
            "respect_retry_after": True,
        },
    }
    recorder = nrc_aps_safeguards.ApsSafeguardRecorder()
    executor = nrc_aps_safeguards.ApsRequestExecutor(
        policy=policy,
        limiter=nrc_aps_safeguards.ApsLimiterService(),
        recorder=recorder,
    )

    responses = [_response(429, retry_after="0.01"), _response(200)]

    def _send() -> requests.Response:
        return responses.pop(0)

    response = executor.execute(
        method="GET",
        url="https://example.test/aps/api/search",
        call_class="search",
        bucket_key="bucket-2",
        request_callable=_send,
        explicit_scope="search:test",
    )
    assert int(response.status_code) == 200
    event_types = [item["event_type"] for item in recorder.events()]
    assert "aps_retry_scheduled" in event_types


def test_validate_safeguard_artifact_presence_fail_closed(tmp_path: Path):
    run_id = "11111111-1111-1111-1111-111111111111"
    rows = [{"run_id": run_id}]
    missing = nrc_aps_safeguards.validate_safeguard_artifact_presence(run_rows=rows, reports_dir=tmp_path)
    assert missing["passed"] is False
    assert missing["checks"][0]["reasons"] == ["missing_artifact"]

    report_path = tmp_path / f"{run_id}_aps_safeguard_v1.json"
    report_payload = {
        "schema_id": nrc_aps_safeguards.APS_SAFEGUARD_REPORT_SCHEMA_ID,
        "schema_version": nrc_aps_safeguards.APS_SAFEGUARD_REPORT_SCHEMA_VERSION,
        "run_id": run_id,
    }
    report_path.write_text(json.dumps(report_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    passed = nrc_aps_safeguards.validate_safeguard_artifact_presence(run_rows=rows, reports_dir=tmp_path)
    assert passed["passed"] is True

