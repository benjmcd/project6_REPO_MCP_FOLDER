import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_live_batch  # noqa: E402
from app.services import nrc_aps_promotion_gate  # noqa: E402


def _write_policy(
    path: Path,
    *,
    require_v1: bool = True,
    allow_missing_v1: bool = False,
    allow_v1_skipped: bool = False,
    min_reports: int = 3,
) -> None:
    payload = {
        "schema_id": "aps.promotion_policy.v1",
        "schema_version": 1,
        "window_days": 7,
        "min_reports_in_window": min_reports,
        "min_pass_rate": 0.8,
        "latest_report_max_age_hours": 48,
        "require_latest_report_pass": True,
        "require_v1_ramp": require_v1,
        "allow_missing_v1": allow_missing_v1,
        "allow_v1_skipped": allow_v1_skipped,
        "min_v1_recommended_rps": 5,
        "expected_v2": {
            "shape_a_status_class": "2xx",
            "guide_native_status_class_any_of": ["5xx", "4xx"],
            "shape_b_status_class_any_of": ["5xx", "4xx"],
        },
        "allowed_envelope_variants": ["results", "documents"],
        "require_v5_date_added_success": True,
        "take_effective_cap_max": 100,
        "batch_rules": {
            "min_completed_cycles": min_reports,
            "max_batch_age_spread_hours": 24,
            "allow_partial_failure_cycles": True,
            "exclude_failed_cycles_from_evaluation": True,
            "require_all_planned_cycles_attempted": True,
        },
        "tunable_fields": ["min_pass_rate", "min_reports_in_window"],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_live_report(
    path: Path,
    *,
    generated_at: datetime,
    include_v1: bool = True,
    v1_status: str = "observed",
    v1_rps: int = 6,
) -> None:
    tests: dict[str, Any] = {
        "APS-V2_request_shape_acceptance": {
            "shape_a_q_filters": {"status_code": 200},
            "guide_native": {"status_code": 500},
            "shape_b_queryString_docket": {"status_code": 500},
        },
        "APS-V3_response_envelope_variant": {"envelope_variant": "results"},
        "APS-V5_date_added_timestamp_filter_syntax": {"date_added_timestamp_ge": {"ok": True}},
        "APS-V8_take_page_size_behavior": {"take_1000": {"count_returned": 100}},
    }
    if include_v1:
        tests["APS-V1_qps_ramp_test"] = {
            "status": v1_status,
            "recommended_max_rps": v1_rps,
            "first_failure_rps": 6,
            "levels": [],
        }
    payload = {
        "schema_id": "aps.live_validation_report.v1",
        "schema_version": 1,
        "evaluator_version": "test_live_validator",
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "tests": tests,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_batch(
    tmp_path: Path,
    *,
    now: datetime,
    cycle_count: int = 3,
    include_v1: bool = True,
    v1_status: str = "observed",
) -> Path:
    def _runner(
        *,
        cycle_index: int,
        output_path: Path,
        timeout_seconds: int,
        pagination_max_pages: int,
        pagination_take: int,
        url_probe_bytes: int,
    ) -> dict[str, Any]:
        generated_at = now - timedelta(minutes=(cycle_count - cycle_index + 1))
        _write_live_report(
            output_path,
            generated_at=generated_at,
            include_v1=include_v1,
            v1_status=v1_status,
        )
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}

    summary = nrc_aps_live_batch.collect_live_validation_batch(
        cycle_count=cycle_count,
        spacing_seconds=0.0,
        timeout_seconds=45,
        pagination_max_pages=3,
        pagination_take=50,
        url_probe_bytes=4096,
        continue_on_cycle_failure=True,
        batch_root=tmp_path / "batches",
        cycle_runner=_runner,
        invocation_argv=["--test"],
    )
    return Path(summary["manifest_ref"])


def _failure_codes(report: dict[str, Any]) -> set[str]:
    return {str(item.get("code") or "") for item in (report.get("evaluation", {}).get("failures") or [])}


def test_validate_promotion_gate_passes_with_manifest_authoritative_batch(tmp_path: Path):
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    manifest_path = _build_batch(tmp_path, now=now, include_v1=True, v1_status="observed")
    policy_path = tmp_path / "policy.json"
    _write_policy(policy_path, require_v1=True, allow_missing_v1=False, allow_v1_skipped=False, min_reports=3)

    output = nrc_aps_promotion_gate.validate_promotion_gate(
        batch_manifest=manifest_path,
        policy_path=policy_path,
        report_path=tmp_path / "promotion.json",
        now_utc=now,
    )
    assert output["passed"] is True
    assert output["schema_id"] == "aps.promotion_governance.v2"
    assert output["batch_manifest_valid"] is True
    assert output["evaluation"]["evaluated_cycle_count"] == 3
    assert output["evaluation"]["failures"] == []


def test_validate_promotion_gate_fails_when_v1_missing_and_required(tmp_path: Path):
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    manifest_path = _build_batch(tmp_path, now=now, include_v1=False)
    policy_path = tmp_path / "policy.json"
    _write_policy(policy_path, require_v1=True, allow_missing_v1=False, min_reports=3)

    output = nrc_aps_promotion_gate.validate_promotion_gate(
        batch_manifest=manifest_path,
        policy_path=policy_path,
        report_path=tmp_path / "promotion.json",
        now_utc=now,
    )
    assert output["passed"] is False
    assert "v1_missing_not_allowed" in _failure_codes(output)


def test_validate_promotion_gate_v1_skipped_requires_explicit_allow(tmp_path: Path):
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    manifest_path = _build_batch(tmp_path, now=now, include_v1=True, v1_status="skipped")

    blocked_policy = tmp_path / "policy_blocked.json"
    _write_policy(blocked_policy, require_v1=True, allow_missing_v1=False, allow_v1_skipped=False, min_reports=3)
    blocked = nrc_aps_promotion_gate.validate_promotion_gate(
        batch_manifest=manifest_path,
        policy_path=blocked_policy,
        report_path=tmp_path / "promotion_blocked.json",
        now_utc=now,
    )
    assert blocked["passed"] is False
    assert "v1_skipped_not_allowed" in _failure_codes(blocked)

    allowed_policy = tmp_path / "policy_allowed.json"
    _write_policy(allowed_policy, require_v1=True, allow_missing_v1=False, allow_v1_skipped=True, min_reports=3)
    allowed = nrc_aps_promotion_gate.validate_promotion_gate(
        batch_manifest=manifest_path,
        policy_path=allowed_policy,
        report_path=tmp_path / "promotion_allowed.json",
        now_utc=now,
    )
    assert allowed["passed"] is True


def test_validate_promotion_gate_fails_closed_on_mutated_manifest(tmp_path: Path):
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    manifest_path = _build_batch(tmp_path, now=now, include_v1=True)
    policy_path = tmp_path / "policy.json"
    _write_policy(policy_path, require_v1=True, allow_missing_v1=False, min_reports=3)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["batch_status"] = "tampered"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output = nrc_aps_promotion_gate.validate_promotion_gate(
        batch_manifest=manifest_path,
        policy_path=policy_path,
        report_path=tmp_path / "promotion.json",
        now_utc=now,
    )
    assert output["passed"] is False
    assert output["batch_manifest_valid"] is False
    assert "batch_manifest_invalid" in _failure_codes(output)

