from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class ScenarioResult:
    name: str
    run_id: str | None
    status: str
    ok: bool
    detail: str
    not_modified_count: int = 0
    conditional_revalidated_skip_count: int = 0
    conditional_noop_seen: bool = False
    nonterminal_target_count: int = 0


def _write_json_atomic(path: str, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(output)


def _append_ndjson(path: str, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")))
        handle.write("\n")


def _post_json(base_url: str, path: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> requests.Response:
    return requests.post(f"{base_url.rstrip('/')}{path}", json=payload, headers=headers or {}, timeout=60)


def _poll_run(base_url: str, run_id: str, *, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = requests.get(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}", timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") in {"completed", "completed_with_errors", "failed", "cancelled"}:
            return payload
        time.sleep(2)
    raise TimeoutError(f"run {run_id} did not reach terminal state in {timeout_seconds}s")


def _stabilize_nonterminal_targets(
    base_url: str,
    run_id: str,
    run_payload: dict[str, Any],
    *,
    timeout_seconds: int,
    max_resume_attempts: int = 2,
) -> tuple[dict[str, Any], str | None]:
    current = dict(run_payload or {})
    attempts = 0
    while (
        int(current.get("nonterminal_target_count", 0) or 0) > 0
        and str(current.get("status")) in {"completed_with_errors", "failed"}
        and attempts < max_resume_attempts
    ):
        try:
            resume = requests.post(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}/resume", timeout=30)
        except requests.RequestException as exc:
            return current, f"resume request failed while stabilizing nonterminal targets: {exc}"
        if resume.status_code not in {200, 202}:
            return current, f"resume request rejected while stabilizing nonterminal targets: {resume.status_code}"
        try:
            current = _poll_run(base_url, run_id, timeout_seconds=timeout_seconds)
        except Exception as exc:  # noqa: BLE001
            return current, f"resume poll failed while stabilizing nonterminal targets: {exc}"
        attempts += 1
    return current, None


def _validate_operator_surfaces(base_url: str, run_id: str) -> tuple[bool, str, dict[str, Any], dict[str, Any]]:
    try:
        run = requests.get(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}", timeout=30)
        targets = requests.get(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}/targets?limit=500&offset=0", timeout=30)
        events = requests.get(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}/events?limit=500&offset=0", timeout=30)
        reports = requests.get(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}/reports", timeout=30)
    except requests.RequestException as exc:
        return False, f"operator endpoint request failed: {exc}", {}, {}
    if any(resp.status_code != 200 for resp in (run, targets, events, reports)):
        return False, "operator endpoints did not all return 200", {}, {}
    run_payload = run.json()
    targets_payload = targets.json()
    events_payload = events.json()
    reports_payload = reports.json()
    if int(events_payload.get("total", 0)) <= 0:
        return False, "events endpoint returned no events", run_payload, targets_payload
    if "run_summary" not in (reports_payload.get("reports") or {}):
        return False, "reports endpoint missing run_summary", run_payload, targets_payload
    report_status = reports_payload.get("report_status") or {}
    if not bool(report_status.get("run_summary")):
        return False, "reports endpoint indicates run_summary not generated", run_payload, targets_payload
    if int(run_payload.get("nonterminal_target_count", 0)) > 0:
        return False, "run has non-terminal leftovers", run_payload, targets_payload
    return True, "ok", run_payload, targets_payload


def _extract_conditional_noop_metrics(run_payload: dict[str, Any], targets_payload: dict[str, Any]) -> dict[str, int | bool]:
    not_modified_count = int(run_payload.get("not_modified_count", 0) or 0)
    conditional_revalidated_skip_count = 0
    for target in targets_payload.get("targets") or []:
        if target.get("status") != "skipped_unchanged":
            continue
        if target.get("operator_reason_code") == "skipped_unchanged_after_conditional_revalidate":
            conditional_revalidated_skip_count += 1
    return {
        "not_modified_count": not_modified_count,
        "conditional_revalidated_skip_count": conditional_revalidated_skip_count,
        "conditional_noop_seen": bool(not_modified_count > 0 or conditional_revalidated_skip_count > 0),
    }


def _annual_payload(*, run_mode: str) -> dict[str, Any]:
    return {
        "q": "Mineral Commodity Summaries 2026",
        "scope_mode": "keyword_search",
        "filters": ["systemType=Data Release"],
        "run_mode": run_mode,
        "surface_policy": "files_only",
        "allowed_extensions": [".csv"],
        "report_verbosity": "debug",
        "page_size": 20,
        "max_items": 20,
        "max_files": 20,
        "mcs_release_mode": "annual_release",
    }


def _run_standard_scenario(base_url: str, *, name: str, payload: dict[str, Any], timeout_seconds: int, idx: int) -> ScenarioResult:
    key = f"live-pilot-{name}-{int(time.time())}-{idx}"
    try:
        response = _post_json(
            base_url,
            "/api/v1/connectors/sciencebase-mcs/runs",
            payload,
            headers={"Idempotency-Key": key},
        )
    except requests.RequestException as exc:
        return ScenarioResult(name=name, run_id=None, status="submit_failed", ok=False, detail=f"submit request failed: {exc}")
    if response.status_code not in {200, 202}:
        return ScenarioResult(name=name, run_id=None, status="submit_failed", ok=False, detail=response.text)
    run_id = response.json().get("connector_run_id")
    try:
        final_run = _poll_run(base_url, run_id, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        return ScenarioResult(name=name, run_id=run_id, status="timeout", ok=False, detail=str(exc))
    final_run, stabilize_error = _stabilize_nonterminal_targets(base_url, run_id, final_run, timeout_seconds=timeout_seconds)
    if stabilize_error:
        return ScenarioResult(name=name, run_id=run_id, status=str(final_run.get("status", "failed")), ok=False, detail=stabilize_error)
    status = str(final_run.get("status"))
    if status in {"failed", "cancelled"}:
        return ScenarioResult(name=name, run_id=run_id, status=status, ok=False, detail=str(final_run.get("error_summary")))
    surfaces_ok, detail, run_payload, targets_payload = _validate_operator_surfaces(base_url, run_id)
    conditional_metrics = _extract_conditional_noop_metrics(run_payload, targets_payload)
    return ScenarioResult(
        name=name,
        run_id=run_id,
        status=status,
        ok=surfaces_ok,
        detail=detail,
        not_modified_count=int(conditional_metrics["not_modified_count"]),
        conditional_revalidated_skip_count=int(conditional_metrics["conditional_revalidated_skip_count"]),
        conditional_noop_seen=bool(conditional_metrics["conditional_noop_seen"]),
        nonterminal_target_count=int(run_payload.get("nonterminal_target_count", 0) or 0),
    )


def _run_cancel_resume_scenario(base_url: str, *, timeout_seconds: int, idx: int) -> ScenarioResult:
    name = "cancel_resume"
    payload = {
        **_annual_payload(run_mode="one_shot_import"),
        "max_items": 100,
        "max_files": 100,
    }
    key = f"live-pilot-{name}-{int(time.time())}-{idx}"
    try:
        response = _post_json(
            base_url,
            "/api/v1/connectors/sciencebase-mcs/runs",
            payload,
            headers={"Idempotency-Key": key},
        )
    except requests.RequestException as exc:
        return ScenarioResult(name=name, run_id=None, status="submit_failed", ok=False, detail=f"submit request failed: {exc}")
    if response.status_code not in {200, 202}:
        return ScenarioResult(name=name, run_id=None, status="submit_failed", ok=False, detail=response.text)
    run_id = response.json().get("connector_run_id")

    try:
        cancel = requests.post(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}/cancel", timeout=30)
    except requests.RequestException as exc:
        return ScenarioResult(name=name, run_id=run_id, status="cancel_failed", ok=False, detail=f"cancel request failed: {exc}")
    if cancel.status_code != 200:
        return ScenarioResult(name=name, run_id=run_id, status="cancel_failed", ok=False, detail=cancel.text)

    try:
        cancelled = _poll_run(base_url, run_id, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        return ScenarioResult(name=name, run_id=run_id, status="timeout", ok=False, detail=str(exc))

    if str(cancelled.get("status")) != "cancelled":
        return ScenarioResult(
            name=name,
            run_id=run_id,
            status=str(cancelled.get("status")),
            ok=False,
            detail="cancel did not reach cancelled state",
        )

    try:
        resume = requests.post(f"{base_url.rstrip('/')}/api/v1/connectors/runs/{run_id}/resume", timeout=30)
    except requests.RequestException as exc:
        return ScenarioResult(name=name, run_id=run_id, status="resume_failed", ok=False, detail=f"resume request failed: {exc}")
    if resume.status_code not in {200, 202}:
        return ScenarioResult(name=name, run_id=run_id, status="resume_failed", ok=False, detail=resume.text)

    try:
        resumed = _poll_run(base_url, run_id, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        return ScenarioResult(name=name, run_id=run_id, status="timeout", ok=False, detail=str(exc))
    resumed, stabilize_error = _stabilize_nonterminal_targets(base_url, run_id, resumed, timeout_seconds=timeout_seconds)
    if stabilize_error:
        return ScenarioResult(name=name, run_id=run_id, status=str(resumed.get("status", "failed")), ok=False, detail=stabilize_error)

    status = str(resumed.get("status"))
    if status in {"failed", "cancelled"}:
        return ScenarioResult(name=name, run_id=run_id, status=status, ok=False, detail=str(resumed.get("error_summary")))

    surfaces_ok, detail, run_payload, targets_payload = _validate_operator_surfaces(base_url, run_id)
    conditional_metrics = _extract_conditional_noop_metrics(run_payload, targets_payload)
    return ScenarioResult(
        name=name,
        run_id=run_id,
        status=status,
        ok=surfaces_ok,
        detail=detail,
        not_modified_count=int(conditional_metrics["not_modified_count"]),
        conditional_revalidated_skip_count=int(conditional_metrics["conditional_revalidated_skip_count"]),
        conditional_noop_seen=bool(conditional_metrics["conditional_noop_seen"]),
        nonterminal_target_count=int(run_payload.get("nonterminal_target_count", 0) or 0),
    )


def run_live_suite(base_url: str, *, timeout_seconds: int) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []

    scenarios = [
        ("first_import", _annual_payload(run_mode="one_shot_import")),
        ("recurring_sync", _annual_payload(run_mode="recurring_sync")),
        ("budget_cap", {**_annual_payload(run_mode="one_shot_import"), "max_run_bytes": 50000, "max_file_bytes": 2048}),
    ]
    for idx, (name, payload) in enumerate(scenarios, start=1):
        results.append(_run_standard_scenario(base_url, name=name, payload=payload, timeout_seconds=timeout_seconds, idx=idx))
    results.append(_run_cancel_resume_scenario(base_url, timeout_seconds=timeout_seconds, idx=len(scenarios) + 1))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live-only ScienceBase annual MCS pilot validation scenarios.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the running API service.")
    parser.add_argument("--timeout-seconds", type=int, default=600, help="Per-run terminal wait timeout.")
    parser.add_argument("--consecutive-runs", type=int, default=3, help="How many full suites to execute for pilot gate.")
    parser.add_argument("--output-json", default=None, help="Optional path to persist the final validator JSON output.")
    parser.add_argument("--output-ndjson", default=None, help="Optional path to append one NDJSON line per suite cycle.")
    args = parser.parse_args()

    all_results: list[dict[str, Any]] = []
    failed_cycles = 0
    saw_conditional_noop = False
    for cycle in range(1, args.consecutive_runs + 1):
        suite = run_live_suite(args.base_url, timeout_seconds=args.timeout_seconds)
        cycle_payload = {
            "cycle": cycle,
            "results": [result.__dict__ for result in suite],
        }
        all_results.append(cycle_payload)
        if args.output_ndjson:
            _append_ndjson(args.output_ndjson, cycle_payload)
        saw_conditional_noop = saw_conditional_noop or any(result.conditional_noop_seen for result in suite)
        if not all(result.ok for result in suite):
            failed_cycles += 1

    missing_conditional_noop_gate = not saw_conditional_noop
    failed_gate_checks = failed_cycles + (1 if missing_conditional_noop_gate else 0)

    output = {
        "base_url": args.base_url,
        "consecutive_runs": args.consecutive_runs,
        "required_conditional_noop_seen": True,
        "conditional_noop_seen": saw_conditional_noop,
        "failed_cycles": failed_cycles,
        "failed_gate_checks": failed_gate_checks,
        "missing_conditional_noop_gate": missing_conditional_noop_gate,
        "cycles": all_results,
    }
    if args.output_json:
        _write_json_atomic(args.output_json, output)
    print(json.dumps(output, indent=2))
    return 1 if failed_gate_checks > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
