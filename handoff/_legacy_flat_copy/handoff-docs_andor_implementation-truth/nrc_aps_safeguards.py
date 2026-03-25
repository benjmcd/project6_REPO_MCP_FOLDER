from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests


APS_SAFEGUARD_POLICY_SCHEMA_ID = "aps_safeguard_policy.v1"
APS_SAFEGUARD_POLICY_SCHEMA_VERSION = 1
APS_SAFEGUARD_LINT_SCHEMA_ID = "aps.safeguard_lint.v1"
APS_SAFEGUARD_REPORT_SCHEMA_ID = "aps.safeguard_report.v1"
APS_SAFEGUARD_REPORT_SCHEMA_VERSION = 1
APS_SAFEGUARD_VALIDATION_SCHEMA_ID = "aps.safeguard_validation.v1"

APS_TIMEOUT_CONNECT = "connect_timeout"
APS_TIMEOUT_READ = "read_timeout"
APS_TIMEOUT_DEADLINE = "deadline_exceeded"

APS_CLASS_HTTP_429 = "http_429"
APS_CLASS_HTTP_5XX = "http_5xx"
APS_CLASS_NETWORK = "network_connectivity_failure"
APS_CLASS_JSON_MALFORMED = "malformed_invalid_json"
APS_CLASS_HTTP_4XX = "http_4xx_request_contract"
APS_CLASS_AUTH = "auth_subscription_failure"
APS_CLASS_DOWNLOAD_FAILURE = "artifact_download_failure"
APS_CLASS_LIMITER_WAIT = "limiter_wait_exceeded"
APS_CLASS_REQUEST_BUDGET = "request_attempt_budget_exhausted"
APS_CLASS_SCOPE_BUDGET = "scope_attempt_budget_exhausted"
APS_CLASS_RUN_BUDGET = "run_attempt_budget_exhausted"

APS_PARSE_FAILURE_STATUSES = {"empty_body", "invalid_json", "non_dict_json"}


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


@dataclass(frozen=True)
class ApsFailureDecision:
    failure_class: str
    retryable: bool
    status_code: int | None = None
    retry_after_seconds: float | None = None


@dataclass(frozen=True)
class ApsLimiterAcquireResult:
    granted: bool
    wait_seconds: float
    queue_depth: int
    failure_class: str | None = None
    cooldown_remaining_seconds: float = 0.0


class ApsTimeoutNormalizer:
    @staticmethod
    def normalize(*, config: dict[str, Any], policy: dict[str, Any]) -> tuple[float, float, float]:
        timeout_cfg = _as_dict(policy.get("timeouts"))
        connect_timeout = _coerce_float(
            config.get("connect_timeout_seconds", timeout_cfg.get("connect_timeout_seconds", 10.0)),
            10.0,
        )
        legacy_timeout = _coerce_float(config.get("request_timeout_seconds", timeout_cfg.get("read_timeout_seconds", 30.0)), 30.0)
        read_timeout = _coerce_float(config.get("read_timeout_seconds", legacy_timeout), legacy_timeout)
        deadline_timeout = _coerce_float(
            config.get("overall_deadline_seconds", timeout_cfg.get("overall_deadline_seconds", 120.0)),
            120.0,
        )
        connect_timeout = max(0.1, connect_timeout)
        read_timeout = max(0.1, read_timeout)
        deadline_timeout = max(max(connect_timeout, read_timeout), deadline_timeout)
        return connect_timeout, read_timeout, deadline_timeout


class ApsBackoffPlanner:
    @staticmethod
    def compute_delay(
        *,
        attempt_index: int,
        retry_after_header: str | None,
        retry_cfg: dict[str, Any],
        cumulative_sleep_seconds: float,
    ) -> float:
        base = max(0.01, _coerce_float(retry_cfg.get("base_backoff_seconds", 0.4), 0.4))
        max_backoff = max(base, _coerce_float(retry_cfg.get("max_backoff_seconds", 3.0), 3.0))
        max_cumulative = max(0.0, _coerce_float(retry_cfg.get("max_cumulative_sleep_seconds", 20.0), 20.0))
        respect_retry_after = _coerce_bool(retry_cfg.get("respect_retry_after", True), True)
        jitter_mode = str(retry_cfg.get("jitter_mode", "none") or "none").strip().lower()

        retry_after_seconds: float | None = None
        if respect_retry_after and retry_after_header:
            try:
                retry_after_seconds = max(0.0, float(str(retry_after_header).strip()))
            except ValueError:
                retry_after_seconds = None

        delay = retry_after_seconds if retry_after_seconds is not None else base * (2 ** max(0, attempt_index - 1))
        delay = min(delay, max_backoff)
        if jitter_mode == "full":
            delay = random.uniform(0.0, delay)

        remaining_sleep = max(0.0, max_cumulative - max(0.0, cumulative_sleep_seconds))
        return max(0.0, min(delay, remaining_sleep))


class ApsFailureClassifier:
    @staticmethod
    def classify_exception(exc: Exception) -> ApsFailureDecision:
        if isinstance(exc, requests.ConnectTimeout):
            return ApsFailureDecision(failure_class=APS_TIMEOUT_CONNECT, retryable=True)
        if isinstance(exc, requests.ReadTimeout):
            return ApsFailureDecision(failure_class=APS_TIMEOUT_READ, retryable=True)
        if isinstance(exc, requests.Timeout):
            if "overall_deadline_exceeded" in str(exc):
                return ApsFailureDecision(failure_class=APS_TIMEOUT_DEADLINE, retryable=True)
            return ApsFailureDecision(failure_class=APS_TIMEOUT_READ, retryable=True)
        if isinstance(exc, requests.ConnectionError):
            return ApsFailureDecision(failure_class=APS_CLASS_NETWORK, retryable=True)
        if isinstance(exc, requests.HTTPError):
            status_code = int(exc.response.status_code) if exc.response is not None else 0
            return ApsFailureClassifier.classify_status(status_code)
        return ApsFailureDecision(failure_class="runtime_exception", retryable=False)

    @staticmethod
    def classify_status(status_code: int) -> ApsFailureDecision:
        code = int(status_code or 0)
        if code == 429:
            return ApsFailureDecision(failure_class=APS_CLASS_HTTP_429, retryable=True, status_code=code)
        if code in {500, 502, 503, 504}:
            return ApsFailureDecision(failure_class=APS_CLASS_HTTP_5XX, retryable=True, status_code=code)
        if code in {401, 403}:
            return ApsFailureDecision(failure_class=APS_CLASS_AUTH, retryable=False, status_code=code)
        if 400 <= code <= 499:
            return ApsFailureDecision(failure_class=APS_CLASS_HTTP_4XX, retryable=False, status_code=code)
        return ApsFailureDecision(failure_class="ok", retryable=False, status_code=code)

    @staticmethod
    def classify_parse_status(parse_status: str | None) -> ApsFailureDecision | None:
        normalized = str(parse_status or "").strip().lower()
        if normalized in APS_PARSE_FAILURE_STATUSES:
            return ApsFailureDecision(failure_class=APS_CLASS_JSON_MALFORMED, retryable=False)
        return None


class ApsSafeguardPolicyLoader:
    @staticmethod
    def _unknown_keys(payload: dict[str, Any], allowed: set[str]) -> list[str]:
        return sorted([str(key) for key in payload.keys() if str(key) not in allowed])

    @staticmethod
    def load_from_config(
        config: dict[str, Any],
        *,
        max_concurrent_runs: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        source = _as_dict(config.get("safeguard_policy"))
        limiter_source = _as_dict(source.get("limiter"))
        timeout_source = _as_dict(source.get("timeouts"))
        retry_source = _as_dict(source.get("retry"))
        blocking: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        limiter_policy = {
            "max_rps": max(
                0.1,
                _coerce_float(
                    config.get("max_rps", limiter_source.get("max_rps", 5.0)),
                    5.0,
                ),
            ),
            "max_wait_seconds": max(
                0.1,
                _coerce_float(
                    config.get("limiter_max_wait_seconds", limiter_source.get("max_wait_seconds", 10.0)),
                    10.0,
                ),
            ),
            "queue_poll_seconds": max(
                0.01,
                _coerce_float(
                    config.get("limiter_queue_poll_seconds", limiter_source.get("queue_poll_seconds", 0.05)),
                    0.05,
                ),
            ),
            "auth_cooldown_seconds": max(
                0.0,
                _coerce_float(
                    config.get("limiter_auth_cooldown_seconds", limiter_source.get("auth_cooldown_seconds", 10.0)),
                    10.0,
                ),
            ),
            "shared_budget_across_call_classes": _coerce_bool(
                config.get(
                    "limiter_shared_budget_across_call_classes",
                    limiter_source.get("shared_budget_across_call_classes", True),
                ),
                True,
            ),
            "runtime_process_count": max(
                1,
                _coerce_int(
                    config.get("runtime_process_count", limiter_source.get("runtime_process_count", 1)),
                    1,
                ),
            ),
            "unsafe_allow_multi_process_limiter": _coerce_bool(
                config.get(
                    "unsafe_allow_multi_process_limiter",
                    limiter_source.get("unsafe_allow_multi_process_limiter", False),
                ),
                False,
            ),
        }
        timeout_policy = {
            "connect_timeout_seconds": max(
                0.1,
                _coerce_float(
                    config.get("connect_timeout_seconds", timeout_source.get("connect_timeout_seconds", 10.0)),
                    10.0,
                ),
            ),
            "read_timeout_seconds": max(
                0.1,
                _coerce_float(
                    config.get(
                        "read_timeout_seconds",
                        config.get("request_timeout_seconds", timeout_source.get("read_timeout_seconds", 30.0)),
                    ),
                    30.0,
                ),
            ),
            "overall_deadline_seconds": max(
                0.1,
                _coerce_float(
                    config.get("overall_deadline_seconds", timeout_source.get("overall_deadline_seconds", 120.0)),
                    120.0,
                ),
            ),
        }
        timeout_policy["overall_deadline_seconds"] = max(
            timeout_policy["overall_deadline_seconds"],
            timeout_policy["connect_timeout_seconds"],
            timeout_policy["read_timeout_seconds"],
        )

        retry_policy = {
            "max_attempts_per_request": max(
                1,
                _coerce_int(
                    config.get("retry_max_attempts_per_request", retry_source.get("max_attempts_per_request", 4)),
                    4,
                ),
            ),
            "max_attempts_per_scope": max(
                1,
                _coerce_int(
                    config.get("retry_max_attempts_per_scope", retry_source.get("max_attempts_per_scope", 8)),
                    8,
                ),
            ),
            "max_attempts_per_run": max(
                1,
                _coerce_int(
                    config.get("retry_max_attempts_per_run", retry_source.get("max_attempts_per_run", 300)),
                    300,
                ),
            ),
            "max_cumulative_sleep_seconds": max(
                0.0,
                _coerce_float(
                    config.get("retry_max_cumulative_sleep_seconds", retry_source.get("max_cumulative_sleep_seconds", 20.0)),
                    20.0,
                ),
            ),
            "base_backoff_seconds": max(
                0.01,
                _coerce_float(
                    config.get("retry_base_backoff_seconds", retry_source.get("base_backoff_seconds", 0.4)),
                    0.4,
                ),
            ),
            "max_backoff_seconds": max(
                0.01,
                _coerce_float(
                    config.get("retry_max_backoff_seconds", retry_source.get("max_backoff_seconds", 3.0)),
                    3.0,
                ),
            ),
            "jitter_mode": str(config.get("retry_jitter_mode", retry_source.get("jitter_mode", "none")) or "none").strip().lower(),
            "respect_retry_after": _coerce_bool(
                config.get("retry_respect_retry_after", retry_source.get("respect_retry_after", True)),
                True,
            ),
        }

        if retry_policy["max_attempts_per_scope"] < retry_policy["max_attempts_per_request"]:
            retry_policy["max_attempts_per_scope"] = retry_policy["max_attempts_per_request"]
            warnings.append(
                {
                    "code": "retry_scope_budget_normalized",
                    "field": "retry.max_attempts_per_scope",
                    "message": "max_attempts_per_scope raised to satisfy max_attempts_per_request",
                }
            )
        if retry_policy["max_attempts_per_run"] < retry_policy["max_attempts_per_scope"]:
            retry_policy["max_attempts_per_run"] = retry_policy["max_attempts_per_scope"]
            warnings.append(
                {
                    "code": "retry_run_budget_normalized",
                    "field": "retry.max_attempts_per_run",
                    "message": "max_attempts_per_run raised to satisfy max_attempts_per_scope",
                }
            )

        if limiter_policy["max_rps"] > 25.0:
            blocking.append(
                {
                    "code": "max_rps_out_of_bounds",
                    "field": "limiter.max_rps",
                    "message": "max_rps exceeds safeguard bound (25.0) and is blocked",
                }
            )
        if limiter_policy["runtime_process_count"] > 1 and not limiter_policy["unsafe_allow_multi_process_limiter"]:
            blocking.append(
                {
                    "code": "multi_process_limiter_unsafe",
                    "field": "limiter.runtime_process_count",
                    "message": "process-local limiter is unsafe across multi-process runtime without override",
                }
            )
        if timeout_policy["overall_deadline_seconds"] < timeout_policy["read_timeout_seconds"]:
            blocking.append(
                {
                    "code": "deadline_less_than_read_timeout",
                    "field": "timeouts.overall_deadline_seconds",
                    "message": "overall_deadline_seconds must be >= read_timeout_seconds",
                }
            )
        if retry_policy["jitter_mode"] not in {"none", "full"}:
            blocking.append(
                {
                    "code": "retry_jitter_mode_invalid",
                    "field": "retry.jitter_mode",
                    "message": "retry.jitter_mode must be one of: none, full",
                }
            )

        if max_concurrent_runs > 1 and limiter_policy["runtime_process_count"] == 1:
            warnings.append(
                {
                    "code": "max_concurrent_runs_gt_one",
                    "field": "runtime",
                    "message": "connector_max_concurrent_runs>1 uses shared process-local limiter; verify deployment is single-process",
                }
            )

        for unknown in ApsSafeguardPolicyLoader._unknown_keys(source, {"schema_id", "schema_version", "limiter", "timeouts", "retry"}):
            warnings.append(
                {
                    "code": "unknown_policy_field",
                    "field": f"safeguard_policy.{unknown}",
                    "message": "unknown safeguard_policy field preserved as warning",
                }
            )
        for unknown in ApsSafeguardPolicyLoader._unknown_keys(limiter_source, set(limiter_policy.keys())):
            warnings.append(
                {
                    "code": "unknown_policy_field",
                    "field": f"safeguard_policy.limiter.{unknown}",
                    "message": "unknown limiter field preserved as warning",
                }
            )
        for unknown in ApsSafeguardPolicyLoader._unknown_keys(timeout_source, set(timeout_policy.keys())):
            warnings.append(
                {
                    "code": "unknown_policy_field",
                    "field": f"safeguard_policy.timeouts.{unknown}",
                    "message": "unknown timeout field preserved as warning",
                }
            )
        for unknown in ApsSafeguardPolicyLoader._unknown_keys(retry_source, set(retry_policy.keys())):
            warnings.append(
                {
                    "code": "unknown_policy_field",
                    "field": f"safeguard_policy.retry.{unknown}",
                    "message": "unknown retry field preserved as warning",
                }
            )

        policy = {
            "schema_id": APS_SAFEGUARD_POLICY_SCHEMA_ID,
            "schema_version": APS_SAFEGUARD_POLICY_SCHEMA_VERSION,
            "limiter": limiter_policy,
            "timeouts": timeout_policy,
            "retry": retry_policy,
        }
        lint = {
            "schema_id": APS_SAFEGUARD_LINT_SCHEMA_ID,
            "schema_version": 1,
            "policy_schema_id": APS_SAFEGUARD_POLICY_SCHEMA_ID,
            "blocking_errors": blocking,
            "warnings": warnings,
            "policy_hash": _stable_hash(policy),
        }
        return policy, lint


class ApsLimiterService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, dict[str, Any]] = {}

    def _bucket(self, bucket_key: str, *, rate_per_second: float) -> dict[str, Any]:
        safe_rate = max(0.1, float(rate_per_second))
        capacity = max(1.0, safe_rate * 2.0)
        current = self._state.get(bucket_key)
        if current:
            return current
        bucket = {
            "tokens": capacity,
            "last_refill": time.monotonic(),
            "capacity": capacity,
            "cooldown_until": 0.0,
            "waiters": deque(),
        }
        self._state[bucket_key] = bucket
        return bucket

    def set_cooldown(self, *, bucket_key: str, rate_per_second: float, cooldown_seconds: float) -> None:
        with self._lock:
            bucket = self._bucket(bucket_key, rate_per_second=rate_per_second)
            bucket["cooldown_until"] = max(float(bucket.get("cooldown_until") or 0.0), time.monotonic() + max(0.0, cooldown_seconds))

    def acquire(
        self,
        *,
        bucket_key: str,
        rate_per_second: float,
        max_wait_seconds: float,
        queue_poll_seconds: float,
    ) -> ApsLimiterAcquireResult:
        ticket = uuid.uuid4().hex
        deadline = time.monotonic() + max(0.01, float(max_wait_seconds))
        poll_seconds = max(0.005, float(queue_poll_seconds))
        start = time.monotonic()

        with self._lock:
            bucket = self._bucket(bucket_key, rate_per_second=rate_per_second)
            waiters: deque[str] = bucket["waiters"]
            waiters.append(ticket)

        while True:
            with self._lock:
                bucket = self._bucket(bucket_key, rate_per_second=rate_per_second)
                waiters = bucket["waiters"]
                now = time.monotonic()
                capacity = float(bucket["capacity"])
                elapsed = max(0.0, now - float(bucket["last_refill"]))
                tokens = min(capacity, float(bucket["tokens"]) + (elapsed * max(0.1, float(rate_per_second))))
                bucket["tokens"] = tokens
                bucket["last_refill"] = now
                queue_depth = len(waiters)
                cooldown_until = float(bucket.get("cooldown_until") or 0.0)
                cooldown_remaining = max(0.0, cooldown_until - now)

                if ticket not in waiters:
                    waiters.append(ticket)
                    queue_depth = len(waiters)

                if now > deadline:
                    try:
                        waiters.remove(ticket)
                    except ValueError:
                        pass
                    return ApsLimiterAcquireResult(
                        granted=False,
                        wait_seconds=max(0.0, now - start),
                        queue_depth=max(0, queue_depth - 1),
                        failure_class=APS_CLASS_LIMITER_WAIT,
                        cooldown_remaining_seconds=cooldown_remaining,
                    )

                is_turn = bool(waiters and waiters[0] == ticket)
                if is_turn and cooldown_remaining <= 0.0 and tokens >= 1.0:
                    waiters.popleft()
                    bucket["tokens"] = max(0.0, tokens - 1.0)
                    return ApsLimiterAcquireResult(
                        granted=True,
                        wait_seconds=max(0.0, now - start),
                        queue_depth=max(0, queue_depth - 1),
                    )

                sleep_for = poll_seconds
                if cooldown_remaining > 0.0:
                    sleep_for = min(sleep_for, cooldown_remaining)
                sleep_for = min(sleep_for, max(0.005, deadline - now))
            time.sleep(max(0.005, sleep_for))


APS_LIMITER = ApsLimiterService()

class ApsSafeguardRecorder:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._dedupe: set[str] = set()

    def record(
        self,
        *,
        event_type: str,
        reason_code: str | None = None,
        error_class: str | None = None,
        message: str | None = None,
        metrics: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
    ) -> None:
        key = str(dedupe_key or "").strip()
        if key and key in self._dedupe:
            return
        if key:
            self._dedupe.add(key)
        self._events.append(
            {
                "event_type": event_type,
                "reason_code": reason_code,
                "error_class": error_class,
                "message": message,
                "metrics": dict(metrics or {}),
                "dedupe_key": key or None,
                "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )

    def events(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._events]

    def to_report(
        self,
        *,
        run_id: str,
        policy: dict[str, Any],
        lint: dict[str, Any],
    ) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for event in self._events:
            event_type = str(event.get("event_type") or "unknown")
            counts[event_type] = int(counts.get(event_type, 0)) + 1
        return {
            "schema_id": APS_SAFEGUARD_REPORT_SCHEMA_ID,
            "schema_version": APS_SAFEGUARD_REPORT_SCHEMA_VERSION,
            "policy_schema_id": str(policy.get("schema_id") or APS_SAFEGUARD_POLICY_SCHEMA_ID),
            "policy_hash": _stable_hash(policy),
            "run_id": run_id,
            "lint_blocking_error_count": len(list(lint.get("blocking_errors") or [])),
            "lint_warning_count": len(list(lint.get("warnings") or [])),
            "event_counts": counts,
            "events": self.events(),
        }


class ApsRequestExecutor:
    def __init__(
        self,
        *,
        policy: dict[str, Any],
        limiter: ApsLimiterService,
        recorder: ApsSafeguardRecorder,
    ) -> None:
        self.policy = dict(policy)
        self.limiter = limiter
        self.recorder = recorder
        self._run_attempts = 0
        self._scope_attempts: dict[str, int] = {}
        self._cumulative_sleep_seconds = 0.0

    def _scope_key(self, *, method: str, url: str, json_body: Any | None, explicit_scope: str | None) -> str:
        if explicit_scope:
            return str(explicit_scope)
        payload_hash = _stable_hash({"method": method, "url": url, "body": json_body if isinstance(json_body, dict) else {}})
        return f"{method.upper()}:{url}:{payload_hash}"

    def execute(
        self,
        *,
        method: str,
        url: str,
        call_class: str,
        bucket_key: str,
        request_callable: Callable[[], requests.Response],
        json_body: dict[str, Any] | None = None,
        explicit_scope: str | None = None,
    ) -> requests.Response:
        limiter_cfg = _as_dict(self.policy.get("limiter"))
        retry_cfg = _as_dict(self.policy.get("retry"))
        max_attempts_request = max(1, _coerce_int(retry_cfg.get("max_attempts_per_request", 4), 4))
        max_attempts_scope = max(1, _coerce_int(retry_cfg.get("max_attempts_per_scope", 8), 8))
        max_attempts_run = max(1, _coerce_int(retry_cfg.get("max_attempts_per_run", 300), 300))
        scope_key = self._scope_key(method=method, url=url, json_body=json_body, explicit_scope=explicit_scope)
        attempt = 0

        while True:
            self._run_attempts += 1
            self._scope_attempts[scope_key] = int(self._scope_attempts.get(scope_key, 0)) + 1
            attempt += 1
            if self._run_attempts > max_attempts_run:
                self.recorder.record(
                    event_type="aps_safeguard_abort",
                    error_class=APS_CLASS_RUN_BUDGET,
                    reason_code="run_budget_exhausted",
                    message="run attempt budget exhausted",
                    metrics={"run_attempts": self._run_attempts, "max_attempts_per_run": max_attempts_run},
                    dedupe_key=f"run-budget:{bucket_key}:{max_attempts_run}",
                )
                raise RuntimeError("aps_safeguard_run_attempt_budget_exhausted")
            if self._scope_attempts[scope_key] > max_attempts_scope:
                self.recorder.record(
                    event_type="aps_safeguard_abort",
                    error_class=APS_CLASS_SCOPE_BUDGET,
                    reason_code="scope_budget_exhausted",
                    message="scope attempt budget exhausted",
                    metrics={"scope_key": scope_key, "scope_attempts": self._scope_attempts[scope_key], "max_attempts_per_scope": max_attempts_scope},
                    dedupe_key=f"scope-budget:{scope_key}:{max_attempts_scope}",
                )
                raise RuntimeError("aps_safeguard_scope_attempt_budget_exhausted")
            if attempt > max_attempts_request:
                self.recorder.record(
                    event_type="aps_retry_exhausted",
                    error_class=APS_CLASS_REQUEST_BUDGET,
                    reason_code="request_budget_exhausted",
                    message="request attempt budget exhausted",
                    metrics={"attempt": attempt, "max_attempts_per_request": max_attempts_request, "scope_key": scope_key},
                    dedupe_key=f"request-budget:{scope_key}:{max_attempts_request}",
                )
                raise RuntimeError("aps_safeguard_request_attempt_budget_exhausted")

            limiter_result = self.limiter.acquire(
                bucket_key=bucket_key,
                rate_per_second=_coerce_float(limiter_cfg.get("max_rps", 5.0), 5.0),
                max_wait_seconds=_coerce_float(limiter_cfg.get("max_wait_seconds", 10.0), 10.0),
                queue_poll_seconds=_coerce_float(limiter_cfg.get("queue_poll_seconds", 0.05), 0.05),
            )
            if not limiter_result.granted:
                self.recorder.record(
                    event_type="aps_safeguard_abort",
                    error_class=limiter_result.failure_class or APS_CLASS_LIMITER_WAIT,
                    reason_code="limiter_wait_exceeded",
                    message="limiter wait budget exceeded",
                    metrics={
                        "wait_seconds": limiter_result.wait_seconds,
                        "queue_depth": limiter_result.queue_depth,
                        "cooldown_remaining_seconds": limiter_result.cooldown_remaining_seconds,
                        "scope_key": scope_key,
                        "call_class": call_class,
                    },
                )
                raise RuntimeError("aps_safeguard_limiter_wait_exceeded")
            if limiter_result.wait_seconds > 0.001:
                self.recorder.record(
                    event_type="aps_limiter_wait",
                    reason_code="limiter_wait",
                    metrics={
                        "wait_seconds": limiter_result.wait_seconds,
                        "queue_depth": limiter_result.queue_depth,
                        "scope_key": scope_key,
                        "call_class": call_class,
                    },
                )

            try:
                response = request_callable()
            except Exception as exc:  # noqa: BLE001
                decision = ApsFailureClassifier.classify_exception(exc)
                if decision.retryable and attempt < max_attempts_request:
                    delay = ApsBackoffPlanner.compute_delay(
                        attempt_index=attempt,
                        retry_after_header=None,
                        retry_cfg=retry_cfg,
                        cumulative_sleep_seconds=self._cumulative_sleep_seconds,
                    )
                    if delay > 0.0:
                        self.recorder.record(
                            event_type="aps_retry_scheduled",
                            reason_code="exception_retryable",
                            error_class=decision.failure_class,
                            metrics={"attempt": attempt, "sleep_seconds": delay, "scope_key": scope_key, "call_class": call_class},
                        )
                        time.sleep(delay)
                        self._cumulative_sleep_seconds += delay
                        continue
                self.recorder.record(
                    event_type="aps_retry_exhausted",
                    reason_code="exception_terminal_or_exhausted",
                    error_class=decision.failure_class,
                    message=str(exc),
                    metrics={"attempt": attempt, "scope_key": scope_key, "call_class": call_class},
                )
                raise

            decision = ApsFailureClassifier.classify_status(int(response.status_code or 0))
            if decision.failure_class == APS_CLASS_AUTH:
                cooldown = _coerce_float(limiter_cfg.get("auth_cooldown_seconds", 10.0), 10.0)
                self.limiter.set_cooldown(bucket_key=bucket_key, rate_per_second=_coerce_float(limiter_cfg.get("max_rps", 5.0), 5.0), cooldown_seconds=cooldown)
                self.recorder.record(
                    event_type="aps_auth_cooldown_applied",
                    reason_code="auth_failure",
                    error_class=decision.failure_class,
                    metrics={"status_code": int(response.status_code or 0), "cooldown_seconds": cooldown, "scope_key": scope_key},
                    dedupe_key=f"auth-cooldown:{bucket_key}:{int(response.status_code or 0)}",
                )

            if decision.retryable and attempt < max_attempts_request:
                delay = ApsBackoffPlanner.compute_delay(
                    attempt_index=attempt,
                    retry_after_header=response.headers.get("retry-after") if response.headers else None,
                    retry_cfg=retry_cfg,
                    cumulative_sleep_seconds=self._cumulative_sleep_seconds,
                )
                if delay > 0.0:
                    self.recorder.record(
                        event_type="aps_retry_scheduled",
                        reason_code="status_retryable",
                        error_class=decision.failure_class,
                        metrics={
                            "attempt": attempt,
                            "status_code": int(response.status_code or 0),
                            "sleep_seconds": delay,
                            "scope_key": scope_key,
                            "call_class": call_class,
                        },
                    )
                    time.sleep(delay)
                    self._cumulative_sleep_seconds += delay
                    continue

            if decision.retryable and attempt >= max_attempts_request:
                self.recorder.record(
                    event_type="aps_retry_exhausted",
                    reason_code="status_retry_exhausted",
                    error_class=decision.failure_class,
                    metrics={"attempt": attempt, "status_code": int(response.status_code or 0), "scope_key": scope_key, "call_class": call_class},
                )
            return response


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if target.exists():
        try:
            existing = target.read_text(encoding="utf-8")
            if existing == serialized:
                return str(target)
        except OSError:
            pass
    tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(serialized, encoding="utf-8")
    os.replace(tmp, target)
    return str(target)


def validate_safeguard_artifact_presence(*, run_rows: list[dict[str, Any]], reports_dir: str | Path) -> dict[str, Any]:
    base = Path(reports_dir)
    checks: list[dict[str, Any]] = []
    for row in run_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        path = base / f"{run_id}_aps_safeguard_v1.json"
        exists = path.exists()
        schema_ok = False
        parse_ok = False
        reasons: list[str] = []
        if exists:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                parse_ok = isinstance(payload, dict)
                if parse_ok and str(payload.get("schema_id") or "") == APS_SAFEGUARD_REPORT_SCHEMA_ID and int(payload.get("schema_version") or 0) == APS_SAFEGUARD_REPORT_SCHEMA_VERSION:
                    schema_ok = True
                else:
                    reasons.append("invalid_schema")
            except (OSError, ValueError):
                reasons.append("invalid_json")
        else:
            reasons.append("missing_artifact")
        checks.append(
            {
                "run_id": run_id,
                "artifact_ref": str(path),
                "artifact_exists": exists,
                "parse_ok": parse_ok,
                "schema_ok": schema_ok,
                "passed": bool(exists and parse_ok and schema_ok),
                "reasons": reasons,
            }
        )
    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    return {
        "schema_id": APS_SAFEGUARD_VALIDATION_SCHEMA_ID,
        "schema_version": 1,
        "passed": passed,
        "checked_runs": len(checks),
        "failed_runs": len([item for item in checks if not bool(item.get("passed"))]),
        "checks": checks,
    }
