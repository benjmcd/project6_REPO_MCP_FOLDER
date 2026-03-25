from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.services import nrc_aps_safeguards  # noqa: E402
from app.services import nrc_aps_sync_drift  # noqa: E402


LIVE_VALIDATION_SCHEMA_ID = "aps.live_validation_report.v1"
LIVE_VALIDATION_SCHEMA_VERSION = 1
LIVE_VALIDATOR_VERSION = "nrc_aps_live_validation_v3"

V1_STATUS_OBSERVED = "observed"
V1_STATUS_SKIPPED = "skipped"
V1_STATUS_ERROR = "error"
V1_STATUS_VALUES = {V1_STATUS_OBSERVED, V1_STATUS_SKIPPED, V1_STATUS_ERROR}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json_hash(payload: dict[str, Any]) -> str:
    stable = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _safe_json(response: requests.Response) -> tuple[dict[str, Any] | None, str]:
    text = response.text or ""
    if not text.strip():
        return None, "empty_body"
    try:
        payload = response.json()
    except ValueError:
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "non_dict_json"
    return payload, "ok"


def _event_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in events:
        event_type = str(item.get("event_type") or "unknown")
        counts[event_type] = int(counts.get(event_type, 0)) + 1
    return counts


class LiveValidationHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        subscription_key: str,
        timeout_seconds: int,
        max_rps: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.subscription_key = subscription_key
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.subscription_key_hash = hashlib.sha256(subscription_key.encode("utf-8")).hexdigest()
        self.api_host = self.base_url.split("://", 1)[-1].split("/", 1)[0].lower()
        self.limiter_bucket_key = f"{self.subscription_key_hash}:{self.api_host}"
        policy_config = {
            "request_timeout_seconds": self.timeout_seconds,
            "connect_timeout_seconds": max(5.0, min(15.0, float(self.timeout_seconds))),
            "read_timeout_seconds": float(self.timeout_seconds),
            "overall_deadline_seconds": max(float(self.timeout_seconds) + 20.0, 45.0),
            "max_rps": max(0.1, float(max_rps)),
            "runtime_process_count": 1,
            "unsafe_allow_multi_process_limiter": False,
        }
        self._policy, self._lint = nrc_aps_safeguards.ApsSafeguardPolicyLoader.load_from_config(
            policy_config,
            max_concurrent_runs=1,
        )
        blocking_errors = [dict(item or {}) for item in (self._lint.get("blocking_errors") or [])]
        if blocking_errors:
            codes = [str(item.get("code") or "unknown") for item in blocking_errors]
            raise RuntimeError(f"live_validation_safeguard_lint_blocked:{','.join(codes)}")
        self._timeouts = nrc_aps_safeguards.ApsTimeoutNormalizer.normalize(
            config={},
            policy=self._policy,
        )
        self.recorder = nrc_aps_safeguards.ApsSafeguardRecorder()
        self.executor = nrc_aps_safeguards.ApsRequestExecutor(
            policy=self._policy,
            limiter=nrc_aps_safeguards.APS_LIMITER,
            recorder=self.recorder,
        )

    @property
    def safeguard_policy(self) -> dict[str, Any]:
        return dict(self._policy)

    @property
    def safeguard_lint(self) -> dict[str, Any]:
        return dict(self._lint)

    def request(
        self,
        *,
        method: str,
        url: str,
        call_class: str,
        headers: dict[str, str],
        json_payload: dict[str, Any] | None = None,
        stream: bool = False,
        explicit_scope: str | None = None,
    ) -> requests.Response:
        connect_timeout, read_timeout, _ = self._timeouts

        def _send() -> requests.Response:
            return requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_payload,
                stream=stream,
                allow_redirects=True,
                timeout=(connect_timeout, read_timeout),
            )

        return self.executor.execute(
            method=method,
            url=url,
            call_class=call_class,
            bucket_key=self.limiter_bucket_key,
            request_callable=_send,
            json_body=json_payload,
            explicit_scope=explicit_scope,
        )


def _post_search(
    *,
    client: LiveValidationHttpClient,
    payload: dict[str, Any],
    explicit_scope: str | None = None,
) -> dict[str, Any]:
    url = f"{client.base_url.rstrip('/')}/aps/api/search"
    started = time.perf_counter()
    payload_hash = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    response = client.request(
        method="POST",
        url=url,
        call_class="search",
        headers={
            "Ocp-Apim-Subscription-Key": client.subscription_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json_payload=payload,
        explicit_scope=explicit_scope or f"live_validation_search:{payload_hash}",
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    parsed, parse_status = _safe_json(response)
    count_returned = 0
    first_hit: dict[str, Any] | None = None
    if isinstance(parsed, dict):
        rows: list[Any] = []
        for key_name in ("results", "Results", "documents", "Documents"):
            if isinstance(parsed.get(key_name), list):
                rows = list(parsed.get(key_name) or [])
                break
        count_returned = len(rows)
        if rows and isinstance(rows[0], dict):
            first_hit = rows[0]

    return {
        "status_code": int(response.status_code),
        "elapsed_ms": elapsed_ms,
        "ok": int(response.status_code) < 400,
        "parse_status": parse_status,
        "body_bytes": len(response.content or b""),
        "root_keys": sorted(list(parsed.keys())) if isinstance(parsed, dict) else [],
        "count_returned": count_returned,
        "count_value": parsed.get("count") if isinstance(parsed, dict) else None,
        "total_value": parsed.get("total") if isinstance(parsed, dict) else None,
        "response_preview": (response.text or "")[:500],
        "first_hit": first_hit,
        "payload_sent": payload,
    }


def _extract_first_document(hit: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(hit, dict):
        return {}
    if isinstance(hit.get("document"), dict):
        return dict(hit.get("document") or {})
    return dict(hit)


def _base_shape_a_query() -> dict[str, Any]:
    return {
        "q": "safety valve",
        "filters": [],
        "anyFilters": [],
        "mainLibFilter": True,
        "legacyLibFilter": False,
        "sort": "DateAddedTimestamp",
        "sortDirection": 1,
        "skip": 0,
    }


def run_v1_qps_ramp(client: LiveValidationHttpClient, *, mode: str) -> dict[str, Any]:
    normalized_mode = str(mode or "observe").strip().lower()
    if normalized_mode == "skip":
        return {
            "status": V1_STATUS_SKIPPED,
            "skip_reason_code": "v1_disabled_by_operator_mode",
            "levels": [],
            "first_failure_rps": None,
            "recommended_max_rps": None,
        }

    levels = [1, 2, 3, 4, 5, 6, 8, 10]
    observations: list[dict[str, Any]] = []
    first_failure_rps: int | None = None
    try:
        for rps in levels:
            failures = 0
            statuses: list[int] = []
            for attempt_index in range(rps):
                result = _post_search(
                    client=client,
                    payload={**_base_shape_a_query(), "take": 1},
                    explicit_scope=f"live_validation_v1_rps:{rps}:attempt:{attempt_index + 1}",
                )
                status = int(result.get("status_code") or 0)
                statuses.append(status)
                if status >= 400:
                    failures += 1
                time.sleep(max(0.0, 1.0 / max(1, rps)))
            observations.append({"rps": rps, "statuses": statuses, "failures": failures})
            if failures > 0 and first_failure_rps is None:
                first_failure_rps = rps
                break
        recommended_cap = 5
        if first_failure_rps is not None:
            recommended_cap = max(1, int(first_failure_rps * 0.8))
        return {
            "status": V1_STATUS_OBSERVED,
            "levels": observations,
            "first_failure_rps": first_failure_rps,
            "recommended_max_rps": recommended_cap,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": V1_STATUS_ERROR,
            "error_code": "v1_probe_execution_error",
            "error_class": exc.__class__.__name__,
            "error_message": str(exc),
            "levels": observations,
            "first_failure_rps": first_failure_rps,
            "recommended_max_rps": None,
        }


def run_v2(client: LiveValidationHttpClient) -> dict[str, Any]:
    guide_native = {
        "skip": 0,
        "sort": "DateAddedTimestamp",
        "sortDirection": 1,
        "searchCriteria": {
            "q": "safety valve",
            "mainLibFilter": True,
            "legacyLibFilter": False,
            "properties": [],
        },
    }
    shape_a = _base_shape_a_query()
    shape_b = {
        "queryString": "safety valve",
        "docketNumber": "05000275,05000323",
        "filters": [{"name": "DocumentType", "operator": "contains", "value": "Letter"}],
        "sort": "+DateAddedTimestamp",
        "skip": 0,
    }
    return {
        "guide_native": _post_search(client=client, payload=guide_native),
        "shape_a_q_filters": _post_search(client=client, payload=shape_a),
        "shape_b_queryString_docket": _post_search(client=client, payload=shape_b),
    }


def run_v3(v2_results: dict[str, Any]) -> dict[str, Any]:
    preferred_order = ["shape_a_q_filters", "guide_native", "shape_b_queryString_docket"]
    selected_name = None
    selected: dict[str, Any] | None = None
    for name in preferred_order:
        result = v2_results.get(name) if isinstance(v2_results.get(name), dict) else {}
        if bool(result.get("ok")):
            selected_name = name
            selected = result
            break

    if not selected:
        return {"selected_case": None, "status": "no_successful_shape", "envelope_variant": None}

    root_keys = [str(x) for x in selected.get("root_keys") or []]
    if "results" in root_keys or "Results" in root_keys:
        envelope_variant = "results"
    elif "documents" in root_keys or "Documents" in root_keys:
        envelope_variant = "documents"
    else:
        envelope_variant = "unknown"

    return {
        "selected_case": selected_name,
        "status": "observed",
        "envelope_variant": envelope_variant,
        "root_keys": root_keys,
        "count_value": selected.get("count_value"),
        "total_value": selected.get("total_value"),
        "count_returned": selected.get("count_returned"),
    }


def run_v5(client: LiveValidationHttpClient) -> dict[str, Any]:
    with_document_date = {
        **_base_shape_a_query(),
        "filters": [{"field": "DocumentDate", "value": "(DocumentDate ge '2024-01-01')"}],
    }
    with_date_added_timestamp = {
        **_base_shape_a_query(),
        "filters": [{"field": "DateAddedTimestamp", "value": "(DateAddedTimestamp ge '2024-01-01')"}],
    }
    return {
        "document_date_ge": _post_search(client=client, payload=with_document_date),
        "date_added_timestamp_ge": _post_search(client=client, payload=with_date_added_timestamp),
    }


def run_v6(client: LiveValidationHttpClient, max_pages: int, take: int) -> dict[str, Any]:
    page_records: list[dict[str, Any]] = []
    skip = 0
    stop_reason = "max_pages_reached"
    for page_index in range(max_pages):
        payload = {**_base_shape_a_query(), "skip": skip, "take": take}
        result = _post_search(client=client, payload=payload)
        page_records.append(
            {
                "page_index": page_index,
                "skip": skip,
                "status_code": result.get("status_code"),
                "ok": result.get("ok"),
                "count_returned": result.get("count_returned"),
                "count_value": result.get("count_value"),
            }
        )
        if not bool(result.get("ok")):
            stop_reason = "http_error"
            break
        count_returned = int(result.get("count_returned") or 0)
        if count_returned == 0:
            stop_reason = "empty_results"
            break
        skip += take
    return {"pages": page_records, "stop_reason": stop_reason}


def run_v7(client: LiveValidationHttpClient) -> dict[str, Any]:
    with_content = {**_base_shape_a_query(), "content": True, "take": 20}
    without_content = {**_base_shape_a_query(), "content": False, "take": 20}
    on = _post_search(client=client, payload=with_content)
    off = _post_search(client=client, payload=without_content)

    def _content_presence(result: dict[str, Any]) -> dict[str, Any]:
        doc = _extract_first_document(result.get("first_hit"))
        return {
            "content_key_present": "content" in doc,
            "content_non_null": doc.get("content") is not None if "content" in doc else False,
        }

    return {
        "content_true": {**on, **_content_presence(on)},
        "content_false": {**off, **_content_presence(off)},
    }


def run_v8(client: LiveValidationHttpClient) -> dict[str, Any]:
    base = _base_shape_a_query()
    variants = {
        "take_omitted": dict(base),
        "take_100": {**base, "take": 100},
        "take_500": {**base, "take": 500},
        "take_1000": {**base, "take": 1000},
    }
    return {
        name: _post_search(client=client, payload=payload)
        for name, payload in variants.items()
    }


def run_v4_url_auth(
    *,
    client: LiveValidationHttpClient,
    first_hit: dict[str, Any] | None,
    max_probe_bytes: int,
) -> dict[str, Any]:
    document = _extract_first_document(first_hit)
    url = str(document.get("Url") or document.get("url") or "").strip()
    accession = str(document.get("AccessionNumber") or document.get("accessionNumber") or "").strip()
    if not url:
        return {"status": "skipped_no_url", "accession_number": accession or None}

    def _probe(headers: dict[str, str]) -> dict[str, Any]:
        started = time.perf_counter()
        response = client.request(
            method="GET",
            url=url,
            call_class="download",
            headers=headers,
            stream=True,
            explicit_scope=f"live_validation_url_probe:{url}:{int('Ocp-Apim-Subscription-Key' in headers)}",
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        sampled = 0
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            sampled += len(chunk)
            if sampled >= max_probe_bytes:
                break
        return {
            "status_code": int(response.status_code),
            "elapsed_ms": elapsed_ms,
            "final_url": str(response.url),
            "redirect_count": len(response.history),
            "content_type": response.headers.get("content-type"),
            "sampled_bytes": sampled,
        }

    no_auth = _probe({"Accept": "*/*"})
    with_auth = _probe({"Accept": "*/*", "Ocp-Apim-Subscription-Key": client.subscription_key})
    auth_required = (
        int(no_auth.get("status_code") or 0) in {401, 403}
        and int(with_auth.get("status_code") or 0) < 400
    )
    return {
        "status": "observed",
        "accession_number": accession or None,
        "url": url,
        "no_auth": no_auth,
        "with_auth": with_auth,
        "auth_required": auth_required,
    }


def _default_output_path() -> Path:
    reports_dir = Path(settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return reports_dir / f"nrc_aps_live_validation_{ts}.json"


def _run_test_probe(
    *,
    name: str,
    fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "error_code": "probe_execution_error",
            "error_class": exc.__class__.__name__,
            "error_message": f"{name}: {exc}",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run live NRC ADAMS APS contract validation probes.")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--pagination-max-pages", type=int, default=5)
    parser.add_argument("--pagination-take", type=int, default=50)
    parser.add_argument("--url-probe-bytes", type=int, default=262144)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--v1-mode", type=str, default="observe", choices=["observe", "skip"])
    parser.add_argument("--max-rps", type=float, default=5.0)
    args = parser.parse_args(argv)

    base_url = settings.nrc_adams_api_base_url.rstrip("/")
    key = settings.nrc_adams_subscription_key
    if not key:
        raise SystemExit("NRC_ADAMS_APS_SUBSCRIPTION_KEY is not configured")

    client = LiveValidationHttpClient(
        base_url=base_url,
        subscription_key=key,
        timeout_seconds=max(5, int(args.timeout_seconds)),
        max_rps=max(0.1, float(args.max_rps)),
    )

    tests: dict[str, Any] = {}
    tests["APS-V1_qps_ramp_test"] = run_v1_qps_ramp(client=client, mode=args.v1_mode)
    tests["APS-V2_request_shape_acceptance"] = _run_test_probe(name="APS-V2", fn=lambda: run_v2(client))
    tests["APS-V3_response_envelope_variant"] = _run_test_probe(
        name="APS-V3",
        fn=lambda: run_v3(dict(tests.get("APS-V2_request_shape_acceptance") or {})),
    )
    tests["APS-V5_date_added_timestamp_filter_syntax"] = _run_test_probe(name="APS-V5", fn=lambda: run_v5(client))
    tests["APS-V6_pagination_stop_condition"] = _run_test_probe(
        name="APS-V6",
        fn=lambda: run_v6(client, int(args.pagination_max_pages), int(args.pagination_take)),
    )
    tests["APS-V7_content_boolean_behavior"] = _run_test_probe(name="APS-V7", fn=lambda: run_v7(client))
    tests["APS-V8_take_page_size_behavior"] = _run_test_probe(name="APS-V8", fn=lambda: run_v8(client))

    v2 = dict(tests.get("APS-V2_request_shape_acceptance") or {})
    first_success = None
    for candidate in ("shape_a_q_filters", "guide_native", "shape_b_queryString_docket"):
        result = v2.get(candidate) if isinstance(v2.get(candidate), dict) else {}
        if bool(result.get("ok")):
            first_success = result
            break
    tests["APS-V4_url_auth_behavior"] = _run_test_probe(
        name="APS-V4",
        fn=lambda: run_v4_url_auth(
            client=client,
            first_hit=(first_success or {}).get("first_hit"),
            max_probe_bytes=max(4096, int(args.url_probe_bytes)),
        ),
    )

    v1_payload = dict(tests.get("APS-V1_qps_ramp_test") or {})
    v1_status = str(v1_payload.get("status") or "").strip().lower()
    if v1_status not in V1_STATUS_VALUES:
        v1_payload = {
            "status": V1_STATUS_ERROR,
            "error_code": "v1_status_invalid",
            "error_message": f"unexpected status value: {v1_status or '<missing>'}",
            "raw_v1_payload": dict(tests.get("APS-V1_qps_ramp_test") or {}),
        }
        tests["APS-V1_qps_ramp_test"] = v1_payload

    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    safeguard_events = client.recorder.events()
    safeguard_policy = dict(client.safeguard_policy)
    safeguard_lint = dict(client.safeguard_lint)
    report = {
        "schema_id": LIVE_VALIDATION_SCHEMA_ID,
        "schema_version": LIVE_VALIDATION_SCHEMA_VERSION,
        "evaluator_version": LIVE_VALIDATOR_VERSION,
        "generated_at_utc": _utc_iso(),
        "api_base_url": base_url,
        "subscription_key_hash": key_hash,
        "collector_provenance": {
            "tool": "tools/run_nrc_aps_live_validation.py",
            "argv": [str(item) for item in (argv if argv is not None else sys.argv[1:])],
            "cwd": str(Path.cwd()),
        },
        "input_config": {
            "timeout_seconds": int(args.timeout_seconds),
            "pagination_max_pages": int(args.pagination_max_pages),
            "pagination_take": int(args.pagination_take),
            "url_probe_bytes": int(args.url_probe_bytes),
            "v1_mode": str(args.v1_mode),
            "max_rps": float(args.max_rps),
        },
        "safeguard": {
            "policy_schema_id": str(safeguard_policy.get("schema_id") or ""),
            "policy_schema_version": int(safeguard_policy.get("schema_version") or 0),
            "policy_hash": _stable_json_hash(safeguard_policy),
            "lint_schema_id": str(safeguard_lint.get("schema_id") or ""),
            "lint_blocking_errors": [dict(item or {}) for item in (safeguard_lint.get("blocking_errors") or [])],
            "lint_warnings": [dict(item or {}) for item in (safeguard_lint.get("warnings") or [])],
            "event_counts": _event_counts(safeguard_events),
        },
        "tests": tests,
    }

    output = Path(args.output) if args.output else _default_output_path()
    nrc_aps_sync_drift.write_json_deterministic(output, report)

    v2_summary = {
        name: (result.get("status_code"), result.get("count_returned"))
        for name, result in v2.items()
        if isinstance(result, dict)
    }
    print("NRC APS live validation complete")
    print(f"base_url={base_url}")
    print(f"v2_statuses={v2_summary}")
    print(f"v1_status={tests['APS-V1_qps_ramp_test'].get('status')}")
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
