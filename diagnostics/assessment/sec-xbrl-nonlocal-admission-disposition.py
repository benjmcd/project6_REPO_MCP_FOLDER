from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition-report.json")
READINESS_REPORT = "diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json"
ROUTE_ENFORCEMENT_DOC = "next_milestone_plans/Layer3_planning_docs/1326-auth-owner-binding-route-enforcement.md"
RECONCILIATION_DOC = "next_milestone_plans/Layer3_planning_docs/1327-nonlocal-readiness-in-app-reconciliation.md"
AUTH_BINDING_SERVICE = "backend/app/services/layer3_sec_xbrl_auth_binding.py"
API_FILE = "backend/app/api/layer3.py"
AUTH_BINDING_TEST = "backend/tests/test_sec_xbrl_auth_binding_receipt.py"
OPERATOR_WORKFLOW_TEST = "backend/tests/test_sec_xbrl_operator_review_workflow.py"
TARGET = "sec_xbrl_nonlocal_production_admission_or_historical_backfill_disposition_v1"
REDACTION_POLICY_ID = "sec_xbrl_nonlocal_admission_disposition_redaction_v1"
PACKET_DIR_ADMISSION_FILENAME = "sec-xbrl-final-admission-packet.json"
PACKET_DIR_BACKFILL_DISPOSITION_FILENAME = "sec-xbrl-backfill-disposition-packet.json"

ADMISSION_REQUIRED_FIELDS = (
    "admission_mode",
    "admission_owner_ref",
    "approval_record_ref",
    "approval_record_hash",
    "in_app_auth_evidence_ref",
    "in_app_auth_evidence_hash",
    "auth_binding_evidence_ref",
    "auth_binding_evidence_hash",
    "rollback_owner_ref",
    "incident_owner_ref",
    "redaction_policy_id",
    "verification_run_ref",
    "admission_provenance_ref",
    "admission_provenance_hash",
)
DISPOSITION_REQUIRED_FIELDS = (
    "disposition_mode",
    "disposition_owner_ref",
    "disposition_record_ref",
    "disposition_record_hash",
    "historical_inventory_ref",
    "historical_inventory_hash",
    "unbound_receipt_count",
    "backfill_required",
    "backfill_authority_ref",
    "backfill_authority_hash",
    "containment_policy_ref",
    "containment_policy_hash",
    "redaction_policy_id",
    "verification_run_ref",
    "disposition_provenance_ref",
    "disposition_provenance_hash",
)
PACKET_ALLOWED_FIELDS = {
    "admission": frozenset(ADMISSION_REQUIRED_FIELDS),
    "backfill_disposition": frozenset(DISPOSITION_REQUIRED_FIELDS),
}
UNKNOWN_PACKET_FIELD = "unexpected_packet_field"
HASH_FIELDS = {
    "approval_record_hash",
    "in_app_auth_evidence_hash",
    "auth_binding_evidence_hash",
    "admission_provenance_hash",
    "disposition_record_hash",
    "historical_inventory_hash",
    "backfill_authority_hash",
    "containment_policy_hash",
    "disposition_provenance_hash",
}
ALLOWED_ADMISSION_MODES = {"nonlocal_in_app_auth_final_admission"}
ALLOWED_DISPOSITION_MODES = {
    "no_historical_unbound_receipts",
    "historical_unbound_receipts_fail_closed_pending_backfill",
    "historical_unbound_receipts_backfill_authorized",
}

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
REDACTED_REF_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*-ref-[a-z0-9]+(?:-[a-z0-9]+)*$")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
CIK_RE = re.compile(r'(?:"cik"|\bcik\b)\s*[:=]\s*"?\d{1,10}"?', re.IGNORECASE)
BARE_CIK_RE = re.compile(r"(?<![A-Za-z0-9_])\d{6,10}(?![A-Za-z0-9_])")
RAW_CIK_RE = re.compile(f"(?:{CIK_RE.pattern})|(?:{BARE_CIK_RE.pattern})", re.IGNORECASE)
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov/", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|file://|/Users/|/home/)")
PERIOD_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
RAW_DECIMAL_RE = re.compile(r"(?<![A-Za-z0-9_])-?\d+\.\d+(?![A-Za-z0-9_])")
RAW_KEYS = {
    "accession",
    "amount",
    "cik",
    "company_name",
    "email",
    "issuer",
    "issuer_name",
    "local_path",
    "magnitude",
    "operator_email",
    "payload",
    "raw_identity",
    "raw_path",
    "raw_sidecar_payload",
    "raw_value",
    "raw_value_store_payload",
    "residual_magnitude",
    "sec_url",
    "sidecar_payload",
    "value",
    "value_store_payload",
}
FORBIDDEN_PAYLOAD_CLASSES = (
    "raw_operator_identity",
    "issuer_identity",
    "accession",
    "cik",
    "sec_url",
    "local_path",
    "period_date",
    "raw_value",
    "raw_payload",
    "residual_magnitude",
    "free_text_deployment_note",
    "local_evidence_filename",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--admission-packet", default=None)
    parser.add_argument("--backfill-disposition", default=None)
    parser.add_argument("--packet-dir", default=None)
    args = parser.parse_args(argv)
    if args.packet_dir and (args.admission_packet or args.backfill_disposition):
        parser.error("--packet-dir cannot be combined with --admission-packet or --backfill-disposition")
    admission_packet_path = args.admission_packet
    backfill_disposition_path = args.backfill_disposition
    if args.packet_dir:
        packet_dir = Path(args.packet_dir)
        admission_packet_path = packet_dir / PACKET_DIR_ADMISSION_FILENAME
        backfill_disposition_path = packet_dir / PACKET_DIR_BACKFILL_DISPOSITION_FILENAME

    report = build_report(
        admission_packet_path=admission_packet_path,
        backfill_disposition_path=backfill_disposition_path,
    )
    output = ROOT / args.output
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def build_report(
    admission_packet_path: str | Path | None = None,
    backfill_disposition_path: str | Path | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    readiness = _load_json(root / READINESS_REPORT)
    sources = {
        "route_doc": _read(root / ROUTE_ENFORCEMENT_DOC),
        "reconciliation_doc": _read(root / RECONCILIATION_DOC),
        "auth_binding_service": _read(root / AUTH_BINDING_SERVICE),
        "api": _read(root / API_FILE),
        "auth_binding_tests": _read(root / AUTH_BINDING_TEST),
        "operator_workflow_tests": _read(root / OPERATOR_WORKFLOW_TEST),
    }
    admission = _packet_summary(
        admission_packet_path,
        required_fields=ADMISSION_REQUIRED_FIELDS,
        packet_kind="admission",
    )
    disposition = _packet_summary(
        backfill_disposition_path,
        required_fields=DISPOSITION_REQUIRED_FIELDS,
        packet_kind="backfill_disposition",
    )
    readiness_current = _readiness_evidence_current(readiness)
    route_evidence = _route_and_backfill_evidence_summary(sources, root=root)
    admission_ok = admission["admissible"]
    disposition_ok = disposition["admissible"]
    criteria = [
        _criterion(
            "readiness_gate_current_for_admission_disposition",
            readiness_current["admissible"],
            readiness_current,
            "sec_xbrl_nonlocal_admission_readiness_gate_not_current",
        ),
        _criterion(
            "route_atomicity_and_fail_closed_evidence_current",
            route_evidence["admissible"],
            route_evidence,
            "sec_xbrl_nonlocal_admission_route_atomicity_evidence_missing",
        ),
        _criterion(
            "final_admission_packet_present_and_admissible",
            admission_ok,
            admission,
            admission["blocked_reason"],
        ),
        _criterion(
            "historical_backfill_disposition_present_and_admissible",
            disposition_ok,
            disposition,
            disposition["blocked_reason"],
        ),
        _criterion(
            "standing_non_admissions_preserved",
            _standing_non_admissions_preserved(readiness),
            {
                "production_readiness_claimed": False,
                "source_acquisition_performed_by_gate": False,
                "arelle_subprocess_invoked_by_gate": False,
                "value_reveal_default_enabled_by_gate": False,
                "export_or_delivery_enabled_by_gate": False,
                "provider_or_connector_dispatch_enabled_by_gate": False,
                "historical_backfill_performed_by_gate": False,
            },
            "sec_xbrl_nonlocal_admission_standing_non_admissions_regressed",
        ),
    ]
    blocking_reasons = [
        criterion["blocked_reason"]
        for criterion in criteria
        if criterion["state"] == "blocked" and criterion["blocked_reason"]
    ]

    return {
        "schema_id": "diagnostics.sec_xbrl_nonlocal_admission_disposition.v1",
        "target": TARGET,
        "decision": (
            "nonlocal_production_admission_disposition_ready_for_operator_review"
            if not blocking_reasons
            else "nonlocal_production_admission_disposition_blocked"
        ),
        "headline": (
            "Final nonlocal admission and historical backfill disposition are both admissible for operator review; "
            "this diagnostic still performs no production enablement."
            if not blocking_reasons
            else "Final nonlocal admission or historical backfill disposition authority is missing; current repo state remains blocked and validate-only."
        ),
        "blocking_reasons": blocking_reasons,
        "criteria": criteria,
        "readiness_gate_summary": readiness_current,
        "route_and_backfill_evidence_summary": route_evidence,
        "final_admission_packet_summary": admission,
        "historical_backfill_disposition_summary": disposition,
        "operator_packet_contract": _operator_packet_contract(),
        "production_readiness_claimed": False,
        "next_slice": (
            "sec_xbrl_nonlocal_production_readiness_operator_review_v1"
            if not blocking_reasons
            else "sec_xbrl_nonlocal_final_admission_packet_and_backfill_disposition_v1"
        ),
        "non_goals_preserved": {
            "runtime_behavior_changed_by_gate": False,
            "runtime_default_changed_by_gate": False,
            "schema_models_changed_by_gate": False,
            "migration_changed_by_gate": False,
            "durable_persistence_changed_by_gate": False,
            "backend_api_contract_changed_by_gate": False,
            "rendered_ui_changed_by_gate": False,
            "operator_workflow_changed_by_gate": False,
            "source_acquisition_performed_by_gate": False,
            "arelle_subprocess_invoked_by_gate": False,
            "live_sec_network_run_performed_by_gate": False,
            "value_reveal_default_enabled_by_gate": False,
            "controlled_value_reveal_submit_default_enabled_by_gate": False,
            "raw_internal_value_store_default_enabled_by_gate": False,
            "export_or_delivery_enabled_by_gate": False,
            "provider_or_connector_dispatch_enabled_by_gate": False,
            "historical_backfill_performed_by_gate": False,
            "raw_runtime_artifacts_added_by_gate": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "source_reports": {
            "nonlocal_readiness_gate": READINESS_REPORT,
        },
        "source_documents": {
            "route_enforcement": ROUTE_ENFORCEMENT_DOC,
            "readiness_reconciliation": RECONCILIATION_DOC,
        },
    }


def _operator_packet_contract() -> dict[str, Any]:
    return {
        "contract_id": "sec_xbrl_nonlocal_final_admission_packet_contract_v1",
        "redaction_policy_id": REDACTION_POLICY_ID,
        "validation_command": (
            "python diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py "
            "--admission-packet <admission-packet.json> "
            "--backfill-disposition <backfill-disposition.json> "
            "--output <report.json>"
        ),
        "packet_dir_validation_command": (
            "python diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py "
            "--packet-dir <packet-directory> "
            "--output <report.json>"
        ),
        "packet_directory": {
            "cli_argument": "--packet-dir",
            "required_filenames": {
                "admission_packet": PACKET_DIR_ADMISSION_FILENAME,
                "backfill_disposition_packet": PACKET_DIR_BACKFILL_DISPOSITION_FILENAME,
            },
            "cannot_combine_with": ["--admission-packet", "--backfill-disposition"],
            "files_are_operator_supplied": True,
            "files_are_committed_to_repo": False,
        },
        "success_decision": "nonlocal_production_admission_disposition_ready_for_operator_review",
        "blocked_decision": "nonlocal_production_admission_disposition_blocked",
        "production_readiness_claimed_by_success": False,
        "packet_files_are_operator_supplied": True,
        "packet_files_are_committed_to_repo": False,
        "unknown_fields": {
            "admitted": False,
            "reported_as": UNKNOWN_PACKET_FIELD,
        },
        "hash_rule": "64 lowercase hexadecimal characters",
        "redacted_ref_rule": (
            "nonempty lowercase kebab-case reference ending in -ref-<token>, "
            "with no operator identity, issuer identity, accession, CIK, SEC URL, "
            "local path, period date, raw decimal, raw value, or payload"
        ),
        "forbidden_payload_classes": list(FORBIDDEN_PAYLOAD_CLASSES),
        "admission_packet": _packet_contract(
            cli_argument="--admission-packet",
            packet_kind="admission",
            required_fields=ADMISSION_REQUIRED_FIELDS,
            allowed_modes=ALLOWED_ADMISSION_MODES,
            mode_field="admission_mode",
            mode_requirements={
                "nonlocal_in_app_auth_final_admission": (
                    "final redacted operator authority admits current nonlocal in-app auth evidence "
                    "for operator review only"
                ),
            },
        ),
        "backfill_disposition_packet": _packet_contract(
            cli_argument="--backfill-disposition",
            packet_kind="backfill_disposition",
            required_fields=DISPOSITION_REQUIRED_FIELDS,
            allowed_modes=ALLOWED_DISPOSITION_MODES,
            mode_field="disposition_mode",
            mode_requirements={
                "no_historical_unbound_receipts": (
                    "unbound_receipt_count must equal 0 and backfill_required must be false"
                ),
                "historical_unbound_receipts_fail_closed_pending_backfill": (
                    "unbound_receipt_count must be greater than 0 and backfill_required must be true"
                ),
                "historical_unbound_receipts_backfill_authorized": (
                    "unbound_receipt_count must be greater than 0 and backfill_required must be true"
                ),
            },
        ),
    }


def _packet_contract(
    *,
    cli_argument: str,
    packet_kind: str,
    required_fields: tuple[str, ...],
    allowed_modes: set[str],
    mode_field: str,
    mode_requirements: dict[str, str],
) -> dict[str, Any]:
    return {
        "cli_argument": cli_argument,
        "packet_kind": packet_kind,
        "required_fields": list(required_fields),
        "allowed_fields": list(required_fields),
        "mode_field": mode_field,
        "allowed_modes": sorted(allowed_modes),
        "mode_requirements": mode_requirements,
        "hash_fields": [field for field in required_fields if field in HASH_FIELDS],
        "redacted_ref_fields": [field for field in required_fields if field.endswith("_ref")],
        "redaction_policy_field": "redaction_policy_id",
        "redaction_policy_id": REDACTION_POLICY_ID,
    }


def _readiness_evidence_current(readiness: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "readiness_decision_blocked": readiness.get("decision") == "nonlocal_production_readiness_blocked",
        "only_final_admission_blocking": readiness.get("blocking_reasons")
        == ["nonlocal_production_readiness_final_admission_missing"],
        "in_app_auth_evidence_current": readiness.get("in_app_auth_evidence_summary", {}).get("admissible")
        is True,
        "production_readiness_not_claimed": readiness.get("production_readiness_claimed") is False,
        "next_slice_matches": readiness.get("next_slice") == TARGET,
    }
    blockers = [
        f"sec_xbrl_nonlocal_admission_readiness_{name}_missing"
        for name, passed in checks.items()
        if not passed
    ]
    return {
        "admissible": not blockers,
        "blocked_reasons": blockers,
        "evidence_checks": checks,
        "source_report": READINESS_REPORT,
        "source_report_hash": _file_hash(ROOT / READINESS_REPORT),
        "readiness_decision": readiness.get("decision"),
        "readiness_blocking_reasons": readiness.get("blocking_reasons"),
    }


def _route_and_backfill_evidence_summary(sources: Mapping[str, str], *, root: Path) -> dict[str, Any]:
    tests = sources["auth_binding_tests"] + "\n" + sources["operator_workflow_tests"]
    checks = {
        "route_doc_records_historical_backfill_boundary": _all_tokens(
            sources["route_doc"],
            (
                "historical unbound receipts",
                "repair/backfill authority question",
                "protected mutating routes now defer source-receipt service commits",
            ),
        ),
        "reconciliation_doc_names_next_disposition": TARGET in sources["reconciliation_doc"],
        "auth_binding_service_requires_owner_binding": _all_tokens(
            sources["auth_binding_service"],
            (
                "def require_sec_xbrl_owner_binding",
                "sec_xbrl_auth_binding_missing",
                "sec_xbrl_auth_binding_context_mismatch",
                "compatible_policy_hashes",
            ),
        ),
        "api_records_source_and_binding_atomically": _all_tokens(
            sources["api"],
            (
                "_sec_xbrl_record_binding",
                "sec_xbrl_auth_binding_atomic_commit_failed",
                "source_auth_binding_ref",
                "auth_binding_required",
            ),
        ),
        "tests_prove_fail_closed_unbound_and_rollback": _all_tokens(
            tests,
            (
                "test_operator_review_workflow_status_api_requires_auth_binding_for_existing_workflow",
                "test_value_reveal_authority_api_rolls_back_source_receipt_when_binding_fails",
                "test_controlled_value_reveal_submit_api_rolls_back_source_receipt_when_binding_fails",
            ),
        ),
    }
    blockers = [
        f"sec_xbrl_nonlocal_admission_route_evidence_{name}_missing"
        for name, passed in checks.items()
        if not passed
    ]
    return {
        "admissible": not blockers,
        "blocked_reasons": blockers,
        "evidence_checks": checks,
        "source_files": {
            "route_enforcement_doc": ROUTE_ENFORCEMENT_DOC,
            "readiness_reconciliation_doc": RECONCILIATION_DOC,
            "auth_binding_service": AUTH_BINDING_SERVICE,
            "api": API_FILE,
            "auth_binding_tests": AUTH_BINDING_TEST,
            "operator_workflow_tests": OPERATOR_WORKFLOW_TEST,
        },
        "source_hashes": {
            "auth_binding_service": _file_hash(root / AUTH_BINDING_SERVICE),
            "api": _file_hash(root / API_FILE),
            "route_enforcement_doc": _file_hash(root / ROUTE_ENFORCEMENT_DOC),
            "readiness_reconciliation_doc": _file_hash(root / RECONCILIATION_DOC),
        },
        "historical_backfill_performed_by_gate": False,
    }


def _packet_summary(
    packet_path: str | Path | None,
    *,
    required_fields: tuple[str, ...],
    packet_kind: str,
) -> dict[str, Any]:
    if packet_path is None:
        return {
            "packet_kind": packet_kind,
            "packet_present": False,
            "packet_hash": None,
            "required_fields_present": [],
            "required_fields_missing": list(required_fields),
            "invalid_required_fields": [],
            "admissible": False,
            "redaction_scan": {"status": "not_run", "hit_classes": []},
            "blocked_reason": f"sec_xbrl_nonlocal_{packet_kind}_packet_missing",
        }
    path = Path(packet_path)
    if not path.is_file():
        return {
            "packet_kind": packet_kind,
            "packet_present": False,
            "packet_hash": None,
            "required_fields_present": [],
            "required_fields_missing": list(required_fields),
            "invalid_required_fields": [],
            "admissible": False,
            "redaction_scan": {"status": "not_run", "hit_classes": []},
            "blocked_reason": f"sec_xbrl_nonlocal_{packet_kind}_packet_missing",
        }
    try:
        text = path.read_text(encoding="utf-8-sig")
        packet = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return {
            "packet_kind": packet_kind,
            "packet_present": True,
            "packet_hash": None,
            "required_fields_present": [],
            "required_fields_missing": list(required_fields),
            "invalid_required_fields": [],
            "admissible": False,
            "redaction_scan": {"status": "failed_closed", "hit_classes": []},
            "blocked_reason": f"sec_xbrl_nonlocal_{packet_kind}_packet_unreadable",
        }
    if not isinstance(packet, dict):
        return {
            "packet_kind": packet_kind,
            "packet_present": True,
            "packet_hash": _stable_hash(packet),
            "required_fields_present": [],
            "required_fields_missing": list(required_fields),
            "invalid_required_fields": [],
            "admissible": False,
            "redaction_scan": {"status": "failed_closed", "hit_classes": []},
            "blocked_reason": f"sec_xbrl_nonlocal_{packet_kind}_packet_invalid_shape",
        }
    missing = [field for field in required_fields if field not in packet]
    present = [field for field in required_fields if field in packet]
    invalid = _invalid_packet_fields(packet, packet_kind=packet_kind)
    raw_hits = sorted(set(_redaction_hit_classes(text, packet)))
    blocked_reason = None
    if raw_hits:
        blocked_reason = f"sec_xbrl_nonlocal_{packet_kind}_raw_authority_not_admitted"
    elif missing:
        blocked_reason = f"sec_xbrl_nonlocal_{packet_kind}_packet_missing_required_fields"
    elif invalid:
        blocked_reason = f"sec_xbrl_nonlocal_{packet_kind}_packet_invalid_required_fields"
    return {
        "packet_kind": packet_kind,
        "packet_present": True,
        "packet_hash": _stable_hash(packet),
        "required_fields_present": present,
        "required_fields_missing": missing,
        "invalid_required_fields": invalid,
        "admissible": blocked_reason is None,
        "redaction_scan": {
            "status": "failed_closed" if raw_hits else "passed",
            "hit_classes": raw_hits,
        },
        "blocked_reason": blocked_reason,
        "mode": packet.get("admission_mode") or packet.get("disposition_mode"),
        "unbound_receipt_count": packet.get("unbound_receipt_count")
        if packet_kind == "backfill_disposition"
        else None,
    }


def _invalid_packet_fields(packet: Mapping[str, Any], *, packet_kind: str) -> list[str]:
    invalid: list[str] = []
    allowed_fields = PACKET_ALLOWED_FIELDS[packet_kind]
    allowed_modes = (
        ALLOWED_ADMISSION_MODES
        if packet_kind == "admission"
        else ALLOWED_DISPOSITION_MODES
    )
    mode_field = "admission_mode" if packet_kind == "admission" else "disposition_mode"
    if packet.get(mode_field) not in allowed_modes:
        invalid.append(mode_field)
    if packet.get("redaction_policy_id") != REDACTION_POLICY_ID:
        invalid.append("redaction_policy_id")
    for field, value in packet.items():
        if field not in allowed_fields:
            invalid.append(UNKNOWN_PACKET_FIELD)
            continue
        if field in HASH_FIELDS and not _hash(value):
            invalid.append(field)
        if field.endswith("_ref") and not _redacted_ref(value):
            invalid.append(field)
    if packet_kind == "backfill_disposition":
        count = packet.get("unbound_receipt_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            invalid.append("unbound_receipt_count")
        mode = packet.get("disposition_mode")
        backfill_required = packet.get("backfill_required")
        if mode == "no_historical_unbound_receipts" and (count != 0 or backfill_required is not False):
            invalid.extend(["disposition_mode", "backfill_required"])
        if mode == "historical_unbound_receipts_fail_closed_pending_backfill" and (
            not isinstance(count, int) or count <= 0 or backfill_required is not True
        ):
            invalid.extend(["disposition_mode", "backfill_required"])
        if mode == "historical_unbound_receipts_backfill_authorized" and (
            not isinstance(count, int) or count <= 0 or backfill_required is not True
        ):
            invalid.extend(["disposition_mode", "backfill_required"])
    return sorted(set(invalid))


def _redaction_hit_classes(packet_text: str, packet: Any) -> list[str]:
    hits: list[str] = []
    regexes = {
        "raw_operator_email": EMAIL_RE,
        "raw_accession": ACCESSION_RE,
        "raw_cik": RAW_CIK_RE,
        "sec_url": SEC_URL_RE,
        "local_path": LOCAL_PATH_RE,
        "raw_period_date": PERIOD_DATE_RE,
        "raw_decimal_or_residual_magnitude": RAW_DECIMAL_RE,
    }
    for name, regex in regexes.items():
        if regex.search(packet_text):
            hits.append(name)
    if isinstance(packet, dict):
        for field, value in packet.items():
            if str(field).endswith("_ref") and not _redacted_ref(value):
                hits.append("raw_or_unreduced_authority_ref")
    for key in _iter_keys(packet):
        if key.lower() in RAW_KEYS:
            hits.append("raw_or_local_authority_key")
    return hits


def _standing_non_admissions_preserved(readiness: Mapping[str, Any]) -> bool:
    non_goals = readiness.get("non_goals_preserved", {})
    return all(
        non_goals.get(key) is False
        for key in (
            "source_acquisition_performed_by_gate",
            "arelle_subprocess_invoked_by_gate",
            "live_sec_network_run_performed_by_gate",
            "value_reveal_default_enabled_by_gate",
            "controlled_value_reveal_submit_default_enabled_by_gate",
            "raw_internal_value_store_default_enabled_by_gate",
            "export_or_delivery_enabled_by_gate",
            "provider_or_connector_dispatch_enabled_by_gate",
            "production_readiness_claimed",
        )
    )


def _criterion(
    name: str,
    passed: bool,
    evidence: dict[str, Any],
    blocked_reason: str | None,
) -> dict[str, Any]:
    return {
        "criterion": name,
        "state": "passed" if passed else "blocked",
        "evidence": evidence,
        "blocked_reason": None if passed else blocked_reason,
    }


def _redacted_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and bool(REDACTED_REF_RE.fullmatch(value.strip()))
        and not any(
            regex.search(value)
            for regex in (
                EMAIL_RE,
                ACCESSION_RE,
                CIK_RE,
                BARE_CIK_RE,
                SEC_URL_RE,
                LOCAL_PATH_RE,
                PERIOD_DATE_RE,
                RAW_DECIMAL_RE,
            )
        )
    )


def _hash(value: Any) -> bool:
    return isinstance(value, str) and bool(HASH_RE.fullmatch(value))


def _all_tokens(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


def _iter_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, nested in value.items():
            keys.append(str(key))
            keys.extend(_iter_keys(nested))
        return keys
    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_iter_keys(item))
        return keys
    return []


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _file_hash(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    raise SystemExit(main())
