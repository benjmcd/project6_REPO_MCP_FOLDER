from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_diagnostic_framework import report_header as _report_header  # noqa: E402


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-live-smoke-report.json")
PREFLIGHT_PATH = ASSESSMENT / "sec-live-preflight.py"

TARGET = "sec_live_source_artifact_operator_smoke_v1"
NEXT_SLICE = "bind_arelle_fact_authority_to_server_owned_live_source_artifact"
PREFLIGHT_READY = "sec_live_source_artifact_smoke_preflight_ready"
DECISION_EXECUTED = "sec_live_source_artifact_smoke_executed"
DECISION_NOT_REQUESTED = "sec_live_source_artifact_smoke_execution_not_requested"
DECISION_BLOCKED = "sec_live_source_artifact_smoke_blocked"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Operator-gated SEC live source-artifact smoke. The default path is a "
            "dry-run report only; --execute-live is required before the diagnostic "
            "may call the existing live acquisition service."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not write a report; print the decision and return the proof exit code.",
    )
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help=(
            "Run the one-filing live source-artifact acquire/status smoke after the "
            "preflight is ready. Without this flag no SEC request or artifact write occurs."
        ),
    )
    args = parser.parse_args(argv)

    report = build_report(source_root=ROOT, execute_live=bool(args.execute_live))
    if args.no_report:
        print("report_write=skipped")
    else:
        output = _resolve_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0 if report["decision"] == DECISION_EXECUTED else 1


def build_report(
    *,
    source_root: Path,
    env: Mapping[str, str] | None = None,
    execute_live: bool = False,
    sec_client: Any | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    current_env = dict(os.environ if env is None else env)
    preflight_module = _preflight_module()
    preflight = preflight_module.build_report(source_root=source_root, env=current_env)
    preflight_ready = preflight.get("decision") == PREFLIGHT_READY
    plan = _execution_plan(preflight_module=preflight_module, preflight=preflight, env=current_env)

    if not preflight_ready or not execute_live:
        criteria = [
            _criterion(
                "operator_preflight_ready",
                preflight_ready,
                _preflight_summary(preflight),
                "sec_live_smoke_preflight_not_ready",
            ),
            _criterion(
                "explicit_live_execution_requested",
                bool(execute_live),
                {"execute_live_requested": bool(execute_live), "default_executes_live": False},
                "sec_live_smoke_execute_live_not_requested",
            ),
        ]
        blockers = [item for item in criteria if item["state"] != "passed"]
        return _report_header(
            schema_id="diagnostics.sec_live_source_artifact_operator_smoke.v1",
            target=TARGET,
            next_slice=TARGET if not preflight_ready else NEXT_SLICE,
            decision=DECISION_BLOCKED if not preflight_ready else DECISION_NOT_REQUESTED,
            headline=_headline(preflight_ready=preflight_ready, executed=False, blockers=blockers),
            criteria=criteria,
            blocking_reasons=blockers,
            preflight=_preflight_summary(preflight),
            execution_plan=plan,
            execution_effects=_execution_effects(network_request_made=False, source_artifact_created=False),
            redaction=_redaction_result(),
            required_next_action=(
                "resolve_preflight_blockers_before_any_live_sec_smoke"
                if not preflight_ready
                else "rerun_with_execute_live_only_after_operator_confirms_the_selected_one_filing_smoke"
            ),
            non_goals_preserved=_non_goals(),
        )

    return _execute_smoke(
        env=current_env,
        preflight_module=preflight_module,
        preflight=preflight,
        plan=plan,
        sec_client=sec_client,
        sleep=sleep,
    )


def _execute_smoke(
    *,
    env: Mapping[str, str],
    preflight_module: Any,
    preflight: Mapping[str, Any],
    plan: Mapping[str, Any],
    sec_client: Any | None,
    sleep: Callable[[float], None] | None,
) -> dict[str, Any]:
    svc = _service_module()
    previous = _capture_runtime(svc)
    request = _request_payload(preflight_module=preflight_module, env=env)
    transport_kind = "fake_client" if sec_client is not None else "live_http"
    acquire: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    try:
        _install_runtime_from_env(svc=svc, preflight_module=preflight_module, env=env)
        if sec_client is not None:
            svc.SEC_EDGAR_CLIENT = sec_client
        if sleep is not None:
            svc.SEC_EDGAR_SLEEP = sleep
        acquire = svc.acquire_sec_edgar_text_table_live_source_artifact(request)
        status = svc.inspect_sec_edgar_text_table_live_source_artifact_status(
            acquire["live_source_artifact_receipt_id"]
        )
    except svc.Layer3WorkbenchError as exc:
        error = {
            "error_code": exc.error_code,
            "http_status": exc.http_status,
            "blocked_fields": list(exc.blocked_fields),
            "recoverable": exc.recoverable,
            "raw_message_returned": False,
        }
    finally:
        _restore_runtime(svc=svc, previous=previous)

    evidence = _operator_evidence(acquire=acquire, status=status, transport_kind=transport_kind)
    execution_effects = _execution_effects(
        network_request_made=bool((acquire or {}).get("cache", {}).get("network_request_made")),
        source_artifact_created=bool(acquire and not error),
        transport_kind=transport_kind,
    )
    redaction = _redaction_result(
        report_parts=[plan, evidence, execution_effects, error or {}],
        preflight_module=preflight_module,
        env=env,
    )
    criteria = [
        _criterion(
            "operator_preflight_ready",
            preflight.get("decision") == PREFLIGHT_READY,
            _preflight_summary(preflight),
            "sec_live_smoke_preflight_not_ready",
        ),
        _criterion(
            "explicit_live_execution_requested",
            True,
            {"execute_live_requested": True, "default_executes_live": False},
            "sec_live_smoke_execute_live_not_requested",
        ),
        _criterion(
            "one_source_artifact_acquire_completed",
            bool(acquire and acquire.get("status") == "available" and not error),
            evidence,
            "sec_live_smoke_acquire_failed",
        ),
        _criterion(
            "status_reread_completed",
            bool(status and status.get("schema_id") == svc.STATUS_SCHEMA_ID),
            evidence,
            "sec_live_smoke_status_reread_failed",
        ),
        _criterion(
            "acquire_performed_exactly_one_network_miss",
            bool(
                acquire
                and acquire.get("cache", {}).get("network_request_made") is True
                and acquire.get("cache", {}).get("cache_status") == "miss"
            ),
            evidence.get("cache", {}),
            "sec_live_smoke_not_a_fresh_network_miss",
        ),
        _criterion(
            "redacted_hash_only_evidence",
            not any(redaction.values()),
            redaction,
            "sec_live_smoke_raw_authority_leak",
        ),
        _criterion(
            "downstream_non_goals_preserved",
            not any(_non_goals().values()),
            _non_goals(),
            "sec_live_smoke_downstream_non_goal_changed",
        ),
    ]
    if error:
        criteria.append(
            _criterion(
                "service_error_absent",
                False,
                error,
                error["error_code"],
            )
        )
    blockers = [item for item in criteria if item["state"] != "passed"]
    executed = not blockers
    return _report_header(
        schema_id="diagnostics.sec_live_source_artifact_operator_smoke.v1",
        target=TARGET,
        next_slice=NEXT_SLICE,
        decision=DECISION_EXECUTED if executed else DECISION_BLOCKED,
        headline=_headline(preflight_ready=True, executed=executed, blockers=blockers),
        criteria=criteria,
        blocking_reasons=blockers,
        preflight=_preflight_summary(preflight),
        execution_plan=plan,
        execution_effects=execution_effects,
        operator_evidence=evidence,
        service_error=error,
        redaction=redaction,
        required_next_action=(
            "bind_arelle_fact_authority_to_server_owned_live_source_artifact"
            if executed
            else "resolve_live_smoke_error_without_advancing_to_arelle_or_downstream_authority"
        ),
        non_goals_preserved=_non_goals(),
    )


def _execution_plan(*, preflight_module: Any, preflight: Mapping[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    request_ready = bool((preflight.get("smoke_request_preflight") or {}).get("request_ready"))
    return {
        "execute_live_default": False,
        "execute_live_flag_required": "--execute-live",
        "acquire_route": preflight_module.ACQUIRE_ROUTE,
        "status_route": preflight_module.STATUS_ROUTE,
        "request_schema_id": "layer3.sec_edgar_text_table_live_source_artifact_acquisition_request.v1",
        "request_fields": [
            "schema_id",
            "client_request_id",
            "acquisition_mode",
            "operator_decision",
            "cik_or_filer_ref",
            "accession_or_submission_id",
            "form_type",
            "filing_date",
            "operator_confirmation",
        ],
        "request_ready": request_ready,
        "source_identity_marker": (preflight.get("smoke_request_preflight") or {}).get("source_identity_marker"),
        "client_request_id_marker": _marker(_client_request_id(preflight=preflight)),
        "raw_request_identity_returned": False,
    }


def _request_payload(*, preflight_module: Any, env: Mapping[str, str]) -> dict[str, Any]:
    return {
        "schema_id": "layer3.sec_edgar_text_table_live_source_artifact_acquisition_request.v1",
        "client_request_id": _client_request_id_from_env(preflight_module=preflight_module, env=env),
        "acquisition_mode": "sec_edgar_text_table_live_source_artifact_acquisition_v1",
        "operator_decision": "acquire_sec_edgar_text_table_live_source_artifact",
        "cik_or_filer_ref": str(env.get(preflight_module.SMOKE_CIK_ENV) or "").strip(),
        "accession_or_submission_id": str(env.get(preflight_module.SMOKE_ACCESSION_ENV) or "").strip(),
        "form_type": str(env.get(preflight_module.SMOKE_FORM_ENV) or "").strip().upper(),
        "filing_date": str(env.get(preflight_module.SMOKE_DATE_ENV) or "").strip(),
        "operator_confirmation": True,
    }


def _operator_evidence(
    *,
    acquire: Mapping[str, Any] | None,
    status: Mapping[str, Any] | None,
    transport_kind: str,
) -> dict[str, Any]:
    if not acquire:
        return {"transport_kind": transport_kind, "acquire_returned": False}
    source_receipt = acquire.get("source_artifact_receipt") or {}
    manifest = acquire.get("retained_source_artifact_manifest") or {}
    status_payload = dict(status or {})
    return {
        "transport_kind": transport_kind,
        "acquire_returned": True,
        "status_returned": bool(status),
        "live_source_artifact_receipt_id": acquire.get("live_source_artifact_receipt_id"),
        "live_source_artifact_receipt_hash": acquire.get("live_source_artifact_receipt_hash"),
        "source_artifact_receipt_id": source_receipt.get("source_artifact_receipt_id"),
        "source_artifact_receipt_hash": source_receipt.get("source_artifact_receipt_hash"),
        "source_artifact_ref_hash": source_receipt.get("source_artifact_ref_hash"),
        "content_sha256": source_receipt.get("content_sha256"),
        "content_length": source_receipt.get("content_length"),
        "source_identity_hash": (acquire.get("source_identity") or {}).get("source_identity_hash"),
        "server_derived_url_hash": (acquire.get("sec_request_policy") or {}).get("server_derived_url_hash"),
        "user_agent_hash": (acquire.get("sec_request_policy") or {}).get("server_configured_user_agent_hash"),
        "retained_source_artifact_available": manifest.get("retained_source_artifact_available"),
        "cache": dict(acquire.get("cache") or {}),
        "idempotency": dict(acquire.get("idempotency") or {}),
        "status_schema_id": status_payload.get("schema_id"),
        "status_response_hash": _stable_hash(status_payload) if status else None,
        "acquire_response_hash": _stable_hash(dict(acquire)),
        "raw_sec_url_returned": False,
        "raw_storage_path_returned": False,
        "raw_user_agent_returned": False,
        "artifact_bytes_returned": False,
    }


def _preflight_summary(preflight: Mapping[str, Any]) -> dict[str, Any]:
    blockers = [str(item.get("blocked_reason") or "") for item in preflight.get("blocking_reasons", [])]
    return {
        "decision": preflight.get("decision"),
        "blocking_reasons": blockers,
        "ready": preflight.get("decision") == PREFLIGHT_READY,
        "source_identity_marker": (preflight.get("smoke_request_preflight") or {}).get("source_identity_marker"),
        "raw_identity_returned": False,
        "raw_user_agent_returned": False,
        "raw_storage_path_returned": False,
    }


def _execution_effects(
    *,
    network_request_made: bool,
    source_artifact_created: bool,
    transport_kind: str = "none",
) -> dict[str, Any]:
    return {
        "transport_kind": transport_kind,
        "network_request_made": bool(network_request_made),
        "real_sec_network_request_performed": bool(network_request_made and transport_kind == "live_http"),
        "source_artifact_or_receipt_created": bool(source_artifact_created),
        "status_reread_performed": bool(source_artifact_created),
        "arelle_subprocess_invoked": False,
        "multi_filing_enforcement_exercised": False,
        "delivery_export_status_exercised": False,
        "value_reveal_exercised": False,
        "default_on_graduation_claimed": False,
    }


def _redaction_result(
    report_parts: list[Any] | None = None,
    preflight_module: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    serialized = json.dumps(report_parts or [], sort_keys=True)
    forbidden: list[str] = []
    if preflight_module is not None and env is not None:
        raw_cik = str(env.get(preflight_module.SMOKE_CIK_ENV) or "").strip()
        normalized_cik = raw_cik.lstrip("0") or ("0" if raw_cik else "")
        accession = str(env.get(preflight_module.SMOKE_ACCESSION_ENV) or "").strip()
        user_agent = str(env.get(preflight_module.USER_AGENT_ENV) or "").strip()
        storage = str(env.get(preflight_module.STORAGE_ENV) or "").strip()
        url = ""
        if normalized_cik and accession:
            url = f"https://www.sec.gov/Archives/edgar/data/{normalized_cik}/{accession.replace('-', '')}/{accession}.txt"
        forbidden = [raw_cik, normalized_cik, accession, user_agent, storage, url]
    return {
        "raw_cik_returned": _contains_any(serialized, forbidden[:2]),
        "raw_accession_returned": _contains_any(serialized, forbidden[2:3]),
        "raw_user_agent_returned": _contains_any(serialized, forbidden[3:4]),
        "raw_storage_path_returned": _contains_any(serialized, forbidden[4:5]),
        "raw_sec_url_returned": _contains_any(serialized, forbidden[5:6]),
        "artifact_bytes_returned": False,
    }


def _non_goals() -> dict[str, bool]:
    return {
        "arelle_subprocess_invoked": False,
        "multi_filing_enforcement_exercised": False,
        "delivery_export_status_exercised": False,
        "provider_delivery_exercised": False,
        "nonlocal_auth_hardening_changed": False,
        "value_reveal_exercised": False,
        "default_on_graduation_claimed": False,
        "config_default_changed": False,
        "support_matrix_changed": False,
        "redaction_posture_changed": False,
        "production_readiness_claimed": False,
    }


def _install_runtime_from_env(*, svc: Any, preflight_module: Any, env: Mapping[str, str]) -> None:
    storage = preflight_module._normalise_storage_dir(  # noqa: SLF001 - diagnostic must mirror runtime normalization.
        ROOT,
        str(env.get(preflight_module.STORAGE_ENV) or ""),
    )
    setattr(svc.settings, "storage_dir", str(storage))
    setattr(
        svc.settings,
        "layer3_sec_edgar_live_network_enabled",
        _truthy(str(env.get(preflight_module.LIVE_ENABLED_ENV) or "")),
    )
    setattr(svc.settings, "layer3_sec_edgar_user_agent", str(env.get(preflight_module.USER_AGENT_ENV) or "").strip())
    setattr(
        svc.settings,
        "layer3_sec_edgar_rate_limit_per_second",
        int(str(env.get(preflight_module.RATE_ENV) or "1").strip()),
    )
    setattr(
        svc.settings,
        "layer3_sec_edgar_max_live_requests_per_process",
        int(str(env.get(preflight_module.MAX_REQUESTS_ENV) or "10").strip()),
    )
    setattr(svc.settings, "layer3_sec_edgar_max_bytes", int(str(env.get(preflight_module.MAX_BYTES_ENV) or "0").strip()))
    setattr(
        svc.settings,
        "layer3_sec_edgar_timeout_seconds",
        int(str(env.get(preflight_module.TIMEOUT_ENV) or "0").strip()),
    )


def _capture_runtime(svc: Any) -> dict[str, Any]:
    setting_names = [
        "storage_dir",
        "layer3_sec_edgar_live_network_enabled",
        "layer3_sec_edgar_user_agent",
        "layer3_sec_edgar_rate_limit_per_second",
        "layer3_sec_edgar_max_live_requests_per_process",
        "layer3_sec_edgar_max_bytes",
        "layer3_sec_edgar_timeout_seconds",
    ]
    with svc._SEC_LIVE_REQUEST_COUNT_LOCK:  # noqa: SLF001 - restore diagnostic process state.
        request_count = svc._SEC_LIVE_REQUEST_COUNT  # noqa: SLF001
    return {
        "settings": {name: getattr(svc.settings, name) for name in setting_names},
        "client": svc.SEC_EDGAR_CLIENT,
        "sleep": svc.SEC_EDGAR_SLEEP,
        "request_count": request_count,
    }


def _restore_runtime(*, svc: Any, previous: Mapping[str, Any]) -> None:
    for name, value in dict(previous["settings"]).items():
        setattr(svc.settings, name, value)
    svc.SEC_EDGAR_CLIENT = previous["client"]
    svc.SEC_EDGAR_SLEEP = previous["sleep"]
    with svc._SEC_LIVE_REQUEST_COUNT_LOCK:  # noqa: SLF001 - restore diagnostic process state.
        svc._SEC_LIVE_REQUEST_COUNT = int(previous["request_count"])  # noqa: SLF001


def _preflight_module() -> Any:
    spec = importlib.util.spec_from_file_location("sec_live_preflight", PREFLIGHT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load preflight module from {PREFLIGHT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _service_module() -> Any:
    from app.services import layer3_sec_edgar_live_source_artifact as svc

    return svc


def _client_request_id(*, preflight: Mapping[str, Any]) -> str:
    marker = str((preflight.get("smoke_request_preflight") or {}).get("source_identity_marker") or "missing")
    return f"sec-live-source-artifact-smoke-{marker}"


def _client_request_id_from_env(*, preflight_module: Any, env: Mapping[str, str]) -> str:
    cik = str(env.get(preflight_module.SMOKE_CIK_ENV) or "").strip().lstrip("0") or "0"
    accession = str(env.get(preflight_module.SMOKE_ACCESSION_ENV) or "").strip()
    form = str(env.get(preflight_module.SMOKE_FORM_ENV) or "").strip().upper()
    filing_date = str(env.get(preflight_module.SMOKE_DATE_ENV) or "").strip()
    source_identity_hash = preflight_module._source_identity_hash(  # noqa: SLF001 - use the preflight authority hash.
        cik=cik,
        accession=accession,
        form=form,
        filing_date=filing_date,
    )
    return f"sec-live-source-artifact-smoke-{source_identity_hash[:16]}"


def _headline(*, preflight_ready: bool, executed: bool, blockers: list[dict[str, Any]]) -> str:
    if executed:
        return "One-filing SEC live source-artifact smoke executed with redacted/hash-only evidence."
    if not preflight_ready:
        return "SEC live source-artifact smoke is blocked before execution by the preflight."
    reasons = ", ".join(str(item.get("blocked_reason") or "") for item in blockers)
    return f"SEC live source-artifact smoke is ready but not executed: {reasons}."


def _contains_any(value: str, needles: list[str]) -> bool:
    return any(bool(needle) and needle in value for needle in needles)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _marker(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _stable_hash(value: Any) -> str:
    import hashlib

    stable_json = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
