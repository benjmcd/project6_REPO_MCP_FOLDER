from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_context_dossier_contract as dossier_contract


APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID = "aps.deterministic_insight_artifact.v1"
APS_DETERMINISTIC_INSIGHT_ARTIFACT_FAILURE_SCHEMA_ID = "aps.deterministic_insight_artifact_failure.v1"
APS_DETERMINISTIC_INSIGHT_ARTIFACT_GATE_SCHEMA_ID = "aps.deterministic_insight_artifact_gate.v1"
APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION = 1

APS_DETERMINISTIC_INSIGHT_RULESET_CONTRACT_ID = "aps_deterministic_insight_ruleset_v1"
APS_DETERMINISTIC_INSIGHT_RULESET_ID = "single_dossier_presence_rules"
APS_DETERMINISTIC_INSIGHT_RULESET_VERSION = 1
APS_DETERMINISTIC_INSIGHT_MODE = "deterministic_rules_only"
APS_DETERMINISTIC_INSIGHT_ARTIFACT_ID_TOKEN_LEN = dossier_contract.APS_CONTEXT_DOSSIER_ARTIFACT_ID_TOKEN_LEN

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_SOURCE_DOSSIER_NOT_FOUND = "source_dossier_not_found"
APS_RUNTIME_FAILURE_SOURCE_DOSSIER_INVALID = "source_dossier_invalid"
APS_RUNTIME_FAILURE_SOURCE_DOSSIER_CONFLICT = "source_dossier_conflict"
APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND = "insight_artifact_not_found"
APS_RUNTIME_FAILURE_ARTIFACT_INVALID = "insight_artifact_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "insight_artifact_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "insight_artifact_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_insight_artifact_error"

APS_GATE_FAILURE_MISSING_REF = "missing_deterministic_insight_artifact_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_deterministic_insight_artifact_ref"
APS_GATE_FAILURE_ARTIFACT_SCHEMA = "deterministic_insight_artifact_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "deterministic_insight_artifact_failure_schema_mismatch"
APS_GATE_FAILURE_RULESET = "ruleset_mismatch"
APS_GATE_FAILURE_INSIGHT_MODE = "insight_mode_mismatch"
APS_GATE_FAILURE_SOURCE_DOSSIER_REF = "source_dossier_ref_mismatch"
APS_GATE_FAILURE_SOURCE_DOSSIER_SUMMARY = "source_dossier_summary_mismatch"
APS_GATE_FAILURE_FINDINGS = "findings_mismatch"
APS_GATE_FAILURE_FINDING_COUNTS = "finding_counts_mismatch"
APS_GATE_FAILURE_TOTAL_FINDINGS = "total_findings_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_DERIVATION_DRIFT = "deterministic_insight_artifact_derivation_drift"

APS_FINDING_CATEGORY_COVERAGE = "coverage"
APS_FINDING_CATEGORY_UNCERTAINTY = "uncertainty"
APS_FINDING_CATEGORY_CONSTRAINT = "constraint"
APS_FINDING_CATEGORY_QUALIFICATION = "qualification"

APS_FINDING_SEVERITY_INFO = "info"
APS_FINDING_SEVERITY_WARNING = "warning"
APS_FINDING_SEVERITY_CRITICAL = "critical"
APS_FINDING_SEVERITIES = (
    APS_FINDING_SEVERITY_INFO,
    APS_FINDING_SEVERITY_WARNING,
    APS_FINDING_SEVERITY_CRITICAL,
)

APS_RULE_ID_DOSSIER_ZERO_FACTS = "dossier_zero_facts"
APS_RULE_ID_SOURCE_PACKET_ZERO_FACTS_PARTIAL = "source_packet_zero_facts_partial"
APS_RULE_ID_DOSSIER_UNRESOLVED_QUESTIONS_PRESENT = "dossier_unresolved_questions_present"
APS_RULE_ID_DOSSIER_CONSTRAINTS_PRESENT = "dossier_constraints_present"
APS_RULE_ID_DOSSIER_CAVEATS_PRESENT = "dossier_caveats_present"
APS_RULE_VERSION_V1 = 1

APS_RULE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "rule_id": APS_RULE_ID_DOSSIER_ZERO_FACTS,
        "rule_version": APS_RULE_VERSION_V1,
        "category": APS_FINDING_CATEGORY_COVERAGE,
        "severity": APS_FINDING_SEVERITY_CRITICAL,
        "metric_field": "total_facts",
    },
    {
        "rule_id": APS_RULE_ID_SOURCE_PACKET_ZERO_FACTS_PARTIAL,
        "rule_version": APS_RULE_VERSION_V1,
        "category": APS_FINDING_CATEGORY_COVERAGE,
        "severity": APS_FINDING_SEVERITY_WARNING,
        "metric_field": "total_facts",
    },
    {
        "rule_id": APS_RULE_ID_DOSSIER_UNRESOLVED_QUESTIONS_PRESENT,
        "rule_version": APS_RULE_VERSION_V1,
        "category": APS_FINDING_CATEGORY_UNCERTAINTY,
        "severity": APS_FINDING_SEVERITY_WARNING,
        "metric_field": "total_unresolved_questions",
    },
    {
        "rule_id": APS_RULE_ID_DOSSIER_CONSTRAINTS_PRESENT,
        "rule_version": APS_RULE_VERSION_V1,
        "category": APS_FINDING_CATEGORY_CONSTRAINT,
        "severity": APS_FINDING_SEVERITY_WARNING,
        "metric_field": "total_constraints",
    },
    {
        "rule_id": APS_RULE_ID_DOSSIER_CAVEATS_PRESENT,
        "rule_version": APS_RULE_VERSION_V1,
        "category": APS_FINDING_CATEGORY_QUALIFICATION,
        "severity": APS_FINDING_SEVERITY_INFO,
        "metric_field": "total_caveats",
    },
)


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_deterministic_insight_artifact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("deterministic_insight_artifact_checksum", None)
    clean.pop("_deterministic_insight_artifact_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_deterministic_insight_artifact_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_deterministic_insight_artifact_payload(payload))


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_DETERMINISTIC_INSIGHT_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_deterministic_insight_artifact_file_name(*, scope: str, deterministic_insight_artifact_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(deterministic_insight_artifact_id)}"
        "_aps_deterministic_insight_artifact_v1.json"
    )


def expected_failure_file_name(*, scope: str, deterministic_insight_artifact_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(deterministic_insight_artifact_id)}"
        "_aps_deterministic_insight_artifact_failure_v1.json"
    )


def derive_failure_deterministic_insight_artifact_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_INSIGHT_ARTIFACT_FAILURE_SCHEMA_ID,
            APS_DETERMINISTIC_INSIGHT_RULESET_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_deterministic_insight_artifact_id(*, source_context_dossier_id: str) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID,
            APS_DETERMINISTIC_INSIGHT_RULESET_CONTRACT_ID,
            APS_DETERMINISTIC_INSIGHT_RULESET_ID,
            str(APS_DETERMINISTIC_INSIGHT_RULESET_VERSION),
            APS_DETERMINISTIC_INSIGHT_MODE,
            str(source_context_dossier_id or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_finding_id(*, deterministic_insight_artifact_id: str, rule_id: str, rule_version: int) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID,
            str(deterministic_insight_artifact_id or ""),
            str(rule_id or ""),
            str(int(rule_version or 0)),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    context_dossier_id = str(payload.get("context_dossier_id") or "").strip() or None
    context_dossier_ref = str(payload.get("context_dossier_ref") or "").strip() or None
    if bool(context_dossier_id) == bool(context_dossier_ref):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    return {
        "context_dossier_id": context_dossier_id,
        "context_dossier_ref": context_dossier_ref,
        "persist_insight_artifact": bool(payload.get("persist_insight_artifact", False)),
    }


def ruleset_identity_payload() -> dict[str, Any]:
    return {
        "ruleset_contract_id": APS_DETERMINISTIC_INSIGHT_RULESET_CONTRACT_ID,
        "ruleset_id": APS_DETERMINISTIC_INSIGHT_RULESET_ID,
        "ruleset_version": APS_DETERMINISTIC_INSIGHT_RULESET_VERSION,
    }


def source_context_dossier_summary_payload(source_payload: dict[str, Any]) -> dict[str, Any]:
    source_packets = [dict(item or {}) for item in list(source_payload.get("source_packets") or []) if isinstance(item, dict)]
    return {
        "schema_id": str(source_payload.get("schema_id") or ""),
        "schema_version": int(source_payload.get("schema_version") or 0),
        "context_dossier_id": str(source_payload.get("context_dossier_id") or ""),
        "context_dossier_checksum": str(source_payload.get("context_dossier_checksum") or ""),
        "context_dossier_ref": str(source_payload.get("_context_dossier_ref") or source_payload.get("context_dossier_ref") or "") or None,
        "composition_contract_id": str(source_payload.get("composition_contract_id") or ""),
        "dossier_mode": str(source_payload.get("dossier_mode") or ""),
        "owner_run_id": str(source_payload.get("owner_run_id") or ""),
        "projection_contract_id": str(source_payload.get("projection_contract_id") or ""),
        "fact_grammar_contract_id": str(source_payload.get("fact_grammar_contract_id") or ""),
        "objective": str(source_payload.get("objective") or ""),
        "source_family": str(source_payload.get("source_family") or ""),
        "source_packet_count": int(source_payload.get("source_packet_count") or 0),
        "ordered_source_packets_sha256": str(source_payload.get("ordered_source_packets_sha256") or ""),
        "total_facts": int(source_payload.get("total_facts") or 0),
        "total_caveats": int(source_payload.get("total_caveats") or 0),
        "total_constraints": int(source_payload.get("total_constraints") or 0),
        "total_unresolved_questions": int(source_payload.get("total_unresolved_questions") or 0),
        "source_packets": [
            {
                "packet_ordinal": int(item.get("packet_ordinal") or 0),
                "context_packet_id": str(item.get("context_packet_id") or ""),
                "total_facts": int(item.get("total_facts") or 0),
                "total_caveats": int(item.get("total_caveats") or 0),
                "total_constraints": int(item.get("total_constraints") or 0),
                "total_unresolved_questions": int(item.get("total_unresolved_questions") or 0),
            }
            for item in source_packets
        ],
    }


def rule_evaluation_view(source_context_dossier: dict[str, Any]) -> dict[str, Any]:
    source_packets = [dict(item or {}) for item in list(source_context_dossier.get("source_packets") or []) if isinstance(item, dict)]
    return {
        "total_facts": int(source_context_dossier.get("total_facts") or 0),
        "total_caveats": int(source_context_dossier.get("total_caveats") or 0),
        "total_constraints": int(source_context_dossier.get("total_constraints") or 0),
        "total_unresolved_questions": int(source_context_dossier.get("total_unresolved_questions") or 0),
        "source_packet_count": int(source_context_dossier.get("source_packet_count") or 0),
        "source_packets": [
            {
                "total_facts": int(item.get("total_facts") or 0),
                "total_caveats": int(item.get("total_caveats") or 0),
                "total_constraints": int(item.get("total_constraints") or 0),
                "total_unresolved_questions": int(item.get("total_unresolved_questions") or 0),
            }
            for item in source_packets
        ],
    }


def _evidence_pointer(*, pointer: str, packet_ordinal: int | None = None, context_packet_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"pointer": str(pointer or "")}
    if packet_ordinal is not None:
        payload["packet_ordinal"] = int(packet_ordinal)
    if str(context_packet_id or "").strip():
        payload["context_packet_id"] = str(context_packet_id or "").strip()
    return payload


def _matched_packet_evidence(*, source_context_dossier: dict[str, Any], matched_indexes: list[int], metric_field: str) -> list[dict[str, Any]]:
    source_packets = [dict(item or {}) for item in list(source_context_dossier.get("source_packets") or []) if isinstance(item, dict)]
    evidence: list[dict[str, Any]] = []
    for index in matched_indexes:
        if index < 0 or index >= len(source_packets):
            continue
        source_packet = source_packets[index]
        evidence.append(
            _evidence_pointer(
                pointer=f"/source_context_dossier/source_packets/{index}/{metric_field}",
                packet_ordinal=int(source_packet.get("packet_ordinal") or 0),
                context_packet_id=str(source_packet.get("context_packet_id") or "") or None,
            )
        )
    return evidence


def _finding_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        APS_FINDING_SEVERITY_INFO: 0,
        APS_FINDING_SEVERITY_WARNING: 0,
        APS_FINDING_SEVERITY_CRITICAL: 0,
    }
    for finding in findings:
        severity = str(finding.get("severity") or "")
        if severity in counts:
            counts[severity] = int(counts.get(severity, 0)) + 1
    return counts


def evaluate_findings(*, source_context_dossier: dict[str, Any], deterministic_insight_artifact_id: str) -> list[dict[str, Any]]:
    rule_input = rule_evaluation_view(source_context_dossier)
    findings: list[dict[str, Any]] = []
    source_packet_count = int(rule_input.get("source_packet_count") or 0)
    source_packets = [dict(item or {}) for item in list(rule_input.get("source_packets") or []) if isinstance(item, dict)]

    if int(rule_input.get("total_facts") or 0) == 0:
        matched_indexes = [index for index, _item in enumerate(source_packets)]
        evidence = [_evidence_pointer(pointer="/source_context_dossier/total_facts")]
        evidence.extend(_matched_packet_evidence(source_context_dossier=source_context_dossier, matched_indexes=matched_indexes, metric_field="total_facts"))
        findings.append(
            {
                "rule_id": APS_RULE_ID_DOSSIER_ZERO_FACTS,
                "rule_version": APS_RULE_VERSION_V1,
                "category": APS_FINDING_CATEGORY_COVERAGE,
                "severity": APS_FINDING_SEVERITY_CRITICAL,
                "matched_source_packet_count": source_packet_count,
                "message": f"Dossier contains zero facts across {source_packet_count} source packets.",
                "evidence_pointers": evidence,
            }
        )

    zero_fact_indexes = [index for index, item in enumerate(source_packets) if int(item.get("total_facts") or 0) == 0]
    if int(rule_input.get("total_facts") or 0) > 0 and zero_fact_indexes:
        evidence = [_evidence_pointer(pointer="/source_context_dossier/total_facts")]
        evidence.extend(_matched_packet_evidence(source_context_dossier=source_context_dossier, matched_indexes=zero_fact_indexes, metric_field="total_facts"))
        findings.append(
            {
                "rule_id": APS_RULE_ID_SOURCE_PACKET_ZERO_FACTS_PARTIAL,
                "rule_version": APS_RULE_VERSION_V1,
                "category": APS_FINDING_CATEGORY_COVERAGE,
                "severity": APS_FINDING_SEVERITY_WARNING,
                "matched_source_packet_count": len(zero_fact_indexes),
                "message": (
                    f"{len(zero_fact_indexes)} source packets contain zero facts while "
                    f"dossier total_facts={int(rule_input.get('total_facts') or 0)}."
                ),
                "evidence_pointers": evidence,
            }
        )

    unresolved_indexes = [
        index for index, item in enumerate(source_packets) if int(item.get("total_unresolved_questions") or 0) > 0
    ]
    if int(rule_input.get("total_unresolved_questions") or 0) > 0:
        evidence = [_evidence_pointer(pointer="/source_context_dossier/total_unresolved_questions")]
        evidence.extend(
            _matched_packet_evidence(
                source_context_dossier=source_context_dossier,
                matched_indexes=unresolved_indexes,
                metric_field="total_unresolved_questions",
            )
        )
        findings.append(
            {
                "rule_id": APS_RULE_ID_DOSSIER_UNRESOLVED_QUESTIONS_PRESENT,
                "rule_version": APS_RULE_VERSION_V1,
                "category": APS_FINDING_CATEGORY_UNCERTAINTY,
                "severity": APS_FINDING_SEVERITY_WARNING,
                "matched_source_packet_count": len(unresolved_indexes),
                "message": (
                    f"Dossier records {int(rule_input.get('total_unresolved_questions') or 0)} unresolved questions "
                    f"across {len(unresolved_indexes)} source packets."
                ),
                "evidence_pointers": evidence,
            }
        )

    constraint_indexes = [index for index, item in enumerate(source_packets) if int(item.get("total_constraints") or 0) > 0]
    if int(rule_input.get("total_constraints") or 0) > 0:
        evidence = [_evidence_pointer(pointer="/source_context_dossier/total_constraints")]
        evidence.extend(
            _matched_packet_evidence(
                source_context_dossier=source_context_dossier,
                matched_indexes=constraint_indexes,
                metric_field="total_constraints",
            )
        )
        findings.append(
            {
                "rule_id": APS_RULE_ID_DOSSIER_CONSTRAINTS_PRESENT,
                "rule_version": APS_RULE_VERSION_V1,
                "category": APS_FINDING_CATEGORY_CONSTRAINT,
                "severity": APS_FINDING_SEVERITY_WARNING,
                "matched_source_packet_count": len(constraint_indexes),
                "message": (
                    f"Dossier records {int(rule_input.get('total_constraints') or 0)} constraints across "
                    f"{len(constraint_indexes)} source packets."
                ),
                "evidence_pointers": evidence,
            }
        )

    caveat_indexes = [index for index, item in enumerate(source_packets) if int(item.get("total_caveats") or 0) > 0]
    if int(rule_input.get("total_caveats") or 0) > 0:
        evidence = [_evidence_pointer(pointer="/source_context_dossier/total_caveats")]
        evidence.extend(
            _matched_packet_evidence(
                source_context_dossier=source_context_dossier,
                matched_indexes=caveat_indexes,
                metric_field="total_caveats",
            )
        )
        findings.append(
            {
                "rule_id": APS_RULE_ID_DOSSIER_CAVEATS_PRESENT,
                "rule_version": APS_RULE_VERSION_V1,
                "category": APS_FINDING_CATEGORY_QUALIFICATION,
                "severity": APS_FINDING_SEVERITY_INFO,
                "matched_source_packet_count": len(caveat_indexes),
                "message": (
                    f"Dossier records {int(rule_input.get('total_caveats') or 0)} caveats across "
                    f"{len(caveat_indexes)} source packets."
                ),
                "evidence_pointers": evidence,
            }
        )

    ordered_findings: list[dict[str, Any]] = []
    for rule_spec in APS_RULE_SPECS:
        rule_id = str(rule_spec.get("rule_id") or "")
        matched = next((dict(item) for item in findings if str(item.get("rule_id") or "") == rule_id), None)
        if matched is None:
            continue
        matched["finding_id"] = derive_finding_id(
            deterministic_insight_artifact_id=deterministic_insight_artifact_id,
            rule_id=rule_id,
            rule_version=int(matched.get("rule_version") or 0),
        )
        ordered_findings.append(matched)
    return ordered_findings


def build_deterministic_insight_artifact_payload(
    source_context_dossier_payload: dict[str, Any],
    *,
    generated_at_utc: str,
) -> dict[str, Any]:
    source_context_dossier = source_context_dossier_summary_payload(source_context_dossier_payload)
    payload: dict[str, Any] = {
        "schema_id": APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID,
        "schema_version": APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        **ruleset_identity_payload(),
        "insight_mode": APS_DETERMINISTIC_INSIGHT_MODE,
        "source_context_dossier": source_context_dossier,
    }
    payload["deterministic_insight_artifact_id"] = derive_deterministic_insight_artifact_id(
        source_context_dossier_id=str(source_context_dossier.get("context_dossier_id") or "")
    )
    findings = evaluate_findings(
        source_context_dossier=source_context_dossier,
        deterministic_insight_artifact_id=str(payload.get("deterministic_insight_artifact_id") or ""),
    )
    payload["findings"] = findings
    payload["total_findings"] = len(findings)
    payload["finding_counts"] = _finding_counts(findings)
    payload["deterministic_insight_artifact_checksum"] = compute_deterministic_insight_artifact_checksum(payload)
    return payload
