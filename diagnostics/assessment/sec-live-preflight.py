from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping
import urllib.parse


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = Path(__file__).resolve().parent
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))

from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_diagnostic_framework import report_header as _report_header  # noqa: E402


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-live-preflight-report.json")

TARGET = "sec_live_source_artifact_manual_smoke_preflight_v1"
NEXT_SLICE = "execute_operator_configured_manual_live_sec_source_artifact_smoke"
ACQUIRE_ROUTE = "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/acquire"
STATUS_ROUTE = "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/status/{live_source_artifact_receipt_id}"

LIVE_ENABLED_ENV = "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED"
USER_AGENT_ENV = "LAYER3_SEC_EDGAR_USER_AGENT"
RATE_ENV = "LAYER3_SEC_EDGAR_RATE_LIMIT_PER_SECOND"
MAX_REQUESTS_ENV = "LAYER3_SEC_EDGAR_MAX_LIVE_REQUESTS_PER_PROCESS"
MAX_BYTES_ENV = "LAYER3_SEC_EDGAR_MAX_BYTES"
TIMEOUT_ENV = "LAYER3_SEC_EDGAR_TIMEOUT_SECONDS"
STORAGE_ENV = "STORAGE_DIR"
STORAGE_EXPOSURE_ENV = "STORAGE_EXPOSURE"
DATABASE_ENV = "DATABASE_URL"
CI_ENV = "CI"

SMOKE_CIK_ENV = "LAYER3_SEC_EDGAR_SMOKE_CIK"
SMOKE_ACCESSION_ENV = "LAYER3_SEC_EDGAR_SMOKE_ACCESSION"
SMOKE_FORM_ENV = "LAYER3_SEC_EDGAR_SMOKE_FORM_TYPE"
SMOKE_DATE_ENV = "LAYER3_SEC_EDGAR_SMOKE_FILING_DATE"
SMOKE_CONFIRM_ENV = "LAYER3_SEC_EDGAR_SMOKE_OPERATOR_CONFIRMATION"

CIK_RE = re.compile(r"^\d{1,10}$")
ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
FORM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,31}$")
FILING_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RECEIPT_DIR = "layer3-sec-edgar-live-source-artifact-acquisition"
RECEIPT_PREFIX = "sec-edgar-text-table-live-source-artifact"
ADMITTED_EXTERNAL_DB_SCHEMES = {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}
MAX_BYTES_CEILING = 25_000_000
TIMEOUT_SECONDS_CEILING = 120


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only preflight for the manual SEC live source-artifact smoke. "
            "This does not fetch SEC data, create artifacts, seed storage, invoke "
            "Arelle, or change defaults."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(source_root=ROOT)
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(*, source_root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    current_env = dict(os.environ if env is None else env)
    source = _source_surface(source_root)
    defaults = _default_projection(source_root)
    runtime = _runtime_preflight(source_root=source_root, env=current_env)
    request = _smoke_request_preflight(source_root=source_root, env=current_env)

    criteria = [
        _criterion(
            "source_surface_contains_live_acquire_and_status_routes",
            source["acquire_route_present"]
            and source["status_route_present"]
            and source["service_requires_user_agent"]
            and source["service_requires_operator_confirmation"]
            and source["service_rejects_raw_refs"],
            source,
            "sec_live_preflight_source_surface_missing_required_gate",
        ),
        _criterion(
            "committed_defaults_and_support_matrix_remain_default_off",
            defaults["live_network_default_off"] and defaults["support_matrix_experimental_default_off"],
            defaults,
            "sec_live_preflight_committed_default_or_support_matrix_changed",
        ),
        _criterion(
            "live_network_explicitly_enabled_for_this_operator_smoke",
            runtime["live_network"]["enabled"],
            runtime["live_network"],
            "sec_live_preflight_live_network_not_explicitly_enabled",
        ),
        _criterion(
            "sec_user_agent_present_and_redacted",
            runtime["user_agent"]["present"] and runtime["user_agent"]["raw_value_returned"] is False,
            runtime["user_agent"],
            "sec_live_preflight_user_agent_missing",
        ),
        _criterion(
            "ci_runtime_not_active",
            runtime["ci"]["ci_active"] is False,
            runtime["ci"],
            "sec_live_preflight_ci_runtime_active",
        ),
        _criterion(
            "isolated_storage_ready_outside_repo_or_onedrive",
            runtime["storage"]["storage_dir_exists"]
            and runtime["storage"]["storage_dir_writable_non_mutating_check"]
            and runtime["storage"]["storage_dir_inside_repo_or_onedrive"] is False
            and runtime["storage"]["storage_exposure_disabled"],
            runtime["storage"],
            "sec_live_preflight_storage_missing_or_unsafe",
        ),
        _criterion(
            "database_runtime_containment_ready",
            runtime["database"]["database_safe_for_live_sec"],
            runtime["database"],
            "sec_live_preflight_database_missing_or_unsafe",
        ),
        _criterion(
            "rate_and_size_controls_admitted",
            runtime["limits"]["rate_limit_admitted"]
            and runtime["limits"]["max_live_requests_admitted"]
            and runtime["limits"]["max_bytes_admitted"]
            and runtime["limits"]["timeout_seconds_admitted"],
            runtime["limits"],
            "sec_live_preflight_rate_or_size_controls_invalid",
        ),
        _criterion(
            "operator_smoke_request_identity_present_and_redacted",
            request["request_ready"]
            and request["matching_existing_receipt_found"] is False
            and request["raw_identity_returned"] is False,
            request,
            "sec_live_preflight_smoke_request_missing_or_invalid",
        ),
    ]
    blockers = [item for item in criteria if item["state"] != "passed"]
    ready = not blockers
    return _report_header(
        schema_id="diagnostics.sec_live_source_artifact_smoke_preflight.v1",
        target=TARGET,
        next_slice=NEXT_SLICE,
        decision=(
            "sec_live_source_artifact_smoke_preflight_ready"
            if ready
            else "sec_live_source_artifact_smoke_preflight_blocked"
        ),
        headline=_headline(ready=ready, blockers=blockers),
        criteria=criteria,
        blocking_reasons=blockers,
        source_surface=source,
        default_posture=defaults,
        runtime_preflight=runtime,
        smoke_request_preflight=request,
        required_next_action=(
            "run_one_filing_live_source_artifact_smoke_with_redacted_hash_only_evidence"
            if ready
            else "configure_operator_sec_user_agent_live_flag_safe_storage_database_and_smoke_request_then_rerun_preflight"
        ),
        non_goals_preserved={
            "sec_network_fetch_performed": False,
            "source_artifact_created": False,
            "receipt_created": False,
            "status_reread_performed": False,
            "arelle_subprocess_invoked": False,
            "multi_filing_enforcement_exercised": False,
            "delivery_export_status_exercised": False,
            "provider_delivery_exercised": False,
            "nonlocal_auth_hardening_changed": False,
            "value_reveal_exercised": False,
            "default_on_graduation_claimed": False,
            "raw_sec_url_returned": False,
            "raw_local_path_returned": False,
            "raw_user_agent_returned": False,
            "artifact_bytes_returned": False,
            "config_default_changed": False,
            "support_matrix_changed": False,
            "production_readiness_claimed": False,
        },
    )


def _source_surface(source_root: Path) -> dict[str, Any]:
    api_text = _read_text(source_root / "backend" / "app" / "api" / "layer3" / "source_sec_edgar.py")
    service_text = _read_text(
        source_root / "backend" / "app" / "services" / "layer3_sec_edgar_live_source_artifact.py"
    )
    return {
        "acquire_route": ACQUIRE_ROUTE,
        "status_route": STATUS_ROUTE,
        "acquire_route_present": '"/source/sec-edgar/text-table/live-source-artifact/acquire"' in api_text,
        "status_route_present": '"/source/sec-edgar/text-table/live-source-artifact/status/{live_source_artifact_receipt_id}"'
        in api_text,
        "service_requires_user_agent": "def _server_configured_user_agent" in service_text
        and "sec_edgar_text_table_live_source_artifact_user_agent_missing" in service_text,
        "service_requires_operator_confirmation": "operator_confirmation" in service_text
        and "sec_edgar_text_table_live_source_artifact_operator_confirmation_missing" in service_text,
        "service_rejects_raw_refs": "FORBIDDEN_REQUEST_FIELDS" in service_text
        and "raw_url" in service_text
        and "artifact_bytes" in service_text,
        "routes_redacted": True,
    }


def _default_projection(source_root: Path) -> dict[str, Any]:
    config_text = _read_text(source_root / "backend" / "app" / "core" / "config.py")
    support_text = _read_text(source_root / "config" / "support_matrix.yaml")
    support_live_entry_default_off = bool(
        re.search(
            r'"id":\s*"sec_live_network_egress"[\s\S]{0,240}?"status":\s*"experimental_default_off"',
            support_text,
        )
    )
    return {
        "live_network_default_off": _contains(
            config_text,
            "layer3_sec_edgar_live_network_enabled: bool = Field(\n        default=False,",
        ),
        "support_matrix_experimental_default_off": support_live_entry_default_off,
        "config_default_changed_by_preflight": False,
        "support_matrix_changed_by_preflight": False,
    }


def _runtime_preflight(*, source_root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    return {
        "live_network": _live_network(env),
        "user_agent": _user_agent(env),
        "ci": {"ci_active": _truthy(env.get(CI_ENV)), "ci_env_var": CI_ENV},
        "storage": _storage(source_root=source_root, env=env),
        "database": _database(source_root=source_root, env=env),
        "limits": _limits(env),
    }


def _live_network(env: Mapping[str, str]) -> dict[str, Any]:
    raw = str(env.get(LIVE_ENABLED_ENV) or "").strip()
    return {
        "env_var": LIVE_ENABLED_ENV,
        "present": bool(raw),
        "enabled": _truthy(raw),
        "raw_value_returned": False,
    }


def _user_agent(env: Mapping[str, str]) -> dict[str, Any]:
    value = str(env.get(USER_AGENT_ENV) or "").strip()
    return {
        "env_var": USER_AGENT_ENV,
        "present": bool(value),
        "marker": _marker(value) if value else None,
        "length": len(value) if value else 0,
        "raw_value_returned": False,
    }


def _storage(*, source_root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    raw_storage = str(env.get(STORAGE_ENV) or "").strip()
    exposure = str(env.get(STORAGE_EXPOSURE_ENV) or "auto").strip().lower()
    resolved = _normalise_storage_dir(source_root, raw_storage) if raw_storage else None
    inside = _path_inside_repo_or_onedrive(resolved, source_root.resolve()) if resolved else False
    return {
        "storage_env_var": STORAGE_ENV,
        "storage_exposure_env_var": STORAGE_EXPOSURE_ENV,
        "storage_dir_present": bool(raw_storage),
        "storage_dir_exists": resolved.is_dir() if resolved else False,
        "storage_dir_writable_non_mutating_check": os.access(resolved, os.W_OK) if resolved else False,
        "storage_dir_marker": _marker(str(resolved)) if resolved else None,
        "storage_dir_inside_repo_or_onedrive": inside,
        "storage_exposure": exposure,
        "storage_exposure_disabled": exposure == "disabled",
        "raw_path_returned": False,
    }


def _database(*, source_root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    raw = str(env.get(DATABASE_ENV) or "").strip()
    sqlite_path = _sqlite_database_path(raw, source_root=source_root)
    inside = _path_inside_repo_or_onedrive(sqlite_path, source_root.resolve()) if sqlite_path else False
    sqlite_memory = raw == "sqlite:///:memory:" or raw.startswith("sqlite:///file::memory:")
    parsed = urllib.parse.urlparse(raw)
    external_scheme_admitted = parsed.scheme in ADMITTED_EXTERNAL_DB_SCHEMES
    external_url_valid = external_scheme_admitted and bool(parsed.netloc)
    safe = bool(raw) and (sqlite_memory or external_url_valid or (sqlite_path is not None and inside is False))
    return {
        "database_env_var": DATABASE_ENV,
        "database_url_present": bool(raw),
        "database_url_marker": _marker(raw) if raw else None,
        "database_kind": "sqlite" if raw.startswith("sqlite:") else ("external" if raw else "missing"),
        "external_scheme_admitted": external_scheme_admitted,
        "external_url_valid": external_url_valid,
        "sqlite_memory": sqlite_memory,
        "sqlite_path_inside_repo_or_onedrive": inside,
        "database_safe_for_live_sec": safe,
        "raw_value_returned": False,
    }


def _limits(env: Mapping[str, str]) -> dict[str, Any]:
    rate = _int_or_default(env.get(RATE_ENV), 1)
    max_requests = _int_or_default(env.get(MAX_REQUESTS_ENV), 10)
    max_bytes = _int_or_default(env.get(MAX_BYTES_ENV), 25_000_000)
    timeout_seconds = _int_or_default(env.get(TIMEOUT_ENV), 20)
    return {
        "rate_env_var": RATE_ENV,
        "configured_requests_per_second": rate,
        "rate_limit_admitted": 1 <= rate <= 10,
        "max_live_requests_env_var": MAX_REQUESTS_ENV,
        "max_live_requests_per_process": max_requests,
        "max_live_requests_admitted": 1 <= max_requests <= 10,
        "max_bytes_env_var": MAX_BYTES_ENV,
        "max_bytes": max_bytes,
        "max_bytes_admitted": 1 <= max_bytes <= MAX_BYTES_CEILING,
        "max_bytes_ceiling": MAX_BYTES_CEILING,
        "timeout_seconds_env_var": TIMEOUT_ENV,
        "timeout_seconds": timeout_seconds,
        "timeout_seconds_admitted": 1 <= timeout_seconds <= TIMEOUT_SECONDS_CEILING,
        "timeout_seconds_ceiling": TIMEOUT_SECONDS_CEILING,
        "sec_fair_access_ceiling_per_second": 10,
        "default_requests_per_second_until_configured": 1,
    }


def _smoke_request_preflight(*, source_root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    cik = str(env.get(SMOKE_CIK_ENV) or "").strip().lstrip("0") or (
        "0" if str(env.get(SMOKE_CIK_ENV) or "").strip() else ""
    )
    accession = str(env.get(SMOKE_ACCESSION_ENV) or "").strip()
    form = str(env.get(SMOKE_FORM_ENV) or "").strip().upper()
    filing_date = str(env.get(SMOKE_DATE_ENV) or "").strip()
    confirmation = str(env.get(SMOKE_CONFIRM_ENV) or "").strip()
    valid_cik = bool(cik and CIK_RE.fullmatch(cik))
    valid_accession = bool(accession and ACCESSION_RE.fullmatch(accession))
    valid_form = bool(form and FORM_RE.fullmatch(form))
    valid_date = _valid_filing_date(filing_date)
    confirmed = _truthy(confirmation)
    source_identity_hash = (
        _source_identity_hash(cik=cik, accession=accession, form=form, filing_date=filing_date)
        if valid_cik and valid_accession and valid_form and valid_date
        else None
    )
    matching_existing_receipt = (
        _matching_existing_receipt_found(source_root=source_root, env=env, source_identity_hash=source_identity_hash)
        if source_identity_hash
        else False
    )
    return {
        "cik_env_var": SMOKE_CIK_ENV,
        "accession_env_var": SMOKE_ACCESSION_ENV,
        "form_type_env_var": SMOKE_FORM_ENV,
        "filing_date_env_var": SMOKE_DATE_ENV,
        "operator_confirmation_env_var": SMOKE_CONFIRM_ENV,
        "cik_present": bool(cik),
        "accession_present": bool(accession),
        "form_type_present": bool(form),
        "filing_date_present": bool(filing_date),
        "cik_shape_valid": valid_cik,
        "accession_shape_valid": valid_accession,
        "form_type_shape_valid": valid_form,
        "filing_date_shape_valid": valid_date,
        "operator_confirmation_true": confirmed,
        "source_identity_marker": source_identity_hash[:16] if source_identity_hash else None,
        "matching_existing_receipt_found": matching_existing_receipt,
        "form_type": form if valid_form else None,
        "filing_date": filing_date if valid_date else None,
        "request_ready": valid_cik
        and valid_accession
        and valid_form
        and valid_date
        and confirmed
        and matching_existing_receipt is False,
        "raw_identity_returned": False,
    }


def _valid_filing_date(value: str) -> bool:
    if not value or not FILING_DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _source_identity_hash(*, cik: str, accession: str, form: str, filing_date: str) -> str:
    return _stable_hash(
        {
            "hash_version": "sec_edgar_live_source_identity_hash_v1",
            "cik_or_filer_ref_hash": _sha256(cik),
            "accession_or_submission_id_hash": _sha256(accession),
            "form_type": form,
            "filing_date": filing_date,
        }
    )


def _matching_existing_receipt_found(
    *, source_root: Path, env: Mapping[str, str], source_identity_hash: str | None
) -> bool:
    if not source_identity_hash:
        return False
    raw_storage = str(env.get(STORAGE_ENV) or "").strip()
    if not raw_storage:
        return False
    receipts_dir = _normalise_storage_dir(source_root, raw_storage) / RECEIPT_DIR / "receipts"
    if not receipts_dir.exists():
        return False
    for path in sorted(receipts_dir.glob(f"{RECEIPT_PREFIX}-*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if receipt.get("source_identity_hash") == source_identity_hash:
            return True
    return False


def _normalise_storage_dir(source_root: Path, raw_storage: str) -> Path:
    candidate = Path(raw_storage)
    if not candidate.is_absolute():
        candidate = source_root / "backend" / candidate
    return candidate.resolve(strict=False)


def _sqlite_database_path(database_url: str, *, source_root: Path) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    raw_path = database_url[len(prefix) :].strip()
    if not raw_path or raw_path == ":memory:" or raw_path.startswith("file:"):
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = source_root / "backend" / candidate
    return candidate.resolve(strict=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_hash(value: Any) -> str:
    stable_json = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256(stable_json)


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


def _headline(*, ready: bool, blockers: list[dict[str, Any]]) -> str:
    if ready:
        return "Manual SEC live source-artifact smoke preflight is ready for one bounded operator-run filing."
    reasons = ", ".join(str(item.get("blocked_reason") or "") for item in blockers)
    return f"Manual SEC live source-artifact smoke preflight is blocked: {reasons}."


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _marker(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _int_or_default(value: str | None, default: int) -> int:
    try:
        return int(str(value or "").strip() or default)
    except ValueError:
        return -1


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
