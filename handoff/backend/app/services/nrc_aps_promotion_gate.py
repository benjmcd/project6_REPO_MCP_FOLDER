from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import nrc_aps_live_batch
from app.services import nrc_aps_sync_drift


PROMOTION_POLICY_SCHEMA_ID = "aps.promotion_policy.v1"
PROMOTION_REPORT_SCHEMA_ID = "aps.promotion_governance.v2"
PROMOTION_REPORT_SCHEMA_VERSION = 1
PROMOTION_EVALUATOR_VERSION = "nrc_aps_promotion_gate_v2"

DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "nrc_adams_resources" / "aps_promotion_policy_v1.json"
DEFAULT_REPORT_DIR = Path("tests/reports")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
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


def _status_class(status_code: Any) -> str:
    code = _safe_int(status_code, 0)
    if code <= 0:
        return "unknown"
    if 200 <= code <= 299:
        return "2xx"
    if 300 <= code <= 399:
        return "3xx"
    if 400 <= code <= 499:
        return "4xx"
    if 500 <= code <= 599:
        return "5xx"
    return "other"


def _parse_iso_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _json_sha256(payload: dict[str, Any]) -> str:
    stable = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _failure(code: str, message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": str(code),
        "message": str(message),
        "context": dict(context or {}),
    }


def _default_report_path(batch_manifest_path: Path, manifest_payload: dict[str, Any]) -> Path:
    batch_id = str(manifest_payload.get("batch_id") or batch_manifest_path.stem).strip() or batch_manifest_path.stem
    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_REPORT_DIR / f"{batch_id}_aps_promotion_eval_v1.json"


def _resolve_report_ref(batch_manifest_path: Path, raw_ref: Any) -> Path:
    report_ref = str(raw_ref or "").strip()
    if not report_ref:
        return Path("")
    direct = Path(report_ref)
    if direct.is_absolute():
        return direct
    return (batch_manifest_path.parent / direct).resolve()


def _normalize_policy(policy_payload: dict[str, Any]) -> dict[str, Any]:
    batch_rules = dict(policy_payload.get("batch_rules") or {})
    expected_v2 = dict(policy_payload.get("expected_v2") or {})
    allowed_envelope_variants = [
        str(item).strip().lower()
        for item in (policy_payload.get("allowed_envelope_variants") or [])
        if str(item).strip()
    ]
    return {
        "schema_id": str(policy_payload.get("schema_id") or ""),
        "schema_version": _safe_int(policy_payload.get("schema_version"), 0),
        "window_days": max(1, _safe_int(policy_payload.get("window_days"), 7)),
        "min_reports_in_window": max(1, _safe_int(policy_payload.get("min_reports_in_window"), 3)),
        "min_pass_rate": min(1.0, max(0.0, _safe_float(policy_payload.get("min_pass_rate"), 0.8))),
        "latest_report_max_age_hours": max(1, _safe_int(policy_payload.get("latest_report_max_age_hours"), 36)),
        "require_latest_report_pass": _safe_bool(policy_payload.get("require_latest_report_pass"), True),
        "require_v1_ramp": _safe_bool(policy_payload.get("require_v1_ramp"), True),
        "allow_missing_v1": _safe_bool(policy_payload.get("allow_missing_v1"), False),
        "allow_v1_skipped": _safe_bool(policy_payload.get("allow_v1_skipped"), False),
        "min_v1_recommended_rps": max(1, _safe_int(policy_payload.get("min_v1_recommended_rps"), 5)),
        "expected_v2": {
            "shape_a_status_class": str(expected_v2.get("shape_a_status_class") or "2xx").strip().lower(),
            "guide_native_status_class_any_of": [
                str(item).strip().lower()
                for item in (expected_v2.get("guide_native_status_class_any_of") or [])
                if str(item).strip()
            ],
            "shape_b_status_class_any_of": [
                str(item).strip().lower()
                for item in (expected_v2.get("shape_b_status_class_any_of") or [])
                if str(item).strip()
            ],
        },
        "allowed_envelope_variants": allowed_envelope_variants or ["results", "documents"],
        "require_v5_date_added_success": _safe_bool(policy_payload.get("require_v5_date_added_success"), True),
        "take_effective_cap_max": max(1, _safe_int(policy_payload.get("take_effective_cap_max"), 100)),
        "batch_rules": {
            "min_completed_cycles": max(
                1,
                _safe_int(batch_rules.get("min_completed_cycles"), _safe_int(policy_payload.get("min_reports_in_window"), 3)),
            ),
            "max_batch_age_spread_hours": max(0.0, _safe_float(batch_rules.get("max_batch_age_spread_hours"), 24.0)),
            "allow_partial_failure_cycles": _safe_bool(batch_rules.get("allow_partial_failure_cycles"), True),
            "exclude_failed_cycles_from_evaluation": _safe_bool(batch_rules.get("exclude_failed_cycles_from_evaluation"), True),
            "require_all_planned_cycles_attempted": _safe_bool(batch_rules.get("require_all_planned_cycles_attempted"), True),
        },
    }


def load_promotion_policy(policy_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(policy_path) if policy_path else DEFAULT_POLICY_PATH
    payload = _load_json(path)
    schema_id = str(payload.get("schema_id") or "").strip()
    schema_version = _safe_int(payload.get("schema_version"), 0)
    if schema_id != PROMOTION_POLICY_SCHEMA_ID:
        raise ValueError(f"Invalid promotion policy schema_id: {schema_id}")
    if schema_version != 1:
        raise ValueError(f"Unsupported promotion policy schema_version: {schema_version}")
    normalized = _normalize_policy(payload)
    normalized["policy_path"] = str(path.resolve())
    normalized["policy_sha256"] = _json_sha256(payload)
    normalized["raw_policy"] = payload
    return normalized


def _extract_report_evidence(
    *,
    path: Path,
    payload: dict[str, Any],
    policy: dict[str, Any],
    cycle_index: int,
) -> dict[str, Any]:
    tests = dict(payload.get("tests") or {})
    v1_key_present = "APS-V1_qps_ramp_test" in tests
    v1 = dict(tests.get("APS-V1_qps_ramp_test") or {})
    v2 = dict(tests.get("APS-V2_request_shape_acceptance") or {})
    v3 = dict(tests.get("APS-V3_response_envelope_variant") or {})
    v5 = dict(tests.get("APS-V5_date_added_timestamp_filter_syntax") or {})
    v8 = dict(tests.get("APS-V8_take_page_size_behavior") or {})

    shape_a = dict(v2.get("shape_a_q_filters") or {})
    guide_native = dict(v2.get("guide_native") or {})
    shape_b = dict(v2.get("shape_b_queryString_docket") or v2.get("shape_b") or {})
    date_added = dict(v5.get("date_added_timestamp_ge") or {})
    take_1000 = dict(v8.get("take_1000") or {})
    generated_at = _parse_iso_datetime(payload.get("generated_at_utc"))

    evidence = {
        "cycle_index": cycle_index,
        "path": str(path),
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z") if generated_at else None,
        "shape_a_status_class": _status_class(shape_a.get("status_code")),
        "guide_native_status_class": _status_class(guide_native.get("status_code")),
        "shape_b_status_class": _status_class(shape_b.get("status_code")),
        "envelope_variant": str(v3.get("envelope_variant") or "").strip().lower() or None,
        "date_added_success": bool(date_added.get("ok")),
        "take_1000_count_returned": _safe_int(take_1000.get("count_returned"), -1),
        "v1_key_present": bool(v1_key_present),
        "v1_status": str(v1.get("status") or "").strip().lower() if v1 else None,
        "v1_recommended_max_rps": _safe_int(v1.get("recommended_max_rps"), 0) if v1 else None,
        "v1_first_failure_rps": _safe_int(v1.get("first_failure_rps"), 0) if v1 else None,
    }

    expected_v2 = dict(policy.get("expected_v2") or {})
    allowed_envelope = [str(item).strip().lower() for item in (policy.get("allowed_envelope_variants") or []) if str(item).strip()]
    take_cap = _safe_int(policy.get("take_effective_cap_max"), 100)
    min_v1_rps = _safe_int(policy.get("min_v1_recommended_rps"), 5)
    require_v1 = bool(policy.get("require_v1_ramp", True))
    allow_missing_v1 = bool(policy.get("allow_missing_v1", False))
    allow_v1_skipped = bool(policy.get("allow_v1_skipped", False))
    require_v5 = bool(policy.get("require_v5_date_added_success", True))

    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if evidence["shape_a_status_class"] != str(expected_v2.get("shape_a_status_class") or "2xx"):
        failures.append(_failure("shape_a_status_class_mismatch", "shape_a status class mismatch"))

    guide_allowed = [str(item).strip().lower() for item in (expected_v2.get("guide_native_status_class_any_of") or []) if str(item).strip()]
    if guide_allowed and str(evidence["guide_native_status_class"]).lower() not in guide_allowed:
        failures.append(_failure("guide_native_status_class_mismatch", "guide_native status class mismatch"))

    shape_b_allowed = [str(item).strip().lower() for item in (expected_v2.get("shape_b_status_class_any_of") or []) if str(item).strip()]
    if shape_b_allowed and str(evidence["shape_b_status_class"]).lower() not in shape_b_allowed:
        failures.append(_failure("shape_b_status_class_mismatch", "shape_b status class mismatch"))

    if allowed_envelope and str(evidence["envelope_variant"] or "").lower() not in allowed_envelope:
        failures.append(_failure("envelope_variant_mismatch", "envelope variant mismatch"))

    if require_v5 and not bool(evidence["date_added_success"]):
        failures.append(_failure("date_added_filter_failed", "DateAddedTimestamp ge behavior failed"))

    if evidence["take_1000_count_returned"] >= 0 and evidence["take_1000_count_returned"] > take_cap:
        failures.append(_failure("take_effective_cap_exceeded", "observed take_1000 exceeded effective cap"))

    if require_v1:
        if not evidence["v1_key_present"]:
            if not allow_missing_v1:
                failures.append(_failure("v1_missing_not_allowed", "APS-V1 key is missing and policy disallows missing V1"))
        else:
            v1_status = str(evidence.get("v1_status") or "").strip().lower()
            if v1_status == "observed":
                if _safe_int(evidence["v1_recommended_max_rps"], 0) < min_v1_rps:
                    failures.append(_failure("v1_recommended_rps_below_floor", "V1 recommended max rps below policy floor"))
            elif v1_status == "skipped":
                if allow_v1_skipped:
                    warnings.append(_failure("v1_skipped_allowed", "V1 status skipped accepted by policy"))
                else:
                    failures.append(_failure("v1_skipped_not_allowed", "V1 status skipped is not promotable under current policy"))
            elif v1_status == "error":
                failures.append(_failure("v1_status_error", "V1 probe returned error status"))
            else:
                failures.append(_failure("v1_status_invalid", "V1 status is invalid or missing"))
    else:
        if evidence["v1_key_present"] and str(evidence.get("v1_status") or "").strip().lower() == "error":
            warnings.append(_failure("v1_status_error_ignored", "V1 probe error ignored because require_v1_ramp=false"))

    evidence["passed"] = len(failures) == 0
    evidence["failures"] = failures
    evidence["warnings"] = warnings
    return evidence


def _load_cycle_rows(
    *,
    batch_manifest_path: Path,
    manifest_payload: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    cycles = [dict(item or {}) for item in (manifest_payload.get("cycle_reports") or []) if isinstance(item, dict)]
    if not cycles:
        failures.append(_failure("batch_manifest_cycle_reports_missing", "cycle_reports must be a non-empty list"))
        return rows, failures, warnings

    seen_indexes: set[int] = set()
    for cycle in sorted(cycles, key=lambda item: _safe_int(item.get("cycle_index"), 0)):
        cycle_index = _safe_int(cycle.get("cycle_index"), 0)
        if cycle_index <= 0:
            failures.append(_failure("batch_manifest_cycle_index_invalid", "cycle_index must be a positive integer", context={"cycle": cycle}))
            continue
        if cycle_index in seen_indexes:
            failures.append(_failure("batch_manifest_cycle_index_duplicate", "duplicate cycle_index detected", context={"cycle_index": cycle_index}))
            continue
        seen_indexes.add(cycle_index)
        status = str(cycle.get("status") or "").strip().lower()
        row: dict[str, Any] = {
            "cycle_index": cycle_index,
            "cycle_status": status,
            "report_ref": str(cycle.get("report_ref") or ""),
            "report_sha256": str(cycle.get("report_sha256") or "").strip(),
            "eligible_for_evaluation": False,
            "passed": False,
            "failures": [],
            "warnings": [],
        }

        if status not in {"completed", "failed"}:
            row["failures"].append(_failure("batch_manifest_cycle_status_invalid", "cycle status must be completed|failed"))
            failures.extend(row["failures"])
            rows.append(row)
            continue

        if status != "completed":
            row["warnings"].append(_failure("cycle_failed_excluded", "failed cycle excluded from promotion evaluation"))
            rows.append(row)
            continue

        report_path = _resolve_report_ref(batch_manifest_path, cycle.get("report_ref"))
        if not report_path or not report_path.exists():
            row["failures"].append(_failure("batch_manifest_report_missing", "completed cycle report is missing", context={"report_ref": str(report_path)}))
            failures.extend(row["failures"])
            rows.append(row)
            continue

        if not row["report_sha256"]:
            row["failures"].append(_failure("batch_manifest_report_sha256_missing", "completed cycle report_sha256 is missing"))
            failures.extend(row["failures"])
            rows.append(row)
            continue

        computed_sha = _file_sha256(report_path)
        row["report_sha256_computed"] = computed_sha
        if computed_sha != row["report_sha256"]:
            row["failures"].append(
                _failure(
                    "batch_manifest_report_sha256_mismatch",
                    "completed cycle report sha256 mismatch",
                    context={"expected": row["report_sha256"], "actual": computed_sha},
                )
            )
            failures.extend(row["failures"])
            rows.append(row)
            continue

        try:
            report_payload = _load_json(report_path)
        except Exception as exc:  # noqa: BLE001
            row["failures"].append(_failure("batch_manifest_report_parse_failure", f"failed to parse cycle report: {exc.__class__.__name__}"))
            failures.extend(row["failures"])
            rows.append(row)
            continue

        report_schema_id = str(report_payload.get("schema_id") or "")
        report_schema_version = _safe_int(report_payload.get("schema_version"), 0)
        row["report_schema_id"] = report_schema_id
        row["report_schema_version"] = report_schema_version
        if report_schema_id != nrc_aps_live_batch.LIVE_REPORT_SCHEMA_ID or report_schema_version != nrc_aps_live_batch.LIVE_REPORT_SCHEMA_VERSION:
            row["failures"].append(
                _failure(
                    "batch_manifest_report_schema_invalid",
                    "live validation report schema mismatch",
                    context={"schema_id": report_schema_id, "schema_version": report_schema_version},
                )
            )
            failures.extend(row["failures"])
            rows.append(row)
            continue

        evidence = _extract_report_evidence(
            path=report_path,
            payload=report_payload,
            policy=policy,
            cycle_index=cycle_index,
        )
        row["eligible_for_evaluation"] = True
        row["generated_at_utc"] = evidence.get("generated_at_utc")
        row["evidence"] = evidence
        row["passed"] = bool(evidence.get("passed"))
        row["failures"] = list(evidence.get("failures") or [])
        row["warnings"] = list(evidence.get("warnings") or [])
        rows.append(row)
    return rows, failures, warnings


def _evaluate_batch_validity(
    *,
    manifest_payload: dict[str, Any],
    cycle_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    batch_rules = dict(policy.get("batch_rules") or {})
    min_completed = max(1, _safe_int(batch_rules.get("min_completed_cycles"), 1))
    max_age_spread_hours = max(0.0, _safe_float(batch_rules.get("max_batch_age_spread_hours"), 24.0))
    allow_partial_failures = bool(batch_rules.get("allow_partial_failure_cycles", True))
    exclude_failed = bool(batch_rules.get("exclude_failed_cycles_from_evaluation", True))
    require_all_attempted = bool(batch_rules.get("require_all_planned_cycles_attempted", True))

    planned = _safe_int(manifest_payload.get("planned_cycle_count"), 0)
    attempted = _safe_int(manifest_payload.get("attempted_cycle_count"), 0)
    failed_count = _safe_int(manifest_payload.get("failed_cycle_count"), 0)
    completed_count = _safe_int(manifest_payload.get("completed_cycle_count"), 0)

    if require_all_attempted and planned > 0 and attempted < planned:
        failures.append(
            _failure(
                "batch_incomplete_not_allowed",
                "attempted cycles below planned cycle count",
                context={"planned_cycle_count": planned, "attempted_cycle_count": attempted},
            )
        )

    if failed_count > 0 and not allow_partial_failures:
        failures.append(
            _failure(
                "batch_partial_failures_not_allowed",
                "batch has failed cycles and policy disallows partial failure batches",
                context={"failed_cycle_count": failed_count},
            )
        )
    elif failed_count > 0 and allow_partial_failures:
        warnings.append(_failure("batch_partial_failures_excluded", "failed cycles recorded and excluded from promotion evidence"))

    if completed_count < min_completed:
        failures.append(
            _failure(
                "batch_min_completed_cycles_not_met",
                "completed cycle count is below policy minimum",
                context={"completed_cycle_count": completed_count, "min_completed_cycles": min_completed},
            )
        )

    if not exclude_failed and failed_count > 0:
        failures.append(_failure("batch_failed_cycle_inclusion_unsupported", "failed cycles cannot be included in promotion evidence"))

    generated_times: list[datetime] = []
    for row in cycle_rows:
        if not bool(row.get("eligible_for_evaluation")):
            continue
        generated_at = _parse_iso_datetime(row.get("generated_at_utc"))
        if generated_at is None:
            failures.append(
                _failure(
                    "batch_cycle_generated_at_missing",
                    "eligible cycle is missing generated_at_utc",
                    context={"cycle_index": row.get("cycle_index")},
                )
            )
            continue
        generated_times.append(generated_at)

    if not generated_times:
        failures.append(_failure("batch_no_eligible_cycles", "no eligible completed cycles available for promotion evaluation"))
    else:
        oldest = min(generated_times)
        newest = max(generated_times)
        spread_hours = max(0.0, (newest - oldest).total_seconds() / 3600.0)
        if spread_hours > max_age_spread_hours:
            failures.append(
                _failure(
                    "batch_age_spread_exceeded",
                    "batch report age spread exceeds policy limit",
                    context={
                        "spread_hours": round(spread_hours, 6),
                        "max_batch_age_spread_hours": max_age_spread_hours,
                    },
                )
            )

    spacing_affects_validity = _safe_bool(manifest_payload.get("cycle_spacing_affects_batch_validity"), False)
    spacing_requested = max(0.0, _safe_float(manifest_payload.get("cycle_spacing_seconds_requested"), 0.0))
    if spacing_affects_validity and spacing_requested > 0:
        cycle_rows_by_index = {
            _safe_int((item or {}).get("cycle_index"), 0): dict(item or {})
            for item in (manifest_payload.get("cycle_reports") or [])
            if isinstance(item, dict)
        }
        for row in cycle_rows:
            cycle_index = _safe_int(row.get("cycle_index"), 0)
            if cycle_index <= 1:
                continue
            source_cycle = cycle_rows_by_index.get(cycle_index, {})
            actual = source_cycle.get("actual_spacing_seconds_from_previous")
            actual_spacing = _safe_float(actual, -1.0)
            if actual_spacing < 0 or actual_spacing + 0.001 < spacing_requested:
                failures.append(
                    _failure(
                        "batch_cycle_spacing_violation",
                        "actual cycle spacing is below requested spacing while spacing validity is enabled",
                        context={
                            "cycle_index": cycle_index,
                            "requested_spacing_seconds": spacing_requested,
                            "actual_spacing_seconds_from_previous": actual,
                        },
                    )
                )

    return cycle_rows, failures, warnings


def evaluate_promotion_governance(
    *,
    cycle_rows: list[dict[str, Any]],
    policy: dict[str, Any],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    min_reports = max(1, _safe_int(policy.get("min_reports_in_window"), 3))
    min_pass_rate = min(1.0, max(0.0, _safe_float(policy.get("min_pass_rate"), 0.8)))
    latest_max_age_hours = max(1, _safe_int(policy.get("latest_report_max_age_hours"), 36))
    require_latest_pass = bool(policy.get("require_latest_report_pass", True))

    evaluated_rows = [row for row in cycle_rows if bool(row.get("eligible_for_evaluation"))]
    evaluated_rows = sorted(
        evaluated_rows,
        key=lambda item: _parse_iso_datetime(item.get("generated_at_utc")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    latest_row = evaluated_rows[0] if evaluated_rows else None
    pass_count = len([row for row in evaluated_rows if bool(row.get("passed"))])
    pass_rate = (float(pass_count) / float(len(evaluated_rows))) if evaluated_rows else 0.0

    failures: list[dict[str, Any]] = []
    if len(evaluated_rows) < min_reports:
        failures.append(
            _failure(
                "promotion_min_cycles_not_met",
                "eligible cycle count is below policy minimum",
                context={"evaluated_cycles": len(evaluated_rows), "min_reports_in_window": min_reports},
            )
        )
    if pass_rate < min_pass_rate:
        failures.append(
            _failure(
                "promotion_pass_rate_below_threshold",
                "cycle pass rate is below promotion threshold",
                context={"pass_rate": round(pass_rate, 6), "min_pass_rate": min_pass_rate},
            )
        )
    if latest_row is None:
        failures.append(_failure("promotion_latest_cycle_missing", "no eligible latest cycle available"))
    else:
        latest_generated = _parse_iso_datetime(latest_row.get("generated_at_utc"))
        if latest_generated is None:
            failures.append(_failure("promotion_latest_cycle_timestamp_missing", "latest cycle timestamp is missing"))
        else:
            latest_age_hours = max(0.0, (now - latest_generated).total_seconds() / 3600.0)
            if latest_age_hours > latest_max_age_hours:
                failures.append(
                    _failure(
                        "promotion_latest_cycle_too_old",
                        "latest cycle is older than maximum allowed age",
                        context={"latest_age_hours": round(latest_age_hours, 6), "latest_report_max_age_hours": latest_max_age_hours},
                    )
                )
        if require_latest_pass and not bool(latest_row.get("passed")):
            failures.append(_failure("promotion_latest_cycle_failed", "latest cycle failed promotion invariants"))

    return {
        "evaluated_cycle_count": len(evaluated_rows),
        "pass_count": pass_count,
        "fail_count": max(0, len(evaluated_rows) - pass_count),
        "pass_rate": round(pass_rate, 6),
        "min_reports_required": min_reports,
        "min_pass_rate_required": min_pass_rate,
        "latest_report_max_age_hours": latest_max_age_hours,
        "latest_cycle_index": latest_row.get("cycle_index") if latest_row else None,
        "latest_report_ref": latest_row.get("report_ref") if latest_row else None,
        "latest_report_generated_at_utc": latest_row.get("generated_at_utc") if latest_row else None,
        "latest_report_passed": bool(latest_row.get("passed")) if latest_row else False,
        "failures": failures,
        "passed": len(failures) == 0,
    }


def validate_promotion_gate(
    *,
    batch_manifest: str | Path,
    policy_path: str | Path | None = None,
    report_path: str | Path | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    batch_manifest_path = Path(batch_manifest).resolve()
    policy = load_promotion_policy(policy_path)
    policy_path_resolved = Path(policy["policy_path"]).resolve()
    generated_at_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        manifest_payload = nrc_aps_live_batch.load_and_validate_finalized_manifest(batch_manifest_path)
    except Exception as exc:  # noqa: BLE001
        output = {
            "schema_id": PROMOTION_REPORT_SCHEMA_ID,
            "schema_version": PROMOTION_REPORT_SCHEMA_VERSION,
            "evaluator_version": PROMOTION_EVALUATOR_VERSION,
            "generated_at_utc": generated_at_utc,
            "batch_manifest_ref": str(batch_manifest_path),
            "batch_manifest_valid": False,
            "policy_path": str(policy_path_resolved),
            "policy_schema_id": str(policy.get("schema_id") or ""),
            "policy_schema_version": _safe_int(policy.get("schema_version"), 0),
            "policy_sha256": str(policy.get("policy_sha256") or ""),
            "cycle_rows": [],
            "evaluation": {
                "evaluated_cycle_count": 0,
                "pass_count": 0,
                "fail_count": 0,
                "pass_rate": 0.0,
                "failures": [
                    _failure(
                        "batch_manifest_invalid",
                        f"{exc.__class__.__name__}: {exc}",
                        context={"batch_manifest_ref": str(batch_manifest_path)},
                    )
                ],
                "passed": False,
            },
            "passed": False,
        }
        target_report = Path(report_path).resolve() if report_path else DEFAULT_REPORT_DIR / "nrc_aps_promotion_validation_report.json"
        nrc_aps_sync_drift.write_json_deterministic(target_report, output)
        output["report_ref"] = str(target_report)
        return output

    target_report = Path(report_path).resolve() if report_path else _default_report_path(batch_manifest_path, manifest_payload)
    cycle_rows, cycle_failures, cycle_warnings = _load_cycle_rows(
        batch_manifest_path=batch_manifest_path,
        manifest_payload=manifest_payload,
        policy=policy,
    )
    cycle_rows, batch_failures, batch_warnings = _evaluate_batch_validity(
        manifest_payload=manifest_payload,
        cycle_rows=cycle_rows,
        policy=policy,
    )
    evaluation = evaluate_promotion_governance(
        cycle_rows=cycle_rows,
        policy=policy,
        now_utc=now_utc,
    )
    row_failures: list[dict[str, Any]] = []
    for row in cycle_rows:
        cycle_index = _safe_int(row.get("cycle_index"), 0)
        for failure in row.get("failures", []) if isinstance(row.get("failures"), list) else []:
            if not isinstance(failure, dict):
                continue
            context = dict(failure.get("context") or {})
            if cycle_index > 0 and "cycle_index" not in context:
                context["cycle_index"] = cycle_index
            row_failures.append(
                {
                    "code": str(failure.get("code") or ""),
                    "message": str(failure.get("message") or ""),
                    "context": context,
                }
            )
    merged_failures = list(cycle_failures) + row_failures + list(batch_failures) + list(evaluation.get("failures") or [])
    evaluation["failures"] = merged_failures
    evaluation["passed"] = len(merged_failures) == 0
    output = {
        "schema_id": PROMOTION_REPORT_SCHEMA_ID,
        "schema_version": PROMOTION_REPORT_SCHEMA_VERSION,
        "evaluator_version": PROMOTION_EVALUATOR_VERSION,
        "generated_at_utc": generated_at_utc,
        "batch_manifest_ref": str(batch_manifest_path),
        "batch_manifest_sha256": str(manifest_payload.get("manifest_sha256") or ""),
        "batch_manifest_valid": True,
        "batch_id": str(manifest_payload.get("batch_id") or ""),
        "batch_status": str(manifest_payload.get("batch_status") or ""),
        "batch_cycle_spacing": {
            "cycle_spacing_seconds_requested": _safe_float(manifest_payload.get("cycle_spacing_seconds_requested"), 0.0),
            "cycle_spacing_enforced": _safe_bool(manifest_payload.get("cycle_spacing_enforced"), True),
            "cycle_spacing_affects_batch_validity": _safe_bool(manifest_payload.get("cycle_spacing_affects_batch_validity"), False),
        },
        "policy_path": str(policy_path_resolved),
        "policy_schema_id": str(policy.get("schema_id") or ""),
        "policy_schema_version": _safe_int(policy.get("schema_version"), 0),
        "policy_sha256": str(policy.get("policy_sha256") or ""),
        "policy_settings": {
            "min_reports_in_window": _safe_int(policy.get("min_reports_in_window"), 0),
            "min_pass_rate": _safe_float(policy.get("min_pass_rate"), 0.0),
            "latest_report_max_age_hours": _safe_int(policy.get("latest_report_max_age_hours"), 0),
            "require_latest_report_pass": _safe_bool(policy.get("require_latest_report_pass"), True),
            "require_v1_ramp": _safe_bool(policy.get("require_v1_ramp"), True),
            "allow_missing_v1": _safe_bool(policy.get("allow_missing_v1"), False),
            "allow_v1_skipped": _safe_bool(policy.get("allow_v1_skipped"), False),
            "min_v1_recommended_rps": _safe_int(policy.get("min_v1_recommended_rps"), 0),
            "batch_rules": dict(policy.get("batch_rules") or {}),
        },
        "collector_provenance": {
            "collector_version": str(manifest_payload.get("collector_version") or ""),
            "collector_invocation_argv": [str(item) for item in (manifest_payload.get("collector_invocation_argv") or [])],
            "collector_config": dict(manifest_payload.get("collector_config") or {}),
        },
        "cycle_rows": cycle_rows,
        "cycle_warnings": list(cycle_warnings) + list(batch_warnings),
        "evaluation": evaluation,
        "passed": bool(evaluation.get("passed")),
    }
    nrc_aps_sync_drift.write_json_deterministic(target_report, output)
    output["report_ref"] = str(target_report)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate NRC APS promotion governance from one finalized live-validation batch.")
    parser.add_argument("--batch-manifest", required=True, help="Finalized live-validation batch manifest path.")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH), help="Promotion policy JSON path.")
    parser.add_argument("--report", default="", help="Output promotion report path (default derived from batch id).")
    args = parser.parse_args(argv)

    report = validate_promotion_gate(
        batch_manifest=args.batch_manifest,
        policy_path=args.policy,
        report_path=(args.report if str(args.report or "").strip() else None),
    )
    status = "PASS" if bool(report.get("passed")) else "FAIL"
    evaluation = dict(report.get("evaluation") or {})
    print(f"NRC APS promotion governance {status}")
    print(
        "batch_id={0} evaluated_cycles={1} pass_rate={2}".format(
            str(report.get("batch_id") or ""),
            int(evaluation.get("evaluated_cycle_count") or 0),
            evaluation.get("pass_rate"),
        )
    )
    print(f"report={report.get('report_ref')}")
    return 0 if bool(report.get("passed")) else 1
