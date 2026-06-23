from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_diagnostic_framework import report_header as _report_header  # noqa: E402


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-live-smoke-evidence-report.json")
SMOKE_SCHEMA_ID = "diagnostics.sec_live_source_artifact_operator_smoke.v1"
SMOKE_EXECUTED_DECISION = "sec_live_source_artifact_smoke_executed"
TARGET = "sec_live_source_artifact_operator_smoke_evidence_verification_v1"
NEXT_SLICE = "bind_arelle_fact_authority_to_server_owned_live_source_artifact"
DECISION_VERIFIED = "sec_live_source_artifact_smoke_evidence_verified"
DECISION_BLOCKED = "sec_live_source_artifact_smoke_evidence_blocked"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
CIK_RE = re.compile(r"(?<![A-Za-z0-9])0*\d{6,10}(?![A-Za-z0-9])")
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a private SEC live source-artifact smoke report against "
            "the current isolated retained artifact storage. This performs no "
            "SEC network request and creates no source artifacts or receipts."
        )
    )
    parser.add_argument("--report", required=True, help="Path to the operator-private smoke report JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not write an output report; print only the decision and return the verification exit code.",
    )
    args = parser.parse_args(argv)

    report = build_report(source_root=ROOT, report_path=Path(args.report))
    if args.no_report:
        print("report_write=skipped")
    else:
        output = _resolve_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0 if report["decision"] == DECISION_VERIFIED else 1


def build_report(
    *,
    source_root: Path,
    report_path: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    current_env = dict(os.environ if env is None else env)
    preflight = _preflight_module()
    svc = _service_module()
    report_info = _load_smoke_report(source_root=source_root, report_path=report_path)
    smoke_report = report_info.get("payload") if isinstance(report_info.get("payload"), Mapping) else {}
    storage = _storage_preflight(preflight_module=preflight, source_root=source_root, env=current_env)
    smoke_summary = _smoke_report_summary(smoke_report)
    transport = _live_transport_result(smoke_summary)
    hash_shapes = _hash_shape_result(smoke_summary)
    redaction = _redaction_scan(smoke_report=smoke_report, report_info=report_info, storage=storage)
    status_result = _status_reread(
        svc=svc,
        storage_dir=storage.get("storage_dir_resolved"),
        smoke_report=smoke_report,
    )
    non_goals = _non_goals()
    criteria = [
        _criterion(
            "private_smoke_report_path_admitted",
            bool(report_info["exists"] and report_info["json_valid"] and not report_info["inside_repo_or_onedrive"]),
            _public_report_info(report_info),
            "sec_live_smoke_evidence_report_missing_invalid_or_not_private",
        ),
        _criterion(
            "smoke_report_executed_successfully",
            bool(
                smoke_report.get("schema_id") == SMOKE_SCHEMA_ID
                and smoke_report.get("decision") == SMOKE_EXECUTED_DECISION
                and not smoke_report.get("blocking_reasons")
            ),
            smoke_summary,
            "sec_live_smoke_evidence_report_not_executed",
        ),
        _criterion(
            "smoke_report_live_transport_proven",
            bool(transport["live_transport_proven"]),
            transport,
            "sec_live_smoke_evidence_live_transport_not_proven",
        ),
        _criterion(
            "smoke_report_hash_shapes_valid",
            all(hash_shapes.values()),
            hash_shapes,
            "sec_live_smoke_evidence_report_hash_shape_invalid",
        ),
        _criterion(
            "smoke_report_redacted_hash_only",
            not any(redaction.values()),
            redaction,
            "sec_live_smoke_evidence_raw_authority_leak",
        ),
        _criterion(
            "isolated_storage_ready_for_evidence_reread",
            bool(storage["storage_ready"]),
            _public_storage_info(storage),
            "sec_live_smoke_evidence_storage_missing_or_unsafe",
        ),
        _criterion(
            "retained_status_matches_smoke_report",
            bool(status_result["status_matches_report"]),
            status_result,
            "sec_live_smoke_evidence_retained_status_mismatch",
        ),
        _criterion(
            "downstream_non_goals_preserved",
            not any(non_goals.values()),
            non_goals,
            "sec_live_smoke_evidence_downstream_non_goal_changed",
        ),
    ]
    blockers = [item for item in criteria if item["state"] != "passed"]
    verified = not blockers
    return _report_header(
        schema_id="diagnostics.sec_live_source_artifact_smoke_evidence_verification.v1",
        target=TARGET,
        next_slice=NEXT_SLICE,
        decision=DECISION_VERIFIED if verified else DECISION_BLOCKED,
        headline=(
            "SEC live source-artifact smoke evidence is verified against retained storage."
            if verified
            else "SEC live source-artifact smoke evidence is blocked before Arelle/fact authority."
        ),
        criteria=criteria,
        blocking_reasons=blockers,
        smoke_report=smoke_summary,
        transport=transport,
        report_path=_public_report_info(report_info),
        storage=_public_storage_info(storage),
        retained_status=status_result,
        hash_shapes=hash_shapes,
        redaction=redaction,
        execution_effects={
            "validate_only": True,
            "sec_network_request_performed": False,
            "source_artifact_or_receipt_created": False,
            "retained_status_reread_performed": bool(status_result["status_reread_performed"]),
            "arelle_subprocess_invoked": False,
            "value_reveal_exercised": False,
        },
        required_next_action=(
            "bind_arelle_fact_authority_to_server_owned_live_source_artifact"
            if verified
            else "rerun_or_repair_operator_smoke_before_arelle_fact_authority"
        ),
        non_goals_preserved=non_goals,
    )


def _load_smoke_report(*, source_root: Path, report_path: Path) -> dict[str, Any]:
    resolved = report_path if report_path.is_absolute() else source_root / report_path
    resolved = resolved.resolve(strict=False)
    info: dict[str, Any] = {
        "path_marker": _marker(str(resolved)),
        "exists": resolved.is_file(),
        "inside_repo_or_onedrive": _path_inside_repo_or_onedrive(resolved, source_root.resolve()),
        "json_valid": False,
        "payload": {},
        "raw_path_returned": False,
    }
    if not info["exists"]:
        return info
    try:
        info["payload"] = json.loads(resolved.read_text(encoding="utf-8"))
        info["json_valid"] = isinstance(info["payload"], dict)
    except (OSError, json.JSONDecodeError):
        info["payload"] = {}
    return info


def _smoke_report_summary(smoke_report: Mapping[str, Any]) -> dict[str, Any]:
    evidence = smoke_report.get("operator_evidence") if isinstance(smoke_report.get("operator_evidence"), Mapping) else {}
    effects = smoke_report.get("execution_effects") if isinstance(smoke_report.get("execution_effects"), Mapping) else {}
    return {
        "schema_id": smoke_report.get("schema_id"),
        "decision": smoke_report.get("decision"),
        "target": smoke_report.get("target"),
        "blocking_reason_count": len(smoke_report.get("blocking_reasons") or []),
        "transport_kind": evidence.get("transport_kind"),
        "transport_call_count": evidence.get("transport_call_count"),
        "network_request_made": effects.get("network_request_made"),
        "real_sec_network_request_performed": effects.get("real_sec_network_request_performed"),
        "source_artifact_or_receipt_created": effects.get("source_artifact_or_receipt_created"),
        "status_reread_performed": effects.get("status_reread_performed"),
        "live_source_artifact_receipt_id": evidence.get("live_source_artifact_receipt_id"),
        "live_source_artifact_receipt_hash": evidence.get("live_source_artifact_receipt_hash"),
        "source_artifact_receipt_hash": evidence.get("source_artifact_receipt_hash"),
        "source_artifact_ref_hash": evidence.get("source_artifact_ref_hash"),
        "source_identity_hash": evidence.get("source_identity_hash"),
        "content_sha256": evidence.get("content_sha256"),
        "content_length": evidence.get("content_length"),
    }


def _storage_preflight(*, preflight_module: Any, source_root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    raw_storage = str(env.get(preflight_module.STORAGE_ENV) or "").strip()
    exposure = str(env.get(preflight_module.STORAGE_EXPOSURE_ENV) or "auto").strip().lower()
    resolved = preflight_module._normalise_storage_dir(source_root, raw_storage) if raw_storage else None  # noqa: SLF001
    inside = (
        preflight_module._path_inside_repo_or_onedrive(resolved, source_root.resolve())  # noqa: SLF001
        if resolved
        else False
    )
    return {
        "storage_env_var": preflight_module.STORAGE_ENV,
        "storage_exposure_env_var": preflight_module.STORAGE_EXPOSURE_ENV,
        "storage_dir_present": bool(raw_storage),
        "storage_dir_exists": resolved.is_dir() if resolved else False,
        "storage_dir_marker": _marker(str(resolved)) if resolved else None,
        "storage_dir_resolved": resolved,
        "storage_dir_inside_repo_or_onedrive": inside,
        "storage_exposure": exposure,
        "storage_exposure_disabled": exposure == "disabled",
        "storage_ready": bool(
            raw_storage
            and resolved
            and resolved.is_dir()
            and not inside
            and exposure == "disabled"
        ),
        "raw_path_returned": False,
    }


def _status_reread(*, svc: Any, storage_dir: Any, smoke_report: Mapping[str, Any]) -> dict[str, Any]:
    summary = _smoke_report_summary(smoke_report)
    receipt_id = str(summary.get("live_source_artifact_receipt_id") or "")
    expected_hash = str(summary.get("live_source_artifact_receipt_hash") or "")
    result: dict[str, Any] = {
        "status_reread_performed": False,
        "status_matches_report": False,
        "live_source_artifact_receipt_id": receipt_id or None,
        "live_source_artifact_receipt_hash": expected_hash or None,
        "source_artifact_receipt_hash": summary.get("source_artifact_receipt_hash"),
        "source_artifact_ref_hash": summary.get("source_artifact_ref_hash"),
        "source_identity_hash": summary.get("source_identity_hash"),
        "content_sha256": summary.get("content_sha256"),
        "content_length": summary.get("content_length"),
        "error_code": None,
        "raw_path_returned": False,
        "artifact_bytes_returned": False,
    }
    if not storage_dir or not receipt_id or not expected_hash:
        result["error_code"] = "sec_live_smoke_evidence_missing_receipt_identity"
        return result

    previous_storage = getattr(svc.settings, "storage_dir")
    try:
        setattr(svc.settings, "storage_dir", str(storage_dir))
        status = svc.inspect_sec_edgar_text_table_live_source_artifact_status(receipt_id)
        result["status_reread_performed"] = True
        source_receipt = status.get("source_artifact_receipt") or {}
        retained = status.get("retained_source_artifact_manifest") or {}
        observed = {
            "live_source_artifact_receipt_hash": status.get("live_source_artifact_receipt_hash"),
            "source_artifact_receipt_hash": source_receipt.get("source_artifact_receipt_hash"),
            "source_artifact_ref_hash": source_receipt.get("source_artifact_ref_hash"),
            "source_identity_hash": (status.get("source_identity") or {}).get("source_identity_hash"),
            "content_sha256": source_receipt.get("content_sha256"),
            "content_length": source_receipt.get("content_length"),
            "retained_source_artifact_available": retained.get("retained_source_artifact_available"),
        }
        result.update(observed)
        result["status_response_hash"] = _stable_hash(status)
        result["status_matches_report"] = all(
            [
                observed["live_source_artifact_receipt_hash"] == expected_hash,
                observed["source_artifact_receipt_hash"] == summary.get("source_artifact_receipt_hash"),
                observed["source_artifact_ref_hash"] == summary.get("source_artifact_ref_hash"),
                observed["source_identity_hash"] == summary.get("source_identity_hash"),
                observed["content_sha256"] == summary.get("content_sha256"),
                observed["content_length"] == summary.get("content_length"),
                observed["retained_source_artifact_available"] is True,
            ]
        )
    except svc.Layer3WorkbenchError as exc:
        result["error_code"] = exc.error_code
    finally:
        setattr(svc.settings, "storage_dir", previous_storage)
    return result


def _live_transport_result(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "transport_kind": summary.get("transport_kind"),
        "network_request_made": summary.get("network_request_made"),
        "real_sec_network_request_performed": summary.get("real_sec_network_request_performed"),
        "transport_call_count": summary.get("transport_call_count"),
        "live_transport_required": True,
        "live_transport_proven": bool(
            summary.get("transport_kind") == "live_http"
            and summary.get("network_request_made") is True
            and summary.get("real_sec_network_request_performed") is True
            and summary.get("transport_call_count") == 1
        ),
    }


def _hash_shape_result(summary: Mapping[str, Any]) -> dict[str, bool]:
    fields = [
        "live_source_artifact_receipt_hash",
        "source_artifact_receipt_hash",
        "source_artifact_ref_hash",
        "source_identity_hash",
        "content_sha256",
    ]
    return {field: bool(SHA256_RE.fullmatch(str(summary.get(field) or ""))) for field in fields}


def _redaction_scan(
    *,
    smoke_report: Mapping[str, Any],
    report_info: Mapping[str, Any],
    storage: Mapping[str, Any],
) -> dict[str, bool]:
    text = json.dumps(smoke_report, sort_keys=True)
    redaction = smoke_report.get("redaction") if isinstance(smoke_report.get("redaction"), Mapping) else {}
    raw_flags = {str(key): bool(value) for key, value in redaction.items()}
    path_markers_only = _marker_absent(report_info.get("path_marker"), text) and _marker_absent(
        storage.get("storage_dir_marker"),
        text,
    )
    return {
        "smoke_report_redaction_flag_leak": any(raw_flags.values()),
        "raw_cik_like_returned": _raw_cik_like_returned(smoke_report),
        "raw_accession_pattern_returned": bool(ACCESSION_RE.search(text)),
        "raw_sec_url_returned": bool(SEC_URL_RE.search(text)),
        "raw_report_path_returned": not path_markers_only,
        "artifact_bytes_returned": "SEC-LIVE-SMOKE-RAW-CONTENT" in text,
    }


def _raw_cik_like_returned(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_raw_cik_like_returned(item) for item in value.values())
    if isinstance(value, list):
        return any(_raw_cik_like_returned(item) for item in value)
    if not isinstance(value, str):
        return False
    if SHA256_RE.fullmatch(value) or re.fullmatch(r"[a-f0-9]{16,}", value):
        return False
    return bool(CIK_RE.search(value))


def _public_report_info(report_info: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path_marker": report_info.get("path_marker"),
        "exists": report_info.get("exists"),
        "json_valid": report_info.get("json_valid"),
        "inside_repo_or_onedrive": report_info.get("inside_repo_or_onedrive"),
        "raw_path_returned": False,
    }


def _public_storage_info(storage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "storage_env_var": storage.get("storage_env_var"),
        "storage_exposure_env_var": storage.get("storage_exposure_env_var"),
        "storage_dir_present": storage.get("storage_dir_present"),
        "storage_dir_exists": storage.get("storage_dir_exists"),
        "storage_dir_marker": storage.get("storage_dir_marker"),
        "storage_dir_inside_repo_or_onedrive": storage.get("storage_dir_inside_repo_or_onedrive"),
        "storage_exposure": storage.get("storage_exposure"),
        "storage_exposure_disabled": storage.get("storage_exposure_disabled"),
        "storage_ready": storage.get("storage_ready"),
        "raw_path_returned": False,
    }


def _non_goals() -> dict[str, bool]:
    return {
        "sec_network_request_performed": False,
        "source_artifact_or_receipt_created": False,
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


def _preflight_module() -> Any:
    path = ASSESSMENT / "sec-live-preflight.py"
    spec = importlib.util.spec_from_file_location("sec_live_preflight", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load preflight module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _service_module() -> Any:
    from app.services import layer3_sec_edgar_live_source_artifact as svc

    return svc


def _path_inside_repo_or_onedrive(path: Path | None, root: Path) -> bool:
    if path is None:
        return False
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
        return True
    except ValueError:
        pass
    return any(part.lower().startswith("onedrive") for part in resolved.parts)


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _marker(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _marker_absent(value: Any, text: str) -> bool:
    marker = str(value or "")
    return not marker or marker not in text


def _stable_hash(value: Any) -> str:
    import hashlib

    stable_json = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
