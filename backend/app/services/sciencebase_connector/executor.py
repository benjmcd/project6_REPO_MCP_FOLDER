from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget, ConnectorTargetStageAttempt
from app.services.sciencebase_connector.contracts import LeaseConflictError, RECONCILIATION_STATUSES, TARGET_TERMINAL_STATUSES


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExecutorGuards:
    _host_locks: dict[str, threading.BoundedSemaphore] = {}
    _host_guard = threading.Lock()

    def __init__(self, *, max_concurrent_runs: int):
        self.run_gate = threading.BoundedSemaphore(max(1, int(max_concurrent_runs)))

    def acquire_run_slot(self) -> None:
        self.run_gate.acquire()

    def release_run_slot(self) -> None:
        self.run_gate.release()

    @classmethod
    def acquire_host_slot(cls, url: str, per_host_limit: int) -> threading.BoundedSemaphore:
        host = (urlparse(url).hostname or "").lower() or "unknown-host"
        with cls._host_guard:
            gate = cls._host_locks.get(host)
            if gate is None:
                gate = threading.BoundedSemaphore(max(1, int(per_host_limit)))
                cls._host_locks[host] = gate
        gate.acquire()
        return gate


def assert_lease_token(*, current_token: str | None, expected_token: str | None, expires_at: datetime | None) -> None:
    if not expected_token or not current_token or current_token != expected_token:
        raise LeaseConflictError("lease_conflict")
    now = utcnow()
    if expires_at is not None and expires_at <= now:
        raise LeaseConflictError("lease_conflict")


_SELECTED_STATUSES = {
    "selected",
    "downloaded",
    "ingested",
    "profiled",
    "recommended",
    "skipped_unchanged",
    "not_modified_remote",
    "dry_run_skipped",
}
_IGNORED_STATUSES = {"ignored_by_policy", "unsupported_artifact_surface"}
_POLICY_STATUSES = {"ignored_by_policy", "unsupported_artifact_surface", "blocked_by_fetch_policy"}
_DOWNLOADED_STATUSES = {"downloaded", "ingested", "profiled", "recommended", "skipped_unchanged", "not_modified_remote"}
_INGESTED_STATUSES = {"ingested", "profiled", "recommended"}
_PROFILED_STATUSES = {"profiled", "recommended"}
_FAILED_STATUSES = {"download_failed", "ingest_failed", "profile_failed", "recommend_failed"}


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _is_target_terminal(status: str | None, retry_eligible: bool) -> bool:
    if not status:
        return False
    if status in TARGET_TERMINAL_STATUSES:
        return True
    if status in _FAILED_STATUSES and not retry_eligible:
        return True
    return False


def _status_contribution(status: str | None) -> dict[str, int]:
    if not status:
        return {
            "selected_count": 0,
            "ignored_count": 0,
            "collapsed_duplicate_count": 0,
            "deduped_within_run_count": 0,
            "blocked_by_fetch_policy_count": 0,
            "skipped_unchanged_count": 0,
            "not_modified_count": 0,
            "reconciliation_only_count": 0,
            "budget_blocked_count": 0,
            "downloaded_count": 0,
            "ingested_count": 0,
            "profiled_count": 0,
            "recommended_count": 0,
            "failed_count": 0,
        }
    return {
        "selected_count": 1 if status in _SELECTED_STATUSES else 0,
        "ignored_count": 1 if status in _IGNORED_STATUSES else 0,
        "collapsed_duplicate_count": 1 if status == "collapsed_duplicate" else 0,
        "deduped_within_run_count": 1 if status == "collapsed_duplicate" else 0,
        "blocked_by_fetch_policy_count": 1 if status == "blocked_by_fetch_policy" else 0,
        "skipped_unchanged_count": 1 if status == "skipped_unchanged" else 0,
        "not_modified_count": 1 if status == "not_modified_remote" else 0,
        "reconciliation_only_count": 1 if status in RECONCILIATION_STATUSES else 0,
        "budget_blocked_count": 1 if status == "budget_blocked" else 0,
        "downloaded_count": 1 if status in _DOWNLOADED_STATUSES else 0,
        "ingested_count": 1 if status in _INGESTED_STATUSES else 0,
        "profiled_count": 1 if status in _PROFILED_STATUSES else 0,
        "recommended_count": 1 if status == "recommended" else 0,
        "failed_count": 1 if status in _FAILED_STATUSES else 0,
    }


def _apply_counter_delta(
    run: ConnectorRun,
    *,
    status_before: str | None,
    status_after: str | None,
    retry_before: bool,
    retry_after: bool,
    reason_before: str | None,
    reason_after: str | None,
    created: bool,
) -> None:
    if created:
        run.discovered_count = _as_int(run.discovered_count) + 1

    before = _status_contribution(status_before)
    after = _status_contribution(status_after)
    for field, after_value in after.items():
        before_value = before.get(field, 0)
        delta = int(after_value) - int(before_value)
        if delta:
            setattr(run, field, _as_int(getattr(run, field, 0)) + delta)

    if status_before is None:
        retry_delta = int(bool(retry_after))
        if retry_delta:
            run.retryable_target_count = _as_int(getattr(run, "retryable_target_count", 0)) + retry_delta

        is_terminal = _is_target_terminal(status_after, retry_after)
        terminal_delta = int(is_terminal)
        if terminal_delta:
            run.terminal_target_count = _as_int(getattr(run, "terminal_target_count", 0)) + terminal_delta
        nonterminal_delta = int(not is_terminal)
        if nonterminal_delta:
            run.nonterminal_target_count = _as_int(getattr(run, "nonterminal_target_count", 0)) + nonterminal_delta
    elif status_after is not None:
        retry_delta = int(bool(retry_after)) - int(bool(retry_before))
        if retry_delta:
            run.retryable_target_count = _as_int(getattr(run, "retryable_target_count", 0)) + retry_delta

        was_terminal = _is_target_terminal(status_before, retry_before)
        is_terminal = _is_target_terminal(status_after, retry_after)
        terminal_delta = int(is_terminal) - int(was_terminal)
        if terminal_delta:
            run.terminal_target_count = _as_int(getattr(run, "terminal_target_count", 0)) + terminal_delta
        nonterminal_delta = int(not is_terminal) - int(not was_terminal)
        if nonterminal_delta:
            run.nonterminal_target_count = _as_int(getattr(run, "nonterminal_target_count", 0)) + nonterminal_delta

    policy_counts = dict(run.policy_skipped_count_by_reason_json or {})
    if status_before in _POLICY_STATUSES and reason_before:
        policy_counts[reason_before] = max(0, int(policy_counts.get(reason_before, 0)) - 1)
        if policy_counts[reason_before] == 0:
            policy_counts.pop(reason_before, None)
    if status_after in _POLICY_STATUSES and reason_after:
        policy_counts[reason_after] = int(policy_counts.get(reason_after, 0)) + 1
    run.policy_skipped_count_by_reason_json = policy_counts
    run.deduped_within_run_count = _as_int(run.collapsed_duplicate_count)
    run.budget_exhausted = bool(run.budget_exhausted or _as_int(run.budget_blocked_count) > 0)


def transition_target_state(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    status_after: str,
    phase: str | None = None,
    stage: str | None = None,
    event_type: str | None = None,
    status_before_override: str | None = None,
    created: bool = False,
    operator_reason_code: str | None = None,
    error_class: str | None = None,
    message: str | None = None,
    retry_eligible: bool | None = None,
    target_updates: dict[str, Any] | None = None,
    stage_attempt: dict[str, Any] | None = None,
    metrics_json: dict[str, Any] | None = None,
    assert_lease: Callable[[ConnectorRun, str | None], None] | None = None,
    lease_token: str | None = None,
) -> None:
    now = utcnow()
    status_before = status_before_override
    if not created and status_before is None:
        status_before = target.status
    retry_before = bool(target.retry_eligible) if status_before else False
    reason_before = target.operator_reason_code if status_before else None

    if target_updates:
        for key, value in target_updates.items():
            setattr(target, key, value)
    if retry_eligible is not None:
        target.retry_eligible = bool(retry_eligible)
    if operator_reason_code is not None:
        target.operator_reason_code = operator_reason_code

    target.status = status_after
    target.last_stage_transition_at = now

    _apply_counter_delta(
        run,
        status_before=status_before,
        status_after=status_after,
        retry_before=retry_before,
        retry_after=bool(target.retry_eligible),
        reason_before=reason_before,
        reason_after=target.operator_reason_code,
        created=created,
    )

    if event_type:
        db.add(
            ConnectorRunEvent(
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                phase=phase,
                stage=stage,
                event_type=event_type,
                status_before=status_before,
                status_after=status_after,
                reason_code=target.operator_reason_code,
                error_class=error_class,
                message=message,
                metrics_json=metrics_json or {},
                created_at=now,
            )
        )

    if stage_attempt:
        metrics_payload = dict(stage_attempt.get("metrics_json") or {})
        db.add(
            ConnectorTargetStageAttempt(
                connector_run_target_id=target.connector_run_target_id,
                stage=str(stage_attempt.get("stage") or stage or "unknown"),
                attempt_number=int(stage_attempt.get("attempt_number") or target.attempt_count or 1),
                started_at=stage_attempt.get("started_at") or now,
                completed_at=now,
                status=str(stage_attempt.get("status") or status_after),
                error_class=stage_attempt.get("error_class"),
                error_message=stage_attempt.get("error_message"),
                retryable=bool(stage_attempt.get("retryable", target.retry_eligible)),
                metrics_json=metrics_payload,
            )
        )

    if assert_lease:
        assert_lease(run, lease_token)
    db.commit()
