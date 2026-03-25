import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_live_batch  # noqa: E402
from app.services import nrc_aps_promotion_tuning  # noqa: E402


def _write_policy(path: Path, *, min_pass_rate: float = 0.8, schema_version: int = 1) -> None:
    payload = {
        "schema_id": "aps.promotion_policy.v1",
        "schema_version": schema_version,
        "window_days": 7,
        "min_reports_in_window": 3,
        "min_pass_rate": min_pass_rate,
        "latest_report_max_age_hours": 48,
        "require_latest_report_pass": True,
        "require_v1_ramp": True,
        "allow_missing_v1": False,
        "allow_v1_skipped": False,
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
            "min_completed_cycles": 3,
            "max_batch_age_spread_hours": 24,
            "allow_partial_failure_cycles": True,
            "exclude_failed_cycles_from_evaluation": True,
            "require_all_planned_cycles_attempted": True,
        },
        "tunable_fields": ["min_pass_rate", "min_reports_in_window"],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_rationale(path: Path, entries: list[dict[str, Any]]) -> None:
    payload = {
        "schema_id": "aps.promotion_policy_rationale.v1",
        "schema_version": 1,
        "entries": entries,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_live_report(path: Path, generated_at: datetime) -> None:
    payload = {
        "schema_id": "aps.live_validation_report.v1",
        "schema_version": 1,
        "evaluator_version": "test_live_validator",
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "tests": {
            "APS-V1_qps_ramp_test": {
                "status": "observed",
                "recommended_max_rps": 6,
                "first_failure_rps": 8,
                "levels": [],
            },
            "APS-V2_request_shape_acceptance": {
                "shape_a_q_filters": {"status_code": 200},
                "guide_native": {"status_code": 500},
                "shape_b_queryString_docket": {"status_code": 500},
            },
            "APS-V3_response_envelope_variant": {"envelope_variant": "results"},
            "APS-V5_date_added_timestamp_filter_syntax": {"date_added_timestamp_ge": {"ok": True}},
            "APS-V8_take_page_size_behavior": {"take_1000": {"count_returned": 100}},
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_batch(tmp_path: Path) -> Path:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)

    def _runner(
        *,
        cycle_index: int,
        output_path: Path,
        timeout_seconds: int,
        pagination_max_pages: int,
        pagination_take: int,
        url_probe_bytes: int,
    ) -> dict[str, Any]:
        _write_live_report(output_path, generated_at=now - timedelta(minutes=cycle_index))
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}

    summary = nrc_aps_live_batch.collect_live_validation_batch(
        cycle_count=3,
        spacing_seconds=0.0,
        timeout_seconds=45,
        pagination_max_pages=2,
        pagination_take=10,
        url_probe_bytes=4096,
        batch_root=tmp_path / "batches",
        cycle_runner=_runner,
        invocation_argv=["--test"],
    )
    return Path(summary["manifest_ref"])


def _failure_codes(report: dict[str, Any]) -> set[str]:
    return {str(item.get("code") or "") for item in (report.get("failures") or [])}


def test_compare_promotion_policies_passes_for_tunable_change_with_rationale(tmp_path: Path):
    manifest_path = _build_batch(tmp_path)
    baseline_policy = tmp_path / "baseline_policy.json"
    tuned_policy = tmp_path / "tuned_policy.json"
    rationale_path = tmp_path / "rationale.json"
    _write_policy(baseline_policy, min_pass_rate=0.8)
    _write_policy(tuned_policy, min_pass_rate=0.7)
    _write_rationale(
        rationale_path,
        entries=[{"key": "min_pass_rate", "reason": "Temporary threshold experiment for this batch."}],
    )

    report = nrc_aps_promotion_tuning.compare_promotion_policies(
        batch_manifest=manifest_path,
        baseline_policy_path=baseline_policy,
        tuned_policy_path=tuned_policy,
        rationale_path=rationale_path,
        output_dir=tmp_path / "reports",
        now_utc=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
    )
    assert report["passed"] is True
    assert report["canonical_policy_unchanged"] is True
    assert report["tuned_policy_status"] in {"experimental_pass_not_promoted", "experimental_fail"}
    assert Path(report["comparison_ref"]).exists()


def test_compare_promotion_policies_fails_on_non_tunable_change(tmp_path: Path):
    manifest_path = _build_batch(tmp_path)
    baseline_policy = tmp_path / "baseline_policy.json"
    tuned_policy = tmp_path / "tuned_policy.json"
    rationale_path = tmp_path / "rationale.json"
    _write_policy(baseline_policy, min_pass_rate=0.8, schema_version=1)
    _write_policy(tuned_policy, min_pass_rate=0.8, schema_version=1)
    payload = json.loads(tuned_policy.read_text(encoding="utf-8"))
    payload["tunable_fields"] = ["min_reports_in_window"]
    tuned_policy.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_rationale(rationale_path, entries=[{"key": "tunable_fields", "reason": "Should fail as non-tunable."}])

    report = nrc_aps_promotion_tuning.compare_promotion_policies(
        batch_manifest=manifest_path,
        baseline_policy_path=baseline_policy,
        tuned_policy_path=tuned_policy,
        rationale_path=rationale_path,
        output_dir=tmp_path / "reports",
    )
    assert report["passed"] is False
    assert "policy_diff_non_tunable_change" in _failure_codes(report)


def test_compare_promotion_policies_fails_on_missing_rationale(tmp_path: Path):
    manifest_path = _build_batch(tmp_path)
    baseline_policy = tmp_path / "baseline_policy.json"
    tuned_policy = tmp_path / "tuned_policy.json"
    rationale_path = tmp_path / "rationale.json"
    _write_policy(baseline_policy, min_pass_rate=0.8)
    _write_policy(tuned_policy, min_pass_rate=0.7)
    _write_rationale(rationale_path, entries=[])

    report = nrc_aps_promotion_tuning.compare_promotion_policies(
        batch_manifest=manifest_path,
        baseline_policy_path=baseline_policy,
        tuned_policy_path=tuned_policy,
        rationale_path=rationale_path,
        output_dir=tmp_path / "reports",
    )
    assert report["passed"] is False
    assert "policy_diff_missing_rationale" in _failure_codes(report)
