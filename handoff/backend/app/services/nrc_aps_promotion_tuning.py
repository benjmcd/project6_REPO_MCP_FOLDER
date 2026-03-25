from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import nrc_aps_live_batch
from app.services import nrc_aps_promotion_gate
from app.services import nrc_aps_sync_drift


PROMOTION_POLICY_RATIONALE_SCHEMA_ID = "aps.promotion_policy_rationale.v1"
PROMOTION_POLICY_DIFF_SCHEMA_ID = "aps.promotion_policy_diff.v1"
PROMOTION_POLICY_COMPARE_SCHEMA_ID = "aps.promotion_policy_compare.v1"
PROMOTION_POLICY_COMPARE_SCHEMA_VERSION = 1
PROMOTION_TUNER_VERSION = "nrc_aps_promotion_tuning_v1"

DEFAULT_OUTPUT_DIR = Path("tests/reports")
DEFAULT_BASELINE_POLICY_PATH = nrc_aps_promotion_gate.DEFAULT_POLICY_PATH

DEFAULT_TUNABLE_FIELDS = {
    "window_days",
    "min_reports_in_window",
    "min_pass_rate",
    "latest_report_max_age_hours",
    "require_latest_report_pass",
    "require_v1_ramp",
    "allow_missing_v1",
    "allow_v1_skipped",
    "min_v1_recommended_rps",
    "allowed_envelope_variants",
    "require_v5_date_added_success",
    "take_effective_cap_max",
    "expected_v2.shape_a_status_class",
    "expected_v2.guide_native_status_class_any_of",
    "expected_v2.shape_b_status_class_any_of",
    "batch_rules.min_completed_cycles",
    "batch_rules.max_batch_age_spread_hours",
    "batch_rules.allow_partial_failure_cycles",
    "batch_rules.exclude_failed_cycles_from_evaluation",
    "batch_rules.require_all_planned_cycles_attempted",
}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_sha256(payload: dict[str, Any]) -> str:
    stable = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _flatten_diffs(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        out: list[dict[str, Any]] = []
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            key_path = f"{path}.{key}" if path else str(key)
            out.extend(_flatten_diffs(before.get(key), after.get(key), key_path))
        return out
    if isinstance(before, list) and isinstance(after, list):
        if before == after:
            return []
        return [{"path": path, "baseline_value": before, "tuned_value": after}]
    if before == after:
        return []
    return [{"path": path, "baseline_value": before, "tuned_value": after}]


def _is_tunable(path: str, tunable_fields: set[str]) -> bool:
    for candidate in tunable_fields:
        if path == candidate or path.startswith(f"{candidate}."):
            return True
    return False


def _load_rationale_map(path: Path) -> tuple[dict[str, dict[str, Any]], str]:
    payload = _load_json(path)
    if str(payload.get("schema_id") or "") != PROMOTION_POLICY_RATIONALE_SCHEMA_ID:
        raise ValueError("rationale_schema_id_invalid")
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("rationale_schema_version_invalid")
    out: dict[str, dict[str, Any]] = {}
    for entry in payload.get("entries", []) if isinstance(payload.get("entries"), list) else []:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        if not key or not reason:
            continue
        out[key] = dict(entry)
    return out, _json_sha256(payload)


def compare_promotion_policies(
    *,
    batch_manifest: str | Path,
    tuned_policy_path: str | Path,
    rationale_path: str | Path,
    baseline_policy_path: str | Path = DEFAULT_BASELINE_POLICY_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    batch_manifest_path = Path(batch_manifest).resolve()
    manifest_payload = nrc_aps_live_batch.load_and_validate_finalized_manifest(batch_manifest_path)
    batch_id = str(manifest_payload.get("batch_id") or batch_manifest_path.stem).strip() or batch_manifest_path.stem
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline_policy = nrc_aps_promotion_gate.load_promotion_policy(baseline_policy_path)
    tuned_policy = nrc_aps_promotion_gate.load_promotion_policy(tuned_policy_path)
    rationale_map, rationale_sha = _load_rationale_map(Path(rationale_path).resolve())

    baseline_raw = dict(baseline_policy.get("raw_policy") or {})
    tuned_raw = dict(tuned_policy.get("raw_policy") or {})
    diffs = _flatten_diffs(baseline_raw, tuned_raw)

    tunable_fields = {
        str(item).strip()
        for item in (baseline_raw.get("tunable_fields") or DEFAULT_TUNABLE_FIELDS)
        if str(item).strip()
    }
    failures: list[dict[str, Any]] = []
    if not diffs:
        failures.append({"code": "policy_diff_no_changes", "message": "No policy changes detected between baseline and tuned policy", "context": {}})

    enriched_diffs: list[dict[str, Any]] = []
    for diff in diffs:
        path = str(diff.get("path") or "")
        tunable = _is_tunable(path, tunable_fields)
        rationale = rationale_map.get(path)
        row = {
            "path": path,
            "baseline_value": diff.get("baseline_value"),
            "tuned_value": diff.get("tuned_value"),
            "tunable": tunable,
            "rationale": rationale,
        }
        if not tunable:
            failures.append({"code": "policy_diff_non_tunable_change", "message": "Changed policy key is not tunable", "context": {"path": path}})
        if rationale is None:
            failures.append({"code": "policy_diff_missing_rationale", "message": "Missing rationale for tuned policy key", "context": {"path": path}})
        enriched_diffs.append(row)

    baseline_report_path = out_dir / f"{batch_id}_aps_promotion_baseline_eval_v1.json"
    tuned_report_path = out_dir / f"{batch_id}_aps_promotion_tuned_eval_v1.json"
    policy_diff_path = out_dir / f"{batch_id}_aps_promotion_policy_diff_v1.json"
    comparison_path = out_dir / f"{batch_id}_aps_promotion_compare_v1.json"

    baseline_eval = nrc_aps_promotion_gate.validate_promotion_gate(
        batch_manifest=batch_manifest_path,
        policy_path=Path(baseline_policy.get("policy_path") or ""),
        report_path=baseline_report_path,
        now_utc=now_utc,
    )
    tuned_eval = nrc_aps_promotion_gate.validate_promotion_gate(
        batch_manifest=batch_manifest_path,
        policy_path=Path(tuned_policy.get("policy_path") or ""),
        report_path=tuned_report_path,
        now_utc=now_utc,
    )

    baseline_failure_codes = sorted({str(item.get("code") or "") for item in (baseline_eval.get("evaluation", {}).get("failures") or []) if str(item.get("code") or "")})
    tuned_failure_codes = sorted({str(item.get("code") or "") for item in (tuned_eval.get("evaluation", {}).get("failures") or []) if str(item.get("code") or "")})
    failure_code_delta = {
        "added_in_tuned": sorted(set(tuned_failure_codes) - set(baseline_failure_codes)),
        "removed_in_tuned": sorted(set(baseline_failure_codes) - set(tuned_failure_codes)),
    }

    policy_diff = {
        "schema_id": PROMOTION_POLICY_DIFF_SCHEMA_ID,
        "schema_version": 1,
        "generated_at_utc": _utc_iso(),
        "batch_id": batch_id,
        "baseline_policy_path": str(Path(baseline_policy.get("policy_path") or "").resolve()),
        "baseline_policy_sha256": str(baseline_policy.get("policy_sha256") or ""),
        "tuned_policy_path": str(Path(tuned_policy.get("policy_path") or "").resolve()),
        "tuned_policy_sha256": str(tuned_policy.get("policy_sha256") or ""),
        "rationale_path": str(Path(rationale_path).resolve()),
        "rationale_sha256": rationale_sha,
        "changed_fields": enriched_diffs,
        "tunable_fields": sorted(tunable_fields),
        "failures": failures,
    }
    nrc_aps_sync_drift.write_json_deterministic(policy_diff_path, policy_diff)

    comparison = {
        "schema_id": PROMOTION_POLICY_COMPARE_SCHEMA_ID,
        "schema_version": PROMOTION_POLICY_COMPARE_SCHEMA_VERSION,
        "evaluator_version": PROMOTION_TUNER_VERSION,
        "generated_at_utc": _utc_iso(),
        "batch_manifest_ref": str(batch_manifest_path),
        "batch_manifest_sha256": str(manifest_payload.get("manifest_sha256") or ""),
        "baseline_policy_path": str(Path(baseline_policy.get("policy_path") or "").resolve()),
        "baseline_policy_sha256": str(baseline_policy.get("policy_sha256") or ""),
        "tuned_policy_path": str(Path(tuned_policy.get("policy_path") or "").resolve()),
        "tuned_policy_sha256": str(tuned_policy.get("policy_sha256") or ""),
        "rationale_path": str(Path(rationale_path).resolve()),
        "rationale_sha256": rationale_sha,
        "policy_diff_ref": str(policy_diff_path),
        "baseline_report_ref": str(baseline_eval.get("report_ref") or baseline_report_path),
        "tuned_report_ref": str(tuned_eval.get("report_ref") or tuned_report_path),
        "baseline_passed": bool(baseline_eval.get("passed")),
        "tuned_passed": bool(tuned_eval.get("passed")),
        "tuned_policy_status": "experimental_pass_not_promoted" if bool(tuned_eval.get("passed")) else "experimental_fail",
        "canonical_policy_unchanged": True,
        "failure_code_delta": failure_code_delta,
        "baseline_pass_rate": baseline_eval.get("evaluation", {}).get("pass_rate"),
        "tuned_pass_rate": tuned_eval.get("evaluation", {}).get("pass_rate"),
        "failures": failures,
        "passed": len(failures) == 0,
    }
    nrc_aps_sync_drift.write_json_deterministic(comparison_path, comparison)
    comparison["comparison_ref"] = str(comparison_path)
    return comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare baseline vs tuned NRC APS promotion policy against one finalized batch.")
    parser.add_argument("--batch-manifest", required=True, help="Finalized live-validation batch manifest path.")
    parser.add_argument("--tuned-policy", required=True, help="Tuned policy JSON path (experimental override only).")
    parser.add_argument("--rationale", required=True, help="Rationale JSON path for tuned policy keys.")
    parser.add_argument("--baseline-policy", default=str(DEFAULT_BASELINE_POLICY_PATH), help="Canonical baseline policy JSON path.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for policy diff and comparison artifacts.")
    parser.add_argument("--require-tuned-pass", action="store_true", help="Fail command if tuned policy does not pass promotion evaluation.")
    args = parser.parse_args(argv)

    comparison = compare_promotion_policies(
        batch_manifest=args.batch_manifest,
        tuned_policy_path=args.tuned_policy,
        rationale_path=args.rationale,
        baseline_policy_path=args.baseline_policy,
        output_dir=args.out_dir,
    )
    status = "PASS" if bool(comparison.get("passed")) else "FAIL"
    print(f"NRC APS promotion policy comparison {status}")
    print(f"comparison={comparison.get('comparison_ref')}")
    print(
        "baseline_passed={0} tuned_passed={1} tuned_policy_status={2}".format(
            bool(comparison.get("baseline_passed")),
            bool(comparison.get("tuned_passed")),
            str(comparison.get("tuned_policy_status") or ""),
        )
    )
    if bool(args.require_tuned_pass) and not bool(comparison.get("tuned_passed")):
        return 1
    return 0 if bool(comparison.get("passed")) else 1
