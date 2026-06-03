from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = Path(__file__).resolve().parent
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))

from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_diagnostic_framework import redaction_hit_classes as _framework_redaction_hit_classes  # noqa: E402

DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json")
RUNTIME_REPORT = "diagnostics/assessment/sec-xbrl-default-on-runtime-report.json"
IN_APP_AUTH_POLICY_REPORT = "diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json"
AUTH_OWNER_BINDING_STRATEGY_REPORT = "diagnostics/assessment/sec-xbrl-auth-owner-binding-strategy-report.json"
DESIGN_DOC = "next_milestone_plans/Layer3_planning_docs/1319-nonlocal-production-readiness.md"
IN_APP_AUTH_DOC = "next_milestone_plans/Layer3_planning_docs/1321-in-app-auth.md"
AUTH_ROUTE_ENFORCEMENT_DOC = "next_milestone_plans/Layer3_planning_docs/1326-auth-owner-binding-route-enforcement.md"
IN_APP_AUTH_POLICY_SERVICE = "backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py"
AUTH_BINDING_SERVICE = "backend/app/services/layer3_sec_xbrl_auth_binding.py"
AUTH_BINDING_TEST = "backend/tests/test_sec_xbrl_auth_binding_receipt.py"
OPERATOR_WORKFLOW_TEST = "backend/tests/test_sec_xbrl_operator_review_workflow.py"
TARGET = "sec_xbrl_default_on_nonlocal_production_readiness_gate_v1"
REDACTION_POLICY_ID = "sec_xbrl_nonlocal_production_readiness_gate_redaction_v1"

REQUIRED_AUTHORITY_FIELDS = (
    "deployment_mode",
    "deployment_owner_ref",
    "approval_record_ref",
    "approval_record_hash",
    "proxy_boundary_mode",
    "proxy_identity_header",
    "allowed_origins_policy_hash",
    "storage_exposure_policy",
    "arelle_fact_authority_nonlocal_authorized",
    "rollback_owner_ref",
    "incident_owner_ref",
    "redaction_policy_id",
    "verification_run_ref",
    "deployment_authority_provenance_ref",
    "deployment_authority_provenance_hash",
)
HASH_FIELDS = (
    "approval_record_hash",
    "allowed_origins_policy_hash",
    "deployment_authority_provenance_hash",
)
REF_FIELDS = (
    "deployment_owner_ref",
    "approval_record_ref",
    "rollback_owner_ref",
    "incident_owner_ref",
    "verification_run_ref",
    "deployment_authority_provenance_ref",
)
ALLOWED_PROXY_BOUNDARY_MODES = {"trusted_external_proxy"}
ALLOWED_STORAGE_EXPOSURE_POLICIES = {"auto", "disabled"}

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
    "raw_sidecar_payload",
    "raw_value",
    "raw_value_store_payload",
    "residual_magnitude",
    "sec_url",
    "sidecar_payload",
    "value",
    "value_store_payload",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--authority-packet", default=None)
    args = parser.parse_args(argv)

    report = build_report(authority_packet_path=args.authority_packet)
    output = ROOT / args.output
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def build_report(
    authority_packet_path: str | Path | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    runtime_report = _load_json(root / RUNTIME_REPORT)
    in_app_auth_policy_report = _load_json(root / IN_APP_AUTH_POLICY_REPORT)
    auth_owner_binding_strategy_report = _load_json(root / AUTH_OWNER_BINDING_STRATEGY_REPORT)
    sources = {
        "config": _read(root / "backend/app/core/config.py"),
        "api": _read(root / "backend/app/api/layer3.py"),
        "api_tests": _read(root / "backend/tests/test_layer3_api.py"),
        "runtime_report": runtime_report,
        "in_app_auth_policy_report": in_app_auth_policy_report,
        "auth_owner_binding_strategy_report": auth_owner_binding_strategy_report,
        "design_doc": _read(root / DESIGN_DOC),
        "in_app_auth_doc": _read(root / IN_APP_AUTH_DOC),
        "auth_route_enforcement_doc": _read(root / AUTH_ROUTE_ENFORCEMENT_DOC),
        "in_app_auth_policy_service": _read(root / IN_APP_AUTH_POLICY_SERVICE),
        "auth_binding_service": _read(root / AUTH_BINDING_SERVICE),
        "auth_binding_tests": _read(root / AUTH_BINDING_TEST),
        "operator_workflow_tests": _read(root / OPERATOR_WORKFLOW_TEST),
    }
    authority = _authority_packet_summary(authority_packet_path)
    in_app_auth = _in_app_auth_evidence_summary(sources, root=root)

    default_runtime_clean = (
        runtime_report.get("decision") == "default_on_runtime_enabled"
        and runtime_report.get("blocking_reasons") == []
        and runtime_report.get("non_goals_preserved", {}).get("production_readiness_claimed") is False
    )
    nonlocal_guardrails = _nonlocal_guardrails_hold(sources["config"], sources["api_tests"])
    non_admitted_surfaces = _non_admitted_surfaces_hold(sources)
    production_claim_separated = (
        "The next admissible implementation should be a validate-first nonlocal"
        in sources["design_doc"]
        and "production-readiness overclaim" in sources["design_doc"]
        and "production_readiness_claimed" in json.dumps(runtime_report, sort_keys=True)
    )
    authority_or_in_app_evidence = authority["admissible"] or (
        not authority["authority_packet_present"] and in_app_auth["admissible"]
    )
    authority_or_in_app_blocker = None
    if not authority_or_in_app_evidence:
        authority_or_in_app_blocker = (
            authority["blocked_reason"]
            or "nonlocal_production_readiness_in_app_auth_evidence_not_current"
        )
    final_production_admission = authority["admissible"]

    criteria = [
        _criterion(
            "current_default_on_runtime_evidence_clean",
            default_runtime_clean,
            {
                "source_report": RUNTIME_REPORT,
                "decision": runtime_report.get("decision"),
                "blocking_reasons_count": len(runtime_report.get("blocking_reasons", [])),
                "runtime_report_hash": _file_hash(root / RUNTIME_REPORT),
            },
            "nonlocal_production_readiness_default_on_runtime_evidence_not_clean",
        ),
        _criterion(
            "nonlocal_proxy_guardrails_fail_closed",
            nonlocal_guardrails,
            {
                "config_file": "backend/app/core/config.py",
                "test_file": "backend/tests/test_layer3_api.py",
                "requires_https_origins": True,
                "requires_proxy_owner": True,
                "requires_trusted_proxy": True,
                "requires_proxy_identity_header": True,
                "blocks_direct_storage_exposure": True,
                "requires_explicit_arelle_nonlocal_authorization": True,
            },
            "nonlocal_production_readiness_nonlocal_guardrails_missing",
        ),
        _criterion(
            "authority_packet_or_in_app_auth_fork_evidence_present",
            authority_or_in_app_evidence,
            {
                "authority_packet_admissible": authority["admissible"],
                "authority_packet_present": authority["authority_packet_present"],
                "in_app_auth_evidence_admissible": in_app_auth["admissible"],
                "selected_current_fork": (
                    "external_authority_packet"
                    if authority["admissible"]
                    else "repo_owned_in_app_auth"
                    if in_app_auth["admissible"] and not authority["authority_packet_present"]
                    else "blocked"
                ),
                "authority_packet_summary": authority,
            },
            authority_or_in_app_blocker,
        ),
        _criterion(
            "in_app_auth_fork_evidence_current",
            in_app_auth["admissible"],
            in_app_auth,
            "nonlocal_production_readiness_in_app_auth_evidence_not_current",
        ),
        _criterion(
            "final_nonlocal_production_admission_present",
            final_production_admission,
            {
                "authority_packet_admissible": authority["admissible"],
                "in_app_auth_evidence_admissible": in_app_auth["admissible"],
                "production_readiness_claimed": False,
                "admission_boundary": (
                    "external_authority_packet"
                    if authority["admissible"]
                    else "operator_nonlocal_production_admission_required_after_in_app_auth"
                ),
            },
            "nonlocal_production_readiness_final_admission_missing",
        ),
        _criterion(
            "standing_non_admissions_preserved",
            non_admitted_surfaces,
            {
                "value_reveal_default_enabled": False,
                "controlled_value_reveal_submit_default_enabled": False,
                "raw_internal_value_store_default_enabled": False,
                "corpus_validation_arelle_default_enabled": False,
                "source_acquisition_performed_by_gate": False,
                "arelle_subprocess_invoked_by_gate": False,
                "export_or_delivery_enabled_by_gate": False,
                "provider_or_connector_dispatch_enabled_by_gate": False,
            },
            "nonlocal_production_readiness_standing_non_admissions_regressed",
        ),
        _criterion(
            "production_readiness_claim_separated_from_gate",
            production_claim_separated,
            {
                "design_doc": DESIGN_DOC,
                "production_readiness_claimed": False,
                "readiness_gate_is_validate_only": True,
                "actual_nonlocal_enablement_admitted": False,
            },
            "nonlocal_production_readiness_claim_boundary_ambiguous",
        ),
    ]
    blocking_reasons = [
        criterion["blocked_reason"]
        for criterion in criteria
        if criterion["state"] == "blocked" and criterion["blocked_reason"]
    ]

    return {
        "schema_id": "diagnostics.sec_xbrl_nonlocal_production_readiness_gate.v1",
        "target": TARGET,
        "decision": (
            "nonlocal_production_readiness_authority_admitted"
            if not blocking_reasons
            else "nonlocal_production_readiness_blocked"
        ),
        "headline": (
            "Nonlocal production-readiness authority is admitted as redacted deployment evidence, "
            "but this diagnostic still performs no runtime enablement."
            if not blocking_reasons
            else "Nonlocal production-readiness authority is not admitted; current repo evidence remains "
            "validate-only and production readiness is not claimed."
        ),
        "criteria": criteria,
        "blocking_reasons": blocking_reasons,
        "authority_packet_summary": authority,
        "in_app_auth_evidence_summary": in_app_auth,
        "production_readiness_claimed": False,
        "inherited_default_on_runtime_evidence": {
            "source_report": RUNTIME_REPORT,
            "decision": runtime_report.get("decision"),
            "next_slice": runtime_report.get("next_slice"),
            "blocking_reasons_count": len(runtime_report.get("blocking_reasons", [])),
            "runtime_report_hash": _file_hash(root / RUNTIME_REPORT),
        },
        "nonlocal_runtime_boundary": {
            "deployment_mode_required": "nonlocal",
            "auth_owner_required": "proxy",
            "trusted_proxy_mode_required": True,
            "proxy_identity_header_name_required": True,
            "allowed_origins_policy": "explicit_https_only",
            "storage_exposure_allowed": ["auto", "disabled"],
            "arelle_fact_authority_nonlocal_authorized_required": True,
            "in_app_auth_implemented_by_gate": False,
            "in_app_auth_implementation_evidence_present": in_app_auth["admissible"],
            "direct_storage_exposure_admitted": False,
        },
        "non_goals_preserved": {
            "runtime_behavior_changed_by_gate": False,
            "runtime_default_changed_by_gate": False,
            "schema_models_changed_by_gate": False,
            "migration_changed_by_gate": False,
            "durable_persistence_changed_by_gate": False,
            "backend_api_contract_changed_by_gate": False,
            "rendered_ui_changed_by_gate": False,
            "operator_workflow_changed_by_gate": False,
            "value_reveal_default_enabled_by_gate": False,
            "controlled_value_reveal_submit_default_enabled_by_gate": False,
            "raw_internal_value_store_default_enabled_by_gate": False,
            "source_acquisition_performed_by_gate": False,
            "arelle_subprocess_invoked_by_gate": False,
            "live_sec_network_run_performed_by_gate": False,
            "export_or_delivery_enabled_by_gate": False,
            "provider_or_connector_dispatch_enabled_by_gate": False,
            "raw_runtime_artifacts_added_by_gate": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "source_reports": {
            "default_on_runtime": RUNTIME_REPORT,
            "in_app_auth_policy_validation": IN_APP_AUTH_POLICY_REPORT,
            "auth_owner_binding_strategy": AUTH_OWNER_BINDING_STRATEGY_REPORT,
        },
        "source_documents": {
            "nonlocal_readiness_design": DESIGN_DOC,
            "in_app_auth_design": IN_APP_AUTH_DOC,
            "auth_route_enforcement": AUTH_ROUTE_ENFORCEMENT_DOC,
        },
        "next_slice": (
            "sec_xbrl_nonlocal_production_admission_or_historical_backfill_disposition_v1"
            if blocking_reasons
            else "sec_xbrl_nonlocal_production_readiness_operator_review_v1"
        ),
    }


def _in_app_auth_evidence_summary(sources: dict[str, Any], *, root: Path) -> dict[str, Any]:
    policy_report = sources["in_app_auth_policy_report"]
    strategy_report = sources["auth_owner_binding_strategy_report"]
    policy_report_clean = (
        policy_report.get("decision") == "sec_xbrl_in_app_auth_policy_validation_passed"
        and policy_report.get("blocking_reasons") == []
        and policy_report.get("non_goals_preserved", {}).get("production_readiness_claimed") is False
    )
    strategy_report_clean = (
        strategy_report.get("decision") == "sec_xbrl_auth_owner_binding_strategy_selected"
        and strategy_report.get("blocking_reasons") == []
        and strategy_report.get("selected_strategy")
        == "separate_hash_only_auth_binding_receipt_table"
    )
    policy_service_current = _all_tokens(
        sources["in_app_auth_policy_service"],
        (
            "PROTECTED_ROUTE_FAMILIES",
            "sec_xbrl_controlled_value_reveal_submit_write",
            "sec_xbrl_controlled_value_reveal_submit_status_read",
            "FORBIDDEN_REQUEST_FIELDS",
            "AUTH_OWNER=proxy requires TRUSTED_PROXY_MODE=true",
            "compatible_policy_hashes",
            "raw_value_exposed",
            "residual_magnitude_exposed",
        ),
    )
    binding_service_current = _all_tokens(
        sources["auth_binding_service"],
        (
            "def record_sec_xbrl_auth_binding",
            "def require_sec_xbrl_owner_binding",
            "SOURCE_ROUTE_COMPATIBLE_PRIOR_BINDINGS",
            "sec_xbrl_auth_binding_context_mismatch",
            "sec_xbrl_auth_binding_role_route_forbidden",
            "sec_xbrl_auth_binding_source_route_actor_conflict",
        ),
    )
    api_route_enforcement_current = _all_tokens(
        sources["api"],
        (
            "_sec_xbrl_require_binding",
            "_sec_xbrl_record_binding",
            "sec_xbrl_operator_review_workflow_status_read",
            "sec_xbrl_operator_review_decision_submit_write",
            "sec_xbrl_operator_review_decision_status_read",
            "sec_xbrl_value_reveal_authority_prepare_write",
            "sec_xbrl_controlled_value_reveal_submit_write",
            "sec_xbrl_controlled_value_reveal_submit_status_read",
            "source_auth_binding_ref",
            "auth_binding_required",
        ),
    )
    route_doc_current = _all_tokens(
        sources["auth_route_enforcement_doc"],
        (
            "workflow status requires an existing workflow auth binding",
            "value-reveal authority prepare requires an existing decision auth binding",
            "controlled value-reveal submit requires an existing authority auth binding",
            "protected mutating routes now defer source-receipt service commits",
            "historical unbound receipts",
            "no production-readiness claim",
        ),
    )
    test_evidence_current = _all_tokens(
        sources["auth_binding_tests"] + "\n" + sources["operator_workflow_tests"],
        (
            "test_auth_binding_requires_matching_owner_context",
            "test_auth_binding_accepts_legacy_policy_hash_candidate_for_existing_binding",
            "test_auth_binding_inspection_returns_redacted_list_for_multiple_route_bindings",
            "test_operator_review_workflow_status_api_requires_auth_binding_for_existing_workflow",
            "test_operator_review_decision_status_api_returns_read_only_projection",
            "test_operator_review_decision_status_rejects_missing_authority",
            "test_value_reveal_authority_api_rolls_back_source_receipt_when_binding_fails",
            "test_controlled_value_reveal_submit_api_rolls_back_source_receipt_when_binding_fails",
        ),
    )
    checks = {
        "policy_report_clean": policy_report_clean,
        "strategy_report_clean": strategy_report_clean,
        "policy_service_current": policy_service_current,
        "binding_service_current": binding_service_current,
        "api_route_enforcement_current": api_route_enforcement_current,
        "route_enforcement_doc_current": route_doc_current,
        "route_and_binding_test_evidence_current": test_evidence_current,
    }
    blockers = [
        f"nonlocal_production_readiness_in_app_auth_{name}_missing"
        for name, passed in checks.items()
        if not passed
    ]
    return {
        "admissible": not blockers,
        "blocked_reasons": blockers,
        "selected_auth_mode": "sec_xbrl_repo_owned_in_app_operator_auth_boundary_v1",
        "route_family_count": 6,
        "evidence_checks": checks,
        "source_reports": {
            "in_app_auth_policy_validation": {
                "path": IN_APP_AUTH_POLICY_REPORT,
                "decision": policy_report.get("decision"),
                "blocking_reasons_count": len(policy_report.get("blocking_reasons", [])),
                "report_hash": _file_hash(root / IN_APP_AUTH_POLICY_REPORT),
            },
            "auth_owner_binding_strategy": {
                "path": AUTH_OWNER_BINDING_STRATEGY_REPORT,
                "decision": strategy_report.get("decision"),
                "blocking_reasons_count": len(strategy_report.get("blocking_reasons", [])),
                "report_hash": _file_hash(root / AUTH_OWNER_BINDING_STRATEGY_REPORT),
            },
        },
        "source_files": {
            "policy_service": IN_APP_AUTH_POLICY_SERVICE,
            "auth_binding_service": AUTH_BINDING_SERVICE,
            "api": "backend/app/api/layer3.py",
            "auth_binding_tests": AUTH_BINDING_TEST,
            "operator_workflow_tests": OPERATOR_WORKFLOW_TEST,
        },
        "production_readiness_claimed": False,
        "value_reveal_default_enabled_by_evidence": False,
        "export_or_delivery_enabled_by_evidence": False,
        "source_acquisition_performed_by_evidence": False,
        "arelle_subprocess_invoked_by_evidence": False,
        "historical_unbound_receipt_backfill_admitted": False,
    }


def _authority_packet_summary(authority_packet_path: str | Path | None) -> dict[str, Any]:
    if authority_packet_path is None:
        return {
            "authority_packet_present": False,
            "authority_packet_hash": None,
            "required_fields_present": [],
            "required_fields_missing": list(REQUIRED_AUTHORITY_FIELDS),
            "admissible": False,
            "redaction_scan": {"status": "not_run", "hit_classes": []},
            "blocked_reason": "nonlocal_production_readiness_authority_packet_missing",
        }

    packet_path = Path(authority_packet_path)
    try:
        packet_text = packet_path.read_text(encoding="utf-8-sig")
        packet = json.loads(packet_text)
    except (OSError, json.JSONDecodeError):
        return {
            "authority_packet_present": True,
            "authority_packet_hash": None,
            "required_fields_present": [],
            "required_fields_missing": list(REQUIRED_AUTHORITY_FIELDS),
            "admissible": False,
            "redaction_scan": {"status": "failed_closed", "hit_classes": []},
            "blocked_reason": "nonlocal_production_readiness_authority_packet_unreadable",
        }

    if not isinstance(packet, dict):
        return {
            "authority_packet_present": True,
            "authority_packet_hash": _stable_hash(packet),
            "required_fields_present": [],
            "required_fields_missing": list(REQUIRED_AUTHORITY_FIELDS),
            "admissible": False,
            "redaction_scan": {"status": "failed_closed", "hit_classes": []},
            "blocked_reason": "nonlocal_production_readiness_authority_packet_invalid_shape",
        }

    missing = [field for field in REQUIRED_AUTHORITY_FIELDS if field not in packet]
    present = [field for field in REQUIRED_AUTHORITY_FIELDS if field in packet]
    invalid_ref_fields = _invalid_redacted_ref_fields(packet)
    invalid = _invalid_authority_fields(packet, invalid_ref_fields=invalid_ref_fields)
    raw_hits = sorted(set(_redaction_hit_classes(packet_text, packet)))
    blocked_reason = None
    if raw_hits:
        blocked_reason = "nonlocal_production_readiness_raw_authority_not_admitted"
    elif missing:
        blocked_reason = "nonlocal_production_readiness_authority_packet_missing_required_fields"
    elif invalid:
        blocked_reason = "nonlocal_production_readiness_authority_packet_invalid_required_fields"

    return {
        "authority_packet_present": True,
        "authority_packet_hash": _stable_hash(packet),
        "required_fields_present": present,
        "required_fields_missing": missing,
        "invalid_required_fields": invalid,
        "admissible": blocked_reason is None,
        "redaction_scan": {
            "status": "failed_closed" if raw_hits else "passed",
            "hit_classes": raw_hits,
        },
        "blocked_reason": blocked_reason,
        "deployment_mode": packet.get("deployment_mode") if packet.get("deployment_mode") == "nonlocal" else None,
        "proxy_boundary_mode": (
            packet.get("proxy_boundary_mode")
            if packet.get("proxy_boundary_mode") in ALLOWED_PROXY_BOUNDARY_MODES
            else None
        ),
        "storage_exposure_policy": (
            packet.get("storage_exposure_policy")
            if packet.get("storage_exposure_policy") in ALLOWED_STORAGE_EXPOSURE_POLICIES
            else None
        ),
        "arelle_fact_authority_nonlocal_authorized": (
            packet.get("arelle_fact_authority_nonlocal_authorized") is True
        ),
        "redaction_policy_id": (
            packet.get("redaction_policy_id")
            if packet.get("redaction_policy_id") == REDACTION_POLICY_ID
            else None
        ),
    }


def _invalid_authority_fields(
    packet: dict[str, Any],
    *,
    invalid_ref_fields: list[str] | None = None,
) -> list[str]:
    invalid: list[str] = []
    if packet.get("deployment_mode") != "nonlocal":
        invalid.append("deployment_mode")
    if packet.get("proxy_boundary_mode") not in ALLOWED_PROXY_BOUNDARY_MODES:
        invalid.append("proxy_boundary_mode")
    if not _header_name(packet.get("proxy_identity_header")):
        invalid.append("proxy_identity_header")
    if packet.get("storage_exposure_policy") not in ALLOWED_STORAGE_EXPOSURE_POLICIES:
        invalid.append("storage_exposure_policy")
    if packet.get("arelle_fact_authority_nonlocal_authorized") is not True:
        invalid.append("arelle_fact_authority_nonlocal_authorized")
    if packet.get("redaction_policy_id") != REDACTION_POLICY_ID:
        invalid.append("redaction_policy_id")
    for field in HASH_FIELDS:
        if not isinstance(packet.get(field), str) or not HASH_RE.fullmatch(packet[field]):
            invalid.append(field)
    invalid.extend(invalid_ref_fields if invalid_ref_fields is not None else _invalid_redacted_ref_fields(packet))
    return sorted(set(invalid))


def _redaction_hit_classes(packet_text: str, packet: Any) -> list[str]:
    return _framework_redaction_hit_classes(
        packet_text,
        packet,
        regexes={
            "raw_operator_email": EMAIL_RE,
            "raw_accession": ACCESSION_RE,
            "raw_cik": RAW_CIK_RE,
            "sec_url": SEC_URL_RE,
            "local_path": LOCAL_PATH_RE,
            "raw_period_date": PERIOD_DATE_RE,
            "raw_decimal_or_residual_magnitude": RAW_DECIMAL_RE,
        },
        raw_keys=RAW_KEYS,
        authority_ref_invalid=lambda value: isinstance(value, dict) and bool(_invalid_redacted_ref_fields(value)),
    )


def _invalid_redacted_ref_fields(packet: dict[str, Any]) -> list[str]:
    authority_ref_fields = {
        str(field)
        for field in packet
        if isinstance(field, str) and field.endswith("_ref")
    }
    authority_ref_fields.update(field for field in REF_FIELDS if field in packet)
    return sorted(field for field in authority_ref_fields if not _redacted_ref(packet.get(field)))


def _nonlocal_guardrails_hold(config: str, api_tests: str) -> bool:
    return all(
        token in config
        for token in (
            'deployment_mode: Literal["local", "nonlocal"]',
            'auth_owner: Literal["none", "proxy"]',
            "ALLOWED_ORIGINS must use explicit origins when DEPLOYMENT_MODE=nonlocal",
            "ALLOWED_ORIGINS must use HTTPS origins when DEPLOYMENT_MODE=nonlocal",
            "AUTH_OWNER=proxy is required when DEPLOYMENT_MODE=nonlocal",
            "TRUSTED_PROXY_MODE=true is required when DEPLOYMENT_MODE=nonlocal",
            "PROXY_IDENTITY_HEADER is required when DEPLOYMENT_MODE=nonlocal",
            "STORAGE_EXPOSURE must be auto or disabled when DEPLOYMENT_MODE=nonlocal",
            "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED=true is required",
        )
    ) and all(
        token in api_tests
        for token in (
            "test_layer3_deployment_profile_nonlocal_accepts_proxy_owned_guardrail",
            "test_layer3_deployment_profile_nonlocal_requires_explicit_arelle_cutover_authorization",
            "test_layer3_deployment_profile_nonlocal_main_disables_direct_storage",
            "test_layer3_deployment_profile_nonlocal_fails_closed",
        )
    )


def _non_admitted_surfaces_hold(sources: dict[str, Any]) -> bool:
    config = sources["config"]
    runtime_report_text = json.dumps(sources["runtime_report"], sort_keys=True)
    return all(
        token in config
        for token in (
            'layer3_sec_edgar_arelle_internal_value_store_enabled: bool = Field(\n        default=False,',
            'layer3_sec_edgar_arelle_corpus_validation_enabled: bool = Field(\n        default=False,',
            'layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(\n        default=False,',
            'layer3_sec_xbrl_controlled_value_reveal_submit_enabled: bool = Field(\n        default=False,',
        )
    ) and all(
        token in runtime_report_text
        for token in (
            '"delivery_export_enabled": false',
            '"production_readiness_claimed": false',
            '"raw_internal_value_store_default_on_claimed": false',
            '"value_reveal_default_on_claimed": false',
        )
    )


def _all_tokens(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


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


def _header_name(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _file_hash(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
