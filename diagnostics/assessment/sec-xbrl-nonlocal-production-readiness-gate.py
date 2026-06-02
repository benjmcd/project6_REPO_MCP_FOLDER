from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json")
RUNTIME_REPORT = "diagnostics/assessment/sec-xbrl-default-on-runtime-report.json"
DESIGN_DOC = "next_milestone_plans/Layer3_planning_docs/1319-nonlocal-production-readiness.md"
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
    sources = {
        "config": _read(root / "backend/app/core/config.py"),
        "api": _read(root / "backend/app/api/layer3.py"),
        "api_tests": _read(root / "backend/tests/test_layer3_api.py"),
        "runtime_report": runtime_report,
        "design_doc": _read(root / DESIGN_DOC),
    }
    authority = _authority_packet_summary(authority_packet_path)

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
            "authority_packet_present_and_admissible",
            authority["admissible"],
            authority,
            authority["blocked_reason"],
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
        },
        "source_documents": {
            "nonlocal_readiness_design": DESIGN_DOC,
        },
        "next_slice": (
            "sec_xbrl_nonlocal_deployment_authority_packet_or_in_app_auth_boundary_v1"
            if blocking_reasons
            else "sec_xbrl_nonlocal_production_readiness_operator_review_v1"
        ),
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
    if isinstance(packet, dict) and _invalid_redacted_ref_fields(packet):
        hits.append("raw_or_unreduced_authority_ref")
    for key in _iter_keys(packet):
        if key.lower() in RAW_KEYS:
            hits.append("raw_or_local_authority_key")
    return hits


def _invalid_redacted_ref_fields(packet: dict[str, Any]) -> list[str]:
    return [field for field in REF_FIELDS if field in packet and not _redacted_ref(packet.get(field))]


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


def _header_name(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
